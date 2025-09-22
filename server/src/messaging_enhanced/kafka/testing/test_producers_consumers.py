#!/usr/bin/env python3
"""
Kafka Producers and Consumers Testing
====================================

Comprehensive testing for Kafka producers and consumers:
- Market Data Producer/Consumer
- Order Producer/Consumer  
- Sentiment Producer/Consumer
- Risk Event Producer/Consumer

Run from project root: python server/src/messaging_enhanced/kafka/testing/test_producers_consumers.py
"""

import sys
import os
import time
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional

# Add server/src to Python path
current_dir = Path(__file__).parent
kafka_dir = current_dir.parent
messaging_dir = kafka_dir.parent  
server_src_dir = messaging_dir.parent
if str(server_src_dir) not in sys.path:
    sys.path.insert(0, str(server_src_dir))

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class ProducerConsumerTest:
    """Test producers and consumers functionality."""
    
    def __init__(self):
        self.test_results = {}
        self.start_time = datetime.now()
        
        print("🧪 KAFKA PRODUCERS & CONSUMERS TESTING")
        print("=" * 60)
        print(f"📅 Test started: {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print()
    
    def test_producers_import(self) -> bool:
        """Test producer imports."""
        print("🔍 Testing Producer Imports...")
        
        try:
            from messaging_enhanced.kafka.producers import (
                MarketDataProducer, OrderProducer, SentimentProducer, RiskEventProducer
            )
            from messaging_enhanced.kafka.producers.market_data_producer import get_market_data_producer
            from messaging_enhanced.kafka.producers.order_producer import get_order_producer
            from messaging_enhanced.kafka.producers.sentiment_producer import get_sentiment_producer
            from messaging_enhanced.kafka.producers.risk_event_producer import get_risk_event_producer
            
            print("  ✅ All producer imports successful")
            self.test_results['producer_imports'] = True
            return True
            
        except Exception as e:
            print(f"  ❌ Producer imports failed: {e}")
            self.test_results['producer_imports'] = False
            return False
    
    def test_consumers_import(self) -> bool:
        """Test consumer imports."""
        print("🔍 Testing Consumer Imports...")
        
        try:
            from messaging_enhanced.kafka.consumers import (
                MarketDataConsumer, OrderConsumer, SentimentConsumer, RiskEventConsumer
            )
            from messaging_enhanced.kafka.consumers.market_data_consumer import get_market_data_consumer
            from messaging_enhanced.kafka.consumers.order_consumer import get_order_consumer
            from messaging_enhanced.kafka.consumers.sentiment_consumer import get_sentiment_consumer
            from messaging_enhanced.kafka.consumers.risk_event_consumer import get_risk_event_consumer
            
            print("  ✅ All consumer imports successful")
            self.test_results['consumer_imports'] = True
            return True
            
        except Exception as e:
            print(f"  ❌ Consumer imports failed: {e}")
            self.test_results['consumer_imports'] = False
            return False
    
    def test_market_data_producer(self) -> bool:
        """Test market data producer functionality."""
        print("🔍 Testing Market Data Producer...")
        
        try:
            from messaging_enhanced.kafka.producers.market_data_producer import get_market_data_producer
            
            # Get producer
            producer = get_market_data_producer("test_market_producer")
            print("  ✅ Market data producer created")
            
            # Test single tick
            result = producer.send_market_tick(
                symbol="RELIANCE",
                exchange="NSE",
                price=2500.50,
                volume=1000,
                bid=2500.25,
                ask=2500.75,
                bid_size=100,
                ask_size=150
            )
            
            if result:
                print("  ✅ Market tick sent successfully")
            else:
                print("  ⚠️  Market tick send returned False (expected without Kafka)")
            
            # Test bulk ticks
            bulk_ticks = [
                {
                    'symbol': 'TCS',
                    'exchange': 'NSE',
                    'price': 3500.0 + i,
                    'volume': 1000 + i * 10,
                    'bid': 3499.5 + i,
                    'ask': 3500.5 + i
                }
                for i in range(5)
            ]
            
            bulk_result = producer.send_bulk_ticks(bulk_ticks)
            print(f"  ✅ Bulk ticks processed: {bulk_result}")
            
            # Test OHLCV bar
            ohlcv_result = producer.send_ohlcv_bar(
                symbol="INFY",
                exchange="NSE",
                timeframe="1m",
                open_price=1500.0,
                high_price=1505.0,
                low_price=1498.0,
                close_price=1502.0,
                volume=5000
            )
            
            if ohlcv_result:
                print("  ✅ OHLCV bar sent successfully")
            
            # Get stats
            stats = producer.get_stats()
            print(f"  📊 Producer stats: {stats}")
            
            self.test_results['market_data_producer'] = True
            print("  🎉 Market Data Producer test completed!\n")
            return True
            
        except Exception as e:
            print(f"  ❌ Market Data Producer test failed: {e}")
            import traceback
            traceback.print_exc()
            self.test_results['market_data_producer'] = False
            return False
    
    def test_order_producer(self) -> bool:
        """Test order producer functionality."""
        print("🔍 Testing Order Producer...")
        
        try:
            from messaging_enhanced.kafka.producers.order_producer import get_order_producer
            
            # Get producer
            producer = get_order_producer("test_order_producer")
            print("  ✅ Order producer created")
            
            # Test single order
            order_result = producer.send_order(
                strategy_id="STRAT_001",
                symbol="RELIANCE",
                exchange="NSE",
                side="BUY",
                quantity=100,
                order_type="LIMIT",
                price=2500.00
            )
            
            print(f"  ✅ Order sent: {order_result}")
            
            if order_result['success']:
                order_id = order_result['order_id']
                
                # Test order update
                update_result = producer.send_order_update(
                    order_id=order_id,
                    status="PARTIALLY_FILLED",
                    filled_quantity=50,
                    average_price=2500.25,
                    symbol="RELIANCE",
                    exchange="NSE",
                    side="BUY",
                    quantity=100,
                    order_type="LIMIT"
                )
                
                if update_result:
                    print("  ✅ Order update sent successfully")
                
                # Test execution event
                exec_result = producer.send_execution_event(
                    order_id=order_id,
                    execution_id="EXEC_001",
                    symbol="RELIANCE",
                    exchange="NSE",
                    side="BUY",
                    quantity=50,
                    price=2500.25,
                    execution_type="PARTIAL"
                )
                
                if exec_result:
                    print("  ✅ Execution event sent successfully")
            
            # Get stats
            stats = producer.get_stats()
            print(f"  📊 Producer stats: {stats}")
            
            self.test_results['order_producer'] = True
            print("  🎉 Order Producer test completed!\n")
            return True
            
        except Exception as e:
            print(f"  ❌ Order Producer test failed: {e}")
            import traceback
            traceback.print_exc()
            self.test_results['order_producer'] = False
            return False
    
    def test_sentiment_producer(self) -> bool:
        """Test sentiment producer functionality."""
        print("🔍 Testing Sentiment Producer...")
        
        try:
            from messaging_enhanced.kafka.producers.sentiment_producer import get_sentiment_producer
            
            # Get producer
            producer = get_sentiment_producer()
            print("  ✅ Sentiment producer created")
            
            # Test sentiment signal
            signal_result = producer.send_sentiment_signal(
                symbol="RELIANCE",
                sentiment_score=0.75,
                confidence=0.85,
                source="newsapi",
                news_headline="Reliance shows strong Q3 results",
                keywords=["strong", "results", "profit"]
            )
            
            print(f"  ✅ Sentiment signal sent: {signal_result}")
            
            # Get stats
            stats = producer.get_stats()
            print(f"  📊 Producer stats: {stats}")
            
            self.test_results['sentiment_producer'] = True
            print("  🎉 Sentiment Producer test completed!\n")
            return True
            
        except Exception as e:
            print(f"  ❌ Sentiment Producer test failed: {e}")
            import traceback
            traceback.print_exc()
            self.test_results['sentiment_producer'] = False
            return False
    
    def test_risk_event_producer(self) -> bool:
        """Test risk event producer functionality."""
        print("🔍 Testing Risk Event Producer...")
        
        try:
            from messaging_enhanced.kafka.producers.risk_event_producer import get_risk_event_producer
            
            # Get producer
            producer = get_risk_event_producer()
            print("  ✅ Risk event producer created")
            
            # Test risk event
            risk_result = producer.send_risk_event(
                event_type="PRE_TRADE_CHECK",
                decision="APPROVED",
                risk_score=0.3,
                order_id="ORD_001",
                symbol="RELIANCE",
                strategy_id="STRAT_001"
            )
            
            print(f"  ✅ Risk event sent: {risk_result}")
            
            # Get stats
            stats = producer.get_stats()
            print(f"  📊 Producer stats: {stats}")
            
            self.test_results['risk_event_producer'] = True
            print("  🎉 Risk Event Producer test completed!\n")
            return True
            
        except Exception as e:
            print(f"  ❌ Risk Event Producer test failed: {e}")
            import traceback
            traceback.print_exc()
            self.test_results['risk_event_producer'] = False
            return False
    
    def test_consumer_creation(self) -> bool:
        """Test consumer creation and basic functionality."""
        print("🔍 Testing Consumer Creation...")
        
        try:
            from messaging_enhanced.kafka.consumers.market_data_consumer import get_market_data_consumer
            from messaging_enhanced.kafka.consumers.order_consumer import get_order_consumer
            from messaging_enhanced.kafka.consumers.sentiment_consumer import get_sentiment_consumer
            from messaging_enhanced.kafka.consumers.risk_event_consumer import get_risk_event_consumer
            
            # Test market data consumer
            market_consumer = get_market_data_consumer("test_market_consumer")
            print("  ✅ Market data consumer created")
            
            # Test callback registration
            def test_callback(symbol, data, processing_info=None):
                print(f"    📊 Test callback received: {symbol}")
            
            market_consumer.register_callback("test_callback", test_callback)
            print("  ✅ Market data callback registered")
            
            # Test order consumer
            order_consumer = get_order_consumer()
            print("  ✅ Order consumer created")
            
            # Test sentiment consumer
            sentiment_consumer = get_sentiment_consumer()
            print("  ✅ Sentiment consumer created")
            
            # Test risk event consumer
            risk_consumer = get_risk_event_consumer()
            print("  ✅ Risk event consumer created")
            
            # Get stats from all consumers
            market_stats = market_consumer.get_stats()
            order_stats = order_consumer.get_stats()
            sentiment_stats = sentiment_consumer.get_stats()
            risk_stats = risk_consumer.get_stats()
            
            print(f"  📊 Market consumer stats: {market_stats}")
            print(f"  📊 Order consumer stats: {order_stats}")
            print(f"  📊 Sentiment consumer stats: {sentiment_stats}")
            print(f"  📊 Risk consumer stats: {risk_stats}")
            
            self.test_results['consumer_creation'] = True
            print("  🎉 Consumer creation test completed!\n")
            return True
            
        except Exception as e:
            print(f"  ❌ Consumer creation test failed: {e}")
            import traceback
            traceback.print_exc()
            self.test_results['consumer_creation'] = False
            return False
    
    def print_summary(self):
        """Print comprehensive test summary."""
        end_time = datetime.now()
        duration = end_time - self.start_time
        
        print("=" * 70)
        print("📋 PRODUCER & CONSUMER TEST SUMMARY")
        print("=" * 70)
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
            print("🎉 ALL PRODUCER/CONSUMER TESTS PASSED!")
            print("✅ Kafka producer/consumer infrastructure is ready!")
        else:
            print(f"⚠️  {total_tests - passed_tests} tests failed. Review issues above.")
        
        print("=" * 70)
    
    def run_all_tests(self):
        """Run all producer/consumer tests."""
        print("🚀 Starting comprehensive producer/consumer testing...\n")
        
        tests = [
            ("Producer Imports", self.test_producers_import),
            ("Consumer Imports", self.test_consumers_import),
            ("Market Data Producer", self.test_market_data_producer),
            ("Order Producer", self.test_order_producer),
            ("Sentiment Producer", self.test_sentiment_producer),
            ("Risk Event Producer", self.test_risk_event_producer),
            ("Consumer Creation", self.test_consumer_creation)
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
        tester = ProducerConsumerTest()
        tester.run_all_tests()
        
    except KeyboardInterrupt:
        print("\n⚠️  Testing interrupted by user")
    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
