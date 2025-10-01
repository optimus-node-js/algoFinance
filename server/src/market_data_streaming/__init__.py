"""
Real-Time Market Data Streaming System
=====================================

Unified market data streaming system that:
- Uses Kafka infrastructure for streaming
- Provides WebSocket endpoints for UI
- Normalizes data formats for consistency
- Integrates with Angel One API
"""

from .data_normalizer import DataNormalizer
from .websocket_market_manager import WebSocketMarketManager

__all__ = [
    "DataNormalizer",
    "WebSocketMarketManager"
]
