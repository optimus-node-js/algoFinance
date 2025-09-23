#!/usr/bin/env python3
"""
Simple Angel One API Test
========================

Minimal FastAPI service to test basic functionality and identify startup issues.
"""

from fastapi import FastAPI
import uvicorn
import sys
from pathlib import Path

# Add server/src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Create simple FastAPI app
app = FastAPI(
    title="Angel One API Test",
    description="Simple test version of Angel One API",
    version="1.0.0"
)

@app.get("/")
async def root():
    return {"message": "Angel One API Test is working!", "status": "healthy"}

@app.get("/ping")
async def ping():
    return {"status": "pong", "service": "angel-one-test", "version": "1.0.0"}

@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "service": "angel-one-api-test",
        "version": "1.0.0",
        "dependencies": {
            "redis": "not_tested",
            "kafka": "not_tested"
        }
    }

if __name__ == "__main__":
    print("🚀 Starting Simple Angel One API Test...")
    print("📊 Available endpoints:")
    print("   • GET / - Root endpoint")
    print("   • GET /ping - Ping endpoint")
    print("   • GET /health - Health check")
    print("🌐 Server will be available at: http://localhost:8000")
    print("📚 API docs: http://localhost:8000/docs")
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info"
    )

