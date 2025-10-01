"""
Kafka Integration for HFT System
================================

High-throughput, low-latency message streaming for:
- Market data feeds
- Trade execution events
- Sentiment signals
- Risk events

Features:
- Avro schema registry integration
- Producer/consumer with automatic serialization
- Topic management and configuration
- Performance monitoring
- Specialized producers and consumers
"""

from .kafka_manager import KafkaManager
from .schema_registry import SchemaRegistry
from .topic_manager import TopicManager

# Import specialized producers
from .producers import (
    MarketDataProducer,
    OrderProducer,
    SentimentProducer,
    RiskEventProducer,
    DatabaseProducer
)

# Import specialized consumers  
from .consumers import (
    MarketDataConsumer,
    OrderConsumer,
    SentimentConsumer,
    RiskEventConsumer,
    DatabaseConsumer
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
    "DatabaseProducer",
    
    # Specialized consumers
    "MarketDataConsumer",
    "OrderConsumer",
    "SentimentConsumer", 
    "RiskEventConsumer",
    "DatabaseConsumer"
]
