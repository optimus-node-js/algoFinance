"""
Base Strategy Engine
===================

Abstract base class for all strategy engines in the HFT system.
Provides common interface and functionality for strategy implementations.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
import pandas as pd
import logging

class BaseStrategyEngine(ABC):
    """
    Abstract base class for all trading strategy engines.
    
    Each strategy engine must implement core methods for signal generation,
    risk assessment, and order creation. The engine receives market data
    and produces trading signals with risk assessments.
    """
    
    def __init__(self, strategy_id: str, symbol: str, timeframe: str = "1m"):
        """
        Initialize the base strategy engine.
        
        Args:
            strategy_id: Unique identifier for this strategy instance
            symbol: Trading symbol (e.g., "RELIANCE", "TCS")
            timeframe: Timeframe for analysis (1m, 5m, 15m, 1h, 1d)
        """
        self.strategy_id = strategy_id
        self.symbol = symbol
        self.timeframe = timeframe
        self.is_active = True
        self.last_signal_time = datetime.min
        self.performance_metrics = {
            "signals_generated": 0,
            "orders_placed": 0,
            "success_rate": 0.0,
            "avg_latency_ms": 0.0
        }
        
        # Strategy configuration
        self.config = {
            "min_signal_interval": 1,  # Minimum seconds between signals
            "max_position_size": 1000,  # Maximum position size
            "risk_tolerance": 0.02,     # Risk tolerance (2%)
            "enable_risk_checks": True
        }
        
        self.logger = logging.getLogger(f"strategy.{strategy_id}")
        
    @abstractmethod
    def analyze_market_data(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze incoming market data and generate technical indicators.
        
        Args:
            market_data: Real-time market data from Kafka
            
        Returns:
            Dict containing analysis results and indicators
        """
        pass
    
    @abstractmethod
    def generate_signal(self, analysis: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Generate trading signal based on market analysis.
        
        Args:
            analysis: Results from analyze_market_data()
            
        Returns:
            Trading signal dictionary or None if no signal
        """
        pass
    
    @abstractmethod
    def calculate_position_size(self, signal: Dict[str, Any], market_data: Dict[str, Any]) -> int:
        """
        Calculate optimal position size based on signal strength and risk.
        
        Args:
            signal: Trading signal from generate_signal()
            market_data: Current market data
            
        Returns:
            Position size (number of shares/contracts)
        """
        pass
    
    def validate_signal(self, signal: Dict[str, Any]) -> bool:
        """
        Validate signal against basic criteria (timing, thresholds, etc.)
        
        Args:
            signal: Trading signal to validate
            
        Returns:
            True if signal is valid, False otherwise
        """
        if not signal:
            return False
            
        # Check minimum time interval between signals
        time_since_last = (datetime.now() - self.last_signal_time).total_seconds()
        if time_since_last < self.config["min_signal_interval"]:
            return False
            
        # Check required signal fields
        required_fields = ["action", "confidence", "symbol", "quantity"]
        if not all(field in signal for field in required_fields):
            self.logger.warning(f"Signal missing required fields: {required_fields}")
            return False
            
        # Validate confidence score
        confidence = signal.get("confidence", 0)
        if confidence < 0.5:  # Minimum confidence threshold
            return False
            
        return True
    
    def process_market_data(self, market_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Main processing pipeline: analyze data -> generate signal -> validate.
        
        Args:
            market_data: Real-time market data from Kafka
            
        Returns:
            Validated trading signal or None
        """
        if not self.is_active:
            return None
            
        try:
            start_time = datetime.now()
            
            # Step 1: Analyze market data
            analysis = self.analyze_market_data(market_data)
            
            # Step 2: Generate signal
            signal = self.generate_signal(analysis)
            
            if signal:
                # Step 3: Calculate position size
                position_size = self.calculate_position_size(signal, market_data)
                signal["quantity"] = position_size
                
                # Step 4: Validate signal
                if self.validate_signal(signal):
                    # Update performance metrics
                    processing_time = (datetime.now() - start_time).total_seconds() * 1000
                    self.performance_metrics["avg_latency_ms"] = processing_time
                    self.performance_metrics["signals_generated"] += 1
                    self.last_signal_time = datetime.now()
                    
                    self.logger.info(f"Generated signal: {signal['action']} {signal['quantity']} {signal['symbol']} (confidence: {signal['confidence']:.2f})")
                    return signal
                    
        except Exception as e:
            self.logger.error(f"Error processing market data: {str(e)}")
            
        return None
    
    def update_config(self, new_config: Dict[str, Any]) -> None:
        """
        Update strategy configuration parameters.
        
        Args:
            new_config: Dictionary of configuration updates
        """
        self.config.update(new_config)
        self.logger.info(f"Updated config: {new_config}")
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """
        Get current performance metrics for this strategy.
        
        Returns:
            Dictionary containing performance metrics
        """
        return {
            **self.performance_metrics,
            "strategy_id": self.strategy_id,
            "symbol": self.symbol,
            "is_active": self.is_active,
            "last_signal_time": self.last_signal_time.isoformat() if self.last_signal_time != datetime.min else None
        }
    
    def activate(self) -> None:
        """Activate this strategy engine."""
        self.is_active = True
        self.logger.info(f"Strategy {self.strategy_id} activated")
    
    def deactivate(self) -> None:
        """Deactivate this strategy engine."""
        self.is_active = False
        self.logger.info(f"Strategy {self.strategy_id} deactivated")
    
    # Backtesting support methods
    @abstractmethod
    def generate_signals_batch(self, historical_data: pd.DataFrame) -> Tuple[pd.Series, pd.Series]:
        """
        Generate trading signals for backtesting on historical data.
        
        Args:
            historical_data: DataFrame with OHLCV data
            
        Returns:
            Tuple of (entry_signals, exit_signals) as boolean Series
        """
        pass
    
    def __str__(self) -> str:
        return f"StrategyEngine(id={self.strategy_id}, symbol={self.symbol}, active={self.is_active})"
    
    def __repr__(self) -> str:
        return self.__str__()

