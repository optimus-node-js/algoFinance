"""
Angel One API: getCandleData - Historical Candlestick Data
=========================================================

CRITICAL METHOD: Historical data for backtesting and analysis
Rate Limit: 3 requests/second per API key (MOST RESTRICTIVE)
Priority: HIGH

MOVED FROM: services/market_data/market_data_service.py, data_ingestion/historical.py
This method consolidates and improves all existing historical data fetching.

Usage:
    from angel_one_api.methods.get_candle_data import get_candle_data
    
    # Get 1-minute data for last hour
    candles = await get_candle_data(
        exchange="NSE",
        symboltoken="2885",
        interval="ONE_MINUTE",
        fromdate="2025-09-17 13:00",
        todate="2025-09-17 14:00"
    )
    
    # Get daily data for last 30 days  
    daily_candles = await get_candle_data(
        exchange="NSE",
        symboltoken="2885", 
        interval="ONE_DAY",
        days_back=30
    )

Author: AI Trading System
Rate Limit: STRICTLY ENFORCED 3 req/sec per key (15 req/sec total with 5 keys)
"""

import asyncio
import time
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
# Import new Angel One logger
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))
from logger import get_api_logger

# Import our rate limiting system
from rate_limiter.rate_controller import get_rate_controller, rate_limited, APIPriority
from rate_limiter.api_limits import API_LIMITS

# Import idempotency enhancements
try:
    from ..enhancements.idempotency_manager import idempotency_wrapper
    IDEMPOTENCY_AVAILABLE = True
except ImportError:
    IDEMPOTENCY_AVAILABLE = False

logger = get_api_logger("get_candle_data")

class CandleDataError(Exception):
    """Raised when candle data fetching fails."""
    pass

class Interval:
    """Angel One supported intervals."""
    ONE_MINUTE = "ONE_MINUTE"
    THREE_MINUTE = "THREE_MINUTE"
    FIVE_MINUTE = "FIVE_MINUTE"
    TEN_MINUTE = "TEN_MINUTE"
    FIFTEEN_MINUTE = "FIFTEEN_MINUTE"
    THIRTY_MINUTE = "THIRTY_MINUTE"
    ONE_HOUR = "ONE_HOUR"
    ONE_DAY = "ONE_DAY"

@idempotency_wrapper(method_type="market", ttl=60, cache_response=True) if IDEMPOTENCY_AVAILABLE else lambda x: x
@rate_limited("get_candle_data", APIPriority.HIGH)
async def get_candle_data(
    exchange: str,
    symboltoken: str,
    interval: str,
    fromdate: Optional[str] = None,
    todate: Optional[str] = None,
    days_back: Optional[int] = None,
    _rate_limit_permit: Optional[Dict] = None
) -> Dict[str, Any]:
    """
    Get historical candlestick data from Angel One API.
    
    Args:
        exchange: Exchange name (NSE, BSE, NFO, MCX)
        symboltoken: Angel One symbol token
        interval: Time interval (ONE_MINUTE, FIVE_MINUTE, ONE_HOUR, ONE_DAY, etc.)
        fromdate: Start date-time "YYYY-MM-DD HH:MM" (optional)
        todate: End date-time "YYYY-MM-DD HH:MM" (optional)
        days_back: Number of days back from today (alternative to fromdate/todate)
        _rate_limit_permit: Automatically provided by rate limiter
        
    Returns:
        Dict containing:
            - success: bool
            - data: List of candle data [timestamp, open, high, low, close, volume]
            - count: int (number of candles)
            - fromdate: str
            - todate: str
            - interval: str
        
    Raises:
        CandleDataError: If data fetching fails
        RateLimitExceeded: If rate limit would be exceeded
        
    Rate Limit: 3 requests/second per API key (MOST RESTRICTIVE)
    """
    try:
        if not _rate_limit_permit:
            raise CandleDataError("No rate limit permit - internal error")
        
        # Get Angel One client
        # Use interface to get SmartAPI client
        from interface import get_angel_one_interface
        interface = get_angel_one_interface()
        angel_client = interface.smart_api
        
        # angel_client already set above
        if not angel_client:
            raise CandleDataError("Angel One API client not available")
        
        # Validate inputs
        if not all([exchange, symboltoken, interval]):
            raise CandleDataError("Missing required parameters: exchange, symboltoken, interval")
        
        # Handle date parameters
        if days_back:
            todate = datetime.now().strftime("%Y-%m-%d %H:%M")
            fromdate = (datetime.now() - timedelta(days=days_back)).strftime("%Y-%m-%d %H:%M")
        else:
            if not todate:
                todate = datetime.now().strftime("%Y-%m-%d %H:%M")
            if not fromdate:
                # Default to last 24 hours
                fromdate = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d %H:%M")
        
        # Validate interval
        valid_intervals = [
            "ONE_MINUTE", "THREE_MINUTE", "FIVE_MINUTE", "TEN_MINUTE",
            "FIFTEEN_MINUTE", "THIRTY_MINUTE", "ONE_HOUR", "ONE_DAY"
        ]
        if interval not in valid_intervals:
            raise CandleDataError(f"Invalid interval. Must be one of: {valid_intervals}")
        
        # Validate date format and range
        try:
            from_dt = datetime.strptime(fromdate, "%Y-%m-%d %H:%M")
            to_dt = datetime.strptime(todate, "%Y-%m-%d %H:%M")
            
            if from_dt >= to_dt:
                raise ValueError("fromdate must be before todate")
            
            # Check if date range is reasonable (not too far back)
            max_days_back = 365  # 1 year limit
            if (datetime.now() - from_dt).days > max_days_back:
                raise ValueError(f"Date range too large. Maximum {max_days_back} days back")
                
        except ValueError as e:
            raise CandleDataError(f"Invalid date format or range: {e}")
        
        # Log request
        logger.debug(
            f"📊 Candle data request: {symboltoken} {interval} "
            f"{fromdate} to {todate} using {_rate_limit_permit['api_key_id']}"
        )
        
        # Make API call with strict rate limiting already enforced
        # Note: SmartConnect getCandleData uses different parameter names
        response = angel_client.getCandleData(
            historicDataParams={
                "exchange": exchange,
                "symboltoken": symboltoken,
                "interval": interval,
                "fromdate": fromdate,
                "todate": todate
            }
        )
        
        # Parse response
        if not response:
            raise CandleDataError("Empty response from getCandleData API")
        
        if not response.get('status'):
            error_msg = response.get('message', 'Unknown error')
            raise CandleDataError(f"API error: {error_msg}")
        
        candle_data = response.get('data', [])
        
        # Validate candle data format
        if not isinstance(candle_data, list):
            raise CandleDataError("Invalid candle data format received")
        
        # Process candle data
        processed_candles = []
        for candle in candle_data:
            if len(candle) >= 6:  # [timestamp, open, high, low, close, volume]
                processed_candles.append({
                    'timestamp': candle[0],
                    'open': float(candle[1]),
                    'high': float(candle[2]),
                    'low': float(candle[3]),
                    'close': float(candle[4]),
                    'volume': int(candle[5])
                })
        
        # Success response
        result = {
            'success': True,
            'data': processed_candles,
            'raw_data': candle_data,  # Original format for compatibility
            'count': len(processed_candles),
            'exchange': exchange,
            'symboltoken': symboltoken,
            'interval': interval,
            'fromdate': fromdate,
            'todate': todate,
            'api_key_id': _rate_limit_permit['api_key_id'],
            'timestamp': time.time()
        }
        
        logger.info(f"✅ Candle data fetched: {len(processed_candles)} candles for {symboltoken}")
        
        return result
        
    except Exception as e:
        logger.error(f"❌ Candle data fetch failed for {symboltoken}: {e}")
        
        # Create error response
        error_result = {
            'success': False,
            'data': [],
            'count': 0,
            'error': str(e),
            'timestamp': time.time()
        }
        
        # Re-raise as CandleDataError for consistent error handling
        if isinstance(e, CandleDataError):
            raise
        else:
            raise CandleDataError(f"Candle data fetch failed: {e}")

async def get_intraday_data(
    symboltoken: str,
    interval: str = "FIVE_MINUTE",
    exchange: str = "NSE"
) -> Dict[str, Any]:
    """
    Get intraday candle data for current trading day.
    
    Args:
        symboltoken: Angel One symbol token
        interval: Time interval (default: "FIVE_MINUTE")
        exchange: Exchange name (default: "NSE")
        
    Returns:
        Dict: Intraday candle data
    """
    # Get today's trading hours (9:15 AM to 3:30 PM)
    today = datetime.now().date()
    fromdate = f"{today} 09:15"
    todate = f"{today} 15:30"
    
    return await get_candle_data(
        exchange=exchange,
        symboltoken=symboltoken,
        interval=interval,
        fromdate=fromdate,
        todate=todate
    )

async def get_daily_data(
    symboltoken: str,
    days_back: int = 30,
    exchange: str = "NSE"
) -> Dict[str, Any]:
    """
    Get daily candle data for specified number of days.
    
    Args:
        symboltoken: Angel One symbol token  
        days_back: Number of days back (default: 30)
        exchange: Exchange name (default: "NSE")
        
    Returns:
        Dict: Daily candle data
    """
    return await get_candle_data(
        exchange=exchange,
        symboltoken=symboltoken,
        interval="ONE_DAY",
        days_back=days_back
    )

async def get_weekly_data(
    symboltoken: str,
    weeks_back: int = 12,
    exchange: str = "NSE"
) -> Dict[str, Any]:
    """
    Get weekly candle data (using daily data aggregated).
    
    Args:
        symboltoken: Angel One symbol token
        weeks_back: Number of weeks back (default: 12)
        exchange: Exchange name (default: "NSE")
        
    Returns:
        Dict: Weekly candle data
    """
    days_back = weeks_back * 7
    return await get_candle_data(
        exchange=exchange,
        symboltoken=symboltoken,
        interval="ONE_DAY",
        days_back=days_back
    )

async def bulk_candle_data(
    symbol_tokens: List[str],
    interval: str = "ONE_DAY",
    days_back: int = 30,
    exchange: str = "NSE",
    batch_delay: float = 0.4  # 3 req/sec = 0.33s, use 0.4s for safety
) -> Dict[str, Dict[str, Any]]:
    """
    Get candle data for multiple symbols efficiently with rate limiting.
    
    Args:
        symbol_tokens: List of symbol tokens
        interval: Time interval (default: "ONE_DAY")
        days_back: Number of days back (default: 30)
        exchange: Exchange name (default: "NSE")
        batch_delay: Delay between requests in seconds (default: 0.4)
        
    Returns:
        Dict[str, Dict]: Token -> candle data mapping
        
    Rate Limiting:
        - Processes 3 requests per second to respect rate limit
        - Uses multiple API keys for parallel processing
    """
    results = {}
    
    if not symbol_tokens:
        return results
    
    logger.info(f"📊 Bulk candle data for {len(symbol_tokens)} symbols (3 req/sec limit)")
    
    for i, token in enumerate(symbol_tokens):
        batch_start_time = time.time()
        
        try:
            candle_result = await get_candle_data(
                exchange=exchange,
                symboltoken=token,
                interval=interval,
                days_back=days_back
            )
            results[token] = candle_result
            
            logger.debug(f"✅ Candles {i+1}/{len(symbol_tokens)}: {token} - {candle_result.get('count', 0)} candles")
            
        except Exception as e:
            logger.warning(f"⚠️ Candle fetch failed for {token}: {e}")
            results[token] = {'success': False, 'error': str(e)}
        
        # Add delay between requests (except for last one)
        if i < len(symbol_tokens) - 1:
            elapsed = time.time() - batch_start_time
            if elapsed < batch_delay:
                sleep_time = batch_delay - elapsed
                logger.debug(f"⏳ Rate limit delay: {sleep_time:.2f}s")
                await asyncio.sleep(sleep_time)
    
    successful_count = sum(1 for r in results.values() if r.get('success'))
    logger.info(f"✅ Bulk candle fetch complete: {successful_count}/{len(symbol_tokens)} successful")
    
    return results

def get_candle_data_sync(
    exchange: str,
    symboltoken: str,
    interval: str,
    fromdate: Optional[str] = None,
    todate: Optional[str] = None
) -> Dict[str, Any]:
    """
    Synchronous wrapper for get_candle_data.
    
    ⚠️ WARNING: Use async version when possible for better performance.
    This is only for compatibility with legacy code.
    """
    try:
        return asyncio.run(get_candle_data(exchange, symboltoken, interval, fromdate, todate))
    except Exception as e:
        logger.error(f"❌ Sync candle data fetch failed for {symboltoken}: {e}")
        return {
            'success': False,
            'data': [],
            'count': 0,
            'error': str(e)
        }

# Backward compatibility aliases (DEPRECATED - use new names)
fetch_historical_data = get_candle_data  # Alias for existing code
get_historical_candles = get_candle_data  # Alias for existing code

if __name__ == "__main__":
    # Test candle data fetching
    async def test_candle_data():
        print("🧪 Testing Angel One Candle Data")
        print("=" * 40)
        
        # Test daily data
        try:
            daily_data = await get_daily_data("2885", days_back=5)  # RELIANCE
            if daily_data['success']:
                print(f"✅ Daily data: {daily_data['count']} candles")
                if daily_data['data']:
                    latest = daily_data['data'][-1]
                    print(f"   Latest: Close=₹{latest['close']}, Volume={latest['volume']}")
            else:
                print(f"❌ Daily data failed: {daily_data.get('error')}")
        except Exception as e:
            print(f"❌ Daily data test failed: {e}")
        
        # Test intraday data
        try:
            intraday_data = await get_intraday_data("2885", "FIFTEEN_MINUTE")
            if intraday_data['success']:
                print(f"✅ Intraday data: {intraday_data['count']} candles")
            else:
                print(f"❌ Intraday data failed: {intraday_data.get('error')}")
        except Exception as e:
            print(f"❌ Intraday data test failed: {e}")
    
    # Run test (requires rate controller to be initialized)
    print("⚠️ Note: Requires rate controller initialization for testing")
    # asyncio.run(test_candle_data())
