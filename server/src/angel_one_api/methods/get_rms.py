"""
Angel One API: getRMS - Risk Management System Data
==================================================

CRITICAL METHOD: Risk limits, margin requirements, and fund information
Rate Limit: 2 requests/second per API key
Priority: CRITICAL (essential for risk management)

Usage:
    from angel_one_api.methods.get_rms import get_rms
    
    # Get complete RMS data
    rms_data = await get_rms()
    
    # Get available funds
    funds = await get_available_funds()
    
    # Check if sufficient margin for trade
    margin_ok = await check_margin_availability(required_margin=50000)

Author: AI Trading System
Rate Limit: STRICTLY ENFORCED 2 req/sec per key
"""

import time
from typing import Dict, List, Optional, Any
# Import new Angel One logger
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))
from logger import get_api_logger
from datetime import datetime, UTC

# Import our rate limiting system
from rate_limiter.rate_controller import get_rate_controller, rate_limited, APIPriority
from rate_limiter.api_limits import API_LIMITS

logger = get_api_logger("get_rms")

class RMSError(Exception):
    """Raised when RMS data fetching fails."""
    pass

@rate_limited("get_rms", APIPriority.CRITICAL)
async def get_rms(_rate_limit_permit: Optional[Dict] = None) -> Dict[str, Any]:
    """
    Get Risk Management System data from Angel One API.
    
    Args:
        _rate_limit_permit: Automatically provided by rate limiter
        
    Returns:
        Dict containing:
            - success: bool
            - rms_data: Dict of RMS information
            - net_available_cash: float
            - utilized_margin: float
            - available_margin: float
            - gross_collateral_value: float
            - funds_summary: Dict
            - timestamp: str
        
    Raises:
        RMSError: If RMS data fetching fails
        RateLimitExceeded: If rate limit would be exceeded
        
    Rate Limit: 2 requests/second per API key
    """
    try:
        if not _rate_limit_permit:
            raise RMSError("No rate limit permit - internal error")
        
        # Get Angel One client
        # Use interface to get SmartAPI client
        from interface import get_angel_one_interface
        interface = get_angel_one_interface()
        angel_client = interface.smart_api
        
        # angel_client already set above
        if not angel_client:
            raise RMSError("Angel One API client not available")
        
        # Log request
        logger.debug(f"💰 RMS data request using {_rate_limit_permit['api_key_id']}")
        
        # Make API call with strict rate limiting already enforced
        # Use the correct SmartConnect method name
        response = angel_client.rmsLimit()
        
        # Parse response
        if not response:
            raise RMSError("Empty response from getRMS API")
        
        if not response.get('status'):
            error_msg = response.get('message', 'Unknown error')
            raise RMSError(f"RMS API error: {error_msg}")
        
        rms_data = response.get('data', {})
        
        # Process RMS data
        processed_rms = {
            'net_available_cash': float(rms_data.get('net', 0)),
            'available_cash': float(rms_data.get('availablecash', 0)),
            'available_intradaypayin': float(rms_data.get('availableintradaypayin', 0)),
            'available_limit_margin': float(rms_data.get('availablelimitmargin', 0)),
            'collateral_value': float(rms_data.get('collateral', 0)),
            'margin_2_limit': float(rms_data.get('m2mlimit', 0)),
            'margin_2_unrealized': float(rms_data.get('m2munrealized', 0)),
            'margin_utilized': float(rms_data.get('utilisedpayout', 0)),
            'gross_collateral_value': float(rms_data.get('grosscollateralvalue', 0)),
            'utilized_debits': float(rms_data.get('utiliseddebits', 0)),
            'category': rms_data.get('category', ''),
            'rms_date': rms_data.get('rmsdate', ''),
            'adhoc_margin': float(rms_data.get('adhocmargin', 0)),
            'tender_margin': float(rms_data.get('tendermargin', 0)),
            'available_margin_for_delivery': float(rms_data.get('availablemargin', 0))
        }
        
        # Calculate derived metrics
        total_available_funds = (
            processed_rms['net_available_cash'] + 
            processed_rms['available_intradaypayin'] +
            processed_rms['available_limit_margin']
        )
        
        utilization_percentage = (
            (processed_rms['margin_utilized'] / total_available_funds) * 100
            if total_available_funds > 0 else 0
        )
        
        # Create funds summary
        funds_summary = {
            'total_available_funds': total_available_funds,
            'cash_available': processed_rms['net_available_cash'],
            'margin_available': processed_rms['available_limit_margin'],
            'intraday_payin': processed_rms['available_intradaypayin'],
            'margin_utilized': processed_rms['margin_utilized'],
            'utilization_percentage': utilization_percentage,
            'collateral_value': processed_rms['collateral_value'],
            'unrealized_mtm': processed_rms['margin_2_unrealized'],
            'can_trade_delivery': processed_rms['net_available_cash'] > 0,
            'can_trade_intraday': total_available_funds > 0,
            'risk_level': _assess_risk_level(utilization_percentage)
        }
        
        # Success response
        result = {
            'success': True,
            'rms_data': processed_rms,
            'net_available_cash': processed_rms['net_available_cash'],
            'utilized_margin': processed_rms['margin_utilized'],
            'available_margin': processed_rms['available_limit_margin'],
            'gross_collateral_value': processed_rms['gross_collateral_value'],
            'funds_summary': funds_summary,
            'raw_data': rms_data,
            'timestamp': datetime.now(UTC).isoformat(),
            'api_key_id': _rate_limit_permit['api_key_id'],
            'response_time': time.time()
        }
        
        logger.info(f"✅ RMS data fetched: ₹{total_available_funds:.2f} available, {utilization_percentage:.1f}% utilized")
        
        return result
        
    except Exception as e:
        logger.error(f"❌ RMS data fetch failed: {e}")
        
        # Create error response
        error_result = {
            'success': False,
            'rms_data': {},
            'funds_summary': {},
            'error': str(e),
            'timestamp': datetime.now(UTC).isoformat()
        }
        
        # Re-raise as RMSError for consistent error handling
        if isinstance(e, RMSError):
            raise
        else:
            raise RMSError(f"RMS data fetch failed: {e}")

def _assess_risk_level(utilization_percentage: float) -> str:
    """
    Assess risk level based on margin utilization.
    
    Args:
        utilization_percentage: Percentage of margin utilized
        
    Returns:
        str: Risk level (LOW, MEDIUM, HIGH, CRITICAL)
    """
    if utilization_percentage >= 90:
        return 'CRITICAL'
    elif utilization_percentage >= 70:
        return 'HIGH'
    elif utilization_percentage >= 50:
        return 'MEDIUM'
    else:
        return 'LOW'

async def get_available_funds() -> Dict[str, Any]:
    """
    Get simplified available funds information.
    
    Returns:
        Dict: Available funds summary
    """
    try:
        rms_result = await get_rms()
        
        if not rms_result['success']:
            return {'success': False, 'error': rms_result.get('error')}
        
        funds = rms_result['funds_summary']
        
        return {
            'success': True,
            'total_available': funds['total_available_funds'],
            'cash_available': funds['cash_available'],
            'margin_available': funds['margin_available'],
            'can_trade': funds['can_trade_intraday'],
            'risk_level': funds['risk_level'],
            'timestamp': rms_result['timestamp']
        }
        
    except Exception as e:
        logger.error(f"❌ Available funds fetch failed: {e}")
        return {'success': False, 'error': str(e)}

async def check_margin_availability(required_margin: float) -> Dict[str, Any]:
    """
    Check if sufficient margin is available for a trade.
    
    Args:
        required_margin: Required margin amount
        
    Returns:
        Dict: Margin availability check result
    """
    try:
        rms_result = await get_rms()
        
        if not rms_result['success']:
            return {
                'success': False,
                'margin_available': False,
                'error': rms_result.get('error')
            }
        
        funds = rms_result['funds_summary']
        total_available = funds['total_available_funds']
        
        margin_available = total_available >= required_margin
        excess_margin = total_available - required_margin
        
        result = {
            'success': True,
            'margin_available': margin_available,
            'required_margin': required_margin,
            'total_available': total_available,
            'excess_margin': excess_margin if margin_available else 0,
            'shortfall': abs(excess_margin) if not margin_available else 0,
            'utilization_after_trade': (
                ((funds['margin_utilized'] + required_margin) / total_available) * 100
                if total_available > 0 else 100
            ),
            'risk_assessment': _assess_trade_risk(required_margin, total_available, funds['margin_utilized']),
            'timestamp': rms_result['timestamp']
        }
        
        return result
        
    except Exception as e:
        logger.error(f"❌ Margin availability check failed: {e}")
        return {
            'success': False,
            'margin_available': False,
            'error': str(e)
        }

def _assess_trade_risk(required_margin: float, total_available: float, current_utilized: float) -> Dict[str, Any]:
    """
    Assess risk of a potential trade.
    
    Args:
        required_margin: Required margin for trade
        total_available: Total available funds
        current_utilized: Currently utilized margin
        
    Returns:
        Dict: Risk assessment
    """
    if total_available == 0:
        return {
            'risk_level': 'CRITICAL',
            'recommendation': 'NO_TRADE',
            'reason': 'No funds available'
        }
    
    new_utilization = ((current_utilized + required_margin) / total_available) * 100
    
    if new_utilization >= 95:
        return {
            'risk_level': 'CRITICAL',
            'recommendation': 'NO_TRADE',
            'reason': 'Would exceed 95% margin utilization'
        }
    elif new_utilization >= 80:
        return {
            'risk_level': 'HIGH',
            'recommendation': 'REDUCE_SIZE',
            'reason': 'High margin utilization risk'
        }
    elif new_utilization >= 60:
        return {
            'risk_level': 'MEDIUM',
            'recommendation': 'PROCEED_CAUTION',
            'reason': 'Moderate margin utilization'
        }
    else:
        return {
            'risk_level': 'LOW',
            'recommendation': 'PROCEED',
            'reason': 'Safe margin utilization level'
        }

async def get_trading_limits() -> Dict[str, Any]:
    """
    Get trading limits and capacity information.
    
    Returns:
        Dict: Trading limits and capacity
    """
    try:
        rms_result = await get_rms()
        
        if not rms_result['success']:
            return {'success': False, 'error': rms_result.get('error')}
        
        rms_data = rms_result['rms_data']
        funds = rms_result['funds_summary']
        
        # Calculate approximate trading limits
        # These are rough estimates - actual limits depend on specific instruments
        
        limits = {
            'success': True,
            'cash_limit': rms_data['net_available_cash'],
            'intraday_limit': funds['total_available_funds'],
            'delivery_limit': rms_data['net_available_cash'],
            'margin_limit': rms_data['available_limit_margin'],
            'max_single_trade': min(funds['total_available_funds'] * 0.1, 100000),  # 10% or 1L max
            'daily_limit': funds['total_available_funds'] * 0.8,  # 80% utilization limit
            'emergency_reserve': funds['total_available_funds'] * 0.2,  # Keep 20% reserve
            'risk_assessment': {
                'current_risk': funds['risk_level'],
                'utilization': funds['utilization_percentage'],
                'can_increase_positions': funds['utilization_percentage'] < 70
            },
            'timestamp': rms_result['timestamp']
        }
        
        return limits
        
    except Exception as e:
        logger.error(f"❌ Trading limits fetch failed: {e}")
        return {'success': False, 'error': str(e)}

def get_rms_sync() -> Dict[str, Any]:
    """
    Synchronous wrapper for get_rms.
    
    ⚠️ WARNING: Use async version when possible for better performance.
    This is only for compatibility with legacy code.
    """
    import asyncio
    try:
        return asyncio.run(get_rms())
    except Exception as e:
        logger.error(f"❌ Sync RMS fetch failed: {e}")
        return {
            'success': False,
            'rms_data': {},
            'funds_summary': {},
            'error': str(e)
        }

# Backward compatibility aliases (DEPRECATED - use new names)
fetch_rms_data = get_rms  # Alias for existing code
get_risk_data = get_rms   # Alias for existing code

if __name__ == "__main__":
    # Test RMS data fetching
    async def test_rms_data():
        print("🧪 Testing Angel One RMS Data")
        print("=" * 40)
        
        try:
            # Test basic RMS data
            rms = await get_rms()
            if rms['success']:
                print(f"✅ RMS data fetched:")
                funds = rms['funds_summary']
                print(f"   Total Available: ₹{funds['total_available_funds']:.2f}")
                print(f"   Cash Available: ₹{funds['cash_available']:.2f}")
                print(f"   Margin Utilized: {funds['utilization_percentage']:.1f}%")
                print(f"   Risk Level: {funds['risk_level']}")
            else:
                print(f"❌ RMS fetch failed: {rms.get('error')}")
                
        except Exception as e:
            print(f"❌ RMS test failed: {e}")
        
        try:
            # Test margin availability check
            margin_check = await check_margin_availability(50000)
            if margin_check['success']:
                print(f"✅ Margin check (₹50,000):")
                print(f"   Available: {'Yes' if margin_check['margin_available'] else 'No'}")
                if margin_check['margin_available']:
                    print(f"   Excess: ₹{margin_check['excess_margin']:.2f}")
                else:
                    print(f"   Shortfall: ₹{margin_check['shortfall']:.2f}")
                print(f"   Risk: {margin_check['risk_assessment']['risk_level']}")
            else:
                print(f"❌ Margin check failed: {margin_check.get('error')}")
                
        except Exception as e:
            print(f"❌ Margin check test failed: {e}")
    
    # Run test (requires rate controller to be initialized)
    print("⚠️ Note: Requires rate controller initialization for testing")
    # asyncio.run(test_rms_data())
