#!/usr/bin/env python3
"""
All Services Launcher
=====================

Starts all microservices concurrently for the AI Trading System:
1. Stock Discovery Service
2. Market Data Service
3. Portfolio Management Service
4. Order Book Service
5. Risk Management Service
6. Trade Execution Service (if enabled)

Each service runs independently and communicates via RabbitMQ.
"""

import asyncio
import sys
import os
import signal
import logging
from datetime import datetime
from typing import List, Dict, Any

# Add project root to path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.join(current_dir, '..', '..')
sys.path.insert(0, project_root)

# Import services
try:
    from server.src.services.stock_discovery.stock_discovery_service import StockDiscoveryService
    from server.src.services.market_data.market_data_service import MarketDataService
    from server.src.services.portfolio_management.portfolio_service import PortfolioService
    from server.src.services.order_book.order_book_service import OrderBookService
    from server.src.services.risk_management.risk_service import RiskManagementService
    from server.src.logging.advanced_logger import advanced_logger
    SERVICES_AVAILABLE = True
except ImportError as e:
    print(f"⚠️ Could not import all services: {e}")
    SERVICES_AVAILABLE = False

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(name)s - %(message)s'
)
logger = logging.getLogger(__name__)

class ServiceManager:
    """Manages all microservices lifecycle."""
    
    def __init__(self):
        self.services: Dict[str, Any] = {}
        self.service_tasks: List[asyncio.Task] = []
        self.running = False
        
        # Configure signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals."""
        logger.info(f"🛑 Received signal {signum}, initiating graceful shutdown...")
        self.running = False
    
    async def start_all_services(self):
        """Start all microservices concurrently."""
        if not SERVICES_AVAILABLE:
            logger.error("❌ Services not available, cannot start")
            return
        
        self.running = True
        start_time = datetime.now()
        
        print("🚀 STARTING ALL MICROSERVICES")
        print("=" * 60)
        print(f"⏰ Start Time: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print("🔗 Services will communicate via RabbitMQ")
        print("📊 Each service will log to its dedicated log file")
        print("=" * 60)
        
        try:
            # Initialize all services
            await self._initialize_services()
            
            # Start all services concurrently
            await self._start_services_concurrently()
            
            # Log successful startup
            startup_time = (datetime.now() - start_time).total_seconds()
            logger.info(f"✅ All services started successfully in {startup_time:.2f}s")
            
            # Monitor services
            await self._monitor_services()
            
        except Exception as e:
            logger.error(f"❌ Error starting services: {e}")
        finally:
            await self._shutdown_all_services()
    
    async def _initialize_services(self):
        """Initialize all services."""
        logger.info("🔧 Initializing all services...")
        
        service_configs = [
            ("stock_discovery", StockDiscoveryService, "📊 Stock Discovery"),
            ("market_data", MarketDataService, "📈 Market Data"),
            ("portfolio_management", PortfolioService, "💼 Portfolio Management"),
            ("order_book", OrderBookService, "📋 Order Book"),
            ("risk_management", RiskManagementService, "🛡️ Risk Management"),
        ]
        
        for service_name, service_class, description in service_configs:
            try:
                logger.info(f"🔧 Initializing {description} Service...")
                service_instance = service_class()
                self.services[service_name] = service_instance
                logger.info(f"✅ {description} Service initialized")
            except Exception as e:
                logger.error(f"❌ Failed to initialize {description} Service: {e}")
    
    async def _start_services_concurrently(self):
        """Start all services as concurrent tasks."""
        logger.info("🚀 Starting services concurrently...")
        
        # Create tasks for each service
        service_runners = [
            ("stock_discovery", self._run_stock_discovery_service),
            ("market_data", self._run_market_data_service),
            ("portfolio_management", self._run_portfolio_service),
            ("order_book", self._run_order_book_service),
            ("risk_management", self._run_risk_service),
        ]
        
        for service_name, runner_func in service_runners:
            if service_name in self.services:
                task = asyncio.create_task(runner_func())
                task.set_name(f"Service-{service_name}")
                self.service_tasks.append(task)
                logger.info(f"🚀 Started {service_name} service task")
    
    async def _run_stock_discovery_service(self):
        """Run stock discovery service."""
        try:
            service = self.services.get("stock_discovery")
            if service:
                advanced_logger.info("STOCK_DISCOVERY", "🚀 Stock Discovery Service starting...")
                
                # Discover stocks on startup
                await service.discover_all_stocks()
                
                # Keep service running for periodic discovery
                while self.running:
                    await asyncio.sleep(3600)  # Rediscover every hour
                    if self.running:
                        await service.discover_all_stocks()
                        
        except Exception as e:
            advanced_logger.error("STOCK_DISCOVERY", f"❌ Stock Discovery Service error: {e}", {'error': str(e)})
    
    async def _run_market_data_service(self):
        """Run market data service."""
        try:
            service = self.services.get("market_data")
            if service:
                advanced_logger.info("MARKET_DATA", "🚀 Market Data Service starting...")
                
                # Start market data processing
                await service.start_service()
                
        except Exception as e:
            advanced_logger.error("MARKET_DATA", f"❌ Market Data Service error: {e}", {'error': str(e)})
    
    async def _run_portfolio_service(self):
        """Run portfolio management service."""
        try:
            service = self.services.get("portfolio_management")
            if service:
                advanced_logger.info("PORTFOLIO", "🚀 Portfolio Service starting...")
                
                # Start portfolio management
                await service.start_service()
                
        except Exception as e:
            advanced_logger.error("PORTFOLIO", f"❌ Portfolio Service error: {e}", {'error': str(e)})
    
    async def _run_order_book_service(self):
        """Run order book service."""
        try:
            service = self.services.get("order_book")
            if service:
                advanced_logger.info("ORDER_BOOK", "🚀 Order Book Service starting...")
                
                # Start order book management
                await service.start_service()
                
        except Exception as e:
            advanced_logger.error("ORDER_BOOK", f"❌ Order Book Service error: {e}", {'error': str(e)})
    
    async def _run_risk_service(self):
        """Run risk management service."""
        try:
            service = self.services.get("risk_management")
            if service:
                advanced_logger.info("RISK_MANAGEMENT", "🚀 Risk Management Service starting...")
                
                # Start risk monitoring
                await service.start_service()
                
        except Exception as e:
            advanced_logger.error("RISK_MANAGEMENT", f"❌ Risk Management Service error: {e}", {'error': str(e)})
    
    async def _monitor_services(self):
        """Monitor all running services."""
        logger.info("👀 Monitoring all services...")
        
        while self.running:
            # Check service health
            alive_services = sum(1 for task in self.service_tasks if not task.done())
            logger.info(f"📊 Services Status: {alive_services}/{len(self.service_tasks)} running")
            
            # Wait before next check
            await asyncio.sleep(30)
    
    async def _shutdown_all_services(self):
        """Gracefully shutdown all services."""
        logger.info("🛑 Shutting down all services...")
        
        # Cancel all service tasks
        for task in self.service_tasks:
            if not task.done():
                task.cancel()
        
        # Wait for tasks to complete
        if self.service_tasks:
            await asyncio.gather(*self.service_tasks, return_exceptions=True)
        
        # Cleanup services
        for service_name, service in self.services.items():
            try:
                if hasattr(service, 'cleanup'):
                    await service.cleanup()
                logger.info(f"✅ {service_name} service shutdown complete")
            except Exception as e:
                logger.error(f"❌ Error shutting down {service_name}: {e}")
        
        logger.info("✅ All services shutdown complete")

async def main():
    """Main entry point."""
    print("🤖 AI Trading System - All Services Launcher")
    print("=" * 60)
    
    service_manager = ServiceManager()
    await service_manager.start_all_services()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n🛑 Shutdown initiated by user")
    except Exception as e:
        print(f"❌ Fatal error: {e}")
