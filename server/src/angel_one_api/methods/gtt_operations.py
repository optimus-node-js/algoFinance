"""
Angel One API: GTT Operations - Complete GTT Management
======================================================

METHODS: Modify, Cancel, Get Details, and List GTT Rules
Rate Limit: 10 requests/second per API key for all GTT operations
Priority: LOW (advanced trading features)

Usage:
    from angel_one_api.methods.gtt_operations import (
        modify_gtt_rule, cancel_gtt_rule, get_gtt_details, get_gtt_list
    )
    
    # Modify existing GTT rule
    result = await modify_gtt_rule(gtt_id="12345", price="2600.00", qty="15")
    
    # Cancel GTT rule
    result = await cancel_gtt_rule(gtt_id="12345")
    
    # Get GTT rule details
    details = await get_gtt_details(gtt_id="12345")
    
    # List all GTT rules
    all_rules = await get_gtt_list()

Author: AI Trading System
Rate Limit: STRICTLY ENFORCED 10 req/sec per key
"""

import time
import asyncio
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

logger = get_api_logger("gtt_operations")

class GTTOperationError(Exception):
    """Raised when GTT operations fail."""
    pass

@idempotency_wrapper(method_type="trading", ttl=300, cache_response=True) if IDEMPOTENCY_AVAILABLE else lambda x: x
@rate_limited("modify_gtt_rule", APIPriority.LOW)
async def modify_gtt_rule(
    gtt_id: str,
    price: Optional[str] = None,
    qty: Optional[str] = None,
    triggerprice: Optional[str] = None,
    timeperiod: Optional[str] = None,
    _rate_limit_permit: Optional[Dict] = None
) -> Dict[str, Any]:
    """
    Modify an existing GTT rule using Angel One API.
    
    Args:
        gtt_id: GTT rule ID to modify
        price: New order price (optional)
        qty: New quantity (optional)
        triggerprice: New trigger price (optional)
        timeperiod: New time period in days (optional)
        _rate_limit_permit: Automatically provided by rate limiter
        
    Returns:
        Dict containing modification result
        
    Rate Limit: 10 requests/second per API key
    """
    try:
        if not _rate_limit_permit:
            raise GTTOperationError("No rate limit permit - internal error")
        
        if not gtt_id:
            raise GTTOperationError("GTT rule ID is required")
        
        # Get Angel One client
        # Use interface to get SmartAPI client
        from interface import get_angel_one_interface
        interface = get_angel_one_interface()
        angel_client = interface.smart_api
        
        # angel_client already set above
        if not angel_client:
            raise GTTOperationError("Angel One API client not available")
        
        # Build modification parameters
        modify_params = {'id': gtt_id}
        
        if price is not None:
            modify_params['price'] = str(price)
        if qty is not None:
            modify_params['qty'] = str(qty)
        if triggerprice is not None:
            modify_params['triggerprice'] = str(triggerprice)
        if timeperiod is not None:
            modify_params['timeperiod'] = str(timeperiod)
        
        if len(modify_params) == 1:  # Only ID provided
            raise GTTOperationError("At least one parameter to modify must be provided")
        
        logger.info(f"🔄 GTT rule modification: {gtt_id} using {_rate_limit_permit['api_key_id']}")
        
        # Make API call
        response = angel_client.modifyGTTRule(modify_params)
        
        if not response or not response.get('status'):
            error_msg = response.get('message', 'Unknown error') if response else 'Empty response'
            raise GTTOperationError(f"GTT modification failed: {error_msg}")
        
        result = {
            'success': True,
            'gtt_id': gtt_id,
            'message': 'GTT rule modified successfully',
            'modified_params': modify_params,
            'response': response,
            'timestamp': datetime.now(UTC).isoformat()
        }
        
        logger.info(f"✅ GTT rule modified: {gtt_id}")
        return result
        
    except Exception as e:
        logger.error(f"❌ GTT modification failed for {gtt_id}: {e}")
        return {'success': False, 'gtt_id': gtt_id, 'error': str(e)}

@idempotency_wrapper(method_type="trading", ttl=300, cache_response=True) if IDEMPOTENCY_AVAILABLE else lambda x: x
@rate_limited("cancel_gtt_rule", APIPriority.LOW)
async def cancel_gtt_rule(
    gtt_id: str,
    _rate_limit_permit: Optional[Dict] = None
) -> Dict[str, Any]:
    """
    Cancel an existing GTT rule using Angel One API.
    
    Args:
        gtt_id: GTT rule ID to cancel
        _rate_limit_permit: Automatically provided by rate limiter
        
    Returns:
        Dict containing cancellation result
        
    Rate Limit: 10 requests/second per API key
    """
    try:
        if not _rate_limit_permit:
            raise GTTOperationError("No rate limit permit - internal error")
        
        if not gtt_id:
            raise GTTOperationError("GTT rule ID is required")
        
        # Get Angel One client
        # Use interface to get SmartAPI client
        from interface import get_angel_one_interface
        interface = get_angel_one_interface()
        angel_client = interface.smart_api
        
        # angel_client already set above
        if not angel_client:
            raise GTTOperationError("Angel One API client not available")
        
        logger.info(f"❌ GTT rule cancellation: {gtt_id} using {_rate_limit_permit['api_key_id']}")
        
        # Make API call
        response = angel_client.cancelGTTRule({'id': gtt_id})
        
        if not response or not response.get('status'):
            error_msg = response.get('message', 'Unknown error') if response else 'Empty response'
            raise GTTOperationError(f"GTT cancellation failed: {error_msg}")
        
        result = {
            'success': True,
            'gtt_id': gtt_id,
            'message': 'GTT rule cancelled successfully',
            'response': response,
            'cancelled_at': datetime.now(UTC).isoformat()
        }
        
        logger.info(f"✅ GTT rule cancelled: {gtt_id}")
        return result
        
    except Exception as e:
        logger.error(f"❌ GTT cancellation failed for {gtt_id}: {e}")
        return {'success': False, 'gtt_id': gtt_id, 'error': str(e)}

@idempotency_wrapper(method_type="account", ttl=60, cache_response=True) if IDEMPOTENCY_AVAILABLE else lambda x: x
@rate_limited("gtt_rule_details", APIPriority.LOW)
async def get_gtt_details(
    gtt_id: str,
    _rate_limit_permit: Optional[Dict] = None
) -> Dict[str, Any]:
    """
    Get details of a specific GTT rule using Angel One API.
    
    Args:
        gtt_id: GTT rule ID to get details for
        _rate_limit_permit: Automatically provided by rate limiter
        
    Returns:
        Dict containing GTT rule details
        
    Rate Limit: 10 requests/second per API key
    """
    try:
        if not _rate_limit_permit:
            raise GTTOperationError("No rate limit permit - internal error")
        
        if not gtt_id:
            raise GTTOperationError("GTT rule ID is required")
        
        # Get Angel One client
        # Use interface to get SmartAPI client
        from interface import get_angel_one_interface
        interface = get_angel_one_interface()
        angel_client = interface.smart_api
        
        # angel_client already set above
        if not angel_client:
            raise GTTOperationError("Angel One API client not available")
        
        logger.debug(f"🔍 GTT details request: {gtt_id} using {_rate_limit_permit['api_key_id']}")
        
        # Make API call
        response = angel_client.gttRuleDetails({'id': gtt_id})
        
        if not response or not response.get('status'):
            error_msg = response.get('message', 'Unknown error') if response else 'Empty response'
            raise GTTOperationError(f"GTT details fetch failed: {error_msg}")
        
        gtt_data = response.get('data', {})
        
        # Process GTT details
        processed_details = {
            'gtt_id': gtt_data.get('id', gtt_id),
            'symbol': gtt_data.get('tradingsymbol', ''),
            'exchange': gtt_data.get('exchange', ''),
            'transaction_type': gtt_data.get('transactiontype', ''),
            'product_type': gtt_data.get('producttype', ''),
            'quantity': gtt_data.get('qty', ''),
            'price': gtt_data.get('price', ''),
            'trigger_price': gtt_data.get('triggerprice', ''),
            'time_period': gtt_data.get('timeperiod', ''),
            'status': gtt_data.get('status', 'UNKNOWN'),
            'created_date': gtt_data.get('createddate', ''),
            'updated_date': gtt_data.get('updateddate', ''),
            'expiry_date': gtt_data.get('expirydate', '')
        }
        
        result = {
            'success': True,
            'gtt_details': processed_details,
            'raw_data': gtt_data,
            'timestamp': datetime.now(UTC).isoformat()
        }
        
        logger.info(f"✅ GTT details fetched: {gtt_id}")
        return result
        
    except Exception as e:
        logger.error(f"❌ GTT details fetch failed for {gtt_id}: {e}")
        return {'success': False, 'gtt_id': gtt_id, 'error': str(e)}

@idempotency_wrapper(method_type="account", ttl=60, cache_response=True) if IDEMPOTENCY_AVAILABLE else lambda x: x
@rate_limited("gtt_rule_list", APIPriority.LOW)
async def get_gtt_list(
    status_filter: Optional[str] = None,
    _rate_limit_permit: Optional[Dict] = None
) -> Dict[str, Any]:
    """
    Get list of all GTT rules using Angel One API.
    
    Args:
        status_filter: Filter by status (ACTIVE, TRIGGERED, EXPIRED, etc.)
        _rate_limit_permit: Automatically provided by rate limiter
        
    Returns:
        Dict containing list of GTT rules
        
    Rate Limit: 10 requests/second per API key
    """
    try:
        if not _rate_limit_permit:
            raise GTTOperationError("No rate limit permit - internal error")
        
        # Get Angel One client
        # Use interface to get SmartAPI client
        from interface import get_angel_one_interface
        interface = get_angel_one_interface()
        angel_client = interface.smart_api
        
        # angel_client already set above
        if not angel_client:
            raise GTTOperationError("Angel One API client not available")
        
        logger.debug(f"📋 GTT list request using {_rate_limit_permit['api_key_id']}")
        
        # Make API call
        params = {}
        if status_filter:
            params['status'] = status_filter
            
        # Check if GTT methods are available in SmartConnect SDK
        if hasattr(angel_client, 'gttRuleList'):
            response = angel_client.gttRuleList(params if params else None)
        else:
            # GTT methods not available in SmartConnect SDK
            raise GTTOperationError("GTT methods not available in SmartConnect SDK. Please check Angel One SmartAPI documentation for GTT endpoints.")
        
        if not response or not response.get('status'):
            error_msg = response.get('message', 'Unknown error') if response else 'Empty response'
            raise GTTOperationError(f"GTT list fetch failed: {error_msg}")
        
        gtt_list = response.get('data', [])
        
        # Process GTT list
        processed_rules = []
        active_count = 0
        triggered_count = 0
        expired_count = 0
        
        for gtt in gtt_list:
            processed_gtt = {
                'gtt_id': gtt.get('id', ''),
                'symbol': gtt.get('tradingsymbol', ''),
                'transaction_type': gtt.get('transactiontype', ''),
                'quantity': gtt.get('qty', ''),
                'trigger_price': gtt.get('triggerprice', ''),
                'status': gtt.get('status', 'UNKNOWN'),
                'created_date': gtt.get('createddate', ''),
                'expiry_date': gtt.get('expirydate', '')
            }
            processed_rules.append(processed_gtt)
            
            # Count by status
            status = processed_gtt['status'].upper()
            if status == 'ACTIVE':
                active_count += 1
            elif status == 'TRIGGERED':
                triggered_count += 1
            elif status == 'EXPIRED':
                expired_count += 1
        
        result = {
            'success': True,
            'gtt_rules': processed_rules,
            'total_rules': len(processed_rules),
            'summary': {
                'active_rules': active_count,
                'triggered_rules': triggered_count,
                'expired_rules': expired_count,
                'other_rules': len(processed_rules) - active_count - triggered_count - expired_count
            },
            'raw_data': gtt_list,
            'timestamp': datetime.now(UTC).isoformat()
        }
        
        logger.info(f"✅ GTT list fetched: {len(processed_rules)} rules")
        return result
        
    except Exception as e:
        logger.error(f"❌ GTT list fetch failed: {e}")
        return {'success': False, 'error': str(e)}

# Bulk operations
async def cancel_multiple_gtt_rules(
    gtt_ids: List[str],
    batch_delay: float = 0.1  # 10 req/sec = 0.1s between requests
) -> Dict[str, Any]:
    """Cancel multiple GTT rules efficiently."""
    if not gtt_ids:
        return {'success': True, 'cancelled_count': 0, 'results': {}}
    
    logger.info(f"❌ Bulk GTT cancellation: {len(gtt_ids)} rules")
    
    results = {}
    cancelled_count = 0
    
    for i, gtt_id in enumerate(gtt_ids):
        batch_start_time = time.time()
        
        try:
            cancel_result = await cancel_gtt_rule(gtt_id)
            results[gtt_id] = cancel_result
            
            if cancel_result['success']:
                cancelled_count += 1
                logger.debug(f"✅ Cancelled {i+1}/{len(gtt_ids)}: {gtt_id}")
            
        except Exception as e:
            logger.warning(f"⚠️ GTT cancellation failed for {gtt_id}: {e}")
            results[gtt_id] = {'success': False, 'error': str(e)}
        
        # Rate limiting delay
        if i < len(gtt_ids) - 1:
            elapsed = time.time() - batch_start_time
            if elapsed < batch_delay:
                await asyncio.sleep(batch_delay - elapsed)
    
    return {
        'success': True,
        'cancelled_count': cancelled_count,
        'total_requested': len(gtt_ids),
        'success_rate': (cancelled_count / len(gtt_ids)) * 100,
        'results': results
    }

async def get_active_gtt_rules() -> List[Dict[str, Any]]:
    """Get only active GTT rules."""
    try:
        gtt_list_result = await get_gtt_list('ACTIVE')
        if gtt_list_result['success']:
            return gtt_list_result['gtt_rules']
        return []
    except Exception as e:
        logger.error(f"❌ Active GTT rules fetch failed: {e}")
        return []

async def get_gtt_summary() -> Dict[str, Any]:
    """Get summary of all GTT rules."""
    try:
        gtt_list_result = await get_gtt_list()
        if gtt_list_result['success']:
            return {
                'success': True,
                'summary': gtt_list_result['summary'],
                'total_rules': gtt_list_result['total_rules']
            }
        return {'success': False, 'error': gtt_list_result.get('error')}
    except Exception as e:
        logger.error(f"❌ GTT summary failed: {e}")
        return {'success': False, 'error': str(e)}

# Synchronous wrappers
def modify_gtt_rule_sync(gtt_id: str, **kwargs) -> Dict[str, Any]:
    """Synchronous wrapper for modify_gtt_rule."""
    import asyncio
    return asyncio.run(modify_gtt_rule(gtt_id, **kwargs))

def cancel_gtt_rule_sync(gtt_id: str) -> Dict[str, Any]:
    """Synchronous wrapper for cancel_gtt_rule."""
    import asyncio
    return asyncio.run(cancel_gtt_rule(gtt_id))

def get_gtt_details_sync(gtt_id: str) -> Dict[str, Any]:
    """Synchronous wrapper for get_gtt_details."""
    import asyncio
    return asyncio.run(get_gtt_details(gtt_id))

def get_gtt_list_sync() -> Dict[str, Any]:
    """Synchronous wrapper for get_gtt_list."""
    import asyncio
    return asyncio.run(get_gtt_list())

if __name__ == "__main__":
    # Test GTT operations
    async def test_gtt_operations():
        print("🧪 Testing Angel One GTT Operations")
        print("=" * 40)
        
        test_gtt_id = "12345"
        
        print(f"📋 GTT Operations Test:")
        print(f"   Modify GTT: Change price and quantity")
        print(f"   Cancel GTT: Remove active rule") 
        print(f"   Get Details: Fetch rule information")
        print(f"   List All: Show all GTT rules")
        
        try:
            # Test GTT summary
            summary = await get_gtt_summary()
            if summary['success']:
                print(f"✅ GTT summary test passed")
            else:
                print(f"❌ GTT summary failed: {summary.get('error')}")
        except Exception as e:
            print(f"❌ GTT operations test failed: {e}")
        
        print("\n⚠️ Note: Actual GTT operations require valid GTT IDs and live connection")
    
    # Run test
    import asyncio
    asyncio.run(test_gtt_operations())
