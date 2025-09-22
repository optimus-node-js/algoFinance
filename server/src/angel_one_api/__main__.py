#!/usr/bin/env python3
"""
Angel One FastAPI Server - Main Entry Point
==========================================

This is the proper Python package entry point for the Angel One FastAPI server.
This fixes the relative import issues by running the module as a package.

Usage:
    python -m angel_one_api                    # Start development server
    python -m angel_one_api --prod             # Start production server
    python -m angel_one_api --test             # Start with test data
    python -m angel_one_api --port 8080        # Custom port
"""

import sys
import os
import asyncio
import argparse
import uvicorn
from pathlib import Path
from datetime import datetime

def print_banner():
    """Print startup banner."""
    print("\n" + "=" * 80)
    print("🚀 ANGEL ONE FASTAPI MICROSERVICE")
    print("   Enterprise HFT Trading API Server")
    print("=" * 80)
    print(f"📅 Startup Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"🐍 Python Version: {sys.version.split()[0]}")
    print(f"📁 Working Directory: {Path.cwd()}")

def print_endpoints():
    """Print available endpoints."""
    print("\n📡 AVAILABLE ENDPOINTS:")
    print("=" * 50)
    
    endpoints = [
        ("🏠 Service Info", "GET", "/"),
        ("📊 API Documentation", "GET", "/scalar-docs"),
        ("💚 Health Status", "GET", "/health/status"),
        ("📈 Health Metrics", "GET", "/health/metrics"),
        ("🔐 Auto Login", "POST", "/auth/auto-login"),
        ("📊 Auth Status", "GET", "/auth/status"),
        ("🔄 Session Refresh", "POST", "/auth/refresh"),
        ("📋 Place Order", "POST", "/trading/orders"),
        ("📊 Order Book", "GET", "/trading/orders"),
        ("📈 Positions", "GET", "/trading/positions"),
        ("💰 LTP Data", "GET", "/market/ltp/{symbol}"),
        ("📊 Market Quotes", "GET", "/market/quotes/{symbol}"),
        ("📈 Historical Data", "GET", "/market/history/{symbol}"),
        ("💼 Holdings", "GET", "/portfolio/holdings"),
        ("📊 Portfolio Performance", "GET", "/portfolio/performance"),
        ("⚠️ Risk Metrics", "GET", "/risk/metrics"),
        ("🎯 GTT Rules", "GET", "/advanced/gtt-rules"),
        ("📊 System Metrics", "GET", "/admin/metrics"),
    ]
    
    for desc, method, path in endpoints:
        print(f"   {desc:<25} {method:<6} {path}")

def print_websocket_endpoints():
    """Print WebSocket endpoints."""
    print("\n🌐 REAL-TIME WEBSOCKET STREAMS:")
    print("=" * 50)
    
    ws_endpoints = [
        ("💰 Live Market Data", "WS", "/ws/market/ltp"),
        ("📋 Trading Updates", "WS", "/ws/trading/orders"),
        ("💼 Portfolio Updates", "WS", "/ws/portfolio/updates"),
        ("📊 Admin Monitoring", "WS", "/ws/admin/monitoring"),
        ("💚 Health Monitoring", "WS", "/ws/health/monitoring")
    ]
    
    for desc, method, path in ws_endpoints:
        print(f"   {desc:<25} {method:<6} {path}")

def print_performance_targets():
    """Print performance targets."""
    print("\n⚡ PERFORMANCE TARGETS:")
    print("=" * 50)
    print("   🎯 API Response Time:      < 100ms")
    print("   🌐 WebSocket Latency:      < 50ms")
    print("   📊 Database Query Time:    < 50ms")
    print("   🐰 RabbitMQ Message Time:  < 20ms")
    print("   🔄 Authentication Time:    < 200ms")
    print("   💾 Memory Usage:           < 512MB")
    print("   🔗 Concurrent Connections: 1000+")

async def start_development_server(port: int = 8000):
    """Start development server with hot reload."""
    print(f"\n🔧 DEVELOPMENT MODE - Hot reload enabled")
    print(f"🌐 Server URL: http://localhost:{port}")
    print(f"📊 API Docs: http://localhost:{port}/scalar-docs")
    print(f"💚 Health Check: http://localhost:{port}/health/status")
    
    config = uvicorn.Config(
        "api.main:app",
        host="0.0.0.0",
        port=port,
        reload=True,
        log_level="info",
        reload_dirs=["./"]
    )
    server = uvicorn.Server(config)
    await server.serve()

async def start_production_server(port: int = 8000):
    """Start production server with multiple workers."""
    print(f"\n🚀 PRODUCTION MODE - Multi-worker configuration")
    print(f"🌐 Server URL: http://localhost:{port}")
    print(f"📊 API Docs: http://localhost:{port}/scalar-docs")
    
    config = uvicorn.Config(
        "api.main:app",
        host="0.0.0.0",
        port=port,
        workers=4,
        log_level="warning",
        access_log=False
    )
    server = uvicorn.Server(config)
    await server.serve()

async def start_test_server(port: int = 8000):
    """Start test server with mock data."""
    print(f"\n🧪 TEST MODE - Mock data enabled")
    print(f"🌐 Server URL: http://localhost:{port}")
    print(f"📊 API Docs: http://localhost:{port}/scalar-docs")
    
    config = uvicorn.Config(
        "api.main:app",
        host="127.0.0.1",
        port=port,
        reload=False,
        log_level="debug"
    )
    server = uvicorn.Server(config)
    await server.serve()

def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Angel One FastAPI Server")
    parser.add_argument("--prod", action="store_true", help="Start in production mode")
    parser.add_argument("--test", action="store_true", help="Start in test mode")
    parser.add_argument("--port", type=int, default=8000, help="Server port")
    
    args = parser.parse_args()
    
    print_banner()
    
    try:
        # Test imports first
        from api.main import app
        print("✅ FastAPI application loaded successfully")
        
        # Print information
        print_endpoints()
        print_websocket_endpoints()
        print_performance_targets()
        
        # Update port if specified
        if args.port != 8000:
            print(f"\n🔧 Custom port: {args.port}")
        
        # Start appropriate server
        if args.prod:
            asyncio.run(start_production_server(args.port))
        elif args.test:
            asyncio.run(start_test_server(args.port))
        else:
            asyncio.run(start_development_server(args.port))
            
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("\n💡 TROUBLESHOOTING:")
        print("   1. Install dependencies: pip install -r requirements.txt")
        print("   2. Check Python path and working directory")
        print("   3. Ensure all required modules are present")
        print("   4. Try: python -m angel_one_api (run as module)")
        return 1
    except Exception as e:
        print(f"❌ Startup error: {e}")
        print("\n💡 Check logs for detailed error information")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())



