"""
Auto-Idempotency Wrapper System
==============================

Automatically applies idempotency protection to Angel One API methods
without manual intervention. Supports both individual method wrapping
and bulk module wrapping.

Features:
- Automatic method detection and wrapping
- Configurable idempotency settings per method type
- Selective wrapping based on method patterns
- Zero-configuration setup
- Backward compatibility preservation

Usage:
    # Option 1: Auto-wrap entire module
    from angel_one_api.enhancements.auto_idempotency import auto_wrap_module
    auto_wrap_module(current_module, method_patterns=['place_', 'modify_', 'cancel_'])
    
    # Option 2: Auto-wrap specific methods
    from angel_one_api.enhancements.auto_idempotency import auto_idempotency
    
    # Apply to all trading methods
    auto_idempotency.wrap_trading_methods()
    
    # Apply to all account methods  
    auto_idempotency.wrap_account_methods()

Author: HFT Trading System
Created: September 23, 2025
"""

import inspect
import importlib
import sys
from typing import Dict, Any, List, Optional, Callable, Union
from pathlib import Path
import logging

# Import our idempotency system
try:
    from .idempotency_manager import idempotency_wrapper
    IDEMPOTENCY_AVAILABLE = True
except ImportError:
    IDEMPOTENCY_AVAILABLE = False

logger = logging.getLogger(__name__)

class AutoIdempotency:
    """
    Automatic idempotency wrapper system for Angel One API methods.
    
    Provides intelligent, zero-configuration idempotency protection
    for all Angel One API methods based on method patterns and types.
    """
    
    def __init__(self):
        """Initialize auto-idempotency system."""
        self.wrapped_methods = set()
        self.config = self._get_default_config()
        
    def _get_default_config(self) -> Dict[str, Dict[str, Any]]:
        """Get default configuration for different method types."""
        return {
            "trading_methods": {
                "patterns": ["place_", "modify_", "cancel_"],
                "ttl": 300,  # 5 minutes
                "cache_response": True,
                "allow_override": True
            },
            "account_methods": {
                "patterns": ["get_order", "get_position", "get_trade", "get_holding", "get_rms"],
                "ttl": 60,   # 1 minute
                "cache_response": True,
                "allow_override": False
            },
            "market_methods": {
                "patterns": ["get_ltp", "get_quote", "get_candle", "search_"],
                "ttl": 30,   # 30 seconds
                "cache_response": True,
                "allow_override": False
            }
        }
    
    def wrap_method(
        self,
        method: Callable,
        method_type: str = "trading",
        ttl: Optional[int] = None,
        cache_response: bool = True,
        allow_override: bool = False
    ) -> Callable:
        """
        Wrap a single method with idempotency protection.
        
        Args:
            method: Method to wrap
            method_type: Type of method (trading, account, market)
            ttl: Time-to-live for idempotency (seconds)
            cache_response: Whether to cache responses
            allow_override: Allow manual override
            
        Returns:
            Wrapped method with idempotency protection
        """
        if not IDEMPOTENCY_AVAILABLE:
            logger.warning(f"⚠️ Idempotency not available for {method.__name__}")
            return method
        
        if method.__name__ in self.wrapped_methods:
            logger.debug(f"Method {method.__name__} already wrapped")
            return method
        
        # Get configuration
        config = self.config.get(f"{method_type}_methods", self.config["trading_methods"])
        wrapper_ttl = ttl or config["ttl"]
        
        # Apply idempotency wrapper
        wrapped_method = idempotency_wrapper(
            method_type=method_type,
            ttl=wrapper_ttl,
            cache_response=cache_response,
            allow_override=allow_override
        )(method)
        
        self.wrapped_methods.add(method.__name__)
        logger.info(f"✅ Applied idempotency to {method.__name__} ({method_type}, TTL: {wrapper_ttl}s)")
        
        return wrapped_method
    
    def wrap_module_methods(
        self,
        module,
        method_patterns: Optional[List[str]] = None,
        method_type: str = "trading",
        exclude_patterns: Optional[List[str]] = None
    ) -> int:
        """
        Automatically wrap all methods in a module that match patterns.
        
        Args:
            module: Python module to wrap methods in
            method_patterns: List of patterns to match (e.g., ['place_', 'modify_'])
            method_type: Type of methods (trading, account, market)
            exclude_patterns: Patterns to exclude from wrapping
            
        Returns:
            Number of methods wrapped
        """
        if not IDEMPOTENCY_AVAILABLE:
            logger.warning("⚠️ Idempotency not available - skipping module wrapping")
            return 0
        
        if method_patterns is None:
            method_patterns = self.config.get(f"{method_type}_methods", {}).get("patterns", [])
        
        exclude_patterns = exclude_patterns or ["_", "test_"]
        
        wrapped_count = 0
        
        # Get all functions in the module
        for name, obj in inspect.getmembers(module, inspect.isfunction):
            # Skip if already wrapped
            if name in self.wrapped_methods:
                continue
            
            # Skip if matches exclude patterns
            if any(exclude in name for exclude in exclude_patterns):
                continue
            
            # Check if matches any include patterns
            if method_patterns and not any(pattern in name for pattern in method_patterns):
                continue
            
            # Skip private methods
            if name.startswith('_'):
                continue
            
            try:
                # Wrap the method
                wrapped_method = self.wrap_method(obj, method_type)
                
                # Replace in module
                setattr(module, name, wrapped_method)
                wrapped_count += 1
                
            except Exception as e:
                logger.error(f"Failed to wrap {name}: {e}")
        
        logger.info(f"🎯 Wrapped {wrapped_count} methods in {module.__name__}")
        return wrapped_count
    
    def wrap_trading_methods(self) -> int:
        """Automatically wrap all trading methods in the Angel One API."""
        try:
            # Import Angel One methods modules
            from angel_one_api import methods
            
            trading_patterns = ["place_", "modify_", "cancel_"]
            total_wrapped = 0
            
            # Get all method modules
            methods_path = Path(methods.__file__).parent
            for method_file in methods_path.glob("*.py"):
                if method_file.name.startswith('_'):
                    continue
                
                module_name = f"angel_one_api.methods.{method_file.stem}"
                try:
                    module = importlib.import_module(module_name)
                    wrapped = self.wrap_module_methods(
                        module, 
                        method_patterns=trading_patterns,
                        method_type="trading"
                    )
                    total_wrapped += wrapped
                except Exception as e:
                    logger.error(f"Failed to wrap methods in {module_name}: {e}")
            
            logger.info(f"🛡️ Total trading methods wrapped: {total_wrapped}")
            return total_wrapped
            
        except Exception as e:
            logger.error(f"Failed to wrap trading methods: {e}")
            return 0
    
    def wrap_account_methods(self) -> int:
        """Automatically wrap all account-related methods."""
        try:
            from angel_one_api import methods
            
            account_patterns = ["get_order", "get_position", "get_trade", "get_holding", "get_rms"]
            total_wrapped = 0
            
            methods_path = Path(methods.__file__).parent
            for method_file in methods_path.glob("get_*.py"):
                module_name = f"angel_one_api.methods.{method_file.stem}"
                try:
                    module = importlib.import_module(module_name)
                    wrapped = self.wrap_module_methods(
                        module,
                        method_patterns=account_patterns,
                        method_type="account"
                    )
                    total_wrapped += wrapped
                except Exception as e:
                    logger.error(f"Failed to wrap methods in {module_name}: {e}")
            
            logger.info(f"📊 Total account methods wrapped: {total_wrapped}")
            return total_wrapped
            
        except Exception as e:
            logger.error(f"Failed to wrap account methods: {e}")
            return 0
    
    def wrap_market_methods(self) -> int:
        """Automatically wrap all market data methods."""
        try:
            from angel_one_api import methods
            
            market_patterns = ["get_ltp", "get_quote", "get_candle", "search_", "get_market"]
            total_wrapped = 0
            
            methods_path = Path(methods.__file__).parent
            for method_file in methods_path.glob("*.py"):
                if not any(pattern in method_file.name for pattern in market_patterns):
                    continue
                    
                module_name = f"angel_one_api.methods.{method_file.stem}"
                try:
                    module = importlib.import_module(module_name)
                    wrapped = self.wrap_module_methods(
                        module,
                        method_patterns=market_patterns,
                        method_type="market"
                    )
                    total_wrapped += wrapped
                except Exception as e:
                    logger.error(f"Failed to wrap methods in {module_name}: {e}")
            
            logger.info(f"📈 Total market methods wrapped: {total_wrapped}")
            return total_wrapped
            
        except Exception as e:
            logger.error(f"Failed to wrap market methods: {e}")
            return 0
    
    def wrap_all_methods(self) -> Dict[str, int]:
        """Wrap all Angel One API methods with appropriate idempotency settings."""
        results = {
            "trading": self.wrap_trading_methods(),
            "account": self.wrap_account_methods(), 
            "market": self.wrap_market_methods()
        }
        
        total = sum(results.values())
        logger.info(f"🎉 Auto-idempotency complete: {total} methods wrapped")
        
        return results
    
    def get_wrapped_methods(self) -> List[str]:
        """Get list of all wrapped methods."""
        return list(self.wrapped_methods)
    
    def is_method_wrapped(self, method_name: str) -> bool:
        """Check if a method is already wrapped."""
        return method_name in self.wrapped_methods

# Convenience functions for easy usage
def auto_wrap_module(
    module,
    method_patterns: Optional[List[str]] = None,
    method_type: str = "trading",
    exclude_patterns: Optional[List[str]] = None
) -> int:
    """
    Convenience function to auto-wrap all methods in a module.
    
    Args:
        module: Python module to wrap
        method_patterns: Patterns to match (e.g., ['place_', 'modify_'])
        method_type: Type of methods (trading, account, market)
        exclude_patterns: Patterns to exclude
        
    Returns:
        Number of methods wrapped
    """
    auto_idempotency = AutoIdempotency()
    return auto_idempotency.wrap_module_methods(
        module, method_patterns, method_type, exclude_patterns
    )

def auto_wrap_all() -> Dict[str, int]:
    """
    Convenience function to wrap all Angel One API methods.
    
    Returns:
        Dictionary with counts per method type
    """
    auto_idempotency = AutoIdempotency()
    return auto_idempotency.wrap_all_methods()

# Global instance for easy access
auto_idempotency = AutoIdempotency()

# Export commonly used functions
__all__ = [
    "AutoIdempotency",
    "auto_idempotency", 
    "auto_wrap_module",
    "auto_wrap_all"
]
