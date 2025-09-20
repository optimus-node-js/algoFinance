"""
Angel One Authentication Manager
===============================

Central authentication controller that consolidates all auth logic from:
- core/connections.py (SmartAPI client management)
- api_gateway/auth.py (Login procedures)

Features:
- Unified login with multiple API key support
- TOTP-based authentication
- Automatic client management
- Session validation
- Error handling and retry logic
- Integration with rate limiting system

Author: AI Trading System
"""

import time
import asyncio
import pyotp
from typing import Dict, Optional, List, Any
from datetime import datetime, UTC, timedelta
from SmartApi import SmartConnect

# Import our components
from ..rate_limiter.rate_controller import get_rate_controller, rate_limited, APIPriority

# Import new Angel One logger
from ..logger import get_service_logger

logger = get_service_logger("auth_manager")

class AuthenticationError(Exception):
    """Raised when authentication fails."""
    pass

class AuthManager:
    """
    Central authentication controller for Angel One SmartAPI.
    
    Manages multiple API keys, sessions, and client instances with
    automatic failover and session validation.
    """
    
    def __init__(self):
        self._authenticated_clients: Dict[str, SmartConnect] = {}
        self._session_data: Dict[str, Dict[str, Any]] = {}
        self._api_keys: Dict[str, Dict[str, str]] = {}
        self._current_key_index: int = 0
        self._last_auth_time: Dict[str, float] = {}
        self._failed_keys: set = set()
    
    def configure_api_keys(self, api_keys_config: Dict[str, Dict[str, str]]) -> None:
        """
        Configure multiple API keys for authentication.
        
        Args:
            api_keys_config: Dict mapping key names to credential dicts
                Format: {
                    "key1": {
                        "api_key": "...",
                        "client_id": "...", 
                        "password": "...",
                        "totp_secret": "..."
                    }
                }
        """
        self._api_keys = api_keys_config.copy()
        logger.info("API keys configured for authentication", {
            "total_keys": len(self._api_keys),
            "key_names": list(self._api_keys.keys()),
            "action": "configuration_complete"
        })
    
    async def login_all_keys(self) -> Dict[str, bool]:
        """
        Login to all configured API keys.
        
        Returns:
            Dict mapping key names to success status
        """
        if not self._api_keys:
            raise AuthenticationError("No API keys configured. Call configure_api_keys() first.")
        
        results = {}
        
        for key_name, credentials in self._api_keys.items():
            try:
                success = await self.login_single_key(key_name, credentials)
                results[key_name] = success
                
                if success:
                    logger.success("Authentication successful", {
                        "key_name": key_name,
                        "action": "login_success"
                    })
                else:
                    logger.warning("Authentication failed", {
                        "key_name": key_name,
                        "action": "login_failed"
                    })
                    
            except Exception as e:
                logger.error("Authentication error", 
                           error=e, 
                           error_code="AUTH001",
                           extra={
                               "key_name": key_name,
                               "action": "login_error"
                           })
                results[key_name] = False
        
        successful_count = sum(results.values())
        logger.info("Authentication batch complete", {
            "successful_count": successful_count,
            "total_keys": len(self._api_keys),
            "success_rate": f"{(successful_count/len(self._api_keys)*100):.1f}%",
            "action": "batch_complete"
        })
        
        return results
    
    async def login_single_key(self, key_name: str, credentials: Dict[str, str]) -> bool:
        """
        Login to a single API key.
        
        Args:
            key_name: Name identifier for the API key
            credentials: Dict with api_key, client_id, password, totp_secret
            
        Returns:
            bool: Success status
        """
        try:
            api_key = credentials.get('api_key')
            client_id = credentials.get('client_id')
            password = credentials.get('password')
            totp_secret = credentials.get('totp_secret')
            
            if not all([api_key, client_id, password, totp_secret]):
                raise AuthenticationError(f"Missing credentials for {key_name}")
            
            logger.info(f"🔐 Authenticating {key_name}...")
            
            # Create SmartConnect client
            client = SmartConnect(api_key)
            
            # Generate TOTP
            totp = pyotp.TOTP(totp_secret).now()
            
            # Perform login with rate limiting
            session_data = await self._rate_limited_login(client, client_id, password, totp)
            
            if session_data and session_data.get('status') and session_data.get('data'):
                data = session_data['data']
                jwt_token = data.get('jwtToken')
                refresh_token = data.get('refreshToken')
                feed_token = data.get('feedToken')
                
                if jwt_token:
                    # Store client and session data
                    self._authenticated_clients[key_name] = client
                    self._session_data[key_name] = {
                        'jwt_token': jwt_token,
                        'refresh_token': refresh_token,
                        'feed_token': feed_token,
                        'client_code': data.get('clientcode', client_id),
                        'login_time': datetime.now(UTC).isoformat(),
                        'expires_at': (datetime.now(UTC) + timedelta(hours=24)).isoformat()
                    }
                    self._last_auth_time[key_name] = time.time()
                    
                    # Remove from failed keys if present
                    self._failed_keys.discard(key_name)
                    
                    # Store refresh token in client for API calls
                    if refresh_token:
                        client.refreshToken = refresh_token
                    
                    logger.info(f"✅ Login successful: {key_name}")
                    return True
                else:
                    raise AuthenticationError(f"No JWT token received for {key_name}")
            else:
                error_msg = session_data.get('message', 'Unknown login error') if session_data else 'Empty response'
                raise AuthenticationError(f"Login failed for {key_name}: {error_msg}")
                
        except Exception as e:
            logger.error(f"❌ Login failed for {key_name}: {e}")
            self._failed_keys.add(key_name)
            
            # Clean up failed authentication
            if key_name in self._authenticated_clients:
                del self._authenticated_clients[key_name]
            if key_name in self._session_data:
                del self._session_data[key_name]
                
            return False
    
    @rate_limited("login_by_password", APIPriority.CRITICAL)
    async def _rate_limited_login(
        self, 
        client: SmartConnect, 
        client_id: str, 
        password: str, 
        totp: str,
        _rate_limit_permit: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Login with rate limiting applied."""
        try:
            return client.generateSession(client_id, password, totp)
        except Exception as e:
            logger.error(f"❌ SmartAPI login call failed: {e}")
            raise AuthenticationError(f"SmartAPI login failed: {e}")
    
    def get_authenticated_client(self, key_name: Optional[str] = None) -> Optional[SmartConnect]:
        """
        Get an authenticated SmartConnect client.
        
        Args:
            key_name: Specific key name, or None for automatic selection
            
        Returns:
            SmartConnect client or None if no valid client available
        """
        if key_name:
            # Return specific client if requested
            if key_name in self._authenticated_clients:
                if self._is_session_valid(key_name):
                    return self._authenticated_clients[key_name]
                else:
                    logger.warning(f"⚠️ Session expired for {key_name}")
                    return None
            else:
                logger.warning(f"⚠️ No authenticated client for {key_name}")
                return None
        
        # Auto-select best available client
        return self._get_best_available_client()
    
    def _get_best_available_client(self) -> Optional[SmartConnect]:
        """Get the best available authenticated client."""
        valid_clients = []
        
        for key_name, client in self._authenticated_clients.items():
            if self._is_session_valid(key_name) and key_name not in self._failed_keys:
                valid_clients.append((key_name, client))
        
        if not valid_clients:
            logger.warning("⚠️ No valid authenticated clients available")
            return None
        
        # For now, use round-robin selection
        # Future: Could implement load balancing based on rate limits
        self._current_key_index = (self._current_key_index + 1) % len(valid_clients)
        selected_key, selected_client = valid_clients[self._current_key_index]
        
        logger.debug(f"🎯 Selected client: {selected_key}")
        return selected_client
    
    def _is_session_valid(self, key_name: str) -> bool:
        """Check if session is still valid."""
        if key_name not in self._session_data:
            return False
        
        session = self._session_data[key_name]
        expires_at_str = session.get('expires_at')
        
        if not expires_at_str:
            # No expiration info, assume valid for 23 hours from login
            login_time = session.get('login_time')
            if login_time:
                login_dt = datetime.fromisoformat(login_time.replace('Z', '+00:00'))
                expires_at = login_dt + timedelta(hours=23)  # Conservative
                return datetime.now(UTC) < expires_at
            return False
        
        try:
            expires_at = datetime.fromisoformat(expires_at_str.replace('Z', '+00:00'))
            return datetime.now(UTC) < expires_at
        except Exception:
            return False
    
    async def refresh_token(self, key_name: str) -> bool:
        """
        Refresh authentication token for a specific key.
        
        Args:
            key_name: API key name to refresh
            
        Returns:
            bool: Success status
        """
        if key_name not in self._session_data:
            logger.warning(f"⚠️ No session data for {key_name} to refresh")
            return False
        
        session = self._session_data[key_name]
        refresh_token = session.get('refresh_token')
        
        if not refresh_token:
            logger.warning(f"⚠️ No refresh token available for {key_name}")
            return False
        
        try:
            # Use our token manager for refresh
            from .token_manager import TokenManager
            
            token_manager = TokenManager()
            result = await token_manager.refresh_token(refresh_token)
            
            if result['success']:
                # Update session data with new tokens
                new_token_info = result['token_info']
                session.update({
                    'jwt_token': new_token_info['jwt_token'],
                    'refresh_token': new_token_info['refresh_token'],
                    'expires_at': new_token_info['expires_at']
                })
                
                logger.info(f"✅ Token refreshed successfully: {key_name}")
                return True
            else:
                logger.error(f"❌ Token refresh failed for {key_name}: {result.get('error')}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Token refresh error for {key_name}: {e}")
            return False
    
    async def validate_all_sessions(self) -> Dict[str, bool]:
        """
        Validate all current sessions and refresh if needed.
        
        Returns:
            Dict mapping key names to validation status
        """
        results = {}
        
        for key_name in self._authenticated_clients.keys():
            is_valid = self._is_session_valid(key_name)
            
            if not is_valid:
                # Try to refresh
                logger.info(f"🔄 Attempting to refresh expired session: {key_name}")
                refresh_success = await self.refresh_token(key_name)
                results[key_name] = refresh_success
            else:
                results[key_name] = True
        
        valid_count = sum(results.values())
        logger.info(f"🔍 Session validation: {valid_count}/{len(results)} sessions valid")
        
        return results
    
    def get_session_info(self, key_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Get session information.
        
        Args:
            key_name: Specific key name, or None for all sessions
            
        Returns:
            Dict with session information
        """
        if key_name:
            return self._session_data.get(key_name, {})
        
        return {
            'total_clients': len(self._authenticated_clients),
            'valid_sessions': sum(1 for k in self._authenticated_clients.keys() if self._is_session_valid(k)),
            'failed_keys': list(self._failed_keys),
            'sessions': self._session_data.copy()
        }
    
    async def logout(self, key_name: Optional[str] = None) -> bool:
        """
        Logout from one or all sessions.
        
        Args:
            key_name: Specific key to logout, or None for all
            
        Returns:
            bool: Success status
        """
        try:
            if key_name:
                return await self._logout_single_key(key_name)
            else:
                # Logout all keys
                results = []
                for k in list(self._authenticated_clients.keys()):
                    results.append(await self._logout_single_key(k))
                return all(results)
                
        except Exception as e:
            logger.error(f"❌ Logout error: {e}")
            return False
    
    async def _logout_single_key(self, key_name: str) -> bool:
        """Logout a single key."""
        try:
            if key_name in self._authenticated_clients:
                client = self._authenticated_clients[key_name]
                
                # Call logout API with rate limiting
                from ..methods.logout import logout
                logout_result = await logout()
                
                # Clean up local data regardless of API response
                del self._authenticated_clients[key_name]
                if key_name in self._session_data:
                    del self._session_data[key_name]
                if key_name in self._last_auth_time:
                    del self._last_auth_time[key_name]
                
                logger.info(f"🚪 Logged out: {key_name}")
                return logout_result.get('success', True)
            else:
                logger.warning(f"⚠️ No session to logout for {key_name}")
                return True
                
        except Exception as e:
            logger.error(f"❌ Logout error for {key_name}: {e}")
            return False
    
    def get_stats(self) -> Dict[str, Any]:
        """Get authentication manager statistics."""
        return {
            'configured_keys': len(self._api_keys),
            'authenticated_clients': len(self._authenticated_clients),
            'valid_sessions': sum(1 for k in self._authenticated_clients.keys() if self._is_session_valid(k)),
            'failed_keys': len(self._failed_keys),
            'current_key_index': self._current_key_index,
            'uptime_hours': {
                k: (time.time() - auth_time) / 3600 
                for k, auth_time in self._last_auth_time.items()
            }
        }

# Singleton instance for global use
_auth_manager = None

def get_auth_manager() -> AuthManager:
    """Get the global AuthManager instance."""
    global _auth_manager
    if _auth_manager is None:
        _auth_manager = AuthManager()
    return _auth_manager
