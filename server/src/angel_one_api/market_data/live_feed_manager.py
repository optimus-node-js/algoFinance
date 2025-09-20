"""
Angel One Live Feed Manager
===========================

Real-time market data feed management with intelligent caching,
bulk processing, and rate optimization.

Consolidates LTP logic from:
- ai/master/ai_master_orchestrator.py (_get_live_ltp method)
- Various scattered LTP calls across services

Features:
- Intelligent caching with TTL
- Bulk LTP fetching for efficiency
- Real-time price validation
- Rate-optimized streaming
- Automatic instrument token resolution
- Price change detection and alerts

Author: AI Trading System
"""

import time
import asyncio
from typing import Dict, List, Optional, Any, Set
import logging
from datetime import datetime, UTC, timedelta
from dataclasses import dataclass
import json

# Import our rate limiting and methods
from ..rate_limiter.rate_controller import rate_limited, APIPriority
from ..methods.get_ltp_data import get_ltp_data, get_bulk_ltp_data

logger = logging.getLogger(__name__)

class LiveFeedError(Exception):
    """Raised when live feed operations fail."""
    pass

@dataclass
class PriceUpdate:
    """Price update data structure."""
    symbol: str
    ltp: float
    previous_ltp: float
    change: float
    change_pct: float
    timestamp: str
    volume: Optional[int] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'symbol': self.symbol,
            'ltp': self.ltp,
            'previous_ltp': self.previous_ltp,
            'change': self.change,
            'change_pct': self.change_pct,
            'timestamp': self.timestamp,
            'volume': self.volume
        }

@dataclass
class CachedLTP:
    """Cached LTP data structure."""
    symbol: str
    token: str
    ltp: float
    timestamp: float
    ttl: float = 5.0  # 5 second TTL for LTP cache
    
    def is_expired(self) -> bool:
        return time.time() - self.timestamp > self.ttl
    
    def age_seconds(self) -> float:
        return time.time() - self.timestamp

class LiveFeedManager:
    """
    Advanced real-time market data feed management.
    
    Provides intelligent caching, bulk processing, and real-time
    streaming capabilities for Angel One market data.
    """
    
    def __init__(self, cache_ttl: float = 5.0, max_cache_size: int = 10000):
        self._ltp_cache: Dict[str, CachedLTP] = {}
        self._price_history: Dict[str, List[float]] = {}
        self._subscriptions: Set[str] = set()
        self._cache_ttl = cache_ttl
        self._max_cache_size = max_cache_size
        self._last_cleanup = time.time()
        self._cleanup_interval = 60  # Clean cache every minute
        self._price_change_callbacks: List[callable] = []
        
        # Performance metrics
        self._metrics = {
            'cache_hits': 0,
            'cache_misses': 0,
            'api_calls': 0,
            'bulk_requests': 0,
            'price_updates': 0
        }
    
    async def get_ltp(self, symbol: str, token: str, exchange: str = "NSE") -> float:
        """
        Get Last Traded Price with intelligent caching.
        
        Args:
            symbol: Trading symbol
            token: Instrument token
            exchange: Exchange name
            
        Returns:
            float: Current LTP
        """
        try:
            # Check cache first
            cache_key = f"{symbol}_{token}"
            cached_ltp = self._ltp_cache.get(cache_key)
            
            if cached_ltp and not cached_ltp.is_expired():
                self._metrics['cache_hits'] += 1
                logger.debug(f"📊 LTP cache hit: {symbol} = ₹{cached_ltp.ltp:.2f}")
                return cached_ltp.ltp
            
            # Cache miss - fetch from API
            self._metrics['cache_misses'] += 1
            self._metrics['api_calls'] += 1
            
            # Use our rate-limited method
            ltp = await get_ltp_data(symbol, token, exchange)
            
            if ltp is None:
                raise LiveFeedError(f"Failed to fetch LTP for {symbol}")
            
            # Validate price
            validated_ltp = self._validate_price(symbol, ltp)
            
            # Update cache
            self._update_cache(symbol, token, validated_ltp)
            
            # Track price changes
            await self._track_price_change(symbol, validated_ltp)
            
            # Cleanup cache if needed
            await self._cleanup_cache_if_needed()
            
            logger.debug(f"📊 LTP fetched: {symbol} = ₹{validated_ltp:.2f}")
            return validated_ltp
            
        except Exception as e:
            logger.error(f"❌ LTP fetch failed for {symbol}: {e}")
            raise LiveFeedError(f"LTP fetch failed for {symbol}: {e}")
    
    async def get_bulk_ltp(
        self, 
        symbols_tokens: List[Dict[str, str]], 
        exchange: str = "NSE"
    ) -> Dict[str, float]:
        """
        Get LTP for multiple symbols efficiently.
        
        Args:
            symbols_tokens: List of dicts with 'symbol' and 'token' keys
            exchange: Exchange name
            
        Returns:
            Dict mapping symbols to LTP values
        """
        try:
            if not symbols_tokens:
                return {}
            
            logger.info(f"📊 Bulk LTP request: {len(symbols_tokens)} symbols")
            
            # Separate cached and uncached symbols
            cached_results = {}
            uncached_requests = []
            
            for item in symbols_tokens:
                symbol = item['symbol']
                token = item['token']
                cache_key = f"{symbol}_{token}"
                
                cached_ltp = self._ltp_cache.get(cache_key)
                if cached_ltp and not cached_ltp.is_expired():
                    cached_results[symbol] = cached_ltp.ltp
                    self._metrics['cache_hits'] += 1
                else:
                    uncached_requests.append(item)
                    self._metrics['cache_misses'] += 1
            
            # Fetch uncached data
            fresh_results = {}
            if uncached_requests:
                self._metrics['bulk_requests'] += 1
                
                # Use bulk API method
                fresh_results = await get_bulk_ltp_data(uncached_requests, exchange)
                
                # Update cache with fresh data
                for item in uncached_requests:
                    symbol = item['symbol']
                    token = item['token']
                    
                    if symbol in fresh_results:
                        ltp = fresh_results[symbol]
                        validated_ltp = self._validate_price(symbol, ltp)
                        fresh_results[symbol] = validated_ltp
                        
                        # Update cache
                        self._update_cache(symbol, token, validated_ltp)
                        
                        # Track price changes
                        await self._track_price_change(symbol, validated_ltp)
            
            # Combine results
            all_results = {**cached_results, **fresh_results}
            
            # Cleanup cache if needed
            await self._cleanup_cache_if_needed()
            
            success_count = len(all_results)
            cache_hit_rate = (self._metrics['cache_hits'] / 
                            (self._metrics['cache_hits'] + self._metrics['cache_misses'])) * 100
            
            logger.info(
                f"✅ Bulk LTP complete: {success_count}/{len(symbols_tokens)} symbols, "
                f"Cache hit rate: {cache_hit_rate:.1f}%"
            )
            
            return all_results
            
        except Exception as e:
            logger.error(f"❌ Bulk LTP fetch failed: {e}")
            raise LiveFeedError(f"Bulk LTP fetch failed: {e}")
    
    def _validate_price(self, symbol: str, ltp: float) -> float:
        """
        Validate LTP price for sanity.
        
        Args:
            symbol: Trading symbol
            ltp: LTP value to validate
            
        Returns:
            float: Validated LTP
        """
        if ltp <= 0:
            logger.warning(f"⚠️ Invalid LTP for {symbol}: {ltp}")
            return 0.0
        
        if ltp > 100000:  # Sanity check for extremely high prices
            logger.warning(f"⚠️ Suspicious high LTP for {symbol}: ₹{ltp}")
        
        if ltp < 0.01:  # Sanity check for extremely low prices
            logger.warning(f"⚠️ Suspicious low LTP for {symbol}: ₹{ltp}")
        
        return ltp
    
    def _update_cache(self, symbol: str, token: str, ltp: float):
        """Update LTP cache with new data."""
        cache_key = f"{symbol}_{token}"
        
        self._ltp_cache[cache_key] = CachedLTP(
            symbol=symbol,
            token=token,
            ltp=ltp,
            timestamp=time.time(),
            ttl=self._cache_ttl
        )
        
        # Maintain cache size limit
        if len(self._ltp_cache) > self._max_cache_size:
            self._cleanup_cache_by_size()
    
    async def _track_price_change(self, symbol: str, new_ltp: float):
        """Track price changes and trigger callbacks."""
        try:
            # Get previous LTP from history
            if symbol not in self._price_history:
                self._price_history[symbol] = []
            
            history = self._price_history[symbol]
            previous_ltp = history[-1] if history else new_ltp
            
            # Add to history (keep last 10 prices)
            history.append(new_ltp)
            if len(history) > 10:
                history.pop(0)
            
            # Calculate change
            if previous_ltp != new_ltp:
                change = new_ltp - previous_ltp
                change_pct = (change / previous_ltp) * 100 if previous_ltp > 0 else 0
                
                price_update = PriceUpdate(
                    symbol=symbol,
                    ltp=new_ltp,
                    previous_ltp=previous_ltp,
                    change=change,
                    change_pct=change_pct,
                    timestamp=datetime.now(UTC).isoformat()
                )
                
                # Trigger callbacks
                await self._notify_price_change(price_update)
                
                self._metrics['price_updates'] += 1
                
                if abs(change_pct) > 1.0:  # Log significant changes
                    logger.info(f"📈 Price change: {symbol} {change_pct:+.2f}% = ₹{new_ltp:.2f}")
        
        except Exception as e:
            logger.warning(f"⚠️ Price change tracking failed for {symbol}: {e}")
    
    async def _notify_price_change(self, price_update: PriceUpdate):
        """Notify registered callbacks of price changes."""
        for callback in self._price_change_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(price_update)
                else:
                    callback(price_update)
            except Exception as e:
                logger.warning(f"⚠️ Price change callback failed: {e}")
    
    def register_price_change_callback(self, callback: callable):
        """Register a callback for price changes."""
        self._price_change_callbacks.append(callback)
        logger.info(f"✅ Price change callback registered: {callback.__name__}")
    
    def unregister_price_change_callback(self, callback: callable):
        """Unregister a price change callback."""
        if callback in self._price_change_callbacks:
            self._price_change_callbacks.remove(callback)
            logger.info(f"🚪 Price change callback unregistered: {callback.__name__}")
    
    async def _cleanup_cache_if_needed(self):
        """Clean up expired cache entries if needed."""
        current_time = time.time()
        
        if current_time - self._last_cleanup > self._cleanup_interval:
            await self._cleanup_expired_cache()
            self._last_cleanup = current_time
    
    async def _cleanup_expired_cache(self):
        """Remove expired cache entries."""
        expired_keys = [
            key for key, cached_ltp in self._ltp_cache.items()
            if cached_ltp.is_expired()
        ]
        
        for key in expired_keys:
            del self._ltp_cache[key]
        
        if expired_keys:
            logger.debug(f"🧹 Cleaned {len(expired_keys)} expired cache entries")
    
    def _cleanup_cache_by_size(self):
        """Remove oldest cache entries to maintain size limit."""
        if len(self._ltp_cache) <= self._max_cache_size:
            return
        
        # Sort by timestamp and remove oldest
        sorted_cache = sorted(
            self._ltp_cache.items(),
            key=lambda x: x[1].timestamp
        )
        
        entries_to_remove = len(self._ltp_cache) - self._max_cache_size
        
        for i in range(entries_to_remove):
            key, _ = sorted_cache[i]
            del self._ltp_cache[key]
        
        logger.debug(f"🧹 Cleaned {entries_to_remove} cache entries to maintain size limit")
    
    def subscribe_to_symbol(self, symbol: str):
        """Subscribe to real-time updates for a symbol."""
        self._subscriptions.add(symbol)
        logger.info(f"📡 Subscribed to: {symbol}")
    
    def unsubscribe_from_symbol(self, symbol: str):
        """Unsubscribe from real-time updates for a symbol."""
        self._subscriptions.discard(symbol)
        logger.info(f"📡 Unsubscribed from: {symbol}")
    
    def get_subscriptions(self) -> Set[str]:
        """Get current subscriptions."""
        return self._subscriptions.copy()
    
    def get_cached_symbols(self) -> List[str]:
        """Get list of currently cached symbols."""
        return [cached.symbol for cached in self._ltp_cache.values()]
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        total_requests = self._metrics['cache_hits'] + self._metrics['cache_misses']
        hit_rate = (self._metrics['cache_hits'] / total_requests * 100) if total_requests > 0 else 0
        
        return {
            'cache_size': len(self._ltp_cache),
            'max_cache_size': self._max_cache_size,
            'cache_hit_rate': hit_rate,
            'total_requests': total_requests,
            'api_calls_saved': self._metrics['cache_hits'],
            'subscriptions': len(self._subscriptions),
            'price_updates_tracked': self._metrics['price_updates'],
            'metrics': self._metrics.copy()
        }
    
    def get_price_history(self, symbol: str) -> List[float]:
        """Get price history for a symbol."""
        return self._price_history.get(symbol, []).copy()
    
    async def warm_cache(self, symbols_tokens: List[Dict[str, str]]):
        """Pre-populate cache with LTP data."""
        logger.info(f"🔥 Warming LTP cache with {len(symbols_tokens)} symbols")
        
        try:
            await self.get_bulk_ltp(symbols_tokens)
            logger.info(f"✅ Cache warmed successfully")
        except Exception as e:
            logger.error(f"❌ Cache warming failed: {e}")
    
    def clear_cache(self):
        """Clear all cached data."""
        self._ltp_cache.clear()
        self._price_history.clear()
        logger.info("🧹 LTP cache cleared")
    
    def export_cache(self) -> Dict[str, Any]:
        """Export cache data for backup/analysis."""
        return {
            'timestamp': datetime.now(UTC).isoformat(),
            'cache_data': {
                key: {
                    'symbol': cached.symbol,
                    'token': cached.token,
                    'ltp': cached.ltp,
                    'timestamp': cached.timestamp,
                    'age_seconds': cached.age_seconds()
                }
                for key, cached in self._ltp_cache.items()
            },
            'price_history': self._price_history.copy(),
            'subscriptions': list(self._subscriptions),
            'stats': self.get_cache_stats()
        }

# Global live feed manager instance
_live_feed_manager = None

def get_live_feed_manager() -> LiveFeedManager:
    """Get the global LiveFeedManager instance."""
    global _live_feed_manager
    if _live_feed_manager is None:
        _live_feed_manager = LiveFeedManager()
    return _live_feed_manager
