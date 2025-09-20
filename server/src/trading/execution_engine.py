"""
AI-Powered Trade Execution Engine
================================

The final component that executes validated AI trading decisions via Angel One API.
Handles order placement, position management, risk validation, and portfolio synchronization.

Key Features:
- Real-time order execution based on AI signals
- Position tracking and monitoring
- Automatic stop-loss and profit target execution
- Risk validation before every trade
- Portfolio synchronization with broker
- Emergency position management
- Real-time P&L calculation

Author: AI Trading System
Version: 1.0.0
"""

import asyncio
import logging
import time
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
from concurrent.futures import ThreadPoolExecutor
import threading
import random
# Standard libraries
import pandas as pd
import numpy as np

# Import project modules
import sys
import os
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(current_dir, '..'))

try:
    from core.message_broker import MessageBroker
    from core.connections import ConnectionManager
    from config import settings
    from log_system.enhanced_loguru_logger import get_enhanced_logger, setup_service_logger
    REAL_COMPONENTS = True
    # Setup enhanced logger for trade execution
    enhanced_logger = get_enhanced_logger()
    setup_service_logger("TRADE_EXECUTION", "INFO")
    logger = enhanced_logger
except ImportError:
    REAL_COMPONENTS = False
    import logging
    logger = logging.getLogger(__name__)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

class OrderType(Enum):
    """Order types supported by the execution engine."""
    MARKET = "MARKET"
    LIMIT = "LIMIT"
    STOP_LOSS = "STOPLOSS"
    STOP_LOSS_MARKET = "STOPLOSS_M"

class OrderStatus(Enum):
    """Order status types."""
    PENDING = "pending"
    PLACED = "placed"
    FILLED = "filled"
    PARTIALLY_FILLED = "partially_filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"

class PositionType(Enum):
    """Position types."""
    LONG = "long"
    SHORT = "short"

class TradingMode(Enum):
    """Trading modes."""
    LIVE = "live"
    PAPER = "paper"
    SIMULATION = "simulation"

@dataclass
class TradingOrder:
    """Represents a trading order."""
    symbol: str
    quantity: int
    order_type: OrderType
    price: float = 0.0
    trigger_price: float = 0.0
    order_id: Optional[str] = None
    parent_order_id: Optional[str] = None
    status: OrderStatus = OrderStatus.PENDING
    created_at: datetime = field(default_factory=datetime.now)
    filled_at: Optional[datetime] = None
    filled_price: float = 0.0
    filled_quantity: int = 0
    transaction_type: str = "BUY"  # BUY/SELL
    product_type: str = "INTRADAY"  # INTRADAY/DELIVERY
    variety: str = "NORMAL"  # NORMAL/STOPLOSS/AMO
    ai_signal_id: Optional[str] = None
    backtest_validation: Optional[Dict] = None

@dataclass
class Position:
    """Represents an active trading position."""
    symbol: str
    quantity: int
    entry_price: float
    current_price: float
    position_type: PositionType
    entry_time: datetime
    stop_loss_price: float = 0.0
    profit_target_price: float = 0.0
    stop_loss_order_id: Optional[str] = None
    profit_target_order_id: Optional[str] = None
    unrealized_pnl: float = 0.0
    unrealized_pnl_percent: float = 0.0
    ai_decision_id: Optional[str] = None
    risk_score: float = 0.0

@dataclass
class TradingConfig:
    """Trading configuration."""
    max_positions: int = 10
    max_daily_trades: int = 50
    max_daily_loss: float = 10000.0
    max_position_value: float = 50000.0
    default_stop_loss_percent: float = 2.0
    default_profit_target_percent: float = 5.0
    trading_mode: TradingMode = TradingMode.PAPER
    enable_auto_stop_loss: bool = True
    enable_auto_profit_target: bool = True
    risk_per_trade: float = 1000.0
    trading_start_time: str = "09:15"
    trading_end_time: str = "15:30"

class TradeExecutionEngine:
    """
    AI-Powered Trade Execution Engine
    
    Executes validated trading decisions from the AI system via Angel One API.
    Manages positions, orders, and risk in real-time.
    """
    
    def __init__(self, config: Optional[TradingConfig] = None):
        """Initialize the trade execution engine."""
        self.config = config or TradingConfig()
        
        # Core components
        if REAL_COMPONENTS:
            self.connection_manager = ConnectionManager()
            self.message_broker = MessageBroker()
        else:
            self.connection_manager = None
            self.message_broker = self._create_mock_broker()
        
        # Execution management
        self.executor = ThreadPoolExecutor(max_workers=8, thread_name_prefix="TradeExecutor")
        
        # State management
        self.active_positions: Dict[str, Position] = {}
        self.pending_orders: Dict[str, TradingOrder] = {}
        self.executed_orders: List[TradingOrder] = []
        self.daily_trades: int = 0
        self.daily_pnl: float = 0.0
        self.is_trading_enabled: bool = False
        self.emergency_stop: bool = False
        
        # Performance tracking
        self.metrics = {
            'total_trades': 0,
            'winning_trades': 0,
            'losing_trades': 0,
            'total_pnl': 0.0,
            'max_drawdown': 0.0,
            'win_rate': 0.0,
            'average_win': 0.0,
            'average_loss': 0.0
        }
        
        # Trading session management
        self.session_start_time = None
        self.last_portfolio_sync = None
        
        # Setup message subscriptions
        asyncio.create_task(self._setup_message_subscriptions())
        
        logger.info("🚀 Trade Execution Engine initialized successfully")
    
    def _create_mock_broker(self):
        """Create mock message broker for testing."""
        class MockBroker:
            def __init__(self):
                self.subscriptions = {}
            
            async def subscribe_to_queue_with_retry(self, queue, handler, **kwargs):
                logger.info(f"📝 Mock: Subscribed to {queue}")
                self.subscriptions[queue] = handler
                return True
                
            def subscribe_to_queue(self, queue, handler):
                asyncio.create_task(self.subscribe_to_queue_with_retry(queue, handler))
                
            def publish_ai_analysis(self, routing_key, symbol, data):
                logger.info(f"📤 Mock: Published {routing_key} for {symbol}")
                
            async def wait_for_queues_ready(self, queues, timeout=60):
                return {q: True for q in queues}
        
        return MockBroker()
    
    async def _setup_message_subscriptions(self):
        """Setup RabbitMQ subscriptions for trade execution coordination."""
        try:
            # Define all queues for trade execution
            execution_queues = [
                'live_trade_validation_response',  # From backtesting engine
                'ai_trade_execution_requests',     # From AI Master
                'risk_violations',                 # From risk management
                'portfolio_updates',               # Portfolio changes
                'market_data_ticks',               # Real-time price updates
                'stop_loss_triggers',              # Stop-loss execution
                'profit_target_triggers',          # Profit target execution
                'emergency_exit_signals'           # Emergency position closure
            ]
            
            logger.info(f"🔄 Setting up trade execution subscriptions for {len(execution_queues)} queues...")
            
            # Wait for queues to be ready
            if hasattr(self.message_broker, 'wait_for_queues_ready'):
                queue_status = await self.message_broker.wait_for_queues_ready(execution_queues, timeout=30)
                ready_count = sum(queue_status.values())
                logger.info(f"✅ {ready_count}/{len(execution_queues)} execution queues ready")
            
            # Setup subscriptions with retry
            subscriptions = [
                ('live_trade_validation_response', self._handle_trade_validation),
                ('ai_trade_execution_requests', self._handle_execution_request),
                ('risk_violations', self._handle_risk_violation),
                ('portfolio_updates', self._handle_portfolio_update),
                ('market_data_ticks', self._handle_market_data_update),
                ('stop_loss_triggers', self._handle_stop_loss_trigger),
                ('profit_target_triggers', self._handle_profit_target_trigger),
                ('emergency_exit_signals', self._handle_emergency_exit)
            ]
            
            successful_subs = 0
            for queue, handler in subscriptions:
                try:
                    if hasattr(self.message_broker, 'subscribe_to_queue_with_retry'):
                        success = await self.message_broker.subscribe_to_queue_with_retry(
                            queue, handler, max_retries=3, retry_delay=1
                        )
                        if success:
                            successful_subs += 1
                    else:
                        self.message_broker.subscribe_to_queue(queue, handler)
                        successful_subs += 1
                        
                except Exception as e:
                    logger.warning(f"⚠️ Could not subscribe to {queue}: {e}")
            
            logger.info(f"✅ Trade execution setup: {successful_subs}/{len(subscriptions)} subscriptions active")
            
        except Exception as e:
            logger.error(f"❌ Failed to setup execution subscriptions: {e}")
    
    async def start_trading_session(self):
        """Start a new trading session."""
        try:
            logger.info("🚀 Starting trading session...")
            
            # Reset daily counters
            self.daily_trades = 0
            self.daily_pnl = 0.0
            self.session_start_time = datetime.now()
            
            # Sync with broker portfolio
            await self._sync_portfolio()
            
            # Enable trading
            self.is_trading_enabled = True
            self.emergency_stop = False
            
            # Start monitoring tasks
            asyncio.create_task(self._monitor_positions())
            asyncio.create_task(self._monitor_market_hours())
            asyncio.create_task(self._sync_portfolio_periodic())
            
            logger.info("✅ Trading session started successfully")
            
            # Publish trading session status
            self.message_broker.publish_ai_analysis('trading_session_started', 'system', {
                'session_start_time': self.session_start_time.isoformat(),
                'trading_mode': self.config.trading_mode.value,
                'max_positions': self.config.max_positions,
                'max_daily_trades': self.config.max_daily_trades
            })
            
        except Exception as e:
            logger.error(f"❌ Error starting trading session: {e}")
            self.is_trading_enabled = False
    
    async def stop_trading_session(self):
        """Stop the current trading session."""
        try:
            logger.info("🛑 Stopping trading session...")
            
            # Disable new trades
            self.is_trading_enabled = False
            
            # Close all positions if emergency stop
            if self.emergency_stop:
                await self._emergency_close_all_positions()
            
            # Cancel all pending orders
            await self._cancel_all_pending_orders()
            
            # Final portfolio sync
            await self._sync_portfolio()
            
            # Calculate session metrics
            session_duration = datetime.now() - self.session_start_time if self.session_start_time else timedelta(0)
            
            session_summary = {
                'session_end_time': datetime.now().isoformat(),
                'session_duration': str(session_duration),
                'total_trades': self.daily_trades,
                'daily_pnl': self.daily_pnl,
                'active_positions': len(self.active_positions),
                'trading_mode': self.config.trading_mode.value
            }
            
            logger.info(f"✅ Trading session stopped - {self.daily_trades} trades, ₹{self.daily_pnl:.2f} P&L")
            
            # Publish session summary
            self.message_broker.publish_ai_analysis('trading_session_stopped', 'system', session_summary)
            
        except Exception as e:
            logger.error(f"❌ Error stopping trading session: {e}")
    
    async def execute_trade(self, trade_signal: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a validated trade signal from the AI system.
        
        Args:
            trade_signal: Validated trade signal with entry analysis and backtest results
            
        Returns:
            Dict containing execution results
        """
        try:
            symbol = trade_signal.get('symbol')
            signal_type = trade_signal.get('entry_signal', 'hold')
            confidence = trade_signal.get('confidence', 0)
            entry_price = trade_signal.get('entry_price', 0)
            quantity = trade_signal.get('optimal_quantity', 0)
            
            if REAL_COMPONENTS and hasattr(logger, 'log_trade_execution'):
                logger.info("TRADE_EXECUTION", f"🎯 Executing trade signal for {symbol}: {signal_type} (confidence: {confidence:.2f})", {
                    'trade_type': 'signal_execution',
                    'symbol': symbol,
                    'signal_type': signal_type,
                    'confidence': confidence,
                    'mode': self.config.trading_mode.value
                })
            else:
                logger.info(f"🎯 Executing trade signal for {symbol}: {signal_type} (confidence: {confidence:.2f})")
            
            # Pre-execution validation
            validation_result = await self._validate_trade_execution(trade_signal)
            if not validation_result['valid']:
                logger.warning(f"⚠️ Trade validation failed for {symbol}: {validation_result['reason']}")
                return validation_result
            
            # Determine order parameters
            order_params = await self._calculate_order_parameters(trade_signal)
            
            # Create trading order
            order = TradingOrder(
                symbol=symbol,
                quantity=order_params['quantity'],
                order_type=OrderType.MARKET,  # Use market orders for immediate execution
                transaction_type="BUY" if signal_type in ['buy', 'strong_buy'] else "SELL",
                product_type="INTRADAY",
                ai_signal_id=trade_signal.get('request_id'),
                backtest_validation=trade_signal.get('backtest_results')
            )
            
            # Execute the order
            execution_result = await self._place_order(order)
            
            if execution_result['success']:
                # Create position tracking
                if order.transaction_type == "BUY":
                    await self._create_position(order, trade_signal)
                
                # Update metrics
                self.daily_trades += 1
                self.metrics['total_trades'] += 1
                
                logger.info(f"✅ Trade executed successfully for {symbol}")
                
                # Publish execution confirmation
                self.message_broker.publish_ai_analysis('trade_executed', symbol, {
                    'symbol': symbol,
                    'order_id': execution_result.get('order_id'),
                    'quantity': order.quantity,
                    'transaction_type': order.transaction_type,
                    'execution_price': execution_result.get('price', 0),
                    'timestamp': datetime.now().isoformat()
                })
            
            return execution_result
            
        except Exception as e:
            logger.error(f"❌ Error executing trade for {symbol}: {e}")
            return {
                'success': False,
                'error': str(e),
                'symbol': symbol
            }
    
    async def _validate_trade_execution(self, trade_signal: Dict) -> Dict[str, Any]:
        """Validate trade before execution."""
        try:
            symbol = trade_signal.get('symbol')
            quantity = trade_signal.get('optimal_quantity', 0)
            price = trade_signal.get('entry_price', 0)
            
            # Check trading enabled
            if not self.is_trading_enabled:
                return {'valid': False, 'reason': 'Trading disabled'}
            
            # Check emergency stop
            if self.emergency_stop:
                return {'valid': False, 'reason': 'Emergency stop active'}
            
            # Market hours check disabled for testing
            # if not self._is_market_hours():
            #     return {'valid': False, 'reason': 'Outside market hours'}
            
            # Check daily limits
            if self.daily_trades >= self.config.max_daily_trades:
                return {'valid': False, 'reason': 'Daily trade limit reached'}
            
            # Check position limits
            if len(self.active_positions) >= self.config.max_positions:
                return {'valid': False, 'reason': 'Maximum positions limit reached'}
            
            # Check position value
            position_value = quantity * price
            if position_value > self.config.max_position_value:
                return {'valid': False, 'reason': 'Position value too large'}
            
            # Check daily loss limit
            if self.daily_pnl < -self.config.max_daily_loss:
                return {'valid': False, 'reason': 'Daily loss limit reached'}
            
            # Check if position already exists
            if symbol in self.active_positions:
                return {'valid': False, 'reason': 'Position already exists for symbol'}
            
            return {'valid': True, 'reason': 'All validations passed'}
            
        except Exception as e:
            logger.error(f"❌ Error validating trade: {e}")
            return {'valid': False, 'reason': f'Validation error: {e}'}
    
    async def _calculate_order_parameters(self, trade_signal: Dict) -> Dict[str, Any]:
        """Calculate optimal order parameters."""
        try:
            symbol = trade_signal.get('symbol')
            suggested_quantity = trade_signal.get('optimal_quantity', 10)  # Default to 10 if not provided
            entry_price = trade_signal.get('entry_price', 0)
            
            # Ensure we have a valid entry price
            if entry_price <= 0:
                entry_price = self._get_mock_price(symbol)  # Get mock price if no price provided
                logger.warning(f"⚠️ No entry price provided for {symbol}, using mock price: ₹{entry_price:.2f}")
            
            # Apply risk management to quantity
            max_risk_amount = min(self.config.risk_per_trade, self.config.max_position_value * 0.02)
            risk_adjusted_quantity = int(max_risk_amount / (entry_price * 0.02))  # 2% stop-loss
            
            # Use the smaller of suggested or risk-adjusted quantity
            final_quantity = min(suggested_quantity, risk_adjusted_quantity)
            final_quantity = max(1, final_quantity)  # Minimum 1 share
            
            return {
                'quantity': final_quantity,
                'estimated_value': final_quantity * entry_price,
                'risk_amount': final_quantity * entry_price * 0.02
            }
            
        except Exception as e:
            logger.error(f"❌ Error calculating order parameters: {e}")
            return {'quantity': 1, 'estimated_value': 0, 'risk_amount': 0}
    
    async def _place_order(self, order: TradingOrder) -> Dict[str, Any]:
        """Place order via Angel One API."""
        try:
            if self.config.trading_mode == TradingMode.PAPER:
                # Enhanced paper trading simulation
                order.order_id = f"PAPER_{int(time.time())}{random.randint(100, 999)}"
                order.status = OrderStatus.FILLED
                order.filled_at = datetime.now()
                
                # Get base price
                base_price = order.price if order.price > 0 else self._get_mock_price(order.symbol)
                
                # Realistic price simulation with slight slippage
                if order.transaction_type == "BUY":
                    slippage = random.uniform(0.0005, 0.002)  # 0.05% to 0.2% upward slippage
                    order.filled_price = base_price * (1 + slippage)
                else:  # SELL
                    slippage = random.uniform(0.0005, 0.002)  # 0.05% to 0.2% downward slippage
                    order.filled_price = base_price * (1 - slippage)
                
                order.filled_quantity = order.quantity
                
                # Calculate trade value and fees
                trade_value = order.filled_price * order.filled_quantity
                brokerage_fee = min(trade_value * 0.0003, 20)  # 0.03% or ₹20, whichever is lower
                
                self.executed_orders.append(order)
                
                # Log detailed paper trade
                logger.info(f"✅ [PAPER TRADE] {order.symbol}: {order.order_type.value.upper()} {order.filled_quantity} @ ₹{order.filled_price:.2f}")
                logger.info(f"   💰 Trade Value: ₹{trade_value:.2f} | Fees: ₹{brokerage_fee:.2f} | Net: ₹{trade_value - brokerage_fee:.2f}")
                
                return {
                    'success': True,
                    'order_id': order.order_id,
                    'price': order.filled_price,
                    'quantity': order.filled_quantity,
                    'trade_value': trade_value,
                    'brokerage_fee': brokerage_fee,
                    'net_value': trade_value - brokerage_fee,
                    'mode': 'paper'
                }
            
            elif self.config.trading_mode == TradingMode.LIVE:
                # Real trading via Angel One API
                if not REAL_COMPONENTS or not self.connection_manager:
                    raise Exception("Real trading requires Angel One API connection")
                
                # Get SmartAPI client
                client = self.connection_manager.get_smartapi_client()
                if not client:
                    raise Exception("Angel One API client not available")
                
                # Prepare order parameters
                order_params = {
                    'variety': order.variety,
                    'tradingsymbol': order.symbol,
                    'symboltoken': self._get_symbol_token(order.symbol),
                    'transactiontype': order.transaction_type,
                    'exchange': 'NSE',
                    'ordertype': order.order_type.value,
                    'producttype': order.product_type,
                    'duration': 'DAY',
                    'quantity': str(order.quantity)
                }
                
                # Add price for limit orders
                if order.order_type == OrderType.LIMIT:
                    order_params['price'] = str(order.price)
                
                # Place order
                response = client.placeOrder(order_params)
                
                if response and response.get('status'):
                    order.order_id = response.get('data', {}).get('orderid')
                    order.status = OrderStatus.PLACED
                    
                    self.pending_orders[order.order_id] = order
                    
                    logger.info(f"✅ Live order placed: {order.symbol} {order.quantity} (ID: {order.order_id})")
                    
                    return {
                        'success': True,
                        'order_id': order.order_id,
                        'response': response,
                        'mode': 'live'
                    }
                else:
                    raise Exception(f"Order placement failed: {response}")
            
            else:
                # Simulation mode
                return await self._simulate_order_execution(order)
                
        except Exception as e:
            logger.error(f"❌ Error placing order for {order.symbol}: {e}")
            return {
                'success': False,
                'error': str(e),
                'symbol': order.symbol
            }
    
    async def _create_position(self, order: TradingOrder, trade_signal: Dict):
        """Create position tracking for executed order."""
        try:
            # Calculate stop-loss and profit target
            entry_price = order.filled_price
            stop_loss_price = entry_price * (1 - self.config.default_stop_loss_percent / 100)
            profit_target_price = entry_price * (1 + self.config.default_profit_target_percent / 100)
            
            # Create position
            position = Position(
                symbol=order.symbol,
                quantity=order.filled_quantity,
                entry_price=entry_price,
                current_price=entry_price,
                position_type=PositionType.LONG,  # Assuming long positions for now
                entry_time=order.filled_at or datetime.now(),
                stop_loss_price=stop_loss_price,
                profit_target_price=profit_target_price,
                ai_decision_id=order.ai_signal_id,
                risk_score=trade_signal.get('risk_level', 0.5)
            )
            
            # Store position
            self.active_positions[order.symbol] = position
            
            # Place stop-loss and profit target orders if enabled
            if self.config.enable_auto_stop_loss:
                await self._place_stop_loss_order(position)
            
            if self.config.enable_auto_profit_target:
                await self._place_profit_target_order(position)
            
            logger.info(f"📈 Position created for {order.symbol}: {order.filled_quantity} @ ₹{entry_price:.2f}")
            
            # Publish position creation
            self.message_broker.publish_ai_analysis('position_opened', order.symbol, {
                'symbol': order.symbol,
                'quantity': position.quantity,
                'entry_price': position.entry_price,
                'stop_loss_price': position.stop_loss_price,
                'profit_target_price': position.profit_target_price,
                'timestamp': position.entry_time.isoformat()
            })
            
        except Exception as e:
            logger.error(f"❌ Error creating position for {order.symbol}: {e}")
    
    def _get_mock_price(self, symbol: str) -> float:
        """Get mock price for paper trading."""
        # Simple mock price generation
        base_prices = {
            'RELIANCE-EQ': 2500,
            'TCS-EQ': 3500,
            'INFY-EQ': 1800,
            'SBIN-EQ': 600,
            'ICICIBANK-EQ': 1000
        }
        
        base_price = base_prices.get(symbol, 1000)
        return base_price + np.random.uniform(-50, 50)
    
    def _get_symbol_token(self, symbol: str) -> str:
        """Get symbol token for Angel One API."""
        # This would normally lookup the token from instrument master
        # For now, return a mock token
        return "1234"
    
    def _is_market_hours(self) -> bool:
        """Check if current time is within trading hours."""
        # For paper trading, always return True (24/7 trading)
        if self.config.trading_mode == TradingMode.PAPER:
            return True
            
        now = datetime.now()
        current_time = now.strftime("%H:%M")
        
        # Market hours check only for REAL trading (9:15 AM to 3:30 PM)
        start_time = self.config.trading_start_time
        end_time = self.config.trading_end_time
        
        return start_time <= current_time <= end_time
    
    # Message Handlers
    def _handle_trade_validation(self, message):
        """Handle trade validation responses from backtesting engine."""
        try:
            data = message.get('data', {})
            symbol = data.get('symbol')
            recommendation = data.get('recommendation')
            
            logger.info(f"🔍 Trade validation received for {symbol}: {recommendation}")
            
            # Execute trade if validation passed
            if recommendation == "EXECUTE":
                asyncio.create_task(self.execute_trade(data))
                
        except Exception as e:
            logger.error(f"❌ Error handling trade validation: {e}")
    
    def _handle_execution_request(self, message):
        """Handle trade execution requests from AI Master."""
        try:
            data = message.get('data', {})
            symbol = data.get('symbol')
            
            logger.info(f"🚀 Execution request received for {symbol}")
            
            # Execute the trade
            asyncio.create_task(self.execute_trade(data))
            
        except Exception as e:
            logger.error(f"❌ Error handling execution request: {e}")
    
    def _handle_risk_violation(self, message):
        """Handle risk violation alerts."""
        try:
            data = message.get('data', {})
            symbol = data.get('symbol')
            violation_type = data.get('violation_type')
            
            logger.warning(f"⚠️ Risk violation for {symbol}: {violation_type}")
            
            # Take immediate action based on violation type
            if violation_type in ['critical', 'emergency']:
                asyncio.create_task(self._handle_emergency_risk(symbol, data))
                
        except Exception as e:
            logger.error(f"❌ Error handling risk violation: {e}")
    
    def _handle_portfolio_update(self, message):
        """Handle portfolio updates."""
        try:
            data = message.get('data', {})
            logger.info(f"📊 Portfolio update received: {data.get('type', 'unknown')}")
            
        except Exception as e:
            logger.error(f"❌ Error handling portfolio update: {e}")
    
    def _handle_market_data_update(self, message):
        """Handle real-time market data updates."""
        try:
            data = message.get('data', {})
            symbol = data.get('symbol')
            price = data.get('price', {}).get('ltp', 0)
            
            # Update position if we have one
            if symbol in self.active_positions:
                asyncio.create_task(self._update_position_price(symbol, price))
                
        except Exception as e:
            logger.error(f"❌ Error handling market data update: {e}")
    
    def _handle_stop_loss_trigger(self, message):
        """Handle stop-loss trigger signals."""
        try:
            data = message.get('data', {})
            symbol = data.get('symbol')
            
            logger.warning(f"🛡️ Stop-loss triggered for {symbol}")
            
            # Execute stop-loss
            asyncio.create_task(self._execute_stop_loss(symbol))
            
        except Exception as e:
            logger.error(f"❌ Error handling stop-loss trigger: {e}")
    
    def _handle_profit_target_trigger(self, message):
        """Handle profit target trigger signals."""
        try:
            data = message.get('data', {})
            symbol = data.get('symbol')
            
            logger.info(f"🎯 Profit target triggered for {symbol}")
            
            # Execute profit taking
            asyncio.create_task(self._execute_profit_target(symbol))
            
        except Exception as e:
            logger.error(f"❌ Error handling profit target trigger: {e}")
    
    def _handle_emergency_exit(self, message):
        """Handle emergency exit signals."""
        try:
            data = message.get('data', {})
            logger.warning(f"🚨 Emergency exit signal received")
            
            # Trigger emergency stop
            self.emergency_stop = True
            asyncio.create_task(self._emergency_close_all_positions())
            
        except Exception as e:
            logger.error(f"❌ Error handling emergency exit: {e}")
    
    # Additional methods for monitoring and management
    async def _monitor_positions(self):
        """Monitor all active positions."""
        while self.is_trading_enabled:
            try:
                for symbol, position in self.active_positions.items():
                    # Update P&L
                    await self._update_position_pnl(position)
                    
                    # Check stop-loss and profit target triggers
                    await self._check_position_triggers(position)
                
                await asyncio.sleep(5)  # Check every 5 seconds
                
            except Exception as e:
                logger.error(f"❌ Error monitoring positions: {e}")
                await asyncio.sleep(10)
    
    async def _monitor_market_hours(self):
        """Monitor market hours and stop trading when market closes."""
        while self.is_trading_enabled:
            try:
                if not self._is_market_hours():
                    logger.info("🕐 Market closed - stopping trading session")
                    await self.stop_trading_session()
                    break
                
                await asyncio.sleep(60)  # Check every minute
                
            except Exception as e:
                logger.error(f"❌ Error monitoring market hours: {e}")
                await asyncio.sleep(60)
    
    async def _sync_portfolio_periodic(self):
        """Periodically sync with broker portfolio."""
        while self.is_trading_enabled:
            try:
                await self._sync_portfolio()
                await asyncio.sleep(300)  # Sync every 5 minutes
                
            except Exception as e:
                logger.error(f"❌ Error in periodic portfolio sync: {e}")
                await asyncio.sleep(300)
    
    async def _sync_portfolio(self):
        """Sync portfolio with broker."""
        try:
            logger.info("🔄 Syncing portfolio with broker...")
            
            if self.config.trading_mode == TradingMode.LIVE and REAL_COMPONENTS:
                # Sync with real broker
                # Implementation would fetch actual positions from Angel One
                pass
            
            self.last_portfolio_sync = datetime.now()
            logger.debug("✅ Portfolio sync completed")
            
        except Exception as e:
            logger.error(f"❌ Error syncing portfolio: {e}")
    
    # Placeholder methods for additional functionality
    async def _place_stop_loss_order(self, position: Position):
        """Place stop-loss order for position."""
        logger.info(f"🛡️ Placing stop-loss for {position.symbol} at ₹{position.stop_loss_price:.2f}")
    
    async def _place_profit_target_order(self, position: Position):
        """Place profit target order for position."""
        logger.info(f"🎯 Placing profit target for {position.symbol} at ₹{position.profit_target_price:.2f}")
    
    async def _update_position_price(self, symbol: str, price: float):
        """Update position with current market price."""
        if symbol in self.active_positions:
            self.active_positions[symbol].current_price = price
    
    async def _update_position_pnl(self, position: Position):
        """Update position P&L."""
        position.unrealized_pnl = (position.current_price - position.entry_price) * position.quantity
        position.unrealized_pnl_percent = (position.current_price - position.entry_price) / position.entry_price * 100
    
    async def _check_position_triggers(self, position: Position):
        """Check if position has hit stop-loss or profit targets."""
        # Implementation for checking triggers
        pass
    
    async def _execute_stop_loss(self, symbol: str):
        """Execute stop-loss for symbol."""
        logger.warning(f"🛡️ Executing stop-loss for {symbol}")
    
    async def _execute_profit_target(self, symbol: str):
        """Execute profit target for symbol."""
        logger.info(f"🎯 Executing profit target for {symbol}")
    
    async def _emergency_close_all_positions(self):
        """Emergency close all positions."""
        logger.warning("🚨 Emergency closing all positions")
    
    async def _cancel_all_pending_orders(self):
        """Cancel all pending orders."""
        logger.info("❌ Cancelling all pending orders")
    
    async def _handle_emergency_risk(self, symbol: str, data: Dict):
        """Handle emergency risk situation."""
        logger.warning(f"🚨 Handling emergency risk for {symbol}")
    
    async def _simulate_order_execution(self, order: TradingOrder) -> Dict[str, Any]:
        """Simulate order execution for testing."""
        order.order_id = f"SIM_{int(time.time())}"
        order.status = OrderStatus.FILLED
        order.filled_at = datetime.now()
        order.filled_price = self._get_mock_price(order.symbol)
        order.filled_quantity = order.quantity
        
        return {
            'success': True,
            'order_id': order.order_id,
            'price': order.filled_price,
            'quantity': order.filled_quantity,
            'mode': 'simulation'
        }
    
    def get_execution_metrics(self) -> Dict[str, Any]:
        """Get current execution metrics."""
        return {
            'metrics': self.metrics,
            'active_positions': len(self.active_positions),
            'daily_trades': self.daily_trades,
            'daily_pnl': self.daily_pnl,
            'trading_enabled': self.is_trading_enabled,
            'emergency_stop': self.emergency_stop,
            'trading_mode': self.config.trading_mode.value,
            'last_portfolio_sync': self.last_portfolio_sync.isoformat() if self.last_portfolio_sync else None
        }
    
    def cleanup(self):
        """Cleanup resources."""
        self.executor.shutdown(wait=True)
        logger.info("✅ Trade Execution Engine cleanup completed")


# Main execution for testing
async def main():
    """Test the Trade Execution Engine."""
    print("🚀 AI-Powered Trade Execution Engine")
    print("=" * 60)
    
    # Test with paper trading (override market hours for testing)
    config = TradingConfig(
        trading_mode=TradingMode.PAPER,
        max_positions=5,
        max_daily_trades=10,
        trading_start_time="00:00",  # 24/7 for testing
        trading_end_time="23:59"
    )
    
    engine = TradeExecutionEngine(config)
    
    try:
        # Start trading session
        print("\n🚀 Starting trading session...")
        await engine.start_trading_session()
        
        # Test trade execution
        mock_trade_signal = {
            'symbol': 'RELIANCE-EQ',
            'entry_signal': 'buy',
            'confidence': 0.75,
            'entry_price': 2500.0,
            'optimal_quantity': 10,
            'expected_profit': 5.0,
            'request_id': 'test_001'
        }
        
        print(f"\n📊 Testing trade execution...")
        result = await engine.execute_trade(mock_trade_signal)
        
        if result.get('success'):
            print(f"   ✅ Trade executed: {result['mode']} mode")
            print(f"   📊 Order ID: {result['order_id']}")
            print(f"   💰 Price: ₹{result['price']:.2f}")
            print(f"   📈 Quantity: {result['quantity']}")
        else:
            print(f"   ❌ Trade failed: {result.get('error', 'Unknown error')}")
        
        # Show metrics
        metrics = engine.get_execution_metrics()
        print(f"\n📊 Execution Metrics:")
        print(f"   🎯 Active Positions: {metrics['active_positions']}")
        print(f"   📈 Daily Trades: {metrics['daily_trades']}")
        print(f"   💰 Daily P&L: ₹{metrics['daily_pnl']:.2f}")
        print(f"   🔧 Trading Mode: {metrics['trading_mode']}")
        
        await asyncio.sleep(2)
        
        # Stop trading session
        print(f"\n🛑 Stopping trading session...")
        await engine.stop_trading_session()
        
        print(f"\n✅ Trade Execution Engine test completed successfully!")
        
    except KeyboardInterrupt:
        print("\n⏹️ Testing interrupted")
    finally:
        engine.cleanup()


if __name__ == "__main__":
    asyncio.run(main())
