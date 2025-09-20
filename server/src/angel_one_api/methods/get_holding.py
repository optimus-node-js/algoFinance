"""
Angel One API: getHolding - Holdings Data Retrieval
==================================================

CRITICAL METHOD: Portfolio holdings and investment tracking
Rate Limit: 1 request/second per API key
Priority: HIGH (essential for portfolio management)

Usage:
    from angel_one_api.methods.get_holding import get_holding
    
    # Get all holdings
    holdings = await get_holding()
    
    # Get holdings with analysis
    analyzed_holdings = await get_analyzed_holdings()
    
    # Get specific symbol holding
    symbol_holding = await get_symbol_holding("RELIANCE-EQ")

Author: AI Trading System
Rate Limit: STRICTLY ENFORCED 1 req/sec per key
"""

import time
from typing import Dict, List, Optional, Any
import logging
from datetime import datetime, UTC

# Import our rate limiting system
from ..rate_limiter.rate_controller import get_rate_controller, rate_limited, APIPriority
from ..rate_limiter.api_limits import API_LIMITS

logger = logging.getLogger(__name__)

class HoldingError(Exception):
    """Raised when holdings data fetching fails."""
    pass

@rate_limited("get_holding", APIPriority.HIGH)
async def get_holding(_rate_limit_permit: Optional[Dict] = None) -> Dict[str, Any]:
    """
    Get holdings data from Angel One API.
    
    Args:
        _rate_limit_permit: Automatically provided by rate limiter
        
    Returns:
        Dict containing:
            - success: bool
            - holdings: List of holding data
            - total_holdings: int
            - portfolio_value: float
            - total_invested: float
            - total_pnl: float
            - timestamp: str
        
    Raises:
        HoldingError: If holdings fetching fails
        RateLimitExceeded: If rate limit would be exceeded
        
    Rate Limit: 1 request/second per API key
    """
    try:
        if not _rate_limit_permit:
            raise HoldingError("No rate limit permit - internal error")
        
        # Get Angel One client
        from core.connections import ConnectionManager
        
        angel_client = ConnectionManager.get_smartapi_client()
        if not angel_client:
            raise HoldingError("Angel One API client not available")
        
        # Log request
        logger.debug(f"💼 Holdings request using {_rate_limit_permit['api_key_id']}")
        
        # Make API call with strict rate limiting already enforced
        response = angel_client.holding()
        
        # Parse response
        if not response:
            raise HoldingError("Empty response from holdings API")
        
        if not response.get('status'):
            error_msg = response.get('message', 'Unknown error')
            raise HoldingError(f"Holdings API error: {error_msg}")
        
        holdings_data = response.get('data', [])
        
        # Validate holdings data
        if not isinstance(holdings_data, list):
            raise HoldingError("Invalid holdings data format received")
        
        # Process holdings data
        processed_holdings = []
        total_invested = 0.0
        total_current_value = 0.0
        total_pnl = 0.0
        
        for holding in holdings_data:
            # Clean and validate holding data
            processed_holding = _process_holding_data(holding)
            processed_holdings.append(processed_holding)
            
            # Accumulate totals
            total_invested += processed_holding.get('invested_amount', 0)
            total_current_value += processed_holding.get('current_value', 0)
            total_pnl += processed_holding.get('pnl', 0)
        
        # Calculate portfolio metrics
        portfolio_return_pct = (
            (total_pnl / total_invested) * 100 
            if total_invested > 0 else 0
        )
        
        # Success response
        result = {
            'success': True,
            'holdings': processed_holdings,
            'total_holdings': len(processed_holdings),
            'portfolio_summary': {
                'total_invested': total_invested,
                'current_value': total_current_value,
                'total_pnl': total_pnl,
                'portfolio_return_pct': portfolio_return_pct,
                'largest_holding': _find_largest_holding(processed_holdings),
                'best_performer': _find_best_performer(processed_holdings),
                'worst_performer': _find_worst_performer(processed_holdings)
            },
            'timestamp': datetime.now(UTC).isoformat(),
            'api_key_id': _rate_limit_permit['api_key_id'],
            'response_time': time.time()
        }
        
        logger.info(f"✅ Holdings fetched: {len(processed_holdings)} holdings, Portfolio: ₹{total_current_value:.2f}")
        
        return result
        
    except Exception as e:
        logger.error(f"❌ Holdings fetch failed: {e}")
        
        # Create error response
        error_result = {
            'success': False,
            'holdings': [],
            'total_holdings': 0,
            'error': str(e),
            'timestamp': datetime.now(UTC).isoformat()
        }
        
        # Re-raise as HoldingError for consistent error handling
        if isinstance(e, HoldingError):
            raise
        else:
            raise HoldingError(f"Holdings fetch failed: {e}")

def _process_holding_data(holding: Dict[str, Any]) -> Dict[str, Any]:
    """
    Process and clean raw holding data from Angel One API.
    
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
            
            # Additional fields (with null safety)
            'collateraltype': holding.get('collateraltype', ''),
            'collateralquantity': int(holding.get('collateralquantity') or 0),
            'haircut': float(holding.get('haircut') or 0),
            't1quantity': int(holding.get('t1quantity') or 0),
            'symbolname': holding.get('symbolname', ''),
            'precision': int(holding.get('precision') or 2)
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
        
        # Portfolio weight (will be calculated later with total portfolio value)
        processed['portfolio_weight_pct'] = 0.0
        
        # Risk categorization
        processed['risk_category'] = _categorize_holding_risk(processed)
        
        return processed
        
    except (ValueError, TypeError) as e:
        logger.warning(f"⚠️ Error processing holding data: {e}")
        return holding  # Return original if processing fails

def _categorize_holding_risk(holding: Dict[str, Any]) -> str:
    """
    Categorize holding risk based on various factors.
    
    Args:
        holding: Processed holding data
        
    Returns:
        str: Risk category (LOW, MEDIUM, HIGH)
    """
    try:
        return_pct = abs(holding.get('return_percentage', 0))
        current_value = holding.get('current_value', 0)
        
        # Simple risk categorization logic
        if return_pct > 50 or current_value > 500000:  # >50% return or >5L value
            return 'HIGH'
        elif return_pct > 20 or current_value > 100000:  # >20% return or >1L value
            return 'MEDIUM'
        else:
            return 'LOW'
            
    except Exception:
        return 'UNKNOWN'

def _find_largest_holding(holdings: List[Dict[str, Any]]) -> Optional[Dict[str, str]]:
    """Find the largest holding by value."""
    if not holdings:
        return None
    
    largest = max(holdings, key=lambda x: x.get('current_value', 0))
    return {
        'symbol': largest.get('tradingsymbol'),
        'value': largest.get('current_value', 0),
        'percentage': 0  # Will be calculated with portfolio weight
    }

def _find_best_performer(holdings: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """Find the best performing holding by percentage return."""
    if not holdings:
        return None
    
    best = max(holdings, key=lambda x: x.get('return_percentage', -float('inf')))
    return {
        'symbol': best.get('tradingsymbol'),
        'return_pct': best.get('return_percentage', 0),
        'pnl': best.get('pnl', 0)
    }

def _find_worst_performer(holdings: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """Find the worst performing holding by percentage return."""
    if not holdings:
        return None
    
    worst = min(holdings, key=lambda x: x.get('return_percentage', float('inf')))
    return {
        'symbol': worst.get('tradingsymbol'),
        'return_pct': worst.get('return_percentage', 0),
        'pnl': worst.get('pnl', 0)
    }

async def get_analyzed_holdings() -> Dict[str, Any]:
    """
    Get holdings with additional analysis and portfolio weights.
    
    Returns:
        Dict: Enhanced holdings data with analysis
    """
    try:
        holdings_result = await get_holding()
        
        if not holdings_result['success']:
            return holdings_result
        
        holdings = holdings_result['holdings']
        total_portfolio_value = holdings_result['portfolio_summary']['current_value']
        
        # Calculate portfolio weights
        for holding in holdings:
            if total_portfolio_value > 0:
                holding['portfolio_weight_pct'] = (
                    (holding['current_value'] / total_portfolio_value) * 100
                )
        
        # Update largest holding percentage
        if holdings_result['portfolio_summary']['largest_holding']:
            largest = holdings_result['portfolio_summary']['largest_holding']
            largest_value = largest['value']
            largest['percentage'] = (largest_value / total_portfolio_value) * 100 if total_portfolio_value > 0 else 0
        
        # Add sector/industry analysis (would need additional data)
        holdings_result['analysis'] = {
            'concentration_risk': _analyze_concentration_risk(holdings),
            'risk_distribution': _analyze_risk_distribution(holdings),
            'performance_summary': _analyze_performance(holdings)
        }
        
        return holdings_result
        
    except Exception as e:
        logger.error(f"❌ Analyzed holdings fetch failed: {e}")
        raise HoldingError(f"Analyzed holdings fetch failed: {e}")

def _analyze_concentration_risk(holdings: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Analyze portfolio concentration risk."""
    if not holdings:
        return {'risk_level': 'UNKNOWN', 'top_holdings_pct': 0}
    
    # Sort by portfolio weight
    sorted_holdings = sorted(holdings, key=lambda x: x.get('portfolio_weight_pct', 0), reverse=True)
    
    # Top 3 holdings concentration
    top_3_pct = sum(h.get('portfolio_weight_pct', 0) for h in sorted_holdings[:3])
    
    # Risk assessment
    if top_3_pct > 60:
        risk_level = 'HIGH'
    elif top_3_pct > 40:
        risk_level = 'MEDIUM'
    else:
        risk_level = 'LOW'
    
    return {
        'risk_level': risk_level,
        'top_3_concentration_pct': top_3_pct,
        'total_holdings': len(holdings)
    }

def _analyze_risk_distribution(holdings: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Analyze risk distribution across holdings."""
    risk_counts = {'LOW': 0, 'MEDIUM': 0, 'HIGH': 0, 'UNKNOWN': 0}
    
    for holding in holdings:
        risk_category = holding.get('risk_category', 'UNKNOWN')
        risk_counts[risk_category] += 1
    
    total_holdings = len(holdings)
    
    return {
        'risk_distribution': risk_counts,
        'risk_percentages': {
            risk: (count / total_holdings) * 100 if total_holdings > 0 else 0
            for risk, count in risk_counts.items()
        }
    }

def _analyze_performance(holdings: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Analyze overall performance statistics."""
    if not holdings:
        return {}
    
    returns = [h.get('return_percentage', 0) for h in holdings]
    positive_returns = [r for r in returns if r > 0]
    negative_returns = [r for r in returns if r < 0]
    
    return {
        'avg_return_pct': sum(returns) / len(returns) if returns else 0,
        'positive_holdings_count': len(positive_returns),
        'negative_holdings_count': len(negative_returns),
        'positive_holdings_pct': (len(positive_returns) / len(holdings)) * 100,
        'best_return_pct': max(returns) if returns else 0,
        'worst_return_pct': min(returns) if returns else 0
    }

async def get_symbol_holding(symbol: str) -> Optional[Dict[str, Any]]:
    """
    Get holding data for a specific symbol.
    
    Args:
        symbol: Trading symbol (e.g., "RELIANCE-EQ")
        
    Returns:
        Dict: Holding data for symbol or None if not found
    """
    try:
        holdings_result = await get_holding()
        
        if not holdings_result['success']:
            return None
        
        # Find matching symbol
        for holding in holdings_result['holdings']:
            if holding.get('tradingsymbol') == symbol:
                return holding
        
        return None
        
    except Exception as e:
        logger.error(f"❌ Symbol holding fetch failed for {symbol}: {e}")
        return None

async def get_holdings_summary() -> Dict[str, Any]:
    """
    Get a concise summary of holdings portfolio.
    
    Returns:
        Dict: Holdings summary with key metrics
    """
    try:
        holdings_result = await get_holding()
        
        if not holdings_result['success']:
            return {'success': False, 'error': holdings_result.get('error')}
        
        summary = holdings_result['portfolio_summary'].copy()
        summary.update({
            'success': True,
            'total_holdings': holdings_result['total_holdings'],
            'timestamp': holdings_result['timestamp']
        })
        
        return summary
        
    except Exception as e:
        logger.error(f"❌ Holdings summary failed: {e}")
        return {'success': False, 'error': str(e)}

def get_holding_sync() -> Dict[str, Any]:
    """
    Synchronous wrapper for get_holding.
    
    ⚠️ WARNING: Use async version when possible for better performance.
    This is only for compatibility with legacy code.
    """
    import asyncio
    try:
        return asyncio.run(get_holding())
    except Exception as e:
        logger.error(f"❌ Sync holdings fetch failed: {e}")
        return {
            'success': False,
            'holdings': [],
            'total_holdings': 0,
            'error': str(e)
        }

# Backward compatibility aliases (DEPRECATED - use new names)
fetch_holdings = get_holding  # Alias for existing code
get_portfolio_holdings = get_holding  # Alias for existing code

if __name__ == "__main__":
    # Test holdings fetching
    async def test_holdings():
        print("🧪 Testing Angel One Holdings")
        print("=" * 40)
        
        try:
            # Test basic holdings
            holdings = await get_holding()
            if holdings['success']:
                print(f"✅ Holdings fetched: {holdings['total_holdings']} holdings")
                summary = holdings['portfolio_summary']
                print(f"   Portfolio value: ₹{summary['current_value']:.2f}")
                print(f"   Total P&L: ₹{summary['total_pnl']:.2f} ({summary['portfolio_return_pct']:.2f}%)")
                
                if summary['largest_holding']:
                    largest = summary['largest_holding']
                    print(f"   Largest holding: {largest['symbol']} (₹{largest['value']:.2f})")
                    
            else:
                print(f"❌ Holdings fetch failed: {holdings.get('error')}")
                
        except Exception as e:
            print(f"❌ Holdings test failed: {e}")
        
        try:
            # Test analyzed holdings
            analyzed = await get_analyzed_holdings()
            if analyzed['success']:
                print(f"✅ Analyzed holdings:")
                analysis = analyzed['analysis']
                print(f"   Concentration risk: {analysis['concentration_risk']['risk_level']}")
                print(f"   Positive holdings: {analysis['performance_summary']['positive_holdings_pct']:.1f}%")
            else:
                print(f"❌ Analyzed holdings failed: {analyzed.get('error')}")
                
        except Exception as e:
            print(f"❌ Analyzed holdings test failed: {e}")
    
    # Run test (requires rate controller to be initialized)
    print("⚠️ Note: Requires rate controller initialization for testing")
    # asyncio.run(test_holdings())
