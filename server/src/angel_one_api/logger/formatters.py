"""
Angel One Logger Formatters
============================

Custom formatters for Angel One API logging with color coding and structured output.
Provides console, file, and JSON formatters for different logging destinations.

Author: AI Trading System
"""

import sys
from typing import Dict, Any, Optional
from loguru._defaults import LOGURU_FORMAT
from .config import LogScope, CONSOLE_COLORS, LOG_FORMATS

class AngelOneFormatter:
    """
    Custom formatter for Angel One logs with scope-based color coding.
    
    Features:
    - Color-coded console output by scope
    - Structured file formatting
    - JSON formatting for structured logging
    - Performance metrics integration
    """
    
    def __init__(self, format_type: str = "console"):
        self.format_type = format_type
        self.colors_enabled = self._check_color_support()
    
    def _check_color_support(self) -> bool:
        """Check if the terminal supports colors."""
        # Check if we're in a terminal that supports colors
        if hasattr(sys.stdout, 'isatty') and sys.stdout.isatty():
            # Windows Terminal, VS Code terminal, etc.
            return True
        return False
    
    def format_console(self, record: Dict[str, Any]) -> str:
        """
        Format log record for colorized console output.
        
        Args:
            record: Log record with extra fields
            
        Returns:
            Formatted string with color codes
        """
        # Ensure record has extra dict
        if "extra" not in record:
            record["extra"] = {}
        
        # Get scope information
        scope = record.get("extra", {}).get("scope", "UNKNOWN")
        component = record.get("extra", {}).get("component", "unknown")
        
        # Get scope icon/color
        try:
            scope_enum = LogScope(scope)
            scope_icon = CONSOLE_COLORS.get(scope_enum, "⚪")
        except (ValueError, KeyError):
            scope_icon = "⚪"
        
        # Add scope icon to extra data
        record["extra"]["scope_icon"] = scope_icon
        
        # Ensure required fields exist
        record["extra"].setdefault("scope", scope)
        record["extra"].setdefault("component", component)
        record["extra"].setdefault("session_id", "unknown")
        
        # Format using template
        base_format = LOG_FORMATS["console"]
        
        # Add color codes if supported
        if self.colors_enabled:
            base_format = self._add_console_colors(base_format, scope)
        
        return base_format
    
    def _add_console_colors(self, format_str: str, scope: str) -> str:
        """Add color codes to console format based on scope."""
        # Color mappings based on scope
        color_map = {
            "API_METHODS": "<blue>",
            "SERVICES": "<green>", 
            "INFRASTRUCTURE": "<yellow>",
            "TESTING": "<magenta>",
            "ERRORS": "<red>",
            "PERFORMANCE": "<cyan>",
            "DATABASE": "<white>"
        }
        
        color = color_map.get(scope, "<white>")
        end_color = "</>"
        
        # Apply color to the entire message
        return f"{color}{format_str}{end_color}"
    
    def format_file(self, record: Dict[str, Any]) -> str:
        """
        Format log record for file output.
        
        Args:
            record: Log record with extra fields
            
        Returns:
            Formatted string for file storage
        """
        # Ensure record has required fields
        if "extra" not in record:
            record["extra"] = {}
        
        record["extra"].setdefault("scope", "UNKNOWN")
        record["extra"].setdefault("component", "unknown")
        record["extra"].setdefault("session_id", "unknown")
        
        return LOG_FORMATS["file"]
    
    def format_json(self, record: Dict[str, Any]) -> str:
        """
        Format log record as JSON for structured logging.
        
        Args:
            record: Log record with extra fields
            
        Returns:
            JSON formatted string
        """
        # Ensure record has required fields
        if "extra" not in record:
            record["extra"] = {}
        
        record["extra"].setdefault("scope", "UNKNOWN")
        record["extra"].setdefault("component", "unknown")
        record["extra"].setdefault("session_id", "unknown")
        record["extra"].setdefault("extra_data", "{}")
        
        return LOG_FORMATS["json"]
    
    def format_database(self, record: Dict[str, Any]) -> str:
        """
        Format log record for database storage.
        
        Args:
            record: Log record with extra fields
            
        Returns:
            Formatted string for database
        """
        # Ensure record has required fields
        if "extra" not in record:
            record["extra"] = {}
        
        record["extra"].setdefault("scope", "UNKNOWN")
        record["extra"].setdefault("component", "unknown")
        record["extra"].setdefault("session_id", "unknown")
        
        return LOG_FORMATS["database"]

class PerformanceFormatter(AngelOneFormatter):
    """
    Specialized formatter for performance logging.
    
    Adds timing information, performance metrics, and operation context.
    """
    
    def format_console(self, record: Dict[str, Any]) -> str:
        """Format performance logs with timing information."""
        # Ensure record has extra dict
        if "extra" not in record:
            record["extra"] = {}
        
        extra = record.get("extra", {})
        
        # Ensure required fields exist
        extra.setdefault("component", "unknown")
        extra.setdefault("perf_icon", "⚡")
        extra.setdefault("status_icon", "ℹ️")
        extra.setdefault("duration_ms", "0.0ms")
        
        # Add performance indicators
        if "duration" in extra:
            duration = extra["duration"]
            if duration < 0.1:
                perf_icon = "⚡"  # Very fast
            elif duration < 0.5:
                perf_icon = "🟢"  # Fast
            elif duration < 1.0:
                perf_icon = "🟡"  # Medium
            elif duration < 2.0:
                perf_icon = "🟠"  # Slow
            else:
                perf_icon = "🔴"  # Very slow
            
            extra["perf_icon"] = perf_icon
            extra["duration_ms"] = f"{duration*1000:.1f}ms"
        
        # Add success/failure indicators
        if "success" in extra:
            extra["status_icon"] = "✅" if extra["success"] else "❌"
        
        # Use performance-specific format
        perf_format = "{time:HH:mm:ss.SSS} | {extra[perf_icon]} {extra[status_icon]} | 🟠 [PERF] {extra[component]: <20} | {extra[duration_ms]: >8} | {message}"
        
        record["extra"] = extra
        return perf_format

class ApiMethodFormatter(AngelOneFormatter):
    """
    Specialized formatter for API method logging.
    
    Adds API-specific context like method name, parameters, and response status.
    """
    
    def format_console(self, record: Dict[str, Any]) -> str:
        """Format API method logs with method context."""
        # Ensure record has extra dict
        if "extra" not in record:
            record["extra"] = {}
        
        extra = record.get("extra", {})
        
        # Ensure required fields exist
        extra.setdefault("component", "unknown")
        extra.setdefault("method_icon", "🔧")
        extra.setdefault("key_indicator", "K?")
        
        # Add API method indicators
        if "method_name" in extra:
            method = extra["method_name"]
            # Common method type indicators
            if "get_" in method:
                extra["method_icon"] = "📥"  # Data retrieval
            elif "place_" in method or "modify_" in method or "cancel_" in method:
                extra["method_icon"] = "📤"  # Trading operations
            elif "search_" in method:
                extra["method_icon"] = "🔍"  # Search operations
            else:
                extra["method_icon"] = "🔧"  # Other operations
        
        # Add rate limit context
        if "api_key_id" in extra:
            extra["key_indicator"] = f"K{extra['api_key_id'][-1]}"  # Last digit of key ID
        
        # Use API-specific format
        api_format = "{time:HH:mm:ss.SSS} | {level: <8} | 🔵 [API] {extra[method_icon]} {extra[component]: <15} | {extra[key_indicator]} | {message}"
        
        record["extra"] = extra
        return api_format

class ServiceFormatter(AngelOneFormatter):
    """
    Specialized formatter for service logging.
    
    Adds service-specific context and coordination information.
    """
    
    def format_console(self, record: Dict[str, Any]) -> str:
        """Format service logs with service context."""
        # Ensure record has extra dict
        if "extra" not in record:
            record["extra"] = {}
        
        extra = record.get("extra", {})
        
        # Ensure required fields exist
        extra.setdefault("component", "unknown")
        extra.setdefault("service_icon", "⚙️")
        
        # Add service type indicators
        component = extra.get("component", "")
        if "auth" in component.lower():
            extra["service_icon"] = "🔐"
        elif "market" in component.lower():
            extra["service_icon"] = "📊"
        elif "portfolio" in component.lower():
            extra["service_icon"] = "💰"
        elif "fund" in component.lower():
            extra["service_icon"] = "💳"
        elif "alert" in component.lower():
            extra["service_icon"] = "🚨"
        else:
            extra["service_icon"] = "⚙️"
        
        # Use service-specific format
        service_format = "{time:HH:mm:ss.SSS} | {level: <8} | 🟢 [SVC] {extra[service_icon]} {extra[component]: <15} | {message}"
        
        record["extra"] = extra
        return service_format

class ErrorFormatter(AngelOneFormatter):
    """
    Specialized formatter for error logging.
    
    Adds error context, severity indicators, and troubleshooting information.
    """
    
    def format_console(self, record: Dict[str, Any]) -> str:
        """Format error logs with enhanced error context."""
        # Ensure record has extra dict
        if "extra" not in record:
            record["extra"] = {}
        
        extra = record.get("extra", {})
        level = record.get("level", {}).get("name", "ERROR")
        
        # Ensure required fields exist
        extra.setdefault("component", "unknown")
        extra.setdefault("error_icon", "❌")
        extra.setdefault("severity", "ERR")
        extra.setdefault("error_code_display", "")
        
        # Add error severity indicators
        if level == "CRITICAL":
            extra["error_icon"] = "💥"
            extra["severity"] = "CRIT"
        elif level == "ERROR":
            extra["error_icon"] = "❌"
            extra["severity"] = "ERR"
        elif level == "WARNING":
            extra["error_icon"] = "⚠️"
            extra["severity"] = "WARN"
        else:
            extra["error_icon"] = "ℹ️"
            extra["severity"] = "INFO"
        
        # Add error code if available
        if "error_code" in extra:
            extra["error_code_display"] = f"[{extra['error_code']}]"
        else:
            extra["error_code_display"] = ""
        
        # Use error-specific format
        error_format = "{time:HH:mm:ss.SSS} | {extra[severity]: <4} | 🔴 [ERR] {extra[error_icon]} {extra[component]: <15} | {extra[error_code_display]} {message}"
        
        record["extra"] = extra
        return error_format

# Formatter factory
def get_formatter(scope: LogScope, format_type: str = "console") -> AngelOneFormatter:
    """
    Get appropriate formatter for scope and format type.
    
    Args:
        scope: Logging scope
        format_type: Format type (console, file, json, database)
        
    Returns:
        Appropriate formatter instance
    """
    if scope == LogScope.PERFORMANCE:
        return PerformanceFormatter(format_type)
    elif scope == LogScope.API_METHODS:
        return ApiMethodFormatter(format_type)
    elif scope == LogScope.SERVICES:
        return ServiceFormatter(format_type)
    elif scope == LogScope.ERRORS:
        return ErrorFormatter(format_type)
    else:
        return AngelOneFormatter(format_type)

# Pre-configured formatters for common use cases
console_formatter = AngelOneFormatter("console")
file_formatter = AngelOneFormatter("file")
json_formatter = AngelOneFormatter("json")
database_formatter = AngelOneFormatter("database")
performance_formatter = PerformanceFormatter("console")
api_formatter = ApiMethodFormatter("console")
service_formatter = ServiceFormatter("console")
error_formatter = ErrorFormatter("console")
