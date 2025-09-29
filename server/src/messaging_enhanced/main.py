"""
Messaging Service Main Entry Point
===================================

FastAPI application for the messaging service.
"""

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Create FastAPI app
app = FastAPI(
    title="HFT Messaging Service",
    description="High-Frequency Trading Messaging Service",
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
    return {"status": "healthy", "service": "messaging"}

@app.get("/ping")
async def ping():
    """Simple ping endpoint."""
    return {"message": "pong"}

if __name__ == "__main__":
    uvicorn.run(
        "messaging_enhanced.main:app",
        host="0.0.0.0",
        port=8002,
        reload=False
    )

