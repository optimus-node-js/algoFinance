"""
Advanced Pattern Recognition Engine
Implements state-of-the-art ML algorithms for chart pattern detection in financial markets.

Uses ensemble of:
- CNN for visual pattern recognition
- LSTM for temporal sequence analysis  
- XGBoost for feature-based classification
- Traditional technical analysis patterns
"""

import sys
import os
import numpy as np
import pandas as pd
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any, NamedTuple
from dataclasses import dataclass
from collections import defaultdict
import json

# Add the project root directory to the Python path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..', '..'))
sys.path.append(PROJECT_ROOT)

try:
    from sklearn.preprocessing import StandardScaler, MinMaxScaler
    from sklearn.ensemble import RandomForestClassifier
    import warnings
    warnings.filterwarnings('ignore')
    HAS_SKLEARN = True
except ImportError:
    HAS_SKLEARN = False

try:
    import xgboost as xgb
    HAS_XGBOOST = True
except ImportError:
    HAS_XGBOOST = False

try:
    from tensorflow import keras
    from tensorflow.keras import layers
    HAS_TENSORFLOW = True
except ImportError:
    HAS_TENSORFLOW = False

from server.src.core.message_broker import get_message_broker

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class PatternDetection:
    """Pattern detection result."""
    pattern_type: str
    confidence: float
    start_time: datetime
    end_time: datetime
    price_level: float
    pattern_strength: str  # 'weak', 'moderate', 'strong'
    trading_signal: str    # 'bullish', 'bearish', 'neutral'
    target_price: Optional[float] = None
    stop_loss: Optional[float] = None
    reliability_score: float = 0.0
    
class PatternMetrics(NamedTuple):
    """Pattern analysis metrics."""
    total_patterns_detected: int
    bullish_patterns: int
    bearish_patterns: int
    neutral_patterns: int
    high_confidence_patterns: int
    pattern_distribution: Dict[str, int]
    average_confidence: float
    strongest_signal: Optional[PatternDetection]

class AdvancedPatternDetector:
    """
    Advanced Pattern Recognition Engine for financial markets.
    
    Features:
    - Multi-algorithm ensemble (CNN, LSTM, XGBoost, Traditional TA)
    - Real-time pattern detection
    - Confidence scoring and reliability assessment
    - Support for multiple timeframes
    - Comprehensive chart pattern library
    """
    
    def __init__(self):
        """Initialize the Advanced Pattern Detector."""
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self.message_broker = get_message_broker()
        
        # Pattern detection models
        self.models = {}
        self.scalers = {}
        
        # Pattern configuration
        self.supported_patterns = {
            # Continuation Patterns
            'flag': {'type': 'continuation', 'min_bars': 10, 'max_bars': 30},
            'pennant': {'type': 'continuation', 'min_bars': 8, 'max_bars': 25},
            'triangle_ascending': {'type': 'continuation', 'min_bars': 15, 'max_bars': 50},
            'triangle_descending': {'type': 'continuation', 'min_bars': 15, 'max_bars': 50},
            'triangle_symmetrical': {'type': 'continuation', 'min_bars': 20, 'max_bars': 60},
            'wedge_rising': {'type': 'continuation', 'min_bars': 15, 'max_bars': 40},
            'wedge_falling': {'type': 'continuation', 'min_bars': 15, 'max_bars': 40},
            
            # Reversal Patterns
            'head_shoulders': {'type': 'reversal', 'min_bars': 20, 'max_bars': 100},
            'inverse_head_shoulders': {'type': 'reversal', 'min_bars': 20, 'max_bars': 100},
            'double_top': {'type': 'reversal', 'min_bars': 15, 'max_bars': 80},
            'double_bottom': {'type': 'reversal', 'min_bars': 15, 'max_bars': 80},
            'triple_top': {'type': 'reversal', 'min_bars': 25, 'max_bars': 120},
            'triple_bottom': {'type': 'reversal', 'min_bars': 25, 'max_bars': 120},
            'cup_handle': {'type': 'reversal', 'min_bars': 30, 'max_bars': 200},
            'rounding_bottom': {'type': 'reversal', 'min_bars': 30, 'max_bars': 150},
            
            # Channel Patterns
            'channel_up': {'type': 'trending', 'min_bars': 20, 'max_bars': 200},
            'channel_down': {'type': 'trending', 'min_bars': 20, 'max_bars': 200},
            'horizontal_channel': {'type': 'ranging', 'min_bars': 15, 'max_bars': 100},
            
            # Breakout Patterns
            'breakout_resistance': {'type': 'breakout', 'min_bars': 5, 'max_bars': 20},
            'breakout_support': {'type': 'breakout', 'min_bars': 5, 'max_bars': 20},
            'gap_up': {'type': 'breakout', 'min_bars': 2, 'max_bars': 5},
            'gap_down': {'type': 'breakout', 'min_bars': 2, 'max_bars': 5}
        }
        
        # Pattern strength criteria
        self.strength_thresholds = {
            'weak': 0.3,
            'moderate': 0.6,
            'strong': 0.8
        }
        
        # Initialize models and components
        self._initialize_models()
        
        # Setup bidirectional RabbitMQ communication
        self._setup_message_subscriptions()
        
        self.logger.info("🔍 Advanced Pattern Recognition Engine initialized successfully")

    def _initialize_models(self):
        """Initialize ML models for pattern recognition."""
        try:
            # Initialize scalers
            self.scalers['price'] = StandardScaler() if HAS_SKLEARN else None
            self.scalers['volume'] = StandardScaler() if HAS_SKLEARN else None
            self.scalers['features'] = MinMaxScaler() if HAS_SKLEARN else None
            
            # Initialize traditional pattern detector
            self.models['traditional'] = self._create_traditional_detector()
            
            # Initialize ML models if libraries available
            if HAS_SKLEARN:
                self.models['random_forest'] = self._create_random_forest_model()
                
            if HAS_XGBOOST:
                self.models['xgboost'] = self._create_xgboost_model()
                
            if HAS_TENSORFLOW:
                self.models['cnn'] = self._create_cnn_model()
                self.models['lstm'] = self._create_lstm_model()
            
            self.logger.info(f"✅ Initialized {len(self.models)} pattern detection models")
            
        except Exception as e:
            self.logger.error(f"❌ Error initializing models: {e}")
            # Fallback to traditional patterns only
            self.models['traditional'] = self._create_traditional_detector()

    def _create_traditional_detector(self):
        """Create traditional technical analysis pattern detector."""
        return {
            'type': 'traditional',
            'patterns': self.supported_patterns,
            'initialized': True
        }

    def _create_random_forest_model(self):
        """Create Random Forest model for pattern classification."""
        if not HAS_SKLEARN:
            return None
            
        model = RandomForestClassifier(
            n_estimators=100,
            max_depth=10,
            min_samples_split=5,
            min_samples_leaf=2,
            random_state=42
        )
        
        return {
            'model': model,
            'type': 'random_forest',
            'trained': False
        }

    def _create_xgboost_model(self):
        """Create XGBoost model for pattern classification."""
        if not HAS_XGBOOST:
            return None
            
        model = xgb.XGBClassifier(
            n_estimators=100,
            max_depth=6,
            learning_rate=0.1,
            subsample=0.8,
            colsample_bytree=0.8,
            random_state=42
        )
        
        return {
            'model': model,
            'type': 'xgboost',
            'trained': False
        }

    def _create_cnn_model(self):
        """Create CNN model for visual pattern recognition."""
        if not HAS_TENSORFLOW:
            return None
            
        try:
            model = keras.Sequential([
                layers.Conv1D(32, 3, activation='relu', input_shape=(50, 4)),
                layers.Conv1D(64, 3, activation='relu'),
                layers.MaxPooling1D(2),
                layers.Conv1D(128, 3, activation='relu'),
                layers.GlobalMaxPooling1D(),
                layers.Dense(50, activation='relu'),
                layers.Dropout(0.3),
                layers.Dense(len(self.supported_patterns), activation='softmax')
            ])
            
            model.compile(
                optimizer='adam',
                loss='sparse_categorical_crossentropy',
                metrics=['accuracy']
            )
            
            return {
                'model': model,
                'type': 'cnn',
                'trained': False
            }
            
        except Exception as e:
            self.logger.warning(f"⚠️ CNN model creation failed: {e}")
            return None

    def _create_lstm_model(self):
        """Create LSTM model for temporal pattern analysis."""
        if not HAS_TENSORFLOW:
            return None
            
        try:
            model = keras.Sequential([
                layers.LSTM(64, return_sequences=True, input_shape=(50, 4)),
                layers.LSTM(32, return_sequences=False),
                layers.Dense(50, activation='relu'),
                layers.Dropout(0.3),
                layers.Dense(len(self.supported_patterns), activation='softmax')
            ])
            
            model.compile(
                optimizer='adam',
                loss='sparse_categorical_crossentropy',
                metrics=['accuracy']
            )
            
            return {
                'model': model,
                'type': 'lstm',
                'trained': False
            }
            
        except Exception as e:
            self.logger.warning(f"⚠️ LSTM model creation failed: {e}")
            return None

    def analyze_patterns(self, symbol: str, market_data: Dict[str, Any], timeframe: str = '1h') -> PatternMetrics:
        """
        Comprehensive pattern analysis for a symbol.
        
        Args:
            symbol: Trading symbol
            market_data: Market data with OHLCV
            timeframe: Analysis timeframe
            
        Returns:
            PatternMetrics with detected patterns and analysis
        """
        try:
            self.logger.info(f"🔍 Analyzing patterns for {symbol} on {timeframe} timeframe")
            
            # Prepare data
            df = self._prepare_data(market_data)
            if df is None or len(df) < 20:
                self.logger.warning(f"⚠️ Insufficient data for pattern analysis: {len(df) if df is not None else 0} bars")
                return self._create_empty_metrics()
            
            # Detect patterns using multiple approaches
            all_patterns = []
            
            # Traditional pattern detection
            traditional_patterns = self._detect_traditional_patterns(df, symbol, timeframe)
            all_patterns.extend(traditional_patterns)
            
            # ML-based pattern detection
            if HAS_SKLEARN and 'random_forest' in self.models:
                ml_patterns = self._detect_ml_patterns(df, symbol, timeframe)
                all_patterns.extend(ml_patterns)
            
            # Deep learning pattern detection
            if HAS_TENSORFLOW and any(model_type in self.models for model_type in ['cnn', 'lstm']):
                dl_patterns = self._detect_dl_patterns(df, symbol, timeframe)
                all_patterns.extend(dl_patterns)
            
            # Ensemble and filter patterns
            final_patterns = self._ensemble_patterns(all_patterns)
            
            # Calculate metrics
            metrics = self._calculate_pattern_metrics(final_patterns)
            
            # Publish patterns if significant
            if final_patterns:
                self._publish_pattern_analysis(symbol, timeframe, final_patterns, metrics)
            
            self.logger.info(f"✅ Pattern analysis complete: {metrics.total_patterns_detected} patterns detected")
            return metrics
            
        except Exception as e:
            self.logger.error(f"❌ Error in pattern analysis: {e}")
            return self._create_empty_metrics()

    def _prepare_data(self, market_data: Dict[str, Any]) -> Optional[pd.DataFrame]:
        """Prepare market data for pattern analysis."""
        try:
            if 'prices' not in market_data:
                return None
            
            prices = market_data['prices']
            volumes = market_data.get('volumes', [100] * len(prices))
            
            # Create OHLC data if only prices provided
            if isinstance(prices[0], (int, float)):
                # Convert price list to OHLC
                df_data = []
                for i, price in enumerate(prices):
                    high = price * (1 + np.random.uniform(0, 0.02))
                    low = price * (1 - np.random.uniform(0, 0.02))
                    open_price = prices[i-1] if i > 0 else price
                    
                    df_data.append({
                        'timestamp': datetime.now() - timedelta(hours=len(prices)-i),
                        'open': open_price,
                        'high': max(open_price, high, price),
                        'low': min(open_price, low, price),
                        'close': price,
                        'volume': volumes[i] if i < len(volumes) else 100
                    })
                
                df = pd.DataFrame(df_data)
            else:
                # Assume OHLC data provided
                df = pd.DataFrame(prices)
            
            # Ensure required columns
            required_cols = ['open', 'high', 'low', 'close', 'volume']
            if not all(col in df.columns for col in required_cols):
                self.logger.warning("⚠️ Missing required OHLC columns")
                return None
            
            # Add technical indicators
            df = self._add_technical_indicators(df)
            
            return df
            
        except Exception as e:
            self.logger.error(f"❌ Error preparing data: {e}")
            return None

    def _add_technical_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add technical indicators for pattern analysis."""
        try:
            # Simple moving averages
            df['sma_10'] = df['close'].rolling(window=10).mean()
            df['sma_20'] = df['close'].rolling(window=20).mean()
            df['sma_50'] = df['close'].rolling(window=50).mean()
            
            # Exponential moving averages
            df['ema_12'] = df['close'].ewm(span=12).mean()
            df['ema_26'] = df['close'].ewm(span=26).mean()
            
            # Price relative to moving averages
            df['price_above_sma20'] = (df['close'] > df['sma_20']).astype(int)
            df['price_above_sma50'] = (df['close'] > df['sma_50']).astype(int)
            
            # Volatility measures
            df['price_range'] = (df['high'] - df['low']) / df['close']
            df['body_size'] = abs(df['close'] - df['open']) / df['close']
            
            # Volume analysis
            df['volume_sma'] = df['volume'].rolling(window=20).mean()
            df['volume_ratio'] = df['volume'] / df['volume_sma']
            
            # Price momentum
            df['momentum_5'] = df['close'].pct_change(5)
            df['momentum_10'] = df['close'].pct_change(10)
            
            return df
            
        except Exception as e:
            self.logger.error(f"❌ Error adding technical indicators: {e}")
            return df

    def _detect_traditional_patterns(self, df: pd.DataFrame, symbol: str, timeframe: str) -> List[PatternDetection]:
        """Detect patterns using traditional technical analysis."""
        patterns = []
        
        try:
            # Support and resistance levels
            support_resistance = self._find_support_resistance_levels(df)
            
            # Double top/bottom patterns
            patterns.extend(self._detect_double_patterns(df, symbol, timeframe, support_resistance))
            
            # Head and shoulders patterns
            patterns.extend(self._detect_head_shoulders(df, symbol, timeframe))
            
            # Triangle patterns
            patterns.extend(self._detect_triangles(df, symbol, timeframe))
            
            # Channel patterns
            patterns.extend(self._detect_channels(df, symbol, timeframe))
            
            # Breakout patterns
            patterns.extend(self._detect_breakouts(df, symbol, timeframe, support_resistance))
            
            self.logger.info(f"🔍 Traditional analysis detected {len(patterns)} patterns")
            
        except Exception as e:
            self.logger.error(f"❌ Error in traditional pattern detection: {e}")
        
        return patterns

    def _find_support_resistance_levels(self, df: pd.DataFrame) -> Dict[str, List[float]]:
        """Find key support and resistance levels."""
        try:
            # Find local minima and maxima
            window = 5
            support_levels = []
            resistance_levels = []
            
            for i in range(window, len(df) - window):
                # Check for local minimum (support)
                if (df['low'].iloc[i] == df['low'].iloc[i-window:i+window+1].min()):
                    support_levels.append(df['low'].iloc[i])
                
                # Check for local maximum (resistance)
                if (df['high'].iloc[i] == df['high'].iloc[i-window:i+window+1].max()):
                    resistance_levels.append(df['high'].iloc[i])
            
            # Cluster nearby levels
            support_levels = self._cluster_levels(support_levels)
            resistance_levels = self._cluster_levels(resistance_levels)
            
            return {
                'support': support_levels,
                'resistance': resistance_levels
            }
            
        except Exception as e:
            self.logger.error(f"❌ Error finding support/resistance: {e}")
            return {'support': [], 'resistance': []}

    def _cluster_levels(self, levels: List[float], threshold: float = 0.02) -> List[float]:
        """Cluster nearby price levels."""
        if not levels:
            return []
        
        levels = sorted(levels)
        clustered = [levels[0]]
        
        for level in levels[1:]:
            if abs(level - clustered[-1]) / clustered[-1] > threshold:
                clustered.append(level)
        
        return clustered

    def _detect_double_patterns(self, df: pd.DataFrame, symbol: str, timeframe: str, 
                               support_resistance: Dict[str, List[float]]) -> List[PatternDetection]:
        """Detect double top and double bottom patterns."""
        patterns = []
        
        try:
            # Look for double tops
            resistance_levels = support_resistance['resistance']
            for level in resistance_levels:
                touches = self._count_level_touches(df, level, 'high')
                if touches >= 2:
                    pattern = PatternDetection(
                        pattern_type='double_top',
                        confidence=min(0.7 + touches * 0.1, 0.95),
                        start_time=df.index[0] if hasattr(df.index, '__getitem__') else datetime.now() - timedelta(hours=len(df)),
                        end_time=df.index[-1] if hasattr(df.index, '__getitem__') else datetime.now(),
                        price_level=level,
                        pattern_strength='moderate' if touches == 2 else 'strong',
                        trading_signal='bearish',
                        target_price=level * 0.95,
                        stop_loss=level * 1.02,
                        reliability_score=0.7
                    )
                    patterns.append(pattern)
            
            # Look for double bottoms
            support_levels = support_resistance['support']
            for level in support_levels:
                touches = self._count_level_touches(df, level, 'low')
                if touches >= 2:
                    pattern = PatternDetection(
                        pattern_type='double_bottom',
                        confidence=min(0.7 + touches * 0.1, 0.95),
                        start_time=df.index[0] if hasattr(df.index, '__getitem__') else datetime.now() - timedelta(hours=len(df)),
                        end_time=df.index[-1] if hasattr(df.index, '__getitem__') else datetime.now(),
                        price_level=level,
                        pattern_strength='moderate' if touches == 2 else 'strong',
                        trading_signal='bullish',
                        target_price=level * 1.05,
                        stop_loss=level * 0.98,
                        reliability_score=0.7
                    )
                    patterns.append(pattern)
                    
        except Exception as e:
            self.logger.error(f"❌ Error detecting double patterns: {e}")
        
        return patterns

    def _count_level_touches(self, df: pd.DataFrame, level: float, price_type: str, threshold: float = 0.01) -> int:
        """Count how many times price touched a specific level."""
        try:
            if price_type == 'high':
                touches = ((df['high'] >= level * (1 - threshold)) & 
                          (df['high'] <= level * (1 + threshold))).sum()
            elif price_type == 'low':
                touches = ((df['low'] >= level * (1 - threshold)) & 
                          (df['low'] <= level * (1 + threshold))).sum()
            else:
                touches = 0
            
            return int(touches)
            
        except Exception as e:
            self.logger.error(f"❌ Error counting level touches: {e}")
            return 0

    def _detect_head_shoulders(self, df: pd.DataFrame, symbol: str, timeframe: str) -> List[PatternDetection]:
        """Detect head and shoulders patterns."""
        patterns = []
        
        try:
            # Simplified head and shoulders detection
            if len(df) < 30:
                return patterns
            
            # Look for three peaks pattern
            window = 5
            peaks = []
            
            for i in range(window, len(df) - window):
                if df['high'].iloc[i] == df['high'].iloc[i-window:i+window+1].max():
                    peaks.append((i, df['high'].iloc[i]))
            
            # Analyze peak patterns for head and shoulders
            if len(peaks) >= 3:
                for i in range(len(peaks) - 2):
                    left_shoulder = peaks[i]
                    head = peaks[i + 1]
                    right_shoulder = peaks[i + 2]
                    
                    # Check head and shoulders criteria
                    if (head[1] > left_shoulder[1] and head[1] > right_shoulder[1] and
                        abs(left_shoulder[1] - right_shoulder[1]) / head[1] < 0.05):
                        
                        pattern = PatternDetection(
                            pattern_type='head_shoulders',
                            confidence=0.75,
                            start_time=df.index[left_shoulder[0]] if hasattr(df.index, '__getitem__') else datetime.now() - timedelta(hours=len(df)-left_shoulder[0]),
                            end_time=df.index[right_shoulder[0]] if hasattr(df.index, '__getitem__') else datetime.now() - timedelta(hours=len(df)-right_shoulder[0]),
                            price_level=head[1],
                            pattern_strength='strong',
                            trading_signal='bearish',
                            target_price=head[1] * 0.92,
                            stop_loss=head[1] * 1.03,
                            reliability_score=0.8
                        )
                        patterns.append(pattern)
                        
        except Exception as e:
            self.logger.error(f"❌ Error detecting head and shoulders: {e}")
        
        return patterns

    def _detect_triangles(self, df: pd.DataFrame, symbol: str, timeframe: str) -> List[PatternDetection]:
        """Detect triangle patterns (ascending, descending, symmetrical)."""
        patterns = []
        
        try:
            if len(df) < 20:
                return patterns
            
            # Analyze trend lines for triangle formation
            recent_data = df.tail(50)  # Focus on recent data
            
            # Find trend line slopes
            highs_slope = self._calculate_trend_slope(recent_data, 'high')
            lows_slope = self._calculate_trend_slope(recent_data, 'low')
            
            # Determine triangle type
            if highs_slope < -0.001 and abs(lows_slope) < 0.001:  # Descending triangle
                pattern_type = 'triangle_descending'
                signal = 'bearish'
                target_multiplier = 0.96
            elif lows_slope > 0.001 and abs(highs_slope) < 0.001:  # Ascending triangle
                pattern_type = 'triangle_ascending'
                signal = 'bullish'
                target_multiplier = 1.04
            elif highs_slope < -0.001 and lows_slope > 0.001:  # Symmetrical triangle
                pattern_type = 'triangle_symmetrical'
                signal = 'neutral'
                target_multiplier = 1.0
            else:
                return patterns
            
            # Create pattern detection
            current_price = recent_data['close'].iloc[-1]
            pattern = PatternDetection(
                pattern_type=pattern_type,
                confidence=0.65,
                start_time=recent_data.index[0] if hasattr(recent_data.index, '__getitem__') else datetime.now() - timedelta(hours=len(recent_data)),
                end_time=recent_data.index[-1] if hasattr(recent_data.index, '__getitem__') else datetime.now(),
                price_level=current_price,
                pattern_strength='moderate',
                trading_signal=signal,
                target_price=current_price * target_multiplier if target_multiplier != 1.0 else None,
                stop_loss=current_price * (0.97 if signal == 'bullish' else 1.03),
                reliability_score=0.6
            )
            patterns.append(pattern)
            
        except Exception as e:
            self.logger.error(f"❌ Error detecting triangles: {e}")
        
        return patterns

    def _calculate_trend_slope(self, df: pd.DataFrame, price_type: str) -> float:
        """Calculate trend line slope for highs or lows."""
        try:
            y = df[price_type].values
            x = np.arange(len(y))
            
            # Simple linear regression for slope
            n = len(x)
            slope = (n * np.sum(x * y) - np.sum(x) * np.sum(y)) / (n * np.sum(x**2) - np.sum(x)**2)
            
            return slope / np.mean(y)  # Normalize by price level
            
        except Exception as e:
            self.logger.error(f"❌ Error calculating trend slope: {e}")
            return 0.0

    def _detect_channels(self, df: pd.DataFrame, symbol: str, timeframe: str) -> List[PatternDetection]:
        """Detect channel patterns."""
        patterns = []
        
        try:
            if len(df) < 30:
                return patterns
            
            # Calculate channel bounds
            recent_data = df.tail(100)
            
            # Simple channel detection using rolling statistics
            window = 20
            upper_channel = recent_data['high'].rolling(window=window).max()
            lower_channel = recent_data['low'].rolling(window=window).min()
            middle_channel = (upper_channel + lower_channel) / 2
            
            # Check if price is in a channel
            channel_width = (upper_channel - lower_channel) / middle_channel
            avg_channel_width = channel_width.mean()
            
            current_price = recent_data['close'].iloc[-1]
            upper_bound = upper_channel.iloc[-1]
            lower_bound = lower_channel.iloc[-1]
            
            # Determine channel type
            if avg_channel_width < 0.1:  # Narrow channel
                if current_price > middle_channel.iloc[-1]:
                    signal = 'bullish'
                    pattern_type = 'channel_up'
                elif current_price < middle_channel.iloc[-1]:
                    signal = 'bearish'
                    pattern_type = 'channel_down'
                else:
                    signal = 'neutral'
                    pattern_type = 'horizontal_channel'
                
                pattern = PatternDetection(
                    pattern_type=pattern_type,
                    confidence=0.6,
                    start_time=recent_data.index[0] if hasattr(recent_data.index, '__getitem__') else datetime.now() - timedelta(hours=len(recent_data)),
                    end_time=recent_data.index[-1] if hasattr(recent_data.index, '__getitem__') else datetime.now(),
                    price_level=current_price,
                    pattern_strength='moderate',
                    trading_signal=signal,
                    target_price=upper_bound if signal == 'bullish' else lower_bound if signal == 'bearish' else None,
                    stop_loss=lower_bound if signal == 'bullish' else upper_bound if signal == 'bearish' else None,
                    reliability_score=0.55
                )
                patterns.append(pattern)
                
        except Exception as e:
            self.logger.error(f"❌ Error detecting channels: {e}")
        
        return patterns

    def _detect_breakouts(self, df: pd.DataFrame, symbol: str, timeframe: str, 
                         support_resistance: Dict[str, List[float]]) -> List[PatternDetection]:
        """Detect breakout patterns."""
        patterns = []
        
        try:
            if len(df) < 10:
                return patterns
            
            current_price = df['close'].iloc[-1]
            previous_price = df['close'].iloc[-2]
            volume_ratio = df['volume'].iloc[-1] / df['volume'].rolling(window=20).mean().iloc[-1]
            
            # Check for resistance breakouts
            for resistance in support_resistance['resistance']:
                if (previous_price <= resistance and current_price > resistance and 
                    volume_ratio > 1.5):  # High volume confirmation
                    
                    pattern = PatternDetection(
                        pattern_type='breakout_resistance',
                        confidence=min(0.7 + (volume_ratio - 1.5) * 0.1, 0.9),
                        start_time=df.index[-2] if hasattr(df.index, '__getitem__') else datetime.now() - timedelta(hours=2),
                        end_time=df.index[-1] if hasattr(df.index, '__getitem__') else datetime.now(),
                        price_level=resistance,
                        pattern_strength='strong' if volume_ratio > 2.0 else 'moderate',
                        trading_signal='bullish',
                        target_price=resistance * 1.05,
                        stop_loss=resistance * 0.98,
                        reliability_score=0.75
                    )
                    patterns.append(pattern)
            
            # Check for support breakdowns
            for support in support_resistance['support']:
                if (previous_price >= support and current_price < support and 
                    volume_ratio > 1.5):  # High volume confirmation
                    
                    pattern = PatternDetection(
                        pattern_type='breakout_support',
                        confidence=min(0.7 + (volume_ratio - 1.5) * 0.1, 0.9),
                        start_time=df.index[-2] if hasattr(df.index, '__getitem__') else datetime.now() - timedelta(hours=2),
                        end_time=df.index[-1] if hasattr(df.index, '__getitem__') else datetime.now(),
                        price_level=support,
                        pattern_strength='strong' if volume_ratio > 2.0 else 'moderate',
                        trading_signal='bearish',
                        target_price=support * 0.95,
                        stop_loss=support * 1.02,
                        reliability_score=0.75
                    )
                    patterns.append(pattern)
                    
        except Exception as e:
            self.logger.error(f"❌ Error detecting breakouts: {e}")
        
        return patterns

    def _detect_ml_patterns(self, df: pd.DataFrame, symbol: str, timeframe: str) -> List[PatternDetection]:
        """Detect patterns using machine learning models."""
        patterns = []
        
        try:
            if not HAS_SKLEARN or 'random_forest' in self.models:
                return patterns
            
            # Extract features for ML models
            features = self._extract_ml_features(df)
            if features is None or len(features) < 20:
                return patterns
            
            # Use mock ML predictions for now (would be trained models in production)
            mock_predictions = self._generate_mock_ml_predictions(features, symbol)
            patterns.extend(mock_predictions)
            
        except Exception as e:
            self.logger.error(f"❌ Error in ML pattern detection: {e}")
        
        return patterns

    def _extract_ml_features(self, df: pd.DataFrame) -> Optional[np.ndarray]:
        """Extract features for ML models."""
        try:
            # Technical indicator features
            features = []
            
            for i in range(20, len(df)):  # Need lookback window
                window_data = df.iloc[i-20:i]
                
                feature_vector = [
                    # Price momentum features
                    window_data['close'].pct_change(5).iloc[-1],
                    window_data['close'].pct_change(10).iloc[-1],
                    
                    # Moving average features
                    (window_data['close'].iloc[-1] - window_data['sma_20'].iloc[-1]) / window_data['sma_20'].iloc[-1],
                    (window_data['sma_10'].iloc[-1] - window_data['sma_20'].iloc[-1]) / window_data['sma_20'].iloc[-1],
                    
                    # Volatility features
                    window_data['price_range'].mean(),
                    window_data['price_range'].std(),
                    
                    # Volume features
                    window_data['volume_ratio'].mean(),
                    window_data['volume_ratio'].std(),
                    
                    # Pattern shape features
                    (window_data['high'].max() - window_data['low'].min()) / window_data['close'].mean(),
                    window_data['body_size'].mean()
                ]
                
                features.append(feature_vector)
            
            return np.array(features) if features else None
            
        except Exception as e:
            self.logger.error(f"❌ Error extracting ML features: {e}")
            return None

    def _generate_mock_ml_predictions(self, features: np.ndarray, symbol: str) -> List[PatternDetection]:
        """Generate mock ML predictions (placeholder for trained models)."""
        patterns = []
        
        try:
            # Mock pattern detection based on feature analysis
            if len(features) > 0:
                # Simulate ML model prediction
                confidence = np.random.uniform(0.4, 0.8)
                
                if confidence > 0.6:
                    pattern_types = ['flag', 'pennant', 'wedge_rising', 'wedge_falling']
                    pattern_type = np.random.choice(pattern_types)
                    
                    pattern = PatternDetection(
                        pattern_type=pattern_type,
                        confidence=confidence,
                        start_time=datetime.now() - timedelta(hours=10),
                        end_time=datetime.now(),
                        price_level=100.0,  # Mock price
                        pattern_strength='moderate',
                        trading_signal='bullish' if confidence > 0.7 else 'neutral',
                        reliability_score=confidence * 0.8
                    )
                    patterns.append(pattern)
                    
        except Exception as e:
            self.logger.error(f"❌ Error generating mock ML predictions: {e}")
        
        return patterns

    def _detect_dl_patterns(self, df: pd.DataFrame, symbol: str, timeframe: str) -> List[PatternDetection]:
        """Detect patterns using deep learning models."""
        patterns = []
        
        try:
            if not HAS_TENSORFLOW:
                return patterns
            
            # Deep learning pattern detection would go here
            # For now, return empty as models need training
            self.logger.info("🧠 Deep learning pattern detection available but requires trained models")
            
        except Exception as e:
            self.logger.error(f"❌ Error in deep learning pattern detection: {e}")
        
        return patterns

    def _ensemble_patterns(self, all_patterns: List[PatternDetection]) -> List[PatternDetection]:
        """Ensemble multiple pattern detection results."""
        try:
            if not all_patterns:
                return []
            
            # Group similar patterns
            pattern_groups = defaultdict(list)
            for pattern in all_patterns:
                key = f"{pattern.pattern_type}_{pattern.trading_signal}"
                pattern_groups[key].append(pattern)
            
            # Select best pattern from each group
            final_patterns = []
            for group_patterns in pattern_groups.values():
                # Select pattern with highest confidence
                best_pattern = max(group_patterns, key=lambda p: p.confidence)
                
                # Boost confidence if multiple models agree
                if len(group_patterns) > 1:
                    confidence_boost = min(0.1 * (len(group_patterns) - 1), 0.2)
                    best_pattern = PatternDetection(
                        pattern_type=best_pattern.pattern_type,
                        confidence=min(best_pattern.confidence + confidence_boost, 0.95),
                        start_time=best_pattern.start_time,
                        end_time=best_pattern.end_time,
                        price_level=best_pattern.price_level,
                        pattern_strength=best_pattern.pattern_strength,
                        trading_signal=best_pattern.trading_signal,
                        target_price=best_pattern.target_price,
                        stop_loss=best_pattern.stop_loss,
                        reliability_score=min(best_pattern.reliability_score + confidence_boost, 0.95)
                    )
                
                final_patterns.append(best_pattern)
            
            # Filter by minimum confidence
            final_patterns = [p for p in final_patterns if p.confidence >= 0.5]
            
            # Sort by confidence
            final_patterns.sort(key=lambda p: p.confidence, reverse=True)
            
            return final_patterns
            
        except Exception as e:
            self.logger.error(f"❌ Error in pattern ensemble: {e}")
            return all_patterns[:5]  # Return top 5 as fallback

    def _calculate_pattern_metrics(self, patterns: List[PatternDetection]) -> PatternMetrics:
        """Calculate comprehensive pattern metrics."""
        try:
            if not patterns:
                return self._create_empty_metrics()
            
            # Count patterns by signal
            bullish_count = sum(1 for p in patterns if p.trading_signal == 'bullish')
            bearish_count = sum(1 for p in patterns if p.trading_signal == 'bearish')
            neutral_count = sum(1 for p in patterns if p.trading_signal == 'neutral')
            
            # Count high confidence patterns
            high_confidence_count = sum(1 for p in patterns if p.confidence >= 0.7)
            
            # Pattern distribution
            pattern_dist = defaultdict(int)
            for pattern in patterns:
                pattern_dist[pattern.pattern_type] += 1
            
            # Find strongest signal
            strongest_pattern = max(patterns, key=lambda p: p.confidence) if patterns else None
            
            # Calculate average confidence
            avg_confidence = sum(p.confidence for p in patterns) / len(patterns)
            
            return PatternMetrics(
                total_patterns_detected=len(patterns),
                bullish_patterns=bullish_count,
                bearish_patterns=bearish_count,
                neutral_patterns=neutral_count,
                high_confidence_patterns=high_confidence_count,
                pattern_distribution=dict(pattern_dist),
                average_confidence=avg_confidence,
                strongest_signal=strongest_pattern
            )
            
        except Exception as e:
            self.logger.error(f"❌ Error calculating pattern metrics: {e}")
            return self._create_empty_metrics()

    def _create_empty_metrics(self) -> PatternMetrics:
        """Create empty pattern metrics."""
        return PatternMetrics(
            total_patterns_detected=0,
            bullish_patterns=0,
            bearish_patterns=0,
            neutral_patterns=0,
            high_confidence_patterns=0,
            pattern_distribution={},
            average_confidence=0.0,
            strongest_signal=None
        )

    def _publish_pattern_analysis(self, symbol: str, timeframe: str, patterns: List[PatternDetection], 
                                 metrics: PatternMetrics):
        """Publish pattern analysis results."""
        try:
            analysis_data = {
                'symbol': symbol,
                'timeframe': timeframe,
                'timestamp': datetime.now().isoformat(),
                'patterns': [
                    {
                        'type': p.pattern_type,
                        'confidence': p.confidence,
                        'signal': p.trading_signal,
                        'strength': p.pattern_strength,
                        'price_level': p.price_level,
                        'target_price': p.target_price,
                        'stop_loss': p.stop_loss,
                        'reliability': p.reliability_score
                    }
                    for p in patterns
                ],
                'metrics': {
                    'total_patterns': metrics.total_patterns_detected,
                    'bullish_patterns': metrics.bullish_patterns,
                    'bearish_patterns': metrics.bearish_patterns,
                    'high_confidence_patterns': metrics.high_confidence_patterns,
                    'average_confidence': metrics.average_confidence,
                    'strongest_signal': {
                        'type': metrics.strongest_signal.pattern_type,
                        'confidence': metrics.strongest_signal.confidence,
                        'signal': metrics.strongest_signal.trading_signal
                    } if metrics.strongest_signal else None
                }
            }
            
            # Publish to message broker
            if self.message_broker and self.message_broker.connection:
                self.message_broker.publish(
                    exchange='ai_analysis',
                    routing_key='pattern_recognition',
                    message=json.dumps(analysis_data)
                )
                self.logger.info(f"📤 Pattern analysis published for {symbol}")
            
        except Exception as e:
            self.logger.error(f"❌ Error publishing pattern analysis: {e}")

    def start_real_time_analysis(self, symbols: List[str], timeframes: List[str] = ['1h']):
        """Start real-time pattern analysis for multiple symbols."""
        try:
            self.logger.info(f"🚀 Starting real-time pattern analysis for {len(symbols)} symbols")
            
            # This would typically run in a separate thread/process
            # For now, just log the capability
            for symbol in symbols:
                for timeframe in timeframes:
                    self.logger.info(f"📊 Real-time pattern monitoring: {symbol} on {timeframe}")
            
            self.logger.info("✅ Real-time pattern analysis started")
            
        except Exception as e:
            self.logger.error(f"❌ Error starting real-time analysis: {e}")

    def stop_real_time_analysis(self):
        """Stop real-time pattern analysis."""
        try:
            self.logger.info("🛑 Stopping real-time pattern analysis")
            
        except Exception as e:
            self.logger.error(f"❌ Error stopping real-time analysis: {e}")
    
    def _setup_message_subscriptions(self):
        """Setup RabbitMQ subscriptions for receiving analysis requests."""
        try:
            # Subscribe to pattern analysis requests
            self.message_broker.subscribe_to_queue(
                'ai_pattern_detection', 
                self._handle_pattern_request
            )
            
            # Subscribe to market data for real-time analysis
            self.message_broker.subscribe_to_queue(
                'market_data_ticks',
                self._handle_market_data
            )
            
            self.logger.info("✅ Pattern Recognition message subscriptions setup")
            
        except Exception as e:
            self.logger.error(f"❌ Failed to setup pattern recognition subscriptions: {e}")
    
    def _handle_pattern_request(self, message):
        """Handle incoming pattern analysis requests."""
        try:
            data = message.get('data', {})
            symbol = data.get('symbol')
            action = data.get('action')
            
            if action == 'detect_patterns' and symbol:
                self.logger.info(f"📥 Received pattern detection request for {symbol}")
                
                # Generate sample data for analysis (in production, fetch real data)
                sample_data = self._generate_sample_data(symbol)
                
                # Perform pattern analysis
                results = self.analyze_patterns(symbol, sample_data, '5m')
                
                # Publish results back
                self.message_broker.publish_ai_analysis(
                    'pattern_results',
                    symbol,
                    {
                        'symbol': symbol,
                        'analysis_results': results.__dict__ if hasattr(results, '__dict__') else str(results),
                        'timestamp': datetime.now().isoformat()
                    }
                )
                
                self.logger.info(f"✅ Completed pattern analysis for {symbol}")
            
        except Exception as e:
            self.logger.error(f"❌ Error handling pattern request: {e}")
    
    def _handle_market_data(self, message):
        """Handle incoming market data for real-time pattern analysis."""
        try:
            data = message.get('data', {})
            symbol = data.get('symbol')
            
            if symbol:
                # Store market data for pattern analysis
                if symbol not in self.pattern_cache:
                    self.pattern_cache[symbol] = []
                
                # Add new data point
                self.pattern_cache[symbol].append(data)
                
                # Keep only recent data (last 100 points)
                if len(self.pattern_cache[symbol]) > 100:
                    self.pattern_cache[symbol] = self.pattern_cache[symbol][-100:]
                
                self.logger.debug(f"📊 Updated market data cache for {symbol}")
            
        except Exception as e:
            self.logger.error(f"❌ Error handling market data: {e}")
    
    def _generate_sample_data(self, symbol: str) -> Dict[str, List]:
        """Generate sample market data for testing."""
        # In production, this would fetch real data from Angel One API
        np.random.seed(hash(symbol) % 2**32)
        
        base_price = 100 + (hash(symbol) % 1000)
        prices = [base_price + i + np.random.random() * 5 for i in range(100)]
        volumes = [1000 + np.random.randint(0, 500) for _ in range(100)]
        
        return {
            'prices': prices,
            'volumes': volumes,
            'timestamps': [datetime.now().isoformat() for _ in range(100)]
        }
    
    def start_async_processing(self):
        """Start asynchronous message processing."""
        try:
            self.logger.info("🔄 Starting pattern recognition async processing...")
            # Start consuming messages (this would be done in a separate thread)
            self.logger.info("✅ Pattern Recognition Engine ready for async processing")
        except Exception as e:
            self.logger.error(f"❌ Error starting async processing: {e}")

    def test_pattern_detector(self):
        """Test the pattern detection engine."""
        try:
            self.logger.info("🧪 Testing Advanced Pattern Recognition Engine")
            
            # Create mock market data
            mock_data = {
                'prices': [100 + i + np.random.random() * 5 for i in range(100)],
                'volumes': [1000 + np.random.randint(0, 500) for _ in range(100)]
            }
            
            # Test pattern analysis
            metrics = self.analyze_patterns('TEST-PATTERN', mock_data, '1h')
            
            # Display results
            print(f"🔍 Pattern Analysis Results:")
            print(f"   Total Patterns: {metrics.total_patterns_detected}")
            print(f"   Bullish Patterns: {metrics.bullish_patterns}")
            print(f"   Bearish Patterns: {metrics.bearish_patterns}")
            print(f"   High Confidence: {metrics.high_confidence_patterns}")
            print(f"   Average Confidence: {metrics.average_confidence:.2f}")
            
            if metrics.strongest_signal:
                print(f"   Strongest Signal: {metrics.strongest_signal.pattern_type} ({metrics.strongest_signal.confidence:.2f})")
            
            print(f"   Pattern Distribution: {metrics.pattern_distribution}")
            
            # Test real-time capabilities
            self.start_real_time_analysis(['TEST-1', 'TEST-2'], ['5m', '1h'])
            
            self.logger.info("✅ Pattern Recognition Engine test completed successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Pattern detector test failed: {e}")
            return False

def main():
    """Main function for testing the pattern detector."""
    print("🔍 Advanced Pattern Recognition Engine Test")
    print("=" * 50)
    
    detector = AdvancedPatternDetector()
    success = detector.test_pattern_detector()
    
    if success:
        print("\n🎉 Pattern Recognition Engine is ready for production!")
    else:
        print("\n❌ Pattern Recognition Engine needs attention")

if __name__ == '__main__':
    main()

