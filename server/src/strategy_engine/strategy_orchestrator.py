"""
Strategy Orchestrator
====================

Multi-strategy coordination system for managing multiple strategy engines,
workers, and ensuring optimal resource allocation and performance.
"""

import asyncio
import logging
import json
from typing import Dict, List, Optional, Any, Set
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum
import traceback

from .kafka_strategy_worker import KafkaStrategyWorker
from .base_strategy_engine import BaseStrategyEngine

class OrchestratorStatus(Enum):
    """Orchestrator status states."""
    INITIALIZING = "INITIALIZING"
    RUNNING = "RUNNING"
    PAUSED = "PAUSED"
    STOPPING = "STOPPING"
    STOPPED = "STOPPED"
    ERROR = "ERROR"

@dataclass
class WorkerConfig:
    """Configuration for a strategy worker."""
    worker_id: str
    input_topics: List[str]
    output_topic: str
    max_strategies: int = 5
    kafka_config: Optional[Dict[str, Any]] = None

@dataclass
class StrategyConfig:
    """Configuration for a strategy engine."""
    strategy_id: str
    strategy_class: str
    symbol: str
    timeframe: str
    parameters: Dict[str, Any]
    worker_id: Optional[str] = None

class StrategyOrchestrator:
    """
    Orchestrates multiple strategy workers and engines for optimal performance.
    
    Features:
    - Dynamic worker and strategy management
    - Load balancing across workers
    - Health monitoring and failover
    - Performance optimization
    - Real-time metrics and monitoring
    """
    
    def __init__(
        self,
        orchestrator_id: str,
        kafka_config: Dict[str, Any],
        config: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize strategy orchestrator.
        
        Args:
            orchestrator_id: Unique identifier for this orchestrator
            kafka_config: Kafka connection configuration
            config: Orchestrator configuration
        """
        self.orchestrator_id = orchestrator_id
        self.kafka_config = kafka_config
        self.config = config or self._get_default_config()
        
        # State management
        self.status = OrchestratorStatus.INITIALIZING
        self.workers: Dict[str, KafkaStrategyWorker] = {}
        self.worker_tasks: Dict[str, asyncio.Task] = {}
        self.strategy_registry: Dict[str, StrategyConfig] = {}
        self.worker_assignments: Dict[str, str] = {}  # strategy_id -> worker_id
        
        # Performance tracking
        self.metrics = {
            "total_strategies": 0,
            "active_workers": 0,
            "messages_processed": 0,
            "signals_generated": 0,
            "errors": 0,
            "uptime_seconds": 0
        }
        
        self.start_time = None
        self.health_check_interval = 30  # seconds
        self.last_health_check = datetime.now()
        
        self.logger = logging.getLogger(f"orchestrator.{orchestrator_id}")
        
    def _get_default_config(self) -> Dict[str, Any]:
        """Get default orchestrator configuration."""
        return {
            "max_workers": 10,
            "max_strategies_per_worker": 5,
            "health_check_interval": 30,
            "worker_restart_threshold": 0.1,  # 10% error rate
            "load_balance_interval": 60,  # seconds
            "metrics_update_interval": 10,  # seconds
            "enable_auto_scaling": True,
            "min_workers": 1,
            "max_worker_load": 0.8
        }
    
    async def start(self) -> None:
        """Start the orchestrator and all configured components."""
        self.logger.info(f"Starting strategy orchestrator: {self.orchestrator_id}")
        self.start_time = datetime.now()
        self.status = OrchestratorStatus.RUNNING
        
        try:
            # Start background tasks
            asyncio.create_task(self._health_monitor())
            asyncio.create_task(self._metrics_updater())
            asyncio.create_task(self._load_balancer())
            
            self.logger.info("Orchestrator started successfully")
            
            # Keep orchestrator running
            while self.status == OrchestratorStatus.RUNNING:
                await asyncio.sleep(1)
                
        except Exception as e:
            self.logger.error(f"Orchestrator error: {str(e)}")
            self.status = OrchestratorStatus.ERROR
            raise
        finally:
            await self.stop()
            
    async def stop(self) -> None:
        """Stop the orchestrator and all workers gracefully."""
        self.logger.info("Stopping strategy orchestrator")
        self.status = OrchestratorStatus.STOPPING
        
        # Stop all workers
        stop_tasks = []
        for worker_id, worker in self.workers.items():
            self.logger.info(f"Stopping worker: {worker_id}")
            stop_tasks.append(worker.stop())
            
        if stop_tasks:
            await asyncio.gather(*stop_tasks, return_exceptions=True)
            
        # Cancel worker tasks
        for task in self.worker_tasks.values():
            if not task.done():
                task.cancel()
                
        self.status = OrchestratorStatus.STOPPED
        self.logger.info("Orchestrator stopped")
        
    def create_worker(self, worker_config: WorkerConfig) -> bool:
        """
        Create and register a new strategy worker.
        
        Args:
            worker_config: Worker configuration
            
        Returns:
            True if worker created successfully
        """
        if worker_config.worker_id in self.workers:
            self.logger.warning(f"Worker {worker_config.worker_id} already exists")
            return False
            
        try:
            # Create worker
            worker = KafkaStrategyWorker(
                worker_id=worker_config.worker_id,
                kafka_config=worker_config.kafka_config or self.kafka_config,
                input_topics=worker_config.input_topics,
                output_topic=worker_config.output_topic
            )
            
            self.workers[worker_config.worker_id] = worker
            self.logger.info(f"Created worker: {worker_config.worker_id}")
            
            # Start worker if orchestrator is running
            if self.status == OrchestratorStatus.RUNNING:
                self._start_worker(worker_config.worker_id)
                
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to create worker {worker_config.worker_id}: {str(e)}")
            return False
            
    def _start_worker(self, worker_id: str) -> None:
        """Start a worker task."""
        if worker_id in self.worker_tasks:
            return
            
        worker = self.workers[worker_id]
        task = asyncio.create_task(worker.start())
        self.worker_tasks[worker_id] = task
        self.logger.info(f"Started worker task: {worker_id}")
        
    def remove_worker(self, worker_id: str) -> bool:
        """
        Remove a strategy worker.
        
        Args:
            worker_id: ID of worker to remove
            
        Returns:
            True if worker removed successfully
        """
        if worker_id not in self.workers:
            return False
            
        try:
            # Stop worker task
            if worker_id in self.worker_tasks:
                task = self.worker_tasks[worker_id]
                if not task.done():
                    task.cancel()
                del self.worker_tasks[worker_id]
                
            # Remove worker
            worker = self.workers[worker_id]
            asyncio.create_task(worker.stop())
            del self.workers[worker_id]
            
            # Reassign strategies from this worker
            self._reassign_strategies_from_worker(worker_id)
            
            self.logger.info(f"Removed worker: {worker_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to remove worker {worker_id}: {str(e)}")
            return False
            
    def register_strategy(self, strategy_config: StrategyConfig) -> bool:
        """
        Register a new strategy configuration.
        
        Args:
            strategy_config: Strategy configuration
            
        Returns:
            True if strategy registered successfully
        """
        if strategy_config.strategy_id in self.strategy_registry:
            self.logger.warning(f"Strategy {strategy_config.strategy_id} already registered")
            return False
            
        try:
            self.strategy_registry[strategy_config.strategy_id] = strategy_config
            
            # Assign to worker
            if strategy_config.worker_id:
                # Specific worker requested
                if strategy_config.worker_id in self.workers:
                    self._assign_strategy_to_worker(strategy_config.strategy_id, strategy_config.worker_id)
                else:
                    self.logger.error(f"Requested worker {strategy_config.worker_id} not found")
                    return False
            else:
                # Auto-assign to best worker
                worker_id = self._find_best_worker_for_strategy(strategy_config)
                if worker_id:
                    self._assign_strategy_to_worker(strategy_config.strategy_id, worker_id)
                else:
                    self.logger.warning(f"No suitable worker found for strategy {strategy_config.strategy_id}")
                    
            self.metrics["total_strategies"] += 1
            self.logger.info(f"Registered strategy: {strategy_config.strategy_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to register strategy {strategy_config.strategy_id}: {str(e)}")
            return False
            
    def unregister_strategy(self, strategy_id: str) -> bool:
        """
        Unregister a strategy.
        
        Args:
            strategy_id: ID of strategy to unregister
            
        Returns:
            True if strategy unregistered successfully
        """
        if strategy_id not in self.strategy_registry:
            return False
            
        try:
            # Remove from worker
            if strategy_id in self.worker_assignments:
                worker_id = self.worker_assignments[strategy_id]
                worker = self.workers.get(worker_id)
                if worker:
                    worker.remove_strategy_engine(strategy_id)
                del self.worker_assignments[strategy_id]
                
            # Remove from registry
            del self.strategy_registry[strategy_id]
            self.metrics["total_strategies"] -= 1
            
            self.logger.info(f"Unregistered strategy: {strategy_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to unregister strategy {strategy_id}: {str(e)}")
            return False
            
    def _assign_strategy_to_worker(self, strategy_id: str, worker_id: str) -> bool:
        """Assign a strategy to a specific worker."""
        if worker_id not in self.workers:
            return False
            
        try:
            # Create strategy engine instance
            strategy_config = self.strategy_registry[strategy_id]
            strategy_engine = self._create_strategy_engine(strategy_config)
            
            if strategy_engine:
                # Add to worker
                worker = self.workers[worker_id]
                worker.add_strategy_engine(strategy_engine)
                self.worker_assignments[strategy_id] = worker_id
                
                self.logger.info(f"Assigned strategy {strategy_id} to worker {worker_id}")
                return True
                
        except Exception as e:
            self.logger.error(f"Failed to assign strategy {strategy_id} to worker {worker_id}: {str(e)}")
            
        return False
        
    def _create_strategy_engine(self, strategy_config: StrategyConfig) -> Optional[BaseStrategyEngine]:
        """Create a strategy engine instance from configuration."""
        try:
            # This would normally use a factory pattern or import system
            # For now, return a placeholder implementation
            self.logger.warning(f"Strategy engine creation not implemented for {strategy_config.strategy_class}")
            return None
            
        except Exception as e:
            self.logger.error(f"Failed to create strategy engine: {str(e)}")
            return None
            
    def _find_best_worker_for_strategy(self, strategy_config: StrategyConfig) -> Optional[str]:
        """Find the best worker for a strategy based on load and compatibility."""
        if not self.workers:
            return None
            
        # Find worker with lowest load
        best_worker = None
        lowest_load = float('inf')
        
        for worker_id, worker in self.workers.items():
            current_load = len(worker.strategy_engines)
            max_load = self.config["max_strategies_per_worker"]
            
            if current_load < max_load and current_load < lowest_load:
                best_worker = worker_id
                lowest_load = current_load
                
        return best_worker
        
    def _reassign_strategies_from_worker(self, failed_worker_id: str) -> None:
        """Reassign strategies from a failed worker to other workers."""
        strategies_to_reassign = [
            strategy_id for strategy_id, worker_id in self.worker_assignments.items()
            if worker_id == failed_worker_id
        ]
        
        for strategy_id in strategies_to_reassign:
            strategy_config = self.strategy_registry[strategy_id]
            new_worker_id = self._find_best_worker_for_strategy(strategy_config)
            
            if new_worker_id:
                # Remove from old assignment
                del self.worker_assignments[strategy_id]
                
                # Assign to new worker
                self._assign_strategy_to_worker(strategy_id, new_worker_id)
                self.logger.info(f"Reassigned strategy {strategy_id} from {failed_worker_id} to {new_worker_id}")
            else:
                self.logger.warning(f"Could not reassign strategy {strategy_id} - no available workers")
                
    async def _health_monitor(self) -> None:
        """Monitor health of all workers and restart if needed."""
        while self.status == OrchestratorStatus.RUNNING:
            try:
                await asyncio.sleep(self.config["health_check_interval"])
                
                failed_workers = []
                
                for worker_id, worker in self.workers.items():
                    health = worker.get_health_status()
                    
                    if not health["healthy"]:
                        self.logger.warning(f"Worker {worker_id} is unhealthy: {health}")
                        
                        # Check if error rate exceeds threshold
                        if health["error_rate"] > self.config["worker_restart_threshold"]:
                            failed_workers.append(worker_id)
                            
                # Restart failed workers
                for worker_id in failed_workers:
                    self.logger.info(f"Restarting failed worker: {worker_id}")
                    await self._restart_worker(worker_id)
                    
                self.last_health_check = datetime.now()
                
            except Exception as e:
                self.logger.error(f"Health monitor error: {str(e)}")
                
    async def _restart_worker(self, worker_id: str) -> None:
        """Restart a failed worker."""
        try:
            # Stop current worker
            if worker_id in self.worker_tasks:
                task = self.worker_tasks[worker_id]
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
                del self.worker_tasks[worker_id]
                
            # Restart worker
            worker = self.workers[worker_id]
            await worker.stop()
            self._start_worker(worker_id)
            
            self.logger.info(f"Restarted worker: {worker_id}")
            
        except Exception as e:
            self.logger.error(f"Failed to restart worker {worker_id}: {str(e)}")
            
    async def _metrics_updater(self) -> None:
        """Update orchestrator metrics periodically."""
        while self.status == OrchestratorStatus.RUNNING:
            try:
                await asyncio.sleep(self.config["metrics_update_interval"])
                
                # Aggregate metrics from all workers
                total_messages = 0
                total_signals = 0
                total_errors = 0
                active_workers = 0
                
                for worker in self.workers.values():
                    worker_metrics = worker.get_metrics()
                    total_messages += worker_metrics["message_count"]
                    total_signals += worker_metrics["metrics"]["signals_generated"]
                    total_errors += worker_metrics["error_count"]
                    
                    if worker_metrics["is_running"]:
                        active_workers += 1
                        
                # Update metrics
                self.metrics.update({
                    "active_workers": active_workers,
                    "messages_processed": total_messages,
                    "signals_generated": total_signals,
                    "errors": total_errors,
                    "uptime_seconds": (datetime.now() - self.start_time).total_seconds() if self.start_time else 0
                })
                
            except Exception as e:
                self.logger.error(f"Metrics update error: {str(e)}")
                
    async def _load_balancer(self) -> None:
        """Rebalance strategies across workers for optimal performance."""
        while self.status == OrchestratorStatus.RUNNING:
            try:
                await asyncio.sleep(self.config["load_balance_interval"])
                
                if not self.config["enable_auto_scaling"]:
                    continue
                    
                # Analyze current load distribution
                worker_loads = {}
                for worker_id, worker in self.workers.items():
                    worker_loads[worker_id] = len(worker.strategy_engines)
                    
                # Check if rebalancing is needed
                if len(worker_loads) > 1:
                    max_load = max(worker_loads.values())
                    min_load = min(worker_loads.values())
                    
                    # If load difference is significant, rebalance
                    if max_load - min_load > 2:
                        await self._rebalance_strategies(worker_loads)
                        
            except Exception as e:
                self.logger.error(f"Load balancer error: {str(e)}")
                
    async def _rebalance_strategies(self, worker_loads: Dict[str, int]) -> None:
        """Rebalance strategies across workers."""
        # Find overloaded and underloaded workers
        avg_load = sum(worker_loads.values()) / len(worker_loads)
        
        overloaded = [(w, l) for w, l in worker_loads.items() if l > avg_load + 1]
        underloaded = [(w, l) for w, l in worker_loads.items() if l < avg_load - 1]
        
        # Move strategies from overloaded to underloaded workers
        for overloaded_worker, _ in overloaded:
            if not underloaded:
                break
                
            # Find a strategy to move
            strategies_in_worker = [
                s_id for s_id, w_id in self.worker_assignments.items()
                if w_id == overloaded_worker
            ]
            
            if strategies_in_worker:
                strategy_to_move = strategies_in_worker[0]
                target_worker, _ = underloaded[0]
                
                # Move strategy
                self.workers[overloaded_worker].remove_strategy_engine(strategy_to_move)
                self._assign_strategy_to_worker(strategy_to_move, target_worker)
                
                self.logger.info(f"Rebalanced strategy {strategy_to_move} from {overloaded_worker} to {target_worker}")
                
                # Update load tracking
                underloaded[0] = (target_worker, underloaded[0][1] + 1)
                if underloaded[0][1] >= avg_load:
                    underloaded.pop(0)
                    
    def get_status(self) -> Dict[str, Any]:
        """
        Get comprehensive orchestrator status.
        
        Returns:
            Dictionary containing status information
        """
        worker_status = {}
        for worker_id, worker in self.workers.items():
            worker_status[worker_id] = worker.get_health_status()
            
        return {
            "orchestrator_id": self.orchestrator_id,
            "status": self.status.value,
            "uptime_seconds": self.metrics["uptime_seconds"],
            "total_workers": len(self.workers),
            "active_workers": self.metrics["active_workers"],
            "total_strategies": self.metrics["total_strategies"],
            "messages_processed": self.metrics["messages_processed"],
            "signals_generated": self.metrics["signals_generated"],
            "error_count": self.metrics["errors"],
            "last_health_check": self.last_health_check.isoformat(),
            "worker_status": worker_status,
            "strategy_assignments": self.worker_assignments
        }
        
    def get_metrics(self) -> Dict[str, Any]:
        """Get detailed performance metrics."""
        worker_metrics = {}
        for worker_id, worker in self.workers.items():
            worker_metrics[worker_id] = worker.get_metrics()
            
        return {
            "orchestrator_metrics": self.metrics,
            "worker_metrics": worker_metrics,
            "timestamp": datetime.now().isoformat()
        }

