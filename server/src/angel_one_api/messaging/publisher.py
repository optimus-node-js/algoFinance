"""
RabbitMQ Message Publisher
=========================

Publishes messages to RabbitMQ for AI engine and system communication.
"""

import json
import uuid
from datetime import datetime, UTC
from typing import Dict, Any, Optional

import aio_pika

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from .connection import get_exchange, get_queue
from logger import get_infrastructure_logger

logger = get_infrastructure_logger("rabbitmq_publisher")

class MessagePublisher:
    """Handles message publishing to RabbitMQ."""
    
    def __init__(self):
        self.message_counter = 0
    
    async def publish_to_ai(
        self,
        message_type: str,
        data: Dict[str, Any],
        priority: int = 0,
        correlation_id: Optional[str] = None,
        reply_to: Optional[str] = None
    ) -> str:
        """
        Publish message to AI engine.
        
        Args:
            message_type: Type of message (e.g., 'market_data_request')
            data: Message payload
            priority: Message priority (0-9)
            correlation_id: Correlation ID for request tracking
            reply_to: Reply queue name
            
        Returns:
            str: Message correlation ID
        """
        try:
            # Get exchange and queue
            exchange = await get_exchange("angel.direct")
            if not exchange:
                logger.warning("AI exchange not available, message not sent")
                return correlation_id or str(uuid.uuid4())
            
            # Generate correlation ID if not provided
            if not correlation_id:
                correlation_id = str(uuid.uuid4())
            
            # Prepare message
            message_body = {
                "message_type": message_type,
                "correlation_id": correlation_id,
                "timestamp": datetime.now(UTC).isoformat(),
                "data": data,
                "source": "angel_one_service",
                "version": "1.0.0"
            }
            
            # Create message
            message = aio_pika.Message(
                json.dumps(message_body).encode(),
                correlation_id=correlation_id,
                reply_to=reply_to or "ai.responses",
                priority=priority,
                content_type="application/json",
                headers={
                    "message_type": message_type,
                    "source": "angel_one_service",
                    "timestamp": datetime.now(UTC).isoformat()
                }
            )
            
            # Publish message
            await exchange.publish(
                message,
                routing_key="ai.requests"
            )
            
            self.message_counter += 1
            
            logger.info("Message published to AI engine", {
                "message_type": message_type,
                "correlation_id": correlation_id,
                "data_size": len(json.dumps(data)),
                "priority": priority,
                "total_messages": self.message_counter
            })
            
            return correlation_id
            
        except Exception as e:
            logger.error("Failed to publish message to AI", {
                "error": str(e),
                "message_type": message_type,
                "correlation_id": correlation_id
            })
            raise
    
    async def broadcast_market_data(
        self,
        symbol: str,
        data: Dict[str, Any],
        data_type: str = "ltp_update"
    ):
        """
        Broadcast market data to all interested services.
        
        Args:
            symbol: Trading symbol
            data: Market data
            data_type: Type of market data
        """
        try:
            # Get fanout exchange for broadcasting
            exchange = await get_exchange("angel.fanout")
            if not exchange:
                logger.warning("Market data broadcast exchange not available")
                return
            
            # Prepare broadcast message
            message_body = {
                "type": "market_data_broadcast",
                "data_type": data_type,
                "symbol": symbol,
                "data": data,
                "timestamp": datetime.now(UTC).isoformat(),
                "source": "angel_one_service"
            }
            
            # Create message
            message = aio_pika.Message(
                json.dumps(message_body).encode(),
                content_type="application/json",
                headers={
                    "type": "market_data_broadcast",
                    "symbol": symbol,
                    "data_type": data_type
                }
            )
            
            # Broadcast to all subscribers
            await exchange.publish(message, routing_key="")
            
            logger.debug("Market data broadcasted", {
                "symbol": symbol,
                "data_type": data_type,
                "data_keys": list(data.keys())
            })
            
        except Exception as e:
            logger.error("Failed to broadcast market data", {
                "error": str(e),
                "symbol": symbol,
                "data_type": data_type
            })
    
    async def publish_trading_event(
        self,
        event_type: str,
        order_data: Dict[str, Any],
        routing_key: Optional[str] = None
    ):
        """
        Publish trading event.
        
        Args:
            event_type: Type of trading event
            order_data: Order/trade data
            routing_key: Custom routing key
        """
        try:
            # Get topic exchange for trading events
            exchange = await get_exchange("angel.topic")
            if not exchange:
                logger.warning("Trading events exchange not available")
                return
            
            # Prepare event message
            message_body = {
                "type": "trading_event",
                "event_type": event_type,
                "data": order_data,
                "timestamp": datetime.now(UTC).isoformat(),
                "source": "angel_one_service"
            }
            
            # Create message
            message = aio_pika.Message(
                json.dumps(message_body).encode(),
                content_type="application/json",
                headers={
                    "type": "trading_event",
                    "event_type": event_type
                }
            )
            
            # Use custom routing key or default
            if not routing_key:
                routing_key = f"trading.{event_type}"
            
            # Publish event
            await exchange.publish(message, routing_key=routing_key)
            
            logger.info("Trading event published", {
                "event_type": event_type,
                "routing_key": routing_key,
                "order_id": order_data.get("order_id")
            })
            
        except Exception as e:
            logger.error("Failed to publish trading event", {
                "error": str(e),
                "event_type": event_type
            })
    
    async def publish_portfolio_update(
        self,
        update_type: str,
        portfolio_data: Dict[str, Any]
    ):
        """
        Publish portfolio update event.
        
        Args:
            update_type: Type of portfolio update
            portfolio_data: Portfolio data
        """
        try:
            # Get topic exchange
            exchange = await get_exchange("angel.topic")
            if not exchange:
                logger.warning("Portfolio updates exchange not available")
                return
            
            # Prepare update message
            message_body = {
                "type": "portfolio_update",
                "update_type": update_type,
                "data": portfolio_data,
                "timestamp": datetime.now(UTC).isoformat(),
                "source": "angel_one_service"
            }
            
            # Create message
            message = aio_pika.Message(
                json.dumps(message_body).encode(),
                content_type="application/json",
                headers={
                    "type": "portfolio_update",
                    "update_type": update_type
                }
            )
            
            # Publish with routing key
            routing_key = f"portfolio.{update_type}"
            await exchange.publish(message, routing_key=routing_key)
            
            logger.info("Portfolio update published", {
                "update_type": update_type,
                "routing_key": routing_key
            })
            
        except Exception as e:
            logger.error("Failed to publish portfolio update", {
                "error": str(e),
                "update_type": update_type
            })
    
    async def publish_system_health(self, health_data: Dict[str, Any]):
        """
        Publish system health status.
        
        Args:
            health_data: Health check data
        """
        try:
            # Get topic exchange
            exchange = await get_exchange("angel.topic")
            if not exchange:
                return
            
            # Prepare health message
            message_body = {
                "type": "system_health",
                "data": health_data,
                "timestamp": datetime.now(UTC).isoformat(),
                "source": "angel_one_service"
            }
            
            # Create message
            message = aio_pika.Message(
                json.dumps(message_body).encode(),
                content_type="application/json"
            )
            
            # Publish with health routing key
            await exchange.publish(message, routing_key="system.health.angel_one")
            
            logger.debug("System health published")
            
        except Exception as e:
            logger.error("Failed to publish system health", error=e)

# Global publisher instance
publisher = MessagePublisher()

# Convenience functions
async def publish_to_ai(message_type: str, data: Dict[str, Any], **kwargs) -> str:
    """Convenience function to publish to AI engine."""
    return await publisher.publish_to_ai(message_type, data, **kwargs)

async def broadcast_market_data(symbol: str, data: Dict[str, Any], **kwargs):
    """Convenience function to broadcast market data."""
    await publisher.broadcast_market_data(symbol, data, **kwargs)

async def publish_trading_event(event_type: str, order_data: Dict[str, Any], **kwargs):
    """Convenience function to publish trading events."""
    await publisher.publish_trading_event(event_type, order_data, **kwargs)
