"""
Angel One API: batchMargin - Margin Calculator
=============================================

METHOD: Calculate margin requirements for multiple positions
Rate Limit: 1 request/second per API key
Priority: MEDIUM (margin planning and risk management)

Usage:
    from angel_one_api.methods.batch_margin import batch_margin
    
    # Calculate margin for multiple positions
    positions = [
        {
            "exchange": "NSE",
            "tradingsymbol": "RELIANCE-EQ",
            "symboltoken": "2885",
            "quantity": "10",
            "price": "2500.00",
            "product": "INTRADAY",
            "transactiontype": "BUY"
        }
    ]
    
    margin_result = await batch_margin(positions)

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

logger = get_api_logger("batch_margin")

class BatchMarginError(Exception):
    """Raised when batch margin calculation fails."""
    pass

@rate_limited("batch_margin", APIPriority.MEDIUM)
async def batch_margin(
    positions: List[Dict[str, Any]],
    _rate_limit_permit: Optional[Dict] = None
) -> Dict[str, Any]:
    """
    Calculate margin requirements for multiple positions using Angel One API.
    
    Args:
        positions: List of position dicts with:
            - exchange: Exchange name (NSE, BSE, NFO, MCX)
            - tradingsymbol: Trading symbol
            - symboltoken: Symbol token
            - quantity: Quantity as string
            - price: Price as string
            - product: Product type (INTRADAY, DELIVERY, etc.)
            - transactiontype: BUY or SELL
        _rate_limit_permit: Automatically provided by rate limiter
        
    Returns:
        Dict containing:
            - success: bool
            - margin_data: List of margin calculations
            - total_margin: float
            - position_wise_margin: Dict
            - summary: Dict
            - timestamp: str
        
    Raises:
        BatchMarginError: If margin calculation fails
        RateLimitExceeded: If rate limit would be exceeded
        
    Rate Limit: 1 request/second per API key
    """
    try:
        if not _rate_limit_permit:
            raise BatchMarginError("No rate limit permit - internal error")
        
        # Get Angel One client
        # Use interface to get SmartAPI client
        from interface import get_angel_one_interface
        interface = get_angel_one_interface()
        angel_client = interface.smart_api
        
        # angel_client already set above
        if not angel_client:
            raise BatchMarginError("Angel One API client not available")
        
        # Validate positions
        if not positions or not isinstance(positions, list):
            raise BatchMarginError("Positions list is required")
        
        if len(positions) > 50:
            raise BatchMarginError("Maximum 50 positions allowed per request")
        
        # Validate and clean positions
        validated_positions = _validate_margin_positions(positions)
        
        # Log request
        logger.debug(f"💰 Margin calculation for {len(validated_positions)} positions using {_rate_limit_permit['api_key_id']}")
        
        # Make API call with strict rate limiting already enforced
        response = angel_client.getMargin(validated_positions)
        
        # Parse response
        if not response:
            raise BatchMarginError("Empty response from margin calculation API")
        
        if not response.get('status'):
            error_msg = response.get('message', 'Unknown error')
            raise BatchMarginError(f"Margin calculation API error: {error_msg}")
        
        margin_data = response.get('data', [])
        
        # Process margin data
        processed_margins = _process_margin_data(margin_data, validated_positions)
        position_wise_margin = _create_position_wise_mapping(processed_margins, validated_positions)
        summary = _calculate_margin_summary(processed_margins)
        
        # Success response
        result = {
            'success': True,
            'margin_data': processed_margins,
            'position_wise_margin': position_wise_margin,
            'total_margin': summary.get('total_margin_required', 0),
            'summary': summary,
            'positions_count': len(validated_positions),
            'raw_data': margin_data,
            'timestamp': datetime.now(UTC).isoformat(),
            'api_key_id': _rate_limit_permit['api_key_id'],
            'response_time': time.time()
        }
        
        logger.info(f"✅ Margin calculated: {len(validated_positions)} positions, Total: ₹{summary.get('total_margin_required', 0):.2f}")
        
        return result
        
    except Exception as e:
        logger.error(f"❌ Margin calculation failed: {e}")
        
        # Create error response
        error_result = {
            'success': False,
            'margin_data': [],
            'total_margin': 0,
            'error': str(e),
            'timestamp': datetime.now(UTC).isoformat()
        }
        
        # Re-raise as BatchMarginError for consistent error handling
        if isinstance(e, BatchMarginError):
            raise
        else:
            raise BatchMarginError(f"Margin calculation failed: {e}")

def _validate_margin_positions(positions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Validate and clean margin calculation positions.
    
    Args:
        positions: Raw position data
        
    Returns:
        List: Validated positions
        
    Raises:
        BatchMarginError: If validation fails
    """
    validated = []
    
    for i, position in enumerate(positions):
        try:
            # Required fields
            required_fields = ['exchange', 'tradingsymbol', 'symboltoken', 'quantity', 'price', 'product', 'transactiontype']
            missing_fields = [field for field in required_fields if not position.get(field)]
            
            if missing_fields:
                raise BatchMarginError(f"Position {i+1} missing fields: {missing_fields}")
            
            validated_position = {
                'exchange': position['exchange'].upper(),
                'tradingsymbol': position['tradingsymbol'],
                'symboltoken': str(position['symboltoken']),
                'quantity': str(position['quantity']),
                'price': str(float(position['price'])),
                'product': position['product'].upper(),
                'transactiontype': position['transactiontype'].upper()
            }
            
            # Validate values
            if validated_position['exchange'] not in ['NSE', 'BSE', 'NFO', 'MCX']:
                raise BatchMarginError(f"Invalid exchange: {validated_position['exchange']}")
            
            if validated_position['transactiontype'] not in ['BUY', 'SELL']:
                raise BatchMarginError(f"Invalid transaction type: {validated_position['transactiontype']}")
            
            if validated_position['product'] not in ['INTRADAY', 'DELIVERY', 'CARRYFORWARD', 'MIS', 'CNC']:
                raise BatchMarginError(f"Invalid product: {validated_position['product']}")
            
            # Validate numeric values
            quantity = int(validated_position['quantity'])
            price = float(validated_position['price'])
            
            if quantity <= 0:
                raise BatchMarginError(f"Invalid quantity: {quantity}")
            if price <= 0:
                raise BatchMarginError(f"Invalid price: {price}")
            
            validated.append(validated_position)
            
        except (ValueError, TypeError) as e:
            raise BatchMarginError(f"Position {i+1} validation error: {e}")
    
    return validated

def _process_margin_data(margin_data: List[Dict[str, Any]], positions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Process raw margin data from Angel One API.
    
    Args:
        margin_data: Raw margin data from API
        positions: Original position data for reference
        
    Returns:
        List: Processed margin data
    """
    processed_margins = []
    
    for i, (margin, position) in enumerate(zip(margin_data, positions)):
        try:
            processed = {
                'position_index': i,
                'symbol': position.get('tradingsymbol'),
                'exchange': position.get('exchange'),
                'quantity': int(position.get('quantity', 0)),
                'price': float(position.get('price', 0)),
                'product': position.get('product'),
                'transaction_type': position.get('transactiontype'),
                
                # Margin fields
                'margin_required': float(margin.get('marginrequired', 0)),
                'additional_margin': float(margin.get('additionalmargin', 0)),
                'exposure_margin': float(margin.get('exposuremargin', 0)),
                'span_margin': float(margin.get('spanmargin', 0)),
                'elm_margin': float(margin.get('elmmargin', 0)),
                'var_margin': float(margin.get('varmargin', 0)),
                'total_margin': float(margin.get('totalmargin', 0)),
                
                # Calculated fields
                'position_value': int(position.get('quantity', 0)) * float(position.get('price', 0)),
                'margin_percentage': 0.0
            }
            
            # Calculate margin percentage
            if processed['position_value'] > 0:
                processed['margin_percentage'] = (processed['total_margin'] / processed['position_value']) * 100
            
            processed_margins.append(processed)
            
        except (ValueError, TypeError) as e:
            logger.warning(f"⚠️ Error processing margin data for position {i}: {e}")
            # Add minimal data for failed processing
            processed_margins.append({
                'position_index': i,
                'symbol': position.get('tradingsymbol', 'UNKNOWN'),
                'error': str(e),
                'margin_required': 0,
                'total_margin': 0
            })
    
    return processed_margins

def _create_position_wise_mapping(processed_margins: List[Dict[str, Any]], positions: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    """Create a mapping of symbol to margin data."""
    mapping = {}
    
    for margin_data in processed_margins:
        symbol = margin_data.get('symbol', 'UNKNOWN')
        mapping[symbol] = margin_data
    
    return mapping

def _calculate_margin_summary(processed_margins: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Calculate summary statistics for margin data."""
    if not processed_margins:
        return {'total_margin_required': 0}
    
    total_margin = sum(m.get('total_margin', 0) for m in processed_margins)
    total_position_value = sum(m.get('position_value', 0) for m in processed_margins)
    
    buy_positions = [m for m in processed_margins if m.get('transaction_type') == 'BUY']
    sell_positions = [m for m in processed_margins if m.get('transaction_type') == 'SELL']
    
    summary = {
        'total_margin_required': total_margin,
        'total_position_value': total_position_value,
        'average_margin_percentage': (total_margin / total_position_value * 100) if total_position_value > 0 else 0,
        'positions_count': len(processed_margins),
        'buy_positions_count': len(buy_positions),
        'sell_positions_count': len(sell_positions),
        'buy_margin': sum(m.get('total_margin', 0) for m in buy_positions),
        'sell_margin': sum(m.get('total_margin', 0) for m in sell_positions),
        'highest_margin_position': max(processed_margins, key=lambda x: x.get('total_margin', 0)) if processed_margins else None,
        'highest_margin_percentage': max(m.get('margin_percentage', 0) for m in processed_margins) if processed_margins else 0
    }
    
    return summary

async def calculate_single_margin(
    exchange: str,
    tradingsymbol: str,
    symboltoken: str,
    quantity: int,
    price: float,
    product: str = "INTRADAY",
    transactiontype: str = "BUY"
) -> Dict[str, Any]:
    """
    Calculate margin for a single position.
    
    Args:
        exchange: Exchange name
        tradingsymbol: Trading symbol
        symboltoken: Symbol token
        quantity: Quantity
        price: Price
        product: Product type
        transactiontype: Transaction type
        
    Returns:
        Dict: Single position margin data
    """
    position = [{
        'exchange': exchange,
        'tradingsymbol': tradingsymbol,
        'symboltoken': symboltoken,
        'quantity': str(quantity),
        'price': str(price),
        'product': product,
        'transactiontype': transactiontype
    }]
    
    try:
        result = await batch_margin(position)
        if result['success'] and result['margin_data']:
            return result['margin_data'][0]
        return {'success': False, 'error': result.get('error', 'Unknown error')}
    except Exception as e:
        return {'success': False, 'error': str(e)}

async def check_margin_sufficiency(
    positions: List[Dict[str, Any]],
    available_funds: float
) -> Dict[str, Any]:
    """
    Check if available funds are sufficient for positions.
    
    Args:
        positions: List of positions
        available_funds: Available funds amount
        
    Returns:
        Dict: Margin sufficiency analysis
    """
    try:
        margin_result = await batch_margin(positions)
        
        if not margin_result['success']:
            return {'success': False, 'error': margin_result.get('error')}
        
        total_margin = margin_result['total_margin']
        sufficient = available_funds >= total_margin
        
        analysis = {
            'success': True,
            'margin_sufficient': sufficient,
            'required_margin': total_margin,
            'available_funds': available_funds,
            'excess_funds': available_funds - total_margin if sufficient else 0,
            'shortfall': total_margin - available_funds if not sufficient else 0,
            'utilization_percentage': (total_margin / available_funds * 100) if available_funds > 0 else 100,
            'positions_analysis': margin_result['margin_data'],
            'recommendation': _get_margin_recommendation(sufficient, total_margin, available_funds)
        }
        
        return analysis
        
    except Exception as e:
        logger.error(f"❌ Margin sufficiency check failed: {e}")
        return {'success': False, 'error': str(e)}

def _get_margin_recommendation(sufficient: bool, required: float, available: float) -> Dict[str, str]:
    """Get margin recommendation based on analysis."""
    if not sufficient:
        return {
            'action': 'CANNOT_PROCEED',
            'reason': f'Insufficient funds. Need ₹{required - available:.2f} more.',
            'suggestion': 'Reduce position size or add more funds'
        }
    
    utilization = (required / available) * 100 if available > 0 else 100
    
    if utilization > 90:
        return {
            'action': 'HIGH_RISK',
            'reason': f'High margin utilization ({utilization:.1f}%)',
            'suggestion': 'Consider reducing position size for safety'
        }
    elif utilization > 70:
        return {
            'action': 'MODERATE_RISK',
            'reason': f'Moderate margin utilization ({utilization:.1f}%)',
            'suggestion': 'Monitor positions closely'
        }
    else:
        return {
            'action': 'PROCEED',
            'reason': f'Safe margin utilization ({utilization:.1f}%)',
            'suggestion': 'Positions can be taken safely'
        }

def batch_margin_sync(positions: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Synchronous wrapper for batch_margin.
    
    ⚠️ WARNING: Use async version when possible for better performance.
    This is only for compatibility with legacy code.
    """
    import asyncio
    try:
        return asyncio.run(batch_margin(positions))
    except Exception as e:
        logger.error(f"❌ Sync margin calculation failed: {e}")
        return {
            'success': False,
            'margin_data': [],
            'total_margin': 0,
            'error': str(e)
        }

# Backward compatibility aliases (DEPRECATED - use new names)
calculate_margin = batch_margin  # Alias for existing code
get_margin_requirements = batch_margin  # Alias for existing code

if __name__ == "__main__":
    # Test margin calculation
    async def test_margin_calculation():
        print("🧪 Testing Angel One Margin Calculation")
        print("=" * 40)
        
        # Test positions
        test_positions = [
            {
                "exchange": "NSE",
                "tradingsymbol": "RELIANCE-EQ",
                "symboltoken": "2885",
                "quantity": "10",
                "price": "2500.00",
                "product": "INTRADAY",
                "transactiontype": "BUY"
            },
            {
                "exchange": "NSE",
                "tradingsymbol": "TCS-EQ",
                "symboltoken": "11536",
                "quantity": "5",
                "price": "3800.00",
                "product": "DELIVERY",
                "transactiontype": "BUY"
            }
        ]
        
        try:
            # Test validation
            validated = _validate_margin_positions(test_positions)
            print(f"✅ Position validation successful: {len(validated)} positions")
            
            for i, pos in enumerate(validated):
                print(f"   Position {i+1}: {pos['tradingsymbol']} x{pos['quantity']} @ ₹{pos['price']}")
            
        except Exception as e:
            print(f"❌ Position validation failed: {e}")
        
        print("\n⚠️ Note: Actual margin calculation requires rate controller and live connection")
    
    # Run test
    import asyncio
    asyncio.run(test_margin_calculation())
