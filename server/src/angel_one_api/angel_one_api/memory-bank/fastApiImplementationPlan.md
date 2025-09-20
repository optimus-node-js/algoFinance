# FastAPI Implementation Plan for Angel One Microservice

## 🚀 **DETAILED IMPLEMENTATION STRATEGY**

**Target**: Transform Angel One module into production-ready FastAPI microservice  
**Timeline**: 4-6 weeks  
**Integration**: RabbitMQ + WebSocket + React Frontend  

---

## 📁 **DETAILED FILE STRUCTURE**

### **NEW FASTAPI STRUCTURE**
```
angel_one_api/
├── 🎯 api/                           # NEW: FastAPI Application Layer
│   ├── __init__.py
│   ├── main.py                       # FastAPI app + startup/shutdown
│   ├── dependencies.py               # Dependency injection
│   ├── middleware.py                 # Custom middleware  
│   ├── exceptions.py                 # Global exception handlers
│   └── routers/                      # API Route Handlers
│       ├── __init__.py
│       ├── authentication.py         # Auth: /auth/*
│       ├── trading.py                # Trading: /trading/*
│       ├── market_data.py            # Market: /market/*
│       ├── portfolio.py              # Portfolio: /portfolio/*
│       ├── risk.py                   # Risk: /risk/*
│       ├── advanced.py               # Advanced: /advanced/*
│       ├── admin.py                  # Admin: /admin/*
│       └── websockets.py             # WebSocket: /ws/*
├── 🐰 messaging/                     # NEW: RabbitMQ Integration
│   ├── __init__.py
│   ├── connection.py                 # RabbitMQ connection management
│   ├── publisher.py                  # Message publishing
│   ├── consumer.py                   # Message consumption
│   ├── handlers/                     # Message handlers
│   │   ├── __init__.py
│   │   ├── ai_requests.py            # Handle AI engine requests
│   │   ├── market_events.py          # Market data events
│   │   ├── trading_events.py         # Trading events
│   │   └── system_events.py          # System notifications
│   └── schemas/                      # Message schemas
│       ├── __init__.py
│       ├── requests.py               # Request message schemas
│       ├── responses.py              # Response message schemas
│       └── events.py                 # Event message schemas
├── 📊 models/                        # NEW: Pydantic Models
│   ├── __init__.py
│   ├── auth.py                       # Authentication models
│   ├── trading.py                    # Trading request/response models
│   ├── market.py                     # Market data models
│   ├── portfolio.py                  # Portfolio models
│   ├── risk.py                       # Risk management models
│   ├── admin.py                      # Admin models
│   └── base.py                       # Base model classes
├── 🔧 config/                        # NEW: Configuration Management
│   ├── __init__.py
│   ├── settings.py                   # Application settings
│   ├── rabbitmq.py                   # RabbitMQ configuration
│   ├── database.py                   # Database configuration
│   └── security.py                   # Security configuration
├── 🌐 websockets/                    # NEW: WebSocket Handlers
│   ├── __init__.py
│   ├── connection_manager.py         # WebSocket connection management
│   ├── handlers/
│   │   ├── __init__.py
│   │   ├── market_data.py            # Real-time market data
│   │   ├── trading.py                # Real-time trading updates
│   │   ├── portfolio.py              # Real-time portfolio updates
│   │   └── admin.py                  # Real-time admin monitoring
│   └── schemas.py                    # WebSocket message schemas
├── 🔄 services/                      # ENHANCED: Business Logic Layer
│   ├── authentication/               # ✅ EXISTING (enhanced)
│   ├── market_data/                  # ✅ EXISTING (enhanced)
│   ├── portfolio/                    # ✅ EXISTING (enhanced)
│   ├── fund_management/              # ✅ EXISTING (enhanced)
│   ├── reports/                      # ✅ EXISTING (enhanced)
│   ├── alerts/                       # ✅ EXISTING (enhanced)
│   └── 🆕 orchestration/             # NEW: Service orchestration
│       ├── __init__.py
│       ├── ai_service.py             # AI engine communication
│       ├── workflow_manager.py       # Workflow coordination
│       └── event_dispatcher.py       # Event distribution
├── 📱 frontend/                      # NEW: React Testing Dashboard
│   ├── package.json
│   ├── src/
│   │   ├── components/
│   │   ├── pages/
│   │   ├── hooks/
│   │   ├── services/
│   │   └── utils/
│   └── public/
├── 🔵 methods/                       # ✅ EXISTING (28 API methods)
├── 🎛️ rate_limiter/                  # ✅ EXISTING (enhanced for microservice)
├── 📋 logger/                        # ✅ EXISTING (enhanced)
├── 🧪 tests/                         # ENHANCED: Comprehensive testing
│   ├── 🆕 api/                       # FastAPI endpoint tests
│   ├── 🆕 messaging/                 # RabbitMQ tests
│   ├── 🆕 websockets/                # WebSocket tests
│   ├── 🆕 integration/               # Integration tests
│   └── 🆕 performance/               # Performance tests
└── 📚 memory-bank/                   # ✅ EXISTING (updated)
```

---

## 🔧 **IMPLEMENTATION DETAILS**

### **1. FASTAPI MAIN APPLICATION**

#### **api/main.py**
```python
"""
Angel One FastAPI Microservice
==============================

Production-ready FastAPI application for Angel One trading operations.
Integrates with RabbitMQ for AI communication and WebSocket for real-time data.
"""

from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from contextlib import asynccontextmanager
import uvicorn

from .routers import (
    authentication, trading, market_data, 
    portfolio, risk, advanced, admin, websockets
)
from .middleware import LoggingMiddleware, RateLimitMiddleware
from .exceptions import global_exception_handler
from ..messaging.connection import init_rabbitmq, close_rabbitmq
from ..logger import get_infrastructure_logger
from ..config.settings import settings

logger = get_infrastructure_logger("fastapi_main")

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management."""
    # Startup
    logger.info("Starting Angel One FastAPI service", {
        "version": settings.VERSION,
        "environment": settings.ENVIRONMENT,
        "debug": settings.DEBUG
    })
    
    # Initialize RabbitMQ
    await init_rabbitmq()
    logger.info("RabbitMQ connection established")
    
    yield
    
    # Shutdown
    logger.info("Shutting down Angel One FastAPI service")
    await close_rabbitmq()
    logger.info("RabbitMQ connection closed")

# Create FastAPI application
app = FastAPI(
    title="Angel One Trading API",
    description="Enterprise-grade Angel One SmartAPI microservice for HFT trading",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan
)

# Add middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(GZipMiddleware, minimum_size=1000)
app.add_middleware(LoggingMiddleware)
app.add_middleware(RateLimitMiddleware)

# Add exception handlers
app.add_exception_handler(Exception, global_exception_handler)

# Include routers
app.include_router(authentication.router, prefix="/auth", tags=["authentication"])
app.include_router(trading.router, prefix="/trading", tags=["trading"])
app.include_router(market_data.router, prefix="/market", tags=["market-data"])
app.include_router(portfolio.router, prefix="/portfolio", tags=["portfolio"])
app.include_router(risk.router, prefix="/risk", tags=["risk-management"])
app.include_router(advanced.router, prefix="/advanced", tags=["advanced-features"])
app.include_router(admin.router, prefix="/admin", tags=["administration"])
app.include_router(websockets.router, prefix="/ws", tags=["websockets"])

@app.get("/")
async def root():
    """Root endpoint with service information."""
    return {
        "service": "Angel One Trading API",
        "version": "1.0.0",
        "status": "operational",
        "docs": "/docs",
        "health": "/admin/health"
    }

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "angel-one-api",
        "version": "1.0.0"
    }

if __name__ == "__main__":
    uvicorn.run(
        "api.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level=settings.LOG_LEVEL.lower()
    )
```

### **2. AUTHENTICATION ROUTER**

#### **api/routers/authentication.py**
```python
"""
Authentication API Endpoints
============================

Handles all authentication-related operations for Angel One API.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from typing import Dict, Any

from ...services.authentication import AuthManager
from ...models.auth import (
    ConfigureKeysRequest, ConfigureKeysResponse,
    LoginRequest, LoginResponse,
    AuthStatusResponse
)
from ...logger import get_api_logger

router = APIRouter()
logger = get_api_logger("auth_router")

@router.post("/configure", response_model=ConfigureKeysResponse)
async def configure_api_keys(
    request: ConfigureKeysRequest,
    auth_manager: AuthManager = Depends(get_auth_manager)
):
    """Configure Angel One API keys for the service."""
    try:
        logger.info("API keys configuration requested", {
            "total_keys": len(request.api_keys),
            "action": "configure_request"
        })
        
        # Configure API keys
        auth_manager.configure_api_keys(request.api_keys)
        
        logger.success("API keys configured successfully", {
            "total_keys": len(request.api_keys)
        })
        
        return ConfigureKeysResponse(
            success=True,
            message=f"Configured {len(request.api_keys)} API keys",
            total_keys=len(request.api_keys)
        )
        
    except Exception as e:
        logger.error("API keys configuration failed", 
                    error=e, 
                    error_code="AUTH001")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Configuration failed: {str(e)}"
        )

@router.post("/login", response_model=LoginResponse)
async def login_all_keys(
    auth_manager: AuthManager = Depends(get_auth_manager)
):
    """Login to all configured API keys."""
    try:
        logger.info("Login to all keys requested")
        
        # Perform login
        results = await auth_manager.login_all_keys()
        successful_logins = sum(results.values())
        total_keys = len(results)
        
        logger.info("Login process completed", {
            "successful_logins": successful_logins,
            "total_keys": total_keys,
            "success_rate": f"{(successful_logins/total_keys*100):.1f}%"
        })
        
        return LoginResponse(
            success=successful_logins > 0,
            message=f"Login completed: {successful_logins}/{total_keys} successful",
            successful_logins=successful_logins,
            total_keys=total_keys,
            login_results=results
        )
        
    except Exception as e:
        logger.error("Login process failed", error=e, error_code="AUTH002")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Login failed: {str(e)}"
        )

@router.get("/status", response_model=AuthStatusResponse)
async def get_auth_status(
    auth_manager: AuthManager = Depends(get_auth_manager)
):
    """Get current authentication status."""
    try:
        status_info = auth_manager.get_auth_status()
        
        return AuthStatusResponse(
            authenticated=status_info.get("authenticated", False),
            active_keys=status_info.get("active_keys", 0),
            total_keys=status_info.get("total_keys", 0),
            session_info=status_info.get("sessions", {})
        )
        
    except Exception as e:
        logger.error("Status check failed", error=e, error_code="AUTH003")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Status check failed: {str(e)}"
        )
```

### **3. TRADING ROUTER**

#### **api/routers/trading.py**
```python
"""
Trading API Endpoints
=====================

Handles all trading operations including orders, positions, and trades.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from typing import List, Optional

from ...methods import place_order, modify_order, cancel_order
from ...models.trading import (
    PlaceOrderRequest, PlaceOrderResponse,
    ModifyOrderRequest, ModifyOrderResponse,
    CancelOrderRequest, CancelOrderResponse,
    OrderBookResponse, TradeBookResponse
)
from ...logger import get_api_logger

router = APIRouter()
logger = get_api_logger("trading_router")

@router.post("/orders", response_model=PlaceOrderResponse)
async def place_trading_order(request: PlaceOrderRequest):
    """Place a new trading order."""
    try:
        logger.info("Order placement requested", {
            "symbol": request.symbol,
            "quantity": request.quantity,
            "transaction_type": request.transaction_type,
            "order_type": request.order_type
        })
        
        # Place order using existing method
        result = await place_order(
            symbol=request.symbol,
            quantity=request.quantity,
            transaction_type=request.transaction_type,
            order_type=request.order_type,
            product=request.product,
            price=request.price,
            trigger_price=request.trigger_price,
            disclosed_quantity=request.disclosed_quantity,
            validity=request.validity,
            variety=request.variety
        )
        
        logger.success("Order placed successfully", {
            "order_id": result.get("order_id"),
            "symbol": request.symbol,
            "status": result.get("status")
        })
        
        return PlaceOrderResponse(
            success=True,
            order_id=result.get("order_id"),
            status=result.get("status"),
            message=result.get("message", "Order placed successfully"),
            timestamp=result.get("timestamp")
        )
        
    except Exception as e:
        logger.error("Order placement failed", 
                    error=e, 
                    error_code="TRADE001",
                    extra={"symbol": request.symbol})
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Order placement failed: {str(e)}"
        )

@router.put("/orders/{order_id}", response_model=ModifyOrderResponse)
async def modify_trading_order(
    order_id: str,
    request: ModifyOrderRequest
):
    """Modify an existing order."""
    try:
        logger.info("Order modification requested", {
            "order_id": order_id,
            "modifications": request.dict(exclude_unset=True)
        })
        
        # Modify order using existing method
        result = await modify_order(
            order_id=order_id,
            quantity=request.quantity,
            price=request.price,
            trigger_price=request.trigger_price,
            disclosed_quantity=request.disclosed_quantity,
            validity=request.validity
        )
        
        logger.success("Order modified successfully", {
            "order_id": order_id,
            "status": result.get("status")
        })
        
        return ModifyOrderResponse(
            success=True,
            order_id=order_id,
            status=result.get("status"),
            message=result.get("message", "Order modified successfully")
        )
        
    except Exception as e:
        logger.error("Order modification failed",
                    error=e,
                    error_code="TRADE002", 
                    extra={"order_id": order_id})
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Order modification failed: {str(e)}"
        )

@router.delete("/orders/{order_id}", response_model=CancelOrderResponse)
async def cancel_trading_order(order_id: str):
    """Cancel an existing order."""
    try:
        logger.info("Order cancellation requested", {"order_id": order_id})
        
        # Cancel order using existing method
        result = await cancel_order(order_id=order_id)
        
        logger.success("Order cancelled successfully", {
            "order_id": order_id,
            "status": result.get("status")
        })
        
        return CancelOrderResponse(
            success=True,
            order_id=order_id,
            status=result.get("status"),
            message=result.get("message", "Order cancelled successfully")
        )
        
    except Exception as e:
        logger.error("Order cancellation failed",
                    error=e,
                    error_code="TRADE003",
                    extra={"order_id": order_id})
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Order cancellation failed: {str(e)}"
        )
```

### **4. WEBSOCKET IMPLEMENTATION**

#### **websockets/handlers/market_data.py**
```python
"""
Real-time Market Data WebSocket Handler
=======================================

Provides real-time market data streaming via WebSocket.
"""

import asyncio
import json
from typing import Set, Dict, Any
from fastapi import WebSocket, WebSocketDisconnect

from ...methods.get_ltp_data import get_ltp_data, get_bulk_ltp_data
from ...logger import get_api_logger
from ..connection_manager import ConnectionManager

logger = get_api_logger("ws_market_data")

class MarketDataHandler:
    """Handles real-time market data WebSocket connections."""
    
    def __init__(self):
        self.connection_manager = ConnectionManager()
        self.subscribed_symbols: Dict[str, Set[WebSocket]] = {}
        self.streaming_task: Optional[asyncio.Task] = None
        
    async def connect(self, websocket: WebSocket, client_id: str):
        """Connect a new WebSocket client."""
        await self.connection_manager.connect(websocket, client_id)
        logger.info("Market data WebSocket connected", {
            "client_id": client_id,
            "total_connections": len(self.connection_manager.active_connections)
        })
        
    async def disconnect(self, websocket: WebSocket, client_id: str):
        """Disconnect a WebSocket client."""
        self.connection_manager.disconnect(websocket, client_id)
        
        # Remove from symbol subscriptions
        for symbol_set in self.subscribed_symbols.values():
            symbol_set.discard(websocket)
            
        logger.info("Market data WebSocket disconnected", {
            "client_id": client_id,
            "remaining_connections": len(self.connection_manager.active_connections)
        })
    
    async def subscribe_symbols(self, websocket: WebSocket, symbols: List[str]):
        """Subscribe to real-time data for specific symbols."""
        for symbol in symbols:
            if symbol not in self.subscribed_symbols:
                self.subscribed_symbols[symbol] = set()
            self.subscribed_symbols[symbol].add(websocket)
            
        logger.info("Symbols subscribed", {
            "symbols": symbols,
            "total_subscriptions": sum(len(s) for s in self.subscribed_symbols.values())
        })
        
        # Start streaming if not already running
        if not self.streaming_task or self.streaming_task.done():
            self.streaming_task = asyncio.create_task(self._stream_market_data())
    
    async def _stream_market_data(self):
        """Stream real-time market data to subscribed clients."""
        while self.subscribed_symbols:
            try:
                # Get unique symbols from all subscriptions
                symbols = list(self.subscribed_symbols.keys())
                
                if symbols:
                    # Fetch bulk LTP data
                    ltp_data = await get_bulk_ltp_data(symbols)
                    
                    # Send data to subscribed clients
                    for symbol, data in ltp_data.items():
                        if symbol in self.subscribed_symbols:
                            message = {
                                "type": "market_data",
                                "symbol": symbol,
                                "data": data,
                                "timestamp": datetime.now(UTC).isoformat()
                            }
                            
                            # Send to all subscribers of this symbol
                            websockets_to_remove = set()
                            for ws in self.subscribed_symbols[symbol]:
                                try:
                                    await ws.send_text(json.dumps(message))
                                except:
                                    websockets_to_remove.add(ws)
                            
                            # Remove disconnected websockets
                            for ws in websockets_to_remove:
                                self.subscribed_symbols[symbol].discard(ws)
                
                # Wait before next update (configurable interval)
                await asyncio.sleep(1.0)  # 1 second interval
                
            except Exception as e:
                logger.error("Market data streaming error", 
                           error=e, 
                           error_code="WS001")
                await asyncio.sleep(5.0)  # Wait before retry

# Global handler instance
market_data_handler = MarketDataHandler()
```

---

## 🐰 **RABBITMQ INTEGRATION**

### **messaging/publisher.py**
```python
"""
RabbitMQ Message Publisher
==========================

Handles publishing messages to RabbitMQ for AI engine communication.
"""

import asyncio
import json
import uuid
from typing import Dict, Any, Optional
from datetime import datetime, UTC

from .connection import get_rabbitmq_connection
from ..logger import get_infrastructure_logger

logger = get_infrastructure_logger("rabbitmq_publisher")

class MessagePublisher:
    """Publishes messages to RabbitMQ queues."""
    
    def __init__(self):
        self.connection = None
        self.channel = None
        
    async def initialize(self):
        """Initialize RabbitMQ connection."""
        self.connection = await get_rabbitmq_connection()
        self.channel = await self.connection.channel()
        
        # Declare exchanges
        await self.channel.declare_exchange(
            "angel.direct", 
            type="direct", 
            durable=True
        )
        await self.channel.declare_exchange(
            "angel.topic", 
            type="topic", 
            durable=True
        )
        await self.channel.declare_exchange(
            "angel.fanout", 
            type="fanout", 
            durable=True
        )
        
        logger.info("RabbitMQ publisher initialized")
    
    async def publish_to_ai(self, message_type: str, data: Dict[str, Any], 
                           priority: int = 0, correlation_id: Optional[str] = None):
        """Publish message to AI engine."""
        try:
            message = {
                "message_type": message_type,
                "correlation_id": correlation_id or str(uuid.uuid4()),
                "timestamp": datetime.now(UTC).isoformat(),
                "data": data,
                "source": "angel_one_service"
            }
            
            await self.channel.default_exchange.publish(
                message=json.dumps(message),
                routing_key="ai.requests",
                properties={
                    "priority": priority,
                    "correlation_id": message["correlation_id"],
                    "reply_to": "angel.responses"
                }
            )
            
            logger.info("Message published to AI engine", {
                "message_type": message_type,
                "correlation_id": message["correlation_id"],
                "data_size": len(json.dumps(data))
            })
            
            return message["correlation_id"]
            
        except Exception as e:
            logger.error("Failed to publish message to AI",
                        error=e,
                        error_code="MSG001",
                        extra={
                            "message_type": message_type,
                            "correlation_id": correlation_id
                        })
            raise
    
    async def broadcast_market_data(self, symbol: str, data: Dict[str, Any]):
        """Broadcast market data to all interested services."""
        try:
            message = {
                "type": "market_data_update",
                "symbol": symbol,
                "data": data,
                "timestamp": datetime.now(UTC).isoformat(),
                "source": "angel_one_service"
            }
            
            await self.channel.declare_exchange("angel.fanout").publish(
                message=json.dumps(message),
                routing_key=""  # Fanout ignores routing key
            )
            
        except Exception as e:
            logger.error("Failed to broadcast market data",
                        error=e,
                        error_code="MSG002",
                        extra={"symbol": symbol})

# Global publisher instance
publisher = MessagePublisher()
```

---

## 📊 **PYDANTIC MODELS**

### **models/trading.py**
```python
"""
Trading Request/Response Models
===============================

Pydantic models for trading operations.
"""

from pydantic import BaseModel, Field, validator
from typing import Optional, Literal
from datetime import datetime
from decimal import Decimal

class PlaceOrderRequest(BaseModel):
    """Request model for placing orders."""
    
    symbol: str = Field(..., description="Trading symbol (e.g., RELIANCE)")
    quantity: int = Field(..., gt=0, description="Order quantity")
    transaction_type: Literal["BUY", "SELL"] = Field(..., description="Transaction type")
    order_type: Literal["MARKET", "LIMIT", "SLM", "SL"] = Field(..., description="Order type")
    product: Literal["INTRADAY", "DELIVERY", "MARGIN", "BO", "CO"] = Field(..., description="Product type")
    
    price: Optional[Decimal] = Field(None, gt=0, description="Order price (required for LIMIT orders)")
    trigger_price: Optional[Decimal] = Field(None, gt=0, description="Trigger price (for SL/SLM orders)")
    disclosed_quantity: Optional[int] = Field(None, ge=0, description="Disclosed quantity")
    validity: Literal["DAY", "IOC", "GTD"] = Field("DAY", description="Order validity")
    variety: Literal["NORMAL", "STOPLOSS", "AMO", "ROBO"] = Field("NORMAL", description="Order variety")
    
    @validator("price")
    def validate_price_for_limit_orders(cls, v, values):
        """Validate price for limit orders."""
        if values.get("order_type") in ["LIMIT", "SL"] and v is None:
            raise ValueError("Price is required for LIMIT and SL orders")
        return v
    
    @validator("trigger_price")
    def validate_trigger_price(cls, v, values):
        """Validate trigger price for stop loss orders."""
        if values.get("order_type") in ["SLM", "SL"] and v is None:
            raise ValueError("Trigger price is required for SLM and SL orders")
        return v

class PlaceOrderResponse(BaseModel):
    """Response model for order placement."""
    
    success: bool = Field(..., description="Operation success status")
    order_id: Optional[str] = Field(None, description="Generated order ID")
    status: Optional[str] = Field(None, description="Order status")
    message: str = Field(..., description="Response message")
    timestamp: Optional[datetime] = Field(None, description="Response timestamp")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

class ModifyOrderRequest(BaseModel):
    """Request model for modifying orders."""
    
    quantity: Optional[int] = Field(None, gt=0, description="New quantity")
    price: Optional[Decimal] = Field(None, gt=0, description="New price")
    trigger_price: Optional[Decimal] = Field(None, gt=0, description="New trigger price")
    disclosed_quantity: Optional[int] = Field(None, ge=0, description="New disclosed quantity")
    validity: Optional[Literal["DAY", "IOC", "GTD"]] = Field(None, description="New validity")

class ModifyOrderResponse(BaseModel):
    """Response model for order modification."""
    
    success: bool = Field(..., description="Operation success status")
    order_id: str = Field(..., description="Modified order ID")
    status: Optional[str] = Field(None, description="Order status after modification")
    message: str = Field(..., description="Response message")

class CancelOrderResponse(BaseModel):
    """Response model for order cancellation."""
    
    success: bool = Field(..., description="Operation success status")
    order_id: str = Field(..., description="Cancelled order ID")
    status: Optional[str] = Field(None, description="Order status after cancellation")
    message: str = Field(..., description="Response message")
```

---

This detailed implementation plan provides the complete structure for transforming your Angel One module into a production-ready FastAPI microservice with RabbitMQ integration and WebSocket support. The architecture maintains all existing functionality while adding powerful new capabilities for AI-driven trading.

Would you like me to proceed with implementing any specific part of this plan?
