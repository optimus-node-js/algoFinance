"""
FastAPI Middleware
=================

Custom middleware for Angel One FastAPI service.
Handles logging, performance monitoring, rate limiting, and security.
"""

import asyncio
import time
import uuid
from typing import Callable, Dict, Any
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response, JSONResponse
from starlette.status import HTTP_500_INTERNAL_SERVER_ERROR, HTTP_429_TOO_MANY_REQUESTS

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from config.settings import settings
from logger import get_infrastructure_logger

logger = get_infrastructure_logger("middleware")

class LoggingMiddleware(BaseHTTPMiddleware):
    """
    Logging middleware for comprehensive request/response logging.
    """
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request with logging."""
        
        # Generate unique request ID
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id
        request.state.start_time = time.time()
        
        # Extract request info
        client_ip = request.client.host if request.client else "unknown"
        user_agent = request.headers.get("user-agent", "unknown")
        method = request.method
        url = str(request.url)
        path = request.url.path
        
        # Log incoming request
        logger.info("📥 Incoming request", {
            "request_id": request_id,
            "method": method,
            "path": path,
            "client_ip": client_ip,
            "user_agent": user_agent,
            "content_type": request.headers.get("content-type"),
            "content_length": request.headers.get("content-length")
        })
        
        try:
            # Process request
            response = await call_next(request)
            
            # Calculate response time
            response_time = (time.time() - request.state.start_time) * 1000
            
            # Add response headers
            response.headers["X-Request-ID"] = request_id
            response.headers["X-Response-Time"] = f"{response_time:.2f}ms"
            
            # Log successful response
            logger.info("📤 Request completed", {
                "request_id": request_id,
                "method": method,
                "path": path,
                "status_code": response.status_code,
                "response_time_ms": round(response_time, 2),
                "content_length": response.headers.get("content-length")
            })
            
            return response
            
        except Exception as e:
            # Calculate response time for error
            response_time = (time.time() - request.state.start_time) * 1000
            
            # Log error
            logger.error("❌ Request failed", {
                "request_id": request_id,
                "method": method,
                "path": path,
                "error": str(e),
                "error_type": type(e).__name__,
                "response_time_ms": round(response_time, 2)
            })
            
            # Return error response
            error_response = JSONResponse(
                status_code=HTTP_500_INTERNAL_SERVER_ERROR,
                content={
                    "success": False,
                    "message": "Internal server error",
                    "request_id": request_id,
                    "error_code": "MIDDLEWARE_001"
                }
            )
            error_response.headers["X-Request-ID"] = request_id
            error_response.headers["X-Response-Time"] = f"{response_time:.2f}ms"
            
            return error_response

class PerformanceMiddleware(BaseHTTPMiddleware):
    """
    Performance monitoring middleware.
    Tracks response times and identifies slow endpoints.
    """
    
    def __init__(self, app, slow_request_threshold_ms: float = 1000):
        super().__init__(app)
        self.slow_request_threshold_ms = slow_request_threshold_ms
        self.performance_stats = {
            "total_requests": 0,
            "slow_requests": 0,
            "average_response_time": 0,
            "fastest_response": float('inf'),
            "slowest_response": 0
        }
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request with performance monitoring."""
        
        start_time = time.time()
        request.state.start_time = start_time
        
        try:
            # Process request
            response = await call_next(request)
            
            # Calculate performance metrics
            end_time = time.time()
            response_time_ms = (end_time - start_time) * 1000
            
            # Update stats
            self.performance_stats["total_requests"] += 1
            
            # Update average (simple moving average)
            current_avg = self.performance_stats["average_response_time"]
            total_requests = self.performance_stats["total_requests"]
            self.performance_stats["average_response_time"] = (
                (current_avg * (total_requests - 1) + response_time_ms) / total_requests
            )
            
            # Update min/max
            if response_time_ms < self.performance_stats["fastest_response"]:
                self.performance_stats["fastest_response"] = response_time_ms
            if response_time_ms > self.performance_stats["slowest_response"]:
                self.performance_stats["slowest_response"] = response_time_ms
            
            # Check for slow request
            if response_time_ms > self.slow_request_threshold_ms:
                self.performance_stats["slow_requests"] += 1
                
                logger.warning("🐌 Slow request detected", {
                    "request_id": getattr(request.state, "request_id", "unknown"),
                    "method": request.method,
                    "path": request.url.path,
                    "response_time_ms": round(response_time_ms, 2),
                    "threshold_ms": self.slow_request_threshold_ms
                })
            
            # Add performance headers
            response.headers["X-Response-Time"] = f"{response_time_ms:.2f}ms"
            response.headers["X-Performance-Target"] = "100ms"
            
            # Performance status header
            if response_time_ms <= 100:
                response.headers["X-Performance-Status"] = "excellent"
            elif response_time_ms <= 500:
                response.headers["X-Performance-Status"] = "good"
            elif response_time_ms <= 1000:
                response.headers["X-Performance-Status"] = "acceptable"
            else:
                response.headers["X-Performance-Status"] = "slow"
            
            return response
            
        except Exception as e:
            # Still track failed requests
            response_time_ms = (time.time() - start_time) * 1000
            self.performance_stats["total_requests"] += 1
            
            logger.error("Performance tracking error", {
                "error": str(e),
                "response_time_ms": round(response_time_ms, 2)
            })
            
            raise

class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Rate limiting middleware for API protection.
    """
    
    def __init__(self, app):
        super().__init__(app)
        self.rate_limit_store = {}  # Simple in-memory store
        self.window_size = 60  # 1 minute window
        self.max_requests = settings.RATE_LIMIT_REQUESTS_PER_MINUTE
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request with rate limiting."""
        
        if not settings.RATE_LIMIT_ENABLED:
            return await call_next(request)
        
        # Skip rate limiting for health checks
        if request.url.path in ["/health/live", "/health/ready", "/ping"]:
            return await call_next(request)
        
        # Get client identifier
        client_ip = request.client.host if request.client else "unknown"
        client_id = f"{client_ip}:{request.url.path}"
        
        current_time = time.time()
        
        # Clean old entries
        cutoff_time = current_time - self.window_size
        
        if client_id in self.rate_limit_store:
            self.rate_limit_store[client_id] = [
                timestamp for timestamp in self.rate_limit_store[client_id]
                if timestamp > cutoff_time
            ]
        else:
            self.rate_limit_store[client_id] = []
        
        # Check rate limit
        current_requests = len(self.rate_limit_store[client_id])
        
        if current_requests >= self.max_requests:
            logger.warning("🛡️ Rate limit exceeded", {
                "client_id": client_id,
                "current_requests": current_requests,
                "max_requests": self.max_requests,
                "window_size": self.window_size
            })
            
            return JSONResponse(
                status_code=HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "success": False,
                    "message": "Rate limit exceeded",
                    "error_code": "RATE_LIMIT_001",
                    "retry_after": self.window_size,
                    "limit": self.max_requests,
                    "window": f"{self.window_size}s"
                },
                headers={
                    "Retry-After": str(self.window_size),
                    "X-RateLimit-Limit": str(self.max_requests),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(int(current_time + self.window_size))
                }
            )
        
        # Add request to store
        self.rate_limit_store[client_id].append(current_time)
        
        # Process request
        response = await call_next(request)
        
        # Add rate limit headers
        remaining = max(0, self.max_requests - len(self.rate_limit_store[client_id]))
        response.headers["X-RateLimit-Limit"] = str(self.max_requests)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Reset"] = str(int(current_time + self.window_size))
        
        return response

class SecurityMiddleware(BaseHTTPMiddleware):
    """
    Security middleware for enhanced protection.
    """
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request with security enhancements."""
        
        # Security headers
        security_headers = {
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY",
            "X-XSS-Protection": "1; mode=block",
            "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
            "Referrer-Policy": "strict-origin-when-cross-origin"
        }
        
        # Check for suspicious patterns
        user_agent = request.headers.get("user-agent", "")
        if any(pattern in user_agent.lower() for pattern in ["bot", "crawler", "spider"]):
            logger.info("🕷️ Bot/crawler detected", {
                "user_agent": user_agent,
                "client_ip": request.client.host if request.client else "unknown",
                "path": request.url.path
            })
        
        # Check content length
        content_length = request.headers.get("content-length")
        if content_length and int(content_length) > 10 * 1024 * 1024:  # 10MB limit
            logger.warning("🚨 Large request detected", {
                "content_length": content_length,
                "client_ip": request.client.host if request.client else "unknown",
                "path": request.url.path
            })
            
            return JSONResponse(
                status_code=413,
                content={
                    "success": False,
                    "message": "Request too large",
                    "error_code": "SECURITY_001"
                }
            )
        
        # Process request
        response = await call_next(request)
        
        # Add security headers
        for header, value in security_headers.items():
            response.headers[header] = value
        
        # Add service identification
        response.headers["X-Service"] = "Angel-One-API"
        response.headers["X-Version"] = settings.VERSION
        
        return response

# Export middleware classes
__all__ = [
    "LoggingMiddleware",
    "PerformanceMiddleware", 
    "RateLimitMiddleware",
    "SecurityMiddleware"
]
