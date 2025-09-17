"""
Enhanced Stock Discovery Service
===============================

Comprehensive stock discovery system that:
- Fetches all stocks from MongoDB tickers collection (5000-7000 stocks)
- Validates stocks via Angel One API searchScrip
- Filters and categorizes stocks by type and exchange
- Provides real-time progress tracking
- Caches validated instruments for performance

Author: AI Trading System
Version: 1.0.0
"""

import asyncio
import time
from datetime import datetime, UTC, timedelta
from typing import Dict, List, Optional, Any, Set, Tuple
from dataclasses import dataclass, field
from concurrent.futures import ThreadPoolExecutor
import threading
from collections import defaultdict

# Standard libraries
import sys
import os
import logging

# Project imports
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(current_dir, '..', '..'))

try:
    from core.connections import ConnectionManager
    from core.message_broker import MessageBroker
    from config import settings
    REAL_COMPONENTS = True
except ImportError:
    REAL_COMPONENTS = False

# Always use standard logging for now
import logging
logger = logging.getLogger(__name__)

# Configure logging
if not REAL_COMPONENTS:
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    logger = logging.getLogger(__name__)

@dataclass
class StockInfo:
    """Information about a discovered stock."""
    symbol: str
    name: str = ""
    exchange: str = "NSE"
    symbol_token: str = ""
    instrument_type: str = "EQ"
    lot_size: int = 1
    tick_size: float = 0.05
    is_valid: bool = False
    last_validated: Optional[datetime] = None
    validation_source: str = "unknown"  # mongodb, api, cache
    api_data: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def trading_symbol(self) -> str:
        """Get trading symbol in Angel One format."""
        if self.symbol.endswith('-EQ'):
            return self.symbol
        return f"{self.symbol}-EQ"

class StockDiscoveryService:
    """
    Enhanced Stock Discovery Service
    
    Discovers and validates stocks from multiple sources:
    1. MongoDB tickers collection (primary source)
    2. Angel One API validation
    3. Instrument cache for performance
    
    Features:
    - Real-time progress tracking
    - Parallel validation processing
    - Intelligent caching
    - Error handling and retry logic
    - Comprehensive logging
    """
    
    def __init__(self):
        """Initialize stock discovery service."""
        
        # Core components
        self.logger = logger
        self.progress_tracker = None
        
        if REAL_COMPONENTS:
            try:
                self.connection_manager = ConnectionManager()
                self.message_broker = MessageBroker()
            except:
                self.connection_manager = None
                self.message_broker = self._create_mock_broker()
        else:
            self.connection_manager = None
            self.message_broker = self._create_mock_broker()
        
        # Discovery state
        self.discovered_stocks: Dict[str, StockInfo] = {}
        self.valid_stocks: Dict[str, StockInfo] = {}
        self.invalid_stocks: Set[str] = set()
        
        # Performance tracking
        self.metrics = {
            'total_discovered': 0,
            'mongodb_stocks': 0,
            'api_validated': 0,
            'cache_hits': 0,
            'validation_errors': 0,
            'processing_time': 0.0
        }
        
        # Threading
        self.executor = ThreadPoolExecutor(max_workers=10, thread_name_prefix="StockDiscovery")
        
        # Setup message subscriptions
        if REAL_COMPONENTS:
            asyncio.create_task(self._setup_message_subscriptions())
        
        if self.logger:
            self.logger.info("🚀 [STOCK_DISCOVERY] Stock Discovery Service initialized")
    
    def _create_mock_broker(self):
        """Create mock message broker for testing."""
        class MockBroker:
            def publish_ai_analysis(self, routing_key, symbol, data):
                print(f"📤 Mock: Published {routing_key} for {symbol}")
        return MockBroker()
    
    async def _setup_message_subscriptions(self):
        """Setup RabbitMQ subscriptions."""
        try:
            # Subscribe to stock discovery requests
            discovery_queues = [
                'stock_discovery_requests',
                'instrument_validation_requests'
            ]
            
            if hasattr(self.message_broker, 'wait_for_queues_ready'):
                await self.message_broker.wait_for_queues_ready(discovery_queues, timeout=30)
            
            # Setup subscriptions
            if hasattr(self.message_broker, 'subscribe_to_queue'):
                self.message_broker.subscribe_to_queue('stock_discovery_requests', self._handle_discovery_request)
                self.message_broker.subscribe_to_queue('instrument_validation_requests', self._handle_validation_request)
            
            if self.logger:
                self.logger.info("✅ [STOCK_DISCOVERY] Message subscriptions setup complete")
                
        except Exception as e:
            if self.logger:
                self.logger.error(f"❌ [STOCK_DISCOVERY] Failed to setup subscriptions: {e}")
    
    async def discover_all_stocks(self) -> Dict[str, StockInfo]:
        """
        Discover all stocks from multiple sources.
        
        Returns:
            Dict of symbol -> StockInfo for all discovered stocks
        """
        start_time = time.time()
        
        logger.info("🔍 Starting comprehensive stock discovery...")
        
        try:
            # Step 1: Discover from MongoDB
            mongodb_stocks = await self._discover_from_mongodb()
            
            # Step 2: Validate via Angel One API
            validated_stocks = await self._validate_stocks_via_api(mongodb_stocks)
            
            # Step 3: Update cache and metrics
            await self._update_discovery_cache(validated_stocks)
            
            # Calculate final metrics
            processing_time = time.time() - start_time
            self.metrics['processing_time'] = processing_time
            self.metrics['total_discovered'] = len(self.discovered_stocks)
            
            # Log completion
            logger.info(f"✅ Stock discovery complete: {len(self.valid_stocks)} valid stocks in {processing_time:.2f}s")
            
            # Publish discovery results
            self._publish_discovery_results()
            
            return self.discovered_stocks
            
        except Exception as e:
            logger.error(f"❌ Error in stock discovery: {e}")
            return {}
    
    async def _discover_from_mongodb(self) -> List[Dict[str, Any]]:
        """Discover stocks from MongoDB tickers collection."""
        
        logger.info("📊 Fetching stocks from MongoDB tickers collection...")
        
        try:
            if not REAL_COMPONENTS or not self.connection_manager:
                # Return mock data for testing
                return self._get_mock_mongodb_stocks()
            
            # Get MongoDB client
            db = self.connection_manager.get_mongodb_client()
            if not db:
                raise Exception("MongoDB connection not available")
            
            # Query tickers collection
            tickers_collection = db.tickers
            
            # Fetch all tickers with equity instruments
            query = {
                "$or": [
                    {"symbol": {"$regex": "-EQ$"}},  # Already has -EQ suffix
                    {"instrumenttype": "EQ"},        # Equity instruments
                    {"exch_seg": "NSE"}             # NSE exchange
                ]
            }
            
            cursor = tickers_collection.find(query)
            mongodb_stocks = list(cursor)
            
            logger.info(f"📊 Found {len(mongodb_stocks)} stocks in MongoDB tickers collection")
            
            # Update progress tracker
            if self.progress_tracker:
                self.progress_tracker.log_stock_discovery(len(mongodb_stocks), 0, 0)
            
            self.metrics['mongodb_stocks'] = len(mongodb_stocks)
            
            # Convert to standardized format
            standardized_stocks = []
            for stock in mongodb_stocks:
                standardized = self._standardize_mongodb_stock(stock)
                if standardized:
                    standardized_stocks.append(standardized)
            
            return standardized_stocks
            
        except Exception as e:
            logger.error(f"❌ Error fetching from MongoDB: {e}")
            return self._get_mock_mongodb_stocks()
    
    def _standardize_mongodb_stock(self, stock_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Standardize MongoDB stock data format."""
        try:
            # Extract symbol
            symbol = stock_data.get('symbol', stock_data.get('tradingsymbol', ''))
            if not symbol:
                return None
            
            # Ensure proper format (add -EQ if needed)
            if not symbol.endswith('-EQ') and stock_data.get('instrumenttype') == 'EQ':
                symbol = f"{symbol}-EQ"
            
            return {
                'symbol': symbol,
                'name': stock_data.get('name', symbol.replace('-EQ', '')),
                'exchange': stock_data.get('exch_seg', 'NSE'),
                'symbol_token': stock_data.get('token', stock_data.get('symboltoken', '')),
                'instrument_type': stock_data.get('instrumenttype', 'EQ'),
                'lot_size': int(stock_data.get('lotsize', stock_data.get('lot_size', 1))),
                'tick_size': float(stock_data.get('tick_size', 0.05)),
                'source': 'mongodb'
            }
            
        except Exception as e:
            logger.warning(f"⚠️ Error standardizing stock {stock_data}: {e}")
            return None
    
    def _get_mock_mongodb_stocks(self) -> List[Dict[str, Any]]:
        """Get mock MongoDB stocks for testing."""
        mock_stocks = [
            # Real NSE stocks
            'RELIANCE', 'TCS', 'INFY', 'SBIN', 'HDFC', 'ICICIBANK', 'BHARTIARTL', 
            'KOTAKBANK', 'HINDUNILVR', 'ITC', 'LT', 'AXISBANK', 'HCLTECH', 
            'ASIANPAINT', 'MARUTI', 'BAJFINANCE', 'NESTLEIND', 'ULTRACEMCO', 
            'TITAN', 'WIPRO', 'M&M', 'SUNPHARMA', 'NTPC', 'POWERGRID', 'TECHM',
            'TATASTEEL', 'COALINDIA', 'ONGC', 'HDFCBANK', 'JSWSTEEL', 'IRFC',
            'ADANIPORTS', 'ADANIGREEN', 'BAJAJFINSV', 'BRITANNIA', 'CIPLA',
            'DRREDDY', 'EICHERMOT', 'GRASIM', 'HEROMOTOCO', 'HINDALCO',
            'INDUSINDBK', 'IOC', 'DIVISLAB', 'TATACONSUM', 'TATAMOTORS',
            'APOLLOHOSP', 'BAJAJ-AUTO', 'BPCL', 'GAIL', 'GODREJCP',
            'HAVELLS', 'HDFCLIFE', 'ICICIPRULI', 'INDIGO', 'JSWENERGY'
        ]
        
        standardized = []
        for i, symbol in enumerate(mock_stocks):
            standardized.append({
                'symbol': f"{symbol}-EQ",
                'name': symbol,
                'exchange': 'NSE',
                'symbol_token': str(1000 + i),
                'instrument_type': 'EQ',
                'lot_size': 1,
                'tick_size': 0.05,
                'source': 'mock'
            })
        
        # Add more real NSE stocks instead of fake ones
        additional_real_stocks = [
            'ADANIENT', 'APOLLOTYRE', 'ASHOKLEY', 'AUROPHARMA', 'BALKRISIND',
            'BANDHANBNK', 'BANKBARODA', 'BATAINDIA', 'BEL', 'BERGEPAINT',
            'BIOCON', 'BOSCHLTD', 'BSOFT', 'CANBK', 'CHOLAFIN',
            'COLPAL', 'CONCOR', 'CUMMINSIND', 'DABUR', 'DEEPAKNTR',
            'DMART', 'FEDERALBNK', 'GLENMARK', 'GMRINFRA', 'GODREJIND',
            'GRANULES', 'GUJGASLTD', 'HDFCAMC', 'HINDZINC', 'IBULHSGFIN',
            'IDEA', 'IDFCFIRSTB', 'IGL', 'INDHOTEL', 'INDUSTOWER',
            'INOXLEISUR', 'IPCALAB', 'JINDALSTEL', 'JUBLFOOD', 'KOTAKBANK',
            'L&TFH', 'LICHSGFIN', 'LUPIN', 'MARICO', 'MINDTREE',
            'MOTHERSUMI', 'MPHASIS', 'MRF', 'MUTHOOTFIN', 'NATIONALUM',
            'NAUKRI', 'NMDC', 'OFSS', 'OIL', 'PAGEIND',
            'PETRONET', 'PIDILITIND', 'PNB', 'RAMCOCEM', 'RBLBANK',
            'RECLTD', 'SAIL', 'SHREECEM', 'SIEMENS', 'SRF',
            'SRTRANSFIN', 'STAR', 'SUNTV', 'TATACOMM', 'TATAPOWER',
            'TORNTPHARM', 'TRENT', 'UBL', 'UJJIVAN', 'UPL',
            'VEDL', 'VOLTAS', 'WHIRLPOOL', 'YESBANK', 'ZEEL'
        ]
        
        for symbol in additional_real_stocks:
            standardized.append({
                'symbol': f"{symbol}-EQ",
                'name': symbol,
                'exchange': 'NSE',
                'symbol_token': str(3000 + len(standardized)),
                'instrument_type': 'EQ',
                'lot_size': 1,
                'tick_size': 0.05,
                'source': 'mock_real'
            })
        
        return standardized
    
    async def _validate_stocks_via_api(self, stocks: List[Dict[str, Any]]) -> Dict[str, StockInfo]:
        """Validate stocks via Angel One API."""
        
        logger.info(f"🔍 Validating {len(stocks)} stocks via Angel One API...")
        
        # Start progress tracking (simplified for now)
        # if self.progress_tracker:
        #     self.progress_tracker.start_stage(
        #         ProgressStage.STOCK_VALIDATION, 
        #         len(stocks),
        #         {'validation_method': 'Angel One searchScrip API'}
        #     )
        
        validated_stocks = {}
        
        # Process in batches for better performance
        batch_size = 20
        total_batches = (len(stocks) + batch_size - 1) // batch_size
        
        for i in range(0, len(stocks), batch_size):
            batch = stocks[i:i + batch_size]
            batch_num = i // batch_size + 1
            
            logger.debug(f"📊 Processing validation batch {batch_num}/{total_batches}")
            
            # Validate batch in parallel
            batch_results = await self._validate_stock_batch(batch)
            validated_stocks.update(batch_results)
            
            # Update progress (simplified for now)
            # if self.progress_tracker:
            #     self.progress_tracker.update_progress(
            #         ProgressStage.STOCK_VALIDATION,
            #         len(batch),
            #         successful=True,
            #         details={'batch': batch_num, 'validated_count': len(batch_results)}
            #     )
            
            # Small delay to avoid rate limiting
            await asyncio.sleep(0.1)
        
        # Complete progress tracking (simplified for now)
        # if self.progress_tracker:
        #     self.progress_tracker.complete_stage(
        #         ProgressStage.STOCK_VALIDATION,
        #         {
        #             'total_validated': len(validated_stocks),
        #             'validation_rate': (len(validated_stocks) / len(stocks)) * 100 if stocks else 0
        #         }
        #     )
        
        self.valid_stocks = validated_stocks
        self.metrics['api_validated'] = len(validated_stocks)
        
        return validated_stocks
    
    async def _validate_stock_batch(self, batch: List[Dict[str, Any]]) -> Dict[str, StockInfo]:
        """Validate a batch of stocks."""
        batch_results = {}
        
        # Use thread pool for API calls
        tasks = []
        for stock_data in batch:
            task = asyncio.create_task(self._validate_single_stock(stock_data))
            tasks.append(task)
        
        # Wait for all validations to complete
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results
        for stock_data, result in zip(batch, results):
            if isinstance(result, Exception):
                if self.logger:
                    self.logger.warning(f"⚠️ [STOCK_DISCOVERY] Validation failed for {stock_data.get('symbol')}: {result}")
                continue
            
            if result:
                batch_results[result.symbol] = result
        
        return batch_results
    
    async def _validate_single_stock(self, stock_data: Dict[str, Any]) -> Optional[StockInfo]:
        """Validate a single stock via Angel One API."""
        try:
            symbol = stock_data['symbol']
            
            # Check cache first
            cached_result = await self._check_validation_cache(symbol)
            if cached_result:
                self.metrics['cache_hits'] += 1
                return cached_result
            
            # Validate via API
            if not REAL_COMPONENTS or not self.connection_manager:
                # Mock validation for testing
                return self._create_mock_validated_stock(stock_data)
            
            # Get Angel One client
            client = self.connection_manager.get_smartapi_client()
            if not client:
                raise Exception("Angel One API client not available")
            
            # Check cache first, then search API
            cached_token = await self._get_cached_token(symbol)
            if cached_token:
                # Use cached data
                stock_info = StockInfo(
                    symbol=symbol,
                    name=cached_token.get('name', stock_data.get('name', '')),
                    exchange=cached_token.get('exchange', 'NSE'),
                    symbol_token=cached_token.get('symboltoken', ''),
                    instrument_type=cached_token.get('instrumenttype', 'EQ'),
                    lot_size=int(cached_token.get('lotsize', 1)),
                    tick_size=float(cached_token.get('tick_size', 0.05)),
                    is_valid=True,
                    last_validated=datetime.now(UTC),
                    validation_source='cache',
                    api_data=cached_token.get('full_data', {})
                )
            else:
                # Search for the instrument via API
                base_symbol = symbol.replace('-EQ', '')
                search_response = client.searchScrip(
                    exchange="NSE",
                    searchscrip=base_symbol
                )
                
                if not search_response or not search_response.get('status') or not search_response.get('data'):
                    self.invalid_stocks.add(symbol)
                    return None
                
                # Find the best match
                best_match = self._find_best_instrument_match(search_response['data'], symbol)
                if not best_match:
                    self.invalid_stocks.add(symbol)
                    return None
                
                # Create validated stock info with real Angel One token
                stock_info = StockInfo(
                    symbol=symbol,
                    name=best_match.get('name', stock_data.get('name', '')),
                    exchange=best_match.get('exch_seg', 'NSE'),
                    symbol_token=best_match.get('symboltoken', ''),  # Real token from Angel One API
                    instrument_type=best_match.get('instrumenttype', 'EQ'),
                    lot_size=int(best_match.get('lotsize', 1)),
                    tick_size=float(best_match.get('tick_size', 0.05)),
                    is_valid=True,
                    last_validated=datetime.now(UTC),
                    validation_source='api',
                    api_data=best_match
                )
                
                # Cache ALL search results asynchronously (not just the best match)
                await self._cache_all_search_results_bulk(search_response['data'])
            
            # Cache the result
            await self._cache_validation_result(stock_info)
            
            return stock_info
            
        except Exception as e:
            self.metrics['validation_errors'] += 1
            logger.warning(f"⚠️ Error validating {stock_data.get('symbol')}: {e}")
            return None
    
    def _find_best_instrument_match(self, instruments: List[Dict], target_symbol: str) -> Optional[Dict]:
        """Find the best matching instrument from search results."""
        if not instruments:
            return None
        
        # Try exact match first
        for instrument in instruments:
            if instrument.get('tradingsymbol') == target_symbol:
                return instrument
        
        # Try without -EQ suffix
        base_symbol = target_symbol.replace('-EQ', '')
        for instrument in instruments:
            if instrument.get('tradingsymbol') == f"{base_symbol}-EQ":
                return instrument
        
        # Try base symbol match
        for instrument in instruments:
            if instrument.get('tradingsymbol', '').replace('-EQ', '') == base_symbol:
                return instrument
        
        # Return first equity instrument if available
        for instrument in instruments:
            if instrument.get('instrumenttype') == 'EQ':
                return instrument
        
        return None
    
    def _create_mock_validated_stock(self, stock_data: Dict[str, Any]) -> StockInfo:
        """Create mock validated stock for testing."""
        return StockInfo(
            symbol=stock_data['symbol'],
            name=stock_data.get('name', ''),
            exchange=stock_data.get('exchange', 'NSE'),
            symbol_token=stock_data.get('symbol_token', ''),
            instrument_type=stock_data.get('instrument_type', 'EQ'),
            lot_size=stock_data.get('lot_size', 1),
            tick_size=stock_data.get('tick_size', 0.05),
            is_valid=True,
            last_validated=datetime.now(UTC),
            validation_source='mock'
        )
    
    async def _check_validation_cache(self, symbol: str) -> Optional[StockInfo]:
        """Check if stock validation is cached."""
        # For now, return None (no cache)
        # In production, this would check MongoDB cache
        return None
    
    async def _cache_validation_result(self, stock_info: StockInfo):
        """Cache validation result."""
        # Store in discovered stocks
        self.discovered_stocks[stock_info.symbol] = stock_info
        
        # In production, this would cache to MongoDB
        pass
    
    async def _update_discovery_cache(self, validated_stocks: Dict[str, StockInfo]):
        """Update discovery cache with results."""
        logger.debug(f"📊 Updating discovery cache with {len(validated_stocks)} stocks")
        
        # Update main discovery cache
        self.discovered_stocks.update(validated_stocks)
        
        # Update database cache if available
        if REAL_COMPONENTS and self.connection_manager:
            try:
                db = self.connection_manager.get_mongodb_client()
                if db:
                    cache_collection = db.stock_discovery_cache
                    
                    # Store cache data
                    cache_data = {
                        'discovery_timestamp': datetime.now(UTC),
                        'total_stocks': len(validated_stocks),
                        'stocks': {symbol: stock.to_dict() for symbol, stock in validated_stocks.items()},
                        'metrics': self.metrics
                    }
                    
                    cache_collection.replace_one(
                        {'_id': 'latest_discovery'},
                        {**cache_data, '_id': 'latest_discovery'},
                        upsert=True
                    )
            except Exception as e:
                logger.warning(f"⚠️ Could not update cache: {e}")
    
    def _publish_discovery_results(self):
        """Publish discovery results via message broker."""
        try:
            discovery_data = {
                'timestamp': datetime.now(UTC).isoformat(),
                'total_discovered': len(self.discovered_stocks),
                'valid_stocks': len(self.valid_stocks),
                'invalid_stocks': len(self.invalid_stocks),
                'metrics': self.metrics,
                'top_stocks': list(self.valid_stocks.keys())[:50]  # Top 50 stocks
            }
            
            self.message_broker.publish_ai_analysis('stock_discovery_complete', 'system', discovery_data)
            
            logger.info("📤 Published discovery results to message broker")
                
        except Exception as e:
            logger.error(f"❌ Error publishing results: {e}")
    
    # Message handlers
    def _handle_discovery_request(self, message):
        """Handle stock discovery requests."""
        try:
            data = message.get('data', {})
            logger.info("📨 Received discovery request")
            
            # Trigger discovery
            asyncio.create_task(self.discover_all_stocks())
            
        except Exception as e:
            logger.error(f"❌ Error handling discovery request: {e}")
    
    def _handle_validation_request(self, message):
        """Handle stock validation requests."""
        try:
            data = message.get('data', {})
            symbol = data.get('symbol')
            
            if symbol:
                logger.info(f"📨 Received validation request for {symbol}")
            
        except Exception as e:
            logger.error(f"❌ Error handling validation request: {e}")
    
    def get_valid_stocks_list(self) -> List[str]:
        """Get list of all valid stock symbols."""
        return list(self.valid_stocks.keys())
    
    def get_discovery_summary(self) -> Dict[str, Any]:
        """Get discovery summary."""
        return {
            'metrics': self.metrics,
            'total_discovered': len(self.discovered_stocks),
            'valid_stocks': len(self.valid_stocks),
            'invalid_stocks': len(self.invalid_stocks),
            'top_valid_stocks': list(self.valid_stocks.keys())[:20]
        }
    
    def cleanup(self):
        """Cleanup resources."""
        self.executor.shutdown(wait=True)
        logger.info("✅ Stock Discovery Service cleanup completed")

    async def _get_cached_token(self, symbol):
        """Get cached instrument token from MongoDB."""
        try:
            if not self.connection_manager:
                return None
                
            mongo_client = self.connection_manager.get_mongodb_client()
            if not mongo_client:
                return None
                
            db = mongo_client['trading_system']
            scripts_collection = db['scripts']
            
            # Look for cached token
            cached_instrument = scripts_collection.find_one({
                "tradingsymbol": symbol,
                "exchange": "NSE"
            })
            
            if cached_instrument:
                # Check if cache is fresh (less than 24 hours old)
                from datetime import datetime, timedelta, UTC
                last_updated = cached_instrument.get('last_updated')
                if last_updated and isinstance(last_updated, datetime):
                    if datetime.now(UTC) - last_updated.replace(tzinfo=UTC) < timedelta(hours=24):
                        return cached_instrument
            
            return None
            
        except Exception as e:
            if self.logger:
                self.logger.warning(f"⚠️ Error getting cached token for {symbol}: {e}")
            return None

    async def _cache_token_async(self, instrument_data):
        """Cache instrument token in MongoDB asynchronously."""
        try:
            import asyncio
            from datetime import datetime, UTC
            
            if not self.connection_manager:
                return
                
            mongo_client = self.connection_manager.get_mongodb_client()
            if not mongo_client:
                return
                
            db = mongo_client['trading_system']
            scripts_collection = db['scripts']
            
            # Prepare document for caching
            cache_document = {
                'tradingsymbol': instrument_data.get('tradingsymbol'),
                'symboltoken': instrument_data.get('symboltoken'),
                'exchange': instrument_data.get('exch_seg', 'NSE'),
                'instrumenttype': instrument_data.get('instrumenttype'),
                'name': instrument_data.get('name', ''),
                'lotsize': instrument_data.get('lotsize', '1'),
                'tick_size': instrument_data.get('tick_size', '0.05'),
                'last_updated': datetime.now(UTC),
                'source': 'angel_one_api',
                'full_data': instrument_data  # Store complete data for reference
            }
            
            # Run MongoDB operation in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,
                lambda: scripts_collection.update_one(
                    {
                        'tradingsymbol': instrument_data.get('tradingsymbol'),
                        'exchange': instrument_data.get('exch_seg', 'NSE')
                    },
                    {'$set': cache_document},
                    upsert=True
                )
            )
            
            if self.logger:
                self.logger.debug(f"💾 Cached token for {instrument_data.get('tradingsymbol')} in MongoDB")
            
        except Exception as e:
            if self.logger:
                self.logger.warning(f"⚠️ Failed to cache instrument token: {e}")

    async def _cache_all_search_results_bulk(self, search_results):
        """Cache ALL search results in MongoDB - bulk operation to avoid duplicates."""
        try:
            import asyncio
            from datetime import datetime, UTC
            
            if not search_results or not self.connection_manager:
                return
                
            mongo_client = self.connection_manager.get_mongodb_client()
            if not mongo_client:
                return
                
            db = mongo_client['trading_system']
            scripts_collection = db['scripts']
            
            # Prepare bulk operations - check existence first, then insert only new ones
            loop = asyncio.get_event_loop()
            
            # Step 1: Get existing symbols to avoid duplicates
            existing_symbols = await loop.run_in_executor(
                None,
                lambda: set([
                    doc['tradingsymbol'] for doc in scripts_collection.find(
                        {'tradingsymbol': {'$in': [r.get('tradingsymbol') for r in search_results]}},
                        {'tradingsymbol': 1}
                    )
                ])
            )
            
            # Step 2: Prepare documents for new symbols only
            new_documents = []
            for instrument_data in search_results:
                tradingsymbol = instrument_data.get('tradingsymbol')
                if tradingsymbol and tradingsymbol not in existing_symbols:
                    cache_document = {
                        'tradingsymbol': tradingsymbol,
                        'symboltoken': instrument_data.get('symboltoken'),
                        'exchange': instrument_data.get('exch_seg', 'NSE'),
                        'instrumenttype': instrument_data.get('instrumenttype'),
                        'name': instrument_data.get('name', ''),
                        'lotsize': instrument_data.get('lotsize', '1'),
                        'tick_size': instrument_data.get('tick_size', '0.05'),
                        'last_updated': datetime.now(UTC),
                        'source': 'angel_one_api',
                        'full_data': instrument_data  # Store complete data for reference
                    }
                    new_documents.append(cache_document)
            
            # Step 3: Bulk insert new documents only
            if new_documents:
                await loop.run_in_executor(
                    None,
                    lambda: scripts_collection.insert_many(new_documents, ordered=False)
                )
                if self.logger:
                    self.logger.info(f"💾 Bulk cached {len(new_documents)} new instruments from search")
            else:
                if self.logger:
                    self.logger.debug(f"📋 All {len(search_results)} search results already cached")
            
        except Exception as e:
            if self.logger:
                self.logger.warning(f"⚠️ Failed to bulk cache search results: {e}")

# Add to_dict method to StockInfo
def _stock_info_to_dict(self) -> Dict[str, Any]:
    """Convert StockInfo to dictionary."""
    return {
        'symbol': self.symbol,
        'name': self.name,
        'exchange': self.exchange,
        'symbol_token': self.symbol_token,
        'instrument_type': self.instrument_type,
        'lot_size': self.lot_size,
        'tick_size': self.tick_size,
        'is_valid': self.is_valid,
        'last_validated': self.last_validated.isoformat() if self.last_validated else None,
        'validation_source': self.validation_source,
        'trading_symbol': self.trading_symbol
    }

# Monkey patch the method
StockInfo.to_dict = _stock_info_to_dict

# Test the stock discovery service
async def main():
    """Test the stock discovery service."""
    print("🧪 Testing Enhanced Stock Discovery Service")
    print("=" * 60)
    
    # Create service
    service = StockDiscoveryService()
    
    try:
        # Discover all stocks
        print("🔍 Starting stock discovery...")
        discovered_stocks = await service.discover_all_stocks()
        
        # Show results
        print(f"\n📊 Discovery Results:")
        print(f"   📈 Total Discovered: {len(discovered_stocks):,}")
        print(f"   ✅ Valid Stocks: {len(service.valid_stocks):,}")
        print(f"   ❌ Invalid Stocks: {len(service.invalid_stocks):,}")
        print(f"   ⚡ Processing Time: {service.metrics['processing_time']:.2f}s")
        
        # Show sample stocks
        sample_stocks = list(service.valid_stocks.keys())[:10]
        print(f"\n📋 Sample Valid Stocks:")
        for symbol in sample_stocks:
            stock_info = service.valid_stocks[symbol]
            print(f"   📈 {symbol} - {stock_info.name} (Token: {stock_info.symbol_token})")
        
        # Show metrics
        print(f"\n📊 Discovery Metrics:")
        for metric, value in service.metrics.items():
            print(f"   {metric}: {value}")
        
        print(f"\n✅ Stock Discovery Service test completed!")
        
    except KeyboardInterrupt:
        print("\n⏹️ Testing interrupted")
    finally:
        service.cleanup()

if __name__ == "__main__":
    asyncio.run(main())
