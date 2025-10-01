"""
Sentiment Aggregator Service
===========================

Real-time news sentiment analysis for Indian stock markets.
Aggregates news from multiple sources, performs sentiment analysis,
and publishes signals to Kafka for trading strategy consumption.

Components:
- news_apis/: Multi-source news API clients
- data_processing/: News filtering and processing
- nlp_pipeline/: Sentiment analysis and NLP
- signal_publisher.py: Kafka signal publishing
- monitoring.py: Performance monitoring

Features:
- Multi-source news aggregation (RSS + APIs)
- Real-time sentiment analysis
- Company-to-stock mapping
- Kafka integration for live signals
- Redis caching for performance
- Indian market focus
"""

__version__ = "1.0.0"
__author__ = "HFT Trading System"

# Import main components
from .news_apis.api_manager import NewsAPIManager
from .data_processing.news_filter import NewsFilter
from .nlp_pipeline.sentiment_analyzer import SentimentAnalyzer
from .signal_publisher import SentimentSignalPublisher

__all__ = [
    "NewsAPIManager",
    "NewsFilter", 
    "SentimentAnalyzer",
    "SentimentSignalPublisher"
]
