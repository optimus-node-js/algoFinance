"""
Admin & Monitoring Models
========================

Pydantic models for administration and monitoring endpoints.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime
from pydantic import BaseModel, Field
from decimal import Decimal
from enum import Enum

from .base import BaseResponse, HealthStatus, ComponentHealth, PerformanceMetrics, SystemMetrics

class ServiceHealth(BaseModel):
    """Service health information."""
    
    name: str = Field(..., description="Service name")
    version: str = Field(..., description="Service version")
    environment: str = Field(..., description="Environment")
    uptime_seconds: float = Field(..., description="Service uptime in seconds")
    status: HealthStatus = Field(..., description="Overall health status")

class HealthSummary(BaseModel):
    """Health check summary."""
    
    healthy_components: int = Field(..., description="Number of healthy components")
    total_components: int = Field(..., description="Total number of components")
    health_percentage: float = Field(..., description="Overall health percentage")

class HealthResponse(BaseResponse):
    """Comprehensive health check response."""
    
    status: HealthStatus = Field(..., description="Overall health status")
    service: ServiceHealth = Field(..., description="Service information")
    components: Dict[str, ComponentHealth] = Field(..., description="Component health details")
    system: SystemMetrics = Field(..., description="System metrics")
    summary: HealthSummary = Field(..., description="Health summary")

class APIEndpointStats(BaseModel):
    """Statistics for an API endpoint."""
    
    endpoint: str = Field(..., description="Endpoint path")
    method: str = Field(..., description="HTTP method")
    total_requests: int = Field(..., description="Total requests")
    successful_requests: int = Field(..., description="Successful requests")
    failed_requests: int = Field(..., description="Failed requests")
    average_response_time_ms: float = Field(..., description="Average response time")
    last_accessed: Optional[datetime] = Field(None, description="Last access time")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat() + "Z"
        }

class ServiceStats(BaseModel):
    """Service-level statistics."""
    
    # Request statistics
    total_requests: int = Field(..., description="Total requests processed")
    requests_per_minute: float = Field(..., description="Current requests per minute")
    
    # Performance statistics
    average_response_time_ms: float = Field(..., description="Average response time")
    slowest_endpoint: Optional[str] = Field(None, description="Slowest endpoint")
    fastest_endpoint: Optional[str] = Field(None, description="Fastest endpoint")
    
    # Error statistics
    total_errors: int = Field(..., description="Total errors")
    error_rate: float = Field(..., description="Error rate percentage")
    most_common_error: Optional[str] = Field(None, description="Most common error")

class RateLimitStats(BaseModel):
    """Rate limiting statistics."""
    
    enabled: bool = Field(..., description="Whether rate limiting is enabled")
    requests_per_minute_limit: int = Field(..., description="Requests per minute limit")
    current_requests_per_minute: float = Field(..., description="Current requests per minute")
    rate_limited_requests: int = Field(..., description="Total rate limited requests")
    top_rate_limited_clients: List[str] = Field(..., description="Most rate limited clients")

class AngelOneAPIStats(BaseModel):
    """Angel One API integration statistics."""
    
    active_sessions: int = Field(..., description="Active Angel One sessions")
    total_api_calls: int = Field(..., description="Total API calls made")
    successful_api_calls: int = Field(..., description="Successful API calls")
    failed_api_calls: int = Field(..., description="Failed API calls")
    api_success_rate: float = Field(..., description="API success rate percentage")
    average_api_response_time_ms: float = Field(..., description="Average API response time")

class MetricsResponse(BaseResponse):
    """Comprehensive metrics response."""
    
    service: ServiceStats = Field(..., description="Service-level statistics")
    endpoints: List[APIEndpointStats] = Field(..., description="Endpoint statistics")
    rate_limiting: RateLimitStats = Field(..., description="Rate limiting statistics")
    angel_one_api: AngelOneAPIStats = Field(..., description="Angel One API statistics")
    system: SystemMetrics = Field(..., description="System resource metrics")
    performance: PerformanceMetrics = Field(..., description="Performance metrics")

class LogLevel(str, Enum):
    """Log levels."""
    DEBUG = "DEBUG"
    INFO = "INFO" 
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"

class LogEntry(BaseModel):
    """Individual log entry."""
    
    timestamp: datetime = Field(..., description="Log timestamp")
    level: LogLevel = Field(..., description="Log level")
    logger: str = Field(..., description="Logger name")
    message: str = Field(..., description="Log message")
    extra: Optional[Dict[str, Any]] = Field(None, description="Additional log data")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat() + "Z"
        }

class LogStats(BaseModel):
    """Log statistics."""
    
    total_logs: int = Field(..., description="Total log entries")
    logs_by_level: Dict[str, int] = Field(..., description="Log count by level")
    recent_errors: List[LogEntry] = Field(..., description="Recent error logs")

class LogStatsResponse(BaseResponse):
    """Response for log statistics."""
    
    stats: LogStats = Field(..., description="Log statistics")
    time_range_hours: int = Field(..., description="Time range in hours")

class ConfigurationInfo(BaseModel):
    """Service configuration information."""
    
    environment: str = Field(..., description="Environment")
    debug_mode: bool = Field(..., description="Debug mode enabled")
    rate_limiting_enabled: bool = Field(..., description="Rate limiting enabled")
    websocket_enabled: bool = Field(..., description="WebSocket enabled")
    rabbitmq_enabled: bool = Field(..., description="RabbitMQ enabled")
    database_enabled: bool = Field(..., description="Database enabled")

class SystemStatsResponse(BaseResponse):
    """System statistics response."""
    
    configuration: ConfigurationInfo = Field(..., description="Configuration info")
    uptime_seconds: float = Field(..., description="System uptime")
    memory_usage: Dict[str, float] = Field(..., description="Memory usage statistics")
    cpu_usage: Dict[str, float] = Field(..., description="CPU usage statistics")
    disk_usage: Dict[str, float] = Field(..., description="Disk usage statistics")

class MaintenanceMode(BaseModel):
    """Maintenance mode configuration."""
    
    enabled: bool = Field(..., description="Maintenance mode enabled")
    message: Optional[str] = Field(None, description="Maintenance message")
    estimated_duration_minutes: Optional[int] = Field(None, description="Estimated duration")
    allowed_ips: Optional[List[str]] = Field(None, description="IPs allowed during maintenance")

class MaintenanceModeResponse(BaseResponse):
    """Maintenance mode response."""
    
    maintenance: MaintenanceMode = Field(..., description="Maintenance configuration")

class CacheStats(BaseModel):
    """Cache statistics."""
    
    enabled: bool = Field(..., description="Cache enabled")
    total_keys: int = Field(..., description="Total cached keys")
    hit_rate: float = Field(..., description="Cache hit rate percentage")
    memory_usage_mb: float = Field(..., description="Cache memory usage in MB")

class CacheStatsResponse(BaseResponse):
    """Cache statistics response."""
    
    stats: CacheStats = Field(..., description="Cache statistics")



