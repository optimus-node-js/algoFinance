"""
Async Redis Compatibility Layer
===============================

Python 3.13+ compatible async Redis operations using redis-py's async support
instead of aioredis which has compatibility issues.
"""

import asyncio
import json
import logging
from typing import Dict, Any, Optional, Union
import redis.asyncio as redis_async

logger = logging.getLogger(__name__)

class AsyncRedisCompat:
    """
    Async Redis client compatible with Python 3.13+.
    Uses redis-py's built-in async support instead of aioredis.
    """
    
    def __init__(
        self,
        host: str = "localhost",
        port: int = 6379,
        db: int = 0,
        password: Optional[str] = None,
        socket_timeout: float = 1.0,
        socket_connect_timeout: float = 1.0
    ):
        """Initialize async Redis client."""
        self.host = host
        self.port = port
        self.db = db
        self.password = password
        self.socket_timeout = socket_timeout
        self.socket_connect_timeout = socket_connect_timeout
        self.client = None
        
    async def connect(self):
        """Establish connection."""
        try:
            self.client = redis_async.Redis(
                host=self.host,
                port=self.port,
                db=self.db,
                password=self.password,
                socket_timeout=self.socket_timeout,
                socket_connect_timeout=self.socket_connect_timeout,
                decode_responses=False  # We'll handle encoding ourselves
            )
            
            # Test connection
            await self.client.ping()
            logger.info(f"Async Redis connected to {self.host}:{self.port}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to connect to async Redis: {e}")
            self.client = None
            return False
    
    async def ping(self) -> bool:
        """Test connection."""
        try:
            if self.client:
                await self.client.ping()
                return True
        except Exception as e:
            logger.error(f"Async Redis ping failed: {e}")
        return False
    
    async def set(
        self, 
        key: str, 
        value: Union[str, Dict, list], 
        ex: Optional[int] = None,
        nx: bool = False
    ) -> bool:
        """Set key-value pair."""
        try:
            if not self.client:
                await self.connect()
                if not self.client:
                    return False
            
            # Serialize complex objects
            if isinstance(value, (dict, list)):
                value = json.dumps(value)
            elif not isinstance(value, (str, bytes)):
                value = str(value)
            
            result = await self.client.set(key, value, ex=ex, nx=nx)
            return bool(result)
            
        except Exception as e:
            logger.error(f"Async Redis set error for key {key}: {e}")
            return False
    
    async def get(self, key: str) -> Optional[Any]:
        """Get value by key."""
        try:
            if not self.client:
                await self.connect()
                if not self.client:
                    return None
            
            value = await self.client.get(key)
            
            if value is None:
                return None
            
            # Decode bytes to string
            if isinstance(value, bytes):
                value = value.decode('utf-8')
            
            # Try to deserialize JSON
            try:
                return json.loads(value)
            except (json.JSONDecodeError, TypeError):
                return value
                
        except Exception as e:
            logger.error(f"Async Redis get error for key {key}: {e}")
            return None
    
    async def delete(self, key: str) -> bool:
        """Delete key."""
        try:
            if not self.client:
                await self.connect()
                if not self.client:
                    return False
            
            result = await self.client.delete(key)
            return bool(result)
            
        except Exception as e:
            logger.error(f"Async Redis delete error for key {key}: {e}")
            return False
    
    async def exists(self, key: str) -> bool:
        """Check if key exists."""
        try:
            if not self.client:
                await self.connect()
                if not self.client:
                    return False
            
            result = await self.client.exists(key)
            return bool(result)
            
        except Exception as e:
            logger.error(f"Async Redis exists error for key {key}: {e}")
            return False
    
    async def close(self):
        """Close connection."""
        if self.client:
            await self.client.close()
            self.client = None
            logger.info("Async Redis connection closed")

