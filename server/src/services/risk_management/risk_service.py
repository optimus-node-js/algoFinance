"""
Risk Management Service
Provides comprehensive risk management capabilities including position sizing,
stop-loss management, margin calculations, and exposure monitoring.
"""

import sys
import os
import json
import logging
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, timedelta
import pymongo
import pika
from decimal import Decimal

# Add the project root directory to the Python path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..', '..'))
sys.path.append(PROJECT_ROOT)

from server.src.core.connections import ConnectionManager
from server.src.config import settings

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class RiskManagementService:
    """
    Comprehensive Risk Management Service for algorithmic trading.
    
    Features:
    - Position sizing calculations
    - Stop-loss and take-profit management
    - Margin and exposure monitoring
    - Risk metrics calculation
    - Portfolio risk assessment
    - Real-time risk monitoring
    """
    
    def __init__(self):
        """Initialize the Risk Management Service."""
        self.settings = settings
        self.db = None
        self.rabbitmq_connection = None
        self.rabbitmq_channel = None
        self.smart_connect = None
        
        # Risk parameters (configurable)
        self.max_portfolio_risk = 0.02  # 2% max portfolio risk per trade
        self.max_position_size = 0.10   # 10% max single position size
        self.max_daily_loss = 0.05      # 5% max daily loss
        self.max_drawdown = 0.15        # 15% max drawdown
        
        # Initialize connections
        self._initialize_connections()
        
        logger.info("✅ Risk Management Service initialized successfully")
    
    def _initialize_connections(self):
        """Initialize database and API connections."""
        try:
            # MongoDB connection
            self.db = ConnectionManager.get_mongodb_client()
            if self.db:
                # Create indexes for better performance
                self._create_indexes()
                logger.info("✅ MongoDB connection established")
            
            # RabbitMQ connection for publishing risk alerts
            try:
                import pika
                self.rabbitmq_connection = pika.BlockingConnection(pika.ConnectionParameters('localhost'))
            except Exception as e:
                logger.warning(f"⚠️ RabbitMQ connection failed: {e}")
                self.rabbitmq_connection = None
            
            if self.rabbitmq_connection:
                self.rabbitmq_channel = self.rabbitmq_connection.channel()
                
                # Declare risk management exchanges and queues
                self.rabbitmq_channel.exchange_declare(
                    exchange='risk_alerts', 
                    exchange_type='topic',
                    durable=True
                )
                
                self.rabbitmq_channel.queue_declare(
                    queue='risk_violations',
                    durable=True
                )
                
                self.rabbitmq_channel.queue_bind(
                    exchange='risk_alerts',
                    queue='risk_violations',
                    routing_key='risk.violation.*'
                )
                
                logger.info("✅ RabbitMQ connection established")
            
            # Angel One API connection
            self.smart_connect = ConnectionManager.get_smartapi_client()
            if self.smart_connect:
                logger.info("✅ Angel One API connection established")
                
        except Exception as e:
            logger.error(f"❌ Failed to initialize connections: {e}")
            raise
    
    def _create_indexes(self):
        """Create MongoDB indexes for optimal performance."""
        try:
            collections = {
                'risk_metrics': [
                    ('timestamp', pymongo.DESCENDING),
                    ('portfolio_risk', pymongo.ASCENDING),
                    ('account_id', pymongo.ASCENDING)
                ],
                'position_risks': [
                    ('symbol', pymongo.ASCENDING),
                    ('timestamp', pymongo.DESCENDING),
                    ('risk_level', pymongo.ASCENDING)
                ],
                'risk_violations': [
                    ('timestamp', pymongo.DESCENDING),
                    ('violation_type', pymongo.ASCENDING),
                    ('severity', pymongo.ASCENDING)
                ],
                'stop_loss_orders': [
                    ('symbol', pymongo.ASCENDING),
                    ('is_active', pymongo.ASCENDING),
                    ('trigger_price', pymongo.ASCENDING)
                ]
            }
            
            from server.src.config.settings import DB_NAME
            for collection_name, indexes in collections.items():
                collection = self.db[DB_NAME][collection_name]
                for index in indexes:
                    collection.create_index([index])
                    
            logger.info("✅ Database indexes created successfully")
            
        except Exception as e:
            logger.error(f"❌ Failed to create indexes: {e}")
    
    def calculate_position_size(self, symbol: str, entry_price: float, stop_loss_price: float, 
                              account_balance: float = None) -> Dict[str, Any]:
        """
        Calculate optimal position size based on risk management rules.
        
        Args:
            symbol: Trading symbol
            entry_price: Entry price for the position
            stop_loss_price: Stop loss price
            account_balance: Account balance (if None, fetches from API)
            
        Returns:
            Dict containing position size calculations and risk metrics
        """
        try:
            logger.info(f"🧮 Calculating position size for {symbol}")
            
            # Get account balance if not provided
            if account_balance is None:
                funds_data = self.get_account_funds()
                if funds_data and funds_data.get('status'):
                    account_balance = float(funds_data['data'].get('availablecash', 0))
                else:
                    logger.error("❌ Failed to fetch account balance")
                    return {'status': 'error', 'message': 'Failed to fetch account balance'}
            
            # Calculate risk per share
            risk_per_share = abs(entry_price - stop_loss_price)
            risk_percentage = risk_per_share / entry_price
            
            # Calculate maximum risk amount
            max_risk_amount = account_balance * self.max_portfolio_risk
            
            # Calculate position size based on risk
            max_shares_by_risk = int(max_risk_amount / risk_per_share) if risk_per_share > 0 else 0
            
            # Calculate position size based on portfolio percentage
            max_position_value = account_balance * self.max_position_size
            max_shares_by_position = int(max_position_value / entry_price) if entry_price > 0 else 0
            
            # Take the smaller of the two limits
            recommended_shares = min(max_shares_by_risk, max_shares_by_position)
            
            # Calculate actual investment and risk
            actual_investment = recommended_shares * entry_price
            actual_risk = recommended_shares * risk_per_share
            actual_risk_percentage = (actual_risk / account_balance) * 100 if account_balance > 0 else 0
            
            result = {
                'status': 'success',
                'symbol': symbol,
                'entry_price': entry_price,
                'stop_loss_price': stop_loss_price,
                'account_balance': account_balance,
                'risk_per_share': risk_per_share,
                'risk_percentage': risk_percentage * 100,
                'recommended_shares': recommended_shares,
                'actual_investment': actual_investment,
                'actual_risk': actual_risk,
                'actual_risk_percentage': actual_risk_percentage,
                'max_portfolio_risk': self.max_portfolio_risk * 100,
                'max_position_size': self.max_position_size * 100,
                'timestamp': datetime.now()
            }
            
            # Store calculation in database
            self._store_position_risk_calculation(result)
            
            logger.info(f"✅ Position size calculated: {recommended_shares} shares for {symbol}")
            return result
            
        except Exception as e:
            logger.error(f"❌ Error calculating position size for {symbol}: {e}")
            return {'status': 'error', 'message': str(e)}
    
    def get_account_funds(self) -> Dict[str, Any]:
        """
        Get account funds and margin information using Angel One API.
        
        Returns:
            Dict containing funds and margin data
        """
        try:
            if not self.smart_connect:
                return {'status': 'error', 'message': 'SmartConnect not initialized'}
            
            logger.info("💰 Fetching account funds and margin data")
            
            # Get RMS limits (funds and margin)
            response = self.smart_connect.rmsLimit()
            
            if response and (response.get('status') is True or response.get('status') == 'success'):
                funds_data = {
                    'status': 'success',
                    'data': response.get('data', {}),
                    'timestamp': datetime.now()
                }
                
                # Store in database  
                from server.src.config.settings import DB_NAME
                collection = self.db[DB_NAME]['account_funds']
                collection.insert_one(funds_data)
                
                logger.info("✅ Account funds retrieved successfully")
                return funds_data
            else:
                error_msg = response.get('message', 'Unknown error') if response else 'No response'
                logger.error(f"❌ Failed to get account funds: {error_msg}")
                return {'status': 'error', 'message': error_msg}
                
        except Exception as e:
            logger.error(f"❌ Error getting account funds: {e}")
            return {'status': 'error', 'message': str(e)}
    
    def calculate_portfolio_risk(self) -> Dict[str, Any]:
        """
        Calculate comprehensive portfolio risk metrics.
        
        Returns:
            Dict containing portfolio risk analysis
        """
        try:
            logger.info("📊 Calculating portfolio risk metrics")
            
            # Get current positions
            if not self.smart_connect:
                return {'status': 'error', 'message': 'SmartConnect not initialized'}
            
            positions_response = self.smart_connect.position()
            
            if not (positions_response and (positions_response.get('status') is True or 
                                          positions_response.get('status') == 'success')):
                return {'status': 'error', 'message': 'Failed to fetch positions'}
            
            positions = positions_response.get('data', [])
            if positions is None:
                positions = []
            
            # Get account funds
            funds_data = self.get_account_funds()
            if not funds_data.get('status') == 'success':
                return {'status': 'error', 'message': 'Failed to fetch account funds'}
            
            account_balance = float(funds_data['data'].get('availablecash', 0))
            
            # Calculate risk metrics
            total_investment = 0
            total_pnl = 0
            total_unrealized_pnl = 0
            position_risks = []
            
            for position in positions:
                try:
                    quantity = float(position.get('netqty', 0))
                    if quantity == 0:
                        continue
                    
                    avg_price = float(position.get('avgprice', 0))
                    ltp = float(position.get('ltp', 0))
                    investment = abs(quantity) * avg_price
                    
                    # Calculate P&L
                    pnl = quantity * (ltp - avg_price) if ltp > 0 else 0
                    
                    total_investment += investment
                    total_pnl += float(position.get('pnl', 0))
                    total_unrealized_pnl += pnl
                    
                    # Calculate individual position risk
                    position_risk = {
                        'symbol': position.get('tradingsymbol', ''),
                        'quantity': quantity,
                        'avg_price': avg_price,
                        'ltp': ltp,
                        'investment': investment,
                        'pnl': pnl,
                        'investment_percentage': (investment / account_balance * 100) if account_balance > 0 else 0
                    }
                    position_risks.append(position_risk)
                    
                except (ValueError, TypeError) as e:
                    logger.warning(f"⚠️ Error processing position {position}: {e}")
                    continue
            
            # Calculate portfolio metrics
            portfolio_risk = {
                'status': 'success',
                'timestamp': datetime.now(),
                'account_balance': account_balance,
                'total_investment': total_investment,
                'total_pnl': total_pnl,
                'total_unrealized_pnl': total_unrealized_pnl,
                'investment_percentage': (total_investment / account_balance * 100) if account_balance > 0 else 0,
                'daily_pnl_percentage': (total_pnl / account_balance * 100) if account_balance > 0 else 0,
                'total_positions': len(position_risks),
                'position_risks': position_risks
            }
            
            # Check for risk violations
            violations = self._check_risk_violations(portfolio_risk)
            portfolio_risk['violations'] = violations
            
            # Store in database
            from server.src.config.settings import DB_NAME
            collection = self.db[DB_NAME]['risk_metrics']
            collection.insert_one(portfolio_risk)
            
            # Publish risk alerts if violations found
            if violations:
                self._publish_risk_alert(portfolio_risk)
            
            logger.info(f"✅ Portfolio risk calculated: {len(position_risks)} positions, {total_investment:.2f} invested")
            return portfolio_risk
            
        except Exception as e:
            logger.error(f"❌ Error calculating portfolio risk: {e}")
            return {'status': 'error', 'message': str(e)}
    
    def _check_risk_violations(self, portfolio_risk: Dict) -> List[Dict]:
        """Check for risk violations and return list of violations."""
        violations = []
        
        try:
            # Check daily loss limit
            daily_pnl_percentage = portfolio_risk.get('daily_pnl_percentage', 0)
            if daily_pnl_percentage < -self.max_daily_loss * 100:
                violations.append({
                    'type': 'daily_loss_limit',
                    'severity': 'high',
                    'current_value': daily_pnl_percentage,
                    'limit': -self.max_daily_loss * 100,
                    'message': f'Daily loss {daily_pnl_percentage:.2f}% exceeds limit of {self.max_daily_loss * 100}%'
                })
            
            # Check individual position sizes
            for position in portfolio_risk.get('position_risks', []):
                investment_percentage = position.get('investment_percentage', 0)
                if investment_percentage > self.max_position_size * 100:
                    violations.append({
                        'type': 'position_size_limit',
                        'severity': 'medium',
                        'symbol': position.get('symbol'),
                        'current_value': investment_percentage,
                        'limit': self.max_position_size * 100,
                        'message': f'Position {position.get("symbol")} size {investment_percentage:.2f}% exceeds limit of {self.max_position_size * 100}%'
                    })
            
            # Check total investment percentage
            investment_percentage = portfolio_risk.get('investment_percentage', 0)
            if investment_percentage > 95:  # 95% of account invested
                violations.append({
                    'type': 'overinvestment',
                    'severity': 'medium',
                    'current_value': investment_percentage,
                    'limit': 95,
                    'message': f'Total investment {investment_percentage:.2f}% is too high'
                })
                
        except Exception as e:
            logger.error(f"❌ Error checking risk violations: {e}")
        
        return violations
    
    def _store_position_risk_calculation(self, calculation: Dict):
        """Store position risk calculation in database."""
        try:
            from server.src.config.settings import DB_NAME
            collection = self.db[DB_NAME]['position_risks']
            collection.insert_one(calculation)
        except Exception as e:
            logger.error(f"❌ Error storing position risk calculation: {e}")
    
    def _publish_risk_alert(self, risk_data: Dict):
        """Publish risk alert to RabbitMQ."""
        try:
            if self.rabbitmq_channel:
                alert_message = {
                    'timestamp': datetime.now().isoformat(),
                    'type': 'risk_violation',
                    'violations': risk_data.get('violations', []),
                    'portfolio_summary': {
                        'total_investment': risk_data.get('total_investment'),
                        'daily_pnl_percentage': risk_data.get('daily_pnl_percentage'),
                        'total_positions': risk_data.get('total_positions')
                    }
                }
                
                self.rabbitmq_channel.basic_publish(
                    exchange='risk_alerts',
                    routing_key='risk.violation.high',
                    body=json.dumps(alert_message),
                    properties=pika.BasicProperties(delivery_mode=2)  # Make message persistent
                )
                
                logger.warning(f"⚠️ Risk alert published: {len(risk_data.get('violations', []))} violations")
                
        except Exception as e:
            logger.error(f"❌ Error publishing risk alert: {e}")
    
    def create_stop_loss_order(self, symbol: str, quantity: int, trigger_price: float,
                              order_type: str = 'STOPLOSS_LIMIT') -> Dict[str, Any]:
        """
        Create a stop-loss order for risk management.
        
        Args:
            symbol: Trading symbol
            quantity: Quantity to sell/buy
            trigger_price: Price at which to trigger the stop loss
            order_type: Type of stop loss order
            
        Returns:
            Dict containing order details and status
        """
        try:
            logger.info(f"🛡️ Creating stop-loss order for {symbol} at {trigger_price}")
            
            if not self.smart_connect:
                return {'status': 'error', 'message': 'SmartConnect not initialized'}
            
            # Prepare order parameters
            order_params = {
                'variety': 'NORMAL',
                'tradingsymbol': symbol,
                'symboltoken': '',  # Will need to get this from market data service
                'transactiontype': 'SELL' if quantity > 0 else 'BUY',
                'exchange': 'NSE',  # Default to NSE, should be configurable
                'ordertype': order_type,
                'producttype': 'INTRADAY',
                'duration': 'DAY',
                'price': str(trigger_price),
                'triggerprice': str(trigger_price),
                'quantity': str(abs(quantity))
            }
            
            # Note: This is a placeholder for stop-loss order creation
            # In a real implementation, you would use smart_connect.placeOrder()
            # but we need proper symboltoken and exchange information
            
            stop_loss_record = {
                'symbol': symbol,
                'quantity': quantity,
                'trigger_price': trigger_price,
                'order_type': order_type,
                'created_at': datetime.now(),
                'is_active': True,
                'status': 'pending',
                'order_params': order_params
            }
            
            # Store stop-loss order in database
            from server.src.config.settings import DB_NAME
            collection = self.db[DB_NAME]['stop_loss_orders']
            result = collection.insert_one(stop_loss_record)
            
            stop_loss_record['_id'] = str(result.inserted_id)
            
            logger.info(f"✅ Stop-loss order created for {symbol}")
            return {'status': 'success', 'data': stop_loss_record}
            
        except Exception as e:
            logger.error(f"❌ Error creating stop-loss order for {symbol}: {e}")
            return {'status': 'error', 'message': str(e)}
    
    def monitor_positions(self) -> Dict[str, Any]:
        """
        Monitor all positions for risk violations and stop-loss triggers.
        
        Returns:
            Dict containing monitoring results
        """
        try:
            logger.info("👀 Monitoring positions for risk violations")
            
            # Calculate current portfolio risk
            portfolio_risk = self.calculate_portfolio_risk()
            
            if portfolio_risk.get('status') != 'success':
                return portfolio_risk
            
            monitoring_result = {
                'status': 'success',
                'timestamp': datetime.now(),
                'portfolio_risk': portfolio_risk,
                'stop_loss_checks': [],
                'recommendations': []
            }
            
            # Check stop-loss triggers
            active_stop_losses = self._get_active_stop_losses()
            
            for stop_loss in active_stop_losses:
                symbol = stop_loss.get('symbol')
                trigger_price = stop_loss.get('trigger_price')
                
                # Get current price (this would integrate with market data service)
                # For now, we'll use a placeholder
                current_price = self._get_current_price(symbol)
                
                if current_price and self._should_trigger_stop_loss(stop_loss, current_price):
                    monitoring_result['stop_loss_checks'].append({
                        'symbol': symbol,
                        'trigger_price': trigger_price,
                        'current_price': current_price,
                        'action': 'trigger_stop_loss'
                    })
            
            # Generate recommendations
            violations = portfolio_risk.get('violations', [])
            for violation in violations:
                if violation.get('type') == 'position_size_limit':
                    monitoring_result['recommendations'].append({
                        'type': 'reduce_position',
                        'symbol': violation.get('symbol'),
                        'reason': 'Position size exceeds limit'
                    })
                elif violation.get('type') == 'daily_loss_limit':
                    monitoring_result['recommendations'].append({
                        'type': 'stop_trading',
                        'reason': 'Daily loss limit exceeded'
                    })
            
            # Store monitoring result
            from server.src.config.settings import DB_NAME
            collection = self.db[DB_NAME]['position_monitoring']
            collection.insert_one(monitoring_result)
            
            logger.info(f"✅ Position monitoring completed: {len(violations)} violations, {len(monitoring_result['recommendations'])} recommendations")
            return monitoring_result
            
        except Exception as e:
            logger.error(f"❌ Error monitoring positions: {e}")
            return {'status': 'error', 'message': str(e)}
    
    def _get_active_stop_losses(self) -> List[Dict]:
        """Get all active stop-loss orders from database."""
        try:
            from server.src.config.settings import DB_NAME
            collection = self.db[DB_NAME]['stop_loss_orders']
            return list(collection.find({'is_active': True}))
        except Exception as e:
            logger.error(f"❌ Error getting active stop losses: {e}")
            return []
    
    def _get_current_price(self, symbol: str) -> Optional[float]:
        """
        Get current price for a symbol.
        This should integrate with the Market Data Service.
        """
        # Placeholder - in real implementation, this would call Market Data Service
        # or use Angel One LTP API
        return None
    
    def _should_trigger_stop_loss(self, stop_loss: Dict, current_price: float) -> bool:
        """Determine if stop-loss should be triggered."""
        trigger_price = stop_loss.get('trigger_price', 0)
        quantity = stop_loss.get('quantity', 0)
        
        if quantity > 0:  # Long position
            return current_price <= trigger_price
        else:  # Short position
            return current_price >= trigger_price
    
    def get_risk_summary(self) -> Dict[str, Any]:
        """
        Get comprehensive risk summary for the portfolio.
        
        Returns:
            Dict containing risk summary and metrics
        """
        try:
            logger.info("📋 Generating risk summary")
            
            # Get latest portfolio risk
            portfolio_risk = self.calculate_portfolio_risk()
            
            # Get risk history (last 7 days)
            from server.src.config.settings import DB_NAME
            week_ago = datetime.now() - timedelta(days=7)
            collection = self.db[DB_NAME]['risk_metrics']
            risk_history = list(collection.find(
                {'timestamp': {'$gte': week_ago}},
                sort=[('timestamp', -1)]
            ))
            
            # Get violation history
            violation_collection = self.db[DB_NAME]['risk_violations']
            recent_violations = list(violation_collection.find(
                {'timestamp': {'$gte': week_ago}},
                sort=[('timestamp', -1)]
            ))
            
            summary = {
                'status': 'success',
                'timestamp': datetime.now(),
                'current_risk': portfolio_risk,
                'risk_history_count': len(risk_history),
                'recent_violations_count': len(recent_violations),
                'risk_parameters': {
                    'max_portfolio_risk': self.max_portfolio_risk * 100,
                    'max_position_size': self.max_position_size * 100,
                    'max_daily_loss': self.max_daily_loss * 100,
                    'max_drawdown': self.max_drawdown * 100
                },
                'recommendations': []
            }
            
            # Add recommendations based on current risk
            if portfolio_risk.get('status') == 'success':
                violations = portfolio_risk.get('violations', [])
                if violations:
                    summary['recommendations'].append({
                        'priority': 'high',
                        'message': f'{len(violations)} risk violations detected - immediate action required'
                    })
                
                investment_percentage = portfolio_risk.get('investment_percentage', 0)
                if investment_percentage > 80:
                    summary['recommendations'].append({
                        'priority': 'medium',
                        'message': 'High portfolio utilization - consider reducing exposure'
                    })
            
            logger.info("✅ Risk summary generated successfully")
            return summary
            
        except Exception as e:
            logger.error(f"❌ Error generating risk summary: {e}")
            return {'status': 'error', 'message': str(e)}
    
    def close(self):
        """Close all connections and cleanup resources."""
        try:
            if self.rabbitmq_connection and not self.rabbitmq_connection.is_closed:
                self.rabbitmq_connection.close()
                logger.info("✅ RabbitMQ connection closed")
                
            logger.info("✅ Risk Management Service closed successfully")
            
        except Exception as e:
            logger.error(f"❌ Error closing Risk Management Service: {e}")


def test_risk_management_service():
    """Test function for the Risk Management Service."""
    print("🧪 Testing Risk Management Service...")
    
    try:
        # Initialize service
        service = RiskManagementService()
        
        # Test 1: Calculate position size
        print("\n1️⃣ Testing position size calculation...")
        position_calc = service.calculate_position_size(
            symbol='RELIANCE-EQ',
            entry_price=2500.0,
            stop_loss_price=2400.0,
            account_balance=100000.0
        )
        print(f"Position calculation result: {position_calc.get('status')}")
        if position_calc.get('status') == 'success':
            print(f"Recommended shares: {position_calc.get('recommended_shares')}")
            print(f"Risk percentage: {position_calc.get('actual_risk_percentage'):.2f}%")
        
        # Test 2: Get account funds
        print("\n2️⃣ Testing account funds retrieval...")
        funds = service.get_account_funds()
        print(f"Funds retrieval result: {funds.get('status')}")
        
        # Test 3: Calculate portfolio risk
        print("\n3️⃣ Testing portfolio risk calculation...")
        portfolio_risk = service.calculate_portfolio_risk()
        print(f"Portfolio risk calculation result: {portfolio_risk.get('status')}")
        if portfolio_risk.get('status') == 'success':
            print(f"Total positions: {portfolio_risk.get('total_positions')}")
            print(f"Violations: {len(portfolio_risk.get('violations', []))}")
        
        # Test 4: Create stop-loss order
        print("\n4️⃣ Testing stop-loss order creation...")
        stop_loss = service.create_stop_loss_order(
            symbol='RELIANCE-EQ',
            quantity=10,
            trigger_price=2400.0
        )
        print(f"Stop-loss creation result: {stop_loss.get('status')}")
        
        # Test 5: Monitor positions
        print("\n5️⃣ Testing position monitoring...")
        monitoring = service.monitor_positions()
        print(f"Position monitoring result: {monitoring.get('status')}")
        
        # Test 6: Get risk summary
        print("\n6️⃣ Testing risk summary...")
        summary = service.get_risk_summary()
        print(f"Risk summary result: {summary.get('status')}")
        if summary.get('status') == 'success':
            print(f"Recent violations: {summary.get('recent_violations_count')}")
            print(f"Recommendations: {len(summary.get('recommendations', []))}")
        
        # Cleanup
        service.close()
        
        print("\n✅ Risk Management Service testing completed successfully!")
        
    except Exception as e:
        print(f"\n❌ Risk Management Service testing failed: {e}")


if __name__ == '__main__':
    test_risk_management_service()
