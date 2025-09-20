"""
Enhanced Loguru-based Logging System for AI Trading
===================================================

Production-grade logging with:
- Colorized console output with service identification
- Structured file logging with service-specific folders
- MongoDB integration for analytics
- Performance monitoring and metrics
- Real-time progress tracking

Author: AI Trading System
Version: 2.0.0
"""

import os
import sys
import asyncio
import threading
import time
from datetime import datetime, UTC
from typing import Dict, Any, Optional, List, Union
from pathlib import Path
from dataclasses import dataclass, field
from collections import defaultdict
import json

# Enhanced logging with Loguru
from loguru import logger
import logging

# Project imports
try:
    from core.connections import ConnectionManager
    MONGO_AVAILABLE = True
except ImportError:
    MONGO_AVAILABLE = False

@dataclass
class ServiceLogger:
    """Service-specific logger configuration."""
    service_name: str
    log_level: str = "INFO"
    enable_file_logging: bool = True
    enable_mongodb_logging: bool = True
    log_format: str = "{time:YYYY-MM-DD HH:mm:ss.SSS} | {level:8} | {extra[service]:15} | {message}"
    
class EnhancedTradingLogger:
    """
    Enhanced Trading Logger with Loguru
    
    Features:
    - Beautiful colorized console output
    - Service-specific file organization
    - MongoDB analytics integration
    - Performance monitoring
    - Real-time progress tracking
    - Trading-specific log categories
    """
    
    def __init__(self, base_log_dir: str = "server/src/logging/logs"):
        """Initialize the enhanced trading logger."""
        
        self.base_log_dir = Path(base_log_dir)
        self.base_log_dir.mkdir(parents=True, exist_ok=True)
        
        # Session tracking
        self.session_id = f"trading_session_{datetime.now(UTC).strftime('%Y%m%d_%H%M%S')}"
        self.start_time = datetime.now(UTC)
        
        # Service loggers registry
        self.service_loggers: Dict[str, ServiceLogger] = {}
        
        # Performance tracking
        self.metrics = defaultdict(int)
        self.service_metrics = defaultdict(lambda: defaultdict(int))
        
        # MongoDB connection
        self.mongodb_enabled = False
        self.db = None
        self._setup_mongodb()
        
        # Thread safety
        self._lock = threading.Lock()
        
        # Setup default loggers
        self._setup_console_logger()
        self._setup_service_loggers()
        
        # Log startup
        self.info("SYSTEM", "🚀 Enhanced Trading Logger with Loguru initialized", {
            'session_id': self.session_id,
            'log_dir': str(self.base_log_dir),
            'mongodb_enabled': self.mongodb_enabled
        })
    
    def _setup_mongodb(self):
        """Setup MongoDB connection for log analytics."""
        if MONGO_AVAILABLE:
            try:
                self.connection_manager = ConnectionManager()
                self.db = self.connection_manager.get_mongodb_client()
                if self.db:
                    self.log_collection = self.db.trading_logs
                    self.mongodb_enabled = True
            except Exception as e:
                print(f"⚠️ MongoDB logging disabled: {e}")
    
    def _setup_console_logger(self):
        """Setup beautiful console logger with colors."""
        # Remove default logger
        logger.remove()
        
        # Enhanced console format with service identification
        console_format = (
            "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
            "<level>{level: <8}</level> | "
            "<cyan>{extra[service]: <15}</cyan> | "
            "<level>{message}</level>"
        )
        
        # Add colorized console logger
        logger.add(
            sys.stdout,
            format=console_format,
            level="DEBUG",
            colorize=True,
            diagnose=True,
            backtrace=True,
            enqueue=True
        )
    
    def _setup_service_loggers(self):
        """Setup service-specific file loggers."""
        
        # Define trading services
        trading_services = [
            "SYSTEM", "AI_MASTER", "STOCK_DISCOVERY", "TRADE_EXECUTION",
            "RISK_MANAGEMENT", "PORTFOLIO_MANAGER", "MARKET_DATA",
            "PATTERN_RECOGNITION", "VOLATILITY_ANALYZER", "TECHNICAL_INDICATORS",
            "ORDER_MANAGER", "BACKTESTING", "STRATEGY_ENGINE", "MESSAGE_BROKER"
        ]
        
        # Create service-specific loggers
        for service in trading_services:
            self.register_service_logger(service)
    
    def register_service_logger(self, service_name: str, log_level: str = "INFO"):
        """Register a new service logger."""
        
        # Create service directory
        service_dir = self.base_log_dir / service_name.lower()
        service_dir.mkdir(parents=True, exist_ok=True)
        
        # Create service logger
        service_logger = ServiceLogger(
            service_name=service_name,
            log_level=log_level
        )
        
        self.service_loggers[service_name] = service_logger
        
        # Add file logger for this service
        log_file = service_dir / f"{datetime.now().strftime('%Y-%m-%d')}_{service_name.lower()}.log"
        
        file_format = (
            "{time:YYYY-MM-DD HH:mm:ss.SSS} | "
            "{level: <8} | "
            "{extra[service]: <15} | "
            "{message} | "
            "{extra[metadata]}"
        )
        
        logger.add(
            str(log_file),
            format=file_format,
            level=log_level,
            rotation="00:00",  # Rotate at midnight
            retention="30 days",  # Keep logs for 30 days
            compression="zip",  # Compress old logs
            filter=lambda record: record["extra"].get("service") == service_name,
            enqueue=True
        )
        
        return service_logger
    
    def _log_to_mongodb(self, service: str, level: str, message: str, metadata: Dict = None):
        """Log to MongoDB for analytics."""
        if not self.mongodb_enabled:
            return
        
        try:
            log_entry = {
                'timestamp': datetime.now(UTC),
                'session_id': self.session_id,
                'service': service,
                'level': level,
                'message': message,
                'metadata': metadata or {},
                'log_id': f"{service}_{int(time.time()*1000)}"
            }
            
            # Insert asynchronously
            self.log_collection.insert_one(log_entry)
            
        except Exception:
            # Don't let MongoDB errors break the application
            pass
    
    # Enhanced logging methods
    def debug(self, service: str, message: str, metadata: Dict = None, **kwargs):
        """Debug level logging."""
        self._log(service, "DEBUG", message, metadata, **kwargs)
    
    def info(self, service: str, message: str, metadata: Dict = None, **kwargs):
        """Info level logging."""
        self._log(service, "INFO", message, metadata, **kwargs)
    
    def success(self, service: str, message: str, metadata: Dict = None, **kwargs):
        """Success level logging."""
        self._log(service, "SUCCESS", message, metadata, **kwargs)
    
    def warning(self, service: str, message: str, metadata: Dict = None, **kwargs):
        """Warning level logging."""
        self._log(service, "WARNING", message, metadata, **kwargs)
    
    def error(self, service: str, message: str, metadata: Dict = None, **kwargs):
        """Error level logging."""
        self._log(service, "ERROR", message, metadata, **kwargs)
    
    def critical(self, service: str, message: str, metadata: Dict = None, **kwargs):
        """Critical level logging."""
        self._log(service, "CRITICAL", message, metadata, **kwargs)
    
    def trace(self, service: str, message: str, metadata: Dict = None, **kwargs):
        """Trace level logging with full stack trace."""
        self._log(service, "TRACE", message, metadata, **kwargs)
    
    def _log(self, service: str, level: str, message: str, metadata: Dict = None, **kwargs):
        """Internal logging method."""
        
        with self._lock:
            # Update metrics
            self.metrics['total_logs'] += 1
            self.metrics[f'{level.lower()}_logs'] += 1
            self.service_metrics[service]['total_logs'] += 1
            self.service_metrics[service][f'{level.lower()}_logs'] += 1
            
            # Prepare metadata
            log_metadata = metadata or {}
            log_metadata.update(kwargs)
            
            # Create logger context
            context_logger = logger.bind(
                service=service,
                metadata=json.dumps(log_metadata) if log_metadata else "{}"
            )
            
            # Log based on level
            if level == "DEBUG":
                context_logger.debug(message)
            elif level == "INFO":
                context_logger.info(message)
            elif level == "SUCCESS":
                context_logger.success(message)
            elif level == "WARNING":
                context_logger.warning(message)
            elif level == "ERROR":
                context_logger.error(message)
            elif level == "CRITICAL":
                context_logger.critical(message)
            elif level == "TRACE":
                context_logger.trace(message)
            
            # Log to MongoDB
            self._log_to_mongodb(service, level, message, log_metadata)
    
    # Trading-specific logging methods
    def log_trade_execution(self, symbol: str, action: str, quantity: int, price: float, 
                           order_id: str = None, execution_mode: str = "paper"):
        """Log trade execution with full details."""
        self.success("TRADE_EXECUTION", 
                    f"🚀 {action} {quantity} {symbol} @ ₹{price:.2f} ({execution_mode})",
                    {
                        'trade_type': 'execution',
                        'symbol': symbol,
                        'action': action,
                        'quantity': quantity,
                        'price': price,
                        'order_id': order_id,
                        'execution_mode': execution_mode,
                        'execution_timestamp': datetime.now(UTC).isoformat()
                    })
    
    def log_stock_analysis(self, symbol: str, decision: str, confidence: float, 
                          indicators: Dict = None, timeframes: List = None):
        """Log stock analysis results."""
        self.info("AI_ANALYSIS",
                 f"📊 {symbol} Analysis: {decision} (confidence: {confidence:.1%})",
                 {
                     'analysis_type': 'stock_analysis',
                     'symbol': symbol,
                     'decision': decision,
                     'confidence': confidence,
                     'indicators': indicators or {},
                     'timeframes': timeframes or [],
                     'analysis_timestamp': datetime.now(UTC).isoformat()
                 })
    
    def log_risk_alert(self, alert_type: str, symbol: str, current_value: float, 
                      threshold: float, action_taken: str):
        """Log risk management alerts."""
        self.warning("RISK_MANAGEMENT",
                    f"⚠️ {alert_type} Alert: {symbol} {current_value} > {threshold} → {action_taken}",
                    {
                        'alert_type': alert_type,
                        'symbol': symbol,
                        'current_value': current_value,
                        'threshold': threshold,
                        'action_taken': action_taken,
                        'alert_timestamp': datetime.now(UTC).isoformat()
                    })
    
    def log_system_performance(self, component: str, metric_name: str, value: float, 
                              target: float = None, unit: str = ""):
        """Log system performance metrics."""
        status = "✅" if target and value >= target else "📊"
        target_info = f" (target: {target}{unit})" if target else ""
        
        self.info("PERFORMANCE",
                 f"{status} {component}: {metric_name} = {value}{unit}{target_info}",
                 {
                     'performance_type': 'metric',
                     'component': component,
                     'metric_name': metric_name,
                     'value': value,
                     'target': target,
                     'unit': unit,
                     'performance_timestamp': datetime.now(UTC).isoformat()
                 })
    
    def log_progress_milestone(self, component: str, milestone: str, current: int, 
                              total: int, details: Dict = None):
        """Log progress milestones."""
        percentage = (current / total * 100) if total > 0 else 0
        
        self.info("PROGRESS",
                 f"🎯 {component}: {milestone} {current}/{total} ({percentage:.1f}%)",
                 {
                     'progress_type': 'milestone',
                     'component': component,
                     'milestone': milestone,
                     'current': current,
                     'total': total,
                     'percentage': percentage,
                     'details': details or {},
                     'progress_timestamp': datetime.now(UTC).isoformat()
                 })
    
    def log_service_status(self, service: str, status: str, details: Dict = None):
        """Log service status changes."""
        status_emoji = {
            'starting': '🚀',
            'running': '✅',
            'stopping': '🛑',
            'stopped': '⏹️',
            'error': '❌',
            'warning': '⚠️'
        }
        
        emoji = status_emoji.get(status.lower(), '📋')
        
        self.info("SERVICE_STATUS",
                 f"{emoji} {service}: {status}",
                 {
                     'status_type': 'service_status',
                     'service': service,
                     'status': status,
                     'details': details or {},
                     'status_timestamp': datetime.now(UTC).isoformat()
                 })
    
    def get_session_summary(self) -> Dict[str, Any]:
        """Get current session summary with metrics."""
        runtime = datetime.now(UTC) - self.start_time
        
        return {
            'session_id': self.session_id,
            'start_time': self.start_time.isoformat(),
            'runtime_seconds': runtime.total_seconds(),
            'runtime_formatted': str(runtime),
            'total_logs': self.metrics['total_logs'],
            'log_metrics': dict(self.metrics),
            'service_metrics': {k: dict(v) for k, v in self.service_metrics.items()},
            'mongodb_enabled': self.mongodb_enabled,
            'active_services': list(self.service_loggers.keys())
        }
    
    def get_service_logs_path(self, service: str) -> Optional[Path]:
        """Get the log file path for a specific service."""
        if service in self.service_loggers:
            service_dir = self.base_log_dir / service.lower()
            return service_dir / f"{datetime.now().strftime('%Y-%m-%d')}_{service.lower()}.log"
        return None
    
    def cleanup(self):
        """Cleanup logger resources."""
        try:
            # Log final summary
            summary = self.get_session_summary()
            self.info("SYSTEM", "📊 Final Session Summary", summary)
            
            # Remove all handlers
            logger.remove()
            
        except Exception as e:
            print(f"Error during logger cleanup: {e}")

# Global logger instance
_global_enhanced_logger: Optional[EnhancedTradingLogger] = None

def get_enhanced_logger() -> EnhancedTradingLogger:
    """Get or create the global enhanced logger instance."""
    global _global_enhanced_logger
    
    if _global_enhanced_logger is None:
        _global_enhanced_logger = EnhancedTradingLogger()
    
    return _global_enhanced_logger

def setup_service_logger(service_name: str, log_level: str = "INFO") -> EnhancedTradingLogger:
    """Setup logger for a specific service."""
    enhanced_logger = get_enhanced_logger()
    enhanced_logger.register_service_logger(service_name, log_level)
    return enhanced_logger

# Convenience functions for quick logging
def log_trade(symbol: str, action: str, quantity: int, price: float, **kwargs):
    """Quick trade logging."""
    get_enhanced_logger().log_trade_execution(symbol, action, quantity, price, **kwargs)

def log_analysis(symbol: str, decision: str, confidence: float, **kwargs):
    """Quick analysis logging."""
    get_enhanced_logger().log_stock_analysis(symbol, decision, confidence, **kwargs)

def log_risk(alert_type: str, symbol: str, current_value: float, threshold: float, action: str):
    """Quick risk logging."""
    get_enhanced_logger().log_risk_alert(alert_type, symbol, current_value, threshold, action)

def log_performance(component: str, metric: str, value: float, **kwargs):
    """Quick performance logging."""
    get_enhanced_logger().log_system_performance(component, metric, value, **kwargs)

def log_progress(component: str, milestone: str, current: int, total: int, **kwargs):
    """Quick progress logging."""
    get_enhanced_logger().log_progress_milestone(component, milestone, current, total, **kwargs)

def log_service(service: str, status: str, **kwargs):
    """Quick service status logging."""
    get_enhanced_logger().log_service_status(service, status, **kwargs)

# Test the enhanced logger
if __name__ == "__main__":
    print("🧪 Testing Enhanced Loguru Trading Logger...")
    
    # Create enhanced logger
    enhanced_logger = EnhancedTradingLogger()
    
    # Test different log levels
    enhanced_logger.debug("SYSTEM", "Debug message for testing")
    enhanced_logger.info("SYSTEM", "Info message with enhanced formatting")
    enhanced_logger.success("SYSTEM", "Success message - operation completed!")
    enhanced_logger.warning("SYSTEM", "Warning message - attention needed")
    enhanced_logger.error("SYSTEM", "Error message - something went wrong")
    enhanced_logger.critical("SYSTEM", "Critical message - immediate action required")
    
    # Test trading-specific logging
    enhanced_logger.log_trade_execution("RELIANCE-EQ", "BUY", 10, 2547.80, order_id="ORD_001", execution_mode="paper")
    enhanced_logger.log_stock_analysis("SBIN-EQ", "STRONG_BUY", 0.87, 
                                      indicators={"rsi": 45.2, "macd": 1.23}, 
                                      timeframes=["1m", "5m", "15m"])
    enhanced_logger.log_risk_alert("POSITION_SIZE", "TCS-EQ", 15000, 10000, "REDUCE_POSITION")
    enhanced_logger.log_system_performance("AI_ANALYSIS", "stocks_per_second", 16.3, target=15.0, unit="/sec")
    enhanced_logger.log_progress_milestone("STOCK_DISCOVERY", "Validation Complete", 1000, 5000)
    enhanced_logger.log_service_status("TRADE_EXECUTION", "running", {"active_positions": 5})
    
    # Show session summary
    summary = enhanced_logger.get_session_summary()
    enhanced_logger.info("SYSTEM", "📊 Session Summary", summary)
    
    print(f"\n✅ Enhanced Loguru Logger test completed!")
    print(f"📁 Logs stored in: {enhanced_logger.base_log_dir}")
    print(f"📊 MongoDB enabled: {enhanced_logger.mongodb_enabled}")
    print(f"🔢 Total logs: {enhanced_logger.metrics['total_logs']}")
    
    # Cleanup
    enhanced_logger.cleanup()


