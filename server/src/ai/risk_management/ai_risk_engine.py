"""
AI-Enhanced Risk Engine
Advanced AI-powered risk management with dynamic adjustment, predictive modeling,
and intelligent decision making for algorithmic trading.
"""

import sys
import os
import json
import logging
import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, timedelta
import threading
from dataclasses import dataclass

# Add the project root directory to the Python path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..', '..'))
sys.path.append(PROJECT_ROOT)

from server.src.core.message_broker import get_message_broker

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class RiskMetrics:
    """Data class for risk metrics."""
    portfolio_risk: float
    position_risk: float
    volatility_score: float
    correlation_risk: float
    drawdown_risk: float
    confidence_score: float
    recommendation: str

@dataclass
class MarketRegime:
    """Data class for market regime detection."""
    regime: str  # 'trending', 'ranging', 'volatile', 'stable'
    confidence: float
    volatility_level: str  # 'low', 'medium', 'high', 'extreme'
    trend_strength: float
    regime_change_probability: float

class AIRiskEngine:
    """
    AI-Enhanced Risk Engine for intelligent risk management.
    
    Features:
    - Dynamic risk parameter adjustment based on market conditions
    - Predictive risk modeling using AI/ML algorithms
    - Market regime detection and adaptation
    - Real-time risk assessment with confidence scoring
    - Portfolio optimization recommendations
    """
    
    def __init__(self):
        """Initialize the AI Risk Engine."""
        self.message_broker = get_message_broker()
        self.is_running = False
        self.analysis_thread = None
        
        # AI model parameters (will be enhanced with actual ML models)
        self.base_risk_parameters = {
            'max_portfolio_risk': 0.02,  # 2%
            'max_position_size': 0.10,   # 10%
            'max_daily_loss': 0.05,      # 5%
            'max_correlation': 0.70,     # 70%
        }
        
        # Dynamic risk adjustments based on market conditions
        self.regime_adjustments = {
            'trending_low_vol': {'risk_multiplier': 1.2, 'position_multiplier': 1.1},
            'trending_high_vol': {'risk_multiplier': 0.8, 'position_multiplier': 0.9},
            'ranging_low_vol': {'risk_multiplier': 0.9, 'position_multiplier': 1.0},
            'ranging_high_vol': {'risk_multiplier': 0.6, 'position_multiplier': 0.8},
            'volatile_extreme': {'risk_multiplier': 0.4, 'position_multiplier': 0.6}
        }
        
        # Historical data for learning (will be populated from MongoDB)
        self.historical_trades = []
        self.market_data_cache = {}
        self.correlation_matrix = None
        
        logger.info("🧠 AI Risk Engine initialized successfully")
    
    def analyze_market_regime(self, symbol: str, market_data: Dict[str, Any]) -> MarketRegime:
        """
        Analyze current market regime using AI algorithms.
        
        Args:
            symbol: Trading symbol
            market_data: Market data including price, volume, indicators
            
        Returns:
            MarketRegime: Detected market regime with confidence
        """
        try:
            # Extract relevant data
            prices = market_data.get('prices', [])
            volumes = market_data.get('volumes', [])
            
            if len(prices) < 20:
                logger.warning(f"⚠️ Insufficient data for regime analysis: {symbol}")
                return MarketRegime(
                    regime='unknown',
                    confidence=0.0,
                    volatility_level='medium',
                    trend_strength=0.0,
                    regime_change_probability=0.5
                )
            
            # Calculate key metrics
            price_series = pd.Series(prices)
            returns = price_series.pct_change().dropna()
            
            # Volatility analysis
            volatility = returns.std() * np.sqrt(252)  # Annualized volatility
            volatility_level = self._classify_volatility(volatility)
            
            # Trend analysis
            sma_20 = price_series.rolling(20).mean().iloc[-1]
            sma_50 = price_series.rolling(50).mean().iloc[-1] if len(prices) >= 50 else sma_20
            current_price = prices[-1]
            
            trend_strength = self._calculate_trend_strength(price_series)
            
            # Regime detection logic (simplified AI logic - will be enhanced with ML models)
            if trend_strength > 0.7:
                regime = 'trending'
            elif trend_strength < 0.3:
                regime = 'ranging'
            else:
                regime = 'transitional'
            
            # Combine regime with volatility
            regime_key = f"{regime}_{volatility_level}_vol"
            
            # Calculate confidence based on data quality and consistency
            confidence = min(1.0, len(prices) / 100.0)  # More data = higher confidence
            
            # Regime change probability (simplified)
            price_momentum = (current_price - sma_20) / sma_20
            regime_change_probability = abs(price_momentum) * 0.5
            
            regime_info = MarketRegime(
                regime=regime,
                confidence=confidence,
                volatility_level=volatility_level,
                trend_strength=trend_strength,
                regime_change_probability=min(1.0, regime_change_probability)
            )
            
            logger.info(f"📊 Market regime for {symbol}: {regime} ({volatility_level} vol, {confidence:.2f} confidence)")
            
            # Publish regime analysis to message broker
            if self.message_broker.is_connected:
                self.message_broker.publish_ai_analysis('regime', symbol, {
                    'regime': regime,
                    'volatility_level': volatility_level,
                    'trend_strength': trend_strength,
                    'confidence': confidence
                })
            
            return regime_info
            
        except Exception as e:
            logger.error(f"❌ Error analyzing market regime for {symbol}: {e}")
            return MarketRegime(
                regime='unknown',
                confidence=0.0,
                volatility_level='medium',
                trend_strength=0.0,
                regime_change_probability=0.5
            )
    
    def _classify_volatility(self, volatility: float) -> str:
        """Classify volatility level."""
        if volatility < 0.15:
            return 'low'
        elif volatility < 0.25:
            return 'medium'
        elif volatility < 0.40:
            return 'high'
        else:
            return 'extreme'
    
    def _calculate_trend_strength(self, price_series: pd.Series) -> float:
        """Calculate trend strength using multiple indicators."""
        try:
            # Linear regression slope
            x = np.arange(len(price_series))
            slope = np.polyfit(x, price_series, 1)[0]
            normalized_slope = slope / price_series.mean()
            
            # R-squared for trend consistency
            correlation = np.corrcoef(x, price_series)[0, 1]
            r_squared = correlation ** 2
            
            # Combine slope direction and consistency
            trend_strength = abs(normalized_slope) * r_squared * 100
            
            return min(1.0, trend_strength)
            
        except Exception as e:
            logger.error(f"❌ Error calculating trend strength: {e}")
            return 0.5
    
    def calculate_ai_position_size(self, symbol: str, entry_price: float, stop_loss_price: float,
                                 account_balance: float, market_data: Dict[str, Any],
                                 confidence_score: float = 0.5) -> Dict[str, Any]:
        """
        Calculate AI-enhanced position size with dynamic risk adjustment.
        
        Args:
            symbol: Trading symbol
            entry_price: Entry price
            stop_loss_price: Stop loss price
            account_balance: Account balance
            market_data: Current market data
            confidence_score: AI confidence in the trade (0-1)
            
        Returns:
            Dict containing AI-enhanced position sizing
        """
        try:
            logger.info(f"🧮 AI position sizing for {symbol} (confidence: {confidence_score:.2f})")
            
            # Analyze market regime
            market_regime = self.analyze_market_regime(symbol, market_data)
            
            # Get base risk parameters
            base_risk = self.base_risk_parameters['max_portfolio_risk']
            base_position = self.base_risk_parameters['max_position_size']
            
            # Apply regime-based adjustments
            regime_key = f"{market_regime.regime}_{market_regime.volatility_level}_vol"
            adjustments = self.regime_adjustments.get(regime_key, {'risk_multiplier': 1.0, 'position_multiplier': 1.0})
            
            # Calculate adjusted risk parameters
            adjusted_risk = base_risk * adjustments['risk_multiplier']
            adjusted_position = base_position * adjustments['position_multiplier']
            
            # Apply confidence-based scaling
            confidence_multiplier = 0.5 + (confidence_score * 0.5)  # Scale from 0.5 to 1.0
            final_risk = adjusted_risk * confidence_multiplier
            final_position = adjusted_position * confidence_multiplier
            
            # Calculate position size
            risk_per_share = abs(entry_price - stop_loss_price)
            max_risk_amount = account_balance * final_risk
            max_position_value = account_balance * final_position
            
            if risk_per_share > 0:
                max_shares_by_risk = int(max_risk_amount / risk_per_share)
                max_shares_by_position = int(max_position_value / entry_price)
                recommended_shares = min(max_shares_by_risk, max_shares_by_position)
            else:
                recommended_shares = 0
            
            # Calculate metrics
            actual_investment = recommended_shares * entry_price
            actual_risk = recommended_shares * risk_per_share
            actual_risk_percentage = (actual_risk / account_balance) * 100 if account_balance > 0 else 0
            
            result = {
                'status': 'success',
                'symbol': symbol,
                'entry_price': entry_price,
                'stop_loss_price': stop_loss_price,
                'recommended_shares': recommended_shares,
                'actual_investment': actual_investment,
                'actual_risk': actual_risk,
                'actual_risk_percentage': actual_risk_percentage,
                'ai_enhancements': {
                    'market_regime': market_regime.regime,
                    'volatility_level': market_regime.volatility_level,
                    'trend_strength': market_regime.trend_strength,
                    'confidence_score': confidence_score,
                    'regime_adjustment': adjustments,
                    'final_risk_limit': final_risk * 100,
                    'final_position_limit': final_position * 100
                },
                'timestamp': datetime.now()
            }
            
            # Publish AI position sizing to message broker
            if self.message_broker.is_connected:
                self.message_broker.publish_ai_analysis('position_sizing', symbol, result)
            
            logger.info(f"✅ AI position sizing: {recommended_shares} shares ({actual_risk_percentage:.2f}% risk)")
            return result
            
        except Exception as e:
            logger.error(f"❌ Error in AI position sizing for {symbol}: {e}")
            return {
                'status': 'error',
                'message': str(e),
                'symbol': symbol
            }
    
    def assess_portfolio_risk_ai(self, portfolio_data: Dict[str, Any], 
                                market_data: Dict[str, Any]) -> RiskMetrics:
        """
        AI-powered portfolio risk assessment.
        
        Args:
            portfolio_data: Current portfolio positions
            market_data: Real-time market data
            
        Returns:
            RiskMetrics: Comprehensive AI risk assessment
        """
        try:
            logger.info("🧠 AI portfolio risk assessment")
            
            positions = portfolio_data.get('positions', [])
            account_balance = portfolio_data.get('account_balance', 0)
            
            if not positions or account_balance <= 0:
                return RiskMetrics(
                    portfolio_risk=0.0,
                    position_risk=0.0,
                    volatility_score=0.0,
                    correlation_risk=0.0,
                    drawdown_risk=0.0,
                    confidence_score=1.0,
                    recommendation='no_positions'
                )
            
            # Calculate individual position risks
            total_investment = 0
            position_risks = []
            symbols = []
            
            for position in positions:
                symbol = position.get('symbol', '')
                quantity = float(position.get('quantity', 0))
                avg_price = float(position.get('avg_price', 0))
                current_price = float(position.get('current_price', avg_price))
                
                if quantity != 0:
                    investment = abs(quantity) * avg_price
                    total_investment += investment
                    
                    # Get market regime for this position
                    symbol_market_data = market_data.get(symbol, {})
                    regime = self.analyze_market_regime(symbol, symbol_market_data)
                    
                    # Calculate position risk score
                    position_risk_score = self._calculate_position_risk_score(
                        investment, account_balance, regime
                    )
                    
                    position_risks.append(position_risk_score)
                    symbols.append(symbol)
            
            # Portfolio-level risk calculations
            portfolio_risk = (total_investment / account_balance) if account_balance > 0 else 0
            avg_position_risk = np.mean(position_risks) if position_risks else 0
            
            # Volatility score (simplified - will be enhanced with actual volatility models)
            volatility_score = self._calculate_portfolio_volatility(positions, market_data)
            
            # Correlation risk (simplified)
            correlation_risk = self._calculate_correlation_risk(symbols)
            
            # Drawdown risk assessment
            drawdown_risk = self._assess_drawdown_risk(portfolio_data)
            
            # Overall confidence in risk assessment
            data_quality = min(1.0, len(positions) / 10.0)  # More positions = better diversification data
            confidence_score = data_quality * 0.8 + 0.2  # Minimum 20% confidence
            
            # Generate AI recommendation
            recommendation = self._generate_ai_recommendation(
                portfolio_risk, avg_position_risk, volatility_score, 
                correlation_risk, drawdown_risk
            )
            
            risk_metrics = RiskMetrics(
                portfolio_risk=portfolio_risk,
                position_risk=avg_position_risk,
                volatility_score=volatility_score,
                correlation_risk=correlation_risk,
                drawdown_risk=drawdown_risk,
                confidence_score=confidence_score,
                recommendation=recommendation
            )
            
            # Publish AI risk assessment
            if self.message_broker.is_connected:
                self.message_broker.publish_ai_analysis('portfolio_risk', 'PORTFOLIO', {
                    'portfolio_risk': portfolio_risk,
                    'volatility_score': volatility_score,
                    'correlation_risk': correlation_risk,
                    'recommendation': recommendation,
                    'confidence': confidence_score
                })
            
            logger.info(f"✅ AI portfolio risk: {portfolio_risk:.2f}, recommendation: {recommendation}")
            return risk_metrics
            
        except Exception as e:
            logger.error(f"❌ Error in AI portfolio risk assessment: {e}")
            return RiskMetrics(
                portfolio_risk=0.0,
                position_risk=0.0,
                volatility_score=0.0,
                correlation_risk=0.0,
                drawdown_risk=0.0,
                confidence_score=0.0,
                recommendation='error'
            )
    
    def _calculate_position_risk_score(self, investment: float, account_balance: float, 
                                     regime: MarketRegime) -> float:
        """Calculate risk score for individual position."""
        position_percentage = investment / account_balance
        
        # Base risk from position size
        base_risk = position_percentage
        
        # Adjust for market regime
        regime_multiplier = {
            'trending': 0.8,
            'ranging': 1.0,
            'transitional': 1.2,
            'unknown': 1.5
        }.get(regime.regime, 1.0)
        
        # Adjust for volatility
        volatility_multiplier = {
            'low': 0.8,
            'medium': 1.0,
            'high': 1.3,
            'extreme': 1.6
        }.get(regime.volatility_level, 1.0)
        
        risk_score = base_risk * regime_multiplier * volatility_multiplier
        return min(1.0, risk_score)
    
    def _calculate_portfolio_volatility(self, positions: List[Dict], market_data: Dict) -> float:
        """Calculate portfolio volatility score."""
        # Simplified volatility calculation - will be enhanced with actual models
        try:
            volatilities = []
            for position in positions:
                symbol = position.get('symbol', '')
                symbol_data = market_data.get(symbol, {})
                prices = symbol_data.get('prices', [])
                
                if len(prices) > 10:
                    returns = pd.Series(prices).pct_change().dropna()
                    vol = returns.std() * np.sqrt(252)
                    volatilities.append(vol)
            
            if volatilities:
                return np.mean(volatilities)
            return 0.2  # Default medium volatility
            
        except Exception:
            return 0.2
    
    def _calculate_correlation_risk(self, symbols: List[str]) -> float:
        """Calculate correlation risk between positions."""
        # Simplified correlation calculation - will be enhanced with actual correlation matrix
        if len(symbols) <= 1:
            return 0.0
        
        # For now, assume moderate correlation
        # Will be replaced with actual correlation calculation from historical data
        return 0.4
    
    def _assess_drawdown_risk(self, portfolio_data: Dict) -> float:
        """Assess portfolio drawdown risk."""
        # Simplified drawdown assessment - will be enhanced with historical analysis
        current_pnl = portfolio_data.get('total_pnl', 0)
        account_balance = portfolio_data.get('account_balance', 1)
        
        if account_balance > 0:
            pnl_percentage = current_pnl / account_balance
            # Higher negative P&L = higher drawdown risk
            return max(0.0, min(1.0, -pnl_percentage * 2))
        
        return 0.0
    
    def _generate_ai_recommendation(self, portfolio_risk: float, position_risk: float,
                                  volatility_score: float, correlation_risk: float,
                                  drawdown_risk: float) -> str:
        """Generate AI-powered portfolio recommendation."""
        # Risk scoring
        total_risk_score = (
            portfolio_risk * 0.3 +
            position_risk * 0.2 +
            volatility_score * 0.2 +
            correlation_risk * 0.15 +
            drawdown_risk * 0.15
        )
        
        if total_risk_score < 0.3:
            return 'low_risk_increase_exposure'
        elif total_risk_score < 0.5:
            return 'optimal_risk_maintain'
        elif total_risk_score < 0.7:
            return 'elevated_risk_reduce_exposure'
        elif total_risk_score < 0.9:
            return 'high_risk_significant_reduction'
        else:
            return 'extreme_risk_stop_trading'
    
    def start_real_time_analysis(self):
        """Start real-time AI risk analysis."""
        if self.is_running:
            logger.warning("⚠️ AI Risk Engine already running")
            return
        
        self.is_running = True
        self.analysis_thread = threading.Thread(target=self._analysis_loop, daemon=True)
        self.analysis_thread.start()
        logger.info("🚀 AI Risk Engine real-time analysis started")
    
    def stop_real_time_analysis(self):
        """Stop real-time AI risk analysis."""
        self.is_running = False
        if self.analysis_thread and self.analysis_thread.is_alive():
            self.analysis_thread.join(timeout=5)
        logger.info("🛑 AI Risk Engine real-time analysis stopped")
    
    def _analysis_loop(self):
        """Main analysis loop for real-time processing."""
        while self.is_running:
            try:
                # Real-time analysis logic will be implemented here
                # For now, just sleep
                threading.Event().wait(30)  # Analysis every 30 seconds
                
            except Exception as e:
                logger.error(f"❌ Error in AI analysis loop: {e}")
                threading.Event().wait(5)


# Example usage and testing
if __name__ == '__main__':
    def test_ai_risk_engine():
        """Test the AI Risk Engine."""
        print("🧪 Testing AI Risk Engine...")
        
        # Initialize engine
        ai_engine = AIRiskEngine()
        
        # Test market regime analysis
        print("\n📊 Testing market regime analysis...")
        sample_data = {
            'prices': [100 + i + np.random.random() for i in range(50)],
            'volumes': [1000 + np.random.randint(0, 500) for _ in range(50)]
        }
        
        regime = ai_engine.analyze_market_regime('TEST-SYMBOL', sample_data)
        print(f"Market Regime: {regime.regime}")
        print(f"Volatility: {regime.volatility_level}")
        print(f"Trend Strength: {regime.trend_strength:.2f}")
        print(f"Confidence: {regime.confidence:.2f}")
        
        # Test AI position sizing
        print("\n🧮 Testing AI position sizing...")
        position_result = ai_engine.calculate_ai_position_size(
            symbol='TEST-SYMBOL',
            entry_price=100.0,
            stop_loss_price=95.0,
            account_balance=50000.0,
            market_data=sample_data,
            confidence_score=0.8
        )
        
        if position_result.get('status') == 'success':
            print(f"Recommended shares: {position_result['recommended_shares']}")
            print(f"AI risk percentage: {position_result['actual_risk_percentage']:.2f}%")
            print(f"Market regime: {position_result['ai_enhancements']['market_regime']}")
        
        # Test portfolio risk assessment
        print("\n🛡️ Testing portfolio risk assessment...")
        portfolio_data = {
            'positions': [
                {'symbol': 'TEST1', 'quantity': 10, 'avg_price': 100, 'current_price': 105},
                {'symbol': 'TEST2', 'quantity': 5, 'avg_price': 200, 'current_price': 190}
            ],
            'account_balance': 50000.0,
            'total_pnl': 500.0
        }
        
        market_data = {
            'TEST1': sample_data,
            'TEST2': sample_data
        }
        
        risk_metrics = ai_engine.assess_portfolio_risk_ai(portfolio_data, market_data)
        print(f"Portfolio risk: {risk_metrics.portfolio_risk:.2f}")
        print(f"Volatility score: {risk_metrics.volatility_score:.2f}")
        print(f"AI recommendation: {risk_metrics.recommendation}")
        print(f"Confidence: {risk_metrics.confidence_score:.2f}")
        
        print("\n✅ AI Risk Engine testing completed!")
    
    test_ai_risk_engine()




