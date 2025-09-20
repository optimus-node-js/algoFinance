"""
RabbitMQ Messaging Package
=========================

Message broker integration for AI engine communication.
"""

from .connection import init_rabbitmq, close_rabbitmq, get_rabbitmq_connection
from .publisher import MessagePublisher, publish_to_ai
from .consumer import MessageConsumer, start_message_consumer
from .schemas import AIRequest, AIResponse, MarketDataEvent, TradingEvent

__all__ = [
    "init_rabbitmq",
    "close_rabbitmq", 
    "get_rabbitmq_connection",
    "MessagePublisher",
    "publish_to_ai",
    "MessageConsumer",
    "start_message_consumer",
    "AIRequest",
    "AIResponse",
    "MarketDataEvent",
    "TradingEvent"
]
