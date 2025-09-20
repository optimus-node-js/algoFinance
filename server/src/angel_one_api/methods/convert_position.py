"""
Angel One API: convertPosition - Position Conversion
===================================================

CRITICAL METHOD: Convert positions (Intraday to Delivery, etc.)
Rate Limit: 10 requests/second per API key
Priority: MEDIUM (important for position management)

Usage:
    from angel_one_api.methods.convert_position import convert_position
    
    # Convert intraday position to delivery
    result = await convert_position(
        exchange="NSE",
        tradingsymbol="RELIANCE-EQ",
        symboltoken="2885",
        transactiontype="BUY",
        positiontype="DAY",
        targetproduct="DELIVERY",
        quantity="10"
    )

Author: AI Trading System
Rate Limit: STRICTLY ENFORCED 10 req/sec per key
"""

import time
from typing import Dict, List, Optional, Any
# Import new Angel One logger
from ..logger import get_api_logger
from datetime import datetime, UTC

# Import our rate limiting system
from ..rate_limiter.rate_controller import get_rate_controller, rate_limited, APIPriority
from ..rate_limiter.api_limits import API_LIMITS

logger = get_api_logger("convert_position")

class ConvertPositionError(Exception):
    """Raised when position conversion fails."""
    pass

@rate_limited("convert_position", APIPriority.MEDIUM)
async def convert_position(
    exchange: str,
    tradingsymbol: str,
    symboltoken: str,
    transactiontype: str,
    positiontype: str,
    targetproduct: str,
    quantity: str,
    _rate_limit_permit: Optional[Dict] = None
) -> Dict[str, Any]:
    """
    Convert position from one product type to another using Angel One API.
    
    Args:
        exchange: Exchange name (NSE, BSE, NFO, MCX)
        tradingsymbol: Trading symbol (e.g., "RELIANCE-EQ")
        symboltoken: Angel One symbol token
        transactiontype: Transaction type (BUY, SELL)
        positiontype: Current position type (DAY, NET)
        targetproduct: Target product type (DELIVERY, INTRADAY, CARRYFORWARD)
        quantity: Quantity to convert
        _rate_limit_permit: Automatically provided by rate limiter
        
    Returns:
        Dict containing:
            - success: bool
            - conversion_id: str (if successful)
            - message: str
            - response: dict (full API response)
        
    Raises:
        ConvertPositionError: If position conversion fails
        RateLimitExceeded: If rate limit would be exceeded
        
    Rate Limit: 10 requests/second per API key
    """
    try:
        if not _rate_limit_permit:
            raise ConvertPositionError("No rate limit permit - internal error")
        
        # Get Angel One client
        from core.connections import ConnectionManager
        
        angel_client = ConnectionManager.get_smartapi_client()
        if not angel_client:
            raise ConvertPositionError("Angel One API client not available")
        
        # Validate required parameters
        required_params = [
            exchange, tradingsymbol, symboltoken, transactiontype,
            positiontype, targetproduct, quantity
        ]
        
        if not all(required_params):
            raise ConvertPositionError("All parameters are required for position conversion")
        
        # Build conversion parameters
        convert_params = {
            'exchange': exchange,
            'tradingsymbol': tradingsymbol,
            'symboltoken': str(symboltoken),
            'transactiontype': transactiontype,
            'positiontype': positiontype,
            'targetproduct': targetproduct,
            'quantity': str(quantity)
        }
        
        # Validate parameters
        validated_params = _validate_conversion_parameters(convert_params)
        
        # Log conversion attempt
        logger.info(
            f"🔄 Position conversion: {validated_params['tradingsymbol']} "
            f"{validated_params['quantity']} from {validated_params['positiontype']} "
            f"to {validated_params['targetproduct']} using {_rate_limit_permit['api_key_id']}"
        )
        
        # Make API call with strict rate limiting already enforced
        response = angel_client.convertPosition(validated_params)
        
        # Parse response
        if not response:
            raise ConvertPositionError("Empty response from convertPosition API")
        
        if not response.get('status'):
            error_msg = response.get('message', 'Unknown conversion error')
            error_code = response.get('errorcode', 'N/A')
            raise ConvertPositionError(f"Position conversion failed: {error_msg} (Code: {error_code})")
        
        # Extract conversion details
        data = response.get('data', {})
        conversion_id = data.get('orderid') or data.get('conversionid', 'N/A')
        
        # Success response
        result = {
            'success': True,
            'conversion_id': conversion_id,
            'message': 'Position converted successfully',
            'response': response,
            'conversion_params': validated_params,
            'conversion_details': {
                'symbol': validated_params['tradingsymbol'],
                'quantity': validated_params['quantity'],
                'from_type': validated_params['positiontype'],
                'to_type': validated_params['targetproduct'],
                'transaction_type': validated_params['transactiontype']
            },
            'api_key_id': _rate_limit_permit['api_key_id'],
            'timestamp': time.time()
        }
        
        logger.info(f"✅ Position converted successfully: {conversion_id}")
        
        return result
        
    except Exception as e:
        logger.error(f"❌ Position conversion failed for {tradingsymbol}: {e}")
        
        # Create error response
        error_result = {
            'success': False,
            'conversion_id': None,
            'message': str(e),
            'response': None,
            'error': str(e),
            'timestamp': time.time()
        }
        
        # Re-raise as ConvertPositionError for consistent error handling
        if isinstance(e, ConvertPositionError):
            raise
        else:
            raise ConvertPositionError(f"Position conversion failed: {e}")

def _validate_conversion_parameters(convert_params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate and clean position conversion parameters.
    
    Args:
        convert_params: Raw conversion parameters
        
    Returns:
        Dict: Validated and cleaned parameters
        
    Raises:
        ConvertPositionError: If validation fails
    """
    validated = convert_params.copy()
    
    # Validate exchange
    valid_exchanges = ['NSE', 'BSE', 'NFO', 'MCX']
    if validated.get('exchange') not in valid_exchanges:
        raise ConvertPositionError(f"Invalid exchange. Must be one of: {valid_exchanges}")
    
    # Validate transaction type
    if validated.get('transactiontype') not in ['BUY', 'SELL']:
        raise ConvertPositionError("Invalid transactiontype. Must be 'BUY' or 'SELL'")
    
    # Validate position type
    valid_position_types = ['DAY', 'NET']
    if validated.get('positiontype') not in valid_position_types:
        raise ConvertPositionError(f"Invalid positiontype. Must be one of: {valid_position_types}")
    
    # Validate target product
    valid_products = ['DELIVERY', 'INTRADAY', 'CARRYFORWARD', 'CNC', 'MIS']
    if validated.get('targetproduct') not in valid_products:
        raise ConvertPositionError(f"Invalid targetproduct. Must be one of: {valid_products}")
    
    # Validate quantity
    try:
        quantity = int(validated['quantity'])
        if quantity <= 0:
            raise ValueError("Quantity must be positive")
        validated['quantity'] = str(quantity)
    except (ValueError, TypeError):
        raise ConvertPositionError("Invalid quantity. Must be a positive integer")
    
    # Validate symbol token
    if not validated.get('symboltoken'):
        raise ConvertPositionError("Symbol token is required")
    
    # Validate trading symbol
    if not validated.get('tradingsymbol'):
        raise ConvertPositionError("Trading symbol is required")
    
    return validated

async def convert_intraday_to_delivery(
    symbol: str,
    symbol_token: str,
    transaction_type: str,
    quantity: int,
    exchange: str = "NSE"
) -> Dict[str, Any]:
    """
    Simplified conversion from intraday to delivery.
    
    Args:
        symbol: Trading symbol (e.g., "RELIANCE-EQ")
        symbol_token: Angel One symbol token
        transaction_type: "BUY" or "SELL"
        quantity: Quantity to convert
        exchange: Exchange name (default: "NSE")
        
    Returns:
        Dict: Conversion result
    """
    return await convert_position(
        exchange=exchange,
        tradingsymbol=symbol,
        symboltoken=symbol_token,
        transactiontype=transaction_type,
        positiontype="DAY",
        targetproduct="DELIVERY",
        quantity=str(quantity)
    )

async def convert_delivery_to_intraday(
    symbol: str,
    symbol_token: str,
    transaction_type: str,
    quantity: int,
    exchange: str = "NSE"
) -> Dict[str, Any]:
    """
    Simplified conversion from delivery to intraday.
    
    Args:
        symbol: Trading symbol (e.g., "RELIANCE-EQ")
        symbol_token: Angel One symbol token
        transaction_type: "BUY" or "SELL"
        quantity: Quantity to convert
        exchange: Exchange name (default: "NSE")
        
    Returns:
        Dict: Conversion result
    """
    return await convert_position(
        exchange=exchange,
        tradingsymbol=symbol,
        symboltoken=symbol_token,
        transactiontype=transaction_type,
        positiontype="NET",
        targetproduct="INTRADAY",
        quantity=str(quantity)
    )

async def bulk_convert_positions(
    conversions: List[Dict[str, Any]],
    batch_delay: float = 0.1  # 10 req/sec = 0.1s between requests
) -> Dict[str, Any]:
    """
    Convert multiple positions efficiently with rate limiting.
    
    Args:
        conversions: List of conversion parameter dicts
        batch_delay: Delay between conversions in seconds
        
    Returns:
        Dict: Bulk conversion results
    """
    if not conversions:
        return {
            'success': True,
            'total_conversions': 0,
            'successful_count': 0,
            'failed_count': 0,
            'results': {}
        }
    
    logger.info(f"🔄 Bulk position conversion: {len(conversions)} conversions")
    
    results = {}
    successful_count = 0
    failed_count = 0
    
    for i, conversion_params in enumerate(conversions):
        batch_start_time = time.time()
        
        conversion_key = f"{conversion_params.get('tradingsymbol')}_{i}"
        
        try:
            conversion_result = await convert_position(**conversion_params)
            results[conversion_key] = conversion_result
            
            if conversion_result['success']:
                successful_count += 1
                logger.debug(f"✅ Converted {i+1}/{len(conversions)}: {conversion_key}")
            else:
                failed_count += 1
                logger.warning(f"❌ Failed {i+1}/{len(conversions)}: {conversion_key}")
                
        except Exception as e:
            failed_count += 1
            logger.warning(f"❌ Conversion failed for {conversion_key}: {e}")
            results[conversion_key] = {
                'success': False,
                'conversion_id': None,
                'error': str(e)
            }
        
        # Add delay between requests (except for last one)
        if i < len(conversions) - 1:
            elapsed = time.time() - batch_start_time
            if elapsed < batch_delay:
                sleep_time = batch_delay - elapsed
                await asyncio.sleep(sleep_time)
    
    summary = {
        'success': True,
        'total_conversions': len(conversions),
        'successful_count': successful_count,
        'failed_count': failed_count,
        'success_rate': (successful_count / len(conversions)) * 100,
        'results': results,
        'timestamp': time.time()
    }
    
    logger.info(f"✅ Bulk conversion complete: {successful_count}/{len(conversions)} successful")
    
    return summary

async def get_convertible_positions() -> List[Dict[str, Any]]:
    """
    Get positions that can be converted.
    
    Returns:
        List: Positions eligible for conversion
    """
    try:
        # Get current positions
        from .get_position import get_position
        
        positions_result = await get_position()
        if not positions_result['success']:
            return []
        
        positions = positions_result['positions']
        
        # Filter positions that can be converted
        convertible_positions = []
        for position in positions:
            # Positions with non-zero quantity can potentially be converted
            if position.get('netqty', 0) != 0:
                # Add conversion suggestions
                position_copy = position.copy()
                position_copy['conversion_suggestions'] = _get_conversion_suggestions(position)
                convertible_positions.append(position_copy)
        
        return convertible_positions
        
    except Exception as e:
        logger.error(f"❌ Convertible positions fetch failed: {e}")
        return []

def _get_conversion_suggestions(position: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Get conversion suggestions for a position.
    
    Args:
        position: Position data
        
    Returns:
        List: Conversion suggestions
    """
    suggestions = []
    
    product_type = position.get('producttype', '').upper()
    net_qty = position.get('netqty', 0)
    
    if net_qty == 0:
        return suggestions  # No conversion needed for zero quantity
    
    # Suggest conversions based on current product type
    if product_type in ['INTRADAY', 'MIS']:
        suggestions.append({
            'from_type': 'DAY',
            'to_type': 'DELIVERY',
            'description': 'Convert intraday position to delivery',
            'benefit': 'Avoid square-off, hold overnight'
        })
    
    elif product_type in ['DELIVERY', 'CNC']:
        suggestions.append({
            'from_type': 'NET',
            'to_type': 'INTRADAY',
            'description': 'Convert delivery position to intraday',
            'benefit': 'Use as margin for day trading'
        })
    
    return suggestions

def convert_position_sync(
    exchange: str,
    tradingsymbol: str,
    symboltoken: str,
    transactiontype: str,
    positiontype: str,
    targetproduct: str,
    quantity: str
) -> Dict[str, Any]:
    """
    Synchronous wrapper for convert_position.
    
    ⚠️ WARNING: Use async version when possible for better performance.
    This is only for compatibility with legacy code.
    """
    import asyncio
    try:
        return asyncio.run(convert_position(
            exchange, tradingsymbol, symboltoken, transactiontype,
            positiontype, targetproduct, quantity
        ))
    except Exception as e:
        logger.error(f"❌ Sync position conversion failed for {tradingsymbol}: {e}")
        return {
            'success': False,
            'conversion_id': None,
            'message': str(e),
            'error': str(e)
        }

# Backward compatibility aliases (DEPRECATED - use new names)
change_position_type = convert_position  # Alias for existing code
switch_product_type = convert_position   # Alias for existing code

if __name__ == "__main__":
    # Test position conversion
    async def test_position_conversion():
        print("🧪 Testing Angel One Position Conversion")
        print("=" * 40)
        print("⚠️ Note: This is a test - no real positions will be converted")
        
        # Test parameter validation
        test_params = {
            'exchange': 'NSE',
            'tradingsymbol': 'RELIANCE-EQ',
            'symboltoken': '2885',
            'transactiontype': 'BUY',
            'positiontype': 'DAY',
            'targetproduct': 'DELIVERY',
            'quantity': '10'
        }
        
        try:
            validated = _validate_conversion_parameters(test_params)
            print(f"✅ Parameter validation successful")
            print(f"   Symbol: {validated['tradingsymbol']}")
            print(f"   Conversion: {validated['positiontype']} → {validated['targetproduct']}")
            print(f"   Quantity: {validated['quantity']}")
        except Exception as e:
            print(f"❌ Parameter validation failed: {e}")
        
        print("\n⚠️ Note: Actual position conversion requires rate controller and live connection")
    
    # Run test
    import asyncio
    asyncio.run(test_position_conversion())
