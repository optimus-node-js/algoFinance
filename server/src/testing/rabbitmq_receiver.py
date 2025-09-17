"""
RabbitMQ Receiver Test Script
Receives stock market data to test RabbitMQ communication
Based on: https://www.geeksforgeeks.org/python/integrating-rabbitmq-with-python/
"""

import sys
import os
import json
import pika
from datetime import datetime

# Add the project root directory to the Python path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
sys.path.append(PROJECT_ROOT)

class StockDataReceiver:
    """Simple RabbitMQ receiver for stock market data testing."""
    
    def __init__(self):
        self.connection = None
        self.channel = None
        self.queue_name = 'stock_data_test'
        self.message_count = 0
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
            print(f"📥 Ready to receive stock data from queue: {self.queue_name}")
            return True
            
        except pika.exceptions.AMQPConnectionError as e:
            print(f"❌ Failed to connect to RabbitMQ: {e}")
            print("💡 Make sure RabbitMQ server is running on localhost:5672")
            return False
        except Exception as e:
            print(f"❌ Unexpected error: {e}")
            return False
    
    def process_stock_data(self, ch, method, properties, body):
        """Process received stock market data."""
        try:
            # Decode JSON message
            stock_data = json.loads(body)
            
            # Extract stock information
            symbol = stock_data.get('symbol', 'Unknown')
            price = stock_data.get('price', 0.0)
            volume = stock_data.get('volume', 0)
            timestamp = stock_data.get('timestamp', 'No timestamp')
            source = stock_data.get('source', 'Unknown')
            
            self.message_count += 1
            
            # Display received data
            print(f"📥 [{self.message_count:3d}] {symbol}: ₹{price:8.2f} | Vol: {volume:5d} | From: {source}")
            print(f"    ⏰ Received at: {datetime.now().strftime('%H:%M:%S.%f')[:-3]}")
            
            # Acknowledge message processing
            ch.basic_ack(delivery_tag=method.delivery_tag)
            
        except json.JSONDecodeError as e:
            print(f"❌ Failed to decode JSON: {e}")
            print(f"Raw message: {body}")
            # Still acknowledge to remove from queue
            ch.basic_ack(delivery_tag=method.delivery_tag)
            
        except Exception as e:
            print(f"❌ Error processing message: {e}")
            # Still acknowledge to remove from queue
            ch.basic_ack(delivery_tag=method.delivery_tag)
    
    def start_receiving(self):
        """Start receiving messages from RabbitMQ."""
        if not self.channel:
            print("❌ No connection to RabbitMQ")
            return
        
        try:
            # Configure message consumption
            self.channel.basic_qos(prefetch_count=1)  # Process one message at a time
            
            # Set up consumer
            self.channel.basic_consume(
                queue=self.queue_name,
                on_message_callback=self.process_stock_data,
                auto_ack=False  # Manual acknowledgment
            )
            
            print("\n🔄 Waiting for stock data messages...")
            print("📋 Press Ctrl+C to stop receiving")
            print("=" * 50)
            
            # Start consuming (blocking call)
            self.channel.start_consuming()
            
        except KeyboardInterrupt:
            print(f"\n⏹️ Receiver stopped by user")
            print(f"📊 Total messages processed: {self.message_count}")
            self.channel.stop_consuming()
            
        except Exception as e:
            print(f"❌ Error during message consumption: {e}")
    
    def check_queue_status(self):
        """Check the current status of the queue."""
        try:
            method = self.channel.queue_declare(queue=self.queue_name, passive=True)
            message_count = method.method.message_count
            consumer_count = method.method.consumer_count
            
            print(f"📊 Queue Status:")
            print(f"   📨 Messages waiting: {message_count}")
            print(f"   👥 Active consumers: {consumer_count}")
            print(f"   📋 Queue name: {self.queue_name}")
            
            return message_count, consumer_count
            
        except Exception as e:
            print(f"❌ Failed to get queue status: {e}")
            return None, None
    
    def close(self):
        """Close RabbitMQ connection."""
        try:
            if self.connection and not self.connection.is_closed:
                self.connection.close()
                print("✅ RabbitMQ connection closed")
        except Exception as e:
            print(f"❌ Error closing connection: {e}")


def main():
    """Main function to run the receiver."""
    print("🐰 RabbitMQ Stock Data Receiver Test")
    print("=" * 40)
    
    receiver = StockDataReceiver()
    
    if not receiver.channel:
        print("❌ Cannot proceed without RabbitMQ connection")
        return
    
    try:
        # Check queue status first
        receiver.check_queue_status()
        
        print("\nChoose an option:")
        print("1. Start receiving messages")
        print("2. Check queue status only")
        
        choice = input("\nEnter choice (1-2): ").strip()
        
        if choice == '1':
            # Start receiving messages
            receiver.start_receiving()
            
        elif choice == '2':
            # Just check status
            receiver.check_queue_status()
            
        else:
            print("❌ Invalid choice")
    
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        receiver.close()


if __name__ == "__main__":
    main()



