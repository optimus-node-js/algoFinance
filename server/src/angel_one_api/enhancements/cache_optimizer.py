"""
Cache Optimizer for Angel One API
=================================

Intelligent caching system that optimizes API performance through
strategic response caching and cache management.

Features:
- Method-specific caching strategies
- Adaptive TTL based on data freshness requirements
- Cache invalidation triggers
- Performance monitoring and optimization
- Memory-efficient cache management

Author: HFT Trading System
Created: September 23, 2025
"""

import time
import logging
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime, timedelta
from enum import Enum

logger = logging.getLogger(__name__)

class CacheStrategy(Enum):
    """Cache strategy types for different data categories."""
    TIME_BASED = "time_based"          # Cache based on time windows
    INVALIDATE_ON_TRADE = "invalidate_on_trade"  # Invalidate when trades occur
    APPEND_ONLY = "append_only"        # Data only grows (trade history)
    SESSION_BASED = "session_based"    # Cache for session duration
    CONTENT_BASED = "content_based"    # Cache based on content hash
    REAL_TIME = "real_time"           # Short-lived cache for real-time data

class CacheOptimizer:
    """
    Advanced cache optimizer for Angel One API operations.
    
    Implements intelligent caching strategies to maximize performance
    while ensuring data freshness and consistency.
    """
    
    def __init__(self):
        """Initialize CacheOptimizer with method configurations."""
        self.cache_strategies = self._get_cache_strategies()
        self.performance_metrics = {
            "cache_hits": 0,
            "cache_misses": 0,
            "cache_invalidations": 0,
            "total_requests": 0,
            "response_time_savings": 0.0,
            "start_time": time.time()
        }
        
    def _get_cache_strategies(self) -> Dict[str, Dict[str, Any]]:
        """Get caching strategies for different Angel One API methods."""
        return {
            # Real-time market data (short cache)
            "get_ltp_data": {
                "strategy": CacheStrategy.REAL_TIME,
                "ttl": 5,
                "description": "Real-time LTP data with 5-second cache"
            },
            "get_quote": {
                "strategy": CacheStrategy.REAL_TIME,
                "ttl": 10,
                "description": "Market quotes with 10-second cache"
            },
            "get_market_status": {
                "strategy": CacheStrategy.TIME_BASED,
                "ttl": 60,
                "description": "Market status with 1-minute cache"
            },
            
            # Account data (medium cache with trade invalidation)
            "get_order_book": {
                "strategy": CacheStrategy.INVALIDATE_ON_TRADE,
                "ttl": 30,
                "description": "Order book invalidated on new trades"
            },
            "get_position": {
                "strategy": CacheStrategy.INVALIDATE_ON_TRADE,
                "ttl": 60,
                "description": "Positions invalidated on new trades"
            },
            "get_rms": {
                "strategy": CacheStrategy.INVALIDATE_ON_TRADE,
                "ttl": 120,
                "description": "RMS data invalidated on new trades"
            },
            "get_holding": {
                "strategy": CacheStrategy.TIME_BASED,
                "ttl": 300,
                "description": "Holdings with 5-minute cache"
            },
            
            # Trade history (append-only cache)
            "get_trade_book": {
                "strategy": CacheStrategy.APPEND_ONLY,
                "ttl": 300,
                "description": "Trade book with append-only strategy"
            },
            "order_details": {
                "strategy": CacheStrategy.CONTENT_BASED,
                "ttl": 600,
                "description": "Order details with content-based caching"
            },
            
            # Static/semi-static data (long cache)
            "get_profile": {
                "strategy": CacheStrategy.SESSION_BASED,
                "ttl": 3600,
                "description": "User profile cached for session"
            },
            "search_scrip": {
                "strategy": CacheStrategy.CONTENT_BASED,
                "ttl": 1800,
                "description": "Script search with content-based caching"
            },
            "get_all_holding": {
                "strategy": CacheStrategy.TIME_BASED,
                "ttl": 600,
                "description": "All holdings with 10-minute cache"
            },
            
            # Market data with time-based caching
            "get_candle_data": {
                "strategy": CacheStrategy.TIME_BASED,
                "ttl": 180,
                "description": "Candle data with 3-minute cache"
            },
            "get_top_gainers_losers": {
                "strategy": CacheStrategy.TIME_BASED,
                "ttl": 300,
                "description": "Top gainers/losers with 5-minute cache"
            }
        }
    
    def get_optimal_cache_config(
        self,
        method_name: str,
        params: Dict[str, Any],
        current_time: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Get optimal cache configuration for a specific method and parameters.
        
        Args:
            method_name: Name of the Angel One API method
            params: Method parameters
            current_time: Current timestamp (optional)
            
        Returns:
            Dictionary with cache configuration
        """
        current_time = current_time or time.time()
        
        # Get base strategy for method
        base_config = self.cache_strategies.get(method_name, {
            "strategy": CacheStrategy.TIME_BASED,
            "ttl": 60,
            "description": "Default time-based caching"
        })
        
        # Apply dynamic adjustments
        optimized_config = self._apply_dynamic_optimizations(
            method_name, params, base_config, current_time
        )
        
        return optimized_config
    
    def _apply_dynamic_optimizations(
        self,
        method_name: str,
        params: Dict[str, Any],
        base_config: Dict[str, Any],
        current_time: float
    ) -> Dict[str, Any]:
        """Apply dynamic optimizations to cache configuration."""
        config = base_config.copy()
        
        # Market hours optimization
        if self._is_market_hours(current_time):
            # During market hours, reduce TTL for real-time data
            if base_config["strategy"] == CacheStrategy.REAL_TIME:
                config["ttl"] = max(config["ttl"] // 2, 1)
        else:
            # After market hours, increase TTL
            if base_config["strategy"] in [CacheStrategy.REAL_TIME, CacheStrategy.TIME_BASED]:
                config["ttl"] = min(config["ttl"] * 2, 300)
        
        # Parameter-based optimization
        config = self._apply_parameter_optimizations(method_name, params, config)
        
        # Performance-based optimization
        config = self._apply_performance_optimizations(method_name, config)
        
        return config
    
    def _is_market_hours(self, current_time: float) -> bool:
        """Check if current time is within market hours."""
        # Simple market hours check (9:15 AM - 3:30 PM IST, Monday-Friday)
        dt = datetime.fromtimestamp(current_time)
        
        # Skip weekends
        if dt.weekday() >= 5:  # Saturday = 5, Sunday = 6
            return False
        
        # Check time (simplified - doesn't account for holidays)
        market_start = dt.replace(hour=9, minute=15, second=0, microsecond=0)
        market_end = dt.replace(hour=15, minute=30, second=0, microsecond=0)
        
        return market_start <= dt <= market_end
    
    def _apply_parameter_optimizations(
        self,
        method_name: str,
        params: Dict[str, Any],
        config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Apply optimizations based on method parameters."""
        optimized_config = config.copy()
        
        # Symbol-specific optimizations
        if "symboltoken" in params or "tradingsymbol" in params:
            symbol = params.get("tradingsymbol", "") or params.get("symboltoken", "")
            
            # High-volume stocks get shorter cache TTL
            if self._is_high_volume_symbol(symbol):
                optimized_config["ttl"] = max(optimized_config["ttl"] // 2, 1)
        
        # Exchange-specific optimizations
        if "exchange" in params:
            exchange = params["exchange"]
            if exchange in ["NSE", "BSE"]:
                # Major exchanges get optimized caching
                optimized_config["priority"] = "high"
        
        return optimized_config
    
    def _apply_performance_optimizations(
        self,
        method_name: str,
        config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Apply optimizations based on historical performance."""
        optimized_config = config.copy()
        
        # Calculate cache hit rate for this method
        cache_hit_rate = self._get_method_cache_hit_rate(method_name)
        
        # If cache hit rate is low, reduce TTL
        if cache_hit_rate < 0.3:  # Less than 30% hit rate
            optimized_config["ttl"] = max(optimized_config["ttl"] // 2, 5)
            optimized_config["reason"] = "low_hit_rate_optimization"
        
        # If hit rate is very high, can increase TTL slightly
        elif cache_hit_rate > 0.9:  # More than 90% hit rate
            optimized_config["ttl"] = min(optimized_config["ttl"] * 1.2, 600)
            optimized_config["reason"] = "high_hit_rate_optimization"
        
        return optimized_config
    
    def _is_high_volume_symbol(self, symbol: str) -> bool:
        """Check if symbol is high-volume (requires more frequent updates)."""
        # List of high-volume symbols that need frequent updates
        high_volume_symbols = {
            "RELIANCE-EQ", "TCS-EQ", "INFY-EQ", "HINDUNILVR-EQ",
            "HDFC-EQ", "ICICIBANK-EQ", "KOTAKBANK-EQ", "SBIN-EQ",
            "ITC-EQ", "LT-EQ", "AXISBANK-EQ", "MARUTI-EQ"
        }
        
        # Also check by symbol token (common high-volume tokens)
        high_volume_tokens = {
            "2885", "11536", "1594", "356", "1333", "4963",  # RELIANCE, TCS, INFY, etc.
        }
        
        return symbol in high_volume_symbols or symbol in high_volume_tokens
    
    def _get_method_cache_hit_rate(self, method_name: str) -> float:
        """Get cache hit rate for specific method."""
        # This would be implemented with actual metrics storage
        # For now, return default based on method type
        real_time_methods = ["get_ltp_data", "get_quote"]
        if method_name in real_time_methods:
            return 0.4  # Lower hit rate for real-time data
        else:
            return 0.7  # Higher hit rate for other data
    
    def should_invalidate_cache(
        self,
        method_name: str,
        trigger_event: str,
        trigger_params: Dict[str, Any] = None
    ) -> List[str]:
        """
        Determine which cache entries should be invalidated based on trigger event.
        
        Args:
            method_name: Method that triggered the event
            trigger_event: Type of event (trade_placed, order_modified, etc.)
            trigger_params: Parameters of the triggering event
            
        Returns:
            List of cache patterns to invalidate
        """
        invalidation_patterns = []
        
        if trigger_event == "trade_placed":
            # Invalidate position and order data
            invalidation_patterns.extend([
                "account:get_position:*",
                "account:get_order_book:*",
                "account:get_rms:*"
            ])
            
        elif trigger_event == "order_modified":
            # Invalidate order book
            invalidation_patterns.extend([
                "account:get_order_book:*",
                "trading:order_details:*"
            ])
            
        elif trigger_event == "order_cancelled":
            # Invalidate order book and positions
            invalidation_patterns.extend([
                "account:get_order_book:*",
                "account:get_position:*"
            ])
        
        elif trigger_event == "market_data_update":
            # Invalidate market data for specific symbol
            if trigger_params and "symbol" in trigger_params:
                symbol = trigger_params["symbol"]
                invalidation_patterns.extend([
                    f"market:get_ltp_data:*{symbol}*",
                    f"market:get_quote:*{symbol}*"
                ])
        
        return invalidation_patterns
    
    def update_performance_metrics(
        self,
        method_name: str,
        cache_hit: bool,
        response_time: float,
        saved_time: float = 0.0
    ):
        """Update performance metrics for cache optimization."""
        self.performance_metrics["total_requests"] += 1
        
        if cache_hit:
            self.performance_metrics["cache_hits"] += 1
            self.performance_metrics["response_time_savings"] += saved_time
        else:
            self.performance_metrics["cache_misses"] += 1
    
    def get_cache_performance_report(self) -> Dict[str, Any]:
        """Get comprehensive cache performance report."""
        metrics = self.performance_metrics
        total_requests = metrics["total_requests"]
        uptime = time.time() - metrics["start_time"]
        
        if total_requests == 0:
            return {"status": "no_data", "message": "No requests processed yet"}
        
        cache_hit_rate = metrics["cache_hits"] / total_requests
        avg_time_savings = (
            metrics["response_time_savings"] / max(metrics["cache_hits"], 1)
        )
        
        return {
            "total_requests": total_requests,
            "cache_hits": metrics["cache_hits"],
            "cache_misses": metrics["cache_misses"],
            "cache_hit_rate": round(cache_hit_rate * 100, 2),
            "cache_invalidations": metrics["cache_invalidations"],
            "total_time_saved": round(metrics["response_time_savings"], 2),
            "average_time_savings_per_hit": round(avg_time_savings, 3),
            "requests_per_minute": round(total_requests / max(uptime / 60, 1), 1),
            "uptime_minutes": round(uptime / 60, 1),
            "efficiency_score": round(cache_hit_rate * avg_time_savings * 100, 1)
        }
    
    def optimize_cache_strategy(
        self,
        method_name: str,
        historical_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Optimize cache strategy based on historical performance data.
        
        Args:
            method_name: Method to optimize
            historical_data: Historical performance data
            
        Returns:
            Optimized cache configuration
        """
        current_config = self.cache_strategies.get(method_name, {})
        
        # Analyze historical data
        hit_rate = historical_data.get("hit_rate", 0.5)
        avg_response_time = historical_data.get("avg_response_time", 100)
        request_frequency = historical_data.get("request_frequency", 1)
        
        # Create optimized configuration
        optimized_config = current_config.copy()
        
        # Adjust TTL based on hit rate and frequency
        if hit_rate < 0.3 and request_frequency > 10:
            # Low hit rate with high frequency - reduce TTL
            optimized_config["ttl"] = max(optimized_config.get("ttl", 60) // 2, 5)
        elif hit_rate > 0.8 and avg_response_time > 200:
            # High hit rate with slow responses - increase TTL
            optimized_config["ttl"] = min(optimized_config.get("ttl", 60) * 1.5, 600)
        
        # Add optimization metadata
        optimized_config["optimization_applied"] = True
        optimized_config["optimization_reason"] = f"hit_rate={hit_rate:.2f}, freq={request_frequency}"
        optimized_config["optimization_timestamp"] = time.time()
        
        return optimized_config
