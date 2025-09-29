"""
Angel One API: getAllHolding - Complete Holdings Data
===================================================

METHOD: Comprehensive holdings information including pledged holdings
Rate Limit: 1 request/second per API key
Priority: HIGH (comprehensive portfolio data)

Usage:
    from angel_one_api.methods.get_all_holding import get_all_holding
    
    # Get complete holdings data
    all_holdings = await get_all_holding()
    
    # Get segregated holdings
    segregated = await get_segregated_holdings()
    
    # Get pledged holdings only
    pledged = await get_pledged_holdings()

Author: AI Trading System
Rate Limit: STRICTLY ENFORCED 1 req/sec per key
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

# Import idempotency enhancements
try:
    from ..enhancements.idempotency_manager import idempotency_wrapper
    IDEMPOTENCY_AVAILABLE = True
except ImportError:
    IDEMPOTENCY_AVAILABLE = False

logger = get_api_logger("get_all_holding")

class AllHoldingError(Exception):
    """Raised when all holdings data fetching fails."""
    pass

@idempotency_wrapper(method_type="account", ttl=300, cache_response=True) if IDEMPOTENCY_AVAILABLE else lambda x: x
@rate_limited("get_all_holding", APIPriority.HIGH)
async def get_all_holding(_rate_limit_permit: Optional[Dict] = None) -> Dict[str, Any]:
    """
    Get complete holdings data including pledged holdings from Angel One API.
    
    Args:
        _rate_limit_permit: Automatically provided by rate limiter
        
    Returns:
        Dict containing:
            - success: bool
            - all_holdings: List of all holding data
            - regular_holdings: List of regular holdings
            - pledged_holdings: List of pledged holdings
            - total_holdings: int
            - comprehensive_summary: Dict
            - timestamp: str
        
    Raises:
        AllHoldingError: If all holdings fetching fails
        RateLimitExceeded: If rate limit would be exceeded
        
    Rate Limit: 1 request/second per API key
    """
    try:
        if not _rate_limit_permit:
            raise AllHoldingError("No rate limit permit - internal error")
        
        # Get Angel One client
        # Use interface to get SmartAPI client
        from interface import get_angel_one_interface
        interface = get_angel_one_interface()
        angel_client = interface.smart_api
        
        # angel_client already set above
        if not angel_client:
            raise AllHoldingError("Angel One API client not available")
        
        # Log request
        logger.debug(f"💼 All holdings request using {_rate_limit_permit['api_key_id']}")
        
        # Make API call with strict rate limiting already enforced
        # Use the correct SmartConnect method name
        response = angel_client.holding()
        
        # Parse response
        if not response:
            raise AllHoldingError("Empty response from getAllHolding API")
        
        if not response.get('status'):
            error_msg = response.get('message', 'Unknown error')
            raise AllHoldingError(f"All holdings API error: {error_msg}")
        
        holdings_data = response.get('data', [])
        
        # Validate holdings data
        if not isinstance(holdings_data, list):
            raise AllHoldingError("Invalid all holdings data format received")
        
        # Process and categorize all holdings
        all_holdings = []
        regular_holdings = []
        pledged_holdings = []
        demat_holdings = []
        
        # Portfolio totals
        total_invested = 0.0
        total_current_value = 0.0
        total_pnl = 0.0
        total_pledged_value = 0.0
        
        for holding in holdings_data:
            # Clean and validate holding data
            processed_holding = _process_all_holding_data(holding)
            all_holdings.append(processed_holding)
            
            # Categorize holdings
            if processed_holding.get('is_pledged', False):
                pledged_holdings.append(processed_holding)
                total_pledged_value += processed_holding.get('current_value', 0)
            else:
                regular_holdings.append(processed_holding)
            
            if processed_holding.get('holding_type') == 'DEMAT':
                demat_holdings.append(processed_holding)
            
            # Accumulate totals
            total_invested += processed_holding.get('invested_amount', 0)
            total_current_value += processed_holding.get('current_value', 0)
            total_pnl += processed_holding.get('pnl', 0)
        
        # Calculate comprehensive portfolio metrics
        portfolio_return_pct = (
            (total_pnl / total_invested) * 100 
            if total_invested > 0 else 0
        )
        
        pledged_percentage = (
            (total_pledged_value / total_current_value) * 100
            if total_current_value > 0 else 0
        )
        
        comprehensive_summary = {
            'total_invested': total_invested,
            'current_value': total_current_value,
            'total_pnl': total_pnl,
            'portfolio_return_pct': portfolio_return_pct,
            'total_pledged_value': total_pledged_value,
            'pledged_percentage': pledged_percentage,
            'regular_holdings_count': len(regular_holdings),
            'pledged_holdings_count': len(pledged_holdings),
            'demat_holdings_count': len(demat_holdings),
            'largest_holding': _find_largest_holding(all_holdings),
            'best_performer': _find_best_performer(all_holdings),
            'worst_performer': _find_worst_performer(all_holdings),
            'sector_analysis': _analyze_sectors(all_holdings),
            'risk_analysis': _analyze_portfolio_risk(all_holdings),
            'liquidity_analysis': _analyze_liquidity(all_holdings)
        }
        
        # Success response
        result = {
            'success': True,
            'all_holdings': all_holdings,
            'regular_holdings': regular_holdings,
            'pledged_holdings': pledged_holdings,
            'demat_holdings': demat_holdings,
            'total_holdings': len(all_holdings),
            'comprehensive_summary': comprehensive_summary,
            'raw_data': holdings_data,
            'timestamp': datetime.now(UTC).isoformat(),
            'api_key_id': _rate_limit_permit['api_key_id'],
            'response_time': time.time()
        }
        
        logger.info(
            f"✅ All holdings fetched: {len(all_holdings)} total "
            f"({len(regular_holdings)} regular, {len(pledged_holdings)} pledged), "
            f"Portfolio: ₹{total_current_value:.2f}"
        )
        
        return result
        
    except Exception as e:
        logger.error(f"❌ All holdings fetch failed: {e}")
        
        # Create error response
        error_result = {
            'success': False,
            'all_holdings': [],
            'total_holdings': 0,
            'error': str(e),
            'timestamp': datetime.now(UTC).isoformat()
        }
        
        # Re-raise as AllHoldingError for consistent error handling
        if isinstance(e, AllHoldingError):
            raise
        else:
            raise AllHoldingError(f"All holdings fetch failed: {e}")

def _process_all_holding_data(holding: Dict[str, Any]) -> Dict[str, Any]:
    """
    Process and clean raw all holdings data from Angel One API.
    
    Args:
        holding: Raw holding data from API
        
    Returns:
        Dict: Cleaned and enhanced holding data
    """
    try:
        # Core holding fields
        processed = {
            'tradingsymbol': holding.get('tradingsymbol', ''),
            'exchange': holding.get('exchange', ''),
            'instrumenttype': holding.get('instrumenttype', ''),
            'producttype': holding.get('producttype', ''),
            'symboltoken': holding.get('symboltoken', ''),
            'isin': holding.get('isin', ''),
            
            # Quantity and price fields (with null safety)
            'quantity': int(holding.get('quantity') or 0),
            'averageprice': float(holding.get('averageprice') or 0),
            'ltp': float(holding.get('ltp') or 0),
            'close': float(holding.get('close') or 0),
            
            # P&L fields (with null safety)
            'pnl': float(holding.get('pnl') or 0),
            'pnlpercentage': float(holding.get('pnlpercentage') or 0),
            
            # Additional fields specific to getAllHolding
            'collateraltype': holding.get('collateraltype', ''),
            'collateralquantity': int(holding.get('collateralquantity') or 0),
            'haircut': float(holding.get('haircut') or 0),
            't1quantity': int(holding.get('t1quantity') or 0),
            'symbolname': holding.get('symbolname', ''),
            'precision': int(holding.get('precision') or 2),
            
            # Enhanced fields for getAllHolding (with null safety)
            'pledged_quantity': int(holding.get('pledgedquantity') or 0),
            'holding_type': holding.get('holdingtype', 'DEMAT'),
            'auth_quantity': int(holding.get('authquantity') or 0),
            'selling_quantity': int(holding.get('sellqty') or 0),
            'buying_quantity': int(holding.get('buyqty') or 0)
        }
        
        # Calculate derived fields
        processed['invested_amount'] = processed['quantity'] * processed['averageprice']
        processed['current_value'] = processed['quantity'] * processed['ltp']
        processed['unrealized_pnl'] = processed['current_value'] - processed['invested_amount']
        
        # Calculate percentage returns
        if processed['averageprice'] > 0:
            processed['return_percentage'] = (
                (processed['ltp'] - processed['averageprice']) / processed['averageprice']
            ) * 100
        else:
            processed['return_percentage'] = 0.0
        
        # Calculate day change
        if processed['close'] > 0:
            processed['day_change'] = processed['ltp'] - processed['close']
            processed['day_change_pct'] = (processed['day_change'] / processed['close']) * 100
        else:
            processed['day_change'] = 0.0
            processed['day_change_pct'] = 0.0
        
        # Pledged analysis
        processed['is_pledged'] = processed['pledged_quantity'] > 0
        processed['pledged_value'] = processed['pledged_quantity'] * processed['ltp']
        processed['free_quantity'] = processed['quantity'] - processed['pledged_quantity']
        processed['free_value'] = processed['free_quantity'] * processed['ltp']
        
        # Risk categorization
        processed['risk_category'] = _categorize_holding_risk(processed)
        processed['liquidity_category'] = _categorize_liquidity(processed)
        
        return processed
        
    except (ValueError, TypeError) as e:
        logger.warning(f"⚠️ Error processing all holdings data: {e}")
        return holding  # Return original if processing fails

def _categorize_holding_risk(holding: Dict[str, Any]) -> str:
    """Categorize holding risk based on various factors."""
    try:
        return_pct = abs(holding.get('return_percentage', 0))
        current_value = holding.get('current_value', 0)
        is_pledged = holding.get('is_pledged', False)
        
        # Enhanced risk categorization
        if is_pledged and return_pct > 30:
            return 'CRITICAL'  # Pledged holdings with high volatility
        elif return_pct > 50 or current_value > 1000000:  # >50% return or >10L value
            return 'HIGH'
        elif return_pct > 20 or current_value > 200000:  # >20% return or >2L value
            return 'MEDIUM'
        else:
            return 'LOW'
            
    except Exception:
        return 'UNKNOWN'

def _categorize_liquidity(holding: Dict[str, Any]) -> str:
    """Categorize holding liquidity."""
    try:
        symbol = holding.get('tradingsymbol', '')
        current_value = holding.get('current_value', 0)
        
        # Simple liquidity categorization (would need more data for accuracy)
        if current_value < 50000:  # < 50K
            return 'LOW'
        elif current_value < 200000:  # < 2L
            return 'MEDIUM'
        else:
            return 'HIGH'
            
    except Exception:
        return 'UNKNOWN'

def _find_largest_holding(holdings: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """Find the largest holding by value."""
    if not holdings:
        return None
    
    largest = max(holdings, key=lambda x: x.get('current_value', 0))
    return {
        'symbol': largest.get('tradingsymbol'),
        'value': largest.get('current_value', 0),
        'quantity': largest.get('quantity', 0),
        'is_pledged': largest.get('is_pledged', False)
    }

def _find_best_performer(holdings: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """Find the best performing holding by percentage return."""
    if not holdings:
        return None
    
    best = max(holdings, key=lambda x: x.get('return_percentage', -float('inf')))
    return {
        'symbol': best.get('tradingsymbol'),
        'return_pct': best.get('return_percentage', 0),
        'pnl': best.get('pnl', 0),
        'current_value': best.get('current_value', 0)
    }

def _find_worst_performer(holdings: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """Find the worst performing holding by percentage return."""
    if not holdings:
        return None
    
    worst = min(holdings, key=lambda x: x.get('return_percentage', float('inf')))
    return {
        'symbol': worst.get('tradingsymbol'),
        'return_pct': worst.get('return_percentage', 0),
        'pnl': worst.get('pnl', 0),
        'current_value': worst.get('current_value', 0)
    }

def _analyze_sectors(holdings: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Analyze sector distribution (simplified)."""
    # This would require additional data mapping symbols to sectors
    # For now, provide basic categorization
    
    equity_count = sum(1 for h in holdings if h.get('instrumenttype') == 'EQ')
    other_count = len(holdings) - equity_count
    
    return {
        'equity_holdings': equity_count,
        'other_holdings': other_count,
        'equity_percentage': (equity_count / len(holdings)) * 100 if holdings else 0,
        'diversification_score': min(len(holdings) / 10, 1.0)  # Simple diversification metric
    }

def _analyze_portfolio_risk(holdings: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Analyze overall portfolio risk."""
    if not holdings:
        return {'risk_level': 'UNKNOWN'}
    
    risk_counts = {'LOW': 0, 'MEDIUM': 0, 'HIGH': 0, 'CRITICAL': 0, 'UNKNOWN': 0}
    total_value = sum(h.get('current_value', 0) for h in holdings)
    pledged_value = sum(h.get('pledged_value', 0) for h in holdings)
    
    for holding in holdings:
        risk_category = holding.get('risk_category', 'UNKNOWN')
        risk_counts[risk_category] += 1
    
    # Calculate overall risk level
    critical_pct = risk_counts['CRITICAL'] / len(holdings) * 100
    high_pct = risk_counts['HIGH'] / len(holdings) * 100
    pledged_pct = (pledged_value / total_value) * 100 if total_value > 0 else 0
    
    if critical_pct > 10 or pledged_pct > 50:
        overall_risk = 'CRITICAL'
    elif high_pct > 30 or pledged_pct > 30:
        overall_risk = 'HIGH'
    elif high_pct > 10 or pledged_pct > 15:
        overall_risk = 'MEDIUM'
    else:
        overall_risk = 'LOW'
    
    return {
        'overall_risk_level': overall_risk,
        'risk_distribution': risk_counts,
        'pledged_percentage': pledged_pct,
        'concentration_risk': max(h.get('current_value', 0) for h in holdings) / total_value * 100 if total_value > 0 else 0
    }

def _analyze_liquidity(holdings: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Analyze portfolio liquidity."""
    if not holdings:
        return {'liquidity_level': 'UNKNOWN'}
    
    liquidity_counts = {'LOW': 0, 'MEDIUM': 0, 'HIGH': 0, 'UNKNOWN': 0}
    total_value = sum(h.get('current_value', 0) for h in holdings)
    
    for holding in holdings:
        liquidity_category = holding.get('liquidity_category', 'UNKNOWN')
        liquidity_counts[liquidity_category] += 1
    
    high_liquidity_pct = liquidity_counts['HIGH'] / len(holdings) * 100
    
    if high_liquidity_pct > 70:
        overall_liquidity = 'HIGH'
    elif high_liquidity_pct > 40:
        overall_liquidity = 'MEDIUM'
    else:
        overall_liquidity = 'LOW'
    
    return {
        'overall_liquidity_level': overall_liquidity,
        'liquidity_distribution': liquidity_counts,
        'high_liquidity_percentage': high_liquidity_pct
    }

async def get_segregated_holdings() -> Dict[str, Any]:
    """
    Get holdings segregated by type (regular vs pledged).
    
    Returns:
        Dict: Segregated holdings data
    """
    try:
        all_holdings_result = await get_all_holding()
        
        if not all_holdings_result['success']:
            return {'success': False, 'error': all_holdings_result.get('error')}
        
        return {
            'success': True,
            'regular_holdings': all_holdings_result['regular_holdings'],
            'pledged_holdings': all_holdings_result['pledged_holdings'],
            'regular_count': len(all_holdings_result['regular_holdings']),
            'pledged_count': len(all_holdings_result['pledged_holdings']),
            'segregation_summary': {
                'total_holdings': all_holdings_result['total_holdings'],
                'pledged_percentage': all_holdings_result['comprehensive_summary']['pledged_percentage']
            },
            'timestamp': all_holdings_result['timestamp']
        }
        
    except Exception as e:
        logger.error(f"❌ Segregated holdings fetch failed: {e}")
        return {'success': False, 'error': str(e)}

async def get_pledged_holdings() -> List[Dict[str, Any]]:
    """
    Get only pledged holdings.
    
    Returns:
        List: Pledged holdings
    """
    try:
        all_holdings_result = await get_all_holding()
        if all_holdings_result['success']:
            return all_holdings_result['pledged_holdings']
        return []
    except Exception as e:
        logger.error(f"❌ Pledged holdings fetch failed: {e}")
        return []

async def get_comprehensive_portfolio_analysis() -> Dict[str, Any]:
    """
    Get comprehensive portfolio analysis including all metrics.
    
    Returns:
        Dict: Complete portfolio analysis
    """
    try:
        all_holdings_result = await get_all_holding()
        
        if not all_holdings_result['success']:
            return {'success': False, 'error': all_holdings_result.get('error')}
        
        summary = all_holdings_result['comprehensive_summary']
        
        # Enhanced analysis
        analysis = {
            'success': True,
            'portfolio_overview': {
                'total_value': summary['current_value'],
                'total_invested': summary['total_invested'],
                'total_pnl': summary['total_pnl'],
                'return_percentage': summary['portfolio_return_pct'],
                'holdings_count': all_holdings_result['total_holdings']
            },
            'risk_analysis': summary['risk_analysis'],
            'liquidity_analysis': summary['liquidity_analysis'],
            'sector_analysis': summary['sector_analysis'],
            'pledged_analysis': {
                'pledged_value': summary['total_pledged_value'],
                'pledged_percentage': summary['pledged_percentage'],
                'pledged_count': summary['pledged_holdings_count']
            },
            'performance_highlights': {
                'best_performer': summary['best_performer'],
                'worst_performer': summary['worst_performer'],
                'largest_holding': summary['largest_holding']
            },
            'timestamp': all_holdings_result['timestamp']
        }
        
        return analysis
        
    except Exception as e:
        logger.error(f"❌ Comprehensive portfolio analysis failed: {e}")
        return {'success': False, 'error': str(e)}

def get_all_holding_sync() -> Dict[str, Any]:
    """
    Synchronous wrapper for get_all_holding.
    
    ⚠️ WARNING: Use async version when possible for better performance.
    This is only for compatibility with legacy code.
    """
    import asyncio
    try:
        return asyncio.run(get_all_holding())
    except Exception as e:
        logger.error(f"❌ Sync all holdings fetch failed: {e}")
        return {
            'success': False,
            'all_holdings': [],
            'total_holdings': 0,
            'error': str(e)
        }

# Backward compatibility aliases (DEPRECATED - use new names)
fetch_all_holdings = get_all_holding  # Alias for existing code
get_complete_holdings = get_all_holding  # Alias for existing code

if __name__ == "__main__":
    # Test all holdings fetching
    async def test_all_holdings():
        print("🧪 Testing Angel One All Holdings")
        print("=" * 40)
        
        try:
            # Test basic all holdings
            all_holdings = await get_all_holding()
            if all_holdings['success']:
                print(f"✅ All holdings fetched: {all_holdings['total_holdings']} holdings")
                summary = all_holdings['comprehensive_summary']
                print(f"   Total value: ₹{summary['current_value']:.2f}")
                print(f"   Regular holdings: {summary['regular_holdings_count']}")
                print(f"   Pledged holdings: {summary['pledged_holdings_count']}")
                print(f"   Pledged percentage: {summary['pledged_percentage']:.1f}%")
                print(f"   Portfolio return: {summary['portfolio_return_pct']:.2f}%")
                print(f"   Risk level: {summary['risk_analysis']['overall_risk_level']}")
                
            else:
                print(f"❌ All holdings fetch failed: {all_holdings.get('error')}")
                
        except Exception as e:
            print(f"❌ All holdings test failed: {e}")
    
    # Run test (requires rate controller to be initialized)
    print("⚠️ Note: Requires rate controller initialization for testing")
    # asyncio.run(test_all_holdings())
