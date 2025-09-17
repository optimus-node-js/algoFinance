"""
Central AI Decision Engine
The brain of the algorithmic trading system that coordinates all AI components,
makes real-time decisions, and manages the entire AI ecosystem.
"""

import sys
import os
import json
import logging
import asyncio
import threading
import time
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from concurrent.futures import ThreadPoolExecutor, as_completed
import numpy as np
import pandas as pd

# Add the project root directory to the Python path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
sys.path.append(PROJECT_ROOT)

from server.src.core.message_broker import get_message_broker
# Import AI components (avoid circular imports during testing)
try:
    from server.src.ai.risk_management.ai_risk_engine import AIRiskEngine, RiskMetrics
except ImportError:
    # For testing purposes, create mock classes
    class AIRiskEngine:
        def __init__(self):
            pass
        def start_real_time_analysis(self):
            pass
        def stop_real_time_analysis(self):
            pass
        def analyze_market_regime(self, symbol, data):
            from dataclasses import dataclass
            @dataclass
            class MockRegime:
                regime: str = 'trending'
                confidence: float = 0.8
                volatility_level: str = 'medium'
                trend_strength: float = 0.7
                regime_change_probability: float = 0.3
            return MockRegime()
        def assess_portfolio_risk_ai(self, portfolio, market_data):
            from dataclasses import dataclass
            @dataclass 
            class MockRiskMetrics:
                portfolio_risk: float = 0.5
                position_risk: float = 0.3
                volatility_score: float = 0.4
                correlation_risk: float = 0.3
                drawdown_risk: float = 0.2
                confidence_score: float = 0.8
                recommendation: str = 'optimal_risk_maintain'
            return MockRiskMetrics()
    
    @dataclass
    class RiskMetrics:
        portfolio_risk: float
        position_risk: float
        volatility_score: float
        correlation_risk: float
        drawdown_risk: float
        confidence_score: float
        recommendation: str

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@dataclass
class AIDecision:
    """Data class for AI decisions."""
    decision_id: str
    timestamp: datetime
    decision_type: str  # 'trade', 'risk_adjust', 'portfolio_rebalance', 'stop_trading'
    symbol: str
    action: str  # 'buy', 'sell', 'hold', 'reduce', 'increase'
    confidence: float
    reasoning: List[str]
    risk_assessment: RiskMetrics
    expected_outcome: Dict[str, Any]
    execution_priority: int  # 1-10, 10 being highest priority

@dataclass
class MarketIntelligence:
    """Comprehensive market intelligence data."""
    symbol: str
    timestamp: datetime
    price_data: Dict[str, Any]
    volatility_analysis: Dict[str, Any]
    pattern_analysis: Dict[str, Any]
    sentiment_analysis: Dict[str, Any]
    risk_metrics: RiskMetrics
    market_regime: str
    confidence_score: float

class CentralAIEngine:
    """
    Central AI Decision Engine that coordinates all AI components and makes
    intelligent trading decisions in real-time.
    
    Features:
    - Real-time decision making across multiple stocks
    - AI component coordination and orchestration
    - Advanced machine learning model ensemble
    - Risk-aware decision optimization
    - Performance tracking and continuous learning
    """
    
    def __init__(self):
        """Initialize the Central AI Engine."""
        self.message_broker = get_message_broker()
        self.is_running = False
        self.decision_thread = None
        self.executor = ThreadPoolExecutor(max_workers=6)  # For parallel processing
        
        # AI Component instances
        self.ai_risk_engine = AIRiskEngine()
        self.volatility_analyzer = None  # Will be initialized when created
        self.pattern_recognizer = None   # Will be initialized when created
        self.sentiment_analyzer = None   # Will be initialized when created
        self.progressive_learner = None  # Will be initialized when created
        
        # Decision tracking
        self.recent_decisions = []
        self.decision_performance = {}
        self.market_intelligence = {}
        
        # Configuration
        self.config = {
            'max_parallel_analysis': 6,
            'decision_cooldown': 5,  # seconds between decisions for same symbol
            'confidence_threshold': 0.7,  # minimum confidence for trade decisions
            'risk_threshold': 0.8,  # maximum risk score for trades
            'performance_window': 100,  # number of recent decisions to track
        }
        
        # Watchlist for parallel analysis
        self.active_symbols = [
            'RELIANCE-EQ', 'TCS-EQ', 'INFY-EQ', 
            'HDFC-EQ', 'SBIN-EQ', 'ITC-EQ'
        ]
        
        logger.info("🧠 Central AI Engine initialized successfully")
    
    def start_ai_engine(self):
        """Start the Central AI Engine for real-time decision making."""
        if self.is_running:
            logger.warning("⚠️ Central AI Engine already running")
            return
        
        self.is_running = True
        
        # Start AI risk engine
        self.ai_risk_engine.start_real_time_analysis()
        
        # Start main decision loop
        self.decision_thread = threading.Thread(target=self._decision_loop, daemon=True)
        self.decision_thread.start()
        
        logger.info("🚀 Central AI Engine started - Real-time decision making active")
    
    def stop_ai_engine(self):
        """Stop the Central AI Engine."""
        self.is_running = False
        
        # Stop AI components
        self.ai_risk_engine.stop_real_time_analysis()
        
        # Stop decision thread
        if self.decision_thread and self.decision_thread.is_alive():
            self.decision_thread.join(timeout=5)
        
        # Shutdown executor
        self.executor.shutdown(wait=True)
        
        logger.info("🛑 Central AI Engine stopped")
    
    def _decision_loop(self):
        """Main decision loop for real-time AI processing."""
        logger.info("🔄 Central AI decision loop started")
        
        while self.is_running:
            try:
                start_time = time.time()
                
                # Parallel analysis of all active symbols
                self._parallel_market_analysis()
                
                # Make trading decisions based on analysis
                decisions = self._make_trading_decisions()
                
                # Execute high-priority decisions
                self._execute_decisions(decisions)
                
                # Update performance metrics
                self._update_performance_metrics()
                
                # Log performance
                processing_time = time.time() - start_time
                logger.info(f"⚡ AI decision cycle completed in {processing_time:.3f}s")
                
                # Wait before next cycle
                time.sleep(max(1, 5 - processing_time))  # Target 5-second cycles
                
            except Exception as e:
                logger.error(f"❌ Error in AI decision loop: {e}")
                time.sleep(5)
    
    def _parallel_market_analysis(self):
        """Perform parallel market analysis across multiple symbols."""
        try:
            logger.debug("📊 Starting parallel market analysis")
            
            # Submit analysis tasks for all symbols
            analysis_futures = {}
            for symbol in self.active_symbols:
                future = self.executor.submit(self._comprehensive_symbol_analysis, symbol)
                analysis_futures[symbol] = future
            
            # Collect results
            for symbol, future in analysis_futures.items():
                try:
                    intelligence = future.result(timeout=3)  # 3-second timeout per symbol
                    self.market_intelligence[symbol] = intelligence
                    
                    # Publish intelligence to message broker
                    if self.message_broker.is_connected:
                        self.message_broker.publish_ai_analysis('market_intelligence', symbol, {
                            'intelligence': asdict(intelligence),
                            'timestamp': datetime.now().isoformat()
                        })
                    
                except Exception as e:
                    logger.warning(f"⚠️ Analysis timeout/error for {symbol}: {e}")
            
        except Exception as e:
            logger.error(f"❌ Error in parallel market analysis: {e}")
    
    def _comprehensive_symbol_analysis(self, symbol: str) -> MarketIntelligence:
        """Perform comprehensive AI analysis for a single symbol."""
        try:
            # Mock market data (in production, this would come from data feeds)
            price_data = self._get_symbol_market_data(symbol)
            
            # AI Component Analysis (parallel where possible)
            analysis_results = {}
            
            # Risk Analysis
            try:
                risk_metrics = self.ai_risk_engine.assess_portfolio_risk_ai(
                    {'positions': [{'symbol': symbol, 'quantity': 10, 'avg_price': 100}],
                     'account_balance': 100000},
                    {symbol: price_data}
                )
                analysis_results['risk'] = risk_metrics
            except Exception as e:
                logger.warning(f"⚠️ Risk analysis failed for {symbol}: {e}")
                analysis_results['risk'] = RiskMetrics(0, 0, 0, 0, 0, 0, 'error')
            
            # Volatility Analysis (placeholder - will use real volatility analyzer)
            volatility_analysis = self._analyze_volatility(symbol, price_data)
            analysis_results['volatility'] = volatility_analysis
            
            # Pattern Analysis (placeholder)
            pattern_analysis = self._analyze_patterns(symbol, price_data)
            analysis_results['patterns'] = pattern_analysis
            
            # Sentiment Analysis (placeholder)
            sentiment_analysis = self._analyze_sentiment(symbol)
            analysis_results['sentiment'] = sentiment_analysis
            
            # Market Regime Detection
            regime = self.ai_risk_engine.analyze_market_regime(symbol, price_data)
            
            # Calculate overall confidence
            confidence_score = self._calculate_overall_confidence(analysis_results)
            
            intelligence = MarketIntelligence(
                symbol=symbol,
                timestamp=datetime.now(),
                price_data=price_data,
                volatility_analysis=volatility_analysis,
                pattern_analysis=pattern_analysis,
                sentiment_analysis=sentiment_analysis,
                risk_metrics=analysis_results['risk'],
                market_regime=regime.regime,
                confidence_score=confidence_score
            )
            
            logger.debug(f"✅ Comprehensive analysis completed for {symbol} (confidence: {confidence_score:.2f})")
            return intelligence
            
        except Exception as e:
            logger.error(f"❌ Error in comprehensive analysis for {symbol}: {e}")
            # Return default intelligence
            return MarketIntelligence(
                symbol=symbol,
                timestamp=datetime.now(),
                price_data={},
                volatility_analysis={},
                pattern_analysis={},
                sentiment_analysis={},
                risk_metrics=RiskMetrics(0, 0, 0, 0, 0, 0, 'error'),
                market_regime='unknown',
                confidence_score=0.0
            )
    
    def _get_symbol_market_data(self, symbol: str) -> Dict[str, Any]:
        """Get market data for a symbol (mock data for now)."""
        # Mock market data - in production, this would come from real feeds
        base_price = 100 + hash(symbol) % 1000
        prices = [base_price + i + np.random.random() * 5 for i in range(50)]
        volumes = [1000 + np.random.randint(0, 500) for _ in range(50)]
        
        return {
            'prices': prices,
            'volumes': volumes,
            'current_price': prices[-1],
            'timeframes': {
                '5m': prices[-12:],   # Last 12 * 5min = 1 hour
                '15m': prices[-16:],  # Last 16 * 15min = 4 hours
                '1h': prices[-24:],   # Last 24 hours
                '1d': prices[-30:],   # Last 30 days
            }
        }
    
    def _analyze_volatility(self, symbol: str, price_data: Dict) -> Dict[str, Any]:
        """Analyze volatility (placeholder - will use real volatility analyzer)."""
        prices = price_data.get('prices', [])
        if len(prices) < 10:
            return {'volatility': 0.2, 'volatility_regime': 'medium', 'forecast': 0.2}
        
        returns = pd.Series(prices).pct_change().dropna()
        volatility = returns.std() * np.sqrt(252)
        
        return {
            'current_volatility': volatility,
            'volatility_regime': 'high' if volatility > 0.3 else 'medium' if volatility > 0.15 else 'low',
            'volatility_forecast': volatility * (1 + np.random.random() * 0.1 - 0.05),
            'garch_forecast': volatility * 1.05,  # Placeholder
            'confidence': 0.8
        }
    
    def _analyze_patterns(self, symbol: str, price_data: Dict) -> Dict[str, Any]:
        """Analyze price patterns (placeholder)."""
        prices = price_data.get('prices', [])
        if len(prices) < 20:
            return {'patterns': [], 'trend': 'neutral', 'strength': 0.5}
        
        # Simple trend analysis
        recent_trend = (prices[-1] - prices[-10]) / prices[-10]
        trend = 'bullish' if recent_trend > 0.02 else 'bearish' if recent_trend < -0.02 else 'neutral'
        
        return {
            'detected_patterns': ['ascending_triangle'] if recent_trend > 0 else ['descending_triangle'],
            'trend': trend,
            'trend_strength': min(1.0, abs(recent_trend) * 10),
            'support_levels': [min(prices[-10:])],
            'resistance_levels': [max(prices[-10:])],
            'confidence': 0.7
        }
    
    def _analyze_sentiment(self, symbol: str) -> Dict[str, Any]:
        """Analyze market sentiment (placeholder)."""
        # Mock sentiment analysis
        sentiment_score = np.random.random() * 2 - 1  # -1 to 1
        
        return {
            'overall_sentiment': sentiment_score,
            'sentiment_label': 'bullish' if sentiment_score > 0.2 else 'bearish' if sentiment_score < -0.2 else 'neutral',
            'news_sentiment': sentiment_score * 0.8,
            'social_sentiment': sentiment_score * 1.2,
            'confidence': 0.6
        }
    
    def _calculate_overall_confidence(self, analysis_results: Dict) -> float:
        """Calculate overall confidence score from all analyses."""
        confidences = []
        
        # Extract confidence scores from each analysis
        if 'volatility' in analysis_results:
            confidences.append(analysis_results['volatility'].get('confidence', 0.5))
        
        if 'patterns' in analysis_results:
            confidences.append(analysis_results['patterns'].get('confidence', 0.5))
        
        if 'sentiment' in analysis_results:
            confidences.append(analysis_results['sentiment'].get('confidence', 0.5))
        
        if 'risk' in analysis_results:
            confidences.append(analysis_results['risk'].confidence_score)
        
        return np.mean(confidences) if confidences else 0.5
    
    def _make_trading_decisions(self) -> List[AIDecision]:
        """Make trading decisions based on market intelligence."""
        decisions = []
        
        try:
            for symbol, intelligence in self.market_intelligence.items():
                # Skip if confidence too low
                if intelligence.confidence_score < self.config['confidence_threshold']:
                    continue
                
                # Skip if risk too high
                if intelligence.risk_metrics.portfolio_risk > self.config['risk_threshold']:
                    continue
                
                # Generate decision based on multiple factors
                decision = self._generate_symbol_decision(intelligence)
                if decision:
                    decisions.append(decision)
            
            # Sort decisions by priority
            decisions.sort(key=lambda d: d.execution_priority, reverse=True)
            
            logger.info(f"🎯 Generated {len(decisions)} AI trading decisions")
            
        except Exception as e:
            logger.error(f"❌ Error making trading decisions: {e}")
        
        return decisions
    
    def _generate_symbol_decision(self, intelligence: MarketIntelligence) -> Optional[AIDecision]:
        """Generate a trading decision for a specific symbol."""
        try:
            symbol = intelligence.symbol
            confidence = intelligence.confidence_score
            
            # Decision logic based on multiple AI factors
            reasoning = []
            action_score = 0
            
            # Pattern analysis influence
            pattern_data = intelligence.pattern_analysis
            if pattern_data.get('trend') == 'bullish':
                action_score += 0.3 * pattern_data.get('trend_strength', 0.5)
                reasoning.append(f"Bullish pattern detected (strength: {pattern_data.get('trend_strength', 0.5):.2f})")
            elif pattern_data.get('trend') == 'bearish':
                action_score -= 0.3 * pattern_data.get('trend_strength', 0.5)
                reasoning.append(f"Bearish pattern detected (strength: {pattern_data.get('trend_strength', 0.5):.2f})")
            
            # Sentiment analysis influence
            sentiment_data = intelligence.sentiment_analysis
            sentiment_score = sentiment_data.get('overall_sentiment', 0)
            action_score += 0.2 * sentiment_score
            reasoning.append(f"Market sentiment: {sentiment_data.get('sentiment_label', 'neutral')} ({sentiment_score:.2f})")
            
            # Volatility analysis influence
            volatility_data = intelligence.volatility_analysis
            vol_regime = volatility_data.get('volatility_regime', 'medium')
            if vol_regime == 'low':
                action_score += 0.1  # Favor trading in low volatility
                reasoning.append("Low volatility environment favors trading")
            elif vol_regime == 'high':
                action_score -= 0.1  # Reduce exposure in high volatility
                reasoning.append("High volatility environment - reducing exposure")
            
            # Risk assessment influence
            risk_metrics = intelligence.risk_metrics
            if risk_metrics.recommendation in ['low_risk_increase_exposure', 'optimal_risk_maintain']:
                action_score += 0.2
                reasoning.append(f"Risk assessment: {risk_metrics.recommendation}")
            elif risk_metrics.recommendation in ['high_risk_significant_reduction', 'extreme_risk_stop_trading']:
                action_score -= 0.5
                reasoning.append(f"Risk assessment: {risk_metrics.recommendation}")
            
            # Determine action based on action_score
            if action_score > 0.3:
                action = 'buy'
                decision_type = 'trade'
            elif action_score < -0.3:
                action = 'sell'
                decision_type = 'trade'
            elif abs(action_score) < 0.1:
                action = 'hold'
                decision_type = 'hold'
            else:
                return None  # No clear decision
            
            # Calculate execution priority
            priority = min(10, int(confidence * 10))
            
            # Expected outcome prediction
            expected_outcome = {
                'expected_return': action_score * 0.02,  # 2% max expected return
                'expected_risk': intelligence.risk_metrics.portfolio_risk,
                'time_horizon': '1d',
                'probability_success': confidence
            }
            
            decision = AIDecision(
                decision_id=f"{symbol}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                timestamp=datetime.now(),
                decision_type=decision_type,
                symbol=symbol,
                action=action,
                confidence=confidence,
                reasoning=reasoning,
                risk_assessment=risk_metrics,
                expected_outcome=expected_outcome,
                execution_priority=priority
            )
            
            logger.info(f"🎯 Decision for {symbol}: {action} (confidence: {confidence:.2f}, priority: {priority})")
            return decision
            
        except Exception as e:
            logger.error(f"❌ Error generating decision for {intelligence.symbol}: {e}")
            return None
    
    def _execute_decisions(self, decisions: List[AIDecision]):
        """Execute high-priority AI decisions."""
        try:
            executed_count = 0
            
            for decision in decisions[:3]:  # Execute top 3 decisions
                # Check cooldown
                if self._is_decision_on_cooldown(decision.symbol):
                    continue
                
                # Execute decision
                success = self._execute_single_decision(decision)
                if success:
                    executed_count += 1
                    self.recent_decisions.append(decision)
                    
                    # Publish decision to message broker
                    if self.message_broker.is_connected:
                        self.message_broker.publish_strategy_signal('central_ai', decision.symbol, {
                            'decision': asdict(decision),
                            'execution_time': datetime.now().isoformat()
                        })
            
            if executed_count > 0:
                logger.info(f"⚡ Executed {executed_count} AI decisions")
            
        except Exception as e:
            logger.error(f"❌ Error executing decisions: {e}")
    
    def _execute_single_decision(self, decision: AIDecision) -> bool:
        """Execute a single trading decision."""
        try:
            # Log decision execution
            logger.info(f"🎯 Executing {decision.action} decision for {decision.symbol}")
            logger.info(f"   Reasoning: {', '.join(decision.reasoning)}")
            logger.info(f"   Confidence: {decision.confidence:.2f}")
            logger.info(f"   Expected return: {decision.expected_outcome['expected_return']:.2%}")
            
            # In production, this would integrate with the order management service
            # For now, we'll simulate execution
            execution_success = True  # Simulate successful execution
            
            if execution_success:
                logger.info(f"✅ Decision executed successfully for {decision.symbol}")
            else:
                logger.warning(f"❌ Decision execution failed for {decision.symbol}")
            
            return execution_success
            
        except Exception as e:
            logger.error(f"❌ Error executing decision for {decision.symbol}: {e}")
            return False
    
    def _is_decision_on_cooldown(self, symbol: str) -> bool:
        """Check if a symbol is on decision cooldown."""
        cooldown_time = datetime.now() - timedelta(seconds=self.config['decision_cooldown'])
        
        for decision in self.recent_decisions:
            if decision.symbol == symbol and decision.timestamp > cooldown_time:
                return True
        
        return False
    
    def _update_performance_metrics(self):
        """Update AI performance metrics."""
        try:
            # Keep only recent decisions for performance tracking
            cutoff_time = datetime.now() - timedelta(hours=24)
            self.recent_decisions = [
                d for d in self.recent_decisions 
                if d.timestamp > cutoff_time
            ]
            
            # Calculate performance metrics
            if len(self.recent_decisions) > 0:
                avg_confidence = np.mean([d.confidence for d in self.recent_decisions])
                decision_count = len(self.recent_decisions)
                
                # Log performance
                logger.debug(f"📊 AI Performance: {decision_count} decisions, avg confidence: {avg_confidence:.2f}")
            
        except Exception as e:
            logger.error(f"❌ Error updating performance metrics: {e}")
    
    def get_ai_status(self) -> Dict[str, Any]:
        """Get comprehensive AI engine status."""
        try:
            return {
                'is_running': self.is_running,
                'active_symbols': len(self.active_symbols),
                'recent_decisions': len(self.recent_decisions),
                'market_intelligence_symbols': len(self.market_intelligence),
                'ai_components': {
                    'risk_engine': self.ai_risk_engine is not None,
                    'volatility_analyzer': self.volatility_analyzer is not None,
                    'pattern_recognizer': self.pattern_recognizer is not None,
                    'sentiment_analyzer': self.sentiment_analyzer is not None,
                    'progressive_learner': self.progressive_learner is not None
                },
                'configuration': self.config,
                'performance': {
                    'avg_confidence': np.mean([d.confidence for d in self.recent_decisions]) if self.recent_decisions else 0,
                    'decisions_last_hour': len([d for d in self.recent_decisions if d.timestamp > datetime.now() - timedelta(hours=1)])
                },
                'timestamp': datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"❌ Error getting AI status: {e}")
            return {'error': str(e)}


# Example usage and testing
if __name__ == '__main__':
    def test_central_ai_engine():
        """Test the Central AI Engine."""
        print("🧪 Testing Central AI Engine...")
        
        # Initialize engine
        ai_engine = CentralAIEngine()
        
        # Test status
        status = ai_engine.get_ai_status()
        print(f"AI Engine Status: {status['is_running']}")
        print(f"Active Symbols: {status['active_symbols']}")
        print(f"AI Components: {status['ai_components']}")
        
        # Test single symbol analysis
        print("\n📊 Testing comprehensive symbol analysis...")
        intelligence = ai_engine._comprehensive_symbol_analysis('RELIANCE-EQ')
        print(f"Analysis completed for {intelligence.symbol}")
        print(f"Market Regime: {intelligence.market_regime}")
        print(f"Confidence: {intelligence.confidence_score:.2f}")
        print(f"Risk Recommendation: {intelligence.risk_metrics.recommendation}")
        
        # Test decision generation
        print("\n🎯 Testing decision generation...")
        decision = ai_engine._generate_symbol_decision(intelligence)
        if decision:
            print(f"Decision: {decision.action} {decision.symbol}")
            print(f"Confidence: {decision.confidence:.2f}")
            print(f"Reasoning: {', '.join(decision.reasoning)}")
            print(f"Priority: {decision.execution_priority}")
        
        print("\n✅ Central AI Engine testing completed!")
    
    test_central_ai_engine()
