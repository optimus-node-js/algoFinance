import sys
import os
import time
import threading
import signal
from typing import Dict, List, Optional
import subprocess

# Add the project root directory to the Python path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
sys.path.append(PROJECT_ROOT)

class ServiceOrchestrator:
    """
    Orchestrates multiple microservices for the algorithmic trading system.
    Manages service startup, shutdown, health monitoring, and inter-service communication.
    """
    
    def __init__(self):
        self.services = {}
        self.service_processes = {}
        self.is_running = False
        self.health_check_interval = 30  # seconds
        self.health_monitor_thread = None
        
        # Service configurations
        self.service_configs = {
            'portfolio_service': {
                'module': 'server.src.services.portfolio_management.portfolio_service',
                'class': 'PortfolioService',
                'dependencies': ['rabbitmq', 'mongodb'],
                'critical': True,
                'restart_on_failure': True
            },
            'order_book_service': {
                'module': 'server.src.services.order_book.order_book_service', 
                'class': 'OrderBookService',
                'dependencies': ['rabbitmq', 'mongodb'],
                'critical': True,
                'restart_on_failure': True
            },
            'market_data_service': {
                'module': 'server.src.services.market_data.market_data_service',
                'class': 'MarketDataService', 
                'dependencies': ['rabbitmq', 'mongodb'],
                'critical': True,
                'restart_on_failure': True
            },
            'data_ingestion_service': {
                'module': 'server.src.data_ingestion.stream',
                'class': 'DataStreamer',
                'dependencies': ['rabbitmq', 'mongodb', 'market_data_service'],
                'critical': True,
                'restart_on_failure': True
            },
            'risk_management_service': {
                'module': 'server.src.services.risk_management.risk_service',
                'class': 'RiskManagementService',
                'dependencies': ['rabbitmq', 'mongodb'],
                'critical': True,
                'restart_on_failure': True
            }
        }
    
    def start_service(self, service_name: str) -> bool:
        """
        Start a specific service.
        Args:
            service_name: Name of the service to start
        Returns:
            bool: True if service started successfully
        """
        if service_name in self.services:
            print(f"⚠️ Service {service_name} is already running")
            return False
            
        config = self.service_configs.get(service_name)
        if not config:
            print(f"❌ Unknown service: {service_name}")
            return False
        
        try:
            print(f"🚀 Starting {service_name}...")
            
            # Import the service module
            module_path = config['module']
            class_name = config['class']
            
            # Dynamic import
            parts = module_path.split('.')
            module = __import__(module_path, fromlist=[class_name])
            service_class = getattr(module, class_name)
            
            # Instantiate the service
            service_instance = service_class()
            self.services[service_name] = {
                'instance': service_instance,
                'config': config,
                'start_time': time.time(),
                'status': 'running'
            }
            
            print(f"✅ {service_name} started successfully")
            return True
            
        except Exception as e:
            print(f"❌ Failed to start {service_name}: {e}")
            return False
    
    def stop_service(self, service_name: str) -> bool:
        """
        Stop a specific service.
        Args:
            service_name: Name of the service to stop
        Returns:
            bool: True if service stopped successfully
        """
        if service_name not in self.services:
            print(f"⚠️ Service {service_name} is not running")
            return False
        
        try:
            print(f"🛑 Stopping {service_name}...")
            
            service_info = self.services[service_name]
            service_instance = service_info['instance']
            
            # Call close method if available
            if hasattr(service_instance, 'close'):
                service_instance.close()
            
            # Remove from services
            del self.services[service_name]
            
            print(f"✅ {service_name} stopped successfully")
            return True
            
        except Exception as e:
            print(f"❌ Failed to stop {service_name}: {e}")
            return False
    
    def start_all_services(self) -> bool:
        """
        Start all configured services in dependency order.
        Returns:
            bool: True if all services started successfully
        """
        print("🚀 Starting all services...")
        
        # Start services in dependency order
        startup_order = [
            'portfolio_service',
            'order_book_service', 
            'market_data_service',
            'risk_management_service',
            'data_ingestion_service'
        ]
        
        failed_services = []
        
        for service_name in startup_order:
            if not self.start_service(service_name):
                failed_services.append(service_name)
                # Continue starting other services even if one fails
        
        if failed_services:
            print(f"❌ Failed to start services: {failed_services}")
            return False
        
        self.is_running = True
        self._start_health_monitoring()
        
        print("✅ All services started successfully")
        return True
    
    def stop_all_services(self) -> bool:
        """
        Stop all running services.
        Returns:
            bool: True if all services stopped successfully
        """
        print("🛑 Stopping all services...")
        
        self.is_running = False
        
        # Stop health monitoring
        if self.health_monitor_thread and self.health_monitor_thread.is_alive():
            self.health_monitor_thread.join(timeout=5)
        
        # Stop services in reverse order
        service_names = list(self.services.keys())
        service_names.reverse()
        
        failed_services = []
        
        for service_name in service_names:
            if not self.stop_service(service_name):
                failed_services.append(service_name)
        
        if failed_services:
            print(f"❌ Failed to stop services: {failed_services}")
            return False
        
        print("✅ All services stopped successfully")
        return True
    
    def get_service_status(self) -> Dict:
        """
        Get status of all services.
        Returns:
            Dict: Service status information
        """
        status = {
            'orchestrator_running': self.is_running,
            'total_services': len(self.services),
            'services': {}
        }
        
        for service_name, service_info in self.services.items():
            uptime = time.time() - service_info['start_time']
            status['services'][service_name] = {
                'status': service_info['status'],
                'uptime_seconds': uptime,
                'uptime_formatted': f"{uptime//3600:.0f}h {(uptime%3600)//60:.0f}m {uptime%60:.0f}s"
            }
        
        return status
    
    def _start_health_monitoring(self):
        """Start health monitoring thread."""
        def health_monitor():
            while self.is_running:
                try:
                    self._check_service_health()
                    time.sleep(self.health_check_interval)
                except Exception as e:
                    print(f"❌ Error in health monitoring: {e}")
                    time.sleep(10)
        
        self.health_monitor_thread = threading.Thread(target=health_monitor, daemon=True)
        self.health_monitor_thread.start()
        print("✅ Health monitoring started")
    
    def _check_service_health(self):
        """Check health of all services."""
        for service_name, service_info in self.services.items():
            try:
                service_instance = service_info['instance']
                
                # Basic health check - verify instance is still alive
                if hasattr(service_instance, 'db') and service_instance.db is not None:
                    service_info['status'] = 'healthy'
                else:
                    service_info['status'] = 'unhealthy'
                    print(f"⚠️ Service {service_name} appears unhealthy")
                    
            except Exception as e:
                service_info['status'] = 'error'
                print(f"❌ Health check failed for {service_name}: {e}")
    
    def start_trading_stack(self) -> bool:
        """
        Start only trading-related services.
        Returns:
            bool: True if trading stack started successfully
        """
        print("🚀 Starting trading stack...")
        
        trading_services = [
            'market_data_service',
            'portfolio_service', 
            'order_book_service',
            'risk_management_service'
        ]
        
        failed_services = []
        
        for service_name in trading_services:
            if not self.start_service(service_name):
                failed_services.append(service_name)
        
        if failed_services:
            print(f"❌ Failed to start trading services: {failed_services}")
            return False
        
        self.is_running = True
        self._start_health_monitoring()
        
        print("✅ Trading stack started successfully")
        return True
    
    def start_data_stack(self) -> bool:
        """
        Start only data-related services.
        Returns:
            bool: True if data stack started successfully
        """
        print("🚀 Starting data stack...")
        
        data_services = [
            'market_data_service',
            'data_ingestion_service'
        ]
        
        failed_services = []
        
        for service_name in data_services:
            if not self.start_service(service_name):
                failed_services.append(service_name)
        
        if failed_services:
            print(f"❌ Failed to start data services: {failed_services}")
            return False
        
        self.is_running = True
        self._start_health_monitoring()
        
        print("✅ Data stack started successfully")
        return True
    
    def restart_service(self, service_name: str) -> bool:
        """
        Restart a specific service.
        Args:
            service_name: Name of the service to restart
        Returns:
            bool: True if service restarted successfully
        """
        print(f"🔄 Restarting {service_name}...")
        
        # Stop the service
        self.stop_service(service_name)
        
        # Wait a moment
        time.sleep(2)
        
        # Start the service
        return self.start_service(service_name)


def signal_handler(sig, frame):
    """Handle shutdown signals gracefully."""
    print("\n🛑 Received shutdown signal, stopping all services...")
    global orchestrator
    if orchestrator:
        orchestrator.stop_all_services()
    sys.exit(0)


# Global orchestrator instance
orchestrator = None

if __name__ == '__main__':
    # Setup signal handlers for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Create orchestrator
    orchestrator = ServiceOrchestrator()
    
    print("🎼 Service Orchestrator Started")
    print("Available commands:")
    print("  1. Start all services")
    print("  2. Start trading stack")
    print("  3. Start data stack") 
    print("  4. Stop all services")
    print("  5. Service status")
    print("  6. Exit")
    
    try:
        while True:
            choice = input("\nEnter your choice (1-6): ").strip()
            
            if choice == '1':
                orchestrator.start_all_services()
            elif choice == '2':
                orchestrator.start_trading_stack()
            elif choice == '3':
                orchestrator.start_data_stack()
            elif choice == '4':
                orchestrator.stop_all_services()
            elif choice == '5':
                status = orchestrator.get_service_status()
                print("\n📊 Service Status:")
                print(f"Orchestrator Running: {status['orchestrator_running']}")
                print(f"Total Services: {status['total_services']}")
                for service_name, service_status in status['services'].items():
                    print(f"  {service_name}: {service_status['status']} (uptime: {service_status['uptime_formatted']})")
            elif choice == '6':
                orchestrator.stop_all_services()
                break
            else:
                print("❌ Invalid choice, please try again")
                
    except KeyboardInterrupt:
        print("\n🛑 Shutting down...")
        orchestrator.stop_all_services()
