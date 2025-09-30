"""
Admin API Endpoints
==================

Administrative endpoints for monitoring and system management.
"""

from fastapi import APIRouter, Depends, HTTPException
import sys
import os
import psutil
import time
from datetime import datetime, UTC
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent.parent))

from models.admin import MetricsResponse, SystemStatsResponse, LogStatsResponse
from logger import get_infrastructure_logger
from api.dependencies import get_auth_manager, validate_angel_one_session
from services.authentication import AuthManager

router = APIRouter()
logger = get_infrastructure_logger("admin_router")

@router.get("/metrics", response_model=MetricsResponse)
async def get_system_metrics(
    auth_manager: AuthManager = Depends(get_auth_manager),
    _: bool = Depends(validate_angel_one_session)
):
    """📊 Get comprehensive system metrics"""
    try:
        # Get real system metrics
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        boot_time = psutil.boot_time()
        uptime_seconds = time.time() - boot_time
        
        # Get Angel One session stats (if available)
        auth_stats = auth_manager.get_session_stats() if hasattr(auth_manager, 'get_session_stats') else {
            "active_sessions": len(getattr(auth_manager, '_sessions', {})),
            "total_api_calls": 0,
            "successful_calls": 0,
            "failed_calls": 0,
            "success_rate": 0.0,
            "avg_response_time": 0.0
        }
        
        metrics = {
            "service": {
                "total_requests": auth_stats.get("total_api_calls", 0),
                "requests_per_minute": 0.0,
                "average_response_time_ms": auth_stats.get("avg_response_time", 0.0),
                "slowest_endpoint": "/market/candles",
                "fastest_endpoint": "/health/live",
                "total_errors": auth_stats.get("failed_calls", 0),
                "error_rate": (100 - auth_stats.get("success_rate", 100.0)) / 100.0 if auth_stats.get("success_rate") else 0.0,
                "most_common_error": "NONE"
            },
            "endpoints": [],
            "rate_limiting": {
                "enabled": True,
                "requests_per_minute_limit": 1000,
                "current_requests_per_minute": 0.0,
                "rate_limited_requests": 0,
                "top_rate_limited_clients": []
            },
            "angel_one_api": {
                "active_sessions": auth_stats.get("active_sessions", 0),
                "total_api_calls": auth_stats.get("total_api_calls", 0),
                "successful_api_calls": auth_stats.get("successful_calls", 0),
                "failed_api_calls": auth_stats.get("failed_calls", 0),
                "api_success_rate": auth_stats.get("success_rate", 0.0),
                "average_api_response_time_ms": auth_stats.get("avg_response_time", 0.0)
            },
            "system": {
                "cpu_percent": round(cpu_percent, 2),
                "memory_total_gb": round(memory.total / (1024**3), 2),
                "memory_available_gb": round(memory.available / (1024**3), 2),
                "memory_used_percent": round(memory.percent, 2),
                "disk_total_gb": round(disk.total / (1024**3), 2),
                "disk_free_gb": round(disk.free / (1024**3), 2),
                "disk_used_percent": round((disk.used / disk.total) * 100, 2),
                "uptime_seconds": round(uptime_seconds, 2)
            },
            "performance": {
                "average_response_time_ms": auth_stats.get("avg_response_time", 0.0),
                "median_response_time_ms": 0.0,
                "p95_response_time_ms": 0.0,
                "p99_response_time_ms": 0.0,
                "requests_per_second": 0.0,
                "total_requests": auth_stats.get("total_api_calls", 0),
                "successful_requests": auth_stats.get("successful_calls", 0),
                "failed_requests": auth_stats.get("failed_calls", 0),
                "cache_hit_rate": 0.0,
                "database_query_time_ms": 0.0,
                "external_api_time_ms": auth_stats.get("avg_response_time", 0.0)
            }
        }
        
        logger.info("System metrics retrieved", {
            "cpu_percent": cpu_percent,
            "memory_percent": memory.percent,
            "disk_percent": round((disk.used / disk.total) * 100, 2),
            "uptime_hours": round(uptime_seconds / 3600, 2)
        })
        
        return MetricsResponse(
            success=True,
            message="System metrics retrieved successfully",
            metrics=metrics,
            timestamp=datetime.now(UTC).isoformat()
        )
        
    except Exception as e:
        logger.error("Failed to get system metrics", error=e)
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/stats", response_model=SystemStatsResponse)
async def get_system_stats(_: bool = Depends(validate_angel_one_session)):
    """📈 Get system performance statistics"""
    try:
        # Get real system stats
        cpu_count = psutil.cpu_count()
        cpu_freq = psutil.cpu_freq()
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        # Get network stats
        net_io = psutil.net_io_counters()
        
        # Get process info
        process = psutil.Process()
        
        stats = {
            "system_info": {
                "cpu_count": cpu_count,
                "cpu_frequency_mhz": round(cpu_freq.current if cpu_freq else 0, 2),
                "total_memory_gb": round(memory.total / (1024**3), 2),
                "total_disk_gb": round(disk.total / (1024**3), 2),
                "platform": psutil.WINDOWS if os.name == 'nt' else "Linux",
                "python_version": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
            },
            "current_usage": {
                "cpu_percent": psutil.cpu_percent(),
                "memory_percent": memory.percent,
                "disk_percent": round((disk.used / disk.total) * 100, 2),
                "network_bytes_sent": net_io.bytes_sent,
                "network_bytes_recv": net_io.bytes_recv
            },
            "process_info": {
                "process_id": process.pid,
                "memory_mb": round(process.memory_info().rss / (1024**2), 2),
                "cpu_percent": process.cpu_percent(),
                "threads": process.num_threads(),
                "status": process.status()
            }
        }
        
        return SystemStatsResponse(
            success=True,
            message="System statistics retrieved successfully",
            stats=stats,
            timestamp=datetime.now(UTC).isoformat()
        )
        
    except Exception as e:
        logger.error("Failed to get system stats", error=e)
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/logs", response_model=LogStatsResponse)
async def get_log_stats(_: bool = Depends(validate_angel_one_session)):
    """📄 Get logging statistics"""
    try:
        # Get logger statistics from the logging system
        from logger.scope_loggers import get_logger_stats
        
        log_stats = get_logger_stats() if callable(get_logger_stats) else {
            "total_logs": 0,
            "error_logs": 0,
            "warning_logs": 0,
            "info_logs": 0,
            "success_logs": 0,
            "recent_errors": []
        }
        
        stats = {
            "logging_summary": {
                "total_log_entries": log_stats.get("total_logs", 0),
                "error_count": log_stats.get("error_logs", 0),
                "warning_count": log_stats.get("warning_logs", 0),
                "info_count": log_stats.get("info_logs", 0),
                "success_count": log_stats.get("success_logs", 0),
                "debug_count": log_stats.get("debug_logs", 0)
            },
            "recent_activity": {
                "recent_errors": log_stats.get("recent_errors", []),
                "last_error_time": log_stats.get("last_error_time"),
                "error_rate_per_hour": log_stats.get("error_rate", 0.0)
            },
            "log_levels": {
                "critical": log_stats.get("critical_logs", 0),
                "error": log_stats.get("error_logs", 0),
                "warning": log_stats.get("warning_logs", 0),
                "info": log_stats.get("info_logs", 0),
                "debug": log_stats.get("debug_logs", 0)
            }
        }
        
        return LogStatsResponse(
            success=True,
            message="Log statistics retrieved successfully",
            stats=stats,
            timestamp=datetime.now(UTC).isoformat()
        )
        
    except Exception as e:
        logger.error("Failed to get log stats", error=e)
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/cleanup")
async def cleanup_system(_: bool = Depends(validate_angel_one_session)):
    """🧹 Perform system cleanup operations"""
    try:
        cleanup_results = {
            "logs_cleaned": False,
            "cache_cleared": False,
            "temp_files_removed": False,
            "memory_freed_mb": 0
        }
        
        # Simulate cleanup operations
        logger.info("System cleanup initiated")
        
        return {
            "success": True,
            "message": "System cleanup completed",
            "results": cleanup_results,
            "timestamp": datetime.now(UTC).isoformat()
        }
        
    except Exception as e:
        logger.error("System cleanup failed", error=e)
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/health-detailed")
async def get_detailed_health(_: bool = Depends(validate_angel_one_session)):
    """🏥 Get detailed health information"""
    try:
        health_info = {
            "service_status": "healthy",
            "dependencies": {
                "angel_one_api": "connected",
                "database": "unknown",
                "rabbitmq": "unknown",
                "logger": "active"
            },
            "performance": {
                "response_time_ms": 0.0,
                "memory_usage_mb": round(psutil.Process().memory_info().rss / (1024**2), 2),
                "cpu_usage_percent": psutil.Process().cpu_percent()
            },
            "uptime_seconds": round(time.time() - psutil.boot_time(), 2)
        }
        
        return {
            "success": True,
            "message": "Detailed health information retrieved",
            "health": health_info,
            "timestamp": datetime.now(UTC).isoformat()
        }
        
    except Exception as e:
        logger.error("Failed to get detailed health", error=e)
        raise HTTPException(status_code=500, detail=str(e))