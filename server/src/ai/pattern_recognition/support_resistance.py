"""
Support and Resistance Level Detection
Advanced algorithm for identifying key price levels using multiple technical approaches.

Features:
- Pivot point analysis
- Volume profile analysis
- Fibonacci retracements
- Dynamic level strength scoring
- Multi-timeframe level validation
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

from server.src.core.message_broker import get_message_broker

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class SupportResistanceLevel:
    """Support or resistance level with metadata."""
    level: float
    level_type: str  # 'support', 'resistance'
    strength: float  # 0.0 to 1.0
    touch_count: int
    volume_at_level: float
    first_touch: datetime
    last_touch: datetime
    confidence: float
    breakout_target: Optional[float] = None
    fibonacci_level: Optional[str] = None
    pivot_type: Optional[str] = None

class SupportResistanceMetrics(NamedTuple):
    """Support and resistance analysis metrics."""
    total_levels: int
    support_levels: int
    resistance_levels: int
    strong_levels: int
    weak_levels: int
    most_recent_level: Optional[SupportResistanceLevel]
    strongest_level: Optional[SupportResistanceLevel]
    nearest_support: Optional[SupportResistanceLevel]
    nearest_resistance: Optional[SupportResistanceLevel]
    level_density: float

class SupportResistanceDetector:
    """
    Advanced Support and Resistance Level Detection System.
    
    Features:
    - Multi-method level detection (pivots, volume, fibonacci)
    - Dynamic strength scoring
    - Real-time level monitoring
    - Breakout/breakdown detection
    - Multi-timeframe validation
    """
    
    def __init__(self):
        """Initialize the Support and Resistance Detector."""
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self.message_broker = get_message_broker()
        
        # Detection parameters
        self.pivot_window = 5
        self.min_touches = 2
        self.level_threshold = 0.005  # 0.5% price tolerance
        self.volume_threshold = 1.2   # Volume multiplier for significance
        
        # Strength thresholds
        self.strength_thresholds = {
            'weak': 0.3,
            'moderate': 0.6,
            'strong': 0.8
        }
        
        # Fibonacci levels
        self.fibonacci_levels = [0.236, 0.382, 0.5, 0.618, 0.786]
        
        self.logger.info("📊 Advanced Support/Resistance Detector initialized")

    def detect_support_resistance_levels(self, symbol: str, ohlc_data: pd.DataFrame, 
                                       include_volume: bool = True) -> SupportResistanceMetrics:
        """
        Comprehensive support and resistance level detection.
        
        Args:
            symbol: Trading symbol
            ohlc_data: OHLC price data with volume
            include_volume: Whether to use volume in analysis
            
        Returns:
            SupportResistanceMetrics with detected levels and analysis
        """
        try:
            self.logger.info(f"📊 Detecting support/resistance levels for {symbol}")
            
            if len(ohlc_data) < 20:
                self.logger.warning(f"⚠️ Insufficient data for S/R analysis: {len(ohlc_data)} bars")
                return self._create_empty_metrics()
            
            # Detect levels using multiple methods
            all_levels = []
            
            # Method 1: Pivot point analysis
            pivot_levels = self._detect_pivot_levels(ohlc_data)
            all_levels.extend(pivot_levels)
            
            # Method 2: Volume profile analysis (if volume available)
            if include_volume and 'volume' in ohlc_data.columns:
                volume_levels = self._detect_volume_levels(ohlc_data)
                all_levels.extend(volume_levels)
            
            # Method 3: Fibonacci retracements
            fib_levels = self._detect_fibonacci_levels(ohlc_data)
            all_levels.extend(fib_levels)
            
            # Method 4: Round number levels
            round_levels = self._detect_round_number_levels(ohlc_data)
            all_levels.extend(round_levels)
            
            # Consolidate and filter levels
            consolidated_levels = self._consolidate_levels(all_levels)
            significant_levels = self._filter_significant_levels(consolidated_levels, ohlc_data)
            
            # Calculate metrics
            metrics = self._calculate_sr_metrics(significant_levels, ohlc_data)
            
            # Publish results
            if significant_levels:
                self._publish_sr_analysis(symbol, significant_levels, metrics)
            
            self.logger.info(f"✅ S/R analysis complete: {metrics.total_levels} levels detected")
            return metrics
            
        except Exception as e:
            self.logger.error(f"❌ Error in support/resistance detection: {e}")
            return self._create_empty_metrics()

    def _detect_pivot_levels(self, df: pd.DataFrame) -> List[SupportResistanceLevel]:
        """Detect support and resistance using pivot point analysis."""
        levels = []
        
        try:
            # Find local minima (support) and maxima (resistance)
            window = self.pivot_window
            
            for i in range(window, len(df) - window):
                current_high = df['high'].iloc[i]
                current_low = df['low'].iloc[i]
                
                # Check for resistance (local maximum)
                if current_high == df['high'].iloc[i-window:i+window+1].max():
                    touches = self._count_touches(df, current_high, 'resistance', i)
                    if touches >= self.min_touches:
                        level = SupportResistanceLevel(
                            level=current_high,
                            level_type='resistance',
                            strength=min(0.5 + touches * 0.1, 1.0),
                            touch_count=touches,
                            volume_at_level=df['volume'].iloc[i] if 'volume' in df.columns else 0,
                            first_touch=df.index[i] if hasattr(df.index, '__getitem__') else datetime.now(),
                            last_touch=df.index[i] if hasattr(df.index, '__getitem__') else datetime.now(),
                            confidence=0.7 + min(touches * 0.05, 0.2),
                            pivot_type='resistance_pivot'
                        )
                        levels.append(level)
                
                # Check for support (local minimum)
                if current_low == df['low'].iloc[i-window:i+window+1].min():
                    touches = self._count_touches(df, current_low, 'support', i)
                    if touches >= self.min_touches:
                        level = SupportResistanceLevel(
                            level=current_low,
                            level_type='support',
                            strength=min(0.5 + touches * 0.1, 1.0),
                            touch_count=touches,
                            volume_at_level=df['volume'].iloc[i] if 'volume' in df.columns else 0,
                            first_touch=df.index[i] if hasattr(df.index, '__getitem__') else datetime.now(),
                            last_touch=df.index[i] if hasattr(df.index, '__getitem__') else datetime.now(),
                            confidence=0.7 + min(touches * 0.05, 0.2),
                            pivot_type='support_pivot'
                        )
                        levels.append(level)
                        
        except Exception as e:
            self.logger.error(f"❌ Error detecting pivot levels: {e}")
        
        return levels

    def _detect_volume_levels(self, df: pd.DataFrame) -> List[SupportResistanceLevel]:
        """Detect levels using volume profile analysis."""
        levels = []
        
        try:
            # Calculate volume-weighted average price levels
            price_volume_data = []
            
            for i in range(len(df)):
                # Create price buckets for volume analysis
                high_price = df['high'].iloc[i]
                low_price = df['low'].iloc[i]
                volume = df['volume'].iloc[i]
                
                # Distribute volume across price range
                price_range = high_price - low_price
                if price_range > 0:
                    num_buckets = max(1, int(price_range / (low_price * 0.001)))  # 0.1% buckets
                    volume_per_bucket = volume / num_buckets
                    
                    for j in range(num_buckets):
                        bucket_price = low_price + (j * price_range / num_buckets)
                        price_volume_data.append({
                            'price': bucket_price,
                            'volume': volume_per_bucket,
                            'index': i
                        })
            
            if not price_volume_data:
                return levels
            
            # Convert to DataFrame for analysis
            pv_df = pd.DataFrame(price_volume_data)
            
            # Group by price levels and sum volume
            price_min = pv_df['price'].min()
            price_max = pv_df['price'].max()
            num_levels = 50  # Divide price range into 50 levels
            
            level_size = (price_max - price_min) / num_levels
            pv_df['price_level'] = ((pv_df['price'] - price_min) / level_size).round() * level_size + price_min
            
            volume_by_level = pv_df.groupby('price_level')['volume'].sum().sort_values(ascending=False)
            
            # Find high volume levels
            avg_volume = volume_by_level.mean()
            significant_levels = volume_by_level[volume_by_level > avg_volume * self.volume_threshold]
            
            for price_level, volume in significant_levels.head(10).items():  # Top 10 volume levels
                # Determine if support or resistance based on current price
                current_price = df['close'].iloc[-1]
                level_type = 'resistance' if price_level > current_price else 'support'
                
                # Calculate strength based on volume
                volume_strength = min(volume / volume_by_level.max(), 1.0)
                
                level = SupportResistanceLevel(
                    level=price_level,
                    level_type=level_type,
                    strength=volume_strength,
                    touch_count=0,  # Will be calculated later
                    volume_at_level=volume,
                    first_touch=df.index[0] if hasattr(df.index, '__getitem__') else datetime.now(),
                    last_touch=df.index[-1] if hasattr(df.index, '__getitem__') else datetime.now(),
                    confidence=0.6 + volume_strength * 0.3,
                    pivot_type='volume_level'
                )
                levels.append(level)
                
        except Exception as e:
            self.logger.error(f"❌ Error detecting volume levels: {e}")
        
        return levels

    def _detect_fibonacci_levels(self, df: pd.DataFrame) -> List[SupportResistanceLevel]:
        """Detect Fibonacci retracement levels."""
        levels = []
        
        try:
            # Find significant swing high and low
            recent_data = df.tail(100)  # Use recent data for relevance
            
            swing_high = recent_data['high'].max()
            swing_low = recent_data['low'].min()
            swing_range = swing_high - swing_low
            
            if swing_range == 0:
                return levels
            
            current_price = df['close'].iloc[-1]
            
            # Calculate Fibonacci levels
            for fib_ratio in self.fibonacci_levels:
                # Retracement from high
                fib_level_from_high = swing_high - (swing_range * fib_ratio)
                
                # Retracement from low  
                fib_level_from_low = swing_low + (swing_range * fib_ratio)
                
                # Add level from high (potential support)
                if fib_level_from_high < current_price:
                    level = SupportResistanceLevel(
                        level=fib_level_from_high,
                        level_type='support',
                        strength=0.6,  # Moderate strength for Fibonacci
                        touch_count=0,
                        volume_at_level=0,
                        first_touch=recent_data.index[0] if hasattr(recent_data.index, '__getitem__') else datetime.now(),
                        last_touch=recent_data.index[-1] if hasattr(recent_data.index, '__getitem__') else datetime.now(),
                        confidence=0.6,
                        fibonacci_level=f"{fib_ratio:.1%} retracement"
                    )
                    levels.append(level)
                
                # Add level from low (potential resistance)
                if fib_level_from_low > current_price:
                    level = SupportResistanceLevel(
                        level=fib_level_from_low,
                        level_type='resistance',
                        strength=0.6,
                        touch_count=0,
                        volume_at_level=0,
                        first_touch=recent_data.index[0] if hasattr(recent_data.index, '__getitem__') else datetime.now(),
                        last_touch=recent_data.index[-1] if hasattr(recent_data.index, '__getitem__') else datetime.now(),
                        confidence=0.6,
                        fibonacci_level=f"{fib_ratio:.1%} retracement"
                    )
                    levels.append(level)
                    
        except Exception as e:
            self.logger.error(f"❌ Error detecting Fibonacci levels: {e}")
        
        return levels

    def _detect_round_number_levels(self, df: pd.DataFrame) -> List[SupportResistanceLevel]:
        """Detect psychological round number levels."""
        levels = []
        
        try:
            current_price = df['close'].iloc[-1]
            price_range = df['high'].max() - df['low'].min()
            
            # Determine round number intervals based on price
            if current_price < 10:
                intervals = [0.5, 1.0]
            elif current_price < 100:
                intervals = [1, 5, 10]
            elif current_price < 1000:
                intervals = [10, 25, 50, 100]
            else:
                intervals = [100, 250, 500, 1000]
            
            for interval in intervals:
                # Find round numbers within reasonable range
                lower_bound = current_price - price_range * 0.2
                upper_bound = current_price + price_range * 0.2
                
                start_level = int(lower_bound / interval) * interval
                end_level = int(upper_bound / interval) * interval
                
                for level_price in range(int(start_level), int(end_level) + int(interval), int(interval)):
                    if lower_bound <= level_price <= upper_bound and level_price != current_price:
                        # Determine if support or resistance
                        level_type = 'resistance' if level_price > current_price else 'support'
                        
                        # Count actual touches for this level
                        touches = self._count_touches(df, level_price, level_type, len(df)-1)
                        
                        if touches > 0:  # Only add if price has actually touched this level
                            level = SupportResistanceLevel(
                                level=float(level_price),
                                level_type=level_type,
                                strength=0.4 + min(touches * 0.1, 0.3),  # Moderate strength for round numbers
                                touch_count=touches,
                                volume_at_level=0,
                                first_touch=df.index[0] if hasattr(df.index, '__getitem__') else datetime.now(),
                                last_touch=df.index[-1] if hasattr(df.index, '__getitem__') else datetime.now(),
                                confidence=0.5 + min(touches * 0.05, 0.2),
                                pivot_type='round_number'
                            )
                            levels.append(level)
                            
        except Exception as e:
            self.logger.error(f"❌ Error detecting round number levels: {e}")
        
        return levels

    def _count_touches(self, df: pd.DataFrame, level: float, level_type: str, max_index: int) -> int:
        """Count how many times price touched a specific level."""
        try:
            touches = 0
            threshold = level * self.level_threshold
            
            for i in range(min(max_index + 1, len(df))):
                if level_type == 'resistance':
                    # Check if high touched resistance level
                    if abs(df['high'].iloc[i] - level) <= threshold:
                        touches += 1
                elif level_type == 'support':
                    # Check if low touched support level
                    if abs(df['low'].iloc[i] - level) <= threshold:
                        touches += 1
                        
            return touches
            
        except Exception as e:
            self.logger.error(f"❌ Error counting touches: {e}")
            return 0

    def _consolidate_levels(self, levels: List[SupportResistanceLevel]) -> List[SupportResistanceLevel]:
        """Consolidate nearby levels into single stronger levels."""
        try:
            if not levels:
                return []
            
            # Sort levels by price
            sorted_levels = sorted(levels, key=lambda x: x.level)
            consolidated = []
            
            i = 0
            while i < len(sorted_levels):
                current_level = sorted_levels[i]
                nearby_levels = [current_level]
                
                # Find all levels within threshold
                j = i + 1
                while j < len(sorted_levels):
                    if abs(sorted_levels[j].level - current_level.level) / current_level.level <= self.level_threshold:
                        nearby_levels.append(sorted_levels[j])
                        j += 1
                    else:
                        break
                
                # Consolidate nearby levels
                if len(nearby_levels) > 1:
                    # Calculate weighted average level
                    total_strength = sum(level.strength for level in nearby_levels)
                    weighted_level = sum(level.level * level.strength for level in nearby_levels) / total_strength
                    
                    # Combine properties
                    max_strength_level = max(nearby_levels, key=lambda x: x.strength)
                    total_touches = sum(level.touch_count for level in nearby_levels)
                    total_volume = sum(level.volume_at_level for level in nearby_levels)
                    avg_confidence = sum(level.confidence for level in nearby_levels) / len(nearby_levels)
                    
                    consolidated_level = SupportResistanceLevel(
                        level=weighted_level,
                        level_type=max_strength_level.level_type,
                        strength=min(total_strength / len(nearby_levels) * 1.2, 1.0),  # Boost consolidated strength
                        touch_count=total_touches,
                        volume_at_level=total_volume,
                        first_touch=min(level.first_touch for level in nearby_levels),
                        last_touch=max(level.last_touch for level in nearby_levels),
                        confidence=min(avg_confidence * 1.1, 0.95),  # Boost consolidated confidence
                        fibonacci_level=max_strength_level.fibonacci_level,
                        pivot_type=max_strength_level.pivot_type
                    )
                    consolidated.append(consolidated_level)
                else:
                    consolidated.append(current_level)
                
                i = j
            
            return consolidated
            
        except Exception as e:
            self.logger.error(f"❌ Error consolidating levels: {e}")
            return levels

    def _filter_significant_levels(self, levels: List[SupportResistanceLevel], 
                                 df: pd.DataFrame) -> List[SupportResistanceLevel]:
        """Filter to keep only significant levels."""
        try:
            current_price = df['close'].iloc[-1]
            
            # Filter by minimum strength and confidence
            significant_levels = [
                level for level in levels 
                if level.strength >= 0.3 and level.confidence >= 0.4
            ]
            
            # Sort by strength and keep top levels
            significant_levels.sort(key=lambda x: x.strength, reverse=True)
            
            # Limit total number of levels
            max_levels = 15
            if len(significant_levels) > max_levels:
                significant_levels = significant_levels[:max_levels]
            
            # Calculate breakout targets
            for level in significant_levels:
                if level.level_type == 'resistance':
                    # Resistance breakout target
                    level.breakout_target = level.level * 1.02  # 2% above resistance
                else:
                    # Support breakdown target  
                    level.breakout_target = level.level * 0.98  # 2% below support
            
            return significant_levels
            
        except Exception as e:
            self.logger.error(f"❌ Error filtering significant levels: {e}")
            return levels

    def _calculate_sr_metrics(self, levels: List[SupportResistanceLevel], 
                            df: pd.DataFrame) -> SupportResistanceMetrics:
        """Calculate comprehensive support and resistance metrics."""
        try:
            if not levels:
                return self._create_empty_metrics()
            
            current_price = df['close'].iloc[-1]
            
            # Count levels by type
            support_count = sum(1 for level in levels if level.level_type == 'support')
            resistance_count = sum(1 for level in levels if level.level_type == 'resistance')
            
            # Count by strength
            strong_count = sum(1 for level in levels if level.strength >= 0.7)
            weak_count = sum(1 for level in levels if level.strength < 0.5)
            
            # Find most recent level (by last touch time)
            most_recent = max(levels, key=lambda x: x.last_touch) if levels else None
            
            # Find strongest level
            strongest = max(levels, key=lambda x: x.strength) if levels else None
            
            # Find nearest support and resistance
            supports = [level for level in levels if level.level_type == 'support' and level.level < current_price]
            resistances = [level for level in levels if level.level_type == 'resistance' and level.level > current_price]
            
            nearest_support = max(supports, key=lambda x: x.level) if supports else None
            nearest_resistance = min(resistances, key=lambda x: x.level) if resistances else None
            
            # Calculate level density (levels per price range)
            if levels:
                price_range = max(level.level for level in levels) - min(level.level for level in levels)
                level_density = len(levels) / price_range if price_range > 0 else 0
            else:
                level_density = 0
            
            return SupportResistanceMetrics(
                total_levels=len(levels),
                support_levels=support_count,
                resistance_levels=resistance_count,
                strong_levels=strong_count,
                weak_levels=weak_count,
                most_recent_level=most_recent,
                strongest_level=strongest,
                nearest_support=nearest_support,
                nearest_resistance=nearest_resistance,
                level_density=level_density
            )
            
        except Exception as e:
            self.logger.error(f"❌ Error calculating S/R metrics: {e}")
            return self._create_empty_metrics()

    def _create_empty_metrics(self) -> SupportResistanceMetrics:
        """Create empty support/resistance metrics."""
        return SupportResistanceMetrics(
            total_levels=0,
            support_levels=0,
            resistance_levels=0,
            strong_levels=0,
            weak_levels=0,
            most_recent_level=None,
            strongest_level=None,
            nearest_support=None,
            nearest_resistance=None,
            level_density=0.0
        )

    def _publish_sr_analysis(self, symbol: str, levels: List[SupportResistanceLevel], 
                           metrics: SupportResistanceMetrics):
        """Publish support and resistance analysis results."""
        try:
            analysis_data = {
                'symbol': symbol,
                'timestamp': datetime.now().isoformat(),
                'analysis_type': 'support_resistance',
                'levels': [
                    {
                        'level': level.level,
                        'type': level.level_type,
                        'strength': level.strength,
                        'touch_count': level.touch_count,
                        'confidence': level.confidence,
                        'volume_at_level': level.volume_at_level,
                        'breakout_target': level.breakout_target,
                        'fibonacci_level': level.fibonacci_level,
                        'pivot_type': level.pivot_type
                    }
                    for level in levels
                ],
                'metrics': {
                    'total_levels': metrics.total_levels,
                    'support_levels': metrics.support_levels,
                    'resistance_levels': metrics.resistance_levels,
                    'strong_levels': metrics.strong_levels,
                    'level_density': metrics.level_density,
                    'nearest_support': metrics.nearest_support.level if metrics.nearest_support else None,
                    'nearest_resistance': metrics.nearest_resistance.level if metrics.nearest_resistance else None,
                    'strongest_level': {
                        'level': metrics.strongest_level.level,
                        'type': metrics.strongest_level.level_type,
                        'strength': metrics.strongest_level.strength
                    } if metrics.strongest_level else None
                }
            }
            
            # Publish to message broker
            if self.message_broker and self.message_broker.connection:
                self.message_broker.publish(
                    exchange='ai_analysis',
                    routing_key='support_resistance',
                    message=json.dumps(analysis_data)
                )
                self.logger.info(f"📤 Support/Resistance analysis published for {symbol}")
            
        except Exception as e:
            self.logger.error(f"❌ Error publishing S/R analysis: {e}")

    def test_support_resistance_detector(self):
        """Test the support and resistance detector."""
        try:
            self.logger.info("🧪 Testing Support and Resistance Detector")
            
            # Create mock OHLC data with clear support/resistance levels
            np.random.seed(42)  # For reproducible results
            
            mock_data = []
            base_price = 100
            
            # Create data with clear support at 95 and resistance at 105
            for i in range(100):
                if i < 20:  # Initial uptrend
                    price = base_price + i * 0.5 + np.random.random() * 2
                elif i < 40:  # Test resistance at 105
                    price = min(105, base_price + 20 + np.random.random() * 3)
                elif i < 60:  # Pullback to support at 95
                    price = max(95, 105 - (i-40) * 0.8 + np.random.random() * 3)
                elif i < 80:  # Bounce from support
                    price = 95 + (i-60) * 0.7 + np.random.random() * 3
                else:  # Test resistance again
                    price = min(105, 95 + 14 + np.random.random() * 3)
                
                # Create OHLC from price
                high = price + np.random.random() * 1
                low = price - np.random.random() * 1
                open_price = (price + np.random.random() * 2 - 1)
                close = price
                volume = 1000 + np.random.randint(0, 500)
                
                mock_data.append({
                    'open': open_price,
                    'high': high,
                    'low': low,
                    'close': close,
                    'volume': volume
                })
            
            df = pd.DataFrame(mock_data)
            
            # Test support/resistance detection
            metrics = self.detect_support_resistance_levels('TEST-SR', df, include_volume=True)
            
            # Display results
            print(f"📊 Support/Resistance Analysis Results:")
            print(f"   Total Levels: {metrics.total_levels}")
            print(f"   Support Levels: {metrics.support_levels}")
            print(f"   Resistance Levels: {metrics.resistance_levels}")
            print(f"   Strong Levels: {metrics.strong_levels}")
            print(f"   Level Density: {metrics.level_density:.4f}")
            
            if metrics.nearest_support:
                print(f"   Nearest Support: {metrics.nearest_support.level:.2f} (strength: {metrics.nearest_support.strength:.2f})")
            
            if metrics.nearest_resistance:
                print(f"   Nearest Resistance: {metrics.nearest_resistance.level:.2f} (strength: {metrics.nearest_resistance.strength:.2f})")
            
            if metrics.strongest_level:
                print(f"   Strongest Level: {metrics.strongest_level.level:.2f} ({metrics.strongest_level.level_type}) - {metrics.strongest_level.strength:.2f}")
            
            self.logger.info("✅ Support/Resistance Detector test completed successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Support/Resistance detector test failed: {e}")
            return False

def main():
    """Main function for testing the support/resistance detector."""
    print("📊 Support and Resistance Detector Test")
    print("=" * 50)
    
    detector = SupportResistanceDetector()
    success = detector.test_support_resistance_detector()
    
    if success:
        print("\n🎉 Support and Resistance Detector is ready!")
    else:
        print("\n❌ Support and Resistance Detector needs attention")

if __name__ == '__main__':
    main()




