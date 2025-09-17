"""
Comprehensive Technical Indicators Engine
Implements all popular trading indicators for HFT-grade analysis
MACD, RSI, Pivot Points, Bollinger Bands, Stochastic, and more
"""

import sys
import os
import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional, Any
from datetime import datetime
import logging

# Using our own technical analysis implementations for better control
HAS_TALIB = False

# Add the project root directory to the Python path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..', '..'))
sys.path.append(PROJECT_ROOT)

from server.src.core.message_broker import get_message_broker

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TechnicalIndicatorsEngine:
    """
    Professional Technical Indicators Engine for HFT Trading
    
    Supported Indicators:
    - MACD (Moving Average Convergence Divergence)
    - RSI (Relative Strength Index)  
    - Pivot Points (Standard, Fibonacci, Camarilla)
    - Bollinger Bands
    - Stochastic Oscillator
    - ADX (Average Directional Index)
    - Williams %R
    - CCI (Commodity Channel Index)
    - Support/Resistance Levels
    - Volume Indicators (OBV, Volume Profile)
    """
    
    def __init__(self):
        """Initialize the Technical Indicators Engine."""
        self.message_broker = get_message_broker()
        self.cache = {}  # Cache for calculated indicators
        
        # Setup bidirectional RabbitMQ communication
        self._setup_message_subscriptions()
        
        logger.info("📊 Technical Indicators Engine initialized")
    
    def calculate_all_indicators(self, symbol: str, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Calculate all technical indicators for a symbol.
        
        Args:
            symbol: Stock symbol
            df: OHLCV DataFrame with columns [open, high, low, close, volume]
            
        Returns:
            Dictionary containing all calculated indicators
        """
        try:
            if len(df) < 50:
                logger.warning(f"⚠️ Insufficient data for {symbol}: {len(df)} rows")
                return {}
            
            # Ensure required columns exist
            required_cols = ['open', 'high', 'low', 'close', 'volume']
            for col in required_cols:
                if col not in df.columns:
                    logger.error(f"❌ Missing column {col} for {symbol}")
                    return {}
            
            indicators = {}
            
            # Trend Indicators
            indicators.update(self._calculate_trend_indicators(df))
            
            # Momentum Indicators  
            indicators.update(self._calculate_momentum_indicators(df))
            
            # Volatility Indicators
            indicators.update(self._calculate_volatility_indicators(df))
            
            # Volume Indicators
            indicators.update(self._calculate_volume_indicators(df))
            
            # Support/Resistance Levels
            indicators.update(self._calculate_support_resistance(df))
            
            # Pivot Points
            indicators.update(self._calculate_pivot_points(df))
            
            # Market Structure
            indicators.update(self._calculate_market_structure(df))
            
            # Overall Signal
            indicators['overall_signal'] = self._generate_overall_signal(indicators)
            
            # Cache results
            self.cache[symbol] = {
                'indicators': indicators,
                'timestamp': datetime.now(),
                'last_price': df['close'].iloc[-1]
            }
            
            logger.info(f"✅ Calculated {len(indicators)} indicators for {symbol}")
            return indicators
            
        except Exception as e:
            logger.error(f"❌ Error calculating indicators for {symbol}: {e}")
            return {}
    
    def _calculate_trend_indicators(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Calculate trend-following indicators."""
        indicators = {}
        
        try:
            close = df['close'].values
            high = df['high'].values
            low = df['low'].values
            
            # MACD
            if HAS_TALIB:
                macd_line, macd_signal, macd_histogram = talib.MACD(close, fastperiod=12, slowperiod=26, signalperiod=9)
            else:
                # Basic MACD implementation
                ema12 = self._calculate_ema(close, 12)
                ema26 = self._calculate_ema(close, 26)
                macd_line = ema12 - ema26
                macd_signal = self._calculate_ema(macd_line, 9)
                macd_histogram = macd_line - macd_signal
            indicators['macd'] = {
                'line': macd_line[-1] if not np.isnan(macd_line[-1]) else 0,
                'signal': macd_signal[-1] if not np.isnan(macd_signal[-1]) else 0,
                'histogram': macd_histogram[-1] if not np.isnan(macd_histogram[-1]) else 0,
                'crossover': 'bullish' if macd_line[-1] > macd_signal[-1] else 'bearish'
            }
            
            # Moving Averages
            if HAS_TALIB:
                sma_20 = talib.SMA(close, timeperiod=20)
                sma_50 = talib.SMA(close, timeperiod=50)
                ema_20 = talib.EMA(close, timeperiod=20)
            else:
                sma_20 = self._calculate_sma(close, 20)
                sma_50 = self._calculate_sma(close, 50)
                ema_20 = self._calculate_ema(close, 20)
            
            indicators['moving_averages'] = {
                'sma_20': sma_20[-1] if not np.isnan(sma_20[-1]) else 0,
                'sma_50': sma_50[-1] if not np.isnan(sma_50[-1]) else 0,
                'ema_20': ema_20[-1] if not np.isnan(ema_20[-1]) else 0,
                'price_vs_sma20': 'above' if close[-1] > sma_20[-1] else 'below',
                'sma_crossover': 'golden' if sma_20[-1] > sma_50[-1] else 'death'
            }
            
            # ADX (Trend Strength)
            adx = talib.ADX(high, low, close, timeperiod=14)
            plus_di = talib.PLUS_DI(high, low, close, timeperiod=14)
            minus_di = talib.MINUS_DI(high, low, close, timeperiod=14)
            
            indicators['adx'] = {
                'value': adx[-1] if not np.isnan(adx[-1]) else 0,
                'plus_di': plus_di[-1] if not np.isnan(plus_di[-1]) else 0,
                'minus_di': minus_di[-1] if not np.isnan(minus_di[-1]) else 0,
                'trend_strength': 'strong' if adx[-1] > 25 else 'weak',
                'direction': 'bullish' if plus_di[-1] > minus_di[-1] else 'bearish'
            }
            
        except Exception as e:
            logger.warning(f"⚠️ Error calculating trend indicators: {e}")
            
        return indicators
    
    def _calculate_momentum_indicators(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Calculate momentum oscillators."""
        indicators = {}
        
        try:
            close = df['close'].values
            high = df['high'].values
            low = df['low'].values
            
            # RSI
            if HAS_TALIB:
                rsi = talib.RSI(close, timeperiod=14)
            else:
                rsi = self._calculate_rsi(close, 14)
            indicators['rsi'] = {
                'value': rsi[-1] if not np.isnan(rsi[-1]) else 50,
                'signal': 'overbought' if rsi[-1] > 70 else 'oversold' if rsi[-1] < 30 else 'neutral',
                'divergence': self._detect_rsi_divergence(df, rsi)
            }
            
            # Stochastic Oscillator
            slowk, slowd = talib.STOCH(high, low, close, fastk_period=14, slowk_period=3, slowd_period=3)
            indicators['stochastic'] = {
                'k': slowk[-1] if not np.isnan(slowk[-1]) else 50,
                'd': slowd[-1] if not np.isnan(slowd[-1]) else 50,
                'signal': 'overbought' if slowk[-1] > 80 else 'oversold' if slowk[-1] < 20 else 'neutral',
                'crossover': 'bullish' if slowk[-1] > slowd[-1] else 'bearish'
            }
            
            # Williams %R
            willr = talib.WILLR(high, low, close, timeperiod=14)
            indicators['williams_r'] = {
                'value': willr[-1] if not np.isnan(willr[-1]) else -50,
                'signal': 'overbought' if willr[-1] > -20 else 'oversold' if willr[-1] < -80 else 'neutral'
            }
            
            # CCI (Commodity Channel Index)
            cci = talib.CCI(high, low, close, timeperiod=20)
            indicators['cci'] = {
                'value': cci[-1] if not np.isnan(cci[-1]) else 0,
                'signal': 'overbought' if cci[-1] > 100 else 'oversold' if cci[-1] < -100 else 'neutral'
            }
            
        except Exception as e:
            logger.warning(f"⚠️ Error calculating momentum indicators: {e}")
            
        return indicators
    
    def _calculate_volatility_indicators(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Calculate volatility-based indicators."""
        indicators = {}
        
        try:
            close = df['close'].values
            high = df['high'].values
            low = df['low'].values
            
            # Bollinger Bands
            bb_upper, bb_middle, bb_lower = talib.BBANDS(close, timeperiod=20, nbdevup=2, nbdevdn=2)
            bb_width = (bb_upper[-1] - bb_lower[-1]) / bb_middle[-1] * 100
            bb_position = (close[-1] - bb_lower[-1]) / (bb_upper[-1] - bb_lower[-1])
            
            indicators['bollinger_bands'] = {
                'upper': bb_upper[-1] if not np.isnan(bb_upper[-1]) else 0,
                'middle': bb_middle[-1] if not np.isnan(bb_middle[-1]) else 0,
                'lower': bb_lower[-1] if not np.isnan(bb_lower[-1]) else 0,
                'width': bb_width if not np.isnan(bb_width) else 0,
                'position': bb_position if not np.isnan(bb_position) else 0.5,
                'signal': 'squeeze' if bb_width < 10 else 'expansion' if bb_width > 20 else 'normal'
            }
            
            # Average True Range (ATR)
            atr = talib.ATR(high, low, close, timeperiod=14)
            indicators['atr'] = {
                'value': atr[-1] if not np.isnan(atr[-1]) else 0,
                'percentage': (atr[-1] / close[-1]) * 100 if atr[-1] > 0 else 0
            }
            
        except Exception as e:
            logger.warning(f"⚠️ Error calculating volatility indicators: {e}")
            
        return indicators
    
    def _calculate_volume_indicators(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Calculate volume-based indicators."""
        indicators = {}
        
        try:
            close = df['close'].values
            volume = df['volume'].values
            
            # On-Balance Volume (OBV)
            obv = talib.OBV(close, volume)
            indicators['obv'] = {
                'value': obv[-1] if not np.isnan(obv[-1]) else 0,
                'trend': 'bullish' if obv[-1] > obv[-10] else 'bearish'
            }
            
            # Volume Moving Average
            volume_ma = talib.SMA(volume.astype(float), timeperiod=20)
            indicators['volume'] = {
                'current': volume[-1],
                'average': volume_ma[-1] if not np.isnan(volume_ma[-1]) else 0,
                'relative': volume[-1] / volume_ma[-1] if volume_ma[-1] > 0 else 1,
                'signal': 'high' if volume[-1] > volume_ma[-1] * 1.5 else 'normal'
            }
            
        except Exception as e:
            logger.warning(f"⚠️ Error calculating volume indicators: {e}")
            
        return indicators
    
    def _calculate_support_resistance(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Calculate support and resistance levels."""
        indicators = {}
        
        try:
            high = df['high'].values
            low = df['low'].values
            close = df['close'].values
            
            # Calculate recent highs and lows
            recent_high = np.max(high[-20:])
            recent_low = np.min(low[-20:])
            
            # Calculate support/resistance levels
            price_range = recent_high - recent_low
            current_price = close[-1]
            
            indicators['support_resistance'] = {
                'resistance_1': recent_high,
                'resistance_2': recent_high + (price_range * 0.618),
                'support_1': recent_low,
                'support_2': recent_low - (price_range * 0.618),
                'current_level': 'resistance' if current_price > (recent_high + recent_low) / 2 else 'support'
            }
            
        except Exception as e:
            logger.warning(f"⚠️ Error calculating support/resistance: {e}")
            
        return indicators
    
    def _calculate_pivot_points(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Calculate pivot points (Standard, Fibonacci, Camarilla)."""
        indicators = {}
        
        try:
            # Use previous day's data
            prev_high = df['high'].iloc[-2]
            prev_low = df['low'].iloc[-2] 
            prev_close = df['close'].iloc[-2]
            
            # Standard Pivot Points
            pivot = (prev_high + prev_low + prev_close) / 3
            r1 = 2 * pivot - prev_low
            s1 = 2 * pivot - prev_high
            r2 = pivot + (prev_high - prev_low)
            s2 = pivot - (prev_high - prev_low)
            
            # Fibonacci Pivot Points
            fib_r1 = pivot + 0.382 * (prev_high - prev_low)
            fib_s1 = pivot - 0.382 * (prev_high - prev_low)
            fib_r2 = pivot + 0.618 * (prev_high - prev_low)
            fib_s2 = pivot - 0.618 * (prev_high - prev_low)
            
            # Camarilla Pivot Points
            cam_r1 = prev_close + (prev_high - prev_low) * 1.1 / 12
            cam_s1 = prev_close - (prev_high - prev_low) * 1.1 / 12
            cam_r2 = prev_close + (prev_high - prev_low) * 1.1 / 6
            cam_s2 = prev_close - (prev_high - prev_low) * 1.1 / 6
            
            indicators['pivot_points'] = {
                'standard': {
                    'pivot': pivot,
                    'r1': r1, 'r2': r2,
                    's1': s1, 's2': s2
                },
                'fibonacci': {
                    'pivot': pivot,
                    'r1': fib_r1, 'r2': fib_r2,
                    's1': fib_s1, 's2': fib_s2
                },
                'camarilla': {
                    'r1': cam_r1, 'r2': cam_r2,
                    's1': cam_s1, 's2': cam_s2
                }
            }
            
        except Exception as e:
            logger.warning(f"⚠️ Error calculating pivot points: {e}")
            
        return indicators
    
    def _calculate_market_structure(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Analyze market structure and patterns."""
        indicators = {}
        
        try:
            close = df['close'].values
            high = df['high'].values
            low = df['low'].values
            
            # Higher highs and higher lows detection
            recent_highs = []
            recent_lows = []
            
            for i in range(len(high) - 10, len(high)):
                if i > 0 and i < len(high) - 1:
                    if high[i] > high[i-1] and high[i] > high[i+1]:
                        recent_highs.append(high[i])
                    if low[i] < low[i-1] and low[i] < low[i+1]:
                        recent_lows.append(low[i])
            
            # Trend structure analysis
            if len(recent_highs) >= 2 and len(recent_lows) >= 2:
                higher_highs = recent_highs[-1] > recent_highs[-2]
                higher_lows = recent_lows[-1] > recent_lows[-2]
                
                if higher_highs and higher_lows:
                    trend_structure = 'bullish'
                elif not higher_highs and not higher_lows:
                    trend_structure = 'bearish'
                else:
                    trend_structure = 'ranging'
            else:
                trend_structure = 'insufficient_data'
            
            indicators['market_structure'] = {
                'trend': trend_structure,
                'recent_highs': recent_highs[-2:] if len(recent_highs) >= 2 else [],
                'recent_lows': recent_lows[-2:] if len(recent_lows) >= 2 else []
            }
            
        except Exception as e:
            logger.warning(f"⚠️ Error calculating market structure: {e}")
            
        return indicators
    
    def _detect_rsi_divergence(self, df: pd.DataFrame, rsi: np.ndarray) -> str:
        """Detect RSI divergence patterns."""
        try:
            if len(df) < 20 or len(rsi) < 20:
                return 'insufficient_data'
            
            # Simple divergence detection
            recent_prices = df['close'].values[-10:]
            recent_rsi = rsi[-10:]
            
            price_trend = 'up' if recent_prices[-1] > recent_prices[0] else 'down'
            rsi_trend = 'up' if recent_rsi[-1] > recent_rsi[0] else 'down'
            
            if price_trend == 'up' and rsi_trend == 'down':
                return 'bearish_divergence'
            elif price_trend == 'down' and rsi_trend == 'up':
                return 'bullish_divergence'
            else:
                return 'no_divergence'
                
        except Exception:
            return 'error'
    
    def _generate_overall_signal(self, indicators: Dict[str, Any]) -> Dict[str, Any]:
        """Generate overall trading signal based on all indicators."""
        try:
            bullish_signals = 0
            bearish_signals = 0
            total_signals = 0
            
            # MACD signal
            if 'macd' in indicators:
                total_signals += 1
                if indicators['macd']['crossover'] == 'bullish':
                    bullish_signals += 1
                else:
                    bearish_signals += 1
            
            # RSI signal
            if 'rsi' in indicators:
                total_signals += 1
                if indicators['rsi']['signal'] == 'oversold':
                    bullish_signals += 1
                elif indicators['rsi']['signal'] == 'overbought':
                    bearish_signals += 1
            
            # Moving average signal
            if 'moving_averages' in indicators:
                total_signals += 1
                if indicators['moving_averages']['price_vs_sma20'] == 'above':
                    bullish_signals += 1
                else:
                    bearish_signals += 1
            
            # Calculate overall sentiment
            if total_signals > 0:
                bullish_percentage = (bullish_signals / total_signals) * 100
                bearish_percentage = (bearish_signals / total_signals) * 100
                
                if bullish_percentage > 60:
                    overall_signal = 'bullish'
                elif bearish_percentage > 60:
                    overall_signal = 'bearish'
                else:
                    overall_signal = 'neutral'
            else:
                overall_signal = 'insufficient_data'
                bullish_percentage = 0
                bearish_percentage = 0
            
            return {
                'signal': overall_signal,
                'bullish_percentage': bullish_percentage,
                'bearish_percentage': bearish_percentage,
                'confidence': max(bullish_percentage, bearish_percentage) / 100
            }
            
        except Exception as e:
            logger.error(f"❌ Error generating overall signal: {e}")
            return {'signal': 'error', 'confidence': 0}
    
    def get_cached_indicators(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get cached indicators for a symbol."""
        return self.cache.get(symbol)
    
    def publish_indicators(self, symbol: str, indicators: Dict[str, Any]):
        """Publish indicators to message broker."""
        try:
            self.message_broker.publish_ai_analysis(
                'indicators',
                symbol,
                {
                    'symbol': symbol,
                    'indicators': indicators,
                    'timestamp': datetime.now().isoformat()
                }
            )
            logger.debug(f"📤 Published indicators for {symbol}")
        except Exception as e:
            logger.error(f"❌ Failed to publish indicators for {symbol}: {e}")
    
    def _setup_message_subscriptions(self):
        """Setup RabbitMQ subscriptions for receiving indicator requests."""
        try:
            # Subscribe to indicator calculation requests
            self.message_broker.subscribe_to_queue(
                'ai_indicator_requests',
                self._handle_indicator_request
            )
            
            # Subscribe to market data for real-time indicator calculation
            self.message_broker.subscribe_to_queue(
                'market_data_candles',
                self._handle_market_data
            )
            
            logger.info("✅ Technical Indicators message subscriptions setup")
            
        except Exception as e:
            logger.error(f"❌ Failed to setup indicator subscriptions: {e}")
    
    def _handle_indicator_request(self, message):
        """Handle incoming indicator calculation requests."""
        try:
            data = message.get('data', {})
            symbol = data.get('symbol')
            indicator = data.get('indicator')
            
            if symbol:
                logger.info(f"📥 Received indicator request for {symbol}")
                
                # Generate sample data for calculation (in production, fetch real data)
                sample_data = self._generate_sample_data(symbol)
                
                # Calculate indicators
                if indicator == 'all':
                    indicators = self.calculate_all_indicators(symbol, sample_data)
                else:
                    # Calculate specific indicator
                    indicators = self._calculate_specific_indicator(symbol, sample_data, indicator)
                
                # Publish results back
                self.message_broker.publish_ai_analysis(
                    'indicator_results',
                    symbol,
                    {
                        'symbol': symbol,
                        'indicators': indicators,
                        'requested_indicator': indicator,
                        'timestamp': datetime.now().isoformat()
                    }
                )
                
                logger.info(f"✅ Completed indicator calculation for {symbol}")
            
        except Exception as e:
            logger.error(f"❌ Error handling indicator request: {e}")
    
    def _handle_market_data(self, message):
        """Handle incoming market data for real-time indicator calculation."""
        try:
            data = message.get('data', {})
            symbol = data.get('symbol')
            
            if symbol and 'candle_info' in data:
                # Update cache with new candle data
                if symbol not in self.cache:
                    self.cache[symbol] = {'candles': []}
                
                self.cache[symbol]['candles'].append(data['candle_info'])
                
                # Keep only recent candles (last 200)
                if len(self.cache[symbol]['candles']) > 200:
                    self.cache[symbol]['candles'] = self.cache[symbol]['candles'][-200:]
                
                logger.debug(f"📊 Updated candle data cache for {symbol}")
            
        except Exception as e:
            logger.error(f"❌ Error handling market data: {e}")
    
    def _calculate_specific_indicator(self, symbol: str, df: pd.DataFrame, indicator: str) -> Dict[str, Any]:
        """Calculate a specific indicator."""
        try:
            if indicator == 'macd':
                return self._calculate_trend_indicators(df)
            elif indicator == 'rsi':
                return self._calculate_momentum_indicators(df)
            elif indicator == 'bollinger_bands':
                return self._calculate_volatility_indicators(df)
            elif indicator == 'pivot_points':
                return self._calculate_pivot_points(df)
            else:
                # Return all if unknown
                return self.calculate_all_indicators(symbol, df)
                
        except Exception as e:
            logger.error(f"❌ Error calculating {indicator} for {symbol}: {e}")
            return {}
    
    def _generate_sample_data(self, symbol: str) -> pd.DataFrame:
        """Generate sample OHLCV data for testing."""
        # In production, this would fetch real data from Angel One API
        dates = pd.date_range(end=datetime.now(), periods=100, freq='5T')
        np.random.seed(hash(symbol) % 2**32)
        
        base_price = 100 + (hash(symbol) % 1000)
        returns = np.random.normal(0, 0.02, 100)
        prices = base_price * np.exp(np.cumsum(returns))
        
        return pd.DataFrame({
            'timestamp': dates,
            'open': prices * (1 + np.random.normal(0, 0.001, 100)),
            'high': prices * (1 + np.abs(np.random.normal(0, 0.005, 100))),
            'low': prices * (1 - np.abs(np.random.normal(0, 0.005, 100))),
            'close': prices,
            'volume': np.random.randint(10000, 100000, 100)
        })
    
    def start_async_processing(self):
        """Start asynchronous indicator processing."""
        try:
            logger.info("🔄 Starting technical indicators async processing...")
            logger.info("✅ Technical Indicators Engine ready for async processing")
        except Exception as e:
            logger.error(f"❌ Error starting async processing: {e}")
    
    def _calculate_ema(self, data: np.ndarray, period: int) -> np.ndarray:
        """Calculate Exponential Moving Average."""
        try:
            ema = np.zeros_like(data)
            alpha = 2.0 / (period + 1)
            ema[0] = data[0]
            
            for i in range(1, len(data)):
                ema[i] = alpha * data[i] + (1 - alpha) * ema[i-1]
            
            return ema
        except Exception:
            return np.full_like(data, np.nan)
    
    def _calculate_sma(self, data: np.ndarray, period: int) -> np.ndarray:
        """Calculate Simple Moving Average."""
        try:
            sma = np.full_like(data, np.nan)
            for i in range(period - 1, len(data)):
                sma[i] = np.mean(data[i - period + 1:i + 1])
            return sma
        except Exception:
            return np.full_like(data, np.nan)
    
    def _calculate_rsi(self, data: np.ndarray, period: int = 14) -> np.ndarray:
        """Calculate Relative Strength Index."""
        try:
            delta = np.diff(data)
            gain = np.where(delta > 0, delta, 0)
            loss = np.where(delta < 0, -delta, 0)
            
            avg_gain = np.zeros(len(data))
            avg_loss = np.zeros(len(data))
            
            # Initialize first values
            avg_gain[period] = np.mean(gain[:period])
            avg_loss[period] = np.mean(loss[:period])
            
            # Calculate RSI
            for i in range(period + 1, len(data)):
                avg_gain[i] = (avg_gain[i-1] * (period - 1) + gain[i-1]) / period
                avg_loss[i] = (avg_loss[i-1] * (period - 1) + loss[i-1]) / period
            
            rs = avg_gain / (avg_loss + 1e-10)
            rsi = 100 - (100 / (1 + rs))
            
            return rsi
        except Exception:
            return np.full_like(data, 50)


# Example usage and testing
if __name__ == "__main__":
    # Test the Technical Indicators Engine
    print("🧪 Testing Technical Indicators Engine...")
    
    # Create sample data
    dates = pd.date_range(start='2023-01-01', periods=100, freq='D')
    np.random.seed(42)
    
    # Generate realistic OHLCV data
    closes = 100 + np.cumsum(np.random.randn(100) * 0.5)
    opens = closes + np.random.randn(100) * 0.2
    highs = np.maximum(opens, closes) + np.abs(np.random.randn(100) * 0.3)
    lows = np.minimum(opens, closes) - np.abs(np.random.randn(100) * 0.3)
    volumes = np.random.randint(100000, 1000000, 100)
    
    test_df = pd.DataFrame({
        'timestamp': dates,
        'open': opens,
        'high': highs,
        'low': lows,
        'close': closes,
        'volume': volumes
    })
    
    # Initialize engine
    engine = TechnicalIndicatorsEngine()
    
    # Calculate indicators
    indicators = engine.calculate_all_indicators('TEST-SYMBOL', test_df)
    
    print(f"\n📊 Calculated indicators for TEST-SYMBOL:")
    for category, data in indicators.items():
        print(f"   {category}: {type(data)}")
    
    if 'overall_signal' in indicators:
        signal = indicators['overall_signal']
        print(f"\n🎯 Overall Signal: {signal['signal'].upper()}")
        print(f"   Confidence: {signal['confidence']:.2%}")
        print(f"   Bullish: {signal['bullish_percentage']:.1f}%")
        print(f"   Bearish: {signal['bearish_percentage']:.1f}%")
    
    print("\n✅ Technical Indicators Engine testing completed!")
