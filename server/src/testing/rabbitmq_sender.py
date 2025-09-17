"""
RabbitMQ Sender Test Script
Sends stock market data to test RabbitMQ communication
Based on: https://www.geeksforgeeks.org/python/integrating-rabbitmq-with-python/
"""

import sys
import os
import json
import time
import pika
from datetime import datetime

# Add the project root directory to the Python path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
sys.path.append(PROJECT_ROOT)

class StockDataSender:
    """Simple RabbitMQ sender for stock market data testing."""
    
    def __init__(self):
        self.connection = None
        self.channel = None
        self.queue_name = 'stock_data_test'
        self.connect()
    
    def connect(self):
        """Connect to RabbitMQ server."""
        try:
            # Default connection parameters for local RabbitMQ
            self.connection = pika.BlockingConnection(
                pika.ConnectionParameters(
                    host='localhost',
                    port=5672,
                    virtual_host='/',
                    credentials=pika.PlainCredentials('guest', 'guest')
                )
            )
            self.channel = self.connection.channel()
            
            # Declare queue (create if doesn't exist)
            self.channel.queue_declare(queue=self.queue_name, durable=True)
            
            print("✅ Connected to RabbitMQ successfully!")
            print(f"📤 Ready to send stock data to queue: {self.queue_name}")
            return True
            
        except pika.exceptions.AMQPConnectionError as e:
            print(f"❌ Failed to connect to RabbitMQ: {e}")
            print("💡 Make sure RabbitMQ server is running on localhost:5672")
            return False
        except Exception as e:
            print(f"❌ Unexpected error: {e}")
            return False
    
    def send_stock_data(self, symbol, price, volume=1000):
        """Send stock market data."""
        if not self.channel:
            print("❌ No connection to RabbitMQ")
            return False
        
        try:
            # Create stock data message
            stock_data = {
                'symbol': symbol,
                'price': price,
                'volume': volume,
                'timestamp': datetime.now().isoformat(),
                'source': 'test_sender'
            }
            
            # Convert to JSON
            message = json.dumps(stock_data)
            
            # Publish message
            self.channel.basic_publish(
                exchange='',
                routing_key=self.queue_name,
                body=message,
                properties=pika.BasicProperties(
                    delivery_mode=2,  # Make message persistent
                    content_type='application/json'
                )
            )
            
            print(f"📤 Sent: {symbol} @ ₹{price} (Volume: {volume})")
            return True
            
        except Exception as e:
            print(f"❌ Failed to send message: {e}")
            return False
    
    def send_test_data_stream(self, duration_seconds=30):
        """Send a stream of test stock data."""
        print(f"🚀 Starting test data stream for {duration_seconds} seconds...")
        
        # Sample stock symbols and base prices
        stocks = {
            'RELIANCE-EQ': 2500.0,
            'TCS-EQ': 3500.0,
            'INFY-EQ': 1800.0,
            'SBIN-EQ': 550.0,
            'HDFC-EQ': 1600.0
        }
        
        start_time = time.time()
        count = 0
        
        try:
            while (time.time() - start_time) < duration_seconds:
                for symbol, base_price in stocks.items():
                    # Simulate price fluctuation (±2%)
                    import random
                    price_change = random.uniform(-0.02, 0.02)
                    current_price = round(base_price * (1 + price_change), 2)
                    volume = random.randint(500, 2000)
                    
                    # Send stock data
                    if self.send_stock_data(symbol, current_price, volume):
                        count += 1
                    
                    time.sleep(0.5)  # Send every 500ms
                
                print(f"📊 Sent {count} messages so far...")
                
        except KeyboardInterrupt:
            print("\n⏹️ Data stream stopped by user")
        
        print(f"✅ Test completed! Sent {count} stock data messages")
    
    def close(self):
        """Close RabbitMQ connection."""
        try:
            if self.connection and not self.connection.is_closed:
                self.connection.close()
                print("✅ RabbitMQ connection closed")
        except Exception as e:
            print(f"❌ Error closing connection: {e}")


def main():
    """Main function to run the sender."""
    print("🐰 RabbitMQ Stock Data Sender Test")
    print("=" * 40)
    
    sender = StockDataSender()
    
    if not sender.channel:
        print("❌ Cannot proceed without RabbitMQ connection")
        return
    
    try:
        print("\nChoose an option:")
        print("1. Send single stock data")
        print("2. Send continuous data stream (30 seconds)")
        print("3. Send custom message")
        
        choice = input("\nEnter choice (1-3): ").strip()
        
        if choice == '1':
            # Send single message
            sender.send_stock_data('RELIANCE-EQ', 2525.50, 1500)
            
        elif choice == '2':
            # Send continuous stream
            sender.send_test_data_stream(30)
            
        elif choice == '3':
            # Custom message
            symbol = input("Enter symbol (e.g., SBIN-EQ): ").strip()
            price = float(input("Enter price: "))
            volume = int(input("Enter volume: "))
            sender.send_stock_data(symbol, price, volume)
            
        else:
            print("❌ Invalid choice")
    
    except KeyboardInterrupt:
        print("\n⏹️ Sender stopped by user")
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        sender.close()


if __name__ == "__main__":
    main()



