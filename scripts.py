#!/usr/bin/env python3
"""
HFT Service Management Scripts
==============================

Python equivalent of package.json scripts for managing all HFT microservices.
Run individual services or multiple services in parallel.

Usage:
    python scripts.py --help                    # Show all available commands
    python scripts.py run:angel-one            # Start Angel One API service
    python scripts.py run:redis                # Start Redis container
    python scripts.py run:kafka                # Start Kafka container  
    python scripts.py run:all                  # Start all core services
    python scripts.py test:integration         # Run integration tests
    python scripts.py test:angel-one           # Test Angel One module
    python scripts.py stop:all                 # Stop all services
    python scripts.py logs:angel-one           # Show service logs

Examples:
    # Start development stack
    python scripts.py run:dev-stack
    
    # Run performance tests
    python scripts.py test:performance
    
    # Monitor all services
    python scripts.py monitor
"""

import sys
import os
import subprocess
import time
import argparse
import asyncio
import concurrent.futures
from pathlib import Path
from typing import List, Dict, Optional
import json

# Add server/src to Python path
PROJECT_ROOT = Path(__file__).parent
SERVER_SRC = PROJECT_ROOT / "server" / "src"
sys.path.insert(0, str(SERVER_SRC))

class ServiceManager:
    """Manages all HFT microservices."""
    
    def __init__(self):
        self.project_root = PROJECT_ROOT
        self.server_src = SERVER_SRC
        self.services = {
            "angel-one": {
                "command": ["python", "-m", "angel_one_api.api.main"],
                "port": 8000,
                "health_check": "http://localhost:8000/ping",
                "cwd": str(SERVER_SRC)
            },
            "caching": {
                "command": ["python", "-m", "caching_service.main"],
                "port": 8001,
                "health_check": "http://localhost:8001/health",
                "cwd": str(SERVER_SRC)
            },
            "messaging": {
                "command": ["python", "-m", "messaging_enhanced.main"],
                "port": 8002,
                "health_check": "http://localhost:8002/health",
                "cwd": str(SERVER_SRC)
            }
        }
        
        self.containers = {
            "redis": {
                "command": ["docker", "run", "--name", "redis-hft", "-d", "-p", "6379:6379", "redis:alpine"],
                "stop_command": ["docker", "stop", "redis-hft"],
                "remove_command": ["docker", "rm", "redis-hft"],
                "health_check": ["docker", "exec", "redis-hft", "redis-cli", "ping"]
            },
            "kafka": {
                "command": ["docker", "run", "--name", "kafka-hft", "-d", "-p", "9092:9092", 
                           "-e", "KAFKA_ZOOKEEPER_CONNECT=localhost:2181",
                           "-e", "KAFKA_ADVERTISED_LISTENERS=PLAINTEXT://localhost:9092",
                           "confluentinc/cp-kafka:latest"],
                "stop_command": ["docker", "stop", "kafka-hft"],
                "remove_command": ["docker", "rm", "kafka-hft"],
                "health_check": ["docker", "ps", "--filter", "name=kafka-hft", "--format", "table {{.Status}}"]
            }
        }
        
        self.running_processes = {}

    def print_banner(self, title: str):
        """Print a formatted banner."""
        print("\n" + "="*60)
        print(f" 🚀 {title}")
        print("="*60)

    def run_command(self, command: List[str], cwd: Optional[str] = None, background: bool = False) -> subprocess.Popen:
        """Run a command with proper error handling."""
        try:
            print(f"🔧 Running: {' '.join(command)}")
            if cwd:
                print(f"📁 Working directory: {cwd}")
            
            if background:
                process = subprocess.Popen(
                    command,
                    cwd=cwd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True
                )
                return process
            else:
                result = subprocess.run(command, cwd=cwd, check=True, capture_output=True, text=True)
                if result.stdout:
                    print(f"✅ Output: {result.stdout.strip()}")
                return result
                
        except subprocess.CalledProcessError as e:
            print(f"❌ Error running command: {e}")
            if e.stdout:
                print(f"📤 Stdout: {e.stdout}")
            if e.stderr:
                print(f"📥 Stderr: {e.stderr}")
            raise
        except FileNotFoundError:
            print(f"❌ Command not found: {command[0]}")
            raise

    def start_redis(self):
        """Start Redis container."""
        self.print_banner("Starting Redis Container")
        
        # Check if already running
        try:
            result = subprocess.run(["docker", "ps", "--filter", "name=redis-hft", "--format", "{{.Names}}"],
                                  capture_output=True, text=True)
            if "redis-hft" in result.stdout:
                print("✅ Redis container already running")
                return
        except:
            pass
        
        # Remove existing container if stopped
        try:
            subprocess.run(["docker", "rm", "redis-hft"], capture_output=True)
        except:
            pass
        
        # Start Redis
        self.run_command(self.containers["redis"]["command"])
        time.sleep(2)
        
        # Health check
        try:
            result = self.run_command(self.containers["redis"]["health_check"])
            print("✅ Redis is healthy and responding")
        except:
            print("⚠️  Redis health check failed, but container started")

    def start_angel_one(self):
        """Start Angel One API service."""
        self.print_banner("Starting Angel One API Service")
        
        service = self.services["angel-one"]
        try:
            process = self.run_command(service["command"], service["cwd"], background=True)
            self.running_processes["angel-one"] = process
            print(f"✅ Angel One API starting on port {service['port']}")
            print(f"🌐 Health check: {service['health_check']}")
            return process
        except Exception as e:
            print(f"❌ Failed to start Angel One API: {e}")
            raise

    def start_risk(self):
        """Start Risk Service FastAPI app."""
        port = os.getenv("RISK_API_PORT") or "8003"
        try:
            cmd = [sys.executable, "-m", "server.src.risk_service.api"]
            env = {**os.environ, "RISK_API_PORT": port}
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                env=env
            )
            self.running_processes["risk"] = process
            print(f"✅ Risk Service starting on port {port}")
            print(f"🌐 Health check: http://localhost:{port}/health")
            return process
        except Exception as e:
            print(f"❌ Failed to start Risk Service: {e}")
            raise

    def start_all_services(self):
        """Start all core services."""
        self.print_banner("Starting All HFT Services")
        
        # Start containers first
        print("\n🐳 Starting Docker containers...")
        self.start_redis()
        
        # Start microservices
        print("\n🚀 Starting microservices...")
        self.start_angel_one()
        self.start_risk()
        
        print("\n✅ All services started successfully!")
        print("\n📋 Service URLs:")
        print("   🔹 Angel One API: http://localhost:8000")
        print("   🔹 API Docs: http://localhost:8000/scalar-docs")
        print("   🔹 Risk Service: http://localhost:8003")
        print("   🔹 Redis: localhost:6379")

    def run_integration_tests(self):
        """Run integration tests."""
        self.print_banner("Running Integration Tests")
        
        test_command = ["python", "caching_service/testing/test_microservice_integration.py"]
        self.run_command(test_command, str(SERVER_SRC))

    def run_angel_one_tests(self):
        """Run Angel One module tests."""
        self.print_banner("Running Angel One Module Tests")
        
        test_command = ["python", "angel_one_api/testing/test_angel_one_module.py"]
        self.run_command(test_command, str(SERVER_SRC))

    def stop_all_services(self):
        """Stop all running services."""
        self.print_banner("Stopping All Services")
        
        # Stop running processes
        for name, process in self.running_processes.items():
            try:
                print(f"🛑 Stopping {name}...")
                process.terminate()
                process.wait(timeout=10)
                print(f"✅ {name} stopped")
            except:
                try:
                    process.kill()
                    print(f"🔨 {name} force killed")
                except:
                    print(f"⚠️  Could not stop {name}")
        
        # Stop containers
        try:
            subprocess.run(["docker", "stop", "redis-hft"], capture_output=True)
            subprocess.run(["docker", "stop", "kafka-hft"], capture_output=True)
            print("✅ All containers stopped")
        except:
            print("⚠️  Some containers may still be running")

    def show_status(self):
        """Show status of all services."""
        self.print_banner("HFT Services Status")
        
        print("\n🐳 Docker Containers:")
        try:
            result = subprocess.run(["docker", "ps", "--format", "table {{.Names}}\t{{.Status}}\t{{.Ports}}"],
                                  capture_output=True, text=True)
            print(result.stdout)
        except:
            print("   ❌ Docker not available")
        
        print("\n🚀 Microservices:")
        for name, process in self.running_processes.items():
            if process and process.poll() is None:
                print(f"   ✅ {name}: Running (PID: {process.pid})")
            else:
                print(f"   ❌ {name}: Stopped")

def main():
    """Main script entry point."""
    parser = argparse.ArgumentParser(description="HFT Service Management Scripts")
    
    # Service commands
    parser.add_argument("command", nargs="?", default="help", 
                       choices=[
                           "run:angel-one", "run:redis", "run:kafka", "run:risk", "run:all", "run:dev-stack",
                           "test:integration", "test:angel-one", "test:performance",
                           "stop:all", "status", "logs", "monitor", "help"
                       ],
                       help="Command to execute")
    
    args = parser.parse_args()
    manager = ServiceManager()
    
    try:
        if args.command == "help" or not args.command:
            print(__doc__)
            parser.print_help()
        
        elif args.command == "run:redis":
            manager.start_redis()
        
        elif args.command == "run:risk":
            manager.start_risk()
            print("\n⏳ Press Ctrl+C to stop the service...")
            try:
                # Keep the main process alive
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                print("\n🛑 Stopping Risk service...")
                manager.stop_all_services()
        
        elif args.command == "run:angel-one":
            manager.start_angel_one()
            print("\n⏳ Press Ctrl+C to stop the service...")
            try:
                # Keep the main process alive
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                print("\n🛑 Stopping Angel One service...")
                manager.stop_all_services()
        
        elif args.command in ["run:all", "run:dev-stack"]:
            manager.start_all_services()
            print("\n⏳ Press Ctrl+C to stop all services...")
            try:
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                print("\n🛑 Stopping all services...")
                manager.stop_all_services()
        
        elif args.command == "test:integration":
            manager.run_integration_tests()
        
        elif args.command == "test:angel-one":
            manager.run_angel_one_tests()
        
        elif args.command == "stop:all":
            manager.stop_all_services()
        
        elif args.command == "status":
            manager.show_status()
        
        else:
            print(f"❌ Unknown command: {args.command}")
            parser.print_help()
            
    except KeyboardInterrupt:
        print("\n🛑 Operation cancelled by user")
        manager.stop_all_services()
    except Exception as e:
        print(f"❌ Error: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
