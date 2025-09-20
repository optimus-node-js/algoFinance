"""
Market Data Models
=================

Pydantic models for market data requests and responses.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, date
from pydantic import BaseModel, Field, validator
from decimal import Decimal
from enum import Enum

from .base import BaseResponse

class Interval(str, Enum):
    """Candle data intervals."""
    ONE_MINUTE = "1minute"
    THREE_MINUTE = "3minute" 
    FIVE_MINUTE = "5minute"
    TEN_MINUTE = "10minute"
    FIFTEEN_MINUTE = "15minute"
    THIRTY_MINUTE = "30minute"
    ONE_HOUR = "1hour"
    ONE_DAY = "1day"

class Exchange(str, Enum):
    """Exchange identifiers."""
    NSE = "NSE"
    BSE = "BSE"
    NFO = "NFO"
    BFO = "BFO"
    CDS = "CDS"
    MCX = "MCX"

class LTPRequest(BaseModel):
    """Request for Live Trading Price data."""
    
    symbol: str = Field(..., description="Trading symbol")
    exchange: Optional[Exchange] = Field(Exchange.NSE, description="Exchange")

class LTPData(BaseModel):
    """Live Trading Price data."""
    
    symbol: str = Field(..., description="Trading symbol")
    ltp: Decimal = Field(..., description="Last traded price")
    change: Decimal = Field(..., description="Price change")
    change_percentage: Decimal = Field(..., description="Percentage change")
    volume: int = Field(..., description="Trading volume")
    open_price: Optional[Decimal] = Field(None, description="Opening price")
    high_price: Optional[Decimal] = Field(None, description="High price")
    low_price: Optional[Decimal] = Field(None, description="Low price")
    close_price: Optional[Decimal] = Field(None, description="Previous close price")
    
    class Config:
        json_encoders = {
            Decimal: lambda v: float(v)
        }

class LTPResponse(BaseResponse):
    """Response for LTP data."""
    
    data: LTPData = Field(..., description="LTP data")

class BulkLTPRequest(BaseModel):
    """Request for bulk LTP data."""
    
    symbols: List[str] = Field(..., min_items=1, max_items=50, description="List of symbols (max 50)")
    exchange: Optional[Exchange] = Field(Exchange.NSE, description="Exchange")

class BulkLTPResponse(BaseResponse):
    """Response for bulk LTP data."""
    
    data: Dict[str, LTPData] = Field(..., description="LTP data by symbol")
    total_symbols: int = Field(..., description="Total symbols requested")
    successful_symbols: int = Field(..., description="Successfully retrieved symbols")

class QuoteData(BaseModel):
    """Enhanced quote data."""
    
    symbol: str = Field(..., description="Trading symbol")
    ltp: Decimal = Field(..., description="Last traded price")
    change: Decimal = Field(..., description="Price change")
    change_percentage: Decimal = Field(..., description="Percentage change")
    volume: int = Field(..., description="Trading volume")
    open_price: Decimal = Field(..., description="Opening price")
    high_price: Decimal = Field(..., description="High price")
    low_price: Decimal = Field(..., description="Low price")
    close_price: Decimal = Field(..., description="Previous close price")
    
    # Market depth
    bid_price: Optional[Decimal] = Field(None, description="Best bid price")
    bid_quantity: Optional[int] = Field(None, description="Best bid quantity")
    ask_price: Optional[Decimal] = Field(None, description="Best ask price")
    ask_quantity: Optional[int] = Field(None, description="Best ask quantity")
    
    # Additional fields
    upper_circuit: Optional[Decimal] = Field(None, description="Upper circuit limit")
    lower_circuit: Optional[Decimal] = Field(None, description="Lower circuit limit")
    
    class Config:
        json_encoders = {
            Decimal: lambda v: float(v)
        }

class QuoteResponse(BaseResponse):
    """Response for quote data."""
    
    data: QuoteData = Field(..., description="Quote data")

class CandleDataRequest(BaseModel):
    """Request for historical candle data."""
    
    symbol: str = Field(..., description="Trading symbol")
    exchange: Exchange = Field(Exchange.NSE, description="Exchange")
    interval: Interval = Field(..., description="Candle interval")
    from_date: date = Field(..., description="Start date")
    to_date: date = Field(..., description="End date")
    
    @validator("to_date")
    def validate_date_range(cls, v, values):
        """Validate date range."""
        if "from_date" in values and v < values["from_date"]:
            raise ValueError("to_date must be after from_date")
        return v

class CandleData(BaseModel):
    """Individual candle data."""
    
    timestamp: datetime = Field(..., description="Candle timestamp")
    open_price: Decimal = Field(..., description="Opening price")
    high_price: Decimal = Field(..., description="High price") 
    low_price: Decimal = Field(..., description="Low price")
    close_price: Decimal = Field(..., description="Closing price")
    volume: int = Field(..., description="Trading volume")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat() + "Z",
            Decimal: lambda v: float(v)
        }

class CandleDataResponse(BaseResponse):
    """Response for candle data."""
    
    symbol: str = Field(..., description="Trading symbol")
    interval: Interval = Field(..., description="Candle interval")
    from_date: date = Field(..., description="Start date")
    to_date: date = Field(..., description="End date")
    candles: List[CandleData] = Field(..., description="Candle data")
    total_candles: int = Field(..., description="Total number of candles")
    
    class Config:
        json_encoders = {
            date: lambda v: v.isoformat()
        }

class InstrumentSearchRequest(BaseModel):
    """Request for instrument search."""
    
    search_text: str = Field(..., min_length=2, description="Search text (minimum 2 characters)")
    exchange: Optional[Exchange] = Field(None, description="Filter by exchange")
    instrument_type: Optional[str] = Field(None, description="Filter by instrument type")

class InstrumentInfo(BaseModel):
    """Instrument information."""
    
    symbol: str = Field(..., description="Trading symbol")
    token: str = Field(..., description="Instrument token")
    exchange: Exchange = Field(..., description="Exchange")
    trading_symbol: str = Field(..., description="Trading symbol")
    instrument_name: str = Field(..., description="Instrument name")
    instrument_type: str = Field(..., description="Instrument type")
    lot_size: int = Field(..., description="Lot size")
    tick_size: Decimal = Field(..., description="Tick size")
    
    class Config:
        json_encoders = {
            Decimal: lambda v: float(v)
        }

class InstrumentSearchResponse(BaseResponse):
    """Response for instrument search."""
    
    search_text: str = Field(..., description="Search text used")
    instruments: List[InstrumentInfo] = Field(..., description="Found instruments")
    total_results: int = Field(..., description="Total search results")

class MarketStatus(BaseModel):
    """Market status information."""
    
    exchange: Exchange = Field(..., description="Exchange")
    market_status: str = Field(..., description="Market status")
    market_type: str = Field(..., description="Market type")
    
class MarketStatusResponse(BaseResponse):
    """Response for market status."""
    
    status: List[MarketStatus] = Field(..., description="Market status by exchange")
    timestamp: datetime = Field(..., description="Status timestamp")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat() + "Z"
        }
