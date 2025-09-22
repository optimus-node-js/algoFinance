"""
Advanced Features API Endpoints
===============================

Advanced trading features including GTT rules and option Greeks.
"""

from fastapi import APIRouter, Depends, HTTPException
from typing import List

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent.parent))
from methods import create_gtt_rule, gtt_operations, option_greek, generate_tokens
from logger import get_api_logger
from api.dependencies import validate_angel_one_session

router = APIRouter()
logger = get_api_logger("advanced_router")

@router.post("/gtt")
async def create_gtt_order(
    gtt_data: dict,
    _: bool = Depends(validate_angel_one_session)
):
    """🎯 Create GTT (Good Till Triggered) rule"""
    try:
        result = await create_gtt_rule(gtt_data)
        return {
            "success": True,
            "message": "GTT rule created successfully",
            "gtt_id": result.get("gtt_id"),
            "status": result.get("status")
        }
    except Exception as e:
        logger.error("Failed to create GTT rule", error=e)
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/gtt/{gtt_id}")
async def modify_gtt_rule(
    gtt_id: str,
    gtt_data: dict,
    _: bool = Depends(validate_angel_one_session)
):
    """✏️ Modify GTT rule"""
    try:
        result = await gtt_operations.modify_gtt_rule(gtt_id, gtt_data)
        return {
            "success": True,
            "message": "GTT rule modified successfully",
            "gtt_id": gtt_id,
            "status": result.get("status")
        }
    except Exception as e:
        logger.error("Failed to modify GTT rule", error=e)
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/gtt/{gtt_id}")
async def cancel_gtt_rule(
    gtt_id: str,
    _: bool = Depends(validate_angel_one_session)
):
    """❌ Cancel GTT rule"""
    try:
        result = await gtt_operations.cancel_gtt_rule(gtt_id)
        return {
            "success": True,
            "message": "GTT rule cancelled successfully",
            "gtt_id": gtt_id,
            "status": result.get("status")
        }
    except Exception as e:
        logger.error("Failed to cancel GTT rule", error=e)
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/gtt")
async def list_gtt_rules(_: bool = Depends(validate_angel_one_session)):
    """📋 List all GTT rules"""
    try:
        result = await gtt_operations.list_gtt_rules()
        return {
            "success": True,
            "message": "GTT rules retrieved successfully",
            "gtt_rules": result.get("gtt_rules", []),
            "total_rules": len(result.get("gtt_rules", []))
        }
    except Exception as e:
        logger.error("Failed to list GTT rules", error=e)
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/gtt/{gtt_id}")
async def get_gtt_details(
    gtt_id: str,
    _: bool = Depends(validate_angel_one_session)
):
    """📊 Get GTT rule details"""
    try:
        result = await gtt_operations.get_gtt_details(gtt_id)
        return {
            "success": True,
            "message": "GTT rule details retrieved successfully",
            "gtt_details": result
        }
    except Exception as e:
        logger.error("Failed to get GTT details", error=e)
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/option-greeks")
async def calculate_option_greeks(
    option_data: dict,
    _: bool = Depends(validate_angel_one_session)
):
    """📈 Calculate option Greeks"""
    try:
        result = await option_greek(option_data)
        return {
            "success": True,
            "message": "Option Greeks calculated successfully",
            "greeks": result.get("greeks"),
            "symbol": option_data.get("symbol")
        }
    except Exception as e:
        logger.error("Failed to calculate option Greeks", error=e)
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/tokens/generate")
async def generate_access_tokens(
    token_data: dict,
    _: bool = Depends(validate_angel_one_session)
):
    """🔑 Generate access tokens"""
    try:
        result = await generate_tokens(token_data)
        return {
            "success": True,
            "message": "Tokens generated successfully",
            "access_token": result.get("access_token"),
            "refresh_token": result.get("refresh_token"),
            "expires_in": result.get("expires_in")
        }
    except Exception as e:
        logger.error("Failed to generate tokens", error=e)
        raise HTTPException(status_code=500, detail=str(e))



