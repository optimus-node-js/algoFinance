"""
Angel One API: placeOrder - Trading Order Placement
===================================================

CRITICAL METHOD: Core trading functionality - order placement
Rate Limit: 20 requests/second per API key (HIGHEST frequency)
Priority: CRITICAL

MOVED FROM: trading/execution_engine.py, order_management/oms.py
This method consolidates and improves all existing order placement logic.

Usage:
    from angel_one_api.methods.place_order import place_order
    
    # Market order
    order_result = await place_order({
        'variety': 'NORMAL',
        'tradingsymbol': 'RELIANCE-EQ',
        'symboltoken': '2885',
        'transactiontype': 'BUY',
        'exchange': 'NSE',
        'ordertype': 'MARKET',
        'producttype': 'INTRADAY',
        'duration': 'DAY',
        'quantity': '10'
    })
    
    # Limit order
    order_result = await place_order({
        'variety': 'NORMAL',
        'tradingsymbol': 'TCS-EQ',
        'symboltoken': '11536',
        'transactiontype': 'SELL',
        'exchange': 'NSE',
        'ordertype': 'LIMIT',
        'producttype': 'DELIVERY',
        'duration': 'DAY',
        'quantity': '5',
        'price': '3500.50'
    })

Author: AI Trading System
Rate Limit: STRICTLY ENFORCED 20 req/sec per key
"""

import time
from typing import Dict, List, Optional, Any
# Import new Angel One logger
from ..logger import get_api_logger
from enum import Enum

# Import our rate limiting system
from ..rate_limiter.rate_controller import get_rate_controller, rate_limited, APIPriority
from ..rate_limiter.api_limits import API_LIMITS

logger = get_api_logger("place_order")

class OrderError(Exception):
    """Raised when order placement fails."""
    pass

class OrderType(Enum):
    """Order types for Angel One."""
    MARKET = "MARKET"
    LIMIT = "LIMIT"
    STOP_LOSS = "STOPLOSS"
    STOP_LOSS_MARKET = "SL-M"

class TransactionType(Enum):
    """Transaction types."""
    BUY = "BUY"
    SELL = "SELL"

class ProductType(Enum):
    """Product types."""
    INTRADAY = "INTRADAY"
    DELIVERY = "DELIVERY"
    CARRYFORWARD = "CARRYFORWARD"

class Exchange(Enum):
    """Supported exchanges."""
    NSE = "NSE"
    BSE = "BSE"
    NFO = "NFO"
    MCX = "MCX"

@rate_limited("place_order", APIPriority.CRITICAL)
async def place_order(
    order_params: Dict[str, Any],
    _rate_limit_permit: Optional[Dict] = None
) -> Dict[str, Any]:
    """
    Place trading order using Angel One placeOrder API.
    
    Args:
        order_params: Order parameters dict containing:
            - variety: Order variety (NORMAL, STOPLOSS, AMO)
            - tradingsymbol: Trading symbol (e.g., "RELIANCE-EQ")
            - symboltoken: Angel One symbol token
            - transactiontype: BUY or SELL
            - exchange: NSE, BSE, NFO, MCX
            - ordertype: MARKET, LIMIT, STOPLOSS, SL-M
            - producttype: INTRADAY, DELIVERY, CARRYFORWARD
            - duration: DAY, IOC
            - quantity: Number of shares/lots
            - price: Price (required for LIMIT orders)
            - triggerprice: Trigger price (required for STOPLOSS orders)
        _rate_limit_permit: Automatically provided by rate limiter
        
    Returns:
        Dict containing:
            - success: bool
            - order_id: str (if successful)
            - message: str
            - response: dict (full API response)
        
    Raises:
        OrderError: If order placement fails
        RateLimitExceeded: If rate limit would be exceeded
        
    Rate Limit: 20 requests/second per API key
    """
    try:
        if not _rate_limit_permit:
            raise OrderError("No rate limit permit - internal error")
        
        # Get Angel One client
        from core.connections import ConnectionManager
        
        angel_client = ConnectionManager.get_smartapi_client()
        if not angel_client:
            raise OrderError("Angel One API client not available")
        
        # Validate required parameters
        required_params = [
            'variety', 'tradingsymbol', 'symboltoken', 'transactiontype',
            'exchange', 'ordertype', 'producttype', 'duration', 'quantity'
        ]
        
        missing_params = [param for param in required_params if param not in order_params]
        if missing_params:
            raise OrderError(f"Missing required parameters: {missing_params}")
        
        # Validate parameter values
        validated_params = _validate_order_parameters(order_params)
        
        # Log order placement attempt
        logger.info(
            f"📈 Order placement: {validated_params['transactiontype']} "
            f"{validated_params['quantity']} {validated_params['tradingsymbol']} "
            f"@ {validated_params.get('ordertype')} using {_rate_limit_permit['api_key_id']}"
        )
        
        # Make API call with strict rate limiting already enforced
        response = angel_client.placeOrder(validated_params)
        
        # Parse response
        if not response:
            raise OrderError("Empty response from placeOrder API")
        
        if not response.get('status'):
            error_msg = response.get('message', 'Unknown order error')
            error_code = response.get('errorcode', 'N/A')
            raise OrderError(f"Order placement failed: {error_msg} (Code: {error_code})")
        
        # Extract order details
        data = response.get('data', {})
        order_id = data.get('orderid')
        
        if not order_id:
            raise OrderError("Order ID not received in response")
        
        # Success response
        result = {
            'success': True,
            'order_id': order_id,
            'message': 'Order placed successfully',
            'response': response,
            'order_params': validated_params,
            'api_key_id': _rate_limit_permit['api_key_id'],
            'timestamp': time.time()
        }
        
        logger.info(f"✅ Order placed successfully: ID {order_id}")
        
        return result
        
    except Exception as e:
        logger.error(f"❌ Order placement failed: {e}")
        
        # Create error response
        error_result = {
            'success': False,
            'order_id': None,
            'message': str(e),
            'response': None,
            'order_params': order_params,
            'error': str(e),
            'timestamp': time.time()
        }
        
        # Re-raise as OrderError for consistent error handling
        if isinstance(e, OrderError):
            raise
        else:
            raise OrderError(f"Order placement failed: {e}")

def _validate_order_parameters(order_params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate and clean order parameters.
    
    Args:
        order_params: Raw order parameters
        
    Returns:
        Dict: Validated and cleaned parameters
        
    Raises:
        OrderError: If validation fails
    """
    validated = order_params.copy()
    
    # Validate variety
    valid_varieties = ['NORMAL', 'STOPLOSS', 'AMO']
    if validated.get('variety') not in valid_varieties:
        raise OrderError(f"Invalid variety. Must be one of: {valid_varieties}")
    
    # Validate transaction type
    if validated.get('transactiontype') not in ['BUY', 'SELL']:
        raise OrderError("Invalid transactiontype. Must be 'BUY' or 'SELL'")
    
    # Validate exchange
    valid_exchanges = ['NSE', 'BSE', 'NFO', 'MCX']
    if validated.get('exchange') not in valid_exchanges:
        raise OrderError(f"Invalid exchange. Must be one of: {valid_exchanges}")
    
    # Validate order type
    valid_order_types = ['MARKET', 'LIMIT', 'STOPLOSS', 'SL-M']
    if validated.get('ordertype') not in valid_order_types:
        raise OrderError(f"Invalid ordertype. Must be one of: {valid_order_types}")
    
    # Validate product type
    valid_product_types = ['INTRADAY', 'DELIVERY', 'CARRYFORWARD']
    if validated.get('producttype') not in valid_product_types:
        raise OrderError(f"Invalid producttype. Must be one of: {valid_product_types}")
    
    # Validate duration
    valid_durations = ['DAY', 'IOC']
    if validated.get('duration') not in valid_durations:
        raise OrderError(f"Invalid duration. Must be one of: {valid_durations}")
    
    # Validate quantity
    try:
        quantity = int(validated['quantity'])
        if quantity <= 0:
            raise ValueError("Quantity must be positive")
        validated['quantity'] = str(quantity)
    except (ValueError, TypeError):
        raise OrderError("Invalid quantity. Must be a positive integer")
    
    # Validate price for LIMIT orders
    if validated.get('ordertype') == 'LIMIT':
        if 'price' not in validated:
            raise OrderError("Price is required for LIMIT orders")
        try:
            price = float(validated['price'])
            if price <= 0:
                raise ValueError("Price must be positive")
            validated['price'] = str(price)
        except (ValueError, TypeError):
            raise OrderError("Invalid price. Must be a positive number")
    
    # Validate trigger price for STOPLOSS orders
    if validated.get('ordertype') in ['STOPLOSS', 'SL-M']:
        if 'triggerprice' not in validated:
            raise OrderError("Triggerprice is required for STOPLOSS orders")
        try:
            trigger_price = float(validated['triggerprice'])
            if trigger_price <= 0:
                raise ValueError("Trigger price must be positive")
            validated['triggerprice'] = str(trigger_price)
        except (ValueError, TypeError):
            raise OrderError("Invalid triggerprice. Must be a positive number")
    
    # Ensure symbol token is string
    validated['symboltoken'] = str(validated['symboltoken'])
    
    return validated

async def place_market_order(
    symbol: str,
    symbol_token: str,
    transaction_type: str,
    quantity: int,
    exchange: str = "NSE",
    product_type: str = "INTRADAY"
) -> Dict[str, Any]:
    """
    Simplified market order placement.
    
    Args:
        symbol: Trading symbol (e.g., "RELIANCE-EQ")
        symbol_token: Angel One symbol token
        transaction_type: "BUY" or "SELL"
        quantity: Number of shares
        exchange: Exchange name (default: "NSE")
        product_type: Product type (default: "INTRADAY")
        
    Returns:
        Dict: Order placement result
    """
    order_params = {
        'variety': 'NORMAL',
        'tradingsymbol': symbol,
        'symboltoken': symbol_token,
        'transactiontype': transaction_type,
        'exchange': exchange,
        'ordertype': 'MARKET',
        'producttype': product_type,
        'duration': 'DAY',
        'quantity': str(quantity)
    }
    
    return await place_order(order_params)

async def place_limit_order(
    symbol: str,
    symbol_token: str,
    transaction_type: str,
    quantity: int,
    price: float,
    exchange: str = "NSE",
    product_type: str = "INTRADAY"
) -> Dict[str, Any]:
    """
    Simplified limit order placement.
    
    Args:
        symbol: Trading symbol (e.g., "RELIANCE-EQ")
        symbol_token: Angel One symbol token
        transaction_type: "BUY" or "SELL"
        quantity: Number of shares
        price: Limit price
        exchange: Exchange name (default: "NSE")
        product_type: Product type (default: "INTRADAY")
        
    Returns:
        Dict: Order placement result
    """
    order_params = {
        'variety': 'NORMAL',
        'tradingsymbol': symbol,
        'symboltoken': symbol_token,
        'transactiontype': transaction_type,
        'exchange': exchange,
        'ordertype': 'LIMIT',
        'producttype': product_type,
        'duration': 'DAY',
        'quantity': str(quantity),
        'price': str(price)
    }
    
    return await place_order(order_params)

async def place_stop_loss_order(
    symbol: str,
    symbol_token: str,
    transaction_type: str,
    quantity: int,
    trigger_price: float,
    exchange: str = "NSE",
    product_type: str = "INTRADAY"
) -> Dict[str, Any]:
    """
    Simplified stop loss order placement.
    
    Args:
        symbol: Trading symbol (e.g., "RELIANCE-EQ")
        symbol_token: Angel One symbol token
        transaction_type: "BUY" or "SELL"
        quantity: Number of shares
        trigger_price: Stop loss trigger price
        exchange: Exchange name (default: "NSE")
        product_type: Product type (default: "INTRADAY")
        
    Returns:
        Dict: Order placement result
    """
    order_params = {
        'variety': 'STOPLOSS',
        'tradingsymbol': symbol,
        'symboltoken': symbol_token,
        'transactiontype': transaction_type,
        'exchange': exchange,
        'ordertype': 'SL-M',
        'producttype': product_type,
        'duration': 'DAY',
        'quantity': str(quantity),
        'triggerprice': str(trigger_price)
    }
    
    return await place_order(order_params)

def place_order_sync(order_params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Synchronous wrapper for place_order.
    
    ⚠️ WARNING: Use async version when possible for better performance.
    This is only for compatibility with legacy code.
    """
    import asyncio
    try:
        return asyncio.run(place_order(order_params))
    except Exception as e:
        logger.error(f"❌ Sync order placement failed: {e}")
        return {
            'success': False,
            'order_id': None,
            'message': str(e),
            'error': str(e)
        }

# Backward compatibility aliases (DEPRECATED - use new names)
execute_order = place_order  # Alias for existing code
submit_order = place_order   # Alias for existing code

if __name__ == "__main__":
    # Test order placement
    async def test_order_placement():
        print("🧪 Testing Angel One Order Placement")
        print("=" * 40)
        print("⚠️ Note: This is a test - no real orders will be placed")
        
        # Test market order parameters
        market_order = {
            'variety': 'NORMAL',
            'tradingsymbol': 'RELIANCE-EQ',
            'symboltoken': '2885',
            'transactiontype': 'BUY',
            'exchange': 'NSE',
            'ordertype': 'MARKET',
            'producttype': 'INTRADAY',
            'duration': 'DAY',
            'quantity': '1'
        }
        
        # Test parameter validation
        try:
            validated = _validate_order_parameters(market_order)
            print(f"✅ Parameter validation successful")
            print(f"   Symbol: {validated['tradingsymbol']}")
            print(f"   Type: {validated['transactiontype']} {validated['ordertype']}")
            print(f"   Quantity: {validated['quantity']}")
        except Exception as e:
            print(f"❌ Parameter validation failed: {e}")
        
        print("\n⚠️ Note: Actual order placement requires rate controller and live connection")
    
    # Run test
    import asyncio
    asyncio.run(test_order_placement())
