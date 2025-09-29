"""
Angel One Market Data Module
============================

Centralized market data management for Angel One SmartAPI.

This module consolidates all market data logic from:
- ai/master/ai_master_orchestrator.py (LTP fetching)
- services/market_data/market_data_service.py (Historical data)
- services/stock_discovery/stock_discovery_service.py (Instrument search)

Components:
- LiveFeedManager: Real-time LTP and quote management
- HistoricalManager: Historical data coordination
- InstrumentManager: Instrument token management
- QuoteManager: Enhanced quote management

Usage:
    from angel_one_api.market_data import LiveFeedManager
    
    feed_manager = LiveFeedManager()
    ltp = await feed_manager.get_ltp("RELIANCE", "2885")
"""

from angel_one_api.market_data.live_feed_manager import LiveFeedManager, LiveFeedError
from angel_one_api.market_data.historical_manager import HistoricalManager, HistoricalDataError
from angel_one_api.market_data.instrument_manager import InstrumentManager, InstrumentError
from angel_one_api.market_data.quote_manager import QuoteManager, QuoteError

__all__ = [
    'LiveFeedManager',
    'HistoricalManager', 
    'InstrumentManager',
    'QuoteManager',
    'LiveFeedError',
    'HistoricalDataError',
    'InstrumentError',
    'QuoteError'
]
