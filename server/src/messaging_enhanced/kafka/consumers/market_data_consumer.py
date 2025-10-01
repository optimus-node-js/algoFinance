"""
Market Data Consumer for HFT System
===================================

High-frequency market data consumer optimized for:
- Ultra-low latency processing
- Real-time tick data handling
- Bulk message processing
- Performance monitoring
"""

import logging
import time
import threading
from typing import Dict, List, Any, Optional, Callable
from datetime import datetime
from ..kafka_manager import get_kafka_manager
from ..schema_registry import get_schema_registry

logger = logging.getLogger(__name__)

class MarketDataConsumer:
    """
    Specialized consumer for market data processing.
    
    Features:
    - High-frequency tick processing
    - Latency tracking and monitoring
    - Configurable batch processing
    - Real-time callbacks
    """
    
    def __init__(
        self,
        consumer_id: str = "market_data_consumer",
        group_id: str = "hft_market_data_group",
        auto_offset_reset: str = "latest"
    ):
        """
        Initialize market data consumer.
        
        Args:
            consumer_id: Unique identifier for this consumer
            group_id: Consumer group ID
            auto_offset_reset: Where to start reading (earliest/latest)
        """
        self.consumer_id = consumer_id
        self.group_id = group_id
        self.kafka_manager = get_kafka_manager()
        self.schema_registry = get_schema_registry()
        
        # Configuration
        self.topics = [
            "hft-market-data",
            "hft-market-data-live-ticks",
            "hft-market-data-live-ltp", 
            "hft-market-data-live-candles",
            "hft-market-data-live-orderbook"
        ]
        self.batch_size = 100
        self.poll_timeout = 1.0  # seconds
        
        # Performance tracking
        self.messages_processed = 0
        self.bytes_processed = 0
        self.processing_errors = 0
        self.start_time = datetime.now()
        self._lock = threading.Lock()
        
        # Consumer management
        self.consumer = None
        self.is_running = False
        self.callbacks: Dict[str, Callable] = {}
        self.live_data_callbacks: Dict[str, Callable] = {}
        
        # Initialize consumer
        self._initialize_consumer(auto_offset_reset)
        
        logger.info(f"MarketDataConsumer initialized: {consumer_id}")
    
    def _initialize_consumer(self, auto_offset_reset: str):
        """Initialize Kafka consumer."""
        try:
            self.consumer = self.kafka_manager.get_consumer(
                consumer_id=self.consumer_id,
                topics=self.topics,
                group_id=self.group_id,
                auto_offset_reset=auto_offset_reset
            )
            logger.info(f"Consumer initialized for topics: {self.topics}")
        except Exception as e:
            logger.error(f"Failed to initialize consumer: {e}")
            raise
    
    def register_callback(self, callback_name: str, callback_func: Callable):
        """
        Register a callback function for market data processing.
        
        Args:
            callback_name: Name of the callback
            callback_func: Function to call with market data
                          Should accept (symbol, tick_data) arguments
        """
        self.callbacks[callback_name] = callback_func
        logger.info(f"Registered callback: {callback_name}")
    
    def register_live_data_callback(self, callback_name: str, callback_func: Callable):
        """
        Register a callback function for live market data processing.
        
        Args:
            callback_name: Name of the callback
            callback_func: Function to call with live market data
                          Should accept (symbol, live_data) arguments
        """
        self.live_data_callbacks[callback_name] = callback_func
        logger.info(f"Registered live data callback: {callback_name}")
    
    def unregister_callback(self, callback_name: str):
        """Unregister a callback function."""
        if callback_name in self.callbacks:
            del self.callbacks[callback_name]
            logger.info(f"Unregistered callback: {callback_name}")
    
    def process_single_message(self, message: Dict[str, Any]) -> bool:
        """
        Process a single market data message.
        
        Args:
            message: Parsed message data
            
        Returns:
            True if processed successfully
        """
        try:
            # Extract symbol for routing
            symbol = message.get('symbol', 'UNKNOWN')
            
            # Calculate processing latency
            now_ns = int(time.time() * 1_000_000_000)
            system_timestamp = message.get('system_timestamp', now_ns)
            processing_latency_ns = now_ns - system_timestamp
            
            # Add processing metadata
            processing_info = {
                'processing_timestamp': now_ns,
                'processing_latency_ns': processing_latency_ns,
                'consumer_id': self.consumer_id
            }
            
            # Call registered callbacks
            for callback_name, callback_func in self.callbacks.items():
                try:
                    callback_func(symbol, message, processing_info)
                except Exception as e:
                    logger.error(f"Error in callback {callback_name}: {e}")
            
            # Update statistics
            with self._lock:
                self.messages_processed += 1
            
            # Log high latency warnings
            if processing_latency_ns > 10_000_000:  # 10ms
                logger.warning(f"High processing latency: {processing_latency_ns/1_000_000:.2f}ms for {symbol}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error processing market data message: {e}")
            with self._lock:
                self.processing_errors += 1
            return False
    
    def process_batch(self, timeout: float = None) -> Dict[str, Any]:
        """
        Process a batch of market data messages.
        
        Args:
            timeout: Polling timeout (uses default if None)
            
        Returns:
            Processing results and statistics
        """
        if timeout is None:
            timeout = self.poll_timeout
        
        start_time = time.time()
        processed_count = 0
        error_count = 0
        
        try:
            # Consume messages
            messages = self.kafka_manager.consume_messages(
                consumer_id=self.consumer_id,
                timeout=timeout,
                max_messages=self.batch_size
            )
            
            if not messages:
                return {
                    'processed': 0,
                    'errors': 0,
                    'duration': time.time() - start_time,
                    'status': 'NO_MESSAGES'
                }
            
            # Process each message
            for msg_data in messages:
                try:
                    # Deserialize market tick data
                    if msg_data['value']:
                        # If already deserialized by kafka_manager
                        if isinstance(msg_data['value'], dict):
                            tick_data = msg_data['value']
                        else:
                            # If still bytes, deserialize
                            tick_data = self.schema_registry.deserialize('market_tick', msg_data['value'])
                        
                        if tick_data:
                            success = self.process_single_message(tick_data)
                            if success:
                                processed_count += 1
                            else:
                                error_count += 1
                        else:
                            logger.error("Failed to deserialize market tick message")
                            error_count += 1
                    
                    # Update bytes processed
                    with self._lock:
                        if isinstance(msg_data['value'], bytes):
                            self.bytes_processed += len(msg_data['value'])
                        else:
                            self.bytes_processed += len(str(msg_data['value']).encode())
                
                except Exception as e:
                    logger.error(f"Error processing message: {e}")
                    error_count += 1
            
            end_time = time.time()
            duration = end_time - start_time
            
            results = {
                'processed': processed_count,
                'errors': error_count,
                'duration': duration,
                'messages_per_second': processed_count / duration if duration > 0 else 0,
                'status': 'SUCCESS' if error_count == 0 else 'PARTIAL_SUCCESS'
            }
            
            if processed_count > 0:
                logger.debug(f"Processed batch: {results}")
            
            return results
            
        except Exception as e:
            logger.error(f"Error in batch processing: {e}")
            return {
                'processed': processed_count,
                'errors': error_count + 1,
                'duration': time.time() - start_time,
                'status': 'ERROR',
                'error': str(e)
            }
    
    def start_continuous_processing(self, process_interval: float = 0.1):
        """
        Start continuous message processing in background.
        
        Args:
            process_interval: Interval between processing cycles (seconds)
        """
        if self.is_running:
            logger.warning("Consumer is already running")
            return
        
        self.is_running = True
        logger.info(f"Starting continuous processing with {process_interval}s interval")
        
        def processing_loop():
            while self.is_running:
                try:
                    results = self.process_batch()
                    
                    # Sleep if no messages to avoid busy waiting
                    if results['processed'] == 0:
                        time.sleep(process_interval)
                    
                except Exception as e:
                    logger.error(f"Error in processing loop: {e}")
                    time.sleep(process_interval)
        
        # Start processing thread
        self.processing_thread = threading.Thread(target=processing_loop, daemon=True)
        self.processing_thread.start()
        logger.info("Continuous processing started")
    
    def stop_continuous_processing(self):
        """Stop continuous message processing."""
        if not self.is_running:
            return
        
        logger.info("Stopping continuous processing...")
        self.is_running = False
        
        # Wait for processing thread to finish
        if hasattr(self, 'processing_thread'):
            self.processing_thread.join(timeout=5.0)
            if self.processing_thread.is_alive():
                logger.warning("Processing thread did not stop gracefully")
        
        logger.info("Continuous processing stopped")
    
    def seek_to_beginning(self):
        """Seek to the beginning of all partitions."""
        try:
            if self.consumer:
                partitions = self.consumer.assignment()
                self.consumer.seek_to_beginning(partitions)
                logger.info("Seeked to beginning of all partitions")
        except Exception as e:
            logger.error(f"Error seeking to beginning: {e}")
    
    def seek_to_end(self):
        """Seek to the end of all partitions."""
        try:
            if self.consumer:
                partitions = self.consumer.assignment()
                self.consumer.seek_to_end(partitions)
                logger.info("Seeked to end of all partitions")
        except Exception as e:
            logger.error(f"Error seeking to end: {e}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get consumer statistics."""
        with self._lock:
            runtime = (datetime.now() - self.start_time).total_seconds()
            
            return {
                'consumer_id': self.consumer_id,
                'group_id': self.group_id,
                'topics': self.topics,
                'messages_processed': self.messages_processed,
                'bytes_processed': self.bytes_processed,
                'processing_errors': self.processing_errors,
                'runtime_seconds': runtime,
                'messages_per_second': self.messages_processed / runtime if runtime > 0 else 0,
                'bytes_per_second': self.bytes_processed / runtime if runtime > 0 else 0,
                'error_rate': self.processing_errors / self.messages_processed if self.messages_processed > 0 else 0,
                'is_running': self.is_running,
                'callbacks_registered': len(self.callbacks),
                'start_time': self.start_time.isoformat()
            }
    
    def close(self):
        """Close the consumer."""
        logger.info(f"Closing MarketDataConsumer: {self.consumer_id}")
        
        # Stop continuous processing
        self.stop_continuous_processing()
        
        # Log final statistics
        stats = self.get_stats()
        logger.info(f"MarketDataConsumer final stats: {stats}")
        
        # Consumer will be closed by kafka_manager


# Global market data consumer instance
_market_data_consumer: Optional[MarketDataConsumer] = None
_consumer_lock = threading.Lock()

def get_market_data_consumer(
    consumer_id: str = "market_data_consumer",
    group_id: str = "hft_market_data_group"
) -> MarketDataConsumer:
    """Get or create global market data consumer instance."""
    global _market_data_consumer
    
    with _consumer_lock:
        if _market_data_consumer is None:
            _market_data_consumer = MarketDataConsumer(consumer_id, group_id)
        return _market_data_consumer

def close_market_data_consumer():
    """Close global market data consumer."""
    global _market_data_consumer
    
    with _consumer_lock:
        if _market_data_consumer:
            _market_data_consumer.close()
            _market_data_consumer = None
