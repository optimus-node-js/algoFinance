"""
Angel One API Rate Limits Configuration
======================================

OFFICIAL Angel One SmartAPI rate limits for all endpoints.
This is the SINGLE SOURCE OF TRUTH for all API rate limits.

Source: https://smartapi.angelbroking.com/docs/RateLimit
Last Updated: 2025-09-18
Version: 3.0.0

CRITICAL: These limits are strictly enforced by Angel One.
Exceeding them will result in API key blocking and 403 errors.
"""

from enum import Enum
from dataclasses import dataclass
from typing import Optional, Dict, Any

class APIPriority(Enum):
    """API Priority levels for rate limiting."""
    CRITICAL = "CRITICAL"    # Authentication, orders - highest priority
    HIGH = "HIGH"            # Market data, positions - high priority  
    MEDIUM = "MEDIUM"        # Reports, analytics - medium priority
    LOW = "LOW"              # GTT, options - lowest priority

@dataclass
class APIMethodLimit:
    """
    Individual API method rate limit configuration.
    
    Each Angel One API method has specific rate limits:
    - requests_per_second: Max requests per second
    - requests_per_minute: Max requests per minute (if applicable)
    - requests_per_hour: Max requests per hour (if applicable)
    - priority: Business priority for load balancing
    - endpoint: Actual API endpoint path
    - description: Human-readable description
    """
    method_name: str
    requests_per_second: int
    requests_per_minute: Optional[int] = None
    requests_per_hour: Optional[int] = None
    priority: APIPriority = APIPriority.MEDIUM
    endpoint: str = ""
    description: str = ""

# Official Angel One API Rate Limits
# Source: https://smartapi.angelbroking.com/docs/RateLimit
ANGEL_ONE_API_LIMITS: Dict[str, APIMethodLimit] = {
    # Authentication & Session Management (CRITICAL)
    "login_by_password": APIMethodLimit(
        method_name="login_by_password",
        requests_per_second=1,
        requests_per_minute=None,
        requests_per_hour=None,
        priority=APIPriority.CRITICAL,
        endpoint="/rest/auth/angelbroking/user/v1/loginByPassword",
        description="User authentication - CRITICAL for system access"
    ),
    
    "generate_tokens": APIMethodLimit(
        method_name="generate_tokens",
        requests_per_second=1,
        requests_per_minute=None,
        requests_per_hour=None,
        priority=APIPriority.CRITICAL,
        endpoint="/rest/auth/angelbroking/jwt/v1/generateTokens",
        description="JWT token generation - CRITICAL for session refresh"
    ),
    
    "get_profile": APIMethodLimit(
        method_name="get_profile",
        requests_per_second=3,
        requests_per_minute=None,
        requests_per_hour=None,
        priority=APIPriority.HIGH,
        endpoint="/rest/secure/angelbroking/user/v1/getProfile",
        description="User profile information"
    ),
    
    "logout": APIMethodLimit(
        method_name="logout",
        requests_per_second=1,
        requests_per_minute=None,
        requests_per_hour=None,
        priority=APIPriority.LOW,
        endpoint="/rest/secure/angelbroking/user/v1/logout",
        description="Session logout"
    ),
    
    # Fund Management & RMS
    "get_rms": APIMethodLimit(
        method_name="get_rms",
        requests_per_second=2,
        requests_per_minute=None,
        requests_per_hour=None,
        priority=APIPriority.MEDIUM,
        endpoint="/rest/secure/angelbroking/user/v1/getRMS",
        description="Risk Management System data"
    ),
    
    # Order Management (CRITICAL)
    "place_order": APIMethodLimit(
        method_name="place_order",
        requests_per_second=20,
        requests_per_minute=None,
        requests_per_hour=None,
        priority=APIPriority.CRITICAL,
        endpoint="/rest/secure/angelbroking/order/v1/placeOrder",
        description="Place new order - CRITICAL for trading"
    ),
    
    "modify_order": APIMethodLimit(
        method_name="modify_order",
        requests_per_second=20,
        requests_per_minute=None,
        requests_per_hour=None,
        priority=APIPriority.CRITICAL,
        endpoint="/rest/secure/angelbroking/order/v1/modifyOrder",
        description="Modify existing order - CRITICAL for trading"
    ),
    
    "cancel_order": APIMethodLimit(
        method_name="cancel_order",
        requests_per_second=20,
        requests_per_minute=None,
        requests_per_hour=None,
        priority=APIPriority.CRITICAL,
        endpoint="/rest/secure/angelbroking/order/v1/cancelOrder",
        description="Cancel order - CRITICAL for risk management"
    ),
    
    "get_order_book": APIMethodLimit(
        method_name="get_order_book",
        requests_per_second=1,
        requests_per_minute=None,
        requests_per_hour=None,
        priority=APIPriority.HIGH,
        endpoint="/rest/secure/angelbroking/order/v1/getOrderBook",
        description="Order book data"
    ),
    
    # Market Data (HIGH PRIORITY)
    "get_ltp_data": APIMethodLimit(
        method_name="get_ltp_data",
        requests_per_second=10,
        requests_per_minute=None,
        requests_per_hour=None,
        priority=APIPriority.HIGH,
        endpoint="/rest/secure/angelbroking/order/v1/getLtpData",
        description="Last Traded Price - HIGH frequency data"
    ),
    
    "get_position": APIMethodLimit(
        method_name="get_position",
        requests_per_second=1,
        requests_per_minute=None,
        requests_per_hour=None,
        priority=APIPriority.HIGH,
        endpoint="/rest/secure/angelbroking/order/v1/getPosition",
        description="Position data"
    ),
    
    "get_trade_book": APIMethodLimit(
        method_name="get_trade_book",
        requests_per_second=1,
        requests_per_minute=None,
        requests_per_hour=None,
        priority=APIPriority.MEDIUM,
        endpoint="/rest/secure/angelbroking/order/v1/getTradeBook",
        description="Trade book data"
    ),
    
    "convert_position": APIMethodLimit(
        method_name="convert_position",
        requests_per_second=10,
        requests_per_minute=None,
        requests_per_hour=None,
        priority=APIPriority.MEDIUM,
        endpoint="/rest/secure/angelbroking/order/v1/convertPosition",
        description="Convert position type"
    ),
    
    "search_scrip": APIMethodLimit(
        method_name="search_scrip",
        requests_per_second=1,
        requests_per_minute=None,
        requests_per_hour=None,
        priority=APIPriority.HIGH,
        endpoint="/rest/secure/angelbroking/order/v1/searchScrip",
        description="Search instruments"
    ),
    
    "get_order_details": APIMethodLimit(
        method_name="get_order_details",
        requests_per_second=10,
        requests_per_minute=None,
        requests_per_hour=None,
        priority=APIPriority.MEDIUM,
        endpoint="/rest/secure/angelbroking/order/v1/details",
        description="Order details by ID"
    ),
    
    # Portfolio Management
    "get_holding": APIMethodLimit(
        method_name="get_holding",
        requests_per_second=1,
        requests_per_minute=None,
        requests_per_hour=None,
        priority=APIPriority.HIGH,
        endpoint="/rest/secure/angelbroking/portfolio/v1/getHolding",
        description="Holdings data"
    ),
    
    "get_all_holding": APIMethodLimit(
        method_name="get_all_holding",
        requests_per_second=1,
        requests_per_minute=None,
        requests_per_hour=None,
        priority=APIPriority.HIGH,
        endpoint="/rest/secure/angelbroking/portfolio/v1/getAllHolding",
        description="Complete holdings data"
    ),
    
    # Enhanced Market Data
    "get_quote": APIMethodLimit(
        method_name="get_quote",
        requests_per_second=10,
        requests_per_minute=None,
        requests_per_hour=None,
        priority=APIPriority.HIGH,
        endpoint="/rest/secure/angelbroking/market/v1/getQuote",
        description="Market quotes"
    ),
    
    "batch_margin": APIMethodLimit(
        method_name="batch_margin",
        requests_per_second=10,
        requests_per_minute=None,
        requests_per_hour=None,
        priority=APIPriority.MEDIUM,
        endpoint="/rest/secure/angelbroking/margin/v1/batch",
        description="Batch margin calculation"
    ),
    
    # GTT (Good Till Triggered) Rules - LOW PRIORITY
    "create_gtt_rule": APIMethodLimit(
        method_name="create_gtt_rule",
        requests_per_second=10,
        requests_per_minute=None,
        requests_per_hour=None,
        priority=APIPriority.LOW,
        endpoint="/rest/secure/angelbroking/gtt/v1/createRule",
        description="Create GTT rule"
    ),
    
    "modify_gtt_rule": APIMethodLimit(
        method_name="modify_gtt_rule",
        requests_per_second=10,
        requests_per_minute=None,
        requests_per_hour=None,
        priority=APIPriority.LOW,
        endpoint="/rest/secure/angelbroking/gtt/v1/modifyRule",
        description="Modify GTT rule"
    ),
    
    "cancel_gtt_rule": APIMethodLimit(
        method_name="cancel_gtt_rule",
        requests_per_second=10,
        requests_per_minute=None,
        requests_per_hour=None,
        priority=APIPriority.LOW,
        endpoint="/rest/secure/angelbroking/gtt/v1/cancelRule",
        description="Cancel GTT rule"
    ),
    
    "get_gtt_details": APIMethodLimit(
        method_name="get_gtt_details",
        requests_per_second=10,
        requests_per_minute=None,
        requests_per_hour=None,
        priority=APIPriority.LOW,
        endpoint="/rest/secure/angelbroking/gtt/v1/ruleDetails",
        description="GTT rule details"
    ),
    
    "gtt_rule_list": APIMethodLimit(
        method_name="gtt_rule_list",
        requests_per_second=10,
        requests_per_minute=None,
        requests_per_hour=None,
        priority=APIPriority.LOW,
        endpoint="/rest/secure/angelbroking/gtt/v1/ruleList",
        description="List all GTT rules"
    ),
    
    # Historical Data (MOST RESTRICTIVE)
    "get_candle_data": APIMethodLimit(
        method_name="get_candle_data",
        requests_per_second=3,
        requests_per_minute=None,
        requests_per_hour=None,
        priority=APIPriority.HIGH,
        endpoint="/rest/secure/angelbroking/historical/v1/getCandleData",
        description="Historical candlestick data - MOST RESTRICTIVE"
    ),
    
    # Options Analytics
    "option_greek": APIMethodLimit(
        method_name="option_greek",
        requests_per_second=1,
        requests_per_minute=None,
        requests_per_hour=None,
        priority=APIPriority.MEDIUM,
        endpoint="/rest/secure/angelbroking/option/v1/optionGreek",
        description="Options Greeks calculation"
    ),
    
    # Market Analysis - NEW METHODS
    "get_top_gainers_losers": APIMethodLimit(
        method_name="get_top_gainers_losers",
        requests_per_second=5,
        requests_per_minute=None,
        requests_per_hour=None,
        priority=APIPriority.MEDIUM,
        endpoint="/rest/secure/angelbroking/market/v1/topGainersLosers",
        description="Top gainers and losers data"
    ),
    
    "get_market_status": APIMethodLimit(
        method_name="get_market_status",
        requests_per_second=2,
        requests_per_minute=None,
        requests_per_hour=None,
        priority=APIPriority.MEDIUM,
        endpoint="/rest/secure/angelbroking/market/v1/marketStatus",
        description="Market status information"
    )
}

class AngelOneAPILimits:
    """
    Angel One API Limits Manager.
    
    Provides access to all official Angel One SmartAPI rate limits.
    This class serves as the interface to the ANGEL_ONE_API_LIMITS configuration.
    """
    
    def __init__(self):
        self.limits = ANGEL_ONE_API_LIMITS
    
    def get_method_limit(self, method_name: str) -> Optional[APIMethodLimit]:
        """Get rate limit for a specific method."""
        return self.limits.get(method_name)
    
    def get_all_methods(self) -> Dict[str, APIMethodLimit]:
        """Get all method limits."""
        return self.limits.copy()
    
    def get_methods_by_priority(self, priority: APIPriority) -> Dict[str, APIMethodLimit]:
        """Get all methods with specific priority."""
        return {
            name: limit for name, limit in self.limits.items()
            if limit.priority == priority
        }
    
    def get_total_methods_count(self) -> int:
        """Get total number of implemented methods."""
        return len(self.limits)
    
    def get_method_priority(self, method_name: str) -> Optional[APIPriority]:
        """Get priority for a specific method."""
        limit = self.get_method_limit(method_name)
        return limit.priority if limit else None
    
    def get_method_rate_limit(self, method_name: str) -> Optional[int]:
        """Get requests per second limit for a method."""
        limit = self.get_method_limit(method_name)
        return limit.requests_per_second if limit else None

# Export the main instances
API_LIMITS = AngelOneAPILimits()

# Quick access exports
__all__ = [
    'APIPriority',
    'APIMethodLimit', 
    'AngelOneAPILimits',
    'ANGEL_ONE_API_LIMITS',
    'API_LIMITS'
]

# Summary Statistics
print(f"Angel One API Limits Configuration Loaded:")
print(f"   Total Methods: {len(ANGEL_ONE_API_LIMITS)}")
print(f"   CRITICAL: {len([l for l in ANGEL_ONE_API_LIMITS.values() if l.priority == APIPriority.CRITICAL])}")
print(f"   HIGH: {len([l for l in ANGEL_ONE_API_LIMITS.values() if l.priority == APIPriority.HIGH])}")
print(f"   MEDIUM: {len([l for l in ANGEL_ONE_API_LIMITS.values() if l.priority == APIPriority.MEDIUM])}")
print(f"   LOW: {len([l for l in ANGEL_ONE_API_LIMITS.values() if l.priority == APIPriority.LOW])}")
