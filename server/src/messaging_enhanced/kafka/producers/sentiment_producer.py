"""
Sentiment Producer for Kafka
============================

Kafka producer for publishing sentiment analysis events, news articles,
and sentiment signals to the HFT system.
"""

import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional
import uuid

from ..kafka_manager import KafkaManager
from ..base_producer import BaseProducer

logger = logging.getLogger(__name__)

class SentimentProducer(BaseProducer):
    """Kafka producer for sentiment analysis events."""
    
    def __init__(self, kafka_manager: KafkaManager):
        """Initialize sentiment producer."""
        super().__init__(kafka_manager, "sentiment_producer")
        
        # Topic mappings
        self.topics = {
            "news_raw": "hft-sentiment-news-raw",
            "sentiment_analysis": "hft-sentiment-analysis", 
            "sentiment_signals": "hft-sentiment-signals",
            "company_news": "hft-sentiment-company-news",
            "breaking_news": "hft-sentiment-breaking-news",
            "health": "hft-sentiment-health"
        }
        
        # Schema name for sentiment events
        self.schema_name = "sentiment_event"
        
        logger.info("SentimentProducer initialized")
    
    async def send_sentiment_event(self, event_data: Dict[str, Any]) -> bool:
        """Send a general sentiment event."""
        
        # Add event metadata
        event_data.update({
            "event_id": str(uuid.uuid4()),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event_type": event_data.get("event_type", "SERVICE_EVENT")
        })
        
        return await self.send_message(
            topic=self.topics["health"],
            key=event_data.get("event_id"),
            value=event_data,
            schema_name=self.schema_name
        )
    
    async def send_news_article(self, article_data: Dict[str, Any]) -> bool:
        """Send a raw news article event."""
        
        # Prepare news article event
        event_data = {
            "event_id": str(uuid.uuid4()),
            "event_type": "NEWS_ARTICLE",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "source": article_data.get("source", "unknown"),
            "article_id": article_data.get("article_id"),
            "title": article_data.get("title"),
            "content": article_data.get("content"),
            "url": article_data.get("url"),
            "published_at": article_data.get("published_at"),
            "tags": article_data.get("tags", []),
            "metadata": {
                "content_length": str(len(article_data.get("content", ""))),
                "word_count": str(len(article_data.get("content", "").split()))
            }
        }
        
        return await self.send_message(
            topic=self.topics["news_raw"],
            key=article_data.get("article_id"),
            value=event_data,
            schema_name=self.schema_name
        )
    
    async def send_sentiment_analysis(self, analysis_data: Dict[str, Any]) -> bool:
        """Send sentiment analysis results."""
        
        # Prepare sentiment analysis event
        event_data = {
            "event_id": str(uuid.uuid4()),
            "event_type": "SENTIMENT_ANALYSIS",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "source": "sentiment_analyzer",
            "article_id": analysis_data.get("article_id"),
            "title": analysis_data.get("title"),
            "content": analysis_data.get("content"),
            "company_name": analysis_data.get("company_name"),
            "company_symbol": analysis_data.get("company_symbol"),
            "sector": analysis_data.get("sector"),
            "sentiment_score": analysis_data.get("sentiment_score"),
            "sentiment_label": analysis_data.get("sentiment_label"),
            "confidence": analysis_data.get("confidence"),
            "tags": analysis_data.get("tags", []),
            "metadata": analysis_data.get("metadata", {})
        }
        
        return await self.send_message(
            topic=self.topics["sentiment_analysis"],
            key=analysis_data.get("article_id"),
            value=event_data,
            schema_name=self.schema_name
        )
    
    async def send_sentiment_signal(self, signal_data: Dict[str, Any]) -> bool:
        """Send trading signal based on sentiment analysis."""
        
        # Prepare sentiment signal event
        event_data = {
            "event_id": str(uuid.uuid4()),
            "event_type": "SENTIMENT_SIGNAL",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "source": "sentiment_signal_generator",
            "company_name": signal_data.get("company_name"),
            "company_symbol": signal_data.get("company_symbol"),
            "sector": signal_data.get("sector"),
            "sentiment_score": signal_data.get("sentiment_score"),
            "sentiment_label": signal_data.get("sentiment_label"),
            "confidence": signal_data.get("confidence"),
            "tags": signal_data.get("tags", ["trading_signal"]),
            "metadata": {
                "signal_strength": str(signal_data.get("signal_strength", 0.0)),
                "recommendation": signal_data.get("recommendation", "HOLD"),
                "articles_analyzed": str(signal_data.get("articles_analyzed", 0))
            }
        }
        
        return await self.send_message(
            topic=self.topics["sentiment_signals"],
            key=signal_data.get("company_symbol"),
            value=event_data,
            schema_name=self.schema_name
        )
    
    async def send_company_news(self, company_data: Dict[str, Any]) -> bool:
        """Send company-specific news event."""
        
        # Prepare company news event
        event_data = {
            "event_id": str(uuid.uuid4()),
            "event_type": "COMPANY_NEWS",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "source": company_data.get("source", "unknown"),
            "article_id": company_data.get("article_id"),
            "title": company_data.get("title"),
            "content": company_data.get("content"),
            "url": company_data.get("url"),
            "published_at": company_data.get("published_at"),
            "company_name": company_data.get("company_name"),
            "company_symbol": company_data.get("company_symbol"),
            "sector": company_data.get("sector"),
            "tags": company_data.get("tags", []),
            "metadata": {
                "content_length": str(len(company_data.get("content", ""))),
                "relevance_score": str(company_data.get("relevance_score", 0.0))
            }
        }
        
        return await self.send_message(
            topic=self.topics["company_news"],
            key=company_data.get("company_symbol"),
            value=event_data,
            schema_name=self.schema_name
        )
    
    async def send_breaking_news(self, breaking_data: Dict[str, Any]) -> bool:
        """Send breaking news alert."""
        
        # Prepare breaking news event
        event_data = {
            "event_id": str(uuid.uuid4()),
            "event_type": "BREAKING_NEWS",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "source": breaking_data.get("source", "unknown"),
            "article_id": breaking_data.get("article_id"),
            "title": breaking_data.get("title"),
            "content": breaking_data.get("content"),
            "url": breaking_data.get("url"),
            "published_at": breaking_data.get("published_at"),
            "company_name": breaking_data.get("company_name"),
            "company_symbol": breaking_data.get("company_symbol"),
            "sector": breaking_data.get("sector"),
            "tags": breaking_data.get("tags", ["breaking"]),
            "metadata": {
                "urgency": breaking_data.get("urgency", "high"),
                "impact_score": str(breaking_data.get("impact_score", 0.0))
            }
        }
        
        return await self.send_message(
            topic=self.topics["breaking_news"],
            key=breaking_data.get("article_id"),
            value=event_data,
            schema_name=self.schema_name
        )
    
    def get_producer_stats(self) -> Dict[str, Any]:
        """Get sentiment producer statistics."""
        base_stats = super().get_producer_stats()
        
        return {
            **base_stats,
            "topics": self.topics,
            "schema_name": self.schema_name,
            "producer_type": "sentiment_producer"
        }

# Global producer instance management
_sentiment_producer: Optional[SentimentProducer] = None

async def get_sentiment_producer(kafka_manager: KafkaManager) -> SentimentProducer:
    """Get or create sentiment producer instance."""
    global _sentiment_producer
    
    if _sentiment_producer is None:
        _sentiment_producer = SentimentProducer(kafka_manager)
        await _sentiment_producer.start()
    
    return _sentiment_producer

async def close_sentiment_producer():
    """Close sentiment producer instance."""
    global _sentiment_producer
    
    if _sentiment_producer:
        await _sentiment_producer.close()
        _sentiment_producer = None

# Example usage and testing
async def test_sentiment_producer():
    """Test sentiment producer functionality."""
    from ..kafka_manager import KafkaManager
    
    # Initialize Kafka manager
    kafka_manager = KafkaManager()
    await kafka_manager.start()
    
    try:
        # Create sentiment producer
        producer = SentimentProducer(kafka_manager)
        await producer.start()
        
        print("Testing Sentiment Producer...")
        
        # Test news article
        article_success = await producer.send_news_article({
            "article_id": "test_article_001",
            "title": "Test Financial News Article",
            "content": "This is a test article about Indian stock markets.",
            "url": "https://example.com/test-article",
            "source": "test_source",
            "published_at": datetime.now(timezone.utc).isoformat(),
            "tags": ["test", "financial"]
        })
        print(f"News article sent: {article_success}")
        
        # Test sentiment analysis
        analysis_success = await producer.send_sentiment_analysis({
            "article_id": "test_article_001",
            "title": "Test Financial News Article",
            "sentiment_score": 0.75,
            "sentiment_label": "POSITIVE",
            "confidence": 0.85,
            "company_name": "Test Company",
            "company_symbol": "TEST",
            "tags": ["positive", "analysis"]
        })
        print(f"Sentiment analysis sent: {analysis_success}")
        
        # Test sentiment signal
        signal_success = await producer.send_sentiment_signal({
            "company_name": "Test Company",
            "company_symbol": "TEST",
            "sentiment_score": 0.75,
            "sentiment_label": "POSITIVE",
            "confidence": 0.85,
            "signal_strength": 0.8,
            "recommendation": "BUY",
            "articles_analyzed": 5
        })
        print(f"Sentiment signal sent: {signal_success}")
        
        # Get stats
        stats = producer.get_producer_stats()
        print(f"Producer stats: {stats}")
        
        await producer.close()
        
    finally:
        await kafka_manager.close()

if __name__ == "__main__":
    asyncio.run(test_sentiment_producer())