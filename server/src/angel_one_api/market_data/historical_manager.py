"""
Angel One Historical Data Manager
================================

Historical data management for Angel One SmartAPI.
Integrates with getCandleData method for comprehensive historical analysis.
"""

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent))

import asyncio
from typing import Dict, List, Optional, Any
# Import new Angel One logger
from logger import get_service_logger
from datetime import datetime, UTC, timedelta

from methods.get_candle_data import get_candle_data

logger = get_service_logger("historical_manager")

class HistoricalDataError(Exception):
    """Raised when historical data operations fail."""
    pass

class HistoricalManager:
    """Comprehensive historical data manager."""
    
    def __init__(self, auth_manager=None, rate_controller=None):
        self.auth_manager = auth_manager
        self.rate_controller = rate_controller
        self._cache = {}
        self._cache_ttl = 300  # 5 minutes
    
    async def get_historical_data(self, symbol: str, exchange: str = "NSE", 
                                 interval: str = "ONE_DAY", from_date: str = None, 
                                 to_date: str = None) -> Dict[str, Any]:
        """
        Get comprehensive historical data for a symbol.
        
        Args:
            symbol: Trading symbol
            exchange: Exchange (NSE/BSE)
            interval: Time interval (ONE_MINUTE, FIVE_MINUTE, ONE_DAY, etc.)
            from_date: Start date (YYYY-MM-DD)
            to_date: End date (YYYY-MM-DD)
            
        Returns:
            Dict: Historical data with analysis
        """
        try:
            # Default dates if not provided
            if not to_date:
                to_date = datetime.now().strftime("%Y-%m-%d")
            if not from_date:
                from_date = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
            
            # Check cache
            cache_key = f"{symbol}_{exchange}_{interval}_{from_date}_{to_date}"
            if cache_key in self._cache:
                cache_data = self._cache[cache_key]
                if (datetime.now(UTC) - cache_data['timestamp']).seconds < self._cache_ttl:
                    logger.info(f"📊 Using cached historical data for {symbol}")
                    return cache_data['data']
            
            # Get raw candle data
            candle_result = await get_candle_data(
                exchange=exchange,
                symbol_token="",  # Will be resolved by get_candle_data
                symbol=symbol,
                interval=interval,
                from_date=from_date,
                to_date=to_date
            )
            
            if not candle_result['success']:
                raise HistoricalDataError(f"Failed to get candle data: {candle_result.get('error')}")
            
            # Enhanced analysis
            analyzed_data = await self._analyze_historical_data(candle_result['data'], symbol)
            
            # Cache result
            self._cache[cache_key] = {
                'data': analyzed_data,
                'timestamp': datetime.now(UTC)
            }
            
            logger.info(f"✅ Historical data retrieved for {symbol}: {len(candle_result['data'])} candles")
            
            return analyzed_data
            
        except Exception as e:
            logger.error(f"❌ Historical data fetch failed for {symbol}: {e}")
            raise HistoricalDataError(f"Historical data fetch failed: {e}")
    
    async def _analyze_historical_data(self, candle_data: List[Dict], symbol: str) -> Dict[str, Any]:
        """Analyze historical candle data."""
        try:
            if not candle_data:
                return {
                    'success': False,
                    'symbol': symbol,
                    'error': 'No candle data available'
                }
            
            # Basic statistics
            closes = [float(candle['close']) for candle in candle_data]
            highs = [float(candle['high']) for candle in candle_data]
            lows = [float(candle['low']) for candle in candle_data]
            volumes = [int(candle['volume']) for candle in candle_data]
            
            # Calculate technical indicators
            sma_20 = self._calculate_sma(closes, 20)
            volatility = self._calculate_volatility(closes)
            trend = self._identify_trend(closes)
            support_resistance = self._find_support_resistance(highs, lows)
            
            analysis = {
                'success': True,
                'symbol': symbol,
                'data_points': len(candle_data),
                'raw_candles': candle_data,
                'price_analysis': {
                    'current_price': closes[-1] if closes else 0,
                    'highest_price': max(highs) if highs else 0,
                    'lowest_price': min(lows) if lows else 0,
                    'price_change': closes[-1] - closes[0] if len(closes) > 1 else 0,
                    'price_change_pct': ((closes[-1] - closes[0]) / closes[0] * 100) if len(closes) > 1 and closes[0] > 0 else 0
                },
                'volume_analysis': {
                    'avg_volume': sum(volumes) / len(volumes) if volumes else 0,
                    'max_volume': max(volumes) if volumes else 0,
                    'volume_trend': 'INCREASING' if len(volumes) > 1 and volumes[-1] > volumes[0] else 'DECREASING'
                },
                'technical_indicators': {
                    'sma_20': sma_20,
                    'volatility': volatility,
                    'trend': trend,
                    'support_level': support_resistance['support'],
                    'resistance_level': support_resistance['resistance']
                },
                'trading_signals': self._generate_trading_signals(closes, sma_20, trend),
                'timestamp': datetime.now(UTC).isoformat()
            }
            
            return analysis
            
        except Exception as e:
            logger.error(f"❌ Historical data analysis failed: {e}")
            return {
                'success': False,
                'symbol': symbol,
                'error': str(e)
            }
    
    def _calculate_sma(self, prices: List[float], period: int) -> float:
        """Calculate Simple Moving Average."""
        if len(prices) < period:
            return 0
        return sum(prices[-period:]) / period
    
    def _calculate_volatility(self, prices: List[float]) -> float:
        """Calculate price volatility."""
        if len(prices) < 2:
            return 0
        
        returns = [(prices[i] - prices[i-1]) / prices[i-1] for i in range(1, len(prices)) if prices[i-1] > 0]
        if not returns:
            return 0
        
        avg_return = sum(returns) / len(returns)
        variance = sum((r - avg_return) ** 2 for r in returns) / len(returns)
        return variance ** 0.5 * 100  # Percentage volatility
    
    def _identify_trend(self, prices: List[float]) -> str:
        """Identify price trend."""
        if len(prices) < 3:
            return 'INSUFFICIENT_DATA'
        
        recent_avg = sum(prices[-3:]) / 3
        earlier_avg = sum(prices[:3]) / 3
        
        if recent_avg > earlier_avg * 1.02:
            return 'UPTREND'
        elif recent_avg < earlier_avg * 0.98:
            return 'DOWNTREND'
        else:
            return 'SIDEWAYS'
    
    def _find_support_resistance(self, highs: List[float], lows: List[float]) -> Dict[str, float]:
        """Find basic support and resistance levels."""
        if not highs or not lows:
            return {'support': 0, 'resistance': 0}
        
        # Simple approach: use recent averages
        recent_highs = highs[-10:] if len(highs) >= 10 else highs
        recent_lows = lows[-10:] if len(lows) >= 10 else lows
        
        resistance = sum(recent_highs) / len(recent_highs)
        support = sum(recent_lows) / len(recent_lows)
        
        return {'support': support, 'resistance': resistance}
    
    def _generate_trading_signals(self, prices: List[float], sma: float, trend: str) -> Dict[str, Any]:
        """Generate basic trading signals."""
        if not prices or sma == 0:
            return {'signal': 'NO_SIGNAL', 'strength': 0}
        
        current_price = prices[-1]
        
        # Simple signal generation
        if current_price > sma and trend == 'UPTREND':
            return {'signal': 'BUY', 'strength': 75, 'reason': 'Price above SMA in uptrend'}
        elif current_price < sma and trend == 'DOWNTREND':
            return {'signal': 'SELL', 'strength': 75, 'reason': 'Price below SMA in downtrend'}
        elif abs(current_price - sma) / sma < 0.02:  # Within 2% of SMA
            return {'signal': 'HOLD', 'strength': 50, 'reason': 'Price near SMA'}
        else:
            return {'signal': 'WAIT', 'strength': 25, 'reason': 'Mixed signals'}
    
    async def get_intraday_data(self, symbol: str, exchange: str = "NSE") -> Dict[str, Any]:
        """Get intraday historical data."""
        today = datetime.now().strftime("%Y-%m-%d")
        return await self.get_historical_data(
            symbol=symbol,
            exchange=exchange,
            interval="FIVE_MINUTE",
            from_date=today,
            to_date=today
        )
    
    async def get_weekly_data(self, symbol: str, exchange: str = "NSE") -> Dict[str, Any]:
        """Get weekly historical data."""
        end_date = datetime.now().strftime("%Y-%m-%d")
        start_date = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
        return await self.get_historical_data(
            symbol=symbol,
            exchange=exchange,
            interval="ONE_DAY",
            from_date=start_date,
            to_date=end_date
        )
    
    async def get_monthly_data(self, symbol: str, exchange: str = "NSE") -> Dict[str, Any]:
        """Get monthly historical data."""
        end_date = datetime.now().strftime("%Y-%m-%d")
        start_date = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
        return await self.get_historical_data(
            symbol=symbol,
            exchange=exchange,
            interval="ONE_DAY",
            from_date=start_date,
            to_date=end_date
        )
    
    def clear_cache(self):
        """Clear historical data cache."""
        self._cache.clear()
        logger.info("🧹 Historical data cache cleared")
