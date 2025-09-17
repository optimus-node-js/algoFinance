"""
Enhanced Message Broker for Real-Time Service Communication
Provides comprehensive RabbitMQ integration for all microservices with intelligent routing,
error handling, and monitoring capabilities.
"""

import sys
import os
import json
import logging
import threading
import time
import asyncio
from typing import Dict, List, Optional, Callable, Any
from datetime import datetime
import pika
from pika.exchange_type import ExchangeType

# Add the project root directory to the Python path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
sys.path.append(PROJECT_ROOT)

from server.src.config import settings
from server.src.core.message_broker_fallback import get_fallback_message_broker

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class EnhancedMessageBroker:
    """
    Enhanced Message Broker for real-time microservices communication.
    Provides intelligent routing, error handling, and monitoring.
    """
    
    def __init__(self):
        """Initialize the Enhanced Message Broker."""
        self.connection = None
        self.channel = None
        self.is_connected = False
        self.consumers = {}
        self.exchanges = {}
        self.connection_lock = threading.Lock()
        
        # Message broker configuration
        self.config = {
            'host': 'localhost',
            'port': 5672,
            'virtual_host': '/',
            'heartbeat': 600,
            'blocked_connection_timeout': 300,
            'retry_attempts': 3,
            'retry_delay': 5
        }
        
        # Initialize connection
        self._initialize_connection()
        
        # Setup core exchanges
        self._setup_core_exchanges()
        
        logger.info("✅ Enhanced Message Broker initialized successfully")
    
    def _initialize_connection(self):
        """Initialize RabbitMQ connection with retry logic and fallback."""
        for attempt in range(self.config['retry_attempts']):
            try:
                connection_params = pika.ConnectionParameters(
                    host=self.config['host'],
                    port=self.config['port'],
                    virtual_host=self.config['virtual_host'],
                    heartbeat=self.config['heartbeat'],
                    blocked_connection_timeout=self.config['blocked_connection_timeout']
                )
                
                self.connection = pika.BlockingConnection(connection_params)
                self.channel = self.connection.channel()
                self.is_connected = True
                
                logger.info("✅ RabbitMQ connection established successfully")
                return
                
            except Exception as e:
                logger.warning(f"⚠️ RabbitMQ connection attempt {attempt + 1} failed: {e}")
                if attempt < self.config['retry_attempts'] - 1:
                    time.sleep(self.config['retry_delay'])
                else:
                    logger.error("❌ Failed to establish RabbitMQ connection after all attempts")
                    logger.warning("🔄 Falling back to in-memory message broker for development")
                    self._setup_fallback_broker()
                    self.is_connected = False
    
    def _setup_fallback_broker(self):
        """Setup fallback in-memory message broker when RabbitMQ is unavailable."""
        try:
            self.fallback_broker = get_fallback_message_broker()
            logger.info("✅ Fallback message broker initialized")
        except Exception as e:
            logger.error(f"❌ Failed to setup fallback broker: {e}")
    
    def _setup_core_exchanges(self):
        """Setup core exchanges for microservices communication."""
        if not self.is_connected:
            logger.warning("⚠️ Cannot setup exchanges - RabbitMQ not connected")
            return
        
        try:
            # Core system exchanges
            core_exchanges = {
                'market_data_realtime': {
                    'type': ExchangeType.topic,
                    'durable': True,
                    'description': 'Real-time market data distribution'
                },
                'ai_analysis': {
                    'type': ExchangeType.topic,
                    'durable': True,
                    'description': 'AI analysis results and signals'
                },
                'risk_management': {
                    'type': ExchangeType.topic,
                    'durable': True,
                    'description': 'Risk management decisions and alerts'
                },
                'trade_execution': {
                    'type': ExchangeType.topic,
                    'durable': True,
                    'description': 'Trade execution and order management'
                },
                'portfolio_updates': {
                    'type': ExchangeType.topic,
                    'durable': True,
                    'description': 'Portfolio and position updates'
                },
                'system_alerts': {
                    'type': ExchangeType.fanout,
                    'durable': True,
                    'description': 'System-wide alerts and notifications'
                },
                'strategy_signals': {
                    'type': ExchangeType.topic,
                    'durable': True,
                    'description': 'Trading strategy signals and decisions'
                }
            }
            
            for exchange_name, config in core_exchanges.items():
                self.channel.exchange_declare(
                    exchange=exchange_name,
                    exchange_type=config['type'],
                    durable=config['durable']
                )
                self.exchanges[exchange_name] = config
                logger.info(f"✅ Exchange '{exchange_name}' declared: {config['description']}")
            
            # Setup core queues
            self._setup_core_queues()
            
        except Exception as e:
            logger.error(f"❌ Failed to setup core exchanges: {e}")
    
    def _setup_core_queues(self):
        """Setup core queues for service communication."""
        try:
            core_queues = {
                # Market Data Queues
                'market_data_ticks': {
                    'exchange': 'market_data_realtime',
                    'routing_key': 'tick.*',
                    'durable': True
                },
                'market_data_candles': {
                    'exchange': 'market_data_realtime', 
                    'routing_key': 'candle.*',
                    'durable': True
                },
                
                # AI Analysis Queues
                'ai_volatility_analysis': {
                    'exchange': 'ai_analysis',
                    'routing_key': 'volatility.*',
                    'durable': True
                },
                'ai_pattern_detection': {
                    'exchange': 'ai_analysis',
                    'routing_key': 'pattern.*',
                    'durable': True
                },
                'ai_sentiment_analysis': {
                    'exchange': 'ai_analysis',
                    'routing_key': 'sentiment.*',
                    'durable': True
                },
                
                # Risk Management Queues
                'risk_violations': {
                    'exchange': 'risk_management',
                    'routing_key': 'violation.*',
                    'durable': True
                },
                'risk_position_sizing': {
                    'exchange': 'risk_management',
                    'routing_key': 'position.size.*',
                    'durable': True
                },
                'risk_alerts': {
                    'exchange': 'risk_management',
                    'routing_key': 'alert.*',
                    'durable': True
                },
                
                # Strategy Queues
                'strategy_signals': {
                    'exchange': 'strategy_signals',
                    'routing_key': 'signal.*',
                    'durable': True
                },
                'strategy_execution': {
                    'exchange': 'strategy_signals',
                    'routing_key': 'execute.*',
                    'durable': True
                },
                
                # Portfolio Queues
                'portfolio_updates': {
                    'exchange': 'portfolio_updates',
                    'routing_key': 'update.*',
                    'durable': True
                },
                
                # System Alert Queues
                'system_alerts_critical': {
                    'exchange': 'system_alerts',
                    'routing_key': '',  # Fanout doesn't use routing key
                    'durable': True
                }
            }
            
            for queue_name, config in core_queues.items():
                # Declare queue
                self.channel.queue_declare(
                    queue=queue_name,
                    durable=config['durable']
                )
                
                # Bind queue to exchange
                self.channel.queue_bind(
                    exchange=config['exchange'],
                    queue=queue_name,
                    routing_key=config['routing_key']
                )
                
                logger.info(f"✅ Queue '{queue_name}' setup with routing key '{config['routing_key']}'")
                
        except Exception as e:
            logger.error(f"❌ Failed to setup core queues: {e}")
    
    def publish_message(self, exchange: str, routing_key: str, message: Dict[str, Any], 
                       persistent: bool = True) -> bool:
        """
        Publish a message to the specified exchange.
        
        Args:
            exchange: Exchange name
            routing_key: Routing key for message
            message: Message payload (will be JSON encoded)
            persistent: Whether message should persist in queue
            
        Returns:
            bool: True if message published successfully
        """
        if not self.is_connected or not self.channel or self.channel.is_closed:
            # Silently fail if connection is closed (during shutdown)
            return False
        
        try:
            # Add metadata to message (ensure JSON serializable)
            enhanced_message = {
                'timestamp': datetime.now().isoformat(),
                'source': 'enhanced_message_broker',
                'routing_key': routing_key,
                'data': self._make_json_serializable(message)
            }
            
            # Publish message
            self.channel.basic_publish(
                exchange=exchange,
                routing_key=routing_key,
                body=json.dumps(enhanced_message),
                properties=pika.BasicProperties(
                    delivery_mode=2 if persistent else 1,  # 2 = persistent
                    content_type='application/json',
                    timestamp=int(time.time())
                )
            )
            
            logger.debug(f"📤 Message published to {exchange} with routing key {routing_key}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to publish message: {e}")
            return False
    
    async def subscribe_to_queue_with_retry(self, queue_name: str, callback: Callable, 
                                          auto_ack: bool = False, max_retries: int = 10, 
                                          retry_delay: int = 3):
        """
        Subscribe to queue with intelligent retry mechanism.
        Waits for queue to be available instead of failing immediately.
        """
        for attempt in range(max_retries):
            try:
                # Check if we're connected
                if not self.is_connected:
                    logger.info(f"🔄 Attempting to connect for queue subscription '{queue_name}' (attempt {attempt + 1})")
                    await asyncio.sleep(retry_delay)
                    continue
                
                # Try to declare/access the queue
                try:
                    self.channel.queue_declare(queue=queue_name, durable=True, passive=True)
                except Exception:
                    # Queue doesn't exist, create it
                    self.channel.queue_declare(queue=queue_name, durable=True)
                
                def wrapped_callback(ch, method, properties, body):
                    try:
                        message = json.loads(body)
                        callback(message)
                        if not auto_ack:
                            ch.basic_ack(delivery_tag=method.delivery_tag)
                    except Exception as e:
                        logger.error(f"❌ Error processing message from {queue_name}: {e}")
                        if not auto_ack:
                            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
                
                self.channel.basic_qos(prefetch_count=1)
                self.channel.basic_consume(
                    queue=queue_name,
                    on_message_callback=wrapped_callback,
                    auto_ack=auto_ack
                )
                
                logger.info(f"✅ Successfully subscribed to queue '{queue_name}' (attempt {attempt + 1})")
                return True
                
            except Exception as e:
                logger.warning(f"⚠️ Queue '{queue_name}' subscription attempt {attempt + 1}/{max_retries} failed: {e}")
                if attempt < max_retries - 1:
                    logger.info(f"🔄 Retrying in {retry_delay} seconds...")
                    await asyncio.sleep(retry_delay)
                else:
                    logger.error(f"❌ Failed to subscribe to queue '{queue_name}' after {max_retries} attempts")
        
        return False
    
    async def wait_for_queues_ready(self, queue_names: List[str], timeout: int = 60) -> Dict[str, bool]:
        """
        Wait for multiple queues to be ready/available.
        Returns status for each queue.
        """
        results = {}
        start_time = asyncio.get_event_loop().time()
        
        logger.info(f"🔄 Waiting for {len(queue_names)} queues to be ready...")
        
        for queue_name in queue_names:
            queue_ready = False
            current_time = asyncio.get_event_loop().time()
            remaining_time = timeout - (current_time - start_time)
            
            if remaining_time <= 0:
                logger.warning(f"⚠️ Timeout reached while waiting for queue '{queue_name}'")
                results[queue_name] = False
                continue
            
            # Wait for this specific queue
            queue_start = asyncio.get_event_loop().time()
            while (asyncio.get_event_loop().time() - queue_start) < min(remaining_time, 30):
                try:
                    if self.is_connected:
                        # Try to declare queue passively (check if exists)
                        self.channel.queue_declare(queue=queue_name, durable=True, passive=True)
                        logger.info(f"✅ Queue '{queue_name}' is ready")
                        queue_ready = True
                        break
                    else:
                        logger.debug(f"🔄 Waiting for RabbitMQ connection...")
                        
                except Exception as e:
                    logger.debug(f"🔄 Queue '{queue_name}' not ready yet: {e}")
                    
                await asyncio.sleep(1)
            
            results[queue_name] = queue_ready
            if not queue_ready:
                logger.warning(f"⚠️ Queue '{queue_name}' not ready after waiting")
        
        ready_count = sum(results.values())
        logger.info(f"✅ Queue readiness check complete: {ready_count}/{len(queue_names)} queues ready")
        
        return results
    
    def subscribe_to_queue(self, queue_name: str, callback: Callable, auto_ack: bool = False):
        """
        Legacy subscribe method - now creates async task with retry mechanism.
        """
        try:
            # Create async task for subscription with retry
            asyncio.create_task(self.subscribe_to_queue_with_retry(
                queue_name, callback, auto_ack
            ))
        except Exception as e:
            logger.error(f"❌ Failed to create subscription task for {queue_name}: {e}")
    
    def subscribe_to_queue_sync(self, queue_name: str, callback: Callable, auto_ack: bool = False):
        """
        Original synchronous subscription method for backwards compatibility.
        """
        if not self.is_connected:
            logger.error("❌ Cannot subscribe - RabbitMQ not connected")
            return
        
        try:
            def wrapped_callback(ch, method, properties, body):
                try:
                    # Decode message
                    message = json.loads(body)
                    
                    # Call user callback
                    callback(message)
                    
                    # Acknowledge message if not auto-ack
                    if not auto_ack:
                        ch.basic_ack(delivery_tag=method.delivery_tag)
                        
                except Exception as e:
                    logger.error(f"❌ Error processing message from {queue_name}: {e}")
                    if not auto_ack:
                        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
            
            # Setup consumer
            self.channel.basic_qos(prefetch_count=1)
            self.channel.basic_consume(
                queue=queue_name,
                on_message_callback=wrapped_callback,
                auto_ack=auto_ack
            )
            
            self.consumers[queue_name] = {
                'callback': callback,
                'auto_ack': auto_ack
            }
            
            logger.info(f"✅ Subscribed to queue '{queue_name}'")
            
        except Exception as e:
            logger.error(f"❌ Failed to subscribe to queue {queue_name}: {e}")
    
    def start_consuming(self):
        """Start consuming messages (blocking call)."""
        if not self.is_connected:
            logger.error("❌ Cannot start consuming - RabbitMQ not connected")
            return
        
        try:
            logger.info("🔄 Starting message consumption...")
            self.channel.start_consuming()
        except KeyboardInterrupt:
            logger.info("🛑 Message consumption stopped by user")
            self.channel.stop_consuming()
        except Exception as e:
            logger.error(f"❌ Error during message consumption: {e}")
    
    def publish_market_data(self, symbol: str, timeframe: str, data: Dict[str, Any]):
        """Publish market data update."""
        routing_key = f"tick.{symbol}.{timeframe}"
        return self.publish_message('market_data_realtime', routing_key, {
            'symbol': symbol,
            'timeframe': timeframe,
            'data': data
        })
    
    def publish_ai_analysis(self, analysis_type: str, symbol: str, results: Dict[str, Any]):
        """Publish AI analysis results."""
        routing_key = f"{analysis_type}.{symbol}"
        return self.publish_message('ai_analysis', routing_key, {
            'analysis_type': analysis_type,
            'symbol': symbol,
            'results': results
        })
    
    def publish_risk_alert(self, alert_type: str, severity: str, details: Dict[str, Any]):
        """Publish risk management alert."""
        routing_key = f"alert.{severity}.{alert_type}"
        return self.publish_message('risk_management', routing_key, {
            'alert_type': alert_type,
            'severity': severity,
            'details': details
        })
    
    def publish_strategy_signal(self, strategy: str, symbol: str, signal: Dict[str, Any]):
        """Publish trading strategy signal."""
        routing_key = f"signal.{strategy}.{symbol}"
        return self.publish_message('strategy_signals', routing_key, {
            'strategy': strategy,
            'symbol': symbol,
            'signal': signal
        })
    
    def publish_system_alert(self, alert: Dict[str, Any]):
        """Publish system-wide alert (fanout)."""
        return self.publish_message('system_alerts', '', alert)
    
    def get_queue_info(self, queue_name: str) -> Optional[Dict]:
        """Get queue information (message count, consumers, etc.)."""
        if not self.is_connected:
            return None
        
        try:
            method = self.channel.queue_declare(queue=queue_name, passive=True)
            return {
                'message_count': method.method.message_count,
                'consumer_count': method.method.consumer_count,
                'queue_name': queue_name
            }
        except Exception as e:
            logger.error(f"❌ Failed to get queue info for {queue_name}: {e}")
            return None
    
    def get_connection_status(self) -> Dict[str, Any]:
        """Get connection status and statistics."""
        return {
            'is_connected': self.is_connected,
            'exchanges_count': len(self.exchanges),
            'consumers_count': len(self.consumers),
            'connection_info': {
                'host': self.config['host'],
                'port': self.config['port'],
                'virtual_host': self.config['virtual_host']
            }
        }
    
    def _make_json_serializable(self, obj: Any) -> Any:
        """Convert objects to JSON serializable format."""
        if isinstance(obj, datetime):
            return obj.isoformat()
        elif isinstance(obj, dict):
            return {key: self._make_json_serializable(value) for key, value in obj.items()}
        elif isinstance(obj, list):
            return [self._make_json_serializable(item) for item in obj]
        elif hasattr(obj, '__dict__'):
            return self._make_json_serializable(obj.__dict__)
        else:
            return obj
    
    def close(self):
        """Close RabbitMQ connection."""
        try:
            if self.channel and not self.channel.is_closed:
                self.channel.close()
            
            if self.connection and not self.connection.is_closed:
                self.connection.close()
            
            self.is_connected = False
            logger.info("✅ RabbitMQ connection closed successfully")
            
        except Exception as e:
            logger.error(f"❌ Error closing RabbitMQ connection: {e}")


# Global message broker instance
message_broker = None

def get_message_broker() -> EnhancedMessageBroker:
    """Get or create global message broker instance."""
    global message_broker
    if message_broker is None:
        message_broker = EnhancedMessageBroker()
    return message_broker

def close_message_broker():
    """Close global message broker instance."""
    global message_broker
    if message_broker:
        message_broker.close()
        message_broker = None


# Example usage and testing
if __name__ == '__main__':
    def test_message_broker():
        """Test the Enhanced Message Broker."""
        print("🧪 Testing Enhanced Message Broker...")
        
        # Initialize broker
        broker = EnhancedMessageBroker()
        
        # Test connection status
        status = broker.get_connection_status()
        print(f"Connection Status: {status}")
        
        # Test message publishing
        if broker.is_connected:
            # Test market data
            market_data = {
                'price': 2500.0,
                'volume': 1000,
                'timestamp': datetime.now().isoformat()
            }
            result = broker.publish_market_data('RELIANCE-EQ', '1m', market_data)
            print(f"Market data published: {result}")
            
            # Test AI analysis
            ai_results = {
                'volatility': 0.02,
                'trend': 'bullish',
                'confidence': 0.85
            }
            result = broker.publish_ai_analysis('volatility', 'RELIANCE-EQ', ai_results)
            print(f"AI analysis published: {result}")
            
            # Test risk alert
            risk_alert = {
                'position': 'RELIANCE-EQ',
                'violation': 'position_size_exceeded',
                'current_size': '12%',
                'limit': '10%'
            }
            result = broker.publish_risk_alert('position_limit', 'high', risk_alert)
            print(f"Risk alert published: {result}")
        
        # Cleanup
        broker.close()
        print("✅ Message Broker testing completed!")
    
    test_message_broker()
