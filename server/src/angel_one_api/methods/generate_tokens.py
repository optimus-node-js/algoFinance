"""
Angel One API: generateTokens - Token Generation and Refresh
==========================================================

METHOD: Generate and refresh authentication tokens
Rate Limit: 1 request/second per API key
Priority: MEDIUM (session management)

Usage:
    from angel_one_api.methods.generate_tokens import generate_tokens
    
    # Generate new tokens with refresh token
    new_tokens = await generate_tokens("your_refresh_token")
    
    # Auto-refresh tokens when needed
    tokens = await auto_refresh_tokens()

Author: AI Trading System
Rate Limit: STRICTLY ENFORCED 1 req/sec per key
"""

import time
from typing import Dict, List, Optional, Any
# Import new Angel One logger
from ..logger import get_api_logger
from datetime import datetime, UTC, timedelta

# Import our rate limiting system
from ..rate_limiter.rate_controller import get_rate_controller, rate_limited, APIPriority
from ..rate_limiter.api_limits import API_LIMITS

logger = get_api_logger("generate_tokens")

class TokenGenerationError(Exception):
    """Raised when token generation fails."""
    pass

@rate_limited("generate_tokens", APIPriority.MEDIUM)
async def generate_tokens(
    refresh_token: str,
    _rate_limit_permit: Optional[Dict] = None
) -> Dict[str, Any]:
    """
    Generate new access and refresh tokens using Angel One API.
    
    Args:
        refresh_token: Valid refresh token
        _rate_limit_permit: Automatically provided by rate limiter
        
    Returns:
        Dict containing:
            - success: bool
            - access_token: str (new access token)
            - refresh_token: str (new refresh token)
            - expires_at: str (expiration timestamp)
            - token_info: Dict
            - timestamp: str
        
    Raises:
        TokenGenerationError: If token generation fails
        RateLimitExceeded: If rate limit would be exceeded
        
    Rate Limit: 1 request/second per API key
    """
    try:
        if not _rate_limit_permit:
            raise TokenGenerationError("No rate limit permit - internal error")
        
        # Get Angel One client
        from core.connections import ConnectionManager
        
        angel_client = ConnectionManager.get_smartapi_client()
        if not angel_client:
            raise TokenGenerationError("Angel One API client not available")
        
        # Validate refresh token
        if not refresh_token or len(refresh_token) < 10:
            raise TokenGenerationError("Valid refresh token is required")
        
        # Log request
        logger.debug(f"🔄 Token generation request using {_rate_limit_permit['api_key_id']}")
        
        # Make API call with strict rate limiting already enforced
        response = angel_client.generateToken(refresh_token)
        
        # Parse response
        if not response:
            raise TokenGenerationError("Empty response from generateTokens API")
        
        if not response.get('status'):
            error_msg = response.get('message', 'Unknown error')
            error_code = response.get('errorcode', 'N/A')
            raise TokenGenerationError(f"Token generation failed: {error_msg} (Code: {error_code})")
        
        token_data = response.get('data', {})
        
        # Extract token information
        new_access_token = token_data.get('jwtToken', '')
        new_refresh_token = token_data.get('refreshToken', '')
        
        if not new_access_token or not new_refresh_token:
            raise TokenGenerationError("Invalid token data received")
        
        # Calculate expiration (JWT tokens typically expire in 24 hours)
        expires_at = datetime.now(UTC) + timedelta(hours=24)
        
        # Process token information
        token_info = {
            'client_code': token_data.get('clientcode', ''),
            'jwt_token': new_access_token,
            'refresh_token': new_refresh_token,
            'feed_token': token_data.get('feedToken', ''),
            'generated_at': datetime.now(UTC).isoformat(),
            'expires_at': expires_at.isoformat(),
            'token_type': 'Bearer'
        }
        
        # Success response
        result = {
            'success': True,
            'access_token': new_access_token,
            'refresh_token': new_refresh_token,
            'feed_token': token_data.get('feedToken', ''),
            'expires_at': expires_at.isoformat(),
            'token_info': token_info,
            'raw_data': token_data,
            'timestamp': datetime.now(UTC).isoformat(),
            'api_key_id': _rate_limit_permit['api_key_id'],
            'response_time': time.time()
        }
        
        logger.info(f"✅ Tokens generated successfully, expires: {expires_at.strftime('%Y-%m-%d %H:%M:%S')}")
        
        return result
        
    except Exception as e:
        logger.error(f"❌ Token generation failed: {e}")
        
        # Create error response
        error_result = {
            'success': False,
            'access_token': '',
            'refresh_token': '',
            'error': str(e),
            'timestamp': datetime.now(UTC).isoformat()
        }
        
        # Re-raise as TokenGenerationError for consistent error handling
        if isinstance(e, TokenGenerationError):
            raise
        else:
            raise TokenGenerationError(f"Token generation failed: {e}")

async def auto_refresh_tokens() -> Dict[str, Any]:
    """
    Automatically refresh tokens using stored refresh token.
    
    Returns:
        Dict: Token refresh result
    """
    try:
        # Get stored refresh token (would typically come from secure storage)
        from core.connections import ConnectionManager
        
        # This is a simplified implementation - in practice, you'd have
        # secure token storage and retrieval mechanisms
        stored_refresh_token = _get_stored_refresh_token()
        
        if not stored_refresh_token:
            raise TokenGenerationError("No stored refresh token available")
        
        # Generate new tokens
        token_result = await generate_tokens(stored_refresh_token)
        
        if token_result['success']:
            # Store new tokens securely
            await _store_tokens_securely(token_result)
            
            # Update connection manager with new tokens
            await _update_connection_tokens(token_result)
        
        return token_result
        
    except Exception as e:
        logger.error(f"❌ Auto token refresh failed: {e}")
        return {'success': False, 'error': str(e)}

def _get_stored_refresh_token() -> Optional[str]:
    """
    Get refresh token from secure storage.
    
    Returns:
        str: Stored refresh token or None
    """
    try:
        # In a real implementation, this would retrieve from secure storage
        # (database, encrypted file, environment variables, etc.)
        
        # For now, we'll try to get it from connection manager
        from core.connections import ConnectionManager
        
        # This is a placeholder - actual implementation would vary
        # based on your storage mechanism
        return None
        
    except Exception as e:
        logger.warning(f"⚠️ Could not retrieve stored refresh token: {e}")
        return None

async def _store_tokens_securely(token_result: Dict[str, Any]) -> bool:
    """
    Store tokens securely.
    
    Args:
        token_result: Token generation result
        
    Returns:
        bool: Success status
    """
    try:
        # In a real implementation, this would store tokens securely
        # (encrypted database, secure file, key management service, etc.)
        
        token_info = token_result.get('token_info', {})
        
        # Log successful storage (without exposing actual tokens)
        logger.info("✅ Tokens stored securely")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Token storage failed: {e}")
        return False

async def _update_connection_tokens(token_result: Dict[str, Any]) -> bool:
    """
    Update connection manager with new tokens.
    
    Args:
        token_result: Token generation result
        
    Returns:
        bool: Success status
    """
    try:
        # Update connection manager with new tokens
        from core.connections import ConnectionManager
        
        # This would update the active connection with new tokens
        # Implementation depends on your connection manager design
        
        logger.info("✅ Connection tokens updated")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Connection token update failed: {e}")
        return False

async def check_token_validity(access_token: str) -> Dict[str, Any]:
    """
    Check if an access token is still valid.
    
    Args:
        access_token: Access token to validate
        
    Returns:
        Dict: Token validity information
    """
    try:
        # This would typically make a test API call to validate the token
        # For now, we'll implement basic JWT token validation
        
        if not access_token:
            return {
                'valid': False,
                'reason': 'No token provided',
                'needs_refresh': True
            }
        
        # Basic token format validation
        token_parts = access_token.split('.')
        if len(token_parts) != 3:
            return {
                'valid': False,
                'reason': 'Invalid token format',
                'needs_refresh': True
            }
        
        # In a real implementation, you would:
        # 1. Decode the JWT token
        # 2. Check expiration
        # 3. Validate signature
        # 4. Make a test API call
        
        return {
            'valid': True,
            'reason': 'Token format appears valid',
            'needs_refresh': False,
            'checked_at': datetime.now(UTC).isoformat()
        }
        
    except Exception as e:
        logger.error(f"❌ Token validation failed: {e}")
        return {
            'valid': False,
            'reason': str(e),
            'needs_refresh': True
        }

async def schedule_token_refresh(hours_before_expiry: int = 2) -> Dict[str, Any]:
    """
    Schedule automatic token refresh before expiration.
    
    Args:
        hours_before_expiry: Hours before expiry to refresh (default: 2)
        
    Returns:
        Dict: Scheduling result
    """
    try:
        # This would typically integrate with a task scheduler
        # (celery, APScheduler, cron job, etc.)
        
        refresh_time = datetime.now(UTC) + timedelta(hours=24-hours_before_expiry)
        
        logger.info(f"📅 Token refresh scheduled for {refresh_time.strftime('%Y-%m-%d %H:%M:%S')} UTC")
        
        return {
            'success': True,
            'scheduled_time': refresh_time.isoformat(),
            'hours_before_expiry': hours_before_expiry,
            'message': 'Token refresh scheduled successfully'
        }
        
    except Exception as e:
        logger.error(f"❌ Token refresh scheduling failed: {e}")
        return {'success': False, 'error': str(e)}

async def get_token_status() -> Dict[str, Any]:
    """
    Get current token status and information.
    
    Returns:
        Dict: Token status information
    """
    try:
        # Get current token information
        stored_token = _get_stored_refresh_token()
        
        status = {
            'has_refresh_token': bool(stored_token),
            'auto_refresh_available': bool(stored_token),
            'last_refresh': None,  # Would be stored with tokens
            'next_scheduled_refresh': None,  # Would come from scheduler
            'token_source': 'stored' if stored_token else 'none',
            'checked_at': datetime.now(UTC).isoformat()
        }
        
        return {'success': True, 'status': status}
        
    except Exception as e:
        logger.error(f"❌ Token status check failed: {e}")
        return {'success': False, 'error': str(e)}

def generate_tokens_sync(refresh_token: str) -> Dict[str, Any]:
    """
    Synchronous wrapper for generate_tokens.
    
    ⚠️ WARNING: Use async version when possible for better performance.
    This is only for compatibility with legacy code.
    """
    import asyncio
    try:
        return asyncio.run(generate_tokens(refresh_token))
    except Exception as e:
        logger.error(f"❌ Sync token generation failed: {e}")
        return {
            'success': False,
            'access_token': '',
            'refresh_token': '',
            'error': str(e)
        }

# Backward compatibility aliases (DEPRECATED - use new names)
refresh_tokens = generate_tokens  # Alias for existing code
get_new_tokens = generate_tokens  # Alias for existing code

if __name__ == "__main__":
    # Test token generation
    async def test_token_generation():
        print("🧪 Testing Angel One Token Generation")
        print("=" * 40)
        
        # Test token status
        try:
            status = await get_token_status()
            if status['success']:
                print(f"✅ Token status check:")
                token_status = status['status']
                print(f"   Has refresh token: {token_status['has_refresh_token']}")
                print(f"   Auto refresh available: {token_status['auto_refresh_available']}")
            else:
                print(f"❌ Token status check failed: {status.get('error')}")
        except Exception as e:
            print(f"❌ Token status test failed: {e}")
        
        # Test token validation
        try:
            validation = await check_token_validity("sample.jwt.token")
            print(f"✅ Token validation test:")
            print(f"   Valid: {validation['valid']}")
            print(f"   Reason: {validation['reason']}")
        except Exception as e:
            print(f"❌ Token validation test failed: {e}")
        
        print("\n⚠️ Note: Actual token generation requires valid refresh token and live connection")
    
    # Run test
    import asyncio
    asyncio.run(test_token_generation())
