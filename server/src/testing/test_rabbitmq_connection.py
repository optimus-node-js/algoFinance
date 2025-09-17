"""
RabbitMQ Connection Test Script
Quick test to check if RabbitMQ server is running and accessible
"""

import pika
import sys
import os

def test_rabbitmq_connection():
    """Test basic RabbitMQ connection."""
    print("🧪 Testing RabbitMQ Connection...")
    print("=" * 40)
    
    try:
        # Try to connect to RabbitMQ
        print("🔗 Attempting to connect to RabbitMQ...")
        
        connection = pika.BlockingConnection(
            pika.ConnectionParameters(
                host='localhost',
                port=5672,
                virtual_host='/',
                credentials=pika.PlainCredentials('guest', 'guest')
            )
        )
        
        print("✅ Connection successful!")
        
        # Create a channel
        channel = connection.channel()
        print("✅ Channel created successfully!")
        
        # Test queue declaration
        test_queue = 'rabbitmq_test_queue'
        channel.queue_declare(queue=test_queue, durable=True)
        print(f"✅ Test queue '{test_queue}' declared successfully!")
        
        # Test message publishing
        test_message = "Hello RabbitMQ! Test message."
        channel.basic_publish(
            exchange='',
            routing_key=test_queue,
            body=test_message,
            properties=pika.BasicProperties(delivery_mode=2)
        )
        print("✅ Test message published successfully!")
        
        # Clean up test queue
        channel.queue_delete(queue=test_queue)
        print("✅ Test queue cleaned up!")
        
        # Close connection
        connection.close()
        print("✅ Connection closed successfully!")
        
        print("\n🎉 RabbitMQ is working perfectly!")
        print("📋 You can now run the sender and receiver scripts")
        
        return True
        
    except pika.exceptions.AMQPConnectionError as e:
        print(f"❌ RabbitMQ Connection Failed: {e}")
        print("\n💡 Possible solutions:")
        print("   1. Install RabbitMQ server")
        print("   2. Start RabbitMQ service")
        print("   3. Check if RabbitMQ is running on localhost:5672")
        print("   4. Verify firewall settings")
        return False
        
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

def check_rabbitmq_service():
    """Check if RabbitMQ service is running."""
    print("\n🔍 Checking RabbitMQ Service Status...")
    
    try:
        # Windows service check
        if os.name == 'nt':
            import subprocess
            result = subprocess.run(
                ['sc', 'query', 'RabbitMQ'],
                capture_output=True,
                text=True
            )
            
            if 'RUNNING' in result.stdout:
                print("✅ RabbitMQ service is running")
                return True
            else:
                print("❌ RabbitMQ service is not running")
                print("💡 Try starting it with: net start RabbitMQ")
                return False
        else:
            # Linux service check
            import subprocess
            result = subprocess.run(
                ['systemctl', 'is-active', 'rabbitmq-server'],
                capture_output=True,
                text=True
            )
            
            if result.stdout.strip() == 'active':
                print("✅ RabbitMQ service is running")
                return True
            else:
                print("❌ RabbitMQ service is not running")
                print("💡 Try starting it with: sudo systemctl start rabbitmq-server")
                return False
                
    except Exception as e:
        print(f"⚠️ Could not check service status: {e}")
        return None

def main():
    """Main test function."""
    print("🐰 RabbitMQ Connection Test")
    print("=" * 40)
    
    # Check service status first
    service_running = check_rabbitmq_service()
    
    # Test connection
    connection_ok = test_rabbitmq_connection()
    
    print("\n📊 Test Summary:")
    print(f"   🔧 Service Status: {'✅ Running' if service_running else '❌ Not Running'}")
    print(f"   🔗 Connection Test: {'✅ Success' if connection_ok else '❌ Failed'}")
    
    if connection_ok:
        print("\n🚀 Ready to test stock data communication!")
        print("📋 Next steps:")
        print("   1. Run receiver: python server/src/testing/rabbitmq_receiver.py")
        print("   2. Run sender: python server/src/testing/rabbitmq_sender.py")
    else:
        print("\n🔧 RabbitMQ needs to be installed/started first")

if __name__ == "__main__":
    main()

