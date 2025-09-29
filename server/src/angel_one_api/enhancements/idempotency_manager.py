"""
Idempotency Manager for Angel One API
====================================

Core idempotency management system that prevents duplicate API calls and
provides intelligent caching for performance optimization.

Features:
- Automatic duplicate request detection
- Configurable TTL per method type
- Response caching for successful operations
- Emergency override capabilities
- Comprehensive metrics and monitoring
- Thread-safe operations
- Async/sync compatibility

Usage:
    # As decorator
    @idempotency_wrapper(method_type="trading", ttl=300)
    async def place_order(**params):
        return await original_place_order(**params)
    
    # As context manager
    async with IdempotencyManager() as idm:
        result = await idm.execute_with_idempotency(
            method=place_order,
            params=order_params,
            method_type="trading"
        )

Author: HFT Trading System
Created: September 23, 2025
"""

import asyncio
import hashlib
import json
import time
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, Callable, Union, Awaitable
from functools import wraps
import inspect

# Import our Redis infrastructure
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent.parent))

from caching_service.redis_manager import get_redis_manager
from caching_service.idempotency_service import get_idempotency_service
from caching_service.cache_service import get_cache_service

# Set up logging
logger = logging.getLogger(__name__)

class IdempotencyError(Exception):
    """Custom exception for idempotency-related errors"""
    pass

class IdempotencyManager:
    """
    Advanced idempotency management for Angel One API operations.
    
    Provides duplicate prevention, intelligent caching, and performance
    optimization while maintaining full compatibility with existing code.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize IdempotencyManager with configuration.
        
        Args:
            config: Optional configuration dictionary
        """
        self.config = config or self._get_default_config()
        self.redis_manager = get_redis_manager()
        self.idempotency_service = get_idempotency_service()
        self.cache_service = get_cache_service()
        
        # Performance metrics
        self.metrics = {
            "total_requests": 0,
            "duplicates_prevented": 0,
            "cache_hits": 0,
            "cache_misses": 0,
            "api_calls_saved": 0,
            "average_response_time": 0.0,
            "start_time": time.time()
        }
        
        logger.info("IdempotencyManager initialized successfully")
    
    def _get_default_config(self) -> Dict[str, Any]:
        """Get default configuration settings"""
        return {
            "trading_methods": {
                "ttl": 300,  # 5 minutes
                "cache_response": True,
                "allow_override": True
            },
            "account_methods": {
                "ttl": 60,   # 1 minute
                "cache_response": True,
                "allow_override": False
            },
            "market_methods": {
                "ttl": 30,   # 30 seconds
                "cache_response": True,
                "allow_override": False
            },
            "monitoring": {
                "log_duplicates": True,
                "log_cache_hits": True,
                "alert_threshold": 0.1  # Alert if >10% duplicates
            }
        }
    
    async def execute_with_idempotency(
        self,
        method: Callable,
        params: Dict[str, Any],
        method_type: str = "trading",
        ttl: Optional[int] = None,
        cache_response: bool = True,
        allow_override: bool = False,
        request_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Execute a method with full idempotency protection.
        
        Args:
            method: The Angel One API method to execute
            params: Parameters for the method
            method_type: Type of method (trading, account, market)
            ttl: Time-to-live for idempotency (seconds)
            cache_response: Whether to cache successful responses
            allow_override: Allow manual override of idempotency
            request_id: Optional manual request ID
            
        Returns:
            Dictionary containing method result or cached response
        """
        start_time = time.time()
        self.metrics["total_requests"] += 1
        
        try:
            # Generate request fingerprint
            fingerprint = await self._create_request_fingerprint(
                method.__name__, params, method_type
            )
            
            # Use custom request ID if provided
            if request_id:
                fingerprint = f"custom:{request_id}"
            
            # Check for existing request (idempotency)
            existing_response = await self._check_existing_request(
                fingerprint, method_type, method.__name__, params, ttl
            )
            
            if existing_response and not allow_override:
                # Return cached response
                self.metrics["duplicates_prevented"] += 1
                self.metrics["cache_hits"] += 1
                
                logger.info(f"Duplicate request prevented: {method.__name__}")
                
                return {
                    "success": True,
                    "data": existing_response,
                    "from_cache": True,
                    "duplicate_prevented": True,
                    "response_time": time.time() - start_time
                }
            
            # Execute original method
            logger.info(f"Executing {method.__name__} with idempotency protection")
            
            if inspect.iscoroutinefunction(method):
                result = await method(**params)
            else:
                result = method(**params)
            
            # Cache successful response
            if cache_response and result.get("success", True):
                await self._cache_response(
                    fingerprint, result, method_type, method.__name__, params, ttl
                )
            
            # Update metrics
            response_time = time.time() - start_time
            self._update_metrics(response_time, cache_hit=False)
            
            return {
                "success": True,
                "data": result,
                "from_cache": False,
                "duplicate_prevented": False,
                "response_time": response_time
            }
            
        except Exception as e:
            logger.error(f"Error in execute_with_idempotency: {str(e)}")
            raise IdempotencyError(f"Idempotency execution failed: {str(e)}")
    
    async def _create_request_fingerprint(
        self,
        method_name: str,
        params: Dict[str, Any],
        method_type: str
    ) -> str:
        """
        Create unique fingerprint for request identification.
        
        Args:
            method_name: Name of the Angel One API method
            params: Method parameters
            method_type: Type of method (trading, account, market)
            
        Returns:
            Unique fingerprint string
        """
        # Create fingerprint based on method type
        if method_type == "trading":
            # For trading methods, include all critical parameters
            fingerprint_data = {
                "method": method_name,
                "symbol": params.get("tradingsymbol", ""),
                "symboltoken": params.get("symboltoken", ""),
                "quantity": params.get("quantity", ""),
                "price": params.get("price", ""),
                "transactiontype": params.get("transactiontype", ""),
                "ordertype": params.get("ordertype", ""),
                "producttype": params.get("producttype", ""),
                "exchange": params.get("exchange", ""),
                # Exclude timestamp and auto-generated fields
            }
        elif method_type == "account":
            # For account methods, simpler fingerprint
            fingerprint_data = {
                "method": method_name,
                # Group by time window for caching
                "time_window": int(time.time() / 60)  # 1-minute windows
            }
        else:  # market data
            # For market methods, include symbol and time window
            fingerprint_data = {
                "method": method_name,
                "symbol": params.get("symboltoken", params.get("tradingsymbol", "")),
                "exchange": params.get("exchange", ""),
                "time_window": int(time.time() / 30)  # 30-second windows
            }
        
        # Create hash
        fingerprint_str = json.dumps(fingerprint_data, sort_keys=True)
        fingerprint = hashlib.sha256(fingerprint_str.encode()).hexdigest()[:16]
        
        return f"{method_type}:{method_name}:{fingerprint}"
    
    async def _check_existing_request(
        self,
        fingerprint: str,
        method_type: str,
        method_name: str,
        params: Dict[str, Any],
        custom_ttl: Optional[int] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Check if request already exists in cache.
        
        Args:
            fingerprint: Request fingerprint
            method_type: Type of method
            method_name: Name of the method
            params: Method parameters
            custom_ttl: Custom TTL override
            
        Returns:
            Cached response if exists, None otherwise
        """
        try:
            # Check idempotency service using correct API
            is_duplicate, cached_response = self.idempotency_service.check_duplicate_request(
                method=method_type,
                endpoint=method_name,
                params=params,
                custom_key=fingerprint
            )
            
            if is_duplicate and cached_response:
                return cached_response
            
            return None
            
        except Exception as e:
            logger.error(f"Error checking existing request: {e}")
            return None
    
    async def _cache_response(
        self,
        fingerprint: str,
        response: Dict[str, Any],
        method_type: str,
        method_name: str,
        params: Dict[str, Any],
        custom_ttl: Optional[int] = None
    ) -> bool:
        """
        Cache successful response for future idempotency checks.
        
        Args:
            fingerprint: Request fingerprint
            response: Response to cache
            method_type: Type of method
            method_name: Name of the method
            params: Method parameters
            custom_ttl: Custom TTL override
            
        Returns:
            True if cached successfully
        """
        try:
            # Get TTL for method type
            ttl = custom_ttl or self.config.get(f"{method_type}_methods", {}).get("ttl", 300)
            
            # Store in idempotency service using correct API
            success = self.idempotency_service.store_response(
                method=method_type,
                endpoint=method_name,
                response=response,
                params=params,
                custom_key=fingerprint,
                ttl=ttl
            )
            
            if success:
                logger.debug(f"Response cached for {fingerprint}")
            
            return success
            
        except Exception as e:
            logger.error(f"Failed to cache response: {str(e)}")
            return False
    
    def _update_metrics(self, response_time: float, cache_hit: bool = False):
        """Update performance metrics"""
        if cache_hit:
            self.metrics["cache_hits"] += 1
        else:
            self.metrics["cache_misses"] += 1
        
        # Update average response time
        total_responses = self.metrics["cache_hits"] + self.metrics["cache_misses"]
        self.metrics["average_response_time"] = (
            (self.metrics["average_response_time"] * (total_responses - 1) + response_time) 
            / total_responses
        )
        
        self.metrics["api_calls_saved"] = self.metrics["duplicates_prevented"]
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get current performance metrics"""
        uptime = time.time() - self.metrics["start_time"]
        total_requests = self.metrics["total_requests"]
        
        return {
            "total_requests": total_requests,
            "duplicates_prevented": self.metrics["duplicates_prevented"],
            "duplicate_prevention_rate": (
                self.metrics["duplicates_prevented"] / max(total_requests, 1) * 100
            ),
            "cache_hit_rate": (
                self.metrics["cache_hits"] / max(total_requests, 1) * 100
            ),
            "api_calls_saved": self.metrics["api_calls_saved"],
            "average_response_time": self.metrics["average_response_time"],
            "uptime_seconds": uptime,
            "requests_per_minute": total_requests / max(uptime / 60, 1)
        }
    
    async def invalidate_cache(
        self, 
        method_name: Optional[str] = None,
        method_type: Optional[str] = None
    ) -> int:
        """
        Invalidate cached responses.
        
        Args:
            method_name: Specific method to invalidate (optional)
            method_type: Method type to invalidate (optional)
            
        Returns:
            Number of entries invalidated
        """
        try:
            if method_name and method_type:
                pattern = f"{method_type}:{method_name}:*"
            elif method_type:
                pattern = f"{method_type}:*"
            else:
                pattern = "*"
            
            # Use Redis pattern deletion
            redis_client = self.redis_manager.get_sync_client()
            keys = redis_client.keys(f"idem:{pattern}")
            
            if keys:
                deleted = redis_client.delete(*keys)
                logger.info(f"Invalidated {deleted} cache entries")
                return deleted
            
            return 0
            
        except Exception as e:
            logger.error(f"Failed to invalidate cache: {str(e)}")
            return 0


def idempotency_wrapper(
    method_type: str = "trading",
    ttl: Optional[int] = None,
    cache_response: bool = True,
    allow_override: bool = False
):
    """
    Decorator for adding idempotency to Angel One API methods.
    
    Args:
        method_type: Type of method (trading, account, market)
        ttl: Time-to-live for idempotency (seconds)
        cache_response: Whether to cache successful responses
        allow_override: Allow manual override of idempotency
        
    Usage:
        @idempotency_wrapper(method_type="trading", ttl=300)
        async def place_order(**params):
            return await original_place_order(**params)
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Initialize idempotency manager
            idm = IdempotencyManager()
            
            # Extract parameters
            if args:
                # Handle class methods (self as first argument)
                params = kwargs
                if len(args) > 1:
                    params.update(dict(zip(func.__code__.co_varnames[1:], args[1:])))
            else:
                params = kwargs
            
            # Execute with idempotency
            result = await idm.execute_with_idempotency(
                method=func,
                params=params,
                method_type=method_type,
                ttl=ttl,
                cache_response=cache_response,
                allow_override=allow_override
            )
            
            return result
        
        return wrapper
    return decorator
