"""
Risk Management Models
=====================

Pydantic models for risk management requests and responses.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime
from pydantic import BaseModel, Field
from decimal import Decimal
from enum import Enum

from .base import BaseResponse

class RMSLimits(BaseModel):
    """Risk Management System limits."""
    
    # Cash limits
    available_cash: Decimal = Field(..., description="Available cash")
    used_cash: Decimal = Field(..., description="Used cash")
    
    # Margin limits  
    available_margin: Decimal = Field(..., description="Available margin")
    used_margin: Decimal = Field(..., description="Used margin")
    
    # Position limits
    gross_exposure: Decimal = Field(..., description="Gross exposure")
    net_exposure: Decimal = Field(..., description="Net exposure")
    
    # Limits
    exposure_limit: Decimal = Field(..., description="Total exposure limit")
    margin_limit: Decimal = Field(..., description="Margin limit")
    
    class Config:
        json_encoders = {
            Decimal: lambda v: float(v)
        }

class RMSResponse(BaseResponse):
    """Response for RMS limits."""
    
    limits: RMSLimits = Field(..., description="RMS limits and usage")
    last_updated: datetime = Field(..., description="Last update timestamp")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat() + "Z"
        }

class MarginCalculationRequest(BaseModel):
    """Request for margin calculation."""
    
    positions: List[Dict[str, Any]] = Field(..., description="List of positions for margin calculation")

class MarginBreakup(BaseModel):
    """Margin breakup details."""
    
    symbol: str = Field(..., description="Trading symbol")
    quantity: int = Field(..., description="Position quantity")
    
    # Margin components
    span_margin: Decimal = Field(..., description="SPAN margin")
    exposure_margin: Decimal = Field(..., description="Exposure margin")
    premium_margin: Decimal = Field(..., description="Premium margin")
    additional_margin: Decimal = Field(..., description="Additional margin")
    
    # Total margin
    total_margin: Decimal = Field(..., description="Total margin required")
    
    class Config:
        json_encoders = {
            Decimal: lambda v: float(v)
        }

class MarginCalculationResponse(BaseResponse):
    """Response for margin calculation."""
    
    margins: List[MarginBreakup] = Field(..., description="Margin breakup by position")
    total_margin_required: Decimal = Field(..., description="Total margin required")
    available_margin: Decimal = Field(..., description="Available margin")
    margin_shortfall: Decimal = Field(..., description="Margin shortfall if any")
    
    class Config:
        json_encoders = {
            Decimal: lambda v: float(v)
        }

class RiskAlert(BaseModel):
    """Risk alert information."""
    
    alert_id: str = Field(..., description="Alert identifier")
    alert_type: str = Field(..., description="Type of alert")
    severity: str = Field(..., description="Alert severity")
    message: str = Field(..., description="Alert message")
    symbol: Optional[str] = Field(None, description="Related symbol")
    threshold_value: Optional[Decimal] = Field(None, description="Threshold that triggered alert")
    current_value: Optional[Decimal] = Field(None, description="Current value")
    timestamp: datetime = Field(..., description="Alert timestamp")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat() + "Z",
            Decimal: lambda v: float(v)
        }

class RiskAlertsResponse(BaseResponse):
    """Response for risk alerts."""
    
    alerts: List[RiskAlert] = Field(..., description="List of active risk alerts")
    total_alerts: int = Field(..., description="Total number of alerts")
    critical_alerts: int = Field(..., description="Number of critical alerts")
    warning_alerts: int = Field(..., description="Number of warning alerts")

class RiskProfile(BaseModel):
    """User risk profile information."""
    
    risk_category: str = Field(..., description="Risk category")
    max_position_size: Decimal = Field(..., description="Maximum position size")
    max_daily_loss: Decimal = Field(..., description="Maximum daily loss limit")
    max_portfolio_value: Decimal = Field(..., description="Maximum portfolio value")
    
    # Risk settings
    stop_loss_mandatory: bool = Field(..., description="Whether stop loss is mandatory")
    intraday_squareoff_time: Optional[str] = Field(None, description="Auto square-off time")
    
    class Config:
        json_encoders = {
            Decimal: lambda v: float(v)
        }

class RiskProfileResponse(BaseResponse):
    """Response for risk profile."""
    
    profile: RiskProfile = Field(..., description="Risk profile settings")
    last_updated: datetime = Field(..., description="Last update timestamp")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat() + "Z"
        }



