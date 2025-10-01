"""
Data Normalizer
===============

Normalizes market data from Angel One API into consistent formats
for Kafka streaming and strategy consumption.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, UTC
import json
from dataclasses import dataclass
from enum import Enum

# Add project root to path for imports
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

import logging
logger = logging.getLogger("data_normalizer")


class DataType(Enum):
    """Market data types"""
    TICK = "tick"
    CANDLE = "candle"
    ORDER_BOOK = "order_book"
    TRADE = "trade"
    POSITION = "position"
    HOLDING = "holding"


@dataclass
class NormalizedTick:
    """Normalized tick data structure"""
    symbol: str
    exchange: str
    token: str
    ltp: float
    open: float
    high: float
    low: float
    close: float
    volume: int
    change: float
    change_percent: float
    timestamp: str
    data_type: str = "tick"


@dataclass
class NormalizedCandle:
    """Normalized candle data structure"""
    symbol: str
    exchange: str
    token: str
    open: float
    high: float
    low: float
    close: float
    volume: int
    timestamp: str
    interval: str  # 1m, 5m, 15m, etc.
    data_type: str = "candle"


@dataclass
class NormalizedOrderBook:
    """Normalized order book data structure"""
    symbol: str
    exchange: str
    bids: List[Dict[str, float]]  # [{"price": 100.0, "quantity": 50}]
    asks: List[Dict[str, float]]  # [{"price": 101.0, "quantity": 25}]
    timestamp: str
    data_type: str = "order_book"


class DataNormalizer:
    """
    Normalizes market data from Angel One API into consistent formats
    for Kafka streaming and strategy consumption.
    """
    
    def __init__(self):
        logger.info("DataNormalizer initialized")
    
    def normalize_ltp_data(self, raw_data: Dict[str, Any], symbol: str, exchange: str = "NSE") -> Optional[NormalizedTick]:
        """
        Normalize LTP data from Angel One API
        
        Args:
            raw_data: Raw LTP data from Angel One API
            symbol: Trading symbol
            exchange: Exchange name
            
        Returns:
            NormalizedTick object or None if normalization fails
        """
        try:
            if not raw_data or "data" not in raw_data:
                return None
                
            data = raw_data["data"]
            
            # Extract values with safe defaults
            ltp = float(data.get("ltp", 0))
            open_price = float(data.get("open", 0))
            high = float(data.get("high", 0))
            low = float(data.get("low", 0))
            close = float(data.get("close", 0))
            volume = int(data.get("volume", 0))
            
            # Calculate change and change percentage
            change = ltp - close if ltp and close else 0
            change_percent = (change / close * 100) if close else 0
            
            return NormalizedTick(
                symbol=symbol,
                exchange=exchange,
                token=str(data.get("token", "")),
                ltp=ltp,
                open=open_price,
                high=high,
                low=low,
                close=close,
                volume=volume,
                change=round(change, 2),
                change_percent=round(change_percent, 2),
                timestamp=datetime.now(UTC).isoformat()
            )
            
        except Exception as e:
            logger.error(f"Failed to normalize LTP data for {symbol}: {e}")
            return None
    
    def normalize_candle_data(self, raw_data: Dict[str, Any], symbol: str, interval: str = "1m", exchange: str = "NSE") -> Optional[NormalizedCandle]:
        """
        Normalize candle data from Angel One API
        
        Args:
            raw_data: Raw candle data from Angel One API
            symbol: Trading symbol
            interval: Candle interval (1m, 5m, 15m, etc.)
            exchange: Exchange name
            
        Returns:
            NormalizedCandle object or None if normalization fails
        """
        try:
            if not raw_data or "data" not in raw_data:
                return None
                
            data = raw_data["data"]
            
            # Handle both single candle and array of candles
            if isinstance(data, list) and data:
                # Take the latest candle
                candle_data = data[-1]
            elif isinstance(data, dict):
                candle_data = data
            else:
                return None
            
            return NormalizedCandle(
                symbol=symbol,
                exchange=exchange,
                token=str(candle_data.get("token", "")),
                open=float(candle_data.get("open", 0)),
                high=float(candle_data.get("high", 0)),
                low=float(candle_data.get("low", 0)),
                close=float(candle_data.get("close", 0)),
                volume=int(candle_data.get("volume", 0)),
                timestamp=candle_data.get("timestamp", datetime.now(UTC).isoformat()),
                interval=interval
            )
            
        except Exception as e:
            logger.error(f"Failed to normalize candle data for {symbol}: {e}")
            return None
    
    def normalize_order_book_data(self, raw_data: Dict[str, Any], symbol: str, exchange: str = "NSE") -> Optional[NormalizedOrderBook]:
        """
        Normalize order book data from Angel One API
        
        Args:
            raw_data: Raw order book data from Angel One API
            symbol: Trading symbol
            exchange: Exchange name
            
        Returns:
            NormalizedOrderBook object or None if normalization fails
        """
        try:
            if not raw_data or "data" not in raw_data:
                return None
                
            data = raw_data["data"]
            
            # Extract bids and asks
            bids = []
            asks = []
            
            if "bids" in data:
                for bid in data["bids"]:
                    bids.append({
                        "price": float(bid.get("price", 0)),
                        "quantity": float(bid.get("quantity", 0))
                    })
            
            if "asks" in data:
                for ask in data["asks"]:
                    asks.append({
                        "price": float(ask.get("price", 0)),
                        "quantity": float(ask.get("quantity", 0))
                    })
            
            return NormalizedOrderBook(
                symbol=symbol,
                exchange=exchange,
                bids=bids,
                asks=asks,
                timestamp=datetime.now(UTC).isoformat()
            )
            
        except Exception as e:
            logger.error(f"Failed to normalize order book data for {symbol}: {e}")
            return None
    
    def to_dict(self, normalized_data) -> Dict[str, Any]:
        """
        Convert normalized data object to dictionary for JSON serialization
        
        Args:
            normalized_data: NormalizedTick, NormalizedCandle, or NormalizedOrderBook
            
        Returns:
            Dictionary representation of the data
        """
        try:
            if hasattr(normalized_data, '__dict__'):
                return normalized_data.__dict__
            else:
                return dict(normalized_data)
        except Exception as e:
            logger.error(f"Failed to convert normalized data to dict: {e}")
            return {}
    
    def to_json(self, normalized_data) -> str:
        """
        Convert normalized data object to JSON string
        
        Args:
            normalized_data: NormalizedTick, NormalizedCandle, or NormalizedOrderBook
            
        Returns:
            JSON string representation of the data
        """
        try:
            return json.dumps(self.to_dict(normalized_data), default=str)
        except Exception as e:
            logger.error(f"Failed to convert normalized data to JSON: {e}")
            return "{}"
    
    def validate_data(self, normalized_data) -> bool:
        """
        Validate normalized data for completeness and correctness
        
        Args:
            normalized_data: NormalizedTick, NormalizedCandle, or NormalizedOrderBook
            
        Returns:
            True if data is valid, False otherwise
        """
        try:
            if not normalized_data:
                return False
            
            # Check required fields based on data type
            if isinstance(normalized_data, NormalizedTick):
                return (
                    normalized_data.symbol and
                    normalized_data.exchange and
                    normalized_data.ltp >= 0 and
                    normalized_data.timestamp
                )
            elif isinstance(normalized_data, NormalizedCandle):
                return (
                    normalized_data.symbol and
                    normalized_data.exchange and
                    normalized_data.open >= 0 and
                    normalized_data.high >= 0 and
                    normalized_data.low >= 0 and
                    normalized_data.close >= 0 and
                    normalized_data.timestamp
                )
            elif isinstance(normalized_data, NormalizedOrderBook):
                return (
                    normalized_data.symbol and
                    normalized_data.exchange and
                    normalized_data.timestamp and
                    (normalized_data.bids or normalized_data.asks)
                )
            
            return False
            
        except Exception as e:
            logger.error(f"Failed to validate normalized data: {e}")
            return False


# Example usage and testing
if __name__ == "__main__":
    normalizer = DataNormalizer()
    
    # Test LTP normalization
    sample_ltp = {
        "data": {
            "token": "99926000",
            "ltp": 22150.50,
            "open": 22100.00,
            "high": 22200.00,
            "low": 22050.00,
            "close": 22120.00,
            "volume": 1500000
        }
    }
    
    normalized_tick = normalizer.normalize_ltp_data(sample_ltp, "NIFTY", "NSE")
    if normalized_tick:
        print("✅ LTP Normalization successful:")
        print(f"   Symbol: {normalized_tick.symbol}")
        print(f"   LTP: {normalized_tick.ltp}")
        print(f"   Change: {normalized_tick.change} ({normalized_tick.change_percent}%)")
        print(f"   JSON: {normalizer.to_json(normalized_tick)}")
    else:
        print("❌ LTP Normalization failed")
