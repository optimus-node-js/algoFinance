"""
Angel One API: getProfile - User Profile Data
============================================

METHOD: User account and profile information
Rate Limit: 1 request/second per API key
Priority: MEDIUM (account information)

Usage:
    from angel_one_api.methods.get_profile import get_profile
    
    # Get user profile
    profile = await get_profile()
    
    # Get user limits and margins
    limits = await get_user_limits()

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

logger = get_api_logger("get_profile")

class ProfileError(Exception):
    """Raised when profile data fetching fails."""
    pass

@rate_limited("get_profile", APIPriority.MEDIUM)
async def get_profile(_rate_limit_permit: Optional[Dict] = None) -> Dict[str, Any]:
    """
    Get user profile from Angel One API.
    
    Args:
        _rate_limit_permit: Automatically provided by rate limiter
        
    Returns:
        Dict containing:
            - success: bool
            - profile: Dict of profile data
            - client_code: str
            - name: str
            - email: str
            - mobile: str
            - exchanges: List
            - products: List
            - timestamp: str
        
    Raises:
        ProfileError: If profile fetching fails
        RateLimitExceeded: If rate limit would be exceeded
        
    Rate Limit: 1 request/second per API key
    """
    try:
        if not _rate_limit_permit:
            raise ProfileError("No rate limit permit - internal error")
        
        # Get Angel One client
        # Use interface to get SmartAPI client
        from interface import get_angel_one_interface
        interface = get_angel_one_interface()
        angel_client = interface.smart_api
        
        # angel_client already set above
        if not angel_client:
            raise ProfileError("Angel One API client not available")
        
        # Log request
        logger.debug(f"👤 Profile request using {_rate_limit_permit['api_key_id']}")
        
        # Make API call with strict rate limiting already enforced
        # Get refresh token from the client (stored by ConnectionManager)
        refresh_token = getattr(angel_client, 'refreshToken', None)
        if not refresh_token:
            raise ProfileError("No refresh token available - client may not be properly authenticated")
        
        response = angel_client.getProfile(refresh_token)
        
        # Parse response
        if not response:
            raise ProfileError("Empty response from profile API")
        
        if not response.get('status'):
            error_msg = response.get('message', 'Unknown error')
            raise ProfileError(f"Profile API error: {error_msg}")
        
        profile_data = response.get('data', {})
        
        # Process profile data
        processed_profile = {
            'client_code': profile_data.get('clientcode', ''),
            'name': profile_data.get('name', ''),
            'email': profile_data.get('email', ''),
            'mobile_number': profile_data.get('mobileno', ''),
            'broker': profile_data.get('broker', ''),
            'products': profile_data.get('products', []),
            'last_login_time': profile_data.get('lastlogintime', ''),
            'exchanges': profile_data.get('exchanges', [])
        }
        print('this is profile data', profile_data)
        # Success response
        result = {
            'success': True,
            'profile': processed_profile,
            'client_code': processed_profile['client_code'],
            'name': processed_profile['name'],
            'email': processed_profile['email'],
            'mobile': processed_profile['mobile_number'],
            'exchanges': processed_profile['exchanges'],
            'products': processed_profile['products'],
            'raw_data': profile_data,
            'timestamp': datetime.now(UTC).isoformat(),
            'api_key_id': _rate_limit_permit['api_key_id'],
            'response_time': time.time()
        }
        
        logger.info(f"✅ Profile fetched for: {processed_profile['name']} ({processed_profile['client_code']})")
        
        return result
        
    except Exception as e:
        logger.error(f"❌ Profile fetch failed: {e}")
        
        # Create error response
        error_result = {
            'success': False,
            'profile': {},
            'error': str(e),
            'timestamp': datetime.now(UTC).isoformat()
        }
        
        # Re-raise as ProfileError for consistent error handling
        if isinstance(e, ProfileError):
            raise
        else:
            raise ProfileError(f"Profile fetch failed: {e}")

async def get_user_limits() -> Dict[str, Any]:
    """
    Get user trading limits and margin information.
    
    Note: This combines profile data with additional limit analysis.
    
    Returns:
        Dict: User limits and trading capacity
    """
    try:
        # Get profile first
        profile_result = await get_profile()
        
        if not profile_result['success']:
            return {'success': False, 'error': profile_result.get('error')}
        
        profile = profile_result['profile']
        
        # Analyze available products and exchanges
        available_exchanges = profile.get('exchanges', [])
        available_products = profile.get('products', [])
        
        # Basic limits analysis
        limits_info = {
            'success': True,
            'client_code': profile.get('client_code'),
            'trading_capacity': {
                'exchanges': available_exchanges,
                'exchange_count': len(available_exchanges),
                'products': available_products,
                'product_count': len(available_products),
                'can_trade_equity': 'NSE' in available_exchanges or 'BSE' in available_exchanges,
                'can_trade_derivatives': 'NFO' in available_exchanges,
                'can_trade_commodity': 'MCX' in available_exchanges,
                'intraday_enabled': 'MIS' in available_products or 'INTRADAY' in available_products,
                'delivery_enabled': 'CNC' in available_products or 'DELIVERY' in available_products
            },
            'profile_data': profile,
            'timestamp': profile_result['timestamp']
        }
        
        return limits_info
        
    except Exception as e:
        logger.error(f"❌ User limits fetch failed: {e}")
        return {'success': False, 'error': str(e)}

def get_profile_sync() -> Dict[str, Any]:
    """
    Synchronous wrapper for get_profile.
    
    ⚠️ WARNING: Use async version when possible for better performance.
    This is only for compatibility with legacy code.
    """
    import asyncio
    try:
        return asyncio.run(get_profile())
    except Exception as e:
        logger.error(f"❌ Sync profile fetch failed: {e}")
        return {
            'success': False,
            'profile': {},
            'error': str(e)
        }

# Backward compatibility aliases (DEPRECATED - use new names)
fetch_profile = get_profile  # Alias for existing code
get_user_profile = get_profile  # Alias for existing code

if __name__ == "__main__":
    # Test profile fetching
    async def test_profile():
        print("🧪 Testing Angel One Profile")
        print("=" * 40)
        
        try:
            # Test basic profile
            profile = await get_profile()
            print('this is the main profile', profile)
            if profile['success']:
                print(f"✅ Profile fetched:")
                print(f"   Name: {profile['name']}")
                print(f"   Client Code: {profile['client_code']}")
                print(f"   Email: {profile['email']}")
                print(f"   Exchanges: {', '.join(profile['exchanges'])}")
                print(f"   Products: {', '.join(profile['products'])}")
            else:
                print(f"❌ Profile fetch failed: {profile.get('error')}")
                
        except Exception as e:
            print(f"❌ Profile test failed: {e}")
        
        try:
            # Test user limits
            limits = await get_user_limits()
            if limits['success']:
                capacity = limits['trading_capacity']
                print(f"✅ Trading capacity:")
                print(f"   Equity trading: {'✅' if capacity['can_trade_equity'] else '❌'}")
                print(f"   Derivatives: {'✅' if capacity['can_trade_derivatives'] else '❌'}")
                print(f"   Intraday: {'✅' if capacity['intraday_enabled'] else '❌'}")
                print(f"   Delivery: {'✅' if capacity['delivery_enabled'] else '❌'}")
            else:
                print(f"❌ User limits failed: {limits.get('error')}")
                
        except Exception as e:
            print(f"❌ User limits test failed: {e}")
    
    # Run test (requires rate controller to be initialized)
    print("⚠️ Note: Requires rate controller initialization for testing")
    # asyncio.run(test_profile())
