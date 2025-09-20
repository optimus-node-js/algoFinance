"""
Angel One API: searchScrip - Instrument Search & Validation
===========================================================

CRITICAL METHOD: Stock validation and token fetching
Rate Limit: 1 request/second per API key
Priority: HIGH (used for all stock validation)

MOVED FROM: stock_discovery_service.py, ai_master_orchestrator.py, api_gateway/utils.py
This method consolidates and improves all existing searchScrip implementations.

Usage:
    from angel_one_api.methods.search_scrip import search_scrip
    
    # Single search
    results = await search_scrip("RELIANCE", "NSE")
    
    # Find best equity match
    best_match = await find_best_equity_match("RELIANCE", "NSE")
    
    # Bulk search (efficiently batched) 
    bulk_results = await bulk_search_scrip(["RELIANCE", "TCS", "INFY"])

Author: AI Trading System
Rate Limit: STRICTLY ENFORCED 1 req/sec per key
"""

import asyncio
import time
from typing import Dict, List, Optional, Any, Tuple
# Import new Angel One logger
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from logger import get_api_logger

# Import our rate limiting system
from rate_limiter.rate_controller import get_rate_controller, rate_limited, APIPriority
from rate_limiter.api_limits import API_LIMITS

logger = get_api_logger("search_scrip")

class SearchScripError(Exception):
    """Raised when instrument search fails."""
    pass

@rate_limited("search_scrip", APIPriority.HIGH)
async def search_scrip(
    search_term: str,
    exchange: str = "NSE",
    _rate_limit_permit: Optional[Dict] = None
) -> List[Dict[str, Any]]:
    """
    Search for instruments using Angel One searchScrip API.
    
    Args:
        search_term: Symbol to search for (e.g., "RELIANCE")
        exchange: Exchange name (default: "NSE")
        _rate_limit_permit: Automatically provided by rate limiter
        
    Returns:
        List[Dict]: List of matching instruments with full details
        
    Raises:
        SearchScripError: If search fails
        RateLimitExceeded: If rate limit would be exceeded
        
    Rate Limit: 1 request/second per API key
    """
    try:
        if not _rate_limit_permit:
            raise SearchScripError("No rate limit permit - internal error")
        
        # Get Angel One client
        # Use interface to get SmartAPI client
        from interface import get_angel_one_interface
        interface = get_angel_one_interface()
        angel_client = interface.smart_api
        
        # angel_client already set above
        if not angel_client:
            raise SearchScripError("Angel One API client not available")
        
        # Validate inputs
        if not search_term or not search_term.strip():
            raise SearchScripError("Search term cannot be empty")
        
        search_term_clean = search_term.strip().upper()
        exchange_clean = exchange.strip().upper()
        
        # Make API call with strict rate limiting already enforced
        logger.debug(f"🔍 Search request: '{search_term_clean}' on {exchange_clean} using {_rate_limit_permit['api_key_id']}")
        
        response = angel_client.searchScrip(
            exchange=exchange_clean,
            searchscrip=search_term_clean
        )
        
        # Parse response
        if not response:
            raise SearchScripError(f"Empty response for search term: {search_term}")
        
        if not response.get('status'):
            error_msg = response.get('message', 'Unknown error')
            # Handle "No matching symbols" as empty result, not error
            if "no matching" in error_msg.lower():
                logger.debug(f"📝 No matching symbols found for '{search_term_clean}'")
                return []
            else:
                raise SearchScripError(f"API error for {search_term}: {error_msg}")
        
        data = response.get('data', [])
        
        # Validate response data
        if not isinstance(data, list):
            raise SearchScripError(f"Invalid response format for {search_term}")
        
        # Log result summary
        if data:
            logger.debug(f"✅ Search '{search_term_clean}': {len(data)} instruments found")
        else:
            logger.debug(f"📝 Search '{search_term_clean}': No instruments found")
        
        return data
        
    except Exception as e:
        logger.error(f"❌ Search failed for '{search_term}' on {exchange}: {e}")
        
        # Re-raise as SearchScripError for consistent error handling
        if isinstance(e, SearchScripError):
            raise
        else:
            raise SearchScripError(f"Search failed for {search_term}: {e}")

async def find_best_equity_match(
    symbol: str,
    exchange: str = "NSE"
) -> Optional[Dict[str, Any]]:
    """
    Find the best equity instrument match for a symbol.
    
    Args:
        symbol: Base symbol (e.g., "RELIANCE")
        exchange: Exchange name (default: "NSE")
        
    Returns:
        Dict: Best matching equity instrument or None if not found
        
    Search Priority:
        1. Exact equity match (e.g., "RELIANCE-EQ")
        2. Partial equity match containing symbol
        3. None if no equity instrument found
    """
    try:
        # Search for instruments
        results = await search_scrip(symbol, exchange)
        
        if not results:
            return None
        
        # Clean symbol for matching
        symbol_clean = symbol.replace('-EQ', '').upper()
        equity_symbol = f"{symbol_clean}-EQ"
        
        # Priority 1: Exact equity match
        for instrument in results:
            trading_symbol = instrument.get('tradingsymbol', '').upper()
            if trading_symbol == equity_symbol:
                logger.debug(f"✅ Exact equity match found: {trading_symbol}")
                return instrument
        
        # Priority 2: Partial equity match
        for instrument in results:
            trading_symbol = instrument.get('tradingsymbol', '').upper()
            if symbol_clean in trading_symbol and '-EQ' in trading_symbol:
                logger.debug(f"✅ Partial equity match found: {trading_symbol}")
                return instrument
        
        # No equity match found
        logger.debug(f"📝 No equity instrument found for '{symbol}'")
        available_symbols = [r.get('tradingsymbol') for r in results]
        logger.debug(f"   Available instruments: {available_symbols}")
        
        return None
        
    except Exception as e:
        logger.error(f"❌ Best equity match search failed for {symbol}: {e}")
        return None

async def get_instrument_token(
    symbol: str,
    exchange: str = "NSE"
) -> Optional[str]:
    """
    Get instrument token for a symbol (equity preferred).
    
    Args:
        symbol: Symbol to get token for
        exchange: Exchange name (default: "NSE")
        
    Returns:
        str: Symbol token or None if not found
    """
    try:
        best_match = await find_best_equity_match(symbol, exchange)
        
        if best_match:
            token = best_match.get('symboltoken')
            if token:
                logger.debug(f"📋 Token for {symbol}: {token}")
                return token
        
        logger.warning(f"⚠️ No token found for {symbol}")
        return None
        
    except Exception as e:
        logger.error(f"❌ Token fetch failed for {symbol}: {e}")
        return None

async def bulk_search_scrip(
    symbols: List[str],
    exchange: str = "NSE",
    batch_delay: float = 1.1  # Slightly above 1 sec to respect 1 req/sec limit
) -> Dict[str, List[Dict[str, Any]]]:
    """
    Search for multiple instruments efficiently with rate limiting.
    
    Args:
        symbols: List of symbols to search for
        exchange: Exchange name (default: "NSE")  
        batch_delay: Delay between searches in seconds (default: 1.1)
        
    Returns:
        Dict[str, List[Dict]]: Symbol -> search results mapping
        
    Rate Limiting:
        - Processes one search per second to respect 1 req/sec limit
        - Uses multiple API keys for parallel processing
    """
    results = {}
    
    if not symbols:
        return results
    
    logger.info(f"📊 Bulk search for {len(symbols)} symbols (1 req/sec limit)")
    
    for i, symbol in enumerate(symbols):
        batch_start_time = time.time()
        
        try:
            search_results = await search_scrip(symbol, exchange)
            results[symbol] = search_results
            
            logger.debug(f"✅ Search {i+1}/{len(symbols)}: {symbol} - {len(search_results)} results")
            
        except Exception as e:
            logger.warning(f"⚠️ Search failed for {symbol}: {e}")
            results[symbol] = []
        
        # Add delay between searches (except for last one)
        if i < len(symbols) - 1:
            elapsed = time.time() - batch_start_time
            if elapsed < batch_delay:
                sleep_time = batch_delay - elapsed
                logger.debug(f"⏳ Rate limit delay: {sleep_time:.1f}s")
                await asyncio.sleep(sleep_time)
    
    successful_count = sum(1 for r in results.values() if r)
    logger.info(f"✅ Bulk search complete: {successful_count}/{len(symbols)} successful")
    
    return results

def search_scrip_sync(search_term: str, exchange: str = "NSE") -> List[Dict[str, Any]]:
    """
    Synchronous wrapper for search_scrip.
    
    ⚠️ WARNING: Use async version when possible for better performance.
    This is only for compatibility with legacy code.
    """
    try:
        return asyncio.run(search_scrip(search_term, exchange))
    except Exception as e:
        logger.error(f"❌ Sync search failed for {search_term}: {e}")
        return []

def find_best_equity_match_sync(symbol: str, exchange: str = "NSE") -> Optional[Dict[str, Any]]:
    """
    Synchronous wrapper for find_best_equity_match.
    
    ⚠️ WARNING: Use async version when possible.
    """
    try:
        return asyncio.run(find_best_equity_match(symbol, exchange))
    except Exception as e:
        logger.error(f"❌ Sync equity match failed for {symbol}: {e}")
        return None

# Backward compatibility aliases (DEPRECATED - use new names)
search_instruments = search_scrip  # Alias for existing code
find_instrument = find_best_equity_match  # Alias for existing code

if __name__ == "__main__":
    # Test the search functionality
    async def test_search_scrip():
        print("🧪 Testing Angel One Search Scrip")
        print("=" * 40)
        
        # Test single search
        try:
            results = await search_scrip("RELIANCE")
            print(f"✅ RELIANCE search: {len(results)} results")
            if results:
                print(f"   First result: {results[0].get('tradingsymbol')}")
        except Exception as e:
            print(f"❌ RELIANCE search failed: {e}")
        
        # Test best equity match
        try:
            best_match = await find_best_equity_match("TCS")
            if best_match:
                print(f"✅ TCS best match: {best_match.get('tradingsymbol')} (token: {best_match.get('symboltoken')})")
            else:
                print(f"❌ TCS: No equity match found")
        except Exception as e:
            print(f"❌ TCS equity match failed: {e}")
        
        # Test bulk search
        test_symbols = ["INFY", "HDFCBANK", "ICICIBANK"]
        try:
            bulk_results = await bulk_search_scrip(test_symbols)
            print(f"\n📊 Bulk Search Results:")
            for symbol, results in bulk_results.items():
                print(f"  {symbol}: {len(results)} results")
        except Exception as e:
            print(f"❌ Bulk search failed: {e}")
    
    # Run test (requires rate controller to be initialized)
    print("⚠️ Note: Requires rate controller initialization for testing")
    # asyncio.run(test_search_scrip())
