"""
Angel One Logger Handlers
==========================

Custom handlers for Angel One API logging including file, console, and database handlers.
Provides async operations and performance optimization for high-volume logging.

Author: AI Trading System
"""

import asyncio
import sys
from pathlib import Path
from typing import Dict, Any, Optional, Callable
from loguru import logger as loguru_logger
import json
from datetime import datetime, UTC

from .config import LogScope, LoggerConfig, logger_config
from .formatters import get_formatter
from .db_handler import db_handler, LogRecord

class AngelOneHandler:
    """
    Base handler for Angel One logging operations.
    
    Provides common functionality for all handler types including
    context management, filtering, and performance tracking.
    """
    
    def __init__(self, scope: LogScope, component: Optional[str] = None):
        self.scope = scope
        self.component = component or "unknown"
        self.config = logger_config.get_component_config(scope, self.component)
        self.stats = {
            "total_logs": 0,
            "errors": 0,
            "last_log_time": None
        }
    
    def _prepare_extra_context(self, extra: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Prepare extra context for logging."""
        context = {
            "scope": self.scope.value,
            "component": self.component,
            "session_id": getattr(self, '_session_id', None),
            "api_key_id": getattr(self, '_api_key_id', None),
            "extra_data": extra or {}
        }
        return context
    
    def set_session_context(self, session_id: str, api_key_id: Optional[str] = None):
        """Set session context for this handler."""
        self._session_id = session_id
        self._api_key_id = api_key_id
    
    def get_stats(self) -> Dict[str, Any]:
        """Get handler statistics."""
        return {
            **self.stats,
            "scope": self.scope.value,
            "component": self.component
        }

class ConsoleHandler(AngelOneHandler):
    """
    Console handler with color-coded output based on scope.
    
    Features:
    - Color-coded output by scope
    - Performance indicators
    - Real-time log streaming
    - Configurable log levels
    """
    
    def __init__(self, scope: LogScope, component: Optional[str] = None):
        super().__init__(scope, component)
        self.formatter = get_formatter(scope, "console")
        self._setup_console_handler()
    
    def _setup_console_handler(self):
        """Setup Loguru console handler with custom formatting."""
        # Remove default handler
        loguru_logger.remove()
        
        # Use a simple default format - the custom formatting will be applied during actual logging
        format_str = "{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {message}"
        
        self.handler_id = loguru_logger.add(
            sys.stdout,
            format=format_str,
            level=self.config["console_level"].value,
            colorize=True,
            filter=self._console_filter
        )
    
    def _console_filter(self, record: Dict[str, Any]) -> bool:
        """Filter logs for console output."""
        # Only show logs from our scope/component
        extra = record.get("extra", {})
        return (
            extra.get("scope") == self.scope.value and
            extra.get("component") == self.component
        )
    
    def log(self, level: str, message: str, extra: Optional[Dict[str, Any]] = None, db_store: bool = True):
        """Log message to console."""
        context = self._prepare_extra_context(extra)
        
        # Update stats
        self.stats["total_logs"] += 1
        self.stats["last_log_time"] = datetime.now(UTC)
        
        # Log with context
        getattr(loguru_logger, level.lower())(message, **context)
        
        # Also log to database if enabled
        if db_store and db_handler.enabled:
            db_handler.log_dict(
                level=level.upper(),
                scope=self.scope.value,
                component=self.component,
                message=message,
                extra_data=extra,
                session_id=context.get("session_id"),
                api_key_id=context.get("api_key_id"),
                db_store=db_store
            )

class FileHandler(AngelOneHandler):
    """
    File handler with automatic rotation and scope-based organization.
    
    Features:
    - Automatic file rotation by size and time
    - Scope-based file organization
    - Async file operations
    - Structured logging format
    """
    
    def __init__(self, scope: LogScope, component: Optional[str] = None):
        super().__init__(scope, component)
        self.formatter = get_formatter(scope, "file")
        self.log_file = self.config["log_file"]
        self._setup_file_handler()
    
    def _setup_file_handler(self):
        """Setup Loguru file handler with rotation."""
        # Ensure log directory exists
        self.log_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Use a simple default format for files
        format_str = "{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {extra[scope]: <12} | {extra[component]: <20} | {message}"
        
        self.handler_id = loguru_logger.add(
            str(self.log_file),
            format=format_str,
            level=self.config["file_level"].value,
            rotation=self.config["max_file_size"],
            retention=self.config["max_files"],
            compression="zip",
            filter=self._file_filter,
            enqueue=True  # Async file operations
        )
    
    def _file_filter(self, record: Dict[str, Any]) -> bool:
        """Filter logs for file output."""
        extra = record.get("extra", {})
        return (
            extra.get("scope") == self.scope.value and
            extra.get("component") == self.component
        )
    
    def log(self, level: str, message: str, extra: Optional[Dict[str, Any]] = None, db_store: bool = True):
        """Log message to file."""
        context = self._prepare_extra_context(extra)
        
        # Update stats
        self.stats["total_logs"] += 1
        self.stats["last_log_time"] = datetime.now(UTC)
        
        # Log with context
        getattr(loguru_logger, level.lower())(message, **context)

class PerformanceHandler(AngelOneHandler):
    """
    Specialized handler for performance logging.
    
    Features:
    - Timing measurement integration
    - Performance metrics collection
    - Operation success/failure tracking
    - Performance threshold alerts
    """
    
    def __init__(self, scope: LogScope, component: Optional[str] = None):
        super().__init__(scope, component)
        self.performance_stats = {
            "total_operations": 0,
            "successful_operations": 0,
            "failed_operations": 0,
            "average_duration": 0.0,
            "max_duration": 0.0,
            "min_duration": float('inf')
        }
    
    def log_performance(self, 
                       operation: str,
                       duration: float,
                       success: bool = True,
                       extra: Optional[Dict[str, Any]] = None,
                       db_store: bool = True):
        """
        Log performance metrics for an operation.
        
        Args:
            operation: Name of the operation
            duration: Duration in seconds
            success: Whether operation was successful
            extra: Additional context data
            db_store: Whether to store in database
        """
        # Update performance stats
        self._update_performance_stats(duration, success)
        
        # Prepare performance context
        perf_context = {
            "operation": operation,
            "duration": duration,
            "success": success,
            "duration_ms": duration * 1000,
            **(extra or {})
        }
        
        # Determine log level based on performance
        level = self._get_performance_level(duration, success)
        
        # Create performance message
        status = "✅" if success else "❌"
        message = f"{status} {operation} completed in {duration*1000:.1f}ms"
        
        # Log performance
        context = self._prepare_extra_context(perf_context)
        
        self.stats["total_logs"] += 1
        self.stats["last_log_time"] = datetime.now(UTC)
        
        # Log to console and file
        getattr(loguru_logger, level.lower())(message, **context)
        
        # Log to database if enabled
        if db_store and db_handler.enabled:
            db_handler.log_dict(
                level=level.upper(),
                scope=LogScope.PERFORMANCE.value,
                component=self.component,
                message=message,
                extra_data=perf_context,
                session_id=context.get("session_id"),
                api_key_id=context.get("api_key_id"),
                db_store=db_store
            )
    
    def _update_performance_stats(self, duration: float, success: bool):
        """Update internal performance statistics."""
        self.performance_stats["total_operations"] += 1
        
        if success:
            self.performance_stats["successful_operations"] += 1
        else:
            self.performance_stats["failed_operations"] += 1
        
        # Update duration stats
        self.performance_stats["max_duration"] = max(
            self.performance_stats["max_duration"], 
            duration
        )
        self.performance_stats["min_duration"] = min(
            self.performance_stats["min_duration"], 
            duration
        )
        
        # Update average duration
        total_ops = self.performance_stats["total_operations"]
        current_avg = self.performance_stats["average_duration"]
        self.performance_stats["average_duration"] = (
            (current_avg * (total_ops - 1) + duration) / total_ops
        )
    
    def _get_performance_level(self, duration: float, success: bool) -> str:
        """Determine log level based on performance."""
        if not success:
            return "ERROR"
        
        if duration < 0.1:
            return "DEBUG"  # Very fast
        elif duration < 0.5:
            return "INFO"   # Fast
        elif duration < 1.0:
            return "INFO"   # Medium
        elif duration < 2.0:
            return "WARNING"  # Slow
        else:
            return "ERROR"    # Very slow
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """Get detailed performance statistics."""
        success_rate = 0.0
        if self.performance_stats["total_operations"] > 0:
            success_rate = (
                self.performance_stats["successful_operations"] /
                self.performance_stats["total_operations"] * 100
            )
        
        return {
            **self.performance_stats,
            "success_rate": success_rate,
            "min_duration": self.performance_stats["min_duration"] if self.performance_stats["min_duration"] != float('inf') else 0.0
        }

class ErrorHandler(AngelOneHandler):
    """
    Specialized handler for error logging and tracking.
    
    Features:
    - Error categorization and tracking
    - Automatic stack trace capture
    - Error frequency monitoring
    - Critical error alerting
    """
    
    def __init__(self, scope: LogScope, component: Optional[str] = None):
        super().__init__(scope, component)
        self.error_stats = {
            "total_errors": 0,
            "critical_errors": 0,
            "error_types": {},
            "last_error": None,
            "error_frequency": {}
        }
    
    def log_error(self,
                  message: str,
                  error: Optional[Exception] = None,
                  error_code: Optional[str] = None,
                  level: str = "ERROR",
                  extra: Optional[Dict[str, Any]] = None,
                  db_store: bool = True):
        """
        Log error with enhanced context and tracking.
        
        Args:
            message: Error message
            error: Exception object if available
            error_code: Error code for categorization
            level: Log level (ERROR, CRITICAL)
            extra: Additional context data
            db_store: Whether to store in database
        """
        # Prepare error context
        error_context = {
            "error_code": error_code,
            "error_type": type(error).__name__ if error else "Unknown",
            "error_message": str(error) if error else message,
            **(extra or {})
        }
        
        # Add stack trace if exception provided
        if error:
            import traceback
            error_context["error_traceback"] = traceback.format_exc()
        
        # Update error statistics
        self._update_error_stats(error_context["error_type"], level)
        
        # Log error
        context = self._prepare_extra_context(error_context)
        
        self.stats["total_logs"] += 1
        self.stats["errors"] += 1
        self.stats["last_log_time"] = datetime.now(UTC)
        
        # Log to console and file
        getattr(loguru_logger, level.lower())(message, **context)
        
        # Log to database if enabled
        if db_store and db_handler.enabled:
            db_handler.log_dict(
                level=level.upper(),
                scope=LogScope.ERRORS.value,
                component=self.component,
                message=message,
                extra_data=error_context,
                session_id=context.get("session_id"),
                api_key_id=context.get("api_key_id"),
                error_traceback=error_context.get("error_traceback"),
                db_store=db_store
            )
    
    def _update_error_stats(self, error_type: str, level: str):
        """Update internal error statistics."""
        self.error_stats["total_errors"] += 1
        
        if level == "CRITICAL":
            self.error_stats["critical_errors"] += 1
        
        # Track error types
        if error_type not in self.error_stats["error_types"]:
            self.error_stats["error_types"][error_type] = 0
        self.error_stats["error_types"][error_type] += 1
        
        # Update last error
        self.error_stats["last_error"] = {
            "type": error_type,
            "level": level,
            "timestamp": datetime.now(UTC).isoformat()
        }
    
    def get_error_stats(self) -> Dict[str, Any]:
        """Get detailed error statistics."""
        return self.error_stats

# Handler factory functions
def create_console_handler(scope: LogScope, component: Optional[str] = None) -> ConsoleHandler:
    """Create a console handler for the specified scope and component."""
    return ConsoleHandler(scope, component)

def create_file_handler(scope: LogScope, component: Optional[str] = None) -> FileHandler:
    """Create a file handler for the specified scope and component."""
    return FileHandler(scope, component)

def create_performance_handler(scope: LogScope, component: Optional[str] = None) -> PerformanceHandler:
    """Create a performance handler for the specified scope and component."""
    return PerformanceHandler(scope, component)

def create_error_handler(scope: LogScope, component: Optional[str] = None) -> ErrorHandler:
    """Create an error handler for the specified scope and component."""
    return ErrorHandler(scope, component)
