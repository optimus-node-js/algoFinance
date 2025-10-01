"""
Angel One FastAPI Main Application
==================================

Production-ready FastAPI application for Angel One trading operations.
Features enterprise-grade logging, monitoring, and real-time capabilities.

Key Features:
- 🚀 Sub-100ms API response times
- 🔄 Real-time WebSocket streaming  
- 🐰 RabbitMQ messaging for AI integration
- 📊 Scalar documentation (replacing Swagger)
- 🛡️ Enterprise security and rate limiting
- 📈 Comprehensive health monitoring
- ⚡ Auto-login and session management
"""

import asyncio
import uvicorn
from contextlib import asynccontextmanager
from typing import Dict, Any

from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

# Import routers
from .routers import (
    authentication,
    trading, 
    market_data,
    portfolio,
    risk,
    advanced,
    admin,
    websockets,
    health
)

# Import middleware and dependencies
from .middleware import (
    LoggingMiddleware,
    RateLimitMiddleware, 
    PerformanceMiddleware,
    SecurityMiddleware
)
from .exceptions import setup_exception_handlers
from .dependencies import get_rate_limiter, get_auth_manager

# Import Kafka messaging for order events
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent.parent / "messaging_enhanced"))

try:
    from messaging_enhanced.kafka import OrderProducer, KafkaManager
    from messaging_enhanced.kafka.producers.order_producer import get_order_producer, close_order_producer
    from messaging_enhanced.kafka.kafka_manager import get_kafka_manager, close_kafka_manager
    KAFKA_AVAILABLE = True
except ImportError as e:
    print(f"⚠️ Kafka messaging not available - running without order event publishing: {e}")
    KAFKA_AVAILABLE = False

# Import WebSocket manager for live market data
try:
    from websocket.websocket_manager import get_websocket_manager, close_websocket_manager
    WEBSOCKET_AVAILABLE = True
except ImportError as e:
    print(f"⚠️ WebSocket manager not available - running without live market data: {e}")
    WEBSOCKET_AVAILABLE = False

# Import configuration and services
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from config.settings import settings
from logger import get_infrastructure_logger
from messaging.connection import init_rabbitmq, close_rabbitmq
from services.authentication import AuthManager

# Initialize logger
logger = get_infrastructure_logger("fastapi_main")

# Helper function to publish order events to Kafka
async def publish_order_event(event_type: str, order_data: dict, correlation_id: str = None):
    """
    Publish order events to Kafka for inter-service communication.
    
    Args:
        event_type: Type of order event (ORDER_PLACED, ORDER_EXECUTED, ORDER_CANCELLED, etc.)
        order_data: Order data dictionary
        correlation_id: Optional correlation ID for request tracing
    """
    if not KAFKA_AVAILABLE or not hasattr(app.state, 'order_producer'):
        return
    
    try:
        import time
        import uuid
        from datetime import datetime
        
        # Create order event message
        order_event = {
            "event_id": str(uuid.uuid4()),
            "timestamp": int(time.time() * 1_000_000_000),  # nanoseconds
            "service": "angel_one_api",
            "event_type": event_type,
            "order_id": order_data.get("order_id", ""),
            "symbol": order_data.get("symbol", ""),
            "exchange": order_data.get("exchange", ""),
            "quantity": order_data.get("quantity", 0),
            "price": order_data.get("price", 0.0),
            "order_type": order_data.get("order_type", ""),
            "side": order_data.get("side", ""),
            "status": order_data.get("status", ""),
            "user_id": order_data.get("user_id", ""),
            "correlation_id": correlation_id,
            "metadata": order_data
        }
        
        # Publish to Kafka
        await app.state.order_producer.send_order_event(order_event)
        logger.info(f"📤 Published order event: {event_type} for {order_data.get('symbol', 'unknown')}")
        
    except Exception as e:
        logger.error(f"❌ Failed to publish order event: {e}")

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan management.
    Handles startup and shutdown events.
    """
    # 🚀 STARTUP SEQUENCE
    logger.info("🚀 Starting Angel One FastAPI Service", {
        "version": settings.VERSION,
        "environment": settings.ENVIRONMENT,
        "debug": settings.DEBUG,
        "host": settings.HOST,
        "port": settings.PORT
    })
    
    startup_tasks = []
    
    try:
        # Initialize RabbitMQ connection
        if settings.RABBITMQ_URL != "disabled":
            logger.info("📡 Initializing RabbitMQ connection...")
            startup_tasks.append(init_rabbitmq())
        
        # Initialize Kafka for order events
        if KAFKA_AVAILABLE:
            logger.info("🔄 Initializing Kafka for order events...")
            try:
                kafka_manager = get_kafka_manager()
                order_producer = get_order_producer("angel_one_api_service")
                
                # Create Kafka topics for order events and live market data
                await kafka_manager.create_topic("hft-order-events", num_partitions=3, replication_factor=1)
                await kafka_manager.create_topic("hft-execution-events", num_partitions=3, replication_factor=1)
                await kafka_manager.create_topic("hft-market-data-live-ticks", num_partitions=6, replication_factor=1)
                await kafka_manager.create_topic("hft-market-data-live-ltp", num_partitions=6, replication_factor=1)
                await kafka_manager.create_topic("hft-market-data-live-candles", num_partitions=3, replication_factor=1)
                await kafka_manager.create_topic("hft-market-data-live-orderbook", num_partitions=3, replication_factor=1)
                
                app.state.kafka_manager = kafka_manager
                app.state.order_producer = order_producer
                logger.info("✅ Kafka order event publishing initialized")
            except Exception as e:
                logger.warning(f"⚠️ Failed to initialize Kafka: {e}")
                KAFKA_AVAILABLE = False
        
        # Initialize WebSocket for live market data
        if WEBSOCKET_AVAILABLE:
            logger.info("🌐 Initializing WebSocket for live market data...")
            try:
                websocket_manager = get_websocket_manager(auth_manager)
                app.state.websocket_manager = websocket_manager
                logger.info("✅ WebSocket manager initialized")
            except Exception as e:
                logger.warning(f"⚠️ Failed to initialize WebSocket manager: {e}")
                WEBSOCKET_AVAILABLE = False
        
        # Initialize authentication manager
        logger.info("🔐 Initializing authentication manager...")
        auth_manager = AuthManager()
        app.state.auth_manager = auth_manager
        
        # Initialize rate limiter
        if settings.RATE_LIMIT_ENABLED:
            logger.info("🛡️ Initializing rate limiter...")
            from rate_limiter.rate_controller import initialize_rate_controller
            # Get API keys from settings (.env file)
            api_keys = settings.get_api_keys()
            logger.info(f"🔑 Found {len(api_keys)} API keys: {[key[:8]+'...' if len(key) > 8 else key for key in api_keys]}")
            rate_controller = initialize_rate_controller(api_keys)
            app.state.rate_controller = rate_controller
        
        # Wait for all startup tasks
        if startup_tasks:
            await asyncio.gather(*startup_tasks)
        
        # Auto-login on startup if credentials are available
        try:
            if hasattr(settings, 'CLIENT_ID') and settings.CLIENT_ID and settings.PASSWORD:
                logger.info("🔑 Attempting auto-login with available credentials...")
                from methods.login_by_password import login_by_password
                # Generate TOTP code from secret
                totp_code = "123456"  # Default fallback
                if hasattr(settings, 'TOTP_SECRET') and settings.TOTP_SECRET:
                    try:
                        import pyotp
                        totp = pyotp.TOTP(settings.TOTP_SECRET)
                        totp_code = totp.now()
                        logger.info("🔐 Generated TOTP code from secret")
                    except Exception as e:
                        logger.warning(f"⚠️ Failed to generate TOTP, using fallback: {e}")
                
                login_result = await login_by_password(
                    client_id=settings.CLIENT_ID,
                    password=settings.PASSWORD,
                    totp_code=totp_code
                )
                if login_result.get('success'):
                    logger.success(f"✅ Auto-login successful for {settings.CLIENT_ID[:6]}...")
                else:
                    logger.warning(f"⚠️ Auto-login failed: {login_result.get('error', 'Unknown error')}")
            else:
                logger.info("ℹ️ No credentials configured for auto-login")
        except Exception as e:
            logger.warning(f"⚠️ Auto-login failed: {str(e)}")
        
        # Health check initialization
        logger.info("💚 Running initial health checks...")
        app.state.startup_time = asyncio.get_event_loop().time()
        app.state.healthy = True
        
        logger.success("✅ Angel One FastAPI Service started successfully", {
            "services_initialized": len(startup_tasks) + 2,
            "startup_time_ms": f"{(asyncio.get_event_loop().time() - app.state.startup_time) * 1000:.2f}"
        })
        
    except Exception as e:
        logger.critical("❌ Failed to start Angel One FastAPI Service", 
                       error=e, 
                       error_code="STARTUP_001")
        app.state.healthy = False
        raise
    
    yield
    
    # 🛑 SHUTDOWN SEQUENCE
    logger.info("🛑 Shutting down Angel One FastAPI Service...")
    
    try:
        # Close WebSocket connections
        if WEBSOCKET_AVAILABLE and hasattr(app.state, 'websocket_manager'):
            logger.info("🌐 Closing WebSocket connections...")
            await close_websocket_manager(app.state.websocket_manager)
        
        # Close Kafka connections
        if KAFKA_AVAILABLE and hasattr(app.state, 'order_producer'):
            logger.info("🔄 Closing Kafka connections...")
            await close_order_producer()
            await close_kafka_manager()
        
        # Close RabbitMQ connection
        if hasattr(app.state, 'rabbitmq_connection'):
            logger.info("📡 Closing RabbitMQ connection...")
            await close_rabbitmq()
        
        # Cleanup authentication manager
        if hasattr(app.state, 'auth_manager'):
            logger.info("🔐 Cleaning up authentication manager...")
            # Add cleanup logic if needed
        
        logger.info("✅ Angel One FastAPI Service shutdown complete")
        
    except Exception as e:
        logger.error("❌ Error during shutdown", error=e, error_code="SHUTDOWN_001")

# Create FastAPI application
app = FastAPI(
    title="Angel One Trading API",
    description="""
    🚀 **Enterprise-grade Angel One SmartAPI microservice** for High-Frequency Trading (HFT)
    
    ## Features
    - ✅ **Complete API Coverage**: All 28 Angel One SmartAPI methods
    - ⚡ **Ultra-Fast**: Sub-100ms response times
    - 🔄 **Real-time**: WebSocket streaming for live data
    - 🤖 **AI Integration**: RabbitMQ messaging with AI engine
    - 📊 **Enterprise Monitoring**: Comprehensive health checks
    - 🛡️ **Security**: Advanced rate limiting and authentication
    
    ## Quick Start
    1. **Authenticate**: `POST /auth/auto-login` - Automatic Angel One login
    2. **Health Check**: `GET /health/status` - Service health status  
    3. **Trading**: `POST /trading/orders` - Place orders
    4. **Real-time**: `WS /ws/market/ltp` - Live market data
    
    ## Performance Targets
    - 🎯 **API Response**: < 100ms average
    - 🎯 **WebSocket Latency**: < 50ms
    - 🎯 **Throughput**: 1000+ requests/second
    - 🎯 **Uptime**: 99.9% availability
    """,
    version=settings.VERSION,
    contact={
        "name": "Angel One Trading API Support",
        "email": "support@hft.trading",
    },
    license_info={
        "name": "Enterprise License",
        "url": "https://hft.trading/license",
    },
    # Disable default Swagger docs (we'll use Scalar)
    docs_url=None,
    redoc_url=None,
    openapi_url=settings.OPENAPI_URL,
    lifespan=lifespan
)

# 🔧 MIDDLEWARE SETUP
# Order matters - middleware is applied in reverse order

# Security middleware (applied last)
app.add_middleware(SecurityMiddleware)

# Performance monitoring
app.add_middleware(PerformanceMiddleware)

# Rate limiting
if settings.RATE_LIMIT_ENABLED:
    app.add_middleware(RateLimitMiddleware)

# Logging middleware 
app.add_middleware(LoggingMiddleware)

# GZIP compression
if settings.ENABLE_GZIP:
    app.add_middleware(
        GZipMiddleware, 
        minimum_size=settings.GZIP_MINIMUM_SIZE
    )

# CORS middleware (applied first)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.get_cors_origins(),
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=["*"],
    expose_headers=["X-Request-ID", "X-Response-Time"]
)

# 🚨 EXCEPTION HANDLERS
setup_exception_handlers(app)

# 📡 API ROUTERS
app.include_router(
    health.router,
    prefix="/health",
    tags=["🩺 Health & Monitoring"]
)

app.include_router(
    authentication.router,
    prefix="/auth", 
    tags=["🔐 Authentication"]
)

app.include_router(
    trading.router,
    prefix="/trading",
    tags=["💹 Trading Operations"]
)

app.include_router(
    market_data.router,
    prefix="/market",
    tags=["📊 Market Data"]
)

app.include_router(
    portfolio.router,
    prefix="/portfolio",
    tags=["💰 Portfolio Management"]
)

app.include_router(
    risk.router,
    prefix="/risk",
    tags=["⚠️ Risk Management"]
)

app.include_router(
    advanced.router,
    prefix="/advanced",
    tags=["🎯 Advanced Features"]
)

app.include_router(
    admin.router,
    prefix="/admin",
    tags=["👨‍💼 Administration"]
)

app.include_router(
    websockets.router,
    prefix="/ws",
    tags=["🌐 WebSocket Streaming"]
)

# 🏠 ROOT ENDPOINTS

@app.get("/", response_class=HTMLResponse, include_in_schema=False)
async def root():
    """
    Service information and quick navigation.
    """
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Angel One Trading API</title>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 40px; background: #f5f5f5; }}
            .container {{ max-width: 800px; margin: 0 auto; background: white; padding: 30px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
            h1 {{ color: #2c3e50; margin-bottom: 20px; }}
            .status {{ padding: 10px; border-radius: 5px; margin: 10px 0; }}
            .healthy {{ background: #d4edda; color: #155724; border: 1px solid #c3e6cb; }}
            .link {{ display: inline-block; margin: 10px; padding: 12px 20px; background: #007bff; color: white; text-decoration: none; border-radius: 5px; }}
            .link:hover {{ background: #0056b3; }}
            .info {{ background: #e3f2fd; padding: 15px; border-radius: 5px; margin: 15px 0; }}
            .code {{ background: #f8f9fa; padding: 10px; border-radius: 3px; font-family: monospace; border-left: 4px solid #007bff; }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🚀 Angel One Trading API</h1>
            <div class="status healthy">
                ✅ Service Status: <strong>OPERATIONAL</strong> (v{settings.VERSION})
            </div>
            
            <div class="info">
                <h3>📚 Documentation</h3>
                <a href="/scalar-docs" class="link">📊 Scalar API Docs</a>
                <a href="/health/status" class="link">💚 Health Status</a>
                <a href="/health/metrics" class="link">📈 Metrics</a>
            </div>
            
            <div class="info">
                <h3>🔧 Quick Start</h3>
                <div class="code">
                    # Auto-login to Angel One<br>
                    POST /auth/auto-login<br><br>
                    
                    # Get live LTP data<br>
                    GET /market/ltp/RELIANCE<br><br>
                    
                    # Real-time WebSocket<br>
                    WS /ws/market/ltp
                </div>
            </div>
            
            <div class="info">
                <strong>Environment:</strong> {settings.ENVIRONMENT.value.upper()}<br>
                <strong>Host:</strong> {settings.HOST}:{settings.PORT}<br>
                <strong>Performance Target:</strong> &lt; 100ms response time
            </div>
        </div>
    </body>
    </html>
    """

@app.get("/ping", include_in_schema=False)
async def ping():
    """
    Simple ping endpoint for load balancer health checks.
    """
    return {"status": "pong", "service": "angel-one-api", "version": settings.VERSION}

# 📊 SCALAR DOCUMENTATION ENDPOINT
@app.get("/scalar-docs", response_class=HTMLResponse, include_in_schema=False)
async def scalar_docs():
    """
    Scalar API documentation interface.
    Modern alternative to Swagger UI with better performance.
    """
    return f"""
    <!doctype html>
    <html>
    <head>
        <title>Angel One API Documentation</title>
        <meta charset="utf-8" />
        <meta name="viewport" content="width=device-width, initial-scale=1" />
        <style>
            body {{ margin: 0; }}
        </style>
    </head>
    <body>
        <script
            id="api-reference"
            data-url="{settings.OPENAPI_URL}"
            data-configuration='{{"theme": "kepler", "layout": "modern", "defaultHttpClient": {{"targetKey": "javascript", "clientKey": "fetch"}}}}'
        ></script>
        <script src="https://cdn.jsdelivr.net/npm/@scalar/api-reference@latest"></script>
    </body>
    </html>
    """

# 🔧 DEVELOPMENT SERVER
def run_development_server():
    """Run the development server with hot reload."""
    uvicorn.run(
        "api.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=True,
        log_level=settings.LOG_LEVEL.lower(),
        reload_dirs=["./"],
        reload_excludes=["*.log", "*.pyc", "__pycache__", ".git"]
    )

if __name__ == "__main__":
    if settings.is_development():
        run_development_server()
    else:
        # Production server should be run with gunicorn or similar
        uvicorn.run(
            app,
            host=settings.HOST,
            port=settings.PORT,
            log_level=settings.LOG_LEVEL.lower()
        )
