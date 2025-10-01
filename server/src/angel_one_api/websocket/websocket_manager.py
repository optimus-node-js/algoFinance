"""
Angel One WebSocket Manager
===========================

Real-time WebSocket client for Angel One SmartAPI with Kafka integration.
Handles live market data streaming, authentication, and message processing.

Features:
- Angel One WebSocket authentication
- Real-time market data streaming
- Kafka producer integration
- Automatic reconnection and error handling
- Subscription management
- Performance monitoring

Author: HFT Trading System
"""

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

import json
import time
import asyncio
import websockets
import threading
from typing import Dict, List, Optional, Set, Callable, Any
from datetime import datetime, UTC
from dataclasses import dataclass
import uuid

# Import Angel One components
from authentication.auth_manager import AuthManager
from logger import get_service_logger

# Import Kafka components
sys.path.append(str(Path(__file__).parent.parent.parent / "messaging_enhanced"))
try:
    from messaging_enhanced.kafka.producers.market_data_producer import MarketDataProducer
    from messaging_enhanced.kafka.kafka_manager import get_kafka_manager
    KAFKA_AVAILABLE = True
except ImportError as e:
    print(f"⚠️ Kafka not available for WebSocket manager: {e}")
    KAFKA_AVAILABLE = False

logger = get_service_logger("websocket_manager")

@dataclass
class SubscriptionRequest:
    """WebSocket subscription request."""
    action: str  # subscribe/unsubscribe
    mode: str    # LTP, QUOTE, SNAP_QUOTE
    token_list: List[str]

@dataclass
class WebSocketStats:
    """WebSocket connection statistics."""
    connected: bool = False
    messages_received: int = 0
    messages_sent: int = 0
    bytes_received: int = 0
    bytes_sent: int = 0
    errors: int = 0
    last_message_time: Optional[datetime] = None
    connection_time: Optional[datetime] = None
    reconnections: int = 0

class AngelOneWebSocketManager:
    """
    Angel One WebSocket manager with Kafka integration.
    
    Handles real-time market data streaming from Angel One SmartAPI
    and publishes data to Kafka topics for consumption by other services.
    """
    
    def __init__(self, auth_manager: AuthManager = None):
        """
        Initialize WebSocket manager.
        
        Args:
            auth_manager: Angel One authentication manager
        """
        self.auth_manager = auth_manager or AuthManager()
        
        # WebSocket configuration
        self.websocket_url = "wss://smartapisocket.angelone.in/smart-stream"
        self.websocket = None
        self.is_connected = False
        self.is_running = False
        
        # Subscription management
        self.subscriptions: Dict[str, SubscriptionRequest] = {}
        self.subscribed_tokens: Set[str] = set()
        
        # Performance tracking
        self.stats = WebSocketStats()
        self._stats_lock = threading.Lock()
        
        # Kafka integration
        if KAFKA_AVAILABLE:
            self.kafka_manager = get_kafka_manager()
            self.market_data_producer = MarketDataProducer("angel_one_websocket")
        else:
            self.kafka_manager = None
            self.market_data_producer = None
        
        # Message handlers
        self.message_handlers: Dict[str, Callable] = {}
        self._register_default_handlers()
        
        # Connection management
        self.reconnect_attempts = 0
        self.max_reconnect_attempts = 10
        self.reconnect_delay = 5  # seconds
        
        logger.info("AngelOneWebSocketManager initialized")
    
    def _register_default_handlers(self):
        """Register default message handlers."""
        self.message_handlers.update({
            'tk': self._handle_tick_data,
            'sf': self._handle_snapfull_data,
            'dp': self._handle_depth_data,
            'oi': self._handle_oi_data,
            'error': self._handle_error_message
        })
    
    async def connect(self) -> bool:
        """
        Connect to Angel One WebSocket.
        
        Returns:
            True if connection successful, False otherwise
        """
        try:
            # Ensure we have valid authentication
            if not self.auth_manager.is_authenticated():
                logger.info("Authenticating with Angel One...")
                auth_result = await self.auth_manager.authenticate()
                if not auth_result:
                    logger.error("Failed to authenticate with Angel One")
                    return False
            
            # Get authentication details
            auth_data = self.auth_manager.get_auth_data()
            if not auth_data or 'jwtToken' not in auth_data:
                logger.error("No valid JWT token available")
                return False
            
            # Connect to WebSocket
            logger.info(f"Connecting to Angel One WebSocket: {self.websocket_url}")
            self.websocket = await websockets.connect(
                self.websocket_url,
                ping_interval=30,
                ping_timeout=10,
                close_timeout=10
            )
            
            # Send authentication message
            auth_message = {
                "a": "auth",
                "user": auth_data.get('clientcode', ''),
                "token": auth_data.get('jwtToken', '')
            }
            
            await self.websocket.send(json.dumps(auth_message))
            logger.info("Authentication message sent")
            
            # Wait for authentication response
            response = await asyncio.wait_for(self.websocket.recv(), timeout=10)
            auth_response = json.loads(response)
            
            if auth_response.get('s') == 'OK':
                self.is_connected = True
                with self._stats_lock:
                    self.stats.connected = True
                    self.stats.connection_time = datetime.now(UTC)
                
                logger.success("✅ WebSocket connected and authenticated")
                return True
            else:
                logger.error(f"WebSocket authentication failed: {auth_response}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Failed to connect to WebSocket: {e}")
            self.is_connected = False
            with self._stats_lock:
                self.stats.connected = False
                self.stats.errors += 1
            return False
    
    async def disconnect(self):
        """Disconnect from WebSocket."""
        try:
            self.is_running = False
            self.is_connected = False
            
            if self.websocket:
                await self.websocket.close()
                self.websocket = None
            
            with self._stats_lock:
                self.stats.connected = False
            
            logger.info("WebSocket disconnected")
            
        except Exception as e:
            logger.error(f"Error during WebSocket disconnect: {e}")
    
    async def subscribe(self, tokens: List[str], mode: str = "LTP") -> bool:
        """
        Subscribe to market data for given tokens.
        
        Args:
            tokens: List of instrument tokens
            mode: Subscription mode (LTP, QUOTE, SNAP_QUOTE)
            
        Returns:
            True if subscription successful
        """
        try:
            if not self.is_connected:
                logger.error("WebSocket not connected")
                return False
            
            # Create subscription request
            subscription = SubscriptionRequest(
                action="subscribe",
                mode=mode,
                token_list=tokens
            )
            
            # Send subscription message
            sub_message = {
                "a": "subscribe",
                "v": [[subscription.mode, token] for token in tokens]
            }
            
            await self.websocket.send(json.dumps(sub_message))
            
            # Track subscription
            sub_id = str(uuid.uuid4())
            self.subscriptions[sub_id] = subscription
            self.subscribed_tokens.update(tokens)
            
            with self._stats_lock:
                self.stats.messages_sent += 1
                self.stats.bytes_sent += len(json.dumps(sub_message))
            
            logger.info(f"📡 Subscribed to {len(tokens)} tokens in {mode} mode")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to subscribe: {e}")
            with self._stats_lock:
                self.stats.errors += 1
            return False
    
    async def unsubscribe(self, tokens: List[str], mode: str = "LTP") -> bool:
        """
        Unsubscribe from market data for given tokens.
        
        Args:
            tokens: List of instrument tokens
            mode: Subscription mode
            
        Returns:
            True if unsubscription successful
        """
        try:
            if not self.is_connected:
                logger.error("WebSocket not connected")
                return False
            
            # Send unsubscription message
            unsub_message = {
                "a": "unsubscribe",
                "v": [[mode, token] for token in tokens]
            }
            
            await self.websocket.send(json.dumps(unsub_message))
            
            # Remove from tracked subscriptions
            self.subscribed_tokens.difference_update(tokens)
            
            with self._stats_lock:
                self.stats.messages_sent += 1
                self.stats.bytes_sent += len(json.dumps(unsub_message))
            
            logger.info(f"📡 Unsubscribed from {len(tokens)} tokens")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to unsubscribe: {e}")
            with self._stats_lock:
                self.stats.errors += 1
            return False
    
    async def start_streaming(self):
        """Start WebSocket message streaming."""
        self.is_running = True
        logger.info("🔄 Starting WebSocket message streaming...")
        
        try:
            while self.is_running and self.is_connected:
                try:
                    # Receive message with timeout
                    message = await asyncio.wait_for(self.websocket.recv(), timeout=30)
                    
                    # Update statistics
                    with self._stats_lock:
                        self.stats.messages_received += 1
                        self.stats.bytes_received += len(message)
                        self.stats.last_message_time = datetime.now(UTC)
                    
                    # Process message
                    await self._process_message(message)
                    
                except asyncio.TimeoutError:
                    logger.warning("WebSocket receive timeout")
                    continue
                    
                except websockets.exceptions.ConnectionClosed:
                    logger.warning("WebSocket connection closed")
                    self.is_connected = False
                    break
                    
        except Exception as e:
            logger.error(f"❌ Error in WebSocket streaming: {e}")
            with self._stats_lock:
                self.stats.errors += 1
        
        # Attempt reconnection if needed
        if self.is_running and not self.is_connected:
            await self._attempt_reconnection()
    
    async def _process_message(self, message: str):
        """
        Process incoming WebSocket message.
        
        Args:
            message: Raw WebSocket message
        """
        try:
            # Parse JSON message
            data = json.loads(message)
            
            # Determine message type
            message_type = data.get('t', 'unknown')
            
            # Handle message based on type
            if message_type in self.message_handlers:
                await self.message_handlers[message_type](data)
            else:
                logger.debug(f"Unhandled message type: {message_type}")
                
        except json.JSONDecodeError:
            logger.error(f"Failed to parse WebSocket message: {message}")
            with self._stats_lock:
                self.stats.errors += 1
        except Exception as e:
            logger.error(f"Error processing WebSocket message: {e}")
            with self._stats_lock:
                self.stats.errors += 1
    
    async def _handle_tick_data(self, data: dict):
        """Handle tick data message."""
        try:
            # Extract tick data
            symbol = data.get('tk', '')
            ltp = data.get('lp', 0.0)
            volume = data.get('v', 0)
            
            # Create live market data message
            live_data = {
                "message_id": str(uuid.uuid4()),
                "timestamp": int(time.time() * 1_000_000_000),  # nanoseconds
                "source": "angel_one_websocket",
                "data_type": "TICK",
                "symbol": symbol,
                "exchange": data.get('e', 'NSE'),
                "token": data.get('tk', ''),
                "ltp": float(ltp) if ltp else None,
                "volume": int(volume) if volume else None,
                "change": data.get('c', 0.0),
                "change_percent": data.get('cp', 0.0),
                "metadata": data,
                "sequence_number": self.stats.messages_received
            }
            
            # Publish to Kafka
            if KAFKA_AVAILABLE and self.market_data_producer:
                success = self.market_data_producer.send_live_market_data(live_data)
                if success:
                    logger.debug(f"📤 Tick data published to Kafka: {symbol}")
                else:
                    logger.warning(f"Failed to publish tick data for {symbol}")
            
        except Exception as e:
            logger.error(f"Error handling tick data: {e}")
            with self._stats_lock:
                self.stats.errors += 1
    
    async def _handle_snapfull_data(self, data: dict):
        """Handle snapfull data message."""
        try:
            # Extract snapfull data
            symbol = data.get('tk', '')
            
            # Create live market data message
            live_data = {
                "message_id": str(uuid.uuid4()),
                "timestamp": int(time.time() * 1_000_000_000),
                "source": "angel_one_websocket",
                "data_type": "QUOTE",
                "symbol": symbol,
                "exchange": data.get('e', 'NSE'),
                "token": data.get('tk', ''),
                "ltp": data.get('lp'),
                "open": data.get('o'),
                "high": data.get('h'),
                "low": data.get('l'),
                "close": data.get('c'),
                "volume": data.get('v'),
                "bid_price": data.get('bp1'),
                "ask_price": data.get('sp1'),
                "bid_quantity": data.get('bq1'),
                "ask_quantity": data.get('sq1'),
                "metadata": data,
                "sequence_number": self.stats.messages_received
            }
            
            # Publish to Kafka
            if KAFKA_AVAILABLE and self.market_data_producer:
                success = self.market_data_producer.send_live_market_data(live_data)
                if success:
                    logger.debug(f"📤 Quote data published to Kafka: {symbol}")
            
        except Exception as e:
            logger.error(f"Error handling snapfull data: {e}")
            with self._stats_lock:
                self.stats.errors += 1
    
    async def _handle_depth_data(self, data: dict):
        """Handle market depth data message."""
        try:
            # Extract depth data
            symbol = data.get('tk', '')
            
            # Create live market data message
            live_data = {
                "message_id": str(uuid.uuid4()),
                "timestamp": int(time.time() * 1_000_000_000),
                "source": "angel_one_websocket",
                "data_type": "ORDERBOOK",
                "symbol": symbol,
                "exchange": data.get('e', 'NSE'),
                "token": data.get('tk', ''),
                "ltp": data.get('lp'),
                "total_buy_quantity": data.get('tbq'),
                "total_sell_quantity": data.get('tsq'),
                "metadata": data,
                "sequence_number": self.stats.messages_received
            }
            
            # Publish to Kafka
            if KAFKA_AVAILABLE and self.market_data_producer:
                success = self.market_data_producer.send_live_market_data(live_data)
                if success:
                    logger.debug(f"📤 Depth data published to Kafka: {symbol}")
            
        except Exception as e:
            logger.error(f"Error handling depth data: {e}")
            with self._stats_lock:
                self.stats.errors += 1
    
    async def _handle_oi_data(self, data: dict):
        """Handle open interest data message."""
        logger.debug(f"Received OI data: {data}")
    
    async def _handle_error_message(self, data: dict):
        """Handle error message."""
        logger.error(f"WebSocket error message: {data}")
        with self._stats_lock:
            self.stats.errors += 1
    
    async def _attempt_reconnection(self):
        """Attempt to reconnect WebSocket."""
        if self.reconnect_attempts >= self.max_reconnect_attempts:
            logger.error("Max reconnection attempts reached")
            return
        
        self.reconnect_attempts += 1
        logger.info(f"Attempting reconnection {self.reconnect_attempts}/{self.max_reconnect_attempts}")
        
        await asyncio.sleep(self.reconnect_delay)
        
        if await self.connect():
            self.reconnect_attempts = 0
            with self._stats_lock:
                self.stats.reconnections += 1
            
            # Resubscribe to previous tokens
            if self.subscribed_tokens:
                await self.subscribe(list(self.subscribed_tokens))
            
            # Restart streaming
            await self.start_streaming()
    
    def get_stats(self) -> dict:
        """Get WebSocket statistics."""
        with self._stats_lock:
            return {
                "connected": self.stats.connected,
                "messages_received": self.stats.messages_received,
                "messages_sent": self.stats.messages_sent,
                "bytes_received": self.stats.bytes_received,
                "bytes_sent": self.stats.bytes_sent,
                "errors": self.stats.errors,
                "subscribed_tokens": len(self.subscribed_tokens),
                "reconnections": self.stats.reconnections,
                "last_message_time": self.stats.last_message_time.isoformat() if self.stats.last_message_time else None,
                "connection_time": self.stats.connection_time.isoformat() if self.stats.connection_time else None,
                "kafka_available": KAFKA_AVAILABLE
            }
    
    def register_message_handler(self, message_type: str, handler: Callable):
        """Register custom message handler."""
        self.message_handlers[message_type] = handler
        logger.info(f"Registered message handler for type: {message_type}")
    
    async def health_check(self) -> dict:
        """Perform health check."""
        return {
            "websocket_connected": self.is_connected,
            "streaming": self.is_running,
            "kafka_available": KAFKA_AVAILABLE,
            "subscriptions": len(self.subscribed_tokens),
            "stats": self.get_stats()
        }


# Factory functions for integration
def get_websocket_manager(auth_manager: AuthManager = None) -> AngelOneWebSocketManager:
    """Get WebSocket manager instance."""
    return AngelOneWebSocketManager(auth_manager)

async def close_websocket_manager(manager: AngelOneWebSocketManager):
    """Close WebSocket manager."""
    if manager:
        await manager.disconnect()


