"""
Order Consumer for HFT System
=============================

Consumer for trade orders and execution events.
"""

import logging
import threading
from typing import Dict, Any, Callable, Optional
from datetime import datetime
from ..kafka_manager import get_kafka_manager
from ..schema_registry import get_schema_registry

logger = logging.getLogger(__name__)

class OrderConsumer:
    """Consumer for trade orders and execution events."""
    
    def __init__(self, consumer_id: str = "order_consumer", group_id: str = "hft_order_group"):
        self.consumer_id = consumer_id
        self.group_id = group_id
        self.kafka_manager = get_kafka_manager()
        self.schema_registry = get_schema_registry()
        self.topics = ["hft-trade-orders", "hft-execution-events"]
        self.messages_processed = 0
        self.start_time = datetime.now()
        self._lock = threading.Lock()
        self.callbacks: Dict[str, Callable] = {}
        
        # Initialize consumer
        self.consumer = self.kafka_manager.get_consumer(
            consumer_id=self.consumer_id,
            topics=self.topics,
            group_id=self.group_id
        )
        
        logger.info(f"OrderConsumer initialized: {consumer_id}")
    
    def register_callback(self, callback_name: str, callback_func: Callable):
        """Register callback for order processing."""
        self.callbacks[callback_name] = callback_func
        logger.info(f"Registered order callback: {callback_name}")
    
    def process_batch(self, timeout: float = 1.0) -> Dict[str, Any]:
        """Process batch of order messages."""
        messages = self.kafka_manager.consume_messages(
            consumer_id=self.consumer_id,
            timeout=timeout,
            max_messages=50
        )
        
        processed = 0
        for msg_data in messages:
            try:
                # Determine message type by topic
                if msg_data['topic'] == 'hft-trade-orders':
                    order_data = self.schema_registry.deserialize('trade_order', msg_data['value'])
                    if order_data:
                        self._process_order(order_data)
                        processed += 1
                elif msg_data['topic'] == 'hft-execution-events':
                    exec_data = self.schema_registry.deserialize('execution_event', msg_data['value'])
                    if exec_data:
                        self._process_execution(exec_data)
                        processed += 1
            except Exception as e:
                logger.error(f"Error processing order message: {e}")
        
        with self._lock:
            self.messages_processed += processed
        
        return {'processed': processed}
    
    def _process_order(self, order_data: Dict[str, Any]):
        """Process order message."""
        for callback_name, callback_func in self.callbacks.items():
            try:
                callback_func('order', order_data)
            except Exception as e:
                logger.error(f"Error in order callback {callback_name}: {e}")
    
    def _process_execution(self, exec_data: Dict[str, Any]):
        """Process execution message."""
        for callback_name, callback_func in self.callbacks.items():
            try:
                callback_func('execution', exec_data)
            except Exception as e:
                logger.error(f"Error in execution callback {callback_name}: {e}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get consumer statistics."""
        with self._lock:
            runtime = (datetime.now() - self.start_time).total_seconds()
            return {
                'consumer_id': self.consumer_id,
                'messages_processed': self.messages_processed,
                'runtime_seconds': runtime,
                'messages_per_second': self.messages_processed / runtime if runtime > 0 else 0
            }


# Global instance
_order_consumer: Optional[OrderConsumer] = None

def get_order_consumer() -> OrderConsumer:
    """Get or create global order consumer."""
    global _order_consumer
    if _order_consumer is None:
        _order_consumer = OrderConsumer()
    return _order_consumer
