import sys
import os
import time
import pika
import json
import threading
from queue import Queue
import pandas as pd
from SmartApi.smartWebSocketV2 import SmartWebSocketV2

# Add the src directory to the Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from api_gateway.auth import AngelOneAuth
from database.connect import get_db
from ml.features import FeatureEngine

class DataStreamer:
    def __init__(self, window_size=200):
        self.auth = AngelOneAuth()
        self.db = get_db()
        self.feature_engine = FeatureEngine()
        self.sws = None
        self.rabbit_connection = None
        self.rabbit_channel = None
        self.message_queue = Queue()
        self.window_size = window_size
        self.data_windows = {}  # Holds a DataFrame for each instrument token
        self.window_lock = threading.Lock() # To ensure thread-safe access to windows
        self._setup_rabbitmq()

        # A worker thread to process messages from the queue (DB/RabbitMQ operations)
        self.worker_thread = threading.Thread(target=self._process_messages, daemon=True)
        self.worker_thread.start()

    def _setup_rabbitmq(self):
        """Sets up the connection and channel for RabbitMQ."""
        try:
            self.rabbit_connection = pika.BlockingConnection(pika.ConnectionParameters('localhost'))
            self.rabbit_channel = self.rabbit_connection.channel()
            # A fanout exchange broadcasts all the messages it receives to all the queues it knows.
            self.rabbit_channel.exchange_declare(exchange='market_data_exchange', exchange_type='fanout')
            print("✅ RabbitMQ connection established.")
        except pika.exceptions.AMQPConnectionError as e:
            print(f"❌ RabbitMQ connection failed: {e}")
            self.rabbit_connection = None
            self.rabbit_channel = None

    def _process_messages(self):
        """
        Worker thread function.
        Pulls messages from the in-memory queue and performs the slow I/O operations.
        """
        while True:
            message = self.message_queue.get()
            if message is None:  # A 'None' message is our signal to stop the worker.
                break

            # The message is now a dict (a single row from a DataFrame).
            # Let's ensure it's JSON serializable before publishing.
            # Convert timestamp if it exists and is not JSON friendly.
            if 'timestamp' in message and hasattr(message['timestamp'], 'isoformat'):
                message['timestamp'] = message['timestamp'].isoformat()

            # --- Publish to RabbitMQ ---
            if self.rabbit_channel:
                try:
                    self.rabbit_channel.basic_publish(
                        exchange='market_data_exchange',
                        routing_key='',
                        body=json.dumps(message)
                    )
                except Exception as e:
                    print(f"❌ Error publishing to RabbitMQ: {e}")

            # --- Save to Database ---
            if self.db is not None:
                try:
                    collection = self.db.market_data_ticks
                    collection.insert_one(message)
                except Exception as e:
                    print(f"❌ Error saving tick to DB: {e}")
            
            self.message_queue.task_done()

    def start_streaming(self):
        """
        Connects to the WebSocket V2 and starts streaming data.
        """
        if not self.auth.login():
            print("❌ Streaming cannot start due to login failure.")
            return

        if self.db is None:
            print("❌ Streaming cannot start due to database connection failure.")
            return
            
        correlation_id = "stream1"
        action = 1  # 1 for subscribe
        mode = 1    # 1 for LTP

        # New token format for WebSocket V2
        # exchangeType: 1 for NSE_CM, 2 for NSE_FO, etc.
        # NIFTY 50 Index token is "26000"
        # NIFTY BANK Index token is "26009"
        token_list = [
            {
                "exchangeType": 1,
                "tokens": ["26000", "26009"]
            }
        ]

        self.sws = SmartWebSocketV2(self.auth.jwt_token, self.auth.api_key, self.auth.client_id, self.auth.feed_token)

        def on_data(wsapp, message):
            """
            Callback function to handle incoming WebSocket messages.
            This is now responsible for updating the data window and running feature engineering.
            """
            token = message.get("token")
            if not token:
                return  # Ignore messages without a token

            with self.window_lock:
                # 1. Get or create the DataFrame for this token
                if token not in self.data_windows:
                    self.data_windows[token] = pd.DataFrame(columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
                
                # 2. Prepare the new tick data
                # The tick data from the WebSocket might not have standard OHLCV fields.
                # We need to adapt it. LTP is usually the most important field.
                new_tick = {
                    'timestamp': pd.to_datetime(message.get('exchange_timestamp', time.time()), unit='s'),
                    'open': message.get('last_traded_price'),
                    'high': message.get('last_traded_price'),
                    'low': message.get('last_traded_price'),
                    'close': message.get('last_traded_price'),
                    'volume': message.get('last_traded_quantity')
                }

                # 3. Append new tick and maintain window size
                window_df = self.data_windows[token]
                window_df.loc[len(window_df)] = new_tick
                if len(window_df) > self.window_size:
                    self.data_windows[token] = window_df.iloc[-self.window_size:]
                
                # 4. Generate features if we have enough data
                if len(self.data_windows[token]) > 20: # A reasonable threshold to start calculating
                    enriched_df = self.feature_engine.add_features(self.data_windows[token].copy())
                    
                    # 5. Get the latest row (which has all features) and put it on the queue
                    latest_data_with_features = enriched_df.iloc[-1].to_dict()
                    self.message_queue.put(latest_data_with_features)

        def on_open(wsapp):
            print("✅ WebSocket V2 connection opened.")
            print(f"Subscribing to: {token_list}")
            self.sws.subscribe(correlation_id, mode, token_list)

        def on_error(wsapp, error):
            print(f"❌ WebSocket V2 error: {error}")

        def on_close(wsapp, close_status_code, close_msg):
            print("❕ WebSocket V2 connection closed.")

        # Assign the callbacks.
        self.sws.on_open = on_open
        self.sws.on_data = on_data
        self.sws.on_error = on_error
        self.sws.on_close = on_close

        # Connect to the WebSocket. This is a blocking call.
        self.sws.connect()

    def close(self):
        """Closes connections and stops the worker thread gracefully."""
        # Stop the worker thread by sending the signal
        self.message_queue.put(None)
        if self.worker_thread.is_alive():
            self.worker_thread.join() # Wait for the worker to finish
        
        # Close RabbitMQ connection
        if self.rabbit_connection and self.rabbit_connection.is_open:
            self.rabbit_connection.close()
            print("❕ RabbitMQ connection closed.")


if __name__ == "__main__":
    streamer = DataStreamer()
    try:
        streamer.start_streaming()
    except KeyboardInterrupt:
        print("\n❕ User interrupted. Shutting down.")
    finally:
        streamer.close() 