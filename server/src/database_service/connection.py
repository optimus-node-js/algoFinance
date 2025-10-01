"""
Database Connection Management
=============================

Centralized database connection management for all microservices.
Provides easy access to Prisma client across the HFT system.
"""

import asyncio
import os
import logging
from typing import Optional, Dict, Any, AsyncContextManager
from contextlib import asynccontextmanager
from datetime import datetime, timezone

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent))

from prisma_client import get_prisma_service, PrismaService, DatabaseUtils

logger = logging.getLogger("database_connection")


class DatabaseConnection:
    """
    Centralized database connection manager for microservices.
    
    This class provides a simple interface for microservices to access
    the Prisma database without managing connections directly.
    """
    
    def __init__(self, service_name: str):
        """
        Initialize database connection for a microservice.
        
        Args:
            service_name: Name of the microservice
        """
        self.service_name = service_name
        self.prisma_service: Optional[PrismaService] = None
        self.is_initialized = False
        
        logger.info(f"DatabaseConnection initialized for service: {service_name}")
    
    async def initialize(self) -> bool:
        """
        Initialize the database connection.
        
        Returns:
            True if initialization successful
        """
        try:
            self.prisma_service = await get_prisma_service()
            self.is_initialized = True
            
            # Log service connection
            await self.log_event("INFO", f"Database connection initialized for {self.service_name}")
            
            logger.info(f"Database connection ready for {self.service_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize database connection for {self.service_name}: {e}")
            return False
    
    async def get_client(self):
        """
        Get the Prisma client.
        
        Returns:
            Prisma client instance
        """
        if not self.is_initialized or not self.prisma_service:
            await self.initialize()
        
        return self.prisma_service.client
    
    @asynccontextmanager
    async def transaction(self):
        """
        Database transaction context manager.
        
        Usage:
            async with db.transaction() as tx:
                await tx.user.create(...)
                await tx.order.create(...)
        """
        if not self.is_initialized or not self.prisma_service:
            await self.initialize()
        
        async with self.prisma_service.transaction() as tx:
            yield tx
    
    async def health_check(self) -> Dict[str, Any]:
        """
        Perform database health check for this service.
        
        Returns:
            Health status dictionary
        """
        if not self.is_initialized or not self.prisma_service:
            return {
                "service": self.service_name,
                "status": "unhealthy",
                "error": "Database connection not initialized"
            }
        
        health = await self.prisma_service.health_check()
        health["service"] = self.service_name
        
        return health
    
    async def log_event(self, level: str, message: str, details: Dict[str, Any] = None, user_id: str = None):
        """
        Log an event to the database.
        
        Args:
            level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
            message: Log message
            details: Additional details (optional)
            user_id: User ID if applicable (optional)
        """
        try:
            if not self.is_initialized or not self.prisma_service:
                await self.initialize()
            
            client = await self.get_client()
            
            await DatabaseUtils.log_system_event(
                client, 
                self.service_name, 
                level, 
                message, 
                details
            )
            
        except Exception as e:
            logger.error(f"Failed to log event to database: {e}")
    
    async def execute_query(self, query_func, *args, **kwargs):
        """
        Execute a database query with error handling.
        
        Args:
            query_func: Query function to execute
            *args, **kwargs: Query arguments
            
        Returns:
            Query result
        """
        if not self.is_initialized or not self.prisma_service:
            await self.initialize()
        
        return await self.prisma_service.execute_query(query_func, *args, **kwargs)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get connection statistics."""
        if not self.prisma_service:
            return {
                "service": self.service_name,
                "status": "not_initialized"
            }
        
        stats = self.prisma_service.get_stats()
        stats["service"] = self.service_name
        
        return stats
    
    async def close(self):
        """Close the database connection."""
        if self.prisma_service:
            await self.prisma_service.disconnect()
            self.is_initialized = False
            logger.info(f"Database connection closed for {self.service_name}")


# Service-specific database managers
class AngelOneDBManager(DatabaseConnection):
    """Database manager for Angel One API service."""
    
    def __init__(self):
        super().__init__("angel_one_api")
    
    async def create_api_key(self, user_id: str, key_name: str, key_value: str, secret_key: str = None):
        """Create API key record."""
        client = await self.get_client()
        return await client.apikey.create({
            "userId": user_id,
            "keyName": key_name,
            "keyValue": key_value,
            "secretKey": secret_key
        })
    
    async def get_user_api_keys(self, user_id: str):
        """Get user's API keys."""
        client = await self.get_client()
        return await client.apikey.find_many(
            where={"userId": user_id, "isActive": True}
        )


class StrategyDBManager(DatabaseConnection):
    """Database manager for Strategy Engine service."""
    
    def __init__(self):
        super().__init__("strategy_engine")
    
    async def create_strategy(self, user_id: str, name: str, strategy_type: str, parameters: Dict[str, Any]):
        """Create a new strategy."""
        client = await self.get_client()
        return await client.strategy.create({
            "userId": user_id,
            "name": name,
            "strategyType": strategy_type,
            "parameters": parameters
        })
    
    async def create_trading_signal(self, strategy_id: str, symbol: str, signal_type: str, 
                                  strength: float, price: float, indicators: Dict[str, Any] = None):
        """Create a trading signal."""
        client = await self.get_client()
        return await client.tradingsignal.create({
            "strategyId": strategy_id,
            "symbol": symbol,
            "signalType": signal_type,
            "strength": strength,
            "price": price,
            "indicators": indicators or {}
        })


class MarketDataDBManager(DatabaseConnection):
    """Database manager for Market Data service."""
    
    def __init__(self):
        super().__init__("market_data_streaming")
    
    async def create_instrument(self, symbol: str, name: str, exchange: str, instrument_type: str):
        """Create instrument record."""
        client = await self.get_client()
        return await client.instrument.create({
            "symbol": symbol,
            "name": name,
            "exchange": exchange,
            "instrumentType": instrument_type
        })
    
    async def store_market_tick(self, instrument_id: str, tick_data: Dict[str, Any]):
        """Store market data tick."""
        client = await self.get_client()
        return await DatabaseUtils.create_market_data(client, instrument_id, tick_data)


class RiskDBManager(DatabaseConnection):
    """Database manager for Risk Management service."""
    
    def __init__(self):
        super().__init__("risk_service")
    
    async def create_risk_profile(self, user_id: str, max_daily_loss: float, max_position_size: float):
        """Create risk profile."""
        client = await self.get_client()
        return await client.riskprofile.create({
            "userId": user_id,
            "maxDailyLoss": max_daily_loss,
            "maxPositionSize": max_position_size
        })
    
    async def create_alert(self, alert_type: str, severity: str, title: str, message: str, source: str):
        """Create risk alert."""
        client = await self.get_client()
        return await client.alert.create({
            "type": alert_type,
            "severity": severity,
            "title": title,
            "message": message,
            "source": source
        })


# Factory function to get appropriate database manager
def get_database_manager(service_name: str) -> DatabaseConnection:
    """
    Get appropriate database manager for a service.
    
    Args:
        service_name: Name of the microservice
        
    Returns:
        Database manager instance
    """
    managers = {
        "angel_one_api": AngelOneDBManager,
        "strategy_engine": StrategyDBManager,
        "market_data_streaming": MarketDataDBManager,
        "risk_service": RiskDBManager
    }
    
    manager_class = managers.get(service_name, DatabaseConnection)
    return manager_class() if service_name in managers else DatabaseConnection(service_name)


# Global database managers (lazy initialization)
_db_managers: Dict[str, DatabaseConnection] = {}


async def get_db_manager(service_name: str) -> DatabaseConnection:
    """
    Get or create database manager for a service.
    
    Args:
        service_name: Name of the microservice
        
    Returns:
        Database manager instance
    """
    global _db_managers
    
    if service_name not in _db_managers:
        _db_managers[service_name] = get_database_manager(service_name)
        await _db_managers[service_name].initialize()
    
    return _db_managers[service_name]


async def close_all_db_connections():
    """Close all database connections."""
    global _db_managers
    
    for manager in _db_managers.values():
        await manager.close()
    
    _db_managers.clear()
    logger.info("All database connections closed")


# Export main classes and functions
__all__ = [
    "DatabaseConnection",
    "AngelOneDBManager",
    "StrategyDBManager", 
    "MarketDataDBManager",
    "RiskDBManager",
    "get_database_manager",
    "get_db_manager",
    "close_all_db_connections"
]
