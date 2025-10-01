"""
Live Momentum Strategy
=====================

Enhanced momentum strategy for real-time market data processing.
Optimized for low-latency signal generation and risk integration.
"""

import asyncio
import json
from typing import Dict, Any, List, Optional
from datetime import datetime, UTC
from collections import deque
import logging

# Add project root to path for imports
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent.parent))

from strategy_engine.base_strategy_engine import BaseStrategyEngine

logger = logging.getLogger("live_momentum_strategy")


class LiveMomentumStrategy(BaseStrategyEngine):
    """
    Live momentum strategy optimized for real-time processing.
    
    Features:
    - Real-time tick processing
    - Moving average crossover signals
    - Volume confirmation
    - Risk-adjusted position sizing
    - Sub-millisecond signal generation
    """
    
    def __init__(self, strategy_id: str, symbol: str, short_period: int = 10, long_period: int = 30):
        """Initialize live momentum strategy."""
        super().__init__(strategy_id, symbol)
        
        # Strategy parameters
        self.short_period = short_period
        self.long_period = long_period
        self.min_volume_ratio = 1.2  # Minimum volume spike for signal confirmation
        self.momentum_threshold = 0.001  # 0.1% minimum price movement
        
        # Data storage (using deque for efficient operations)
        self.price_history = deque(maxlen=max(short_period, long_period) + 10)
        self.volume_history = deque(maxlen=20)
        self.timestamp_history = deque(maxlen=max(short_period, long_period) + 10)
        
        # Strategy state
        self.current_position = None  # "LONG", "SHORT", or None
        self.last_signal_time = None
        self.signal_cooldown = 5.0  # seconds between signals
        
        # Performance tracking
        self.signals_generated = 0
        self.orders_placed = 0
        self.processing_times = deque(maxlen=100)
        
        logger.info(f"LiveMomentumStrategy initialized: {strategy_id} for {symbol}")
    
    async def process_market_data(self, market_data: Dict[str, Any]):
        """
        Process real-time market data and generate trading signals.
        
        Args:
            market_data: Real-time tick data
        """
        try:
            processing_start = datetime.now()
            
            # Extract data
            price = float(market_data.get("ltp", market_data.get("price", 0)))
            volume = int(market_data.get("volume", 0))
            timestamp = market_data.get("timestamp", datetime.now(UTC).isoformat())
            
            if price <= 0:
                logger.warning(f"Invalid price data: {price}")
                return
            
            # Update history
            self.price_history.append(price)
            self.volume_history.append(volume)
            self.timestamp_history.append(timestamp)
            
            # Need minimum data points
            if len(self.price_history) < self.long_period:
                logger.debug(f"Insufficient data: {len(self.price_history)}/{self.long_period}")
                return
            
            # Calculate indicators
            short_ma = self._calculate_sma(self.short_period)
            long_ma = self._calculate_sma(self.long_period)
            volume_ratio = self._calculate_volume_ratio()
            price_momentum = self._calculate_momentum()
            
            # Generate signal
            signal = self._generate_signal(
                price, short_ma, long_ma, volume_ratio, price_momentum
            )
            
            if signal:
                await self._execute_signal(signal, market_data)
            
            # Track processing time
            processing_time = (datetime.now() - processing_start).total_seconds() * 1000
            self.processing_times.append(processing_time)
            
            # Log performance warning if slow
            if processing_time > 10:  # 10ms threshold
                logger.warning(f"Slow processing: {processing_time:.2f}ms")
            
        except Exception as e:
            logger.error(f"Error processing market data: {e}")
    
    def _calculate_sma(self, period: int) -> float:
        """Calculate Simple Moving Average."""
        if len(self.price_history) < period:
            return 0.0
        
        recent_prices = list(self.price_history)[-period:]
        return sum(recent_prices) / len(recent_prices)
    
    def _calculate_volume_ratio(self) -> float:
        """Calculate current volume vs average volume."""
        if len(self.volume_history) < 5:
            return 1.0
        
        current_volume = self.volume_history[-1]
        avg_volume = sum(list(self.volume_history)[-10:]) / min(len(self.volume_history), 10)
        
        return current_volume / avg_volume if avg_volume > 0 else 1.0
    
    def _calculate_momentum(self) -> float:
        """Calculate price momentum (rate of change)."""
        if len(self.price_history) < 5:
            return 0.0
        
        current_price = self.price_history[-1]
        old_price = self.price_history[-5]
        
        return (current_price - old_price) / old_price if old_price > 0 else 0.0
    
    def _generate_signal(self, price: float, short_ma: float, long_ma: float, 
                        volume_ratio: float, momentum: float) -> Optional[Dict[str, Any]]:
        """
        Generate trading signal based on indicators.
        
        Returns:
            Signal dictionary or None
        """
        try:
            # Check signal cooldown
            if self.last_signal_time:
                time_since_last = (datetime.now() - self.last_signal_time).total_seconds()
                if time_since_last < self.signal_cooldown:
                    return None
            
            signal = None
            
            # Bullish signal: Short MA crosses above Long MA with volume confirmation
            if (short_ma > long_ma and 
                momentum > self.momentum_threshold and 
                volume_ratio >= self.min_volume_ratio and
                self.current_position != "LONG"):
                
                signal = {
                    "type": "BUY",
                    "strategy_id": self.strategy_id,
                    "symbol": self.symbol,
                    "price": price,
                    "quantity": self._calculate_position_size("BUY", momentum, volume_ratio),
                    "confidence": min(0.9, 0.5 + (momentum * 10) + (volume_ratio * 0.1)),
                    "indicators": {
                        "short_ma": short_ma,
                        "long_ma": long_ma,
                        "momentum": momentum,
                        "volume_ratio": volume_ratio
                    },
                    "timestamp": datetime.now(UTC).isoformat()
                }
                
                self.current_position = "LONG"
            
            # Bearish signal: Short MA crosses below Long MA with volume confirmation
            elif (short_ma < long_ma and 
                  momentum < -self.momentum_threshold and 
                  volume_ratio >= self.min_volume_ratio and
                  self.current_position != "SHORT"):
                
                signal = {
                    "type": "SELL",
                    "strategy_id": self.strategy_id,
                    "symbol": self.symbol,
                    "price": price,
                    "quantity": self._calculate_position_size("SELL", abs(momentum), volume_ratio),
                    "confidence": min(0.9, 0.5 + (abs(momentum) * 10) + (volume_ratio * 0.1)),
                    "indicators": {
                        "short_ma": short_ma,
                        "long_ma": long_ma,
                        "momentum": momentum,
                        "volume_ratio": volume_ratio
                    },
                    "timestamp": datetime.now(UTC).isoformat()
                }
                
                self.current_position = "SHORT"
            
            # Exit signal: Momentum reversal
            elif (self.current_position == "LONG" and momentum < -self.momentum_threshold/2) or \
                 (self.current_position == "SHORT" and momentum > self.momentum_threshold/2):
                
                signal = {
                    "type": "EXIT",
                    "strategy_id": self.strategy_id,
                    "symbol": self.symbol,
                    "price": price,
                    "quantity": 0,  # Exit all positions
                    "confidence": 0.8,
                    "reason": "momentum_reversal",
                    "timestamp": datetime.now(UTC).isoformat()
                }
                
                self.current_position = None
            
            if signal:
                self.signals_generated += 1
                self.last_signal_time = datetime.now()
                logger.info(f"Generated {signal['type']} signal for {self.symbol} at {price:.2f}")
            
            return signal
            
        except Exception as e:
            logger.error(f"Error generating signal: {e}")
            return None
    
    def _calculate_position_size(self, signal_type: str, momentum: float, volume_ratio: float) -> int:
        """Calculate position size based on signal strength."""
        base_size = 100  # Base position size
        
        # Adjust based on momentum strength
        momentum_multiplier = min(2.0, 1.0 + (abs(momentum) * 100))
        
        # Adjust based on volume confirmation
        volume_multiplier = min(1.5, volume_ratio / 2)
        
        # Calculate final size
        position_size = int(base_size * momentum_multiplier * volume_multiplier)
        
        # Apply limits
        max_size = 1000  # Maximum position size
        return min(position_size, max_size)
    
    async def _execute_signal(self, signal: Dict[str, Any], market_data: Dict[str, Any]):
        """
        Execute trading signal through risk management and order placement.
        
        Args:
            signal: Generated trading signal
            market_data: Current market data
        """
        try:
            # Risk validation
            if self.risk_manager:
                risk_result = await self.risk_manager.validate_order(signal)
                
                if not risk_result.get("success", False):
                    logger.warning(f"Signal rejected by risk manager: {risk_result.get('error', 'Unknown')}")
                    return
                
                logger.info("Signal passed risk validation")
            
            # Place order through order publisher
            if self.order_publisher:
                order_data = {
                    "strategy_id": signal["strategy_id"],
                    "symbol": signal["symbol"],
                    "transaction_type": signal["type"],
                    "quantity": signal["quantity"],
                    "price": signal["price"],
                    "order_type": "MARKET",
                    "product_type": "INTRADAY",
                    "confidence": signal["confidence"],
                    "timestamp": signal["timestamp"]
                }
                
                # Send to Kafka for order execution
                success = self.order_publisher.send_order(**order_data)
                
                if success:
                    self.orders_placed += 1
                    logger.info(f"Order placed successfully: {signal['type']} {signal['quantity']} {signal['symbol']}")
                else:
                    logger.error("Failed to place order")
            else:
                logger.warning("No order publisher configured")
                
        except Exception as e:
            logger.error(f"Error executing signal: {e}")
    
    def generate_backtest_signals(self, historical_data) -> Any:
        """Generate signals for backtesting (not implemented for live strategy)."""
        logger.warning("Backtesting not implemented for LiveMomentumStrategy")
        return None
    
    def get_strategy_status(self) -> Dict[str, Any]:
        """Get current strategy status and metrics."""
        avg_processing_time = sum(self.processing_times) / len(self.processing_times) if self.processing_times else 0
        
        return {
            "strategy_id": self.strategy_id,
            "symbol": self.symbol,
            "is_active": self.is_active,
            "current_position": self.current_position,
            "signals_generated": self.signals_generated,
            "orders_placed": self.orders_placed,
            "data_points": len(self.price_history),
            "avg_processing_time_ms": round(avg_processing_time, 2),
            "last_signal_time": self.last_signal_time.isoformat() if self.last_signal_time else None,
            "parameters": {
                "short_period": self.short_period,
                "long_period": self.long_period,
                "momentum_threshold": self.momentum_threshold,
                "min_volume_ratio": self.min_volume_ratio
            },
            "current_indicators": {
                "short_ma": self._calculate_sma(self.short_period) if len(self.price_history) >= self.short_period else 0,
                "long_ma": self._calculate_sma(self.long_period) if len(self.price_history) >= self.long_period else 0,
                "momentum": self._calculate_momentum(),
                "volume_ratio": self._calculate_volume_ratio()
            }
        }

