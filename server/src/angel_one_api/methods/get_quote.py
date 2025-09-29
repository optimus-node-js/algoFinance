"""
Angel One API: getQuote - Enhanced Market Quotes
===============================================

METHOD: Enhanced real-time market quotes with additional data
Rate Limit: 10 requests/second per API key
Priority: HIGH (enhanced market data)

Usage:
    from angel_one_api.methods.get_quote import get_quote
    
    # Get enhanced quote for single symbol
    quote = await get_quote("NSE", "RELIANCE-EQ", "2885")
    
    # Get quotes for multiple symbols
    quotes = await get_multiple_quotes([
        {"exchange": "NSE", "tradingsymbol": "TCS-EQ", "symboltoken": "11536"},
        {"exchange": "NSE", "tradingsymbol": "INFY-EQ", "symboltoken": "1594"}
    ])

Author: AI Trading System
Rate Limit: STRICTLY ENFORCED 10 req/sec per key
"""

import time
import asyncio
from typing import Dict, List, Optional, Any
# Import new Angel One logger
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))
from logger import get_api_logger
from datetime import datetime, UTC

# Import our rate limiting system
from rate_limiter.rate_controller import get_rate_controller, rate_limited, APIPriority
from rate_limiter.api_limits import API_LIMITS

# Import idempotency enhancements
try:
    from ..enhancements.idempotency_manager import idempotency_wrapper
    IDEMPOTENCY_AVAILABLE = True
except ImportError:
    IDEMPOTENCY_AVAILABLE = False

logger = get_api_logger("get_quote")

class QuoteError(Exception):
    """Raised when quote fetching fails."""
    pass

@idempotency_wrapper(method_type="market", ttl=30, cache_response=True) if IDEMPOTENCY_AVAILABLE else lambda x: x
@rate_limited("get_quote", APIPriority.HIGH)
async def get_quote(
    exchange: str,
    tradingsymbol: str,
    symboltoken: str,
    _rate_limit_permit: Optional[Dict] = None
) -> Dict[str, Any]:
    """
    Get enhanced market quote from Angel One API.
    
    Args:
        exchange: Exchange name (NSE, BSE, NFO, MCX)
        tradingsymbol: Trading symbol (e.g., "RELIANCE-EQ")
        symboltoken: Angel One symbol token
        _rate_limit_permit: Automatically provided by rate limiter
        
    Returns:
        Dict containing:
            - success: bool
            - quote_data: Dict of enhanced quote information
            - basic_info: Dict (symbol, ltp, change)
            - detailed_info: Dict (ohlc, volume, etc.)
            - timestamp: str
        
    Raises:
        QuoteError: If quote fetching fails
        RateLimitExceeded: If rate limit would be exceeded
        
    Rate Limit: 10 requests/second per API key
    """
    try:
        if not _rate_limit_permit:
            raise QuoteError("No rate limit permit - internal error")
        
        # Get Angel One client
        # Use interface to get SmartAPI client
        from interface import get_angel_one_interface
        interface = get_angel_one_interface()
        angel_client = interface.smart_api
        
        # angel_client already set above
        if not angel_client:
            raise QuoteError("Angel One API client not available")
        
        # Validate parameters
        if not all([exchange, tradingsymbol, symboltoken]):
            raise QuoteError("Exchange, tradingsymbol, and symboltoken are required")
        
        # Log request
        logger.debug(f"📊 Quote request: {tradingsymbol} using {_rate_limit_permit['api_key_id']}")
        
        # Make API call with strict rate limiting already enforced
        # Check if method exists, use correct SmartConnect method name
        if hasattr(angel_client, 'getQuote'):
            response = angel_client.getQuote(
                exchange=exchange,
                tradingsymbol=tradingsymbol,
                symboltoken=symboltoken
            )
        elif hasattr(angel_client, 'ltpData'):
            # Fallback to ltpData if getQuote not available
            response = angel_client.ltpData(
                exchange=exchange,
                tradingsymbol=tradingsymbol,
                symboltoken=symboltoken
            )
        else:
            raise QuoteError("Neither getQuote nor ltpData method available in SmartConnect SDK")
        
        # Parse response
        if not response:
            raise QuoteError("Empty response from getQuote API")
        
        if not response.get('status'):
            error_msg = response.get('message', 'Unknown error')
            raise QuoteError(f"Quote API error: {error_msg}")
        
        quote_data = response.get('data', {})
        
        # Process quote data
        processed_quote = _process_quote_data(quote_data)
        
        # Extract key information
        basic_info = _extract_basic_info(processed_quote)
        detailed_info = _extract_detailed_info(processed_quote)
        market_info = _extract_market_info(processed_quote)
        
        # Success response
        result = {
            'success': True,
            'quote_data': processed_quote,
            'basic_info': basic_info,
            'detailed_info': detailed_info,
            'market_info': market_info,
            'symbol_info': {
                'exchange': exchange,
                'tradingsymbol': tradingsymbol,
                'symboltoken': symboltoken
            },
            'raw_data': quote_data,
            'timestamp': datetime.now(UTC).isoformat(),
            'api_key_id': _rate_limit_permit['api_key_id'],
            'response_time': time.time()
        }
        
        ltp = basic_info.get('ltp', 0)
        change_pct = basic_info.get('change_percentage', 0)
        logger.info(f"✅ Quote fetched: {tradingsymbol} ₹{ltp:.2f} ({change_pct:+.2f}%)")
        
        return result
        
    except Exception as e:
        logger.error(f"❌ Quote fetch failed for {tradingsymbol}: {e}")
        
        # Create error response
        error_result = {
            'success': False,
            'quote_data': {},
            'error': str(e),
            'timestamp': datetime.now(UTC).isoformat()
        }
        
        # Re-raise as QuoteError for consistent error handling
        if isinstance(e, QuoteError):
            raise
        else:
            raise QuoteError(f"Quote fetch failed: {e}")

def _process_quote_data(quote_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Process and clean raw quote data from Angel One API.
    
    Args:
        quote_data: Raw quote data from API
        
    Returns:
        Dict: Cleaned and enhanced quote data
    """
    try:
        # Core quote fields
        processed = {
            'tradingsymbol': quote_data.get('tradingsymbol', ''),
            'exchange': quote_data.get('exchange', ''),
            'instrumenttype': quote_data.get('instrumenttype', ''),
            'symboltoken': quote_data.get('symboltoken', ''),
            
            # Price fields
            'ltp': float(quote_data.get('ltp', 0)),
            'open': float(quote_data.get('open', 0)),
            'high': float(quote_data.get('high', 0)),
            'low': float(quote_data.get('low', 0)),
            'close': float(quote_data.get('close', 0)),
            
            # Volume and value
            'volume': int(quote_data.get('volume', 0)),
            'value': float(quote_data.get('value', 0)),
            
            # Change calculations
            'netchange': float(quote_data.get('netchange', 0)),
            'percentchange': float(quote_data.get('percentchange', 0)),
            
            # Bid/Ask data
            'bid_price': float(quote_data.get('bid', 0)),
            'ask_price': float(quote_data.get('ask', 0)),
            'bid_size': int(quote_data.get('bidsize', 0)),
            'ask_size': int(quote_data.get('asksize', 0)),
            
            # Additional fields
            'avgprice': float(quote_data.get('avgprice', 0)),
            'totalbuyqty': int(quote_data.get('totalbuyqty', 0)),
            'totalsellqty': int(quote_data.get('totalsellqty', 0)),
            'upper_circuit': float(quote_data.get('uppercircuit', 0)),
            'lower_circuit': float(quote_data.get('lowercircuit', 0)),
            'ltt': quote_data.get('ltt', ''),  # Last trade time
            'precision': int(quote_data.get('precision', 2))
        }
        
        return processed
        
    except (ValueError, TypeError) as e:
        logger.warning(f"⚠️ Error processing quote data: {e}")
        return quote_data  # Return original if processing fails

def _extract_basic_info(quote_data: Dict[str, Any]) -> Dict[str, Any]:
    """Extract basic quote information."""
    return {
        'symbol': quote_data.get('tradingsymbol'),
        'ltp': quote_data.get('ltp', 0),
        'change': quote_data.get('netchange', 0),
        'change_percentage': quote_data.get('percentchange', 0),
        'volume': quote_data.get('volume', 0),
        'last_trade_time': quote_data.get('ltt', '')
    }

def _extract_detailed_info(quote_data: Dict[str, Any]) -> Dict[str, Any]:
    """Extract detailed quote information."""
    return {
        'ohlc': {
            'open': quote_data.get('open', 0),
            'high': quote_data.get('high', 0),
            'low': quote_data.get('low', 0),
            'close': quote_data.get('close', 0)
        },
        'volume_data': {
            'volume': quote_data.get('volume', 0),
            'value': quote_data.get('value', 0),
            'average_price': quote_data.get('avgprice', 0)
        },
        'bid_ask': {
            'bid_price': quote_data.get('bid_price', 0),
            'ask_price': quote_data.get('ask_price', 0),
            'bid_size': quote_data.get('bid_size', 0),
            'ask_size': quote_data.get('ask_size', 0),
            'spread': quote_data.get('ask_price', 0) - quote_data.get('bid_price', 0)
        },
        'circuits': {
            'upper_circuit': quote_data.get('upper_circuit', 0),
            'lower_circuit': quote_data.get('lower_circuit', 0)
        }
    }

def _extract_market_info(quote_data: Dict[str, Any]) -> Dict[str, Any]:
    """Extract market-specific information."""
    total_buy = quote_data.get('totalbuyqty', 0)
    total_sell = quote_data.get('totalsellqty', 0)
    
    return {
        'market_depth': {
            'total_buy_quantity': total_buy,
            'total_sell_quantity': total_sell,
            'buy_sell_ratio': total_buy / total_sell if total_sell > 0 else 0,
            'market_sentiment': _assess_market_sentiment(total_buy, total_sell)
        },
        'liquidity': {
            'high_liquidity': quote_data.get('volume', 0) > 100000,
            'tight_spread': (quote_data.get('ask_price', 0) - quote_data.get('bid_price', 0)) < 0.05
        }
    }

def _assess_market_sentiment(total_buy: int, total_sell: int) -> str:
    """Assess market sentiment based on buy/sell quantities."""
    if total_buy == 0 and total_sell == 0:
        return 'NEUTRAL'
    
    ratio = total_buy / max(total_sell, 1)
    
    if ratio > 1.5:
        return 'BULLISH'
    elif ratio > 1.1:
        return 'SLIGHTLY_BULLISH'
    elif ratio < 0.67:
        return 'BEARISH'
    elif ratio < 0.9:
        return 'SLIGHTLY_BEARISH'
    else:
        return 'NEUTRAL'

async def get_multiple_quotes(
    symbols: List[Dict[str, str]],
    batch_delay: float = 0.1  # 10 req/sec = 0.1s between requests
) -> Dict[str, Dict[str, Any]]:
    """
    Get quotes for multiple symbols efficiently with rate limiting.
    
    Args:
        symbols: List of symbol dicts with exchange, tradingsymbol, symboltoken
        batch_delay: Delay between requests in seconds
        
    Returns:
        Dict: Symbol -> quote data mapping
    """
    if not symbols:
        return {}
    
    logger.info(f"📊 Bulk quote fetch for {len(symbols)} symbols")
    
    results = {}
    
    for i, symbol_info in enumerate(symbols):
        batch_start_time = time.time()
        
        symbol_key = symbol_info.get('tradingsymbol', f'symbol_{i}')
        
        try:
            quote_result = await get_quote(
                exchange=symbol_info.get('exchange'),
                tradingsymbol=symbol_info.get('tradingsymbol'),
                symboltoken=symbol_info.get('symboltoken')
            )
            results[symbol_key] = quote_result
            
            logger.debug(f"✅ Quote {i+1}/{len(symbols)}: {symbol_key}")
            
        except Exception as e:
            logger.warning(f"⚠️ Quote fetch failed for {symbol_key}: {e}")
            results[symbol_key] = {'success': False, 'error': str(e)}
        
        # Add delay between requests (except for last one)
        if i < len(symbols) - 1:
            elapsed = time.time() - batch_start_time
            if elapsed < batch_delay:
                sleep_time = batch_delay - elapsed
                await asyncio.sleep(sleep_time)
    
    successful_count = sum(1 for r in results.values() if r.get('success'))
    logger.info(f"✅ Bulk quote fetch complete: {successful_count}/{len(symbols)} successful")
    
    return results

async def get_market_snapshot(symbols: List[str]) -> Dict[str, Any]:
    """
    Get a market snapshot for multiple symbols.
    
    Args:
        symbols: List of trading symbols
        
    Returns:
        Dict: Market snapshot with summary statistics
    """
    try:
        # Convert symbols to format needed for get_multiple_quotes
        # Note: This would need actual symbol tokens - simplified for demo
        symbol_dicts = [
            {"exchange": "NSE", "tradingsymbol": symbol, "symboltoken": "0"}
            for symbol in symbols
        ]
        
        quotes_result = await get_multiple_quotes(symbol_dicts)
        
        # Calculate market statistics
        successful_quotes = [q for q in quotes_result.values() if q.get('success')]
        
        if not successful_quotes:
            return {'success': False, 'error': 'No successful quotes'}
        
        # Extract basic data for analysis
        changes = [q['basic_info']['change_percentage'] for q in successful_quotes]
        volumes = [q['basic_info']['volume'] for q in successful_quotes]
        
        market_summary = {
            'success': True,
            'total_symbols': len(symbols),
            'successful_symbols': len(successful_quotes),
            'market_statistics': {
                'advancing_stocks': sum(1 for c in changes if c > 0),
                'declining_stocks': sum(1 for c in changes if c < 0),
                'unchanged_stocks': sum(1 for c in changes if c == 0),
                'average_change': sum(changes) / len(changes) if changes else 0,
                'total_volume': sum(volumes),
                'market_sentiment': 'BULLISH' if sum(changes) > 0 else 'BEARISH'
            },
            'quotes': quotes_result,
            'timestamp': datetime.now(UTC).isoformat()
        }
        
        return market_summary
        
    except Exception as e:
        logger.error(f"❌ Market snapshot failed: {e}")
        return {'success': False, 'error': str(e)}

def get_quote_sync(exchange: str, tradingsymbol: str, symboltoken: str) -> Dict[str, Any]:
    """
    Synchronous wrapper for get_quote.
    
    ⚠️ WARNING: Use async version when possible for better performance.
    This is only for compatibility with legacy code.
    """
    import asyncio
    try:
        return asyncio.run(get_quote(exchange, tradingsymbol, symboltoken))
    except Exception as e:
        logger.error(f"❌ Sync quote fetch failed for {tradingsymbol}: {e}")
        return {
            'success': False,
            'quote_data': {},
            'error': str(e)
        }

# Backward compatibility aliases (DEPRECATED - use new names)
fetch_quote = get_quote  # Alias for existing code
get_market_quote = get_quote  # Alias for existing code

if __name__ == "__main__":
    # Test quote fetching
    async def test_quote_fetching():
        print("🧪 Testing Angel One Quote Fetching")
        print("=" * 40)
        
        # Test single quote
        try:
            quote = await get_quote("NSE", "RELIANCE-EQ", "2885")
            if quote['success']:
                basic = quote['basic_info']
                print(f"✅ Quote fetched: {basic['symbol']}")
                print(f"   LTP: ₹{basic['ltp']:.2f}")
                print(f"   Change: {basic['change']:+.2f} ({basic['change_percentage']:+.2f}%)")
                print(f"   Volume: {basic['volume']:,}")
            else:
                print(f"❌ Quote fetch failed: {quote.get('error')}")
        except Exception as e:
            print(f"❌ Quote test failed: {e}")
        
        print("\n⚠️ Note: Actual quote fetching requires rate controller and live connection")
    
    # Run test
    import asyncio
    asyncio.run(test_quote_fetching())
