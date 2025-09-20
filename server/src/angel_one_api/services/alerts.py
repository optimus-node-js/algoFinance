"""
Alert Manager Service
====================

Manages risk alerts and notifications for Angel One trading operations.
"""

import asyncio
from typing import Dict, Any, List
from datetime import datetime, UTC

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from logger import get_service_logger

logger = get_service_logger("alert_manager")

class AlertManager:
    """Manages trading and risk alerts."""
    
    def __init__(self):
        self.active_alerts: List[Dict[str, Any]] = []
        self.alert_history: List[Dict[str, Any]] = []
        
        logger.info("AlertManager initialized")
    
    async def get_active_alerts(self) -> Dict[str, Any]:
        """Get all active alerts."""
        try:
            # Mock active alerts for now
            mock_alerts = [
                {
                    "alert_id": "ALERT_001",
                    "alert_type": "POSITION_LIMIT",
                    "severity": "WARNING",
                    "message": "Position size approaching 80% of limit",
                    "symbol": "RELIANCE",
                    "threshold_value": 100000,
                    "current_value": 85000,
                    "timestamp": datetime.now(UTC).isoformat()
                },
                {
                    "alert_id": "ALERT_002", 
                    "alert_type": "MARGIN_SHORTAGE",
                    "severity": "CRITICAL",
                    "message": "Margin utilization exceeds 90%",
                    "symbol": None,
                    "threshold_value": 90.0,
                    "current_value": 95.5,
                    "timestamp": datetime.now(UTC).isoformat()
                }
            ]
            
            critical_count = sum(1 for alert in mock_alerts if alert["severity"] == "CRITICAL")
            warning_count = sum(1 for alert in mock_alerts if alert["severity"] == "WARNING")
            
            result = {
                "alerts": mock_alerts,
                "critical_alerts": critical_count,
                "warning_alerts": warning_count
            }
            
            logger.info("Active alerts retrieved", {
                "total_alerts": len(mock_alerts),
                "critical": critical_count,
                "warnings": warning_count
            })
            
            return result
            
        except Exception as e:
            logger.error("Failed to get active alerts", error=e)
            return {
                "alerts": [],
                "critical_alerts": 0,
                "warning_alerts": 0
            }
    
    async def create_alert(self, alert_data: Dict[str, Any]) -> str:
        """Create a new alert."""
        try:
            alert_id = f"ALERT_{len(self.active_alerts) + 1:03d}"
            
            alert = {
                "alert_id": alert_id,
                "created_at": datetime.now(UTC).isoformat(),
                **alert_data
            }
            
            self.active_alerts.append(alert)
            
            logger.info("Alert created", {
                "alert_id": alert_id,
                "alert_type": alert_data.get("alert_type"),
                "severity": alert_data.get("severity")
            })
            
            return alert_id
            
        except Exception as e:
            logger.error("Failed to create alert", error=e)
            raise
    
    async def dismiss_alert(self, alert_id: str) -> bool:
        """Dismiss an active alert."""
        try:
            for i, alert in enumerate(self.active_alerts):
                if alert.get("alert_id") == alert_id:
                    dismissed_alert = self.active_alerts.pop(i)
                    dismissed_alert["dismissed_at"] = datetime.now(UTC).isoformat()
                    self.alert_history.append(dismissed_alert)
                    
                    logger.info("Alert dismissed", {"alert_id": alert_id})
                    return True
            
            logger.warning("Alert not found for dismissal", {"alert_id": alert_id})
            return False
            
        except Exception as e:
            logger.error("Failed to dismiss alert", error=e, extra={"alert_id": alert_id})
            return False
