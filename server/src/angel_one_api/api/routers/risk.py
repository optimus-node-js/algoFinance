"""
Risk Management API Endpoints
=============================

Risk management including RMS limits, margin calculations, and alerts.
"""

from fastapi import APIRouter, Depends, HTTPException
from typing import List

from models.risk import (
    RMSResponse, MarginCalculationRequest, MarginCalculationResponse,
    RiskAlertsResponse, RiskProfileResponse
)
from methods import get_rms, batch_margin
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent.parent))

from services.alerts import AlertManager
from logger import get_api_logger
from api.dependencies import validate_angel_one_session

router = APIRouter()
logger = get_api_logger("risk_router")

@router.get("/rms", response_model=RMSResponse)
async def get_rms_limits(_: bool = Depends(validate_angel_one_session)):
    """⚠️ Get RMS limits and usage"""
    try:
        result = await get_rms()
        return RMSResponse(
            success=True,
            message="RMS limits retrieved successfully",
            limits=result.get("limits"),
            last_updated=result.get("last_updated")
        )
    except Exception as e:
        logger.error("Failed to get RMS limits", error=e)
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/margin/calculate", response_model=MarginCalculationResponse)
async def calculate_margin(
    request: MarginCalculationRequest,
    _: bool = Depends(validate_angel_one_session)
):
    """💰 Calculate margin for positions"""
    try:
        result = await batch_margin(request.positions)
        return MarginCalculationResponse(
            success=True,
            message="Margin calculation completed",
            margins=result.get("margins", []),
            total_margin_required=result.get("total_margin_required", 0),
            available_margin=result.get("available_margin", 0),
            margin_shortfall=result.get("margin_shortfall", 0)
        )
    except Exception as e:
        logger.error("Failed to calculate margin", error=e)
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/alerts", response_model=RiskAlertsResponse)
async def get_risk_alerts(_: bool = Depends(validate_angel_one_session)):
    """🚨 Get active risk alerts"""
    try:
        # Use alert manager service
        alert_manager = AlertManager()
        alerts = await alert_manager.get_active_alerts()
        
        return RiskAlertsResponse(
            success=True,
            message="Risk alerts retrieved successfully",
            alerts=alerts.get("alerts", []),
            total_alerts=len(alerts.get("alerts", [])),
            critical_alerts=alerts.get("critical_alerts", 0),
            warning_alerts=alerts.get("warning_alerts", 0)
        )
    except Exception as e:
        logger.error("Failed to get risk alerts", error=e)
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/profile", response_model=RiskProfileResponse)
async def get_risk_profile(_: bool = Depends(validate_angel_one_session)):
    """👤 Get risk profile settings"""
    try:
        # Mock risk profile for now
        profile = {
            "risk_category": "MODERATE",
            "max_position_size": 100000,
            "max_daily_loss": 10000,
            "max_portfolio_value": 1000000,
            "stop_loss_mandatory": True,
            "intraday_squareoff_time": "15:20:00"
        }
        
        return RiskProfileResponse(
            success=True,
            message="Risk profile retrieved successfully",
            profile=profile,
            last_updated="2025-09-20T10:00:00Z"
        )
    except Exception as e:
        logger.error("Failed to get risk profile", error=e)
        raise HTTPException(status_code=500, detail=str(e))
