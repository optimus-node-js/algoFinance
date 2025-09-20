"""
Angel One Logger Configuration
==============================

Centralized configuration for the Angel One API module logging system.
Defines log levels, colors, formats, and storage settings.

Author: AI Trading System
"""

from enum import Enum
from typing import Dict, Any, Optional
from pathlib import Path
import os

class LogScope(Enum):
    """Logging scopes for different parts of the Angel One module."""
    API_METHODS = "API_METHODS"
    SERVICES = "SERVICES" 
    INFRASTRUCTURE = "INFRASTRUCTURE"
    TESTING = "TESTING"
    ERRORS = "ERRORS"
    PERFORMANCE = "PERFORMANCE"
    DATABASE = "DATABASE"

class LogLevel(Enum):
    """Custom log levels for Angel One operations."""
    TRACE = 5      # Detailed execution flow
    DEBUG = 10     # Development debugging
    INFO = 20      # General information
    SUCCESS = 25   # Successful operations (custom level)
    WARNING = 30   # Warning conditions
    ERROR = 40     # Error conditions
    CRITICAL = 50  # Critical failures

# Color scheme for different scopes
SCOPE_COLORS = {
    LogScope.API_METHODS: "#3498db",      # Blue family
    LogScope.SERVICES: "#2ecc71",         # Green family
    LogScope.INFRASTRUCTURE: "#f39c12",   # Orange/Yellow family
    LogScope.TESTING: "#9b59b6",          # Purple family
    LogScope.ERRORS: "#e74c3c",           # Red family
    LogScope.PERFORMANCE: "#ff7f00",      # Orange family
    LogScope.DATABASE: "#8b4513",         # Brown family
}

# Console color codes for different scopes
CONSOLE_COLORS = {
    LogScope.API_METHODS: "🔵",
    LogScope.SERVICES: "🟢",
    LogScope.INFRASTRUCTURE: "🟡",
    LogScope.TESTING: "🟣",
    LogScope.ERRORS: "🔴",
    LogScope.PERFORMANCE: "🟠",
    LogScope.DATABASE: "🟫",
}

# Log format templates
LOG_FORMATS = {
    "console": "{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {extra[scope_icon]} [{extra[scope]: <12}] {extra[component]: <20} | {message}",
    "file": "{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | [{extra[scope]: <12}] {extra[component]: <20} | {extra[session_id]} | {message}",
    "database": "{time:YYYY-MM-DD HH:mm:ss.SSS} | {level} | {extra[scope]} | {extra[component]} | {extra[session_id]} | {message}",
    "json": '{"timestamp": "{time:YYYY-MM-DD HH:mm:ss.SSS}", "level": "{level}", "scope": "{extra[scope]}", "component": "{extra[component]}", "session_id": "{extra[session_id]}", "message": "{message}", "extra": {extra[extra_data]}}'
}

class LoggerConfig:
    """Centralized logger configuration for Angel One API module."""
    
    def __init__(self):
        # Base paths
        self.base_dir = Path(__file__).parent
        self.logs_dir = self.base_dir / "logs"
        
        # Ensure log directories exist
        self._create_log_directories()
        
        # Default settings
        self.default_level = LogLevel.INFO
        self.console_level = LogLevel.INFO
        self.file_level = LogLevel.DEBUG
        self.database_level = LogLevel.INFO
        
        # File rotation settings
        self.max_file_size = "10 MB"
        self.max_files = 10
        self.rotation_time = "1 day"
        
        # Database settings
        self.database_enabled = True
        self.database_table = "logs_angelone"
        self.batch_size = 100
        self.batch_timeout = 5.0
        
        # Performance settings
        self.async_logging = True
        self.buffer_size = 1000
        self.flush_interval = 1.0
        
        # Context tracking
        self.track_session_id = True
        self.track_api_key_id = True
        self.track_performance = True
        
    def _create_log_directories(self):
        """Create all necessary log directories."""
        directories = [
            self.logs_dir,
            self.logs_dir / "api_methods",
            self.logs_dir / "services", 
            self.logs_dir / "infrastructure",
            self.logs_dir / "testing",
            self.logs_dir / "errors"
        ]
        
        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)
    
    def get_log_file_path(self, scope: LogScope, component: Optional[str] = None) -> Path:
        """Get the log file path for a specific scope and component."""
        if scope == LogScope.API_METHODS:
            base_dir = self.logs_dir / "api_methods"
            if component:
                return base_dir / f"{component}.log"
            return base_dir / "api_methods_main.log"
            
        elif scope == LogScope.SERVICES:
            base_dir = self.logs_dir / "services"
            if component:
                return base_dir / f"{component}.log"
            return base_dir / "services_main.log"
            
        elif scope == LogScope.INFRASTRUCTURE:
            base_dir = self.logs_dir / "infrastructure"
            if component:
                return base_dir / f"{component}.log"
            return base_dir / "infrastructure_main.log"
            
        elif scope == LogScope.TESTING:
            return self.logs_dir / "testing" / "test_execution.log"
            
        elif scope == LogScope.ERRORS:
            base_dir = self.logs_dir / "errors"
            if component:
                return base_dir / f"{component}_errors.log"
            return base_dir / "all_errors.log"
            
        else:
            return self.logs_dir / f"{scope.value.lower()}.log"
    
    def get_scope_config(self, scope: LogScope) -> Dict[str, Any]:
        """Get configuration for a specific scope."""
        return {
            "scope": scope,
            "color": SCOPE_COLORS[scope],
            "console_color": CONSOLE_COLORS[scope],
            "level": self.default_level,
            "console_level": self.console_level,
            "file_level": self.file_level,
            "database_level": self.database_level,
            "log_file": self.get_log_file_path(scope),
            "max_file_size": self.max_file_size,
            "rotation_time": self.rotation_time,
            "max_files": self.max_files
        }
    
    def get_component_config(self, scope: LogScope, component: str) -> Dict[str, Any]:
        """Get configuration for a specific component within a scope."""
        base_config = self.get_scope_config(scope)
        base_config.update({
            "component": component,
            "log_file": self.get_log_file_path(scope, component)
        })
        return base_config

# Global configuration instance
logger_config = LoggerConfig()

# Environment-based overrides
if os.getenv("ANGEL_ONE_LOG_LEVEL"):
    try:
        level = getattr(LogLevel, os.getenv("ANGEL_ONE_LOG_LEVEL").upper())
        logger_config.default_level = level
        logger_config.console_level = level
    except AttributeError:
        pass

if os.getenv("ANGEL_ONE_DB_LOGGING") == "false":
    logger_config.database_enabled = False

if os.getenv("ANGEL_ONE_LOG_DIR"):
    logger_config.logs_dir = Path(os.getenv("ANGEL_ONE_LOG_DIR"))
    logger_config._create_log_directories()
