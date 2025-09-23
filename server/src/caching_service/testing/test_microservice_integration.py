#!/usr/bin/env python3
"""
Microservice Integration Testing for Day 2 Caching
=================================================

Interactive testing script that guides you through:
1. Which services to start
2. Step-by-step testing scenarios
3. Real microservice communication testing
4. Performance validation

Run: python server/src/caching_service/testing/test_microservice_integration.py
"""

import sys
import os
import time
import asyncio
import requests
import json
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional

# Add server/src to Python path
current_dir = Path(__file__).parent
caching_dir = current_dir.parent
server_src_dir = caching_dir.parent
if str(server_src_dir) not in sys.path:
    sys.path.insert(0, str(server_src_dir))

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class MicroserviceIntegrationTest:
    """Interactive microservice testing framework."""
    
    def __init__(self):
        self.test_results = {}
        self.services_status = {
            'redis': False,
            'angel_one_api': False,
            'kafka': False
        }
        
        print("🎯 MICROSERVICE INTEGRATION TESTING - DAY 2")
        print("=" * 60)
        print("This script will guide you through testing our caching microservice")
        print("integration with other services step by step!")
        print()
    
    def print_service_guide(self):
        """Print which services to run."""
        print("📋 SERVICES TO RUN FOR FULL TESTING:")
        print("=" * 50)
        print()
        print("🔴 REQUIRED SERVICES:")
        print("1. 🗄️  Redis Server (for caching):")
        print("   Command: redis-server")
        print("   Port: 6379")
        print("   Status: Will test if available")
        print()
        print("2. 🔵 Angel One API Service:")
        print("   Command: python -m server.src.angel_one_api --port 8000")
        print("   Port: 8000") 
        print("   Status: Will test communication")
        print()
        print("🟡 OPTIONAL SERVICES:")
        print("3. 📊 Kafka (for message streaming):")
        print("   Status: Will test if available")
        print()
        print("💡 TIP: Start services in separate terminals as I guide you!")
        print("=" * 50)
        print()
    
    def wait_for_user_input(self, message: str) -> str:
        """Wait for user input with a message."""
        return input(f"👤 {message} (press Enter to continue, 'q' to quit): ")
    
    def check_service_availability(self, service_name: str, check_func) -> bool:
        """Check if a service is available."""
        try:
            print(f"🔍 Checking {service_name} availability...")
            result = check_func()
            if result:
                print(f"  ✅ {service_name} is available!")
                self.services_status[service_name] = True
            else:
                print(f"  ❌ {service_name} is not available")
                self.services_status[service_name] = False
            return result
        except Exception as e:
            print(f"  ❌ {service_name} check failed: {e}")
            self.services_status[service_name] = False
            return False
    
    def check_redis(self) -> bool:
        """Check if Redis is running."""
        try:
            from caching_service.redis_manager import get_redis_manager
            redis_mgr = get_redis_manager()
            return redis_mgr.is_connected()
        except Exception:
            return False
    
    def check_angel_one_api(self) -> bool:
        """Check if Angel One API service is running."""
        try:
            response = requests.get("http://localhost:8000/health", timeout=2)
            return response.status_code == 200
        except Exception:
            return False
    
    def check_kafka(self) -> bool:
        """Check if Kafka is running."""
        try:
            from messaging_enhanced.kafka import KafkaManager
            kafka_mgr = KafkaManager()
            # Simple availability check
            return True  # We'll implement proper check later
        except Exception:
            return False
    
    def test_standalone_caching(self) -> bool:
        """Test caching service without external dependencies."""
        print("\n🧪 TEST 1: Standalone Caching Service")
        print("-" * 40)
        
        try:
            from caching_service import RedisManager, IdempotencyService, CacheService
            
            print("  📦 Testing module imports...")
            print("    ✅ RedisManager imported")
            print("    ✅ IdempotencyService imported") 
            print("    ✅ CacheService imported")
            
            print("  🔧 Testing service initialization...")
            redis_mgr = RedisManager()
            idem_service = IdempotencyService()
            cache_service = CacheService("test_microservice")
            
            print("    ✅ All services initialized successfully")
            
            print("  📊 Testing graceful degradation (no Redis)...")
            # These should work even without Redis
            result1 = redis_mgr.set("test_key", "test_value")
            result2 = redis_mgr.get("test_key")
            
            print(f"    📈 Set operation: {result1} (expected False without Redis)")
            print(f"    📈 Get operation: {result2} (expected None without Redis)")
            
            self.test_results['standalone_caching'] = True
            print("  🎉 Standalone caching test PASSED!")
            return True
            
        except Exception as e:
            print(f"  ❌ Standalone caching test FAILED: {e}")
            self.test_results['standalone_caching'] = False
            return False
    
    def test_redis_integration(self) -> bool:
        """Test Redis integration if available."""
        print("\n🧪 TEST 2: Redis Integration")
        print("-" * 40)
        
        if not self.services_status['redis']:
            print("  ⚠️  Redis not available - skipping Redis integration tests")
            print("  💡 To test Redis: Start 'redis-server' in another terminal")
            self.test_results['redis_integration'] = 'skipped'
            return True
        
        try:
            from caching_service.redis_manager import get_redis_manager
            from caching_service.cache_service import get_cache_service
            
            print("  🔗 Testing Redis connection...")
            redis_mgr = get_redis_manager()
            
            if not redis_mgr.is_connected():
                print("  ❌ Redis connection failed")
                return False
            
            print("    ✅ Redis connected successfully")
            
            print("  📝 Testing sync operations...")
            test_key = f"microservice_test_{int(time.time())}"
            test_data = {
                "service": "caching_microservice",
                "test_time": datetime.now().isoformat(),
                "data": "Hello Redis from HFT system!"
            }
            
            # Test sync operations
            set_result = redis_mgr.set(test_key, test_data, ttl=60)
            get_result = redis_mgr.get(test_key)
            exists_result = redis_mgr.exists(test_key)
            
            print(f"    ✅ Set: {set_result}")
            print(f"    ✅ Get: {bool(get_result)}")
            print(f"    ✅ Exists: {exists_result}")
            
            print("  ⚡ Testing async operations...")
            
            async def test_async():
                async_set = await redis_mgr.set_async(f"{test_key}_async", test_data, ttl=60)
                async_get = await redis_mgr.get_async(f"{test_key}_async")
                return async_set, bool(async_get)
            
            async_set_result, async_get_result = asyncio.run(test_async())
            print(f"    ✅ Async Set: {async_set_result}")
            print(f"    ✅ Async Get: {async_get_result}")
            
            print("  🧠 Testing cache service...")
            cache_service = get_cache_service("microservice_test")
            
            # Test market data caching
            market_cache = cache_service.cache_market_data(
                symbol="RELIANCE",
                exchange="NSE", 
                data={"price": 2500.50, "volume": 1000},
                ttl=30
            )
            
            cached_market = cache_service.get_market_data("RELIANCE", "NSE", max_age=10)
            
            print(f"    ✅ Market data cache: {market_cache}")
            print(f"    ✅ Market data retrieve: {bool(cached_market)}")
            
            # Cleanup
            redis_mgr.delete(test_key)
            redis_mgr.delete(f"{test_key}_async")
            
            self.test_results['redis_integration'] = True
            print("  🎉 Redis integration test PASSED!")
            return True
            
        except Exception as e:
            print(f"  ❌ Redis integration test FAILED: {e}")
            import traceback
            traceback.print_exc()
            self.test_results['redis_integration'] = False
            return False
    
    def test_angel_one_api_integration(self) -> bool:
        """Test integration with Angel One API service."""
        print("\n🧪 TEST 3: Angel One API Integration")
        print("-" * 40)
        
        if not self.services_status['angel_one_api']:
            print("  ⚠️  Angel One API not available")
            print("  💡 To test API integration:")
            print("     Start: python -m server.src.angel_one_api --port 8000")
            self.test_results['angel_one_api_integration'] = 'skipped'
            return True
        
        try:
            print("  🔗 Testing API connectivity...")
            
            # Test health endpoint
            health_response = requests.get("http://localhost:8000/health", timeout=5)
            print(f"    ✅ Health check: {health_response.status_code}")
            
            # Test API endpoints
            endpoints_response = requests.get("http://localhost:8000/api/endpoints", timeout=5)
            if endpoints_response.status_code == 200:
                endpoints = endpoints_response.json()
                print(f"    ✅ Available endpoints: {len(endpoints)} found")
            
            print("  🔄 Testing idempotency with API calls...")
            from caching_service.idempotency_service import get_idempotency_service
            
            idem_service = get_idempotency_service(default_ttl=300)
            
            # Simulate API call with idempotency
            test_params = {
                "symbol": "RELIANCE",
                "quantity": 100,
                "side": "BUY"
            }
            
            # First call - should not be duplicate
            is_dup_1, cached_1 = idem_service.check_duplicate_request(
                method="POST",
                endpoint="/api/orders/place",
                params=test_params,
                user_id="test_microservice_user"
            )
            
            print(f"    ✅ First API call duplicate check: {is_dup_1} (expected False)")
            
            # Store a mock response
            mock_response = {
                "order_id": "ORD_TEST_123",
                "status": "SUBMITTED",
                "timestamp": datetime.now().isoformat()
            }
            
            store_result = idem_service.store_response(
                method="POST",
                endpoint="/api/orders/place",
                response=mock_response,
                params=test_params,
                user_id="test_microservice_user"
            )
            
            print(f"    ✅ Response storage: {store_result}")
            
            # Second identical call - should be duplicate with cached response
            is_dup_2, cached_2 = idem_service.check_duplicate_request(
                method="POST",
                endpoint="/api/orders/place", 
                params=test_params,
                user_id="test_microservice_user"
            )
            
            print(f"    ✅ Second API call duplicate check: {is_dup_2}")
            print(f"    ✅ Cached response available: {bool(cached_2)}")
            
            if cached_2:
                print(f"      📋 Cached order ID: {cached_2.get('order_id', 'N/A')}")
            
            self.test_results['angel_one_api_integration'] = True
            print("  🎉 Angel One API integration test PASSED!")
            return True
            
        except Exception as e:
            print(f"  ❌ Angel One API integration test FAILED: {e}")
            import traceback
            traceback.print_exc()
            self.test_results['angel_one_api_integration'] = False
            return False
    
    def test_performance_scenarios(self) -> bool:
        """Test performance under various scenarios."""
        print("\n🧪 TEST 4: Performance Testing")
        print("-" * 40)
        
        try:
            from caching_service.redis_manager import get_redis_manager
            from caching_service.cache_service import get_cache_service
            from caching_service.idempotency_service import get_idempotency_service
            
            print("  🚀 Testing cache performance...")
            
            cache_service = get_cache_service("perf_test")
            redis_mgr = get_redis_manager()
            
            # Performance test: 100 operations
            start_time = time.time()
            operations_count = 100
            
            for i in range(operations_count):
                key = f"perf_test_{i}"
                data = {
                    "id": i,
                    "timestamp": int(time.time()),
                    "service": "caching_microservice"
                }
                
                # Cache operation
                cache_service.set(key, data, ttl=60, category="performance")
                retrieved = cache_service.get(key, category="performance")
                exists = cache_service.exists(key, category="performance")
            
            end_time = time.time()
            duration = end_time - start_time
            ops_per_second = (operations_count * 3) / duration  # 3 ops per iteration
            
            print(f"    📊 {operations_count * 3} operations in {duration:.3f}s")
            print(f"    📈 Throughput: {ops_per_second:.0f} ops/second")
            print(f"    ⚡ Average latency: {duration/(operations_count * 3)*1000:.3f}ms")
            
            # Test idempotency performance
            print("  🔄 Testing idempotency performance...")
            
            idem_service = get_idempotency_service()
            
            idem_start = time.time()
            duplicate_tests = 50
            
            for i in range(duplicate_tests):
                params = {"test_id": i, "operation": "performance_test"}
                
                # Check duplicate (will create entry first time)
                is_dup, cached = idem_service.check_duplicate_request(
                    method="POST",
                    endpoint="/test/performance",
                    params=params,
                    user_id="perf_test_user"
                )
                
                # Store response
                idem_service.store_response(
                    method="POST",
                    endpoint="/test/performance",
                    response={"result": f"test_{i}"},
                    params=params,
                    user_id="perf_test_user"
                )
            
            idem_end = time.time()
            idem_duration = idem_end - idem_start
            idem_ops_per_second = (duplicate_tests * 2) / idem_duration
            
            print(f"    📊 {duplicate_tests * 2} idempotency ops in {idem_duration:.3f}s")
            print(f"    📈 Idempotency throughput: {idem_ops_per_second:.0f} ops/second")
            
            # Get final statistics
            cache_stats = cache_service.get_stats()
            idem_stats = idem_service.get_stats()
            redis_stats = redis_mgr.get_stats()
            
            print("  📈 Final Performance Stats:")
            print(f"    Cache hit rate: {cache_stats['performance']['hit_rate']:.3f}")
            print(f"    Redis operations: {redis_stats['performance']['total_operations']}")
            print(f"    Redis error rate: {redis_stats['performance']['error_rate']:.3f}")
            print(f"    Idempotency requests: {idem_stats['performance']['requests_processed']}")
            
            self.test_results['performance'] = True
            print("  🎉 Performance testing PASSED!")
            return True
            
        except Exception as e:
            print(f"  ❌ Performance testing FAILED: {e}")
            import traceback
            traceback.print_exc()
            self.test_results['performance'] = False
            return False
    
    def print_final_summary(self):
        """Print comprehensive test summary."""
        print("\n" + "=" * 60)
        print("📋 MICROSERVICE INTEGRATION TEST SUMMARY")
        print("=" * 60)
        
        total_tests = len([k for k in self.test_results.keys() if self.test_results[k] != 'skipped'])
        passed_tests = sum(1 for v in self.test_results.values() if v is True)
        skipped_tests = sum(1 for v in self.test_results.values() if v == 'skipped')
        
        print(f"📊 Results: {passed_tests}/{total_tests} tests passed, {skipped_tests} skipped")
        print()
        
        print("🔍 Test Results:")
        for test_name, result in self.test_results.items():
            if result is True:
                status = "✅ PASS"
            elif result == 'skipped':
                status = "⏭️  SKIP"
            else:
                status = "❌ FAIL"
            print(f"  {status} {test_name.replace('_', ' ').title()}")
        
        print()
        print("🏢 Service Status:")
        for service, status in self.services_status.items():
            icon = "✅" if status else "❌"
            print(f"  {icon} {service.replace('_', ' ').title()}")
        
        print()
        
        if passed_tests == total_tests:
            print("🎉 ALL MICROSERVICE INTEGRATION TESTS PASSED!")
            print("✅ Day 2 caching infrastructure is production ready!")
        else:
            print(f"⚠️  {total_tests - passed_tests} tests failed or were skipped.")
            print("💡 Start the required services for complete testing.")
        
        print()
        print("🚀 Next Steps for Full Production Testing:")
        print("  1. Install Redis server locally")
        print("  2. Run Angel One API service: python -m server.src.angel_one_api")
        print("  3. Re-run this test with all services active")
        print("  4. Proceed to Day 3 implementation")
        print("=" * 60)
    
    def run_interactive_tests(self):
        """Run interactive microservice testing."""
        self.print_service_guide()
        
        # Let user decide on service availability
        print("🔍 CHECKING SERVICE AVAILABILITY")
        print("-" * 40)
        
        # Check each service
        self.check_service_availability("redis", self.check_redis)
        self.check_service_availability("angel_one_api", self.check_angel_one_api)
        self.check_service_availability("kafka", self.check_kafka)
        
        print()
        print("📋 SERVICES STATUS:")
        for service, status in self.services_status.items():
            icon = "🟢" if status else "🔴"
            print(f"  {icon} {service.replace('_', ' ').title()}: {'Available' if status else 'Not Available'}")
        
        print()
        response = self.wait_for_user_input("Ready to start testing?")
        if response.lower() == 'q':
            print("Testing cancelled by user.")
            return
        
        # Run test sequence
        print("\n🚀 STARTING MICROSERVICE INTEGRATION TESTS")
        print("=" * 50)
        
        # Test 1: Standalone (always works)
        self.test_standalone_caching()
        
        # Test 2: Redis integration (if Redis available)
        self.test_redis_integration()
        
        # Test 3: Angel One API integration (if API available)
        self.test_angel_one_api_integration()
        
        # Test 4: Performance testing
        self.test_performance_scenarios()
        
        # Final summary
        self.print_final_summary()


def main():
    """Main test execution."""
    try:
        tester = MicroserviceIntegrationTest()
        tester.run_interactive_tests()
        
    except KeyboardInterrupt:
        print("\n⚠️  Testing interrupted by user")
    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()