"""
RabbitMQ Connection Management
=============================

Connection management and setup for RabbitMQ messaging.
"""

import asyncio
from typing import Optional
import aio_pika
from aio_pika import Connection, Channel, Exchange, Queue

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from config.settings import settings
from logger import get_infrastructure_logger

logger = get_infrastructure_logger("rabbitmq_connection")

# Global connection and channel
_connection: Optional[Connection] = None
_channel: Optional[Channel] = None
_exchanges: dict = {}
_queues: dict = {}

async def get_rabbitmq_connection() -> Optional[Connection]:
    """Get or create RabbitMQ connection."""
    global _connection
    
    if settings.RABBITMQ_URL == "disabled":
        logger.info("RabbitMQ is disabled in configuration")
        return None
    
    if _connection is None or _connection.is_closed:
        try:
            _connection = await aio_pika.connect_robust(
                settings.RABBITMQ_URL,
                heartbeat=60,
                connection_name="angel_one_api"
            )
            
            logger.info("RabbitMQ connection established", {
                "url": settings.RABBITMQ_URL.replace(settings.RABBITMQ_URL.split('@')[0].split('//')[1], '***'),
                "heartbeat": 60
            })
            
        except Exception as e:
            logger.error("Failed to connect to RabbitMQ", error=e)
            _connection = None
    
    return _connection

async def get_rabbitmq_channel() -> Optional[Channel]:
    """Get or create RabbitMQ channel.""" 
    global _channel
    
    connection = await get_rabbitmq_connection()
    if not connection:
        return None
    
    if _channel is None or _channel.is_closed:
        try:
            _channel = await connection.channel()
            
            # Set QoS for better performance
            await _channel.set_qos(prefetch_count=10)
            
            logger.info("RabbitMQ channel created")
            
        except Exception as e:
            logger.error("Failed to create RabbitMQ channel", error=e)
            _channel = None
    
    return _channel

async def setup_exchanges() -> dict:
    """Setup RabbitMQ exchanges."""
    global _exchanges
    
    channel = await get_rabbitmq_channel()
    if not channel:
        return {}
    
    try:
        exchanges_config = [
            ("angel.direct", aio_pika.ExchangeType.DIRECT),
            ("angel.topic", aio_pika.ExchangeType.TOPIC),
            ("angel.fanout", aio_pika.ExchangeType.FANOUT),
            ("angel.dlx", aio_pika.ExchangeType.DIRECT)  # Dead letter exchange
        ]
        
        for exchange_name, exchange_type in exchanges_config:
            exchange = await channel.declare_exchange(
                exchange_name,
                exchange_type,
                durable=True
            )
            _exchanges[exchange_name] = exchange
            
            logger.info("Exchange declared", {
                "name": exchange_name,
                "type": exchange_type.value
            })
        
        return _exchanges
        
    except Exception as e:
        logger.error("Failed to setup exchanges", error=e)
        return {}

async def setup_queues() -> dict:
    """Setup RabbitMQ queues."""
    global _queues
    
    channel = await get_rabbitmq_channel()
    if not channel:
        return {}
    
    try:
        # Ensure exchanges exist
        exchanges = await setup_exchanges()
        if not exchanges:
            return {}
        
        queues_config = [
            # AI Communication
            ("ai.requests", "angel.direct", "ai.requests"),
            ("ai.responses", "angel.direct", "ai.responses"),
            
            # Market Data Broadcasting
            ("market.data.broadcast", "angel.fanout", ""),
            ("market.data.ltp", "angel.topic", "market.ltp.*"),
            ("market.data.quotes", "angel.topic", "market.quotes.*"),
            
            # Trading Events
            ("trading.orders", "angel.topic", "trading.orders.*"),
            ("trading.executions", "angel.topic", "trading.executions.*"),
            
            # Portfolio Updates
            ("portfolio.updates", "angel.topic", "portfolio.*"),
            
            # Risk Alerts
            ("risk.alerts", "angel.direct", "risk.alerts"),
            
            # System Events
            ("system.health", "angel.topic", "system.health.*"),
            ("system.logs", "angel.topic", "system.logs.*"),
            
            # Audit Trail
            ("audit.trail", "angel.direct", "audit.trail")
        ]
        
        for queue_name, exchange_name, routing_key in queues_config:
            # Setup dead letter queue
            dlq_name = f"{queue_name}.dlq"
            dlq = await channel.declare_queue(
                dlq_name,
                durable=True,
                arguments={
                    "x-message-ttl": 86400000,  # 24 hours
                    "x-expires": 172800000       # 48 hours
                }
            )
            
            # Main queue with dead letter configuration
            queue = await channel.declare_queue(
                queue_name,
                durable=True,
                arguments={
                    "x-dead-letter-exchange": "angel.dlx",
                    "x-dead-letter-routing-key": dlq_name,
                    "x-message-ttl": 3600000  # 1 hour
                }
            )
            
            # Bind queue to exchange
            if exchange_name in exchanges:
                await queue.bind(exchanges[exchange_name], routing_key)
                
                logger.info("Queue setup completed", {
                    "queue": queue_name,
                    "exchange": exchange_name,
                    "routing_key": routing_key,
                    "dlq": dlq_name
                })
            
            _queues[queue_name] = queue
            _queues[dlq_name] = dlq
        
        return _queues
        
    except Exception as e:
        logger.error("Failed to setup queues", error=e)
        return {}

async def init_rabbitmq():
    """Initialize RabbitMQ connection and setup."""
    try:
        logger.info("Initializing RabbitMQ infrastructure...")
        
        # Test connection
        connection = await get_rabbitmq_connection()
        if not connection:
            logger.warning("RabbitMQ connection not available")
            return
        
        # Setup exchanges and queues
        exchanges = await setup_exchanges()
        queues = await setup_queues()
        
        logger.success("RabbitMQ initialization completed", {
            "exchanges": len(exchanges),
            "queues": len(queues),
            "connection_status": "active"
        })
        
    except Exception as e:
        logger.error("RabbitMQ initialization failed", error=e)
        # Don't raise exception - service should work without RabbitMQ

async def close_rabbitmq():
    """Close RabbitMQ connections."""
    global _connection, _channel, _exchanges, _queues
    
    try:
        if _channel and not _channel.is_closed:
            await _channel.close()
            logger.info("RabbitMQ channel closed")
        
        if _connection and not _connection.is_closed:
            await _connection.close()
            logger.info("RabbitMQ connection closed")
        
        # Clear global variables
        _connection = None
        _channel = None
        _exchanges.clear()
        _queues.clear()
        
    except Exception as e:
        logger.error("Error closing RabbitMQ connections", error=e)

async def get_queue(queue_name: str) -> Optional[Queue]:
    """Get a specific queue by name."""
    if queue_name in _queues:
        return _queues[queue_name]
    
    # Try to setup queues if not already done
    await setup_queues()
    return _queues.get(queue_name)

async def get_exchange(exchange_name: str) -> Optional[Exchange]:
    """Get a specific exchange by name."""
    if exchange_name in _exchanges:
        return _exchanges[exchange_name]
    
    # Try to setup exchanges if not already done
    await setup_exchanges()
    return _exchanges.get(exchange_name)
