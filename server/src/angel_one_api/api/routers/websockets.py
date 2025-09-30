"""
WebSocket API Endpoints
=======================

Real-time WebSocket endpoints for streaming data.
"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, HTTPException
from typing import List, Dict, Set
import json
import asyncio
from datetime import datetime, UTC

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent.parent))

from logger import get_infrastructure_logger
from methods import get_ltp_data, get_order_book, get_position, get_holding
from api.dependencies import validate_angel_one_session

router = APIRouter()
logger = get_infrastructure_logger("websocket_router")

class ConnectionManager:
    """Manage WebSocket connections."""
    
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.subscriptions: Dict[str, Set[WebSocket]] = {}
        self.symbol_subscriptions: Dict[WebSocket, Set[str]] = {}
    
    async def connect(self, websocket: WebSocket):
        try:
            await websocket.accept()
            self.active_connections.append(websocket)
            logger.info("WebSocket connected", {"total_connections": len(self.active_connections)})
        except Exception as e:
            logger.error("Failed to accept WebSocket connection", error=e)
            raise HTTPException(status_code=400, detail="WebSocket connection failed")
    
    def disconnect(self, websocket: WebSocket):
        try:
            if websocket in self.active_connections:
                self.active_connections.remove(websocket)
            logger.info("WebSocket disconnected", {"total_connections": len(self.active_connections)})
        except Exception as e:
            logger.error("Error during WebSocket disconnect", error=e)
    
    async def send_personal_message(self, message: str, websocket: WebSocket):
        try:
            await websocket.send_text(message)
        except Exception as e:
            logger.error("Failed to send WebSocket message", error=e)
            # Remove dead connection
            if websocket in self.active_connections:
                self.active_connections.remove(websocket)
    
    async def broadcast(self, message: str):
        dead_connections = []
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except Exception as e:
                logger.error("Failed to broadcast to WebSocket", error=e)
                dead_connections.append(connection)
        
        # Remove dead connections
        for connection in dead_connections:
            if connection in self.active_connections:
                self.active_connections.remove(connection)

manager = ConnectionManager()

@router.websocket("/market/ltp")
async def websocket_market_ltp(websocket: WebSocket):
    """🌐 Real-time LTP data stream"""
    try:
        await manager.connect(websocket)
        subscribed_symbols = set()
    except Exception as e:
        logger.error("Failed to establish LTP WebSocket connection", error=e)
        return
    
    try:
        while True:
            # Check for new subscription requests (non-blocking)
            try:
                data = await asyncio.wait_for(websocket.receive_text(), timeout=0.1)
                message = json.loads(data)
                
                if message.get("action") == "subscribe":
                    symbols = message.get("symbols", [])
                    subscribed_symbols.update(symbols)
                    logger.info("LTP subscription request", {"symbols": symbols, "total_subscribed": len(subscribed_symbols)})
                    
                elif message.get("action") == "unsubscribe":
                    symbols = message.get("symbols", [])
                    subscribed_symbols.difference_update(symbols)
                    logger.info("LTP unsubscription request", {"symbols": symbols, "remaining": len(subscribed_symbols)})
                    
            except asyncio.TimeoutError:
                # No new messages, continue with data streaming
                pass
            
            # Stream real LTP data for subscribed symbols
            if subscribed_symbols:
                for symbol in subscribed_symbols:
                    try:
                        # Get real LTP data from Angel One
                        ltp_result = await get_ltp_data(symbol, "NSE")
                        
                        if ltp_result and "data" in ltp_result:
                            data = ltp_result["data"]
                            real_data = {
                                "type": "ltp_update",
                                "symbol": symbol,
                                "ltp": data.get("ltp", 0),
                                "open": data.get("open", 0),
                                "high": data.get("high", 0),
                                "low": data.get("low", 0),
                                "close": data.get("close", 0),
                                "change": data.get("ltp", 0) - data.get("close", 0) if data.get("ltp") and data.get("close") else 0,
                                "change_percent": ((data.get("ltp", 0) - data.get("close", 0)) / data.get("close", 1)) * 100 if data.get("close") else 0,
                                "volume": data.get("volume", 0),
                                "timestamp": datetime.now(UTC).isoformat()
                            }
                            await manager.send_personal_message(json.dumps(real_data), websocket)
                        
                    except Exception as e:
                        logger.error("Failed to get LTP data", error=e, extra={"symbol": symbol})
                        # Send error message
                        error_data = {
                            "type": "error",
                            "symbol": symbol,
                            "error": "Failed to fetch LTP data",
                            "timestamp": datetime.now(UTC).isoformat()
                        }
                        await manager.send_personal_message(json.dumps(error_data), websocket)
            
            await asyncio.sleep(1)  # Send updates every second
            
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        logger.info("LTP WebSocket client disconnected", {"subscribed_symbols": len(subscribed_symbols)})
    except Exception as e:
        logger.error("LTP WebSocket error", error=e)
        manager.disconnect(websocket)

@router.websocket("/trading/orders")
async def websocket_trading_orders(websocket: WebSocket):
    """🌐 Real-time order updates stream"""
    try:
        await manager.connect(websocket)
        last_order_count = 0
    except Exception as e:
        logger.error("Failed to establish trading WebSocket connection", error=e)
        return
    
    try:
        while True:
            try:
                # Get real order book data from Angel One
                order_result = await get_order_book()
                
                if order_result and "orders" in order_result:
                    orders = order_result["orders"]
                    current_order_count = len(orders)
                    
                    # Send updates if there are new orders or changes
                    if current_order_count != last_order_count or orders:
                        order_update = {
                            "type": "order_book_update",
                            "total_orders": current_order_count,
                            "pending_orders": len([o for o in orders if o.get("status") in ["OPEN", "PENDING"]]),
                            "completed_orders": len([o for o in orders if o.get("status") == "COMPLETE"]),
                            "recent_orders": orders[:5] if orders else [],  # Last 5 orders
                            "timestamp": datetime.now(UTC).isoformat()
                        }
                        
                        await manager.send_personal_message(json.dumps(order_update), websocket)
                        last_order_count = current_order_count
                        
                        logger.info("Order book update sent", {
                            "total_orders": current_order_count,
                            "new_orders": current_order_count - last_order_count
                        })
                
            except Exception as e:
                logger.error("Failed to get order book data", error=e)
                # Send error message
                error_data = {
                    "type": "error",
                    "error": "Failed to fetch order book data",
                    "timestamp": datetime.now(UTC).isoformat()
                }
                await manager.send_personal_message(json.dumps(error_data), websocket)
            
            await asyncio.sleep(5)  # Send updates every 5 seconds
            
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        logger.info("Trading WebSocket client disconnected")
    except Exception as e:
        logger.error("Trading WebSocket error", error=e)
        manager.disconnect(websocket)

@router.websocket("/portfolio/updates")
async def websocket_portfolio_updates(websocket: WebSocket):
    """🌐 Real-time portfolio updates stream"""
    try:
        await manager.connect(websocket)
        last_portfolio_hash = None
    except Exception as e:
        logger.error("Failed to establish portfolio WebSocket connection", error=e)
        return
    
    try:
        while True:
            try:
                # Get real portfolio data from Angel One
                positions_result = await get_position()
                holdings_result = await get_holding()
                
                # Calculate portfolio metrics
                total_pnl = 0
                total_invested = 0
                total_current = 0
                positions_count = 0
                holdings_count = 0
                
                if positions_result and "positions" in positions_result:
                    positions = positions_result["positions"]
                    positions_count = len(positions)
                    total_pnl += sum(float(p.get("pnl", 0)) for p in positions)
                
                if holdings_result and "holdings" in holdings_result:
                    holdings = holdings_result["holdings"]
                    holdings_count = len(holdings)
                    for holding in holdings:
                        invested = float(holding.get("investedValue", 0))
                        current = float(holding.get("currentValue", 0))
                        total_invested += invested
                        total_current += current
                        total_pnl += (current - invested)
                
                day_change = total_current - total_invested
                day_change_percent = (day_change / total_invested * 100) if total_invested > 0 else 0
                
                portfolio_update = {
                    "type": "portfolio_update",
                    "total_pnl": round(total_pnl, 2),
                    "day_change": round(day_change, 2),
                    "day_change_percent": round(day_change_percent, 2),
                    "positions_count": positions_count,
                    "holdings_count": holdings_count,
                    "total_invested": round(total_invested, 2),
                    "total_current": round(total_current, 2),
                    "timestamp": datetime.now(UTC).isoformat()
                }
                
                # Create a simple hash to detect changes
                current_hash = hash(str(portfolio_update))
                
                # Only send update if portfolio data changed
                if current_hash != last_portfolio_hash:
                    await manager.send_personal_message(json.dumps(portfolio_update), websocket)
                    last_portfolio_hash = current_hash
                    
                    logger.info("Portfolio update sent", {
                        "total_pnl": total_pnl,
                        "positions": positions_count,
                        "holdings": holdings_count
                    })
                
            except Exception as e:
                logger.error("Failed to get portfolio data", error=e)
                # Send error message
                error_data = {
                    "type": "error",
                    "error": "Failed to fetch portfolio data",
                    "timestamp": datetime.now(UTC).isoformat()
                }
                await manager.send_personal_message(json.dumps(error_data), websocket)
            
            await asyncio.sleep(10)  # Send updates every 10 seconds
            
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        logger.info("Portfolio WebSocket client disconnected")
    except Exception as e:
        logger.error("Portfolio WebSocket error", error=e)
        manager.disconnect(websocket)

@router.websocket("/admin/monitoring")
async def websocket_admin_monitoring(websocket: WebSocket):
    """🌐 Real-time system monitoring stream"""
    try:
        await manager.connect(websocket)
    except Exception as e:
        logger.error("Failed to establish admin WebSocket connection", error=e)
        return
    
    try:
        # Import psutil for real system monitoring
        import psutil
        import os
        
        while True:
            try:
                # Get real system metrics
                cpu_percent = psutil.cpu_percent(interval=1)
                memory = psutil.virtual_memory()
                disk = psutil.disk_usage('/')
                
                # Get process-specific metrics
                process = psutil.Process()
                
                system_metrics = {
                    "type": "system_metrics",
                    "cpu_percent": round(cpu_percent, 2),
                    "memory_percent": round(memory.percent, 2),
                    "memory_used_gb": round(memory.used / (1024**3), 2),
                    "memory_available_gb": round(memory.available / (1024**3), 2),
                    "disk_percent": round((disk.used / disk.total) * 100, 2),
                    "disk_free_gb": round(disk.free / (1024**3), 2),
                    "active_connections": len(manager.active_connections),
                    "process_memory_mb": round(process.memory_info().rss / (1024**2), 2),
                    "process_cpu_percent": round(process.cpu_percent(), 2),
                    "process_threads": process.num_threads(),
                    "process_id": os.getpid(),
                    "requests_per_minute": 0,  # Would be tracked by middleware
                    "timestamp": datetime.now(UTC).isoformat()
                }
                
                await manager.send_personal_message(json.dumps(system_metrics), websocket)
                
            except Exception as e:
                logger.error("Failed to get system metrics", error=e)
                # Send error message
                error_data = {
                    "type": "error",
                    "error": "Failed to fetch system metrics",
                    "timestamp": datetime.now(UTC).isoformat()
                }
                await manager.send_personal_message(json.dumps(error_data), websocket)
            
            await asyncio.sleep(2)  # Send updates every 2 seconds
            
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        logger.info("Admin monitoring WebSocket client disconnected")
    except Exception as e:
        logger.error("Admin WebSocket error", error=e)
        manager.disconnect(websocket)


