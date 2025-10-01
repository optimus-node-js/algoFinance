"""
Caching Service Main Entry Point
=================================

FastAPI application for the caching service with Kafka health monitoring.
"""

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

# Import Kafka for health monitoring
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent / "messaging_enhanced"))

try:
    from messaging_enhanced.kafka import KafkaManager
    from messaging_enhanced.kafka.kafka_manager import get_kafka_manager, close_kafka_manager
    KAFKA_AVAILABLE = True
except ImportError as e:
    print(f"⚠️ Kafka not available for health monitoring: {e}")
    KAFKA_AVAILABLE = False

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management."""
    # Startup
    if KAFKA_AVAILABLE:
        try:
            kafka_manager = get_kafka_manager()
            app.state.kafka_manager = kafka_manager
            print("✅ Kafka health monitoring initialized")
        except Exception as e:
            print(f"⚠️ Failed to initialize Kafka health monitoring: {e}")
    
    yield
    
    # Shutdown
    if KAFKA_AVAILABLE and hasattr(app.state, 'kafka_manager'):
        try:
            await close_kafka_manager()
            print("✅ Kafka connections closed")
        except Exception as e:
            print(f"⚠️ Error closing Kafka connections: {e}")

# Create FastAPI app
app = FastAPI(
    title="HFT Caching Service",
    description="High-Frequency Trading Caching Service with Kafka Integration",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
async def health_check():
    """Health check endpoint with Kafka status."""
    health_status = {
        "status": "healthy",
        "service": "caching",
        "kafka_available": KAFKA_AVAILABLE
    }
    
    if KAFKA_AVAILABLE and hasattr(app.state, 'kafka_manager'):
        try:
            # Check Kafka connection health
            kafka_health = await app.state.kafka_manager.health_check()
            health_status["kafka_status"] = "connected" if kafka_health else "disconnected"
        except Exception as e:
            health_status["kafka_status"] = f"error: {str(e)}"
    else:
        health_status["kafka_status"] = "not_configured"
    
    return health_status

@app.get("/ping")
async def ping():
    """Simple ping endpoint."""
    return {"message": "pong"}

if __name__ == "__main__":
    uvicorn.run(
        "caching_service.main:app",
        host="0.0.0.0",
        port=8001,
        reload=False
    )

