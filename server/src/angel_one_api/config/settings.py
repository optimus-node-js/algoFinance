"""
Application Configuration
========================

Centralized configuration management for Angel One FastAPI service.
Supports environment-based configuration with validation.
"""

import os
from typing import List, Dict, Any, Optional
from pydantic import Field, validator
from pydantic_settings import BaseSettings
from enum import Enum

class Environment(str, Enum):
    """Application environment types."""
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"

class LogLevel(str, Enum):
    """Log level options."""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"

class Settings(BaseSettings):
    """Application settings with environment variable support."""
    
    model_config = {
        'env_file': ['.env', '../.env', '../../.env', '../../../.env'],
        'env_file_encoding': 'utf-8',
        'extra': 'ignore'
    }
    
    # Application
    APP_NAME: str = Field(default="Angel One Trading API", env="APP_NAME")
    VERSION: str = Field(default="1.0.0", env="VERSION")
    ENVIRONMENT: Environment = Field(default=Environment.DEVELOPMENT, env="ENVIRONMENT")
    DEBUG: bool = Field(default=True, env="DEBUG")
    
    # Server
    HOST: str = Field(default="0.0.0.0", env="HOST")
    PORT: int = Field(default=8000, env="PORT")
    WORKERS: int = Field(default=1, env="WORKERS")
    
    # Security
    SECRET_KEY: str = Field(default="your-secret-key-change-in-production", env="SECRET_KEY")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=30, env="ACCESS_TOKEN_EXPIRE_MINUTES")
    ALLOWED_ORIGINS: List[str] = Field(
        default=["http://localhost:3000", "http://localhost:8080"],
        env="ALLOWED_ORIGINS"
    )
    
    # Logging
    LOG_LEVEL: LogLevel = Field(default=LogLevel.INFO, env="LOG_LEVEL")
    LOG_FORMAT: str = Field(default="json", env="LOG_FORMAT")  # json or text
    
    # Database
    DATABASE_URL: str = Field(
        default="postgresql://user:***REDACTED***@localhost/angel_one_db",
        env="DATABASE_URL"
    )
    DATABASE_POOL_SIZE: int = Field(default=20, env="DATABASE_POOL_SIZE")
    
    # Redis Configuration
    REDIS_HOST: str = Field(default="localhost", env="REDIS_HOST")
    REDIS_PORT: int = Field(default=6379, env="REDIS_PORT")
    REDIS_DB: int = Field(default=0, env="REDIS_DB")
    
    # RabbitMQ
    RABBITMQ_URL: str = Field(
        default="amqp://guest:guest@localhost:5672/",
        env="RABBITMQ_URL"
    )
    RABBITMQ_EXCHANGE: str = Field(default="angel_one_exchange", env="RABBITMQ_EXCHANGE")
    RABBITMQ_AI_QUEUE: str = Field(default="ai_requests", env="RABBITMQ_AI_QUEUE")
    RABBITMQ_RESPONSE_QUEUE: str = Field(default="angel_responses", env="RABBITMQ_RESPONSE_QUEUE")
    
    # Angel One API
    ANGEL_ONE_API_TIMEOUT: int = Field(default=30, env="ANGEL_ONE_API_TIMEOUT")
    ANGEL_ONE_MAX_RETRIES: int = Field(default=3, env="ANGEL_ONE_MAX_RETRIES")
    
    # Angel One API Keys - Individual keys from .env
    API_KEY: str = Field(default="demo_key_1", env="API_KEY")
    API_KEY_2: str = Field(default="demo_key_2", env="API_KEY_2") 
    API_KEY_3: str = Field(default="demo_key_3", env="API_KEY_3")
    API_KEY_4: str = Field(default="demo_key_4", env="API_KEY_4")
    API_KEY_5: str = Field(default="demo_key_5", env="API_KEY_5")
    
    # Angel One Authentication Credentials
    SECRET_KEY_ANGEL: str = Field(default="demo_secret", env="SECRET_KEY")
    CLIENT_ID: str = Field(default="demo_client", env="CLIENT_ID")
    PASSWORD: str = Field(default="demo_password", env="PASSWORD")
    TOTP_SECRET: str = Field(default="", env="TOTP_SECRET")
    
    def get_api_keys(self) -> List[str]:
        """Get all configured API keys as a list."""
        keys = [self.API_KEY, self.API_KEY_2, self.API_KEY_3, self.API_KEY_4, self.API_KEY_5]
        return [key.strip() for key in keys if key.strip()]
    
    @property
    def API_KEYS(self) -> Dict[str, str]:
        """Get all configured API keys as a dictionary."""
        return {
            "API_KEY": self.API_KEY,
            "API_KEY_2": self.API_KEY_2,
            "API_KEY_3": self.API_KEY_3,
            "API_KEY_4": self.API_KEY_4,
            "API_KEY_5": self.API_KEY_5
        }
    
    # Rate Limiting
    RATE_LIMIT_ENABLED: bool = Field(default=True, env="RATE_LIMIT_ENABLED")
    RATE_LIMIT_REQUESTS_PER_MINUTE: int = Field(default=1000, env="RATE_LIMIT_REQUESTS_PER_MINUTE")
    
    # WebSocket
    WEBSOCKET_MAX_CONNECTIONS: int = Field(default=100, env="WEBSOCKET_MAX_CONNECTIONS")
    WEBSOCKET_HEARTBEAT_INTERVAL: int = Field(default=30, env="WEBSOCKET_HEARTBEAT_INTERVAL")
    
    # Performance
    ENABLE_GZIP: bool = Field(default=True, env="ENABLE_GZIP")
    GZIP_MINIMUM_SIZE: int = Field(default=1000, env="GZIP_MINIMUM_SIZE")
    
    # Health Check
    HEALTH_CHECK_INTERVAL: int = Field(default=30, env="HEALTH_CHECK_INTERVAL")  # seconds
    HEALTH_CHECK_TIMEOUT: int = Field(default=5, env="HEALTH_CHECK_TIMEOUT")  # seconds
    
    # Documentation
    DOCS_URL: str = Field(default="/docs", env="DOCS_URL")
    REDOC_URL: str = Field(default="/redoc", env="REDOC_URL")
    OPENAPI_URL: str = Field(default="/openapi.json", env="OPENAPI_URL")
    
    # Scalar Documentation
    SCALAR_DOCS_URL: str = Field(default="/scalar-docs", env="SCALAR_DOCS_URL")
    ENABLE_SCALAR_DOCS: bool = Field(default=True, env="ENABLE_SCALAR_DOCS")
    
    @validator("ALLOWED_ORIGINS", pre=True)
    def parse_allowed_origins(cls, v):
        """Parse comma-separated origins."""
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",")]
        return v
    
    @validator("ENVIRONMENT")
    def validate_environment(cls, v):
        """Validate environment setting."""
        if v not in Environment.__members__.values():
            raise ValueError(f"Invalid environment: {v}")
        return v
    
    def is_production(self) -> bool:
        """Check if running in production."""
        return self.ENVIRONMENT == Environment.PRODUCTION
    
    def is_development(self) -> bool:
        """Check if running in development."""
        return self.ENVIRONMENT == Environment.DEVELOPMENT
    
    def get_cors_origins(self) -> List[str]:
        """Get CORS origins based on environment."""
        if self.is_production():
            # In production, only allow specific origins
            return self.ALLOWED_ORIGINS
        else:
            # In development, allow all origins
            return ["*"]
    

# Global settings instance
settings = Settings()

# Export commonly used settings
__all__ = ["settings", "Settings", "Environment", "LogLevel"]
