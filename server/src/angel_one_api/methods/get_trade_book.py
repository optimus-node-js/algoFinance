"""
Angel One API: getTradeBook - Trade History Retrieval
====================================================

CRITICAL METHOD: Executed trades and transaction history
Rate Limit: 1 request/second per API key
Priority: HIGH (essential for trade tracking)

Usage:
    from angel_one_api.methods.get_trade_book import get_trade_book
    
    # Get all executed trades
    trades = await get_trade_book()
    
    # Get trades for specific symbol
    symbol_trades = await get_trades_by_symbol("RELIANCE-EQ")
    
    # Get today's trade summary
    summary = await get_trade_summary()

Author: AI Trading System
Rate Limit: STRICTLY ENFORCED 1 req/sec per key
"""

import time
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

logger = get_api_logger("get_trade_book")

class TradeBookError(Exception):
    """Raised when trade book fetching fails."""
    pass

@idempotency_wrapper(method_type="account", ttl=60, cache_response=True) if IDEMPOTENCY_AVAILABLE else lambda x: x
@rate_limited("get_trade_book", APIPriority.HIGH)
async def get_trade_book(_rate_limit_permit: Optional[Dict] = None) -> Dict[str, Any]:
    """
    Get trade book (executed trades) from Angel One API.
    
    Args:
        _rate_limit_permit: Automatically provided by rate limiter
        
    Returns:
        Dict containing:
            - success: bool
            - trades: List of trade data
            - total_trades: int
            - buy_trades: List
            - sell_trades: List
            - trade_summary: Dict
            - timestamp: str
        
    Raises:
        TradeBookError: If trade book fetching fails
        RateLimitExceeded: If rate limit would be exceeded
        
    Rate Limit: 1 request/second per API key
    """
    try:
        if not _rate_limit_permit:
            raise TradeBookError("No rate limit permit - internal error")
        
        # Get Angel One client
        # Use interface to get SmartAPI client
        from core.connections import ConnectionManager
        angel_client = ConnectionManager.get_smartapi_client()
        
        # angel_client already set above
        if not angel_client:
            raise TradeBookError("Angel One API client not available")
        
        # Log request
        logger.debug(f"📈 Trade book request using {_rate_limit_permit['api_key_id']}")
        
        # Make API call with strict rate limiting already enforced
        # Use the correct SmartConnect method name
        response = angel_client.tradeBook()
        
        # Parse response
        if not response:
            raise TradeBookError("Empty response from getTradeBook API")
        
        if not response.get('status'):
            error_msg = response.get('message', 'Unknown error')
            raise TradeBookError(f"Trade book API error: {error_msg}")
        
        trades_data = response.get('data', [])
        
        # Handle None data (empty trade book)
        if trades_data is None:
            logger.debug("📝 No trades found - empty trade book")
            trades_data = []
        
        # Validate trades data
        if not isinstance(trades_data, list):
            raise TradeBookError(f"Invalid trade book data format received. Expected list, got {type(trades_data)}: {trades_data}")
        
        # Process and categorize trades
        all_trades = []
        buy_trades = []
        sell_trades = []
        
        total_buy_value = 0.0
        total_sell_value = 0.0
        total_buy_quantity = 0
        total_sell_quantity = 0
        
        for trade in trades_data:
            # Clean and validate trade data
            processed_trade = _process_trade_data(trade)
            all_trades.append(processed_trade)
            
            # Categorize by transaction type
            if trade.get('transactiontype') == 'BUY':
                buy_trades.append(processed_trade)
                total_buy_value += processed_trade.get('trade_value', 0)
                total_buy_quantity += processed_trade.get('quantity', 0)
            elif trade.get('transactiontype') == 'SELL':
                sell_trades.append(processed_trade)
                total_sell_value += processed_trade.get('trade_value', 0)
                total_sell_quantity += processed_trade.get('quantity', 0)
        
        # Calculate trade summary
        net_value = total_sell_value - total_buy_value
        net_quantity = total_sell_quantity - total_buy_quantity
        
        trade_summary = {
            'total_trades': len(all_trades),
            'buy_trades_count': len(buy_trades),
            'sell_trades_count': len(sell_trades),
            'total_buy_value': total_buy_value,
            'total_sell_value': total_sell_value,
            'net_trade_value': net_value,
            'total_buy_quantity': total_buy_quantity,
            'total_sell_quantity': total_sell_quantity,
            'net_quantity': net_quantity,
            'unique_symbols': len(set(trade.get('tradingsymbol') for trade in all_trades)),
            'average_trade_size': (total_buy_value + total_sell_value) / len(all_trades) if all_trades else 0,
            'most_traded_symbol': _find_most_traded_symbol(all_trades),
            'largest_trade': _find_largest_trade(all_trades)
        }
        
        # Success response
        result = {
            'success': True,
            'trades': all_trades,
            'buy_trades': buy_trades,
            'sell_trades': sell_trades,
            'total_trades': len(all_trades),
            'trade_summary': trade_summary,
            'timestamp': datetime.now(UTC).isoformat(),
            'api_key_id': _rate_limit_permit['api_key_id'],
            'response_time': time.time()
        }
        
        logger.info(f"✅ Trade book fetched: {len(all_trades)} trades, Net: ₹{net_value:.2f}")
        
        return result
        
    except Exception as e:
        logger.error(f"❌ Trade book fetch failed: {e}")
        
        # Create error response
        error_result = {
            'success': False,
            'trades': [],
            'total_trades': 0,
            'error': str(e),
            'timestamp': datetime.now(UTC).isoformat()
        }
        
        # Re-raise as TradeBookError for consistent error handling
        if isinstance(e, TradeBookError):
            raise
        else:
            raise TradeBookError(f"Trade book fetch failed: {e}")

def _process_trade_data(trade: Dict[str, Any]) -> Dict[str, Any]:
    """
    Process and clean raw trade data from Angel One API.
    
    Args:
        trade: Raw trade data from API
        
    Returns:
        Dict: Cleaned and enhanced trade data
    """
    try:
        # Core trade fields
        processed = {
            'tradingsymbol': trade.get('tradingsymbol', ''),
            'exchange': trade.get('exchange', ''),
            'producttype': trade.get('producttype', ''),
            'orderid': trade.get('orderid', ''),
            'transactiontype': trade.get('transactiontype', ''),
            
            # Quantity and price fields
            'quantity': int(trade.get('quantity', 0)),
            'price': float(trade.get('price', 0)),
            'value': float(trade.get('value', 0)),
            
            # Timing fields
            'tradetime': trade.get('tradetime', ''),
            'tradedate': trade.get('tradedate', ''),
            'settdate': trade.get('settdate', ''),
            
            # Trade identification
            'trade_id': trade.get('tradeid', ''),
            'exchange_order_id': trade.get('exchorderid', ''),
            'symboltoken': trade.get('symboltoken', ''),
            
            # Additional fields
            'instrumenttype': trade.get('instrumenttype', ''),
            'strikeprice': float(trade.get('strikeprice', 0)),
            'optiontype': trade.get('optiontype', ''),
            'expirydate': trade.get('expirydate', ''),
            'lotsize': int(trade.get('lotsize', 1)),
            'multiplier': float(trade.get('multiplier', 1)),
            'precision': int(trade.get('precision', 2))
        }
        
        # Calculate derived fields
        processed['trade_value'] = processed['quantity'] * processed['price']
        processed['is_buy'] = processed['transactiontype'] == 'BUY'
        processed['is_sell'] = processed['transactiontype'] == 'SELL'
        processed['is_options'] = processed['instrumenttype'] in ['OPTSTK', 'OPTIDX']
        processed['is_futures'] = processed['instrumenttype'] in ['FUTSTK', 'FUTIDX']
        processed['is_equity'] = processed['instrumenttype'] == 'EQ'
        
        # Trade size categorization
        if processed['trade_value'] > 500000:  # > 5L
            processed['trade_size_category'] = 'LARGE'
        elif processed['trade_value'] > 100000:  # > 1L
            processed['trade_size_category'] = 'MEDIUM'
        else:
            processed['trade_size_category'] = 'SMALL'
        
        return processed
        
    except (ValueError, TypeError) as e:
        logger.warning(f"⚠️ Error processing trade data: {e}")
        return trade  # Return original if processing fails

def _find_most_traded_symbol(trades: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """Find the most traded symbol by total value."""
    if not trades:
        return None
    
    symbol_volumes = {}
    for trade in trades:
        symbol = trade.get('tradingsymbol')
        value = trade.get('trade_value', 0)
        
        if symbol not in symbol_volumes:
            symbol_volumes[symbol] = {'total_value': 0, 'trade_count': 0}
        
        symbol_volumes[symbol]['total_value'] += value
        symbol_volumes[symbol]['trade_count'] += 1
    
    if not symbol_volumes:
        return None
    
    most_traded_symbol = max(symbol_volumes.keys(), key=lambda x: symbol_volumes[x]['total_value'])
    
    return {
        'symbol': most_traded_symbol,
        'total_value': symbol_volumes[most_traded_symbol]['total_value'],
        'trade_count': symbol_volumes[most_traded_symbol]['trade_count']
    }

def _find_largest_trade(trades: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """Find the largest trade by value."""
    if not trades:
        return None
    
    largest = max(trades, key=lambda x: x.get('trade_value', 0))
    
    return {
        'symbol': largest.get('tradingsymbol'),
        'value': largest.get('trade_value', 0),
        'quantity': largest.get('quantity', 0),
        'price': largest.get('price', 0),
        'transaction_type': largest.get('transactiontype'),
        'trade_time': largest.get('tradetime')
    }

async def get_trades_by_symbol(symbol: str) -> List[Dict[str, Any]]:
    """
    Get all trades for a specific symbol.
    
    Args:
        symbol: Trading symbol (e.g., "RELIANCE-EQ")
        
    Returns:
        List: Trades for the symbol
    """
    try:
        trade_book = await get_trade_book()
        if not trade_book['success']:
            return []
        
        # Filter trades by symbol
        symbol_trades = [
            trade for trade in trade_book['trades']
            if trade.get('tradingsymbol') == symbol
        ]
        
        return symbol_trades
        
    except Exception as e:
        logger.error(f"❌ Symbol trades fetch failed for {symbol}: {e}")
        return []

async def get_trade_summary() -> Dict[str, Any]:
    """
    Get a comprehensive summary of trading activity.
    
    Returns:
        Dict: Trading activity summary
    """
    try:
        trade_book = await get_trade_book()
        if not trade_book['success']:
            return {'success': False, 'error': trade_book.get('error')}
        
        summary = trade_book['trade_summary'].copy()
        trades = trade_book['trades']
        
        # Add more detailed analysis
        if trades:
            # Performance analysis
            equity_trades = [t for t in trades if t.get('is_equity')]
            options_trades = [t for t in trades if t.get('is_options')]
            futures_trades = [t for t in trades if t.get('is_futures')]
            
            # Trade distribution
            large_trades = [t for t in trades if t.get('trade_size_category') == 'LARGE']
            medium_trades = [t for t in trades if t.get('trade_size_category') == 'MEDIUM']
            small_trades = [t for t in trades if t.get('trade_size_category') == 'SMALL']
            
            summary.update({
                'instrument_breakdown': {
                    'equity_trades': len(equity_trades),
                    'options_trades': len(options_trades),
                    'futures_trades': len(futures_trades)
                },
                'size_distribution': {
                    'large_trades': len(large_trades),
                    'medium_trades': len(medium_trades),
                    'small_trades': len(small_trades)
                },
                'trade_frequency': len(trades),  # trades per day (for today)
                'success': True
            })
        
        summary['timestamp'] = trade_book['timestamp']
        
        return summary
        
    except Exception as e:
        logger.error(f"❌ Trade summary failed: {e}")
        return {'success': False, 'error': str(e)}

async def get_recent_trades(limit: int = 10) -> List[Dict[str, Any]]:
    """
    Get the most recent trades.
    
    Args:
        limit: Number of recent trades to return (default: 10)
        
    Returns:
        List: Recent trades sorted by time
    """
    try:
        trade_book = await get_trade_book()
        if not trade_book['success']:
            return []
        
        trades = trade_book['trades']
        
        # Sort by trade time (most recent first)
        # Note: This assumes tradetime format allows string sorting
        sorted_trades = sorted(
            trades, 
            key=lambda x: x.get('tradetime', ''), 
            reverse=True
        )
        
        return sorted_trades[:limit]
        
    except Exception as e:
        logger.error(f"❌ Recent trades fetch failed: {e}")
        return []

def get_trade_book_sync() -> Dict[str, Any]:
    """
    Synchronous wrapper for get_trade_book.
    
    ⚠️ WARNING: Use async version when possible for better performance.
    This is only for compatibility with legacy code.
    """
    import asyncio
    try:
        return asyncio.run(get_trade_book())
    except Exception as e:
        logger.error(f"❌ Sync trade book fetch failed: {e}")
        return {
            'success': False,
            'trades': [],
            'total_trades': 0,
            'error': str(e)
        }

# Backward compatibility aliases (DEPRECATED - use new names)
fetch_trade_book = get_trade_book  # Alias for existing code
get_executed_trades = get_trade_book  # Alias for existing code

if __name__ == "__main__":
    # Test trade book fetching
    async def test_trade_book():
        print("🧪 Testing Angel One Trade Book")
        print("=" * 40)
        
        try:
            # Test basic trade book
            trade_book = await get_trade_book()
            if trade_book['success']:
                print(f"✅ Trade book fetched: {trade_book['total_trades']} trades")
                summary = trade_book['trade_summary']
                print(f"   Buy trades: {summary['buy_trades_count']}")
                print(f"   Sell trades: {summary['sell_trades_count']}")
                print(f"   Net value: ₹{summary['net_trade_value']:.2f}")
                print(f"   Unique symbols: {summary['unique_symbols']}")
                
                if summary['most_traded_symbol']:
                    most_traded = summary['most_traded_symbol']
                    print(f"   Most traded: {most_traded['symbol']} (₹{most_traded['total_value']:.2f})")
                    
            else:
                print(f"❌ Trade book fetch failed: {trade_book.get('error')}")
                
        except Exception as e:
            print(f"❌ Trade book test failed: {e}")
        
        try:
            # Test trade summary
            summary = await get_trade_summary()
            if summary['success']:
                print(f"✅ Trade summary:")
                if 'instrument_breakdown' in summary:
                    breakdown = summary['instrument_breakdown']
                    print(f"   Equity: {breakdown['equity_trades']}")
                    print(f"   Options: {breakdown['options_trades']}")
                    print(f"   Futures: {breakdown['futures_trades']}")
            else:
                print(f"❌ Trade summary failed: {summary.get('error')}")
                
        except Exception as e:
            print(f"❌ Trade summary test failed: {e}")
    
    # Run test (requires rate controller to be initialized)
    print("⚠️ Note: Requires rate controller initialization for testing")
    # asyncio.run(test_trade_book())
