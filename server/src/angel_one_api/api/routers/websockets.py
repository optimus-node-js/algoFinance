"""
WebSocket API Endpoints
=======================

Real-time WebSocket endpoints for streaming data.
"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from typing import List
import json
import asyncio

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent.parent))
from logger import get_infrastructure_logger

router = APIRouter()
logger = get_infrastructure_logger("websocket_router")

class ConnectionManager:
    """Manage WebSocket connections."""
    
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.subscriptions: dict = {}
    
    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info("WebSocket connected", {"total_connections": len(self.active_connections)})
    
    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        logger.info("WebSocket disconnected", {"total_connections": len(self.active_connections)})
    
    async def send_personal_message(self, message: str, websocket: WebSocket):
        await websocket.send_text(message)
    
    async def broadcast(self, message: str):
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except:
                # Remove dead connections
                self.active_connections.remove(connection)

manager = ConnectionManager()

@router.websocket("/market/ltp")
async def websocket_market_ltp(websocket: WebSocket):
    """🌐 Real-time LTP data stream"""
    await manager.connect(websocket)
    try:
        while True:
            # Receive subscription requests
            data = await websocket.receive_text()
            message = json.loads(data)
            
            if message.get("action") == "subscribe":
                symbols = message.get("symbols", [])
                logger.info("LTP subscription request", {"symbols": symbols})
                
                # Start streaming mock data
                for symbol in symbols:
                    mock_data = {
                        "type": "ltp_update",
                        "symbol": symbol,
                        "ltp": 2500.50,
                        "change": 25.50,
                        "change_percent": 1.03,
                        "timestamp": "2025-09-20T18:45:00Z"
                    }
                    await manager.send_personal_message(json.dumps(mock_data), websocket)
            
            elif message.get("action") == "unsubscribe":
                symbols = message.get("symbols", [])
                logger.info("LTP unsubscription request", {"symbols": symbols})
                
            await asyncio.sleep(1)  # Send updates every second
            
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        logger.info("LTP WebSocket client disconnected")

@router.websocket("/trading/orders")
async def websocket_trading_orders(websocket: WebSocket):
    """🌐 Real-time order updates stream"""
    await manager.connect(websocket)
    try:
        while True:
            # Mock order update
            order_update = {
                "type": "order_update",
                "order_id": "240920001234567",
                "status": "COMPLETE",
                "filled_quantity": 100,
                "average_price": 2485.50,
                "timestamp": "2025-09-20T18:45:00Z"
            }
            
            await manager.send_personal_message(json.dumps(order_update), websocket)
            await asyncio.sleep(5)  # Send updates every 5 seconds
            
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        logger.info("Trading WebSocket client disconnected")

@router.websocket("/portfolio/updates")
async def websocket_portfolio_updates(websocket: WebSocket):
    """🌐 Real-time portfolio updates stream"""
    await manager.connect(websocket)
    try:
        while True:
            # Mock portfolio update
            portfolio_update = {
                "type": "portfolio_update",
                "total_pnl": 15500.75,
                "day_change": 750.25,
                "day_change_percent": 5.08,
                "positions_count": 12,
                "timestamp": "2025-09-20T18:45:00Z"
            }
            
            await manager.send_personal_message(json.dumps(portfolio_update), websocket)
            await asyncio.sleep(10)  # Send updates every 10 seconds
            
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        logger.info("Portfolio WebSocket client disconnected")

@router.websocket("/admin/monitoring")
async def websocket_admin_monitoring(websocket: WebSocket):
    """🌐 Real-time system monitoring stream"""
    await manager.connect(websocket)
    try:
        while True:
            # Mock system metrics
            system_metrics = {
                "type": "system_metrics",
                "cpu_percent": 25.5,
                "memory_percent": 45.2,
                "active_connections": len(manager.active_connections),
                "requests_per_minute": 150,
                "timestamp": "2025-09-20T18:45:00Z"
            }
            
            await manager.send_personal_message(json.dumps(system_metrics), websocket)
            await asyncio.sleep(2)  # Send updates every 2 seconds
            
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        logger.info("Admin monitoring WebSocket client disconnected")
