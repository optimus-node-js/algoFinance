"""
AI Intelligence Service - Main FastAPI Application
=================================================

Advanced AI/ML service for sentiment analysis and trading signal generation.
Processes news data and generates actionable trading signals for the HFT system.
"""

import asyncio
import logging
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional

from fastapi import FastAPI, HTTPException, BackgroundTasks, Depends
from fastapi.responses import JSONResponse
import uvicorn

# Core infrastructure imports
from messaging_enhanced.kafka import KafkaManager, SentimentProducer
from caching_service.redis_manager import RedisManager
from database_service.prisma_client import PrismaService

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Global service instances
kafka_manager: Optional[KafkaManager] = None
sentiment_producer: Optional[SentimentProducer] = None
redis_manager: Optional[RedisManager] = None
prisma_service: Optional[PrismaService] = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """FastAPI lifespan events for startup and shutdown."""
    global kafka_manager, sentiment_producer, redis_manager, prisma_service
    
    logger.info("Starting AI Intelligence Service...")
    
    try:
        # Initialize Kafka Manager
        kafka_manager = KafkaManager()
        await kafka_manager.start()
        
        # Create AI/ML specific Kafka topics
        ai_topics = [
            "hft-ai-sentiment-analysis",      # Sentiment analysis results
            "hft-ai-trading-signals",         # Generated trading signals
            "hft-ai-model-health",            # Model performance metrics
            "hft-ai-predictions",             # ML predictions
            "hft-ai-feedback"                 # Model feedback loop
        ]
        
        for topic in ai_topics:
            await kafka_manager.create_topic(topic, num_partitions=3, replication_factor=1)
        
        # Initialize Sentiment Producer
        sentiment_producer = SentimentProducer(kafka_manager)
        await sentiment_producer.start()
        
        # Initialize Redis Manager for ML caching
        redis_manager = RedisManager()
        await redis_manager.connect()
        
        # Initialize Database Service connection
        prisma_service = PrismaService()
        await prisma_service.connect()
        
        logger.info("✅ AI Intelligence Service started successfully")
        
        # Publish startup event
        if sentiment_producer:
            await sentiment_producer.send_sentiment_event({
                "event_type": "service_started",
                "service": "ai_intelligence_service",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "status": "healthy"
            })
        
    except Exception as e:
        logger.error(f"❌ Failed to start AI Intelligence Service: {e}")
        raise
    
    yield
    
    # Shutdown
    logger.info("Shutting down AI Intelligence Service...")
    
    try:
        # Publish shutdown event
        if sentiment_producer:
            await sentiment_producer.send_sentiment_event({
                "event_type": "service_stopping",
                "service": "ai_intelligence_service",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "status": "shutting_down"
            })
        
        # Close all connections
        if sentiment_producer:
            await sentiment_producer.close()
        
        if kafka_manager:
            await kafka_manager.close()
        
        if redis_manager:
            await redis_manager.close()
        
        if prisma_service:
            await prisma_service.disconnect()
        
        logger.info("✅ AI Intelligence Service shutdown complete")
        
    except Exception as e:
        logger.error(f"❌ Error during shutdown: {e}")

# Create FastAPI app
app = FastAPI(
    title="AI Intelligence Service",
    description="Advanced AI/ML service for financial sentiment analysis and trading signals",
    version="1.0.0",
    lifespan=lifespan
)

# Dependency to get services
async def get_services():
    """Dependency to get all service instances."""
    return {
        "kafka_manager": kafka_manager,
        "sentiment_producer": sentiment_producer,
        "redis_manager": redis_manager,
        "prisma_service": prisma_service
    }

@app.get("/health")
async def health_check(services: dict = Depends(get_services)):
    """Health check endpoint."""
    health_status = {
        "service": "ai_intelligence_service",
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "components": {}
    }
    
    # Check Kafka
    if services["kafka_manager"]:
        try:
            kafka_stats = await services["kafka_manager"].get_stats()
            health_status["components"]["kafka"] = {
                "status": "healthy",
                "stats": kafka_stats
            }
        except Exception as e:
            health_status["components"]["kafka"] = {
                "status": "unhealthy",
                "error": str(e)
            }
            health_status["status"] = "degraded"
    
    # Check Redis
    if services["redis_manager"]:
        try:
            redis_info = await services["redis_manager"].get_info()
            health_status["components"]["redis"] = {
                "status": "healthy",
                "info": redis_info
            }
        except Exception as e:
            health_status["components"]["redis"] = {
                "status": "unhealthy",
                "error": str(e)
            }
            health_status["status"] = "degraded"
    
    # Check Database
    if services["prisma_service"]:
        try:
            db_health = await services["prisma_service"].health_check()
            health_status["components"]["database"] = {
                "status": "healthy" if db_health["healthy"] else "unhealthy",
                "stats": db_health
            }
            if not db_health["healthy"]:
                health_status["status"] = "degraded"
        except Exception as e:
            health_status["components"]["database"] = {
                "status": "unhealthy",
                "error": str(e)
            }
            health_status["status"] = "degraded"
    
    return health_status

@app.post("/analyze/sentiment")
async def analyze_sentiment(
    text: str,
    company_symbol: Optional[str] = None,
    services: dict = Depends(get_services)
):
    """Analyze sentiment of provided text using FinBERT model."""
    
    # TODO: Implement FinBERT sentiment analysis
    # Placeholder response for now
    
    return {
        "status": "success",
        "text": text[:100] + "..." if len(text) > 100 else text,
        "company_symbol": company_symbol,
        "sentiment": {
            "score": 0.0,  # Placeholder: -1.0 to 1.0
            "label": "neutral",  # Placeholder: positive/negative/neutral
            "confidence": 0.0  # Placeholder: 0.0 to 1.0
        },
        "message": "FinBERT model not yet implemented - Week 3 deliverable"
    }

@app.post("/signals/generate")
async def generate_trading_signals(
    sentiment_data: Dict[str, Any],
    services: dict = Depends(get_services)
):
    """Generate trading signals from sentiment analysis results."""
    
    # TODO: Implement trading signal generation
    # Placeholder response for now
    
    return {
        "status": "success",
        "sentiment_data": sentiment_data,
        "signals": [],  # Placeholder: Will contain trading signals
        "message": "Signal generation not yet implemented - Week 4 deliverable"
    }

@app.get("/models/status")
async def get_model_status(services: dict = Depends(get_services)):
    """Get status of all AI/ML models."""
    
    return {
        "service": "ai_intelligence_service",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "models": {
            "finbert_sentiment": {
                "status": "not_loaded",
                "version": "1.0.0",
                "last_updated": None,
                "performance_metrics": {}
            },
            "signal_generator": {
                "status": "not_implemented",
                "version": "1.0.0",
                "last_updated": None,
                "performance_metrics": {}
            }
        }
    }

@app.get("/stats")
async def get_service_stats(services: dict = Depends(get_services)):
    """Get comprehensive AI service statistics."""
    
    stats = {
        "service": "ai_intelligence_service",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "components": {
            "ml_models": {
                "loaded_models": 0,
                "total_predictions": 0,
                "average_latency_ms": 0.0,
                "cache_hit_rate": 0.0
            },
            "signal_generation": {
                "signals_generated": 0,
                "successful_signals": 0,
                "signal_accuracy": 0.0
            }
        }
    }
    
    # Add Kafka stats
    if services["kafka_manager"]:
        try:
            stats["components"]["kafka"] = await services["kafka_manager"].get_stats()
        except Exception as e:
            stats["components"]["kafka"] = {"error": str(e)}
    
    # Add Redis stats
    if services["redis_manager"]:
        try:
            stats["components"]["redis"] = await services["redis_manager"].get_stats()
        except Exception as e:
            stats["components"]["redis"] = {"error": str(e)}
    
    return stats

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8011,
        reload=True,
        log_level="info"
    )
