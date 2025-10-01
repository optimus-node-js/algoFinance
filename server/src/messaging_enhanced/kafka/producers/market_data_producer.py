"""
Market Data Producer for HFT System
===================================

High-frequency market data producer optimized for:
- Ultra-low latency streaming
- Bulk message publishing
- Real-time market tick distribution
- Performance monitoring
"""

import logging
import time
from typing import Dict, List, Any, Optional, Callable
from datetime import datetime
import threading
from ..kafka_manager import get_kafka_manager
from ..schema_registry import get_schema_registry

logger = logging.getLogger(__name__)

class MarketDataProducer:
    """
    Specialized producer for market data streaming.
    
    Features:
    - Optimized for high-frequency tick data
    - Bulk publishing for efficiency
    - Latency tracking and monitoring
    - Automatic partitioning by symbol
    """
    
    def __init__(self, producer_id: str = "market_data"):
        """
        Initialize market data producer.
        
        Args:
            producer_id: Unique identifier for this producer
        """
        self.producer_id = producer_id
        self.kafka_manager = get_kafka_manager()
        self.schema_registry = get_schema_registry()
        
        # Performance tracking
        self.messages_sent = 0
        self.bytes_sent = 0
        self.errors = 0
        self.start_time = datetime.now()
        self._lock = threading.Lock()
        
        # Configuration
        self.topic = "hft-market-data"
        self.enable_latency_tracking = True
        
        logger.info(f"MarketDataProducer initialized: {producer_id}")
    
    def send_live_market_data(self, live_data: dict) -> bool:
        """
        Send live market data from WebSocket to Kafka.
        
        Args:
            live_data: Live market data dictionary from Angel One WebSocket
            
        Returns:
            True if message was queued successfully
        """
        try:
            # Serialize using market_data_live schema
            serialized = self.schema_registry.serialize('market_data_live', live_data)
            if not serialized:
                logger.error(f"Failed to serialize live market data for {live_data.get('symbol', 'unknown')}")
                with self._lock:
                    self.errors += 1
                return False
            
            # Determine topic based on data type
            data_type = live_data.get('data_type', 'TICK')
            topic_suffix = {
                'TICK': 'live-ticks',
                'LTP': 'live-ltp', 
                'CANDLE': 'live-candles',
                'ORDERBOOK': 'live-orderbook'
            }.get(data_type, 'live-data')
            
            topic = f"hft-market-data-{topic_suffix}"
            
            # Send to Kafka (use symbol as key for partitioning)
            success = self.kafka_manager.send_message(
                topic=topic,
                message=serialized,
                key=f"{live_data.get('exchange', '')}:{live_data.get('symbol', '')}",
                producer_id=self.producer_id,
                callback=self._delivery_callback
            )
            
            if success:
                with self._lock:
                    self.messages_sent += 1
                    self.bytes_sent += len(serialized)
                logger.debug(f"📤 Live market data sent: {live_data.get('symbol', 'unknown')} ({data_type})")
            else:
                with self._lock:
                    self.errors += 1
            
            return success
            
        except Exception as e:
            logger.error(f"❌ Failed to send live market data: {e}")
            with self._lock:
                self.errors += 1
            return False
    
    def send_market_tick(
        self,
        symbol: str,
        exchange: str,
        price: float,
        volume: int,
        bid: float,
        ask: float,
        bid_size: int = 0,
        ask_size: int = 0,
        sequence_number: Optional[int] = None,
        **kwargs
    ) -> bool:
        """
        Send a single market tick.
        
        Args:
            symbol: Trading symbol
            exchange: Exchange identifier
            price: Last traded price
            volume: Trade volume
            bid: Best bid price
            ask: Best ask price
            bid_size: Best bid quantity
            ask_size: Best ask quantity
            sequence_number: Message sequence number
            **kwargs: Additional market data fields
            
        Returns:
            True if message was queued successfully
        """
        try:
            # Create market tick message
            message = self.schema_registry.create_market_tick(
                symbol=symbol,
                exchange=exchange,
                price=price,
                volume=volume,
                bid=bid,
                ask=ask,
                bid_size=bid_size,
                ask_size=ask_size,
                sequence_number=sequence_number or self.messages_sent,
                **kwargs
            )
            
            # Add latency tracking
            if self.enable_latency_tracking:
                send_timestamp = int(time.time() * 1_000_000_000)  # nanoseconds
                message['system_timestamp'] = send_timestamp
                if 'timestamp' in message:
                    message['feed_latency_ns'] = send_timestamp - message['timestamp']
            
            # Serialize message
            serialized = self.schema_registry.serialize('market_tick', message)
            if not serialized:
                logger.error(f"Failed to serialize market tick for {symbol}")
                with self._lock:
                    self.errors += 1
                return False
            
            # Send to Kafka (use symbol as key for partitioning)
            success = self.kafka_manager.send_message(
                topic=self.topic,
                message=serialized,
                key=f"{exchange}:{symbol}",
                producer_id=self.producer_id,
                callback=self._delivery_callback
            )
            
            if success:
                with self._lock:
                    self.messages_sent += 1
                    self.bytes_sent += len(serialized)
            else:
                with self._lock:
                    self.errors += 1
            
            return success
            
        except Exception as e:
            logger.error(f"Error sending market tick for {symbol}: {e}")
            with self._lock:
                self.errors += 1
            return False
    
    def send_bulk_ticks(self, ticks: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Send multiple market ticks efficiently.
        
        Args:
            ticks: List of market tick data dictionaries
            
        Returns:
            Dictionary with send results and statistics
        """
        start_time = time.time()
        successful_sends = 0
        failed_sends = 0
        
        logger.info(f"Sending bulk market data: {len(ticks)} ticks")
        
        for i, tick in enumerate(ticks):
            try:
                # Add sequence number if not provided
                if 'sequence_number' not in tick:
                    tick['sequence_number'] = self.messages_sent + i
                
                success = self.send_market_tick(**tick)
                if success:
                    successful_sends += 1
                else:
                    failed_sends += 1
                    
            except Exception as e:
                logger.error(f"Error in bulk send for tick {i}: {e}")
                failed_sends += 1
        
        end_time = time.time()
        duration = end_time - start_time
        
        results = {
            'total_ticks': len(ticks),
            'successful': successful_sends,
            'failed': failed_sends,
            'duration_seconds': duration,
            'ticks_per_second': len(ticks) / duration if duration > 0 else 0,
            'success_rate': successful_sends / len(ticks) if len(ticks) > 0 else 0
        }
        
        logger.info(f"Bulk send completed: {results}")
        return results
    
    def send_ohlcv_bar(
        self,
        symbol: str,
        exchange: str,
        timeframe: str,
        open_price: float,
        high_price: float,
        low_price: float,
        close_price: float,
        volume: int,
        timestamp: Optional[int] = None,
        **kwargs
    ) -> bool:
        """
        Send OHLCV bar data as market tick.
        
        Args:
            symbol: Trading symbol
            exchange: Exchange identifier
            timeframe: Bar timeframe (1m, 5m, 1h, etc.)
            open_price: Open price
            high_price: High price
            low_price: Low price
            close_price: Close price
            volume: Total volume
            timestamp: Bar timestamp
            **kwargs: Additional fields
            
        Returns:
            True if message was queued successfully
        """
        try:
            # Create market tick with OHLCV data
            message = self.schema_registry.create_market_tick(
                symbol=symbol,
                exchange=exchange,
                price=close_price,  # Use close as current price
                volume=volume,
                bid=close_price,  # Approximate bid/ask
                ask=close_price,
                open=open_price,
                high=high_price,
                low=low_price,
                close=close_price,
                total_volume=volume,
                sequence_number=self.messages_sent,
                **kwargs
            )
            
            if timestamp:
                message['timestamp'] = timestamp
            
            # Add timeframe to metadata
            message['source'] = f"ohlcv_{timeframe}"
            
            # Serialize and send
            serialized = self.schema_registry.serialize('market_tick', message)
            if not serialized:
                logger.error(f"Failed to serialize OHLCV bar for {symbol}")
                return False
            
            success = self.kafka_manager.send_message(
                topic=self.topic,
                message=serialized,
                key=f"{exchange}:{symbol}:ohlcv",
                producer_id=self.producer_id
            )
            
            if success:
                with self._lock:
                    self.messages_sent += 1
                    self.bytes_sent += len(serialized)
            
            return success
            
        except Exception as e:
            logger.error(f"Error sending OHLCV bar for {symbol}: {e}")
            with self._lock:
                self.errors += 1
            return False
    
    def _delivery_callback(self, err, msg):
        """Callback for message delivery confirmation."""
        if err:
            logger.error(f"Market data delivery failed: {err}")
            with self._lock:
                self.errors += 1
        else:
            logger.debug(f"Market data delivered: {msg.topic()}[{msg.partition()}]@{msg.offset()}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get producer statistics."""
        with self._lock:
            runtime = (datetime.now() - self.start_time).total_seconds()
            
            return {
                'producer_id': self.producer_id,
                'topic': self.topic,
                'messages_sent': self.messages_sent,
                'bytes_sent': self.bytes_sent,
                'errors': self.errors,
                'runtime_seconds': runtime,
                'messages_per_second': self.messages_sent / runtime if runtime > 0 else 0,
                'bytes_per_second': self.bytes_sent / runtime if runtime > 0 else 0,
                'error_rate': self.errors / (self.messages_sent + self.errors) if (self.messages_sent + self.errors) > 0 else 0,
                'start_time': self.start_time.isoformat()
            }
    
    def flush(self, timeout: float = 10.0):
        """Flush all pending messages."""
        try:
            producer = self.kafka_manager.get_producer(self.producer_id)
            remaining = producer.flush(timeout)
            if remaining > 0:
                logger.warning(f"MarketDataProducer: {remaining} messages not delivered after flush")
            else:
                logger.info(f"MarketDataProducer: all messages flushed successfully")
        except Exception as e:
            logger.error(f"Error flushing MarketDataProducer: {e}")
    
    def close(self):
        """Close the producer."""
        logger.info(f"Closing MarketDataProducer: {self.producer_id}")
        self.flush()
        
        # Log final statistics
        stats = self.get_stats()
        logger.info(f"MarketDataProducer final stats: {stats}")


# Global market data producer instance
_market_data_producer: Optional[MarketDataProducer] = None
_producer_lock = threading.Lock()

def get_market_data_producer(producer_id: str = "market_data") -> MarketDataProducer:
    """Get or create global market data producer instance."""
    global _market_data_producer
    
    with _producer_lock:
        if _market_data_producer is None:
            _market_data_producer = MarketDataProducer(producer_id)
        return _market_data_producer

def close_market_data_producer():
    """Close global market data producer."""
    global _market_data_producer
    
    with _producer_lock:
        if _market_data_producer:
            _market_data_producer.close()
            _market_data_producer = None
