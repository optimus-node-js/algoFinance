"""
Trading API Endpoints
=====================

Core trading operations including orders, positions, and trades.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from typing import List, Optional

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent.parent))

from models.trading import (
    PlaceOrderRequest, PlaceOrderResponse,
    ModifyOrderRequest, ModifyOrderResponse,
    CancelOrderResponse, OrderBookResponse,
    TradeBookResponse, PositionsResponse
)
from methods import place_order, modify_order, cancel_order, get_order_book, get_trade_book, get_position
from logger import get_api_logger
from api.dependencies import validate_angel_one_session

router = APIRouter()
logger = get_api_logger("trading_router")

@router.post("/orders", response_model=PlaceOrderResponse)
async def place_trading_order(
    request: PlaceOrderRequest,
    _: bool = Depends(validate_angel_one_session)
):
    """🔵 Place a new trading order"""
    try:
        result = await place_order(
            symbol=request.symbol,
            quantity=request.quantity,
            transaction_type=request.transaction_type.value,
            order_type=request.order_type.value,
            product=request.product.value,
            price=float(request.price) if request.price else None,
            trigger_price=float(request.trigger_price) if request.trigger_price else None,
            disclosed_quantity=request.disclosed_quantity,
            validity=request.validity.value,
            variety=request.variety.value
        )
        
        return PlaceOrderResponse(
            success=True,
            message="Order placed successfully",
            order_id=result.get("order_id"),
            status=result.get("status")
        )
    except Exception as e:
        logger.error("Order placement failed", error=e)
        raise HTTPException(status_code=400, detail=str(e))

@router.put("/orders/{order_id}", response_model=ModifyOrderResponse)
async def modify_trading_order(
    order_id: str,
    request: ModifyOrderRequest,
    _: bool = Depends(validate_angel_one_session)
):
    """🔄 Modify an existing order"""
    try:
        result = await modify_order(
            order_id=order_id,
            quantity=request.quantity,
            price=float(request.price) if request.price else None,
            trigger_price=float(request.trigger_price) if request.trigger_price else None,
            disclosed_quantity=request.disclosed_quantity,
            validity=request.validity.value if request.validity else None
        )
        
        return ModifyOrderResponse(
            success=True,
            message="Order modified successfully",
            order_id=order_id,
            status=result.get("status")
        )
    except Exception as e:
        logger.error("Order modification failed", error=e)
        raise HTTPException(status_code=400, detail=str(e))

@router.delete("/orders/{order_id}", response_model=CancelOrderResponse)
async def cancel_trading_order(
    order_id: str,
    _: bool = Depends(validate_angel_one_session)
):
    """❌ Cancel an existing order"""
    try:
        result = await cancel_order(order_id=order_id)
        
        return CancelOrderResponse(
            success=True,
            message="Order cancelled successfully",
            order_id=order_id,
            status=result.get("status")
        )
    except Exception as e:
        logger.error("Order cancellation failed", error=e)
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/orders", response_model=OrderBookResponse)
async def get_order_book_data(_: bool = Depends(validate_angel_one_session)):
    """📋 Get order book"""
    try:
        result = await get_order_book()
        return OrderBookResponse(
            success=True,
            message="Order book retrieved successfully",
            orders=result.get("orders", []),
            total_orders=len(result.get("orders", []))
        )
    except Exception as e:
        logger.error("Failed to get order book", error=e)
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/trades", response_model=TradeBookResponse)
async def get_trade_book_data(_: bool = Depends(validate_angel_one_session)):
    """📊 Get trade book"""
    try:
        result = await get_trade_book()
        return TradeBookResponse(
            success=True,
            message="Trade book retrieved successfully",
            trades=result.get("trades", []),
            total_trades=len(result.get("trades", []))
        )
    except Exception as e:
        logger.error("Failed to get trade book", error=e)
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/positions", response_model=PositionsResponse)
async def get_positions_data(_: bool = Depends(validate_angel_one_session)):
    """📈 Get positions"""
    try:
        result = await get_position()
        return PositionsResponse(
            success=True,
            message="Positions retrieved successfully",
            positions=result.get("positions", []),
            total_positions=len(result.get("positions", [])),
            net_pnl=result.get("net_pnl", 0)
        )
    except Exception as e:
        logger.error("Failed to get positions", error=e)
        raise HTTPException(status_code=500, detail=str(e))
