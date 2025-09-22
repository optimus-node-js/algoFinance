"""
Risk Event Consumer for HFT System
==================================

Consumer for risk management events and decisions.
"""

import logging
import threading
from typing import Dict, Any, Callable, Optional
from datetime import datetime
from ..kafka_manager import get_kafka_manager
from ..schema_registry import get_schema_registry

logger = logging.getLogger(__name__)

class RiskEventConsumer:
    """Consumer for risk management events."""
    
    def __init__(self, consumer_id: str = "risk_event_consumer", group_id: str = "hft_risk_group"):
        self.consumer_id = consumer_id
        self.group_id = group_id
        self.kafka_manager = get_kafka_manager()
        self.schema_registry = get_schema_registry()
        self.topics = ["hft-risk-events"]
        self.events_processed = 0
        self.start_time = datetime.now()
        self._lock = threading.Lock()
        self.callbacks: Dict[str, Callable] = {}
        
        # Initialize consumer
        self.consumer = self.kafka_manager.get_consumer(
            consumer_id=self.consumer_id,
            topics=self.topics,
            group_id=self.group_id
        )
        
        logger.info(f"RiskEventConsumer initialized: {consumer_id}")
    
    def register_callback(self, callback_name: str, callback_func: Callable):
        """Register callback for risk event processing."""
        self.callbacks[callback_name] = callback_func
        logger.info(f"Registered risk event callback: {callback_name}")
    
    def process_batch(self, timeout: float = 1.0) -> Dict[str, Any]:
        """Process batch of risk event messages."""
        messages = self.kafka_manager.consume_messages(
            consumer_id=self.consumer_id,
            timeout=timeout,
            max_messages=10
        )
        
        processed = 0
        for msg_data in messages:
            try:
                event_data = self.schema_registry.deserialize('risk_event', msg_data['value'])
                if event_data:
                    self._process_risk_event(event_data)
                    processed += 1
            except Exception as e:
                logger.error(f"Error processing risk event message: {e}")
        
        with self._lock:
            self.events_processed += processed
        
        return {'processed': processed}
    
    def _process_risk_event(self, event_data: Dict[str, Any]):
        """Process risk event."""
        event_type = event_data.get('event_type', 'UNKNOWN')
        for callback_name, callback_func in self.callbacks.items():
            try:
                callback_func(event_type, event_data)
            except Exception as e:
                logger.error(f"Error in risk event callback {callback_name}: {e}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get consumer statistics."""
        with self._lock:
            runtime = (datetime.now() - self.start_time).total_seconds()
            return {
                'consumer_id': self.consumer_id,
                'events_processed': self.events_processed,
                'runtime_seconds': runtime,
                'events_per_second': self.events_processed / runtime if runtime > 0 else 0
            }


# Global instance
_risk_event_consumer: Optional[RiskEventConsumer] = None

def get_risk_event_consumer() -> RiskEventConsumer:
    """Get or create global risk event consumer."""
    global _risk_event_consumer
    if _risk_event_consumer is None:
        _risk_event_consumer = RiskEventConsumer()
    return _risk_event_consumer
