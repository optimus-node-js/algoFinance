"""
Health Server for Strategy Engine
=================================

HTTP health endpoint for Docker health checks and monitoring.
"""

import asyncio
import json
import logging
from datetime import datetime
from typing import Dict, Any, Optional
from aiohttp import web, ClientTimeout, ClientSession
import aiohttp_cors

class StrategyEngineHealthServer:
    """
    Health server for Strategy Engine monitoring and Docker health checks.
    
    Provides HTTP endpoints for:
    - Health status
    - Metrics
    - Status information
    """
    
    def __init__(self, port: int = 8004, orchestrator=None):
        """
        Initialize health server.
        
        Args:
            port: HTTP server port
            orchestrator: Strategy orchestrator instance (optional)
        """
        self.port = port
        self.orchestrator = orchestrator
        self.app = web.Application()
        self.start_time = datetime.now()
        
        # Setup routes
        self._setup_routes()
        
        self.logger = logging.getLogger("strategy_health_server")
        
    def _setup_routes(self):
        """Setup HTTP routes."""
        # Health check endpoint
        self.app.router.add_get("/health", self.health_check)
        
        # Metrics endpoint
        self.app.router.add_get("/metrics", self.get_metrics)
        
        # Status endpoint
        self.app.router.add_get("/status", self.get_status)
        
        # Workers endpoint
        self.app.router.add_get("/workers", self.get_workers)
        
        # Strategies endpoint
        self.app.router.add_get("/strategies", self.get_strategies)
        
        # Info endpoint
        self.app.router.add_get("/info", self.get_info)
        
        # Root endpoint
        self.app.router.add_get("/", self.root)
        
        # Setup CORS
        cors = aiohttp_cors.setup(self.app, defaults={
            "*": aiohttp_cors.ResourceOptions(
                allow_credentials=True,
                expose_headers="*",
                allow_headers="*",
                allow_methods="*"
            )
        })
        
        # Add CORS to all routes
        for route in list(self.app.router.routes()):
            cors.add(route)
            
    async def health_check(self, request) -> web.Response:
        """Health check endpoint for Docker and monitoring."""
        try:
            health_data = {
                "status": "healthy",
                "timestamp": datetime.now().isoformat(),
                "uptime_seconds": (datetime.now() - self.start_time).total_seconds(),
                "service": "strategy-engine"
            }
            
            # Check orchestrator health if available
            if self.orchestrator:
                try:
                    orchestrator_status = self.orchestrator.get_status()
                    health_data["orchestrator_status"] = orchestrator_status["status"]
                    health_data["active_workers"] = orchestrator_status["active_workers"]
                    health_data["total_strategies"] = orchestrator_status["total_strategies"]
                    
                    # Mark as unhealthy if orchestrator has issues
                    if orchestrator_status["status"] in ["ERROR", "STOPPED"]:
                        health_data["status"] = "unhealthy"
                        health_data["reason"] = f"Orchestrator status: {orchestrator_status['status']}"
                        
                except Exception as e:
                    health_data["status"] = "degraded"
                    health_data["reason"] = f"Orchestrator check failed: {str(e)}"
                    
            # Check external service connectivity
            service_checks = await self._check_external_services()
            health_data["external_services"] = service_checks
            
            # Determine overall health
            if any(not service["healthy"] for service in service_checks.values()):
                if health_data["status"] == "healthy":
                    health_data["status"] = "degraded"
                    health_data["reason"] = "Some external services unavailable"
                    
            status_code = 200 if health_data["status"] in ["healthy", "degraded"] else 503
            
            return web.json_response(health_data, status=status_code)
            
        except Exception as e:
            self.logger.error(f"Health check failed: {str(e)}")
            return web.json_response({
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }, status=503)
            
    async def get_metrics(self, request) -> web.Response:
        """Get performance metrics."""
        try:
            metrics = {
                "timestamp": datetime.now().isoformat(),
                "uptime_seconds": (datetime.now() - self.start_time).total_seconds(),
                "service": "strategy-engine"
            }
            
            if self.orchestrator:
                orchestrator_metrics = self.orchestrator.get_metrics()
                metrics.update(orchestrator_metrics)
            else:
                metrics["status"] = "orchestrator_not_available"
                
            return web.json_response(metrics)
            
        except Exception as e:
            self.logger.error(f"Metrics retrieval failed: {str(e)}")
            return web.json_response({
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }, status=500)
            
    async def get_status(self, request) -> web.Response:
        """Get detailed status information."""
        try:
            status = {
                "service": "strategy-engine",
                "timestamp": datetime.now().isoformat(),
                "uptime_seconds": (datetime.now() - self.start_time).total_seconds(),
                "start_time": self.start_time.isoformat()
            }
            
            if self.orchestrator:
                orchestrator_status = self.orchestrator.get_status()
                status.update(orchestrator_status)
            else:
                status["orchestrator"] = "not_available"
                
            return web.json_response(status)
            
        except Exception as e:
            self.logger.error(f"Status retrieval failed: {str(e)}")
            return web.json_response({
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }, status=500)
            
    async def get_workers(self, request) -> web.Response:
        """Get worker information."""
        try:
            if not self.orchestrator:
                return web.json_response({
                    "error": "Orchestrator not available",
                    "workers": []
                }, status=503)
                
            workers_info = []
            for worker_id, worker in self.orchestrator.workers.items():
                worker_metrics = worker.get_metrics()
                worker_health = worker.get_health_status()
                
                workers_info.append({
                    "worker_id": worker_id,
                    "metrics": worker_metrics,
                    "health": worker_health
                })
                
            return web.json_response({
                "workers": workers_info,
                "total_workers": len(workers_info),
                "timestamp": datetime.now().isoformat()
            })
            
        except Exception as e:
            self.logger.error(f"Workers info retrieval failed: {str(e)}")
            return web.json_response({
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }, status=500)
            
    async def get_strategies(self, request) -> web.Response:
        """Get strategy information."""
        try:
            if not self.orchestrator:
                return web.json_response({
                    "error": "Orchestrator not available",
                    "strategies": []
                }, status=503)
                
            strategies_info = []
            for strategy_id, strategy_config in self.orchestrator.strategy_registry.items():
                worker_id = self.orchestrator.worker_assignments.get(strategy_id)
                
                strategy_info = {
                    "strategy_id": strategy_id,
                    "strategy_class": strategy_config.strategy_class,
                    "symbol": strategy_config.symbol,
                    "timeframe": strategy_config.timeframe,
                    "worker_id": worker_id,
                    "parameters": strategy_config.parameters
                }
                
                # Get strategy performance if available
                if worker_id and worker_id in self.orchestrator.workers:
                    worker = self.orchestrator.workers[worker_id]
                    for engine in worker.strategy_engines:
                        if engine.strategy_id == strategy_id:
                            strategy_info["performance"] = engine.get_performance_metrics()
                            break
                            
                strategies_info.append(strategy_info)
                
            return web.json_response({
                "strategies": strategies_info,
                "total_strategies": len(strategies_info),
                "timestamp": datetime.now().isoformat()
            })
            
        except Exception as e:
            self.logger.error(f"Strategies info retrieval failed: {str(e)}")
            return web.json_response({
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }, status=500)
            
    async def get_info(self, request) -> web.Response:
        """Get general service information."""
        return web.json_response({
            "service": "Strategy Engine",
            "version": "1.0.0",
            "description": "HFT Strategy Engine Framework",
            "endpoints": [
                "/health - Health check",
                "/metrics - Performance metrics", 
                "/status - Detailed status",
                "/workers - Worker information",
                "/strategies - Strategy information",
                "/info - Service information"
            ],
            "timestamp": datetime.now().isoformat(),
            "uptime_seconds": (datetime.now() - self.start_time).total_seconds()
        })
        
    async def root(self, request) -> web.Response:
        """Root endpoint."""
        return web.json_response({
            "service": "HFT Strategy Engine",
            "status": "running",
            "timestamp": datetime.now().isoformat(),
            "health_endpoint": "/health",
            "metrics_endpoint": "/metrics"
        })
        
    async def _check_external_services(self) -> Dict[str, Dict[str, Any]]:
        """Check connectivity to external services."""
        services = {
            "risk_service": "http://risk-service:8003/health",
            "angel_one_api": "http://angel-one-api:8000/ping",
            "caching_service": "http://caching-service:8001/health",
            "messaging_service": "http://messaging-service:8002/health"
        }
        
        results = {}
        timeout = ClientTimeout(total=2.0)
        
        async with ClientSession(timeout=timeout) as session:
            for service_name, url in services.items():
                try:
                    async with session.get(url) as response:
                        healthy = response.status == 200
                        results[service_name] = {
                            "healthy": healthy,
                            "status_code": response.status,
                            "response_time_ms": 0  # Could add timing if needed
                        }
                except Exception as e:
                    results[service_name] = {
                        "healthy": False,
                        "error": str(e),
                        "response_time_ms": None
                    }
                    
        return results
        
    async def start_server(self) -> None:
        """Start the health server."""
        runner = web.AppRunner(self.app)
        await runner.setup()
        
        site = web.TCPSite(runner, '0.0.0.0', self.port)
        await site.start()
        
        self.logger.info(f"Strategy Engine health server started on port {self.port}")
        
    def set_orchestrator(self, orchestrator) -> None:
        """Set the orchestrator instance for health monitoring."""
        self.orchestrator = orchestrator

