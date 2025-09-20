"""
Angel One API Rate Limits - ENHANCED REAL-TIME SYSTEM
===================================================

This module provides enhanced real-time tracking for Angel One API rate limits.
The actual limits configuration is in api_limit_config.py for better organization.

ENHANCED FEATURES:
- Real-time per-method per-API-key tracking
- In-memory cache for ultra-fast lookups (100ms refresh)
- Intelligent load balancing across methods and keys
- Backwards compatibility with existing code

Source: https://smartapi.angelbroking.com/docs/RateLimit
Author: AI Trading System
Version: 2.0.0 (Enhanced with real-time tracking)
"""

import time
import threading
from collections import defaultdict, deque
from typing import Dict, Optional, Any, List

# Import the official configuration
from .api_limit_config import (
    APIPriority,
    APIMethodLimit,
    AngelOneAPILimits as BaseAPILimits,
    ANGEL_ONE_API_LIMITS,
    API_LIMITS as CONFIG_API_LIMITS
)

class RealTimeMethodTracker:
    """
    REAL-TIME PER-METHOD PER-API-KEY TRACKER
    
    This tracks usage in real-time memory for ultra-fast lookups.
    Each API key tracks usage separately for each method.
    """
    
    def __init__(self):
        self.lock = threading.Lock()
        
        # Real-time tracking: {api_key: {method: {timeframe: deque of timestamps}}}
        self.real_time_usage = defaultdict(lambda: defaultdict(lambda: {
            'per_second': deque(maxlen=100),
            'per_minute': deque(maxlen=1000), 
            'per_hour': deque(maxlen=10000)
        }))
        
        # Fast cache for current usage counts
        self.current_usage_cache = defaultdict(lambda: defaultdict(lambda: {
            'per_second_count': 0,
            'per_minute_count': 0,
            'per_hour_count': 0,
            'last_updated': 0
        }))
        
    def record_method_usage(self, api_key: str, method_name: str):
        """Record a method usage for an API key."""
        with self.lock:
            now = time.time()
            
            # Record in real-time deques
            method_data = self.real_time_usage[api_key][method_name]
            method_data['per_second'].append(now)
            method_data['per_minute'].append(now)
            method_data['per_hour'].append(now)
            
            # Update fast cache
            self._update_usage_cache(api_key, method_name, now)
            
    def _update_usage_cache(self, api_key: str, method_name: str, now: float):
        """Update the fast usage cache for a method."""
        method_data = self.real_time_usage[api_key][method_name]
        cache = self.current_usage_cache[api_key][method_name]
        
        # Count recent requests
        cache['per_second_count'] = len([
            t for t in method_data['per_second'] if now - t < 1.0
        ])
        cache['per_minute_count'] = len([
            t for t in method_data['per_minute'] if now - t < 60.0
        ])
        cache['per_hour_count'] = len([
            t for t in method_data['per_hour'] if now - t < 3600.0
        ])
        cache['last_updated'] = now
        
    def can_make_method_request(self, api_key: str, method_name: str) -> tuple[bool, Optional[str], Optional[float]]:
        """
        Check if a specific method can be called on a specific API key.
        
        Returns:
            (can_make, reason, wait_time)
        """
        limit = ANGEL_ONE_API_LIMITS.get(method_name)
        if not limit:
            return False, f"Unknown method: {method_name}", None
        
        with self.lock:
            now = time.time()
            
            # Update cache if needed
            cache = self.current_usage_cache[api_key][method_name]
            if now - cache['last_updated'] > 0.1:  # Refresh cache every 100ms
                self._update_usage_cache(api_key, method_name, now)
            
            # Check per-second limit
            if limit.requests_per_second:
                if cache['per_second_count'] >= limit.requests_per_second:
                    # Calculate exact wait time
                    method_data = self.real_time_usage[api_key][method_name]
                    oldest_request = min(method_data['per_second']) if method_data['per_second'] else now
                    wait_time = 1.0 - (now - oldest_request)
                    return False, "per_second", max(0, wait_time)
            
            # Check per-minute limit
            if limit.requests_per_minute:
                if cache['per_minute_count'] >= limit.requests_per_minute:
                    method_data = self.real_time_usage[api_key][method_name]
                    oldest_request = min(method_data['per_minute']) if method_data['per_minute'] else now
                    wait_time = 60.0 - (now - oldest_request)
                    return False, "per_minute", max(0, wait_time)
            
            # Check per-hour limit
            if limit.requests_per_hour:
                if cache['per_hour_count'] >= limit.requests_per_hour:
                    method_data = self.real_time_usage[api_key][method_name]
                    oldest_request = min(method_data['per_hour']) if method_data['per_hour'] else now
                    wait_time = 3600.0 - (now - oldest_request)
                    return False, "per_hour", max(0, wait_time)
            
            return True, None, None
    
    def get_optimal_key_for_method(self, method_name: str, api_keys: List[str]) -> Optional[str]:
        """
        Get the optimal API key for a specific method based on current usage.
        """
        available_keys = []
        
        for api_key in api_keys:
            can_make, reason, wait_time = self.can_make_method_request(api_key, method_name)
            if can_make:
                available_keys.append(api_key)
        
        if available_keys:
            # Return the first available key (can be enhanced with load balancing)
            return available_keys[0]
        
        return None

class EnhancedAngelOneAPILimits(BaseAPILimits):
    """
    ENHANCED API Limits with real-time per-method per-API-key tracking.
    
    This extends the base API limits from api_limit_config.py with real-time 
    monitoring capabilities and intelligent load balancing across methods and API keys.
    """
    
    def __init__(self):
        super().__init__()
        self.real_time_tracker = RealTimeMethodTracker()
        
    def record_method_usage(self, api_key: str, method_name: str):
        """Record usage of a specific method on a specific API key."""
        self.real_time_tracker.record_method_usage(api_key, method_name)
    
    def can_make_method_request(self, api_key: str, method_name: str) -> tuple[bool, Optional[str], Optional[float]]:
        """Check if a method can be called on a specific API key."""
        return self.real_time_tracker.can_make_method_request(api_key, method_name)
    
    def get_optimal_key_for_method(self, method_name: str, api_keys: List[str]) -> Optional[str]:
        """Get the best API key for a specific method."""
        return self.real_time_tracker.get_optimal_key_for_method(method_name, api_keys)

# Export the enhanced API limits with real-time tracking
# This uses ANGEL_ONE_API_LIMITS from api_limit_config.py for all configuration data
API_LIMITS = EnhancedAngelOneAPILimits()

# Export key components for easy import
__all__ = [
    'APIPriority',
    'APIMethodLimit', 
    'EnhancedAngelOneAPILimits',
    'RealTimeMethodTracker',
    'API_LIMITS',
    'ANGEL_ONE_API_LIMITS'
]

if __name__ == "__main__":
    # Test the enhanced system
    test_keys = ["API_KEY_1", "API_KEY_2", "API_KEY_3", "API_KEY_4", "API_KEY_5"]
    
    print("🔥 TESTING ENHANCED REAL-TIME API LIMITS SYSTEM")
    print("=" * 80)
    
    # Display configuration summary using the config module
    CONFIG_API_LIMITS.print_limits_summary(num_api_keys=len(test_keys))
    
    # Test optimal key selection
    optimal_key = API_LIMITS.get_optimal_key_for_method("get_ltp_data", test_keys)
    print(f"\n🎯 Optimal key for get_ltp_data: {optimal_key}")


