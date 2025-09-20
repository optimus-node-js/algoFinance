"""
Angel One Logger Service
========================

Comprehensive logging service for Angel One API module with Loguru backend.

Features:
- Scope-based logger organization
- Color-coded console output
- Automatic file rotation and organization
- Database integration with conditional storage
- Performance monitoring and metrics
- Error tracking and alerting
- Session and context management

Author: AI Trading System
"""

from .config import LogScope, LogLevel, logger_config
from .angel_logger import (
    angel_one_logger,
    get_api_logger,
    get_service_logger, 
    get_infrastructure_logger,
    get_testing_logger,
    get_performance_logger,
    get_error_logger
)
from .scope_loggers import (
    ScopeLogger,
    api_methods_logger,
    services_logger,
    infrastructure_logger,
    testing_logger,
    performance_logger,
    error_logger,
    database_logger,
    get_logger,
    log_api_method,
    log_service_operation
)
from .db_handler import db_handler

# Version info
__version__ = "1.0.0"
__author__ = "AI Trading System"

# Export all public components
__all__ = [
    # Core logger service
    'angel_one_logger',
    
    # Scope enumeration
    'LogScope',
    'LogLevel',
    
    # Pre-configured scope loggers
    'api_methods_logger',
    'services_logger', 
    'infrastructure_logger',
    'testing_logger',
    'performance_logger',
    'error_logger',
    'database_logger',
    
    # Logger factories
    'get_api_logger',
    'get_service_logger',
    'get_infrastructure_logger', 
    'get_testing_logger',
    'get_performance_logger',
    'get_error_logger',
    'get_logger',
    
    # Logger class
    'ScopeLogger',
    
    # Decorators
    'log_api_method',
    'log_service_operation',
    
    # Database handler
    'db_handler',
    
    # Configuration
    'logger_config'
]

# Quick setup functions for easy integration
def setup_logger_for_component(scope: LogScope, component: str, session_id: str = None) -> ScopeLogger:
    """
    Quick setup function for component-specific logging.
    
    Args:
        scope: Logging scope (LogScope enum)
        component: Component name
        session_id: Optional session ID
        
    Returns:
        Configured ScopeLogger instance
    """
    logger = get_logger(scope, component)
    
    if session_id:
        logger.set_context(session_id=session_id)
    
    return logger

def configure_database_logging(enabled: bool = True, batch_size: int = 100, batch_timeout: float = 5.0):
    """
    Configure database logging settings.
    
    Args:
        enabled: Whether to enable database logging
        batch_size: Number of logs per batch
        batch_timeout: Timeout for batch processing
    """
    angel_one_logger.configure_database(enabled, batch_size, batch_timeout)

def get_logger_health() -> dict:
    """Get health status of logger service."""
    return angel_one_logger.health_check()

def get_logger_stats() -> dict:
    """Get comprehensive logger statistics."""
    return angel_one_logger.get_comprehensive_stats()

# Initialize logger service on import
try:
    # Log successful import
    infrastructure_logger.info("Angel One Logger Service imported successfully", {
        "version": __version__,
        "scopes_available": [scope.value for scope in LogScope],
        "database_enabled": db_handler.enabled
    })
except Exception as e:
    # Fallback logging if there's an issue
    print(f"Warning: Angel One Logger Service initialization issue: {e}")

# Module-level convenience functions
def log_module_import(module_name: str, scope: LogScope):
    """Log successful module import."""
    logger = get_logger(scope, module_name)
    logger.debug(f"Module {module_name} imported successfully")

def log_module_error(module_name: str, error: Exception, scope: LogScope):
    """Log module import/initialization errors."""
    logger = get_logger(scope, module_name)
    logger.error(f"Module {module_name} initialization failed", error=error)

# Quick usage examples in docstring
"""
Quick Usage Examples:
====================

1. Basic logging with scope:
    from angel_one_api.logger import api_methods_logger
    api_methods_logger.info("API call started", {"method": "get_ltp_data"})

2. Component-specific logger:
    from angel_one_api.logger import get_api_logger
    logger = get_api_logger("get_ltp_data")
    logger.performance("api_call", 0.25, True)

3. With context:
    logger.set_context(session_id="sess123", api_key_id="key1")
    logger.info("Processing request")

4. Error logging:
    try:
        # some operation
        pass
    except Exception as e:
        logger.error("Operation failed", error=e, error_code="API001")

5. Performance timing:
    with logger.timer("complex_operation"):
        # operation code
        pass

6. Database storage control:
    logger.info("Debug message", db_store=False)  # Not stored in DB
    logger.error("Critical error", db_store=True)  # Stored in DB

7. API method decoration:
    @log_api_method("get_ltp_data")
    def get_ltp_data(symbol, token):
        # method implementation
        return result
"""
