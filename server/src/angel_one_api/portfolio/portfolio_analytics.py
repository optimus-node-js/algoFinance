"""
Angel One Portfolio Analytics
============================

Advanced portfolio analytics and performance metrics.
"""

from typing import Dict, List, Any
# Import new Angel One logger
from ..logger import get_service_logger
from datetime import datetime, UTC

logger = get_service_logger("portfolio_analytics")

class AnalyticsError(Exception):
    """Raised when analytics operations fail."""
    pass

class PortfolioAnalytics:
    """Advanced portfolio analytics engine."""
    
    def analyze_portfolio_performance(self, holdings: List[Dict[str, Any]], 
                                    positions: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Perform comprehensive portfolio performance analysis."""
        try:
            # Calculate basic metrics
            total_holdings = len(holdings)
            total_positions = len(positions)
            
            # Risk analysis
            high_risk_holdings = len([h for h in holdings if self._assess_risk(h) == 'HIGH'])
            
            # Performance metrics
            profitable_holdings = len([h for h in holdings if float(h.get('pnl', 0)) > 0])
            win_rate = (profitable_holdings / total_holdings * 100) if total_holdings > 0 else 0
            
            return {
                'success': True,
                'portfolio_metrics': {
                    'total_holdings': total_holdings,
                    'total_positions': total_positions,
                    'win_rate': win_rate,
                    'high_risk_count': high_risk_holdings
                },
                'risk_analysis': {
                    'overall_risk': self._calculate_portfolio_risk(holdings),
                    'diversification_score': min(total_holdings / 10 * 100, 100)
                },
                'timestamp': datetime.now(UTC).isoformat()
            }
            
        except Exception as e:
            logger.error(f"❌ Portfolio analytics failed: {e}")
            raise AnalyticsError(f"Portfolio analytics failed: {e}")
    
    def _assess_risk(self, holding: Dict[str, Any]) -> str:
        """Assess risk level for a holding."""
        pnl_pct = abs(float(holding.get('pnl_percentage', 0)))
        if pnl_pct > 20:
            return 'HIGH'
        elif pnl_pct > 10:
            return 'MEDIUM'
        return 'LOW'
    
    def _calculate_portfolio_risk(self, holdings: List[Dict[str, Any]]) -> str:
        """Calculate overall portfolio risk."""
        high_risk_count = len([h for h in holdings if self._assess_risk(h) == 'HIGH'])
        total_holdings = len(holdings)
        
        if total_holdings == 0:
            return 'LOW'
        
        risk_ratio = high_risk_count / total_holdings
        if risk_ratio > 0.3:
            return 'HIGH'
        elif risk_ratio > 0.15:
            return 'MEDIUM'
        return 'LOW'
