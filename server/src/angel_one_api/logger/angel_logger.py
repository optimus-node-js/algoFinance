"""
Angel One Main Logger Service
=============================

Main logger service for the Angel One API module providing centralized logging
with Loguru backend, scope-based organization, and database integration.

Author: AI Trading System
"""

import asyncio
from typing import Dict, Any, Optional, List, Union
from datetime import datetime, UTC
import os
import sys
from pathlib import Path

# Loguru imports
from loguru import logger as loguru

# Local imports
from .config import LogScope, LogLevel, logger_config
from .scope_loggers import (
    ScopeLogger, get_logger,
    api_methods_logger, services_logger, infrastructure_logger,
    testing_logger, performance_logger, error_logger, database_logger
)
from .db_handler import db_handler

class AngelOneLogger:
    """
    Centralized logger service for Angel One API module.
    
    Features:
    - Scope-based logger management
    - Automatic component detection
    - Database integration with conditional storage
    - Performance monitoring and metrics
    - Error tracking and alerting
    - Session and context management
    """
    
    def __init__(self):
        self.initialized = False
        self.loggers: Dict[str, ScopeLogger] = {}
        self.global_context = {}
        self.session_id = None
        
        # Pre-register scope loggers
        self._register_scope_loggers()
        
        # Initialize Loguru
        self._initialize_loguru()
        
        # Mark as initialized
        self.initialized = True
        
        # Log initialization
        infrastructure_logger.info("Angel One Logger Service initialized", {
            "version": "1.0.0",
            "database_enabled": db_handler.enabled,
            "log_directory": str(logger_config.logs_dir)
        })
    
    def _register_scope_loggers(self):
        """Register all scope loggers."""
        self.loggers = {
            "api_methods": api_methods_logger,
            "services": services_logger,
            "infrastructure": infrastructure_logger,
            "testing": testing_logger,
            "performance": performance_logger,
            "errors": error_logger,
            "database": database_logger
        }
    
    def _initialize_loguru(self):
        """Initialize Loguru with custom configuration."""
        # Remove default handler
        loguru.remove()
        
        # Add console handler with colors
        loguru.add(
            sys.stdout,
            format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {message}",
            level="INFO",
            colorize=True
        )
        
        # Add main log file
        main_log_file = logger_config.logs_dir / "angel_one_main.log"
        loguru.add(
            str(main_log_file),
            format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {extra[scope]: <12} | {extra[component]: <20} | {message}",
            level="DEBUG",
            rotation="10 MB",
            retention="10 days",
            compression="zip"
        )
        
        # Add error log file
        error_log_file = logger_config.logs_dir / "errors" / "all_errors.log"
        loguru.add(
            str(error_log_file),
            format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {extra[scope]: <12} | {extra[component]: <20} | {message}",
            level="WARNING",
            rotation="5 MB",
            retention="30 days"
        )
    
    def get_scope_logger(self, scope: LogScope, component: Optional[str] = None, db_store: bool = True) -> ScopeLogger:
        """
        Get logger for specific scope and component.
        
        Args:
            scope: Logging scope
            component: Component name (auto-detected if None)
            db_store: Default database storage setting
            
        Returns:
            Configured ScopeLogger instance
        """
        # Create unique key for this logger
        key = f"{scope.value}_{component or 'default'}"
        
        if key not in self.loggers:
            # Create new logger for this scope/component
            logger = get_logger(scope, component)
            
            # Set global context
            if self.session_id:
                logger.set_context(session_id=self.session_id)
            
            self.loggers[key] = logger
        
        return self.loggers[key]
    
    def set_global_context(self, session_id: Optional[str] = None, **context):
        """Set global context for all loggers."""
        if session_id:
            self.session_id = session_id
            self.global_context["session_id"] = session_id
        
        self.global_context.update(context)
        
        # Update all existing loggers
        for logger in self.loggers.values():
            logger.set_context(session_id=session_id)
    
    def log_startup(self, component: str, version: str, config: Dict[str, Any]):
        """Log application startup."""
        infrastructure_logger.info(f"Starting {component} v{version}", {
            "component": component,
            "version": version,
            "config": config,
            "startup_time": datetime.now(UTC).isoformat()
        })
    
    def log_shutdown(self, component: str, reason: str = "normal"):
        """Log application shutdown."""
        infrastructure_logger.info(f"Shutting down {component}", {
            "component": component,
            "reason": reason,
            "shutdown_time": datetime.now(UTC).isoformat(),
            "total_logs": sum(logger.stats["total_logs"] for logger in self.loggers.values())
        })
    
    def log_api_call(self, method: str, params: Dict[str, Any], response: Dict[str, Any], 
                     timing: float, api_key_id: str, success: bool = True, db_store: bool = True):
        """
        Log API call with comprehensive context.
        
        Args:
            method: API method name
            params: Call parameters
            response: API response
            timing: Call duration in seconds
            api_key_id: API key used
            success: Whether call was successful
            db_store: Whether to store in database
        """
        logger = self.get_scope_logger(LogScope.API_METHODS, method)
        logger.set_context(api_key_id=api_key_id)
        logger.api_call(method, params, response, timing, success, db_store)
    
    def log_rate_limit_event(self, method: str, api_key_id: str, action: str, 
                             details: Optional[Dict[str, Any]] = None, db_store: bool = True):
        """Log rate limiting events."""
        infrastructure_logger.set_context(api_key_id=api_key_id)
        infrastructure_logger.rate_limit_event(method, api_key_id, action, details, db_store)
    
    def log_service_operation(self, service: str, operation: str, data: Optional[Dict[str, Any]] = None,
                              success: bool = True, duration: Optional[float] = None, db_store: bool = True):
        """Log service operations."""
        logger = self.get_scope_logger(LogScope.SERVICES, service)
        
        if duration is not None:
            logger.performance(f"{service}_{operation}", duration, success, data, db_store)
        
        if success:
            logger.info(f"Service operation: {operation}", data, db_store)
        else:
            logger.error(f"Service operation failed: {operation}", extra=data, db_store=db_store)
    
    def log_error(self, scope: LogScope, component: str, message: str, 
                  error: Optional[Exception] = None, error_code: Optional[str] = None,
                  extra: Optional[Dict[str, Any]] = None, db_store: bool = True):
        """Log errors with enhanced context."""
        logger = self.get_scope_logger(scope, component)
        logger.error(message, error, error_code, extra, db_store)
    
    def log_performance(self, scope: LogScope, component: str, operation: str, 
                        duration: float, success: bool = True, 
                        extra: Optional[Dict[str, Any]] = None, db_store: bool = True):
        """Log performance metrics."""
        logger = self.get_scope_logger(scope, component)
        logger.performance(operation, duration, success, extra, db_store)
    
    def get_comprehensive_stats(self) -> Dict[str, Any]:
        """Get comprehensive statistics for all loggers."""
        stats = {
            "angel_one_logger": {
                "initialized": self.initialized,
                "total_loggers": len(self.loggers),
                "session_id": self.session_id,
                "database_enabled": db_handler.enabled
            },
            "scope_loggers": {},
            "database_handler": db_handler.get_stats() if db_handler else None
        }
        
        # Collect stats from all loggers
        for key, logger in self.loggers.items():
            stats["scope_loggers"][key] = logger.get_stats()
        
        return stats
    
    def health_check(self) -> Dict[str, Any]:
        """Perform health check on logger service."""
        health = {
            "status": "healthy",
            "timestamp": datetime.now(UTC).isoformat(),
            "components": {}
        }
        
        try:
            # Check logger initialization
            health["components"]["logger_service"] = {
                "status": "healthy" if self.initialized else "unhealthy",
                "loggers_count": len(self.loggers)
            }
            
            # Check database handler
            if db_handler:
                db_stats = db_handler.get_stats()
                health["components"]["database_handler"] = {
                    "status": "healthy" if db_stats["worker_alive"] else "degraded",
                    "queue_size": db_stats["queue_size"],
                    "last_error": db_stats.get("last_error")
                }
            
            # Check log directories
            health["components"]["log_directories"] = {
                "status": "healthy" if logger_config.logs_dir.exists() else "unhealthy",
                "path": str(logger_config.logs_dir)
            }
            
            # Overall status
            unhealthy_components = sum(
                1 for comp in health["components"].values() 
                if comp["status"] == "unhealthy"
            )
            
            if unhealthy_components > 0:
                health["status"] = "unhealthy"
            elif any(comp["status"] == "degraded" for comp in health["components"].values()):
                health["status"] = "degraded"
            
        except Exception as e:
            health["status"] = "unhealthy"
            health["error"] = str(e)
        
        return health
    
    def configure_database(self, enabled: bool, batch_size: Optional[int] = None, 
                          batch_timeout: Optional[float] = None):
        """Configure database logging settings."""
        if enabled:
            db_handler.enable()
        else:
            db_handler.disable()
        
        if batch_size is not None:
            db_handler.batch_size = batch_size
        
        if batch_timeout is not None:
            db_handler.batch_timeout = batch_timeout
        
        infrastructure_logger.info("Database logging configured", {
            "enabled": enabled,
            "batch_size": db_handler.batch_size,
            "batch_timeout": db_handler.batch_timeout
        })
    
    def flush_all(self):
        """Flush all pending logs to files and database."""
        # Flush database handler
        if db_handler:
            db_handler.flush()
        
        # Force Loguru to flush
        loguru.complete()
        
        infrastructure_logger.debug("All logs flushed")
    
    def shutdown(self):
        """Shutdown logger service gracefully."""
        infrastructure_logger.info("Shutting down Angel One Logger Service")
        
        # Get final stats
        final_stats = self.get_comprehensive_stats()
        infrastructure_logger.info("Final logger statistics", final_stats)
        
        # Flush all logs
        self.flush_all()
        
        # Shutdown database handler
        if db_handler:
            db_handler.shutdown()
        
        # Remove Loguru handlers
        loguru.remove()

# Global logger service instance
angel_one_logger = AngelOneLogger()

# Convenience functions for easy access
def get_api_logger(component: Optional[str] = None) -> ScopeLogger:
    """Get API methods logger."""
    return angel_one_logger.get_scope_logger(LogScope.API_METHODS, component)

def get_service_logger(component: Optional[str] = None) -> ScopeLogger:
    """Get services logger."""
    return angel_one_logger.get_scope_logger(LogScope.SERVICES, component)

def get_infrastructure_logger(component: Optional[str] = None) -> ScopeLogger:
    """Get infrastructure logger."""
    return angel_one_logger.get_scope_logger(LogScope.INFRASTRUCTURE, component)

def get_testing_logger(component: Optional[str] = None) -> ScopeLogger:
    """Get testing logger."""
    return angel_one_logger.get_scope_logger(LogScope.TESTING, component)

def get_performance_logger(component: Optional[str] = None) -> ScopeLogger:
    """Get performance logger."""
    return angel_one_logger.get_scope_logger(LogScope.PERFORMANCE, component)

def get_error_logger(component: Optional[str] = None) -> ScopeLogger:
    """Get error logger."""
    return angel_one_logger.get_scope_logger(LogScope.ERRORS, component)

# Set up graceful shutdown
import atexit
atexit.register(angel_one_logger.shutdown)
