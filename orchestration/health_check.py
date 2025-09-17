#!/usr/bin/env python3
"""
Health Check Script
Monitors the health and status of all running services.
"""

import sys
import os
import time
import requests
from datetime import datetime

# Add the project root directory to the Python path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(PROJECT_ROOT)

from server.src.core.orchestrator import ServiceOrchestrator

def check_infrastructure():
    """Check if required infrastructure is running."""
    print("🔍 Checking Infrastructure...")
    
    infrastructure_status = {
        'mongodb': False,
        'rabbitmq': False
    }
    
    # Check MongoDB
    try:
        from server.src.core.connections import ConnectionManager
        mongo_client = ConnectionManager.get_mongodb_client()
        if mongo_client:
            mongo_client.admin.command('ismaster')
            infrastructure_status['mongodb'] = True
            print("  ✅ MongoDB: Running")
        else:
            print("  ❌ MongoDB: Not accessible")
    except Exception as e:
        print(f"  ❌ MongoDB: Error - {e}")
    
    # Check RabbitMQ
    try:
        import pika
        connection = pika.BlockingConnection(pika.ConnectionParameters('localhost'))
        connection.close()
        infrastructure_status['rabbitmq'] = True
        print("  ✅ RabbitMQ: Running")
    except Exception as e:
        print(f"  ❌ RabbitMQ: Error - {e}")
    
    return infrastructure_status

def check_angel_one_connectivity():
    """Check Angel One API connectivity."""
    print("🔍 Checking Angel One API...")
    
    try:
        from server.src.core.connections import ConnectionManager
        smart_connect = ConnectionManager.get_smartapi_client()
        if smart_connect:
            print("  ✅ Angel One API: Connected")
            return True
        else:
            print("  ❌ Angel One API: Connection failed")
            return False
    except Exception as e:
        print(f"  ❌ Angel One API: Error - {e}")
        return False

def generate_health_report(orchestrator):
    """Generate comprehensive health report."""
    print("\n📊 Health Report")
    print("=" * 50)
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Infrastructure check
    infra_status = check_infrastructure()
    
    # Angel One API check
    api_status = check_angel_one_connectivity()
    
    # Service status
    if orchestrator:
        service_status = orchestrator.get_service_status()
        print(f"\n🎼 Service Orchestrator: {'✅ Running' if service_status['orchestrator_running'] else '❌ Stopped'}")
        print(f"📈 Total Services: {service_status['total_services']}")
        
        if service_status['services']:
            print("\n🛠️ Service Details:")
            for service_name, details in service_status['services'].items():
                status_emoji = "✅" if details['status'] in ['running', 'healthy'] else "❌"
                print(f"  {status_emoji} {service_name}: {details['status']} (uptime: {details['uptime_formatted']})")
        else:
            print("\n⚠️ No services currently running")
    else:
        print("\n❌ Service Orchestrator: Not running")
    
    # Overall system health
    print("\n🏥 Overall System Health:")
    
    total_checks = len(infra_status) + 1  # Infrastructure + API
    passed_checks = sum(infra_status.values()) + (1 if api_status else 0)
    
    if orchestrator and orchestrator.is_running:
        service_health = all(
            details['status'] in ['running', 'healthy'] 
            for details in service_status['services'].values()
        )
        total_checks += 1
        passed_checks += 1 if service_health else 0
    
    health_percentage = (passed_checks / total_checks) * 100
    
    if health_percentage == 100:
        print(f"  🟢 System Health: {health_percentage:.1f}% - Excellent")
    elif health_percentage >= 80:
        print(f"  🟡 System Health: {health_percentage:.1f}% - Good")
    elif health_percentage >= 60:
        print(f"  🟠 System Health: {health_percentage:.1f}% - Fair")
    else:
        print(f"  🔴 System Health: {health_percentage:.1f}% - Poor")
    
    return health_percentage

def continuous_monitoring(interval_seconds=30):
    """Run continuous health monitoring."""
    print(f"🔄 Starting continuous monitoring (checking every {interval_seconds} seconds)")
    print("Press Ctrl+C to stop monitoring")
    
    try:
        orchestrator = ServiceOrchestrator()
        
        while True:
            os.system('cls' if os.name == 'nt' else 'clear')  # Clear screen
            health_percentage = generate_health_report(orchestrator)
            
            print(f"\n⏰ Next check in {interval_seconds} seconds...")
            time.sleep(interval_seconds)
            
    except KeyboardInterrupt:
        print("\n🛑 Monitoring stopped by user")

def main():
    """Main health check function."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Health Check for Algorithmic Trading System')
    parser.add_argument('--continuous', '-c', action='store_true', 
                       help='Run continuous monitoring')
    parser.add_argument('--interval', '-i', type=int, default=30,
                       help='Monitoring interval in seconds (default: 30)')
    
    args = parser.parse_args()
    
    if args.continuous:
        continuous_monitoring(args.interval)
    else:
        # Single health check
        orchestrator = None
        try:
            orchestrator = ServiceOrchestrator()
        except:
            pass  # Orchestrator might not be running
        
        health_percentage = generate_health_report(orchestrator)
        
        # Exit with appropriate code
        sys.exit(0 if health_percentage == 100 else 1)

if __name__ == '__main__':
    main()



