"""
Message Schemas
==============

Pydantic schemas for RabbitMQ message validation.
"""

from typing import Dict, Any, Optional, List
from datetime import datetime
from pydantic import BaseModel, Field
from enum import Enum

class MessageType(str, Enum):
    """Standard message types."""
    # AI Communication
    MARKET_DATA_REQUEST = "market_data_request"
    MARKET_DATA_RESPONSE = "market_data_response"
    TRADING_REQUEST = "trading_request"
    TRADING_RESPONSE = "trading_response"
    PORTFOLIO_REQUEST = "portfolio_request"
    PORTFOLIO_RESPONSE = "portfolio_response"
    
    # Events
    MARKET_DATA_UPDATE = "market_data_update"
    ORDER_UPDATE = "order_update"
    PORTFOLIO_UPDATE = "portfolio_update"
    RISK_ALERT = "risk_alert"
    
    # System
    HEALTH_CHECK = "health_check"
    CONFIG_UPDATE = "config_update"
    SYSTEM_ALERT = "system_alert"

class Priority(int, Enum):
    """Message priority levels."""
    LOW = 0
    NORMAL = 5
    HIGH = 8
    CRITICAL = 9

class BaseMessage(BaseModel):
    """Base message schema."""
    
    message_type: MessageType = Field(..., description="Type of message")
    correlation_id: str = Field(..., description="Unique correlation ID")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Message timestamp")
    source: str = Field(..., description="Source service")
    version: str = Field(default="1.0.0", description="Message schema version")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat() + "Z"
        }

class AIRequest(BaseMessage):
    """AI engine request message."""
    
    request_id: str = Field(..., description="Unique request ID")
    data: Dict[str, Any] = Field(..., description="Request data")
    priority: Priority = Field(default=Priority.NORMAL, description="Request priority")
    timeout_seconds: Optional[int] = Field(default=30, description="Request timeout")
    callback_queue: Optional[str] = Field(default="ai.responses", description="Response queue")

class AIResponse(BaseMessage):
    """AI engine response message."""
    
    request_id: str = Field(..., description="Original request ID")
    success: bool = Field(..., description="Request success status")
    data: Optional[Dict[str, Any]] = Field(None, description="Response data")
    error: Optional[str] = Field(None, description="Error message if failed")
    processing_time_ms: Optional[float] = Field(None, description="Processing time in milliseconds")

class MarketDataEvent(BaseMessage):
    """Market data update event."""
    
    symbol: str = Field(..., description="Trading symbol")
    data_type: str = Field(..., description="Type of market data (ltp, quote, candles)")
    data: Dict[str, Any] = Field(..., description="Market data")
    exchange: Optional[str] = Field(None, description="Exchange identifier")

class TradingEvent(BaseMessage):
    """Trading event message."""
    
    event_type: str = Field(..., description="Type of trading event")
    order_id: Optional[str] = Field(None, description="Order ID if applicable")
    symbol: Optional[str] = Field(None, description="Trading symbol if applicable")
    data: Dict[str, Any] = Field(..., description="Event data")

class PortfolioEvent(BaseMessage):
    """Portfolio update event."""
    
    update_type: str = Field(..., description="Type of portfolio update")
    account_id: Optional[str] = Field(None, description="Account identifier")
    data: Dict[str, Any] = Field(..., description="Portfolio data")

class RiskAlert(BaseMessage):
    """Risk alert message."""
    
    alert_id: str = Field(..., description="Alert identifier")
    alert_type: str = Field(..., description="Type of risk alert")
    severity: str = Field(..., description="Alert severity level")
    message: str = Field(..., description="Alert message")
    symbol: Optional[str] = Field(None, description="Related symbol")
    threshold_value: Optional[float] = Field(None, description="Threshold that triggered alert")
    current_value: Optional[float] = Field(None, description="Current value")

class SystemEvent(BaseMessage):
    """System event message."""
    
    event_type: str = Field(..., description="Type of system event")
    component: str = Field(..., description="System component")
    data: Dict[str, Any] = Field(..., description="Event data")
    severity: Optional[str] = Field(default="INFO", description="Event severity")

class HealthCheckRequest(BaseMessage):
    """Health check request message."""
    
    requester: str = Field(..., description="Service requesting health check")
    components: Optional[List[str]] = Field(None, description="Specific components to check")
    detailed: bool = Field(default=False, description="Request detailed health info")

class HealthCheckResponse(BaseMessage):
    """Health check response message."""
    
    service_name: str = Field(..., description="Service name")
    overall_status: str = Field(..., description="Overall health status")
    components: Dict[str, Any] = Field(..., description="Component health details")
    uptime_seconds: float = Field(..., description="Service uptime")
    version: str = Field(..., description="Service version")

class ConfigUpdateMessage(BaseMessage):
    """Configuration update message."""
    
    config_section: str = Field(..., description="Configuration section to update")
    config_data: Dict[str, Any] = Field(..., description="New configuration data")
    apply_immediately: bool = Field(default=False, description="Apply config immediately")
    restart_required: bool = Field(default=False, description="Service restart required")

# Message validation functions
def validate_message(message_data: Dict[str, Any], expected_type: MessageType) -> BaseMessage:
    """
    Validate message data against expected schema.
    
    Args:
        message_data: Raw message data
        expected_type: Expected message type
        
    Returns:
        BaseMessage: Validated message object
        
    Raises:
        ValueError: If validation fails
    """
    message_type = message_data.get("message_type")
    
    if message_type != expected_type:
        raise ValueError(f"Expected message type {expected_type}, got {message_type}")
    
    # Map message types to schemas
    schema_map = {
        MessageType.MARKET_DATA_REQUEST: AIRequest,
        MessageType.MARKET_DATA_RESPONSE: AIResponse,
        MessageType.TRADING_REQUEST: AIRequest,
        MessageType.TRADING_RESPONSE: AIResponse,
        MessageType.PORTFOLIO_REQUEST: AIRequest,
        MessageType.PORTFOLIO_RESPONSE: AIResponse,
        MessageType.MARKET_DATA_UPDATE: MarketDataEvent,
        MessageType.ORDER_UPDATE: TradingEvent,
        MessageType.PORTFOLIO_UPDATE: PortfolioEvent,
        MessageType.RISK_ALERT: RiskAlert,
        MessageType.HEALTH_CHECK: HealthCheckRequest,
        MessageType.CONFIG_UPDATE: ConfigUpdateMessage,
        MessageType.SYSTEM_ALERT: SystemEvent
    }
    
    schema_class = schema_map.get(expected_type, BaseMessage)
    return schema_class(**message_data)
