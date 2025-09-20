"""
Angel One API: getPosition - Position Data Retrieval
===================================================

CRITICAL METHOD: Portfolio tracking and risk management
Rate Limit: 1 request/second per API key
Priority: HIGH (essential for position tracking)

MOVED FROM: services/portfolio_management/portfolio_service.py, services/risk_management/risk_service.py
This method consolidates and improves existing position tracking logic.

Usage:
    from angel_one_api.methods.get_position import get_position
    
    # Get all current positions
    positions = await get_position()
    
    # Get positions with detailed analysis
    detailed_positions = await get_detailed_positions()
    
    # Check specific symbol position
    symbol_position = await get_symbol_position("RELIANCE-EQ")

Author: AI Trading System
Rate Limit: STRICTLY ENFORCED 1 req/sec per key
"""

import time
from typing import Dict, List, Optional, Any
import logging
from datetime import datetime, UTC

# Import our rate limiting system
from ..rate_limiter.rate_controller import get_rate_controller, rate_limited, APIPriority
from ..rate_limiter.api_limits import API_LIMITS

logger = logging.getLogger(__name__)

class PositionError(Exception):
    """Raised when position data fetching fails."""
    pass

@rate_limited("get_position", APIPriority.HIGH)
async def get_position(_rate_limit_permit: Optional[Dict] = None) -> Dict[str, Any]:
    """
    Get current positions from Angel One API.
    
    Args:
        _rate_limit_permit: Automatically provided by rate limiter
        
    Returns:
        Dict containing:
            - success: bool
            - positions: List of position data
            - total_positions: int
            - day_positions: List (intraday positions)
            - net_positions: List (overnight positions)
            - timestamp: str
        
    Raises:
        PositionError: If position fetching fails
        RateLimitExceeded: If rate limit would be exceeded
        
    Rate Limit: 1 request/second per API key
    """
    try:
        if not _rate_limit_permit:
            raise PositionError("No rate limit permit - internal error")
        
        # Get Angel One client
        from core.connections import ConnectionManager
        
        angel_client = ConnectionManager.get_smartapi_client()
        if not angel_client:
            raise PositionError("Angel One API client not available")
        
        # Log request
        logger.debug(f"📈 Position data request using {_rate_limit_permit['api_key_id']}")
        
        # Make API call with strict rate limiting already enforced
        response = angel_client.position()
        
        # Parse response
        if not response:
            raise PositionError("Empty response from position API")
        
        if not response.get('status'):
            error_msg = response.get('message', 'Unknown error')
            raise PositionError(f"Position API error: {error_msg}")
        
        positions_data = response.get('data', [])
        
        # Handle None data (empty positions)
        if positions_data is None:
            logger.debug("📝 No positions found - empty portfolio")
            positions_data = []
        
        # Validate positions data
        if not isinstance(positions_data, list):
            raise PositionError(f"Invalid positions data format received. Expected list, got {type(positions_data)}: {positions_data}")
        
        # Process and categorize positions
        day_positions = []
        net_positions = []
        all_positions = []
        
        for position in positions_data:
            # Clean and validate position data
            processed_position = _process_position_data(position)
            all_positions.append(processed_position)
            
            # Categorize by product type
            product_type = position.get('producttype', '').upper()
            if product_type in ['INTRADAY', 'MIS']:
                day_positions.append(processed_position)
            elif product_type in ['DELIVERY', 'CNC', 'CARRYFORWARD']:
                net_positions.append(processed_position)
        
        # Calculate summary statistics
        total_unrealized_pnl = sum(
            float(pos.get('unrealisedpnl', 0)) for pos in all_positions
        )
        total_realized_pnl = sum(
            float(pos.get('realisedpnl', 0)) for pos in all_positions
        )
        
        # Success response
        result = {
            'success': True,
            'positions': all_positions,
            'day_positions': day_positions,
            'net_positions': net_positions,
            'total_positions': len(all_positions),
            'summary': {
                'total_unrealized_pnl': total_unrealized_pnl,
                'total_realized_pnl': total_realized_pnl,
                'total_pnl': total_unrealized_pnl + total_realized_pnl,
                'day_positions_count': len(day_positions),
                'net_positions_count': len(net_positions)
            },
            'timestamp': datetime.now(UTC).isoformat(),
            'api_key_id': _rate_limit_permit['api_key_id'],
            'response_time': time.time()
        }
        
        logger.info(f"✅ Positions fetched: {len(all_positions)} total positions")
        
        return result
        
    except Exception as e:
        logger.error(f"❌ Position fetch failed: {e}")
        
        # Create error response
        error_result = {
            'success': False,
            'positions': [],
            'total_positions': 0,
            'error': str(e),
            'timestamp': datetime.now(UTC).isoformat()
        }
        
        # Re-raise as PositionError for consistent error handling
        if isinstance(e, PositionError):
            raise
        else:
            raise PositionError(f"Position fetch failed: {e}")

def _process_position_data(position: Dict[str, Any]) -> Dict[str, Any]:
    """
    Process and clean raw position data from Angel One API.
    
    Args:
        position: Raw position data from API
        
    Returns:
        Dict: Cleaned and enhanced position data
    """
    try:
        # Core position fields
        processed = {
            'tradingsymbol': position.get('tradingsymbol', ''),
            'exchange': position.get('exchange', ''),
            'producttype': position.get('producttype', ''),
            'symboltoken': position.get('symboltoken', ''),
            
            # Quantity fields (with null safety)
            'buyqty': int(position.get('buyqty') or 0),
            'sellqty': int(position.get('sellqty') or 0),
            'netqty': int(position.get('netqty') or 0),
            
            # Price fields (with null safety)
            'buyavgprice': float(position.get('buyavgprice') or 0),
            'sellavgprice': float(position.get('sellavgprice') or 0),
            'ltp': float(position.get('ltp') or 0),
            'close': float(position.get('close') or 0),
            
            # P&L fields (with null safety)
            'unrealisedpnl': float(position.get('unrealisedpnl') or 0),
            'realisedpnl': float(position.get('realisedpnl') or 0),
            'pnl': float(position.get('pnl') or 0),
            'pnlpercentage': float(position.get('pnlpercentage') or 0),
            
            # Additional fields (with null safety)
            'multiplier': float(position.get('multiplier') or 1),
            'precision': int(position.get('precision') or 2),
            'lotsize': int(position.get('lotsize') or 1)
        }
        
        # Calculate derived fields
        processed['total_quantity'] = abs(processed['netqty'])
        processed['position_value'] = processed['total_quantity'] * processed['ltp']
        processed['position_side'] = 'LONG' if processed['netqty'] > 0 else 'SHORT' if processed['netqty'] < 0 else 'FLAT'
        
        # Calculate percentage change
        if processed['close'] > 0:
            processed['day_change_pct'] = ((processed['ltp'] - processed['close']) / processed['close']) * 100
        else:
            processed['day_change_pct'] = 0.0
        
        return processed
        
    except (ValueError, TypeError) as e:
        logger.warning(f"⚠️ Error processing position data: {e}")
        return position  # Return original if processing fails

async def get_detailed_positions() -> Dict[str, Any]:
    """
    Get positions with additional analysis and risk metrics.
    
    Returns:
        Dict: Enhanced position data with risk analysis
    """
    try:
        # Get basic positions
        positions_result = await get_position()
        
        if not positions_result['success']:
            return positions_result
        
        positions = positions_result['positions']
        
        # Add risk analysis for each position
        enhanced_positions = []
        for position in positions:
            enhanced_position = position.copy()
            
            # Add risk metrics
            enhanced_position.update(_calculate_position_risk(position))
            enhanced_positions.append(enhanced_position)
        
        # Update result with enhanced data
        positions_result['positions'] = enhanced_positions
        positions_result['enhanced'] = True
        
        return positions_result
        
    except Exception as e:
        logger.error(f"❌ Enhanced position fetch failed: {e}")
        raise PositionError(f"Enhanced position fetch failed: {e}")

def _calculate_position_risk(position: Dict[str, Any]) -> Dict[str, Any]:
    """
    Calculate risk metrics for a position.
    
    Args:
        position: Position data
        
    Returns:
        Dict: Risk metrics
    """
    risk_metrics = {}
    
    try:
        ltp = position.get('ltp', 0)
        netqty = position.get('netqty', 0)
        position_value = position.get('position_value', 0)
        
        # Calculate basic risk metrics
        if netqty != 0 and ltp > 0:
            # Risk per share (2% stop loss)
            risk_metrics['risk_per_share_2pct'] = ltp * 0.02
            risk_metrics['total_risk_2pct'] = abs(netqty) * risk_metrics['risk_per_share_2pct']
            
            # Position size as percentage (would need portfolio value)
            # risk_metrics['position_size_pct'] = (position_value / portfolio_value) * 100
            
            # Volatility risk (simplified)
            if position.get('day_change_pct'):
                risk_metrics['daily_volatility_risk'] = abs(position['day_change_pct'])
        
        # Position concentration risk
        risk_metrics['position_value'] = position_value
        risk_metrics['is_large_position'] = position_value > 100000  # > 1 lakh
        
    except Exception as e:
        logger.warning(f"⚠️ Risk calculation error: {e}")
    
    return risk_metrics

async def get_symbol_position(symbol: str) -> Optional[Dict[str, Any]]:
    """
    Get position data for a specific symbol.
    
    Args:
        symbol: Trading symbol (e.g., "RELIANCE-EQ")
        
    Returns:
        Dict: Position data for symbol or None if not found
    """
    try:
        positions_result = await get_position()
        
        if not positions_result['success']:
            return None
        
        # Find matching symbol
        for position in positions_result['positions']:
            if position.get('tradingsymbol') == symbol:
                return position
        
        return None
        
    except Exception as e:
        logger.error(f"❌ Symbol position fetch failed for {symbol}: {e}")
        return None

async def get_positions_summary() -> Dict[str, Any]:
    """
    Get a summary of all positions with key metrics.
    
    Returns:
        Dict: Position summary with key metrics
    """
    try:
        positions_result = await get_position()
        
        if not positions_result['success']:
            return {'success': False, 'error': positions_result.get('error')}
        
        summary = positions_result['summary'].copy()
        positions = positions_result['positions']
        
        # Add more detailed metrics
        symbols_with_positions = [pos['tradingsymbol'] for pos in positions if pos['netqty'] != 0]
        largest_position = max(positions, key=lambda x: abs(x.get('position_value', 0))) if positions else None
        
        summary.update({
            'symbols_count': len(symbols_with_positions),
            'symbols_with_positions': symbols_with_positions,
            'largest_position': {
                'symbol': largest_position['tradingsymbol'] if largest_position else None,
                'value': largest_position.get('position_value', 0) if largest_position else 0
            } if largest_position else None
        })
        
        return {
            'success': True,
            'summary': summary,
            'timestamp': positions_result['timestamp']
        }
        
    except Exception as e:
        logger.error(f"❌ Position summary failed: {e}")
        return {'success': False, 'error': str(e)}

def get_position_sync() -> Dict[str, Any]:
    """
    Synchronous wrapper for get_position.
    
    ⚠️ WARNING: Use async version when possible for better performance.
    This is only for compatibility with legacy code.
    """
    import asyncio
    try:
        return asyncio.run(get_position())
    except Exception as e:
        logger.error(f"❌ Sync position fetch failed: {e}")
        return {
            'success': False,
            'positions': [],
            'total_positions': 0,
            'error': str(e)
        }

# Backward compatibility aliases (DEPRECATED - use new names)
fetch_positions = get_position  # Alias for existing code
get_portfolio_positions = get_position  # Alias for existing code

if __name__ == "__main__":
    # Test position fetching
    async def test_position_data():
        print("🧪 Testing Angel One Position Data")
        print("=" * 40)
        
        try:
            # Test basic positions
            positions = await get_position()
            if positions['success']:
                print(f"✅ Positions fetched: {positions['total_positions']} positions")
                print(f"   Day positions: {positions['summary']['day_positions_count']}")
                print(f"   Net positions: {positions['summary']['net_positions_count']}")
                print(f"   Total P&L: ₹{positions['summary']['total_pnl']:.2f}")
            else:
                print(f"❌ Position fetch failed: {positions.get('error')}")
                
        except Exception as e:
            print(f"❌ Position test failed: {e}")
        
        try:
            # Test position summary
            summary = await get_positions_summary()
            if summary['success']:
                print(f"✅ Position summary: {summary['summary']['symbols_count']} symbols")
                if summary['summary']['largest_position']:
                    largest = summary['summary']['largest_position']
                    print(f"   Largest: {largest['symbol']} (₹{largest['value']:.2f})")
            else:
                print(f"❌ Position summary failed: {summary.get('error')}")
                
        except Exception as e:
            print(f"❌ Position summary test failed: {e}")
    
    # Run test (requires rate controller to be initialized)
    print("⚠️ Note: Requires rate controller initialization for testing")
    # asyncio.run(test_position_data())
