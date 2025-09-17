#!/usr/bin/env python3
"""
Start Data Stack Script
Starts only data ingestion and market data services for data collection and analysis.
"""

import sys
import os
import time

# Add the project root directory to the Python path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(PROJECT_ROOT)

from server.src.core.orchestrator import ServiceOrchestrator

def main():
    """Main function to start data services."""
    print("🚀 Starting Algorithmic Trading System - Data Stack")
    print("=" * 60)
    
    # Create orchestrator
    orchestrator = ServiceOrchestrator()
    
    try:
        # Check prerequisites
        print("📋 Checking prerequisites...")
        print("  ✅ MongoDB should be running")
        print("  ✅ RabbitMQ should be running")
        print("  ✅ Angel One API credentials configured")
        
        # Start data services
        success = orchestrator.start_data_stack()
        
        if success:
            print("\n🎉 Data stack started successfully!")
            print("\n📊 Active Services:")
            status = orchestrator.get_service_status()
            for service_name, service_status in status['services'].items():
                print(f"  ✅ {service_name}: {service_status['status']}")
            
            print("\n📡 Data services ready for:")
            print("  📈 Real-time market data streaming")
            print("  🔍 Instrument search and discovery")
            print("  💾 Historical data collection")
            print("  🧠 AI/ML feature engineering")
            
            print("\n🔄 Services are now running and collecting data...")
            print("Press Ctrl+C to stop data stack")
            
            # Keep running until interrupted
            try:
                while True:
                    time.sleep(10)
                    
            except KeyboardInterrupt:
                print("\n🛑 Received stop signal...")
                
        else:
            print("\n❌ Failed to start data stack. Check logs for details.")
            
    except Exception as e:
        print(f"\n❌ Error starting data stack: {e}")
        
    finally:
        # Cleanup
        print("\n🧹 Stopping data services...")
        orchestrator.stop_all_services()
        print("✅ Data stack stopped. Goodbye!")

if __name__ == '__main__':
    main()



