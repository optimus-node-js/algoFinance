"""
Portfolio API Endpoints
=======================

Portfolio management including holdings, positions, and performance.
"""

from fastapi import APIRouter, Depends, HTTPException

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent.parent))
from models.portfolio import (
    HoldingsResponse, PositionsResponse,
    PortfolioSummaryResponse, PerformanceResponse
)
from methods import get_holding, get_all_holding, get_position, get_rms, batch_margin, get_profile
from services.portfolio import PortfolioAnalytics, PerformanceTracker
from logger import get_api_logger
from api.dependencies import validate_angel_one_session

router = APIRouter()
logger = get_api_logger("portfolio_router")

@router.get("/holdings", response_model=HoldingsResponse)
async def get_holdings_data(_: bool = Depends(validate_angel_one_session)):
    """💰 Get holdings data"""
    try:
        result = await get_holding()
        return HoldingsResponse(
            success=True,
            message="Holdings retrieved successfully",
            holdings=result.get("holdings", []),
            total_holdings=len(result.get("holdings", [])),
            total_invested_value=result.get("total_invested_value", 0),
            total_current_value=result.get("total_current_value", 0),
            total_pnl=result.get("total_pnl", 0),
            total_pnl_percentage=result.get("total_pnl_percentage", 0)
        )
    except Exception as e:
        logger.error("Failed to get holdings", error=e)
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/holdings/all", response_model=HoldingsResponse)
async def get_all_holdings_data(_: bool = Depends(validate_angel_one_session)):
    """💰 Get complete holdings analysis"""
    try:
        result = await get_all_holding()
        return HoldingsResponse(
            success=True,
            message="Complete holdings retrieved successfully",
            holdings=result.get("holdings", []),
            total_holdings=len(result.get("holdings", [])),
            total_invested_value=result.get("total_invested_value", 0),
            total_current_value=result.get("total_current_value", 0),
            total_pnl=result.get("total_pnl", 0),
            total_pnl_percentage=result.get("total_pnl_percentage", 0)
        )
    except Exception as e:
        logger.error("Failed to get all holdings", error=e)
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/positions", response_model=PositionsResponse)
async def get_positions_data(_: bool = Depends(validate_angel_one_session)):
    """📈 Get positions data"""
    try:
        result = await get_position()
        return PositionsResponse(
            success=True,
            message="Positions retrieved successfully",
            positions=result.get("positions", []),
            total_positions=len(result.get("positions", [])),
            net_pnl=result.get("net_pnl", 0),
            realized_pnl=result.get("realized_pnl", 0),
            unrealized_pnl=result.get("unrealized_pnl", 0)
        )
    except Exception as e:
        logger.error("Failed to get positions", error=e)
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/summary", response_model=PortfolioSummaryResponse)
async def get_portfolio_summary(_: bool = Depends(validate_angel_one_session)):
    """📊 Get portfolio summary"""
    try:
        # Use portfolio analytics service
        analytics = PortfolioAnalytics()
        summary = await analytics.get_portfolio_summary()
        
        return PortfolioSummaryResponse(
            success=True,
            message="Portfolio summary retrieved successfully",
            summary=summary,
            last_updated=summary.get("last_updated")
        )
    except Exception as e:
        logger.error("Failed to get portfolio summary", error=e)
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/performance", response_model=PerformanceResponse)
async def get_performance_metrics(_: bool = Depends(validate_angel_one_session)):
    """📈 Get performance metrics"""
    try:
        # Use performance tracker service
        tracker = PerformanceTracker()
        metrics = await tracker.get_performance_metrics()
        
        return PerformanceResponse(
            success=True,
            message="Performance metrics retrieved successfully",
            metrics=metrics.get("metrics"),
            period_start=metrics.get("period_start"),
            period_end=metrics.get("period_end")
        )
    except Exception as e:
        logger.error("Failed to get performance metrics", error=e)
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/funds")
async def get_fund_details(_: bool = Depends(validate_angel_one_session)):
    """💰 Get available funds and limits"""
    try:
        result = await get_rms()
        
        return {
            "success": True,
            "message": "Fund details retrieved successfully",
            "available_cash": result.get("availablecash", 0),
            "used_margin": result.get("collateral", 0),
            "net_available": result.get("net", 0),
            "margin_used": result.get("utiliseddebits", 0),
            "total_trading_power": result.get("totaltradingpower", 0),
            "funds_details": result
        }
    except Exception as e:
        logger.error("Failed to get fund details", error=e)
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/margins")
async def calculate_margin_requirements(
    margin_data: dict,
    _: bool = Depends(validate_angel_one_session)
):
    """🔢 Calculate margin requirements for orders"""
    try:
        result = await batch_margin(margin_data)
        
        return {
            "success": True,
            "message": "Margin calculations completed successfully",
            "margin_details": result.get("margin_details", []),
            "total_margin_required": result.get("total_margin", 0),
            "calculation_timestamp": result.get("timestamp")
        }
    except Exception as e:
        logger.error("Failed to calculate margins", error=e)
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/profile")
async def get_user_profile(_: bool = Depends(validate_angel_one_session)):
    """👤 Get user profile information"""
    try:
        result = await get_profile()
        
        return {
            "success": True,
            "message": "User profile retrieved successfully",
            "profile": result.get("profile"),
            "account_details": result.get("account_details"),
            "trading_preferences": result.get("trading_preferences"),
            "limits": result.get("limits"),
            "timestamp": result.get("timestamp")
        }
    except Exception as e:
        logger.error("Failed to get user profile", error=e)
        raise HTTPException(status_code=500, detail=str(e))


