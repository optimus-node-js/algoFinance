"""
RabbitMQ Message Consumer
========================

Consumes messages from RabbitMQ for AI responses and system events.
"""

import json
import asyncio
from typing import Callable, Dict, Any, Optional

import aio_pika
from aio_pika import IncomingMessage

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from .connection import get_queue
from logger import get_infrastructure_logger

logger = get_infrastructure_logger("rabbitmq_consumer")

class MessageConsumer:
    """Handles message consumption from RabbitMQ."""
    
    def __init__(self):
        self.message_handlers: Dict[str, Callable] = {}
        self.consumer_tasks: list = []
        self.running = False
    
    def register_handler(self, message_type: str, handler: Callable):
        """
        Register a handler for specific message type.
        
        Args:
            message_type: Type of message to handle
            handler: Async function to handle the message
        """
        self.message_handlers[message_type] = handler
        logger.info("Message handler registered", {"message_type": message_type})
    
    async def process_ai_response(self, message: IncomingMessage):
        """Process AI engine response message."""
        try:
            # Decode message
            message_body = json.loads(message.body.decode())
            message_type = message_body.get("message_type", "unknown")
            correlation_id = message_body.get("correlation_id")
            
            logger.info("AI response received", {
                "message_type": message_type,
                "correlation_id": correlation_id
            })
            
            # Find and call appropriate handler
            if message_type in self.message_handlers:
                handler = self.message_handlers[message_type]
                await handler(message_body)
            else:
                logger.warning("No handler for AI response", {"message_type": message_type})
            
            # Acknowledge message
            await message.ack()
            
        except Exception as e:
            logger.error("Failed to process AI response", error=e)
            await message.nack(requeue=False)  # Send to dead letter queue
    
    async def process_system_event(self, message: IncomingMessage):
        """Process system event message."""
        try:
            # Decode message
            message_body = json.loads(message.body.decode())
            event_type = message_body.get("event_type", "unknown")
            
            logger.info("System event received", {"event_type": event_type})
            
            # Handle system events
            await self._handle_system_event(message_body)
            
            # Acknowledge message
            await message.ack()
            
        except Exception as e:
            logger.error("Failed to process system event", error=e)
            await message.nack(requeue=False)
    
    async def _handle_system_event(self, event_data: Dict[str, Any]):
        """Handle system events internally."""
        event_type = event_data.get("event_type")
        
        if event_type == "health_check_request":
            # Respond to health check requests
            await self._respond_to_health_check(event_data)
        elif event_type == "config_update":
            # Handle configuration updates
            await self._handle_config_update(event_data)
        else:
            logger.debug("Unhandled system event", {"event_type": event_type})
    
    async def _respond_to_health_check(self, request_data: Dict[str, Any]):
        """Respond to health check request."""
        try:
            # Import here to avoid circular imports
            from api.routers.health import health_checker
            
            # Get current health status
            # This would be implemented with actual health check
            health_status = {
                "service": "angel_one_api",
                "status": "healthy",
                "timestamp": request_data.get("timestamp"),
                "response_to": request_data.get("correlation_id")
            }
            
            logger.info("Health check response prepared", health_status)
            
        except Exception as e:
            logger.error("Failed to respond to health check", error=e)
    
    async def _handle_config_update(self, config_data: Dict[str, Any]):
        """Handle configuration update."""
        try:
            logger.info("Configuration update received", {
                "config_keys": list(config_data.get("config", {}).keys())
            })
            
            # Handle configuration updates here
            # This would update application settings dynamically
            
        except Exception as e:
            logger.error("Failed to handle config update", error=e)
    
    async def start_consuming(self):
        """Start consuming messages from all relevant queues."""
        try:
            self.running = True
            logger.info("Starting message consumption...")
            
            # Start AI response consumer
            ai_response_task = asyncio.create_task(
                self._consume_queue("ai.responses", self.process_ai_response)
            )
            self.consumer_tasks.append(ai_response_task)
            
            # Start system events consumer  
            system_events_task = asyncio.create_task(
                self._consume_queue("system.health", self.process_system_event)
            )
            self.consumer_tasks.append(system_events_task)
            
            logger.success("Message consumption started", {
                "active_consumers": len(self.consumer_tasks)
            })
            
            # Wait for all consumers
            await asyncio.gather(*self.consumer_tasks)
            
        except Exception as e:
            logger.error("Message consumption failed", error=e)
            await self.stop_consuming()
    
    async def _consume_queue(self, queue_name: str, processor: Callable):
        """Consume messages from a specific queue."""
        try:
            queue = await get_queue(queue_name)
            if not queue:
                logger.warning(f"Queue {queue_name} not available")
                return
            
            logger.info("Starting queue consumer", {"queue": queue_name})
            
            # Start consuming
            async with queue.iterator() as queue_iter:
                async for message in queue_iter:
                    if not self.running:
                        break
                    
                    try:
                        await processor(message)
                    except Exception as e:
                        logger.error("Message processing failed", {
                            "error": str(e),
                            "queue": queue_name
                        })
                        await message.nack(requeue=False)
            
        except Exception as e:
            logger.error("Queue consumption failed", {
                "error": str(e),
                "queue": queue_name
            })
    
    async def stop_consuming(self):
        """Stop all message consumers."""
        try:
            self.running = False
            
            # Cancel all consumer tasks
            for task in self.consumer_tasks:
                if not task.done():
                    task.cancel()
            
            # Wait for cancellation
            if self.consumer_tasks:
                await asyncio.gather(*self.consumer_tasks, return_exceptions=True)
            
            self.consumer_tasks.clear()
            
            logger.info("Message consumption stopped")
            
        except Exception as e:
            logger.error("Error stopping message consumption", error=e)

# Global consumer instance
consumer = MessageConsumer()

async def start_message_consumer():
    """Start the global message consumer."""
    await consumer.start_consuming()

async def stop_message_consumer():
    """Stop the global message consumer."""
    await consumer.stop_consuming()

def register_message_handler(message_type: str, handler: Callable):
    """Register a global message handler."""
    consumer.register_handler(message_type, handler)
