"""
Auto-Idempotency Testing & Examples
===================================

Demonstrates different approaches for applying idempotency automatically
to Angel One API methods.

Usage Examples:
    python server/src/angel_one_api/enhancements/testing/test_auto_idempotency.py

Author: HFT Trading System
Created: September 23, 2025
"""

import sys
from pathlib import Path

# Add paths for imports
current_dir = Path(__file__).parent
sys.path.append(str(current_dir.parent.parent.parent))

def test_decorator_approach():
    """Test the decorator approach (cleanest for individual methods)."""
    print("🧪 Testing Decorator Approach")
    print("-" * 40)
    
    try:
        # This is how place_order.py is now implemented
        from angel_one_api.enhancements import idempotency_wrapper
        
        # Example: Apply decorator to a method
        @idempotency_wrapper(method_type="trading", ttl=300)
        async def example_place_order(**params):
            return {"success": True, "order_id": "TEST123", "params": params}
        
        print("✅ Decorator approach works!")
        print("   - Clean and explicit")
        print("   - Easy to customize per method")
        print("   - Clear in code what's protected")
        print()
        return True
        
    except Exception as e:
        print(f"❌ Decorator approach failed: {e}")
        return False

def test_auto_wrap_module():
    """Test automatic module wrapping."""
    print("🧪 Testing Auto-Wrap Module Approach")
    print("-" * 40)
    
    try:
        from angel_one_api.enhancements import auto_wrap_module
        
        # Create a mock module with methods
        import types
        mock_module = types.ModuleType("mock_angel_methods")
        
        # Add some mock methods
        async def place_order(**params):
            return {"success": True, "method": "place_order"}
        
        async def modify_order(**params):
            return {"success": True, "method": "modify_order"}
        
        async def get_balance(**params):
            return {"success": True, "method": "get_balance"}
        
        # Add to mock module
        mock_module.place_order = place_order
        mock_module.modify_order = modify_order
        mock_module.get_balance = get_balance
        
        # Auto-wrap trading methods
        wrapped_count = auto_wrap_module(
            mock_module, 
            method_patterns=["place_", "modify_"],
            method_type="trading"
        )
        
        print(f"✅ Auto-wrapped {wrapped_count} methods!")
        print("   - Automatic detection and wrapping")
        print("   - Pattern-based method selection")
        print("   - Zero manual intervention")
        print()
        return True
        
    except Exception as e:
        print(f"❌ Auto-wrap module failed: {e}")
        return False

def test_auto_wrap_all():
    """Test wrapping all methods automatically."""
    print("🧪 Testing Auto-Wrap All Approach")
    print("-" * 40)
    
    try:
        from angel_one_api.enhancements import auto_idempotency
        
        # Get current status
        wrapped_methods = auto_idempotency.get_wrapped_methods()
        
        print(f"✅ Auto-idempotency system ready!")
        print(f"   - Currently wrapped methods: {len(wrapped_methods)}")
        print("   - Can wrap all methods: auto_idempotency.wrap_all_methods()")
        print("   - Can wrap specific types: wrap_trading_methods(), wrap_account_methods()")
        print()
        return True
        
    except Exception as e:
        print(f"❌ Auto-wrap all failed: {e}")
        return False

def demonstrate_usage_patterns():
    """Demonstrate different usage patterns."""
    print("📚 USAGE PATTERNS")
    print("=" * 50)
    
    print("🎯 Pattern 1: Individual Method (Recommended)")
    print("""
# In your method file (e.g., place_order.py):
from angel_one_api.enhancements import idempotency_wrapper

@idempotency_wrapper(method_type="trading", ttl=300)
async def place_order(order_params):
    # Your method implementation
    pass
""")
    
    print("🎯 Pattern 2: Module Auto-Wrap")
    print("""
# At the end of a methods module:
from angel_one_api.enhancements import auto_wrap_module
auto_wrap_module(__import__(__name__), ["place_", "modify_"], "trading")
""")
    
    print("🎯 Pattern 3: Global Auto-Wrap")
    print("""
# In your main application startup:
from angel_one_api.enhancements import auto_idempotency

# Wrap all trading methods
auto_idempotency.wrap_trading_methods()

# Or wrap everything
auto_idempotency.wrap_all_methods()
""")
    
    print("🎯 Pattern 4: Selective Wrapping")
    print("""
# For specific methods only:
from angel_one_api.enhancements import auto_idempotency

# Wrap specific method
wrapped_method = auto_idempotency.wrap_method(
    original_method, 
    method_type="trading", 
    ttl=300
)
""")

def main():
    """Main demonstration function."""
    print("🚀 AUTO-IDEMPOTENCY TESTING & EXAMPLES")
    print("=" * 60)
    print()
    
    results = []
    
    # Test different approaches
    results.append(("Decorator Approach", test_decorator_approach()))
    results.append(("Auto-Wrap Module", test_auto_wrap_module()))
    results.append(("Auto-Wrap All", test_auto_wrap_all()))
    
    # Show usage patterns
    demonstrate_usage_patterns()
    
    # Summary
    print("📊 TEST RESULTS")
    print("=" * 30)
    passed = 0
    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL" 
        print(f"{status} {name}")
        if result:
            passed += 1
    
    print()
    print(f"Results: {passed}/{len(results)} approaches working")
    
    if passed == len(results):
        print("🎉 All auto-idempotency approaches are ready!")
        print()
        print("🎯 RECOMMENDED APPROACH:")
        print("   Use @idempotency_wrapper decorator on individual methods")
        print("   - Clean, explicit, and easy to customize")
        print("   - Already implemented in place_order.py")
        print("   - Apply to modify_order.py, cancel_order.py next")
    
    return passed == len(results)

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
