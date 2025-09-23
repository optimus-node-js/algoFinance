"""
Redis Manager for HFT System
============================

High-performance Redis connection management with:
- Async/sync connection pooling
- Connection redundancy
- Performance monitoring
- Auto-failover capabilities
"""

import logging
import asyncio
import time
import json
from typing import Dict, Any, Optional, Union, List
from datetime import datetime, timedelta
import threading
import redis
from redis.connection import ConnectionPool
from redis.exceptions import ConnectionError, TimeoutError, RedisError

# Use our Python 3.13+ compatible async Redis client
from .async_redis_compat import AsyncRedisCompat

logger = logging.getLogger(__name__)

class RedisManager:
    """
    High-performance Redis manager for HFT system.
    
    Features:
    - Dual async/sync connections
    - Connection pooling and failover
    - Performance monitoring
    - TTL management
    """
    
    def __init__(
        self,
        host: str = "localhost",
        port: int = 6379,
        db: int = 0,
        password: Optional[str] = None,
        max_connections: int = 20,
        socket_timeout: float = 1.0,
        socket_connect_timeout: float = 1.0
    ):
        """
        Initialize Redis manager.
        
        Args:
            host: Redis server host
            port: Redis server port
            db: Redis database number
            password: Redis password
            max_connections: Maximum connections in pool
            socket_timeout: Socket timeout in seconds
            socket_connect_timeout: Connection timeout in seconds
        """
        self.host = host
        self.port = port
        self.db = db
        self.password = password
        self.max_connections = max_connections
        self.socket_timeout = socket_timeout
        self.socket_connect_timeout = socket_connect_timeout
        
        # Connection pools
        self.sync_pool = None
        self.async_pool = None
        self.sync_client = None
        self.async_client = None
        
        # Performance tracking
        self.operation_counts = {
            'get': 0, 'set': 0, 'delete': 0, 'exists': 0, 'expire': 0
        }
        self.error_counts = {
            'connection_errors': 0, 'timeout_errors': 0, 'other_errors': 0
        }
        self.start_time = datetime.now()
        self._lock = threading.Lock()
        
        # Initialize connections
        self._initialize_sync_connection()
        
        logger.info(f"RedisManager initialized for {host}:{port}")
    
    def _initialize_sync_connection(self):
        """Initialize synchronous Redis connection pool."""
        try:
            self.sync_pool = ConnectionPool(
                host=self.host,
                port=self.port,
                db=self.db,
                password=self.password,
                max_connections=self.max_connections,
                socket_timeout=self.socket_timeout,
                socket_connect_timeout=self.socket_connect_timeout,
                retry_on_timeout=True,
                health_check_interval=30
            )
            
            self.sync_client = redis.Redis(connection_pool=self.sync_pool)
            
            # Test connection
            self.sync_client.ping()
            logger.info("Sync Redis connection established successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize sync Redis connection: {e}")
            self.sync_client = None
    
    async def _initialize_async_connection(self):
        """Initialize asynchronous Redis connection."""
        try:
            self.async_client = AsyncRedisCompat(
                host=self.host,
                port=self.port,
                db=self.db,
                password=self.password,
                socket_timeout=self.socket_timeout,
                socket_connect_timeout=self.socket_connect_timeout
            )
            
            # Test connection
            connected = await self.async_client.connect()
            if connected:
                logger.info("Async Redis connection established successfully")
            else:
                logger.error("Failed to establish async Redis connection")
                self.async_client = None
            
        except Exception as e:
            logger.error(f"Failed to initialize async Redis connection: {e}")
            self.async_client = None
    
    async def get_async_client(self):
        """Get or create async Redis client."""
        if self.async_client is None:
            await self._initialize_async_connection()
        return self.async_client
    
    def get_sync_client(self):
        """Get sync Redis client."""
        if self.sync_client is None:
            self._initialize_sync_connection()
        return self.sync_client
    
    def is_connected(self) -> bool:
        """Check if Redis is connected."""
        try:
            if self.sync_client:
                self.sync_client.ping()
                return True
        except Exception:
            pass
        return False
    
    async def is_connected_async(self) -> bool:
        """Check if async Redis is connected."""
        try:
            client = await self.get_async_client()
            if client:
                return await client.ping()
        except Exception:
            pass
        return False
    
    # Synchronous Operations
    def set(
        self, 
        key: str, 
        value: Union[str, Dict, List], 
        ttl: Optional[int] = None,
        nx: bool = False
    ) -> bool:
        """
        Set a key-value pair.
        
        Args:
            key: Cache key
            value: Value to cache (will be JSON serialized if not string)
            ttl: Time to live in seconds
            nx: Only set if key doesn't exist
            
        Returns:
            True if set successfully
        """
        try:
            client = self.get_sync_client()
            if not client:
                return False
            
            # Serialize complex objects
            if isinstance(value, (dict, list)):
                value = json.dumps(value)
            
            result = client.set(key, value, ex=ttl, nx=nx)
            
            with self._lock:
                self.operation_counts['set'] += 1
            
            return bool(result)
            
        except ConnectionError:
            with self._lock:
                self.error_counts['connection_errors'] += 1
            logger.error(f"Redis connection error setting key: {key}")
            return False
        except TimeoutError:
            with self._lock:
                self.error_counts['timeout_errors'] += 1
            logger.error(f"Redis timeout setting key: {key}")
            return False
        except Exception as e:
            with self._lock:
                self.error_counts['other_errors'] += 1
            logger.error(f"Redis error setting key {key}: {e}")
            return False
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        Get a value by key.
        
        Args:
            key: Cache key
            default: Default value if key not found
            
        Returns:
            Cached value or default
        """
        try:
            client = self.get_sync_client()
            if not client:
                return default
            
            value = client.get(key)
            
            with self._lock:
                self.operation_counts['get'] += 1
            
            if value is None:
                return default
            
            # Try to deserialize JSON
            try:
                return json.loads(value.decode('utf-8'))
            except (json.JSONDecodeError, UnicodeDecodeError):
                return value.decode('utf-8')
                
        except ConnectionError:
            with self._lock:
                self.error_counts['connection_errors'] += 1
            logger.error(f"Redis connection error getting key: {key}")
            return default
        except TimeoutError:
            with self._lock:
                self.error_counts['timeout_errors'] += 1
            logger.error(f"Redis timeout getting key: {key}")
            return default
        except Exception as e:
            with self._lock:
                self.error_counts['other_errors'] += 1
            logger.error(f"Redis error getting key {key}: {e}")
            return default
    
    def delete(self, key: str) -> bool:
        """Delete a key."""
        try:
            client = self.get_sync_client()
            if not client:
                return False
            
            result = client.delete(key)
            
            with self._lock:
                self.operation_counts['delete'] += 1
            
            return bool(result)
            
        except Exception as e:
            with self._lock:
                self.error_counts['other_errors'] += 1
            logger.error(f"Redis error deleting key {key}: {e}")
            return False
    
    def exists(self, key: str) -> bool:
        """Check if key exists."""
        try:
            client = self.get_sync_client()
            if not client:
                return False
            
            result = client.exists(key)
            
            with self._lock:
                self.operation_counts['exists'] += 1
            
            return bool(result)
            
        except Exception as e:
            with self._lock:
                self.error_counts['other_errors'] += 1
            logger.error(f"Redis error checking key existence {key}: {e}")
            return False
    
    def expire(self, key: str, ttl: int) -> bool:
        """Set TTL for existing key."""
        try:
            client = self.get_sync_client()
            if not client:
                return False
            
            result = client.expire(key, ttl)
            
            with self._lock:
                self.operation_counts['expire'] += 1
            
            return bool(result)
            
        except Exception as e:
            with self._lock:
                self.error_counts['other_errors'] += 1
            logger.error(f"Redis error setting TTL for key {key}: {e}")
            return False
    
    # Asynchronous Operations
    async def set_async(
        self, 
        key: str, 
        value: Union[str, Dict, List], 
        ttl: Optional[int] = None,
        nx: bool = False
    ) -> bool:
        """Async version of set."""
        try:
            client = await self.get_async_client()
            if not client:
                return False
            
            result = await client.set(key, value, ex=ttl, nx=nx)
            
            with self._lock:
                self.operation_counts['set'] += 1
            
            return bool(result)
            
        except Exception as e:
            with self._lock:
                self.error_counts['other_errors'] += 1
            logger.error(f"Async Redis error setting key {key}: {e}")
            return False
    
    async def get_async(self, key: str, default: Any = None) -> Any:
        """Async version of get."""
        try:
            client = await self.get_async_client()
            if not client:
                return default
            
            value = await client.get(key)
            
            with self._lock:
                self.operation_counts['get'] += 1
            
            if value is None:
                return default
            
            return value
                
        except Exception as e:
            with self._lock:
                self.error_counts['other_errors'] += 1
            logger.error(f"Async Redis error getting key {key}: {e}")
            return default
    
    # Utility Methods
    def get_stats(self) -> Dict[str, Any]:
        """Get Redis manager statistics."""
        with self._lock:
            runtime = (datetime.now() - self.start_time).total_seconds()
            total_operations = sum(self.operation_counts.values())
            total_errors = sum(self.error_counts.values())
            
            return {
                'connection': {
                    'host': self.host,
                    'port': self.port,
                    'db': self.db,
                    'connected': self.is_connected(),
                    'max_connections': self.max_connections
                },
                'performance': {
                    'runtime_seconds': runtime,
                    'total_operations': total_operations,
                    'operations_per_second': total_operations / runtime if runtime > 0 else 0,
                    'total_errors': total_errors,
                    'error_rate': total_errors / total_operations if total_operations > 0 else 0
                },
                'operations': self.operation_counts.copy(),
                'errors': self.error_counts.copy()
            }
    
    def clear_stats(self):
        """Clear performance statistics."""
        with self._lock:
            self.operation_counts = {key: 0 for key in self.operation_counts}
            self.error_counts = {key: 0 for key in self.error_counts}
            self.start_time = datetime.now()
    
    def flush_db(self):
        """Flush current database (use with caution!)."""
        try:
            client = self.get_sync_client()
            if client:
                client.flushdb()
                logger.warning("Redis database flushed")
                return True
        except Exception as e:
            logger.error(f"Error flushing Redis database: {e}")
        return False
    
    async def close_async(self):
        """Close async Redis connection."""
        if self.async_client:
            await self.async_client.close()
            self.async_client = None
            logger.info("Async Redis connection closed")
    
    def close(self):
        """Close sync Redis connection."""
        if self.sync_client:
            self.sync_client.connection_pool.disconnect()
            self.sync_client = None
            logger.info("Sync Redis connection closed")


# Global Redis manager instance
_redis_manager: Optional[RedisManager] = None
_redis_lock = threading.Lock()

def get_redis_manager(
    host: str = "localhost",
    port: int = 6379,
    db: int = 0,
    **kwargs
) -> RedisManager:
    """Get or create global Redis manager instance."""
    global _redis_manager
    
    with _redis_lock:
        if _redis_manager is None:
            _redis_manager = RedisManager(host=host, port=port, db=db, **kwargs)
        return _redis_manager

def close_redis_manager():
    """Close global Redis manager."""
    global _redis_manager
    
    with _redis_lock:
        if _redis_manager:
            _redis_manager.close()
            _redis_manager = None
