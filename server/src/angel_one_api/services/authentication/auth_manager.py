"""
Enhanced Authentication Manager for FastAPI
==========================================

Central authentication manager with FastAPI integration.
"""

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime, UTC

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent.parent))

from logger import get_service_logger
from authentication.auth_manager import AuthManager as BaseAuthManager

logger = get_service_logger("enhanced_auth_manager")

class AuthenticationError(Exception):
    """Authentication related errors."""
    
    def __init__(self, message: str, error_code: str = "AUTH_ERROR"):
        self.message = message
        self.error_code = error_code
        super().__init__(self.message)

class AuthManager:
    """Enhanced authentication manager for FastAPI service."""
    
    def __init__(self):
        self.base_auth_manager = None
        self.configured_keys: Dict[str, Dict[str, Any]] = {}
        self.active_sessions: Dict[str, Dict[str, Any]] = {}
        self.auto_refresh_enabled = False
        
        logger.info("Enhanced AuthManager initialized for FastAPI service")
    
    def has_configured_keys(self) -> bool:
        """Check if API keys are configured."""
        return len(self.configured_keys) > 0
    
    def configure_api_keys(self, api_keys: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
        """Configure Angel One API keys."""
        try:
            results = {}
            
            for key_config in api_keys:
                key_id = key_config.get("key_id")
                
                # Store configuration (without sensitive data in logs)
                self.configured_keys[key_id] = {
                    "key_id": key_id,
                    "client_id": key_config.get("client_id"),
                    "configured_at": datetime.now(UTC).isoformat()
                }
                
                results[key_id] = {
                    "success": True,
                    "message": "Key configured successfully",
                    "configured_at": datetime.now(UTC).isoformat()
                }
                
                logger.info("API key configured", {
                    "key_id": key_id,
                    "client_id": key_config.get("client_id")
                })
            
            return results
            
        except Exception as e:
            logger.error("Failed to configure API keys", error=e)
            raise AuthenticationError(f"Configuration failed: {str(e)}")
    
    async def auto_login_all_keys(self) -> Dict[str, Dict[str, Any]]:
        """Perform auto-login for all configured keys."""
        try:
            if not self.configured_keys:
                raise AuthenticationError("No API keys configured")
            
            login_results = {}
            
            for key_id, key_config in self.configured_keys.items():
                try:
                    # Simulate login process
                    login_result = await self._login_single_key(key_id)
                    login_results[key_id] = login_result
                    
                except Exception as e:
                    login_results[key_id] = {
                        "success": False,
                        "status": "failed",
                        "message": str(e),
                        "login_time": datetime.now(UTC).isoformat()
                    }
            
            logger.info("Auto-login completed", {
                "total_keys": len(login_results),
                "successful": sum(1 for r in login_results.values() if r.get("success"))
            })
            
            return login_results
            
        except Exception as e:
            logger.error("Auto-login failed", error=e)
            raise AuthenticationError(f"Auto-login failed: {str(e)}")
    
    async def _login_single_key(self, key_id: str) -> Dict[str, Any]:
        """Login a single API key."""
        try:
            # Get the base auth manager if available
            if not self.base_auth_manager:
                from authentication.auth_manager import AuthManager as BaseAuthManager
                self.base_auth_manager = BaseAuthManager()
            
            # For now, simulate successful login
            # In real implementation, this would call the base auth manager
            session_info = {
                "success": True,
                "status": "active",
                "message": "Login successful",
                "session_token": f"session_token_{key_id}",
                "login_time": datetime.now(UTC).isoformat(),
                "expires_at": None  # Would be set by actual login
            }
            
            # Store active session
            self.active_sessions[key_id] = session_info
            
            logger.success("Single key login successful", {"key_id": key_id})
            
            return session_info
            
        except Exception as e:
            logger.error("Single key login failed", error=e, extra={"key_id": key_id})
            raise
    
    def get_auth_status(self) -> Dict[str, Any]:
        """Get basic authentication status."""
        active_keys = len(self.active_sessions)
        total_keys = len(self.configured_keys)
        
        return {
            "authenticated": active_keys > 0,
            "active_keys": active_keys,
            "total_keys": total_keys,
            "success_rate": (active_keys / total_keys * 100) if total_keys > 0 else 0
        }
    
    def get_detailed_auth_status(self) -> Dict[str, Any]:
        """Get detailed authentication status."""
        basic_status = self.get_auth_status()
        
        return {
            **basic_status,
            "sessions": self.active_sessions,
            "auto_refresh_enabled": self.auto_refresh_enabled,
            "last_refresh": None,  # Would be implemented
            "next_refresh": None   # Would be implemented
        }
    
    async def refresh_all_sessions(self) -> Dict[str, Dict[str, Any]]:
        """Refresh all active sessions."""
        try:
            refresh_results = {}
            
            for key_id in self.active_sessions.keys():
                try:
                    # Simulate refresh
                    refresh_results[key_id] = {
                        "success": True,
                        "message": "Session refreshed successfully",
                        "refreshed_at": datetime.now(UTC).isoformat()
                    }
                    
                except Exception as e:
                    refresh_results[key_id] = {
                        "success": False,
                        "message": str(e),
                        "refreshed_at": datetime.now(UTC).isoformat()
                    }
            
            logger.info("Session refresh completed", {
                "total_sessions": len(refresh_results),
                "successful": sum(1 for r in refresh_results.values() if r.get("success"))
            })
            
            return refresh_results
            
        except Exception as e:
            logger.error("Session refresh failed", error=e)
            raise AuthenticationError(f"Session refresh failed: {str(e)}")
    
    async def logout_all_sessions(self) -> Dict[str, Dict[str, Any]]:
        """Logout from all active sessions."""
        try:
            logout_results = {}
            
            for key_id in list(self.active_sessions.keys()):
                try:
                    # Remove from active sessions
                    if key_id in self.active_sessions:
                        del self.active_sessions[key_id]
                    
                    logout_results[key_id] = {
                        "success": True,
                        "message": "Logout successful",
                        "logout_time": datetime.now(UTC).isoformat()
                    }
                    
                except Exception as e:
                    logout_results[key_id] = {
                        "success": False,
                        "message": str(e),
                        "logout_time": datetime.now(UTC).isoformat()
                    }
            
            logger.info("Logout completed", {
                "total_sessions": len(logout_results),
                "successful": sum(1 for r in logout_results.values() if r.get("success"))
            })
            
            return logout_results
            
        except Exception as e:
            logger.error("Logout failed", error=e)
            return {}  # Return empty dict for logout failures
    
    async def setup_auto_refresh(self):
        """Setup automatic session refresh."""
        try:
            self.auto_refresh_enabled = True
            logger.info("Auto-refresh setup completed")
            
        except Exception as e:
            logger.error("Auto-refresh setup failed", error=e)
