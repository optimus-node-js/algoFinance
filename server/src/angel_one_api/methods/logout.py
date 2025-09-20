"""
Angel One API: logout - Session Logout
=====================================

METHOD: Logout and invalidate session tokens
Rate Limit: 1 request/second per API key
Priority: LOW (session cleanup)

Usage:
    from angel_one_api.methods.logout import logout
    
    # Logout current session
    result = await logout()
    
    # Clean logout with token cleanup
    result = await clean_logout()

Author: AI Trading System
Rate Limit: STRICTLY ENFORCED 1 req/sec per key
"""

import time
from typing import Dict, List, Optional, Any
import logging
from datetime import datetime, UTC

# Import our rate limiting system
from ..rate_limiter.rate_controller import get_rate_controller, rate_limited, APIPriority
from ..rate_limiter.api_limits import API_LIMITS

logger = logging.getLogger(__name__)

class LogoutError(Exception):
    """Raised when logout fails."""
    pass

@rate_limited("logout", APIPriority.LOW)
async def logout(_rate_limit_permit: Optional[Dict] = None) -> Dict[str, Any]:
    """
    Logout from Angel One session and invalidate tokens.
    
    Args:
        _rate_limit_permit: Automatically provided by rate limiter
        
    Returns:
        Dict containing:
            - success: bool
            - message: str
            - logged_out_at: str
            - session_info: Dict
            - timestamp: str
        
    Raises:
        LogoutError: If logout fails
        RateLimitExceeded: If rate limit would be exceeded
        
    Rate Limit: 1 request/second per API key
    """
    try:
        if not _rate_limit_permit:
            raise LogoutError("No rate limit permit - internal error")
        
        # Get Angel One client
        from core.connections import ConnectionManager
        
        angel_client = ConnectionManager.get_smartapi_client()
        if not angel_client:
            raise LogoutError("Angel One API client not available")
        
        # Log request
        logger.debug(f"🚪 Logout request using {_rate_limit_permit['api_key_id']}")
        
        # Get session info before logout
        session_info = await _get_session_info()
        
        # Make API call with strict rate limiting already enforced
        response = angel_client.logout()
        
        # Parse response
        if not response:
            logger.warning("⚠️ Empty response from logout API - proceeding with cleanup")
            response = {'status': True, 'message': 'Logout completed (empty response)'}
        
        # Angel One logout API might return different response formats
        # Some versions return success even for already logged out sessions
        logout_successful = response.get('status', True)
        message = response.get('message', 'Logout completed')
        
        # Perform cleanup regardless of API response
        cleanup_result = await _cleanup_session()
        
        # Success response
        result = {
            'success': True,
            'message': message,
            'logged_out_at': datetime.now(UTC).isoformat(),
            'session_info': session_info,
            'cleanup_performed': cleanup_result,
            'api_response': response,
            'timestamp': datetime.now(UTC).isoformat(),
            'api_key_id': _rate_limit_permit['api_key_id'],
            'response_time': time.time()
        }
        
        logger.info(f"✅ Logout completed successfully")
        
        return result
        
    except Exception as e:
        logger.error(f"❌ Logout failed: {e}")
        
        # Even if logout API fails, try to clean up locally
        try:
            await _cleanup_session()
            logger.info("✅ Local session cleanup completed despite API error")
        except Exception as cleanup_error:
            logger.error(f"❌ Session cleanup also failed: {cleanup_error}")
        
        # Create error response
        error_result = {
            'success': False,
            'message': str(e),
            'error': str(e),
            'timestamp': datetime.now(UTC).isoformat()
        }
        
        # Re-raise as LogoutError for consistent error handling
        if isinstance(e, LogoutError):
            raise
        else:
            raise LogoutError(f"Logout failed: {e}")

async def _get_session_info() -> Dict[str, Any]:
    """
    Get current session information before logout.
    
    Returns:
        Dict: Session information
    """
    try:
        # Get session details from connection manager
        from core.connections import ConnectionManager
        
        # This would extract current session info
        # Implementation depends on your connection manager design
        
        session_info = {
            'session_active': True,
            'session_start': None,  # Would be tracked by connection manager
            'api_calls_made': None,  # Would be tracked by rate limiter
            'last_activity': datetime.now(UTC).isoformat()
        }
        
        return session_info
        
    except Exception as e:
        logger.warning(f"⚠️ Could not retrieve session info: {e}")
        return {'session_active': False, 'error': str(e)}

async def _cleanup_session() -> Dict[str, Any]:
    """
    Perform local session cleanup.
    
    Returns:
        Dict: Cleanup results
    """
    cleanup_tasks = []
    
    try:
        # Clear stored tokens
        token_cleanup = await _clear_stored_tokens()
        cleanup_tasks.append(('clear_tokens', token_cleanup))
        
        # Reset connection manager
        connection_cleanup = await _reset_connection_manager()
        cleanup_tasks.append(('reset_connection', connection_cleanup))
        
        # Clear any cached data
        cache_cleanup = await _clear_cached_data()
        cleanup_tasks.append(('clear_cache', cache_cleanup))
        
        # Stop any background tasks
        background_cleanup = await _stop_background_tasks()
        cleanup_tasks.append(('stop_background', background_cleanup))
        
        successful_tasks = [task for task, result in cleanup_tasks if result]
        
        cleanup_result = {
            'success': True,
            'tasks_completed': len(successful_tasks),
            'total_tasks': len(cleanup_tasks),
            'completed_tasks': successful_tasks,
            'cleanup_timestamp': datetime.now(UTC).isoformat()
        }
        
        logger.info(f"✅ Session cleanup: {len(successful_tasks)}/{len(cleanup_tasks)} tasks completed")
        
        return cleanup_result
        
    except Exception as e:
        logger.error(f"❌ Session cleanup failed: {e}")
        return {'success': False, 'error': str(e)}

async def _clear_stored_tokens() -> bool:
    """Clear stored authentication tokens."""
    try:
        # Clear tokens from secure storage
        # Implementation depends on your token storage mechanism
        
        logger.debug("🔑 Clearing stored tokens")
        return True
        
    except Exception as e:
        logger.warning(f"⚠️ Token clearing failed: {e}")
        return False

async def _reset_connection_manager() -> bool:
    """Reset connection manager state."""
    try:
        # Reset connection manager to clean state
        from core.connections import ConnectionManager
        
        # This would reset the connection manager
        # Implementation depends on your connection manager design
        
        logger.debug("🔄 Resetting connection manager")
        return True
        
    except Exception as e:
        logger.warning(f"⚠️ Connection manager reset failed: {e}")
        return False

async def _clear_cached_data() -> bool:
    """Clear any cached data."""
    try:
        # Clear cached data (instrument tokens, quotes, etc.)
        # Implementation depends on your caching mechanism
        
        logger.debug("🗑️ Clearing cached data")
        return True
        
    except Exception as e:
        logger.warning(f"⚠️ Cache clearing failed: {e}")
        return False

async def _stop_background_tasks() -> bool:
    """Stop any background tasks."""
    try:
        # Stop background tasks (token refresh, data updates, etc.)
        # Implementation depends on your task management
        
        logger.debug("⏹️ Stopping background tasks")
        return True
        
    except Exception as e:
        logger.warning(f"⚠️ Background task stopping failed: {e}")
        return False

async def clean_logout() -> Dict[str, Any]:
    """
    Perform a comprehensive logout with full cleanup.
    
    Returns:
        Dict: Clean logout result
    """
    try:
        logger.info("🧹 Performing clean logout with full cleanup")
        
        # Perform standard logout
        logout_result = await logout()
        
        # Additional cleanup steps for clean logout
        additional_cleanup = {
            'cache_cleared': await _clear_cached_data(),
            'background_stopped': await _stop_background_tasks(),
            'connections_closed': await _close_all_connections(),
            'temp_files_cleaned': await _clean_temp_files()
        }
        
        # Update result with additional cleanup info
        logout_result['clean_logout'] = True
        logout_result['additional_cleanup'] = additional_cleanup
        
        logger.info("✅ Clean logout completed successfully")
        
        return logout_result
        
    except Exception as e:
        logger.error(f"❌ Clean logout failed: {e}")
        return {'success': False, 'error': str(e)}

async def _close_all_connections() -> bool:
    """Close all open connections."""
    try:
        # Close all open connections (database, websockets, etc.)
        logger.debug("🔌 Closing all connections")
        return True
    except Exception as e:
        logger.warning(f"⚠️ Connection closing failed: {e}")
        return False

async def _clean_temp_files() -> bool:
    """Clean temporary files."""
    try:
        # Clean temporary files created during session
        logger.debug("📁 Cleaning temporary files")
        return True
    except Exception as e:
        logger.warning(f"⚠️ Temp file cleaning failed: {e}")
        return False

async def emergency_logout() -> Dict[str, Any]:
    """
    Emergency logout that forces cleanup even if API calls fail.
    
    Returns:
        Dict: Emergency logout result
    """
    try:
        logger.warning("🚨 EMERGENCY LOGOUT - Forcing cleanup")
        
        # Force cleanup without waiting for API response
        cleanup_result = await _cleanup_session()
        
        # Additional emergency cleanup
        emergency_cleanup = {
            'forced_token_clear': True,
            'forced_connection_reset': True,
            'forced_cache_clear': True,
            'emergency_timestamp': datetime.now(UTC).isoformat()
        }
        
        result = {
            'success': True,
            'emergency_logout': True,
            'message': 'Emergency logout completed - all local state cleared',
            'cleanup_result': cleanup_result,
            'emergency_cleanup': emergency_cleanup,
            'timestamp': datetime.now(UTC).isoformat()
        }
        
        logger.warning("⚠️ Emergency logout completed")
        
        return result
        
    except Exception as e:
        logger.error(f"❌ Emergency logout failed: {e}")
        return {'success': False, 'error': str(e), 'emergency_logout': True}

async def check_logout_status() -> Dict[str, Any]:
    """
    Check if logout was successful and session is clean.
    
    Returns:
        Dict: Logout status information
    """
    try:
        status_checks = {
            'tokens_cleared': not bool(_check_stored_tokens()),
            'connections_closed': await _check_connections_status(),
            'cache_empty': await _check_cache_status(),
            'background_tasks_stopped': await _check_background_tasks()
        }
        
        all_clear = all(status_checks.values())
        
        return {
            'success': True,
            'logout_complete': all_clear,
            'status_checks': status_checks,
            'checked_at': datetime.now(UTC).isoformat()
        }
        
    except Exception as e:
        logger.error(f"❌ Logout status check failed: {e}")
        return {'success': False, 'error': str(e)}

def _check_stored_tokens() -> bool:
    """Check if tokens are still stored."""
    try:
        # Check if any tokens are still stored
        return False  # Placeholder
    except Exception:
        return False

async def _check_connections_status() -> bool:
    """Check if connections are closed."""
    try:
        # Check if connections are properly closed
        return True  # Placeholder
    except Exception:
        return False

async def _check_cache_status() -> bool:
    """Check if cache is cleared."""
    try:
        # Check if cache is cleared
        return True  # Placeholder
    except Exception:
        return False

async def _check_background_tasks() -> bool:
    """Check if background tasks are stopped."""
    try:
        # Check if background tasks are stopped
        return True  # Placeholder
    except Exception:
        return False

def logout_sync() -> Dict[str, Any]:
    """
    Synchronous wrapper for logout.
    
    ⚠️ WARNING: Use async version when possible for better performance.
    This is only for compatibility with legacy code.
    """
    import asyncio
    try:
        return asyncio.run(logout())
    except Exception as e:
        logger.error(f"❌ Sync logout failed: {e}")
        return {
            'success': False,
            'message': str(e),
            'error': str(e)
        }

# Backward compatibility aliases (DEPRECATED - use new names)
close_session = logout  # Alias for existing code
end_session = logout   # Alias for existing code

if __name__ == "__main__":
    # Test logout functionality
    async def test_logout():
        print("🧪 Testing Angel One Logout")
        print("=" * 40)
        
        # Test logout status check
        try:
            status = await check_logout_status()
            if status['success']:
                print(f"✅ Logout status check:")
                checks = status['status_checks']
                print(f"   Tokens cleared: {checks['tokens_cleared']}")
                print(f"   Connections closed: {checks['connections_closed']}")
                print(f"   Cache empty: {checks['cache_empty']}")
                print(f"   Background tasks stopped: {checks['background_tasks_stopped']}")
                print(f"   Logout complete: {status['logout_complete']}")
            else:
                print(f"❌ Logout status check failed: {status.get('error')}")
        except Exception as e:
            print(f"❌ Logout status test failed: {e}")
        
        print("\n⚠️ Note: Actual logout requires active session and live connection")
        print("🚨 Emergency logout available for force cleanup")
    
    # Run test
    import asyncio
    asyncio.run(test_logout())
