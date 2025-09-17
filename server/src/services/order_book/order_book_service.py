import sys
import os
import json
import pika
from datetime import datetime, UTC
from typing import Dict, List, Optional, Any

# Add the project root directory to the Python path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
sys.path.append(PROJECT_ROOT)

from server.src.core.connections import ConnectionManager
from server.src.database.connect import get_db

class OrderBookService:
    """
    Order Book Service for Angel One API integration.
    Handles order history, status tracking, modifications, and cancellations.
    """
    
    def __init__(self):
        self.db = get_db()
        self.rabbit_connection = None
        self.rabbit_channel = None
        self._setup_rabbitmq()
    
    def _setup_rabbitmq(self):
        """Sets up RabbitMQ connection for order updates."""
        try:
            self.rabbit_connection = pika.BlockingConnection(pika.ConnectionParameters('localhost'))
            self.rabbit_channel = self.rabbit_connection.channel()
            
            # Declare exchange for order updates
            self.rabbit_channel.exchange_declare(
                exchange='order_updates_exchange', 
                exchange_type='topic',
                durable=True
            )
            print("✅ Order Book Service RabbitMQ connection established.")
        except pika.exceptions.AMQPConnectionError as e:
            print(f"❌ Order Book Service RabbitMQ connection failed: {e}")
            self.rabbit_connection = None
            self.rabbit_channel = None

    @ConnectionManager.api_request
    def get_order_book(self) -> Dict[str, Any]:
        """
        Fetch complete order history from Angel One API.
        Returns: Dictionary containing order book data or error info.
        """
        smart_connect = ConnectionManager.get_smartapi_client()
        if not smart_connect:
            return {"status": "error", "message": "No SmartAPI connection available"}
        
        try:
            print("📋 Fetching order book from Angel One API...")
            response = smart_connect.orderBook()
            
            if response.get('status') is True or response.get('status') == 'success':
                order_book_data = {
                    "status": "success",
                    "timestamp": datetime.now(UTC).isoformat(),
                    "orders": response.get('data', []),
                    "total_orders": len(response.get('data', [])) if response.get('data') else 0
                }
                
                # Store in database
                self._store_order_book(order_book_data)
                
                # Publish to message queue
                self._publish_order_update("order_book", order_book_data)
                
                print(f"✅ Successfully fetched {order_book_data['total_orders']} orders")
                return order_book_data
            else:
                error_msg = response.get('message', f'Error response: {response}')
                print(f"❌ Error fetching order book: {error_msg}")
                return {"status": "error", "message": error_msg}
                
        except Exception as e:
            error_msg = f"Exception in get_order_book: {str(e)}"
            print(f"❌ {error_msg}")
            return {"status": "error", "message": error_msg}

    @ConnectionManager.api_request  
    def get_trade_book(self) -> Dict[str, Any]:
        """
        Fetch trade book (executed orders) from Angel One API.
        Returns: Dictionary containing trade book data or error info.
        """
        smart_connect = ConnectionManager.get_smartapi_client()
        if not smart_connect:
            return {"status": "error", "message": "No SmartAPI connection available"}
        
        try:
            print("📊 Fetching trade book from Angel One API...")
            response = smart_connect.tradeBook()
            
            if response.get('status') is True or response.get('status') == 'success':
                trade_book_data = {
                    "status": "success",
                    "timestamp": datetime.now(UTC).isoformat(),
                    "trades": response.get('data', []),
                    "total_trades": len(response.get('data', [])) if response.get('data') else 0
                }
                
                # Store in database
                self._store_trade_book(trade_book_data)
                
                # Publish to message queue
                self._publish_order_update("trade_book", trade_book_data)
                
                print(f"✅ Successfully fetched {trade_book_data['total_trades']} trades")
                return trade_book_data
            else:
                error_msg = response.get('message', f'Error response: {response}')
                print(f"❌ Error fetching trade book: {error_msg}")
                return {"status": "error", "message": error_msg}
                
        except Exception as e:
            error_msg = f"Exception in get_trade_book: {str(e)}"
            print(f"❌ {error_msg}")
            return {"status": "error", "message": error_msg}

    @ConnectionManager.api_request
    def get_order_status(self, order_id: str) -> Dict[str, Any]:
        """
        Get status of a specific order by order ID.
        Args:
            order_id: The order ID to check status for
        Returns: Dictionary containing order status or error info.
        """
        smart_connect = ConnectionManager.get_smartapi_client()
        if not smart_connect:
            return {"status": "error", "message": "No SmartAPI connection available"}
        
        try:
            print(f"🔍 Fetching order status for Order ID: {order_id}")
            response = smart_connect.individual_order_details(order_id)
            
            if response.get('status') and response.get('data'):
                order_status_data = {
                    "status": "success",
                    "timestamp": datetime.now(UTC).isoformat(),
                    "order_id": order_id,
                    "order_data": response['data']
                }
                
                # Store in database
                self._store_order_status(order_status_data)
                
                # Publish to message queue
                self._publish_order_update("order_status", order_status_data)
                
                print(f"✅ Successfully fetched status for order {order_id}")
                return order_status_data
            else:
                error_msg = response.get('message', f'Unknown error fetching order status for {order_id}')
                print(f"❌ Error fetching order status: {error_msg}")
                return {"status": "error", "message": error_msg}
                
        except Exception as e:
            error_msg = f"Exception in get_order_status: {str(e)}"
            print(f"❌ {error_msg}")
            return {"status": "error", "message": error_msg}

    @ConnectionManager.api_request
    def modify_order(self, order_params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Modify an existing order.
        Args:
            order_params: Dictionary containing order modification parameters
        Returns: Dictionary containing modification result or error info.
        """
        smart_connect = ConnectionManager.get_smartapi_client()
        if not smart_connect:
            return {"status": "error", "message": "No SmartAPI connection available"}
        
        try:
            order_id = order_params.get('orderid')
            print(f"✏️ Modifying order {order_id}...")
            response = smart_connect.modifyOrder(order_params)
            
            if response.get('status'):
                modify_result = {
                    "status": "success",
                    "timestamp": datetime.now(UTC).isoformat(),
                    "original_order_id": order_id,
                    "modification_result": response,
                    "parameters": order_params
                }
                
                # Store in database
                self._store_order_modification(modify_result)
                
                # Publish to message queue
                self._publish_order_update("order_modified", modify_result)
                
                print(f"✅ Successfully modified order {order_id}")
                return modify_result
            else:
                error_msg = response.get('message', f'Unknown error modifying order {order_id}')
                print(f"❌ Error modifying order: {error_msg}")
                return {"status": "error", "message": error_msg}
                
        except Exception as e:
            error_msg = f"Exception in modify_order: {str(e)}"
            print(f"❌ {error_msg}")
            return {"status": "error", "message": error_msg}

    @ConnectionManager.api_request
    def cancel_order(self, order_id: str, variety: str = "NORMAL") -> Dict[str, Any]:
        """
        Cancel an existing order.
        Args:
            order_id: The order ID to cancel
            variety: Order variety (NORMAL, STOPLOSS, AMO, etc.)
        Returns: Dictionary containing cancellation result or error info.
        """
        smart_connect = ConnectionManager.get_smartapi_client()
        if not smart_connect:
            return {"status": "error", "message": "No SmartAPI connection available"}
        
        try:
            print(f"❌ Cancelling order {order_id}...")
            cancel_params = {
                "variety": variety,
                "orderid": order_id
            }
            response = smart_connect.cancelOrder(cancel_params)
            
            if response.get('status'):
                cancel_result = {
                    "status": "success",
                    "timestamp": datetime.now(UTC).isoformat(),
                    "cancelled_order_id": order_id,
                    "cancellation_result": response,
                    "variety": variety
                }
                
                # Store in database
                self._store_order_cancellation(cancel_result)
                
                # Publish to message queue
                self._publish_order_update("order_cancelled", cancel_result)
                
                print(f"✅ Successfully cancelled order {order_id}")
                return cancel_result
            else:
                error_msg = response.get('message', f'Unknown error cancelling order {order_id}')
                print(f"❌ Error cancelling order: {error_msg}")
                return {"status": "error", "message": error_msg}
                
        except Exception as e:
            error_msg = f"Exception in cancel_order: {str(e)}"
            print(f"❌ {error_msg}")
            return {"status": "error", "message": error_msg}

    def get_order_analytics(self) -> Dict[str, Any]:
        """
        Generate comprehensive order analytics and summary.
        Returns: Dictionary containing order analytics or error info.
        """
        try:
            print("📈 Generating order analytics...")
            
            # Fetch all order components
            order_book = self.get_order_book()
            trade_book = self.get_trade_book()
            
            # Calculate analytics
            analytics = {
                "status": "success",
                "timestamp": datetime.now(UTC).isoformat(),
                "summary": {
                    "total_orders": order_book.get('total_orders', 0),
                    "total_trades": trade_book.get('total_trades', 0),
                    "success_rate": 0.0
                },
                "details": {
                    "order_book": order_book,
                    "trade_book": trade_book
                }
            }
            
            # Calculate success rate
            if analytics['summary']['total_orders'] > 0:
                analytics['summary']['success_rate'] = (
                    analytics['summary']['total_trades'] / analytics['summary']['total_orders']
                ) * 100
            
            # Store analytics in database
            self._store_order_analytics(analytics)
            
            print("✅ Order analytics generated successfully")
            return analytics
            
        except Exception as e:
            error_msg = f"Exception in get_order_analytics: {str(e)}"
            print(f"❌ {error_msg}")
            return {"status": "error", "message": error_msg}

    def _store_order_book(self, order_book_data: Dict[str, Any]):
        """Store order book data in MongoDB."""
        if self.db is not None:
            try:
                collection = self.db.order_book_history
                collection.insert_one(order_book_data)
                print("✅ Order book data stored in database")
            except Exception as e:
                print(f"❌ Error storing order book: {e}")

    def _store_trade_book(self, trade_book_data: Dict[str, Any]):
        """Store trade book data in MongoDB."""
        if self.db is not None:
            try:
                collection = self.db.trade_book_history
                collection.insert_one(trade_book_data)
                print("✅ Trade book data stored in database")
            except Exception as e:
                print(f"❌ Error storing trade book: {e}")

    def _store_order_status(self, order_status_data: Dict[str, Any]):
        """Store order status data in MongoDB."""
        if self.db is not None:
            try:
                collection = self.db.order_status_tracking
                collection.insert_one(order_status_data)
                print("✅ Order status data stored in database")
            except Exception as e:
                print(f"❌ Error storing order status: {e}")

    def _store_order_modification(self, modify_result: Dict[str, Any]):
        """Store order modification data in MongoDB."""
        if self.db is not None:
            try:
                collection = self.db.order_modifications
                collection.insert_one(modify_result)
                print("✅ Order modification data stored in database")
            except Exception as e:
                print(f"❌ Error storing order modification: {e}")

    def _store_order_cancellation(self, cancel_result: Dict[str, Any]):
        """Store order cancellation data in MongoDB."""
        if self.db is not None:
            try:
                collection = self.db.order_cancellations
                collection.insert_one(cancel_result)
                print("✅ Order cancellation data stored in database")
            except Exception as e:
                print(f"❌ Error storing order cancellation: {e}")

    def _store_order_analytics(self, analytics_data: Dict[str, Any]):
        """Store order analytics in MongoDB."""
        if self.db is not None:
            try:
                collection = self.db.order_analytics
                collection.insert_one(analytics_data)
                print("✅ Order analytics stored in database")
            except Exception as e:
                print(f"❌ Error storing order analytics: {e}")

    def _publish_order_update(self, update_type: str, data: Dict[str, Any]):
        """Publish order updates to RabbitMQ."""
        if self.rabbit_channel:
            try:
                routing_key = f"orders.{update_type}"
                message = {
                    "type": update_type,
                    "timestamp": datetime.now(UTC).isoformat(),
                    "data": data
                }
                
                self.rabbit_channel.basic_publish(
                    exchange='order_updates_exchange',
                    routing_key=routing_key,
                    body=json.dumps(message),
                    properties=pika.BasicProperties(delivery_mode=2)  # Persistent message
                )
                print(f"✅ Order update published: {routing_key}")
            except Exception as e:
                print(f"❌ Error publishing order update: {e}")

    def start_order_monitoring(self, interval_seconds: int = 300):
        """
        Start continuous order monitoring service.
        Args:
            interval_seconds: How often to refresh order data (default: 5 minutes)
        """
        import time
        import threading
        
        def monitor_loop():
            while True:
                try:
                    print(f"🔄 Starting order monitoring cycle...")
                    self.get_order_analytics()
                    print(f"⏰ Next order monitoring in {interval_seconds} seconds")
                    time.sleep(interval_seconds)
                except KeyboardInterrupt:
                    print("❕ Order monitoring stopped by user")
                    break
                except Exception as e:
                    print(f"❌ Error in order monitoring: {e}")
                    time.sleep(60)  # Wait 1 minute before retrying
        
        monitor_thread = threading.Thread(target=monitor_loop, daemon=True)
        monitor_thread.start()
        print(f"✅ Order monitoring started (refresh every {interval_seconds}s)")
        return monitor_thread

    def close(self):
        """Close RabbitMQ connections gracefully."""
        if self.rabbit_connection and self.rabbit_connection.is_open:
            self.rabbit_connection.close()
            print("❕ Order Book Service RabbitMQ connection closed.")


if __name__ == '__main__':
    # Test the Order Book Service
    print("🚀 Starting Order Book Service Test...")
    
    order_service = OrderBookService()
    
    try:
        # Test all order book functions
        print("\n1. Testing Order Book...")
        order_book = order_service.get_order_book()
        print(f"Order Book Status: {order_book.get('status')}")
        
        print("\n2. Testing Trade Book...")
        trade_book = order_service.get_trade_book()
        print(f"Trade Book Status: {trade_book.get('status')}")
        
        print("\n3. Testing Order Analytics...")
        analytics = order_service.get_order_analytics()
        print(f"Order Analytics Status: {analytics.get('status')}")
        
        # Test order status if we have orders
        if order_book.get('status') == 'success' and order_book.get('total_orders', 0) > 0:
            # Get the first order ID for testing
            first_order = order_book['orders'][0]
            order_id = first_order.get('orderid')
            if order_id:
                print(f"\n4. Testing Order Status for Order ID: {order_id}")
                status = order_service.get_order_status(order_id)
                print(f"Order Status Check: {status.get('status')}")
        else:
            print("\n4. Skipping Order Status test - No orders found")
        
        print("\n✅ Order Book Service testing completed!")
        
    except KeyboardInterrupt:
        print("\n❕ Testing interrupted by user")
    except Exception as e:
        print(f"\n❌ Error during testing: {e}")
    finally:
        order_service.close()
