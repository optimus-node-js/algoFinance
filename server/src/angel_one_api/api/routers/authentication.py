"""
Authentication API Endpoints
============================

Handles all authentication operations for Angel One API.
Features auto-login, session management, and status monitoring.

Key Features:
- 🔐 Auto-login with all configured API keys
- 📊 Real-time authentication status
- 🔄 Automatic session refresh
- ⚡ Sub-100ms response times
- 🛡️ Secure token management
"""

import asyncio
from datetime import datetime, UTC
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from fastapi.responses import JSONResponse

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent.parent))

from services.authentication import AuthManager, AuthenticationError
from config.settings import settings
from logger import get_api_logger
from models.auth import (
    ConfigureKeysRequest, 
    ConfigureKeysResponse,
    AutoLoginResponse,
    AuthStatusResponse,
    LogoutResponse
)
from api.dependencies import get_auth_manager

router = APIRouter()
logger = get_api_logger("auth_router")

@router.post("/auto-login", response_model=AutoLoginResponse)
async def auto_login(
    background_tasks: BackgroundTasks,
    auth_manager: AuthManager = Depends(get_auth_manager)
):
    """
    🚀 **Auto-Login to Angel One**
    
    Automatically logs in to all configured Angel One API keys.
    This is the primary endpoint for frontend initialization.
    
    **Features:**
    - ✅ Logs in to all configured API keys
    - ✅ Returns detailed status for each key
    - ✅ Handles failures gracefully
    - ✅ Sets up automatic refresh
    
    **Target Response Time**: < 2 seconds
    """
    try:
        start_time = asyncio.get_event_loop().time()
        
        logger.info("🔐 Auto-login requested", {
            "action": "auto_login_start",
            "timestamp": datetime.now(UTC).isoformat()
        })
        
        # Check if API keys are configured
        if not auth_manager.has_configured_keys():
            logger.warning("No API keys configured for auto-login")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No API keys configured. Please configure API keys first."
            )
        
        # Perform auto-login
        login_results = await auth_manager.auto_login_all_keys()
        
        # Calculate metrics
        successful_logins = sum(1 for result in login_results.values() if result.get("success", False))
        total_keys = len(login_results)
        success_rate = (successful_logins / total_keys * 100) if total_keys > 0 else 0
        response_time = (asyncio.get_event_loop().time() - start_time) * 1000
        
        # Determine overall status
        if successful_logins == total_keys:
            overall_status = "success"
            message = f"✅ All {total_keys} API keys logged in successfully"
        elif successful_logins > 0:
            overall_status = "partial_success"
            message = f"⚠️ {successful_logins}/{total_keys} API keys logged in successfully"
        else:
            overall_status = "failure"
            message = f"❌ All {total_keys} API key logins failed"
        
        # Schedule background refresh setup
        if successful_logins > 0:
            background_tasks.add_task(auth_manager.setup_auto_refresh)
        
        # Log results
        logger.info("🔐 Auto-login completed", {
            "overall_status": overall_status,
            "successful_logins": successful_logins,
            "total_keys": total_keys,
            "success_rate": f"{success_rate:.1f}%",
            "response_time_ms": round(response_time, 2)
        })
        
        # Detailed results for each key
        key_details = []
        for key_id, result in login_results.items():
            key_details.append({
                "key_id": key_id,
                "success": result.get("success", False),
                "status": result.get("status", "unknown"),
                "message": result.get("message", "No message"),
                "session_token": "***" if result.get("session_token") else None,
                "login_time": result.get("login_time")
            })
        
        response_data = AutoLoginResponse(
            success=(successful_logins > 0),
            overall_status=overall_status,
            message=message,
            successful_logins=successful_logins,
            total_keys=total_keys,
            success_rate=round(success_rate, 1),
            response_time_ms=round(response_time, 2),
            login_results=key_details,
            auto_refresh_enabled=(successful_logins > 0),
            timestamp=datetime.now(UTC)
        )
        
        # Return appropriate HTTP status
        if overall_status == "success":
            return response_data
        elif overall_status == "partial_success":
            return JSONResponse(content=response_data.dict(), status_code=200)
        else:
            return JSONResponse(content=response_data.dict(), status_code=400)
            
    except AuthenticationError as e:
        logger.error("Authentication error during auto-login", 
                    error=e, 
                    error_code="AUTH001")
        
        return JSONResponse(
            content={
                "success": False,
                "overall_status": "authentication_error",
                "message": f"Authentication failed: {str(e)}",
                "error_code": "AUTH001",
                "timestamp": datetime.now(UTC).isoformat()
            },
            status_code=401
        )
        
    except Exception as e:
        logger.error("Unexpected error during auto-login", 
                    error=e, 
                    error_code="AUTH002")
        
        return JSONResponse(
            content={
                "success": False,
                "overall_status": "error",
                "message": f"Auto-login failed: {str(e)}",
                "error_code": "AUTH002",
                "timestamp": datetime.now(UTC).isoformat()
            },
            status_code=500
        )

@router.get("/status", response_model=AuthStatusResponse)
async def get_auth_status(auth_manager: AuthManager = Depends(get_auth_manager)):
    """
    📊 **Authentication Status**
    
    Returns current authentication status for all API keys.
    Use this endpoint to monitor session health.
    
    **Features:**
    - ✅ Real-time session status
    - ✅ Token expiry information
    - ✅ Performance metrics
    - ✅ Auto-refresh status
    
    **Target Response Time**: < 100ms
    """
    try:
        start_time = asyncio.get_event_loop().time()
        
        # Get detailed status
        status_info = auth_manager.get_detailed_auth_status()
        
        response_time = (asyncio.get_event_loop().time() - start_time) * 1000
        
        response_data = AuthStatusResponse(
            authenticated=status_info.get("authenticated", False),
            active_keys=status_info.get("active_keys", 0),
            total_keys=status_info.get("total_keys", 0),
            success_rate=status_info.get("success_rate", 0.0),
            session_info=status_info.get("sessions", {}),
            auto_refresh_enabled=status_info.get("auto_refresh_enabled", False),
            last_refresh=status_info.get("last_refresh"),
            next_refresh=status_info.get("next_refresh"),
            response_time_ms=round(response_time, 2),
            timestamp=datetime.now(UTC)
        )
        
        logger.debug("Authentication status retrieved", {
            "active_keys": response_data.active_keys,
            "total_keys": response_data.total_keys,
            "response_time_ms": response_data.response_time_ms
        })
        
        return response_data
        
    except Exception as e:
        logger.error("Failed to get authentication status", 
                    error=e, 
                    error_code="AUTH003")
        
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get authentication status: {str(e)}"
        )

@router.post("/configure", response_model=ConfigureKeysResponse)
async def configure_api_keys(
    request: ConfigureKeysRequest,
    auth_manager: AuthManager = Depends(get_auth_manager)
):
    """
    🔧 **Configure API Keys**
    
    Configure Angel One API keys for the service.
    Must be called before auto-login.
    
    **Features:**
    - ✅ Validates API key format
    - ✅ Secure storage
    - ✅ Multiple key support
    - ✅ Configuration verification
    
    **Target Response Time**: < 500ms
    """
    try:
        start_time = asyncio.get_event_loop().time()
        
        logger.info("🔧 API keys configuration requested", {
            "total_keys": len(request.api_keys),
            "action": "configure_keys"
        })
        
        # Validate request
        if not request.api_keys:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="At least one API key configuration is required"
            )
        
        if len(request.api_keys) > 5:  # Angel One limit
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Maximum 5 API keys allowed"
            )
        
        # Configure API keys
        configuration_results = auth_manager.configure_api_keys(request.api_keys)
        
        response_time = (asyncio.get_event_loop().time() - start_time) * 1000
        
        # Count successful configurations
        successful_configs = sum(1 for result in configuration_results.values() 
                               if result.get("success", False))
        
        success = successful_configs > 0
        
        logger.info("🔧 API keys configuration completed", {
            "successful_configs": successful_configs,
            "total_keys": len(request.api_keys),
            "success": success,
            "response_time_ms": round(response_time, 2)
        })
        
        return ConfigureKeysResponse(
            success=success,
            message=f"Configured {successful_configs}/{len(request.api_keys)} API keys successfully",
            total_keys=len(request.api_keys),
            successful_configs=successful_configs,
            configuration_results=configuration_results,
            response_time_ms=round(response_time, 2),
            timestamp=datetime.now(UTC)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("API keys configuration failed", 
                    error=e, 
                    error_code="AUTH004")
        
        raise HTTPException(
            status_code=500,
            detail=f"Configuration failed: {str(e)}"
        )

@router.post("/refresh")
async def refresh_sessions(auth_manager: AuthManager = Depends(get_auth_manager)):
    """
    🔄 **Refresh Sessions**
    
    Manually refresh all active Angel One sessions.
    Useful for ensuring fresh tokens.
    
    **Target Response Time**: < 1 second
    """
    try:
        start_time = asyncio.get_event_loop().time()
        
        logger.info("🔄 Manual session refresh requested")
        
        # Perform refresh
        refresh_results = await auth_manager.refresh_all_sessions()
        
        response_time = (asyncio.get_event_loop().time() - start_time) * 1000
        
        successful_refreshes = sum(1 for result in refresh_results.values() 
                                 if result.get("success", False))
        total_sessions = len(refresh_results)
        
        logger.info("🔄 Session refresh completed", {
            "successful_refreshes": successful_refreshes,
            "total_sessions": total_sessions,
            "response_time_ms": round(response_time, 2)
        })
        
        return {
            "success": successful_refreshes > 0,
            "message": f"Refreshed {successful_refreshes}/{total_sessions} sessions",
            "successful_refreshes": successful_refreshes,
            "total_sessions": total_sessions,
            "refresh_results": refresh_results,
            "response_time_ms": round(response_time, 2),
            "timestamp": datetime.now(UTC).isoformat()
        }
        
    except Exception as e:
        logger.error("Session refresh failed", error=e, error_code="AUTH005")
        
        raise HTTPException(
            status_code=500,
            detail=f"Session refresh failed: {str(e)}"
        )

@router.post("/logout", response_model=LogoutResponse)
async def logout_all_sessions(auth_manager: AuthManager = Depends(get_auth_manager)):
    """
    🚪 **Logout All Sessions**
    
    Logout from all active Angel One sessions.
    Cleans up all tokens and sessions.
    
    **Target Response Time**: < 1 second
    """
    try:
        start_time = asyncio.get_event_loop().time()
        
        logger.info("🚪 Logout from all sessions requested")
        
        # Perform logout
        logout_results = await auth_manager.logout_all_sessions()
        
        response_time = (asyncio.get_event_loop().time() - start_time) * 1000
        
        successful_logouts = sum(1 for result in logout_results.values() 
                               if result.get("success", False))
        total_sessions = len(logout_results)
        
        logger.info("🚪 Logout completed", {
            "successful_logouts": successful_logouts,
            "total_sessions": total_sessions,
            "response_time_ms": round(response_time, 2)
        })
        
        return LogoutResponse(
            success=True,  # Always return success for logout
            message=f"Logged out from {successful_logouts}/{total_sessions} sessions",
            successful_logouts=successful_logouts,
            total_sessions=total_sessions,
            logout_results=logout_results,
            response_time_ms=round(response_time, 2),
            timestamp=datetime.now(UTC)
        )
        
    except Exception as e:
        logger.error("Logout failed", error=e, error_code="AUTH006")
        
        # Even if logout fails, we should return success to clean up client state
        return LogoutResponse(
            success=True,
            message=f"Logout completed with errors: {str(e)}",
            successful_logouts=0,
            total_sessions=0,
            logout_results={},
            response_time_ms=0,
            timestamp=datetime.now(UTC)
        )

@router.get("/health")
async def auth_health_check(auth_manager: AuthManager = Depends(get_auth_manager)):
    """
    💚 **Authentication Health Check**
    
    Quick health check for authentication subsystem.
    Used by monitoring systems.
    
    **Target Response Time**: < 100ms
    """
    try:
        start_time = asyncio.get_event_loop().time()
        
        status_info = auth_manager.get_auth_status()
        response_time = (asyncio.get_event_loop().time() - start_time) * 1000
        
        active_keys = status_info.get("active_keys", 0)
        total_keys = status_info.get("total_keys", 0)
        
        if active_keys > 0:
            health_status = "healthy"
            message = f"{active_keys}/{total_keys} sessions active"
        elif total_keys > 0:
            health_status = "degraded"
            message = f"No active sessions ({total_keys} keys configured)"
        else:
            health_status = "not_configured"
            message = "No API keys configured"
        
        return {
            "status": health_status,
            "message": message,
            "active_sessions": active_keys,
            "total_keys": total_keys,
            "response_time_ms": round(response_time, 2),
            "timestamp": datetime.now(UTC).isoformat()
        }
        
    except Exception as e:
        return {
            "status": "unhealthy",
            "message": f"Health check failed: {str(e)}",
            "response_time_ms": 0,
            "timestamp": datetime.now(UTC).isoformat()
        }
