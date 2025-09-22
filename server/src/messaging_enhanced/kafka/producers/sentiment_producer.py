"""
Sentiment Producer for HFT System
=================================

Specialized producer for sentiment signals from news and social media.
"""

import logging
import time
import uuid
from typing import Dict, Any, Optional
from datetime import datetime
import threading
from ..kafka_manager import get_kafka_manager
from ..schema_registry import get_schema_registry

logger = logging.getLogger(__name__)

class SentimentProducer:
    """Producer for sentiment signals."""
    
    def __init__(self, producer_id: str = "sentiment_producer"):
        self.producer_id = producer_id
        self.kafka_manager = get_kafka_manager()
        self.schema_registry = get_schema_registry()
        self.topic = "hft-sentiment-signals"
        self.signals_sent = 0
        self.start_time = datetime.now()
        self._lock = threading.Lock()
        
        logger.info(f"SentimentProducer initialized: {producer_id}")
    
    def send_sentiment_signal(
        self,
        symbol: str,
        sentiment_score: float,
        confidence: float,
        source: str,
        signal_id: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Send sentiment signal."""
        try:
            if not signal_id:
                signal_id = f"SIG_{int(time.time() * 1000)}_{uuid.uuid4().hex[:8]}"
            
            message = self.schema_registry.create_sentiment_signal(
                signal_id=signal_id,
                symbol=symbol,
                sentiment_score=sentiment_score,
                confidence=confidence,
                source=source,
                **kwargs
            )
            
            serialized = self.schema_registry.serialize('sentiment_signal', message)
            if not serialized:
                return {'success': False, 'error': 'Serialization failed'}
            
            success = self.kafka_manager.send_message(
                topic=self.topic,
                message=serialized,
                key=f"{symbol}:{source}",
                producer_id=self.producer_id
            )
            
            if success:
                with self._lock:
                    self.signals_sent += 1
                
                return {
                    'success': True,
                    'signal_id': signal_id,
                    'symbol': symbol,
                    'sentiment_score': sentiment_score,
                    'confidence': confidence
                }
            else:
                return {'success': False, 'error': 'Failed to send to Kafka'}
                
        except Exception as e:
            logger.error(f"Error sending sentiment signal: {e}")
            return {'success': False, 'error': str(e)}
    
    def get_stats(self) -> Dict[str, Any]:
        """Get producer statistics."""
        with self._lock:
            runtime = (datetime.now() - self.start_time).total_seconds()
            return {
                'producer_id': self.producer_id,
                'signals_sent': self.signals_sent,
                'runtime_seconds': runtime,
                'signals_per_second': self.signals_sent / runtime if runtime > 0 else 0
            }


# Global instance
_sentiment_producer: Optional[SentimentProducer] = None

def get_sentiment_producer() -> SentimentProducer:
    """Get or create global sentiment producer."""
    global _sentiment_producer
    if _sentiment_producer is None:
        _sentiment_producer = SentimentProducer()
    return _sentiment_producer
