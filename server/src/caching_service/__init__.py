"""
Caching Service for HFT System
==============================

Redis-based caching and idempotency service for:
- Request deduplication
- API response caching
- Session management
- Performance optimization

Features:
- Async Redis operations
- Request idempotency tracking
- TTL-based cache management
- High-performance caching patterns
"""

from .redis_manager import RedisManager
from .idempotency_service import IdempotencyService
from .cache_service import CacheService

__version__ = "1.0.0"
__author__ = "HFT Trading System"

__all__ = [
    "RedisManager",
    "IdempotencyService", 
    "CacheService"
]

