"""
Angel One API: loginByPassword - User Authentication
===================================================

CRITICAL METHOD: System entry point - required for all other APIs
Rate Limit: 1 request/second per API key  
Priority: CRITICAL

MOVED FROM: api_gateway/auth.py, core/connections.py
This method consolidates and improves the existing authentication logic.

Usage:
    from angel_one_api.methods.login_by_password import login_by_password
    
    # Single login
    session_data = await login_by_password(client_id, password, totp)
    
    # Auto-login with stored credentials
    session_data = await auto_login()

Author: AI Trading System  
Rate Limit: STRICTLY ENFORCED 1 req/sec per key
"""

import time
from typing import Dict, Optional, Any
# Import new Angel One logger
from ..logger import get_api_logger
import pyotp

# Import our rate limiting system
from ..rate_limiter.rate_controller import get_rate_controller, rate_limited, APIPriority
from ..rate_limiter.api_limits import API_LIMITS

logger = get_api_logger("login_by_password")

class AuthenticationError(Exception):
    """Raised when authentication fails."""
    pass

@rate_limited("login_by_password", APIPriority.CRITICAL)
async def login_by_password(
    client_id: str,
    password: str, 
    totp_code: str,
    _rate_limit_permit: Optional[Dict] = None
) -> Dict[str, Any]:
    """
    Authenticate user with Angel One using password and TOTP.
    
    Args:
        client_id: Angel One client ID
        password: Account password  
        totp_code: Time-based OTP (6 digits)
        _rate_limit_permit: Automatically provided by rate limiter
        
    Returns:
        Dict containing session data with jwt_token and feed_token
        
    Raises:
        AuthenticationError: If authentication fails
        RateLimitExceeded: If rate limit would be exceeded
        
    Rate Limit: 1 request/second per API key
    """
    try:
        if not _rate_limit_permit:
            raise AuthenticationError("No rate limit permit - internal error")
        
        # Get Angel One client for authentication
        from SmartApi.smartConnect import SmartConnect
        from core.connections import ConnectionManager
        
        # Get API key from the permit (rate controller selected the best key)
        api_key_id = _rate_limit_permit['api_key_id']
        
        # Get the actual API key from settings
        from config import settings
        api_keys_map = settings.API_KEYS
        
        # Find the actual API key value
        api_key = None
        for key_name, key_value in api_keys_map.items():
            if f"key_{list(api_keys_map.keys()).index(key_name) + 1}" == api_key_id:
                api_key = key_value
                break
        
        if not api_key:
            raise AuthenticationError(f"API key not found for {api_key_id}")
        
        # Validate inputs
        if not all([client_id, password, totp_code]):
            raise AuthenticationError("Missing required authentication parameters")
        
        if len(totp_code) != 6 or not totp_code.isdigit():
            raise AuthenticationError("Invalid TOTP code format (must be 6 digits)")
        
        # Create SmartConnect client
        logger.debug(f"🔐 Login attempt for client {client_id} using {api_key_id}")
        
        smart_connect = SmartConnect(api_key)
        
        # Make authentication request with rate limiting already enforced
        session_data = smart_connect.generateSession(
            client_id,
            password, 
            totp_code
        )
        
        # Validate response
        if not session_data:
            raise AuthenticationError("Empty response from authentication API")
        
        if not session_data.get('status'):
            error_msg = session_data.get('message', 'Unknown authentication error')
            raise AuthenticationError(f"Authentication failed: {error_msg}")
        
        data = session_data.get('data')
        if not data:
            raise AuthenticationError("No data in authentication response")
        
        # Extract tokens
        jwt_token = data.get('jwtToken')
        feed_token = data.get('feedToken') 
        refresh_token = data.get('refreshToken')
        
        if not jwt_token:
            raise AuthenticationError("JWT token not received")
        
        # Success response
        auth_result = {
            'status': True,
            'jwt_token': jwt_token,
            'feed_token': feed_token,
            'refresh_token': refresh_token,
            'client_id': client_id,
            'api_key_id': api_key_id,
            'login_time': time.time(),
            'session_data': session_data  # Full response for reference
        }
        
        logger.info(f"✅ Authentication successful for {client_id} using {api_key_id}")
        
        return auth_result
        
    except Exception as e:
        logger.error(f"❌ Authentication failed for {client_id}: {e}")
        
        # Re-raise as AuthenticationError for consistent error handling
        if isinstance(e, AuthenticationError):
            raise
        else:
            raise AuthenticationError(f"Authentication failed: {e}")

async def auto_login() -> Dict[str, Any]:
    """
    Automatically login using credentials from settings.
    
    Returns:
        Dict containing session data
        
    Raises:
        AuthenticationError: If auto-login fails
    """
    try:
        # Import settings
        from config import settings
        import pyotp
        
        # Validate all required credentials are available
        required_settings = [
            settings.CLIENT_ID,
            settings.PASSWORD, 
            settings.TOTP_SECRET
        ]
        
        if not all(required_settings):
            raise AuthenticationError("Missing credentials in settings - check .env file")
        
        # Generate current TOTP
        totp = pyotp.TOTP(settings.TOTP_SECRET).now()
        
        # Perform login
        result = await login_by_password(
            client_id=settings.CLIENT_ID,
            password=settings.PASSWORD,
            totp_code=totp
        )
        
        logger.info("✅ Auto-login successful")
        return result
        
    except Exception as e:
        logger.error(f"❌ Auto-login failed: {e}")
        raise AuthenticationError(f"Auto-login failed: {e}")

def login_by_password_sync(client_id: str, password: str, totp_code: str) -> Dict[str, Any]:
    """
    Synchronous wrapper for login_by_password.
    
    ⚠️ WARNING: Use async version when possible for better performance.
    This is only for compatibility with legacy code.
    """
    import asyncio
    try:
        return asyncio.run(login_by_password(client_id, password, totp_code))
    except Exception as e:
        logger.error(f"❌ Sync login failed for {client_id}: {e}")
        raise

def auto_login_sync() -> Dict[str, Any]:
    """
    Synchronous wrapper for auto_login.
    
    ⚠️ WARNING: Use async version when possible.
    """
    import asyncio
    try:
        return asyncio.run(auto_login())
    except Exception as e:
        logger.error(f"❌ Sync auto-login failed: {e}")
        raise

# Backward compatibility aliases (DEPRECATED - use new names)
angel_one_login = login_by_password  # Alias for existing code
authenticate_user = login_by_password  # Alias for existing code

if __name__ == "__main__":
    # Test authentication
    async def test_authentication():
        print("🧪 Testing Angel One Authentication")
        print("=" * 40)
        
        try:
            # Test auto-login
            result = await auto_login()
            print(f"✅ Auto-login successful")
            print(f"   JWT Token: {result['jwt_token'][:20]}...")
            print(f"   API Key: {result['api_key_id']}")
            print(f"   Client: {result['client_id']}")
            
        except Exception as e:
            print(f"❌ Auto-login failed: {e}")
        
        # Note: Manual login test would require actual credentials
        print("\n⚠️ Note: Manual login test requires actual credentials")
    
    # Run test (requires rate controller to be initialized)
    print("⚠️ Note: Requires rate controller and valid credentials for testing")
    # asyncio.run(test_authentication())
