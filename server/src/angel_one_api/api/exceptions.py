"""
Exception Handlers
=================

Global exception handlers for Angel One FastAPI service.
Provides consistent error responses and comprehensive error logging.
"""

import traceback
from datetime import datetime, UTC
from typing import Union, Dict, Any
from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError, ResponseValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from pydantic import ValidationError

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from logger import get_infrastructure_logger
from config.settings import settings

logger = get_infrastructure_logger("exception_handlers")

class AngelOneAPIException(Exception):
    """Base exception for Angel One API errors."""
    
    def __init__(
        self, 
        message: str, 
        error_code: str = "ANGEL_ONE_ERROR",
        status_code: int = 500,
        details: Dict[str, Any] = None
    ):
        self.message = message
        self.error_code = error_code
        self.status_code = status_code
        self.details = details or {}
        super().__init__(self.message)

class AuthenticationException(AngelOneAPIException):
    """Authentication related errors."""
    
    def __init__(self, message: str, details: Dict[str, Any] = None):
        super().__init__(
            message=message,
            error_code="AUTH_ERROR",
            status_code=401,
            details=details
        )

class RateLimitException(AngelOneAPIException):
    """Rate limiting errors."""
    
    def __init__(self, message: str, retry_after: int = 60, details: Dict[str, Any] = None):
        super().__init__(
            message=message,
            error_code="RATE_LIMIT_ERROR",
            status_code=429,
            details=details or {"retry_after": retry_after}
        )

class ValidationException(AngelOneAPIException):
    """Data validation errors."""
    
    def __init__(self, message: str, validation_errors: list = None):
        super().__init__(
            message=message,
            error_code="VALIDATION_ERROR",
            status_code=422,
            details={"validation_errors": validation_errors or []}
        )

class ServiceUnavailableException(AngelOneAPIException):
    """Service unavailable errors."""
    
    def __init__(self, message: str, service: str = None):
        super().__init__(
            message=message,
            error_code="SERVICE_UNAVAILABLE",
            status_code=503,
            details={"service": service}
        )

def create_error_response(
    request: Request,
    error_code: str,
    message: str,
    status_code: int,
    details: Dict[str, Any] = None,
    exception: Exception = None
) -> JSONResponse:
    """
    Create standardized error response.
    
    Args:
        request: FastAPI request object
        error_code: Machine-readable error code
        message: Human-readable error message
        status_code: HTTP status code
        details: Additional error details
        exception: Original exception (optional)
        
    Returns:
        JSONResponse: Standardized error response
    """
    
    request_id = getattr(request.state, "request_id", "unknown")
    start_time = getattr(request.state, "start_time", None)
    
    # Calculate response time if available
    response_time_ms = None
    if start_time:
        import time
        response_time_ms = (time.time() - start_time) * 1000
    
    error_response = {
        "success": False,
        "message": message,
        "error_code": error_code,
        "timestamp": datetime.now(UTC).isoformat(),
        "request_id": request_id,
        "path": request.url.path,
        "method": request.method
    }
    
    # Add response time if available
    if response_time_ms:
        error_response["response_time_ms"] = round(response_time_ms, 2)
    
    # Add details if provided
    if details:
        error_response["details"] = details
    
    # Add debug information in development
    if settings.is_development() and exception:
        error_response["debug"] = {
            "exception_type": type(exception).__name__,
            "exception_args": str(exception.args),
            "traceback": traceback.format_exc() if settings.DEBUG else None
        }
    
    # Log error
    log_data = {
        "error_code": error_code,
        "status_code": status_code,
        "request_id": request_id,
        "path": request.url.path,
        "method": request.method,
        "client_ip": request.client.host if request.client else None
    }
    
    if response_time_ms:
        log_data["response_time_ms"] = round(response_time_ms, 2)
    
    if details:
        log_data["details"] = details
    
    logger.error(f"API Error: {message}", log_data)
    
    return JSONResponse(
        status_code=status_code,
        content=error_response,
        headers={
            "X-Error-Code": error_code,
            "X-Request-ID": request_id
        }
    )

async def angel_one_api_exception_handler(request: Request, exc: AngelOneAPIException) -> JSONResponse:
    """Handle Angel One API specific exceptions."""
    
    return create_error_response(
        request=request,
        error_code=exc.error_code,
        message=exc.message,
        status_code=exc.status_code,
        details=exc.details,
        exception=exc
    )

async def authentication_exception_handler(request: Request, exc: AuthenticationException) -> JSONResponse:
    """Handle authentication exceptions."""
    
    return create_error_response(
        request=request,
        error_code=exc.error_code,
        message=exc.message,
        status_code=exc.status_code,
        details=exc.details,
        exception=exc
    )

async def rate_limit_exception_handler(request: Request, exc: RateLimitException) -> JSONResponse:
    """Handle rate limit exceptions."""
    
    response = create_error_response(
        request=request,
        error_code=exc.error_code,
        message=exc.message,
        status_code=exc.status_code,
        details=exc.details,
        exception=exc
    )
    
    # Add rate limit headers
    retry_after = exc.details.get("retry_after", 60)
    response.headers["Retry-After"] = str(retry_after)
    response.headers["X-RateLimit-Remaining"] = "0"
    
    return response

async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """Handle FastAPI HTTP exceptions."""
    
    # Map common HTTP status codes to error codes
    error_code_map = {
        400: "BAD_REQUEST",
        401: "UNAUTHORIZED", 
        403: "FORBIDDEN",
        404: "NOT_FOUND",
        405: "METHOD_NOT_ALLOWED",
        409: "CONFLICT",
        422: "VALIDATION_ERROR",
        429: "RATE_LIMIT_EXCEEDED",
        500: "INTERNAL_SERVER_ERROR",
        502: "BAD_GATEWAY",
        503: "SERVICE_UNAVAILABLE",
        504: "GATEWAY_TIMEOUT"
    }
    
    error_code = error_code_map.get(exc.status_code, f"HTTP_{exc.status_code}")
    
    return create_error_response(
        request=request,
        error_code=error_code,
        message=str(exc.detail),
        status_code=exc.status_code,
        exception=exc
    )

async def starlette_http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    """Handle Starlette HTTP exceptions."""
    
    return create_error_response(
        request=request,
        error_code=f"HTTP_{exc.status_code}",
        message=str(exc.detail),
        status_code=exc.status_code,
        exception=exc
    )

async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """Handle request validation errors."""
    
    # Extract validation error details
    validation_errors = []
    for error in exc.errors():
        validation_errors.append({
            "field": " -> ".join(str(loc) for loc in error["loc"]),
            "message": error["msg"],
            "type": error["type"],
            "input": error.get("input")
        })
    
    return create_error_response(
        request=request,
        error_code="VALIDATION_ERROR",
        message="Request validation failed",
        status_code=422,
        details={"validation_errors": validation_errors},
        exception=exc
    )

async def response_validation_exception_handler(request: Request, exc: ResponseValidationError) -> JSONResponse:
    """Handle response validation errors."""
    
    logger.critical("Response validation error - this should not happen in production", {
        "error": str(exc),
        "path": request.url.path,
        "method": request.method
    })
    
    return create_error_response(
        request=request,
        error_code="RESPONSE_VALIDATION_ERROR",
        message="Internal response validation error",
        status_code=500,
        exception=exc
    )

async def pydantic_validation_exception_handler(request: Request, exc: ValidationError) -> JSONResponse:
    """Handle Pydantic validation errors."""
    
    validation_errors = []
    for error in exc.errors():
        validation_errors.append({
            "field": " -> ".join(str(loc) for loc in error["loc"]),
            "message": error["msg"],
            "type": error["type"]
        })
    
    return create_error_response(
        request=request,
        error_code="DATA_VALIDATION_ERROR",
        message="Data validation failed",
        status_code=422,
        details={"validation_errors": validation_errors},
        exception=exc
    )

async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle all other exceptions."""
    
    # Log full traceback for debugging
    logger.critical("Unhandled exception", {
        "exception_type": type(exc).__name__,
        "exception_message": str(exc),
        "path": request.url.path,
        "method": request.method,
        "traceback": traceback.format_exc()
    })
    
    # Don't expose internal errors in production
    if settings.is_production():
        message = "An internal error occurred"
    else:
        message = f"Internal error: {str(exc)}"
    
    return create_error_response(
        request=request,
        error_code="INTERNAL_ERROR",
        message=message,
        status_code=500,
        exception=exc
    )

def setup_exception_handlers(app):
    """
    Setup all exception handlers for the FastAPI app.
    
    Args:
        app: FastAPI application instance
    """
    
    # Custom exceptions
    app.add_exception_handler(AngelOneAPIException, angel_one_api_exception_handler)
    app.add_exception_handler(AuthenticationException, authentication_exception_handler)
    app.add_exception_handler(RateLimitException, rate_limit_exception_handler)
    
    # Standard HTTP exceptions
    app.add_exception_handler(HTTPException, http_exception_handler)
    app.add_exception_handler(StarletteHTTPException, starlette_http_exception_handler)
    
    # Validation exceptions
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(ResponseValidationError, response_validation_exception_handler)
    app.add_exception_handler(ValidationError, pydantic_validation_exception_handler)
    
    # Generic exception handler (catch-all)
    app.add_exception_handler(Exception, generic_exception_handler)
    
    logger.info("Exception handlers configured", {
        "handlers_count": 8,
        "environment": settings.ENVIRONMENT
    })

# Export exception classes and setup function
__all__ = [
    "AngelOneAPIException",
    "AuthenticationException", 
    "RateLimitException",
    "ValidationException",
    "ServiceUnavailableException",
    "setup_exception_handlers"
]
