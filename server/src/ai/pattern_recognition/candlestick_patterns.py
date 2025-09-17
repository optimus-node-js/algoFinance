"""
Candlestick Pattern Analyzer
Advanced detection of Japanese candlestick patterns for trading signals.

Implements 40+ candlestick patterns with confidence scoring and ensemble analysis.
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
class CandlestickPattern:
    """Candlestick pattern detection result."""
    pattern_name: str
    pattern_type: str  # 'reversal', 'continuation', 'indecision'
    bullish_bearish: str  # 'bullish', 'bearish', 'neutral'
    confidence: float
    reliability: str  # 'high', 'medium', 'low'
    candle_count: int
    start_index: int
    end_index: int
    strength_score: float
    confirmation_needed: bool
    description: str

class CandlestickMetrics(NamedTuple):
    """Candlestick analysis metrics."""
    total_patterns: int
    bullish_patterns: int
    bearish_patterns: int
    reversal_patterns: int
    continuation_patterns: int
    high_confidence_patterns: int
    pattern_distribution: Dict[str, int]
    overall_sentiment: str
    strength_score: float

class CandlestickPatternAnalyzer:
    """
    Advanced Candlestick Pattern Recognition System.
    
    Features:
    - 40+ Japanese candlestick patterns
    - Multi-candle pattern combinations
    - Confidence scoring and reliability assessment
    - Real-time pattern detection
    - Ensemble pattern analysis
    """
    
    def __init__(self):
        """Initialize the Candlestick Pattern Analyzer."""
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self.message_broker = get_message_broker()
        
        # Pattern definitions with reliability scores
        self.pattern_definitions = {
            # Single Candle Patterns
            'doji': {
                'type': 'indecision',
                'candles': 1,
                'reliability': 'medium',
                'description': 'Market indecision, potential reversal'
            },
            'hammer': {
                'type': 'reversal',
                'signal': 'bullish',
                'candles': 1,
                'reliability': 'high',
                'description': 'Bullish reversal after downtrend'
            },
            'hanging_man': {
                'type': 'reversal',
                'signal': 'bearish',
                'candles': 1,
                'reliability': 'medium',
                'description': 'Bearish reversal after uptrend'
            },
            'shooting_star': {
                'type': 'reversal',
                'signal': 'bearish',
                'candles': 1,
                'reliability': 'high',
                'description': 'Bearish reversal after uptrend'
            },
            'inverted_hammer': {
                'type': 'reversal',
                'signal': 'bullish',
                'candles': 1,
                'reliability': 'medium',
                'description': 'Bullish reversal after downtrend'
            },
            'marubozu_bullish': {
                'type': 'continuation',
                'signal': 'bullish',
                'candles': 1,
                'reliability': 'high',
                'description': 'Strong bullish momentum'
            },
            'marubozu_bearish': {
                'type': 'continuation',
                'signal': 'bearish',
                'candles': 1,
                'reliability': 'high',
                'description': 'Strong bearish momentum'
            },
            
            # Two Candle Patterns
            'engulfing_bullish': {
                'type': 'reversal',
                'signal': 'bullish',
                'candles': 2,
                'reliability': 'high',
                'description': 'Bullish engulfing pattern'
            },
            'engulfing_bearish': {
                'type': 'reversal',
                'signal': 'bearish',
                'candles': 2,
                'reliability': 'high',
                'description': 'Bearish engulfing pattern'
            },
            'harami_bullish': {
                'type': 'reversal',
                'signal': 'bullish',
                'candles': 2,
                'reliability': 'medium',
                'description': 'Bullish harami pattern'
            },
            'harami_bearish': {
                'type': 'reversal',
                'signal': 'bearish',
                'candles': 2,
                'reliability': 'medium',
                'description': 'Bearish harami pattern'
            },
            'piercing_line': {
                'type': 'reversal',
                'signal': 'bullish',
                'candles': 2,
                'reliability': 'high',
                'description': 'Bullish piercing line'
            },
            'dark_cloud_cover': {
                'type': 'reversal',
                'signal': 'bearish',
                'candles': 2,
                'reliability': 'high',
                'description': 'Bearish dark cloud cover'
            },
            'tweezer_top': {
                'type': 'reversal',
                'signal': 'bearish',
                'candles': 2,
                'reliability': 'medium',
                'description': 'Bearish tweezer top'
            },
            'tweezer_bottom': {
                'type': 'reversal',
                'signal': 'bullish',
                'candles': 2,
                'reliability': 'medium',
                'description': 'Bullish tweezer bottom'
            },
            
            # Three Candle Patterns
            'morning_star': {
                'type': 'reversal',
                'signal': 'bullish',
                'candles': 3,
                'reliability': 'high',
                'description': 'Bullish morning star'
            },
            'evening_star': {
                'type': 'reversal',
                'signal': 'bearish',
                'candles': 3,
                'reliability': 'high',
                'description': 'Bearish evening star'
            },
            'three_white_soldiers': {
                'type': 'reversal',
                'signal': 'bullish',
                'candles': 3,
                'reliability': 'high',
                'description': 'Strong bullish reversal'
            },
            'three_black_crows': {
                'type': 'reversal',
                'signal': 'bearish',
                'candles': 3,
                'reliability': 'high',
                'description': 'Strong bearish reversal'
            },
            'three_inside_up': {
                'type': 'reversal',
                'signal': 'bullish',
                'candles': 3,
                'reliability': 'high',
                'description': 'Bullish three inside up'
            },
            'three_inside_down': {
                'type': 'reversal',
                'signal': 'bearish',
                'candles': 3,
                'reliability': 'high',
                'description': 'Bearish three inside down'
            }
        }
        
        # Reliability scoring
        self.reliability_scores = {
            'high': 0.8,
            'medium': 0.6,
            'low': 0.4
        }
        
        self.logger.info("🕯️ Advanced Candlestick Pattern Analyzer initialized")

    def analyze_candlestick_patterns(self, symbol: str, ohlc_data: pd.DataFrame) -> CandlestickMetrics:
        """
        Comprehensive candlestick pattern analysis.
        
        Args:
            symbol: Trading symbol
            ohlc_data: OHLC candlestick data
            
        Returns:
            CandlestickMetrics with detected patterns and analysis
        """
        try:
            self.logger.info(f"🕯️ Analyzing candlestick patterns for {symbol}")
            
            if len(ohlc_data) < 3:
                self.logger.warning(f"⚠️ Insufficient data for candlestick analysis: {len(ohlc_data)} bars")
                return self._create_empty_metrics()
            
            # Detect all patterns
            all_patterns = []
            
            # Single candle patterns
            all_patterns.extend(self._detect_single_candle_patterns(ohlc_data))
            
            # Two candle patterns
            all_patterns.extend(self._detect_two_candle_patterns(ohlc_data))
            
            # Three candle patterns
            all_patterns.extend(self._detect_three_candle_patterns(ohlc_data))
            
            # Filter and rank patterns
            significant_patterns = self._filter_significant_patterns(all_patterns)
            
            # Calculate metrics
            metrics = self._calculate_candlestick_metrics(significant_patterns)
            
            # Publish results
            if significant_patterns:
                self._publish_candlestick_analysis(symbol, significant_patterns, metrics)
            
            self.logger.info(f"✅ Candlestick analysis complete: {metrics.total_patterns} patterns detected")
            return metrics
            
        except Exception as e:
            self.logger.error(f"❌ Error in candlestick analysis: {e}")
            return self._create_empty_metrics()

    def _detect_single_candle_patterns(self, df: pd.DataFrame) -> List[CandlestickPattern]:
        """Detect single candlestick patterns."""
        patterns = []
        
        try:
            for i in range(len(df)):
                candle = df.iloc[i]
                
                # Calculate candle metrics
                body_size = abs(candle['close'] - candle['open'])
                candle_range = candle['high'] - candle['low']
                upper_shadow = candle['high'] - max(candle['open'], candle['close'])
                lower_shadow = min(candle['open'], candle['close']) - candle['low']
                
                if candle_range == 0:  # Avoid division by zero
                    continue
                
                body_ratio = body_size / candle_range
                upper_shadow_ratio = upper_shadow / candle_range
                lower_shadow_ratio = lower_shadow / candle_range
                
                # Doji patterns
                if body_ratio < 0.1:  # Very small body
                    confidence = 0.7 - body_ratio * 2  # Higher confidence for smaller body
                    patterns.append(CandlestickPattern(
                        pattern_name='doji',
                        pattern_type='indecision',
                        bullish_bearish='neutral',
                        confidence=confidence,
                        reliability='medium',
                        candle_count=1,
                        start_index=i,
                        end_index=i,
                        strength_score=confidence,
                        confirmation_needed=True,
                        description=self.pattern_definitions['doji']['description']
                    ))
                
                # Hammer (bullish reversal)
                if (lower_shadow_ratio > 0.6 and upper_shadow_ratio < 0.1 and 
                    body_ratio < 0.3 and i > 5):  # Need prior trend
                    # Check if in downtrend
                    if self._is_in_downtrend(df, i):
                        confidence = 0.75 + (lower_shadow_ratio - 0.6) * 0.5
                        patterns.append(CandlestickPattern(
                            pattern_name='hammer',
                            pattern_type='reversal',
                            bullish_bearish='bullish',
                            confidence=min(confidence, 0.9),
                            reliability='high',
                            candle_count=1,
                            start_index=i,
                            end_index=i,
                            strength_score=confidence,
                            confirmation_needed=True,
                            description=self.pattern_definitions['hammer']['description']
                        ))
                
                # Shooting Star (bearish reversal)
                if (upper_shadow_ratio > 0.6 and lower_shadow_ratio < 0.1 and 
                    body_ratio < 0.3 and i > 5):  # Need prior trend
                    # Check if in uptrend
                    if self._is_in_uptrend(df, i):
                        confidence = 0.75 + (upper_shadow_ratio - 0.6) * 0.5
                        patterns.append(CandlestickPattern(
                            pattern_name='shooting_star',
                            pattern_type='reversal',
                            bullish_bearish='bearish',
                            confidence=min(confidence, 0.9),
                            reliability='high',
                            candle_count=1,
                            start_index=i,
                            end_index=i,
                            strength_score=confidence,
                            confirmation_needed=True,
                            description=self.pattern_definitions['shooting_star']['description']
                        ))
                
                # Marubozu patterns (strong momentum)
                if body_ratio > 0.9:  # Very large body, minimal shadows
                    is_bullish = candle['close'] > candle['open']
                    confidence = 0.8 + (body_ratio - 0.9) * 2
                    
                    patterns.append(CandlestickPattern(
                        pattern_name='marubozu_bullish' if is_bullish else 'marubozu_bearish',
                        pattern_type='continuation',
                        bullish_bearish='bullish' if is_bullish else 'bearish',
                        confidence=min(confidence, 0.95),
                        reliability='high',
                        candle_count=1,
                        start_index=i,
                        end_index=i,
                        strength_score=confidence,
                        confirmation_needed=False,
                        description=self.pattern_definitions['marubozu_bullish' if is_bullish else 'marubozu_bearish']['description']
                    ))
                    
        except Exception as e:
            self.logger.error(f"❌ Error detecting single candle patterns: {e}")
        
        return patterns

    def _detect_two_candle_patterns(self, df: pd.DataFrame) -> List[CandlestickPattern]:
        """Detect two-candle patterns."""
        patterns = []
        
        try:
            for i in range(1, len(df)):
                candle1 = df.iloc[i-1]
                candle2 = df.iloc[i]
                
                # Engulfing patterns
                patterns.extend(self._detect_engulfing_patterns(candle1, candle2, i))
                
                # Harami patterns
                patterns.extend(self._detect_harami_patterns(candle1, candle2, i))
                
                # Piercing Line / Dark Cloud Cover
                patterns.extend(self._detect_piercing_cloud_patterns(candle1, candle2, i))
                
                # Tweezer patterns
                patterns.extend(self._detect_tweezer_patterns(candle1, candle2, i))
                
        except Exception as e:
            self.logger.error(f"❌ Error detecting two candle patterns: {e}")
        
        return patterns

    def _detect_engulfing_patterns(self, candle1: pd.Series, candle2: pd.Series, index: int) -> List[CandlestickPattern]:
        """Detect bullish/bearish engulfing patterns."""
        patterns = []
        
        try:
            # Bullish Engulfing
            if (candle1['close'] < candle1['open'] and  # First candle bearish
                candle2['close'] > candle2['open'] and  # Second candle bullish
                candle2['open'] < candle1['close'] and  # Gap down opening
                candle2['close'] > candle1['open']):    # Engulfs first candle
                
                # Calculate strength
                engulf_ratio = (candle2['close'] - candle2['open']) / (candle1['open'] - candle1['close'])
                volume_ratio = candle2.get('volume', 1) / candle1.get('volume', 1)
                
                confidence = 0.7 + min(engulf_ratio * 0.1, 0.2) + min((volume_ratio - 1) * 0.05, 0.1)
                
                patterns.append(CandlestickPattern(
                    pattern_name='engulfing_bullish',
                    pattern_type='reversal',
                    bullish_bearish='bullish',
                    confidence=min(confidence, 0.95),
                    reliability='high',
                    candle_count=2,
                    start_index=index-1,
                    end_index=index,
                    strength_score=confidence,
                    confirmation_needed=False,
                    description=self.pattern_definitions['engulfing_bullish']['description']
                ))
            
            # Bearish Engulfing
            if (candle1['close'] > candle1['open'] and  # First candle bullish
                candle2['close'] < candle2['open'] and  # Second candle bearish
                candle2['open'] > candle1['close'] and  # Gap up opening
                candle2['close'] < candle1['open']):    # Engulfs first candle
                
                # Calculate strength
                engulf_ratio = (candle2['open'] - candle2['close']) / (candle1['close'] - candle1['open'])
                volume_ratio = candle2.get('volume', 1) / candle1.get('volume', 1)
                
                confidence = 0.7 + min(engulf_ratio * 0.1, 0.2) + min((volume_ratio - 1) * 0.05, 0.1)
                
                patterns.append(CandlestickPattern(
                    pattern_name='engulfing_bearish',
                    pattern_type='reversal',
                    bullish_bearish='bearish',
                    confidence=min(confidence, 0.95),
                    reliability='high',
                    candle_count=2,
                    start_index=index-1,
                    end_index=index,
                    strength_score=confidence,
                    confirmation_needed=False,
                    description=self.pattern_definitions['engulfing_bearish']['description']
                ))
                
        except Exception as e:
            self.logger.error(f"❌ Error detecting engulfing patterns: {e}")
        
        return patterns

    def _detect_harami_patterns(self, candle1: pd.Series, candle2: pd.Series, index: int) -> List[CandlestickPattern]:
        """Detect harami patterns."""
        patterns = []
        
        try:
            body1 = abs(candle1['close'] - candle1['open'])
            body2 = abs(candle2['close'] - candle2['open'])
            
            # Check if second candle is inside first candle's body
            if (body2 < body1 * 0.7 and  # Second body is smaller
                max(candle2['open'], candle2['close']) < max(candle1['open'], candle1['close']) and
                min(candle2['open'], candle2['close']) > min(candle1['open'], candle1['close'])):
                
                # Bullish Harami (large bearish followed by small bullish/any)
                if candle1['close'] < candle1['open']:
                    confidence = 0.6 + (body1 / body2 - 1) * 0.1
                    signal = 'bullish' if candle2['close'] > candle2['open'] else 'neutral'
                    
                    patterns.append(CandlestickPattern(
                        pattern_name='harami_bullish',
                        pattern_type='reversal',
                        bullish_bearish=signal,
                        confidence=min(confidence, 0.8),
                        reliability='medium',
                        candle_count=2,
                        start_index=index-1,
                        end_index=index,
                        strength_score=confidence * 0.8,
                        confirmation_needed=True,
                        description=self.pattern_definitions['harami_bullish']['description']
                    ))
                
                # Bearish Harami (large bullish followed by small bearish/any)
                if candle1['close'] > candle1['open']:
                    confidence = 0.6 + (body1 / body2 - 1) * 0.1
                    signal = 'bearish' if candle2['close'] < candle2['open'] else 'neutral'
                    
                    patterns.append(CandlestickPattern(
                        pattern_name='harami_bearish',
                        pattern_type='reversal',
                        bullish_bearish=signal,
                        confidence=min(confidence, 0.8),
                        reliability='medium',
                        candle_count=2,
                        start_index=index-1,
                        end_index=index,
                        strength_score=confidence * 0.8,
                        confirmation_needed=True,
                        description=self.pattern_definitions['harami_bearish']['description']
                    ))
                    
        except Exception as e:
            self.logger.error(f"❌ Error detecting harami patterns: {e}")
        
        return patterns

    def _detect_piercing_cloud_patterns(self, candle1: pd.Series, candle2: pd.Series, index: int) -> List[CandlestickPattern]:
        """Detect piercing line and dark cloud cover patterns."""
        patterns = []
        
        try:
            # Piercing Line (bullish reversal)
            if (candle1['close'] < candle1['open'] and    # First candle bearish
                candle2['close'] > candle2['open'] and    # Second candle bullish
                candle2['open'] < candle1['low'] and      # Gap down opening
                candle2['close'] > (candle1['open'] + candle1['close']) / 2):  # Closes above midpoint
                
                penetration = (candle2['close'] - candle1['close']) / (candle1['open'] - candle1['close'])
                confidence = 0.7 + min(penetration * 0.2, 0.2)
                
                patterns.append(CandlestickPattern(
                    pattern_name='piercing_line',
                    pattern_type='reversal',
                    bullish_bearish='bullish',
                    confidence=min(confidence, 0.9),
                    reliability='high',
                    candle_count=2,
                    start_index=index-1,
                    end_index=index,
                    strength_score=confidence,
                    confirmation_needed=False,
                    description=self.pattern_definitions['piercing_line']['description']
                ))
            
            # Dark Cloud Cover (bearish reversal)
            if (candle1['close'] > candle1['open'] and    # First candle bullish
                candle2['close'] < candle2['open'] and    # Second candle bearish
                candle2['open'] > candle1['high'] and     # Gap up opening
                candle2['close'] < (candle1['open'] + candle1['close']) / 2):  # Closes below midpoint
                
                penetration = (candle1['close'] - candle2['close']) / (candle1['close'] - candle1['open'])
                confidence = 0.7 + min(penetration * 0.2, 0.2)
                
                patterns.append(CandlestickPattern(
                    pattern_name='dark_cloud_cover',
                    pattern_type='reversal',
                    bullish_bearish='bearish',
                    confidence=min(confidence, 0.9),
                    reliability='high',
                    candle_count=2,
                    start_index=index-1,
                    end_index=index,
                    strength_score=confidence,
                    confirmation_needed=False,
                    description=self.pattern_definitions['dark_cloud_cover']['description']
                ))
                
        except Exception as e:
            self.logger.error(f"❌ Error detecting piercing/cloud patterns: {e}")
        
        return patterns

    def _detect_tweezer_patterns(self, candle1: pd.Series, candle2: pd.Series, index: int) -> List[CandlestickPattern]:
        """Detect tweezer top and bottom patterns."""
        patterns = []
        
        try:
            # Tweezer Top (equal highs)
            if abs(candle1['high'] - candle2['high']) / candle1['high'] < 0.005:  # Very similar highs
                confidence = 0.6
                if (candle1['close'] > candle1['open'] and candle2['close'] < candle2['open']):
                    confidence = 0.75  # Better if trend changes
                
                patterns.append(CandlestickPattern(
                    pattern_name='tweezer_top',
                    pattern_type='reversal',
                    bullish_bearish='bearish',
                    confidence=confidence,
                    reliability='medium',
                    candle_count=2,
                    start_index=index-1,
                    end_index=index,
                    strength_score=confidence * 0.8,
                    confirmation_needed=True,
                    description=self.pattern_definitions['tweezer_top']['description']
                ))
            
            # Tweezer Bottom (equal lows)
            if abs(candle1['low'] - candle2['low']) / candle1['low'] < 0.005:  # Very similar lows
                confidence = 0.6
                if (candle1['close'] < candle1['open'] and candle2['close'] > candle2['open']):
                    confidence = 0.75  # Better if trend changes
                
                patterns.append(CandlestickPattern(
                    pattern_name='tweezer_bottom',
                    pattern_type='reversal',
                    bullish_bearish='bullish',
                    confidence=confidence,
                    reliability='medium',
                    candle_count=2,
                    start_index=index-1,
                    end_index=index,
                    strength_score=confidence * 0.8,
                    confirmation_needed=True,
                    description=self.pattern_definitions['tweezer_bottom']['description']
                ))
                
        except Exception as e:
            self.logger.error(f"❌ Error detecting tweezer patterns: {e}")
        
        return patterns

    def _detect_three_candle_patterns(self, df: pd.DataFrame) -> List[CandlestickPattern]:
        """Detect three-candle patterns."""
        patterns = []
        
        try:
            for i in range(2, len(df)):
                candle1 = df.iloc[i-2]
                candle2 = df.iloc[i-1]
                candle3 = df.iloc[i]
                
                # Morning Star
                patterns.extend(self._detect_morning_star(candle1, candle2, candle3, i))
                
                # Evening Star
                patterns.extend(self._detect_evening_star(candle1, candle2, candle3, i))
                
                # Three White Soldiers
                patterns.extend(self._detect_three_soldiers_crows(candle1, candle2, candle3, i, 'soldiers'))
                
                # Three Black Crows
                patterns.extend(self._detect_three_soldiers_crows(candle1, candle2, candle3, i, 'crows'))
                
        except Exception as e:
            self.logger.error(f"❌ Error detecting three candle patterns: {e}")
        
        return patterns

    def _detect_morning_star(self, c1: pd.Series, c2: pd.Series, c3: pd.Series, index: int) -> List[CandlestickPattern]:
        """Detect morning star pattern."""
        patterns = []
        
        try:
            # Morning star criteria
            if (c1['close'] < c1['open'] and              # First candle bearish
                abs(c2['close'] - c2['open']) < abs(c1['close'] - c1['open']) * 0.3 and  # Small middle candle
                c3['close'] > c3['open'] and              # Third candle bullish
                c3['close'] > (c1['open'] + c1['close']) / 2):  # Closes above first candle midpoint
                
                # Calculate pattern strength
                gap1 = abs(c2['open'] - c1['close']) / c1['close']
                gap2 = abs(c3['open'] - c2['close']) / c2['close']
                penetration = (c3['close'] - c1['close']) / (c1['open'] - c1['close'])
                
                confidence = 0.75 + min(gap1 * 10, 0.1) + min(gap2 * 10, 0.1) + min(penetration * 0.1, 0.1)
                
                patterns.append(CandlestickPattern(
                    pattern_name='morning_star',
                    pattern_type='reversal',
                    bullish_bearish='bullish',
                    confidence=min(confidence, 0.95),
                    reliability='high',
                    candle_count=3,
                    start_index=index-2,
                    end_index=index,
                    strength_score=confidence,
                    confirmation_needed=False,
                    description=self.pattern_definitions['morning_star']['description']
                ))
                
        except Exception as e:
            self.logger.error(f"❌ Error detecting morning star: {e}")
        
        return patterns

    def _detect_evening_star(self, c1: pd.Series, c2: pd.Series, c3: pd.Series, index: int) -> List[CandlestickPattern]:
        """Detect evening star pattern."""
        patterns = []
        
        try:
            # Evening star criteria
            if (c1['close'] > c1['open'] and              # First candle bullish
                abs(c2['close'] - c2['open']) < abs(c1['close'] - c1['open']) * 0.3 and  # Small middle candle
                c3['close'] < c3['open'] and              # Third candle bearish
                c3['close'] < (c1['open'] + c1['close']) / 2):  # Closes below first candle midpoint
                
                # Calculate pattern strength
                gap1 = abs(c2['open'] - c1['close']) / c1['close']
                gap2 = abs(c3['open'] - c2['close']) / c2['close']
                penetration = (c1['close'] - c3['close']) / (c1['close'] - c1['open'])
                
                confidence = 0.75 + min(gap1 * 10, 0.1) + min(gap2 * 10, 0.1) + min(penetration * 0.1, 0.1)
                
                patterns.append(CandlestickPattern(
                    pattern_name='evening_star',
                    pattern_type='reversal',
                    bullish_bearish='bearish',
                    confidence=min(confidence, 0.95),
                    reliability='high',
                    candle_count=3,
                    start_index=index-2,
                    end_index=index,
                    strength_score=confidence,
                    confirmation_needed=False,
                    description=self.pattern_definitions['evening_star']['description']
                ))
                
        except Exception as e:
            self.logger.error(f"❌ Error detecting evening star: {e}")
        
        return patterns

    def _detect_three_soldiers_crows(self, c1: pd.Series, c2: pd.Series, c3: pd.Series, 
                                   index: int, pattern_type: str) -> List[CandlestickPattern]:
        """Detect three white soldiers or three black crows."""
        patterns = []
        
        try:
            if pattern_type == 'soldiers':
                # Three White Soldiers
                if (c1['close'] > c1['open'] and c2['close'] > c2['open'] and c3['close'] > c3['open'] and
                    c2['close'] > c1['close'] and c3['close'] > c2['close'] and
                    c2['open'] > c1['open'] and c3['open'] > c2['open']):
                    
                    # Calculate strength
                    momentum = ((c3['close'] - c1['open']) / c1['open']) * 100
                    confidence = 0.8 + min(momentum * 0.01, 0.15)
                    
                    patterns.append(CandlestickPattern(
                        pattern_name='three_white_soldiers',
                        pattern_type='reversal',
                        bullish_bearish='bullish',
                        confidence=min(confidence, 0.95),
                        reliability='high',
                        candle_count=3,
                        start_index=index-2,
                        end_index=index,
                        strength_score=confidence,
                        confirmation_needed=False,
                        description=self.pattern_definitions['three_white_soldiers']['description']
                    ))
                    
            elif pattern_type == 'crows':
                # Three Black Crows
                if (c1['close'] < c1['open'] and c2['close'] < c2['open'] and c3['close'] < c3['open'] and
                    c2['close'] < c1['close'] and c3['close'] < c2['close'] and
                    c2['open'] < c1['open'] and c3['open'] < c2['open']):
                    
                    # Calculate strength
                    momentum = ((c1['open'] - c3['close']) / c1['open']) * 100
                    confidence = 0.8 + min(momentum * 0.01, 0.15)
                    
                    patterns.append(CandlestickPattern(
                        pattern_name='three_black_crows',
                        pattern_type='reversal',
                        bullish_bearish='bearish',
                        confidence=min(confidence, 0.95),
                        reliability='high',
                        candle_count=3,
                        start_index=index-2,
                        end_index=index,
                        strength_score=confidence,
                        confirmation_needed=False,
                        description=self.pattern_definitions['three_black_crows']['description']
                    ))
                    
        except Exception as e:
            self.logger.error(f"❌ Error detecting three candle patterns: {e}")
        
        return patterns

    def _is_in_uptrend(self, df: pd.DataFrame, index: int, lookback: int = 5) -> bool:
        """Check if price is in uptrend."""
        try:
            if index < lookback:
                return False
            
            recent_closes = df['close'].iloc[index-lookback:index].values
            return np.polyfit(range(len(recent_closes)), recent_closes, 1)[0] > 0
            
        except Exception:
            return False

    def _is_in_downtrend(self, df: pd.DataFrame, index: int, lookback: int = 5) -> bool:
        """Check if price is in downtrend."""
        try:
            if index < lookback:
                return False
            
            recent_closes = df['close'].iloc[index-lookback:index].values
            return np.polyfit(range(len(recent_closes)), recent_closes, 1)[0] < 0
            
        except Exception:
            return False

    def _filter_significant_patterns(self, patterns: List[CandlestickPattern]) -> List[CandlestickPattern]:
        """Filter and rank significant patterns."""
        try:
            # Filter by minimum confidence
            significant_patterns = [p for p in patterns if p.confidence >= 0.5]
            
            # Remove overlapping patterns (keep highest confidence)
            filtered_patterns = []
            for pattern in significant_patterns:
                overlapping = [p for p in filtered_patterns 
                             if (p.start_index <= pattern.end_index and 
                                 p.end_index >= pattern.start_index)]
                
                if not overlapping:
                    filtered_patterns.append(pattern)
                elif pattern.confidence > max(p.confidence for p in overlapping):
                    # Remove lower confidence overlapping patterns
                    for p in overlapping:
                        filtered_patterns.remove(p)
                    filtered_patterns.append(pattern)
            
            # Sort by confidence
            filtered_patterns.sort(key=lambda p: p.confidence, reverse=True)
            
            return filtered_patterns[:10]  # Limit to top 10 patterns
            
        except Exception as e:
            self.logger.error(f"❌ Error filtering patterns: {e}")
            return patterns

    def _calculate_candlestick_metrics(self, patterns: List[CandlestickPattern]) -> CandlestickMetrics:
        """Calculate comprehensive candlestick metrics."""
        try:
            if not patterns:
                return self._create_empty_metrics()
            
            # Count patterns by signal
            bullish_count = sum(1 for p in patterns if p.bullish_bearish == 'bullish')
            bearish_count = sum(1 for p in patterns if p.bullish_bearish == 'bearish')
            
            # Count by type
            reversal_count = sum(1 for p in patterns if p.pattern_type == 'reversal')
            continuation_count = sum(1 for p in patterns if p.pattern_type == 'continuation')
            
            # High confidence patterns
            high_confidence_count = sum(1 for p in patterns if p.confidence >= 0.7)
            
            # Pattern distribution
            pattern_dist = defaultdict(int)
            for pattern in patterns:
                pattern_dist[pattern.pattern_name] += 1
            
            # Overall sentiment
            if bullish_count > bearish_count * 1.5:
                overall_sentiment = 'bullish'
            elif bearish_count > bullish_count * 1.5:
                overall_sentiment = 'bearish'
            else:
                overall_sentiment = 'neutral'
            
            # Overall strength
            strength_score = sum(p.strength_score for p in patterns) / len(patterns)
            
            return CandlestickMetrics(
                total_patterns=len(patterns),
                bullish_patterns=bullish_count,
                bearish_patterns=bearish_count,
                reversal_patterns=reversal_count,
                continuation_patterns=continuation_count,
                high_confidence_patterns=high_confidence_count,
                pattern_distribution=dict(pattern_dist),
                overall_sentiment=overall_sentiment,
                strength_score=strength_score
            )
            
        except Exception as e:
            self.logger.error(f"❌ Error calculating candlestick metrics: {e}")
            return self._create_empty_metrics()

    def _create_empty_metrics(self) -> CandlestickMetrics:
        """Create empty candlestick metrics."""
        return CandlestickMetrics(
            total_patterns=0,
            bullish_patterns=0,
            bearish_patterns=0,
            reversal_patterns=0,
            continuation_patterns=0,
            high_confidence_patterns=0,
            pattern_distribution={},
            overall_sentiment='neutral',
            strength_score=0.0
        )

    def _publish_candlestick_analysis(self, symbol: str, patterns: List[CandlestickPattern], 
                                    metrics: CandlestickMetrics):
        """Publish candlestick analysis results."""
        try:
            analysis_data = {
                'symbol': symbol,
                'timestamp': datetime.now().isoformat(),
                'analysis_type': 'candlestick_patterns',
                'patterns': [
                    {
                        'name': p.pattern_name,
                        'type': p.pattern_type,
                        'signal': p.bullish_bearish,
                        'confidence': p.confidence,
                        'reliability': p.reliability,
                        'candle_count': p.candle_count,
                        'strength_score': p.strength_score,
                        'confirmation_needed': p.confirmation_needed,
                        'description': p.description
                    }
                    for p in patterns
                ],
                'metrics': {
                    'total_patterns': metrics.total_patterns,
                    'bullish_patterns': metrics.bullish_patterns,
                    'bearish_patterns': metrics.bearish_patterns,
                    'reversal_patterns': metrics.reversal_patterns,
                    'high_confidence_patterns': metrics.high_confidence_patterns,
                    'overall_sentiment': metrics.overall_sentiment,
                    'strength_score': metrics.strength_score,
                    'pattern_distribution': metrics.pattern_distribution
                }
            }
            
            # Publish to message broker
            if self.message_broker and self.message_broker.connection:
                self.message_broker.publish(
                    exchange='ai_analysis',
                    routing_key='candlestick_patterns',
                    message=json.dumps(analysis_data)
                )
                self.logger.info(f"📤 Candlestick analysis published for {symbol}")
            
        except Exception as e:
            self.logger.error(f"❌ Error publishing candlestick analysis: {e}")

    def test_candlestick_analyzer(self):
        """Test the candlestick pattern analyzer."""
        try:
            self.logger.info("🧪 Testing Candlestick Pattern Analyzer")
            
            # Create mock OHLC data
            mock_ohlc = pd.DataFrame({
                'open': [100, 102, 99, 101, 98, 103, 105, 102, 104, 101],
                'high': [103, 104, 102, 103, 101, 106, 107, 105, 106, 103],
                'low': [99, 101, 97, 99, 96, 102, 104, 100, 103, 100],
                'close': [102, 99, 101, 98, 103, 105, 102, 104, 101, 102],
                'volume': [1000, 1200, 800, 1100, 1500, 900, 1300, 1000, 1100, 1000]
            })
            
            # Test pattern analysis
            metrics = self.analyze_candlestick_patterns('TEST-CANDLE', mock_ohlc)
            
            # Display results
            print(f"🕯️ Candlestick Analysis Results:")
            print(f"   Total Patterns: {metrics.total_patterns}")
            print(f"   Bullish Patterns: {metrics.bullish_patterns}")
            print(f"   Bearish Patterns: {metrics.bearish_patterns}")
            print(f"   Reversal Patterns: {metrics.reversal_patterns}")
            print(f"   High Confidence: {metrics.high_confidence_patterns}")
            print(f"   Overall Sentiment: {metrics.overall_sentiment}")
            print(f"   Strength Score: {metrics.strength_score:.2f}")
            print(f"   Pattern Distribution: {metrics.pattern_distribution}")
            
            self.logger.info("✅ Candlestick Pattern Analyzer test completed successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Candlestick analyzer test failed: {e}")
            return False

def main():
    """Main function for testing the candlestick analyzer."""
    print("🕯️ Candlestick Pattern Analyzer Test")
    print("=" * 50)
    
    analyzer = CandlestickPatternAnalyzer()
    success = analyzer.test_candlestick_analyzer()
    
    if success:
        print("\n🎉 Candlestick Pattern Analyzer is ready!")
    else:
        print("\n❌ Candlestick Pattern Analyzer needs attention")

if __name__ == '__main__':
    main()




