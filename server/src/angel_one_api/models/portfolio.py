"""
Portfolio Models
===============

Pydantic models for portfolio-related requests and responses.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, date
from pydantic import BaseModel, Field
from decimal import Decimal
from enum import Enum

from .base import BaseResponse

class HoldingDetails(BaseModel):
    """Individual holding information."""
    
    symbol: str = Field(..., description="Trading symbol")
    quantity: int = Field(..., description="Total quantity held")
    average_price: Decimal = Field(..., description="Average buy price")
    last_price: Decimal = Field(..., description="Current market price")
    pnl: Decimal = Field(..., description="Unrealized P&L")
    pnl_percentage: Decimal = Field(..., description="P&L percentage")
    day_change: Decimal = Field(..., description="Day's change")
    day_change_percentage: Decimal = Field(..., description="Day's change percentage")
    
    # Additional details
    invested_value: Decimal = Field(..., description="Total invested amount")
    current_value: Decimal = Field(..., description="Current market value")
    exchange: str = Field(..., description="Exchange")
    isin: Optional[str] = Field(None, description="ISIN code")
    
    class Config:
        json_encoders = {
            Decimal: lambda v: float(v)
        }

class HoldingsResponse(BaseResponse):
    """Response for holdings data."""
    
    holdings: List[HoldingDetails] = Field(..., description="List of holdings")
    total_holdings: int = Field(..., description="Total number of holdings")
    total_invested_value: Decimal = Field(..., description="Total invested amount")
    total_current_value: Decimal = Field(..., description="Total current value")
    total_pnl: Decimal = Field(..., description="Total unrealized P&L")
    total_pnl_percentage: Decimal = Field(..., description="Total P&L percentage")
    
    class Config:
        json_encoders = {
            Decimal: lambda v: float(v)
        }

class PositionDetails(BaseModel):
    """Position information."""
    
    symbol: str = Field(..., description="Trading symbol")
    product: str = Field(..., description="Product type")
    quantity: int = Field(..., description="Net quantity")
    buy_quantity: int = Field(0, description="Buy quantity")
    sell_quantity: int = Field(0, description="Sell quantity")
    average_price: Decimal = Field(..., description="Average price")
    last_price: Decimal = Field(..., description="Current market price")
    pnl: Decimal = Field(..., description="Realized + Unrealized P&L")
    realized_pnl: Decimal = Field(..., description="Realized P&L")
    unrealized_pnl: Decimal = Field(..., description="Unrealized P&L")
    
    class Config:
        json_encoders = {
            Decimal: lambda v: float(v)
        }

class PositionsResponse(BaseResponse):
    """Response for positions data."""
    
    positions: List[PositionDetails] = Field(..., description="List of positions")
    total_positions: int = Field(..., description="Total number of positions")
    net_pnl: Decimal = Field(..., description="Net P&L across all positions")
    realized_pnl: Decimal = Field(..., description="Total realized P&L")
    unrealized_pnl: Decimal = Field(..., description="Total unrealized P&L")
    
    class Config:
        json_encoders = {
            Decimal: lambda v: float(v)
        }

class PortfolioSummary(BaseModel):
    """Portfolio summary information."""
    
    # Holdings summary
    total_holdings: int = Field(..., description="Total number of holdings")
    holdings_value: Decimal = Field(..., description="Total holdings value")
    holdings_pnl: Decimal = Field(..., description="Holdings P&L")
    holdings_pnl_percentage: Decimal = Field(..., description="Holdings P&L percentage")
    
    # Positions summary
    total_positions: int = Field(..., description="Total number of positions")
    positions_pnl: Decimal = Field(..., description="Positions P&L")
    
    # Overall summary
    net_worth: Decimal = Field(..., description="Total net worth")
    available_margin: Decimal = Field(..., description="Available margin")
    used_margin: Decimal = Field(..., description="Used margin")
    
    # Performance metrics
    day_change: Decimal = Field(..., description="Day's portfolio change")
    day_change_percentage: Decimal = Field(..., description="Day's change percentage")
    
    class Config:
        json_encoders = {
            Decimal: lambda v: float(v)
        }

class PortfolioSummaryResponse(BaseResponse):
    """Response for portfolio summary."""
    
    summary: PortfolioSummary = Field(..., description="Portfolio summary")
    last_updated: datetime = Field(..., description="Last update timestamp")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat() + "Z"
        }

class PerformanceMetrics(BaseModel):
    """Portfolio performance metrics."""
    
    # Return metrics
    total_return: Decimal = Field(..., description="Total return amount")
    total_return_percentage: Decimal = Field(..., description="Total return percentage")
    annualized_return: Decimal = Field(..., description="Annualized return percentage")
    
    # Risk metrics
    volatility: Decimal = Field(..., description="Portfolio volatility")
    sharpe_ratio: Optional[Decimal] = Field(None, description="Sharpe ratio")
    max_drawdown: Optional[Decimal] = Field(None, description="Maximum drawdown")
    
    # Activity metrics
    total_trades: int = Field(..., description="Total number of trades")
    winning_trades: int = Field(..., description="Number of winning trades")
    losing_trades: int = Field(..., description="Number of losing trades")
    win_rate: Decimal = Field(..., description="Win rate percentage")
    
    class Config:
        json_encoders = {
            Decimal: lambda v: float(v)
        }

class PerformanceResponse(BaseResponse):
    """Response for performance metrics."""
    
    metrics: PerformanceMetrics = Field(..., description="Performance metrics")
    period_start: date = Field(..., description="Analysis period start")
    period_end: date = Field(..., description="Analysis period end")
    
    class Config:
        json_encoders = {
            date: lambda v: v.isoformat()
        }
