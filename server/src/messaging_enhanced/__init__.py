"""
Enhanced Messaging Infrastructure
================================

This module provides enhanced messaging capabilities for the HFT system:
- Kafka for high-throughput market data streams
- RabbitMQ for control messages (existing)
- gRPC for low-latency service communication

Components:
- kafka/: Kafka producers, consumers, and schemas
- rabbitmq/: Existing RabbitMQ integration (enhanced)
- grpc/: Low-latency binary protocols
"""

__version__ = "1.0.0"
__author__ = "HFT Trading System"

# Re-export main components
from .kafka.kafka_manager import KafkaManager
from .kafka.schema_registry import SchemaRegistry
from .kafka.topic_manager import TopicManager

# Re-export specialized producers and consumers
from .kafka.producers import (
    MarketDataProducer,
    OrderProducer,
    SentimentProducer,
    RiskEventProducer
)

from .kafka.consumers import (
    MarketDataConsumer,
    OrderConsumer,
    SentimentConsumer,
    RiskEventConsumer
)

__all__ = [
    # Core components
    "KafkaManager",
    "SchemaRegistry",
    "TopicManager",
    
    # Specialized producers
    "MarketDataProducer",
    "OrderProducer",
    "SentimentProducer", 
    "RiskEventProducer",
    
    # Specialized consumers
    "MarketDataConsumer",
    "OrderConsumer",
    "SentimentConsumer",
    "RiskEventConsumer"
]
