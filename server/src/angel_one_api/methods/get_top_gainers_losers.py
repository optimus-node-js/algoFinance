"""
Angel One API: getTopGainersLosers - Top Gainers and Losers
==========================================================

METHOD: Get top gaining and losing stocks for market analysis
Rate Limit: 5 requests/second per API key
Priority: HIGH (market analysis and trend identification)

Usage:
    from angel_one_api.methods.get_top_gainers_losers import get_top_gainers_losers
    
    # Get top gainers
    gainers = await get_top_gainers_losers("NSE", "topgainers", 20)
    
    # Get top losers
    losers = await get_top_gainers_losers("NSE", "toplosers", 20)
    
    # Get both gainers and losers
    market_movers = await get_market_movers("NSE", 20)

Author: AI Trading System
Rate Limit: STRICTLY ENFORCED 5 req/sec per key
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

logger = get_api_logger("get_top_gainers_losers")

class TopGainersLosersError(Exception):
    """Raised when top gainers/losers fetching fails."""
    pass

@rate_limited("get_top_gainers_losers", APIPriority.HIGH)
async def get_top_gainers_losers(
    exchange: str,
    datatype: str,
    count: int = 25,
    _rate_limit_permit: Optional[Dict] = None
) -> Dict[str, Any]:
    """
    Get top gainers or losers from Angel One API.
    
    Args:
        exchange: Exchange name (NSE, BSE)
        datatype: "topgainers" or "toplosers"
        count: Number of stocks to return (default: 25, max: 50)
        _rate_limit_permit: Automatically provided by rate limiter
        
    Returns:
        Dict containing:
            - success: bool
            - data: List of top gainers/losers
            - exchange: str
            - datatype: str
            - count: int
            - timestamp: str
        
    Raises:
        TopGainersLosersError: If fetching fails
        RateLimitExceeded: If rate limit would be exceeded
        
    Rate Limit: 5 requests/second per API key
    """
    try:
        if not _rate_limit_permit:
            raise TopGainersLosersError("No rate limit permit - internal error")
        
        # Get Angel One client
        # Use interface to get SmartAPI client
        from interface import get_angel_one_interface
        interface = get_angel_one_interface()
        angel_client = interface.smart_api
        
        # angel_client already set above
        if not angel_client:
            raise TopGainersLosersError("Angel One API client not available")
        
        # Validate parameters
        if exchange not in ['NSE', 'BSE']:
            raise TopGainersLosersError("Exchange must be 'NSE' or 'BSE'")
        
        if datatype not in ['topgainers', 'toplosers']:
            raise TopGainersLosersError("Datatype must be 'topgainers' or 'toplosers'")
        
        if not (1 <= count <= 50):
            raise TopGainersLosersError("Count must be between 1 and 50")
        
        # Log request
        logger.debug(f"📈 Top {datatype} request: {exchange} (count: {count}) using {_rate_limit_permit['api_key_id']}")
        
        # Make API call with strict rate limiting already enforced
        # Note: SmartConnect doesn't have getTopGainersLosers method
        # This method may not be available in the current SmartConnect SDK
        # Let's use a workaround or check if it's available
        if hasattr(angel_client, 'getTopGainersLosers'):
            response = angel_client.getTopGainersLosers(
                exchange=exchange,
                datatype=datatype,
                count=count
            )
        else:
            # Method not available in SmartConnect SDK
            raise TopGainersLosersError(f"getTopGainersLosers method not available in SmartConnect SDK. Please check Angel One SmartAPI documentation for alternative endpoints.")
        
        # Parse response
        if not response:
            raise TopGainersLosersError("Empty response from getTopGainersLosers API")
        
        if not response.get('status'):
            error_msg = response.get('message', 'Unknown error')
            raise TopGainersLosersError(f"Top gainers/losers API error: {error_msg}")
        
        data = response.get('data', [])
        
        # Process the data
        processed_data = _process_top_gainers_losers_data(data, datatype)
        
        # Success response
        result = {
            'success': True,
            'data': processed_data,
            'exchange': exchange,
            'datatype': datatype,
            'count': len(processed_data),
            'requested_count': count,
            'raw_data': data,
            'timestamp': datetime.now(UTC).isoformat(),
            'api_key_id': _rate_limit_permit['api_key_id'],
            'response_time': time.time()
        }
        
        logger.info(f"✅ Top {datatype} fetched: {len(processed_data)} stocks from {exchange}")
        
        return result
        
    except Exception as e:
        logger.error(f"❌ Top {datatype} fetch failed for {exchange}: {e}")
        
        # Create error response
        error_result = {
            'success': False,
            'data': [],
            'error': str(e),
            'timestamp': datetime.now(UTC).isoformat()
        }
        
        # Re-raise as TopGainersLosersError for consistent error handling
        if isinstance(e, TopGainersLosersError):
            raise
        else:
            raise TopGainersLosersError(f"Top gainers/losers fetch failed: {e}")

def _process_top_gainers_losers_data(data: List[Dict[str, Any]], datatype: str) -> List[Dict[str, Any]]:
    """
    Process and clean raw top gainers/losers data from Angel One API.
    
    Args:
        data: Raw data from API
        datatype: "topgainers" or "toplosers"
        
    Returns:
        List: Processed data
    """
    try:
        processed_data = []
        
        for item in data:
            processed_item = {
                'symbol': item.get('tradingsymbol', ''),
                'token': item.get('symboltoken', ''),
                'exchange': item.get('exchange', ''),
                'instrumenttype': item.get('instrumenttype', ''),
                'name': item.get('name', ''),
                'ltp': float(item.get('ltp', 0)),
                'change': float(item.get('change', 0)),
                'change_percentage': float(item.get('changepercent', 0)),
                'volume': int(item.get('volume', 0)),
                'open': float(item.get('open', 0)),
                'high': float(item.get('high', 0)),
                'low': float(item.get('low', 0)),
                'close': float(item.get('close', 0)),
                'datatype': datatype,
                'rank': len(processed_data) + 1  # Add rank based on position
            }
            
            # Add additional calculated fields
            if processed_item['close'] > 0:
                processed_item['day_range'] = processed_item['high'] - processed_item['low']
                processed_item['day_range_percentage'] = (processed_item['day_range'] / processed_item['close']) * 100
            else:
                processed_item['day_range'] = 0
                processed_item['day_range_percentage'] = 0
            
            # Add volume analysis
            processed_item['high_volume'] = processed_item['volume'] > 100000  # Basic threshold
            
            # Add price analysis
            if datatype == 'topgainers':
                processed_item['analysis'] = _analyze_gainer(processed_item)
            else:
                processed_item['analysis'] = _analyze_loser(processed_item)
            
            processed_data.append(processed_item)
        
        return processed_data
        
    except Exception as e:
        logger.warning(f"⚠️ Error processing top {datatype} data: {e}")
        return data  # Return original if processing fails

def _analyze_gainer(stock: Dict[str, Any]) -> Dict[str, Any]:
    """Analyze a top gainer stock."""
    analysis = {
        'momentum': 'STRONG' if stock['change_percentage'] > 10 else 'MODERATE' if stock['change_percentage'] > 5 else 'WEAK',
        'volume_profile': 'HIGH' if stock['high_volume'] else 'NORMAL',
        'price_action': 'BREAKOUT' if stock['ltp'] >= stock['high'] * 0.98 else 'CONSOLIDATING'
    }
    
    # Risk assessment for gainers
    if stock['change_percentage'] > 20:
        analysis['risk_level'] = 'HIGH'
        analysis['recommendation'] = 'CAUTION - High volatility'
    elif stock['change_percentage'] > 10:
        analysis['risk_level'] = 'MEDIUM'
        analysis['recommendation'] = 'Monitor for profit booking'
    else:
        analysis['risk_level'] = 'LOW'
        analysis['recommendation'] = 'Potential entry opportunity'
    
    return analysis

def _analyze_loser(stock: Dict[str, Any]) -> Dict[str, Any]:
    """Analyze a top loser stock."""
    analysis = {
        'momentum': 'STRONG_SELL' if stock['change_percentage'] < -10 else 'MODERATE_SELL' if stock['change_percentage'] < -5 else 'WEAK_SELL',
        'volume_profile': 'HIGH' if stock['high_volume'] else 'NORMAL',
        'price_action': 'BREAKDOWN' if stock['ltp'] <= stock['low'] * 1.02 else 'DECLINING'
    }
    
    # Opportunity assessment for losers
    if stock['change_percentage'] < -20:
        analysis['risk_level'] = 'HIGH'
        analysis['recommendation'] = 'Potential oversold bounce - high risk'
    elif stock['change_percentage'] < -10:
        analysis['risk_level'] = 'MEDIUM'
        analysis['recommendation'] = 'Watch for support levels'
    else:
        analysis['risk_level'] = 'LOW'
        analysis['recommendation'] = 'Minor correction - monitor'
    
    return analysis

async def get_top_gainers(exchange: str = "NSE", count: int = 25) -> List[Dict[str, Any]]:
    """
    Get top gainers for an exchange.
    
    Args:
        exchange: Exchange name
        count: Number of stocks to return
        
    Returns:
        List: Top gainers data
    """
    try:
        result = await get_top_gainers_losers(exchange, "topgainers", count)
        if result['success']:
            return result['data']
        return []
    except Exception as e:
        logger.error(f"❌ Top gainers fetch failed: {e}")
        return []

async def get_top_losers(exchange: str = "NSE", count: int = 25) -> List[Dict[str, Any]]:
    """
    Get top losers for an exchange.
    
    Args:
        exchange: Exchange name
        count: Number of stocks to return
        
    Returns:
        List: Top losers data
    """
    try:
        result = await get_top_gainers_losers(exchange, "toplosers", count)
        if result['success']:
            return result['data']
        return []
    except Exception as e:
        logger.error(f"❌ Top losers fetch failed: {e}")
        return []

async def get_market_movers(exchange: str = "NSE", count: int = 25) -> Dict[str, Any]:
    """
    Get both top gainers and losers for comprehensive market analysis.
    
    Args:
        exchange: Exchange name
        count: Number of stocks to return for each category
        
    Returns:
        Dict: Both gainers and losers with market analysis
    """
    try:
        # Fetch both in parallel
        gainers_task = get_top_gainers(exchange, count)
        losers_task = get_top_losers(exchange, count)
        
        gainers, losers = await asyncio.gather(gainers_task, losers_task, return_exceptions=True)
        
        # Handle exceptions
        if isinstance(gainers, Exception):
            logger.error(f"❌ Gainers fetch failed: {gainers}")
            gainers = []
        
        if isinstance(losers, Exception):
            logger.error(f"❌ Losers fetch failed: {losers}")
            losers = []
        
        # Market analysis
        market_analysis = _analyze_market_sentiment(gainers, losers)
        
        result = {
            'success': True,
            'exchange': exchange,
            'top_gainers': gainers,
            'top_losers': losers,
            'gainers_count': len(gainers),
            'losers_count': len(losers),
            'market_analysis': market_analysis,
            'timestamp': datetime.now(UTC).isoformat()
        }
        
        logger.info(f"✅ Market movers fetched: {len(gainers)} gainers, {len(losers)} losers from {exchange}")
        
        return result
        
    except Exception as e:
        logger.error(f"❌ Market movers fetch failed for {exchange}: {e}")
        return {
            'success': False,
            'error': str(e),
            'top_gainers': [],
            'top_losers': [],
            'timestamp': datetime.now(UTC).isoformat()
        }

def _analyze_market_sentiment(gainers: List[Dict[str, Any]], losers: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Analyze overall market sentiment based on gainers and losers.
    
    Args:
        gainers: List of top gainers
        losers: List of top losers
        
    Returns:
        Dict: Market sentiment analysis
    """
    try:
        if not gainers and not losers:
            return {'sentiment': 'UNKNOWN', 'confidence': 0}
        
        # Calculate average changes
        avg_gainer_change = sum(g.get('change_percentage', 0) for g in gainers) / len(gainers) if gainers else 0
        avg_loser_change = sum(l.get('change_percentage', 0) for l in losers) / len(losers) if losers else 0
        
        # Count high-impact moves
        strong_gainers = sum(1 for g in gainers if g.get('change_percentage', 0) > 10)
        strong_losers = sum(1 for l in losers if l.get('change_percentage', 0) < -10)
        
        # Overall sentiment calculation
        sentiment_score = avg_gainer_change + avg_loser_change  # Net sentiment
        
        if sentiment_score > 5:
            sentiment = 'VERY_BULLISH'
        elif sentiment_score > 2:
            sentiment = 'BULLISH'
        elif sentiment_score > -2:
            sentiment = 'NEUTRAL'
        elif sentiment_score > -5:
            sentiment = 'BEARISH'
        else:
            sentiment = 'VERY_BEARISH'
        
        # Confidence based on magnitude of moves
        confidence = min(100, abs(sentiment_score) * 10)
        
        analysis = {
            'sentiment': sentiment,
            'confidence': confidence,
            'sentiment_score': sentiment_score,
            'avg_gainer_change': avg_gainer_change,
            'avg_loser_change': avg_loser_change,
            'strong_gainers': strong_gainers,
            'strong_losers': strong_losers,
            'volatility': 'HIGH' if (strong_gainers + strong_losers) > 10 else 'MEDIUM' if (strong_gainers + strong_losers) > 5 else 'LOW',
            'recommendation': _get_market_recommendation(sentiment, confidence)
        }
        
        return analysis
        
    except Exception as e:
        logger.warning(f"⚠️ Market sentiment analysis failed: {e}")
        return {'sentiment': 'UNKNOWN', 'confidence': 0, 'error': str(e)}

def _get_market_recommendation(sentiment: str, confidence: float) -> str:
    """Get trading recommendation based on market sentiment."""
    recommendations = {
        'VERY_BULLISH': 'Consider long positions, watch for momentum stocks',
        'BULLISH': 'Selective buying opportunities, maintain bullish bias',
        'NEUTRAL': 'Wait for clearer direction, maintain balanced portfolio',
        'BEARISH': 'Consider profit booking, avoid new long positions',
        'VERY_BEARISH': 'Consider defensive positions, high caution advised'
    }
    
    base_rec = recommendations.get(sentiment, 'Monitor market closely')
    
    if confidence < 50:
        return f"{base_rec} (Low confidence - wait for confirmation)"
    else:
        return base_rec

def get_top_gainers_losers_sync(exchange: str, datatype: str, count: int = 25) -> Dict[str, Any]:
    """
    Synchronous wrapper for get_top_gainers_losers.
    
    ⚠️ WARNING: Use async version when possible for better performance.
    This is only for compatibility with legacy code.
    """
    import asyncio
    try:
        return asyncio.run(get_top_gainers_losers(exchange, datatype, count))
    except Exception as e:
        logger.error(f"❌ Sync top {datatype} fetch failed for {exchange}: {e}")
        return {
            'success': False,
            'data': [],
            'error': str(e)
        }

# Backward compatibility aliases (DEPRECATED - use new names)
fetch_top_gainers = get_top_gainers  # Alias for existing code
fetch_top_losers = get_top_losers   # Alias for existing code

if __name__ == "__main__":
    # Test top gainers/losers fetching
    async def test_top_gainers_losers():
        print("🧪 Testing Angel One Top Gainers/Losers")
        print("=" * 40)
        
        try:
            # Test market movers
            market_movers = await get_market_movers("NSE", 10)
            
            if market_movers['success']:
                print(f"✅ Market movers analysis:")
                analysis = market_movers['market_analysis']
                print(f"   Sentiment: {analysis['sentiment']}")
                print(f"   Confidence: {analysis['confidence']:.1f}%")
                print(f"   Gainers: {market_movers['gainers_count']}")
                print(f"   Losers: {market_movers['losers_count']}")
                print(f"   Recommendation: {analysis['recommendation']}")
                
                if market_movers['top_gainers']:
                    top_gainer = market_movers['top_gainers'][0]
                    print(f"   Top Gainer: {top_gainer['symbol']} ({top_gainer['change_percentage']:+.2f}%)")
                
                if market_movers['top_losers']:
                    top_loser = market_movers['top_losers'][0]
                    print(f"   Top Loser: {top_loser['symbol']} ({top_loser['change_percentage']:+.2f}%)")
            else:
                print(f"❌ Market movers fetch failed: {market_movers.get('error')}")
                
        except Exception as e:
            print(f"❌ Top gainers/losers test failed: {e}")
        
        print("\n⚠️ Note: Actual data fetching requires rate controller and live connection")
    
    # Run test
    import asyncio
    asyncio.run(test_top_gainers_losers())
