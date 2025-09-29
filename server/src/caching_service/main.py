"""
Caching Service Main Entry Point
=================================

FastAPI application for the caching service.
"""

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Create FastAPI app
app = FastAPI(
    title="HFT Caching Service",
    description="High-Frequency Trading Caching Service",
    version="1.0.0"
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
    """Health check endpoint."""
    return {"status": "healthy", "service": "caching"}

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

