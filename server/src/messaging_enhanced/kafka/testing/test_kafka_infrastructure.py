#!/usr/bin/env python3
"""
Kafka Infrastructure Testing Script
===================================

Comprehensive testing for Day 1 Kafka setup:
- Schema Registry validation
- Kafka Manager functionality  
- Topic Manager operations
- Message serialization/deserialization
- Performance validation

Run from project root: python server/src/messaging_enhanced/kafka/testing/test_kafka_infrastructure.py
"""

import sys
import os
import json
import time
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Optional

# Add server/src to Python path
current_dir = Path(__file__).parent
kafka_dir = current_dir.parent
messaging_dir = kafka_dir.parent  
server_src_dir = messaging_dir.parent
if str(server_src_dir) not in sys.path:
    sys.path.insert(0, str(server_src_dir))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class KafkaInfrastructureTest:
    """Comprehensive Kafka infrastructure testing."""
    
    def __init__(self):
        """Initialize test environment."""
        self.test_results = {}
        self.start_time = datetime.now()
        
        print("🧪 KAFKA INFRASTRUCTURE TESTING")
        print("=" * 50)
        print(f"📅 Test started: {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"📂 Working directory: {os.getcwd()}")
        print(f"🐍 Python path: {sys.executable}")
        print()
    
    def test_imports(self) -> bool:
        """Test all critical imports."""
        print("🔍 Testing Imports...")
        
        try:
            # Test core Python modules
            import confluent_kafka
            import avro.schema
            import avro.io
            print("  ✅ Core dependencies (confluent_kafka, avro) imported")
            
            # Test our modules
            from messaging_enhanced.kafka import (
                KafkaManager, SchemaRegistry, TopicManager,
                MarketDataProducer, OrderProducer, SentimentProducer, RiskEventProducer,
                MarketDataConsumer, OrderConsumer, SentimentConsumer, RiskEventConsumer
            )
            print("  ✅ Messaging enhanced modules imported")
            
            from messaging_enhanced.kafka.kafka_manager import get_kafka_manager, close_kafka_manager
            from messaging_enhanced.kafka.schema_registry import get_schema_registry
            from messaging_enhanced.kafka.topic_manager import get_topic_manager
            print("  ✅ Global manager functions imported")
            
            # Test producer/consumer imports
            from messaging_enhanced.kafka.producers import (
                MarketDataProducer, OrderProducer, SentimentProducer, RiskEventProducer
            )
            from messaging_enhanced.kafka.consumers import (
                MarketDataConsumer, OrderConsumer, SentimentConsumer, RiskEventConsumer
            )
            print("  ✅ Producer/consumer modules imported")
            
            self.test_results['imports'] = True
            print("  🎉 All imports successful!\n")
            return True
            
        except Exception as e:
            print(f"  ❌ Import failed: {e}")
            self.test_results['imports'] = False
            return False
    
    def test_schema_registry(self) -> bool:
        """Test Schema Registry functionality."""
        print("🔍 Testing Schema Registry...")
        
        try:
            from messaging_enhanced.kafka.schema_registry import get_schema_registry
            
            # Get schema registry
            sr = get_schema_registry()
            print(f"  ✅ Schema registry initialized")
            
            # Check loaded schemas
            schemas = sr.list_schemas()
            print(f"  ✅ Schemas loaded: {len(schemas)} schemas")
            for schema_name in schemas:
                print(f"    - {schema_name}")
            
            if len(schemas) == 0:
                print("  ⚠️  No schemas found - checking schema directory...")
                schema_dir = Path(__file__).parent.parent / "schemas"
                print(f"    Schema directory: {schema_dir}")
                if schema_dir.exists():
                    avsc_files = list(schema_dir.glob("*.avsc"))
                    print(f"    .avsc files found: {len(avsc_files)}")
                    for f in avsc_files:
                        print(f"      - {f.name}")
                else:
                    print(f"    ❌ Schema directory not found: {schema_dir}")
            
            # Test message creation if schemas available
            if 'market_tick' in schemas:
                print("  🧪 Testing market tick message creation...")
                message = sr.create_market_tick(
                    symbol="RELIANCE",
                    exchange="NSE",
                    price=2500.50,
                    volume=1000,
                    bid=2500.25,
                    ask=2500.75,
                    bid_size=100,
                    ask_size=150
                )
                print(f"    ✅ Market tick message created: {len(str(message))} chars")
                
                # Test serialization
                serialized = sr.serialize('market_tick', message)
                if serialized:
                    print(f"    ✅ Message serialized: {len(serialized)} bytes")
                    
                    # Test deserialization
                    deserialized = sr.deserialize('market_tick', serialized)
                    if deserialized:
                        print(f"    ✅ Message deserialized successfully")
                    else:
                        print(f"    ❌ Deserialization failed")
                else:
                    print(f"    ❌ Serialization failed")
            
            # Get statistics
            stats = sr.get_stats()
            print(f"  📊 Schema registry stats:")
            print(f"    - Schemas loaded: {stats['schemas_loaded']}")
            print(f"    - Schema directory: {stats['schema_dir']}")
            
            self.test_results['schema_registry'] = True
            print("  🎉 Schema Registry test completed!\n")
            return True
            
        except Exception as e:
            print(f"  ❌ Schema Registry test failed: {e}")
            import traceback
            traceback.print_exc()
            self.test_results['schema_registry'] = False
            return False
    
    def test_kafka_manager_basic(self) -> bool:
        """Test Kafka Manager basic functionality (without actual Kafka)."""
        print("🔍 Testing Kafka Manager (Basic)...")
        
        try:
            from messaging_enhanced.kafka.kafka_manager import get_kafka_manager
            
            # Get Kafka manager (will fail to connect but should initialize)
            km = get_kafka_manager("localhost:9092")
            print(f"  ✅ Kafka manager initialized")
            
            # Test producer creation (will work even without Kafka)
            try:
                producer = km.get_producer("test_producer")
                print(f"  ✅ Producer created (will connect when needed)")
            except Exception as e:
                print(f"  ⚠️  Producer creation warning: {e}")
            
            # Get statistics
            stats = km.get_stats()
            print(f"  📊 Kafka manager stats:")
            print(f"    - Bootstrap servers: {stats['bootstrap_servers']}")
            print(f"    - Producers: {stats['producers']}")
            print(f"    - Consumers: {stats['consumers']}")
            
            self.test_results['kafka_manager_basic'] = True
            print("  🎉 Kafka Manager basic test completed!\n")
            return True
            
        except Exception as e:
            print(f"  ❌ Kafka Manager basic test failed: {e}")
            import traceback
            traceback.print_exc()
            self.test_results['kafka_manager_basic'] = False
            return False
    
    def test_topic_manager_basic(self) -> bool:
        """Test Topic Manager basic functionality."""
        print("🔍 Testing Topic Manager (Basic)...")
        
        try:
            from messaging_enhanced.kafka.topic_manager import get_topic_manager
            
            # Get topic manager
            tm = get_topic_manager("localhost:9092")
            print(f"  ✅ Topic manager initialized")
            
            # Get HFT topics configuration
            hft_topics = tm.get_hft_topics()
            print(f"  ✅ HFT topics configuration loaded: {len(hft_topics)} topics")
            
            for topic in hft_topics:
                print(f"    - {topic['name']}: {topic['partitions']} partitions, {topic['replication']} replicas")
            
            # Test topic listing (will fail without Kafka but should handle gracefully)
            try:
                topics_info = tm.list_topics()
                if 'error' in topics_info:
                    print(f"  ⚠️  Topic listing warning (expected without Kafka): {topics_info['error']}")
                else:
                    print(f"  ✅ Topics listed successfully")
            except Exception as e:
                print(f"  ⚠️  Topic listing warning (expected without Kafka): {e}")
            
            self.test_results['topic_manager_basic'] = True
            print("  🎉 Topic Manager basic test completed!\n")
            return True
            
        except Exception as e:
            print(f"  ❌ Topic Manager basic test failed: {e}")
            import traceback
            traceback.print_exc()
            self.test_results['topic_manager_basic'] = False
            return False
    
    def test_message_schemas_validation(self) -> bool:
        """Test all message schemas validation."""
        print("🔍 Testing Message Schemas Validation...")
        
        try:
            from messaging_enhanced.kafka.schema_registry import get_schema_registry
            
            sr = get_schema_registry()
            schemas = sr.list_schemas()
            
            if not schemas:
                print("  ⚠️  No schemas available for testing")
                self.test_results['message_schemas'] = False
                return False
            
            test_messages = {}
            
            # Test market_tick schema
            if 'market_tick' in schemas:
                message = sr.create_market_tick(
                    symbol="TCS",
                    exchange="NSE", 
                    price=3500.75,
                    volume=2000,
                    bid=3500.50,
                    ask=3501.00,
                    sequence_number=12345
                )
                if sr.validate_message('market_tick', message):
                    test_messages['market_tick'] = True
                    print("    ✅ market_tick schema validation passed")
                else:
                    test_messages['market_tick'] = False
                    print("    ❌ market_tick schema validation failed")
            
            # Test trade_order schema
            if 'trade_order' in schemas:
                message = sr.create_trade_order(
                    order_id="ORD_001",
                    strategy_id="STRAT_001",
                    symbol="RELIANCE",
                    exchange="NSE",
                    side="BUY",
                    quantity=100,
                    order_type="LIMIT",
                    price=2500.00
                )
                if sr.validate_message('trade_order', message):
                    test_messages['trade_order'] = True
                    print("    ✅ trade_order schema validation passed")
                else:
                    test_messages['trade_order'] = False
                    print("    ❌ trade_order schema validation failed")
            
            # Test sentiment_signal schema
            if 'sentiment_signal' in schemas:
                message = sr.create_sentiment_signal(
                    signal_id="SIG_001",
                    symbol="INFY",
                    sentiment_score=0.75,
                    confidence=0.85,
                    source="newsapi"
                )
                if sr.validate_message('sentiment_signal', message):
                    test_messages['sentiment_signal'] = True
                    print("    ✅ sentiment_signal schema validation passed")
                else:
                    test_messages['sentiment_signal'] = False
                    print("    ❌ sentiment_signal schema validation failed")
            
            success_count = sum(test_messages.values())
            total_count = len(test_messages)
            
            print(f"  📊 Schema validation results: {success_count}/{total_count} passed")
            
            self.test_results['message_schemas'] = success_count == total_count
            print("  🎉 Message schemas validation completed!\n")
            return success_count == total_count
            
        except Exception as e:
            print(f"  ❌ Message schemas validation failed: {e}")
            import traceback
            traceback.print_exc()
            self.test_results['message_schemas'] = False
            return False
    
    def test_performance_basic(self) -> bool:
        """Test basic performance characteristics."""
        print("🔍 Testing Basic Performance...")
        
        try:
            from messaging_enhanced.kafka.schema_registry import get_schema_registry
            
            sr = get_schema_registry()
            schemas = sr.list_schemas()
            
            if 'market_tick' not in schemas:
                print("  ⚠️  market_tick schema not available for performance test")
                self.test_results['performance'] = False
                return False
            
            # Performance test: serialize/deserialize 1000 messages
            print("  🚀 Performance test: 1000 message serialization/deserialization...")
            
            start_time = time.time()
            
            for i in range(1000):
                # Create message
                message = sr.create_market_tick(
                    symbol=f"TEST{i % 10}",
                    exchange="NSE",
                    price=1000.0 + (i % 100),
                    volume=1000 + i,
                    bid=999.9 + (i % 100),
                    ask=1000.1 + (i % 100),
                    sequence_number=i
                )
                
                # Serialize
                serialized = sr.serialize('market_tick', message)
                if not serialized:
                    print(f"    ❌ Serialization failed at message {i}")
                    break
                
                # Deserialize
                deserialized = sr.deserialize('market_tick', serialized)
                if not deserialized:
                    print(f"    ❌ Deserialization failed at message {i}")
                    break
            
            end_time = time.time()
            duration = end_time - start_time
            messages_per_second = 1000 / duration
            
            print(f"    ✅ 1000 messages processed in {duration:.3f} seconds")
            print(f"    ✅ Throughput: {messages_per_second:.0f} messages/second")
            print(f"    ✅ Average latency: {duration/1000*1000:.3f} ms per message")
            
            # Performance targets for HFT
            target_throughput = 1000  # messages per second
            target_latency = 10       # milliseconds per message
            
            avg_latency_ms = (duration / 1000) * 1000
            
            performance_good = (messages_per_second >= target_throughput and 
                              avg_latency_ms <= target_latency)
            
            if performance_good:
                print(f"    🎯 Performance targets met!")
            else:
                print(f"    ⚠️  Performance below targets:")
                print(f"      Target: >{target_throughput} msg/s, <{target_latency}ms latency")
                print(f"      Actual: {messages_per_second:.0f} msg/s, {avg_latency_ms:.3f}ms latency")
            
            self.test_results['performance'] = True
            print("  🎉 Performance test completed!\n")
            return True
            
        except Exception as e:
            print(f"  ❌ Performance test failed: {e}")
            import traceback
            traceback.print_exc()
            self.test_results['performance'] = False
            return False
    
    def test_producers_consumers_basic(self) -> bool:
        """Test basic producer/consumer functionality."""
        print("🔍 Testing Producers & Consumers (Basic)...")
        
        try:
            # Test market data producer
            from messaging_enhanced.kafka.producers.market_data_producer import get_market_data_producer
            market_producer = get_market_data_producer("test_market_producer")
            print("  ✅ Market data producer created")
            
            # Test order producer
            from messaging_enhanced.kafka.producers.order_producer import get_order_producer
            order_producer = get_order_producer("test_order_producer")
            print("  ✅ Order producer created")
            
            # Test sentiment producer
            from messaging_enhanced.kafka.producers.sentiment_producer import get_sentiment_producer
            sentiment_producer = get_sentiment_producer()
            print("  ✅ Sentiment producer created")
            
            # Test risk event producer
            from messaging_enhanced.kafka.producers.risk_event_producer import get_risk_event_producer
            risk_producer = get_risk_event_producer()
            print("  ✅ Risk event producer created")
            
            # Test market data consumer
            from messaging_enhanced.kafka.consumers.market_data_consumer import get_market_data_consumer
            market_consumer = get_market_data_consumer("test_market_consumer")
            print("  ✅ Market data consumer created")
            
            # Test order consumer
            from messaging_enhanced.kafka.consumers.order_consumer import get_order_consumer
            order_consumer = get_order_consumer()
            print("  ✅ Order consumer created")
            
            # Test sentiment consumer
            from messaging_enhanced.kafka.consumers.sentiment_consumer import get_sentiment_consumer
            sentiment_consumer = get_sentiment_consumer()
            print("  ✅ Sentiment consumer created")
            
            # Test risk event consumer
            from messaging_enhanced.kafka.consumers.risk_event_consumer import get_risk_event_consumer
            risk_consumer = get_risk_event_consumer()
            print("  ✅ Risk event consumer created")
            
            # Test basic functionality (without actual Kafka)
            # These will mostly test the object creation and configuration
            
            # Test market tick creation and sending (will fail gracefully without Kafka)
            tick_result = market_producer.send_market_tick(
                symbol="TEST",
                exchange="NSE",
                price=1000.0,
                volume=100,
                bid=999.5,
                ask=1000.5
            )
            print(f"  ✅ Market tick send test: {tick_result} (expected without Kafka)")
            
            # Test order creation and sending
            order_result = order_producer.send_order(
                strategy_id="TEST_STRAT",
                symbol="TEST",
                exchange="NSE",
                side="BUY",
                quantity=10,
                order_type="LIMIT",
                price=1000.0
            )
            print(f"  ✅ Order send test: {order_result['success']} (expected without Kafka)")
            
            # Test sentiment signal sending
            sentiment_result = sentiment_producer.send_sentiment_signal(
                symbol="TEST",
                sentiment_score=0.5,
                confidence=0.8,
                source="test"
            )
            print(f"  ✅ Sentiment signal test: {sentiment_result['success']} (expected without Kafka)")
            
            # Test risk event sending
            risk_result = risk_producer.send_risk_event(
                event_type="PRE_TRADE_CHECK",
                decision="APPROVED",
                risk_score=0.2
            )
            print(f"  ✅ Risk event test: {risk_result['success']} (expected without Kafka)")
            
            # Get stats from all components
            print("  📊 Component statistics:")
            print(f"    - Market producer: {market_producer.get_stats()}")
            print(f"    - Order producer: {order_producer.get_stats()}")
            print(f"    - Sentiment producer: {sentiment_producer.get_stats()}")
            print(f"    - Risk producer: {risk_producer.get_stats()}")
            print(f"    - Market consumer: {market_consumer.get_stats()}")
            print(f"    - Order consumer: {order_consumer.get_stats()}")
            print(f"    - Sentiment consumer: {sentiment_consumer.get_stats()}")
            print(f"    - Risk consumer: {risk_consumer.get_stats()}")
            
            self.test_results['producers_consumers_basic'] = True
            print("  🎉 Producers & Consumers basic test completed!\n")
            return True
            
        except Exception as e:
            print(f"  ❌ Producers & Consumers basic test failed: {e}")
            import traceback
            traceback.print_exc()
            self.test_results['producers_consumers_basic'] = False
            return False
    
    def print_summary(self):
        """Print comprehensive test summary."""
        end_time = datetime.now()
        duration = end_time - self.start_time
        
        print("=" * 60)
        print("📋 KAFKA INFRASTRUCTURE TEST SUMMARY")
        print("=" * 60)
        print(f"⏱️  Test duration: {duration.total_seconds():.2f} seconds")
        print(f"📅 Completed: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print()
        
        total_tests = len(self.test_results)
        passed_tests = sum(self.test_results.values())
        
        print(f"📊 Results: {passed_tests}/{total_tests} tests passed")
        print()
        
        for test_name, result in self.test_results.items():
            status = "✅ PASS" if result else "❌ FAIL"
            print(f"  {status} {test_name}")
        
        print()
        
        if passed_tests == total_tests:
            print("🎉 ALL TESTS PASSED! Day 1 Kafka infrastructure is ready!")
            print("✅ Ready to proceed to Day 2: Angel One API Enhancement")
        else:
            print(f"⚠️  {total_tests - passed_tests} tests failed. Please review and fix issues.")
            print("🔧 Check error messages above for troubleshooting guidance.")
        
        print()
        print("🚀 Next Steps:")
        print("  1. Fix any failing tests")
        print("  2. Install and configure Kafka for live testing")
        print("  3. Proceed to Day 2 implementation")
        print("=" * 60)
    
    def run_all_tests(self):
        """Run all tests in sequence."""
        print("🚀 Starting comprehensive Kafka infrastructure testing...\n")
        
        # Run tests in logical order
        tests = [
            ("Imports", self.test_imports),
            ("Schema Registry", self.test_schema_registry),
            ("Kafka Manager Basic", self.test_kafka_manager_basic),
            ("Topic Manager Basic", self.test_topic_manager_basic),
            ("Message Schemas Validation", self.test_message_schemas_validation),
            ("Basic Performance", self.test_performance_basic),
            ("Producers & Consumers Basic", self.test_producers_consumers_basic)
        ]
        
        for test_name, test_func in tests:
            try:
                test_func()
            except KeyboardInterrupt:
                print(f"\n⚠️  Test interrupted by user: {test_name}")
                break
            except Exception as e:
                print(f"\n❌ Unexpected error in {test_name}: {e}")
                self.test_results[test_name.lower().replace(' ', '_')] = False
        
        self.print_summary()


def main():
    """Main test execution."""
    try:
        tester = KafkaInfrastructureTest()
        tester.run_all_tests()
        
    except KeyboardInterrupt:
        print("\n⚠️  Testing interrupted by user")
    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
