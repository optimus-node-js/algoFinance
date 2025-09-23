"""
Cache Service for HFT System
============================

High-performance caching for Angel One API responses:
- Market data caching
- Authentication token caching
- Rate limiting state caching
- Performance optimization
"""

import time
import logging
from typing import Dict, Any, Optional, Union, List
from datetime import datetime, timedelta
from .redis_manager import get_redis_manager

logger = logging.getLogger(__name__)

class CacheService:
    """
    High-performance caching service for HFT system.
    
    Features:
    - Multi-tier caching strategy
    - TTL-based expiration
    - Namespace-based organization
    - Performance optimization
    """
    
    def __init__(self, namespace: str = "hft_cache"):
        """
        Initialize cache service.
        
        Args:
            namespace: Cache namespace prefix
        """
        self.namespace = namespace
        self.redis = get_redis_manager()
        
        # Performance tracking
        self.stats = {
            'gets': 0,
            'sets': 0,
            'hits': 0,
            'misses': 0,
            'errors': 0
        }
        
        logger.info(f"CacheService initialized with namespace: {namespace}")
    
    def _make_key(self, key: str, category: str = "general") -> str:
        """Generate namespaced cache key."""
        return f"{self.namespace}:{category}:{key}"
    
    # Market Data Caching
    def cache_market_data(
        self,
        symbol: str,
        exchange: str,
        data: Dict[str, Any],
        ttl: int = 5  # 5 seconds for market data
    ) -> bool:
        """
        Cache market data with short TTL.
        
        Args:
            symbol: Trading symbol
            exchange: Exchange identifier
            data: Market data to cache
            ttl: Time to live in seconds
            
        Returns:
            True if cached successfully
        """
        key = self._make_key(f"{exchange}:{symbol}", "market_data")
        
        # Add timestamp to data
        cache_data = {
            **data,
            'cached_at': int(time.time()),
            'symbol': symbol,
            'exchange': exchange
        }
        
        success = self.redis.set(key, cache_data, ttl=ttl)
        
        if success:
            self.stats['sets'] += 1
        else:
            self.stats['errors'] += 1
        
        return success
    
    def get_market_data(
        self,
        symbol: str,
        exchange: str,
        max_age: int = 5  # Max age in seconds
    ) -> Optional[Dict[str, Any]]:
        """
        Get cached market data if fresh enough.
        
        Args:
            symbol: Trading symbol
            exchange: Exchange identifier
            max_age: Maximum age of cached data in seconds
            
        Returns:
            Cached market data or None
        """
        key = self._make_key(f"{exchange}:{symbol}", "market_data")
        
        self.stats['gets'] += 1
        
        data = self.redis.get(key)
        
        if data is None:
            self.stats['misses'] += 1
            return None
        
        # Check data freshness
        cached_at = data.get('cached_at', 0)
        age = int(time.time()) - cached_at
        
        if age > max_age:
            self.stats['misses'] += 1
            # Optionally delete stale data
            self.redis.delete(key)
            return None
        
        self.stats['hits'] += 1
        return data
    
    # Authentication Token Caching
    def cache_auth_token(
        self,
        user_id: str,
        token_data: Dict[str, Any],
        ttl: int = 3600  # 1 hour
    ) -> bool:
        """
        Cache authentication token.
        
        Args:
            user_id: User identifier
            token_data: Token information
            ttl: Time to live in seconds
            
        Returns:
            True if cached successfully
        """
        key = self._make_key(user_id, "auth_tokens")
        
        cache_data = {
            **token_data,
            'cached_at': int(time.time()),
            'user_id': user_id
        }
        
        success = self.redis.set(key, cache_data, ttl=ttl)
        
        if success:
            self.stats['sets'] += 1
            logger.debug(f"Auth token cached for user: {user_id}")
        else:
            self.stats['errors'] += 1
        
        return success
    
    def get_auth_token(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Get cached authentication token.
        
        Args:
            user_id: User identifier
            
        Returns:
            Cached token data or None
        """
        key = self._make_key(user_id, "auth_tokens")
        
        self.stats['gets'] += 1
        
        data = self.redis.get(key)
        
        if data is None:
            self.stats['misses'] += 1
            return None
        
        self.stats['hits'] += 1
        return data
    
    def invalidate_auth_token(self, user_id: str) -> bool:
        """
        Invalidate cached authentication token.
        
        Args:
            user_id: User identifier
            
        Returns:
            True if invalidated successfully
        """
        key = self._make_key(user_id, "auth_tokens")
        success = self.redis.delete(key)
        
        if success:
            logger.debug(f"Auth token invalidated for user: {user_id}")
        
        return success
    
    # Rate Limiting Cache
    def cache_rate_limit_state(
        self,
        api_key: str,
        window: str,
        current_count: int,
        reset_time: int,
        ttl: int = 60
    ) -> bool:
        """
        Cache rate limiting state.
        
        Args:
            api_key: API key identifier
            window: Rate limit window (e.g., "1min", "1hour")
            current_count: Current request count
            reset_time: Window reset time
            ttl: Time to live in seconds
            
        Returns:
            True if cached successfully
        """
        key = self._make_key(f"{api_key}:{window}", "rate_limits")
        
        data = {
            'current_count': current_count,
            'reset_time': reset_time,
            'updated_at': int(time.time())
        }
        
        success = self.redis.set(key, data, ttl=ttl)
        
        if success:
            self.stats['sets'] += 1
        else:
            self.stats['errors'] += 1
        
        return success
    
    def get_rate_limit_state(
        self,
        api_key: str,
        window: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get cached rate limiting state.
        
        Args:
            api_key: API key identifier
            window: Rate limit window
            
        Returns:
            Cached rate limit data or None
        """
        key = self._make_key(f"{api_key}:{window}", "rate_limits")
        
        self.stats['gets'] += 1
        
        data = self.redis.get(key)
        
        if data is None:
            self.stats['misses'] += 1
            return None
        
        self.stats['hits'] += 1
        return data
    
    # Session Data Caching
    def cache_session_data(
        self,
        session_id: str,
        session_data: Dict[str, Any],
        ttl: int = 1800  # 30 minutes
    ) -> bool:
        """
        Cache session data.
        
        Args:
            session_id: Session identifier
            session_data: Session information
            ttl: Time to live in seconds
            
        Returns:
            True if cached successfully
        """
        key = self._make_key(session_id, "sessions")
        
        cache_data = {
            **session_data,
            'cached_at': int(time.time()),
            'session_id': session_id
        }
        
        success = self.redis.set(key, cache_data, ttl=ttl)
        
        if success:
            self.stats['sets'] += 1
        else:
            self.stats['errors'] += 1
        
        return success
    
    def get_session_data(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get cached session data."""
        key = self._make_key(session_id, "sessions")
        
        self.stats['gets'] += 1
        
        data = self.redis.get(key)
        
        if data is None:
            self.stats['misses'] += 1
            return None
        
        self.stats['hits'] += 1
        return data
    
    # Generic Caching Methods
    def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None,
        category: str = "general"
    ) -> bool:
        """
        Generic cache set operation.
        
        Args:
            key: Cache key
            value: Value to cache
            ttl: Time to live in seconds
            category: Cache category
            
        Returns:
            True if cached successfully
        """
        cache_key = self._make_key(key, category)
        success = self.redis.set(cache_key, value, ttl=ttl)
        
        if success:
            self.stats['sets'] += 1
        else:
            self.stats['errors'] += 1
        
        return success
    
    def get(
        self,
        key: str,
        default: Any = None,
        category: str = "general"
    ) -> Any:
        """
        Generic cache get operation.
        
        Args:
            key: Cache key
            default: Default value if not found
            category: Cache category
            
        Returns:
            Cached value or default
        """
        cache_key = self._make_key(key, category)
        
        self.stats['gets'] += 1
        
        value = self.redis.get(cache_key, default)
        
        if value == default:
            self.stats['misses'] += 1
        else:
            self.stats['hits'] += 1
        
        return value
    
    def delete(self, key: str, category: str = "general") -> bool:
        """Delete cached value."""
        cache_key = self._make_key(key, category)
        return self.redis.delete(cache_key)
    
    def exists(self, key: str, category: str = "general") -> bool:
        """Check if key exists in cache."""
        cache_key = self._make_key(key, category)
        return self.redis.exists(cache_key)
    
    # Bulk Operations
    def get_multiple(
        self,
        keys: List[str],
        category: str = "general"
    ) -> Dict[str, Any]:
        """
        Get multiple cached values.
        
        Args:
            keys: List of cache keys
            category: Cache category
            
        Returns:
            Dictionary of key-value pairs
        """
        results = {}
        
        for key in keys:
            value = self.get(key, category=category)
            if value is not None:
                results[key] = value
        
        return results
    
    def set_multiple(
        self,
        data: Dict[str, Any],
        ttl: Optional[int] = None,
        category: str = "general"
    ) -> Dict[str, bool]:
        """
        Set multiple cached values.
        
        Args:
            data: Dictionary of key-value pairs
            ttl: Time to live in seconds
            category: Cache category
            
        Returns:
            Dictionary of key-success pairs
        """
        results = {}
        
        for key, value in data.items():
            results[key] = self.set(key, value, ttl=ttl, category=category)
        
        return results
    
    # Statistics and Management
    def get_stats(self) -> Dict[str, Any]:
        """Get cache service statistics."""
        total_gets = self.stats['gets']
        hit_rate = self.stats['hits'] / total_gets if total_gets > 0 else 0
        
        return {
            'service': {
                'namespace': self.namespace,
                'redis_connected': self.redis.is_connected() if self.redis else False
            },
            'performance': {
                'total_gets': total_gets,
                'total_sets': self.stats['sets'],
                'cache_hits': self.stats['hits'],
                'cache_misses': self.stats['misses'],
                'hit_rate': hit_rate,
                'errors': self.stats['errors']
            },
            'redis_stats': self.redis.get_stats() if self.redis else None
        }
    
    def clear_stats(self):
        """Clear cache statistics."""
        self.stats = {key: 0 for key in self.stats}
    
    def flush_category(self, category: str) -> int:
        """
        Flush all keys in a category (requires Redis SCAN).
        Note: This is a potentially expensive operation.
        
        Args:
            category: Cache category to flush
            
        Returns:
            Number of keys deleted
        """
        try:
            client = self.redis.get_sync_client()
            if not client:
                return 0
            
            pattern = f"{self.namespace}:{category}:*"
            keys = client.keys(pattern)
            
            if keys:
                deleted = client.delete(*keys)
                logger.info(f"Flushed {deleted} keys from category: {category}")
                return deleted
            
            return 0
            
        except Exception as e:
            logger.error(f"Error flushing category {category}: {e}")
            self.stats['errors'] += 1
            return 0


# Global cache service instance
_cache_service: Optional[CacheService] = None

def get_cache_service(namespace: str = "hft_cache") -> CacheService:
    """Get or create global cache service instance."""
    global _cache_service
    
    if _cache_service is None:
        _cache_service = CacheService(namespace=namespace)
    
    return _cache_service

