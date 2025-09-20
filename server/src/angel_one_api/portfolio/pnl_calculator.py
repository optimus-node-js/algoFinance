"""
Angel One P&L Calculator
=======================

Comprehensive P&L calculations for portfolio analysis.
"""

from typing import Dict, List, Any
# Import new Angel One logger
from ..logger import get_service_logger
from datetime import datetime, UTC

logger = get_service_logger("pnl_calculator")

class PnLError(Exception):
    """Raised when P&L calculations fail."""
    pass

class PnLCalculator:
    """Advanced P&L calculation engine."""
    
    def calculate_portfolio_pnl(self, holdings: List[Dict[str, Any]], 
                               positions: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate comprehensive portfolio P&L."""
        try:
            # Holdings P&L
            holdings_pnl = sum(float(h.get('pnl', 0)) for h in holdings)
            
            # Positions P&L
            positions_pnl = sum(float(p.get('unrealizedpnl', 0)) for p in positions)
            
            # Total P&L
            total_pnl = holdings_pnl + positions_pnl
            
            # Calculate percentages
            total_invested = sum(float(h.get('invested_amount', 0)) for h in holdings)
            total_pnl_pct = (total_pnl / total_invested * 100) if total_invested > 0 else 0
            
            return {
                'success': True,
                'holdings_pnl': holdings_pnl,
                'positions_pnl': positions_pnl,
                'total_pnl': total_pnl,
                'total_invested': total_invested,
                'total_pnl_percentage': total_pnl_pct,
                'calculation_time': datetime.now(UTC).isoformat()
            }
            
        except Exception as e:
            logger.error(f"❌ P&L calculation failed: {e}")
            raise PnLError(f"P&L calculation failed: {e}")
    
    def calculate_daily_pnl(self, positions: List[Dict[str, Any]]) -> float:
        """Calculate daily P&L from positions."""
        return sum(float(p.get('unrealizedpnl', 0)) for p in positions)
