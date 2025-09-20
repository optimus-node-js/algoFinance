"""
Angel One Alert Manager
======================

Price and portfolio alerts management.
"""

from typing import Dict, List, Any
import logging
from datetime import datetime, UTC

logger = logging.getLogger(__name__)

class AlertsError(Exception):
    """Raised when alert operations fail."""
    pass

class AlertManager:
    """Alert management system."""
    
    def __init__(self):
        self._active_alerts = []
        self._alert_thresholds = {
            'profit_target': 15.0,
            'stop_loss': -10.0,
            'volume_spike': 2.0
        }
    
    def create_price_alert(self, symbol: str, target_price: float, 
                          alert_type: str = "ABOVE") -> Dict[str, Any]:
        """Create a price-based alert."""
        try:
            alert = {
                'id': f"alert_{len(self._active_alerts) + 1}",
                'symbol': symbol,
                'target_price': target_price,
                'alert_type': alert_type,
                'created_at': datetime.now(UTC).isoformat(),
                'status': 'ACTIVE'
            }
            
            self._active_alerts.append(alert)
            
            return {
                'success': True,
                'alert_id': alert['id'],
                'message': f"Alert created for {symbol} at {target_price}"
            }
            
        except Exception as e:
            logger.error(f"❌ Alert creation failed: {e}")
            raise AlertsError(f"Alert creation failed: {e}")
    
    def check_portfolio_alerts(self, holdings: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Check for portfolio-based alerts."""
        alerts = []
        
        for holding in holdings:
            pnl_pct = float(holding.get('pnl_percentage', 0))
            
            # Profit target alert
            if pnl_pct > self._alert_thresholds['profit_target']:
                alerts.append({
                    'type': 'PROFIT_TARGET',
                    'symbol': holding.get('symbol'),
                    'message': f"Profit target reached: {pnl_pct:.1f}%",
                    'severity': 'HIGH'
                })
            
            # Stop loss alert
            if pnl_pct < self._alert_thresholds['stop_loss']:
                alerts.append({
                    'type': 'STOP_LOSS',
                    'symbol': holding.get('symbol'),
                    'message': f"Stop loss triggered: {pnl_pct:.1f}%",
                    'severity': 'CRITICAL'
                })
        
        return alerts
