"""
Angel One API: createGTTRule - Good Till Triggered Rule Creation
==============================================================

METHOD: Create GTT (Good Till Triggered) orders for automated trading
Rate Limit: 10 requests/second per API key
Priority: LOW (advanced trading feature)

Usage:
    from angel_one_api.methods.create_gtt_rule import create_gtt_rule
    
    # Create simple GTT rule
    gtt_rule = await create_gtt_rule(
        tradingsymbol="RELIANCE-EQ",
        symboltoken="2885",
        exchange="NSE",
        producttype="DELIVERY",
        transactiontype="BUY",
        price="2500.00",
        qty="10",
        triggerprice="2450.00",
        timeperiod="365"
    )

Author: AI Trading System
Rate Limit: STRICTLY ENFORCED 10 req/sec per key
"""

import time
from typing import Dict, List, Optional, Any
# Import new Angel One logger
from ..logger import get_api_logger
from datetime import datetime, UTC, timedelta

# Import our rate limiting system
from ..rate_limiter.rate_controller import get_rate_controller, rate_limited, APIPriority
from ..rate_limiter.api_limits import API_LIMITS

logger = get_api_logger("create_gtt_rule")

class GTTRuleError(Exception):
    """Raised when GTT rule creation fails."""
    pass

@rate_limited("create_gtt_rule", APIPriority.LOW)
async def create_gtt_rule(
    tradingsymbol: str,
    symboltoken: str,
    exchange: str,
    producttype: str,
    transactiontype: str,
    price: str,
    qty: str,
    triggerprice: str,
    timeperiod: str,
    _rate_limit_permit: Optional[Dict] = None
) -> Dict[str, Any]:
    """
    Create a GTT (Good Till Triggered) rule using Angel One API.
    
    Args:
        tradingsymbol: Trading symbol (e.g., "RELIANCE-EQ")
        symboltoken: Angel One symbol token
        exchange: Exchange name (NSE, BSE, NFO, MCX)
        producttype: Product type (DELIVERY, INTRADAY, etc.)
        transactiontype: Transaction type (BUY, SELL)
        price: Order price as string
        qty: Quantity as string
        triggerprice: Trigger price as string
        timeperiod: Time period in days as string
        _rate_limit_permit: Automatically provided by rate limiter
        
    Returns:
        Dict containing:
            - success: bool
            - gtt_rule_id: str (GTT rule ID if successful)
            - message: str
            - rule_details: Dict
            - response: dict (full API response)
        
    Raises:
        GTTRuleError: If GTT rule creation fails
        RateLimitExceeded: If rate limit would be exceeded
        
    Rate Limit: 10 requests/second per API key
    """
    try:
        if not _rate_limit_permit:
            raise GTTRuleError("No rate limit permit - internal error")
        
        # Get Angel One client
        from core.connections import ConnectionManager
        
        angel_client = ConnectionManager.get_smartapi_client()
        if not angel_client:
            raise GTTRuleError("Angel One API client not available")
        
        # Validate required parameters
        required_params = [
            tradingsymbol, symboltoken, exchange, producttype,
            transactiontype, price, qty, triggerprice, timeperiod
        ]
        
        if not all(required_params):
            raise GTTRuleError("All parameters are required for GTT rule creation")
        
        # Build GTT rule parameters
        gtt_params = {
            'tradingsymbol': tradingsymbol,
            'symboltoken': str(symboltoken),
            'exchange': exchange,
            'producttype': producttype,
            'transactiontype': transactiontype,
            'price': str(price),
            'qty': str(qty),
            'triggerprice': str(triggerprice),
            'timeperiod': str(timeperiod)
        }
        
        # Validate parameters
        validated_params = _validate_gtt_parameters(gtt_params)
        
        # Log GTT creation attempt
        logger.info(
            f"🎯 GTT rule creation: {validated_params['tradingsymbol']} "
            f"{validated_params['transactiontype']} {validated_params['qty']} "
            f"@ ₹{validated_params['price']} (trigger: ₹{validated_params['triggerprice']}) "
            f"using {_rate_limit_permit['api_key_id']}"
        )
        
        # Make API call with strict rate limiting already enforced
        response = angel_client.createGTTRule(validated_params)
        
        # Parse response
        if not response:
            raise GTTRuleError("Empty response from createGTTRule API")
        
        if not response.get('status'):
            error_msg = response.get('message', 'Unknown GTT creation error')
            error_code = response.get('errorcode', 'N/A')
            raise GTTRuleError(f"GTT rule creation failed: {error_msg} (Code: {error_code})")
        
        # Extract GTT rule details
        data = response.get('data', {})
        gtt_rule_id = data.get('id') or data.get('gttid') or data.get('ruleid')
        
        if not gtt_rule_id:
            raise GTTRuleError("GTT rule ID not received in response")
        
        # Create rule details
        rule_details = {
            'gtt_rule_id': gtt_rule_id,
            'symbol': validated_params['tradingsymbol'],
            'exchange': validated_params['exchange'],
            'transaction_type': validated_params['transactiontype'],
            'product_type': validated_params['producttype'],
            'quantity': validated_params['qty'],
            'price': validated_params['price'],
            'trigger_price': validated_params['triggerprice'],
            'time_period_days': validated_params['timeperiod'],
            'created_at': datetime.now(UTC).isoformat(),
            'expires_at': (datetime.now(UTC) + timedelta(days=int(validated_params['timeperiod']))).isoformat(),
            'status': 'ACTIVE'
        }
        
        # Success response
        result = {
            'success': True,
            'gtt_rule_id': gtt_rule_id,
            'message': 'GTT rule created successfully',
            'rule_details': rule_details,
            'response': response,
            'gtt_params': validated_params,
            'api_key_id': _rate_limit_permit['api_key_id'],
            'timestamp': time.time()
        }
        
        logger.info(f"✅ GTT rule created successfully: {gtt_rule_id}")
        
        return result
        
    except Exception as e:
        logger.error(f"❌ GTT rule creation failed for {tradingsymbol}: {e}")
        
        # Create error response
        error_result = {
            'success': False,
            'gtt_rule_id': None,
            'message': str(e),
            'response': None,
            'error': str(e),
            'timestamp': time.time()
        }
        
        # Re-raise as GTTRuleError for consistent error handling
        if isinstance(e, GTTRuleError):
            raise
        else:
            raise GTTRuleError(f"GTT rule creation failed: {e}")

def _validate_gtt_parameters(gtt_params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate and clean GTT rule parameters.
    
    Args:
        gtt_params: Raw GTT parameters
        
    Returns:
        Dict: Validated and cleaned parameters
        
    Raises:
        GTTRuleError: If validation fails
    """
    validated = gtt_params.copy()
    
    # Validate exchange
    valid_exchanges = ['NSE', 'BSE', 'NFO', 'MCX']
    if validated.get('exchange') not in valid_exchanges:
        raise GTTRuleError(f"Invalid exchange. Must be one of: {valid_exchanges}")
    
    # Validate transaction type
    if validated.get('transactiontype') not in ['BUY', 'SELL']:
        raise GTTRuleError("Invalid transactiontype. Must be 'BUY' or 'SELL'")
    
    # Validate product type
    valid_products = ['DELIVERY', 'INTRADAY', 'CARRYFORWARD', 'CNC', 'MIS']
    if validated.get('producttype') not in valid_products:
        raise GTTRuleError(f"Invalid producttype. Must be one of: {valid_products}")
    
    # Validate quantity
    try:
        quantity = int(validated['qty'])
        if quantity <= 0:
            raise ValueError("Quantity must be positive")
        validated['qty'] = str(quantity)
    except (ValueError, TypeError):
        raise GTTRuleError("Invalid quantity. Must be a positive integer")
    
    # Validate price
    try:
        price = float(validated['price'])
        if price <= 0:
            raise ValueError("Price must be positive")
        validated['price'] = str(price)
    except (ValueError, TypeError):
        raise GTTRuleError("Invalid price. Must be a positive number")
    
    # Validate trigger price
    try:
        trigger_price = float(validated['triggerprice'])
        if trigger_price <= 0:
            raise ValueError("Trigger price must be positive")
        validated['triggerprice'] = str(trigger_price)
    except (ValueError, TypeError):
        raise GTTRuleError("Invalid trigger price. Must be a positive number")
    
    # Validate time period
    try:
        time_period = int(validated['timeperiod'])
        if time_period <= 0 or time_period > 365:
            raise ValueError("Time period must be between 1 and 365 days")
        validated['timeperiod'] = str(time_period)
    except (ValueError, TypeError):
        raise GTTRuleError("Invalid time period. Must be between 1 and 365 days")
    
    # Validate symbol token
    if not validated.get('symboltoken'):
        raise GTTRuleError("Symbol token is required")
    
    # Validate trading symbol
    if not validated.get('tradingsymbol'):
        raise GTTRuleError("Trading symbol is required")
    
    return validated

async def create_buy_gtt_rule(
    symbol: str,
    symbol_token: str,
    trigger_price: float,
    order_price: float,
    quantity: int,
    exchange: str = "NSE",
    product_type: str = "DELIVERY",
    time_period: int = 30
) -> Dict[str, Any]:
    """
    Simplified GTT rule creation for buy orders.
    
    Args:
        symbol: Trading symbol
        symbol_token: Symbol token
        trigger_price: Price at which to trigger
        order_price: Price at which to place order
        quantity: Quantity to buy
        exchange: Exchange (default: NSE)
        product_type: Product type (default: DELIVERY)
        time_period: Days to keep rule active (default: 30)
        
    Returns:
        Dict: GTT rule creation result
    """
    return await create_gtt_rule(
        tradingsymbol=symbol,
        symboltoken=symbol_token,
        exchange=exchange,
        producttype=product_type,
        transactiontype="BUY",
        price=str(order_price),
        qty=str(quantity),
        triggerprice=str(trigger_price),
        timeperiod=str(time_period)
    )

async def create_sell_gtt_rule(
    symbol: str,
    symbol_token: str,
    trigger_price: float,
    order_price: float,
    quantity: int,
    exchange: str = "NSE",
    product_type: str = "DELIVERY",
    time_period: int = 30
) -> Dict[str, Any]:
    """
    Simplified GTT rule creation for sell orders.
    
    Args:
        symbol: Trading symbol
        symbol_token: Symbol token
        trigger_price: Price at which to trigger
        order_price: Price at which to place order
        quantity: Quantity to sell
        exchange: Exchange (default: NSE)
        product_type: Product type (default: DELIVERY)
        time_period: Days to keep rule active (default: 30)
        
    Returns:
        Dict: GTT rule creation result
    """
    return await create_gtt_rule(
        tradingsymbol=symbol,
        symboltoken=symbol_token,
        exchange=exchange,
        producttype=product_type,
        transactiontype="SELL",
        price=str(order_price),
        qty=str(quantity),
        triggerprice=str(trigger_price),
        timeperiod=str(time_period)
    )

async def create_stop_loss_gtt(
    symbol: str,
    symbol_token: str,
    stop_loss_price: float,
    quantity: int,
    exchange: str = "NSE",
    time_period: int = 30
) -> Dict[str, Any]:
    """
    Create a stop-loss GTT rule.
    
    Args:
        symbol: Trading symbol
        symbol_token: Symbol token
        stop_loss_price: Stop loss trigger price
        quantity: Quantity to sell
        exchange: Exchange (default: NSE)
        time_period: Days to keep rule active (default: 30)
        
    Returns:
        Dict: GTT rule creation result
    """
    # For stop loss, trigger and order price are usually the same
    return await create_gtt_rule(
        tradingsymbol=symbol,
        symboltoken=symbol_token,
        exchange=exchange,
        producttype="DELIVERY",
        transactiontype="SELL",
        price=str(stop_loss_price),
        qty=str(quantity),
        triggerprice=str(stop_loss_price),
        timeperiod=str(time_period)
    )

async def create_target_gtt(
    symbol: str,
    symbol_token: str,
    target_price: float,
    quantity: int,
    exchange: str = "NSE",
    time_period: int = 30
) -> Dict[str, Any]:
    """
    Create a target (profit booking) GTT rule.
    
    Args:
        symbol: Trading symbol
        symbol_token: Symbol token
        target_price: Target trigger price
        quantity: Quantity to sell
        exchange: Exchange (default: NSE)
        time_period: Days to keep rule active (default: 30)
        
    Returns:
        Dict: GTT rule creation result
    """
    # For target, trigger and order price are usually the same
    return await create_gtt_rule(
        tradingsymbol=symbol,
        symboltoken=symbol_token,
        exchange=exchange,
        producttype="DELIVERY",
        transactiontype="SELL",
        price=str(target_price),
        qty=str(quantity),
        triggerprice=str(target_price),
        timeperiod=str(time_period)
    )

async def create_bracket_gtt_rules(
    symbol: str,
    symbol_token: str,
    buy_price: float,
    quantity: int,
    stop_loss_price: float,
    target_price: float,
    exchange: str = "NSE",
    time_period: int = 30
) -> Dict[str, Any]:
    """
    Create bracket GTT rules (buy + stop loss + target).
    
    Args:
        symbol: Trading symbol
        symbol_token: Symbol token
        buy_price: Entry price
        quantity: Quantity
        stop_loss_price: Stop loss price
        target_price: Target price
        exchange: Exchange (default: NSE)
        time_period: Days to keep rules active (default: 30)
        
    Returns:
        Dict: All GTT rule creation results
    """
    try:
        results = {}
        
        # Create buy GTT rule
        buy_result = await create_buy_gtt_rule(
            symbol, symbol_token, buy_price, buy_price, quantity, exchange, "DELIVERY", time_period
        )
        results['buy_rule'] = buy_result
        
        # If buy rule successful, create stop loss and target rules
        if buy_result['success']:
            # Create stop loss GTT
            stop_loss_result = await create_stop_loss_gtt(
                symbol, symbol_token, stop_loss_price, quantity, exchange, time_period
            )
            results['stop_loss_rule'] = stop_loss_result
            
            # Create target GTT
            target_result = await create_target_gtt(
                symbol, symbol_token, target_price, quantity, exchange, time_period
            )
            results['target_rule'] = target_result
        
        # Summary
        successful_rules = sum(1 for r in results.values() if r.get('success'))
        
        bracket_result = {
            'success': successful_rules > 0,
            'rules_created': successful_rules,
            'total_rules': len(results),
            'results': results,
            'bracket_details': {
                'symbol': symbol,
                'entry_price': buy_price,
                'stop_loss': stop_loss_price,
                'target': target_price,
                'quantity': quantity,
                'risk_reward_ratio': (target_price - buy_price) / (buy_price - stop_loss_price) if buy_price > stop_loss_price else 0
            }
        }
        
        return bracket_result
        
    except Exception as e:
        logger.error(f"❌ Bracket GTT creation failed for {symbol}: {e}")
        return {'success': False, 'error': str(e)}

def create_gtt_rule_sync(
    tradingsymbol: str,
    symboltoken: str,
    exchange: str,
    producttype: str,
    transactiontype: str,
    price: str,
    qty: str,
    triggerprice: str,
    timeperiod: str
) -> Dict[str, Any]:
    """
    Synchronous wrapper for create_gtt_rule.
    
    ⚠️ WARNING: Use async version when possible for better performance.
    This is only for compatibility with legacy code.
    """
    import asyncio
    try:
        return asyncio.run(create_gtt_rule(
            tradingsymbol, symboltoken, exchange, producttype,
            transactiontype, price, qty, triggerprice, timeperiod
        ))
    except Exception as e:
        logger.error(f"❌ Sync GTT rule creation failed for {tradingsymbol}: {e}")
        return {
            'success': False,
            'gtt_rule_id': None,
            'message': str(e),
            'error': str(e)
        }

# Backward compatibility aliases (DEPRECATED - use new names)
create_gtt = create_gtt_rule  # Alias for existing code
add_gtt_rule = create_gtt_rule  # Alias for existing code

if __name__ == "__main__":
    # Test GTT rule creation
    async def test_gtt_rule_creation():
        print("🧪 Testing Angel One GTT Rule Creation")
        print("=" * 40)
        print("⚠️ Note: This is a test - no real GTT rules will be created")
        
        # Test parameter validation
        test_params = {
            'tradingsymbol': 'RELIANCE-EQ',
            'symboltoken': '2885',
            'exchange': 'NSE',
            'producttype': 'DELIVERY',
            'transactiontype': 'BUY',
            'price': '2500.00',
            'qty': '10',
            'triggerprice': '2450.00',
            'timeperiod': '30'
        }
        
        try:
            validated = _validate_gtt_parameters(test_params)
            print(f"✅ Parameter validation successful")
            print(f"   Symbol: {validated['tradingsymbol']}")
            print(f"   Type: {validated['transactiontype']} {validated['qty']} @ ₹{validated['price']}")
            print(f"   Trigger: ₹{validated['triggerprice']}")
            print(f"   Period: {validated['timeperiod']} days")
        except Exception as e:
            print(f"❌ Parameter validation failed: {e}")
        
        # Test bracket GTT concept
        print(f"\n📊 Bracket GTT Example:")
        print(f"   Entry: ₹2500, Stop Loss: ₹2400, Target: ₹2700")
        risk_reward = (2700 - 2500) / (2500 - 2400)
        print(f"   Risk-Reward Ratio: 1:{risk_reward:.1f}")
        
        print("\n⚠️ Note: Actual GTT creation requires rate controller and live connection")
    
    # Run test
    import asyncio
    asyncio.run(test_gtt_rule_creation())
