import pika
import json
import sys
import time
import os
import importlib
import inspect

# Add the parent 'src' directory to the path to allow for absolute imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from strategy.base_strategy import BaseStrategy

class StrategyService:
    def __init__(self):
        self.rabbit_connection = None
        self.rabbit_channel = None
        self.strategies = []
        self._setup_rabbitmq()
        self._load_strategies()

    def _load_strategies(self):
        """Dynamically loads all strategy classes from the 'strategies' directory."""
        strategies_dir = os.path.join(os.path.dirname(__file__), 'strategies')
        strategy_files = [f for f in os.listdir(strategies_dir) if f.endswith('.py') and not f.startswith('__')]

        for file_name in strategy_files:
            module_name = f"strategy.strategies.{file_name[:-3]}"
            try:
                module = importlib.import_module(module_name)
                for name, cls in inspect.getmembers(module, inspect.isclass):
                    # Check if it's a subclass of BaseStrategy and not BaseStrategy itself
                    if issubclass(cls, BaseStrategy) and cls is not BaseStrategy:
                        strategy_instance = cls()
                        strategy_instance.publish_order = self.publish_order # Inject the publisher method
                        self.strategies.append(strategy_instance)
                        print(f"✅ Successfully loaded strategy: {name}")
            except ImportError as e:
                print(f"❌ Error importing strategy module {module_name}: {e}")


    def _setup_rabbitmq(self):
        """Sets up the connection and channel for RabbitMQ."""
        while not self.rabbit_connection or self.rabbit_connection.is_closed:
            try:
                self.rabbit_connection = pika.BlockingConnection(pika.ConnectionParameters('localhost'))
                self.rabbit_channel = self.rabbit_connection.channel()
                
                # Declare exchanges to ensure they exist
                self.rabbit_channel.exchange_declare(exchange='market_data_exchange', exchange_type='fanout')
                self.rabbit_channel.exchange_declare(exchange='orders_exchange', exchange_type='direct', durable=True)
                
                print("✅ Strategy Service connected to RabbitMQ.")
                return
            except pika.exceptions.AMQPConnectionError as e:
                print(f"❌ RabbitMQ connection failed for Strategy Service: {e}. Retrying in 5 seconds...")
                time.sleep(5)

    def start(self):
        """Starts consuming market data and applying strategies."""
        # Create a queue for this service to consume market data
        result = self.rabbit_channel.queue_declare(queue='', exclusive=True)
        queue_name = result.method.queue
        self.rabbit_channel.queue_bind(exchange='market_data_exchange', queue=queue_name)

        print('✅ Strategy Service is listening for market data. To exit press CTRL+C')

        def callback(ch, method, properties, body):
            market_data = json.loads(body)
            # print(f"   ▶️ Strategy received data: {market_data}") # Can be noisy

            # --- Execute all loaded strategies ---
            for strategy in self.strategies:
                try:
                    strategy.execute(market_data)
                except Exception as e:
                    print(f"   ❌ Error executing strategy {type(strategy).__name__}: {e}")


        self.rabbit_channel.basic_consume(
            queue=queue_name,
            on_message_callback=callback,
            auto_ack=True
        )

        try:
            self.rabbit_channel.start_consuming()
        except KeyboardInterrupt:
            self.stop()

    def publish_order(self, order_details):
        """Publishes an order to the orders exchange."""
        try:
            if not self.rabbit_channel or self.rabbit_channel.is_closed:
                print("   Reconnecting to RabbitMQ to publish order...")
                self._setup_rabbitmq()

            self.rabbit_channel.basic_publish(
                exchange='orders_exchange',
                routing_key='place.order',
                body=json.dumps(order_details),
                properties=pika.BasicProperties(delivery_mode=2)
            )
            print(f"   ✅ Published order request: {order_details}")
        except Exception as e:
            print(f"   ❌ Error publishing order: {e}")

    def stop(self):
        """Stops the service gracefully."""
        if self.rabbit_connection and self.rabbit_connection.is_open:
            self.rabbit_connection.close()
        print("❕ Strategy Service stopped.")

if __name__ == '__main__':
    service = StrategyService()
    service.start() 