"""
Angel One Instrument Manager
============================

Intelligent instrument token management and caching system.

Consolidates instrument logic from:
- services/stock_discovery/stock_discovery_service.py
- ai/master/ai_master_orchestrator.py (_get_real_instrument_token)
- Various scattered instrument token lookups

Features:
- MongoDB-backed persistent caching
- Intelligent search and matching
- Bulk instrument resolution
- 24-hour TTL automatic cleanup
- Fuzzy matching capabilities
- Performance optimizations

Author: AI Trading System
"""

import time
import asyncio
from typing import Dict, List, Optional, Any, Tuple
import logging
from datetime import datetime, UTC, timedelta
from dataclasses import dataclass

# Import our rate limiting and methods
from ..rate_limiter.rate_controller import rate_limited, APIPriority
from ..methods.search_scrip import search_scrip, find_best_equity_match

logger = logging.getLogger(__name__)

class InstrumentError(Exception):
    """Raised when instrument operations fail."""
    pass

@dataclass
class InstrumentInfo:
    """Instrument information data structure."""
    symbol: str
    token: str
    exchange: str
    name: str
    expiry: Optional[str] = None
    strike: Optional[float] = None
    lotsize: Optional[int] = None
    instrumenttype: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'symbol': self.symbol,
            'token': self.token,
            'exchange': self.exchange,
            'name': self.name,
            'expiry': self.expiry,
            'strike': self.strike,
            'lotsize': self.lotsize,
            'instrumenttype': self.instrumenttype
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'InstrumentInfo':
        return cls(
            symbol=data.get('symbol', ''),
            token=data.get('token', ''),
            exchange=data.get('exchange', ''),
            name=data.get('name', ''),
            expiry=data.get('expiry'),
            strike=data.get('strike'),
            lotsize=data.get('lotsize'),
            instrumenttype=data.get('instrumenttype')
        )

class InstrumentManager:
    """
    Advanced instrument token management with intelligent caching.
    
    Provides high-performance instrument resolution with MongoDB persistence,
    intelligent search, and bulk operations.
    """
    
    def __init__(self):
        self._memory_cache: Dict[str, InstrumentInfo] = {}
        self._search_cache: Dict[str, List[InstrumentInfo]] = {}
        self._last_cleanup = time.time()
        self._cleanup_interval = 3600  # 1 hour
        self._cache_ttl = 24 * 3600  # 24 hours
        
        # Performance metrics
        self._metrics = {
            'cache_hits': 0,
            'cache_misses': 0,
            'api_searches': 0,
            'mongodb_reads': 0,
            'mongodb_writes': 0,
            'bulk_requests': 0
        }
    
    async def get_instrument_token(
        self, 
        symbol: str, 
        exchange: str = "NSE"
    ) -> Optional[str]:
        """
        Get instrument token for a symbol with intelligent caching.
        
        Args:
            symbol: Trading symbol (e.g., "RELIANCE", "RELIANCE-EQ")
            exchange: Exchange name
            
        Returns:
            str: Instrument token or None if not found
        """
        try:
            # Normalize symbol
            normalized_symbol = self._normalize_symbol(symbol, exchange)
            cache_key = f"{normalized_symbol}_{exchange}"
            
            # Check memory cache first
            if cache_key in self._memory_cache:
                self._metrics['cache_hits'] += 1
                token = self._memory_cache[cache_key].token
                logger.debug(f"🎯 Token cache hit: {symbol} = {token}")
                return token
            
            # Check MongoDB cache
            mongodb_result = await self._get_cached_token_from_mongodb(normalized_symbol, exchange)
            if mongodb_result:
                self._metrics['cache_hits'] += 1
                self._metrics['mongodb_reads'] += 1
                
                # Update memory cache
                self._memory_cache[cache_key] = mongodb_result
                
                logger.debug(f"🎯 MongoDB cache hit: {symbol} = {mongodb_result.token}")
                return mongodb_result.token
            
            # Cache miss - search via API
            self._metrics['cache_misses'] += 1
            instrument = await self._search_and_cache_instrument(symbol, exchange)
            
            if instrument:
                logger.info(f"✅ Instrument resolved: {symbol} = {instrument.token}")
                return instrument.token
            else:
                logger.warning(f"⚠️ Instrument not found: {symbol}")
                return None
                
        except Exception as e:
            logger.error(f"❌ Instrument token fetch failed for {symbol}: {e}")
            raise InstrumentError(f"Failed to get token for {symbol}: {e}")
    
    async def get_bulk_instrument_tokens(
        self, 
        symbols: List[str], 
        exchange: str = "NSE"
    ) -> Dict[str, Optional[str]]:
        """
        Get instrument tokens for multiple symbols efficiently.
        
        Args:
            symbols: List of trading symbols
            exchange: Exchange name
            
        Returns:
            Dict mapping symbols to tokens (None if not found)
        """
        try:
            if not symbols:
                return {}
            
            logger.info(f"🎯 Bulk token resolution: {len(symbols)} symbols")
            self._metrics['bulk_requests'] += 1
            
            results = {}
            uncached_symbols = []
            
            # Check caches for all symbols
            for symbol in symbols:
                normalized_symbol = self._normalize_symbol(symbol, exchange)
                cache_key = f"{normalized_symbol}_{exchange}"
                
                # Memory cache check
                if cache_key in self._memory_cache:
                    results[symbol] = self._memory_cache[cache_key].token
                    self._metrics['cache_hits'] += 1
                    continue
                
                # MongoDB cache check
                mongodb_result = await self._get_cached_token_from_mongodb(normalized_symbol, exchange)
                if mongodb_result:
                    results[symbol] = mongodb_result.token
                    self._memory_cache[cache_key] = mongodb_result
                    self._metrics['cache_hits'] += 1
                    self._metrics['mongodb_reads'] += 1
                    continue
                
                # Need to search via API
                uncached_symbols.append(symbol)
                self._metrics['cache_misses'] += 1
            
            # Search uncached symbols
            if uncached_symbols:
                logger.info(f"🔍 Searching {len(uncached_symbols)} uncached symbols")
                
                for symbol in uncached_symbols:
                    instrument = await self._search_and_cache_instrument(symbol, exchange)
                    results[symbol] = instrument.token if instrument else None
            
            # Statistics
            found_count = sum(1 for token in results.values() if token is not None)
            cache_hit_rate = (self._metrics['cache_hits'] / 
                            (self._metrics['cache_hits'] + self._metrics['cache_misses'])) * 100
            
            logger.info(
                f"✅ Bulk token resolution complete: {found_count}/{len(symbols)} found, "
                f"Cache hit rate: {cache_hit_rate:.1f}%"
            )
            
            return results
            
        except Exception as e:
            logger.error(f"❌ Bulk token resolution failed: {e}")
            raise InstrumentError(f"Bulk token resolution failed: {e}")
    
    async def search_instruments(
        self, 
        query: str, 
        exchange: str = "NSE"
    ) -> List[InstrumentInfo]:
        """
        Search for instruments matching a query.
        
        Args:
            query: Search query
            exchange: Exchange name
            
        Returns:
            List of matching instruments
        """
        try:
            # Check search cache
            cache_key = f"search_{query}_{exchange}"
            if cache_key in self._search_cache:
                logger.debug(f"🔍 Search cache hit: {query}")
                return self._search_cache[cache_key]
            
            # Search via API
            self._metrics['api_searches'] += 1
            
            search_results = await search_scrip(query, exchange)
            
            if not search_results['success']:
                logger.warning(f"⚠️ Search failed for {query}: {search_results.get('error')}")
                return []
            
            # Convert to InstrumentInfo objects
            instruments = []
            for result in search_results.get('results', []):
                instrument = InstrumentInfo(
                    symbol=result.get('tradingsymbol', ''),
                    token=result.get('symboltoken', ''),
                    exchange=result.get('exchange', exchange),
                    name=result.get('name', ''),
                    expiry=result.get('expiry'),
                    strike=result.get('strike'),
                    lotsize=result.get('lotsize'),
                    instrumenttype=result.get('instrumenttype')
                )
                instruments.append(instrument)
            
            # Cache search results
            self._search_cache[cache_key] = instruments
            
            # Cache individual instruments
            for instrument in instruments:
                await self._cache_instrument_to_mongodb(instrument)
                
                cache_key = f"{instrument.symbol}_{instrument.exchange}"
                self._memory_cache[cache_key] = instrument
            
            logger.info(f"✅ Search complete: {query} found {len(instruments)} instruments")
            return instruments
            
        except Exception as e:
            logger.error(f"❌ Instrument search failed for {query}: {e}")
            raise InstrumentError(f"Instrument search failed for {query}: {e}")
    
    async def _search_and_cache_instrument(
        self, 
        symbol: str, 
        exchange: str
    ) -> Optional[InstrumentInfo]:
        """Search for instrument and cache the result."""
        try:
            # Use our best equity match function
            match_result = await find_best_equity_match(symbol, exchange)
            
            if not match_result['success'] or not match_result.get('best_match'):
                return None
            
            best_match = match_result['best_match']
            
            instrument = InstrumentInfo(
                symbol=best_match.get('tradingsymbol', ''),
                token=best_match.get('symboltoken', ''),
                exchange=best_match.get('exchange', exchange),
                name=best_match.get('name', ''),
                instrumenttype=best_match.get('instrumenttype')
            )
            
            # Cache to MongoDB and memory
            await self._cache_instrument_to_mongodb(instrument)
            
            cache_key = f"{instrument.symbol}_{instrument.exchange}"
            self._memory_cache[cache_key] = instrument
            
            return instrument
            
        except Exception as e:
            logger.error(f"❌ Search and cache failed for {symbol}: {e}")
            return None
    
    def _normalize_symbol(self, symbol: str, exchange: str) -> str:
        """
        Normalize symbol for consistent caching.
        
        Args:
            symbol: Raw symbol
            exchange: Exchange name
            
        Returns:
            str: Normalized symbol
        """
        # Remove common suffixes if not present
        normalized = symbol.upper().strip()
        
        if exchange == "NSE" and not normalized.endswith("-EQ"):
            # Try both with and without -EQ suffix
            return normalized
        
        return normalized
    
    async def _get_cached_token_from_mongodb(
        self, 
        symbol: str, 
        exchange: str
    ) -> Optional[InstrumentInfo]:
        """Get cached token from MongoDB."""
        try:
            # Get MongoDB connection
            from core.connections import ConnectionManager
            
            mongo_client = ConnectionManager.get_mongodb_client()
            if not mongo_client:
                return None
            
            db = mongo_client.trading_system
            collection = db.instrument_tokens
            
            # Query for the instrument
            query = {
                'symbol': symbol,
                'exchange': exchange,
                'created_at': {
                    '$gte': datetime.now(UTC) - timedelta(hours=24)  # 24-hour TTL
                }
            }
            
            result = collection.find_one(query)
            
            if result:
                return InstrumentInfo.from_dict(result)
            
            return None
            
        except Exception as e:
            logger.warning(f"⚠️ MongoDB cache read failed for {symbol}: {e}")
            return None
    
    async def _cache_instrument_to_mongodb(self, instrument: InstrumentInfo):
        """Cache instrument to MongoDB."""
        try:
            # Get MongoDB connection
            from core.connections import ConnectionManager
            
            mongo_client = ConnectionManager.get_mongodb_client()
            if not mongo_client:
                return
            
            db = mongo_client.trading_system
            collection = db.instrument_tokens
            
            # Prepare document
            document = instrument.to_dict()
            document['created_at'] = datetime.now(UTC)
            document['expires_at'] = datetime.now(UTC) + timedelta(hours=24)
            
            # Upsert to avoid duplicates
            filter_query = {
                'symbol': instrument.symbol,
                'exchange': instrument.exchange
            }
            
            collection.replace_one(filter_query, document, upsert=True)
            self._metrics['mongodb_writes'] += 1
            
            logger.debug(f"💾 Cached to MongoDB: {instrument.symbol} = {instrument.token}")
            
        except Exception as e:
            logger.warning(f"⚠️ MongoDB cache write failed for {instrument.symbol}: {e}")
    
    async def bulk_cache_instruments(self, instruments: List[InstrumentInfo]):
        """Bulk cache instruments to MongoDB."""
        try:
            if not instruments:
                return
            
            # Get MongoDB connection
            from core.connections import ConnectionManager
            
            mongo_client = ConnectionManager.get_mongodb_client()
            if not mongo_client:
                return
            
            db = mongo_client.trading_system
            collection = db.instrument_tokens
            
            # Prepare documents
            documents = []
            for instrument in instruments:
                document = instrument.to_dict()
                document['created_at'] = datetime.now(UTC)
                document['expires_at'] = datetime.now(UTC) + timedelta(hours=24)
                documents.append(document)
            
            # Bulk insert
            if documents:
                # Use upsert operations for bulk
                operations = []
                for doc in documents:
                    filter_query = {
                        'symbol': doc['symbol'],
                        'exchange': doc['exchange']
                    }
                    operations.append(
                        pymongo.ReplaceOne(filter_query, doc, upsert=True)
                    )
                
                if operations:
                    collection.bulk_write(operations)
                    self._metrics['mongodb_writes'] += len(operations)
                    
                    logger.info(f"💾 Bulk cached {len(instruments)} instruments to MongoDB")
            
        except Exception as e:
            logger.error(f"❌ Bulk MongoDB cache failed: {e}")
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        total_requests = self._metrics['cache_hits'] + self._metrics['cache_misses']
        hit_rate = (self._metrics['cache_hits'] / total_requests * 100) if total_requests > 0 else 0
        
        return {
            'memory_cache_size': len(self._memory_cache),
            'search_cache_size': len(self._search_cache),
            'cache_hit_rate': hit_rate,
            'total_requests': total_requests,
            'api_calls_saved': self._metrics['cache_hits'],
            'metrics': self._metrics.copy()
        }
    
    def clear_cache(self):
        """Clear all cached data."""
        self._memory_cache.clear()
        self._search_cache.clear()
        logger.info("🧹 Instrument cache cleared")
    
    async def cleanup_expired_mongodb_cache(self):
        """Clean up expired entries from MongoDB."""
        try:
            # Get MongoDB connection
            from core.connections import ConnectionManager
            
            mongo_client = ConnectionManager.get_mongodb_client()
            if not mongo_client:
                return
            
            db = mongo_client.trading_system
            collection = db.instrument_tokens
            
            # Delete expired entries
            result = collection.delete_many({
                'expires_at': {'$lt': datetime.now(UTC)}
            })
            
            if result.deleted_count > 0:
                logger.info(f"🧹 Cleaned {result.deleted_count} expired instrument cache entries")
            
        except Exception as e:
            logger.error(f"❌ MongoDB cleanup failed: {e}")

# Global instrument manager instance
_instrument_manager = None

def get_instrument_manager() -> InstrumentManager:
    """Get the global InstrumentManager instance."""
    global _instrument_manager
    if _instrument_manager is None:
        _instrument_manager = InstrumentManager()
    return _instrument_manager
