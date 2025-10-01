"""
WebSocket Market Manager
=======================

Enhanced WebSocket manager for real-time market data streaming.
Integrates with the MarketDataStreamer for unified data flow.
"""

from fastapi import WebSocket, WebSocketDisconnect
from typing import Dict, List, Set, Any, Optional
import json
import asyncio
from datetime import datetime, UTC
import threading

# Add project root to path for imports
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

import logging
logger = logging.getLogger("websocket_market_manager")
from .market_data_streamer import get_market_data_streamer


class WebSocketMarketManager:
    """
    Enhanced WebSocket manager that integrates with the real-time market data streamer.
    Provides seamless real-time updates to connected clients.
    """
    
    def __init__(self):
        """Initialize the WebSocket market manager."""
        self.active_connections: List[WebSocket] = []
        self.client_subscriptions: Dict[WebSocket, Set[str]] = {}
        self.symbol_subscribers: Dict[str, Set[WebSocket]] = {}
        self._lock = threading.Lock()
        
        # Get the market data streamer instance
        self.market_streamer = get_market_data_streamer()
        
        # Statistics
        self.connections_count = 0
        self.messages_sent = 0
        self.connection_errors = 0
        
        logger.info("WebSocketMarketManager initialized with MarketDataStreamer integration")
    
    async def connect(self, websocket: WebSocket, client_id: Optional[str] = None) -> bool:
        """
        Connect a new WebSocket client.
        
        Args:
            websocket: WebSocket connection
            client_id: Optional client identifier
            
        Returns:
            True if connection successful
        """
        try:
            await websocket.accept()
            
            with self._lock:
                self.active_connections.append(websocket)
                self.client_subscriptions[websocket] = set()
                self.connections_count += 1
            
            # Register with market data streamer for real-time updates
            self.market_streamer.add_websocket_connection(websocket)
            
            logger.info(f"🌐 WebSocket client connected (total: {len(self.active_connections)})")
            
            # Send welcome message
            welcome_msg = {
                "type": "connection_established",
                "message": "Connected to real-time market data stream",
                "client_id": client_id,
                "timestamp": datetime.now(UTC).isoformat(),
                "available_commands": [
                    "subscribe",
                    "unsubscribe", 
                    "get_subscriptions",
                    "get_streaming_stats"
                ]
            }
            await websocket.send_text(json.dumps(welcome_msg))
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to connect WebSocket client: {e}")
            with self._lock:
                self.connection_errors += 1
            return False
    
    def disconnect(self, websocket: WebSocket):
        """
        Disconnect a WebSocket client.
        
        Args:
            websocket: WebSocket connection to disconnect
        """
        try:
            with self._lock:
                # Remove from active connections
                if websocket in self.active_connections:
                    self.active_connections.remove(websocket)
                
                # Get client's subscriptions before removing
                client_subscriptions = self.client_subscriptions.get(websocket, set())
                
                # Remove client from symbol subscribers
                for symbol in client_subscriptions:
                    if symbol in self.symbol_subscribers:
                        self.symbol_subscribers[symbol].discard(websocket)
                        
                        # If no more subscribers for this symbol, unsubscribe from streamer
                        if not self.symbol_subscribers[symbol]:
                            del self.symbol_subscribers[symbol]
                            # Unsubscribe from market data streamer
                            exchange, symbol_name = symbol.split(":", 1) if ":" in symbol else ("NSE", symbol)
                            self.market_streamer.unsubscribe_symbol(symbol_name, exchange)
                
                # Remove client subscriptions
                if websocket in self.client_subscriptions:
                    del self.client_subscriptions[websocket]
            
            # Remove from market data streamer
            self.market_streamer.remove_websocket_connection(websocket)
            
            logger.info(f"🌐 WebSocket client disconnected (remaining: {len(self.active_connections)})")
            
        except Exception as e:
            logger.error(f"❌ Error during WebSocket disconnect: {e}")
    
    async def handle_client_message(self, websocket: WebSocket, message: str):
        """
        Handle incoming message from WebSocket client.
        
        Args:
            websocket: WebSocket connection
            message: JSON message from client
        """
        try:
            data = json.loads(message)
            action = data.get("action")
            
            if action == "subscribe":
                await self._handle_subscribe(websocket, data)
            elif action == "unsubscribe":
                await self._handle_unsubscribe(websocket, data)
            elif action == "get_subscriptions":
                await self._handle_get_subscriptions(websocket)
            elif action == "get_streaming_stats":
                await self._handle_get_streaming_stats(websocket)
            else:
                await self._send_error(websocket, f"Unknown action: {action}")
                
        except json.JSONDecodeError:
            await self._send_error(websocket, "Invalid JSON message")
        except Exception as e:
            logger.error(f"❌ Error handling client message: {e}")
            await self._send_error(websocket, f"Error processing message: {str(e)}")
    
    async def _handle_subscribe(self, websocket: WebSocket, data: Dict[str, Any]):
        """Handle symbol subscription request."""
        try:
            symbols = data.get("symbols", [])
            exchange = data.get("exchange", "NSE")
            
            if not symbols:
                await self._send_error(websocket, "No symbols provided for subscription")
                return
            
            subscribed_symbols = []
            
            for symbol in symbols:
                symbol_key = f"{exchange}:{symbol}"
                
                with self._lock:
                    # Add to client subscriptions
                    self.client_subscriptions[websocket].add(symbol_key)
                    
                    # Add to symbol subscribers
                    if symbol_key not in self.symbol_subscribers:
                        self.symbol_subscribers[symbol_key] = set()
                    self.symbol_subscribers[symbol_key].add(websocket)
                
                # Subscribe to market data streamer
                success = self.market_streamer.subscribe_symbol(symbol, exchange)
                if success:
                    subscribed_symbols.append(symbol_key)
                    logger.info(f"📊 Client subscribed to {symbol_key}")
                else:
                    logger.error(f"❌ Failed to subscribe client to {symbol_key}")
            
            # Start streaming if not already started
            if subscribed_symbols and not self.market_streamer.is_streaming:
                self.market_streamer.start_streaming()
            
            # Send confirmation
            response = {
                "type": "subscription_response",
                "action": "subscribe",
                "symbols": subscribed_symbols,
                "exchange": exchange,
                "success": True,
                "message": f"Subscribed to {len(subscribed_symbols)} symbols",
                "timestamp": datetime.now(UTC).isoformat()
            }
            await websocket.send_text(json.dumps(response))
            
        except Exception as e:
            logger.error(f"❌ Error handling subscribe: {e}")
            await self._send_error(websocket, f"Subscription failed: {str(e)}")
    
    async def _handle_unsubscribe(self, websocket: WebSocket, data: Dict[str, Any]):
        """Handle symbol unsubscription request."""
        try:
            symbols = data.get("symbols", [])
            exchange = data.get("exchange", "NSE")
            
            if not symbols:
                await self._send_error(websocket, "No symbols provided for unsubscription")
                return
            
            unsubscribed_symbols = []
            
            for symbol in symbols:
                symbol_key = f"{exchange}:{symbol}"
                
                with self._lock:
                    # Remove from client subscriptions
                    self.client_subscriptions[websocket].discard(symbol_key)
                    
                    # Remove from symbol subscribers
                    if symbol_key in self.symbol_subscribers:
                        self.symbol_subscribers[symbol_key].discard(websocket)
                        
                        # If no more subscribers, unsubscribe from streamer
                        if not self.symbol_subscribers[symbol_key]:
                            del self.symbol_subscribers[symbol_key]
                            self.market_streamer.unsubscribe_symbol(symbol, exchange)
                
                unsubscribed_symbols.append(symbol_key)
                logger.info(f"📊 Client unsubscribed from {symbol_key}")
            
            # Send confirmation
            response = {
                "type": "subscription_response",
                "action": "unsubscribe",
                "symbols": unsubscribed_symbols,
                "exchange": exchange,
                "success": True,
                "message": f"Unsubscribed from {len(unsubscribed_symbols)} symbols",
                "timestamp": datetime.now(UTC).isoformat()
            }
            await websocket.send_text(json.dumps(response))
            
        except Exception as e:
            logger.error(f"❌ Error handling unsubscribe: {e}")
            await self._send_error(websocket, f"Unsubscription failed: {str(e)}")
    
    async def _handle_get_subscriptions(self, websocket: WebSocket):
        """Handle get subscriptions request."""
        try:
            with self._lock:
                client_subs = list(self.client_subscriptions.get(websocket, set()))
            
            response = {
                "type": "subscriptions_list",
                "subscriptions": client_subs,
                "count": len(client_subs),
                "timestamp": datetime.now(UTC).isoformat()
            }
            await websocket.send_text(json.dumps(response))
            
        except Exception as e:
            logger.error(f"❌ Error getting subscriptions: {e}")
            await self._send_error(websocket, f"Failed to get subscriptions: {str(e)}")
    
    async def _handle_get_streaming_stats(self, websocket: WebSocket):
        """Handle get streaming stats request."""
        try:
            stats = self.market_streamer.get_streaming_stats()
            websocket_stats = self.get_websocket_stats()
            
            response = {
                "type": "streaming_stats",
                "market_streamer": stats,
                "websocket_manager": websocket_stats,
                "timestamp": datetime.now(UTC).isoformat()
            }
            await websocket.send_text(json.dumps(response))
            
        except Exception as e:
            logger.error(f"❌ Error getting streaming stats: {e}")
            await self._send_error(websocket, f"Failed to get stats: {str(e)}")
    
    async def _send_error(self, websocket: WebSocket, error_message: str):
        """Send error message to WebSocket client."""
        try:
            error_response = {
                "type": "error",
                "error": error_message,
                "timestamp": datetime.now(UTC).isoformat()
            }
            await websocket.send_text(json.dumps(error_response))
        except Exception as e:
            logger.error(f"❌ Failed to send error message: {e}")
    
    async def send_personal_message(self, message: str, websocket: WebSocket):
        """
        Send a personal message to a specific WebSocket client.
        
        Args:
            message: Message to send
            websocket: Target WebSocket connection
        """
        try:
            await websocket.send_text(message)
            with self._lock:
                self.messages_sent += 1
        except Exception as e:
            logger.error(f"❌ Failed to send personal message: {e}")
            # Remove dead connection
            self.disconnect(websocket)
    
    async def broadcast_to_symbol_subscribers(self, symbol_key: str, message: str):
        """
        Broadcast message to all subscribers of a specific symbol.
        
        Args:
            symbol_key: Symbol key (e.g., "NSE:NIFTY")
            message: Message to broadcast
        """
        try:
            with self._lock:
                subscribers = self.symbol_subscribers.get(symbol_key, set()).copy()
            
            if not subscribers:
                return
            
            dead_connections = []
            for websocket in subscribers:
                try:
                    await websocket.send_text(message)
                    with self._lock:
                        self.messages_sent += 1
                except Exception as e:
                    logger.error(f"❌ Failed to broadcast to subscriber: {e}")
                    dead_connections.append(websocket)
            
            # Remove dead connections
            for dead_ws in dead_connections:
                self.disconnect(dead_ws)
                
        except Exception as e:
            logger.error(f"❌ Error broadcasting to symbol subscribers: {e}")
    
    async def broadcast_to_all(self, message: str):
        """
        Broadcast message to all connected WebSocket clients.
        
        Args:
            message: Message to broadcast
        """
        try:
            with self._lock:
                connections = self.active_connections.copy()
            
            if not connections:
                return
            
            dead_connections = []
            for websocket in connections:
                try:
                    await websocket.send_text(message)
                    with self._lock:
                        self.messages_sent += 1
                except Exception as e:
                    logger.error(f"❌ Failed to broadcast to client: {e}")
                    dead_connections.append(websocket)
            
            # Remove dead connections
            for dead_ws in dead_connections:
                self.disconnect(dead_ws)
                
        except Exception as e:
            logger.error(f"❌ Error broadcasting to all clients: {e}")
    
    def get_websocket_stats(self) -> Dict[str, Any]:
        """Get WebSocket manager statistics."""
        with self._lock:
            return {
                'active_connections': len(self.active_connections),
                'total_connections': self.connections_count,
                'messages_sent': self.messages_sent,
                'connection_errors': self.connection_errors,
                'unique_symbols_subscribed': len(self.symbol_subscribers),
                'symbol_subscriptions': {
                    symbol: len(subscribers) 
                    for symbol, subscribers in self.symbol_subscribers.items()
                }
            }
    
    def close(self):
        """Close the WebSocket manager."""
        logger.info("🔒 Closing WebSocketMarketManager...")
        
        # Disconnect all clients
        with self._lock:
            connections = self.active_connections.copy()
        
        for websocket in connections:
            try:
                self.disconnect(websocket)
            except Exception as e:
                logger.error(f"❌ Error disconnecting client: {e}")
        
        # Clear all data structures
        with self._lock:
            self.active_connections.clear()
            self.client_subscriptions.clear()
            self.symbol_subscribers.clear()
        
        logger.success("✅ WebSocketMarketManager closed successfully")


# Global WebSocket market manager instance
_websocket_market_manager: Optional[WebSocketMarketManager] = None
_manager_lock = threading.Lock()

def get_websocket_market_manager() -> WebSocketMarketManager:
    """Get or create global WebSocket market manager instance."""
    global _websocket_market_manager
    
    with _manager_lock:
        if _websocket_market_manager is None:
            _websocket_market_manager = WebSocketMarketManager()
        return _websocket_market_manager

def close_websocket_market_manager():
    """Close global WebSocket market manager."""
    global _websocket_market_manager
    
    with _manager_lock:
        if _websocket_market_manager:
            _websocket_market_manager.close()
            _websocket_market_manager = None
