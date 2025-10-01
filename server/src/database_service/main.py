"""
Database Service API
===================

FastAPI service providing centralized database access for all HFT microservices.
Exposes REST endpoints for database operations with Prisma + PostgreSQL.
"""

import asyncio
import logging
import os
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
from contextlib import asynccontextmanager
from pathlib import Path

import logger
# Load environment variables from .env file
from dotenv import load_dotenv

# Load .env file from project root
env_path = Path(__file__).parent.parent.parent.parent / ".env"
load_dotenv(dotenv_path=env_path)

from fastapi import FastAPI, HTTPException, Depends, Query, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

# Import our database components
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent))
sys.path.append(str(Path(__file__).parent.parent / "messaging_enhanced"))

from connection import get_db_manager, close_all_db_connections
from prisma_client import get_prisma_service, close_prisma_connections
from models import *

# Import Kafka messaging for inter-service communication
try:
    from messaging_enhanced.kafka import DatabaseProducer, KafkaManager
    from messaging_enhanced.kafka.producers.database_producer import get_database_producer, close_database_producer
    from messaging_enhanced.kafka.kafka_manager import get_kafka_manager, close_kafka_manager
    KAFKA_AVAILABLE = True
except ImportError:
    logger.warning("Kafka messaging not available - running without messaging")
    KAFKA_AVAILABLE = False

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("database_service")


# Helper function to publish database events
async def publish_database_event(
    event_type: str, 
    entity_type: str,
    entity_id: Optional[str] = None,
    user_id: Optional[str] = None,
    data: Optional[Dict[str, Any]] = None,
    correlation_id: Optional[str] = None,
    session_id: Optional[str] = None
):
    """Publish database events to Kafka for inter-service communication."""
    if not KAFKA_AVAILABLE:
        return
    
    try:
        database_producer = get_database_producer()
        result = database_producer.send_database_event(
            event_type=event_type,
            entity_type=entity_type,
            entity_id=entity_id,
            user_id=user_id,
            data=data or {},
            correlation_id=correlation_id,
            session_id=session_id
        )
        
        if result['success']:
            logger.debug(f"📤 Published event: {event_type} for {entity_type} (ID: {entity_id})")
        else:
            logger.warning(f"⚠️ Failed to publish event: {event_type} - {result.get('error', 'Unknown error')}")
            
    except Exception as e:
        logger.error(f"❌ Error publishing database event: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management."""
    logger.info("Starting Database Service...")
    
    # Initialize database connections
    try:
        prisma_service = await get_prisma_service()
        logger.info("✅ Database Service connected to Prisma")
        
        # Initialize Kafka if available
        if KAFKA_AVAILABLE:
            kafka_servers = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
            kafka_manager = get_kafka_manager(kafka_servers)
            
            # Create database service topics
            topics = [
                {"name": "hft-database-events", "partitions": 3, "replication": 1},
                {"name": "hft-database-health", "partitions": 1, "replication": 1}
            ]
            
            try:
                results = kafka_manager.create_topics(topics)
                logger.info(f"✅ Kafka topics created: {results}")
                
                # Initialize database producer
                database_producer = get_database_producer()
                logger.info("✅ Database producer initialized")
                
            except Exception as e:
                logger.warning(f"⚠️ Kafka initialization failed: {e}")
            
            logger.info("✅ Database Service Kafka integration ready")
        
        logger.info("🚀 Database Service started successfully")
        yield
        
    except Exception as e:
        logger.error(f"❌ Failed to start Database Service: {e}")
        raise
    finally:
        # Cleanup on shutdown
        logger.info("Shutting down Database Service...")
        await close_all_db_connections()
        await close_prisma_connections()
        
        if KAFKA_AVAILABLE:
            close_database_producer()
            close_kafka_manager()
            logger.info("✅ Kafka connections closed")
        
        logger.info("✅ Database Service shutdown complete")


# Create FastAPI application
app = FastAPI(
    title="HFT Database Service",
    description="Centralized database service for High-Frequency Trading system",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ================================
# HEALTH & STATUS ENDPOINTS
# ================================

@app.get("/health", response_model=HealthCheckResponse)
async def health_check():
    """Database service health check."""
    try:
        prisma_service = await get_prisma_service()
        health = await prisma_service.health_check()
        
        return HealthCheckResponse(
            service="database_service",
            status=health.get("status", "unknown"),
            connection=health.get("connection"),
            queryTimeMs=health.get("query_time_ms"),
            uptimeSeconds=health.get("uptime_seconds"),
            totalQueries=health.get("total_queries"),
            errorCount=health.get("error_count"),
            error=health.get("error")
        )
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return HealthCheckResponse(
            service="database_service",
            status="unhealthy",
            error=str(e)
        )


@app.get("/stats", response_model=DatabaseStatsResponse)
async def get_database_stats():
    """Get database service statistics."""
    try:
        prisma_service = await get_prisma_service()
        stats = prisma_service.get_stats()
        
        return DatabaseStatsResponse(
            service="database_service",
            isConnected=stats["is_connected"],
            uptimeSeconds=stats["uptime_seconds"],
            totalQueries=stats["total_queries"],
            errorCount=stats["error_count"],
            errorRate=stats["error_rate"],
            queriesPerSecond=stats["queries_per_second"],
            connectionAttempts=stats["connection_attempts"]
        )
    except Exception as e:
        logger.error(f"Failed to get stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ================================
# USER MANAGEMENT ENDPOINTS
# ================================

@app.post("/users", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(user_data: UserCreate):
    """Create a new user."""
    try:
        db_manager = await get_db_manager("database_service")
        client = await db_manager.get_client()
        
        # Check if user already exists
        existing_user = await client.user.find_first(
            where={
                "OR": [
                    {"username": user_data.username},
                    {"email": user_data.email}
                ]
            }
        )
        
        if existing_user:
            raise HTTPException(
                status_code=400,
                detail="User with this username or email already exists"
            )
        
        # Create user (password should be hashed in production)
        user = await client.user.create({
            "username": user_data.username,
            "email": user_data.email,
            "password": user_data.password,  # Hash this!
            "role": user_data.role
        })
        
        # Publish user creation event
        await publish_database_event(
            event_type="USER_CREATED",
            entity_type="USER",
            entity_id=user.id,
            data={"username": user.username, "role": user.role}
        )
        
        return UserResponse(**user.dict())
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create user: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/users/{user_id}", response_model=UserResponse)
async def get_user(user_id: str):
    """Get user by ID."""
    try:
        db_manager = await get_db_manager("database_service")
        client = await db_manager.get_client()
        
        user = await client.user.find_unique(where={"id": user_id})
        
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        return UserResponse(**user.dict())
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get user: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/users", response_model=List[UserResponse])
async def list_users(
    page: int = Query(1, ge=1),
    limit: int = Query(100, ge=1, le=1000),
    role: Optional[UserRole] = None
):
    """List users with pagination."""
    try:
        db_manager = await get_db_manager("database_service")
        client = await db_manager.get_client()
        
        skip = (page - 1) * limit
        where_clause = {"role": role} if role else {}
        
        users = await client.user.find_many(
            where=where_clause,
            skip=skip,
            take=limit,
            order={"createdAt": "desc"}
        )
        
        return [UserResponse(**user.dict()) for user in users]
        
    except Exception as e:
        logger.error(f"Failed to list users: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ================================
# INSTRUMENT MANAGEMENT ENDPOINTS
# ================================

@app.post("/instruments", response_model=InstrumentResponse, status_code=status.HTTP_201_CREATED)
async def create_instrument(instrument_data: InstrumentCreate):
    """Create a new instrument."""
    try:
        db_manager = await get_db_manager("database_service")
        client = await db_manager.get_client()
        
        # Check if instrument already exists
        existing = await client.instrument.find_unique(where={"symbol": instrument_data.symbol})
        if existing:
            raise HTTPException(status_code=400, detail="Instrument already exists")
        
        instrument = await client.instrument.create(instrument_data.dict())
        return InstrumentResponse(**instrument.dict())
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create instrument: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/instruments", response_model=List[InstrumentResponse])
async def list_instruments(
    page: int = Query(1, ge=1),
    limit: int = Query(100, ge=1, le=1000),
    exchange: Optional[Exchange] = None,
    instrument_type: Optional[InstrumentType] = None
):
    """List instruments with filtering."""
    try:
        db_manager = await get_db_manager("database_service")
        client = await db_manager.get_client()
        
        skip = (page - 1) * limit
        where_clause = {}
        
        if exchange:
            where_clause["exchange"] = exchange
        if instrument_type:
            where_clause["instrumentType"] = instrument_type
        
        instruments = await client.instrument.find_many(
            where=where_clause,
            skip=skip,
            take=limit,
            order={"symbol": "asc"}
        )
        
        return [InstrumentResponse(**inst.dict()) for inst in instruments]
        
    except Exception as e:
        logger.error(f"Failed to list instruments: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ================================
# MARKET DATA ENDPOINTS
# ================================

@app.post("/market-data", response_model=MarketDataResponse, status_code=status.HTTP_201_CREATED)
async def store_market_data(data: MarketDataCreate):
    """Store market data tick."""
    try:
        db_manager = await get_db_manager("database_service")
        client = await db_manager.get_client()
        
        market_data = await client.marketdata.create(data.dict())
        return MarketDataResponse(**market_data.dict())
        
    except Exception as e:
        logger.error(f"Failed to store market data: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/market-data/bulk", response_model=BaseResponse)
async def store_bulk_market_data(data: BulkMarketDataCreate):
    """Store bulk market data."""
    try:
        db_manager = await get_db_manager("database_service")
        client = await db_manager.get_client()
        
        # Use transaction for bulk insert
        async with db_manager.transaction() as tx:
            for item in data.data:
                await tx.marketdata.create(item.dict())
        
        return BaseResponse(
            message=f"Successfully stored {len(data.data)} market data records"
        )
        
    except Exception as e:
        logger.error(f"Failed to store bulk market data: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/market-data/{instrument_id}", response_model=List[MarketDataResponse])
async def get_market_data(
    instrument_id: str,
    page: int = Query(1, ge=1),
    limit: int = Query(100, ge=1, le=1000),
    from_date: Optional[datetime] = None,
    to_date: Optional[datetime] = None
):
    """Get market data for an instrument."""
    try:
        db_manager = await get_db_manager("database_service")
        client = await db_manager.get_client()
        
        skip = (page - 1) * limit
        where_clause = {"instrumentId": instrument_id}
        
        if from_date or to_date:
            timestamp_filter = {}
            if from_date:
                timestamp_filter["gte"] = from_date
            if to_date:
                timestamp_filter["lte"] = to_date
            where_clause["timestamp"] = timestamp_filter
        
        market_data = await client.marketdata.find_many(
            where=where_clause,
            skip=skip,
            take=limit,
            order={"timestamp": "desc"}
        )
        
        return [MarketDataResponse(**data.dict()) for data in market_data]
        
    except Exception as e:
        logger.error(f"Failed to get market data: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ================================
# ORDER MANAGEMENT ENDPOINTS
# ================================

@app.post("/orders", response_model=OrderResponse, status_code=status.HTTP_201_CREATED)
async def create_order(order_data: OrderCreate, user_id: str = Query(...)):
    """Create a new order."""
    try:
        db_manager = await get_db_manager("database_service")
        client = await db_manager.get_client()
        
        order_dict = order_data.dict()
        order_dict["userId"] = user_id
        
        order = await client.order.create(order_dict)
        
        # Publish order creation event
        await publish_database_event(
            event_type="ORDER_CREATED",
            entity_type="ORDER",
            entity_id=order.id,
            user_id=order.userId,
            data={
                "instrument_id": order.instrumentId,
                "order_type": order.orderType,
                "quantity": order.quantity,
                "price": order.price
            }
        )
        
        return OrderResponse(**order.dict())
        
    except Exception as e:
        logger.error(f"Failed to create order: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/orders", response_model=List[OrderResponse])
async def list_orders(
    user_id: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(100, ge=1, le=1000),
    status_filter: Optional[OrderStatus] = Query(None, alias="status"),
    strategy_id: Optional[str] = None
):
    """List orders with filtering."""
    try:
        db_manager = await get_db_manager("database_service")
        client = await db_manager.get_client()
        
        skip = (page - 1) * limit
        where_clause = {}
        
        if user_id:
            where_clause["userId"] = user_id
        if status_filter:
            where_clause["status"] = status_filter
        if strategy_id:
            where_clause["strategyId"] = strategy_id
        
        orders = await client.order.find_many(
            where=where_clause,
            skip=skip,
            take=limit,
            order={"placedAt": "desc"},
            include={"instrument": True, "strategy": True}
        )
        
        return [OrderResponse(**order.dict()) for order in orders]
        
    except Exception as e:
        logger.error(f"Failed to list orders: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ================================
# STRATEGY ENDPOINTS
# ================================

@app.post("/strategies", response_model=StrategyResponse, status_code=status.HTTP_201_CREATED)
async def create_strategy(strategy_data: StrategyCreate, user_id: str = Query(...)):
    """Create a new strategy."""
    try:
        db_manager = await get_db_manager("database_service")
        client = await db_manager.get_client()
        
        strategy_dict = strategy_data.dict()
        strategy_dict["userId"] = user_id
        
        strategy = await client.strategy.create(strategy_dict)
        return StrategyResponse(**strategy.dict())
        
    except Exception as e:
        logger.error(f"Failed to create strategy: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/trading-signals", response_model=TradingSignalResponse, status_code=status.HTTP_201_CREATED)
async def create_trading_signal(signal_data: TradingSignalCreate):
    """Create a trading signal."""
    try:
        db_manager = await get_db_manager("database_service")
        client = await db_manager.get_client()
        
        signal = await client.tradingsignal.create(signal_data.dict())
        return TradingSignalResponse(**signal.dict())
        
    except Exception as e:
        logger.error(f"Failed to create trading signal: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ================================
# LOGGING ENDPOINTS
# ================================

@app.post("/logs", response_model=BaseResponse, status_code=status.HTTP_201_CREATED)
async def create_log_entry(log_data: SystemLogCreate):
    """Create a system log entry."""
    try:
        db_manager = await get_db_manager("database_service")
        client = await db_manager.get_client()
        
        await client.systemlog.create(log_data.dict())
        return BaseResponse(message="Log entry created successfully")
        
    except Exception as e:
        logger.error(f"Failed to create log entry: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/logs", response_model=List[SystemLogResponse])
async def get_logs(
    service: Optional[str] = None,
    level: Optional[LogLevel] = None,
    page: int = Query(1, ge=1),
    limit: int = Query(100, ge=1, le=1000),
    from_date: Optional[datetime] = None,
    to_date: Optional[datetime] = None
):
    """Get system logs with filtering."""
    try:
        db_manager = await get_db_manager("database_service")
        client = await db_manager.get_client()
        
        skip = (page - 1) * limit
        where_clause = {}
        
        if service:
            where_clause["service"] = service
        if level:
            where_clause["level"] = level
        
        if from_date or to_date:
            timestamp_filter = {}
            if from_date:
                timestamp_filter["gte"] = from_date
            if to_date:
                timestamp_filter["lte"] = to_date
            where_clause["timestamp"] = timestamp_filter
        
        logs = await client.systemlog.find_many(
            where=where_clause,
            skip=skip,
            take=limit,
            order={"timestamp": "desc"}
        )
        
        return [SystemLogResponse(**log.dict()) for log in logs]
        
    except Exception as e:
        logger.error(f"Failed to get logs: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ================================
# MAIN APPLICATION
# ================================

if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8006,
        reload=True,
        log_level="info"
    )
