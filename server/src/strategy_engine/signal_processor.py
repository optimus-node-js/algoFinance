"""
Signal Processor
===============

Advanced signal generation and processing system for HFT strategies.
Provides technical analysis, pattern recognition, and signal validation.
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
import logging
from enum import Enum

class SignalType(Enum):
    """Signal types for trading actions."""
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"
    STOP_LOSS = "STOP_LOSS"
    TAKE_PROFIT = "TAKE_PROFIT"

class SignalStrength(Enum):
    """Signal strength levels."""
    WEAK = 0.5
    MODERATE = 0.7
    STRONG = 0.9
    VERY_STRONG = 1.0

class TechnicalIndicators:
    """
    Collection of technical indicators for signal generation.
    Optimized for real-time processing with minimal latency.
    """
    
    @staticmethod
    def sma(prices: List[float], period: int) -> float:
        """Simple Moving Average."""
        if len(prices) < period:
            return 0.0
        return sum(prices[-period:]) / period
    
    @staticmethod
    def ema(prices: List[float], period: int, smoothing: float = 2.0) -> float:
        """Exponential Moving Average."""
        if len(prices) < period:
            return prices[-1] if prices else 0.0
            
        multiplier = smoothing / (period + 1)
        ema_today = prices[-1]
        
        for i in range(len(prices) - 2, max(len(prices) - period - 1, -1), -1):
            ema_today = (prices[i] * multiplier) + (ema_today * (1 - multiplier))
            
        return ema_today
    
    @staticmethod
    def rsi(prices: List[float], period: int = 14) -> float:
        """Relative Strength Index."""
        if len(prices) < period + 1:
            return 50.0
            
        deltas = [prices[i] - prices[i-1] for i in range(1, len(prices))]
        gains = [d if d > 0 else 0 for d in deltas[-period:]]
        losses = [-d if d < 0 else 0 for d in deltas[-period:]]
        
        avg_gain = sum(gains) / period
        avg_loss = sum(losses) / period
        
        if avg_loss == 0:
            return 100.0
            
        rs = avg_gain / avg_loss
        return 100 - (100 / (1 + rs))
    
    @staticmethod
    def macd(prices: List[float], fast: int = 12, slow: int = 26, signal: int = 9) -> Tuple[float, float, float]:
        """MACD indicator (MACD line, Signal line, Histogram)."""
        if len(prices) < slow:
            return 0.0, 0.0, 0.0
            
        ema_fast = TechnicalIndicators.ema(prices, fast)
        ema_slow = TechnicalIndicators.ema(prices, slow)
        macd_line = ema_fast - ema_slow
        
        # For signal line, we'd need historical MACD values
        # Simplified version for real-time processing
        signal_line = macd_line * 0.9  # Approximation
        histogram = macd_line - signal_line
        
        return macd_line, signal_line, histogram
    
    @staticmethod
    def bollinger_bands(prices: List[float], period: int = 20, std_dev: float = 2.0) -> Tuple[float, float, float]:
        """Bollinger Bands (Upper, Middle, Lower)."""
        if len(prices) < period:
            current_price = prices[-1] if prices else 0.0
            return current_price, current_price, current_price
            
        sma = TechnicalIndicators.sma(prices, period)
        
        # Calculate standard deviation
        recent_prices = prices[-period:]
        variance = sum((price - sma) ** 2 for price in recent_prices) / period
        std = variance ** 0.5
        
        upper_band = sma + (std_dev * std)
        lower_band = sma - (std_dev * std)
        
        return upper_band, sma, lower_band

class PatternDetector:
    """
    Pattern detection for common trading patterns.
    Optimized for real-time processing.
    """
    
    @staticmethod
    def detect_breakout(prices: List[float], volume: List[float], lookback: int = 20) -> Dict[str, Any]:
        """
        Detect price breakout patterns.
        
        Returns:
            Dictionary with breakout information
        """
        if len(prices) < lookback:
            return {"detected": False, "type": None, "strength": 0.0}
            
        recent_prices = prices[-lookback:]
        recent_volume = volume[-lookback:] if len(volume) >= lookback else []
        
        # Calculate resistance and support levels
        resistance = max(recent_prices[:-1])  # Exclude current price
        support = min(recent_prices[:-1])
        current_price = prices[-1]
        
        # Check for breakout
        breakout_threshold = 0.005  # 0.5% breakout threshold
        
        if current_price > resistance * (1 + breakout_threshold):
            # Upward breakout
            volume_confirmation = False
            if recent_volume:
                avg_volume = sum(recent_volume[:-1]) / len(recent_volume[:-1])
                current_volume = recent_volume[-1]
                volume_confirmation = current_volume > avg_volume * 1.5
                
            return {
                "detected": True,
                "type": "upward_breakout",
                "strength": min((current_price - resistance) / resistance * 10, 1.0),
                "volume_confirmation": volume_confirmation,
                "resistance_level": resistance
            }
            
        elif current_price < support * (1 - breakout_threshold):
            # Downward breakout
            volume_confirmation = False
            if recent_volume:
                avg_volume = sum(recent_volume[:-1]) / len(recent_volume[:-1])
                current_volume = recent_volume[-1]
                volume_confirmation = current_volume > avg_volume * 1.5
                
            return {
                "detected": True,
                "type": "downward_breakout",
                "strength": min((support - current_price) / support * 10, 1.0),
                "volume_confirmation": volume_confirmation,
                "support_level": support
            }
            
        return {"detected": False, "type": None, "strength": 0.0}
    
    @staticmethod
    def detect_trend_reversal(prices: List[float], period: int = 10) -> Dict[str, Any]:
        """
        Detect trend reversal patterns.
        
        Returns:
            Dictionary with reversal information
        """
        if len(prices) < period * 2:
            return {"detected": False, "type": None, "confidence": 0.0}
            
        # Split into two periods
        first_half = prices[-period*2:-period]
        second_half = prices[-period:]
        
        # Calculate trends
        first_trend = (first_half[-1] - first_half[0]) / len(first_half)
        second_trend = (second_half[-1] - second_half[0]) / len(second_half)
        
        # Check for reversal
        if first_trend > 0 and second_trend < 0:
            # Uptrend to downtrend
            confidence = min(abs(first_trend - second_trend) * 1000, 1.0)
            return {
                "detected": True,
                "type": "bearish_reversal",
                "confidence": confidence,
                "first_trend": first_trend,
                "second_trend": second_trend
            }
        elif first_trend < 0 and second_trend > 0:
            # Downtrend to uptrend
            confidence = min(abs(first_trend - second_trend) * 1000, 1.0)
            return {
                "detected": True,
                "type": "bullish_reversal",
                "confidence": confidence,
                "first_trend": first_trend,
                "second_trend": second_trend
            }
            
        return {"detected": False, "type": None, "confidence": 0.0}

class SignalProcessor:
    """
    Advanced signal processor that combines technical indicators,
    pattern detection, and risk assessment for signal generation.
    """
    
    def __init__(self, symbol: str, config: Optional[Dict[str, Any]] = None):
        """
        Initialize signal processor.
        
        Args:
            symbol: Trading symbol
            config: Configuration parameters
        """
        self.symbol = symbol
        self.config = config or self._get_default_config()
        self.price_history = []
        self.volume_history = []
        self.signal_history = []
        self.last_signal_time = datetime.min
        
        self.logger = logging.getLogger(f"signal_processor.{symbol}")
        
    def _get_default_config(self) -> Dict[str, Any]:
        """Get default configuration."""
        return {
            "max_history_length": 200,
            "min_signal_interval": 30,  # seconds
            "rsi_overbought": 70,
            "rsi_oversold": 30,
            "macd_signal_threshold": 0.001,
            "breakout_threshold": 0.005,
            "volume_spike_threshold": 2.0,
            "min_confidence": 0.6
        }
    
    def update_market_data(self, price: float, volume: float, timestamp: datetime) -> None:
        """
        Update market data history.
        
        Args:
            price: Current price
            volume: Current volume
            timestamp: Data timestamp
        """
        self.price_history.append(price)
        self.volume_history.append(volume)
        
        # Maintain maximum history length
        max_length = self.config["max_history_length"]
        if len(self.price_history) > max_length:
            self.price_history = self.price_history[-max_length:]
            self.volume_history = self.volume_history[-max_length:]
    
    def calculate_indicators(self) -> Dict[str, Any]:
        """
        Calculate all technical indicators.
        
        Returns:
            Dictionary containing indicator values
        """
        if len(self.price_history) < 20:
            return {}
            
        indicators = {}
        
        # Moving averages
        indicators["sma_20"] = TechnicalIndicators.sma(self.price_history, 20)
        indicators["sma_50"] = TechnicalIndicators.sma(self.price_history, 50)
        indicators["ema_12"] = TechnicalIndicators.ema(self.price_history, 12)
        indicators["ema_26"] = TechnicalIndicators.ema(self.price_history, 26)
        
        # Momentum indicators
        indicators["rsi"] = TechnicalIndicators.rsi(self.price_history)
        
        # MACD
        macd_line, signal_line, histogram = TechnicalIndicators.macd(self.price_history)
        indicators["macd"] = macd_line
        indicators["macd_signal"] = signal_line
        indicators["macd_histogram"] = histogram
        
        # Bollinger Bands
        bb_upper, bb_middle, bb_lower = TechnicalIndicators.bollinger_bands(self.price_history)
        indicators["bb_upper"] = bb_upper
        indicators["bb_middle"] = bb_middle
        indicators["bb_lower"] = bb_lower
        
        # Current price position
        current_price = self.price_history[-1]
        indicators["price_vs_sma20"] = (current_price - indicators["sma_20"]) / indicators["sma_20"]
        indicators["bb_position"] = (current_price - bb_lower) / (bb_upper - bb_lower)
        
        return indicators
    
    def detect_patterns(self) -> Dict[str, Any]:
        """
        Detect trading patterns.
        
        Returns:
            Dictionary containing pattern information
        """
        patterns = {}
        
        # Breakout detection
        breakout = PatternDetector.detect_breakout(self.price_history, self.volume_history)
        patterns["breakout"] = breakout
        
        # Trend reversal detection
        reversal = PatternDetector.detect_trend_reversal(self.price_history)
        patterns["reversal"] = reversal
        
        # Volume analysis
        if len(self.volume_history) >= 20:
            avg_volume = sum(self.volume_history[-20:-1]) / 19
            current_volume = self.volume_history[-1]
            volume_ratio = current_volume / avg_volume if avg_volume > 0 else 1.0
            
            patterns["volume_spike"] = {
                "detected": volume_ratio > self.config["volume_spike_threshold"],
                "ratio": volume_ratio,
                "threshold": self.config["volume_spike_threshold"]
            }
        
        return patterns
    
    def generate_signal(self, market_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Generate trading signal based on technical analysis.
        
        Args:
            market_data: Current market data
            
        Returns:
            Trading signal or None
        """
        # Check minimum time interval
        time_since_last = (datetime.now() - self.last_signal_time).total_seconds()
        if time_since_last < self.config["min_signal_interval"]:
            return None
            
        # Update data
        price = market_data.get("ltp", market_data.get("price", 0))
        volume = market_data.get("volume", 0)
        self.update_market_data(price, volume, datetime.now())
        
        if len(self.price_history) < 20:
            return None
            
        # Calculate indicators and patterns
        indicators = self.calculate_indicators()
        patterns = self.detect_patterns()
        
        # Signal generation logic
        signal = self._analyze_for_signals(indicators, patterns, market_data)
        
        if signal and signal["confidence"] >= self.config["min_confidence"]:
            signal["timestamp"] = datetime.now().isoformat()
            signal["symbol"] = self.symbol
            signal["indicators"] = indicators
            signal["patterns"] = patterns
            
            self.signal_history.append(signal)
            self.last_signal_time = datetime.now()
            
            self.logger.info(f"Generated {signal['action']} signal with confidence {signal['confidence']:.2f}")
            return signal
            
        return None
    
    def _analyze_for_signals(self, indicators: Dict[str, Any], patterns: Dict[str, Any], market_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Analyze indicators and patterns to generate signals.
        
        Args:
            indicators: Technical indicators
            patterns: Detected patterns
            market_data: Current market data
            
        Returns:
            Signal dictionary or None
        """
        signals = []
        current_price = self.price_history[-1]
        
        # RSI-based signals
        rsi = indicators.get("rsi", 50)
        if rsi > self.config["rsi_overbought"]:
            signals.append({
                "action": SignalType.SELL.value,
                "confidence": min((rsi - 70) / 30, 1.0),
                "reason": "RSI_OVERBOUGHT",
                "strength": SignalStrength.MODERATE.value
            })
        elif rsi < self.config["rsi_oversold"]:
            signals.append({
                "action": SignalType.BUY.value,
                "confidence": min((30 - rsi) / 30, 1.0),
                "reason": "RSI_OVERSOLD",
                "strength": SignalStrength.MODERATE.value
            })
        
        # MACD-based signals
        macd = indicators.get("macd", 0)
        macd_signal = indicators.get("macd_signal", 0)
        if macd > macd_signal and macd > self.config["macd_signal_threshold"]:
            signals.append({
                "action": SignalType.BUY.value,
                "confidence": min(abs(macd - macd_signal) * 100, 1.0),
                "reason": "MACD_BULLISH_CROSSOVER",
                "strength": SignalStrength.STRONG.value
            })
        elif macd < macd_signal and macd < -self.config["macd_signal_threshold"]:
            signals.append({
                "action": SignalType.SELL.value,
                "confidence": min(abs(macd - macd_signal) * 100, 1.0),
                "reason": "MACD_BEARISH_CROSSOVER",
                "strength": SignalStrength.STRONG.value
            })
        
        # Moving average signals
        sma_20 = indicators.get("sma_20", current_price)
        sma_50 = indicators.get("sma_50", current_price)
        if current_price > sma_20 > sma_50:
            signals.append({
                "action": SignalType.BUY.value,
                "confidence": min((current_price - sma_20) / sma_20 * 10, 0.8),
                "reason": "PRICE_ABOVE_MA",
                "strength": SignalStrength.WEAK.value
            })
        elif current_price < sma_20 < sma_50:
            signals.append({
                "action": SignalType.SELL.value,
                "confidence": min((sma_20 - current_price) / sma_20 * 10, 0.8),
                "reason": "PRICE_BELOW_MA",
                "strength": SignalStrength.WEAK.value
            })
        
        # Breakout signals
        breakout = patterns.get("breakout", {})
        if breakout.get("detected"):
            action = SignalType.BUY.value if breakout["type"] == "upward_breakout" else SignalType.SELL.value
            confidence = breakout["strength"]
            if breakout.get("volume_confirmation"):
                confidence *= 1.2  # Boost confidence with volume confirmation
                
            signals.append({
                "action": action,
                "confidence": min(confidence, 1.0),
                "reason": f"BREAKOUT_{breakout['type'].upper()}",
                "strength": SignalStrength.VERY_STRONG.value
            })
        
        # Trend reversal signals
        reversal = patterns.get("reversal", {})
        if reversal.get("detected"):
            action = SignalType.BUY.value if reversal["type"] == "bullish_reversal" else SignalType.SELL.value
            signals.append({
                "action": action,
                "confidence": reversal["confidence"],
                "reason": f"TREND_REVERSAL_{reversal['type'].upper()}",
                "strength": SignalStrength.STRONG.value
            })
        
        # Return strongest signal
        if signals:
            best_signal = max(signals, key=lambda s: s["confidence"])
            best_signal["all_signals"] = signals
            return best_signal
            
        return None
    
    def get_metrics(self) -> Dict[str, Any]:
        """
        Get signal processor metrics.
        
        Returns:
            Dictionary containing metrics
        """
        return {
            "symbol": self.symbol,
            "price_history_length": len(self.price_history),
            "volume_history_length": len(self.volume_history),
            "signals_generated": len(self.signal_history),
            "last_signal_time": self.last_signal_time.isoformat() if self.last_signal_time != datetime.min else None,
            "current_price": self.price_history[-1] if self.price_history else 0,
            "config": self.config
        }

