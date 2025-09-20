"""
Angel One Scope-Specific Loggers
=================================

Pre-configured loggers for each development scope in the Angel One API module.
Provides easy-to-use logger instances with appropriate formatting and handlers.

Author: AI Trading System
"""

from typing import Dict, Any, Optional, Union
from datetime import datetime, UTC
import inspect
import asyncio
from contextlib import contextmanager
import time

from .config import LogScope, logger_config
from .handlers import (
    create_console_handler, 
    create_file_handler, 
    create_performance_handler,
    create_error_handler
)

class ScopeLogger:
    """
    Scope-specific logger with integrated console, file, and database logging.
    
    Features:
    - Automatic scope and component detection
    - Performance timing integration
    - Error handling with context
    - Database storage with conditional flag
    - Session and API key context tracking
    """
    
    def __init__(self, scope: LogScope, component: Optional[str] = None):
        self.scope = scope
        self.component = component or self._detect_component()
        
        # Initialize handlers
        self.console_handler = create_console_handler(scope, self.component)
        self.file_handler = create_file_handler(scope, self.component)
        self.performance_handler = create_performance_handler(scope, self.component)
        self.error_handler = create_error_handler(scope, self.component)
        
        # Context tracking
        self._session_id: Optional[str] = None
        self._api_key_id: Optional[str] = None
        
        # Statistics
        self.stats = {
            "total_logs": 0,
            "debug_logs": 0,
            "info_logs": 0,
            "warning_logs": 0,
            "error_logs": 0,
            "critical_logs": 0,
            "performance_logs": 0
        }
    
    def _detect_component(self) -> str:
        """Auto-detect component name from calling code."""
        try:
            frame = inspect.currentframe()
            if frame and frame.f_back and frame.f_back.f_back:
                caller_frame = frame.f_back.f_back
                filename = caller_frame.f_globals.get('__file__', '')
                if filename:
                    import os
                    return os.path.splitext(os.path.basename(filename))[0]
        except:
            pass
        return "unknown"
    
    def set_context(self, session_id: Optional[str] = None, api_key_id: Optional[str] = None):
        """Set logging context for session and API key tracking."""
        if session_id:
            self._session_id = session_id
        if api_key_id:
            self._api_key_id = api_key_id
        
        # Update handler contexts
        for handler in [self.console_handler, self.file_handler, self.performance_handler, self.error_handler]:
            handler.set_session_context(self._session_id, self._api_key_id)
    
    def _log(self, level: str, message: str, extra: Optional[Dict[str, Any]] = None, db_store: bool = True):
        """Internal logging method."""
        # Add context to extra data
        enhanced_extra = {
            "timestamp": datetime.now(UTC).isoformat(),
            "session_id": self._session_id,
            "api_key_id": self._api_key_id,
            **(extra or {})
        }
        
        # Log to console and file
        self.console_handler.log(level, message, enhanced_extra, db_store)
        self.file_handler.log(level, message, enhanced_extra, db_store)
        
        # Update statistics
        self.stats["total_logs"] += 1
        level_key = f"{level.lower()}_logs"
        if level_key not in self.stats:
            self.stats[level_key] = 0
        self.stats[level_key] += 1
    
    def trace(self, message: str, extra: Optional[Dict[str, Any]] = None, db_store: bool = True):
        """Log trace level message (most detailed)."""
        self._log("TRACE", message, extra, db_store)
    
    def debug(self, message: str, extra: Optional[Dict[str, Any]] = None, db_store: bool = True):
        """Log debug level message."""
        self._log("DEBUG", message, extra, db_store)
    
    def info(self, message: str, extra: Optional[Dict[str, Any]] = None, db_store: bool = True):
        """Log info level message."""
        self._log("INFO", message, extra, db_store)
    
    def success(self, message: str, extra: Optional[Dict[str, Any]] = None, db_store: bool = True):
        """Log success message (custom level)."""
        self._log("SUCCESS", message, extra, db_store)
    
    def warning(self, message: str, extra: Optional[Dict[str, Any]] = None, db_store: bool = True):
        """Log warning level message."""
        self._log("WARNING", message, extra, db_store)
    
    def error(self, message: str, error: Optional[Exception] = None, error_code: Optional[str] = None, 
              extra: Optional[Dict[str, Any]] = None, db_store: bool = True):
        """Log error with enhanced error handling."""
        self.error_handler.log_error(message, error, error_code, "ERROR", extra, db_store)
        self.stats["error_logs"] += 1
    
    def critical(self, message: str, error: Optional[Exception] = None, error_code: Optional[str] = None,
                 extra: Optional[Dict[str, Any]] = None, db_store: bool = True):
        """Log critical error with enhanced error handling."""
        self.error_handler.log_error(message, error, error_code, "CRITICAL", extra, db_store)
        self.stats["critical_logs"] += 1
    
    def performance(self, operation: str, duration: float, success: bool = True,
                    extra: Optional[Dict[str, Any]] = None, db_store: bool = True):
        """Log performance metrics."""
        self.performance_handler.log_performance(operation, duration, success, extra, db_store)
        self.stats["performance_logs"] += 1
    
    @contextmanager
    def timer(self, operation: str, extra: Optional[Dict[str, Any]] = None, db_store: bool = True):
        """Context manager for timing operations."""
        start_time = time.time()
        success = True
        try:
            yield
        except Exception as e:
            success = False
            self.error(f"Operation '{operation}' failed", error=e, extra=extra, db_store=db_store)
            raise
        finally:
            duration = time.time() - start_time
            self.performance(operation, duration, success, extra, db_store)
    
    def api_call(self, method: str, params: Optional[Dict[str, Any]] = None, 
                 response: Optional[Dict[str, Any]] = None, timing: Optional[float] = None,
                 success: bool = True, db_store: bool = True):
        """Log API call with standardized format."""
        api_extra = {
            "method_name": method,
            "params": params or {},
            "response_status": "success" if success else "failed",
            "response_size": len(str(response)) if response else 0
        }
        
        if timing is not None:
            api_extra["duration"] = timing
            self.performance(f"api_call_{method}", timing, success, api_extra, db_store)
        
        if success:
            self.info(f"API call {method} completed successfully", api_extra, db_store)
        else:
            self.error(f"API call {method} failed", extra=api_extra, db_store=db_store)
    
    def rate_limit_event(self, method: str, api_key_id: str, action: str, 
                         extra: Optional[Dict[str, Any]] = None, db_store: bool = True):
        """Log rate limiting events."""
        rate_extra = {
            "method_name": method,
            "api_key_id": api_key_id,
            "rate_limit_action": action,
            **(extra or {})
        }
        
        if action in ["blocked", "exceeded"]:
            self.warning(f"Rate limit {action} for {method} on key {api_key_id}", rate_extra, db_store)
        else:
            self.debug(f"Rate limit {action} for {method} on key {api_key_id}", rate_extra, db_store)
    
    def service_event(self, service: str, event: str, data: Optional[Dict[str, Any]] = None,
                      db_store: bool = True):
        """Log service-level events."""
        service_extra = {
            "service_name": service,
            "event_type": event,
            "event_data": data or {}
        }
        
        self.info(f"Service {service}: {event}", service_extra, db_store)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get comprehensive logger statistics."""
        return {
            "scope": self.scope.value,
            "component": self.component,
            "session_id": self._session_id,
            "api_key_id": self._api_key_id,
            "logger_stats": self.stats,
            "console_handler_stats": self.console_handler.get_stats(),
            "file_handler_stats": self.file_handler.get_stats(),
            "performance_stats": self.performance_handler.get_performance_stats(),
            "error_stats": self.error_handler.get_error_stats()
        }

# Pre-configured scope loggers for immediate use
api_methods_logger = ScopeLogger(LogScope.API_METHODS)
services_logger = ScopeLogger(LogScope.SERVICES)
infrastructure_logger = ScopeLogger(LogScope.INFRASTRUCTURE)
testing_logger = ScopeLogger(LogScope.TESTING)
performance_logger = ScopeLogger(LogScope.PERFORMANCE)
error_logger = ScopeLogger(LogScope.ERRORS)
database_logger = ScopeLogger(LogScope.DATABASE)

# Factory function for custom component loggers
def get_logger(scope: LogScope, component: Optional[str] = None, auto_detect: bool = True) -> ScopeLogger:
    """
    Get a logger for specific scope and component.
    
    Args:
        scope: Logging scope
        component: Component name (auto-detected if None and auto_detect=True)
        auto_detect: Whether to auto-detect component from caller
        
    Returns:
        Configured ScopeLogger instance
    """
    if component is None and auto_detect:
        # Auto-detect component from caller
        try:
            frame = inspect.currentframe()
            if frame and frame.f_back:
                caller_frame = frame.f_back
                filename = caller_frame.f_globals.get('__file__', '')
                if filename:
                    import os
                    component = os.path.splitext(os.path.basename(filename))[0]
        except:
            component = "unknown"
    
    return ScopeLogger(scope, component)

# Convenience functions for common logging patterns
def log_api_method(method_name: str, logger: Optional[ScopeLogger] = None):
    """Decorator for automatic API method logging."""
    def decorator(func):
        def wrapper(*args, **kwargs):
            actual_logger = logger or api_methods_logger
            
            with actual_logger.timer(f"api_method_{method_name}"):
                try:
                    result = func(*args, **kwargs)
                    actual_logger.api_call(method_name, kwargs, result, success=True)
                    return result
                except Exception as e:
                    actual_logger.api_call(method_name, kwargs, None, success=False)
                    raise
        return wrapper
    return decorator

def log_service_operation(service_name: str, logger: Optional[ScopeLogger] = None):
    """Decorator for automatic service operation logging."""
    def decorator(func):
        def wrapper(*args, **kwargs):
            actual_logger = logger or services_logger
            
            operation_name = f"{service_name}_{func.__name__}"
            with actual_logger.timer(operation_name):
                try:
                    result = func(*args, **kwargs)
                    actual_logger.service_event(service_name, func.__name__, {"result": "success"})
                    return result
                except Exception as e:
                    actual_logger.service_event(service_name, func.__name__, {"result": "failed", "error": str(e)})
                    raise
        return wrapper
    return decorator

# Global logger instances for easy import
__all__ = [
    'ScopeLogger',
    'api_methods_logger',
    'services_logger', 
    'infrastructure_logger',
    'testing_logger',
    'performance_logger',
    'error_logger',
    'database_logger',
    'get_logger',
    'log_api_method',
    'log_service_operation'
]
