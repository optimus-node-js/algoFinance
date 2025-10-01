"""
Data Processing Module
=====================

News data processing, filtering, and normalization for sentiment analysis.
Handles company mapping, relevance scoring, and duplicate detection.

Components:
- news_filter.py: Stock-related news filtering
- company_mapper.py: Company name to stock symbol mapping
- relevance_scorer.py: Article relevance scoring
- duplicate_filter.py: Duplicate article detection
- data_normalizer.py: Data standardization
"""

from .news_filter import NewsFilter
from .company_mapper import CompanyMapper
from .relevance_scorer import RelevanceScorer
from .duplicate_filter import DuplicateFilter
from .data_normalizer import DataNormalizer

__all__ = [
    "NewsFilter",
    "CompanyMapper",
    "RelevanceScorer", 
    "DuplicateFilter",
    "DataNormalizer"
]
