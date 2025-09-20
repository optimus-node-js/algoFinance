"""
Angel One Unified Interface
===========================

Master interface for ALL Angel One operations.
Routes calls to appropriate managers with consistent error handling.

This is the SINGLE POINT OF ENTRY for all Angel One API operations.
All services should use this interface instead of calling methods directly.

Features:
- Unified API with consistent error handling
- Automatic authentication management
- Intelligent routing to appropriate managers
- Built-in rate limiting and caching
- Comprehensive logging and monitoring
- Backward compatibility with existing code

Usage:
    from angel_one_api.interface import AngelOneInterface
    
    # Initialize (singleton pattern)
    angel_one = AngelOneInterface()
    
    # Configure API keys
    await angel_one.configure({
        "key1": {"api_key": "...", "client_id": "...", ...}
    })
    
    # Use unified API
    ltp = await angel_one.get_ltp("RELIANCE", "2885")
    order_id = await angel_one.place_order(order_params)
    positions = await angel_one.get_positions()

Author: AI Trading System
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any, Union
from datetime import datetime, UTC

# Import our modules
from .authentication import AuthManager, SessionManager, TokenManager
from .market_data import LiveFeedManager, InstrumentManager
from .methods import (
    # Core trading methods
    place_order, modify_order, cancel_order,
    get_order_book, get_trade_book, order_details,
    
    # Portfolio methods  
    get_position, get_holding, get_all_holding,
    convert_position, get_profile, get_rms,
    
    # Market data methods
    get_ltp_data, search_scrip, get_candle_data, get_quote,
    
    # Advanced methods
    create_gtt_rule, batch_margin, option_greek,
    generate_tokens, logout
)

logger = logging.getLogger(__name__)

class AngelOneInterface:
    """
    Master interface for ALL Angel One operations.
    
    Provides a unified, high-level API that routes calls to appropriate
    managers and handles authentication, rate limiting, and error handling
    automatically.
    """
    
    def __init__(self):
        # Core managers
        self.auth_manager = AuthManager()
        self.session_manager = SessionManager()
        self.token_manager = TokenManager()
        self.live_feed_manager = LiveFeedManager()
        self.instrument_manager = InstrumentManager()
        
        # State
        self._initialized = False
        self._api_keys_configured = False
        
        # Statistics
        self._stats = {
            'total_api_calls': 0,
            'successful_calls': 0,
            'failed_calls': 0,
            'start_time': datetime.now(UTC),
            'last_call_time': None
        }
    
    async def configure(self, api_keys_config: Dict[str, Dict[str, str]]) -> bool:
        """
        Configure Angel One interface with API keys.
        
        Args:
            api_keys_config: Dict mapping key names to credential dicts
                Format: {
                    "key1": {
                        "api_key": "...",
                        "client_id": "...", 
                        "password": "...",
                        "totp_secret": "..."
                    }
                }
                
        Returns:
            bool: Success status
        """
        try:
            logger.info("🔧 Configuring Angel One interface...")
            
            # Configure authentication
            self.auth_manager.configure_api_keys(api_keys_config)
            
            # Login to all keys
            login_results = await self.auth_manager.login_all_keys()
            
            successful_logins = sum(login_results.values())
            total_keys = len(api_keys_config)
            
            if successful_logins > 0:
                self._api_keys_configured = True
                self._initialized = True
                
                logger.info(f"✅ Angel One interface configured: {successful_logins}/{total_keys} keys active")
                return True
            else:
                logger.error("❌ Angel One interface configuration failed: No successful logins")
                return False
                
        except Exception as e:
            logger.error(f"❌ Angel One interface configuration failed: {e}")
            return False
    
    def _ensure_initialized(self):
        """Ensure interface is properly initialized."""
        if not self._initialized:
            raise RuntimeError("Angel One interface not initialized. Call configure() first.")
    
    async def _make_api_call(self, operation_name: str, operation_func, *args, **kwargs):
        """
        Make an API call with unified error handling and statistics.
        
        Args:
            operation_name: Name of the operation for logging
            operation_func: Function to call
            *args, **kwargs: Arguments to pass to the function
            
        Returns:
            Any: Result from the operation
        """
        self._ensure_initialized()
        
        start_time = datetime.now(UTC)
        self._stats['total_api_calls'] += 1
        self._stats['last_call_time'] = start_time
        
        try:
            logger.debug(f"🔄 {operation_name} starting...")
            
            # Call the operation
            if asyncio.iscoroutinefunction(operation_func):
                result = await operation_func(*args, **kwargs)
            else:
                result = operation_func(*args, **kwargs)
            
            self._stats['successful_calls'] += 1
            
            elapsed = (datetime.now(UTC) - start_time).total_seconds()
            logger.debug(f"✅ {operation_name} completed in {elapsed:.3f}s")
            
            return result
            
        except Exception as e:
            self._stats['failed_calls'] += 1
            
            elapsed = (datetime.now(UTC) - start_time).total_seconds()
            logger.error(f"❌ {operation_name} failed after {elapsed:.3f}s: {e}")
            
            raise
    
    # =================================================================
    # MARKET DATA METHODS
    # =================================================================
    
    async def get_ltp(self, symbol: str, token: Optional[str] = None, exchange: str = "NSE") -> float:
        """
        Get Last Traded Price with intelligent caching.
        
        Args:
            symbol: Trading symbol
            token: Instrument token (auto-resolved if None)
            exchange: Exchange name
            
        Returns:
            float: Current LTP
        """
        async def _get_ltp():
            # Auto-resolve token if not provided
            if not token:
                resolved_token = await self.instrument_manager.get_instrument_token(symbol, exchange)
                if not resolved_token:
                    raise ValueError(f"Could not resolve token for {symbol}")
                actual_token = resolved_token
            else:
                actual_token = token
            
            # Use live feed manager for caching
            return await self.live_feed_manager.get_ltp(symbol, actual_token, exchange)
        
        return await self._make_api_call(f"get_ltp({symbol})", _get_ltp)
    
    async def get_bulk_ltp(self, symbols: List[str], exchange: str = "NSE") -> Dict[str, float]:
        """
        Get LTP for multiple symbols efficiently.
        
        Args:
            symbols: List of trading symbols
            exchange: Exchange name
            
        Returns:
            Dict mapping symbols to LTP values
        """
        async def _get_bulk_ltp():
            # Resolve tokens for all symbols
            tokens = await self.instrument_manager.get_bulk_instrument_tokens(symbols, exchange)
            
            # Prepare symbols_tokens list for live feed manager
            symbols_tokens = []
            for symbol in symbols:
                token = tokens.get(symbol)
                if token:
                    symbols_tokens.append({'symbol': symbol, 'token': token})
            
            # Get LTP data
            return await self.live_feed_manager.get_bulk_ltp(symbols_tokens, exchange)
        
        return await self._make_api_call(f"get_bulk_ltp({len(symbols)} symbols)", _get_bulk_ltp)
    
    async def search_instruments(self, query: str, exchange: str = "NSE") -> List[Dict[str, Any]]:
        """
        Search for instruments.
        
        Args:
            query: Search query
            exchange: Exchange name
            
        Returns:
            List of instrument dicts
        """
        async def _search():
            instruments = await self.instrument_manager.search_instruments(query, exchange)
            return [instrument.to_dict() for instrument in instruments]
        
        return await self._make_api_call(f"search_instruments({query})", _search)
    
    async def get_candle_data(
        self, 
        symbol: str, 
        interval: str, 
        from_date: str, 
        to_date: str,
        token: Optional[str] = None,
        exchange: str = "NSE"
    ) -> List[Dict[str, Any]]:
        """
        Get historical candlestick data.
        
        Args:
            symbol: Trading symbol
            interval: Time interval (ONE_MINUTE, FIVE_MINUTE, etc.)
            from_date: Start date (YYYY-MM-DD HH:MM)
            to_date: End date (YYYY-MM-DD HH:MM)
            token: Instrument token (auto-resolved if None)
            exchange: Exchange name
            
        Returns:
            List of candle data
        """
        async def _get_candles():
            # Auto-resolve token if not provided
            if not token:
                resolved_token = await self.instrument_manager.get_instrument_token(symbol, exchange)
                if not resolved_token:
                    raise ValueError(f"Could not resolve token for {symbol}")
                actual_token = resolved_token
            else:
                actual_token = token
            
            result = await get_candle_data(
                exchange=exchange,
                tradingsymbol=symbol, 
                symboltoken=actual_token,
                interval=interval,
                fromdate=from_date,
                todate=to_date
            )
            
            if result['success']:
                return result['candle_data']
            else:
                raise Exception(result.get('error', 'Unknown error'))
        
        return await self._make_api_call(f"get_candle_data({symbol})", _get_candles)
    
    # =================================================================
    # TRADING METHODS
    # =================================================================
    
    async def place_order(self, order_params: Dict[str, Any]) -> str:
        """
        Place a trading order.
        
        Args:
            order_params: Order parameters dict
            
        Returns:
            str: Order ID
        """
        async def _place_order():
            result = await place_order(order_params)
            
            if result['success']:
                return result['order_id']
            else:
                raise Exception(result.get('error', 'Order placement failed'))
        
        symbol = order_params.get('tradingsymbol', 'Unknown')
        return await self._make_api_call(f"place_order({symbol})", _place_order)
    
    async def modify_order(self, order_id: str, modifications: Dict[str, Any]) -> bool:
        """
        Modify an existing order.
        
        Args:
            order_id: Order ID to modify
            modifications: Parameters to modify
            
        Returns:
            bool: Success status
        """
        async def _modify_order():
            # Prepare modify params
            modify_params = {'orderid': order_id, **modifications}
            
            result = await modify_order(modify_params)
            return result['success']
        
        return await self._make_api_call(f"modify_order({order_id})", _modify_order)
    
    async def cancel_order(self, order_id: str) -> bool:
        """
        Cancel an order.
        
        Args:
            order_id: Order ID to cancel
            
        Returns:
            bool: Success status
        """
        async def _cancel_order():
            result = await cancel_order(order_id)
            return result['success']
        
        return await self._make_api_call(f"cancel_order({order_id})", _cancel_order)
    
    async def get_order_status(self, order_id: str) -> str:
        """
        Get order status.
        
        Args:
            order_id: Order ID
            
        Returns:
            str: Order status
        """
        async def _get_status():
            result = await order_details(order_id)
            
            if result['success']:
                return result['order_status']
            else:
                raise Exception(result.get('error', 'Failed to get order status'))
        
        return await self._make_api_call(f"get_order_status({order_id})", _get_status)
    
    # =================================================================
    # PORTFOLIO METHODS
    # =================================================================
    
    async def get_positions(self) -> List[Dict[str, Any]]:
        """Get all positions."""
        async def _get_positions():
            result = await get_position()
            
            if result['success']:
                return result['positions']
            else:
                raise Exception(result.get('error', 'Failed to get positions'))
        
        return await self._make_api_call("get_positions", _get_positions)
    
    async def get_holdings(self) -> List[Dict[str, Any]]:
        """Get all holdings."""
        async def _get_holdings():
            result = await get_holding()
            
            if result['success']:
                return result['holdings']
            else:
                raise Exception(result.get('error', 'Failed to get holdings'))
        
        return await self._make_api_call("get_holdings", _get_holdings)
    
    async def get_complete_holdings(self) -> Dict[str, Any]:
        """Get complete holdings with analysis."""
        async def _get_complete():
            result = await get_all_holding()
            
            if result['success']:
                return {
                    'all_holdings': result['all_holdings'],
                    'regular_holdings': result['regular_holdings'],
                    'pledged_holdings': result['pledged_holdings'],
                    'summary': result['comprehensive_summary']
                }
            else:
                raise Exception(result.get('error', 'Failed to get complete holdings'))
        
        return await self._make_api_call("get_complete_holdings", _get_complete)
    
    async def get_funds(self) -> Dict[str, Any]:
        """Get fund details and margin information."""
        async def _get_funds():
            result = await get_rms()
            
            if result['success']:
                return result['rms_data']
            else:
                raise Exception(result.get('error', 'Failed to get funds'))
        
        return await self._make_api_call("get_funds", _get_funds)
    
    # =================================================================
    # CONVENIENCE METHODS
    # =================================================================
    
    async def get_portfolio_summary(self) -> Dict[str, Any]:
        """Get complete portfolio summary."""
        async def _get_summary():
            # Get all portfolio data in parallel
            positions_task = self.get_positions()
            holdings_task = self.get_complete_holdings()
            funds_task = self.get_funds()
            
            positions, holdings, funds = await asyncio.gather(
                positions_task, holdings_task, funds_task,
                return_exceptions=True
            )
            
            # Handle any exceptions
            summary = {
                'timestamp': datetime.now(UTC).isoformat(),
                'positions': positions if not isinstance(positions, Exception) else [],
                'holdings': holdings if not isinstance(holdings, Exception) else {},
                'funds': funds if not isinstance(funds, Exception) else {},
                'errors': []
            }
            
            if isinstance(positions, Exception):
                summary['errors'].append(f"Positions: {positions}")
            if isinstance(holdings, Exception):
                summary['errors'].append(f"Holdings: {holdings}")
            if isinstance(funds, Exception):
                summary['errors'].append(f"Funds: {funds}")
            
            return summary
        
        return await self._make_api_call("get_portfolio_summary", _get_summary)
    
    async def quick_order(
        self, 
        symbol: str, 
        quantity: int, 
        side: str, 
        order_type: str = "MARKET",
        price: Optional[float] = None,
        exchange: str = "NSE"
    ) -> str:
        """
        Quick order placement with minimal parameters.
        
        Args:
            symbol: Trading symbol
            quantity: Quantity to trade
            side: BUY or SELL
            order_type: MARKET or LIMIT
            price: Price (required for LIMIT orders)
            exchange: Exchange name
            
        Returns:
            str: Order ID
        """
        async def _quick_order():
            # Auto-resolve token
            token = await self.instrument_manager.get_instrument_token(symbol, exchange)
            if not token:
                raise ValueError(f"Could not resolve token for {symbol}")
            
            # Build order parameters
            order_params = {
                'exchange': exchange,
                'tradingsymbol': symbol,
                'symboltoken': token,
                'transactiontype': side.upper(),
                'ordertype': order_type.upper(),
                'producttype': 'DELIVERY',
                'duration': 'DAY',
                'quantity': str(quantity)
            }
            
            if order_type.upper() == 'LIMIT':
                if price is None:
                    raise ValueError("Price required for LIMIT orders")
                order_params['price'] = str(price)
            else:
                order_params['price'] = '0'
            
            return await self.place_order(order_params)
        
        return await self._make_api_call(f"quick_order({symbol} {side} {quantity})", _quick_order)
    
    # =================================================================
    # MANAGEMENT METHODS
    # =================================================================
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get interface usage statistics."""
        uptime = datetime.now(UTC) - self._stats['start_time']
        success_rate = (
            (self._stats['successful_calls'] / self._stats['total_api_calls']) * 100
            if self._stats['total_api_calls'] > 0 else 0
        )
        
        return {
            'interface_stats': {
                'initialized': self._initialized,
                'api_keys_configured': self._api_keys_configured,
                'uptime_hours': uptime.total_seconds() / 3600,
                'total_api_calls': self._stats['total_api_calls'],
                'successful_calls': self._stats['successful_calls'],
                'failed_calls': self._stats['failed_calls'],
                'success_rate': success_rate,
                'last_call_time': self._stats['last_call_time']
            },
            'auth_stats': self.auth_manager.get_stats(),
            'cache_stats': self.live_feed_manager.get_cache_stats(),
            'instrument_stats': self.instrument_manager.get_cache_stats()
        }
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform comprehensive health check."""
        try:
            health = {
                'overall_status': 'HEALTHY',
                'timestamp': datetime.now(UTC).isoformat(),
                'components': {}
            }
            
            # Check authentication
            auth_sessions = await self.auth_manager.validate_all_sessions()
            valid_sessions = sum(auth_sessions.values())
            
            health['components']['authentication'] = {
                'status': 'HEALTHY' if valid_sessions > 0 else 'UNHEALTHY',
                'valid_sessions': valid_sessions,
                'total_sessions': len(auth_sessions)
            }
            
            # Check market data
            try:
                # Try to get LTP for a common stock
                test_ltp = await self.get_ltp("RELIANCE")
                health['components']['market_data'] = {
                    'status': 'HEALTHY' if test_ltp > 0 else 'DEGRADED',
                    'test_ltp': test_ltp
                }
            except Exception as e:
                health['components']['market_data'] = {
                    'status': 'UNHEALTHY',
                    'error': str(e)
                }
            
            # Overall status
            unhealthy_components = sum(
                1 for comp in health['components'].values()
                if comp['status'] == 'UNHEALTHY'
            )
            
            if unhealthy_components > 0:
                health['overall_status'] = 'UNHEALTHY'
            elif any(comp['status'] == 'DEGRADED' for comp in health['components'].values()):
                health['overall_status'] = 'DEGRADED'
            
            return health
            
        except Exception as e:
            return {
                'overall_status': 'UNHEALTHY',
                'error': str(e),
                'timestamp': datetime.now(UTC).isoformat()
            }

# Singleton instance for global use
_angel_one_interface = None

def get_angel_one_interface() -> AngelOneInterface:
    """Get the global AngelOneInterface instance."""
    global _angel_one_interface
    if _angel_one_interface is None:
        _angel_one_interface = AngelOneInterface()
    return _angel_one_interface
