"""
FastAPI Dependencies
===================

Dependency injection for Angel One FastAPI service.
Provides centralized access to services and utilities.
"""

import asyncio
from typing import Optional, Dict, Any
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from services.authentication import AuthManager
from rate_limiter.rate_controller import get_rate_controller, AngelOneRateController
from logger import get_infrastructure_logger
from config.settings import settings

logger = get_infrastructure_logger("dependencies")

# Security scheme for JWT tokens
security = HTTPBearer(auto_error=False)

# Global service instances
_auth_manager: Optional[AuthManager] = None
_rate_controller: Optional[AngelOneRateController] = None

def get_auth_manager() -> AuthManager:
    """
    Get the global AuthManager instance.
    
    Returns:
        AuthManager: The authentication manager instance
    """
    global _auth_manager
    
    if _auth_manager is None:
        logger.info("Initializing AuthManager instance")
        _auth_manager = AuthManager()
    
    return _auth_manager

def get_rate_limiter() -> Optional[AngelOneRateController]:
    """
    Get the global rate controller instance.
    
    Returns:
        AngelOneRateController: The rate controller instance or None if disabled
    """
    global _rate_controller
    
    if not settings.RATE_LIMIT_ENABLED:
        return None
    
    if _rate_controller is None:
        logger.info("Initializing rate controller instance")
        _rate_controller = get_rate_controller()
    
    return _rate_controller

async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> Optional[Dict[str, Any]]:
    """
    Get current authenticated user from JWT token.
    
    Args:
        credentials: HTTP authorization credentials
        
    Returns:
        Dict containing user information or None if not authenticated
    """
    if not credentials:
        return None
    
    try:
        # Import JWT utilities
        from auth.jwt import decode_token, TokenData
        
        # Decode and validate token
        token_data = decode_token(credentials.credentials)
        
        return {
            "key_id": token_data.key_id,
            "client_id": token_data.client_id,
            "expires_at": token_data.expires_at
        }
        
    except Exception as e:
        logger.warning("Invalid JWT token provided", {"error": str(e)})
        return None

async def require_authentication(
    current_user: Optional[Dict[str, Any]] = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Require valid authentication for protected endpoints.
    
    Args:
        current_user: Current user information
        
    Returns:
        Dict containing user information
        
    Raises:
        HTTPException: If user is not authenticated
    """
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return current_user

async def check_rate_limit(
    request: Request,
    rate_controller: Optional[AngelOneRateController] = Depends(get_rate_limiter)
) -> bool:
    """
    Check if request is within rate limits.
    
    Args:
        request: FastAPI request object
        rate_controller: Rate controller instance
        
    Returns:
        bool: True if request is allowed
        
    Raises:
        HTTPException: If rate limit is exceeded
    """
    if not rate_controller or not settings.RATE_LIMIT_ENABLED:
        return True
    
    try:
        # Extract client identifier
        client_ip = request.client.host if request.client else "unknown"
        user_agent = request.headers.get("user-agent", "unknown")
        client_id = f"{client_ip}:{user_agent}"
        
        # Check rate limit
        is_allowed = await rate_controller.check_rate_limit(
            endpoint=str(request.url.path),
            client_id=client_id
        )
        
        if not is_allowed:
            logger.warning("Rate limit exceeded", {
                "client_id": client_id,
                "endpoint": str(request.url.path),
                "method": request.method
            })
            
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Rate limit exceeded. Please try again later.",
                headers={
                    "Retry-After": "60",
                    "X-RateLimit-Limit": str(settings.RATE_LIMIT_REQUESTS_PER_MINUTE),
                    "X-RateLimit-Remaining": "0"
                }
            )
        
        return True
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Rate limit check failed", {"error": str(e)})
        # Allow request if rate limit check fails
        return True

async def get_request_context(request: Request) -> Dict[str, Any]:
    """
    Get request context information for logging and monitoring.
    
    Args:
        request: FastAPI request object
        
    Returns:
        Dict containing request context
    """
    return {
        "method": request.method,
        "url": str(request.url),
        "path": request.url.path,
        "client_ip": request.client.host if request.client else None,
        "user_agent": request.headers.get("user-agent"),
        "content_type": request.headers.get("content-type"),
        "request_id": getattr(request.state, "request_id", None),
        "timestamp": asyncio.get_event_loop().time()
    }

class DatabaseSession:
    """Database session dependency."""
    
    def __init__(self):
        self.session = None
    
    async def __call__(self):
        """Get database session."""
        try:
            # Import database utilities
            from database import get_async_session
            
            async with get_async_session() as session:
                yield session
                
        except ImportError:
            # Database not configured
            logger.debug("Database not configured")
            yield None
        except Exception as e:
            logger.error("Database session error", {"error": str(e)})
            yield None

# Database session dependency
get_db_session = DatabaseSession()

class RabbitMQConnection:
    """RabbitMQ connection dependency."""
    
    def __init__(self):
        self.connection = None
    
    async def __call__(self):
        """Get RabbitMQ connection."""
        try:
            if settings.RABBITMQ_URL == "disabled":
                yield None
                return
            
            # Import messaging utilities
            from messaging.connection import get_rabbitmq_connection
            
            if not self.connection:
                self.connection = await get_rabbitmq_connection()
            
            yield self.connection
            
        except ImportError:
            # RabbitMQ not configured
            logger.debug("RabbitMQ not configured")
            yield None
        except Exception as e:
            logger.error("RabbitMQ connection error", {"error": str(e)})
            yield None

# RabbitMQ connection dependency
get_rabbitmq = RabbitMQConnection()

async def validate_angel_one_session(
    auth_manager: AuthManager = Depends(get_auth_manager)
) -> bool:
    """
    Validate that at least one Angel One session is active.
    
    Args:
        auth_manager: Authentication manager instance
        
    Returns:
        bool: True if at least one session is active
        
    Raises:
        HTTPException: If no active sessions
    """
    try:
        status_info = auth_manager.get_auth_status()
        active_keys = status_info.get("active_keys", 0)
        
        if active_keys == 0:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="No active Angel One sessions. Please login first.",
                headers={"X-Retry-After": "60"}
            )
        
        return True
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Session validation failed", {"error": str(e)})
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Session validation error"
        )

async def get_performance_metrics(request: Request) -> Dict[str, Any]:
    """
    Get performance metrics for the current request.
    
    Args:
        request: FastAPI request object
        
    Returns:
        Dict containing performance metrics
    """
    start_time = getattr(request.state, "start_time", asyncio.get_event_loop().time())
    current_time = asyncio.get_event_loop().time()
    
    return {
        "request_start_time": start_time,
        "current_time": current_time,
        "elapsed_time_ms": (current_time - start_time) * 1000,
        "target_response_time_ms": 100  # Target response time
    }

# Health check dependency
async def health_check_dependency() -> Dict[str, Any]:
    """
    Quick health check for dependency injection.
    
    Returns:
        Dict containing basic health information
    """
    return {
        "dependencies_healthy": True,
        "auth_manager_available": _auth_manager is not None,
        "rate_controller_available": _rate_controller is not None,
        "timestamp": asyncio.get_event_loop().time()
    }

# Export commonly used dependencies
__all__ = [
    "get_auth_manager",
    "get_rate_limiter", 
    "get_current_user",
    "require_authentication",
    "check_rate_limit",
    "get_request_context",
    "get_db_session",
    "get_rabbitmq",
    "validate_angel_one_session",
    "get_performance_metrics",
    "health_check_dependency"
]
