"""
Trading Models
=============

Pydantic models for trading-related requests and responses.
"""

from typing import Dict, Any, List, Optional, Literal
from datetime import datetime
from pydantic import BaseModel, Field, validator
from decimal import Decimal
from enum import Enum

from .base import BaseResponse

class TransactionType(str, Enum):
    """Transaction types for orders."""
    BUY = "BUY"
    SELL = "SELL"

class OrderType(str, Enum):
    """Order types."""
    MARKET = "MARKET"
    LIMIT = "LIMIT"
    SLM = "SLM"  # Stop Loss Market
    SL = "SL"    # Stop Loss

class ProductType(str, Enum):
    """Product types."""
    INTRADAY = "INTRADAY"
    DELIVERY = "DELIVERY"
    MARGIN = "MARGIN"
    BO = "BO"  # Bracket Order
    CO = "CO"  # Cover Order

class Validity(str, Enum):
    """Order validity."""
    DAY = "DAY"
    IOC = "IOC"  # Immediate or Cancel
    GTD = "GTD"  # Good Till Date

class Variety(str, Enum):
    """Order variety."""
    NORMAL = "NORMAL"
    STOPLOSS = "STOPLOSS"
    AMO = "AMO"  # After Market Order
    ROBO = "ROBO"

class OrderStatus(str, Enum):
    """Order status values."""
    PENDING = "PENDING"
    OPEN = "OPEN"
    COMPLETE = "COMPLETE"
    CANCELLED = "CANCELLED"
    REJECTED = "REJECTED"
    MODIFIED = "MODIFIED"

class PlaceOrderRequest(BaseModel):
    """Request model for placing orders."""
    
    symbol: str = Field(..., description="Trading symbol (e.g., RELIANCE)")
    quantity: int = Field(..., gt=0, description="Order quantity")
    transaction_type: TransactionType = Field(..., description="Buy or Sell")
    order_type: OrderType = Field(..., description="Order type")
    product: ProductType = Field(..., description="Product type")
    
    price: Optional[Decimal] = Field(None, gt=0, description="Order price (required for LIMIT orders)")
    trigger_price: Optional[Decimal] = Field(None, gt=0, description="Trigger price (for SL/SLM orders)")
    disclosed_quantity: Optional[int] = Field(None, ge=0, description="Disclosed quantity")
    validity: Validity = Field(Validity.DAY, description="Order validity")
    variety: Variety = Field(Variety.NORMAL, description="Order variety")
    
    @validator("price")
    def validate_price_for_limit_orders(cls, v, values):
        """Validate price for limit orders."""
        if values.get("order_type") in [OrderType.LIMIT, OrderType.SL] and v is None:
            raise ValueError("Price is required for LIMIT and SL orders")
        return v
    
    @validator("trigger_price") 
    def validate_trigger_price(cls, v, values):
        """Validate trigger price for stop loss orders."""
        if values.get("order_type") in [OrderType.SLM, OrderType.SL] and v is None:
            raise ValueError("Trigger price is required for SLM and SL orders")
        return v

class PlaceOrderResponse(BaseResponse):
    """Response model for order placement."""
    
    order_id: Optional[str] = Field(None, description="Generated order ID")
    status: Optional[OrderStatus] = Field(None, description="Order status")

class ModifyOrderRequest(BaseModel):
    """Request model for modifying orders."""
    
    quantity: Optional[int] = Field(None, gt=0, description="New quantity")
    price: Optional[Decimal] = Field(None, gt=0, description="New price")
    trigger_price: Optional[Decimal] = Field(None, gt=0, description="New trigger price")
    disclosed_quantity: Optional[int] = Field(None, ge=0, description="New disclosed quantity")
    validity: Optional[Validity] = Field(None, description="New validity")

class ModifyOrderResponse(BaseResponse):
    """Response model for order modification."""
    
    order_id: str = Field(..., description="Modified order ID")
    status: Optional[OrderStatus] = Field(None, description="Order status after modification")

class CancelOrderResponse(BaseResponse):
    """Response model for order cancellation."""
    
    order_id: str = Field(..., description="Cancelled order ID")
    status: Optional[OrderStatus] = Field(None, description="Order status after cancellation")

class OrderDetails(BaseModel):
    """Detailed order information."""
    
    order_id: str = Field(..., description="Order ID")
    symbol: str = Field(..., description="Trading symbol")
    quantity: int = Field(..., description="Order quantity")
    filled_quantity: int = Field(0, description="Filled quantity")
    pending_quantity: int = Field(0, description="Pending quantity")
    transaction_type: TransactionType = Field(..., description="Buy or Sell")
    order_type: OrderType = Field(..., description="Order type")
    product: ProductType = Field(..., description="Product type")
    status: OrderStatus = Field(..., description="Order status")
    price: Optional[Decimal] = Field(None, description="Order price")
    trigger_price: Optional[Decimal] = Field(None, description="Trigger price")
    average_price: Optional[Decimal] = Field(None, description="Average execution price")
    order_time: datetime = Field(..., description="Order placement time")
    exchange_time: Optional[datetime] = Field(None, description="Exchange timestamp")
    validity: Validity = Field(..., description="Order validity")
    variety: Variety = Field(..., description="Order variety")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat() + "Z",
            Decimal: lambda v: float(v)
        }

class OrderBookResponse(BaseResponse):
    """Response model for order book."""
    
    orders: List[OrderDetails] = Field(..., description="List of orders")
    total_orders: int = Field(..., description="Total number of orders")

class TradeDetails(BaseModel):
    """Detailed trade information."""
    
    trade_id: str = Field(..., description="Trade ID")
    order_id: str = Field(..., description="Related order ID")
    symbol: str = Field(..., description="Trading symbol")
    quantity: int = Field(..., description="Trade quantity")
    price: Decimal = Field(..., description="Trade price")
    transaction_type: TransactionType = Field(..., description="Buy or Sell")
    product: ProductType = Field(..., description="Product type")
    trade_time: datetime = Field(..., description="Trade execution time")
    exchange_time: Optional[datetime] = Field(None, description="Exchange timestamp")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat() + "Z",
            Decimal: lambda v: float(v)
        }

class TradeBookResponse(BaseResponse):
    """Response model for trade book."""
    
    trades: List[TradeDetails] = Field(..., description="List of trades")
    total_trades: int = Field(..., description="Total number of trades")

class PositionDetails(BaseModel):
    """Position information."""
    
    symbol: str = Field(..., description="Trading symbol")
    product: ProductType = Field(..., description="Product type")
    quantity: int = Field(..., description="Position quantity")
    average_price: Decimal = Field(..., description="Average buy/sell price")
    last_price: Decimal = Field(..., description="Last traded price")
    pnl: Decimal = Field(..., description="Profit and Loss")
    pnl_percentage: Decimal = Field(..., description="P&L percentage")
    
    class Config:
        json_encoders = {
            Decimal: lambda v: float(v)
        }

class PositionsResponse(BaseResponse):
    """Response model for positions."""
    
    positions: List[PositionDetails] = Field(..., description="List of positions")
    total_positions: int = Field(..., description="Total number of positions")
    net_pnl: Decimal = Field(..., description="Net P&L across all positions")
    
    class Config:
        json_encoders = {
            Decimal: lambda v: float(v)
        }
