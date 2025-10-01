"""
Market Data Streaming Service
============================

FastAPI service for real-time market data streaming.
Integrates with Angel One API and Kafka messaging system.
"""

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Depends
from fastapi.responses import JSONResponse
from typing import Dict, Any, List, Optional
import uvicorn
import os
import asyncio
import json
from datetime import datetime, UTC

# Add project root to path for imports
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("market_data_streaming_main")

# Import Kafka infrastructure components
from messaging_enhanced.kafka import MarketDataProducer, MarketDataConsumer
from messaging_enhanced.kafka.producers.market_data_producer import get_market_data_producer
from messaging_enhanced.kafka.consumers.market_data_consumer import get_market_data_consumer
from market_data_streaming.websocket_market_manager import get_websocket_market_manager
from market_data_streaming.data_normalizer import DataNormalizer

# Initialize FastAPI app
app = FastAPI(
    title="HFT Market Data Streaming Service",
    description="Real-time market data streaming with Angel One integration",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Global instances
market_producer: Optional[MarketDataProducer] = None
market_consumer: Optional[MarketDataConsumer] = None
websocket_manager = None
data_normalizer: Optional[DataNormalizer] = None

async def process_live_market_data(symbol: str, live_data: dict):
    """
    Process live market data from Kafka.
    
    Args:
        symbol: Trading symbol
        live_data: Live market data from Angel One WebSocket
    """
    try:
        # Normalize the data
        normalized_data = data_normalizer.normalize_live_data(live_data)
        
        # Broadcast to WebSocket clients
        if websocket_manager:
            await websocket_manager.broadcast_market_data(symbol, normalized_data)
        
        logger.debug(f"📊 Processed live market data: {symbol}")
        
    except Exception as e:
        logger.error(f"❌ Error processing live market data for {symbol}: {e}")

@app.on_event("startup")
async def startup_event():
    """Initialize services on startup."""
    global market_producer, market_consumer, websocket_manager, data_normalizer
    
    try:
        logger.info("🚀 Starting Market Data Streaming Service...")
        
        # Initialize Kafka market data producer
        market_producer = get_market_data_producer("market_data_streaming_service")
        logger.info("✅ Market Data Producer initialized")
        
        # Initialize Kafka market data consumer
        market_consumer = get_market_data_consumer("market_data_streaming_consumer", "market_data_streaming_group")
        
        # Register live data callback
        market_consumer.register_live_data_callback("live_data_processor", process_live_market_data)
        logger.info("✅ Market Data Consumer initialized")
        
        # Initialize data normalizer
        data_normalizer = DataNormalizer()
        logger.info("✅ Data Normalizer initialized")
        
        # Initialize WebSocket manager
        websocket_manager = get_websocket_market_manager()
        logger.info("✅ WebSocket Manager initialized")
        
        logger.info("🎉 Market Data Streaming Service started successfully!")
        
    except Exception as e:
        logger.error(f"❌ Failed to start Market Data Streaming Service: {e}")
        raise

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown."""
    global market_producer, market_consumer, websocket_manager
    
    try:
        logger.info("🛑 Shutting down Market Data Streaming Service...")
        
        if market_producer:
            market_producer.close()
            logger.info("✅ Market Data Producer closed")
        
        if market_consumer:
            market_consumer.close()
            logger.info("✅ Market Data Consumer closed")
        
        if websocket_manager:
            websocket_manager.close()
            logger.info("✅ WebSocket Manager closed")
        
        logger.info("✅ Market Data Streaming Service shut down successfully")
        
    except Exception as e:
        logger.error(f"❌ Error during shutdown: {e}")

# Health Check Endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint."""
    try:
        producer_stats = market_producer.get_stats() if market_producer else {}
        consumer_stats = market_consumer.get_stats() if market_consumer else {}
        websocket_stats = websocket_manager.get_websocket_stats() if websocket_manager else {}
        
        return {
            "status": "healthy",
            "service": "Market Data Streaming Service",
            "timestamp": datetime.now(UTC).isoformat(),
            "kafka_producer": producer_stats,
            "kafka_consumer": consumer_stats,
            "websockets": websocket_stats
        }
    except Exception as e:
        logger.error(f"❌ Health check failed: {e}")
        raise HTTPException(status_code=500, detail=f"Health check failed: {str(e)}")

# Streaming Management Endpoints
@app.post("/streaming/subscribe")
async def subscribe_symbol(symbol: str, exchange: str = "NSE"):
    """Subscribe to real-time data for a symbol."""
    try:
        if not market_consumer:
            raise HTTPException(status_code=503, detail="Market consumer not initialized")
        
        # Register a callback for this symbol in the consumer
        def symbol_callback(tick_data):
            logger.info(f"Received tick for {symbol}: {tick_data}")
            # Here you could process the tick data, send to WebSocket, etc.
        
        market_consumer.register_callback(f"{exchange}:{symbol}", symbol_callback)
            
        return {
            "success": True,
            "message": f"Subscribed to {exchange}:{symbol}",
            "symbol": f"{exchange}:{symbol}"
        }
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error subscribing to {symbol}: {e}")
        raise HTTPException(status_code=500, detail=f"Subscription failed: {str(e)}")

@app.post("/streaming/unsubscribe")
async def unsubscribe_symbol(symbol: str, exchange: str = "NSE"):
    """Unsubscribe from real-time data for a symbol."""
    try:
        if not market_consumer:
            raise HTTPException(status_code=503, detail="Market consumer not initialized")
        
        # Unregister the callback for this symbol
        market_consumer.unregister_callback(f"{exchange}:{symbol}")
        
        return {
            "success": True,
            "message": f"Unsubscribed from {exchange}:{symbol}",
            "symbol": f"{exchange}:{symbol}"
        }
        
    except Exception as e:
        logger.error(f"❌ Error unsubscribing from {symbol}: {e}")
        raise HTTPException(status_code=500, detail=f"Unsubscription failed: {str(e)}")

@app.get("/streaming/subscriptions")
async def get_subscriptions():
    """Get list of currently subscribed symbols."""
    try:
        if not market_consumer:
            raise HTTPException(status_code=503, detail="Market consumer not initialized")
        
        subscriptions = market_consumer.get_subscribed_symbols()
        
        return {
            "subscriptions": subscriptions,
            "count": len(subscriptions),
            "timestamp": datetime.now(UTC).isoformat()
        }
        
    except Exception as e:
        logger.error(f"❌ Error getting subscriptions: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get subscriptions: {str(e)}")

@app.post("/streaming/start")
async def start_streaming():
    """Start real-time streaming."""
    try:
        if not market_consumer:
            raise HTTPException(status_code=503, detail="Market consumer not initialized")
        
        success = market_consumer.start_streaming()
        
        return {
            "success": success,
            "message": "Streaming started" if success else "Failed to start streaming",
            "timestamp": datetime.now(UTC).isoformat()
        }
        
    except Exception as e:
        logger.error(f"❌ Error starting streaming: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to start streaming: {str(e)}")

@app.post("/streaming/stop")
async def stop_streaming():
    """Stop real-time streaming."""
    try:
        if not market_consumer:
            raise HTTPException(status_code=503, detail="Market consumer not initialized")
        
        # Stop consuming messages
        market_consumer.stop_consuming()
        
        return {
            "success": True,
            "message": "Real-time streaming stopped"
        }
        
    except Exception as e:
        logger.error(f"❌ Error stopping streaming: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to stop streaming: {str(e)}")

@app.get("/streaming/stats")
async def get_streaming_stats():
    """Get streaming statistics."""
    try:
        if not market_consumer:
            raise HTTPException(status_code=503, detail="Market consumer not initialized")
        
        stats = market_consumer.get_streaming_stats()
        
        return {
            "stats": stats,
            "timestamp": datetime.now(UTC).isoformat()
        }
        
    except Exception as e:
        logger.error(f"❌ Error getting streaming stats: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get stats: {str(e)}")

# WebSocket Endpoints
@app.websocket("/ws/market-data")
async def websocket_market_data(websocket: WebSocket):
    """
    WebSocket endpoint for real-time market data streaming.
    
    Client can send JSON messages with actions:
    - {"action": "subscribe", "symbols": ["NIFTY", "RELIANCE"], "exchange": "NSE"}
    - {"action": "unsubscribe", "symbols": ["NIFTY"], "exchange": "NSE"}
    - {"action": "get_subscriptions"}
    - {"action": "get_streaming_stats"}
    """
    if not websocket_manager:
        await websocket.close(code=1011, reason="WebSocket manager not initialized")
        return
    
    client_connected = False
    
    try:
        # Connect the client
        success = await websocket_manager.connect(websocket)
        if not success:
            await websocket.close(code=1011, reason="Failed to establish connection")
            return
        
        client_connected = True
        logger.info("🌐 WebSocket client connected to market data stream")
        
        # Handle client messages
        while True:
            try:
                # Receive message from client
                message = await websocket.receive_text()
                
                # Handle the message
                await websocket_manager.handle_client_message(websocket, message)
                
            except WebSocketDisconnect:
                logger.info("🌐 WebSocket client disconnected")
                break
            except Exception as e:
                logger.error(f"❌ Error handling WebSocket message: {e}")
                # Send error to client
                try:
                    error_msg = {
                        "type": "error",
                        "error": f"Message handling error: {str(e)}",
                        "timestamp": datetime.now(UTC).isoformat()
                    }
                    await websocket.send_text(json.dumps(error_msg))
                except:
                    break  # Connection is likely broken
    
    except WebSocketDisconnect:
        logger.info("🌐 WebSocket client disconnected during setup")
    except Exception as e:
        logger.error(f"❌ WebSocket connection error: {e}")
    finally:
        if client_connected and websocket_manager:
            websocket_manager.disconnect(websocket)

@app.get("/ws/stats")
async def get_websocket_stats():
    """Get WebSocket connection statistics."""
    try:
        if not websocket_manager:
            raise HTTPException(status_code=503, detail="WebSocket manager not initialized")
        
        stats = websocket_manager.get_websocket_stats()
        
        return {
            "websocket_stats": stats,
            "timestamp": datetime.now(UTC).isoformat()
        }
        
    except Exception as e:
        logger.error(f"❌ Error getting WebSocket stats: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get WebSocket stats: {str(e)}")

# Testing Endpoints
@app.post("/test/stream-sample")
async def test_stream_sample():
    """Test endpoint to stream sample data."""
    try:
        if not market_consumer:
            raise HTTPException(status_code=503, detail="Market consumer not initialized")
        
        # Subscribe to some sample symbols
        symbols = ["NIFTY", "RELIANCE", "TCS"]
        subscribed = []
        
        for symbol in symbols:
            success = market_consumer.subscribe_symbol(symbol, "NSE")
            if success:
                subscribed.append(f"NSE:{symbol}")
        
        # Start streaming
        streaming_started = False
        if subscribed:
            streaming_started = market_consumer.start_streaming()
        
        return {
            "success": True,
            "message": "Sample streaming test initiated",
            "subscribed_symbols": subscribed,
            "streaming_started": streaming_started,
            "timestamp": datetime.now(UTC).isoformat()
        }
        
    except Exception as e:
        logger.error(f"❌ Error in sample streaming test: {e}")
        raise HTTPException(status_code=500, detail=f"Test failed: {str(e)}")

if __name__ == "__main__":
    # Configuration
    host = os.getenv("MARKET_DATA_HOST", "0.0.0.0")
    port = int(os.getenv("MARKET_DATA_PORT", "8005"))
    
    logger.info(f"🚀 Starting Market Data Streaming Service on {host}:{port}")
    
    uvicorn.run(
        app,
        host=host,
        port=port,
        log_level="info",
        access_log=True
    )
