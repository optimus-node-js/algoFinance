"""
Order Producer for HFT System
=============================

Specialized producer for trade orders with:
- Order lifecycle tracking
- Risk validation integration
- Execution monitoring
- Performance optimization
"""

import logging
import time
import uuid
from typing import Dict, List, Any, Optional
from datetime import datetime
import threading
from ..kafka_manager import get_kafka_manager
from ..schema_registry import get_schema_registry

logger = logging.getLogger(__name__)

class OrderProducer:
    """
    Specialized producer for trade orders.
    
    Features:
    - Order lifecycle management
    - Risk approval workflow
    - Execution tracking
    - Performance monitoring
    """
    
    def __init__(self, producer_id: str = "order_producer"):
        """
        Initialize order producer.
        
        Args:
            producer_id: Unique identifier for this producer
        """
        self.producer_id = producer_id
        self.kafka_manager = get_kafka_manager()
        self.schema_registry = get_schema_registry()
        
        # Performance tracking
        self.orders_sent = 0
        self.orders_rejected = 0
        self.bytes_sent = 0
        self.start_time = datetime.now()
        self._lock = threading.Lock()
        
        # Configuration
        self.orders_topic = "hft-trade-orders"
        self.executions_topic = "hft-execution-events"
        
        logger.info(f"OrderProducer initialized: {producer_id}")
    
    def send_order(
        self,
        strategy_id: str,
        symbol: str,
        exchange: str,
        side: str,
        quantity: int,
        order_type: str,
        product_type: str = "INTRADAY",
        price: Optional[float] = None,
        order_id: Optional[str] = None,
        parent_order_id: Optional[str] = None,
        risk_check_required: bool = True,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Send a trade order.
        
        Args:
            strategy_id: Strategy that generated the order
            symbol: Trading symbol
            exchange: Exchange identifier
            side: BUY or SELL
            quantity: Order quantity
            order_type: Order type (MARKET, LIMIT, etc.)
            product_type: Product type
            price: Order price (for limit orders)
            order_id: Custom order ID (generated if not provided)
            parent_order_id: Parent order for sliced orders
            risk_check_required: Whether risk validation is needed
            **kwargs: Additional order fields
            
        Returns:
            Dictionary with order details and send status
        """
        try:
            # Generate order ID if not provided
            if not order_id:
                order_id = f"ORD_{int(time.time() * 1000)}_{uuid.uuid4().hex[:8]}"
            
            # Create order message
            message = self.schema_registry.create_trade_order(
                order_id=order_id,
                strategy_id=strategy_id,
                symbol=symbol,
                exchange=exchange,
                side=side.upper(),
                quantity=quantity,
                order_type=order_type.upper(),
                product_type=product_type.upper(),
                price=price,
                parent_order_id=parent_order_id,
                **kwargs
            )
            
            # Add risk check status
            message['risk_approved'] = not risk_check_required  # Will be updated by risk service
            
            # Serialize message
            serialized = self.schema_registry.serialize('trade_order', message)
            if not serialized:
                logger.error(f"Failed to serialize order {order_id}")
                with self._lock:
                    self.orders_rejected += 1
                return {
                    'order_id': order_id,
                    'status': 'SERIALIZATION_FAILED',
                    'success': False,
                    'error': 'Failed to serialize order message'
                }
            
            # Send to Kafka (use order_id as key for ordering)
            success = self.kafka_manager.send_message(
                topic=self.orders_topic,
                message=serialized,
                key=order_id,
                producer_id=self.producer_id,
                callback=lambda err, msg: self._order_delivery_callback(err, msg, order_id)
            )
            
            if success:
                with self._lock:
                    self.orders_sent += 1
                    self.bytes_sent += len(serialized)
                
                logger.info(f"Order sent successfully: {order_id} ({symbol} {side} {quantity})")
                
                return {
                    'order_id': order_id,
                    'status': 'SUBMITTED',
                    'success': True,
                    'symbol': symbol,
                    'side': side,
                    'quantity': quantity,
                    'order_type': order_type,
                    'timestamp': message['timestamp']
                }
            else:
                with self._lock:
                    self.orders_rejected += 1
                
                return {
                    'order_id': order_id,
                    'status': 'SEND_FAILED',
                    'success': False,
                    'error': 'Failed to send to Kafka'
                }
                
        except Exception as e:
            logger.error(f"Error sending order: {e}")
            with self._lock:
                self.orders_rejected += 1
            
            return {
                'order_id': order_id if 'order_id' in locals() else 'UNKNOWN',
                'status': 'ERROR',
                'success': False,
                'error': str(e)
            }
    
    def send_order_update(
        self,
        order_id: str,
        status: str,
        filled_quantity: int = 0,
        average_price: Optional[float] = None,
        commission: Optional[float] = None,
        broker_order_id: Optional[str] = None,
        **kwargs
    ) -> bool:
        """
        Send order status update.
        
        Args:
            order_id: Order identifier
            status: New order status
            filled_quantity: Quantity filled
            average_price: Average fill price
            commission: Commission charged
            broker_order_id: Broker's order ID
            **kwargs: Additional update fields
            
        Returns:
            True if update was sent successfully
        """
        try:
            # Create complete order message for update (using schema registry helper)
            message = self.schema_registry.create_trade_order(
                order_id=order_id,
                strategy_id=kwargs.get('strategy_id', 'UNKNOWN'),
                symbol=kwargs.get('symbol', 'UNKNOWN'),
                exchange=kwargs.get('exchange', 'UNKNOWN'),
                side=kwargs.get('side', 'BUY'),
                quantity=kwargs.get('quantity', 0),
                order_type=kwargs.get('order_type', 'MARKET'),
                product_type=kwargs.get('product_type', 'INTRADAY'),
                filled_quantity=filled_quantity,
                **kwargs
            )
            
            # Update specific fields
            message['order_status'] = status.upper()
            message['risk_approved'] = True  # Updates assume risk was already checked
            
            if average_price is not None:
                message['average_price'] = average_price
            if commission is not None:
                message['commission'] = commission
            if broker_order_id is not None:
                message['broker_order_id'] = broker_order_id
            
            # Serialize and send
            serialized = self.schema_registry.serialize('trade_order', message)
            if not serialized:
                logger.error(f"Failed to serialize order update {order_id}")
                return False
            
            success = self.kafka_manager.send_message(
                topic=self.orders_topic,
                message=serialized,
                key=order_id,
                producer_id=self.producer_id
            )
            
            if success:
                logger.info(f"Order update sent: {order_id} -> {status}")
            else:
                logger.error(f"Failed to send order update: {order_id}")
            
            return success
            
        except Exception as e:
            logger.error(f"Error sending order update for {order_id}: {e}")
            return False
    
    def send_execution_event(
        self,
        order_id: str,
        execution_id: str,
        symbol: str,
        exchange: str,
        side: str,
        quantity: int,
        price: float,
        execution_type: str = "FULL",
        venue_timestamp: Optional[int] = None,
        **kwargs
    ) -> bool:
        """
        Send execution event.
        
        Args:
            order_id: Related order ID
            execution_id: Unique execution ID
            symbol: Trading symbol
            exchange: Exchange identifier
            side: BUY or SELL
            quantity: Executed quantity
            price: Execution price
            execution_type: Type of execution
            venue_timestamp: Venue execution timestamp
            **kwargs: Additional execution fields
            
        Returns:
            True if event was sent successfully
        """
        try:
            now_ns = int(time.time() * 1_000_000_000)
            
            # Create execution event message
            message = {
                'event_id': f"EXEC_{int(time.time() * 1000)}_{uuid.uuid4().hex[:8]}",
                'order_id': order_id,
                'execution_id': execution_id,
                'symbol': symbol,
                'exchange': exchange,
                'side': side.upper(),
                'quantity': quantity,
                'price': price,
                'timestamp': now_ns,
                'venue_timestamp': venue_timestamp,
                'execution_type': execution_type.upper(),
                'net_amount': price * quantity,  # Basic calculation
                **kwargs
            }
            
            # Add default values for required fields
            required_defaults = {
                'cumulative_quantity': quantity,
                'remaining_quantity': 0,
                'average_price': price,
                'order_status': 'FILLED' if execution_type.upper() == 'FULL' else 'PARTIALLY_FILLED',
                'commission': 0.0,
                'fees': 0.0,
                'slippage': 0.0,
                'liquidity': 'UNKNOWN',  # Add missing required field
                'tags': {}  # Add missing required field
            }
            
            for field, default_value in required_defaults.items():
                if field not in message:
                    message[field] = default_value
            
            # Serialize and send
            serialized = self.schema_registry.serialize('execution_event', message)
            if not serialized:
                logger.error(f"Failed to serialize execution event {execution_id}")
                return False
            
            success = self.kafka_manager.send_message(
                topic=self.executions_topic,
                message=serialized,
                key=order_id,  # Key by order_id for ordering
                producer_id=self.producer_id
            )
            
            if success:
                logger.info(f"Execution event sent: {execution_id} ({symbol} {side} {quantity}@{price})")
            else:
                logger.error(f"Failed to send execution event: {execution_id}")
            
            return success
            
        except Exception as e:
            logger.error(f"Error sending execution event {execution_id}: {e}")
            return False
    
    def send_bulk_orders(self, orders: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Send multiple orders efficiently.
        
        Args:
            orders: List of order data dictionaries
            
        Returns:
            Dictionary with send results and statistics
        """
        start_time = time.time()
        successful_orders = []
        failed_orders = []
        
        logger.info(f"Sending bulk orders: {len(orders)} orders")
        
        for order_data in orders:
            try:
                result = self.send_order(**order_data)
                if result['success']:
                    successful_orders.append(result)
                else:
                    failed_orders.append(result)
                    
            except Exception as e:
                logger.error(f"Error in bulk order send: {e}")
                failed_orders.append({
                    'order_id': 'UNKNOWN',
                    'status': 'ERROR',
                    'success': False,
                    'error': str(e)
                })
        
        end_time = time.time()
        duration = end_time - start_time
        
        results = {
            'total_orders': len(orders),
            'successful': len(successful_orders),
            'failed': len(failed_orders),
            'duration_seconds': duration,
            'orders_per_second': len(orders) / duration if duration > 0 else 0,
            'success_rate': len(successful_orders) / len(orders) if len(orders) > 0 else 0,
            'successful_orders': successful_orders,
            'failed_orders': failed_orders
        }
        
        logger.info(f"Bulk order send completed: {results}")
        return results
    
    def _order_delivery_callback(self, err, msg, order_id: str):
        """Callback for order delivery confirmation."""
        if err:
            logger.error(f"Order delivery failed for {order_id}: {err}")
        else:
            logger.debug(f"Order delivered: {order_id} to {msg.topic()}[{msg.partition()}]@{msg.offset()}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get producer statistics."""
        with self._lock:
            runtime = (datetime.now() - self.start_time).total_seconds()
            
            return {
                'producer_id': self.producer_id,
                'orders_topic': self.orders_topic,
                'executions_topic': self.executions_topic,
                'orders_sent': self.orders_sent,
                'orders_rejected': self.orders_rejected,
                'bytes_sent': self.bytes_sent,
                'runtime_seconds': runtime,
                'orders_per_second': self.orders_sent / runtime if runtime > 0 else 0,
                'rejection_rate': self.orders_rejected / (self.orders_sent + self.orders_rejected) if (self.orders_sent + self.orders_rejected) > 0 else 0,
                'start_time': self.start_time.isoformat()
            }
    
    def flush(self, timeout: float = 10.0):
        """Flush all pending messages."""
        try:
            producer = self.kafka_manager.get_producer(self.producer_id)
            remaining = producer.flush(timeout)
            if remaining > 0:
                logger.warning(f"OrderProducer: {remaining} messages not delivered after flush")
            else:
                logger.info(f"OrderProducer: all messages flushed successfully")
        except Exception as e:
            logger.error(f"Error flushing OrderProducer: {e}")
    
    def close(self):
        """Close the producer."""
        logger.info(f"Closing OrderProducer: {self.producer_id}")
        self.flush()
        
        # Log final statistics
        stats = self.get_stats()
        logger.info(f"OrderProducer final stats: {stats}")


# Global order producer instance
_order_producer: Optional[OrderProducer] = None
_producer_lock = threading.Lock()

def get_order_producer(producer_id: str = "order_producer") -> OrderProducer:
    """Get or create global order producer instance."""
    global _order_producer
    
    with _producer_lock:
        if _order_producer is None:
            _order_producer = OrderProducer(producer_id)
        return _order_producer

def close_order_producer():
    """Close global order producer."""
    global _order_producer
    
    with _producer_lock:
        if _order_producer:
            _order_producer.close()
            _order_producer = None
