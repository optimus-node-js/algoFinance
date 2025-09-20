"""
Angel One API: cancelOrder - Order Cancellation
==============================================

CRITICAL METHOD: Order management and cancellation
Rate Limit: 20 requests/second per API key (HIGH frequency)
Priority: CRITICAL (essential for risk management)

Usage:
    from angel_one_api.methods.cancel_order import cancel_order
    
    # Cancel specific order
    result = await cancel_order("210610000000001", "NORMAL")
    
    # Cancel all pending orders for a symbol
    results = await cancel_all_orders_for_symbol("RELIANCE-EQ")
    
    # Emergency cancel all orders
    results = await emergency_cancel_all_orders()

Author: AI Trading System
Rate Limit: STRICTLY ENFORCED 20 req/sec per key
"""

import time
import asyncio
from typing import Dict, List, Optional, Any
# Import new Angel One logger
from ..logger import get_api_logger
from datetime import datetime, UTC

# Import our rate limiting system
from ..rate_limiter.rate_controller import get_rate_controller, rate_limited, APIPriority
from ..rate_limiter.api_limits import API_LIMITS

logger = get_api_logger("cancel_order")

class CancelOrderError(Exception):
    """Raised when order cancellation fails."""
    pass

@rate_limited("cancel_order", APIPriority.CRITICAL)
async def cancel_order(
    orderid: str,
    variety: str = "NORMAL",
    _rate_limit_permit: Optional[Dict] = None
) -> Dict[str, Any]:
    """
    Cancel an existing order using Angel One API.
    
    Args:
        orderid: Order ID to cancel
        variety: Order variety (NORMAL, STOPLOSS, AMO)
        _rate_limit_permit: Automatically provided by rate limiter
        
    Returns:
        Dict containing:
            - success: bool
            - order_id: str (cancelled order ID)
            - message: str
            - response: dict (full API response)
        
    Raises:
        CancelOrderError: If order cancellation fails
        RateLimitExceeded: If rate limit would be exceeded
        
    Rate Limit: 20 requests/second per API key
    """
    try:
        if not _rate_limit_permit:
            raise CancelOrderError("No rate limit permit - internal error")
        
        # Get Angel One client
        from core.connections import ConnectionManager
        
        angel_client = ConnectionManager.get_smartapi_client()
        if not angel_client:
            raise CancelOrderError("Angel One API client not available")
        
        # Validate required parameters
        if not orderid:
            raise CancelOrderError("Order ID is required")
        
        if not variety:
            variety = "NORMAL"
        
        # Build cancellation parameters
        cancel_params = {
            'variety': variety,
            'orderid': orderid
        }
        
        # Validate parameters
        validated_params = _validate_cancel_parameters(cancel_params)
        
        # Log cancellation attempt
        logger.info(
            f"❌ Order cancellation: {orderid} ({variety}) "
            f"using {_rate_limit_permit['api_key_id']}"
        )
        
        # Make API call with strict rate limiting already enforced
        response = angel_client.cancelOrder(validated_params)
        
        # Parse response
        if not response:
            raise CancelOrderError("Empty response from cancelOrder API")
        
        if not response.get('status'):
            error_msg = response.get('message', 'Unknown cancellation error')
            error_code = response.get('errorcode', 'N/A')
            raise CancelOrderError(f"Order cancellation failed: {error_msg} (Code: {error_code})")
        
        # Extract cancellation details
        data = response.get('data', {})
        cancelled_order_id = data.get('orderid', orderid)
        
        # Success response
        result = {
            'success': True,
            'order_id': cancelled_order_id,
            'variety': variety,
            'message': 'Order cancelled successfully',
            'response': response,
            'cancel_params': validated_params,
            'api_key_id': _rate_limit_permit['api_key_id'],
            'timestamp': time.time()
        }
        
        logger.info(f"✅ Order cancelled successfully: {cancelled_order_id}")
        
        return result
        
    except Exception as e:
        logger.error(f"❌ Order cancellation failed for {orderid}: {e}")
        
        # Create error response
        error_result = {
            'success': False,
            'order_id': orderid,
            'message': str(e),
            'response': None,
            'error': str(e),
            'timestamp': time.time()
        }
        
        # Re-raise as CancelOrderError for consistent error handling
        if isinstance(e, CancelOrderError):
            raise
        else:
            raise CancelOrderError(f"Order cancellation failed: {e}")

def _validate_cancel_parameters(cancel_params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate and clean order cancellation parameters.
    
    Args:
        cancel_params: Raw cancellation parameters
        
    Returns:
        Dict: Validated and cleaned parameters
        
    Raises:
        CancelOrderError: If validation fails
    """
    validated = cancel_params.copy()
    
    # Validate variety
    valid_varieties = ['NORMAL', 'STOPLOSS', 'AMO']
    if validated.get('variety') not in valid_varieties:
        raise CancelOrderError(f"Invalid variety. Must be one of: {valid_varieties}")
    
    # Validate order ID format (basic check)
    order_id = validated.get('orderid', '')
    if not order_id or len(order_id) < 10:
        raise CancelOrderError("Invalid order ID format")
    
    return validated

async def cancel_multiple_orders(
    order_ids: List[str],
    variety: str = "NORMAL",
    batch_delay: float = 0.05  # 20 req/sec = 0.05s between requests
) -> Dict[str, Any]:
    """
    Cancel multiple orders efficiently with rate limiting.
    
    Args:
        order_ids: List of order IDs to cancel
        variety: Order variety (default: "NORMAL")
        batch_delay: Delay between cancellations in seconds
        
    Returns:
        Dict: Cancellation results for all orders
    """
    if not order_ids:
        return {
            'success': True,
            'total_orders': 0,
            'cancelled_count': 0,
            'failed_count': 0,
            'results': {}
        }
    
    logger.info(f"❌ Bulk order cancellation: {len(order_ids)} orders")
    
    results = {}
    cancelled_count = 0
    failed_count = 0
    
    for i, order_id in enumerate(order_ids):
        batch_start_time = time.time()
        
        try:
            cancel_result = await cancel_order(order_id, variety)
            results[order_id] = cancel_result
            
            if cancel_result['success']:
                cancelled_count += 1
                logger.debug(f"✅ Cancelled {i+1}/{len(order_ids)}: {order_id}")
            else:
                failed_count += 1
                logger.warning(f"❌ Failed {i+1}/{len(order_ids)}: {order_id}")
                
        except Exception as e:
            failed_count += 1
            logger.warning(f"❌ Cancellation failed for {order_id}: {e}")
            results[order_id] = {
                'success': False,
                'order_id': order_id,
                'error': str(e)
            }
        
        # Add delay between requests (except for last one)
        if i < len(order_ids) - 1:
            elapsed = time.time() - batch_start_time
            if elapsed < batch_delay:
                sleep_time = batch_delay - elapsed
                await asyncio.sleep(sleep_time)
    
    summary = {
        'success': True,
        'total_orders': len(order_ids),
        'cancelled_count': cancelled_count,
        'failed_count': failed_count,
        'success_rate': (cancelled_count / len(order_ids)) * 100,
        'results': results,
        'timestamp': time.time()
    }
    
    logger.info(f"✅ Bulk cancellation complete: {cancelled_count}/{len(order_ids)} successful")
    
    return summary

async def cancel_all_orders_for_symbol(symbol: str) -> Dict[str, Any]:
    """
    Cancel all pending orders for a specific symbol.
    
    Args:
        symbol: Trading symbol (e.g., "RELIANCE-EQ")
        
    Returns:
        Dict: Cancellation results for symbol orders
    """
    try:
        # Get pending orders for the symbol
        from .get_order_book import get_orders_by_symbol
        
        symbol_orders = await get_orders_by_symbol(symbol)
        
        # Filter only pending orders
        pending_orders = [
            order['orderid'] for order in symbol_orders
            if order.get('is_pending', False)
        ]
        
        if not pending_orders:
            return {
                'success': True,
                'symbol': symbol,
                'message': f'No pending orders found for {symbol}',
                'cancelled_count': 0
            }
        
        # Cancel all pending orders
        logger.info(f"❌ Cancelling all orders for {symbol}: {len(pending_orders)} orders")
        
        cancel_results = await cancel_multiple_orders(pending_orders)
        cancel_results['symbol'] = symbol
        
        return cancel_results
        
    except Exception as e:
        logger.error(f"❌ Symbol order cancellation failed for {symbol}: {e}")
        return {
            'success': False,
            'symbol': symbol,
            'error': str(e),
            'cancelled_count': 0
        }

async def emergency_cancel_all_orders() -> Dict[str, Any]:
    """
    Emergency function to cancel ALL pending orders.
    
    ⚠️ USE WITH EXTREME CAUTION - This cancels every pending order!
    
    Returns:
        Dict: Emergency cancellation results
    """
    try:
        logger.warning("🚨 EMERGENCY: Cancelling ALL pending orders")
        
        # Get all pending orders
        from .get_order_book import get_pending_orders
        
        pending_orders = await get_pending_orders()
        
        if not pending_orders:
            return {
                'success': True,
                'message': 'No pending orders to cancel',
                'cancelled_count': 0,
                'emergency': True
            }
        
        # Extract order IDs
        order_ids = [order['orderid'] for order in pending_orders]
        
        logger.warning(f"🚨 EMERGENCY: Found {len(order_ids)} pending orders to cancel")
        
        # Cancel all orders with higher frequency (emergency mode)
        cancel_results = await cancel_multiple_orders(
            order_ids, 
            batch_delay=0.02  # Faster cancellation in emergency
        )
        
        cancel_results['emergency'] = True
        cancel_results['emergency_timestamp'] = datetime.now(UTC).isoformat()
        
        logger.warning(f"🚨 EMERGENCY COMPLETE: {cancel_results['cancelled_count']}/{len(order_ids)} orders cancelled")
        
        return cancel_results
        
    except Exception as e:
        logger.error(f"❌ Emergency cancellation failed: {e}")
        return {
            'success': False,
            'emergency': True,
            'error': str(e),
            'cancelled_count': 0
        }

async def cancel_orders_by_type(
    order_type: str,
    symbol: Optional[str] = None
) -> Dict[str, Any]:
    """
    Cancel orders by order type (and optionally symbol).
    
    Args:
        order_type: Order type to cancel (LIMIT, MARKET, STOPLOSS, etc.)
        symbol: Optional symbol filter
        
    Returns:
        Dict: Cancellation results
    """
    try:
        # Get all pending orders
        from .get_order_book import get_pending_orders
        
        pending_orders = await get_pending_orders()
        
        # Filter by order type and symbol
        target_orders = []
        for order in pending_orders:
            if order.get('ordertype') == order_type:
                if symbol is None or order.get('tradingsymbol') == symbol:
                    target_orders.append(order['orderid'])
        
        if not target_orders:
            return {
                'success': True,
                'order_type': order_type,
                'symbol': symbol,
                'message': f'No pending {order_type} orders found',
                'cancelled_count': 0
            }
        
        # Cancel filtered orders
        logger.info(f"❌ Cancelling {order_type} orders: {len(target_orders)} orders")
        
        cancel_results = await cancel_multiple_orders(target_orders)
        cancel_results['order_type'] = order_type
        cancel_results['symbol'] = symbol
        
        return cancel_results
        
    except Exception as e:
        logger.error(f"❌ Order type cancellation failed for {order_type}: {e}")
        return {
            'success': False,
            'order_type': order_type,
            'symbol': symbol,
            'error': str(e),
            'cancelled_count': 0
        }

def cancel_order_sync(orderid: str, variety: str = "NORMAL") -> Dict[str, Any]:
    """
    Synchronous wrapper for cancel_order.
    
    ⚠️ WARNING: Use async version when possible for better performance.
    This is only for compatibility with legacy code.
    """
    import asyncio
    try:
        return asyncio.run(cancel_order(orderid, variety))
    except Exception as e:
        logger.error(f"❌ Sync order cancellation failed for {orderid}: {e}")
        return {
            'success': False,
            'order_id': orderid,
            'message': str(e),
            'error': str(e)
        }

# Backward compatibility aliases (DEPRECATED - use new names)
delete_order = cancel_order  # Alias for existing code
remove_order = cancel_order  # Alias for existing code

if __name__ == "__main__":
    # Test order cancellation
    async def test_order_cancellation():
        print("🧪 Testing Angel One Order Cancellation")
        print("=" * 40)
        print("⚠️ Note: This is a test - no real orders will be cancelled")
        
        # Test parameter validation
        test_params = {
            'orderid': '210610000000001',
            'variety': 'NORMAL'
        }
        
        try:
            validated = _validate_cancel_parameters(test_params)
            print(f"✅ Parameter validation successful")
            print(f"   Order ID: {validated['orderid']}")
            print(f"   Variety: {validated['variety']}")
        except Exception as e:
            print(f"❌ Parameter validation failed: {e}")
        
        # Test bulk cancellation logic
        test_order_ids = ["210610000000001", "210610000000002", "210610000000003"]
        print(f"\n📋 Bulk cancellation test for {len(test_order_ids)} orders")
        print("   (This would cancel orders with rate limiting)")
        
        print("\n⚠️ Note: Actual order cancellation requires rate controller and live connection")
        print("🚨 WARNING: emergency_cancel_all_orders() cancels EVERY pending order!")
    
    # Run test
    import asyncio
    asyncio.run(test_order_cancellation())
