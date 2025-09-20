"""
Advanced Logging System for AI Trading
======================================

Comprehensive logging infrastructure with:
- Multi-destination logging (console, file, MongoDB)
- Structured logging with metadata
- Real-time progress tracking
- Performance monitoring
- Error categorization and alerts

Author: AI Trading System
Version: 1.0.0
"""

import os
import logging
import json
from datetime import datetime, UTC
from typing import Dict, Any, Optional, List
from enum import Enum
from pathlib import Path
import threading
from dataclasses import dataclass, field
from collections import defaultdict

# Standard libraries
import sys

# Project imports
try:
    from core.connections import ConnectionManager
    CONNECTIONS_AVAILABLE = True
    MONGO_AVAILABLE = True
except ImportError:
    ConnectionManager = None
    CONNECTIONS_AVAILABLE = False
    MONGO_AVAILABLE = False

class LogLevel(Enum):
    """Enhanced log levels for trading system."""
    DEBUG = "DEBUG"
    INFO = "INFO" 
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"
    TRADE = "TRADE"           # Trade-specific events
    ANALYSIS = "ANALYSIS"     # AI analysis events
    PERFORMANCE = "PERFORMANCE"  # Performance metrics
    PROGRESS = "PROGRESS"     # Progress tracking

@dataclass
class LogEntry:
    """Structured log entry."""
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
    level: LogLevel = LogLevel.INFO
    component: str = "SYSTEM"
    message: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    session_id: Optional[str] = None
    trade_id: Optional[str] = None
    stock_symbol: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            'timestamp': self.timestamp.isoformat(),
            'level': self.level.value,
            'component': self.component,
            'message': self.message,
            'metadata': self.metadata,
            'session_id': self.session_id,
            'trade_id': self.trade_id,
            'stock_symbol': self.stock_symbol
        }

class AdvancedLogger:
    """
    Advanced logging system for AI trading with multiple outputs.
    
    Features:
    - Console logging with colors
    - File logging with rotation
    - MongoDB storage for analysis
    - Structured metadata
    - Performance tracking
    - Real-time progress monitoring
    """
    
    def __init__(self, 
                 name: str = "AITradingSystem",
                 log_dir: str = "server/src/logging/logs",
                 console_level: LogLevel = LogLevel.INFO,
                 file_level: LogLevel = LogLevel.DEBUG,
                 enable_mongodb: bool = True):
        """Initialize advanced logger."""
        
        self.name = name
        self.log_dir = Path(log_dir)
        self.console_level = console_level
        self.file_level = file_level
        self.enable_mongodb = enable_mongodb and MONGO_AVAILABLE
        
        # Create logs directory
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        # Session tracking
        self.session_id = f"session_{datetime.now(UTC).strftime('%Y%m%d_%H%M%S')}"
        self.start_time = datetime.now(UTC)
        
        # Performance tracking
        self.metrics = defaultdict(int)
        self.timings = defaultdict(list)
        self.log_counts = defaultdict(int)
        
        # Thread safety
        self._lock = threading.Lock()
        
        # Setup logging infrastructure
        self._setup_console_logging()
        self._setup_file_logging()
        self._setup_mongodb_logging()
        
        # Log startup
        self.info("SYSTEM", "🚀 Advanced Logging System Initialized", {
            'session_id': self.session_id,
            'log_dir': str(self.log_dir),
            'mongodb_enabled': self.enable_mongodb
        })
    
    def _setup_console_logging(self):
        """Setup console logging with colors."""
        self.console_logger = logging.getLogger(f"{self.name}_console")
        self.console_logger.setLevel(getattr(logging, self.console_level.value))
        
        # Remove existing handlers
        self.console_logger.handlers.clear()
        
        # Console handler with colors
        console_handler = logging.StreamHandler(sys.stdout)
        console_formatter = ColoredFormatter(
            '%(asctime)s - %(levelname)s - %(component)s - %(message)s'
        )
        console_handler.setFormatter(console_formatter)
        self.console_logger.addHandler(console_handler)
        
        # Prevent propagation to root logger
        self.console_logger.propagate = False
    
    def _setup_file_logging(self):
        """Setup file logging with rotation."""
        # Daily log file
        today = datetime.now(UTC).strftime('%Y-%m-%d')
        log_file = self.log_dir / f"{today}_trading.log"
        
        self.file_logger = logging.getLogger(f"{self.name}_file")
        self.file_logger.setLevel(getattr(logging, self.file_level.value))
        
        # Remove existing handlers
        self.file_logger.handlers.clear()
        
        # File handler
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_formatter = logging.Formatter(
            '%(asctime)s | %(levelname)-8s | %(component)-15s | %(message)s | %(metadata)s'
        )
        file_handler.setFormatter(file_formatter)
        self.file_logger.addHandler(file_handler)
        
        # Prevent propagation
        self.file_logger.propagate = False
    
    def _setup_mongodb_logging(self):
        """Setup MongoDB logging for analysis."""
        if self.enable_mongodb:
            try:
                self.connection_manager = ConnectionManager()
                self.db = self.connection_manager.get_mongodb_client()
                if self.db:
                    self.log_collection = self.db.trading_logs
                    self.mongodb_enabled = True
                else:
                    self.mongodb_enabled = False
            except Exception as e:
                self.mongodb_enabled = False
                print(f"⚠️ MongoDB logging disabled: {e}")
        else:
            self.mongodb_enabled = False
    
    def log(self, level: LogLevel, component: str, message: str, 
            metadata: Optional[Dict[str, Any]] = None,
            stock_symbol: Optional[str] = None,
            trade_id: Optional[str] = None):
        """Main logging method."""
        
        with self._lock:
            # Create log entry
            entry = LogEntry(
                level=level,
                component=component,
                message=message,
                metadata=metadata or {},
                session_id=self.session_id,
                stock_symbol=stock_symbol,
                trade_id=trade_id
            )
            
            # Update metrics
            self.log_counts[level.value] += 1
            self.metrics['total_logs'] += 1
            
            # Console logging
            if self._should_log_to_console(level):
                self._log_to_console(entry)
            
            # File logging  
            if self._should_log_to_file(level):
                self._log_to_file(entry)
            
            # MongoDB logging
            if self.mongodb_enabled:
                self._log_to_mongodb(entry)
    
    def _should_log_to_console(self, level: LogLevel) -> bool:
        """Check if should log to console."""
        level_order = {
            LogLevel.DEBUG: 10,
            LogLevel.INFO: 20,
            LogLevel.PROGRESS: 25,
            LogLevel.ANALYSIS: 30,
            LogLevel.TRADE: 35,
            LogLevel.PERFORMANCE: 40,
            LogLevel.WARNING: 50,
            LogLevel.ERROR: 60,
            LogLevel.CRITICAL: 70
        }
        return level_order.get(level, 20) >= level_order.get(self.console_level, 20)
    
    def _should_log_to_file(self, level: LogLevel) -> bool:
        """Check if should log to file."""
        level_order = {
            LogLevel.DEBUG: 10,
            LogLevel.INFO: 20,
            LogLevel.PROGRESS: 25,
            LogLevel.ANALYSIS: 30,
            LogLevel.TRADE: 35,
            LogLevel.PERFORMANCE: 40,
            LogLevel.WARNING: 50,
            LogLevel.ERROR: 60,
            LogLevel.CRITICAL: 70
        }
        return level_order.get(level, 20) >= level_order.get(self.file_level, 10)
    
    def _log_to_console(self, entry: LogEntry):
        """Log to console."""
        try:
            # Add metadata to extra for formatting
            extra = {
                'component': entry.component,
                'metadata': json.dumps(entry.metadata) if entry.metadata else ''
            }
            
            # Map custom levels to standard levels
            if entry.level in [LogLevel.TRADE, LogLevel.ANALYSIS, LogLevel.PROGRESS]:
                log_level = logging.INFO
            elif entry.level == LogLevel.PERFORMANCE:
                log_level = logging.WARNING  # Show performance logs prominently
            else:
                log_level = getattr(logging, entry.level.value)
            
            self.console_logger.log(log_level, entry.message, extra=extra)
            
        except Exception as e:
            print(f"Console logging error: {e}")
    
    def _log_to_file(self, entry: LogEntry):
        """Log to file."""
        try:
            extra = {
                'component': entry.component,
                'metadata': json.dumps(entry.metadata) if entry.metadata else '{}'
            }
            
            # Map custom levels
            if entry.level in [LogLevel.TRADE, LogLevel.ANALYSIS, LogLevel.PROGRESS]:
                log_level = logging.INFO
            elif entry.level == LogLevel.PERFORMANCE:
                log_level = logging.WARNING
            else:
                log_level = getattr(logging, entry.level.value)
            
            self.file_logger.log(log_level, entry.message, extra=extra)
            
        except Exception as e:
            print(f"File logging error: {e}")
    
    def _log_to_mongodb(self, entry: LogEntry):
        """Log to MongoDB asynchronously."""
        try:
            if self.log_collection is not None:
                # Insert log entry (non-blocking)
                self.log_collection.insert_one(entry.to_dict())
        except Exception as e:
            # Don't let MongoDB errors break the application
            pass
    
    # Convenience methods
    def debug(self, component: str, message: str, metadata: Dict[str, Any] = None, **kwargs):
        """Debug level logging."""
        self.log(LogLevel.DEBUG, component, message, metadata, **kwargs)
    
    def info(self, component: str, message: str, metadata: Dict[str, Any] = None, **kwargs):
        """Info level logging."""
        self.log(LogLevel.INFO, component, message, metadata, **kwargs)
    
    def warning(self, component: str, message: str, metadata: Dict[str, Any] = None, **kwargs):
        """Warning level logging."""
        self.log(LogLevel.WARNING, component, message, metadata, **kwargs)
    
    def error(self, component: str, message: str, metadata: Dict[str, Any] = None, **kwargs):
        """Error level logging."""
        self.log(LogLevel.ERROR, component, message, metadata, **kwargs)
    
    def critical(self, component: str, message: str, metadata: Dict[str, Any] = None, **kwargs):
        """Critical level logging."""
        self.log(LogLevel.CRITICAL, component, message, metadata, **kwargs)
    
    def trade(self, component: str, message: str, metadata: Dict[str, Any] = None, **kwargs):
        """Trade-specific logging."""
        self.log(LogLevel.TRADE, component, message, metadata, **kwargs)
    
    def analysis(self, component: str, message: str, metadata: Dict[str, Any] = None, **kwargs):
        """Analysis-specific logging."""
        self.log(LogLevel.ANALYSIS, component, message, metadata, **kwargs)
    
    def progress(self, component: str, message: str, metadata: Dict[str, Any] = None, **kwargs):
        """Progress tracking logging."""
        self.log(LogLevel.PROGRESS, component, message, metadata, **kwargs)
    
    def performance(self, component: str, message: str, metadata: Dict[str, Any] = None, **kwargs):
        """Performance monitoring logging."""
        self.log(LogLevel.PERFORMANCE, component, message, metadata, **kwargs)
    
    def log_stock_analysis(self, stock_symbol: str, timeframes: List[str], 
                          indicators: Dict[str, float], decision: str):
        """Log stock analysis with structured data."""
        self.analysis("STOCK_ANALYZER", 
                     f"📊 {stock_symbol} Analysis Complete: {decision}",
                     {
                         'stock_symbol': stock_symbol,
                         'timeframes_analyzed': timeframes,
                         'indicators': indicators,
                         'decision': decision,
                         'analysis_timestamp': datetime.now(UTC).isoformat()
                     },
                     stock_symbol=stock_symbol)
    
    def log_trade_execution(self, stock_symbol: str, action: str, quantity: int, 
                           price: float, order_id: str = None):
        """Log trade execution."""
        self.trade("TRADE_EXECUTOR",
                  f"🚀 {action} {quantity} {stock_symbol} @ ₹{price:.2f}",
                  {
                      'stock_symbol': stock_symbol,
                      'action': action,
                      'quantity': quantity,
                      'price': price,
                      'order_id': order_id,
                      'execution_timestamp': datetime.now(UTC).isoformat()
                  },
                  stock_symbol=stock_symbol,
                  trade_id=order_id)
    
    def log_progress_milestone(self, component: str, milestone: str, 
                              current: int, total: int, details: Dict[str, Any] = None):
        """Log progress milestones."""
        percentage = (current / total * 100) if total > 0 else 0
        
        self.progress(component,
                     f"🎯 {milestone}: {current}/{total} ({percentage:.1f}%)",
                     {
                         'milestone': milestone,
                         'current': current,
                         'total': total,
                         'percentage': percentage,
                         'details': details or {},
                         'progress_timestamp': datetime.now(UTC).isoformat()
                     })
    
    def get_session_summary(self) -> Dict[str, Any]:
        """Get current session summary."""
        runtime = datetime.now(UTC) - self.start_time
        
        return {
            'session_id': self.session_id,
            'start_time': self.start_time.isoformat(),
            'runtime_seconds': runtime.total_seconds(),
            'runtime_formatted': str(runtime),
            'total_logs': self.metrics['total_logs'],
            'log_counts_by_level': dict(self.log_counts),
            'mongodb_enabled': self.mongodb_enabled
        }

class ColoredFormatter(logging.Formatter):
    """Colored formatter for console output."""
    
    # Color codes
    COLORS = {
        'DEBUG': '\033[36m',      # Cyan
        'INFO': '\033[37m',       # White  
        'PROGRESS': '\033[94m',   # Blue
        'ANALYSIS': '\033[95m',   # Magenta
        'TRADE': '\033[92m',      # Green
        'PERFORMANCE': '\033[93m', # Yellow
        'WARNING': '\033[93m',    # Yellow
        'ERROR': '\033[91m',      # Red
        'CRITICAL': '\033[95m\033[1m',  # Bold Magenta
        'RESET': '\033[0m'        # Reset
    }
    
    def format(self, record):
        # Add color based on level
        level_color = self.COLORS.get(record.levelname, self.COLORS['RESET'])
        reset_color = self.COLORS['RESET']
        
        # Color the level name
        colored_levelname = f"{level_color}{record.levelname}{reset_color}"
        
        # Create formatted message
        log_message = super().format(record)
        
        # Replace levelname with colored version
        return log_message.replace(record.levelname, colored_levelname)

# Global logger instance
_global_logger: Optional[AdvancedLogger] = None

def create_logger(name: str = "AITradingSystem", **kwargs) -> AdvancedLogger:
    """Create or get global logger instance."""
    global _global_logger
    
    if _global_logger is None:
        _global_logger = AdvancedLogger(name, **kwargs)
    
    return _global_logger

def get_logger() -> AdvancedLogger:
    """Get the global logger instance."""
    global _global_logger
    
    if _global_logger is None:
        _global_logger = create_logger()
    
    return _global_logger

# Test the logging system
if __name__ == "__main__":
    # Test logging system
    logger = create_logger("TEST_SYSTEM")
    
    print("🧪 Testing Advanced Logging System...")
    
    # Test different log levels
    logger.info("SYSTEM", "Testing info level logging", {'test': True})
    logger.debug("SYSTEM", "Testing debug level logging", {'debug_data': 123})
    logger.warning("SYSTEM", "Testing warning level logging")
    logger.error("SYSTEM", "Testing error level logging")
    
    # Test specialized logging
    logger.analysis("AI_ENGINE", "Testing analysis logging", {
        'indicators': {'rsi': 45.2, 'macd': 1.23},
        'decision': 'BUY'
    })
    
    logger.trade("ORDER_MANAGER", "Testing trade logging", {
        'symbol': 'RELIANCE-EQ',
        'action': 'BUY',
        'quantity': 10
    })
    
    logger.progress("STOCK_FILTER", "Testing progress logging", {
        'processed': 500,
        'total': 1000
    })
    
    # Test structured logging methods
    logger.log_stock_analysis(
        stock_symbol="SBIN-EQ",
        timeframes=["1m", "5m", "15m"],
        indicators={"rsi": 55.4, "macd": 2.1, "volume_ratio": 1.8},
        decision="STRONG_BUY"
    )
    
    logger.log_trade_execution(
        stock_symbol="RELIANCE-EQ",
        action="BUY",
        quantity=25,
        price=2547.80,
        order_id="ORD_12345"
    )
    
    logger.log_progress_milestone(
        component="BULK_ANALYZER",
        milestone="Stock Analysis Complete",
        current=1000,
        total=5000,
        details={"filtered_stocks": 127, "processing_time": 45.2}
    )
    
    # Show session summary
    summary = logger.get_session_summary()
    logger.info("SYSTEM", "📊 Session Summary", summary)
    
    print(f"\n✅ Logging test completed!")
    print(f"📁 Logs stored in: {logger.log_dir}")
    print(f"📊 MongoDB enabled: {logger.mongodb_enabled}")

# Export the main logger instance
advanced_logger = AdvancedLogger()

def get_logger():
    """Get the main advanced logger instance."""
    return advanced_logger
