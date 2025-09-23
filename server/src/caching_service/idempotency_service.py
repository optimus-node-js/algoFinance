"""
Idempotency Service for HFT System
==================================

Request deduplication and idempotency management for:
- Angel One API calls
- Preventing duplicate orders
- Request tracking and replay protection
- Performance optimization
"""

import hashlib
import json
import time
import logging
from typing import Dict, Any, Optional, Tuple, Callable
from datetime import datetime, timedelta
from .redis_manager import get_redis_manager

logger = logging.getLogger(__name__)

class IdempotencyService:
    """
    Request idempotency service for API call deduplication.
    
    Features:
    - Request fingerprinting
    - Duplicate detection
    - Response caching
    - TTL-based cleanup
    """
    
    def __init__(
        self,
        default_ttl: int = 3600,  # 1 hour
        key_prefix: str = "idem:",
        enable_response_caching: bool = True
    ):
        """
        Initialize idempotency service.
        
        Args:
            default_ttl: Default TTL for idempotency keys (seconds)
            key_prefix: Redis key prefix for idempotency
            enable_response_caching: Whether to cache API responses
        """
        self.default_ttl = default_ttl
        self.key_prefix = key_prefix
        self.enable_response_caching = enable_response_caching
        self.redis = get_redis_manager()
        
        # Performance tracking
        self.stats = {
            'requests_processed': 0,
            'duplicates_prevented': 0,
            'cache_hits': 0,
            'cache_misses': 0,
            'errors': 0
        }
        
        logger.info(f"IdempotencyService initialized with TTL: {default_ttl}s")
    
    def _generate_request_key(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict] = None,
        headers: Optional[Dict] = None,
        user_id: Optional[str] = None
    ) -> str:
        """
        Generate unique key for request identification.
        
        Args:
            method: HTTP method
            endpoint: API endpoint
            params: Request parameters
            headers: Request headers (selective)
            user_id: User identifier
            
        Returns:
            Unique request key
        """
        # Create request fingerprint
        fingerprint_data = {
            'method': method.upper(),
            'endpoint': endpoint,
            'params': params or {},
            'user_id': user_id
        }
        
        # Include relevant headers (avoid authorization headers for security)
        if headers:
            filtered_headers = {
                k: v for k, v in headers.items() 
                if k.lower() not in ['authorization', 'x-api-key', 'cookie']
            }
            fingerprint_data['headers'] = filtered_headers
        
        # Generate hash
        fingerprint_json = json.dumps(fingerprint_data, sort_keys=True)
        fingerprint_hash = hashlib.sha256(fingerprint_json.encode()).hexdigest()[:16]
        
        return f"{self.key_prefix}{method.lower()}:{fingerprint_hash}"
    
    def _generate_response_key(self, request_key: str) -> str:
        """Generate response cache key from request key."""
        return f"{request_key}:response"
    
    def check_duplicate_request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict] = None,
        headers: Optional[Dict] = None,
        user_id: Optional[str] = None,
        custom_key: Optional[str] = None
    ) -> Tuple[bool, Optional[Any]]:
        """
        Check if request is duplicate and get cached response if available.
        
        Args:
            method: HTTP method
            endpoint: API endpoint
            params: Request parameters
            headers: Request headers
            user_id: User identifier
            custom_key: Custom idempotency key
            
        Returns:
            Tuple of (is_duplicate, cached_response)
        """
        try:
            self.stats['requests_processed'] += 1
            
            # Generate or use custom key
            if custom_key:
                request_key = f"{self.key_prefix}custom:{custom_key}"
            else:
                request_key = self._generate_request_key(
                    method, endpoint, params, headers, user_id
                )
            
            # Check if request exists
            request_exists = self.redis.exists(request_key)
            
            if request_exists:
                self.stats['duplicates_prevented'] += 1
                logger.info(f"Duplicate request detected: {request_key}")
                
                # Try to get cached response
                if self.enable_response_caching:
                    response_key = self._generate_response_key(request_key)
                    cached_response = self.redis.get(response_key)
                    
                    if cached_response:
                        self.stats['cache_hits'] += 1
                        logger.debug(f"Returning cached response for: {request_key}")
                        return True, cached_response
                    else:
                        self.stats['cache_misses'] += 1
                
                return True, None
            
            # Mark request as in-progress
            request_data = {
                'timestamp': int(time.time()),
                'method': method,
                'endpoint': endpoint,
                'status': 'in_progress'
            }
            
            success = self.redis.set(
                request_key, 
                request_data, 
                ttl=self.default_ttl
            )
            
            if not success:
                logger.warning(f"Failed to mark request in-progress: {request_key}")
            
            return False, None
            
        except Exception as e:
            self.stats['errors'] += 1
            logger.error(f"Error checking duplicate request: {e}")
            return False, None
    
    def store_response(
        self,
        method: str,
        endpoint: str,
        response: Any,
        params: Optional[Dict] = None,
        headers: Optional[Dict] = None,
        user_id: Optional[str] = None,
        custom_key: Optional[str] = None,
        ttl: Optional[int] = None
    ) -> bool:
        """
        Store API response for future duplicate requests.
        
        Args:
            method: HTTP method
            endpoint: API endpoint
            response: API response to cache
            params: Request parameters
            headers: Request headers
            user_id: User identifier
            custom_key: Custom idempotency key
            ttl: TTL for response cache
            
        Returns:
            True if stored successfully
        """
        try:
            if not self.enable_response_caching:
                return True
            
            # Generate keys
            if custom_key:
                request_key = f"{self.key_prefix}custom:{custom_key}"
            else:
                request_key = self._generate_request_key(
                    method, endpoint, params, headers, user_id
                )
            
            response_key = self._generate_response_key(request_key)
            
            # Update request status
            request_data = {
                'timestamp': int(time.time()),
                'method': method,
                'endpoint': endpoint,
                'status': 'completed'
            }
            
            # Use provided TTL or default
            cache_ttl = ttl or self.default_ttl
            
            # Store both request marker and response
            request_stored = self.redis.set(request_key, request_data, ttl=cache_ttl)
            response_stored = self.redis.set(response_key, response, ttl=cache_ttl)
            
            if request_stored and response_stored:
                logger.debug(f"Response cached for: {request_key}")
                return True
            else:
                logger.warning(f"Failed to cache response for: {request_key}")
                return False
                
        except Exception as e:
            self.stats['errors'] += 1
            logger.error(f"Error storing response: {e}")
            return False
    
    def invalidate_request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict] = None,
        headers: Optional[Dict] = None,
        user_id: Optional[str] = None,
        custom_key: Optional[str] = None
    ) -> bool:
        """
        Invalidate idempotency key and cached response.
        
        Args:
            method: HTTP method
            endpoint: API endpoint
            params: Request parameters
            headers: Request headers
            user_id: User identifier
            custom_key: Custom idempotency key
            
        Returns:
            True if invalidated successfully
        """
        try:
            # Generate keys
            if custom_key:
                request_key = f"{self.key_prefix}custom:{custom_key}"
            else:
                request_key = self._generate_request_key(
                    method, endpoint, params, headers, user_id
                )
            
            response_key = self._generate_response_key(request_key)
            
            # Delete both keys
            request_deleted = self.redis.delete(request_key)
            response_deleted = self.redis.delete(response_key)
            
            logger.debug(f"Invalidated idempotency for: {request_key}")
            return True
            
        except Exception as e:
            self.stats['errors'] += 1
            logger.error(f"Error invalidating request: {e}")
            return False
    
    def create_idempotent_decorator(
        self,
        ttl: Optional[int] = None,
        cache_response: bool = True,
        key_generator: Optional[Callable] = None
    ):
        """
        Create decorator for automatic idempotency.
        
        Args:
            ttl: TTL for idempotency key
            cache_response: Whether to cache responses
            key_generator: Custom key generation function
            
        Returns:
            Decorator function
        """
        def decorator(func):
            def wrapper(*args, **kwargs):
                # Extract request details (customize based on function signature)
                method = kwargs.get('method', 'POST')
                endpoint = kwargs.get('endpoint', func.__name__)
                params = kwargs.get('params', {})
                headers = kwargs.get('headers', {})
                user_id = kwargs.get('user_id')
                
                # Generate custom key if function provided
                custom_key = None
                if key_generator:
                    custom_key = key_generator(*args, **kwargs)
                
                # Check for duplicate
                is_duplicate, cached_response = self.check_duplicate_request(
                    method=method,
                    endpoint=endpoint,
                    params=params,
                    headers=headers,
                    user_id=user_id,
                    custom_key=custom_key
                )
                
                if is_duplicate and cached_response is not None:
                    logger.info(f"Returning cached response for {endpoint}")
                    return cached_response
                
                if is_duplicate:
                    logger.warning(f"Duplicate request blocked for {endpoint}")
                    return {'error': 'Duplicate request', 'status': 'rejected'}
                
                # Execute original function
                try:
                    result = func(*args, **kwargs)
                    
                    # Store response if caching enabled
                    if cache_response and result:
                        self.store_response(
                            method=method,
                            endpoint=endpoint,
                            response=result,
                            params=params,
                            headers=headers,
                            user_id=user_id,
                            custom_key=custom_key,
                            ttl=ttl
                        )
                    
                    return result
                    
                except Exception as e:
                    # Invalidate on error to allow retry
                    self.invalidate_request(
                        method=method,
                        endpoint=endpoint,
                        params=params,
                        headers=headers,
                        user_id=user_id,
                        custom_key=custom_key
                    )
                    raise
            
            return wrapper
        return decorator
    
    def get_stats(self) -> Dict[str, Any]:
        """Get idempotency service statistics."""
        total_requests = self.stats['requests_processed']
        
        return {
            'service': {
                'default_ttl': self.default_ttl,
                'key_prefix': self.key_prefix,
                'response_caching_enabled': self.enable_response_caching
            },
            'performance': {
                'requests_processed': total_requests,
                'duplicates_prevented': self.stats['duplicates_prevented'],
                'duplicate_rate': self.stats['duplicates_prevented'] / total_requests if total_requests > 0 else 0,
                'cache_hits': self.stats['cache_hits'],
                'cache_misses': self.stats['cache_misses'],
                'cache_hit_rate': self.stats['cache_hits'] / (self.stats['cache_hits'] + self.stats['cache_misses']) if (self.stats['cache_hits'] + self.stats['cache_misses']) > 0 else 0,
                'errors': self.stats['errors'],
                'error_rate': self.stats['errors'] / total_requests if total_requests > 0 else 0
            },
            'redis_stats': self.redis.get_stats() if self.redis else None
        }
    
    def clear_stats(self):
        """Clear service statistics."""
        self.stats = {key: 0 for key in self.stats}


# Global idempotency service instance
_idempotency_service: Optional[IdempotencyService] = None

def get_idempotency_service(**kwargs) -> IdempotencyService:
    """Get or create global idempotency service instance."""
    global _idempotency_service
    
    if _idempotency_service is None:
        _idempotency_service = IdempotencyService(**kwargs)
    
    return _idempotency_service

