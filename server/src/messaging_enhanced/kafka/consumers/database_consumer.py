"""
Database Consumer for HFT System
=================================

Specialized consumer for database events with:
- Event processing and routing
- Database operation triggers
- Inter-service coordination
- Performance monitoring
"""

import logging
import time
import json
from typing import Dict, List, Any, Optional, Callable
from datetime import datetime
import threading
import asyncio
from ..kafka_manager import get_kafka_manager
from ..schema_registry import get_schema_registry

logger = logging.getLogger(__name__)

class DatabaseConsumer:
    """
    Specialized consumer for database events.
    
    Features:
    - Event processing and routing
    - Database operation triggers
    - Inter-service coordination
    - Performance monitoring
    """
    
    def __init__(self, consumer_id: str = "database_consumer", group_id: str = "database_service_group"):
        """
        Initialize database consumer.
        
        Args:
            consumer_id: Unique identifier for this consumer
            group_id: Consumer group ID
        """
        self.consumer_id = consumer_id
        self.group_id = group_id
        self.kafka_manager = get_kafka_manager()
        self.schema_registry = get_schema_registry()
        
        # Performance tracking
        self.events_processed = 0
        self.events_failed = 0
        self.bytes_received = 0
        self.start_time = datetime.now()
        self._lock = threading.Lock()
        self._running = False
        
        # Configuration
        self.topics = ["hft-database-events", "hft-database-health"]
        self.event_handlers: Dict[str, Callable] = {}
        
        # Register default event handlers
        self._register_default_handlers()
        
        logger.info(f"DatabaseConsumer initialized: {consumer_id}")
    
    def _register_default_handlers(self):
        """Register default event handlers."""
        self.event_handlers.update({
            'USER_CREATED': self._handle_user_created,
            'USER_UPDATED': self._handle_user_updated,
            'ORDER_CREATED': self._handle_order_created,
            'ORDER_UPDATED': self._handle_order_updated,
            'MARKET_DATA_STORED': self._handle_market_data_stored,
            'STRATEGY_ACTIVATED': self._handle_strategy_activated,
            'HEALTH_CHECK_PERFORMED': self._handle_health_check,
        })
    
    def register_handler(self, event_type: str, handler: Callable):
        """
        Register a custom event handler.
        
        Args:
            event_type: Type of event to handle
            handler: Handler function that takes (event_data) as parameter
        """
        self.event_handlers[event_type] = handler
        logger.info(f"Registered handler for event type: {event_type}")
    
    async def start_consuming(self, timeout: float = 1.0, max_messages: int = 100):
        """
        Start consuming database events.
        
        Args:
            timeout: Polling timeout in seconds
            max_messages: Maximum messages to process per batch
        """
        if self._running:
            logger.warning("DatabaseConsumer is already running")
            return
        
        self._running = True
        logger.info(f"Starting DatabaseConsumer: {self.consumer_id}")
        
        try:
            # Create consumer
            consumer = self.kafka_manager.get_consumer(
                consumer_id=self.consumer_id,
                topics=self.topics,
                group_id=self.group_id,
                auto_offset_reset="latest"
            )
            
            while self._running:
                try:
                    # Consume messages
                    messages = self.kafka_manager.consume_messages(
                        consumer_id=self.consumer_id,
                        timeout=timeout,
                        max_messages=max_messages
                    )
                    
                    if messages:
                        await self._process_messages(messages)
                    
                    # Small delay to prevent busy waiting
                    await asyncio.sleep(0.01)
                    
                except Exception as e:
                    logger.error(f"Error in consume loop: {e}")
                    with self._lock:
                        self.events_failed += 1
                    
                    # Brief pause before retrying
                    await asyncio.sleep(1.0)
        
        except Exception as e:
            logger.error(f"Fatal error in DatabaseConsumer: {e}")
        finally:
            self._running = False
            logger.info(f"DatabaseConsumer stopped: {self.consumer_id}")
    
    async def _process_messages(self, messages: List[Dict[str, Any]]):
        """Process consumed messages."""
        for message in messages:
            try:
                await self._process_single_message(message)
                
                with self._lock:
                    self.events_processed += 1
                    if 'value' in message and isinstance(message['value'], (str, bytes)):
                        self.bytes_received += len(str(message['value']))
                
            except Exception as e:
                logger.error(f"Error processing message: {e}")
                with self._lock:
                    self.events_failed += 1
    
    async def _process_single_message(self, message: Dict[str, Any]):
        """Process a single database event message."""
        try:
            # Extract message data
            topic = message.get('topic')
            value = message.get('value')
            key = message.get('key')
            
            if not value:
                logger.warning("Received empty message")
                return
            
            # Deserialize if it's bytes (Avro serialized)
            if isinstance(value, bytes):
                event_data = self.schema_registry.deserialize('database_event', value)
                if not event_data:
                    logger.error("Failed to deserialize database event")
                    return
            elif isinstance(value, dict):
                event_data = value
            else:
                logger.warning(f"Unknown message format: {type(value)}")
                return
            
            # Extract event information
            event_type = event_data.get('event_type')
            entity_type = event_data.get('entity_type')
            entity_id = event_data.get('entity_id')
            user_id = event_data.get('user_id')
            data = event_data.get('data', {})
            
            logger.debug(f"Processing event: {event_type} for {entity_type} (ID: {entity_id})")
            
            # Route to appropriate handler
            if event_type in self.event_handlers:
                handler = self.event_handlers[event_type]
                await self._call_handler(handler, event_data)
            else:
                logger.debug(f"No handler registered for event type: {event_type}")
                await self._handle_unknown_event(event_data)
        
        except Exception as e:
            logger.error(f"Error in _process_single_message: {e}")
            raise
    
    async def _call_handler(self, handler: Callable, event_data: Dict[str, Any]):
        """Call event handler safely."""
        try:
            if asyncio.iscoroutinefunction(handler):
                await handler(event_data)
            else:
                handler(event_data)
        except Exception as e:
            logger.error(f"Error in event handler: {e}")
    
    # Default Event Handlers
    async def _handle_user_created(self, event_data: Dict[str, Any]):
        """Handle user creation events."""
        entity_id = event_data.get('entity_id')
        data = event_data.get('data', {})
        username = data.get('username')
        role = data.get('role')
        
        logger.info(f"User created: {username} (ID: {entity_id}, Role: {role})")
        
        # Here you could trigger additional actions like:
        # - Send welcome email
        # - Initialize user preferences
        # - Create default portfolio
        # - Notify other services
    
    async def _handle_user_updated(self, event_data: Dict[str, Any]):
        """Handle user update events."""
        entity_id = event_data.get('entity_id')
        data = event_data.get('data', {})
        
        logger.info(f"User updated: {entity_id} - {data}")
        
        # Trigger cache invalidation, notifications, etc.
    
    async def _handle_order_created(self, event_data: Dict[str, Any]):
        """Handle order creation events."""
        entity_id = event_data.get('entity_id')
        user_id = event_data.get('user_id')
        data = event_data.get('data', {})
        
        order_type = data.get('order_type')
        quantity = data.get('quantity')
        instrument_id = data.get('instrument_id')
        
        logger.info(f"Order created: {entity_id} by user {user_id} ({order_type} {quantity} of {instrument_id})")
        
        # Here you could trigger:
        # - Risk checks
        # - Portfolio updates
        # - Notification to execution service
        # - Audit logging
    
    async def _handle_order_updated(self, event_data: Dict[str, Any]):
        """Handle order update events."""
        entity_id = event_data.get('entity_id')
        data = event_data.get('data', {})
        
        logger.info(f"Order updated: {entity_id} - {data}")
        
        # Update caches, notify clients, etc.
    
    async def _handle_market_data_stored(self, event_data: Dict[str, Any]):
        """Handle market data storage events."""
        data = event_data.get('data', {})
        symbol = data.get('symbol')
        price = data.get('price')
        
        logger.debug(f"Market data stored for {symbol}: {price}")
        
        # Trigger analytics, alerts, strategy evaluations
    
    async def _handle_strategy_activated(self, event_data: Dict[str, Any]):
        """Handle strategy activation events."""
        entity_id = event_data.get('entity_id')
        user_id = event_data.get('user_id')
        data = event_data.get('data', {})
        
        logger.info(f"Strategy activated: {entity_id} by user {user_id}")
        
        # Start strategy execution, allocate resources, etc.
    
    async def _handle_health_check(self, event_data: Dict[str, Any]):
        """Handle health check events."""
        data = event_data.get('data', {})
        status = data.get('status')
        
        logger.debug(f"Database health check: {status}")
        
        # Update monitoring dashboards, trigger alerts if unhealthy
    
    async def _handle_unknown_event(self, event_data: Dict[str, Any]):
        """Handle unknown event types."""
        event_type = event_data.get('event_type')
        entity_type = event_data.get('entity_type')
        
        logger.debug(f"Unknown event type: {event_type} for {entity_type}")
        
        # Log for analysis, potentially route to generic handlers
    
    def stop_consuming(self):
        """Stop consuming messages."""
        logger.info(f"Stopping DatabaseConsumer: {self.consumer_id}")
        self._running = False
    
    def get_stats(self) -> Dict[str, Any]:
        """Get consumer statistics."""
        with self._lock:
            runtime = (datetime.now() - self.start_time).total_seconds()
            
            return {
                'consumer_id': self.consumer_id,
                'group_id': self.group_id,
                'topics': self.topics,
                'events_processed': self.events_processed,
                'events_failed': self.events_failed,
                'bytes_received': self.bytes_received,
                'runtime_seconds': runtime,
                'events_per_second': self.events_processed / runtime if runtime > 0 else 0,
                'failure_rate': self.events_failed / (self.events_processed + self.events_failed) if (self.events_processed + self.events_failed) > 0 else 0,
                'is_running': self._running,
                'registered_handlers': list(self.event_handlers.keys()),
                'start_time': self.start_time.isoformat()
            }
    
    def close(self):
        """Close the consumer."""
        logger.info(f"Closing DatabaseConsumer: {self.consumer_id}")
        self.stop_consuming()
        
        # Log final statistics
        stats = self.get_stats()
        logger.info(f"DatabaseConsumer final stats: {stats}")


# Global database consumer instance
_database_consumer: Optional[DatabaseConsumer] = None
_consumer_lock = threading.Lock()

def get_database_consumer(consumer_id: str = "database_consumer", group_id: str = "database_service_group") -> DatabaseConsumer:
    """Get or create global database consumer instance."""
    global _database_consumer
    
    with _consumer_lock:
        if _database_consumer is None:
            _database_consumer = DatabaseConsumer(consumer_id, group_id)
        return _database_consumer

def close_database_consumer():
    """Close global database consumer."""
    global _database_consumer
    
    with _consumer_lock:
        if _database_consumer:
            _database_consumer.close()
            _database_consumer = None
