"""
Prisma Client Management
=======================

Centralized Prisma client for all HFT microservices.
Provides type-safe, high-performance database access.
"""

import asyncio
import os
import logging
from typing import Optional, Dict, Any
from contextlib import asynccontextmanager
import datetime
from datetime import timezone
from pathlib import Path

# Load environment variables from .env file
from dotenv import load_dotenv

# Load .env file from project root
env_path = Path(__file__).parent.parent.parent.parent / ".env"
load_dotenv(dotenv_path=env_path)

# Prisma client (will be installed)
try:
    from prisma import Prisma
    from prisma.models import *
except ImportError:
    # Fallback for development
    class Prisma:
        def __init__(self):
            pass
        async def connect(self):
            pass
        async def disconnect(self):
            pass

logger = logging.getLogger("prisma_client")

# Global Prisma client instance
_prisma_client: Optional[Prisma] = None
_connection_lock = asyncio.Lock()


def validate_environment_variables():
    """
    Validate required environment variables for database connection.
    
    Raises:
        ValueError: If required environment variables are missing
    """
    required_vars = ["DATABASE_URL"]
    missing_vars = []
    
    for var in required_vars:
        value = os.getenv(var)
        if not value:
            missing_vars.append(var)
    
    if missing_vars:
        error_msg = f"Missing required environment variables: {', '.join(missing_vars)}"
        logger.error(error_msg)
        logger.error("Please ensure your .env file contains all required database configuration variables.")
        raise ValueError(error_msg)
    
    # Log successful validation (without exposing sensitive data)
    database_url = os.getenv("DATABASE_URL", "")
    if database_url.startswith("postgres://"):
        logger.info("✅ DATABASE_URL found and appears to be a valid PostgreSQL connection string")
    else:
        logger.warning("⚠️ DATABASE_URL found but format may not be standard PostgreSQL")
    
    return True


class PrismaService:
    """
    Centralized Prisma service for all microservices.
    
    Features:
    - Connection pooling and management
    - Automatic reconnection
    - Query optimization
    - Error handling and logging
    - Performance monitoring
    """
    
    def __init__(self):
        """Initialize Prisma service."""
        self.client: Optional[Prisma] = None
        self.is_connected = False
        self.connection_attempts = 0
        self.max_retries = 3
        
        # Performance tracking
        self.query_count = 0
        self.error_count = 0
        self.start_time = datetime.datetime.now(timezone.utc)
        
        # Validate environment variables on initialization
        try:
            validate_environment_variables()
            logger.info("PrismaService initialized with valid environment configuration")
        except ValueError as e:
            logger.error(f"PrismaService initialization failed: {e}")
            raise
    
    async def connect(self) -> bool:
        """
        Connect to the Prisma database.
        
        Returns:
            True if connection successful
        """
        if self.is_connected and self.client:
            return True
        
        try:
            # Validate environment variables before attempting connection
            validate_environment_variables()
            
            logger.info("Connecting to Prisma database...")
            logger.info(f"Database URL format: {os.getenv('DATABASE_URL', '')[:20]}...")
            
            # Initialize Prisma client
            self.client = Prisma()
            
            # Connect with retry logic
            for attempt in range(self.max_retries):
                try:
                    await self.client.connect()
                    self.is_connected = True
                    self.connection_attempts = 0
                    
                    logger.info("✅ Successfully connected to Prisma database")
                    return True
                    
                except Exception as e:
                    self.connection_attempts += 1
                    logger.warning(f"❌ Connection attempt {attempt + 1} failed: {e}")
                    
                    # Provide helpful error messages for common issues
                    error_str = str(e).lower()
                    if "environment variable not found" in error_str:
                        logger.error("💡 Hint: Make sure your .env file is in the project root and contains DATABASE_URL")
                    elif "connection refused" in error_str:
                        logger.error("💡 Hint: Check if your database server is running and accessible")
                    elif "authentication failed" in error_str:
                        logger.error("💡 Hint: Verify your database credentials in DATABASE_URL")
                    
                    if attempt < self.max_retries - 1:
                        await asyncio.sleep(2 ** attempt)  # Exponential backoff
            
            logger.error("❌ Failed to connect to Prisma database after all retries")
            return False
            
        except Exception as e:
            logger.error(f"Error connecting to Prisma database: {e}")
            return False
    
    async def disconnect(self):
        """Disconnect from the Prisma database."""
        if self.client and self.is_connected:
            try:
                await self.client.disconnect()
                self.is_connected = False
                logger.info("Disconnected from Prisma database")
            except Exception as e:
                logger.error(f"Error disconnecting from Prisma database: {e}")
    
    async def health_check(self) -> Dict[str, Any]:
        """
        Perform database health check.
        
        Returns:
            Health status dictionary
        """
        try:
            if not self.is_connected or not self.client:
                return {
                    "status": "unhealthy",
                    "error": "Not connected to database"
                }
            
            # Simple query to test connection
            start_time = datetime.datetime.now()
            
            # Test query - count users (lightweight)
            try:
                count = await self.client.user.count()
                query_time = (datetime.datetime.now() - start_time).total_seconds() * 1000
                
                return {
                    "status": "healthy",
                    "connection": "active",
                    "query_time_ms": round(query_time, 2),
                    "user_count": count,
                    "uptime_seconds": (datetime.datetime.now(timezone.utc) - self.start_time).total_seconds(),
                    "total_queries": self.query_count,
                    "error_count": self.error_count
                }
                
            except Exception as query_error:
                return {
                    "status": "unhealthy",
                    "error": f"Query failed: {query_error}",
                    "connection": "active" if self.is_connected else "inactive"
                }
                
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": f"Health check failed: {e}"
            }
    
    async def execute_query(self, query_func, *args, **kwargs):
        """
        Execute a database query with error handling and monitoring.
        
        Args:
            query_func: Prisma query function
            *args, **kwargs: Query arguments
            
        Returns:
            Query result
        """
        if not self.is_connected or not self.client:
            await self.connect()
        
        try:
            start_time = datetime.datetime.now()
            result = await query_func(*args, **kwargs)
            
            # Track performance
            query_time = (datetime.datetime.now() - start_time).total_seconds() * 1000
            self.query_count += 1
            
            # Log slow queries
            if query_time > 100:  # 100ms threshold
                logger.warning(f"Slow query detected: {query_time:.2f}ms")
            
            return result
            
        except Exception as e:
            self.error_count += 1
            logger.error(f"Database query error: {e}")
            raise
    
    @asynccontextmanager
    async def transaction(self):
        """
        Database transaction context manager.
        
        Usage:
            async with prisma_service.transaction() as tx:
                await tx.user.create(...)
                await tx.order.create(...)
        """
        if not self.is_connected or not self.client:
            await self.connect()
        
        async with self.client.tx() as transaction:
            yield transaction
    
    def get_stats(self) -> Dict[str, Any]:
        """Get service statistics."""
        uptime = (datetime.datetime.now(timezone.utc) - self.start_time).total_seconds()
        
        return {
            "is_connected": self.is_connected,
            "uptime_seconds": uptime,
            "total_queries": self.query_count,
            "error_count": self.error_count,
            "error_rate": self.error_count / max(1, self.query_count),
            "queries_per_second": self.query_count / max(1, uptime),
            "connection_attempts": self.connection_attempts
        }


# Global service instance
_prisma_service: Optional[PrismaService] = None


async def get_prisma_client() -> Prisma:
    """
    Get the global Prisma client instance.
    
    Returns:
        Connected Prisma client
    """
    global _prisma_client, _connection_lock
    
    async with _connection_lock:
        if _prisma_client is None:
            _prisma_client = Prisma()
            await _prisma_client.connect()
            logger.info("Global Prisma client connected")
    
    return _prisma_client


async def get_prisma_service() -> PrismaService:
    """
    Get the global Prisma service instance.
    
    Returns:
        PrismaService instance
    """
    global _prisma_service
    
    if _prisma_service is None:
        _prisma_service = PrismaService()
        await _prisma_service.connect()
    
    return _prisma_service


async def close_prisma_connections():
    """Close all Prisma connections."""
    global _prisma_client, _prisma_service
    
    try:
        if _prisma_client:
            await _prisma_client.disconnect()
            _prisma_client = None
            logger.info("Global Prisma client disconnected")
        
        if _prisma_service:
            await _prisma_service.disconnect()
            _prisma_service = None
            logger.info("Prisma service disconnected")
            
    except Exception as e:
        logger.error(f"Error closing Prisma connections: {e}")


# Utility functions for common operations
class DatabaseUtils:
    """Utility functions for common database operations."""
    
    @staticmethod
    async def create_user(prisma: Prisma, username: str, email: str, password: str, role: str = "TRADER") -> Any:
        """Create a new user."""
        return await prisma.user.create({
            "username": username,
            "email": email,
            "password": password,  # Should be hashed before calling
            "role": role
        })
    
    @staticmethod
    async def get_user_by_id(prisma: Prisma, user_id: str) -> Any:
        """Get user by ID."""
        return await prisma.user.find_unique(where={"id": user_id})
    
    @staticmethod
    async def create_session(prisma: Prisma, user_id: str, token: str, expires_at: datetime) -> Any:
        """Create a new session."""
        return await prisma.session.create({
            "userId": user_id,
            "token": token,
            "expiresAt": expires_at
        })
    
    @staticmethod
    async def get_active_session(prisma: Prisma, token: str) -> Any:
        """Get active session by token."""
        return await prisma.session.find_first(
            where={
                "token": token,
                "isActive": True,
                "expiresAt": {"gt": datetime.datetime.now(timezone.utc)}
            },
            include={"user": True}
        )
    
    @staticmethod
    async def create_order(prisma: Prisma, order_data: Dict[str, Any]) -> Any:
        """Create a new order."""
        return await prisma.order.create(data=order_data)
    
    @staticmethod
    async def get_user_orders(prisma: Prisma, user_id: str, limit: int = 100) -> Any:
        """Get user orders."""
        return await prisma.order.find_many(
            where={"userId": user_id},
            include={"instrument": True, "strategy": True},
            order_by={"placedAt": "desc"},
            take=limit
        )
    
    @staticmethod
    async def create_market_data(prisma: Prisma, instrument_id: str, data: Dict[str, Any]) -> Any:
        """Create market data entry."""
        return await prisma.marketdata.create({
            "instrumentId": instrument_id,
            **data
        })
    
    @staticmethod
    async def log_system_event(prisma: Prisma, service: str, level: str, message: str, details: Dict[str, Any] = None) -> Any:
        """Log system event."""
        return await prisma.systemlog.create({
            "service": service,
            "level": level,
            "message": message,
            "details": details or {}
        })


# Export commonly used functions
__all__ = [
    "get_prisma_client",
    "get_prisma_service", 
    "close_prisma_connections",
    "PrismaService",
    "DatabaseUtils"
]
