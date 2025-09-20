"""
Angel One API: orderDetails - Individual Order Status
====================================================

CRITICAL METHOD: Get detailed status of specific orders
Rate Limit: 10 requests/second per API key
Priority: MEDIUM (important for order tracking)

Usage:
    from angel_one_api.methods.order_details import order_details
    
    # Get specific order details
    details = await order_details("210610000000001")
    
    # Check order status
    status = await get_order_status("210610000000001")
    
    # Monitor order execution
    execution_info = await get_order_execution_info("210610000000001")

Author: AI Trading System
Rate Limit: STRICTLY ENFORCED 10 req/sec per key
"""

import time
from typing import Dict, List, Optional, Any
import logging
from datetime import datetime, UTC

# Import our rate limiting system
from ..rate_limiter.rate_controller import get_rate_controller, rate_limited, APIPriority
from ..rate_limiter.api_limits import API_LIMITS

logger = logging.getLogger(__name__)

class OrderDetailsError(Exception):
    """Raised when order details fetching fails."""
    pass

@rate_limited("order_details", APIPriority.MEDIUM)
async def order_details(
    order_id: str,
    _rate_limit_permit: Optional[Dict] = None
) -> Dict[str, Any]:
    """
    Get detailed information about a specific order using Angel One API.
    
    Args:
        order_id: Order ID to get details for
        _rate_limit_permit: Automatically provided by rate limiter
        
    Returns:
        Dict containing:
            - success: bool
            - order_details: Dict of detailed order information
            - order_status: str
            - execution_info: Dict
            - fill_info: Dict
            - timestamp: str
        
    Raises:
        OrderDetailsError: If order details fetching fails
        RateLimitExceeded: If rate limit would be exceeded
        
    Rate Limit: 10 requests/second per API key
    """
    try:
        if not _rate_limit_permit:
            raise OrderDetailsError("No rate limit permit - internal error")
        
        # Get Angel One client
        from core.connections import ConnectionManager
        
        angel_client = ConnectionManager.get_smartapi_client()
        if not angel_client:
            raise OrderDetailsError("Angel One API client not available")
        
        # Validate order ID
        if not order_id or len(order_id) < 10:
            raise OrderDetailsError("Invalid order ID format")
        
        # Log request
        logger.debug(f"🔍 Order details request: {order_id} using {_rate_limit_permit['api_key_id']}")
        
        # Make API call with strict rate limiting already enforced
        # Note: The endpoint format includes the order ID in the URL
        response = angel_client.getOrderDetails(order_id)
        
        # Parse response
        if not response:
            raise OrderDetailsError("Empty response from orderDetails API")
        
        if not response.get('status'):
            error_msg = response.get('message', 'Unknown error')
            raise OrderDetailsError(f"Order details API error: {error_msg}")
        
        order_data = response.get('data', {})
        
        # Process order details
        processed_details = _process_order_details(order_data)
        
        # Extract key information
        order_status = processed_details.get('orderstatus', 'UNKNOWN')
        execution_info = _extract_execution_info(processed_details)
        fill_info = _extract_fill_info(processed_details)
        timing_info = _extract_timing_info(processed_details)
        
        # Success response
        result = {
            'success': True,
            'order_id': order_id,
            'order_details': processed_details,
            'order_status': order_status,
            'execution_info': execution_info,
            'fill_info': fill_info,
            'timing_info': timing_info,
            'order_summary': {
                'symbol': processed_details.get('tradingsymbol'),
                'quantity': processed_details.get('quantity', 0),
                'price': processed_details.get('price', 0),
                'order_type': processed_details.get('ordertype'),
                'transaction_type': processed_details.get('transactiontype'),
                'product_type': processed_details.get('producttype'),
                'status': order_status,
                'is_complete': order_status == 'COMPLETE',
                'is_pending': order_status in ['OPEN', 'TRIGGER PENDING', 'PENDING'],
                'is_cancelled': order_status in ['CANCELLED', 'REJECTED']
            },
            'raw_data': order_data,
            'timestamp': datetime.now(UTC).isoformat(),
            'api_key_id': _rate_limit_permit['api_key_id'],
            'response_time': time.time()
        }
        
        logger.info(f"✅ Order details fetched: {order_id} - {order_status}")
        
        return result
        
    except Exception as e:
        logger.error(f"❌ Order details fetch failed for {order_id}: {e}")
        
        # Create error response
        error_result = {
            'success': False,
            'order_id': order_id,
            'order_details': {},
            'error': str(e),
            'timestamp': datetime.now(UTC).isoformat()
        }
        
        # Re-raise as OrderDetailsError for consistent error handling
        if isinstance(e, OrderDetailsError):
            raise
        else:
            raise OrderDetailsError(f"Order details fetch failed: {e}")

def _process_order_details(order_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Process and clean raw order details data from Angel One API.
    
    Args:
        order_data: Raw order data from API
        
    Returns:
        Dict: Cleaned and enhanced order details
    """
    try:
        # Core order fields
        processed = {
            'orderid': order_data.get('orderid', ''),
            'tradingsymbol': order_data.get('tradingsymbol', ''),
            'exchange': order_data.get('exchange', ''),
            'producttype': order_data.get('producttype', ''),
            'instrumenttype': order_data.get('instrumenttype', ''),
            'symboltoken': order_data.get('symboltoken', ''),
            
            # Order details
            'transactiontype': order_data.get('transactiontype', ''),
            'ordertype': order_data.get('ordertype', ''),
            'orderstatus': order_data.get('orderstatus', ''),
            'duration': order_data.get('duration', ''),
            'variety': order_data.get('variety', ''),
            
            # Quantity and price fields
            'quantity': int(order_data.get('quantity', 0)),
            'fillshares': int(order_data.get('fillshares', 0)),
            'unfilledshares': int(order_data.get('unfilledshares', 0)),
            'price': float(order_data.get('price', 0)),
            'triggerprice': float(order_data.get('triggerprice', 0)),
            'averageprice': float(order_data.get('averageprice', 0)),
            
            # Timing fields
            'ordertime': order_data.get('ordertime', ''),
            'updatetime': order_data.get('updatetime', ''),
            'exchtime': order_data.get('exchtime', ''),
            'exchorderupdatetime': order_data.get('exchorderupdatetime', ''),
            
            # Exchange details
            'exchorderid': order_data.get('exchorderid', ''),
            'filledshares': int(order_data.get('filledshares', 0)),
            'cancelsize': int(order_data.get('cancelsize', 0)),
            'lotsize': int(order_data.get('lotsize', 1)),
            'multiplier': float(order_data.get('multiplier', 1)),
            'precision': int(order_data.get('precision', 2)),
            
            # Additional fields
            'text': order_data.get('text', ''),
            'status': order_data.get('status', ''),
            'rejectionreason': order_data.get('rejectionreason', ''),
            'disclosedquantity': int(order_data.get('disclosedquantity', 0)),
            'guid': order_data.get('guid', '')
        }
        
        return processed
        
    except (ValueError, TypeError) as e:
        logger.warning(f"⚠️ Error processing order details: {e}")
        return order_data  # Return original if processing fails

def _extract_execution_info(order_details: Dict[str, Any]) -> Dict[str, Any]:
    """Extract execution information from order details."""
    quantity = order_details.get('quantity', 0)
    filled_shares = order_details.get('fillshares', 0)
    
    execution_info = {
        'total_quantity': quantity,
        'filled_quantity': filled_shares,
        'pending_quantity': quantity - filled_shares,
        'fill_percentage': (filled_shares / quantity * 100) if quantity > 0 else 0,
        'is_fully_filled': filled_shares == quantity,
        'is_partially_filled': 0 < filled_shares < quantity,
        'is_unfilled': filled_shares == 0,
        'average_price': order_details.get('averageprice', 0),
        'total_value': filled_shares * order_details.get('averageprice', 0)
    }
    
    return execution_info

def _extract_fill_info(order_details: Dict[str, Any]) -> Dict[str, Any]:
    """Extract fill information from order details."""
    fill_info = {
        'filled_shares': order_details.get('fillshares', 0),
        'unfilled_shares': order_details.get('unfilledshares', 0),
        'cancelled_shares': order_details.get('cancelsize', 0),
        'disclosed_quantity': order_details.get('disclosedquantity', 0),
        'lot_size': order_details.get('lotsize', 1),
        'multiplier': order_details.get('multiplier', 1)
    }
    
    return fill_info

def _extract_timing_info(order_details: Dict[str, Any]) -> Dict[str, Any]:
    """Extract timing information from order details."""
    timing_info = {
        'order_time': order_details.get('ordertime', ''),
        'update_time': order_details.get('updatetime', ''),
        'exchange_time': order_details.get('exchtime', ''),
        'exchange_update_time': order_details.get('exchorderupdatetime', ''),
        'last_update': order_details.get('updatetime', '') or order_details.get('exchorderupdatetime', '')
    }
    
    return timing_info

async def get_order_status(order_id: str) -> str:
    """
    Get simplified order status.
    
    Args:
        order_id: Order ID to check
        
    Returns:
        str: Order status (COMPLETE, PENDING, CANCELLED, etc.)
    """
    try:
        details_result = await order_details(order_id)
        if details_result['success']:
            return details_result['order_status']
        return 'UNKNOWN'
    except Exception as e:
        logger.error(f"❌ Order status check failed for {order_id}: {e}")
        return 'ERROR'

async def get_order_execution_info(order_id: str) -> Dict[str, Any]:
    """
    Get detailed execution information for an order.
    
    Args:
        order_id: Order ID to check
        
    Returns:
        Dict: Execution information
    """
    try:
        details_result = await order_details(order_id)
        if details_result['success']:
            return details_result['execution_info']
        return {'success': False, 'error': 'Failed to fetch order details'}
    except Exception as e:
        logger.error(f"❌ Order execution info failed for {order_id}: {e}")
        return {'success': False, 'error': str(e)}

async def is_order_complete(order_id: str) -> bool:
    """
    Check if an order is completely filled.
    
    Args:
        order_id: Order ID to check
        
    Returns:
        bool: True if order is complete
    """
    try:
        status = await get_order_status(order_id)
        return status == 'COMPLETE'
    except Exception as e:
        logger.error(f"❌ Order completion check failed for {order_id}: {e}")
        return False

async def wait_for_order_completion(
    order_id: str,
    timeout_seconds: int = 300,
    check_interval: float = 1.0
) -> Dict[str, Any]:
    """
    Wait for an order to complete or timeout.
    
    Args:
        order_id: Order ID to monitor
        timeout_seconds: Maximum time to wait (default: 5 minutes)
        check_interval: How often to check status (default: 1 second)
        
    Returns:
        Dict: Final order status and timing info
    """
    import asyncio
    
    start_time = time.time()
    checks_made = 0
    
    while (time.time() - start_time) < timeout_seconds:
        try:
            details_result = await order_details(order_id)
            checks_made += 1
            
            if details_result['success']:
                status = details_result['order_status']
                
                # Order completed
                if status == 'COMPLETE':
                    return {
                        'success': True,
                        'completed': True,
                        'status': status,
                        'execution_info': details_result['execution_info'],
                        'elapsed_time': time.time() - start_time,
                        'checks_made': checks_made
                    }
                
                # Order failed/cancelled
                elif status in ['CANCELLED', 'REJECTED']:
                    return {
                        'success': True,
                        'completed': False,
                        'status': status,
                        'rejection_reason': details_result['order_details'].get('rejectionreason', ''),
                        'elapsed_time': time.time() - start_time,
                        'checks_made': checks_made
                    }
            
            # Wait before next check
            await asyncio.sleep(check_interval)
            
        except Exception as e:
            logger.warning(f"⚠️ Order monitoring error for {order_id}: {e}")
            await asyncio.sleep(check_interval)
    
    # Timeout reached
    return {
        'success': False,
        'completed': False,
        'status': 'TIMEOUT',
        'elapsed_time': time.time() - start_time,
        'checks_made': checks_made,
        'timeout_seconds': timeout_seconds
    }

async def get_multiple_order_details(
    order_ids: List[str],
    batch_delay: float = 0.1  # 10 req/sec = 0.1s between requests
) -> Dict[str, Dict[str, Any]]:
    """
    Get details for multiple orders efficiently with rate limiting.
    
    Args:
        order_ids: List of order IDs
        batch_delay: Delay between requests in seconds
        
    Returns:
        Dict: Order ID -> details mapping
    """
    if not order_ids:
        return {}
    
    logger.info(f"🔍 Bulk order details for {len(order_ids)} orders")
    
    results = {}
    
    for i, order_id in enumerate(order_ids):
        batch_start_time = time.time()
        
        try:
            details_result = await order_details(order_id)
            results[order_id] = details_result
            
            logger.debug(f"✅ Details {i+1}/{len(order_ids)}: {order_id}")
            
        except Exception as e:
            logger.warning(f"⚠️ Details fetch failed for {order_id}: {e}")
            results[order_id] = {'success': False, 'error': str(e)}
        
        # Add delay between requests (except for last one)
        if i < len(order_ids) - 1:
            elapsed = time.time() - batch_start_time
            if elapsed < batch_delay:
                sleep_time = batch_delay - elapsed
                await asyncio.sleep(sleep_time)
    
    successful_count = sum(1 for r in results.values() if r.get('success'))
    logger.info(f"✅ Bulk order details complete: {successful_count}/{len(order_ids)} successful")
    
    return results

def order_details_sync(order_id: str) -> Dict[str, Any]:
    """
    Synchronous wrapper for order_details.
    
    ⚠️ WARNING: Use async version when possible for better performance.
    This is only for compatibility with legacy code.
    """
    import asyncio
    try:
        return asyncio.run(order_details(order_id))
    except Exception as e:
        logger.error(f"❌ Sync order details fetch failed for {order_id}: {e}")
        return {
            'success': False,
            'order_id': order_id,
            'order_details': {},
            'error': str(e)
        }

# Backward compatibility aliases (DEPRECATED - use new names)
get_order_details = order_details  # Alias for existing code
fetch_order_info = order_details   # Alias for existing code

if __name__ == "__main__":
    # Test order details fetching
    async def test_order_details():
        print("🧪 Testing Angel One Order Details")
        print("=" * 40)
        print("⚠️ Note: This is a test - requires valid order ID")
        
        # Test with sample order ID format
        test_order_id = "210610000000001"
        
        print(f"📋 Order details test for: {test_order_id}")
        print("   (This would fetch detailed order information)")
        
        # Test order monitoring
        print(f"\n⏱️ Order monitoring simulation:")
        print("   - Check order status every 1 second")
        print("   - Wait up to 5 minutes for completion")
        print("   - Report final status and timing")
        
        print("\n⚠️ Note: Actual order details require rate controller and live connection")
    
    # Run test
    import asyncio
    asyncio.run(test_order_details())
