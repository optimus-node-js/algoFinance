"""
Strategy Engine Main Entry Point
===============================

Main entry point for running the HFT Strategy Engine Framework.
Provides command-line interface and configuration management.
"""

import asyncio
import argparse
import json
import logging
import sys
import os
from pathlib import Path
from typing import Dict, Any

from .strategy_orchestrator import StrategyOrchestrator, WorkerConfig, StrategyConfig
from .kafka_strategy_worker import KafkaStrategyWorker
from .examples.momentum_strategy import MomentumStrategy
from .risk_integration import RiskIntegrationClient, RiskEnhancedStrategyEngine
from .health_server import StrategyEngineHealthServer

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger("strategy_engine_main")

class StrategyEngineRunner:
    """
    Main runner for the Strategy Engine Framework.
    
    Handles configuration, orchestrator setup, and worker management.
    """
    
    def __init__(self, config_path: str = None):
        """
        Initialize strategy engine runner.
        
        Args:
            config_path: Path to configuration file
        """
        self.config_path = config_path
        self.config = self._load_config()
        self.orchestrator = None
        
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from file or use defaults."""
        # Docker environment detection
        is_docker = os.getenv("STRATEGY_ENGINE_ENV") == "production"
        kafka_servers = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
        risk_url = os.getenv("RISK_SERVICE_URL", "http://localhost:8003")
        
        default_config = {
            "kafka": {
                "bootstrap.servers": kafka_servers,
                "client.id": "hft_strategy_engine"
            },
            "risk_service": {
                "url": risk_url,
                "timeout_seconds": 5,
                "enable_risk_checks": True
            },
            "orchestrator": {
                "orchestrator_id": "hft_main_orchestrator",
                "max_workers": 3,
                "health_check_interval": 30
            },
            "workers": [
                {
                    "worker_id": "momentum_worker",
                    "input_topics": ["market_data"],
                    "output_topic": "trading_signals",
                    "max_strategies": 3
                }
            ],
            "strategies": [
                {
                    "strategy_id": "momentum_reliance",
                    "strategy_class": "MomentumStrategy",
                    "symbol": "RELIANCE",
                    "timeframe": "1m",
                    "parameters": {
                        "momentum_threshold": 0.02,
                        "rsi_momentum_level": 60
                    }
                }
            ],
            "metrics": {
                "enable_metrics_server": True,
                "metrics_port": int(os.getenv("METRICS_PORT", "8004"))
            }
        }
        
        if self.config_path and Path(self.config_path).exists():
            try:
                with open(self.config_path, 'r') as f:
                    file_config = json.load(f)
                    default_config.update(file_config)
                    logger.info(f"Loaded configuration from {self.config_path}")
            except Exception as e:
                logger.error(f"Failed to load config file: {e}")
                logger.info("Using default configuration")
        else:
            logger.info("Using default configuration")
            
        return default_config
        
    async def start(self) -> None:
        """Start the strategy engine framework."""
        logger.info("Starting HFT Strategy Engine Framework")
        
        health_server = None
        
        try:
            # Initialize health server
            if self.config.get("metrics", {}).get("enable_metrics_server", True):
                metrics_port = self.config["metrics"]["metrics_port"]
                health_server = StrategyEngineHealthServer(port=metrics_port)
                await health_server.start_server()
                logger.info(f"Health server started on port {metrics_port}")
            
            # Initialize orchestrator
            self.orchestrator = StrategyOrchestrator(
                orchestrator_id=self.config["orchestrator"]["orchestrator_id"],
                kafka_config=self.config["kafka"],
                config=self.config["orchestrator"]
            )
            
            # Link health server with orchestrator
            if health_server:
                health_server.set_orchestrator(self.orchestrator)
            
            # Create workers
            for worker_config in self.config["workers"]:
                worker_cfg = WorkerConfig(
                    worker_id=worker_config["worker_id"],
                    input_topics=worker_config["input_topics"],
                    output_topic=worker_config["output_topic"],
                    max_strategies=worker_config.get("max_strategies", 5),
                    kafka_config=self.config["kafka"]
                )
                
                success = self.orchestrator.create_worker(worker_cfg)
                if success:
                    logger.info(f"Created worker: {worker_cfg.worker_id}")
                else:
                    logger.error(f"Failed to create worker: {worker_cfg.worker_id}")
                    
            # Register strategies
            for strategy_config in self.config["strategies"]:
                strategy_cfg = StrategyConfig(
                    strategy_id=strategy_config["strategy_id"],
                    strategy_class=strategy_config["strategy_class"],
                    symbol=strategy_config["symbol"],
                    timeframe=strategy_config["timeframe"],
                    parameters=strategy_config.get("parameters", {}),
                    worker_id=strategy_config.get("worker_id")
                )
                
                success = self.orchestrator.register_strategy(strategy_cfg)
                if success:
                    logger.info(f"Registered strategy: {strategy_cfg.strategy_id}")
                else:
                    logger.error(f"Failed to register strategy: {strategy_cfg.strategy_id}")
                    
            # Start orchestrator
            logger.info("Strategy Engine Framework ready - all components initialized")
            await self.orchestrator.start()
            
        except KeyboardInterrupt:
            logger.info("Received shutdown signal")
        except Exception as e:
            logger.error(f"Strategy engine error: {e}")
            raise
        finally:
            if self.orchestrator:
                await self.orchestrator.stop()
                
    def get_status(self) -> Dict[str, Any]:
        """Get current status of the strategy engine."""
        if self.orchestrator:
            return self.orchestrator.get_status()
        else:
            return {"status": "not_running"}

async def run_standalone_worker():
    """Run a standalone worker for testing."""
    logger.info("Starting standalone strategy worker")
    
    # Kafka configuration
    kafka_config = {
        "bootstrap.servers": "localhost:9092",
        "client.id": "standalone_worker"
    }
    
    # Create worker
    worker = KafkaStrategyWorker(
        worker_id="standalone_test",
        kafka_config=kafka_config,
        input_topics=["market_data"],
        output_topic="trading_signals"
    )
    
    # Create and add momentum strategy
    momentum_strategy = MomentumStrategy(
        strategy_id="test_momentum",
        symbol="RELIANCE",
        timeframe="1m"
    )
    
    # Add risk integration if enabled
    risk_config = {
        "url": "http://localhost:8003",
        "timeout_seconds": 5
    }
    
    try:
        risk_client = RiskIntegrationClient(**risk_config)
        enhanced_strategy = RiskEnhancedStrategyEngine(
            momentum_strategy,
            risk_client
        )
        worker.add_strategy_engine(enhanced_strategy)
        logger.info("Added risk-enhanced momentum strategy")
    except Exception as e:
        logger.warning(f"Risk integration failed, using basic strategy: {e}")
        worker.add_strategy_engine(momentum_strategy)
        
    # Start worker
    try:
        await worker.start()
    except KeyboardInterrupt:
        logger.info("Stopping standalone worker")
    finally:
        await worker.stop()

def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="HFT Strategy Engine Framework")
    parser.add_argument(
        "--config", 
        help="Path to configuration file",
        default=None
    )
    parser.add_argument(
        "--mode",
        choices=["orchestrator", "standalone"],
        default="orchestrator",
        help="Run mode: orchestrator (default) or standalone worker"
    )
    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default="INFO",
        help="Logging level"
    )
    
    args = parser.parse_args()
    
    # Set logging level
    logging.getLogger().setLevel(getattr(logging, args.log_level))
    
    try:
        if args.mode == "standalone":
            asyncio.run(run_standalone_worker())
        else:
            runner = StrategyEngineRunner(args.config)
            asyncio.run(runner.start())
    except KeyboardInterrupt:
        logger.info("Shutdown requested")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
