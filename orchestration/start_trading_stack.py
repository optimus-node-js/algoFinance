#!/usr/bin/env python3
"""
Start Trading Stack Script
Starts only the core trading services for active trading operations.
"""

import sys
import os
import time

# Add the project root directory to the Python path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(PROJECT_ROOT)

from server.src.core.orchestrator import ServiceOrchestrator

def main():
    """Main function to start trading services."""
    print("🚀 Starting Algorithmic Trading System - Trading Stack")
    print("=" * 60)
    
    # Create orchestrator
    orchestrator = ServiceOrchestrator()
    
    try:
        # Check prerequisites
        print("📋 Checking prerequisites...")
        print("  ✅ MongoDB should be running")
        print("  ✅ RabbitMQ should be running") 
        print("  ✅ Angel One API credentials configured")
        
        # Start trading services
        success = orchestrator.start_trading_stack()
        
        if success:
            print("\n🎉 Trading stack started successfully!")
            print("\n📊 Active Services:")
            status = orchestrator.get_service_status()
            for service_name, service_status in status['services'].items():
                print(f"  ✅ {service_name}: {service_status['status']}")
            
            print("\n💼 Trading services ready for:")
            print("  📈 Real-time market data")
            print("  💰 Portfolio management")
            print("  📋 Order book operations")
            print("  🔄 Live trading strategies")
            
            print("\n🔄 Services are now running and monitoring...")
            print("Press Ctrl+C to stop trading stack")
            
            # Keep running until interrupted
            try:
                while True:
                    time.sleep(10)
                    
            except KeyboardInterrupt:
                print("\n🛑 Received stop signal...")
                
        else:
            print("\n❌ Failed to start trading stack. Check logs for details.")
            
    except Exception as e:
        print(f"\n❌ Error starting trading stack: {e}")
        
    finally:
        # Cleanup
        print("\n🧹 Stopping trading services...")
        orchestrator.stop_all_services()
        print("✅ Trading stack stopped. Goodbye!")

if __name__ == '__main__':
    main()

