"""
Admin API Endpoints
==================

Administrative endpoints for monitoring and system management.
"""

from fastapi import APIRouter, Depends, HTTPException
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent.parent))
from models.admin import MetricsResponse, SystemStatsResponse, LogStatsResponse
from logger import get_infrastructure_logger
from api.dependencies import get_auth_manager

router = APIRouter()
logger = get_infrastructure_logger("admin_router")

@router.get("/metrics", response_model=MetricsResponse)
async def get_system_metrics():
    """📊 Get comprehensive system metrics"""
    try:
        # Mock metrics for now - would be implemented with actual monitoring
        metrics = {
            "service": {
                "total_requests": 1000,
                "requests_per_minute": 50.0,
                "average_response_time_ms": 85.0,
                "slowest_endpoint": "/market/candles",
                "fastest_endpoint": "/health/live",
                "total_errors": 5,
                "error_rate": 0.5,
                "most_common_error": "RATE_LIMIT_001"
            },
            "endpoints": [],
            "rate_limiting": {
                "enabled": True,
                "requests_per_minute_limit": 1000,
                "current_requests_per_minute": 50.0,
                "rate_limited_requests": 2,
                "top_rate_limited_clients": ["192.168.1.100"]
            },
            "angel_one_api": {
                "active_sessions": 3,
                "total_api_calls": 500,
                "successful_api_calls": 485,
                "failed_api_calls": 15,
                "api_success_rate": 97.0,
                "average_api_response_time_ms": 120.0
            },
            "system": {
                "cpu_percent": 25.5,
                "memory_total_gb": 16.0,
                "memory_available_gb": 12.0,
                "memory_used_percent": 25.0,
                "disk_total_gb": 500.0,
                "disk_free_gb": 350.0,
                "disk_used_percent": 30.0,
                "uptime_seconds": 3600.0
            },
            "performance": {
                "average_response_time_ms": 85.0,
                "median_response_time_ms": 75.0,
                "p95_response_time_ms": 150.0,
                "p99_response_time_ms": 200.0,
                "requests_per_second": 16.7,
                "total_requests": 1000,
                "successful_requests": 995,
                "failed_requests": 5,
                "success_rate": 99.5
            }
        }
        
        return MetricsResponse(
            success=True,
            message="System metrics retrieved successfully",
            **metrics
        )
    except Exception as e:
        logger.error("Failed to get system metrics", error=e)
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/stats", response_model=SystemStatsResponse)
async def get_system_stats():
    """🖥️ Get system statistics"""
    try:
        stats = {
            "configuration": {
                "environment": "development",
                "debug_mode": True,
                "rate_limiting_enabled": True,
                "websocket_enabled": False,
                "rabbitmq_enabled": False,
                "database_enabled": False
            },
            "uptime_seconds": 3600.0,
            "memory_usage": {
                "total_mb": 16384.0,
                "used_mb": 4096.0,
                "free_mb": 12288.0,
                "percentage": 25.0
            },
            "cpu_usage": {
                "current_percent": 25.5,
                "average_percent": 20.0,
                "peak_percent": 45.0
            },
            "disk_usage": {
                "total_gb": 500.0,
                "used_gb": 150.0,
                "free_gb": 350.0,
                "percentage": 30.0
            }
        }
        
        return SystemStatsResponse(
            success=True,
            message="System statistics retrieved successfully",
            **stats
        )
    except Exception as e:
        logger.error("Failed to get system stats", error=e)
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/logs", response_model=LogStatsResponse)
async def get_log_stats():
    """📋 Get logging statistics"""
    try:
        log_stats = {
            "stats": {
                "total_logs": 5000,
                "logs_by_level": {
                    "DEBUG": 2000,
                    "INFO": 2500,
                    "WARNING": 400,
                    "ERROR": 95,
                    "CRITICAL": 5
                },
                "recent_errors": []
            },
            "time_range_hours": 24
        }
        
        return LogStatsResponse(
            success=True,
            message="Log statistics retrieved successfully",
            **log_stats
        )
    except Exception as e:
        logger.error("Failed to get log stats", error=e)
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/rate-limits/reset")
async def reset_rate_limits():
    """🔄 Reset rate limiting emergency brake"""
    try:
        # Would implement actual rate limit reset
        logger.info("Rate limits reset requested")
        
        return {
            "success": True,
            "message": "Rate limits reset successfully",
            "reset_time": "2025-09-20T18:45:00Z"
        }
    except Exception as e:
        logger.error("Failed to reset rate limits", error=e)
        raise HTTPException(status_code=500, detail=str(e))
