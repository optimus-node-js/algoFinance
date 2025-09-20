"""
Angel One Portfolio Module
==========================

Comprehensive portfolio management and analytics for Angel One SmartAPI.

This module consolidates and enhances portfolio logic from:
- services/portfolio_management/portfolio_service.py
- Various P&L calculations scattered across services
- Portfolio analytics and performance tracking

Components:
- HoldingsManager: Advanced holdings management and analysis
- PositionsManager: Position tracking and management
- PnLCalculator: Comprehensive P&L calculations
- PortfolioAnalytics: Advanced portfolio analytics
- PerformanceTracker: Portfolio performance tracking

Usage:
    from angel_one_api.portfolio import HoldingsManager, PositionsManager
    
    holdings_mgr = HoldingsManager()
    complete_holdings = await holdings_mgr.get_complete_analysis()
    
    positions_mgr = PositionsManager()
    position_summary = await positions_mgr.get_positions_with_pnl()
"""

try:
    from .holdings_manager import HoldingsManager, HoldingsError
except ImportError:
    HoldingsManager = None
    HoldingsError = Exception

try:
    from .positions_manager import PositionsManager, PositionsError
except ImportError:
    PositionsManager = None
    PositionsError = Exception

try:
    from .pnl_calculator import PnLCalculator, PnLError
except ImportError:
    PnLCalculator = None
    PnLError = Exception

try:
    from .portfolio_analytics import PortfolioAnalytics, AnalyticsError
except ImportError:
    PortfolioAnalytics = None
    AnalyticsError = Exception

try:
    from .performance_tracker import PerformanceTracker, PerformanceError
except ImportError:
    PerformanceTracker = None
    PerformanceError = Exception

__all__ = [
    'HoldingsManager',
    'PositionsManager',
    'PnLCalculator', 
    'PortfolioAnalytics',
    'PerformanceTracker',
    'HoldingsError',
    'PositionsError',
    'PnLError',
    'AnalyticsError',
    'PerformanceError'
]
