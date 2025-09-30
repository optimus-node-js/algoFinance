"""
Kafka Strategy Worker
====================

Kafka-integrated strategy worker that consumes market data from Kafka topics
and produces trading signals. Designed for high-frequency, low-latency processing.
"""

import asyncio
import json
import logging
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime
import traceback

from confluent_kafka import Consumer, Producer, KafkaError
from .base_strategy_engine import BaseStrategyEngine

class KafkaStrategyWorker:
    """
    Kafka-integrated worker that runs strategy engines and handles message processing.
    
    Features:
    - Consumes market data from Kafka topics
    - Runs multiple strategy engines in parallel
    - Produces trading signals to output topics
    - Handles errors and reconnections gracefully
    - Monitors performance and latency
    """
    
    def __init__(
        self,
        worker_id: str,
        kafka_config: Dict[str, Any],
        input_topics: List[str],
        output_topic: str = "trading_signals"
    ):
        """
        Initialize Kafka strategy worker.
        
        Args:
            worker_id: Unique identifier for this worker
            kafka_config: Kafka connection configuration
            input_topics: List of Kafka topics to consume from
            output_topic: Kafka topic to produce signals to
        """
        self.worker_id = worker_id
        self.input_topics = input_topics
        self.output_topic = output_topic
        
        # Kafka configuration
        self.consumer_config = {
            **kafka_config,
            "group.id": f"strategy_worker_{worker_id}",
            "auto.offset.reset": "latest",
            "enable.auto.commit": False,
            "max.poll.interval.ms": 30000,
        }
        
        self.producer_config = {
            **kafka_config,
            "acks": "1",  # Wait for leader acknowledgment
            "retries": 3,
            "batch.size": 1000,
            "linger.ms": 10  # Batch for up to 10ms for better throughput
        }
        
        # Initialize Kafka clients
        self.consumer = None
        self.producer = None
        
        # Strategy engines
        self.strategy_engines: List[BaseStrategyEngine] = []
        
        # Worker state
        self.is_running = False
        self.message_count = 0
        self.error_count = 0
        self.start_time = None
        
        # Performance tracking
        self.metrics = {
            "messages_processed": 0,
            "signals_generated": 0,
            "errors": 0,
            "avg_processing_time_ms": 0.0,
            "throughput_msg_per_sec": 0.0
        }
        
        self.logger = logging.getLogger(f"kafka_worker.{worker_id}")
        
    def add_strategy_engine(self, strategy_engine: BaseStrategyEngine) -> None:
        """
        Add a strategy engine to this worker.
        
        Args:
            strategy_engine: Strategy engine instance to add
        """
        self.strategy_engines.append(strategy_engine)
        self.logger.info(f"Added strategy engine: {strategy_engine.strategy_id}")
        
    def remove_strategy_engine(self, strategy_id: str) -> bool:
        """
        Remove a strategy engine from this worker.
        
        Args:
            strategy_id: ID of strategy engine to remove
            
        Returns:
            True if removed, False if not found
        """
        for i, engine in enumerate(self.strategy_engines):
            if engine.strategy_id == strategy_id:
                del self.strategy_engines[i]
                self.logger.info(f"Removed strategy engine: {strategy_id}")
                return True
        return False
        
    def _setup_kafka_clients(self) -> None:
        """Initialize Kafka consumer and producer."""
        try:
            self.consumer = Consumer(self.consumer_config)
            self.producer = Producer(self.producer_config)
            self.consumer.subscribe(self.input_topics)
            self.logger.info(f"Kafka clients initialized, subscribed to: {self.input_topics}")
        except Exception as e:
            self.logger.error(f"Failed to setup Kafka clients: {str(e)}")
            raise
            
    def _process_market_data(self, market_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Process market data through all strategy engines.
        
        Args:
            market_data: Market data message from Kafka
            
        Returns:
            List of trading signals generated
        """
        signals = []
        processing_start = datetime.now()
        
        for engine in self.strategy_engines:
            try:
                if engine.is_active:
                    signal = engine.process_market_data(market_data)
                    if signal:
                        # Add metadata to signal
                        signal.update({
                            "strategy_id": engine.strategy_id,
                            "worker_id": self.worker_id,
                            "timestamp": datetime.now().isoformat(),
                            "symbol": market_data.get("symbol", engine.symbol)
                        })
                        signals.append(signal)
                        
            except Exception as e:
                self.logger.error(f"Error in strategy {engine.strategy_id}: {str(e)}")
                self.error_count += 1
                
        # Update performance metrics
        processing_time = (datetime.now() - processing_start).total_seconds() * 1000
        self.metrics["avg_processing_time_ms"] = (
            self.metrics["avg_processing_time_ms"] * 0.9 + processing_time * 0.1
        )
        
        return signals
        
    def _publish_signals(self, signals: List[Dict[str, Any]]) -> None:
        """
        Publish trading signals to Kafka output topic.
        
        Args:
            signals: List of trading signals to publish
        """
        for signal in signals:
            try:
                message_value = json.dumps(signal).encode('utf-8')
                key = f"{signal['symbol']}_{signal['strategy_id']}".encode('utf-8')
                
                # Asynchronous send with callback
                self.producer.produce(
                    topic=self.output_topic,
                    key=key,
                    value=message_value,
                    callback=self._delivery_callback
                )
                
                self.metrics["signals_generated"] += 1
                
            except Exception as e:
                self.logger.error(f"Error publishing signal: {str(e)}")
                self.error_count += 1
                
        # Ensure messages are sent
        self.producer.flush(timeout=1.0)
        
    def _delivery_callback(self, err, msg):
        """Callback for message delivery confirmation."""
        if err:
            self.logger.error(f"Message delivery failed: {err}")
            self.error_count += 1
        else:
            self.logger.debug(f"Signal delivered to {msg.topic()} [{msg.partition()}]")
            
    async def start(self) -> None:
        """Start the Kafka strategy worker."""
        self.logger.info(f"Starting Kafka strategy worker: {self.worker_id}")
        
        if not self.strategy_engines:
            raise ValueError("No strategy engines configured")
            
        self._setup_kafka_clients()
        self.is_running = True
        self.start_time = datetime.now()
        
        try:
            while self.is_running:
                await self._process_messages()
                
        except KeyboardInterrupt:
            self.logger.info("Received shutdown signal")
        except Exception as e:
            self.logger.error(f"Worker error: {str(e)}")
            self.logger.error(traceback.format_exc())
        finally:
            await self.stop()
            
    async def _process_messages(self) -> None:
        """Process messages from Kafka consumer."""
        try:
            # Poll for messages with short timeout for responsiveness
            msg = self.consumer.poll(timeout=0.1)
            
            if msg is None:
                return
                
            if msg.error():
                if msg.error().code() == KafkaError._PARTITION_EOF:
                    self.logger.debug(f"End of partition reached {msg.topic()}/{msg.partition()}")
                else:
                    self.logger.error(f"Consumer error: {msg.error()}")
                    self.error_count += 1
                return
                
            # Process the message
            try:
                market_data = json.loads(msg.value().decode('utf-8'))
                
                # Process through strategy engines
                signals = self._process_market_data(market_data)
                
                # Publish any generated signals
                if signals:
                    self._publish_signals(signals)
                    
                # Commit offset after successful processing
                self.consumer.commit(msg)
                
                # Update metrics
                self.message_count += 1
                self.metrics["messages_processed"] += 1
                self._update_throughput_metrics()
                
            except json.JSONDecodeError as e:
                self.logger.error(f"Invalid JSON in message: {str(e)}")
                self.error_count += 1
            except Exception as e:
                self.logger.error(f"Error processing message: {str(e)}")
                self.error_count += 1
                
        except Exception as e:
            self.logger.error(f"Error in message processing loop: {str(e)}")
            await asyncio.sleep(1)  # Brief pause on error
            
    def _update_throughput_metrics(self) -> None:
        """Update throughput metrics."""
        if self.start_time:
            elapsed_seconds = (datetime.now() - self.start_time).total_seconds()
            if elapsed_seconds > 0:
                self.metrics["throughput_msg_per_sec"] = self.message_count / elapsed_seconds
                
    async def stop(self) -> None:
        """Stop the Kafka strategy worker gracefully."""
        self.logger.info(f"Stopping Kafka strategy worker: {self.worker_id}")
        self.is_running = False
        
        if self.consumer:
            self.consumer.close()
            
        if self.producer:
            self.producer.flush(timeout=5.0)
            
        # Log final metrics
        self.logger.info(f"Worker {self.worker_id} processed {self.message_count} messages, generated {self.metrics['signals_generated']} signals")
        
    def get_metrics(self) -> Dict[str, Any]:
        """
        Get current worker performance metrics.
        
        Returns:
            Dictionary containing performance metrics
        """
        uptime = 0
        if self.start_time:
            uptime = (datetime.now() - self.start_time).total_seconds()
            
        strategy_metrics = [engine.get_performance_metrics() for engine in self.strategy_engines]
        
        return {
            "worker_id": self.worker_id,
            "uptime_seconds": uptime,
            "is_running": self.is_running,
            "message_count": self.message_count,
            "error_count": self.error_count,
            "strategy_count": len(self.strategy_engines),
            "metrics": self.metrics,
            "strategy_engines": strategy_metrics
        }
        
    def get_health_status(self) -> Dict[str, Any]:
        """
        Get health status of the worker.
        
        Returns:
            Health status information
        """
        error_rate = 0
        if self.message_count > 0:
            error_rate = self.error_count / self.message_count
            
        is_healthy = (
            self.is_running and
            error_rate < 0.05 and  # Less than 5% error rate
            len(self.strategy_engines) > 0
        )
        
        return {
            "worker_id": self.worker_id,
            "healthy": is_healthy,
            "error_rate": error_rate,
            "last_processed": datetime.now().isoformat(),
            "strategy_engines_active": sum(1 for engine in self.strategy_engines if engine.is_active)
        }

