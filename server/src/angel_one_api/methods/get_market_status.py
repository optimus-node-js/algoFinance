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
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))
from logger import get_api_logger
from datetime import datetime, UTC

from rate_limiter.rate_controller import rate_limited, APIPriority

# Import idempotency enhancements
try:
    from ..enhancements.idempotency_manager import idempotency_wrapper
    IDEMPOTENCY_AVAILABLE = True
except ImportError:
    IDEMPOTENCY_AVAILABLE = False

logger = get_api_logger("get_market_status")

class MarketStatusError(Exception):
    """Raised when market status check fails."""
    pass

@idempotency_wrapper(method_type="market", ttl=120, cache_response=True) if IDEMPOTENCY_AVAILABLE else lambda x: x
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
        # Use interface to get SmartAPI client
        from interface import get_angel_one_interface
        interface = get_angel_one_interface()
        angel_client = interface.smart_api
        
        # angel_client already set above
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
