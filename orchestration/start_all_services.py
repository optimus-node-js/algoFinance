#!/usr/bin/env python3
"""
Start All Services Script
Orchestrates startup of all microservices for the algorithmic trading system.
"""

import sys
import os
import time

# Add the project root directory to the Python path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(PROJECT_ROOT)

from server.src.core.orchestrator import ServiceOrchestrator

def main():
    """Main function to start all services."""
    print("🚀 Starting Algorithmic Trading System - All Services")
    print("=" * 60)
    
    # Create orchestrator
    orchestrator = ServiceOrchestrator()
    
    try:
        # Check prerequisites
        print("📋 Checking prerequisites...")
        print("  ✅ MongoDB should be running")
        print("  ✅ RabbitMQ should be running")
        print("  ✅ Angel One API credentials configured")
        
        # Start all services
        success = orchestrator.start_all_services()
        
        if success:
            print("\n🎉 All services started successfully!")
            print("\n📊 Service Status:")
            status = orchestrator.get_service_status()
            for service_name, service_status in status['services'].items():
                print(f"  ✅ {service_name}: {service_status['status']}")
            
            print("\n🔄 Services are now running and monitoring...")
            print("Press Ctrl+C to stop all services")
            
            # Keep running until interrupted
            try:
                while True:
                    time.sleep(10)
                    # Optional: Print status updates every minute
                    
            except KeyboardInterrupt:
                print("\n🛑 Received stop signal...")
                
        else:
            print("\n❌ Failed to start some services. Check logs for details.")
            
    except Exception as e:
        print(f"\n❌ Error starting services: {e}")
        
    finally:
        # Cleanup
        print("\n🧹 Stopping all services...")
        orchestrator.stop_all_services()
        print("✅ All services stopped. Goodbye!")

if __name__ == '__main__':
    main()

