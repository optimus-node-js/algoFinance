"""
Sentiment Aggregator Configuration
=================================

Centralized configuration management for the sentiment aggregator service.
Loads settings from the dedicated .env file and provides typed configuration.
"""

import os
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv

# Load environment variables from dedicated .env file
env_path = Path(__file__).parent / ".env"
load_dotenv(dotenv_path=env_path)

logger = logging.getLogger(__name__)

class SentimentConfig:
    """Configuration class for sentiment aggregator service."""
    
    def __init__(self):
        """Initialize configuration from environment variables."""
        self._validate_required_vars()
        
    def _validate_required_vars(self):
        """Validate that required environment variables are set."""
        required_vars = [
            "RSS_FEEDS_ENABLED",
            "NEWS_PROCESSING_ENABLED", 
            "KAFKA_NEWS_TOPIC",
            "KAFKA_SENTIMENT_TOPIC"
        ]
        
        missing_vars = []
        for var in required_vars:
            if not os.getenv(var):
                missing_vars.append(var)
                
        if missing_vars:
            logger.warning(f"Missing environment variables: {missing_vars}")
    
    # ==========================================
    # NEWS APIs CONFIGURATION
    # ==========================================
    
    @property
    def newsapi_key(self) -> Optional[str]:
        return os.getenv("NEWSAPI_KEY")
    
    @property
    def newsapi_url(self) -> str:
        return os.getenv("NEWSAPI_URL", "https://newsapi.org/v2/everything")
    
    @property
    def newsapi_rate_limit(self) -> int:
        return int(os.getenv("NEWSAPI_RATE_LIMIT", "2000"))
    
    @property
    def newsapi_enabled(self) -> bool:
        return os.getenv("NEWSAPI_ENABLED", "true").lower() == "true"
    
    @property
    def gnews_key(self) -> Optional[str]:
        return os.getenv("GNEWS_API_KEY")
    
    @property
    def gnews_url(self) -> str:
        return os.getenv("GNEWS_URL", "https://gnews.io/api/v4/search")
    
    @property
    def gnews_rate_limit(self) -> int:
        return int(os.getenv("GNEWS_RATE_LIMIT", "100"))
    
    @property
    def gnews_enabled(self) -> bool:
        return os.getenv("GNEWS_ENABLED", "true").lower() == "true"
    
    # ==========================================
    # RSS FEEDS CONFIGURATION
    # ==========================================
    
    @property
    def rss_feeds_enabled(self) -> bool:
        return os.getenv("RSS_FEEDS_ENABLED", "true").lower() == "true"
    
    @property
    def rss_update_interval(self) -> int:
        return int(os.getenv("RSS_UPDATE_INTERVAL", "300"))
    
    @property
    def rss_max_articles_per_feed(self) -> int:
        return int(os.getenv("RSS_MAX_ARTICLES_PER_FEED", "50"))
    
    @property
    def rss_timeout(self) -> int:
        return int(os.getenv("RSS_TIMEOUT", "30"))
    
    @property
    def rss_feeds(self) -> Dict[str, List[str]]:
        """Get all RSS feed URLs organized by source."""
        return {
            "economic_times": [
                os.getenv("ECONOMIC_TIMES_MARKETS_RSS", ""),
                os.getenv("ECONOMIC_TIMES_STOCKS_RSS", ""),
                os.getenv("ECONOMIC_TIMES_EARNINGS_RSS", "")
            ],
            "moneycontrol": [
                os.getenv("MONEYCONTROL_BUSINESS_RSS", ""),
                os.getenv("MONEYCONTROL_RESULTS_RSS", ""),
                os.getenv("MONEYCONTROL_MARKETS_RSS", "")
            ],
            "business_standard": [
                os.getenv("BUSINESS_STANDARD_MARKETS_RSS", ""),
                os.getenv("BUSINESS_STANDARD_FINANCE_RSS", ""),
                os.getenv("BUSINESS_STANDARD_COMPANIES_RSS", "")
            ],
            "mint": [
                os.getenv("MINT_MARKETS_RSS", ""),
                os.getenv("MINT_COMPANIES_RSS", ""),
                os.getenv("MINT_MONEY_RSS", "")
            ],
            "financial_express": [
                os.getenv("FINANCIAL_EXPRESS_MARKET_RSS", ""),
                os.getenv("FINANCIAL_EXPRESS_INDUSTRY_RSS", "")
            ],
            "hindu_businessline": [
                os.getenv("HINDU_BUSINESSLINE_MARKETS_RSS", ""),
                os.getenv("HINDU_BUSINESSLINE_COMPANIES_RSS", "")
            ]
        }
    
    # ==========================================
    # PROCESSING CONFIGURATION
    # ==========================================
    
    @property
    def news_processing_enabled(self) -> bool:
        return os.getenv("NEWS_PROCESSING_ENABLED", "true").lower() == "true"
    
    @property
    def news_relevance_threshold(self) -> float:
        return float(os.getenv("NEWS_RELEVANCE_THRESHOLD", "0.7"))
    
    @property
    def news_sentiment_threshold(self) -> float:
        return float(os.getenv("NEWS_SENTIMENT_THRESHOLD", "0.6"))
    
    @property
    def news_confidence_threshold(self) -> float:
        return float(os.getenv("NEWS_CONFIDENCE_THRESHOLD", "0.5"))
    
    @property
    def news_cache_ttl(self) -> int:
        return int(os.getenv("NEWS_CACHE_TTL", "3600"))
    
    @property
    def news_batch_size(self) -> int:
        return int(os.getenv("NEWS_BATCH_SIZE", "100"))
    
    @property
    def max_articles_per_hour(self) -> int:
        return int(os.getenv("NEWS_MAX_ARTICLES_PER_HOUR", "1000"))
    
    # ==========================================
    # MARKET CONFIGURATION
    # ==========================================
    
    @property
    def market_open_time(self) -> str:
        return os.getenv("MARKET_OPEN_TIME", "09:15")
    
    @property
    def market_close_time(self) -> str:
        return os.getenv("MARKET_CLOSE_TIME", "15:30")
    
    @property
    def market_timezone(self) -> str:
        return os.getenv("MARKET_TIMEZONE", "Asia/Kolkata")
    
    @property
    def primary_exchange(self) -> str:
        return os.getenv("PRIMARY_EXCHANGE", "NSE")
    
    @property
    def secondary_exchange(self) -> str:
        return os.getenv("SECONDARY_EXCHANGE", "BSE")
    
    @property
    def base_currency(self) -> str:
        return os.getenv("BASE_CURRENCY", "INR")
    
    # ==========================================
    # KAFKA CONFIGURATION
    # ==========================================
    
    @property
    def kafka_news_topic(self) -> str:
        return os.getenv("KAFKA_NEWS_TOPIC", "hft-news-articles")
    
    @property
    def kafka_sentiment_topic(self) -> str:
        return os.getenv("KAFKA_SENTIMENT_TOPIC", "hft-sentiment-signals")
    
    @property
    def kafka_company_news_topic(self) -> str:
        return os.getenv("KAFKA_COMPANY_NEWS_TOPIC", "hft-company-news")
    
    @property
    def kafka_sector_news_topic(self) -> str:
        return os.getenv("KAFKA_SECTOR_NEWS_TOPIC", "hft-sector-news")
    
    @property
    def kafka_producer_config(self) -> Dict[str, Any]:
        return {
            "batch_size": int(os.getenv("KAFKA_PRODUCER_BATCH_SIZE", "16384")),
            "linger_ms": int(os.getenv("KAFKA_PRODUCER_LINGER_MS", "10")),
            "compression_type": os.getenv("KAFKA_PRODUCER_COMPRESSION_TYPE", "snappy"),
            "retries": int(os.getenv("KAFKA_PRODUCER_RETRIES", "3"))
        }
    
    # ==========================================
    # SENTIMENT ANALYSIS CONFIGURATION
    # ==========================================
    
    @property
    def sentiment_model(self) -> str:
        return os.getenv("SENTIMENT_MODEL", "vader")
    
    @property
    def positive_sentiment_threshold(self) -> float:
        return float(os.getenv("POSITIVE_SENTIMENT_THRESHOLD", "0.1"))
    
    @property
    def negative_sentiment_threshold(self) -> float:
        return float(os.getenv("NEGATIVE_SENTIMENT_THRESHOLD", "-0.1"))
    
    @property
    def neutral_sentiment_range(self) -> float:
        return float(os.getenv("NEUTRAL_SENTIMENT_RANGE", "0.1"))
    
    @property
    def sentiment_confidence_min(self) -> float:
        return float(os.getenv("SENTIMENT_CONFIDENCE_MIN", "0.5"))
    
    # ==========================================
    # CACHING CONFIGURATION
    # ==========================================
    
    @property
    def redis_cache_enabled(self) -> bool:
        return os.getenv("REDIS_CACHE_ENABLED", "true").lower() == "true"
    
    @property
    def redis_host(self) -> str:
        return os.getenv("REDIS_HOST", "localhost")
    
    @property
    def redis_port(self) -> int:
        return int(os.getenv("REDIS_PORT", "6379"))
    
    @property
    def redis_db(self) -> int:
        return int(os.getenv("REDIS_DB", "2"))
    
    @property
    def redis_password(self) -> Optional[str]:
        password = os.getenv("REDIS_PASSWORD")
        return password if password else None
    
    @property
    def cache_prefix(self) -> str:
        return os.getenv("CACHE_PREFIX", "sentiment_aggregator")
    
    # ==========================================
    # LOGGING CONFIGURATION
    # ==========================================
    
    @property
    def log_level(self) -> str:
        return os.getenv("LOG_LEVEL", "INFO")
    
    @property
    def log_file(self) -> str:
        return os.getenv("LOG_FILE", "logs/sentiment_aggregator.log")
    
    @property
    def debug_mode(self) -> bool:
        return os.getenv("DEBUG_MODE", "false").lower() == "true"
    
    @property
    def monitoring_enabled(self) -> bool:
        return os.getenv("MONITORING_ENABLED", "true").lower() == "true"
    
    # ==========================================
    # FEATURE FLAGS
    # ==========================================
    
    @property
    def parallel_processing_enabled(self) -> bool:
        return os.getenv("PARALLEL_PROCESSING_ENABLED", "true").lower() == "true"
    
    @property
    def async_processing_enabled(self) -> bool:
        return os.getenv("ASYNC_PROCESSING_ENABLED", "true").lower() == "true"
    
    @property
    def sentiment_trending_enabled(self) -> bool:
        return os.getenv("SENTIMENT_TRENDING_ENABLED", "true").lower() == "true"

# Global configuration instance
config = SentimentConfig()

# Validation on import
if __name__ == "__main__":
    print("Sentiment Aggregator Configuration:")
    print(f"RSS Feeds Enabled: {config.rss_feeds_enabled}")
    print(f"NewsAPI Enabled: {config.newsapi_enabled}")
    print(f"GNews Enabled: {config.gnews_enabled}")
    print(f"Kafka News Topic: {config.kafka_news_topic}")
    print(f"Market Timezone: {config.market_timezone}")
    print(f"Redis Cache Enabled: {config.redis_cache_enabled}")
    print("Configuration loaded successfully!")
