import sys
import os
import pika
import json
from datetime import datetime, UTC

# Add the src directory to the Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from api_gateway.auth import AngelOneAuth
from api_gateway.utils import find_instrument_token
from database.connect import get_db

class OrderManager:
    def __init__(self):
        self.auth = AngelOneAuth()
        self.db = get_db()
        self.smart_connect = None

    def initialize(self):
        """
        Initializes the OrderManager by logging in.
        """
        if not self.auth.login():
            print("❌ OMS initialization failed.")
            return False
        
        self.smart_connect = self.auth.smart_connect
        if self.db is None:
            print("❌ OMS cannot connect to the database.")
            return False
            
        print("✅ OMS initialized successfully.")
        return True

    def start_listening(self):
        """
        Connects to RabbitMQ and starts listening for order requests.
        This is a blocking call.
        """
        try:
            connection = pika.BlockingConnection(pika.ConnectionParameters('localhost'))
            channel = connection.channel()

            # A direct exchange delivers messages to queues based on a message routing key.
            channel.exchange_declare(exchange='orders_exchange', exchange_type='direct', durable=True)
            
            # This queue will hold all order requests.
            channel.queue_declare(queue='order_requests_queue', durable=True)

            # Bind the queue to the exchange with a specific routing key.
            channel.queue_bind(exchange='orders_exchange', queue='order_requests_queue', routing_key='place.order')

            print('✅ OMS is listening for order requests. To exit press CTRL+C')

            def callback(ch, method, properties, body):
                print("▶️ Received order request")
                try:
                    order_params = json.loads(body)
                    print(f"   Request body: {order_params}")
                    self.place_order(**order_params)
                    ch.basic_ack(delivery_tag=method.delivery_tag) # Acknowledge the message
                    print("   ✅ Order processed and message acknowledged.")
                except json.JSONDecodeError as e:
                    print(f"   ❌ Error decoding message body: {e}")
                    ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False) # Discard malformed message
                except Exception as e:
                    print(f"   ❌ Error processing order: {e}")
                    # We nack and requeue so the message can be retried later.
                    # In a production system, you might want a dead-letter queue for failing messages.
                    ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)

            channel.basic_consume(
                queue='order_requests_queue',
                on_message_callback=callback,
                auto_ack=False # Manual acknowledgement
            )

            channel.start_consuming()

        except pika.exceptions.AMQPConnectionError as e:
            print(f"❌ RabbitMQ connection failed: {e}")
        except KeyboardInterrupt:
            print('❕ OMS listener stopped.')
            connection.close()

    def place_order(self, variety, tradingsymbol, transactiontype, exchange, ordertype, producttype, duration, quantity):
        """
        Places an order and logs the transaction.
        Finds the symbol token automatically.
        """
        if not self.smart_connect:
            print("❌ OMS is not initialized. Cannot place order.")
            return None

        # --- Find Token ---
        symboltoken = find_instrument_token(tradingsymbol, self.db, self.smart_connect)
        if not symboltoken:
            print(f"❌ Could not find token for {tradingsymbol}. Order cancelled.")
            # Log the failure before returning
            request_for_log = {
                "variety": variety,
                "tradingsymbol": tradingsymbol,
                "transactiontype": transactiontype,
                "exchange": exchange,
                "ordertype": ordertype,
                "producttype": producttype,
                "duration": duration,
                "quantity": quantity
            }
            self._log_transaction(request_for_log, None, f"Token not found for {tradingsymbol}")
            return None

        try:
            order_params = {
                "variety": variety,
                "tradingsymbol": tradingsymbol,
                "symboltoken": symboltoken,
                "transactiontype": transactiontype,
                "exchange": exchange,
                "ordertype": ordertype,
                "producttype": producttype,
                "duration": duration,
                "price": "0",  # Required for MARKET orders
                "squareoff": "0",
                "stoploss": "0",
                "quantity": str(quantity)
            }
            
            print(f"Placing order with params: {order_params}")
            
            # Place the order
            order_id = self.smart_connect.placeOrder(order_params)
            
            print(f"Received Order ID: {order_id}")

            # Log the transaction
            self._log_transaction(order_params, order_id)
            
            return order_id

        except Exception as e:
            print(f"❌ Error placing order: {e}")
            self._log_transaction(order_params, None, str(e))
            return None

    def _log_transaction(self, request, order_id, error=None):
        """
        Logs the order request and response/error to MongoDB.
        """
        log_entry = {
            "timestamp": datetime.now(UTC),
            "request_payload": request,
            "response_order_id": order_id,
            "status": "FAILED" if error else "SUCCESS",
            "error_message": error
        }
        try:
            collection = self.db.order_logs
            collection.insert_one(log_entry)
            print("✅ Order transaction logged to DB.")
        except Exception as e:
            print(f"❌ Error logging transaction to DB: {e}")


if __name__ == '__main__':
    oms = OrderManager()
    if oms.initialize():
        oms.start_listening() 