"""
Request Fingerprinting System for Angel One API
==============================================

Advanced request fingerprinting system that creates unique identifiers
for API requests to enable accurate duplicate detection and caching.

Features:
- Method-specific fingerprinting strategies
- Time-window based grouping for caching
- Configurable parameter inclusion/exclusion
- Hash collision prevention
- Performance optimized fingerprint generation

Author: HFT Trading System
Created: September 23, 2025
"""

import hashlib
import json
import time
from typing import Dict, Any, List, Optional, Set
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class RequestFingerprinter:
    """
    Advanced request fingerprinting for Angel One API methods.
    
    Creates unique, deterministic fingerprints for API requests while
    intelligently handling time-sensitive parameters and caching strategies.
    """
    
    def __init__(self):
        """Initialize RequestFingerprinter with method configurations."""
        self.method_configs = self._get_method_configurations()
        self.excluded_params = self._get_excluded_parameters()
        
    def _get_method_configurations(self) -> Dict[str, Dict[str, Any]]:
        """Get fingerprinting configuration for each method type."""
        return {
            "trading": {
                "critical_params": [
                    "tradingsymbol", "symboltoken", "quantity", "price",
                    "transactiontype", "ordertype", "producttype", "exchange"
                ],
                "time_sensitive": False,
                "time_window": None,
                "ttl": 300  # 5 minutes
            },
            "account": {
                "critical_params": ["method_name"],
                "time_sensitive": True,
                "time_window": 60,  # 1 minute windows
                "ttl": 60
            },
            "market": {
                "critical_params": ["symboltoken", "tradingsymbol", "exchange"],
                "time_sensitive": True,
                "time_window": 30,  # 30 second windows
                "ttl": 30
            }
        }
    
    def _get_excluded_parameters(self) -> Set[str]:
        """Get parameters to exclude from fingerprinting."""
        return {
            # Auto-generated fields
            "timestamp", "requestid", "correlation_id",
            # Session-specific fields
            "session_token", "auth_token", "jwtToken",
            # Dynamic fields
            "client_local_ip", "client_public_ip",
            "mac_address", "version", "source"
        }
    
    def create_fingerprint(
        self,
        method_name: str,
        params: Dict[str, Any],
        method_type: str = "trading"
    ) -> str:
        """
        Create unique fingerprint for a request.
        
        Args:
            method_name: Name of the Angel One API method
            params: Request parameters
            method_type: Type of method (trading, account, market)
            
        Returns:
            Unique fingerprint string
        """
        try:
            config = self.method_configs.get(method_type, self.method_configs["trading"])
            
            # Create fingerprint data based on method type
            if method_type == "trading":
                fingerprint_data = self._create_trading_fingerprint(
                    method_name, params, config
                )
            elif method_type == "account":
                fingerprint_data = self._create_account_fingerprint(
                    method_name, params, config
                )
            else:  # market
                fingerprint_data = self._create_market_fingerprint(
                    method_name, params, config
                )
            
            # Generate hash
            fingerprint_str = json.dumps(fingerprint_data, sort_keys=True)
            fingerprint_hash = hashlib.sha256(fingerprint_str.encode()).hexdigest()[:16]
            
            # Create full fingerprint with prefix
            full_fingerprint = f"{method_type}:{method_name}:{fingerprint_hash}"
            
            logger.debug(f"Created fingerprint: {full_fingerprint}")
            return full_fingerprint
            
        except Exception as e:
            logger.error(f"Failed to create fingerprint: {str(e)}")
            # Fallback to simple method-based fingerprint
            return f"{method_type}:{method_name}:{int(time.time())}"
    
    def _create_trading_fingerprint(
        self,
        method_name: str,
        params: Dict[str, Any],
        config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Create fingerprint for trading operations."""
        fingerprint_data = {"method": method_name}
        
        # Add critical parameters for trading
        critical_params = config["critical_params"]
        for param in critical_params:
            if param in params:
                fingerprint_data[param] = str(params[param])
        
        # Special handling for specific trading methods
        if method_name == "place_order":
            fingerprint_data.update(self._get_order_specific_params(params))
        elif method_name == "modify_order":
            fingerprint_data.update(self._get_modify_specific_params(params))
        elif method_name == "cancel_order":
            fingerprint_data.update(self._get_cancel_specific_params(params))
        
        return fingerprint_data
    
    def _create_account_fingerprint(
        self,
        method_name: str,
        params: Dict[str, Any],
        config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Create fingerprint for account operations."""
        fingerprint_data = {"method": method_name}
        
        # Add time window for caching
        if config["time_sensitive"]:
            current_time = int(time.time())
            time_window = config["time_window"]
            fingerprint_data["time_window"] = current_time // time_window
        
        # Add any specific parameters
        specific_params = self._get_account_specific_params(method_name, params)
        fingerprint_data.update(specific_params)
        
        return fingerprint_data
    
    def _create_market_fingerprint(
        self,
        method_name: str,
        params: Dict[str, Any],
        config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Create fingerprint for market data operations."""
        fingerprint_data = {"method": method_name}
        
        # Add critical parameters
        critical_params = config["critical_params"]
        for param in critical_params:
            if param in params:
                fingerprint_data[param] = str(params[param])
        
        # Add time window for caching
        if config["time_sensitive"]:
            current_time = int(time.time())
            time_window = config["time_window"]
            fingerprint_data["time_window"] = current_time // time_window
        
        return fingerprint_data
    
    def _get_order_specific_params(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Get order-specific parameters for place_order fingerprinting."""
        order_params = {}
        
        # Essential order parameters
        essential_fields = [
            "variety", "duration", "disclosedquantity",
            "squareoff", "stoploss", "triggerprice"
        ]
        
        for field in essential_fields:
            if field in params and params[field] is not None:
                order_params[field] = str(params[field])
        
        return order_params
    
    def _get_modify_specific_params(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Get modify-specific parameters for modify_order fingerprinting."""
        modify_params = {}
        
        # Essential modify parameters
        essential_fields = ["orderid", "newprice", "newquantity", "newtrigger"]
        
        for field in essential_fields:
            if field in params and params[field] is not None:
                modify_params[field] = str(params[field])
        
        return modify_params
    
    def _get_cancel_specific_params(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Get cancel-specific parameters for cancel_order fingerprinting."""
        cancel_params = {}
        
        # Essential cancel parameters
        if "orderid" in params:
            cancel_params["orderid"] = str(params["orderid"])
        if "variety" in params:
            cancel_params["variety"] = str(params["variety"])
        
        return cancel_params
    
    def _get_account_specific_params(
        self,
        method_name: str,
        params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Get account-specific parameters based on method."""
        specific_params = {}
        
        # Method-specific parameters
        if method_name in ["get_order_book", "get_trade_book"]:
            # No additional parameters needed - time window is sufficient
            pass
        elif method_name in ["get_position", "get_holding"]:
            # Position type might be relevant
            if "product" in params:
                specific_params["product"] = str(params["product"])
        elif method_name == "get_rms":
            # RMS calls can be grouped by time window only
            pass
        
        return specific_params
    
    def create_custom_fingerprint(
        self,
        method_name: str,
        custom_params: Dict[str, Any],
        prefix: str = "custom"
    ) -> str:
        """
        Create custom fingerprint with specific parameters.
        
        Args:
            method_name: Name of the method
            custom_params: Custom parameters to include
            prefix: Prefix for the fingerprint
            
        Returns:
            Custom fingerprint string
        """
        try:
            # Filter out excluded parameters
            filtered_params = {
                k: v for k, v in custom_params.items()
                if k not in self.excluded_params
            }
            
            fingerprint_data = {
                "method": method_name,
                "params": filtered_params
            }
            
            fingerprint_str = json.dumps(fingerprint_data, sort_keys=True)
            fingerprint_hash = hashlib.sha256(fingerprint_str.encode()).hexdigest()[:16]
            
            return f"{prefix}:{method_name}:{fingerprint_hash}"
            
        except Exception as e:
            logger.error(f"Failed to create custom fingerprint: {str(e)}")
            return f"{prefix}:{method_name}:{int(time.time())}"
    
    def validate_fingerprint(self, fingerprint: str) -> bool:
        """
        Validate fingerprint format.
        
        Args:
            fingerprint: Fingerprint to validate
            
        Returns:
            True if valid format
        """
        try:
            parts = fingerprint.split(":")
            return len(parts) >= 3 and len(parts[-1]) == 16
        except:
            return False
    
    def extract_method_info(self, fingerprint: str) -> Dict[str, str]:
        """
        Extract method information from fingerprint.
        
        Args:
            fingerprint: Fingerprint to extract from
            
        Returns:
            Dictionary with method information
        """
        try:
            parts = fingerprint.split(":")
            if len(parts) >= 3:
                return {
                    "method_type": parts[0],
                    "method_name": parts[1],
                    "hash": parts[2]
                }
        except:
            pass
        
        return {
            "method_type": "unknown",
            "method_name": "unknown", 
            "hash": "unknown"
        }
    
    def get_fingerprint_ttl(self, fingerprint: str) -> int:
        """
        Get appropriate TTL for a fingerprint based on method type.
        
        Args:
            fingerprint: Fingerprint to get TTL for
            
        Returns:
            TTL in seconds
        """
        method_info = self.extract_method_info(fingerprint)
        method_type = method_info["method_type"]
        
        config = self.method_configs.get(method_type, self.method_configs["trading"])
        return config["ttl"]
