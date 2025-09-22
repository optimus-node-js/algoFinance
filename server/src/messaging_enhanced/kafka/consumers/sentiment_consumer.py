"""
Sentiment Consumer for HFT System
=================================

Consumer for sentiment signals from news and social media.
"""

import logging
import threading
from typing import Dict, Any, Callable, Optional
from datetime import datetime
from ..kafka_manager import get_kafka_manager
from ..schema_registry import get_schema_registry

logger = logging.getLogger(__name__)

class SentimentConsumer:
    """Consumer for sentiment signals."""
    
    def __init__(self, consumer_id: str = "sentiment_consumer", group_id: str = "hft_sentiment_group"):
        self.consumer_id = consumer_id
        self.group_id = group_id
        self.kafka_manager = get_kafka_manager()
        self.schema_registry = get_schema_registry()
        self.topics = ["hft-sentiment-signals"]
        self.signals_processed = 0
        self.start_time = datetime.now()
        self._lock = threading.Lock()
        self.callbacks: Dict[str, Callable] = {}
        
        # Initialize consumer
        self.consumer = self.kafka_manager.get_consumer(
            consumer_id=self.consumer_id,
            topics=self.topics,
            group_id=self.group_id
        )
        
        logger.info(f"SentimentConsumer initialized: {consumer_id}")
    
    def register_callback(self, callback_name: str, callback_func: Callable):
        """Register callback for sentiment processing."""
        self.callbacks[callback_name] = callback_func
        logger.info(f"Registered sentiment callback: {callback_name}")
    
    def process_batch(self, timeout: float = 1.0) -> Dict[str, Any]:
        """Process batch of sentiment messages."""
        messages = self.kafka_manager.consume_messages(
            consumer_id=self.consumer_id,
            timeout=timeout,
            max_messages=20
        )
        
        processed = 0
        for msg_data in messages:
            try:
                signal_data = self.schema_registry.deserialize('sentiment_signal', msg_data['value'])
                if signal_data:
                    self._process_sentiment(signal_data)
                    processed += 1
            except Exception as e:
                logger.error(f"Error processing sentiment message: {e}")
        
        with self._lock:
            self.signals_processed += processed
        
        return {'processed': processed}
    
    def _process_sentiment(self, signal_data: Dict[str, Any]):
        """Process sentiment signal."""
        symbol = signal_data.get('symbol', 'UNKNOWN')
        for callback_name, callback_func in self.callbacks.items():
            try:
                callback_func(symbol, signal_data)
            except Exception as e:
                logger.error(f"Error in sentiment callback {callback_name}: {e}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get consumer statistics."""
        with self._lock:
            runtime = (datetime.now() - self.start_time).total_seconds()
            return {
                'consumer_id': self.consumer_id,
                'signals_processed': self.signals_processed,
                'runtime_seconds': runtime,
                'signals_per_second': self.signals_processed / runtime if runtime > 0 else 0
            }


# Global instance
_sentiment_consumer: Optional[SentimentConsumer] = None

def get_sentiment_consumer() -> SentimentConsumer:
    """Get or create global sentiment consumer."""
    global _sentiment_consumer
    if _sentiment_consumer is None:
        _sentiment_consumer = SentimentConsumer()
    return _sentiment_consumer
