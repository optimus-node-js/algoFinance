"""
Angel One API: getMarketStatus - Market Status Check
==================================================

METHOD: Check if markets are open or closed
Rate Limit: 1 request/second per API key
Priority: MEDIUM (market status information)

Usage:
    from angel_one_api.methods.get_market_status import get_market_status
    
    status = await get_market_status()
    if status['market_open']:
        print("Market is open for trading")

Author: AI Trading System
"""

import asyncio
from typing import Dict, Optional, Any
# Import new Angel One logger
from ..logger import get_api_logger
from datetime import datetime, UTC

from ..rate_limiter.rate_controller import rate_limited, APIPriority

logger = get_api_logger("get_market_status")

class MarketStatusError(Exception):
    """Raised when market status check fails."""
    pass

@rate_limited("get_market_status", APIPriority.MEDIUM)
async def get_market_status(_rate_limit_permit: Optional[Dict] = None) -> Dict[str, Any]:
    """
    Get current market status from Angel One API.
    
    Returns:
        Dict containing:
            - success: bool
            - market_open: bool
            - market_status: str
            - timestamp: str
    """
    try:
        from core.connections import ConnectionManager
        
        angel_client = ConnectionManager.get_smartapi_client()
        if not angel_client:
            raise MarketStatusError("Angel One API client not available")
        
        # Make API call - check if method exists
        if hasattr(angel_client, 'getMarketStatus'):
            response = angel_client.getMarketStatus()
        else:
            # Method not available in SmartConnect SDK
            raise MarketStatusError("getMarketStatus method not available in SmartConnect SDK. Please check Angel One SmartAPI documentation for alternative endpoints.")
        
        if not response or not response.get('status'):
            raise MarketStatusError("Failed to get market status")
        
        data = response.get('data', {})
        
        return {
            'success': True,
            'market_open': data.get('marketopen', False),
            'market_status': data.get('status', 'UNKNOWN'),
            'timestamp': datetime.now(UTC).isoformat()
        }
        
    except Exception as e:
        logger.error(f"❌ Market status check failed: {e}")
        raise MarketStatusError(f"Market status check failed: {e}")
