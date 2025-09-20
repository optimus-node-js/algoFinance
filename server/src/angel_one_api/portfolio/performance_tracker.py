"""
Angel One Performance Tracker
=============================

Portfolio performance tracking and historical analysis.
"""

from typing import Dict, List, Any
# Import new Angel One logger
from ..logger import get_service_logger
from datetime import datetime, UTC

logger = get_service_logger("performance_tracker")

class PerformanceError(Exception):
    """Raised when performance tracking fails."""
    pass

class PerformanceTracker:
    """Portfolio performance tracking engine."""
    
    def __init__(self):
        self._performance_history = []
    
    def track_performance(self, portfolio_value: float, total_pnl: float) -> Dict[str, Any]:
        """Track portfolio performance over time."""
        try:
            performance_entry = {
                'timestamp': datetime.now(UTC).isoformat(),
                'portfolio_value': portfolio_value,
                'total_pnl': total_pnl,
                'date': datetime.now(UTC).date().isoformat()
            }
            
            self._performance_history.append(performance_entry)
            
            # Keep only last 30 days
            if len(self._performance_history) > 30:
                self._performance_history = self._performance_history[-30:]
            
            return {
                'success': True,
                'current_performance': performance_entry,
                'historical_data': self._performance_history[-7:],  # Last 7 days
                'performance_trend': self._calculate_trend()
            }
            
        except Exception as e:
            logger.error(f"❌ Performance tracking failed: {e}")
            raise PerformanceError(f"Performance tracking failed: {e}")
    
    def _calculate_trend(self) -> str:
        """Calculate performance trend."""
        if len(self._performance_history) < 2:
            return 'INSUFFICIENT_DATA'
        
        recent_pnl = self._performance_history[-1]['total_pnl']
        older_pnl = self._performance_history[-2]['total_pnl']
        
        if recent_pnl > older_pnl:
            return 'IMPROVING'
        elif recent_pnl < older_pnl:
            return 'DECLINING'
        return 'STABLE'
