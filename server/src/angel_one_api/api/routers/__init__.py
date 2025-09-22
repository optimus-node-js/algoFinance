"""
API Routers Package
==================

FastAPI routers for Angel One trading operations.
Organized by functional areas for maintainability.
"""

# Import all routers for easy access
from . import (
    health,
    authentication,
    trading,
    market_data,
    portfolio,
    risk,
    advanced,
    admin,
    websockets
)

__all__ = [
    "health",
    "authentication", 
    "trading",
    "market_data",
    "portfolio",
    "risk",
    "advanced",
    "admin",
    "websockets"
]



