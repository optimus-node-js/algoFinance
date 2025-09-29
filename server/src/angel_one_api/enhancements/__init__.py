"""
Angel One API Enhancements
==========================

Advanced features and optimizations for the Angel One API:
- Idempotency management for duplicate prevention
- Intelligent caching for performance optimization
- Request fingerprinting for deduplication
- Advanced monitoring and analytics

This package enhances the existing Angel One API with enterprise-grade
reliability and performance features while maintaining full backward compatibility.

Key Components:
- IdempotencyManager: Core duplicate prevention logic
- RequestFingerprinting: Unique request identification  
- CacheOptimizer: Intelligent caching strategies
- DuplicateDetector: Advanced duplicate detection
- PerformanceMonitor: Real-time metrics and analytics

Usage:
    from angel_one_api.enhancements import IdempotencyManager
    
    # Initialize idempotency manager
    idempotency = IdempotencyManager()
    
    # Use with existing Angel One methods
    @idempotency.protect(method_type="trading", ttl=300)
    async def enhanced_place_order(**params):
        return await original_place_order(**params)

Author: HFT Trading System
Created: September 23, 2025
"""

from .idempotency_manager import IdempotencyManager, idempotency_wrapper
from .request_fingerprinting import RequestFingerprinter
from .cache_optimizer import CacheOptimizer
from .duplicate_detector import DuplicateDetector
from .auto_idempotency import AutoIdempotency, auto_idempotency, auto_wrap_module, auto_wrap_all

__version__ = "1.0.0"
__author__ = "HFT Trading System"

# Export main components
__all__ = [
    "IdempotencyManager",
    "idempotency_wrapper", 
    "RequestFingerprinter",
    "CacheOptimizer",
    "DuplicateDetector",
    "AutoIdempotency",
    "auto_idempotency",
    "auto_wrap_module", 
    "auto_wrap_all"
]

# Default configuration
DEFAULT_CONFIG = {
    "redis_connection": {
        "host": "localhost",
        "port": 6379,
        "db": 0,
        "decode_responses": True
    },
    "idempotency": {
        "default_ttl": 300,  # 5 minutes
        "trading_ttl": 300,  # 5 minutes for trading operations
        "account_ttl": 60,   # 1 minute for account queries
        "market_ttl": 30     # 30 seconds for market data
    },
    "caching": {
        "enable_cache": True,
        "cache_hit_target": 0.8,  # 80% cache hit rate target
        "performance_improvement_target": 0.5  # 50% response time improvement
    },
    "monitoring": {
        "enable_metrics": True,
        "log_duplicate_prevention": True,
        "log_cache_performance": True,
        "alert_on_high_duplicate_rate": True
    }
}
