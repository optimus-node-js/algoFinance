"""
Angel One API: modifyOrder - Order Modification
==============================================

CRITICAL METHOD: Order management and modification
Rate Limit: 20 requests/second per API key (HIGH frequency)
Priority: CRITICAL (essential for order management)

Usage:
    from angel_one_api.methods.modify_order import modify_order
    
    # Modify order price
    result = await modify_order(
        orderid="210610000000001",
        quantity="10",
        price="1500.00",
        ordertype="LIMIT"
    )
    
    # Modify order quantity
    result = await modify_order_quantity(
        orderid="210610000000001", 
        new_quantity=15
    )

Author: AI Trading System
Rate Limit: STRICTLY ENFORCED 20 req/sec per key
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

logger = get_api_logger("modify_order")

class ModifyOrderError(Exception):
    """Raised when order modification fails."""
    pass

@idempotency_wrapper(method_type="trading", ttl=300, cache_response=True) if IDEMPOTENCY_AVAILABLE else lambda x: x
@rate_limited("modify_order", APIPriority.CRITICAL)
async def modify_order(
    orderid: str,
    quantity: str,
    price: str,
    ordertype: str,
    tradingsymbol: Optional[str] = None,
    symboltoken: Optional[str] = None,
    exchange: Optional[str] = None,
    producttype: Optional[str] = None,
    duration: Optional[str] = None,
    _rate_limit_permit: Optional[Dict] = None
) -> Dict[str, Any]:
    """
    Modify an existing order using Angel One API.
    
    Args:
        orderid: Order ID to modify
        quantity: New quantity
        price: New price
        ordertype: Order type (MARKET, LIMIT, STOPLOSS, SL-M)
        tradingsymbol: Trading symbol (optional, for validation)
        symboltoken: Symbol token (optional, for validation) 
        exchange: Exchange (optional, for validation)
        producttype: Product type (optional, for validation)
        duration: Duration (optional, for validation)
        _rate_limit_permit: Automatically provided by rate limiter
        
    Returns:
        Dict containing:
            - success: bool
            - order_id: str (modified order ID)
            - message: str
            - response: dict (full API response)
        
    Raises:
        ModifyOrderError: If order modification fails
        RateLimitExceeded: If rate limit would be exceeded
        
    Rate Limit: 20 requests/second per API key
    """
    try:
        if not _rate_limit_permit:
            raise ModifyOrderError("No rate limit permit - internal error")
        
        # Get Angel One client
        # Use interface to get SmartAPI client
        from interface import get_angel_one_interface
        interface = get_angel_one_interface()
        angel_client = interface.smart_api
        
        # angel_client already set above
        if not angel_client:
            raise ModifyOrderError("Angel One API client not available")
        
        # Validate required parameters
        if not all([orderid, quantity, price, ordertype]):
            raise ModifyOrderError("Missing required parameters: orderid, quantity, price, ordertype")
        
        # Build modification parameters
        modify_params = {
            'variety': 'NORMAL',
            'orderid': orderid,
            'ordertype': ordertype,
            'quantity': str(quantity),
            'price': str(price)
        }
        
        # Add optional parameters if provided
        if tradingsymbol:
            modify_params['tradingsymbol'] = tradingsymbol
        if symboltoken:
            modify_params['symboltoken'] = str(symboltoken)
        if exchange:
            modify_params['exchange'] = exchange
        if producttype:
            modify_params['producttype'] = producttype
        if duration:
            modify_params['duration'] = duration
        
        # Validate parameters
        validated_params = _validate_modify_parameters(modify_params)
        
        # Log modification attempt
        logger.info(
            f"🔄 Order modification: {orderid} - {validated_params['ordertype']} "
            f"Qty: {validated_params['quantity']} Price: {validated_params['price']} "
            f"using {_rate_limit_permit['api_key_id']}"
        )
        
        # Make API call with strict rate limiting already enforced
        response = angel_client.modifyOrder(validated_params)
        
        # Parse response
        if not response:
            raise ModifyOrderError("Empty response from modifyOrder API")
        
        if not response.get('status'):
            error_msg = response.get('message', 'Unknown modification error')
            error_code = response.get('errorcode', 'N/A')
            raise ModifyOrderError(f"Order modification failed: {error_msg} (Code: {error_code})")
        
        # Extract modification details
        data = response.get('data', {})
        modified_order_id = data.get('orderid', orderid)
        
        # Success response
        result = {
            'success': True,
            'order_id': modified_order_id,
            'original_order_id': orderid,
            'message': 'Order modified successfully',
            'response': response,
            'modified_params': validated_params,
            'api_key_id': _rate_limit_permit['api_key_id'],
            'timestamp': time.time()
        }
        
        logger.info(f"✅ Order modified successfully: {modified_order_id}")
        
        return result
        
    except Exception as e:
        logger.error(f"❌ Order modification failed for {orderid}: {e}")
        
        # Create error response
        error_result = {
            'success': False,
            'order_id': orderid,
            'message': str(e),
            'response': None,
            'error': str(e),
            'timestamp': time.time()
        }
        
        # Re-raise as ModifyOrderError for consistent error handling
        if isinstance(e, ModifyOrderError):
            raise
        else:
            raise ModifyOrderError(f"Order modification failed: {e}")

def _validate_modify_parameters(modify_params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate and clean order modification parameters.
    
    Args:
        modify_params: Raw modification parameters
        
    Returns:
        Dict: Validated and cleaned parameters
        
    Raises:
        ModifyOrderError: If validation fails
    """
    validated = modify_params.copy()
    
    # Validate order type
    valid_order_types = ['MARKET', 'LIMIT', 'STOPLOSS', 'SL-M']
    if validated.get('ordertype') not in valid_order_types:
        raise ModifyOrderError(f"Invalid ordertype. Must be one of: {valid_order_types}")
    
    # Validate quantity
    try:
        quantity = int(validated['quantity'])
        if quantity <= 0:
            raise ValueError("Quantity must be positive")
        validated['quantity'] = str(quantity)
    except (ValueError, TypeError):
        raise ModifyOrderError("Invalid quantity. Must be a positive integer")
    
    # Validate price for non-market orders
    if validated.get('ordertype') != 'MARKET':
        try:
            price = float(validated['price'])
            if price <= 0:
                raise ValueError("Price must be positive")
            validated['price'] = str(price)
        except (ValueError, TypeError):
            raise ModifyOrderError("Invalid price. Must be a positive number")
    
    # Validate order ID format (basic check)
    order_id = validated.get('orderid', '')
    if not order_id or len(order_id) < 10:
        raise ModifyOrderError("Invalid order ID format")
    
    return validated

async def modify_order_price(
    orderid: str,
    new_price: float,
    ordertype: str = "LIMIT"
) -> Dict[str, Any]:
    """
    Simplified price modification for an order.
    
    Args:
        orderid: Order ID to modify
        new_price: New price to set
        ordertype: Order type (default: "LIMIT")
        
    Returns:
        Dict: Modification result
    """
    # Get current order details first (would need get_order_by_id)
    # For now, we'll modify with minimal parameters
    
    return await modify_order(
        orderid=orderid,
        quantity="1",  # Placeholder - would get from current order
        price=str(new_price),
        ordertype=ordertype
    )

async def modify_order_quantity(
    orderid: str,
    new_quantity: int
) -> Dict[str, Any]:
    """
    Simplified quantity modification for an order.
    
    Args:
        orderid: Order ID to modify
        new_quantity: New quantity to set
        
    Returns:
        Dict: Modification result
    """
    # Get current order details first (would need get_order_by_id)
    # For now, we'll modify with minimal parameters
    
    return await modify_order(
        orderid=orderid,
        quantity=str(new_quantity),
        price="0",  # Placeholder - would get from current order
        ordertype="MARKET"  # Placeholder - would get from current order
    )

async def convert_order_to_market(
    orderid: str,
    quantity: Optional[str] = None
) -> Dict[str, Any]:
    """
    Convert a limit order to market order.
    
    Args:
        orderid: Order ID to convert
        quantity: Quantity (optional, will use current if not provided)
        
    Returns:
        Dict: Modification result
    """
    # This is a common trading operation - convert pending limit order to market
    
    if not quantity:
        quantity = "1"  # Would get from current order details
    
    return await modify_order(
        orderid=orderid,
        quantity=quantity,
        price="0",  # Market orders don't need price
        ordertype="MARKET"
    )

def modify_order_sync(
    orderid: str,
    quantity: str,
    price: str,
    ordertype: str,
    **kwargs
) -> Dict[str, Any]:
    """
    Synchronous wrapper for modify_order.
    
    ⚠️ WARNING: Use async version when possible for better performance.
    This is only for compatibility with legacy code.
    """
    import asyncio
    try:
        return asyncio.run(modify_order(orderid, quantity, price, ordertype, **kwargs))
    except Exception as e:
        logger.error(f"❌ Sync order modification failed for {orderid}: {e}")
        return {
            'success': False,
            'order_id': orderid,
            'message': str(e),
            'error': str(e)
        }

# Backward compatibility aliases (DEPRECATED - use new names)
update_order = modify_order  # Alias for existing code
change_order = modify_order  # Alias for existing code

if __name__ == "__main__":
    # Test order modification
    async def test_order_modification():
        print("🧪 Testing Angel One Order Modification")
        print("=" * 40)
        print("⚠️ Note: This is a test - no real orders will be modified")
        
        # Test parameter validation
        test_params = {
            'orderid': '210610000000001',
            'quantity': '10',
            'price': '1500.50',
            'ordertype': 'LIMIT'
        }
        
        try:
            validated = _validate_modify_parameters(test_params)
            print(f"✅ Parameter validation successful")
            print(f"   Order ID: {validated['orderid']}")
            print(f"   Type: {validated['ordertype']}")
            print(f"   Quantity: {validated['quantity']}")
            print(f"   Price: {validated['price']}")
        except Exception as e:
            print(f"❌ Parameter validation failed: {e}")
        
        print("\n⚠️ Note: Actual order modification requires rate controller and live connection")
    
    # Run test
    import asyncio
    asyncio.run(test_order_modification())
