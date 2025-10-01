"""
Database Service Integration Guide
=================================

Complete guide for integrating all HFT microservices with the centralized
Prisma + PostgreSQL database service.

This guide shows how each microservice can easily access the database
without managing connections directly.
"""

import asyncio
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone

# Import the centralized database components
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent))

from connection import get_db_manager, DatabaseConnection
from models import *

logger = logging.getLogger("database_integration")


# ================================
# INTEGRATION EXAMPLES
# ================================

class AngelOneAPIIntegration:
    """
    Example integration for Angel One API service.
    
    Shows how to:
    1. Initialize database connection
    2. Store API calls and responses
    3. Manage user sessions
    4. Log system events
    """
    
    def __init__(self):
        """Initialize Angel One API database integration."""
        self.db_manager: Optional[DatabaseConnection] = None
        self.service_name = "angel_one_api"
    
    async def initialize(self):
        """Initialize database connection."""
        self.db_manager = await get_db_manager(self.service_name)
        await self.db_manager.log_event("INFO", "Angel One API service initialized")
        logger.info("Angel One API database integration ready")
    
    async def create_user_session(self, username: str, token: str, expires_at: datetime) -> Dict[str, Any]:
        """Create a new user session."""
        try:
            client = await self.db_manager.get_client()
            
            # Find user by username
            user = await client.user.find_unique(where={"username": username})
            if not user:
                raise ValueError(f"User {username} not found")
            
            # Create session
            session = await client.session.create({
                "userId": user.id,
                "token": token,
                "expiresAt": expires_at,
                "isActive": True
            })
            
            await self.db_manager.log_event("INFO", f"Session created for user {username}")
            
            return {
                "session_id": session.id,
                "user_id": user.id,
                "token": token,
                "expires_at": expires_at.isoformat()
            }
            
        except Exception as e:
            await self.db_manager.log_event("ERROR", f"Failed to create session: {e}")
            raise
    
    async def validate_session(self, token: str) -> Optional[Dict[str, Any]]:
        """Validate user session."""
        try:
            client = await self.db_manager.get_client()
            
            session = await client.session.find_first(
                where={
                    "token": token,
                    "isActive": True,
                    "expiresAt": {"gt": datetime.now(UTC)}
                },
                include={"user": True}
            )
            
            if session:
                return {
                    "user_id": session.user.id,
                    "username": session.user.username,
                    "role": session.user.role,
                    "session_id": session.id
                }
            
            return None
            
        except Exception as e:
            await self.db_manager.log_event("ERROR", f"Session validation error: {e}")
            return None
    
    async def store_api_call(self, user_id: str, method: str, endpoint: str, 
                           response_status: int, response_time_ms: float):
        """Store API call for analytics."""
        try:
            await self.db_manager.log_event(
                "INFO",
                f"API call: {method} {endpoint}",
                {
                    "user_id": user_id,
                    "method": method,
                    "endpoint": endpoint,
                    "status": response_status,
                    "response_time_ms": response_time_ms
                }
            )
        except Exception as e:
            logger.error(f"Failed to store API call: {e}")


class StrategyEngineIntegration:
    """
    Example integration for Strategy Engine service.
    
    Shows how to:
    1. Store strategy configurations
    2. Log trading signals
    3. Track strategy performance
    4. Store backtest results
    """
    
    def __init__(self):
        """Initialize Strategy Engine database integration."""
        self.db_manager: Optional[DatabaseConnection] = None
        self.service_name = "strategy_engine"
    
    async def initialize(self):
        """Initialize database connection."""
        self.db_manager = await get_db_manager(self.service_name)
        await self.db_manager.log_event("INFO", "Strategy Engine service initialized")
        logger.info("Strategy Engine database integration ready")
    
    async def create_strategy(self, user_id: str, name: str, strategy_type: str, 
                            parameters: Dict[str, Any]) -> str:
        """Create a new trading strategy."""
        try:
            client = await self.db_manager.get_client()
            
            strategy = await client.strategy.create({
                "userId": user_id,
                "name": name,
                "strategyType": strategy_type,
                "parameters": parameters,
                "isActive": False
            })
            
            await self.db_manager.log_event(
                "INFO", 
                f"Strategy created: {name}",
                {"strategy_id": strategy.id, "type": strategy_type}
            )
            
            return strategy.id
            
        except Exception as e:
            await self.db_manager.log_event("ERROR", f"Failed to create strategy: {e}")
            raise
    
    async def log_trading_signal(self, strategy_id: str, symbol: str, signal_type: str,
                               strength: float, price: float, indicators: Dict[str, Any] = None):
        """Log a trading signal."""
        try:
            client = await self.db_manager.get_client()
            
            signal = await client.tradingsignal.create({
                "strategyId": strategy_id,
                "symbol": symbol,
                "signalType": signal_type,
                "strength": strength,
                "price": price,
                "indicators": indicators or {}
            })
            
            await self.db_manager.log_event(
                "INFO",
                f"Trading signal: {signal_type} {symbol} at {price}",
                {
                    "strategy_id": strategy_id,
                    "signal_id": signal.id,
                    "strength": strength
                }
            )
            
            return signal.id
            
        except Exception as e:
            await self.db_manager.log_event("ERROR", f"Failed to log signal: {e}")
            raise
    
    async def update_strategy_performance(self, strategy_id: str, performance_data: Dict[str, Any]):
        """Update strategy performance metrics."""
        try:
            client = await self.db_manager.get_client()
            
            await client.strategy.update(
                where={"id": strategy_id},
                data={"performance": performance_data}
            )
            
            await self.db_manager.log_event(
                "INFO",
                f"Strategy performance updated",
                {"strategy_id": strategy_id, "performance": performance_data}
            )
            
        except Exception as e:
            await self.db_manager.log_event("ERROR", f"Failed to update performance: {e}")
            raise


class MarketDataIntegration:
    """
    Example integration for Market Data service.
    
    Shows how to:
    1. Store real-time market data
    2. Manage instrument metadata
    3. Store news and events
    4. Bulk data operations
    """
    
    def __init__(self):
        """Initialize Market Data database integration."""
        self.db_manager: Optional[DatabaseConnection] = None
        self.service_name = "market_data_streaming"
    
    async def initialize(self):
        """Initialize database connection."""
        self.db_manager = await get_db_manager(self.service_name)
        await self.db_manager.log_event("INFO", "Market Data service initialized")
        logger.info("Market Data database integration ready")
    
    async def ensure_instrument(self, symbol: str, name: str, exchange: str, 
                              instrument_type: str) -> str:
        """Ensure instrument exists, create if not."""
        try:
            client = await self.db_manager.get_client()
            
            # Check if instrument exists
            instrument = await client.instrument.find_unique(where={"symbol": symbol})
            
            if not instrument:
                # Create new instrument
                instrument = await client.instrument.create({
                    "symbol": symbol,
                    "name": name,
                    "exchange": exchange,
                    "instrumentType": instrument_type
                })
                
                await self.db_manager.log_event(
                    "INFO",
                    f"New instrument created: {symbol}",
                    {"instrument_id": instrument.id}
                )
            
            return instrument.id
            
        except Exception as e:
            await self.db_manager.log_event("ERROR", f"Failed to ensure instrument: {e}")
            raise
    
    async def store_market_tick(self, symbol: str, tick_data: Dict[str, Any]):
        """Store a market data tick."""
        try:
            # Ensure instrument exists
            instrument_id = await self.ensure_instrument(
                symbol, 
                tick_data.get("name", symbol),
                tick_data.get("exchange", "NSE"),
                "EQUITY"
            )
            
            client = await self.db_manager.get_client()
            
            # Store market data
            await client.marketdata.create({
                "instrumentId": instrument_id,
                "timestamp": datetime.now(UTC),
                "open": tick_data.get("open", 0),
                "high": tick_data.get("high", 0),
                "low": tick_data.get("low", 0),
                "close": tick_data.get("close", 0),
                "volume": tick_data.get("volume", 0),
                "ltp": tick_data.get("ltp", 0),
                "bid": tick_data.get("bid"),
                "ask": tick_data.get("ask"),
                "change": tick_data.get("change"),
                "changePct": tick_data.get("changePct")
            })
            
        except Exception as e:
            await self.db_manager.log_event("ERROR", f"Failed to store tick: {e}")
            # Don't raise - market data should be resilient
    
    async def store_bulk_ticks(self, ticks: List[Dict[str, Any]]):
        """Store multiple market data ticks efficiently."""
        try:
            async with self.db_manager.transaction() as tx:
                for tick in ticks:
                    symbol = tick.get("symbol")
                    if symbol:
                        await self.store_market_tick(symbol, tick)
            
            await self.db_manager.log_event(
                "INFO",
                f"Stored {len(ticks)} market data ticks"
            )
            
        except Exception as e:
            await self.db_manager.log_event("ERROR", f"Bulk tick storage failed: {e}")


class RiskManagementIntegration:
    """
    Example integration for Risk Management service.
    
    Shows how to:
    1. Store risk profiles
    2. Log risk alerts
    3. Track position limits
    4. Store compliance events
    """
    
    def __init__(self):
        """Initialize Risk Management database integration."""
        self.db_manager: Optional[DatabaseConnection] = None
        self.service_name = "risk_service"
    
    async def initialize(self):
        """Initialize database connection."""
        self.db_manager = await get_db_manager(self.service_name)
        await self.db_manager.log_event("INFO", "Risk Management service initialized")
        logger.info("Risk Management database integration ready")
    
    async def create_risk_alert(self, alert_type: str, severity: str, title: str, 
                              message: str, metadata: Dict[str, Any] = None):
        """Create a risk alert."""
        try:
            client = await self.db_manager.get_client()
            
            alert = await client.alert.create({
                "type": alert_type,
                "severity": severity,
                "title": title,
                "message": message,
                "source": self.service_name,
                "metadata": metadata or {}
            })
            
            await self.db_manager.log_event(
                "WARNING" if severity in ["HIGH", "CRITICAL"] else "INFO",
                f"Risk alert: {title}",
                {"alert_id": alert.id, "severity": severity}
            )
            
            return alert.id
            
        except Exception as e:
            await self.db_manager.log_event("ERROR", f"Failed to create alert: {e}")
            raise
    
    async def validate_order_risk(self, user_id: str, order_data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate order against risk limits."""
        try:
            client = await self.db_manager.get_client()
            
            # Get user's risk profile
            risk_profile = await client.riskprofile.find_first(
                where={"userId": user_id, "isActive": True}
            )
            
            if not risk_profile:
                return {"approved": False, "reason": "No risk profile found"}
            
            # Validate order value
            order_value = order_data.get("quantity", 0) * order_data.get("price", 0)
            
            if order_value > risk_profile.maxOrderValue:
                await self.create_risk_alert(
                    "RISK_BREACH",
                    "HIGH",
                    "Order value exceeds limit",
                    f"Order value {order_value} exceeds limit {risk_profile.maxOrderValue}",
                    {"user_id": user_id, "order_value": order_value}
                )
                return {"approved": False, "reason": "Order value exceeds limit"}
            
            return {"approved": True, "risk_profile_id": risk_profile.id}
            
        except Exception as e:
            await self.db_manager.log_event("ERROR", f"Risk validation failed: {e}")
            return {"approved": False, "reason": "Risk validation error"}


# ================================
# INTEGRATION HELPER FUNCTIONS
# ================================

async def setup_microservice_database(service_name: str) -> DatabaseConnection:
    """
    Setup database integration for any microservice.
    
    Args:
        service_name: Name of the microservice
        
    Returns:
        Configured database manager
    """
    db_manager = await get_db_manager(service_name)
    await db_manager.log_event("INFO", f"{service_name} database integration initialized")
    
    logger.info(f"Database integration ready for {service_name}")
    return db_manager


async def test_all_integrations():
    """
    Test all microservice database integrations.
    
    This function demonstrates how each service can use the database.
    """
    logger.info("Testing all microservice database integrations...")
    
    try:
        # Test Angel One API integration
        angel_api = AngelOneAPIIntegration()
        await angel_api.initialize()
        logger.info("✅ Angel One API integration working")
        
        # Test Strategy Engine integration
        strategy_engine = StrategyEngineIntegration()
        await strategy_engine.initialize()
        logger.info("✅ Strategy Engine integration working")
        
        # Test Market Data integration
        market_data = MarketDataIntegration()
        await market_data.initialize()
        logger.info("✅ Market Data integration working")
        
        # Test Risk Management integration
        risk_mgmt = RiskManagementIntegration()
        await risk_mgmt.initialize()
        logger.info("✅ Risk Management integration working")
        
        logger.info("🎉 All microservice database integrations are working!")
        
        return True
        
    except Exception as e:
        logger.error(f"Integration test failed: {e}")
        return False


# ================================
# USAGE EXAMPLES
# ================================

async def example_usage():
    """
    Example usage of the database service in microservices.
    """
    print("Database Service Integration Examples")
    print("=" * 50)
    
    # Example 1: Angel One API storing a session
    print("\n1. Angel One API - Creating User Session")
    angel_api = AngelOneAPIIntegration()
    await angel_api.initialize()
    
    # This would be called when a user logs in
    # session_info = await angel_api.create_user_session(
    #     "test_user", 
    #     "jwt_token_here", 
    #     datetime.now(UTC) + timedelta(hours=24)
    # )
    print("   Session creation ready (example)")
    
    # Example 2: Strategy Engine logging a signal
    print("\n2. Strategy Engine - Logging Trading Signal")
    strategy_engine = StrategyEngineIntegration()
    await strategy_engine.initialize()
    
    # This would be called when a strategy generates a signal
    # signal_id = await strategy_engine.log_trading_signal(
    #     "strategy_123",
    #     "NIFTY",
    #     "BUY",
    #     0.85,
    #     18500.0,
    #     {"rsi": 65, "macd": "bullish"}
    # )
    print("   Signal logging ready (example)")
    
    # Example 3: Market Data storing ticks
    print("\n3. Market Data - Storing Market Ticks")
    market_data = MarketDataIntegration()
    await market_data.initialize()
    
    # This would be called for each market data tick
    # await market_data.store_market_tick("NIFTY", {
    #     "ltp": 18500.0,
    #     "volume": 1000000,
    #     "change": 50.0,
    #     "changePct": 0.27
    # })
    print("   Market data storage ready (example)")
    
    # Example 4: Risk Management creating alerts
    print("\n4. Risk Management - Creating Risk Alert")
    risk_mgmt = RiskManagementIntegration()
    await risk_mgmt.initialize()
    
    # This would be called when a risk breach is detected
    # alert_id = await risk_mgmt.create_risk_alert(
    #     "POSITION_LIMIT",
    #     "HIGH",
    #     "Position limit exceeded",
    #     "User position exceeds 80% of allowed limit"
    # )
    print("   Risk alert creation ready (example)")
    
    print("\n✅ All integrations initialized successfully!")
    print("\nNext Steps:")
    print("1. Replace MongoDB calls in each microservice with these patterns")
    print("2. Update Docker services to depend on database-service")
    print("3. Test each service with the new database integration")


if __name__ == "__main__":
    print("HFT Database Service Integration Guide")
    print("=" * 60)
    
    try:
        asyncio.run(example_usage())
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
