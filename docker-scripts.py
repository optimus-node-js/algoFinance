#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
HFT Docker Management Scripts
=============================

Docker Compose orchestration for the complete HFT microservices stack.
Manages dependencies, networking, and service health automatically.

Usage:
    python docker-scripts.py --help                    # Show all commands
    
    # Group Commands
    python docker-scripts.py start:core               # Start core services (Redis, Kafka)
    python docker-scripts.py start:api                # Start API services (Angel One, Risk)
    python docker-scripts.py start:strategy           # Start Strategy Engine service
    python docker-scripts.py start:all                # Start all services (no Strategy Engine)
    python docker-scripts.py start:full-stack         # Start complete HFT stack (with Strategy Engine)
    python docker-scripts.py stop:all                 # Stop all services (with cleanup)
    
    # Individual Service Commands
    python docker-scripts.py start:redis              # Start Redis only
    python docker-scripts.py start:kafka              # Start Kafka only
    python docker-scripts.py start:angel-one-api      # Start Angel One API only
    python docker-scripts.py start:risk-service       # Start Risk Service only
    python docker-scripts.py start:strategy-engine    # Start Strategy Engine only
    
    # Management Commands
    python docker-scripts.py clean-build-all          # Clean build and start all services
    python docker-scripts.py status                   # Show service status
    python docker-scripts.py logs [service]           # Show logs
    python docker-scripts.py health                   # Check service health
    python docker-scripts.py restart [service]        # Restart service(s)

Examples:
    # Start the complete HFT stack with Strategy Engine
    python docker-scripts.py start:full-stack
    
    # Start core services + APIs (no Strategy Engine)
    python docker-scripts.py start:all
    
    # Start individual services
    python docker-scripts.py start:redis
    python docker-scripts.py start:strategy-engine
    
    # Clean build and start everything
    python docker-scripts.py clean-build-all
    
    # Start only infrastructure
    python docker-scripts.py start:core
    
    # Start only Strategy Engine (requires core + API services)
    python docker-scripts.py start:strategy
    
    # Stop all services with cleanup
    python docker-scripts.py stop:all
    
    # Stop individual services
    python docker-scripts.py stop:strategy-engine
    
    # Monitor Strategy Engine
    python docker-scripts.py logs strategy-engine
    
    # Check system health
    python docker-scripts.py health
"""

import sys
import os
import subprocess
import time
import argparse
import json
import requests
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime

# Fix encoding issues on Windows
if sys.platform == "win32":
    import codecs
    sys.stdout = codecs.getwriter("utf-8")(sys.stdout.detach())
    sys.stderr = codecs.getwriter("utf-8")(sys.stderr.detach())

class HFTDockerManager:
    """Docker Compose manager for HFT services."""
    
    def __init__(self):
        self.project_root = Path(__file__).parent
        self.compose_file = self.project_root / "docker-compose.yml"
        
        # Service groups
        self.service_groups = {
            "core": ["redis", "zookeeper", "kafka"],
            "database": ["database-service"],
            "api": ["angel-one-api", "risk-service", "caching-service", "messaging-service"],
            "streaming": ["market-data-streaming"],
            "strategy": ["strategy-engine"],
            "monitoring": ["kafka-ui", "redis-commander"],
            "all": ["redis", "zookeeper", "kafka", "database-service", "angel-one-api", "risk-service", "caching-service", "messaging-service", "market-data-streaming", "strategy-engine"],
            "full-stack": ["redis", "zookeeper", "kafka", "database-service", "angel-one-api", "risk-service", "caching-service", "messaging-service", "market-data-streaming", "strategy-engine", "kafka-ui", "redis-commander"]
        }
        
        # Health check endpoints
        self.health_endpoints = {
            "angel-one-api": "http://localhost:8000/ping",
            "risk-service": "http://localhost:8003/health",
            "caching-service": "http://localhost:8001/health",
            "messaging-service": "http://localhost:8002/health",
            "market-data-streaming": "http://localhost:8005/health",
            "strategy-engine": "http://localhost:8004/health",
            "database-service": "http://localhost:8006/health",
            "redis": {"cmd": ["docker", "exec", "hft-redis", "redis-cli", "ping"]},
            "kafka": {"cmd": ["docker", "exec", "hft-kafka", "kafka-broker-api-versions", "--bootstrap-server", "localhost:9092"]}
        }

    def print_banner(self, title: str):
        """Print a formatted banner."""
        print("\n" + "="*60)
        print(f" DOCKER {title}")
        print("="*60)

    def run_docker_compose(self, command: List[str], capture_output: bool = False) -> subprocess.CompletedProcess:
        """Run docker-compose command."""
        cmd = ["docker-compose", "-f", str(self.compose_file)] + command
        print(f"Running: {' '.join(cmd)}")
        
        try:
            if capture_output:
                result = subprocess.run(cmd, capture_output=True, text=True, check=True)
                return result
            else:
                result = subprocess.run(cmd, check=True)
                return result
        except subprocess.CalledProcessError as e:
            print(f"ERROR: Docker Compose command failed: {e}")
            if hasattr(e, 'stdout') and e.stdout:
                print(f"Stdout: {e.stdout}")
            if hasattr(e, 'stderr') and e.stderr:
                print(f"Stderr: {e.stderr}")
            raise

    def start_services(self, group: str = "all"):
        """Start services by group."""
        self.print_banner(f"Starting HFT Services: {group.upper()}")
        
        if group not in self.service_groups:
            print(f"ERROR: Unknown service group: {group}")
            print(f"Available groups: {', '.join(self.service_groups.keys())}")
            return
        
        services = self.service_groups[group]
        
        # Special handling for core services (sequential startup)
        if group == "core":
            print("Starting core infrastructure services...")
            # Start Redis first
            self.run_docker_compose(["up", "-d", "redis"])
            self._wait_for_service_health("redis")
            
            # Start Zookeeper
            self.run_docker_compose(["up", "-d", "zookeeper"])
            time.sleep(10)  # Zookeeper needs time to initialize
            
            # Start Kafka
            self.run_docker_compose(["up", "-d", "kafka"])
            self._wait_for_service_health("kafka")
            
        elif group == "api":
            print("Starting API services...")
            # Ensure core services are running
            self.run_docker_compose(["up", "-d"] + self.service_groups["core"])
            
            # Start API services with dependencies
            self.run_docker_compose(["up", "-d"] + services)
            
        elif group == "monitoring":
            print("Starting monitoring services...")
            self.run_docker_compose(["--profile", "monitoring", "up", "-d"] + services)
            
        else:  # all
            print("Starting all HFT services...")
            self.run_docker_compose(["up", "-d"] + services)
        
        print(f"\nSUCCESS: {group.upper()} services started!")
        self.show_service_urls()

    def stop_services(self, group: str = "all"):
        """Stop services."""
        self.print_banner(f"Stopping HFT Services: {group.upper()}")
        
        if group == "all":
            # Use down --remove-orphans to ensure all containers are stopped
            self.run_docker_compose(["down", "--remove-orphans"])
            print("✅ All services stopped and containers removed")
        else:
            if group in self.service_groups:
                services = self.service_groups[group]
                self.run_docker_compose(["stop"] + services)
                print(f"✅ {group.upper()} services stopped")
            else:
                print(f"❌ Unknown service group: {group}")

    def restart_services(self, services: Optional[List[str]] = None):
        """Restart specific services or all."""
        if services:
            self.print_banner(f"Restarting Services: {', '.join(services)}")
            self.run_docker_compose(["restart"] + services)
        else:
            self.print_banner("Restarting All Services")
            self.run_docker_compose(["restart"])

    def show_status(self):
        """Show status of all services."""
        self.print_banner("HFT Services Status")
        
        try:
            result = self.run_docker_compose(["ps"], capture_output=True)
            print(result.stdout)
        except Exception as e:
            print(f"❌ Failed to get status: {e}")

    def show_logs(self, service: Optional[str] = None, follow: bool = False):
        """Show logs for service(s)."""
        if service:
            self.print_banner(f"Logs for {service}")
            cmd = ["logs"]
            if follow:
                cmd.append("-f")
            cmd.append(service)
        else:
            self.print_banner("Logs for All Services")
            cmd = ["logs"]
            if follow:
                cmd.append("-f")
        
        self.run_docker_compose(cmd)

    def check_health(self):
        """Check health of all services."""
        self.print_banner("HFT Services Health Check")
        
        health_results = {}
        
        for service, endpoint in self.health_endpoints.items():
            print(f"\n🔍 Checking {service}...")
            
            try:
                if isinstance(endpoint, str):
                    # HTTP health check
                    response = requests.get(endpoint, timeout=10)
                    if response.status_code == 200:
                        print(f"  ✅ {service}: Healthy")
                        health_results[service] = "healthy"
                    else:
                        print(f"  ❌ {service}: Unhealthy (HTTP {response.status_code})")
                        health_results[service] = "unhealthy"
                        
                elif isinstance(endpoint, dict) and "cmd" in endpoint:
                    # Command-based health check
                    result = subprocess.run(endpoint["cmd"], capture_output=True, text=True, timeout=10)
                    if result.returncode == 0:
                        print(f"  ✅ {service}: Healthy")
                        health_results[service] = "healthy"
                    else:
                        print(f"  ❌ {service}: Unhealthy")
                        health_results[service] = "unhealthy"
                        
            except Exception as e:
                print(f"  ❌ {service}: Health check failed - {e}")
                health_results[service] = "failed"
        
        # Summary
        healthy = sum(1 for status in health_results.values() if status == "healthy")
        total = len(health_results)
        
        print(f"\n📊 Health Summary: {healthy}/{total} services healthy")
        
        if healthy == total:
            print("🎉 All services are healthy!")
        else:
            print("⚠️  Some services need attention")

    def _wait_for_service_health(self, service: str, timeout: int = 60):
        """Wait for a service to become healthy."""
        print(f"⏳ Waiting for {service} to become healthy...")
        
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                if service in self.health_endpoints:
                    endpoint = self.health_endpoints[service]
                    
                    if isinstance(endpoint, str):
                        response = requests.get(endpoint, timeout=5)
                        if response.status_code == 200:
                            print(f"✅ {service} is healthy")
                            return
                    elif isinstance(endpoint, dict) and "cmd" in endpoint:
                        result = subprocess.run(endpoint["cmd"], capture_output=True, timeout=5)
                        if result.returncode == 0:
                            print(f"✅ {service} is healthy")
                            return
                
                time.sleep(5)
                
            except Exception:
                time.sleep(5)
                continue
        
        print(f"⚠️  {service} did not become healthy within {timeout} seconds")

    def show_service_urls(self):
        """Show URLs for all services."""
        print("\n📋 Service URLs:")
        print("   🔹 Angel One API: http://localhost:8000")
        print("   🔹 Angel One Docs: http://localhost:8000/scalar-docs")
        print("   🔹 Risk Service: http://localhost:8003/health")
        print("   🔹 Caching Service: http://localhost:8001/health")
        print("   🔹 Messaging Service: http://localhost:8002/health")
        print("   🔹 Market Data Streaming: http://localhost:8005/health")
        print("   🔹 Strategy Engine: http://localhost:8004/health")
        print("   🔹 Strategy Metrics: http://localhost:8004/metrics")
        print("   🔹 Strategy Workers: http://localhost:8004/workers")
        print("   🔹 Database Service: http://localhost:8006/health")
        print("   🔹 Database API Docs: http://localhost:8006/docs")
        print("   🔹 Kafka UI: http://localhost:8080 (with --profile monitoring)")
        print("   🔹 Redis UI: http://localhost:8081 (with --profile monitoring)")
        print("   🔹 Redis: localhost:6379")
        print("   🔹 Kafka: localhost:9092")

    def build_services(self, services: Optional[List[str]] = None):
        """Build Docker images for services."""
        self.print_banner("Building HFT Services")
        
        if services:
            self.run_docker_compose(["build"] + services)
        else:
            self.run_docker_compose(["build"])
    
    def clean_build_all(self):
        """Clean build and start all services."""
        self.print_banner("Clean Build & Start All HFT Services")
        
        print("🧹 Step 1: Stopping and removing all containers...")
        try:
            self.run_docker_compose(["down", "--remove-orphans", "--volumes"])
        except:
            print("⚠️  No running containers to stop")
        
        print("🔨 Step 2: Building all images (no cache)...")
        self.run_docker_compose(["build", "--no-cache"])
        
        print("🚀 Step 3: Starting all services...")
        self.start_services("all")
        
        print("✅ Clean build and start completed!")

def main():
    """Main script entry point."""
    parser = argparse.ArgumentParser(description="HFT Docker Management Scripts")
    
    parser.add_argument("command", nargs="?", default="help",
                       choices=[
                           # Group commands
                           "start:core", "start:database", "start:api", "start:streaming", "start:strategy", "start:monitoring", "start:all", "start:full-stack",
                           "stop:core", "stop:database", "stop:api", "stop:streaming", "stop:strategy", "stop:monitoring", "stop:all",
                               # Individual service commands
                               "start:redis", "start:zookeeper", "start:kafka", "start:database-service", "start:angel-one-api", "start:risk-service", 
                               "start:caching-service", "start:messaging-service", "start:market-data-streaming", "start:strategy-engine",
                               "stop:redis", "stop:zookeeper", "stop:kafka", "stop:database-service", "stop:angel-one-api", "stop:risk-service",
                               "stop:caching-service", "stop:messaging-service", "stop:market-data-streaming", "stop:strategy-engine",
                           # Other commands
                           "restart", "build", "clean-build-all", "status", "logs", "health", "help"
                       ],
                       help="Command to execute")
    
    parser.add_argument("--service", "-s", help="Specific service name")
    parser.add_argument("--follow", "-f", action="store_true", help="Follow logs")
    
    args = parser.parse_args()
    manager = HFTDockerManager()
    
    try:
        if args.command == "help" or not args.command:
            print(__doc__)
            parser.print_help()
        
        elif args.command.startswith("start:"):
            group = args.command.split(":")[1]
            # Handle individual services
            individual_services = ["redis", "zookeeper", "kafka", "angel-one-api", "risk-service", 
                                 "caching-service", "messaging-service", "market-data-streaming", "strategy-engine", "database-service"]
            if group in individual_services:
                manager.run_docker_compose(["up", "-d", group])
                print(f"✅ {group} started successfully!")
            else:
                manager.start_services(group)
        
        elif args.command.startswith("stop:"):
            group = args.command.split(":")[1]
            # Handle individual services
            individual_services = ["redis", "zookeeper", "kafka", "angel-one-api", "risk-service", 
                                 "caching-service", "messaging-service", "market-data-streaming", "strategy-engine", "database-service"]
            if group in individual_services:
                manager.run_docker_compose(["stop", group])
                print(f"✅ {group} stopped successfully!")
            else:
                manager.stop_services(group)
        
        elif args.command == "restart":
            if args.service:
                manager.restart_services([args.service])
            else:
                manager.restart_services()
        
        elif args.command == "build":
            if args.service:
                manager.build_services([args.service])
            else:
                manager.build_services()
        
        elif args.command == "clean-build-all":
            manager.clean_build_all()
        
        elif args.command == "status":
            manager.show_status()
        
        elif args.command == "logs":
            manager.show_logs(args.service, args.follow)
        
        elif args.command == "health":
            manager.check_health()
        
        else:
            print(f"❌ Unknown command: {args.command}")
            parser.print_help()
            
    except KeyboardInterrupt:
        print("\n🛑 Operation cancelled by user")
    except Exception as e:
        print(f"❌ Error: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
