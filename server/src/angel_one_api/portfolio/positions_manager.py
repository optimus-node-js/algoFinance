"""
Angel One Positions Manager
==========================

Enhanced position tracking and management with real-time P&L calculation.
"""

import asyncio
from typing import Dict, List, Optional, Any
import logging
from datetime import datetime, UTC

from ..methods.get_position import get_position, get_detailed_positions

logger = logging.getLogger(__name__)

class PositionsError(Exception):
    """Raised when positions operations fail."""
    pass

class PositionsManager:
    """Enhanced positions management with real-time tracking."""
    
    def __init__(self):
        self._positions_cache = {}
        self._last_update = None
        self._cache_ttl = 60  # 1 minute cache
    
    async def get_positions_with_pnl(self) -> Dict[str, Any]:
        """Get positions with enhanced P&L analysis."""
        try:
            positions_result = await get_detailed_positions()
            
            if not positions_result['success']:
                raise PositionsError(f"Failed to fetch positions: {positions_result.get('error')}")
            
            # Enhanced analysis
            analyzed_positions = []
            total_pnl = 0
            
            for position in positions_result['positions']:
                pnl = float(position.get('unrealizedpnl', 0))
                total_pnl += pnl
                
                analyzed_position = {
                    **position,
                    'risk_level': self._assess_position_risk(position),
                    'recommendation': self._get_position_recommendation(position)
                }
                analyzed_positions.append(analyzed_position)
            
            return {
                'success': True,
                'positions': analyzed_positions,
                'summary': {
                    'total_positions': len(analyzed_positions),
                    'total_pnl': total_pnl,
                    'profitable_positions': len([p for p in analyzed_positions if float(p.get('unrealizedpnl', 0)) > 0])
                },
                'timestamp': datetime.now(UTC).isoformat()
            }
            
        except Exception as e:
            logger.error(f"❌ Positions analysis failed: {e}")
            raise PositionsError(f"Positions analysis failed: {e}")
    
    def _assess_position_risk(self, position: Dict[str, Any]) -> str:
        """Assess risk level for a position."""
        pnl_pct = float(position.get('pnlpercentage', 0))
        if abs(pnl_pct) > 20:
            return 'HIGH'
        elif abs(pnl_pct) > 10:
            return 'MEDIUM'
        return 'LOW'
    
    def _get_position_recommendation(self, position: Dict[str, Any]) -> str:
        """Get recommendation for a position."""
        pnl_pct = float(position.get('pnlpercentage', 0))
        if pnl_pct > 15:
            return 'BOOK_PROFITS'
        elif pnl_pct < -10:
            return 'STOP_LOSS'
        return 'HOLD'
