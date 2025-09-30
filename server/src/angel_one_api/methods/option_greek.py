"""
Angel One API: optionGreek - Options Greeks Calculation
======================================================

METHOD: Calculate Options Greeks (Delta, Gamma, Theta, Vega, Rho)
Rate Limit: 1 request/second per API key
Priority: MEDIUM (options trading support)

Usage:
    from angel_one_api.methods.option_greek import option_greek
    
    # Calculate Greeks for option
    greeks = await option_greek(
        exchange="NFO",
        tradingsymbol="NIFTY22DEC17000CE",
        symboltoken="12345"
    )

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

logger = get_api_logger("option_greek")

class OptionGreekError(Exception):
    """Raised when option Greek calculation fails."""
    pass

@idempotency_wrapper(method_type="market", ttl=300, cache_response=True) if IDEMPOTENCY_AVAILABLE else lambda x: x
@rate_limited("option_greek", APIPriority.MEDIUM)
async def option_greek(
    exchange: str,
    tradingsymbol: str,
    symboltoken: str,
    _rate_limit_permit: Optional[Dict] = None
) -> Dict[str, Any]:
    """
    Calculate Options Greeks using Angel One API.
    
    Args:
        exchange: Exchange name (NFO for options)
        tradingsymbol: Option trading symbol (e.g., "NIFTY22DEC17000CE")
        symboltoken: Angel One symbol token for the option
        _rate_limit_permit: Automatically provided by rate limiter
        
    Returns:
        Dict containing:
            - success: bool
            - greeks: Dict of Greek values
            - option_info: Dict
            - calculations: Dict
            - timestamp: str
        
    Raises:
        OptionGreekError: If Greek calculation fails
        RateLimitExceeded: If rate limit would be exceeded
        
    Rate Limit: 1 request/second per API key
    """
    try:
        if not _rate_limit_permit:
            raise OptionGreekError("No rate limit permit - internal error")
        
        # Get Angel One client
        # Use interface to get SmartAPI client
        from core.connections import ConnectionManager
        angel_client = ConnectionManager.get_smartapi_client()
        
        # angel_client already set above
        if not angel_client:
            raise OptionGreekError("Angel One API client not available")
        
        # Validate parameters
        if not all([exchange, tradingsymbol, symboltoken]):
            raise OptionGreekError("Exchange, tradingsymbol, and symboltoken are required")
        
        # Validate that this is an options symbol
        if not _is_option_symbol(tradingsymbol):
            raise OptionGreekError("Trading symbol does not appear to be an option")
        
        # Log request
        logger.debug(f"📊 Option Greeks request: {tradingsymbol} using {_rate_limit_permit['api_key_id']}")
        
        # Make API call with strict rate limiting already enforced
        response = angel_client.optionGreek(
            exchange=exchange,
            tradingsymbol=tradingsymbol,
            symboltoken=symboltoken
        )
        
        # Parse response
        if not response:
            raise OptionGreekError("Empty response from optionGreek API")
        
        if not response.get('status'):
            error_msg = response.get('message', 'Unknown error')
            raise OptionGreekError(f"Option Greek API error: {error_msg}")
        
        greek_data = response.get('data', {})
        
        # Process Greek data
        processed_greeks = _process_greek_data(greek_data)
        option_info = _extract_option_info(tradingsymbol, greek_data)
        calculations = _calculate_additional_metrics(processed_greeks, option_info)
        
        # Success response
        result = {
            'success': True,
            'greeks': processed_greeks,
            'option_info': option_info,
            'calculations': calculations,
            'symbol_info': {
                'exchange': exchange,
                'tradingsymbol': tradingsymbol,
                'symboltoken': symboltoken
            },
            'raw_data': greek_data,
            'timestamp': datetime.now(UTC).isoformat(),
            'api_key_id': _rate_limit_permit['api_key_id'],
            'response_time': time.time()
        }
        
        logger.info(f"✅ Option Greeks calculated: {tradingsymbol}")
        
        return result
        
    except Exception as e:
        logger.error(f"❌ Option Greek calculation failed for {tradingsymbol}: {e}")
        
        # Create error response
        error_result = {
            'success': False,
            'greeks': {},
            'error': str(e),
            'timestamp': datetime.now(UTC).isoformat()
        }
        
        # Re-raise as OptionGreekError for consistent error handling
        if isinstance(e, OptionGreekError):
            raise
        else:
            raise OptionGreekError(f"Option Greek calculation failed: {e}")

def _is_option_symbol(tradingsymbol: str) -> bool:
    """Check if trading symbol appears to be an option."""
    symbol = tradingsymbol.upper()
    # Common option suffixes
    option_indicators = ['CE', 'PE', 'CALL', 'PUT']
    return any(indicator in symbol for indicator in option_indicators)

def _process_greek_data(greek_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Process and clean raw Greek data from Angel One API.
    
    Args:
        greek_data: Raw Greek data from API
        
    Returns:
        Dict: Cleaned Greek values
    """
    try:
        processed = {
            'delta': float(greek_data.get('delta', 0)),
            'gamma': float(greek_data.get('gamma', 0)),
            'theta': float(greek_data.get('theta', 0)),
            'vega': float(greek_data.get('vega', 0)),
            'rho': float(greek_data.get('rho', 0)),
            'iv': float(greek_data.get('iv', 0)),  # Implied Volatility
            'premium': float(greek_data.get('premium', 0)),
            'strike_price': float(greek_data.get('strikeprice', 0)),
            'underlying_price': float(greek_data.get('underlyingprice', 0)),
            'time_to_expiry': float(greek_data.get('timetoexpiry', 0))
        }
        
        return processed
        
    except (ValueError, TypeError) as e:
        logger.warning(f"⚠️ Error processing Greek data: {e}")
        return greek_data

def _extract_option_info(tradingsymbol: str, greek_data: Dict[str, Any]) -> Dict[str, Any]:
    """Extract option information from symbol and data."""
    try:
        # Parse option symbol to extract information
        option_info = {
            'symbol': tradingsymbol,
            'underlying': _extract_underlying_symbol(tradingsymbol),
            'option_type': _extract_option_type(tradingsymbol),
            'strike_price': float(greek_data.get('strikeprice', 0)),
            'expiry_date': greek_data.get('expirydate', ''),
            'premium': float(greek_data.get('premium', 0)),
            'implied_volatility': float(greek_data.get('iv', 0)),
            'underlying_price': float(greek_data.get('underlyingprice', 0))
        }
        
        # Calculate moneyness
        if option_info['strike_price'] > 0 and option_info['underlying_price'] > 0:
            option_info['moneyness'] = _calculate_moneyness(
                option_info['underlying_price'],
                option_info['strike_price'],
                option_info['option_type']
            )
        else:
            option_info['moneyness'] = 'UNKNOWN'
        
        return option_info
        
    except Exception as e:
        logger.warning(f"⚠️ Error extracting option info: {e}")
        return {'symbol': tradingsymbol, 'error': str(e)}

def _extract_underlying_symbol(tradingsymbol: str) -> str:
    """Extract underlying symbol from option symbol."""
    # Basic extraction - would need more sophisticated parsing for real use
    symbol = tradingsymbol.upper()
    if 'NIFTY' in symbol:
        return 'NIFTY'
    elif 'BANKNIFTY' in symbol:
        return 'BANKNIFTY'
    else:
        # Extract first part before numbers/CE/PE
        import re
        match = re.match(r'^([A-Z]+)', symbol)
        return match.group(1) if match else 'UNKNOWN'

def _extract_option_type(tradingsymbol: str) -> str:
    """Extract option type from symbol."""
    symbol = tradingsymbol.upper()
    if 'CE' in symbol or 'CALL' in symbol:
        return 'CALL'
    elif 'PE' in symbol or 'PUT' in symbol:
        return 'PUT'
    else:
        return 'UNKNOWN'

def _calculate_moneyness(underlying_price: float, strike_price: float, option_type: str) -> str:
    """Calculate option moneyness."""
    if underlying_price <= 0 or strike_price <= 0:
        return 'UNKNOWN'
    
    if option_type == 'CALL':
        if underlying_price > strike_price:
            return 'ITM'  # In The Money
        elif underlying_price == strike_price:
            return 'ATM'  # At The Money
        else:
            return 'OTM'  # Out of The Money
    elif option_type == 'PUT':
        if underlying_price < strike_price:
            return 'ITM'
        elif underlying_price == strike_price:
            return 'ATM'
        else:
            return 'OTM'
    else:
        return 'UNKNOWN'

def _calculate_additional_metrics(greeks: Dict[str, Any], option_info: Dict[str, Any]) -> Dict[str, Any]:
    """Calculate additional option metrics."""
    try:
        calculations = {}
        
        # Delta-adjusted exposure
        if greeks.get('delta') and option_info.get('premium'):
            calculations['delta_adjusted_exposure'] = greeks['delta'] * option_info['premium']
        
        # Gamma exposure
        if greeks.get('gamma') and option_info.get('premium'):
            calculations['gamma_exposure'] = greeks['gamma'] * option_info['premium'] * 0.5
        
        # Theta decay per day
        if greeks.get('theta'):
            calculations['daily_theta_decay'] = abs(greeks['theta'])
        
        # Vega sensitivity (1% volatility change)
        if greeks.get('vega'):
            calculations['vega_sensitivity_1pct'] = greeks['vega'] * 0.01
        
        # Time decay percentage
        if option_info.get('premium') and greeks.get('theta'):
            calculations['time_decay_percentage'] = (abs(greeks['theta']) / option_info['premium']) * 100
        
        # Intrinsic and time value
        if option_info.get('premium') and option_info.get('underlying_price') and option_info.get('strike_price'):
            intrinsic_value = _calculate_intrinsic_value(
                option_info['underlying_price'],
                option_info['strike_price'],
                option_info['option_type']
            )
            calculations['intrinsic_value'] = intrinsic_value
            calculations['time_value'] = max(0, option_info['premium'] - intrinsic_value)
        
        return calculations
        
    except Exception as e:
        logger.warning(f"⚠️ Error calculating additional metrics: {e}")
        return {}

def _calculate_intrinsic_value(underlying_price: float, strike_price: float, option_type: str) -> float:
    """Calculate intrinsic value of option."""
    if option_type == 'CALL':
        return max(0, underlying_price - strike_price)
    elif option_type == 'PUT':
        return max(0, strike_price - underlying_price)
    else:
        return 0

async def get_option_chain_greeks(
    underlying_symbol: str,
    option_symbols: List[str],
    batch_delay: float = 1.0  # 1 req/sec = 1s between requests
) -> Dict[str, Dict[str, Any]]:
    """
    Get Greeks for multiple options in an option chain.
    
    Args:
        underlying_symbol: Underlying symbol name
        option_symbols: List of option trading symbols
        batch_delay: Delay between requests
        
    Returns:
        Dict: Symbol -> Greeks mapping
    """
    if not option_symbols:
        return {}
    
    logger.info(f"📊 Option chain Greeks for {underlying_symbol}: {len(option_symbols)} options")
    
    results = {}
    
    for i, symbol in enumerate(option_symbols):
        batch_start_time = time.time()
        
        try:
            # Note: Would need actual symbol tokens for real implementation
            greek_result = await option_greek("NFO", symbol, "0")  # Placeholder token
            results[symbol] = greek_result
            
            logger.debug(f"✅ Greeks {i+1}/{len(option_symbols)}: {symbol}")
            
        except Exception as e:
            logger.warning(f"⚠️ Greeks calculation failed for {symbol}: {e}")
            results[symbol] = {'success': False, 'error': str(e)}
        
        # Rate limiting delay
        if i < len(option_symbols) - 1:
            elapsed = time.time() - batch_start_time
            if elapsed < batch_delay:
                await asyncio.sleep(batch_delay - elapsed)
    
    successful_count = sum(1 for r in results.values() if r.get('success'))
    logger.info(f"✅ Option chain Greeks complete: {successful_count}/{len(option_symbols)} successful")
    
    return results

async def analyze_option_portfolio_greeks(option_positions: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Analyze portfolio-level Greeks for multiple option positions.
    
    Args:
        option_positions: List of position dicts with symbol, quantity, greeks
        
    Returns:
        Dict: Portfolio Greeks analysis
    """
    try:
        portfolio_greeks = {
            'total_delta': 0,
            'total_gamma': 0,
            'total_theta': 0,
            'total_vega': 0,
            'total_rho': 0
        }
        
        position_count = 0
        total_premium = 0
        
        for position in option_positions:
            quantity = position.get('quantity', 0)
            greeks = position.get('greeks', {})
            premium = position.get('premium', 0)
            
            if greeks and quantity:
                portfolio_greeks['total_delta'] += greeks.get('delta', 0) * quantity
                portfolio_greeks['total_gamma'] += greeks.get('gamma', 0) * quantity
                portfolio_greeks['total_theta'] += greeks.get('theta', 0) * quantity
                portfolio_greeks['total_vega'] += greeks.get('vega', 0) * quantity
                portfolio_greeks['total_rho'] += greeks.get('rho', 0) * quantity
                
                total_premium += premium * abs(quantity)
                position_count += 1
        
        # Calculate portfolio metrics
        portfolio_analysis = {
            'success': True,
            'portfolio_greeks': portfolio_greeks,
            'position_count': position_count,
            'total_premium_exposure': total_premium,
            'risk_metrics': {
                'delta_neutral': abs(portfolio_greeks['total_delta']) < 0.1,
                'gamma_risk': abs(portfolio_greeks['total_gamma']),
                'theta_decay_daily': abs(portfolio_greeks['total_theta']),
                'vega_volatility_risk': abs(portfolio_greeks['total_vega'])
            },
            'recommendations': _get_portfolio_recommendations(portfolio_greeks)
        }
        
        return portfolio_analysis
        
    except Exception as e:
        logger.error(f"❌ Portfolio Greeks analysis failed: {e}")
        return {'success': False, 'error': str(e)}

def _get_portfolio_recommendations(portfolio_greeks: Dict[str, float]) -> List[str]:
    """Get recommendations based on portfolio Greeks."""
    recommendations = []
    
    delta = portfolio_greeks.get('total_delta', 0)
    gamma = portfolio_greeks.get('total_gamma', 0)
    theta = portfolio_greeks.get('total_theta', 0)
    vega = portfolio_greeks.get('total_vega', 0)
    
    if abs(delta) > 10:
        recommendations.append(f"High delta exposure ({delta:.2f}) - consider hedging")
    
    if abs(gamma) > 5:
        recommendations.append(f"High gamma risk ({gamma:.2f}) - monitor closely")
    
    if theta < -50:
        recommendations.append(f"High time decay ({theta:.2f}) - theta working against you")
    
    if abs(vega) > 20:
        recommendations.append(f"High volatility risk ({vega:.2f}) - sensitive to IV changes")
    
    if not recommendations:
        recommendations.append("Portfolio Greeks within acceptable ranges")
    
    return recommendations

def option_greek_sync(exchange: str, tradingsymbol: str, symboltoken: str) -> Dict[str, Any]:
    """
    Synchronous wrapper for option_greek.
    
    ⚠️ WARNING: Use async version when possible for better performance.
    This is only for compatibility with legacy code.
    """
    import asyncio
    try:
        return asyncio.run(option_greek(exchange, tradingsymbol, symboltoken))
    except Exception as e:
        logger.error(f"❌ Sync option Greek calculation failed for {tradingsymbol}: {e}")
        return {
            'success': False,
            'greeks': {},
            'error': str(e)
        }

# Backward compatibility aliases (DEPRECATED - use new names)
calculate_greeks = option_greek  # Alias for existing code
get_option_greeks = option_greek  # Alias for existing code

if __name__ == "__main__":
    # Test option Greek calculation
    async def test_option_greeks():
        print("🧪 Testing Angel One Option Greeks")
        print("=" * 40)
        
        # Test option symbol validation
        test_symbols = ["NIFTY22DEC17000CE", "BANKNIFTY22DEC40000PE", "RELIANCE22DEC2500CE"]
        
        for symbol in test_symbols:
            is_option = _is_option_symbol(symbol)
            option_type = _extract_option_type(symbol)
            underlying = _extract_underlying_symbol(symbol)
            
            print(f"📊 Symbol: {symbol}")
            print(f"   Is Option: {is_option}")
            print(f"   Type: {option_type}")
            print(f"   Underlying: {underlying}")
        
        # Test moneyness calculation
        print(f"\n💰 Moneyness Examples:")
        examples = [
            (17500, 17000, "CALL", "ITM"),
            (17000, 17000, "CALL", "ATM"),
            (16500, 17000, "CALL", "OTM"),
            (16500, 17000, "PUT", "ITM")
        ]
        
        for underlying, strike, opt_type, expected in examples:
            moneyness = _calculate_moneyness(underlying, strike, opt_type)
            print(f"   {opt_type} {strike} @ {underlying}: {moneyness} (expected: {expected})")
        
        print("\n⚠️ Note: Actual Greek calculation requires valid option symbols and live connection")
    
    # Run test
    import asyncio
    asyncio.run(test_option_greeks())
