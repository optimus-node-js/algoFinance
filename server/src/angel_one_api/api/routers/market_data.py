"""
Market Data API Endpoints
=========================

Real-time and historical market data endpoints.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List, Optional
from datetime import date

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent.parent))

from models.market import (
    LTPResponse, BulkLTPResponse, QuoteResponse,
    CandleDataRequest, CandleDataResponse,
    InstrumentSearchRequest, InstrumentSearchResponse,
    MarketStatusResponse
)
from methods import get_ltp_data, get_bulk_ltp_data, get_quote, get_candle_data, search_scrip, get_market_status
from logger import get_api_logger
from api.dependencies import validate_angel_one_session

router = APIRouter()
logger = get_api_logger("market_data_router")

@router.get("/ltp/{symbol}", response_model=LTPResponse)
async def get_ltp(
    symbol: str,
    exchange: str = Query("NSE", description="Exchange"),
    _: bool = Depends(validate_angel_one_session)
):
    """📊 Get Live Trading Price for a symbol"""
    try:
        result = await get_ltp_data(symbol, exchange)
        return LTPResponse(
            success=True,
            message="LTP data retrieved successfully",
            data=result
        )
    except Exception as e:
        logger.error("Failed to get LTP data", error=e, extra={"symbol": symbol})
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/ltp/bulk", response_model=BulkLTPResponse)
async def get_bulk_ltp(
    symbols: List[str],
    exchange: str = Query("NSE", description="Exchange"),
    _: bool = Depends(validate_angel_one_session)
):
    """📊 Get bulk LTP data for multiple symbols"""
    try:
        if len(symbols) > 50:
            raise HTTPException(status_code=400, detail="Maximum 50 symbols allowed")
            
        result = await get_bulk_ltp_data(symbols, exchange)
        return BulkLTPResponse(
            success=True,
            message="Bulk LTP data retrieved successfully",
            data=result,
            total_symbols=len(symbols),
            successful_symbols=len(result)
        )
    except Exception as e:
        logger.error("Failed to get bulk LTP data", error=e)
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/quote/{symbol}", response_model=QuoteResponse)
async def get_market_quote(
    symbol: str,
    exchange: str = Query("NSE", description="Exchange"),
    _: bool = Depends(validate_angel_one_session)
):
    """💹 Get enhanced market quote"""
    try:
        result = await get_quote(symbol, exchange)
        return QuoteResponse(
            success=True,
            message="Quote data retrieved successfully",
            data=result
        )
    except Exception as e:
        logger.error("Failed to get quote data", error=e, extra={"symbol": symbol})
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/candles", response_model=CandleDataResponse)
async def get_historical_candles(
    symbol: str = Query(..., description="Trading symbol"),
    exchange: str = Query("NSE", description="Exchange"),
    interval: str = Query("1day", description="Candle interval"),
    from_date: date = Query(..., description="Start date"),
    to_date: date = Query(..., description="End date"),
    _: bool = Depends(validate_angel_one_session)
):
    """📈 Get historical candle data"""
    try:
        result = await get_candle_data(
            symbol=symbol,
            exchange=exchange,
            interval=interval,
            from_date=from_date,
            to_date=to_date
        )
        return CandleDataResponse(
            success=True,
            message="Candle data retrieved successfully",
            symbol=symbol,
            interval=interval,
            from_date=from_date,
            to_date=to_date,
            candles=result.get("candles", []),
            total_candles=len(result.get("candles", []))
        )
    except Exception as e:
        logger.error("Failed to get candle data", error=e, extra={"symbol": symbol})
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/search", response_model=InstrumentSearchResponse)
async def search_instruments(
    search_text: str = Query(..., min_length=2, description="Search text"),
    exchange: Optional[str] = Query(None, description="Filter by exchange"),
    _: bool = Depends(validate_angel_one_session)
):
    """🔍 Search for trading instruments"""
    try:
        result = await search_scrip(search_text, exchange)
        return InstrumentSearchResponse(
            success=True,
            message="Instrument search completed",
            search_text=search_text,
            instruments=result.get("instruments", []),
            total_results=len(result.get("instruments", []))
        )
    except Exception as e:
        logger.error("Failed to search instruments", error=e)
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/status", response_model=MarketStatusResponse)
async def get_market_status_info(_: bool = Depends(validate_angel_one_session)):
    """🕐 Get market status"""
    try:
        result = await get_market_status()
        return MarketStatusResponse(
            success=True,
            message="Market status retrieved successfully",
            status=result.get("status", []),
            timestamp=result.get("timestamp")
        )
    except Exception as e:
        logger.error("Failed to get market status", error=e)
        raise HTTPException(status_code=500, detail=str(e))
