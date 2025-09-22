"""
Risk Event Producer for HFT System
==================================

Specialized producer for risk management events and decisions.
"""

import logging
import time
import uuid
from typing import Dict, Any, Optional, List
from datetime import datetime
import threading
from ..kafka_manager import get_kafka_manager
from ..schema_registry import get_schema_registry

logger = logging.getLogger(__name__)

class RiskEventProducer:
    """Producer for risk management events."""
    
    def __init__(self, producer_id: str = "risk_event_producer"):
        self.producer_id = producer_id
        self.kafka_manager = get_kafka_manager()
        self.schema_registry = get_schema_registry()
        self.topic = "hft-risk-events"
        self.events_sent = 0
        self.start_time = datetime.now()
        self._lock = threading.Lock()
        
        logger.info(f"RiskEventProducer initialized: {producer_id}")
    
    def send_risk_event(
        self,
        event_type: str,
        decision: str,
        risk_score: float,
        event_id: Optional[str] = None,
        order_id: Optional[str] = None,
        symbol: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Send risk event."""
        try:
            if not event_id:
                event_id = f"RISK_{int(time.time() * 1000)}_{uuid.uuid4().hex[:8]}"
            
            now_ns = int(time.time() * 1_000_000_000)
            
            message = {
                'event_id': event_id,
                'event_type': event_type.upper(),
                'decision': decision.upper(),
                'risk_score': risk_score,
                'timestamp': now_ns,
                'processing_latency_ns': kwargs.get('processing_latency_ns', 0),
                'risk_factors': kwargs.get('risk_factors', []),
                'circuit_breaker_triggered': kwargs.get('circuit_breaker_triggered', False),
                'emergency_stop_triggered': kwargs.get('emergency_stop_triggered', False),
                'model_version': kwargs.get('model_version', '1.0'),
                'metadata': kwargs.get('metadata', {})
            }
            
            # Add optional fields
            if order_id:
                message['order_id'] = order_id
            if symbol:
                message['symbol'] = symbol
            if 'strategy_id' in kwargs:
                message['strategy_id'] = kwargs['strategy_id']
            
            serialized = self.schema_registry.serialize('risk_event', message)
            if not serialized:
                return {'success': False, 'error': 'Serialization failed'}
            
            # Use symbol or order_id as key for partitioning
            key = symbol or order_id or event_id
            
            success = self.kafka_manager.send_message(
                topic=self.topic,
                message=serialized,
                key=key,
                producer_id=self.producer_id
            )
            
            if success:
                with self._lock:
                    self.events_sent += 1
                
                return {
                    'success': True,
                    'event_id': event_id,
                    'event_type': event_type,
                    'decision': decision,
                    'risk_score': risk_score
                }
            else:
                return {'success': False, 'error': 'Failed to send to Kafka'}
                
        except Exception as e:
            logger.error(f"Error sending risk event: {e}")
            return {'success': False, 'error': str(e)}
    
    def get_stats(self) -> Dict[str, Any]:
        """Get producer statistics."""
        with self._lock:
            runtime = (datetime.now() - self.start_time).total_seconds()
            return {
                'producer_id': self.producer_id,
                'events_sent': self.events_sent,
                'runtime_seconds': runtime,
                'events_per_second': self.events_sent / runtime if runtime > 0 else 0
            }


# Global instance
_risk_event_producer: Optional[RiskEventProducer] = None

def get_risk_event_producer() -> RiskEventProducer:
    """Get or create global risk event producer."""
    global _risk_event_producer
    if _risk_event_producer is None:
        _risk_event_producer = RiskEventProducer()
    return _risk_event_producer
