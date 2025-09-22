#!/usr/bin/env python3
"""
Angel One FastAPI Server - SINGLE ENTRY POINT
============================================

Just run this and your server works. PERIOD.

Usage:
    python run_server.py                    # Development server  
    python run_server.py --prod             # Production mode
    python run_server.py --port 8080        # Custom port
"""

import os
import sys
import uvicorn
import argparse
from pathlib import Path

# Add current directory to Python path to fix imports
current_dir = Path(__file__).parent.absolute()
sys.path.insert(0, str(current_dir))

def main():
    """Main entry point - just run the damn server."""
    
    parser = argparse.ArgumentParser(description="Angel One FastAPI Server")
    parser.add_argument("--prod", action="store_true", help="Production mode")
    parser.add_argument("--port", type=int, default=8000, help="Server port")
    parser.add_argument("--host", default="0.0.0.0", help="Server host")
    
    args = parser.parse_args()
    
    print("🚀 Starting Angel One FastAPI Server...")
    print(f"📡 Server will be available at: http://{args.host}:{args.port}")
    print(f"📊 API Documentation: http://{args.host}:{args.port}/scalar-docs")
    print(f"💚 Health Check: http://{args.host}:{args.port}/health/status")
    
    # Production vs Development configuration
    if args.prod:
        print("🏭 PRODUCTION MODE")
        uvicorn.run(
            "api.main:app",
            host=args.host,
            port=args.port,
            workers=4,
            log_level="warning"
        )
    else:
        print("🔧 DEVELOPMENT MODE - Hot reload enabled")
        uvicorn.run(
            "api.main:app",
            host=args.host,
            port=args.port,
            reload=True,
            log_level="info",
            reload_dirs=[str(current_dir)]
        )

if __name__ == "__main__":
    main()



