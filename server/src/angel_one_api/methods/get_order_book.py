"""
Angel One API: getOrderBook - Order Book Retrieval
=================================================

CRITICAL METHOD: Order tracking and trade management
Rate Limit: 1 request/second per API key
Priority: HIGH (essential for order management)

Usage:
    from angel_one_api.methods.get_order_book import get_order_book
    
    # Get all orders
    orders = await get_order_book()
    
    # Get orders with filtering
    pending_orders = await get_pending_orders()
    completed_orders = await get_completed_orders()
    
    # Get specific order
    order_details = await get_order_by_id("210610000000001")

Author: AI Trading System
Rate Limit: STRICTLY ENFORCED 1 req/sec per key
"""

import time
from typing import Dict, List, Optional, Any
# Import new Angel One logger
from ..logger import get_api_logger
from datetime import datetime, UTC

# Import our rate limiting system
from ..rate_limiter.rate_controller import get_rate_controller, rate_limited, APIPriority
from ..rate_limiter.api_limits import API_LIMITS

logger = get_api_logger("get_order_book")

class OrderBookError(Exception):
    """Raised when order book fetching fails."""
    pass

@rate_limited("get_order_book", APIPriority.HIGH)
async def get_order_book(_rate_limit_permit: Optional[Dict] = None) -> Dict[str, Any]:
    """
    Get order book from Angel One API.
    
    Args:
        _rate_limit_permit: Automatically provided by rate limiter
        
    Returns:
        Dict containing:
            - success: bool
            - orders: List of order data
            - total_orders: int
            - pending_orders: List
            - completed_orders: List
            - cancelled_orders: List
            - timestamp: str
        
    Raises:
        OrderBookError: If order book fetching fails
        RateLimitExceeded: If rate limit would be exceeded
        
    Rate Limit: 1 request/second per API key
    """
    try:
        if not _rate_limit_permit:
            raise OrderBookError("No rate limit permit - internal error")
        
        # Get Angel One client
        from core.connections import ConnectionManager
        
        angel_client = ConnectionManager.get_smartapi_client()
        if not angel_client:
            raise OrderBookError("Angel One API client not available")
        
        # Log request
        logger.debug(f"📋 Order book request using {_rate_limit_permit['api_key_id']}")
        
        # Make API call with strict rate limiting already enforced
        response = angel_client.orderBook()
        
        # Parse response
        if not response:
            raise OrderBookError("Empty response from orderBook API")
        
        if not response.get('status'):
            error_msg = response.get('message', 'Unknown error')
            raise OrderBookError(f"Order book API error: {error_msg}")
        
        orders_data = response.get('data', [])
        
        # Handle None data (empty order book)
        if orders_data is None:
            logger.debug("📝 No orders found - empty order book")
            orders_data = []
        
        # Validate orders data
        if not isinstance(orders_data, list):
            raise OrderBookError(f"Invalid order book data format received. Expected list, got {type(orders_data)}: {orders_data}")
        
        # Process and categorize orders
        all_orders = []
        pending_orders = []
        completed_orders = []
        cancelled_orders = []
        
        for order in orders_data:
            # Clean and validate order data
            processed_order = _process_order_data(order)
            all_orders.append(processed_order)
            
            # Categorize by order status
            status = order.get('orderstatus', '').upper()
            if status in ['OPEN', 'TRIGGER PENDING', 'PENDING']:
                pending_orders.append(processed_order)
            elif status in ['COMPLETE', 'EXECUTED']:
                completed_orders.append(processed_order)
            elif status in ['CANCELLED', 'REJECTED']:
                cancelled_orders.append(processed_order)
        
        # Calculate summary statistics
        total_buy_value = sum(
            float(order.get('fillshares', 0)) * float(order.get('averageprice', 0))
            for order in all_orders 
            if order.get('transactiontype') == 'BUY' and order.get('orderstatus') == 'COMPLETE'
        )
        
        total_sell_value = sum(
            float(order.get('fillshares', 0)) * float(order.get('averageprice', 0))
            for order in all_orders 
            if order.get('transactiontype') == 'SELL' and order.get('orderstatus') == 'COMPLETE'
        )
        
        # Success response
        result = {
            'success': True,
            'orders': all_orders,
            'pending_orders': pending_orders,
            'completed_orders': completed_orders,
            'cancelled_orders': cancelled_orders,
            'total_orders': len(all_orders),
            'summary': {
                'pending_count': len(pending_orders),
                'completed_count': len(completed_orders),
                'cancelled_count': len(cancelled_orders),
                'total_buy_value': total_buy_value,
                'total_sell_value': total_sell_value,
                'net_traded_value': total_buy_value - total_sell_value
            },
            'timestamp': datetime.now(UTC).isoformat(),
            'api_key_id': _rate_limit_permit['api_key_id'],
            'response_time': time.time()
        }
        
        logger.info(f"✅ Order book fetched: {len(all_orders)} orders")
        
        return result
        
    except Exception as e:
        logger.error(f"❌ Order book fetch failed: {e}")
        
        # Create error response
        error_result = {
            'success': False,
            'orders': [],
            'total_orders': 0,
            'error': str(e),
            'timestamp': datetime.now(UTC).isoformat()
        }
        
        # Re-raise as OrderBookError for consistent error handling
        if isinstance(e, OrderBookError):
            raise
        else:
            raise OrderBookError(f"Order book fetch failed: {e}")

def _process_order_data(order: Dict[str, Any]) -> Dict[str, Any]:
    """
    Process and clean raw order data from Angel One API.
    
    Args:
        order: Raw order data from API
        
    Returns:
        Dict: Cleaned and enhanced order data
    """
    try:
        # Core order fields
        processed = {
            'orderid': order.get('orderid', ''),
            'tradingsymbol': order.get('tradingsymbol', ''),
            'exchange': order.get('exchange', ''),
            'producttype': order.get('producttype', ''),
            'instrumenttype': order.get('instrumenttype', ''),
            'symboltoken': order.get('symboltoken', ''),
            
            # Order details
            'transactiontype': order.get('transactiontype', ''),
            'ordertype': order.get('ordertype', ''),
            'orderstatus': order.get('orderstatus', ''),
            'duration': order.get('duration', ''),
            'variety': order.get('variety', ''),
            
            # Quantity and price fields
            'quantity': int(order.get('quantity', 0)),
            'fillshares': int(order.get('fillshares', 0)),
            'unfilledshares': int(order.get('unfilledshares', 0)),
            'price': float(order.get('price', 0)),
            'triggerprice': float(order.get('triggerprice', 0)),
            'averageprice': float(order.get('averageprice', 0)),
            
            # Timing fields
            'ordertime': order.get('ordertime', ''),
            'updatetime': order.get('updatetime', ''),
            'exchtime': order.get('exchtime', ''),
            'exchorderupdatetime': order.get('exchorderupdatetime', ''),
            
            # Exchange details
            'exchorderid': order.get('exchorderid', ''),
            'filledshares': int(order.get('filledshares', 0)),
            'cancelsize': int(order.get('cancelsize', 0)),
            'lotsize': int(order.get('lotsize', 1)),
            'multiplier': float(order.get('multiplier', 1)),
            'precision': int(order.get('precision', 2))
        }
        
        # Calculate derived fields
        processed['fill_percentage'] = (
            (processed['fillshares'] / processed['quantity']) * 100 
            if processed['quantity'] > 0 else 0
        )
        
        processed['is_complete'] = processed['orderstatus'].upper() == 'COMPLETE'
        processed['is_pending'] = processed['orderstatus'].upper() in ['OPEN', 'TRIGGER PENDING', 'PENDING']
        processed['is_cancelled'] = processed['orderstatus'].upper() in ['CANCELLED', 'REJECTED']
        
        # Calculate order value
        if processed['averageprice'] > 0 and processed['fillshares'] > 0:
            processed['filled_value'] = processed['fillshares'] * processed['averageprice']
        else:
            processed['filled_value'] = 0
        
        processed['total_order_value'] = processed['quantity'] * processed['price']
        
        return processed
        
    except (ValueError, TypeError) as e:
        logger.warning(f"⚠️ Error processing order data: {e}")
        return order  # Return original if processing fails

async def get_pending_orders() -> List[Dict[str, Any]]:
    """
    Get only pending orders.
    
    Returns:
        List: Pending orders
    """
    try:
        order_book = await get_order_book()
        if order_book['success']:
            return order_book['pending_orders']
        return []
    except Exception as e:
        logger.error(f"❌ Pending orders fetch failed: {e}")
        return []

async def get_completed_orders() -> List[Dict[str, Any]]:
    """
    Get only completed orders.
    
    Returns:
        List: Completed orders
    """
    try:
        order_book = await get_order_book()
        if order_book['success']:
            return order_book['completed_orders']
        return []
    except Exception as e:
        logger.error(f"❌ Completed orders fetch failed: {e}")
        return []

async def get_order_by_id(order_id: str) -> Optional[Dict[str, Any]]:
    """
    Get specific order by order ID.
    
    Args:
        order_id: Order ID to search for
        
    Returns:
        Dict: Order data or None if not found
    """
    try:
        order_book = await get_order_book()
        if not order_book['success']:
            return None
        
        # Find matching order
        for order in order_book['orders']:
            if order.get('orderid') == order_id:
                return order
        
        return None
        
    except Exception as e:
        logger.error(f"❌ Order lookup failed for {order_id}: {e}")
        return None

async def get_orders_by_symbol(symbol: str) -> List[Dict[str, Any]]:
    """
    Get all orders for a specific symbol.
    
    Args:
        symbol: Trading symbol (e.g., "RELIANCE-EQ")
        
    Returns:
        List: Orders for the symbol
    """
    try:
        order_book = await get_order_book()
        if not order_book['success']:
            return []
        
        # Filter orders by symbol
        symbol_orders = [
            order for order in order_book['orders']
            if order.get('tradingsymbol') == symbol
        ]
        
        return symbol_orders
        
    except Exception as e:
        logger.error(f"❌ Symbol orders fetch failed for {symbol}: {e}")
        return []

async def get_today_order_summary() -> Dict[str, Any]:
    """
    Get summary of today's trading activity.
    
    Returns:
        Dict: Today's order summary
    """
    try:
        order_book = await get_order_book()
        if not order_book['success']:
            return {'success': False, 'error': order_book.get('error')}
        
        orders = order_book['orders']
        today = datetime.now(UTC).date()
        
        # Filter today's orders (simplified - would need proper date parsing)
        today_orders = orders  # For now, assume all orders are today's
        
        # Calculate detailed statistics
        buy_orders = [o for o in today_orders if o.get('transactiontype') == 'BUY']
        sell_orders = [o for o in today_orders if o.get('transactiontype') == 'SELL']
        
        completed_buy_orders = [o for o in buy_orders if o.get('is_complete')]
        completed_sell_orders = [o for o in sell_orders if o.get('is_complete')]
        
        summary = {
            'success': True,
            'date': today.isoformat(),
            'total_orders': len(today_orders),
            'buy_orders_count': len(buy_orders),
            'sell_orders_count': len(sell_orders),
            'completed_orders_count': len([o for o in today_orders if o.get('is_complete')]),
            'pending_orders_count': len([o for o in today_orders if o.get('is_pending')]),
            'cancelled_orders_count': len([o for o in today_orders if o.get('is_cancelled')]),
            'total_buy_value': sum(o.get('filled_value', 0) for o in completed_buy_orders),
            'total_sell_value': sum(o.get('filled_value', 0) for o in completed_sell_orders),
            'unique_symbols_traded': len(set(o.get('tradingsymbol') for o in today_orders if o.get('is_complete'))),
            'average_order_size': sum(o.get('quantity', 0) for o in today_orders) / len(today_orders) if today_orders else 0,
            'timestamp': order_book['timestamp']
        }
        
        return summary
        
    except Exception as e:
        logger.error(f"❌ Today's order summary failed: {e}")
        return {'success': False, 'error': str(e)}

def get_order_book_sync() -> Dict[str, Any]:
    """
    Synchronous wrapper for get_order_book.
    
    ⚠️ WARNING: Use async version when possible for better performance.
    This is only for compatibility with legacy code.
    """
    import asyncio
    try:
        return asyncio.run(get_order_book())
    except Exception as e:
        logger.error(f"❌ Sync order book fetch failed: {e}")
        return {
            'success': False,
            'orders': [],
            'total_orders': 0,
            'error': str(e)
        }

# Backward compatibility aliases (DEPRECATED - use new names)
fetch_order_book = get_order_book  # Alias for existing code
get_all_orders = get_order_book    # Alias for existing code

if __name__ == "__main__":
    # Test order book fetching
    async def test_order_book():
        print("🧪 Testing Angel One Order Book")
        print("=" * 40)
        
        try:
            # Test basic order book
            order_book = await get_order_book()
            if order_book['success']:
                print(f"✅ Order book fetched: {order_book['total_orders']} orders")
                print(f"   Pending: {order_book['summary']['pending_count']}")
                print(f"   Completed: {order_book['summary']['completed_count']}")
                print(f"   Cancelled: {order_book['summary']['cancelled_count']}")
            else:
                print(f"❌ Order book fetch failed: {order_book.get('error')}")
                
        except Exception as e:
            print(f"❌ Order book test failed: {e}")
        
        try:
            # Test today's summary
            summary = await get_today_order_summary()
            if summary['success']:
                print(f"✅ Today's summary: {summary['total_orders']} orders")
                print(f"   Symbols traded: {summary['unique_symbols_traded']}")
                print(f"   Total buy value: ₹{summary['total_buy_value']:.2f}")
                print(f"   Total sell value: ₹{summary['total_sell_value']:.2f}")
            else:
                print(f"❌ Today's summary failed: {summary.get('error')}")
                
        except Exception as e:
            print(f"❌ Today's summary test failed: {e}")
    
    # Run test (requires rate controller to be initialized)
    print("⚠️ Note: Requires rate controller initialization for testing")
    # asyncio.run(test_order_book())
