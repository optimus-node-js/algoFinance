"""
Advanced Duplicate Detector for Angel One API
============================================

Sophisticated duplicate detection system that prevents duplicate API calls
and trading operations while ensuring data consistency and performance.

Features:
- Multi-level duplicate detection
- Time-window based analysis
- Trading-specific duplicate prevention
- Configurable sensitivity levels
- Performance optimized detection algorithms

Author: HFT Trading System
Created: September 23, 2025
"""

import hashlib
import time
import logging
from typing import Dict, Any, List, Optional, Tuple, Set
from datetime import datetime, timedelta
from enum import Enum
import json

logger = logging.getLogger(__name__)

class DuplicateLevel(Enum):
    """Duplicate detection sensitivity levels."""
    STRICT = "strict"          # Exact parameter match required
    MODERATE = "moderate"      # Minor parameter differences allowed
    LOOSE = "loose"           # Significant parameter differences allowed

class DuplicateType(Enum):
    """Types of duplicates that can be detected."""
    EXACT = "exact"                    # Exact duplicate
    SIMILAR_PARAMS = "similar_params"  # Similar parameters within threshold
    TIME_WINDOW = "time_window"        # Same request within time window
    PATTERN_BASED = "pattern_based"    # Detected based on patterns

class DuplicateDetector:
    """
    Advanced duplicate detection system for Angel One API operations.
    
    Provides sophisticated duplicate detection with configurable sensitivity
    and trading-specific logic to prevent accidental duplicate operations.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize DuplicateDetector with configuration.
        
        Args:
            config: Optional configuration dictionary
        """
        self.config = config or self._get_default_config()
        self.detection_history = {}
        self.similarity_thresholds = self._get_similarity_thresholds()
        
        # Performance metrics
        self.metrics = {
            "total_checks": 0,
            "duplicates_found": 0,
            "false_positives": 0,
            "detection_time": 0.0,
            "start_time": time.time()
        }
        
    def _get_default_config(self) -> Dict[str, Any]:
        """Get default configuration for duplicate detection."""
        return {
            "trading_operations": {
                "level": DuplicateLevel.STRICT,
                "time_window": 300,  # 5 minutes
                "similarity_threshold": 0.95
            },
            "account_operations": {
                "level": DuplicateLevel.MODERATE,
                "time_window": 60,   # 1 minute
                "similarity_threshold": 0.8
            },
            "market_operations": {
                "level": DuplicateLevel.LOOSE,
                "time_window": 30,   # 30 seconds
                "similarity_threshold": 0.7
            }
        }
    
    def _get_similarity_thresholds(self) -> Dict[str, Dict[str, float]]:
        """Get similarity thresholds for different parameter types."""
        return {
            "trading": {
                "quantity": 0.01,    # 1% difference allowed
                "price": 0.005,      # 0.5% difference allowed
                "symbol": 0.0,       # Exact match required
                "side": 0.0,         # Exact match required
                "ordertype": 0.0     # Exact match required
            },
            "account": {
                "method": 0.0,       # Exact match required
                "time_window": 0.1   # 10% time window variance
            },
            "market": {
                "symbol": 0.0,       # Exact match required
                "exchange": 0.0,     # Exact match required
                "time_window": 0.2   # 20% time window variance
            }
        }
    
    async def detect_duplicate(
        self,
        method_name: str,
        params: Dict[str, Any],
        method_type: str = "trading",
        detection_level: Optional[DuplicateLevel] = None
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Detect if the current request is a duplicate.
        
        Args:
            method_name: Name of the Angel One API method
            params: Method parameters
            method_type: Type of method (trading, account, market)
            detection_level: Override detection sensitivity level
            
        Returns:
            Tuple of (is_duplicate, duplicate_info)
        """
        start_time = time.time()
        self.metrics["total_checks"] += 1
        
        try:
            # Get detection configuration
            config_key = f"{method_type}_operations"
            detection_config = self.config.get(config_key, self.config["trading_operations"])
            
            # Use provided level or default
            level = detection_level or detection_config["level"]
            time_window = detection_config["time_window"]
            similarity_threshold = detection_config["similarity_threshold"]
            
            # Perform duplicate detection based on level
            is_duplicate, duplicate_info = self._perform_detection(
                method_name, params, method_type, level, 
                time_window, similarity_threshold
            )
            
            # Update metrics
            detection_time = time.time() - start_time
            self.metrics["detection_time"] += detection_time
            
            if is_duplicate:
                self.metrics["duplicates_found"] += 1
                logger.warning(f"Duplicate detected for {method_name}: {duplicate_info}")
            
            return is_duplicate, duplicate_info
            
        except Exception as e:
            logger.error(f"Error in duplicate detection: {str(e)}")
            return False, {"error": str(e)}
    
    def _perform_detection(
        self,
        method_name: str,
        params: Dict[str, Any],
        method_type: str,
        level: DuplicateLevel,
        time_window: int,
        similarity_threshold: float
    ) -> Tuple[bool, Dict[str, Any]]:
        """Perform the actual duplicate detection logic."""
        
        current_time = time.time()
        
        # Get recent requests for this method
        recent_requests = self._get_recent_requests(
            method_name, method_type, current_time, time_window
        )
        
        if not recent_requests:
            # No recent requests, not a duplicate
            self._store_request(method_name, params, method_type, current_time)
            return False, {}
        
        # Check for duplicates based on detection level
        if level == DuplicateLevel.STRICT:
            return self._detect_strict_duplicate(
                params, recent_requests, method_name, method_type, current_time
            )
        elif level == DuplicateLevel.MODERATE:
            return self._detect_moderate_duplicate(
                params, recent_requests, method_name, method_type, 
                current_time, similarity_threshold
            )
        else:  # LOOSE
            return self._detect_loose_duplicate(
                params, recent_requests, method_name, method_type,
                current_time, similarity_threshold
            )
    
    def _detect_strict_duplicate(
        self,
        params: Dict[str, Any],
        recent_requests: List[Dict[str, Any]],
        method_name: str,
        method_type: str,
        current_time: float
    ) -> Tuple[bool, Dict[str, Any]]:
        """Detect exact duplicates with strict parameter matching."""
        
        # Create normalized parameter hash
        normalized_params = self._normalize_params(params, method_type)
        param_hash = self._create_param_hash(normalized_params)
        
        for recent_request in recent_requests:
            recent_hash = recent_request.get("param_hash")
            if recent_hash == param_hash:
                # Exact duplicate found
                duplicate_info = {
                    "type": DuplicateType.EXACT,
                    "original_timestamp": recent_request["timestamp"],
                    "time_difference": current_time - recent_request["timestamp"],
                    "original_params": recent_request["params"],
                    "similarity_score": 1.0
                }
                return True, duplicate_info
        
        # No exact duplicate found, store this request
        self._store_request(method_name, params, method_type, current_time)
        return False, {}
    
    def _detect_moderate_duplicate(
        self,
        params: Dict[str, Any],
        recent_requests: List[Dict[str, Any]],
        method_name: str,
        method_type: str,
        current_time: float,
        similarity_threshold: float
    ) -> Tuple[bool, Dict[str, Any]]:
        """Detect duplicates with moderate parameter similarity."""
        
        for recent_request in recent_requests:
            similarity_score = self._calculate_similarity(
                params, recent_request["params"], method_type
            )
            
            if similarity_score >= similarity_threshold:
                # Similar duplicate found
                duplicate_info = {
                    "type": DuplicateType.SIMILAR_PARAMS,
                    "original_timestamp": recent_request["timestamp"],
                    "time_difference": current_time - recent_request["timestamp"],
                    "original_params": recent_request["params"],
                    "similarity_score": similarity_score
                }
                return True, duplicate_info
        
        # No similar duplicate found, store this request
        self._store_request(method_name, params, method_type, current_time)
        return False, {}
    
    def _detect_loose_duplicate(
        self,
        params: Dict[str, Any],
        recent_requests: List[Dict[str, Any]],
        method_name: str,
        method_type: str,
        current_time: float,
        similarity_threshold: float
    ) -> Tuple[bool, Dict[str, Any]]:
        """Detect duplicates with loose pattern-based matching."""
        
        # Check for pattern-based duplicates
        for recent_request in recent_requests:
            if self._detect_pattern_duplicate(params, recent_request["params"], method_type):
                duplicate_info = {
                    "type": DuplicateType.PATTERN_BASED,
                    "original_timestamp": recent_request["timestamp"],
                    "time_difference": current_time - recent_request["timestamp"],
                    "original_params": recent_request["params"],
                    "similarity_score": similarity_threshold
                }
                return True, duplicate_info
        
        # No pattern duplicate found, store this request
        self._store_request(method_name, params, method_type, current_time)
        return False, {}
    
    def _get_recent_requests(
        self,
        method_name: str,
        method_type: str,
        current_time: float,
        time_window: int
    ) -> List[Dict[str, Any]]:
        """Get recent requests within the time window."""
        
        history_key = f"{method_type}:{method_name}"
        if history_key not in self.detection_history:
            return []
        
        # Filter requests within time window
        cutoff_time = current_time - time_window
        recent_requests = [
            req for req in self.detection_history[history_key]
            if req["timestamp"] > cutoff_time
        ]
        
        # Clean up old requests
        self.detection_history[history_key] = recent_requests
        
        return recent_requests
    
    def _store_request(
        self,
        method_name: str,
        params: Dict[str, Any],
        method_type: str,
        timestamp: float
    ):
        """Store request in detection history."""
        
        history_key = f"{method_type}:{method_name}"
        if history_key not in self.detection_history:
            self.detection_history[history_key] = []
        
        # Create request record
        normalized_params = self._normalize_params(params, method_type)
        param_hash = self._create_param_hash(normalized_params)
        
        request_record = {
            "timestamp": timestamp,
            "params": params.copy(),
            "normalized_params": normalized_params,
            "param_hash": param_hash
        }
        
        self.detection_history[history_key].append(request_record)
        
        # Limit history size (keep last 100 requests per method)
        if len(self.detection_history[history_key]) > 100:
            self.detection_history[history_key] = self.detection_history[history_key][-100:]
    
    def _normalize_params(
        self,
        params: Dict[str, Any],
        method_type: str
    ) -> Dict[str, Any]:
        """Normalize parameters for consistent comparison."""
        
        normalized = {}
        
        for key, value in params.items():
            # Skip session-specific parameters
            if key in ["timestamp", "requestid", "correlation_id", "session_token"]:
                continue
            
            # Normalize numeric values
            if isinstance(value, (int, float)):
                normalized[key] = float(value)
            elif isinstance(value, str):
                normalized[key] = value.strip().upper()
            else:
                normalized[key] = str(value)
        
        return normalized
    
    def _create_param_hash(self, params: Dict[str, Any]) -> str:
        """Create hash from normalized parameters."""
        param_str = json.dumps(params, sort_keys=True)
        return hashlib.sha256(param_str.encode()).hexdigest()[:16]
    
    def _calculate_similarity(
        self,
        params1: Dict[str, Any],
        params2: Dict[str, Any],
        method_type: str
    ) -> float:
        """Calculate similarity score between two parameter sets."""
        
        # Normalize both parameter sets
        norm_params1 = self._normalize_params(params1, method_type)
        norm_params2 = self._normalize_params(params2, method_type)
        
        # Get all keys
        all_keys = set(norm_params1.keys()) | set(norm_params2.keys())
        
        if not all_keys:
            return 1.0  # Both empty
        
        # Calculate similarity for each parameter
        thresholds = self.similarity_thresholds.get(method_type, {})
        total_score = 0.0
        
        for key in all_keys:
            val1 = norm_params1.get(key)
            val2 = norm_params2.get(key)
            
            if val1 is None or val2 is None:
                # Missing parameter reduces similarity
                total_score += 0.0
            elif val1 == val2:
                # Exact match
                total_score += 1.0
            else:
                # Calculate parameter-specific similarity
                param_similarity = self._calculate_param_similarity(
                    key, val1, val2, thresholds.get(key, 0.1)
                )
                total_score += param_similarity
        
        return total_score / len(all_keys)
    
    def _calculate_param_similarity(
        self,
        param_name: str,
        value1: Any,
        value2: Any,
        threshold: float
    ) -> float:
        """Calculate similarity for a specific parameter."""
        
        try:
            # For numeric parameters
            if isinstance(value1, (int, float)) and isinstance(value2, (int, float)):
                if value1 == 0 and value2 == 0:
                    return 1.0
                elif value1 == 0 or value2 == 0:
                    return 0.0
                else:
                    diff = abs(value1 - value2) / max(abs(value1), abs(value2))
                    return 1.0 if diff <= threshold else 0.0
            
            # For string parameters
            elif isinstance(value1, str) and isinstance(value2, str):
                return 1.0 if value1 == value2 else 0.0
            
            # For other types
            else:
                return 1.0 if str(value1) == str(value2) else 0.0
                
        except Exception:
            return 0.0
    
    def _detect_pattern_duplicate(
        self,
        params1: Dict[str, Any],
        params2: Dict[str, Any],
        method_type: str
    ) -> bool:
        """Detect pattern-based duplicates."""
        
        if method_type == "trading":
            # For trading, check if it's the same symbol and side
            return (
                params1.get("tradingsymbol") == params2.get("tradingsymbol") and
                params1.get("transactiontype") == params2.get("transactiontype")
            )
        elif method_type == "account":
            # For account operations, any recent call is a potential duplicate
            return True
        else:  # market
            # For market data, check symbol
            return (
                params1.get("symboltoken") == params2.get("symboltoken") or
                params1.get("tradingsymbol") == params2.get("tradingsymbol")
            )
    
    def get_detection_metrics(self) -> Dict[str, Any]:
        """Get duplicate detection performance metrics."""
        
        total_checks = self.metrics["total_checks"]
        if total_checks == 0:
            return {"status": "no_data", "message": "No detection checks performed"}
        
        uptime = time.time() - self.metrics["start_time"]
        
        return {
            "total_checks": total_checks,
            "duplicates_found": self.metrics["duplicates_found"],
            "duplicate_rate": round(self.metrics["duplicates_found"] / total_checks * 100, 2),
            "false_positives": self.metrics["false_positives"],
            "average_detection_time": round(
                self.metrics["detection_time"] / total_checks * 1000, 2
            ),  # in milliseconds
            "checks_per_minute": round(total_checks / max(uptime / 60, 1), 1),
            "uptime_minutes": round(uptime / 60, 1)
        }
    
    def clear_detection_history(self, method_name: Optional[str] = None):
        """Clear detection history for debugging or reset."""
        
        if method_name:
            # Clear specific method history
            keys_to_clear = [
                key for key in self.detection_history.keys()
                if key.endswith(f":{method_name}")
            ]
            for key in keys_to_clear:
                del self.detection_history[key]
            
            logger.info(f"Cleared detection history for {method_name}")
        else:
            # Clear all history
            self.detection_history.clear()
            logger.info("Cleared all detection history")
    
    def set_detection_level(
        self,
        method_type: str,
        level: DuplicateLevel,
        time_window: Optional[int] = None,
        similarity_threshold: Optional[float] = None
    ):
        """Dynamically adjust detection settings."""
        
        config_key = f"{method_type}_operations"
        if config_key not in self.config:
            self.config[config_key] = {}
        
        self.config[config_key]["level"] = level
        
        if time_window is not None:
            self.config[config_key]["time_window"] = time_window
            
        if similarity_threshold is not None:
            self.config[config_key]["similarity_threshold"] = similarity_threshold
        
        logger.info(f"Updated detection settings for {method_type}: {level}")
