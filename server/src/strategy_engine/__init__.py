"""
HFT Strategy Engine Framework
============================

Enhanced strategy engine with Kafka integration, real-time signal processing,
and multi-strategy orchestration for high-frequency trading.

Core Components:
- BaseStrategyEngine: Abstract base for all strategy engines
- KafkaStrategyWorker: Kafka-integrated strategy worker
- SignalProcessor: Signal generation and processing
- StrategyOrchestrator: Multi-strategy coordination
- RiskIntegration: Integration with risk service

Features:
- Real-time market data processing via Kafka
- Sub-100ms signal generation
- Risk service integration
- Multi-strategy parallel execution
- Performance monitoring and metrics
"""

__version__ = "1.0.0"
__author__ = "HFT Development Team"

from .base_strategy_engine import BaseStrategyEngine
from .kafka_strategy_worker import KafkaStrategyWorker
from .signal_processor import SignalProcessor
from .strategy_orchestrator import StrategyOrchestrator

__all__ = [
    "BaseStrategyEngine",
    "KafkaStrategyWorker", 
    "SignalProcessor",
    "StrategyOrchestrator"
]

