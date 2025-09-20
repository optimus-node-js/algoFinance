"""
Angel One P&L Reports
====================

Comprehensive P&L reporting and analysis.
"""

from typing import Dict, List, Any
import logging
from datetime import datetime, UTC

from ..methods.get_trade_book import get_trade_book

logger = logging.getLogger(__name__)

class ReportsError(Exception):
    """Raised when report generation fails."""
    pass

class PnLReports:
    """P&L reporting engine."""
    
    async def generate_daily_pnl_report(self) -> Dict[str, Any]:
        """Generate daily P&L report."""
        try:
            trades_result = await get_trade_book()
            
            if not trades_result['success']:
                raise ReportsError("Failed to get trade book")
            
            trades = trades_result['trades']
            
            # Calculate daily P&L
            total_pnl = sum(float(trade.get('netvalue', 0)) for trade in trades)
            
            # Categorize trades
            profitable_trades = [t for t in trades if float(t.get('netvalue', 0)) > 0]
            loss_trades = [t for t in trades if float(t.get('netvalue', 0)) < 0]
            
            return {
                'success': True,
                'report_date': datetime.now(UTC).date().isoformat(),
                'total_pnl': total_pnl,
                'total_trades': len(trades),
                'profitable_trades': len(profitable_trades),
                'loss_trades': len(loss_trades),
                'win_rate': (len(profitable_trades) / len(trades) * 100) if trades else 0,
                'avg_profit': sum(float(t.get('netvalue', 0)) for t in profitable_trades) / len(profitable_trades) if profitable_trades else 0,
                'avg_loss': sum(float(t.get('netvalue', 0)) for t in loss_trades) / len(loss_trades) if loss_trades else 0,
                'timestamp': datetime.now(UTC).isoformat()
            }
            
        except Exception as e:
            logger.error(f"❌ Daily P&L report failed: {e}")
            raise ReportsError(f"Daily P&L report failed: {e}")
