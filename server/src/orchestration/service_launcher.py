"""
Service Launcher - Independent Microservices Orchestration
=========================================================

Launches all 9 microservices independently with proper RabbitMQ communication.
Each service runs in its own process/thread and communicates asynchronously.

Services:
1. Message Broker Service
2. Stock Discovery Service  
3. Trade Execution Service
4. Portfolio Management Service
5. Order Book Service
6. Market Data Service
7. Risk Management Service
8. Strategy Service
9. Data Ingestion Service

Author: AI Trading System
Version: 1.0.0
"""

import asyncio
import subprocess
import threading
import time
import signal
import sys
import os
from typing import Dict, List, Optional
from dataclasses import dataclass
from datetime import datetime

# Add project root to path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
sys.path.append(PROJECT_ROOT)

try:
    from log_system.advanced_logger import get_logger
    from monitoring.live_console_monitor import get_live_monitor
    DEPENDENCIES_AVAILABLE = True
except ImportError:
    DEPENDENCIES_AVAILABLE = False

@dataclass
class ServiceConfig:
    """Configuration for each microservice."""
    name: str
    module_path: str
    class_name: str
    dependencies: List[str]
    critical: bool = True
    restart_on_failure: bool = True
    max_restarts: int = 3
    health_check_interval: int = 30

class ServiceLauncher:
    """
    Launches and manages all microservices independently.
    
    Features:
    - Independent process/thread management
    - Health monitoring and auto-restart
    - RabbitMQ communication coordination
    - Service dependency management
    - Real-time status monitoring
    """
    
    def __init__(self):
        """Initialize service launcher."""
        self.logger = get_logger() if DEPENDENCIES_AVAILABLE else None
        self.live_monitor = get_live_monitor() if DEPENDENCIES_AVAILABLE else None
        
        # Service configurations
        self.services = {
            'message_broker': ServiceConfig(
                name="Message Broker Service",
                module_path="server.src.core.message_broker",
                class_name="EnhancedMessageBroker",
                dependencies=[],
                critical=True
            ),
            'stock_discovery': ServiceConfig(
                name="Stock Discovery Service", 
                module_path="server.src.services.stock_discovery.stock_discovery_service",
                class_name="StockDiscoveryService",
                dependencies=['message_broker'],
                critical=True
            ),
            'trade_execution': ServiceConfig(
                name="Trade Execution Service",
                module_path="server.src.trading.execution_engine", 
                class_name="TradeExecutionEngine",
                dependencies=['message_broker'],
                critical=True
            ),
            'portfolio_management': ServiceConfig(
                name="Portfolio Management Service",
                module_path="server.src.services.portfolio_management.portfolio_service",
                class_name="PortfolioService", 
                dependencies=['message_broker'],
                critical=True
            ),
            'order_book': ServiceConfig(
                name="Order Book Service",
                module_path="server.src.services.order_book.order_book_service",
                class_name="OrderBookService",
                dependencies=['message_broker'],
                critical=True
            ),
            'market_data': ServiceConfig(
                name="Market Data Service",
                module_path="server.src.services.market_data.market_data_service", 
                class_name="MarketDataService",
                dependencies=['message_broker'],
                critical=True
            ),
            'risk_management': ServiceConfig(
                name="Risk Management Service",
                module_path="server.src.services.risk_management.risk_service",
                class_name="RiskService",
                dependencies=['message_broker', 'portfolio_management'],
                critical=True
            ),
            'strategy': ServiceConfig(
                name="Strategy Service",
                module_path="server.src.strategies.strategy_service",
                class_name="StrategyService", 
                dependencies=['message_broker', 'market_data'],
                critical=True
            ),
            'data_ingestion': ServiceConfig(
                name="Data Ingestion Service",
                module_path="server.src.data_ingestion.stream",
                class_name="DataStreamer",
                dependencies=['message_broker'],
                critical=False  # Not critical for paper trading
            )
        }
        
        # Service status tracking
        self.service_instances = {}
        self.service_threads = {}
        self.service_status = {}
        self.is_running = False
        
        # Initialize status tracking
        for service_id in self.services.keys():
            self.service_status[service_id] = {
                'status': 'stopped',
                'start_time': None,
                'restart_count': 0,
                'last_health_check': None,
                'errors': []
            }
    
    async def start_all_services(self):
        """Start all microservices in proper dependency order."""
        self.is_running = True
        
        if self.logger:
            self.logger.info("LAUNCHER", "🚀 Starting All Microservices", {
                'total_services': len(self.services),
                'critical_services': sum(1 for s in self.services.values() if s.critical)
            })
        
        # Start services in dependency order
        startup_order = self._calculate_startup_order()
        
        for service_id in startup_order:
            await self._start_service(service_id)
            await asyncio.sleep(2)  # Allow service to initialize
        
        # Start health monitoring
        asyncio.create_task(self._health_monitor_loop())
        
        if self.logger:
            self.logger.info("LAUNCHER", "✅ All Services Started Successfully", {
                'running_services': len([s for s in self.service_status.values() if s['status'] == 'running']),
                'total_services': len(self.services)
            })
    
    def _calculate_startup_order(self) -> List[str]:
        """Calculate proper service startup order based on dependencies."""
        order = []
        remaining = set(self.services.keys())
        
        while remaining:
            # Find services with no unmet dependencies
            ready_services = []
            for service_id in remaining:
                deps = self.services[service_id].dependencies
                if all(dep in order for dep in deps):
                    ready_services.append(service_id)
            
            if not ready_services:
                # Circular dependency or missing service - start remaining anyway
                ready_services = list(remaining)
            
            # Start critical services first
            ready_services.sort(key=lambda x: not self.services[x].critical)
            
            for service_id in ready_services:
                order.append(service_id)
                remaining.remove(service_id)
                break
        
        return order
    
    async def _start_service(self, service_id: str):
        """Start a single microservice."""
        config = self.services[service_id]
        
        try:
            if self.logger:
                self.logger.info("LAUNCHER", f"🔄 Starting {config.name}", {
                    'service_id': service_id,
                    'dependencies': config.dependencies
                })
            
            # Import and instantiate service
            module_parts = config.module_path.split('.')
            module_name = '.'.join(module_parts)
            
            try:
                module = __import__(module_name, fromlist=[config.class_name])
                service_class = getattr(module, config.class_name)
                
                # Create service instance
                if service_id == 'trade_execution':
                    # Special handling for trade execution with config
                    from trading.execution_engine import TradingConfig, TradingMode
                    trading_config = TradingConfig(
                        trading_mode=TradingMode.PAPER,
                        max_positions=50,
                        max_daily_trades=200,
                        risk_per_trade=1000.0
                    )
                    service_instance = service_class(trading_config)
                else:
                    service_instance = service_class()
                
                self.service_instances[service_id] = service_instance
                
                # Start service in separate thread
                def run_service():
                    try:
                        if hasattr(service_instance, 'start_service'):
                            service_instance.start_service()
                        elif hasattr(service_instance, 'run'):
                            service_instance.run()
                        else:
                            # Keep service alive
                            while self.is_running:
                                time.sleep(1)
                    except Exception as e:
                        if self.logger:
                            self.logger.error("LAUNCHER", f"Service {service_id} crashed: {e}")
                        self.service_status[service_id]['status'] = 'crashed'
                        self.service_status[service_id]['errors'].append(str(e))
                
                service_thread = threading.Thread(target=run_service, daemon=True)
                service_thread.start()
                self.service_threads[service_id] = service_thread
                
                # Update status
                self.service_status[service_id].update({
                    'status': 'running',
                    'start_time': datetime.now(),
                    'restart_count': 0
                })
                
                if self.logger:
                    self.logger.info("LAUNCHER", f"✅ {config.name} started successfully", {
                        'service_id': service_id,
                        'thread_id': service_thread.ident
                    })
                
            except ImportError as e:
                if self.logger:
                    self.logger.warning("LAUNCHER", f"⚠️ Could not import {config.name}: {e}")
                self.service_status[service_id]['status'] = 'import_failed'
                
            except Exception as e:
                if self.logger:
                    self.logger.error("LAUNCHER", f"❌ Failed to start {config.name}: {e}")
                self.service_status[service_id]['status'] = 'failed'
                self.service_status[service_id]['errors'].append(str(e))
                
        except Exception as e:
            if self.logger:
                self.logger.error("LAUNCHER", f"❌ Error starting service {service_id}: {e}")
    
    async def _health_monitor_loop(self):
        """Monitor service health and restart if needed."""
        while self.is_running:
            try:
                for service_id, config in self.services.items():
                    await self._check_service_health(service_id, config)
                
                await asyncio.sleep(30)  # Health check every 30 seconds
                
            except Exception as e:
                if self.logger:
                    self.logger.error("LAUNCHER", f"Error in health monitoring: {e}")
                await asyncio.sleep(10)
    
    async def _check_service_health(self, service_id: str, config: ServiceConfig):
        """Check health of a single service."""
        try:
            status = self.service_status[service_id]
            
            # Check if service thread is alive
            thread = self.service_threads.get(service_id)
            if thread and not thread.is_alive():
                if self.logger:
                    self.logger.warning("LAUNCHER", f"⚠️ Service {config.name} thread died")
                
                # Restart if configured
                if config.restart_on_failure and status['restart_count'] < config.max_restarts:
                    await self._restart_service(service_id)
                else:
                    status['status'] = 'failed'
            
            # Update last health check
            status['last_health_check'] = datetime.now()
            
        except Exception as e:
            if self.logger:
                self.logger.error("LAUNCHER", f"Error checking health for {service_id}: {e}")
    
    async def _restart_service(self, service_id: str):
        """Restart a failed service."""
        config = self.services[service_id]
        
        if self.logger:
            self.logger.warning("LAUNCHER", f"🔄 Restarting {config.name}")
        
        # Update restart count
        self.service_status[service_id]['restart_count'] += 1
        
        # Restart service
        await self._start_service(service_id)
    
    def get_service_status_summary(self) -> Dict[str, Any]:
        """Get summary of all service statuses."""
        summary = {
            'total_services': len(self.services),
            'running_services': 0,
            'failed_services': 0,
            'crashed_services': 0,
            'services': {}
        }
        
        for service_id, status in self.service_status.items():
            summary['services'][service_id] = {
                'name': self.services[service_id].name,
                'status': status['status'],
                'uptime': str(datetime.now() - status['start_time']).split('.')[0] if status['start_time'] else 'N/A',
                'restart_count': status['restart_count']
            }
            
            if status['status'] == 'running':
                summary['running_services'] += 1
            elif status['status'] == 'failed':
                summary['failed_services'] += 1
            elif status['status'] == 'crashed':
                summary['crashed_services'] += 1
        
        return summary
    
    def stop_all_services(self):
        """Stop all running services."""
        self.is_running = False
        
        if self.logger:
            self.logger.info("LAUNCHER", "🛑 Stopping all services")
        
        # Stop all service threads
        for service_id, thread in self.service_threads.items():
            if thread.is_alive():
                if self.logger:
                    self.logger.info("LAUNCHER", f"🛑 Stopping {self.services[service_id].name}")
                # Services should handle graceful shutdown
                
        # Close service instances
        for service_id, instance in self.service_instances.items():
            try:
                if hasattr(instance, 'close') or hasattr(instance, 'shutdown'):
                    if hasattr(instance, 'close'):
                        instance.close()
                    else:
                        instance.shutdown()
            except Exception as e:
                if self.logger:
                    self.logger.error("LAUNCHER", f"Error closing {service_id}: {e}")
        
        if self.logger:
            self.logger.info("LAUNCHER", "✅ All services stopped")

# Global launcher instance
_launcher_instance: Optional[ServiceLauncher] = None

def get_service_launcher() -> ServiceLauncher:
    """Get global service launcher instance."""
    global _launcher_instance
    if _launcher_instance is None:
        _launcher_instance = ServiceLauncher()
    return _launcher_instance

async def start_all_microservices():
    """Start all microservices and live monitoring."""
    launcher = get_service_launcher()
    
    print("🚀 STARTING ALL MICROSERVICES")
    print("=" * 50)
    
    # Start all services
    await launcher.start_all_services()
    
    # Show service status
    status = launcher.get_service_status_summary()
    print(f"✅ Services Running: {status['running_services']}/{status['total_services']}")
    
    # Start live monitoring in background
    if DEPENDENCIES_AVAILABLE:
        monitor = get_live_monitor()
        asyncio.create_task(monitor.start_live_monitoring())
    
    return launcher

if __name__ == "__main__":
    async def main():
        launcher = await start_all_microservices()
        
        try:
            # Keep running until interrupted
            while True:
                await asyncio.sleep(10)
                
                # Show periodic status
                status = launcher.get_service_status_summary()
                print(f"📊 Status Update: {status['running_services']}/{status['total_services']} services running")
                
        except KeyboardInterrupt:
            print("\n🛑 Shutting down all services...")
            launcher.stop_all_services()
    
    asyncio.run(main())

