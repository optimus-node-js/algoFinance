"""
Angel One Fund Manager
=====================

Fund management and margin tracking.
"""

from typing import Dict, Any
import logging
from datetime import datetime, UTC

from ..methods.get_rms import get_rms

logger = logging.getLogger(__name__)

class FundError(Exception):
    """Raised when fund operations fail."""
    pass

class FundManager:
    """Fund management and tracking."""
    
    async def get_fund_details(self) -> Dict[str, Any]:
        """Get comprehensive fund details."""
        try:
            rms_result = await get_rms()
            
            if not rms_result['success']:
                raise FundError("Failed to get RMS data")
            
            rms_data = rms_result['rms_data']
            
            return {
                'success': True,
                'available_cash': float(rms_data.get('availablecash', 0)),
                'used_margin': float(rms_data.get('utilisedmargin', 0)),
                'available_margin': float(rms_data.get('availablemargin', 0)),
                'total_margin': float(rms_data.get('totalmargin', 0)),
                'fund_summary': {
                    'cash_available': float(rms_data.get('availablecash', 0)),
                    'margin_used_pct': self._calculate_margin_usage_pct(rms_data)
                },
                'timestamp': datetime.now(UTC).isoformat()
            }
            
        except Exception as e:
            logger.error(f"❌ Fund details fetch failed: {e}")
            raise FundError(f"Fund details fetch failed: {e}")
    
    def _calculate_margin_usage_pct(self, rms_data: Dict[str, Any]) -> float:
        """Calculate margin usage percentage."""
        used = float(rms_data.get('utilisedmargin', 0))
        total = float(rms_data.get('totalmargin', 0))
        return (used / total * 100) if total > 0 else 0
