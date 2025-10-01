"""
Company Mapper
=============

Maps company names and mentions in news articles to stock symbols.
Handles Indian stock market companies with multiple aliases and variations.
"""

import json
import logging
import re
from typing import Dict, List, Set, Optional, Tuple
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)

@dataclass
class CompanyMatch:
    """Company match result."""
    symbol: str
    company_name: str
    confidence: float
    matched_text: str
    match_type: str  # exact, alias, fuzzy

class CompanyMapper:
    """Maps company names to stock symbols for Indian markets."""
    
    def __init__(self):
        """Initialize company mapper with Indian companies data."""
        self.companies_data = self._load_companies_data()
        self.symbol_to_company = {}
        self.name_to_symbol = {}
        self.alias_to_symbol = {}
        self.keyword_to_symbols = {}
        
        self._build_mappings()
        logger.info(f"Company mapper initialized with {len(self.companies_data)} companies")
    
    def _load_companies_data(self) -> Dict[str, Dict]:
        """Load Indian companies data."""
        # For now, return hardcoded data. In production, load from JSON file.
        return {
            "RELIANCE": {
                "name": "Reliance Industries Limited",
                "aliases": ["Reliance Industries", "RIL", "Reliance", "Jio"],
                "keywords": ["Mukesh Ambani", "Jio", "petrochemicals", "refining"],
                "sector": "ENERGY",
                "exchange": "NSE"
            },
            "TCS": {
                "name": "Tata Consultancy Services Limited",
                "aliases": ["Tata Consultancy Services", "TCS", "Tata Consultancy"],
                "keywords": ["Tata", "IT services", "consulting"],
                "sector": "IT",
                "exchange": "NSE"
            },
            "INFY": {
                "name": "Infosys Limited",
                "aliases": ["Infosys", "Infosys Limited", "Infosys Technologies"],
                "keywords": ["Narayana Murthy", "Bangalore", "IT services"],
                "sector": "IT",
                "exchange": "NSE"
            },
            "HDFCBANK": {
                "name": "HDFC Bank Limited",
                "aliases": ["HDFC Bank", "HDFC", "Housing Development Finance Corporation Bank"],
                "keywords": ["private bank", "banking"],
                "sector": "BANKING",
                "exchange": "NSE"
            },
            "ICICIBANK": {
                "name": "ICICI Bank Limited",
                "aliases": ["ICICI Bank", "ICICI", "Industrial Credit and Investment Corporation"],
                "keywords": ["private bank", "banking"],
                "sector": "BANKING",
                "exchange": "NSE"
            },
            "HINDUNILVR": {
                "name": "Hindustan Unilever Limited",
                "aliases": ["Hindustan Unilever", "HUL", "Unilever India"],
                "keywords": ["FMCG", "consumer goods", "Unilever"],
                "sector": "FMCG",
                "exchange": "NSE"
            },
            "ITC": {
                "name": "ITC Limited",
                "aliases": ["ITC", "Indian Tobacco Company", "ITC Ltd"],
                "keywords": ["tobacco", "FMCG", "hotels"],
                "sector": "FMCG",
                "exchange": "NSE"
            },
            "SBIN": {
                "name": "State Bank of India",
                "aliases": ["State Bank of India", "SBI", "State Bank"],
                "keywords": ["public sector bank", "government bank"],
                "sector": "BANKING",
                "exchange": "NSE"
            },
            "BHARTIARTL": {
                "name": "Bharti Airtel Limited",
                "aliases": ["Bharti Airtel", "Airtel", "Bharti"],
                "keywords": ["telecom", "mobile", "telecommunications"],
                "sector": "TELECOM",
                "exchange": "NSE"
            },
            "KOTAKBANK": {
                "name": "Kotak Mahindra Bank Limited",
                "aliases": ["Kotak Mahindra Bank", "Kotak Bank", "Kotak"],
                "keywords": ["private bank", "Uday Kotak"],
                "sector": "BANKING",
                "exchange": "NSE"
            },
            "WIPRO": {
                "name": "Wipro Limited",
                "aliases": ["Wipro", "Wipro Technologies", "Wipro Ltd"],
                "keywords": ["IT services", "Azim Premji"],
                "sector": "IT",
                "exchange": "NSE"
            },
            "MARUTI": {
                "name": "Maruti Suzuki India Limited",
                "aliases": ["Maruti Suzuki", "Maruti", "Maruti Udyog"],
                "keywords": ["automobile", "cars", "Suzuki"],
                "sector": "AUTO",
                "exchange": "NSE"
            },
            "HCLTECH": {
                "name": "HCL Technologies Limited",
                "aliases": ["HCL Technologies", "HCL Tech", "HCL"],
                "keywords": ["IT services", "technology"],
                "sector": "IT",
                "exchange": "NSE"
            },
            "AXISBANK": {
                "name": "Axis Bank Limited",
                "aliases": ["Axis Bank", "Axis", "UTI Bank"],
                "keywords": ["private bank", "banking"],
                "sector": "BANKING",
                "exchange": "NSE"
            },
            "LT": {
                "name": "Larsen & Toubro Limited",
                "aliases": ["Larsen & Toubro", "L&T", "Larsen and Toubro"],
                "keywords": ["engineering", "construction", "infrastructure"],
                "sector": "INFRASTRUCTURE",
                "exchange": "NSE"
            },
            "SUNPHARMA": {
                "name": "Sun Pharmaceutical Industries Limited",
                "aliases": ["Sun Pharma", "Sun Pharmaceutical", "Sun Pharmaceuticals"],
                "keywords": ["pharmaceutical", "drugs", "medicine"],
                "sector": "PHARMA",
                "exchange": "NSE"
            },
            "BAJFINANCE": {
                "name": "Bajaj Finance Limited",
                "aliases": ["Bajaj Finance", "Bajaj Finserv"],
                "keywords": ["NBFC", "finance", "Bajaj"],
                "sector": "FINANCIAL_SERVICES",
                "exchange": "NSE"
            },
            "NESTLEIND": {
                "name": "Nestle India Limited",
                "aliases": ["Nestle India", "Nestle", "Nestlé"],
                "keywords": ["FMCG", "food", "beverages"],
                "sector": "FMCG",
                "exchange": "NSE"
            },
            "ASIANPAINT": {
                "name": "Asian Paints Limited",
                "aliases": ["Asian Paints", "Asian Paint"],
                "keywords": ["paints", "coatings", "decorative"],
                "sector": "CHEMICALS",
                "exchange": "NSE"
            },
            "TATAMOTORS": {
                "name": "Tata Motors Limited",
                "aliases": ["Tata Motors", "Tata Motor", "Tata"],
                "keywords": ["automobile", "cars", "commercial vehicles"],
                "sector": "AUTO",
                "exchange": "NSE"
            }
        }
    
    def _build_mappings(self):
        """Build various mapping dictionaries for fast lookup."""
        for symbol, data in self.companies_data.items():
            company_name = data["name"]
            aliases = data.get("aliases", [])
            keywords = data.get("keywords", [])
            
            # Symbol to company mapping
            self.symbol_to_company[symbol] = company_name
            
            # Company name to symbol mapping
            self.name_to_symbol[company_name.lower()] = symbol
            
            # Aliases to symbol mapping
            for alias in aliases:
                self.alias_to_symbol[alias.lower()] = symbol
            
            # Keywords to symbol mapping
            for keyword in keywords:
                if keyword.lower() not in self.keyword_to_symbols:
                    self.keyword_to_symbols[keyword.lower()] = []
                self.keyword_to_symbols[keyword.lower()].append(symbol)
    
    def find_companies_in_text(self, text: str) -> List[CompanyMatch]:
        """Find company mentions in text."""
        if not text:
            return []
        
        text_lower = text.lower()
        matches = []
        
        # 1. Exact company name matches
        for name, symbol in self.name_to_symbol.items():
            if name in text_lower:
                match = CompanyMatch(
                    symbol=symbol,
                    company_name=self.companies_data[symbol]["name"],
                    confidence=1.0,
                    matched_text=name,
                    match_type="exact"
                )
                matches.append(match)
        
        # 2. Alias matches
        for alias, symbol in self.alias_to_symbol.items():
            if alias in text_lower:
                match = CompanyMatch(
                    symbol=symbol,
                    company_name=self.companies_data[symbol]["name"],
                    confidence=0.9,
                    matched_text=alias,
                    match_type="alias"
                )
                matches.append(match)
        
        # 3. Keyword matches
        for keyword, symbols in self.keyword_to_symbols.items():
            if keyword in text_lower:
                for symbol in symbols:
                    match = CompanyMatch(
                        symbol=symbol,
                        company_name=self.companies_data[symbol]["name"],
                        confidence=0.7,
                        matched_text=keyword,
                        match_type="keyword"
                    )
                    matches.append(match)
        
        # Remove duplicates and sort by confidence
        unique_matches = {}
        for match in matches:
            key = match.symbol
            if key not in unique_matches or match.confidence > unique_matches[key].confidence:
                unique_matches[key] = match
        
        result = list(unique_matches.values())
        result.sort(key=lambda x: x.confidence, reverse=True)
        
        return result
    
    def get_company_info(self, symbol: str) -> Optional[Dict]:
        """Get company information by symbol."""
        return self.companies_data.get(symbol)
    
    def get_sector_companies(self, sector: str) -> List[str]:
        """Get all companies in a sector."""
        companies = []
        for symbol, data in self.companies_data.items():
            if data.get("sector", "").upper() == sector.upper():
                companies.append(symbol)
        return companies
    
    def is_financial_keyword(self, text: str) -> bool:
        """Check if text contains financial keywords."""
        financial_keywords = {
            # Market terms
            "stock", "share", "equity", "market", "trading", "investment",
            "bse", "nse", "sensex", "nifty", "index",
            
            # Corporate actions
            "earnings", "results", "dividend", "bonus", "split", "ipo", "fpo",
            "merger", "acquisition", "buyback",
            
            # Financial metrics
            "revenue", "profit", "loss", "growth", "ebitda", "eps",
            "quarterly", "annual", "guidance", "outlook", "forecast",
            
            # Regulatory
            "sebi", "rbi", "regulatory", "compliance", "listing"
        }
        
        text_lower = text.lower()
        return any(keyword in text_lower for keyword in financial_keywords)
    
    def extract_financial_entities(self, text: str) -> Dict[str, List[str]]:
        """Extract financial entities from text."""
        entities = {
            "companies": [],
            "sectors": [],
            "exchanges": [],
            "financial_terms": []
        }
        
        # Find companies
        company_matches = self.find_companies_in_text(text)
        entities["companies"] = [match.symbol for match in company_matches]
        
        # Find sectors
        sectors = ["banking", "it", "pharma", "auto", "fmcg", "energy", "telecom"]
        text_lower = text.lower()
        for sector in sectors:
            if sector in text_lower:
                entities["sectors"].append(sector.upper())
        
        # Find exchanges
        exchanges = ["bse", "nse", "mcx", "ncdex"]
        for exchange in exchanges:
            if exchange in text_lower:
                entities["exchanges"].append(exchange.upper())
        
        # Find financial terms
        financial_terms = ["earnings", "results", "dividend", "ipo", "merger"]
        for term in financial_terms:
            if term in text_lower:
                entities["financial_terms"].append(term)
        
        return entities
    
    def get_mapping_stats(self) -> Dict[str, int]:
        """Get mapping statistics."""
        return {
            "total_companies": len(self.companies_data),
            "name_mappings": len(self.name_to_symbol),
            "alias_mappings": len(self.alias_to_symbol),
            "keyword_mappings": len(self.keyword_to_symbols),
            "sectors": len(set(data.get("sector", "") for data in self.companies_data.values()))
        }

# Example usage and testing
def test_company_mapper():
    """Test company mapper functionality."""
    mapper = CompanyMapper()
    
    print("Company Mapper Test")
    print("=" * 50)
    
    # Test text samples
    test_texts = [
        "Reliance Industries reported strong quarterly earnings",
        "TCS announces new deal with major client",
        "HDFC Bank's profit margins improved significantly",
        "Infosys and Wipro are leading IT companies",
        "State Bank of India launches new digital initiative"
    ]
    
    for text in test_texts:
        print(f"\nText: {text}")
        matches = mapper.find_companies_in_text(text)
        for match in matches:
            print(f"  Found: {match.symbol} ({match.company_name}) - {match.confidence:.2f}")
        
        entities = mapper.extract_financial_entities(text)
        print(f"  Entities: {entities}")
    
    # Get stats
    stats = mapper.get_mapping_stats()
    print(f"\nMapping Stats: {stats}")

if __name__ == "__main__":
    test_company_mapper()
