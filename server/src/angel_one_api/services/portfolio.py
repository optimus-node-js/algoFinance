"""
Portfolio Analytics Services
===========================

Business logic for portfolio analysis and performance tracking.
"""

import asyncio
from typing import Dict, Any, List
from datetime import datetime, UTC

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from logger import get_service_logger

logger = get_service_logger("portfolio_service")

class PortfolioAnalytics:
    """Portfolio analysis and metrics calculation."""
    
    def __init__(self):
        logger.info("PortfolioAnalytics service initialized")
    
    async def calculate_portfolio_summary(self, holdings_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate portfolio summary metrics."""
        try:
            if not holdings_data:
                return {
                    "total_value": 0.0,
                    "total_investment": 0.0,
                    "total_pnl": 0.0,
                    "pnl_percentage": 0.0,
                    "holdings_count": 0
                }
            
            total_value = sum(float(holding.get("current_value", 0)) for holding in holdings_data)
            total_investment = sum(float(holding.get("investment_value", 0)) for holding in holdings_data)
            total_pnl = total_value - total_investment
            pnl_percentage = (total_pnl / total_investment * 100) if total_investment > 0 else 0.0
            
            summary = {
                "total_value": round(total_value, 2),
                "total_investment": round(total_investment, 2),
                "total_pnl": round(total_pnl, 2),
                "pnl_percentage": round(pnl_percentage, 2),
                "holdings_count": len(holdings_data),
                "calculated_at": datetime.now(UTC).isoformat()
            }
            
            logger.info("Portfolio summary calculated", {
                "holdings_count": len(holdings_data),
                "total_value": total_value,
                "total_pnl": total_pnl
            })
            
            return summary
            
        except Exception as e:
            logger.error("Failed to calculate portfolio summary", error=e)
            raise
    
    async def analyze_holdings(self, holdings_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Perform detailed holdings analysis."""
        try:
            if not holdings_data:
                return {"analysis": "No holdings to analyze"}
            
            # Calculate top performers
            performers = []
            for holding in holdings_data:
                pnl = float(holding.get("pnl", 0))
                pnl_percent = float(holding.get("pnl_percentage", 0))
                performers.append({
                    "symbol": holding.get("trading_symbol", "Unknown"),
                    "pnl": pnl,
                    "pnl_percentage": pnl_percent
                })
            
            # Sort by PnL percentage
            performers.sort(key=lambda x: x["pnl_percentage"], reverse=True)
            
            analysis = {
                "top_performers": performers[:5],
                "bottom_performers": performers[-5:] if len(performers) > 5 else [],
                "analysis_timestamp": datetime.now(UTC).isoformat()
            }
            
            logger.info("Holdings analysis completed", {
                "holdings_analyzed": len(holdings_data),
                "top_performer": performers[0]["symbol"] if performers else None
            })
            
            return analysis
            
        except Exception as e:
            logger.error("Failed to analyze holdings", error=e)
            raise

class PerformanceTracker:
    """Track portfolio performance over time."""
    
    def __init__(self):
        self.performance_history = []
        logger.info("PerformanceTracker service initialized")
    
    async def track_performance(self, portfolio_data: Dict[str, Any]) -> Dict[str, Any]:
        """Track current portfolio performance."""
        try:
            performance_snapshot = {
                "timestamp": datetime.now(UTC).isoformat(),
                "total_value": portfolio_data.get("total_value", 0),
                "total_pnl": portfolio_data.get("total_pnl", 0),
                "pnl_percentage": portfolio_data.get("pnl_percentage", 0),
                "holdings_count": portfolio_data.get("holdings_count", 0)
            }
            
            # Store in memory (in real implementation, this would go to database)
            self.performance_history.append(performance_snapshot)
            
            # Keep only last 100 records
            if len(self.performance_history) > 100:
                self.performance_history = self.performance_history[-100:]
            
            logger.info("Performance tracked", {
                "total_value": performance_snapshot["total_value"],
                "total_pnl": performance_snapshot["total_pnl"],
                "history_count": len(self.performance_history)
            })
            
            return performance_snapshot
            
        except Exception as e:
            logger.error("Failed to track performance", error=e)
            raise
    
    async def get_performance_history(self, days: int = 30) -> List[Dict[str, Any]]:
        """Get performance history for specified days."""
        try:
            # In real implementation, this would query database
            # For now, return in-memory history
            return self.performance_history[-days:] if self.performance_history else []
            
        except Exception as e:
            logger.error("Failed to get performance history", error=e)
            raise
    
    async def calculate_performance_metrics(self) -> Dict[str, Any]:
        """Calculate performance metrics from history."""
        try:
            if len(self.performance_history) < 2:
                return {
                    "daily_change": 0.0,
                    "weekly_change": 0.0,
                    "monthly_change": 0.0,
                    "message": "Insufficient data for metrics calculation"
                }
            
            latest = self.performance_history[-1]
            previous = self.performance_history[-2] if len(self.performance_history) > 1 else latest
            
            daily_change = latest["total_value"] - previous["total_value"]
            daily_change_percent = (daily_change / previous["total_value"] * 100) if previous["total_value"] > 0 else 0
            
            metrics = {
                "daily_change": round(daily_change, 2),
                "daily_change_percent": round(daily_change_percent, 2),
                "latest_value": latest["total_value"],
                "calculated_at": datetime.now(UTC).isoformat()
            }
            
            logger.info("Performance metrics calculated", metrics)
            
            return metrics
            
        except Exception as e:
            logger.error("Failed to calculate performance metrics", error=e)
            raise
