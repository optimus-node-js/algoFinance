"""
Database Models and Schemas
===========================

Pydantic models for API requests/responses and data validation.
These complement the Prisma schema for type-safe operations.
"""

from typing import Optional, List, Dict, Any, Union
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field, validator


# ================================
# ENUMS (matching Prisma schema)
# ================================

class UserRole(str, Enum):
    ADMIN = "ADMIN"
    TRADER = "TRADER"
    ANALYST = "ANALYST"
    VIEWER = "VIEWER"


class Exchange(str, Enum):
    NSE = "NSE"
    BSE = "BSE"
    MCX = "MCX"
    NCDEX = "NCDEX"


class InstrumentType(str, Enum):
    EQUITY = "EQUITY"
    FUTURES = "FUTURES"
    OPTIONS = "OPTIONS"
    COMMODITY = "COMMODITY"
    CURRENCY = "CURRENCY"
    INDEX = "INDEX"


class OrderType(str, Enum):
    MARKET = "MARKET"
    LIMIT = "LIMIT"
    STOP_LOSS = "STOP_LOSS"
    STOP_LOSS_MARKET = "STOP_LOSS_MARKET"
    BRACKET = "BRACKET"
    COVER = "COVER"


class TransactionType(str, Enum):
    BUY = "BUY"
    SELL = "SELL"


class OrderStatus(str, Enum):
    PENDING = "PENDING"
    OPEN = "OPEN"
    COMPLETE = "COMPLETE"
    CANCELLED = "CANCELLED"
    REJECTED = "REJECTED"
    MODIFIED = "MODIFIED"
    PARTIALLY_FILLED = "PARTIALLY_FILLED"


class StrategyType(str, Enum):
    MOMENTUM = "MOMENTUM"
    MEAN_REVERSION = "MEAN_REVERSION"
    ARBITRAGE = "ARBITRAGE"
    SCALPING = "SCALPING"
    SWING = "SWING"
    CUSTOM = "CUSTOM"


class SignalType(str, Enum):
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"
    EXIT = "EXIT"


class LogLevel(str, Enum):
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


# ================================
# BASE MODELS
# ================================

class BaseResponse(BaseModel):
    """Base response model."""
    success: bool = True
    message: str = "Operation successful"
    timestamp: datetime = Field(default_factory=datetime.now)


class ErrorResponse(BaseResponse):
    """Error response model."""
    success: bool = False
    error_code: Optional[str] = None
    details: Optional[Dict[str, Any]] = None


# ================================
# USER & AUTHENTICATION MODELS
# ================================

class UserCreate(BaseModel):
    """User creation request."""
    username: str = Field(..., min_length=3, max_length=50)
    email: str = Field(..., pattern=r'^[^@]+@[^@]+\.[^@]+$')
    password: str = Field(..., min_length=8)
    role: UserRole = UserRole.TRADER


class UserResponse(BaseModel):
    """User response model."""
    id: str
    username: str
    email: str
    role: UserRole
    isActive: bool
    createdAt: datetime
    updatedAt: datetime


class SessionCreate(BaseModel):
    """Session creation request."""
    username: str
    password: str


class SessionResponse(BaseModel):
    """Session response model."""
    token: str
    refreshToken: Optional[str] = None
    expiresAt: datetime
    user: UserResponse


class ApiKeyCreate(BaseModel):
    """API key creation request."""
    keyName: str = Field(..., min_length=1, max_length=100)
    keyValue: str
    secretKey: Optional[str] = None
    clientId: Optional[str] = None


class ApiKeyResponse(BaseModel):
    """API key response model."""
    id: str
    keyName: str
    keyValue: str
    isActive: bool
    rateLimit: int
    usageCount: int
    lastUsed: Optional[datetime]
    createdAt: datetime


# ================================
# INSTRUMENT & MARKET DATA MODELS
# ================================

class InstrumentCreate(BaseModel):
    """Instrument creation request."""
    symbol: str = Field(..., min_length=1, max_length=50)
    name: str = Field(..., min_length=1, max_length=200)
    exchange: Exchange
    instrumentType: InstrumentType
    lotSize: int = Field(default=1, ge=1)
    tickSize: float = Field(default=0.01, gt=0)
    sector: Optional[str] = None
    industry: Optional[str] = None
    marketCap: Optional[float] = None


class InstrumentResponse(BaseModel):
    """Instrument response model."""
    id: str
    symbol: str
    name: str
    exchange: Exchange
    instrumentType: InstrumentType
    lotSize: int
    tickSize: float
    isActive: bool
    sector: Optional[str]
    industry: Optional[str]
    marketCap: Optional[float]
    createdAt: datetime


class MarketDataCreate(BaseModel):
    """Market data creation request."""
    instrumentId: str
    timestamp: datetime
    open: float = Field(..., gt=0)
    high: float = Field(..., gt=0)
    low: float = Field(..., gt=0)
    close: float = Field(..., gt=0)
    volume: int = Field(..., ge=0)
    ltp: float = Field(..., gt=0)
    bid: Optional[float] = None
    ask: Optional[float] = None
    bidQty: Optional[int] = None
    askQty: Optional[int] = None
    change: Optional[float] = None
    changePct: Optional[float] = None
    feedLatency: Optional[int] = None


class MarketDataResponse(BaseModel):
    """Market data response model."""
    id: str
    instrumentId: str
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: int
    ltp: float
    bid: Optional[float]
    ask: Optional[float]
    change: Optional[float]
    changePct: Optional[float]
    createdAt: datetime


# ================================
# TRADING MODELS
# ================================

class OrderCreate(BaseModel):
    """Order creation request."""
    instrumentId: str
    strategyId: Optional[str] = None
    orderType: OrderType
    transactionType: TransactionType
    quantity: int = Field(..., gt=0)
    price: Optional[float] = Field(None, gt=0)
    triggerPrice: Optional[float] = Field(None, gt=0)
    stopLoss: Optional[float] = Field(None, gt=0)
    target: Optional[float] = Field(None, gt=0)
    productType: str = "INTRADAY"
    validity: str = "DAY"


class OrderResponse(BaseModel):
    """Order response model."""
    id: str
    instrumentId: str
    strategyId: Optional[str]
    orderType: OrderType
    transactionType: TransactionType
    quantity: int
    price: Optional[float]
    status: OrderStatus
    brokerOrderId: Optional[str]
    averagePrice: Optional[float]
    filledQuantity: int
    pendingQuantity: Optional[int]
    rejectionReason: Optional[str]
    placedAt: datetime
    updatedAt: datetime


class TradeResponse(BaseModel):
    """Trade response model."""
    id: str
    orderId: str
    instrumentId: str
    quantity: int
    price: float
    value: float
    brokerage: float
    taxes: float
    netValue: float
    tradeTime: datetime
    tradeId: Optional[str]


# ================================
# STRATEGY MODELS
# ================================

class StrategyCreate(BaseModel):
    """Strategy creation request."""
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = None
    strategyType: StrategyType
    parameters: Dict[str, Any] = Field(default_factory=dict)


class StrategyResponse(BaseModel):
    """Strategy response model."""
    id: str
    name: str
    description: Optional[str]
    strategyType: StrategyType
    isActive: bool
    isBacktested: bool
    parameters: Dict[str, Any]
    performance: Optional[Dict[str, Any]]
    riskMetrics: Optional[Dict[str, Any]]
    createdAt: datetime
    updatedAt: datetime


class TradingSignalCreate(BaseModel):
    """Trading signal creation request."""
    strategyId: str
    symbol: str
    signalType: SignalType
    strength: float = Field(..., ge=0, le=1)
    price: float = Field(..., gt=0)
    quantity: Optional[int] = Field(None, gt=0)
    stopLoss: Optional[float] = Field(None, gt=0)
    target: Optional[float] = Field(None, gt=0)
    timeframe: Optional[str] = None
    indicators: Optional[Dict[str, Any]] = None


class TradingSignalResponse(BaseModel):
    """Trading signal response model."""
    id: str
    strategyId: str
    symbol: str
    signalType: SignalType
    strength: float
    price: float
    quantity: Optional[int]
    stopLoss: Optional[float]
    target: Optional[float]
    timeframe: Optional[str]
    indicators: Optional[Dict[str, Any]]
    isExecuted: bool
    executedAt: Optional[datetime]
    createdAt: datetime


# ================================
# SYSTEM MODELS
# ================================

class SystemLogCreate(BaseModel):
    """System log creation request."""
    service: str
    level: LogLevel
    message: str
    details: Optional[Dict[str, Any]] = None
    userId: Optional[str] = None
    sessionId: Optional[str] = None
    ipAddress: Optional[str] = None
    userAgent: Optional[str] = None


class SystemLogResponse(BaseModel):
    """System log response model."""
    id: str
    service: str
    level: LogLevel
    message: str
    details: Optional[Dict[str, Any]]
    userId: Optional[str]
    timestamp: datetime


class HealthCheckResponse(BaseModel):
    """Health check response model."""
    service: str
    status: str
    connection: Optional[str] = None
    queryTimeMs: Optional[float] = None
    uptimeSeconds: Optional[float] = None
    totalQueries: Optional[int] = None
    errorCount: Optional[int] = None
    error: Optional[str] = None


class DatabaseStatsResponse(BaseModel):
    """Database statistics response model."""
    service: str
    isConnected: bool
    uptimeSeconds: float
    totalQueries: int
    errorCount: int
    errorRate: float
    queriesPerSecond: float
    connectionAttempts: int


# ================================
# QUERY MODELS
# ================================

class PaginationParams(BaseModel):
    """Pagination parameters."""
    page: int = Field(default=1, ge=1)
    limit: int = Field(default=100, ge=1, le=1000)
    
    @property
    def skip(self) -> int:
        return (self.page - 1) * self.limit


class OrderFilters(BaseModel):
    """Order filtering parameters."""
    status: Optional[OrderStatus] = None
    orderType: Optional[OrderType] = None
    transactionType: Optional[TransactionType] = None
    strategyId: Optional[str] = None
    instrumentId: Optional[str] = None
    fromDate: Optional[datetime] = None
    toDate: Optional[datetime] = None


class MarketDataFilters(BaseModel):
    """Market data filtering parameters."""
    instrumentId: Optional[str] = None
    fromDate: Optional[datetime] = None
    toDate: Optional[datetime] = None
    exchange: Optional[Exchange] = None


# ================================
# BULK OPERATIONS
# ================================

class BulkOrderCreate(BaseModel):
    """Bulk order creation request."""
    orders: List[OrderCreate] = Field(..., min_items=1, max_items=100)


class BulkOrderResponse(BaseModel):
    """Bulk order creation response."""
    successful: List[OrderResponse]
    failed: List[Dict[str, Any]]
    totalProcessed: int
    successCount: int
    failureCount: int


class BulkMarketDataCreate(BaseModel):
    """Bulk market data creation request."""
    data: List[MarketDataCreate] = Field(..., min_items=1, max_items=1000)


# ================================
# EXPORT ALL MODELS
# ================================

__all__ = [
    # Enums
    "UserRole", "Exchange", "InstrumentType", "OrderType", "TransactionType",
    "OrderStatus", "StrategyType", "SignalType", "LogLevel",
    
    # Base models
    "BaseResponse", "ErrorResponse",
    
    # User & Auth models
    "UserCreate", "UserResponse", "SessionCreate", "SessionResponse",
    "ApiKeyCreate", "ApiKeyResponse",
    
    # Instrument & Market Data models
    "InstrumentCreate", "InstrumentResponse", "MarketDataCreate", "MarketDataResponse",
    
    # Trading models
    "OrderCreate", "OrderResponse", "TradeResponse",
    
    # Strategy models
    "StrategyCreate", "StrategyResponse", "TradingSignalCreate", "TradingSignalResponse",
    
    # System models
    "SystemLogCreate", "SystemLogResponse", "HealthCheckResponse", "DatabaseStatsResponse",
    
    # Query models
    "PaginationParams", "OrderFilters", "MarketDataFilters",
    
    # Bulk operations
    "BulkOrderCreate", "BulkOrderResponse", "BulkMarketDataCreate"
]
