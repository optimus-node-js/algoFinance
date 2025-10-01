"""
News APIs Package
================

Centralized news collection from multiple sources for Indian financial markets.
"""

from .rss_client import RSSClient, NewsArticle
from .newsapi_client import NewsAPIClient
from .gnews_client import GNewsClient
from .api_manager import NewsAPIManager, NewsAggregationResult

__all__ = [
    "RSSClient",
    "NewsArticle", 
    "NewsAPIClient",
    "GNewsClient",
    "NewsAPIManager",
    "NewsAggregationResult"
]