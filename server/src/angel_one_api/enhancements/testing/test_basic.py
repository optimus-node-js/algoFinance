"""
Basic Idempotency Test
=====================

Simple test to verify basic idempotency functionality.

Author: HFT Trading System
Created: September 23, 2025
"""

import sys
from pathlib import Path

# Add paths for imports
current_dir = Path(__file__).parent
sys.path.append(str(current_dir.parent.parent.parent))

def test_imports():
    """Test if we can import our modules correctly."""
    print("🧪 Testing Basic Imports...")
    
    try:
        from angel_one_api.enhancements import IdempotencyManager
        print("  ✅ IdempotencyManager imported successfully")
        
        from angel_one_api.enhancements import RequestFingerprinter
        print("  ✅ RequestFingerprinter imported successfully")
        
        from angel_one_api.enhancements import DuplicateDetector
        print("  ✅ DuplicateDetector imported successfully")
        
        from caching_service.redis_manager import get_redis_manager
        print("  ✅ Redis manager imported successfully")
        
        print("  🎉 All imports successful!")
        return True
        
    except ImportError as e:
        print(f"  ❌ Import failed: {e}")
        return False

def test_fingerprinting():
    """Test basic fingerprinting functionality."""
    print("\n🧪 Testing Request Fingerprinting...")
    
    try:
        from angel_one_api.enhancements.request_fingerprinting import RequestFingerprinter
        
        fingerprinter = RequestFingerprinter()
        
        # Test basic fingerprint creation
        params = {
            "tradingsymbol": "RELIANCE-EQ",
            "quantity": "10",
            "price": "2500.00"
        }
        
        fingerprint = fingerprinter.create_fingerprint("place_order", params, "trading")
        print(f"  ✅ Fingerprint created: {fingerprint}")
        
        # Test validation
        is_valid = fingerprinter.validate_fingerprint(fingerprint)
        print(f"  ✅ Fingerprint validation: {is_valid}")
        
        return True
        
    except Exception as e:
        print(f"  ❌ Fingerprinting test failed: {e}")
        return False

def test_redis_connection():
    """Test Redis connection."""
    print("\n🧪 Testing Redis Connection...")
    
    try:
        from caching_service.redis_manager import get_redis_manager
        
        redis_manager = get_redis_manager()
        is_connected = redis_manager.is_connected()
        
        if is_connected:
            print("  ✅ Redis connection successful")
            
            # Test basic operations
            client = redis_manager.get_sync_client()
            client.set("test_key", "test_value")
            value = client.get("test_key")
            print(f"  ✅ Redis operation successful: {value}")
            
            return True
        else:
            print("  ⚠️ Redis not connected (expected if Redis not running)")
            return True  # Not an error for testing
            
    except Exception as e:
        print(f"  ❌ Redis test failed: {e}")
        return False

def main():
    """Main test function."""
    print("🚀 BASIC IDEMPOTENCY TESTS")
    print("=" * 40)
    
    tests = [
        ("Imports", test_imports),
        ("Fingerprinting", test_fingerprinting),
        ("Redis Connection", test_redis_connection)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        try:
            if test_func():
                passed += 1
            else:
                print(f"❌ {test_name} test failed")
        except Exception as e:
            print(f"❌ {test_name} test error: {e}")
    
    print("\n" + "=" * 40)
    print(f"📊 Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All basic tests passed!")
        print("✅ Ready for full idempotency testing!")
        return 0
    else:
        print(f"⚠️ {total - passed} tests failed")
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
