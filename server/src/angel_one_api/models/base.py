"""
Base Pydantic Models
===================

Base models and common response structures for Angel One API.
"""

from typing import Any, Dict, Optional, Union
from datetime import datetime
from pydantic import BaseModel, Field, validator
from enum import Enum

class ResponseStatus(str, Enum):
    """Standard response status values."""
    SUCCESS = "success"
    ERROR = "error"
    WARNING = "warning"
    PARTIAL_SUCCESS = "partial_success"

class BaseResponse(BaseModel):
    """Base response model for all API endpoints."""
    
    success: bool = Field(..., description="Operation success status")
    message: str = Field(..., description="Human-readable response message")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Response timestamp")
    response_time_ms: Optional[float] = Field(None, description="Response time in milliseconds")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat() + "Z"
        }

class SuccessResponse(BaseResponse):
    """Standard success response."""
    
    success: bool = Field(True, description="Always true for success responses")
    data: Optional[Dict[str, Any]] = Field(None, description="Response data")

class ErrorResponse(BaseResponse):
    """Standard error response."""
    
    success: bool = Field(False, description="Always false for error responses")
    error_code: Optional[str] = Field(None, description="Machine-readable error code")
    error_details: Optional[Dict[str, Any]] = Field(None, description="Additional error information")

class HealthStatus(str, Enum):
    """Health status values."""
    HEALTHY = "healthy"
    DEGRADED = "degraded" 
    UNHEALTHY = "unhealthy"
    NOT_CONFIGURED = "not_configured"
    DISABLED = "disabled"

class ComponentHealth(BaseModel):
    """Health information for a system component."""
    
    status: HealthStatus = Field(..., description="Component health status")
    message: Optional[str] = Field(None, description="Health status message")
    response_time_ms: Optional[float] = Field(None, description="Component response time")
    last_check: datetime = Field(default_factory=datetime.utcnow, description="Last health check time")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional health metadata")

class PaginationInfo(BaseModel):
    """Pagination information for paginated responses."""
    
    page: int = Field(..., ge=1, description="Current page number")
    page_size: int = Field(..., ge=1, le=1000, description="Items per page")
    total_items: int = Field(..., ge=0, description="Total number of items")
    total_pages: int = Field(..., ge=0, description="Total number of pages")
    has_next: bool = Field(..., description="Whether there are more pages")
    has_previous: bool = Field(..., description="Whether there are previous pages")

class PaginatedResponse(BaseResponse):
    """Base model for paginated responses."""
    
    pagination: PaginationInfo = Field(..., description="Pagination information")
    items: list = Field(..., description="List of items for current page")

class MetricsData(BaseModel):
    """Base model for metrics data."""
    
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Metrics timestamp")
    service_name: str = Field(..., description="Service name")
    version: str = Field(..., description="Service version")
    environment: str = Field(..., description="Environment (dev/staging/prod)")

class PerformanceMetrics(BaseModel):
    """Performance metrics data."""
    
    average_response_time_ms: float = Field(..., description="Average response time in milliseconds")
    median_response_time_ms: float = Field(..., description="Median response time in milliseconds")
    p95_response_time_ms: float = Field(..., description="95th percentile response time")
    p99_response_time_ms: float = Field(..., description="99th percentile response time")
    requests_per_second: float = Field(..., description="Current requests per second")
    total_requests: int = Field(..., description="Total requests processed")
    successful_requests: int = Field(..., description="Total successful requests")
    failed_requests: int = Field(..., description="Total failed requests")
    success_rate: float = Field(..., ge=0, le=100, description="Success rate percentage")

class SystemMetrics(BaseModel):
    """System resource metrics."""
    
    cpu_percent: float = Field(..., ge=0, le=100, description="CPU usage percentage")
    memory_total_gb: float = Field(..., ge=0, description="Total memory in GB")
    memory_available_gb: float = Field(..., ge=0, description="Available memory in GB")
    memory_used_percent: float = Field(..., ge=0, le=100, description="Memory usage percentage")
    disk_total_gb: float = Field(..., ge=0, description="Total disk space in GB")
    disk_free_gb: float = Field(..., ge=0, description="Free disk space in GB")
    disk_used_percent: float = Field(..., ge=0, le=100, description="Disk usage percentage")
    uptime_seconds: float = Field(..., ge=0, description="System uptime in seconds")

class ValidationError(BaseModel):
    """Validation error details."""
    
    field: str = Field(..., description="Field name that failed validation")
    message: str = Field(..., description="Validation error message")
    invalid_value: Optional[Any] = Field(None, description="The invalid value that was provided")

class APIKeyInfo(BaseModel):
    """Information about an API key (without sensitive data)."""
    
    key_id: str = Field(..., description="API key identifier")
    client_id: str = Field(..., description="Angel One client ID")
    is_active: bool = Field(..., description="Whether the key is currently active")
    last_used: Optional[datetime] = Field(None, description="Last time this key was used")
    session_expires: Optional[datetime] = Field(None, description="When the current session expires")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat() + "Z"
        }
