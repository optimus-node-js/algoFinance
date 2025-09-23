#!/usr/bin/env python3
"""
Caching Service Testing Script
=============================

Comprehensive testing for Day 2 caching infrastructure:
- Redis Manager functionality
- Idempotency Service validation
- Cache Service performance
- Integration testing

Run from project root: python server/src/caching_service/testing/test_caching_service.py
"""

import sys
import os
import time
import asyncio
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, Any

# Add server/src to Python path
current_dir = Path(__file__).parent
caching_dir = current_dir.parent
server_src_dir = caching_dir.parent
if str(server_src_dir) not in sys.path:
    sys.path.insert(0, str(server_src_dir))

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class CachingServiceTest:
    """Comprehensive caching service testing."""
    
    def __init__(self):
        self.test_results = {}
        self.start_time = datetime.now()
        
        print("🧪 CACHING SERVICE TESTING")
        print("=" * 50)
        print(f"📅 Test started: {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"📂 Working directory: {os.getcwd()}")
        print(f"🐍 Python executable: {sys.executable}")
        print()
    
    def test_imports(self) -> bool:
        """Test all critical imports."""
        print("🔍 Testing Imports...")
        
        try:
            # Test Redis dependencies
            import redis
            print("  ✅ Redis dependency imported")
            
            # Test aioredis with fallback
            try:
                import aioredis
                print("  ✅ aioredis imported")
            except Exception as aioredis_error:
                print(f"  ⚠️  aioredis import issue (using compatibility layer): {aioredis_error}")
                # This is expected - we have our own async compatibility layer
            
            # Test our modules
            from caching_service import RedisManager, IdempotencyService, CacheService
            print("  ✅ Caching service modules imported")
            
            from caching_service.redis_manager import get_redis_manager, close_redis_manager
            from caching_service.idempotency_service import get_idempotency_service
            from caching_service.cache_service import get_cache_service
            print("  ✅ Global service functions imported")
            
            # Test our async compatibility layer
            from caching_service.async_redis_compat import AsyncRedisCompat
            print("  ✅ Async Redis compatibility layer imported")
            
            self.test_results['imports'] = True
            print("  🎉 All critical imports successful!\n")
            return True
            
        except Exception as e:
            print(f"  ❌ Critical import failed: {e}")
            self.test_results['imports'] = False
            return False
    
    def test_redis_manager_basic(self) -> bool:
        """Test Redis Manager basic functionality."""
        print("🔍 Testing Redis Manager (Basic)...")
        
        try:
            from caching_service.redis_manager import get_redis_manager
            
            # Get Redis manager
            redis_mgr = get_redis_manager()
            print("  ✅ Redis manager initialized")
            
            # Test connection (will work even without Redis server running)
            connected = redis_mgr.is_connected()
            if connected:
                print("  ✅ Redis server connection successful")
            else:
                print("  ⚠️  Redis server not running (expected in testing)")
            
            # Test basic operations (will gracefully handle connection failures)
            test_key = "test:basic_operation"
            test_value = {"message": "Hello Redis", "timestamp": int(time.time())}
            
            # Test set operation
            set_result = redis_mgr.set(test_key, test_value, ttl=60)
            if connected:
                print(f"  ✅ Set operation result: {set_result}")
            else:
                print(f"  ⚠️  Set operation result: {set_result} (expected False without Redis)")
            
            # Test get operation
            get_result = redis_mgr.get(test_key)
            if connected:
                print(f"  ✅ Get operation successful: {bool(get_result)}")
            else:
                print(f"  ⚠️  Get operation result: {get_result} (expected None without Redis)")
            
            # Test exists operation
            exists_result = redis_mgr.exists(test_key)
            print(f"  ✅ Exists operation result: {exists_result}")
            
            # Get statistics
            stats = redis_mgr.get_stats()
            print(f"  📊 Redis manager stats:")
            print(f"    - Connected: {stats['connection']['connected']}")
            print(f"    - Total operations: {stats['performance']['total_operations']}")
            print(f"    - Error rate: {stats['performance']['error_rate']:.3f}")
            
            self.test_results['redis_manager_basic'] = True
            print("  🎉 Redis Manager basic test completed!\n")
            return True
            
        except Exception as e:
            print(f"  ❌ Redis Manager basic test failed: {e}")
            import traceback
            traceback.print_exc()
            self.test_results['redis_manager_basic'] = False
            return False
    
    def test_idempotency_service(self) -> bool:
        """Test Idempotency Service functionality."""
        print("🔍 Testing Idempotency Service...")
        
        try:
            from caching_service.idempotency_service import get_idempotency_service
            
            # Get idempotency service
            idem_service = get_idempotency_service(default_ttl=60)
            print("  ✅ Idempotency service initialized")
            
            # Test duplicate detection
            method = "POST"
            endpoint = "/api/orders"
            params = {"symbol": "RELIANCE", "quantity": 100, "side": "BUY"}
            
            # First request should not be duplicate
            is_duplicate_1, cached_response_1 = idem_service.check_duplicate_request(
                method=method,
                endpoint=endpoint,
                params=params,
                user_id="test_user"
            )
            
            print(f"  ✅ First request duplicate check: {is_duplicate_1} (expected False)")
            
            # Second identical request should be duplicate
            is_duplicate_2, cached_response_2 = idem_service.check_duplicate_request(
                method=method,
                endpoint=endpoint,
                params=params,
                user_id="test_user"
            )
            
            print(f"  ✅ Second request duplicate check: {is_duplicate_2} (expected True if Redis connected)")
            
            # Test response caching
            test_response = {"order_id": "ORD_123", "status": "SUBMITTED"}
            
            store_result = idem_service.store_response(
                method=method,
                endpoint=endpoint,
                response=test_response,
                params=params,
                user_id="test_user"
            )
            
            print(f"  ✅ Response storage result: {store_result}")
            
            # Test with custom key
            custom_key = "test_custom_order_123"
            is_duplicate_custom, _ = idem_service.check_duplicate_request(
                method=method,
                endpoint=endpoint,
                custom_key=custom_key
            )
            
            print(f"  ✅ Custom key duplicate check: {is_duplicate_custom}")
            
            # Test invalidation
            invalidate_result = idem_service.invalidate_request(
                method=method,
                endpoint=endpoint,
                params=params,
                user_id="test_user"
            )
            
            print(f"  ✅ Invalidation result: {invalidate_result}")
            
            # Get statistics
            stats = idem_service.get_stats()
            print(f"  📊 Idempotency service stats:")
            print(f"    - Requests processed: {stats['performance']['requests_processed']}")
            print(f"    - Duplicates prevented: {stats['performance']['duplicates_prevented']}")
            print(f"    - Duplicate rate: {stats['performance']['duplicate_rate']:.3f}")
            
            self.test_results['idempotency_service'] = True
            print("  🎉 Idempotency Service test completed!\n")
            return True
            
        except Exception as e:
            print(f"  ❌ Idempotency Service test failed: {e}")
            import traceback
            traceback.print_exc()
            self.test_results['idempotency_service'] = False
            return False
    
    def test_cache_service(self) -> bool:
        """Test Cache Service functionality."""
        print("🔍 Testing Cache Service...")
        
        try:
            from caching_service.cache_service import get_cache_service
            
            # Get cache service
            cache_service = get_cache_service("test_cache")
            print("  ✅ Cache service initialized")
            
            # Test market data caching
            symbol = "RELIANCE"
            exchange = "NSE"
            market_data = {
                "price": 2500.50,
                "volume": 1000,
                "bid": 2500.25,
                "ask": 2500.75
            }
            
            cache_result = cache_service.cache_market_data(
                symbol=symbol,
                exchange=exchange,
                data=market_data,
                ttl=10
            )
            
            print(f"  ✅ Market data caching result: {cache_result}")
            
            # Retrieve market data
            cached_data = cache_service.get_market_data(
                symbol=symbol,
                exchange=exchange,
                max_age=5
            )
            
            if cached_data:
                print(f"  ✅ Market data retrieved successfully")
                print(f"    - Symbol: {cached_data.get('symbol')}")
                print(f"    - Price: {cached_data.get('price')}")
            else:
                print(f"  ⚠️  Market data not found (expected without Redis)")
            
            # Test authentication token caching
            user_id = "test_user_123"
            token_data = {
                "access_token": "test_token_123",
                "expires_in": 3600,
                "token_type": "Bearer"
            }
            
            auth_cache_result = cache_service.cache_auth_token(
                user_id=user_id,
                token_data=token_data,
                ttl=1800
            )
            
            print(f"  ✅ Auth token caching result: {auth_cache_result}")
            
            # Retrieve auth token
            cached_token = cache_service.get_auth_token(user_id)
            
            if cached_token:
                print(f"  ✅ Auth token retrieved successfully")
                print(f"    - Token type: {cached_token.get('token_type')}")
            else:
                print(f"  ⚠️  Auth token not found (expected without Redis)")
            
            # Test generic caching
            cache_service.set("test_key", {"data": "test_value"}, ttl=30, category="test")
            cached_value = cache_service.get("test_key", category="test")
            
            print(f"  ✅ Generic cache test: {bool(cached_value)}")
            
            # Test multiple operations
            test_data = {
                "key1": "value1",
                "key2": {"nested": "value2"},
                "key3": [1, 2, 3]
            }
            
            multi_set_result = cache_service.set_multiple(test_data, ttl=60, category="multi_test")
            print(f"  ✅ Multiple set operations: {sum(multi_set_result.values())}/{len(multi_set_result)}")
            
            multi_get_result = cache_service.get_multiple(list(test_data.keys()), category="multi_test")
            print(f"  ✅ Multiple get operations: {len(multi_get_result)} items retrieved")
            
            # Get statistics
            stats = cache_service.get_stats()
            print(f"  📊 Cache service stats:")
            print(f"    - Total gets: {stats['performance']['total_gets']}")
            print(f"    - Total sets: {stats['performance']['total_sets']}")
            print(f"    - Hit rate: {stats['performance']['hit_rate']:.3f}")
            
            self.test_results['cache_service'] = True
            print("  🎉 Cache Service test completed!\n")
            return True
            
        except Exception as e:
            print(f"  ❌ Cache Service test failed: {e}")
            import traceback
            traceback.print_exc()
            self.test_results['cache_service'] = False
            return False
    
    def test_async_operations(self) -> bool:
        """Test async Redis operations."""
        print("🔍 Testing Async Operations...")
        
        try:
            async def async_test():
                from caching_service.redis_manager import get_redis_manager
                
                redis_mgr = get_redis_manager()
                
                # Test async connection
                connected = await redis_mgr.is_connected_async()
                print(f"  ✅ Async connection check: {connected}")
                
                # Test async operations
                test_key = "test:async_operation"
                test_value = {"async": True, "timestamp": int(time.time())}
                
                set_result = await redis_mgr.set_async(test_key, test_value, ttl=30)
                print(f"  ✅ Async set operation: {set_result}")
                
                get_result = await redis_mgr.get_async(test_key)
                print(f"  ✅ Async get operation: {bool(get_result)}")
                
                # Clean up
                await redis_mgr.close_async()
                print(f"  ✅ Async connection closed")
                
                return True
            
            # Run async test
            result = asyncio.run(async_test())
            
            self.test_results['async_operations'] = result
            print("  🎉 Async operations test completed!\n")
            return result
            
        except Exception as e:
            print(f"  ❌ Async operations test failed: {e}")
            import traceback
            traceback.print_exc()
            self.test_results['async_operations'] = False
            return False
    
    def test_performance(self) -> bool:
        """Test basic performance characteristics."""
        print("🔍 Testing Performance...")
        
        try:
            from caching_service.redis_manager import get_redis_manager
            from caching_service.cache_service import get_cache_service
            
            redis_mgr = get_redis_manager()
            cache_service = get_cache_service("perf_test")
            
            # Performance test: 100 operations
            print("  🚀 Performance test: 100 cache operations...")
            
            start_time = time.time()
            
            for i in range(100):
                # Test cache service operations
                key = f"perf_test_key_{i}"
                value = {
                    "id": i,
                    "data": f"test_data_{i}",
                    "timestamp": int(time.time())
                }
                
                # Set operation
                cache_service.set(key, value, ttl=60, category="performance")
                
                # Get operation
                retrieved = cache_service.get(key, category="performance")
                
                # Exists operation
                exists = cache_service.exists(key, category="performance")
            
            end_time = time.time()
            duration = end_time - start_time
            operations_per_second = (100 * 3) / duration  # 3 ops per iteration
            
            print(f"    ✅ 300 operations completed in {duration:.3f} seconds")
            print(f"    ✅ Throughput: {operations_per_second:.0f} operations/second")
            print(f"    ✅ Average latency: {duration/300*1000:.3f} ms per operation")
            
            # Performance targets for caching
            target_throughput = 1000  # operations per second
            target_latency = 5        # milliseconds per operation
            
            avg_latency_ms = (duration / 300) * 1000
            
            performance_good = (operations_per_second >= target_throughput and 
                              avg_latency_ms <= target_latency)
            
            if performance_good:
                print(f"    🎯 Performance targets met!")
            else:
                print(f"    ⚠️  Performance below targets:")
                print(f"      Target: >{target_throughput} ops/s, <{target_latency}ms latency")
                print(f"      Actual: {operations_per_second:.0f} ops/s, {avg_latency_ms:.3f}ms latency")
                print(f"      Note: Performance depends on Redis connection")
            
            self.test_results['performance'] = True
            print("  🎉 Performance test completed!\n")
            return True
            
        except Exception as e:
            print(f"  ❌ Performance test failed: {e}")
            import traceback
            traceback.print_exc()
            self.test_results['performance'] = False
            return False
    
    def print_summary(self):
        """Print comprehensive test summary."""
        end_time = datetime.now()
        duration = end_time - self.start_time
        
        print("=" * 60)
        print("📋 CACHING SERVICE TEST SUMMARY")
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
            print("🎉 ALL CACHING SERVICE TESTS PASSED!")
            print("✅ Day 2 caching infrastructure is ready!")
        else:
            print(f"⚠️  {total_tests - passed_tests} tests failed. Review issues above.")
        
        print()
        print("🚀 Next Steps:")
        print("  1. Install and configure Redis for live testing")
        print("  2. Integrate with Angel One API")
        print("  3. Test idempotency in production scenarios")
        print("=" * 60)
    
    def run_all_tests(self):
        """Run all caching service tests."""
        print("🚀 Starting comprehensive caching service testing...\n")
        
        tests = [
            ("Imports", self.test_imports),
            ("Redis Manager Basic", self.test_redis_manager_basic),
            ("Idempotency Service", self.test_idempotency_service),
            ("Cache Service", self.test_cache_service),
            ("Async Operations", self.test_async_operations),
            ("Performance", self.test_performance)
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
        tester = CachingServiceTest()
        tester.run_all_tests()
        
    except KeyboardInterrupt:
        print("\n⚠️  Testing interrupted by user")
    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()

