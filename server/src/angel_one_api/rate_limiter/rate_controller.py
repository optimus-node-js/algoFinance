"""
Angel One Central Rate Controller - STRICT ENFORCEMENT MIDDLEWARE
===============================================================

CRITICAL COMPONENT: ALL Angel One API calls MUST go through this controller.
This is the ONLY way to prevent 403 rate limit errors.

Features:
- Strict rate limit enforcement for all 25 APIs
- 5 API key rotation and load balancing
- Real-time usage tracking and monitoring
- Automatic blocking when limits approached
- Emergency brake system for rate limit violations

Author: AI Trading System
Version: 1.0.0
"""

import asyncio
import time
from typing import Dict, Optional, List, Any, Callable
from datetime import datetime, timedelta, UTC
import threading
from collections import defaultdict, deque
from contextlib import asynccontextmanager
import logging

from .api_limits import API_LIMITS, APIPriority
from .api_limit_config import ANGEL_ONE_API_LIMITS

logger = logging.getLogger(__name__)

class RateLimitExceeded(Exception):
    """Raised when API rate limit would be exceeded."""
    def __init__(self, api_name: str, limit_type: str, reset_time: float):
        self.api_name = api_name
        self.limit_type = limit_type
        self.reset_time = reset_time
        super().__init__(f"Rate limit exceeded for {api_name} ({limit_type}). Resets in {reset_time:.1f}s")

class APIKeyTracker:
    """Tracks usage for a single API key across all APIs with Token Bucket algorithm."""
    
    def __init__(self, key_id: str):
        self.key_id = key_id
        self.usage_counters = {}
        self.token_buckets = {}  # Token bucket for each API
        self.last_refill = {}
        self.lock = threading.Lock()
        
        # Initialize counters and token buckets for all APIs using new config
        for method_name, limit in ANGEL_ONE_API_LIMITS.items():
            self.usage_counters[method_name] = {
                'per_second': deque(maxlen=1000),
                'per_minute': deque(maxlen=1000), 
                'per_hour': deque(maxlen=1000)
            }
            
            # Initialize token bucket with full capacity
            self.token_buckets[method_name] = {
                'tokens': limit.requests_per_second or 1,  # Start with full bucket
                'capacity': limit.requests_per_second or 1,
                'refill_rate': limit.requests_per_second or 1  # Tokens per second
            }
            self.last_refill[method_name] = time.time()
    
    def _refill_token_bucket(self, api_name: str):
        """Refill token bucket based on elapsed time (Token Bucket Algorithm)."""
        now = time.time()
        elapsed = now - self.last_refill[api_name]
        
        if elapsed > 0:
            # Calculate tokens to add based on refill rate
            bucket = self.token_buckets[api_name]
            tokens_to_add = elapsed * bucket['refill_rate']
            
            # Add tokens but don't exceed capacity
            bucket['tokens'] = min(
                bucket['capacity'],
                bucket['tokens'] + tokens_to_add
            )
            
            self.last_refill[api_name] = now
    
    def can_make_request(self, api_name: str) -> tuple[bool, Optional[str], Optional[float]]:
        """Check if request can be made using Token Bucket + Sliding Window algorithms."""
        with self.lock:
            limit = ANGEL_ONE_API_LIMITS.get(api_name)
            if not limit:
                return False, f"Unknown API: {api_name}", None
            
            now = time.time()
            
            # Refill token bucket first
            self._refill_token_bucket(api_name)
            
            # Check token bucket (per-second rate limiting)
            bucket = self.token_buckets[api_name]
            if bucket['tokens'] < 1:
                # Calculate time until next token is available
                time_for_next_token = 1.0 / bucket['refill_rate']
                return False, "token_bucket", time_for_next_token
            
            # Check sliding window for per-minute limit  
            if limit.requests_per_minute:
                recent_requests = [
                    req_time for req_time in self.usage_counters[api_name]['per_minute'] 
                    if now - req_time < 60.0
                ]
                if len(recent_requests) >= limit.requests_per_minute:
                    reset_time = 60.0 - (now - min(recent_requests))
                    return False, "per_minute", reset_time
            
            # Check sliding window for per-hour limit
            if limit.requests_per_hour:
                recent_requests = [
                    req_time for req_time in self.usage_counters[api_name]['per_hour']
                    if now - req_time < 3600.0
                ]
                if len(recent_requests) >= limit.requests_per_hour:
                    reset_time = 3600.0 - (now - min(recent_requests))
                    return False, "per_hour", reset_time
                    
            return True, None, None
    
    def record_request(self, api_name: str):
        """Record a successful API request and consume token."""
        with self.lock:
            now = time.time()
            
            # Consume one token from bucket
            if api_name in self.token_buckets:
                self.token_buckets[api_name]['tokens'] = max(0, self.token_buckets[api_name]['tokens'] - 1)
            
            # Record in sliding windows
            self.usage_counters[api_name]['per_second'].append(now)
            self.usage_counters[api_name]['per_minute'].append(now)
            self.usage_counters[api_name]['per_hour'].append(now)
    
    def get_usage_stats(self, api_name: str) -> Dict[str, Any]:
        """Get current usage statistics for an API."""
        with self.lock:
            limit = ANGEL_ONE_API_LIMITS.get(api_name)
            if not limit:
                return {}
            
            now = time.time()
            
            # Count recent requests
            per_second_count = len([
                req_time for req_time in self.usage_counters[api_name]['per_second']
                if now - req_time < 1.0
            ])
            
            per_minute_count = len([
                req_time for req_time in self.usage_counters[api_name]['per_minute']
                if now - req_time < 60.0
            ])
            
            per_hour_count = len([
                req_time for req_time in self.usage_counters[api_name]['per_hour'] 
                if now - req_time < 3600.0
            ])
            
            return {
                'key_id': self.key_id,
                'per_second': {
                    'used': per_second_count,
                    'limit': limit.requests_per_second,
                    'percentage': (per_second_count / limit.requests_per_second * 100) if limit.requests_per_second else 0
                },
                'per_minute': {
                    'used': per_minute_count,
                    'limit': limit.requests_per_minute,
                    'percentage': (per_minute_count / limit.requests_per_minute * 100) if limit.requests_per_minute else 0
                },
                'per_hour': {
                    'used': per_hour_count,
                    'limit': limit.requests_per_hour,
                    'percentage': (per_hour_count / limit.requests_per_hour * 100) if limit.requests_per_hour else 0
                }
            }

class AngelOneRateController:
    """
    DISTRIBUTED RATE CONTROLLER - Maximizes throughput across ALL API keys.
    
    ENHANCED FEATURES:
    1. Dynamic API key pool management (auto-detects all keys)
    2. Distributed load balancing (multiplies capacity: 5 keys × 10 req/sec = 50 req/sec)
    3. Token Bucket + Sliding Window algorithms (industry standard)
    4. Real-time key rotation and fallback
    5. Emergency brake system with auto-recovery
    6. Live throughput optimization
    """
    
    def __init__(self, api_keys: List[str]):
        if len(api_keys) < 1:
            raise ValueError("At least 1 API key required")
            
        self.api_keys = api_keys
        self.key_trackers = {
            key_id: APIKeyTracker(f"API_KEY_{i+1}")
            for i, key_id in enumerate(api_keys)
        }
        
        # Distributed load balancing with round-robin + availability
        self.key_rotation_index = 0
        self.key_priority_queue = {}  # Per-API priority queues
        self.lock = asyncio.Lock()
        
        # Emergency brake with auto-recovery
        self.emergency_brake = False
        self.consecutive_errors = 0
        self.max_consecutive_errors = 3  # More aggressive
        self.emergency_brake_timeout = 30  # Auto-reset after 30 seconds
        self.emergency_brake_start_time = None
        
        # Advanced performance tracking
        self.total_requests = 0
        self.successful_requests = 0
        self.blocked_requests = 0
        self.rate_limit_errors = 0
        self.distributed_requests = defaultdict(int)  # Per-key request count
        self.api_method_stats = defaultdict(lambda: {'requests': 0, 'errors': 0})
        
        # Calculate and log total distributed capacity
        total_capacity = self._calculate_distributed_capacity()
        
        logger.info(f"🚨 Angel One Distributed Rate Controller initialized with {len(api_keys)} API keys")
        logger.info(f"📊 DISTRIBUTED CAPACITY: {total_capacity}")
        logger.info(f"🔥 MAXIMUM THROUGHPUT: {sum(total_capacity.values())} requests/second across all methods")
    
    def _calculate_distributed_capacity(self) -> Dict[str, int]:
        """Calculate DISTRIBUTED capacity across ALL API keys for ALL methods."""
        distributed_capacity = {}
        
        for method_name, limit in ANGEL_ONE_API_LIMITS.items():
            if limit.requests_per_second:
                # DISTRIBUTED CAPACITY = per_key_limit × number_of_keys
                distributed_capacity[method_name] = limit.requests_per_second * len(self.api_keys)
            else:
                # Fallback for APIs without per-second limits
                distributed_capacity[method_name] = len(self.api_keys)
        
        return distributed_capacity
    
    def _check_emergency_brake_auto_reset(self):
        """Auto-reset emergency brake after timeout."""
        if (self.emergency_brake and 
            self.emergency_brake_start_time and 
            time.time() - self.emergency_brake_start_time > self.emergency_brake_timeout):
            
            logger.info(f"🔄 Auto-resetting emergency brake after {self.emergency_brake_timeout}s timeout")
            self.reset_emergency_brake()
    
    def _get_key_load_score(self, api_name: str, key_id: str) -> float:
        """Calculate load score for a key (lower = better choice)."""
        tracker = self.key_trackers[key_id]
        
        # Check token availability (primary factor)
        with tracker.lock:
            tracker._refill_token_bucket(api_name)
            bucket = tracker.token_buckets.get(api_name, {})
            token_ratio = bucket.get('tokens', 0) / bucket.get('capacity', 1)
        
        # Calculate recent usage (secondary factor)
        usage_stats = tracker.get_usage_stats(api_name)
        usage_ratio = usage_stats.get('per_second', {}).get('percentage', 0) / 100
        
        # Combined score (lower is better)
        # Token availability weighted more heavily
        load_score = (1 - token_ratio) * 0.7 + usage_ratio * 0.3
        
        return load_score
    
    def _select_optimal_api_key(self, api_name: str) -> Optional[str]:
        """Select optimal API key using intelligent load balancing."""
        available_keys = []
        key_scores = []
        
        # Phase 1: Find all keys with immediate availability
        for key_id in self.api_keys:
            tracker = self.key_trackers[key_id]
            can_make, error_type, reset_time = tracker.can_make_request(api_name)
            
            if can_make:
                available_keys.append(key_id)
                # Calculate load score for intelligent selection
                load_score = self._get_key_load_score(api_name, key_id)
                key_scores.append((key_id, load_score))
        
        # Phase 2: Select best available key by load balancing
        if available_keys:
            # Sort by load score (ascending - lower is better)
            key_scores.sort(key=lambda x: x[1])
            selected_key = key_scores[0][0]
            
            # Update distributed request tracking
            self.distributed_requests[selected_key] += 1
            
            return selected_key
        
        # Phase 3: All keys exhausted - find key with shortest reset time
        best_key = None
        shortest_reset = float('inf')
        
        for key_id in self.api_keys:
            tracker = self.key_trackers[key_id]
            can_make, error_type, reset_time = tracker.can_make_request(api_name)
            
            if not can_make and reset_time and reset_time < shortest_reset:
                shortest_reset = reset_time
                best_key = key_id
        
        return best_key
    
    @asynccontextmanager
    async def acquire_api_permit(self, api_name: str, priority: APIPriority = APIPriority.MEDIUM):
        """
        CRITICAL MIDDLEWARE: Acquire permission to make Angel One API call.
        
        Usage:
            async with rate_controller.acquire_api_permit("getLtpData") as permit:
                if permit:
                    response = angel_client.ltpData(...)
        """
        if self.emergency_brake:
            logger.error(f"🚨 EMERGENCY BRAKE ACTIVE - Blocking {api_name} request")
            yield None
            return
        
        # Check emergency brake auto-reset
        self._check_emergency_brake_auto_reset()
        
        async with self.lock:
            self.total_requests += 1
            self.api_method_stats[api_name]['requests'] += 1
            
            # Find optimal API key using distributed load balancing
            selected_key = self._select_optimal_api_key(api_name)
            
            if not selected_key:
                # All keys are rate limited - calculate distributed wait strategy
                self.blocked_requests += 1
                limit = API_LIMITS.get_limit(api_name)
                
                # Calculate minimum wait time across ALL distributed keys
                min_wait_time = float('inf')
                for key_id in self.api_keys:
                    tracker = self.key_trackers[key_id]
                    can_make, error_type, reset_time = tracker.can_make_request(api_name)
                    if not can_make and reset_time and reset_time < min_wait_time:
                        min_wait_time = reset_time
                
                distributed_capacity = self._calculate_distributed_capacity().get(api_name, 1)
                logger.warning(f"⚠️ DISTRIBUTED RATE LIMIT reached for {api_name} across ALL {len(self.api_keys)} keys. "
                             f"Total capacity: {distributed_capacity} req/sec. Waiting {min_wait_time:.1f}s")
                
                # For CRITICAL APIs, implement smart waiting with token bucket refill prediction
                if priority == APIPriority.CRITICAL and min_wait_time < 3.0:
                    # Calculate optimal wait time based on token refill rate
                    optimal_wait = min(min_wait_time + 0.05, 1.0 / (limit.requests_per_second or 1))
                    await asyncio.sleep(optimal_wait)
                    selected_key = self._select_optimal_api_key(api_name)
                
                if not selected_key:
                    raise RateLimitExceeded(api_name, f"all_{len(self.api_keys)}_keys", min_wait_time)
        
        # Record the request
        tracker = self.key_trackers[selected_key]
        tracker.record_request(api_name)
        self.successful_requests += 1
        
        # Create permit object with selected API key
        permit = {
            'api_key_id': selected_key,
            'api_name': api_name,
            'timestamp': time.time()
        }
        
        try:
            yield permit
            # Request successful - reset consecutive errors
            self.consecutive_errors = 0
            
        except Exception as e:
            # Check if it's a rate limit error (403)
            if "403" in str(e) or "rate limit" in str(e).lower():
                self.rate_limit_errors += 1
                self.consecutive_errors += 1
                
                logger.error(f"🚨 Rate limit error for {api_name}: {e}")
                
                # Activate emergency brake if too many consecutive errors
                if self.consecutive_errors >= self.max_consecutive_errors:
                    self.emergency_brake = True
                    logger.critical(f"🚨 EMERGENCY BRAKE ACTIVATED after {self.consecutive_errors} consecutive rate limit errors")
            else:
                # Other error - reset consecutive error count
                self.consecutive_errors = 0
            
            raise
    
    def get_system_status(self) -> Dict[str, Any]:
        """Get comprehensive DISTRIBUTED system status and statistics."""
        status = {
            'emergency_brake': self.emergency_brake,
            'total_requests': self.total_requests,
            'successful_requests': self.successful_requests,
            'blocked_requests': self.blocked_requests,
            'rate_limit_errors': self.rate_limit_errors,
            'success_rate': (self.successful_requests / max(self.total_requests, 1)) * 100,
            'api_keys_count': len(self.api_keys),
            'consecutive_errors': self.consecutive_errors,
            
            # DISTRIBUTED PERFORMANCE METRICS
            'distributed_capacity': self._calculate_distributed_capacity(),
            'distributed_requests': dict(self.distributed_requests),
            'api_method_stats': dict(self.api_method_stats),
            'total_distributed_throughput': sum(self._calculate_distributed_capacity().values())
        }
        
        # Add per-key usage for ALL APIs (not just critical)
        all_apis = list(ANGEL_ONE_API_LIMITS.keys())
        status['distributed_api_usage'] = {}
        
        for api_name in all_apis:
            status['distributed_api_usage'][api_name] = {
                'total_capacity': self._calculate_distributed_capacity().get(api_name, 0),
                'per_key_usage': {}
            }
            
            for key_id in self.api_keys:
                tracker = self.key_trackers[key_id]
                usage = tracker.get_usage_stats(api_name)
                status['distributed_api_usage'][api_name]['per_key_usage'][key_id] = usage
        
        # Load balancing effectiveness
        total_distributed = sum(self.distributed_requests.values())
        if total_distributed > 0:
            status['load_balancing_effectiveness'] = {
                key_id: (count / total_distributed) * 100 
                for key_id, count in self.distributed_requests.items()
            }
        else:
            status['load_balancing_effectiveness'] = {}
        
        return status
    
    def reset_emergency_brake(self):
        """Reset emergency brake (use with caution)."""
        self.emergency_brake = False
        self.consecutive_errors = 0
        logger.warning("🔄 Emergency brake reset manually")
    
    def print_live_dashboard(self):
        """Print live DISTRIBUTED rate limiting dashboard."""
        print("\n🚀 ANGEL ONE DISTRIBUTED RATE LIMITING DASHBOARD")
        print("=" * 80)
        
        status = self.get_system_status()
        
        print(f"Emergency Brake: {'🚨 ACTIVE' if status['emergency_brake'] else '✅ Normal'}")
        print(f"Success Rate: {status['success_rate']:.1f}%")
        print(f"Total Requests: {status['total_requests']} | Blocked: {status['blocked_requests']}")
        print(f"API Keys: {status['api_keys_count']} | Total Distributed Throughput: {status['total_distributed_throughput']} req/sec")
        
        print(f"\n🔥 DISTRIBUTED CAPACITY (Per API Method):")
        distributed_capacity = status['distributed_capacity']
        for api_name, capacity in list(distributed_capacity.items())[:8]:  # Show top 8
            per_key = capacity // status['api_keys_count']
            print(f"  {api_name:20s}: {capacity:3d} req/sec ({per_key:2d} × {status['api_keys_count']} keys)")
        
        print(f"\n⚖️ LOAD BALANCING EFFECTIVENESS:")
        load_balancing = status.get('load_balancing_effectiveness', {})
        for key_id, percentage in load_balancing.items():
            bar_length = int(percentage / 5)  # Scale for display
            bar = "█" * bar_length + "░" * (20 - bar_length)
            print(f"  {key_id:12s}: [{bar}] {percentage:5.1f}%")
        
        print(f"\n📊 TOP API METHODS USAGE:")
        api_stats = status.get('api_method_stats', {})
        top_apis = sorted(api_stats.items(), key=lambda x: x[1]['requests'], reverse=True)[:5]
        for api_name, stats in top_apis:
            requests = stats['requests']
            errors = stats['errors']
            error_rate = (errors / max(requests, 1)) * 100
            capacity = distributed_capacity.get(api_name, 0)
            print(f"  {api_name:20s}: {requests:4d} requests | {capacity:3d} req/sec capacity | {error_rate:4.1f}% errors")

# Global rate controller instance (initialized by connection manager)
_rate_controller: Optional[AngelOneRateController] = None

def initialize_rate_controller(api_keys: List[str]) -> AngelOneRateController:
    """Initialize the global rate controller with API keys."""
    global _rate_controller
    _rate_controller = AngelOneRateController(api_keys)
    return _rate_controller

def get_rate_controller() -> Optional[AngelOneRateController]:
    """Get the global rate controller instance."""
    return _rate_controller

# Decorator for easy rate limiting
def rate_limited(api_name: str, priority: APIPriority = APIPriority.MEDIUM):
    """Decorator to automatically apply rate limiting to Angel One API calls."""
    def decorator(func: Callable):
        async def wrapper(*args, **kwargs):
            controller = get_rate_controller()
            if not controller:
                raise RuntimeError("Rate controller not initialized")
            
            async with controller.acquire_api_permit(api_name, priority) as permit:
                if not permit:
                    raise RateLimitExceeded(api_name, "emergency_brake", 0)
                
                # Add API key to kwargs for the function
                kwargs['_rate_limit_permit'] = permit
                return await func(*args, **kwargs)
        return wrapper
    return decorator

if __name__ == "__main__":
    # Test the rate controller
    async def test_rate_controller():
        # Mock API keys
        test_keys = ["key1", "key2", "key3", "key4", "key5"]
        controller = initialize_rate_controller(test_keys)
        
        # Test rate limiting for getLtpData (10 req/sec limit)
        print("Testing rate limiting for getLtpData...")
        
        for i in range(15):  # Try to make 15 requests (should block after 10)
            try:
                async with controller.acquire_api_permit("get_ltp_data", APIPriority.CRITICAL) as permit:
                    if permit:
                        print(f"✅ Request {i+1}: Using {permit['api_key_id']}")
                        await asyncio.sleep(0.01)  # Simulate API call
                    else:
                        print(f"❌ Request {i+1}: Blocked")
            except RateLimitExceeded as e:
                print(f"🚨 Request {i+1}: {e}")
        
        # Print dashboard
        controller.print_live_dashboard()
    
    asyncio.run(test_rate_controller())
