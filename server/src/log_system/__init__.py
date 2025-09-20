"""
Advanced Logging Infrastructure for AI Trading System
====================================================

Comprehensive logging system with:
- Console and file output
- MongoDB storage for analysis
- Real-time progress tracking
- Detailed performance metrics
- Error tracking and alerts

Author: AI Trading System
Version: 1.0.0
"""

# Conditional imports to avoid circular import issues
try:
    from .advanced_logger import AdvancedLogger, LogLevel, create_logger
    ADVANCED_LOGGER_AVAILABLE = True
except ImportError:
    ADVANCED_LOGGER_AVAILABLE = False

try:
    from .progress_tracker import ProgressTracker
    PROGRESS_TRACKER_AVAILABLE = True
except ImportError:
    PROGRESS_TRACKER_AVAILABLE = False

try:
    from .performance_monitor import PerformanceMonitor
    PERFORMANCE_MONITOR_AVAILABLE = True
except ImportError:
    PERFORMANCE_MONITOR_AVAILABLE = False

__all__ = []

# Add to __all__ only if imports were successful
if ADVANCED_LOGGER_AVAILABLE:
    __all__.extend(['AdvancedLogger', 'LogLevel', 'create_logger'])

if PROGRESS_TRACKER_AVAILABLE:
    __all__.append('ProgressTracker')

if PERFORMANCE_MONITOR_AVAILABLE:
    __all__.append('PerformanceMonitor')


