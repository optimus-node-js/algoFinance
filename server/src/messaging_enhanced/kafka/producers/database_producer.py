"""
Database Producer for HFT System
=================================

Specialized producer for database events with:
- Entity lifecycle tracking
- Inter-service communication
- Event correlation
- Performance optimization
"""

import logging
import time
import uuid
from typing import Dict, List, Any, Optional
from datetime import datetime
import threading
from ..kafka_manager import get_kafka_manager
from ..schema_registry import get_schema_registry

logger = logging.getLogger(__name__)

class DatabaseProducer:
    """
    Specialized producer for database events.
    
    Features:
    - Entity lifecycle management
    - Event correlation
    - Inter-service notifications
    - Performance monitoring
    """
    
    def __init__(self, producer_id: str = "database_producer"):
        """
        Initialize database producer.
        
        Args:
            producer_id: Unique identifier for this producer
        """
        self.producer_id = producer_id
        self.kafka_manager = get_kafka_manager()
        self.schema_registry = get_schema_registry()
        
        # Performance tracking
        self.events_sent = 0
        self.events_rejected = 0
        self.bytes_sent = 0
        self.start_time = datetime.now()
        self._lock = threading.Lock()
        
        # Configuration
        self.events_topic = "hft-database-events"
        self.health_topic = "hft-database-health"
        
        logger.info(f"DatabaseProducer initialized: {producer_id}")
    
    def send_database_event(
        self,
        event_type: str,
        entity_type: str,
        entity_id: Optional[str] = None,
        user_id: Optional[str] = None,
        data: Optional[Dict[str, Any]] = None,
        correlation_id: Optional[str] = None,
        session_id: Optional[str] = None,
        source_ip: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Send a database event.
        
        Args:
            event_type: Type of database event
            entity_type: Type of entity affected
            entity_id: ID of the affected entity
            user_id: User ID associated with the event
            data: Event-specific data payload
            correlation_id: Correlation ID for request tracking
            session_id: Session ID if applicable
            source_ip: Source IP address if applicable
            **kwargs: Additional event fields
            
        Returns:
            Dictionary with event details and send status
        """
        try:
            # Generate event ID
            event_id = f"DB_{int(time.time() * 1000)}_{uuid.uuid4().hex[:8]}"
            now_ns = int(time.time() * 1_000_000_000)
            
            # Create event message
            message = {
                'event_id': event_id,
                'timestamp': now_ns,
                'service': 'database_service',
                'event_type': event_type.upper(),
                'entity_type': entity_type.upper(),
                'entity_id': entity_id,
                'user_id': user_id,
                'data': data or {},
                'metadata': kwargs.get('metadata', {}),
                'correlation_id': correlation_id,
                'source_ip': source_ip,
                'session_id': session_id
            }
            
            # Serialize message
            serialized = self.schema_registry.serialize('database_event', message)
            if not serialized:
                logger.error(f"Failed to serialize database event {event_id}")
                with self._lock:
                    self.events_rejected += 1
                return {
                    'event_id': event_id,
                    'status': 'SERIALIZATION_FAILED',
                    'success': False,
                    'error': 'Failed to serialize event message'
                }
            
            # Send to Kafka (use entity_type_event_type as key for ordering)
            key = f"{entity_type}_{event_type}"
            success = self.kafka_manager.send_message(
                topic=self.events_topic,
                message=serialized,
                key=key,
                producer_id=self.producer_id,
                callback=lambda err, msg: self._event_delivery_callback(err, msg, event_id)
            )
            
            if success:
                with self._lock:
                    self.events_sent += 1
                    self.bytes_sent += len(serialized)
                
                logger.debug(f"Database event sent: {event_id} ({entity_type} {event_type})")
                
                return {
                    'event_id': event_id,
                    'status': 'SENT',
                    'success': True,
                    'entity_type': entity_type,
                    'event_type': event_type,
                    'timestamp': now_ns
                }
            else:
                with self._lock:
                    self.events_rejected += 1
                
                return {
                    'event_id': event_id,
                    'status': 'SEND_FAILED',
                    'success': False,
                    'error': 'Failed to send to Kafka'
                }
                
        except Exception as e:
            logger.error(f"Error sending database event: {e}")
            with self._lock:
                self.events_rejected += 1
            
            return {
                'event_id': event_id if 'event_id' in locals() else 'UNKNOWN',
                'status': 'ERROR',
                'success': False,
                'error': str(e)
            }
    
    def send_health_event(
        self,
        status: str,
        connection_status: str,
        query_time_ms: Optional[float] = None,
        uptime_seconds: Optional[float] = None,
        total_queries: Optional[int] = None,
        error_count: Optional[int] = None,
        error_message: Optional[str] = None
    ) -> bool:
        """
        Send database health event.
        
        Args:
            status: Health status (healthy/unhealthy)
            connection_status: Database connection status
            query_time_ms: Last query time in milliseconds
            uptime_seconds: Service uptime in seconds
            total_queries: Total queries executed
            error_count: Total error count
            error_message: Error message if unhealthy
            
        Returns:
            True if health event was sent successfully
        """
        try:
            health_data = {
                'status': status,
                'connection_status': connection_status,
                'query_time_ms': query_time_ms,
                'uptime_seconds': uptime_seconds,
                'total_queries': total_queries,
                'error_count': error_count,
                'error_message': error_message
            }
            
            # Remove None values
            health_data = {k: v for k, v in health_data.items() if v is not None}
            
            result = self.send_database_event(
                event_type='HEALTH_CHECK_PERFORMED',
                entity_type='HEALTH',
                data=health_data
            )
            
            return result['success']
            
        except Exception as e:
            logger.error(f"Error sending health event: {e}")
            return False
    
    def send_bulk_events(self, events: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Send multiple database events efficiently.
        
        Args:
            events: List of event data dictionaries
            
        Returns:
            Dictionary with send results and statistics
        """
        start_time = time.time()
        successful_events = []
        failed_events = []
        
        logger.info(f"Sending bulk database events: {len(events)} events")
        
        for event_data in events:
            try:
                result = self.send_database_event(**event_data)
                if result['success']:
                    successful_events.append(result)
                else:
                    failed_events.append(result)
                    
            except Exception as e:
                logger.error(f"Error in bulk event send: {e}")
                failed_events.append({
                    'event_id': 'UNKNOWN',
                    'status': 'ERROR',
                    'success': False,
                    'error': str(e)
                })
        
        end_time = time.time()
        duration = end_time - start_time
        
        results = {
            'total_events': len(events),
            'successful': len(successful_events),
            'failed': len(failed_events),
            'duration_seconds': duration,
            'events_per_second': len(events) / duration if duration > 0 else 0,
            'success_rate': len(successful_events) / len(events) if len(events) > 0 else 0,
            'successful_events': successful_events,
            'failed_events': failed_events
        }
        
        logger.info(f"Bulk database event send completed: {results}")
        return results
    
    def _event_delivery_callback(self, err, msg, event_id: str):
        """Callback for event delivery confirmation."""
        if err:
            logger.error(f"Database event delivery failed for {event_id}: {err}")
        else:
            logger.debug(f"Database event delivered: {event_id} to {msg.topic()}[{msg.partition()}]@{msg.offset()}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get producer statistics."""
        with self._lock:
            runtime = (datetime.now() - self.start_time).total_seconds()
            
            return {
                'producer_id': self.producer_id,
                'events_topic': self.events_topic,
                'health_topic': self.health_topic,
                'events_sent': self.events_sent,
                'events_rejected': self.events_rejected,
                'bytes_sent': self.bytes_sent,
                'runtime_seconds': runtime,
                'events_per_second': self.events_sent / runtime if runtime > 0 else 0,
                'rejection_rate': self.events_rejected / (self.events_sent + self.events_rejected) if (self.events_sent + self.events_rejected) > 0 else 0,
                'start_time': self.start_time.isoformat()
            }
    
    def flush(self, timeout: float = 10.0):
        """Flush all pending messages."""
        try:
            producer = self.kafka_manager.get_producer(self.producer_id)
            remaining = producer.flush(timeout)
            if remaining > 0:
                logger.warning(f"DatabaseProducer: {remaining} messages not delivered after flush")
            else:
                logger.info(f"DatabaseProducer: all messages flushed successfully")
        except Exception as e:
            logger.error(f"Error flushing DatabaseProducer: {e}")
    
    def close(self):
        """Close the producer."""
        logger.info(f"Closing DatabaseProducer: {self.producer_id}")
        self.flush()
        
        # Log final statistics
        stats = self.get_stats()
        logger.info(f"DatabaseProducer final stats: {stats}")


# Global database producer instance
_database_producer: Optional[DatabaseProducer] = None
_producer_lock = threading.Lock()

def get_database_producer(producer_id: str = "database_producer") -> DatabaseProducer:
    """Get or create global database producer instance."""
    global _database_producer
    
    with _producer_lock:
        if _database_producer is None:
            _database_producer = DatabaseProducer(producer_id)
        return _database_producer

def close_database_producer():
    """Close global database producer."""
    global _database_producer
    
    with _producer_lock:
        if _database_producer:
            _database_producer.close()
            _database_producer = None
