"""
Kafka Manager for HFT System
============================

Centralized Kafka management with:
- Connection pooling
- Producer/consumer lifecycle management
- Error handling and reconnection
- Performance monitoring
"""

import logging
import json
from typing import Dict, List, Optional, Any, Callable
from confluent_kafka import Producer, Consumer, KafkaError, KafkaException
from confluent_kafka.admin import AdminClient, NewTopic
import threading
import time
from datetime import datetime

logger = logging.getLogger(__name__)

class KafkaManager:
    """
    Thread-safe Kafka manager for HFT system.
    
    Features:
    - Connection pooling
    - Automatic retry and reconnection
    - Performance monitoring
    - Schema registry integration
    """
    
    def __init__(self, bootstrap_servers: str = "localhost:9092"):
        """
        Initialize Kafka manager.
        
        Args:
            bootstrap_servers: Comma-separated list of Kafka brokers
        """
        self.bootstrap_servers = bootstrap_servers
        self.producers: Dict[str, Producer] = {}
        self.consumers: Dict[str, Consumer] = {}
        self.admin_client: Optional[AdminClient] = None
        self._lock = threading.Lock()
        
        # Performance monitoring
        self.message_counts = {}
        self.error_counts = {}
        self.last_activity = {}
        
        logger.info(f"KafkaManager initialized with brokers: {bootstrap_servers}")
    
    def get_producer(self, producer_id: str = "default") -> Producer:
        """
        Get or create a Kafka producer.
        
        Args:
            producer_id: Unique identifier for the producer
            
        Returns:
            Kafka producer instance
        """
        with self._lock:
            if producer_id not in self.producers:
                config = {
                    'bootstrap.servers': self.bootstrap_servers,
                    'client.id': f'hft-producer-{producer_id}',
                    'acks': 'all',  # Wait for all replicas
                    'retries': 3,
                    'batch.size': 16384,
                    'linger.ms': 5,  # Small batch delay for throughput
                    'compression.type': 'snappy',  # Fast compression
                    'max.in.flight.requests.per.connection': 5,
                    'enable.idempotence': True,  # Exactly-once semantics
                    'delivery.timeout.ms': 30000,
                }
                
                self.producers[producer_id] = Producer(config)
                self.message_counts[producer_id] = 0
                self.error_counts[producer_id] = 0
                logger.info(f"Created Kafka producer: {producer_id}")
            
            return self.producers[producer_id]
    
    def get_consumer(
        self, 
        consumer_id: str,
        topics: List[str],
        group_id: str,
        auto_offset_reset: str = "latest"
    ) -> Consumer:
        """
        Get or create a Kafka consumer.
        
        Args:
            consumer_id: Unique identifier for the consumer
            topics: List of topics to subscribe to
            group_id: Consumer group ID
            auto_offset_reset: Where to start reading (earliest/latest)
            
        Returns:
            Kafka consumer instance
        """
        with self._lock:
            if consumer_id not in self.consumers:
                config = {
                    'bootstrap.servers': self.bootstrap_servers,
                    'group.id': group_id,
                    'client.id': f'hft-consumer-{consumer_id}',
                    'auto.offset.reset': auto_offset_reset,
                    'enable.auto.commit': True,
                    'auto.commit.interval.ms': 1000,
                    'max.poll.interval.ms': 300000,
                    'session.timeout.ms': 10000,
                    'heartbeat.interval.ms': 3000,
                    'fetch.min.bytes': 1,
                    'fetch.wait.max.ms': 500,  # Low latency
                }
                
                consumer = Consumer(config)
                consumer.subscribe(topics)
                self.consumers[consumer_id] = consumer
                self.message_counts[consumer_id] = 0
                self.error_counts[consumer_id] = 0
                logger.info(f"Created Kafka consumer: {consumer_id} for topics: {topics}")
            
            return self.consumers[consumer_id]
    
    def get_admin_client(self) -> AdminClient:
        """Get or create Kafka admin client."""
        if self.admin_client is None:
            config = {
                'bootstrap.servers': self.bootstrap_servers,
                'client.id': 'hft-admin'
            }
            self.admin_client = AdminClient(config)
            logger.info("Created Kafka admin client")
        
        return self.admin_client
    
    def create_topics(self, topics: List[Dict[str, Any]]) -> Dict[str, bool]:
        """
        Create Kafka topics.
        
        Args:
            topics: List of topic configurations
                   [{'name': 'topic-name', 'partitions': 3, 'replication': 1}]
                   
        Returns:
            Dict mapping topic names to creation success status
        """
        admin = self.get_admin_client()
        
        new_topics = []
        for topic_config in topics:
            new_topic = NewTopic(
                topic=topic_config['name'],
                num_partitions=topic_config.get('partitions', 3),
                replication_factor=topic_config.get('replication', 1),
                config=topic_config.get('config', {})
            )
            new_topics.append(new_topic)
        
        # Create topics
        fs = admin.create_topics(new_topics, validate_only=False)
        
        results = {}
        for topic, f in fs.items():
            try:
                f.result()  # The result itself is None
                results[topic] = True
                logger.info(f"Topic created successfully: {topic}")
            except KafkaException as e:
                if e.args[0].code() == KafkaError.TOPIC_ALREADY_EXISTS:
                    results[topic] = True
                    logger.info(f"Topic already exists: {topic}")
                else:
                    results[topic] = False
                    logger.error(f"Failed to create topic {topic}: {e}")
        
        return results
    
    def send_message(
        self,
        topic: str,
        message: Any,
        key: Optional[str] = None,
        producer_id: str = "default",
        callback: Optional[Callable] = None
    ) -> bool:
        """
        Send a message to Kafka topic.
        
        Args:
            topic: Kafka topic name
            message: Message payload (will be JSON serialized)
            key: Optional message key for partitioning
            producer_id: Producer instance to use
            callback: Optional delivery callback
            
        Returns:
            True if message was queued successfully
        """
        try:
            producer = self.get_producer(producer_id)
            
            # Serialize message
            if isinstance(message, (dict, list)):
                message_bytes = json.dumps(message).encode('utf-8')
            elif isinstance(message, str):
                message_bytes = message.encode('utf-8')
            else:
                message_bytes = str(message).encode('utf-8')
            
            # Prepare key
            key_bytes = key.encode('utf-8') if key else None
            
            # Default callback for monitoring
            def delivery_callback(err, msg):
                if err:
                    self.error_counts[producer_id] += 1
                    logger.error(f"Message delivery failed: {err}")
                    if callback:
                        callback(err, msg)
                else:
                    self.message_counts[producer_id] += 1
                    self.last_activity[producer_id] = datetime.now()
                    if callback:
                        callback(err, msg)
            
            # Send message
            producer.produce(
                topic=topic,
                value=message_bytes,
                key=key_bytes,
                callback=delivery_callback
            )
            
            # Trigger delivery (non-blocking)
            producer.poll(0)
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to send message to {topic}: {e}")
            self.error_counts[producer_id] += 1
            return False
    
    def consume_messages(
        self,
        consumer_id: str,
        timeout: float = 1.0,
        max_messages: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Consume messages from Kafka.
        
        Args:
            consumer_id: Consumer instance to use
            timeout: Polling timeout in seconds
            max_messages: Maximum messages to return
            
        Returns:
            List of consumed messages
        """
        if consumer_id not in self.consumers:
            logger.error(f"Consumer not found: {consumer_id}")
            return []
        
        consumer = self.consumers[consumer_id]
        messages = []
        
        try:
            for _ in range(max_messages):
                msg = consumer.poll(timeout=timeout)
                
                if msg is None:
                    break
                
                if msg.error():
                    if msg.error().code() == KafkaError._PARTITION_EOF:
                        continue
                    else:
                        logger.error(f"Consumer error: {msg.error()}")
                        self.error_counts[consumer_id] += 1
                        break
                
                # Parse message
                try:
                    value = json.loads(msg.value().decode('utf-8'))
                except json.JSONDecodeError:
                    value = msg.value().decode('utf-8')
                
                key = msg.key().decode('utf-8') if msg.key() else None
                
                message_data = {
                    'topic': msg.topic(),
                    'partition': msg.partition(),
                    'offset': msg.offset(),
                    'key': key,
                    'value': value,
                    'timestamp': msg.timestamp()[1] if msg.timestamp()[0] else None,
                    'headers': dict(msg.headers()) if msg.headers() else {}
                }
                
                messages.append(message_data)
                self.message_counts[consumer_id] += 1
                self.last_activity[consumer_id] = datetime.now()
        
        except Exception as e:
            logger.error(f"Error consuming messages: {e}")
            self.error_counts[consumer_id] += 1
        
        return messages
    
    def get_stats(self) -> Dict[str, Any]:
        """Get Kafka manager statistics."""
        return {
            'producers': list(self.producers.keys()),
            'consumers': list(self.consumers.keys()),
            'message_counts': self.message_counts.copy(),
            'error_counts': self.error_counts.copy(),
            'last_activity': {k: v.isoformat() for k, v in self.last_activity.items()},
            'bootstrap_servers': self.bootstrap_servers
        }
    
    def flush_all_producers(self, timeout: float = 10.0):
        """Flush all producers to ensure message delivery."""
        for producer_id, producer in self.producers.items():
            try:
                remaining = producer.flush(timeout)
                if remaining > 0:
                    logger.warning(f"Producer {producer_id}: {remaining} messages not delivered")
                else:
                    logger.info(f"Producer {producer_id}: all messages delivered")
            except Exception as e:
                logger.error(f"Error flushing producer {producer_id}: {e}")
    
    def close_all(self):
        """Close all Kafka connections."""
        logger.info("Closing all Kafka connections...")
        
        # Flush producers before closing
        self.flush_all_producers()
        
        # Close producers
        for producer_id, producer in self.producers.items():
            try:
                producer.close()
                logger.info(f"Closed producer: {producer_id}")
            except Exception as e:
                logger.error(f"Error closing producer {producer_id}: {e}")
        
        # Close consumers
        for consumer_id, consumer in self.consumers.items():
            try:
                consumer.close()
                logger.info(f"Closed consumer: {consumer_id}")
            except Exception as e:
                logger.error(f"Error closing consumer {consumer_id}: {e}")
        
        self.producers.clear()
        self.consumers.clear()
        logger.info("All Kafka connections closed")


# Global Kafka manager instance
_kafka_manager: Optional[KafkaManager] = None
_kafka_lock = threading.Lock()

def get_kafka_manager(bootstrap_servers: str = "localhost:9092") -> KafkaManager:
    """Get or create global Kafka manager instance."""
    global _kafka_manager
    
    with _kafka_lock:
        if _kafka_manager is None:
            _kafka_manager = KafkaManager(bootstrap_servers)
        return _kafka_manager

def close_kafka_manager():
    """Close global Kafka manager."""
    global _kafka_manager
    
    with _kafka_lock:
        if _kafka_manager:
            _kafka_manager.close_all()
            _kafka_manager = None
