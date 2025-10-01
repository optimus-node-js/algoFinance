"""
Stock Integration Module
=======================

Advanced stock market data integration for Indian markets (NSE/BSE).
Provides company mapping, stock data fetching, and sector classification.

Components:
- Enhanced Company Mapper: Advanced company-to-symbol mapping
- Stock Data Fetcher: Real-time NSE/BSE data integration  
- Fuzzy Matcher: Handle company name variations
- Sector Classifier: Industry classification system
- Market Data Validator: Data validation and quality checks

Data Sources:
- nsepy: NSE official data
- indstocks: Comprehensive Indian market data
- yfinance: Cross-validation and international data
"""

from .enhanced_company_mapper import EnhancedCompanyMapper
from .stock_data_fetcher import StockDataFetcher
from .fuzzy_matcher import FuzzyMatcher
from .sector_classifier import SectorClassifier

__all__ = [
    "EnhancedCompanyMapper",
    "StockDataFetcher", 
    "FuzzyMatcher",
    "SectorClassifier"
]
