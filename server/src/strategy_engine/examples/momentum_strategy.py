"""
Momentum Strategy Example
========================

Example momentum-based trading strategy using the HFT Strategy Engine Framework.
Demonstrates technical indicator integration and signal generation.
"""

import pandas as pd
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime

from ..base_strategy_engine import BaseStrategyEngine
from ..signal_processor import SignalProcessor, TechnicalIndicators

class MomentumStrategy(BaseStrategyEngine):
    """
    Momentum trading strategy that follows price trends.
    
    Strategy Logic:
    - Uses moving averages and RSI for trend detection
    - Enters positions in direction of strong momentum
    - Exits on momentum reversal signals
    """
    
    def __init__(self, strategy_id: str, symbol: str, timeframe: str = "1m"):
        """Initialize momentum strategy."""
        super().__init__(strategy_id, symbol, timeframe)
        
        # Strategy-specific configuration
        self.config.update({
            "momentum_threshold": 0.02,  # 2% price movement threshold
            "rsi_momentum_level": 60,    # RSI level for momentum confirmation
            "sma_fast_period": 10,       # Fast SMA period
            "sma_slow_period": 20,       # Slow SMA period
            "volume_threshold": 1.5      # Volume spike threshold
        })
        
        # Initialize signal processor
        self.signal_processor = SignalProcessor(symbol, {
            "min_confidence": 0.7,
            "rsi_overbought": 80,
            "rsi_oversold": 20
        })
        
        # Strategy state
        self.price_history = []
        self.volume_history = []
        self.last_entry_price = 0.0
        self.position_direction = None  # "LONG", "SHORT", or None
        
    def analyze_market_data(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze market data for momentum signals.
        
        Args:
            market_data: Real-time market data
            
        Returns:
            Analysis results with momentum indicators
        """
        price = market_data.get("ltp", market_data.get("price", 0))
        volume = market_data.get("volume", 0)
        
        # Update price and volume history
        self.price_history.append(price)
        self.volume_history.append(volume)
        
        # Maintain history length
        max_history = 50
        if len(self.price_history) > max_history:
            self.price_history = self.price_history[-max_history:]
            self.volume_history = self.volume_history[-max_history:]
            
        if len(self.price_history) < 20:
            return {"insufficient_data": True}
            
        # Calculate technical indicators
        sma_fast = TechnicalIndicators.sma(self.price_history, self.config["sma_fast_period"])
        sma_slow = TechnicalIndicators.sma(self.price_history, self.config["sma_slow_period"])
        rsi = TechnicalIndicators.rsi(self.price_history)
        
        # Calculate momentum metrics
        price_change_pct = 0
        if len(self.price_history) >= 5:
            old_price = self.price_history[-5]
            price_change_pct = (price - old_price) / old_price if old_price > 0 else 0
            
        # Volume analysis
        avg_volume = sum(self.volume_history[-10:]) / min(len(self.volume_history), 10)
        volume_ratio = volume / avg_volume if avg_volume > 0 else 1.0
        
        # Momentum strength calculation
        momentum_strength = abs(price_change_pct) * volume_ratio
        
        return {
            "current_price": price,
            "sma_fast": sma_fast,
            "sma_slow": sma_slow,
            "rsi": rsi,
            "price_change_pct": price_change_pct,
            "volume_ratio": volume_ratio,
            "momentum_strength": momentum_strength,
            "trend_direction": "UP" if sma_fast > sma_slow else "DOWN",
            "volume_confirmation": volume_ratio > self.config["volume_threshold"]
        }
        
    def generate_signal(self, analysis: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Generate momentum-based trading signals.
        
        Args:
            analysis: Market analysis results
            
        Returns:
            Trading signal or None
        """
        if analysis.get("insufficient_data"):
            return None
            
        current_price = analysis["current_price"]
        sma_fast = analysis["sma_fast"]
        sma_slow = analysis["sma_slow"]
        rsi = analysis["rsi"]
        price_change_pct = analysis["price_change_pct"]
        momentum_strength = analysis["momentum_strength"]
        volume_confirmation = analysis["volume_confirmation"]
        
        # Entry signals
        if self.position_direction is None:
            # Look for strong momentum entry
            if (price_change_pct > self.config["momentum_threshold"] and
                rsi > self.config["rsi_momentum_level"] and
                sma_fast > sma_slow and
                volume_confirmation):
                
                confidence = min(momentum_strength * 2, 1.0)
                
                return {
                    "action": "BUY",
                    "confidence": confidence,
                    "reason": "MOMENTUM_ENTRY_LONG",
                    "entry_price": current_price,
                    "stop_loss": current_price * 0.98,  # 2% stop loss
                    "take_profit": current_price * 1.06  # 6% take profit
                }
                
            elif (price_change_pct < -self.config["momentum_threshold"] and
                  rsi < (100 - self.config["rsi_momentum_level"]) and
                  sma_fast < sma_slow and
                  volume_confirmation):
                
                confidence = min(momentum_strength * 2, 1.0)
                
                return {
                    "action": "SELL",
                    "confidence": confidence,
                    "reason": "MOMENTUM_ENTRY_SHORT",
                    "entry_price": current_price,
                    "stop_loss": current_price * 1.02,  # 2% stop loss
                    "take_profit": current_price * 0.94  # 6% take profit
                }
                
        # Exit signals
        else:
            if self.position_direction == "LONG":
                # Exit long position
                if (sma_fast < sma_slow or 
                    rsi > 80 or
                    price_change_pct < -self.config["momentum_threshold"]):
                    
                    return {
                        "action": "SELL",
                        "confidence": 0.8,
                        "reason": "MOMENTUM_EXIT_LONG",
                        "exit_price": current_price
                    }
                    
            elif self.position_direction == "SHORT":
                # Exit short position
                if (sma_fast > sma_slow or
                    rsi < 20 or
                    price_change_pct > self.config["momentum_threshold"]):
                    
                    return {
                        "action": "BUY",
                        "confidence": 0.8,
                        "reason": "MOMENTUM_EXIT_SHORT",
                        "exit_price": current_price
                    }
                    
        return None
        
    def calculate_position_size(self, signal: Dict[str, Any], market_data: Dict[str, Any]) -> int:
        """
        Calculate position size based on momentum strength and risk.
        
        Args:
            signal: Trading signal
            market_data: Current market data
            
        Returns:
            Position size
        """
        base_size = 100  # Base position size
        confidence = signal.get("confidence", 0.5)
        
        # Adjust size based on confidence and momentum
        size_multiplier = 0.5 + (confidence * 1.5)  # 0.5x to 2x base size
        position_size = int(base_size * size_multiplier)
        
        # Apply maximum position size limit
        max_size = self.config["max_position_size"]
        return min(position_size, max_size)
        
    def generate_signals_batch(self, historical_data: pd.DataFrame) -> Tuple[pd.Series, pd.Series]:
        """
        Generate signals for backtesting on historical data.
        
        Args:
            historical_data: OHLCV DataFrame
            
        Returns:
            Tuple of (entry_signals, exit_signals)
        """
        if len(historical_data) < 20:
            empty_series = pd.Series(False, index=historical_data.index)
            return empty_series, empty_series
            
        # Calculate indicators
        fast_sma = historical_data['close'].rolling(self.config["sma_fast_period"]).mean()
        slow_sma = historical_data['close'].rolling(self.config["sma_slow_period"]).mean()
        
        # Calculate RSI
        delta = historical_data['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        
        # Calculate price change
        price_change_pct = historical_data['close'].pct_change(5)
        
        # Volume analysis
        volume_ratio = historical_data['volume'] / historical_data['volume'].rolling(10).mean()
        
        # Entry conditions
        long_entry = (
            (price_change_pct > self.config["momentum_threshold"]) &
            (rsi > self.config["rsi_momentum_level"]) &
            (fast_sma > slow_sma) &
            (volume_ratio > self.config["volume_threshold"])
        )
        
        short_entry = (
            (price_change_pct < -self.config["momentum_threshold"]) &
            (rsi < (100 - self.config["rsi_momentum_level"])) &
            (fast_sma < slow_sma) &
            (volume_ratio > self.config["volume_threshold"])
        )
        
        # Exit conditions (simplified for backtesting)
        long_exit = (fast_sma < slow_sma) | (rsi > 80)
        short_exit = (fast_sma > slow_sma) | (rsi < 20)
        
        # Combine entry signals
        entry_signals = long_entry | short_entry
        exit_signals = long_exit | short_exit
        
        return entry_signals.fillna(False), exit_signals.fillna(False)
        
    def update_position_state(self, signal: Dict[str, Any]) -> None:
        """Update position state after signal execution."""
        action = signal.get("action")
        
        if action == "BUY":
            if self.position_direction == "SHORT":
                # Closing short position
                self.position_direction = None
            else:
                # Opening long position
                self.position_direction = "LONG"
                self.last_entry_price = signal.get("entry_price", 0)
                
        elif action == "SELL":
            if self.position_direction == "LONG":
                # Closing long position
                self.position_direction = None
            else:
                # Opening short position
                self.position_direction = "SHORT"
                self.last_entry_price = signal.get("entry_price", 0)

