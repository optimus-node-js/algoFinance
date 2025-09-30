"""
Risk Integration Module
======================

Integration module for connecting strategy engines with the risk service.
Provides real-time risk checks, position management, and compliance validation.
"""

import asyncio
import aiohttp
import logging
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
from enum import Enum
import json

class RiskLevel(Enum):
    """Risk level classifications."""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"

class RiskDecision(Enum):
    """Risk service decisions."""
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    MODIFIED = "MODIFIED"
    PENDING = "PENDING"

class RiskIntegrationClient:
    """
    Client for integrating with the Risk Service.
    
    Provides real-time risk checks, position validation,
    and compliance verification for trading signals.
    """
    
    def __init__(
        self,
        risk_service_url: str = "http://localhost:8003",
        timeout_seconds: int = 5,
        retry_attempts: int = 3
    ):
        """
        Initialize risk integration client.
        
        Args:
            risk_service_url: URL of the risk service
            timeout_seconds: Timeout for risk service calls
            retry_attempts: Number of retry attempts for failed calls
        """
        self.risk_service_url = risk_service_url.rstrip('/')
        self.timeout_seconds = timeout_seconds
        self.retry_attempts = retry_attempts
        
        # Performance tracking
        self.metrics = {
            "total_requests": 0,
            "approved_signals": 0,
            "rejected_signals": 0,
            "modified_signals": 0,
            "timeouts": 0,
            "errors": 0,
            "avg_response_time_ms": 0.0
        }
        
        self.logger = logging.getLogger("risk_integration")
        
    async def validate_signal(self, signal: Dict[str, Any], market_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate a trading signal through the risk service.
        
        Args:
            signal: Trading signal to validate
            market_data: Current market data context
            
        Returns:
            Risk validation result with decision and modifications
        """
        start_time = datetime.now()
        
        try:
            # Prepare risk check request
            risk_request = self._prepare_risk_request(signal, market_data)
            
            # Call risk service
            risk_response = await self._call_risk_service("/risk/validate", risk_request)
            
            # Process response
            result = self._process_risk_response(risk_response, signal)
            
            # Update metrics
            self._update_metrics(start_time, result["decision"])
            
            return result
            
        except Exception as e:
            self.logger.error(f"Risk validation error: {str(e)}")
            self.metrics["errors"] += 1
            
            # Return safe default (reject signal)
            return {
                "decision": RiskDecision.REJECTED.value,
                "reason": f"Risk service error: {str(e)}",
                "original_signal": signal,
                "risk_level": RiskLevel.CRITICAL.value,
                "modifications": {}
            }
            
    async def check_position_limits(self, symbol: str, quantity: int, action: str) -> Dict[str, Any]:
        """
        Check position limits for a trade.
        
        Args:
            symbol: Trading symbol
            quantity: Desired quantity
            action: Trading action (BUY/SELL)
            
        Returns:
            Position limit check result
        """
        try:
            request_data = {
                "symbol": symbol,
                "quantity": quantity,
                "action": action,
                "timestamp": datetime.now().isoformat()
            }
            
            response = await self._call_risk_service("/risk/position-limits", request_data)
            return response
            
        except Exception as e:
            self.logger.error(f"Position limit check error: {str(e)}")
            return {
                "allowed": False,
                "reason": f"Position check error: {str(e)}",
                "max_allowed": 0
            }
            
    async def get_portfolio_risk(self) -> Dict[str, Any]:
        """
        Get current portfolio risk metrics.
        
        Returns:
            Portfolio risk information
        """
        try:
            response = await self._call_risk_service("/risk/portfolio", {})
            return response
            
        except Exception as e:
            self.logger.error(f"Portfolio risk check error: {str(e)}")
            return {
                "total_exposure": 0,
                "var_1d": 0,
                "risk_level": RiskLevel.CRITICAL.value,
                "error": str(e)
            }
            
    async def emergency_stop_check(self) -> bool:
        """
        Check if emergency stop is active.
        
        Returns:
            True if trading should stop, False otherwise
        """
        try:
            response = await self._call_risk_service("/health", {})
            return response.get("kill_switch_on", False)
            
        except Exception as e:
            self.logger.warning(f"Emergency stop check failed: {str(e)}")
            # Err on the side of caution
            return True
            
    def _prepare_risk_request(self, signal: Dict[str, Any], market_data: Dict[str, Any]) -> Dict[str, Any]:
        """Prepare risk service request from signal and market data."""
        return {
            "signal": signal,
            "market_data": market_data,
            "timestamp": datetime.now().isoformat(),
            "strategy_id": signal.get("strategy_id", "unknown"),
            "symbol": signal.get("symbol", ""),
            "action": signal.get("action", ""),
            "quantity": signal.get("quantity", 0),
            "confidence": signal.get("confidence", 0.0),
            "current_price": market_data.get("ltp", market_data.get("price", 0))
        }
        
    async def _call_risk_service(self, endpoint: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Make HTTP call to risk service with retry logic."""
        url = f"{self.risk_service_url}{endpoint}"
        
        for attempt in range(self.retry_attempts):
            try:
                timeout = aiohttp.ClientTimeout(total=self.timeout_seconds)
                
                async with aiohttp.ClientSession(timeout=timeout) as session:
                    async with session.post(url, json=data) as response:
                        if response.status == 200:
                            return await response.json()
                        else:
                            error_text = await response.text()
                            raise Exception(f"Risk service returned {response.status}: {error_text}")
                            
            except asyncio.TimeoutError:
                self.logger.warning(f"Risk service timeout (attempt {attempt + 1}/{self.retry_attempts})")
                self.metrics["timeouts"] += 1
                
                if attempt == self.retry_attempts - 1:
                    raise Exception("Risk service timeout after all retry attempts")
                    
                await asyncio.sleep(0.1 * (attempt + 1))  # Exponential backoff
                
            except Exception as e:
                if attempt == self.retry_attempts - 1:
                    raise e
                    
                self.logger.warning(f"Risk service call failed (attempt {attempt + 1}/{self.retry_attempts}): {str(e)}")
                await asyncio.sleep(0.1 * (attempt + 1))
                
    def _process_risk_response(self, risk_response: Dict[str, Any], original_signal: Dict[str, Any]) -> Dict[str, Any]:
        """Process risk service response and format result."""
        # Default response structure
        result = {
            "decision": RiskDecision.REJECTED.value,
            "reason": "Unknown response format",
            "original_signal": original_signal,
            "modified_signal": None,
            "risk_level": RiskLevel.HIGH.value,
            "risk_score": 0.0,
            "modifications": {},
            "limits_checked": [],
            "timestamp": datetime.now().isoformat()
        }
        
        # Parse risk service response
        if isinstance(risk_response, dict):
            # Extract decision
            if risk_response.get("approved", False):
                result["decision"] = RiskDecision.APPROVED.value
                result["reason"] = risk_response.get("reason", "Risk checks passed")
                result["modified_signal"] = original_signal.copy()
                
            elif risk_response.get("modified", False):
                result["decision"] = RiskDecision.MODIFIED.value
                result["reason"] = risk_response.get("reason", "Signal modified for risk compliance")
                
                # Apply modifications
                modified_signal = original_signal.copy()
                modifications = risk_response.get("modifications", {})
                
                for key, value in modifications.items():
                    if key in modified_signal:
                        modified_signal[key] = value
                        
                result["modified_signal"] = modified_signal
                result["modifications"] = modifications
                
            else:
                result["decision"] = RiskDecision.REJECTED.value
                result["reason"] = risk_response.get("reason", "Risk checks failed")
                
            # Extract additional information
            result["risk_level"] = risk_response.get("risk_level", RiskLevel.MEDIUM.value)
            result["risk_score"] = risk_response.get("risk_score", 0.5)
            result["limits_checked"] = risk_response.get("limits_checked", [])
            
        return result
        
    def _update_metrics(self, start_time: datetime, decision: str) -> None:
        """Update performance metrics."""
        response_time = (datetime.now() - start_time).total_seconds() * 1000
        
        self.metrics["total_requests"] += 1
        self.metrics["avg_response_time_ms"] = (
            self.metrics["avg_response_time_ms"] * 0.9 + response_time * 0.1
        )
        
        if decision == RiskDecision.APPROVED.value:
            self.metrics["approved_signals"] += 1
        elif decision == RiskDecision.REJECTED.value:
            self.metrics["rejected_signals"] += 1
        elif decision == RiskDecision.MODIFIED.value:
            self.metrics["modified_signals"] += 1
            
    def get_metrics(self) -> Dict[str, Any]:
        """Get risk integration metrics."""
        approval_rate = 0.0
        if self.metrics["total_requests"] > 0:
            approval_rate = (
                (self.metrics["approved_signals"] + self.metrics["modified_signals"]) / 
                self.metrics["total_requests"]
            )
            
        return {
            **self.metrics,
            "approval_rate": approval_rate,
            "risk_service_url": self.risk_service_url,
            "timeout_seconds": self.timeout_seconds
        }

class RiskEnhancedStrategyEngine:
    """
    Strategy engine wrapper that integrates risk checks into signal processing.
    
    Automatically validates all signals through the risk service before
    allowing them to proceed to execution.
    """
    
    def __init__(
        self,
        base_strategy_engine,
        risk_client: RiskIntegrationClient,
        config: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize risk-enhanced strategy engine.
        
        Args:
            base_strategy_engine: Base strategy engine to enhance
            risk_client: Risk integration client
            config: Risk enhancement configuration
        """
        self.base_engine = base_strategy_engine
        self.risk_client = risk_client
        self.config = config or self._get_default_config()
        
        # Risk tracking
        self.risk_metrics = {
            "signals_generated": 0,
            "signals_approved": 0,
            "signals_rejected": 0,
            "signals_modified": 0,
            "risk_check_failures": 0
        }
        
        self.logger = logging.getLogger(f"risk_enhanced.{base_strategy_engine.strategy_id}")
        
    def _get_default_config(self) -> Dict[str, Any]:
        """Get default risk enhancement configuration."""
        return {
            "enable_position_checks": True,
            "enable_portfolio_checks": True,
            "enable_emergency_stop": True,
            "max_risk_level": RiskLevel.HIGH.value,
            "bypass_on_risk_failure": False,  # If True, allows signals through on risk service failure
            "log_all_decisions": True
        }
        
    async def process_market_data_with_risk(self, market_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Process market data through strategy engine with risk validation.
        
        Args:
            market_data: Market data to process
            
        Returns:
            Risk-validated signal or None
        """
        try:
            # Check emergency stop first
            if self.config["enable_emergency_stop"]:
                emergency_stop = await self.risk_client.emergency_stop_check()
                if emergency_stop:
                    self.logger.warning("Emergency stop active - blocking all signals")
                    return None
                    
            # Generate signal from base strategy
            signal = self.base_engine.process_market_data(market_data)
            
            if not signal:
                return None
                
            self.risk_metrics["signals_generated"] += 1
            
            # Validate signal through risk service
            risk_result = await self.risk_client.validate_signal(signal, market_data)
            
            # Process risk decision
            decision = risk_result["decision"]
            
            if decision == RiskDecision.APPROVED.value:
                self.risk_metrics["signals_approved"] += 1
                
                if self.config["log_all_decisions"]:
                    self.logger.info(f"Signal approved: {signal['action']} {signal['quantity']} {signal['symbol']}")
                    
                return risk_result["modified_signal"] or signal
                
            elif decision == RiskDecision.MODIFIED.value:
                self.risk_metrics["signals_modified"] += 1
                
                if self.config["log_all_decisions"]:
                    self.logger.info(f"Signal modified: {risk_result['modifications']}")
                    
                return risk_result["modified_signal"]
                
            else:  # REJECTED
                self.risk_metrics["signals_rejected"] += 1
                
                if self.config["log_all_decisions"]:
                    self.logger.warning(f"Signal rejected: {risk_result['reason']}")
                    
                return None
                
        except Exception as e:
            self.logger.error(f"Risk processing error: {str(e)}")
            self.risk_metrics["risk_check_failures"] += 1
            
            # Handle risk service failure
            if self.config["bypass_on_risk_failure"]:
                self.logger.warning("Bypassing risk checks due to service failure")
                return signal
            else:
                self.logger.error("Blocking signal due to risk service failure")
                return None
                
    async def check_portfolio_risk_threshold(self) -> bool:
        """
        Check if portfolio risk is within acceptable thresholds.
        
        Returns:
            True if risk is acceptable, False otherwise
        """
        if not self.config["enable_portfolio_checks"]:
            return True
            
        try:
            portfolio_risk = await self.risk_client.get_portfolio_risk()
            risk_level = portfolio_risk.get("risk_level", RiskLevel.MEDIUM.value)
            
            max_allowed = RiskLevel[self.config["max_risk_level"]]
            current_level = RiskLevel[risk_level]
            
            # Compare risk levels (enum comparison)
            risk_values = {
                RiskLevel.LOW: 1,
                RiskLevel.MEDIUM: 2,
                RiskLevel.HIGH: 3,
                RiskLevel.CRITICAL: 4
            }
            
            return risk_values[current_level] <= risk_values[max_allowed]
            
        except Exception as e:
            self.logger.error(f"Portfolio risk check failed: {str(e)}")
            return False  # Err on the side of caution
            
    def get_risk_metrics(self) -> Dict[str, Any]:
        """Get risk-enhanced strategy metrics."""
        base_metrics = self.base_engine.get_performance_metrics()
        risk_client_metrics = self.risk_client.get_metrics()
        
        approval_rate = 0.0
        if self.risk_metrics["signals_generated"] > 0:
            approved = self.risk_metrics["signals_approved"] + self.risk_metrics["signals_modified"]
            approval_rate = approved / self.risk_metrics["signals_generated"]
            
        return {
            "base_strategy_metrics": base_metrics,
            "risk_metrics": self.risk_metrics,
            "risk_client_metrics": risk_client_metrics,
            "risk_approval_rate": approval_rate,
            "config": self.config
        }
        
    def __getattr__(self, name):
        """Delegate unknown attributes to base strategy engine."""
        return getattr(self.base_engine, name)

