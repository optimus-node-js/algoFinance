"""
Pydantic Models Package
======================

Request and response models for Angel One FastAPI service.
Provides type safety, validation, and automatic documentation.
"""

# Import base models first
from .base import *

# Import specific domain models
from .auth import *
from .trading import *
from .market import *
from .portfolio import *
from .risk import *
from .admin import *

__all__ = [
    # Base models
    "BaseResponse",
    "ErrorResponse", 
    "SuccessResponse",
    
    # Authentication models
    "ConfigureKeysRequest",
    "ConfigureKeysResponse", 
    "AutoLoginResponse",
    "AuthStatusResponse",
    "LogoutResponse",
    
    # Trading models
    "PlaceOrderRequest",
    "PlaceOrderResponse",
    "ModifyOrderRequest", 
    "ModifyOrderResponse",
    "CancelOrderResponse",
    
    # Market data models
    "LTPRequest",
    "LTPResponse",
    "QuoteResponse",
    "CandleDataRequest",
    "CandleDataResponse",
    
    # Portfolio models
    "PositionsResponse",
    "HoldingsResponse",
    "PortfolioSummaryResponse",
    
    # Risk models
    "RMSResponse",
    "MarginCalculationRequest",
    "MarginCalculationResponse",
    
    # Admin models
    "HealthResponse",
    "MetricsResponse",
    "SystemStatsResponse"
]
