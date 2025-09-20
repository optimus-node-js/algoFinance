"""
Authentication Models
====================

Pydantic models for authentication-related requests and responses.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime
from pydantic import BaseModel, Field, validator, SecretStr
from enum import Enum

from .base import BaseResponse, APIKeyInfo, ResponseStatus

class APIKeyConfig(BaseModel):
    """Configuration for a single Angel One API key."""
    
    key_id: str = Field(..., description="Unique identifier for this API key")
    api_key: SecretStr = Field(..., description="Angel One API key")
    client_id: str = Field(..., description="Angel One client ID")
    password: SecretStr = Field(..., description="Angel One password")
    totp_secret: SecretStr = Field(..., description="TOTP secret for 2FA")
    
    @validator("key_id")
    def validate_key_id(cls, v):
        """Validate key ID format."""
        if not v or len(v.strip()) == 0:
            raise ValueError("Key ID cannot be empty")
        if len(v) > 50:
            raise ValueError("Key ID too long (max 50 characters)")
        return v.strip()
    
    @validator("client_id")
    def validate_client_id(cls, v):
        """Validate Angel One client ID format."""
        if not v or len(v.strip()) == 0:
            raise ValueError("Client ID cannot be empty")
        # Angel One client IDs are typically alphanumeric (but may contain underscores)
        if not v.replace("_", "").isalnum():
            raise ValueError("Client ID should be alphanumeric (underscores allowed)")
        return v.strip()
    
    model_config = {
        # Hide sensitive fields in logs and serialization - Pydantic v2 way
        "str_strip_whitespace": True,
        "extra": "forbid"
    }

class ConfigureKeysRequest(BaseModel):
    """Request to configure Angel One API keys."""
    
    api_keys: List[APIKeyConfig] = Field(..., min_items=1, max_items=5, description="List of API key configurations (max 5)")
    
    @validator("api_keys")
    def validate_unique_key_ids(cls, v):
        """Ensure all key IDs are unique."""
        key_ids = [key.key_id for key in v]
        if len(key_ids) != len(set(key_ids)):
            raise ValueError("All key IDs must be unique")
        return v

class ConfigureKeysResponse(BaseResponse):
    """Response for API key configuration."""
    
    total_keys: int = Field(..., description="Total number of keys in request")
    successful_configs: int = Field(..., description="Number of successfully configured keys")
    configuration_results: Dict[str, Dict[str, Any]] = Field(..., description="Detailed results for each key")

class LoginResult(BaseModel):
    """Result of a single key login attempt."""
    
    key_id: str = Field(..., description="API key identifier")
    success: bool = Field(..., description="Whether login was successful")
    status: str = Field(..., description="Login status message")
    message: str = Field(..., description="Detailed login message")
    session_token: Optional[str] = Field(None, description="Session token (masked)")
    login_time: Optional[datetime] = Field(None, description="Time of successful login")
    expires_at: Optional[datetime] = Field(None, description="When the session expires")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat() + "Z"
        }

class AutoLoginResponse(BaseResponse):
    """Response for auto-login operation."""
    
    overall_status: str = Field(..., description="Overall login status")
    successful_logins: int = Field(..., description="Number of successful logins")
    total_keys: int = Field(..., description="Total number of keys attempted")
    success_rate: float = Field(..., description="Success rate percentage")
    login_results: List[LoginResult] = Field(..., description="Detailed results for each key")
    auto_refresh_enabled: bool = Field(..., description="Whether auto-refresh is enabled")

class SessionInfo(BaseModel):
    """Information about an active session."""
    
    key_id: str = Field(..., description="API key identifier")
    is_active: bool = Field(..., description="Whether session is currently active")
    login_time: Optional[datetime] = Field(None, description="When session was established")
    last_activity: Optional[datetime] = Field(None, description="Last activity timestamp")
    expires_at: Optional[datetime] = Field(None, description="When session expires")
    requests_made: int = Field(0, description="Number of requests made with this session")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat() + "Z"
        }

class AuthStatusResponse(BaseResponse):
    """Response for authentication status check."""
    
    authenticated: bool = Field(..., description="Whether service is authenticated")
    active_keys: int = Field(..., description="Number of active API keys")
    total_keys: int = Field(..., description="Total number of configured keys")
    success_rate: float = Field(..., description="Authentication success rate")
    session_info: Dict[str, SessionInfo] = Field(..., description="Detailed session information")
    auto_refresh_enabled: bool = Field(..., description="Whether auto-refresh is enabled")
    last_refresh: Optional[datetime] = Field(None, description="Last refresh timestamp")
    next_refresh: Optional[datetime] = Field(None, description="Next scheduled refresh")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat() + "Z"
        }

class RefreshResult(BaseModel):
    """Result of a session refresh attempt."""
    
    key_id: str = Field(..., description="API key identifier")
    success: bool = Field(..., description="Whether refresh was successful")
    message: str = Field(..., description="Refresh result message")
    new_expires_at: Optional[datetime] = Field(None, description="New session expiry time")
    refresh_time: datetime = Field(default_factory=datetime.utcnow, description="Time of refresh attempt")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat() + "Z"
        }

class RefreshResponse(BaseResponse):
    """Response for session refresh operation."""
    
    successful_refreshes: int = Field(..., description="Number of successful refreshes")
    total_sessions: int = Field(..., description="Total number of sessions attempted")
    refresh_results: Dict[str, RefreshResult] = Field(..., description="Detailed refresh results")

class LogoutResult(BaseModel):
    """Result of a logout attempt."""
    
    key_id: str = Field(..., description="API key identifier")
    success: bool = Field(..., description="Whether logout was successful")
    message: str = Field(..., description="Logout result message")
    logout_time: datetime = Field(default_factory=datetime.utcnow, description="Time of logout")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat() + "Z"
        }

class LogoutResponse(BaseResponse):
    """Response for logout operation."""
    
    successful_logouts: int = Field(..., description="Number of successful logouts")
    total_sessions: int = Field(..., description="Total number of sessions")
    logout_results: Dict[str, LogoutResult] = Field(..., description="Detailed logout results")

class AuthHealthResponse(BaseModel):
    """Authentication health check response."""
    
    status: str = Field(..., description="Health status")
    message: str = Field(..., description="Health status message")
    active_sessions: int = Field(..., description="Number of active sessions")
    total_keys: int = Field(..., description="Total configured keys")
    response_time_ms: float = Field(..., description="Health check response time")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Health check timestamp")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat() + "Z"
        }

# JWT Token Models
class TokenData(BaseModel):
    """JWT token data."""
    
    key_id: Optional[str] = Field(None, description="API key identifier")
    client_id: Optional[str] = Field(None, description="Angel One client ID")
    expires_at: Optional[datetime] = Field(None, description="Token expiry time")
    
class Token(BaseModel):
    """JWT token response."""
    
    access_token: str = Field(..., description="JWT access token")
    token_type: str = Field("bearer", description="Token type")
    expires_in: int = Field(..., description="Token expiry in seconds")
    
class TokenValidationRequest(BaseModel):
    """Request to validate a token."""
    
    token: str = Field(..., description="JWT token to validate")

class TokenValidationResponse(BaseModel):
    """Response for token validation."""
    
    valid: bool = Field(..., description="Whether token is valid")
    token_data: Optional[TokenData] = Field(None, description="Token data if valid")
    error: Optional[str] = Field(None, description="Error message if invalid")
