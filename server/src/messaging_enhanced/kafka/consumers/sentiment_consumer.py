"""
Sentiment Consumer for Kafka
============================

Kafka consumer for processing sentiment analysis events, news articles,
and sentiment signals from the HFT system.
"""

import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional, Callable, List
import uuid

from ..kafka_manager import KafkaManager
from ..base_consumer import BaseConsumer

logger = logging.getLogger(__name__)

class SentimentConsumer(BaseConsumer):
    """Kafka consumer for sentiment analysis events."""
    
    def __init__(self, kafka_manager: KafkaManager, group_id: str = "sentiment_consumer_group"):
        """Initialize sentiment consumer."""
        super().__init__(kafka_manager, group_id)
        
        # Topics to consume from
        self.topics = [
            "hft-sentiment-news-raw",
            "hft-sentiment-analysis", 
            "hft-sentiment-signals",
            "hft-sentiment-company-news",
            "hft-sentiment-breaking-news",
            "hft-sentiment-health"
        ]
        
        # Schema name for sentiment events
        self.schema_name = "sentiment_event"
        
        # Callback handlers for different event types
        self.event_handlers: Dict[str, List[Callable]] = {
            "NEWS_ARTICLE": [],
            "SENTIMENT_ANALYSIS": [],
            "COMPANY_NEWS": [],
            "BREAKING_NEWS": [],
            "SENTIMENT_SIGNAL": [],
            "SERVICE_EVENT": []
        }
        
        # Statistics
        self.processed_events = 0
        self.processing_errors = 0
        self.last_processed = None
        
        logger.info(f"SentimentConsumer initialized with group_id: {group_id}")
    
    def register_news_article_handler(self, handler: Callable[[Dict[str, Any]], None]):
        """Register handler for news article events."""
        self.event_handlers["NEWS_ARTICLE"].append(handler)
        logger.info("News article handler registered")
    
    def register_sentiment_analysis_handler(self, handler: Callable[[Dict[str, Any]], None]):
        """Register handler for sentiment analysis events."""
        self.event_handlers["SENTIMENT_ANALYSIS"].append(handler)
        logger.info("Sentiment analysis handler registered")
    
    def register_company_news_handler(self, handler: Callable[[Dict[str, Any]], None]):
        """Register handler for company news events."""
        self.event_handlers["COMPANY_NEWS"].append(handler)
        logger.info("Company news handler registered")
    
    def register_breaking_news_handler(self, handler: Callable[[Dict[str, Any]], None]):
        """Register handler for breaking news events."""
        self.event_handlers["BREAKING_NEWS"].append(handler)
        logger.info("Breaking news handler registered")
    
    def register_sentiment_signal_handler(self, handler: Callable[[Dict[str, Any]], None]):
        """Register handler for sentiment signal events."""
        self.event_handlers["SENTIMENT_SIGNAL"].append(handler)
        logger.info("Sentiment signal handler registered")
    
    def register_service_event_handler(self, handler: Callable[[Dict[str, Any]], None]):
        """Register handler for service events."""
        self.event_handlers["SERVICE_EVENT"].append(handler)
        logger.info("Service event handler registered")
    
    async def process_message(self, message: Dict[str, Any]) -> bool:
        """Process a sentiment event message."""
        
        try:
            # Extract event type
            event_type = message.get("event_type", "SERVICE_EVENT")
            event_id = message.get("event_id", "unknown")
            
            logger.debug(f"Processing sentiment event: {event_type} (ID: {event_id})")
            
            # Call registered handlers for this event type
            handlers = self.event_handlers.get(event_type, [])
            
            if handlers:
                # Execute all handlers for this event type
                for handler in handlers:
                    try:
                        if asyncio.iscoroutinefunction(handler):
                            await handler(message)
                        else:
                            handler(message)
                    except Exception as e:
                        logger.error(f"Handler error for {event_type}: {e}")
                        self.processing_errors += 1
            else:
                logger.warning(f"No handlers registered for event type: {event_type}")
            
            # Update statistics
            self.processed_events += 1
            self.last_processed = datetime.now(timezone.utc)
            
            return True
            
        except Exception as e:
            logger.error(f"Error processing sentiment message: {e}")
            self.processing_errors += 1
            return False
    
    async def start_consuming(self):
        """Start consuming sentiment events."""
        logger.info(f"Starting sentiment consumer for topics: {self.topics}")
        
        await self.consume_messages(
            topics=self.topics,
            message_processor=self.process_message,
            schema_name=self.schema_name
        )
    
    def get_consumer_stats(self) -> Dict[str, Any]:
        """Get sentiment consumer statistics."""
        base_stats = super().get_consumer_stats()
        
        return {
            **base_stats,
            "topics": self.topics,
            "schema_name": self.schema_name,
            "processed_events": self.processed_events,
            "processing_errors": self.processing_errors,
            "last_processed": self.last_processed.isoformat() if self.last_processed else None,
            "registered_handlers": {
                event_type: len(handlers) 
                for event_type, handlers in self.event_handlers.items()
            },
            "consumer_type": "sentiment_consumer"
        }

# Example event handlers
class SentimentEventHandlers:
    """Example event handlers for sentiment consumer."""
    
    @staticmethod
    async def handle_news_article(event: Dict[str, Any]):
        """Handle news article events."""
        article_id = event.get("article_id")
        title = event.get("title", "")
        source = event.get("source", "unknown")
        
        logger.info(f"📰 News Article: {title[:50]}... (Source: {source}, ID: {article_id})")
        
        # TODO: Store in database, trigger sentiment analysis, etc.
    
    @staticmethod
    async def handle_sentiment_analysis(event: Dict[str, Any]):
        """Handle sentiment analysis results."""
        article_id = event.get("article_id")
        sentiment_score = event.get("sentiment_score", 0.0)
        sentiment_label = event.get("sentiment_label", "NEUTRAL")
        confidence = event.get("confidence", 0.0)
        company_name = event.get("company_name")
        
        logger.info(f"📊 Sentiment Analysis: {sentiment_label} ({sentiment_score:.2f}, confidence: {confidence:.2f})")
        if company_name:
            logger.info(f"   Company: {company_name}")
        
        # TODO: Store results, trigger trading signals, etc.
    
    @staticmethod
    async def handle_company_news(event: Dict[str, Any]):
        """Handle company-specific news."""
        company_name = event.get("company_name")
        company_symbol = event.get("company_symbol")
        title = event.get("title", "")
        
        logger.info(f"🏢 Company News: {company_name} ({company_symbol})")
        logger.info(f"   Title: {title[:50]}...")
        
        # TODO: Company-specific processing, portfolio impact analysis, etc.
    
    @staticmethod
    async def handle_breaking_news(event: Dict[str, Any]):
        """Handle breaking news alerts."""
        title = event.get("title", "")
        urgency = event.get("metadata", {}).get("urgency", "medium")
        
        logger.warning(f"🚨 BREAKING NEWS ({urgency.upper()}): {title}")
        
        # TODO: Immediate alerts, emergency protocols, etc.
    
    @staticmethod
    async def handle_sentiment_signal(event: Dict[str, Any]):
        """Handle sentiment-based trading signals."""
        company_symbol = event.get("company_symbol")
        sentiment_score = event.get("sentiment_score", 0.0)
        recommendation = event.get("metadata", {}).get("recommendation", "HOLD")
        signal_strength = event.get("metadata", {}).get("signal_strength", "0.0")
        
        logger.info(f"📈 Trading Signal: {company_symbol} - {recommendation}")
        logger.info(f"   Sentiment: {sentiment_score:.2f}, Strength: {signal_strength}")
        
        # TODO: Forward to strategy engine, risk management, etc.
    
    @staticmethod
    async def handle_service_event(event: Dict[str, Any]):
        """Handle service lifecycle events."""
        service = event.get("metadata", {}).get("service", "unknown")
        status = event.get("metadata", {}).get("status", "unknown")
        
        logger.info(f"⚙️  Service Event: {service} - {status}")

# Global consumer instance management
_sentiment_consumer: Optional[SentimentConsumer] = None

async def get_sentiment_consumer(kafka_manager: KafkaManager, group_id: str = "sentiment_consumer_group") -> SentimentConsumer:
    """Get or create sentiment consumer instance."""
    global _sentiment_consumer
    
    if _sentiment_consumer is None:
        _sentiment_consumer = SentimentConsumer(kafka_manager, group_id)
        await _sentiment_consumer.start()
    
    return _sentiment_consumer

async def close_sentiment_consumer():
    """Close sentiment consumer instance."""
    global _sentiment_consumer
    
    if _sentiment_consumer:
        await _sentiment_consumer.close()
        _sentiment_consumer = None

# Example usage and testing
async def test_sentiment_consumer():
    """Test sentiment consumer functionality."""
    from ..kafka_manager import KafkaManager
    
    # Initialize Kafka manager
    kafka_manager = KafkaManager()
    await kafka_manager.start()
    
    try:
        # Create sentiment consumer
        consumer = SentimentConsumer(kafka_manager, "test_sentiment_group")
        
        # Register example handlers
        handlers = SentimentEventHandlers()
        consumer.register_news_article_handler(handlers.handle_news_article)
        consumer.register_sentiment_analysis_handler(handlers.handle_sentiment_analysis)
        consumer.register_company_news_handler(handlers.handle_company_news)
        consumer.register_breaking_news_handler(handlers.handle_breaking_news)
        consumer.register_sentiment_signal_handler(handlers.handle_sentiment_signal)
        consumer.register_service_event_handler(handlers.handle_service_event)
        
        print("Testing Sentiment Consumer...")
        print("Registered handlers for all event types")
        
        # Get stats
        stats = consumer.get_consumer_stats()
        print(f"Consumer stats: {stats}")
        
        # Start consuming (this would run indefinitely in real usage)
        print("Starting consumer... (press Ctrl+C to stop)")
        await consumer.start_consuming()
        
    except KeyboardInterrupt:
        print("Consumer stopped by user")
    finally:
        await kafka_manager.close()

if __name__ == "__main__":
    asyncio.run(test_sentiment_consumer())