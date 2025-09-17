"""
Fallback Message Broker Implementation
Provides in-memory message passing when RabbitMQ is not available.
For development and testing purposes.
"""

import sys
import os
import json
import logging
import threading
import time
from typing import Dict, List, Optional, Callable, Any
from datetime import datetime
from collections import defaultdict, deque
import queue

# Add the project root directory to the Python path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
sys.path.append(PROJECT_ROOT)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class FallbackMessageBroker:
    """
    In-memory message broker fallback when RabbitMQ is not available.
    
    Features:
    - In-memory message queues
    - Exchange and routing simulation
    - Thread-safe operations
    - Message persistence (memory only)
    - Subscription and publishing
    """
    
    def __init__(self):
        """Initialize the Fallback Message Broker."""
        self.exchanges = {}
        self.queues = {}
        self.bindings = {}
        self.subscribers = {}
        self.message_history = deque(maxlen=1000)  # Keep last 1000 messages
        self.is_connected = True  # Always connected in fallback mode
        self.connection_lock = threading.Lock()
        
        # Setup default exchanges
        self._setup_default_exchanges()
        
        logger.info("✅ Fallback Message Broker initialized (RabbitMQ alternative)")

    def _setup_default_exchanges(self):
        """Setup default exchanges that match our RabbitMQ configuration."""
        default_exchanges = [
            'market_data_realtime',
            'ai_analysis',
            'risk_management',
            'trade_execution',
            'portfolio_updates',
            'system_alerts',
            'strategy_signals'
        ]
        
        for exchange_name in default_exchanges:
            self.exchanges[exchange_name] = {
                'type': 'topic',
                'queues': [],
                'created_at': datetime.now()
            }
            logger.info(f"📤 Created fallback exchange: {exchange_name}")

    def connect(self):
        """Connect to the fallback broker (always successful)."""
        with self.connection_lock:
            self.is_connected = True
            logger.info("✅ Fallback message broker connected")
            return True

    def disconnect(self):
        """Disconnect from the fallback broker."""
        with self.connection_lock:
            self.is_connected = False
            logger.info("🔌 Fallback message broker disconnected")

    def publish(self, exchange: str, routing_key: str, message: Any):
        """
        Publish a message to an exchange.
        
        Args:
            exchange: Exchange name
            routing_key: Routing key for message
            message: Message content (will be JSON serialized)
        """
        try:
            if not self.is_connected:
                logger.warning("⚠️ Cannot publish - fallback broker not connected")
                return False
            
            # Serialize message
            if isinstance(message, str):
                message_body = message
            else:
                message_body = json.dumps(message)
            
            # Create message envelope
            message_envelope = {
                'exchange': exchange,
                'routing_key': routing_key,
                'body': message_body,
                'timestamp': datetime.now().isoformat(),
                'message_id': f"fallback_{int(time.time() * 1000)}"
            }
            
            # Store in message history
            self.message_history.append(message_envelope)
            
            # Deliver to subscribers
            self._deliver_message(message_envelope)
            
            logger.debug(f"📤 Published message to {exchange}/{routing_key}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error publishing message: {e}")
            return False

    def subscribe(self, exchange: str, routing_key: str, callback: Callable[[str], None]):
        """
        Subscribe to messages from an exchange.
        
        Args:
            exchange: Exchange to subscribe to
            routing_key: Routing key pattern
            callback: Function to call when message received
        """
        try:
            subscription_key = f"{exchange}.{routing_key}"
            
            if subscription_key not in self.subscribers:
                self.subscribers[subscription_key] = []
            
            self.subscribers[subscription_key].append(callback)
            
            logger.info(f"📥 Subscribed to {exchange}/{routing_key}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error subscribing: {e}")
            return False

    def _deliver_message(self, message_envelope: Dict[str, Any]):
        """Deliver message to all matching subscribers."""
        try:
            exchange = message_envelope['exchange']
            routing_key = message_envelope['routing_key']
            
            # Find matching subscribers
            for subscription_key, callbacks in self.subscribers.items():
                sub_exchange, sub_routing_key = subscription_key.split('.', 1)
                
                # Simple pattern matching (exact match or wildcard)
                if (sub_exchange == exchange and 
                    (sub_routing_key == routing_key or sub_routing_key == '*')):
                    
                    # Deliver to all callbacks
                    for callback in callbacks:
                        try:
                            callback(message_envelope['body'])
                        except Exception as e:
                            logger.error(f"❌ Error in message callback: {e}")
                            
        except Exception as e:
            logger.error(f"❌ Error delivering message: {e}")

    def get_message_history(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get recent message history."""
        return list(self.message_history)[-limit:]

    def get_statistics(self) -> Dict[str, Any]:
        """Get broker statistics."""
        return {
            'connected': self.is_connected,
            'exchanges': len(self.exchanges),
            'subscribers': len(self.subscribers),
            'total_messages': len(self.message_history),
            'broker_type': 'fallback',
            'uptime': 'session_based'
        }

    def clear_history(self):
        """Clear message history."""
        self.message_history.clear()
        logger.info("🧹 Message history cleared")

# Global fallback broker instance
_fallback_broker = None

def get_fallback_message_broker():
    """Get the global fallback message broker instance."""
    global _fallback_broker
    if _fallback_broker is None:
        _fallback_broker = FallbackMessageBroker()
    return _fallback_broker

def test_fallback_broker():
    """Test the fallback message broker."""
    print("🧪 Testing Fallback Message Broker")
    print("=" * 40)
    
    broker = get_fallback_message_broker()
    
    # Test subscription
    received_messages = []
    
    def test_callback(message):
        received_messages.append(message)
        print(f"📥 Received: {message}")
    
    # Subscribe to test exchange
    broker.subscribe('test_exchange', 'test.pattern', test_callback)
    
    # Publish test messages
    test_messages = [
        {'type': 'test', 'data': 'Hello World'},
        {'type': 'test', 'data': 'Message 2'},
        'Simple string message'
    ]
    
    for msg in test_messages:
        broker.publish('test_exchange', 'test.pattern', msg)
    
    # Wait a moment for delivery
    time.sleep(0.1)
    
    # Check results
    print(f"\n📊 Results:")
    print(f"   Messages sent: {len(test_messages)}")
    print(f"   Messages received: {len(received_messages)}")
    print(f"   Broker stats: {broker.get_statistics()}")
    
    # Test message history
    history = broker.get_message_history(5)
    print(f"   Recent messages: {len(history)}")
    
    success = len(received_messages) == len(test_messages)
    
    if success:
        print("\n✅ Fallback Message Broker test PASSED!")
    else:
        print("\n❌ Fallback Message Broker test FAILED!")
    
    return success

if __name__ == '__main__':
    test_fallback_broker()




