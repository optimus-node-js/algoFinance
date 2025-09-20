"""
Angel One API: getLtpData - Live Last Traded Price
=================================================

CRITICAL METHOD: Most used API in the entire trading system
Rate Limit: 10 requests/second per API key
With 5 keys: 50 requests/second total capacity

This method REPLACES all existing LTP fetching across the system.
MOVED FROM: ai_master_orchestrator.py, market_data_service.py

Usage:
    from angel_one_api.methods.get_ltp_data import get_ltp_data
    
    # Single LTP
    ltp = await get_ltp_data("RELIANCE", "2885")
    
    # Bulk LTP (efficiently batched)
    ltps = await get_bulk_ltp_data([
        ("RELIANCE", "2885"),
        ("TCS", "11536"), 
        ("INFY", "1594")
    ])

Author: AI Trading System
Rate Limit: STRICTLY ENFORCED 10 req/sec per key
"""

import asyncio
import time
from typing import Dict, List, Tuple, Optional, Any

# Import our rate limiting system
from ..rate_limiter.rate_controller import get_rate_controller, rate_limited, APIPriority
from ..rate_limiter.api_limits import API_LIMITS

# Import new Angel One logger
from ..logger import get_api_logger

logger = get_api_logger("get_ltp_data")

class LTPDataError(Exception):
    """Raised when LTP data cannot be fetched."""
    pass

@rate_limited("get_ltp_data", APIPriority.CRITICAL)
async def get_ltp_data(
    symbol: str, 
    symbol_token: str,
    exchange: str = "NSE",
    _rate_limit_permit: Optional[Dict] = None
) -> Optional[float]:
    """
    Get Live Last Traded Price for a single instrument.
    
    Args:
        symbol: Trading symbol (e.g., "RELIANCE")
        symbol_token: Angel One symbol token (e.g., "2885")
        exchange: Exchange name (default: "NSE")
        _rate_limit_permit: Automatically provided by rate limiter
        
    Returns:
        float: Live LTP price or None if failed
        
    Raises:
        LTPDataError: If API call fails
        RateLimitExceeded: If rate limit would be exceeded
        
    Rate Limit: 10 requests/second per API key
    """
    try:
        # Get Angel One client (using the API key from rate limit permit)
        from core.connections import ConnectionManager
        
        if not _rate_limit_permit:
            raise LTPDataError("No rate limit permit - internal error")
        
        # Get the specific client for this API key
        angel_client = ConnectionManager.get_smartapi_client()
        if not angel_client:
            raise LTPDataError("Angel One API client not available")
        
        # Clean symbol (remove -EQ suffix if present)
        clean_symbol = symbol.replace('-EQ', '')
        
        # Validate inputs
        if not symbol_token or symbol_token in ["1234", "0", ""]:
            raise LTPDataError(f"Invalid symbol token for {symbol}: {symbol_token}")
        
        # Make API call with strict rate limiting already enforced
        logger.debug(f"🔍 LTP Request: {clean_symbol} with token {symbol_token} using {_rate_limit_permit['api_key_id']}")
        
        response = angel_client.ltpData(
            exchange=exchange,
            tradingsymbol=clean_symbol,
            symboltoken=symbol_token
        )
        
        # Parse response
        if not response:
            raise LTPDataError(f"Empty response for {symbol}")
        
        if not response.get('status'):
            error_msg = response.get('message', 'Unknown error')
            raise LTPDataError(f"API error for {symbol}: {error_msg}")
        
        data = response.get('data')
        if not data:
            raise LTPDataError(f"No data in response for {symbol}")
        
        # Handle different response formats
        if isinstance(data, dict):
            ltp = float(data.get('ltp', 0))
        elif isinstance(data, list) and len(data) > 0:
            # If data is a list, get the first item
            first_item = data[0]
            if isinstance(first_item, dict):
                ltp = float(first_item.get('ltp', 0))
            else:
                ltp = float(first_item) if first_item else 0
        elif isinstance(data, (int, float)):
            # If data is directly a number
            ltp = float(data)
        else:
            raise LTPDataError(f"Unexpected data format for {symbol}: {type(data)}")
        
        # Validate LTP value
        if ltp <= 0:
            raise LTPDataError(f"Invalid LTP value for {symbol}: {ltp}")
        
        # Sanity check for suspicious prices
        if ltp < 0.01 or ltp > 1000000:
            logger.warning(f"⚠️ Suspicious LTP for {symbol}: ₹{ltp:.2f}")
            # Don't raise error, but log for investigation
        
        # Success - log occasionally to avoid spam
        if hash(symbol) % 20 == 0:  # Log 1 in 20 successful calls
            logger.debug(f"📈 LTP: {symbol} = ₹{ltp:.2f}")
        
        return ltp
        
    except Exception as e:
        # Log error with context
        logger.error(f"❌ LTP fetch failed for {symbol} (token: {symbol_token}): {e}")
        
        # Re-raise as LTPDataError for consistent error handling
        if isinstance(e, LTPDataError):
            raise
        else:
            raise LTPDataError(f"Failed to fetch LTP for {symbol}: {e}")

async def get_bulk_ltp_data(
    instruments: List[Tuple[str, str]], 
    exchange: str = "NSE",
    max_concurrent: int = 5,
    batch_delay: float = 0.1
) -> Dict[str, Optional[float]]:
    """
    Get LTP data for multiple instruments efficiently.
    
    Args:
        instruments: List of (symbol, token) tuples
        exchange: Exchange name (default: "NSE")
        max_concurrent: Maximum concurrent requests (default: 5)
        batch_delay: Delay between batches in seconds (default: 0.1)
        
    Returns:
        Dict[str, Optional[float]]: Symbol -> LTP mapping
        
    Rate Limiting:
        - Automatically batches requests to stay within 10 req/sec limit
        - Uses multiple API keys for 50 req/sec total capacity
        - Adds delays between batches to prevent rate limiting
    """
    results = {}
    
    if not instruments:
        return results
    
    logger.info(f"📊 Fetching LTP for {len(instruments)} instruments (max {max_concurrent} concurrent)")
    
    # Process in batches to respect rate limits
    batch_size = min(max_concurrent, 10)  # Don't exceed 10 req/sec per key
    
    for i in range(0, len(instruments), batch_size):
        batch = instruments[i:i + batch_size]
        batch_start_time = time.time()
        
        # Create tasks for this batch
        tasks = []
        for symbol, token in batch:
            task = asyncio.create_task(
                get_ltp_data(symbol, token, exchange),
                name=f"ltp_{symbol}"
            )
            tasks.append((symbol, task))
        
        # Wait for batch completion
        batch_results = {}
        for symbol, task in tasks:
            try:
                ltp = await task
                batch_results[symbol] = ltp
            except Exception as e:
                logger.warning(f"⚠️ Failed to get LTP for {symbol}: {e}")
                batch_results[symbol] = None
        
        # Add batch results
        results.update(batch_results)
        
        # Add delay between batches if needed
        batch_time = time.time() - batch_start_time
        if batch_time < batch_delay and i + batch_size < len(instruments):
            sleep_time = batch_delay - batch_time
            logger.debug(f"⏳ Batch delay: {sleep_time:.2f}s")
            await asyncio.sleep(sleep_time)
    
    successful_count = sum(1 for ltp in results.values() if ltp is not None)
    logger.info(f"✅ LTP fetch complete: {successful_count}/{len(instruments)} successful")
    
    return results

def get_ltp_data_sync(symbol: str, symbol_token: str, exchange: str = "NSE") -> Optional[float]:
    """
    Synchronous wrapper for get_ltp_data.
    
    ⚠️ WARNING: Use async version when possible for better performance.
    This is only for compatibility with legacy code.
    """
    try:
        return asyncio.run(get_ltp_data(symbol, symbol_token, exchange))
    except Exception as e:
        logger.error(f"❌ Sync LTP fetch failed for {symbol}: {e}")
        return None

# Backward compatibility aliases (DEPRECATED - use new names)
get_live_ltp = get_ltp_data  # Alias for existing code
fetch_ltp = get_ltp_data     # Alias for existing code

if __name__ == "__main__":
    # Test the LTP fetcher
    async def test_ltp_fetcher():
        print("🧪 Testing Angel One LTP Fetcher")
        print("=" * 40)
        
        # Test single LTP
        try:
            ltp = await get_ltp_data("RELIANCE", "2885")
            print(f"✅ RELIANCE LTP: ₹{ltp}")
        except Exception as e:
            print(f"❌ RELIANCE LTP failed: {e}")
        
        # Test bulk LTP
        test_instruments = [
            ("RELIANCE", "2885"),
            ("TCS", "11536"),
            ("INFY", "1594"),
            ("HDFCBANK", "1333"),
            ("ICICIBANK", "4963")
        ]
        
        try:
            bulk_ltps = await get_bulk_ltp_data(test_instruments)
            print(f"\n📊 Bulk LTP Results:")
            for symbol, ltp in bulk_ltps.items():
                status = f"₹{ltp:.2f}" if ltp else "FAILED"
                print(f"  {symbol}: {status}")
        except Exception as e:
            print(f"❌ Bulk LTP failed: {e}")
    
    # Run test (requires rate controller to be initialized)
    print("⚠️ Note: Requires rate controller initialization for testing")
    # asyncio.run(test_ltp_fetcher())
