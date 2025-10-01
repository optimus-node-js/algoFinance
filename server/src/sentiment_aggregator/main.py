"""
Sentiment Aggregator Service
===========================

FastAPI service for real-time news sentiment analysis for Indian financial markets.
Integrates with Kafka, Redis, Database, and Angel One API services.
"""

import asyncio
import logging
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional

from fastapi import FastAPI, HTTPException, BackgroundTasks, Depends
from fastapi.responses import JSONResponse
import uvicorn

# Core infrastructure imports
from messaging_enhanced.kafka import KafkaManager, SentimentProducer
from caching_service.redis_manager import RedisManager
from database_service.prisma_client import PrismaService

# Local imports
from .config import config
from .news_apis import NewsAPIManager, NewsAggregationResult, NewsArticle
from .data_processing.company_mapper import CompanyMapper

# Configure logging
logging.basicConfig(
    level=getattr(logging, config.log_level.upper()),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Global service instances
kafka_manager: Optional[KafkaManager] = None
sentiment_producer: Optional[SentimentProducer] = None
redis_manager: Optional[RedisManager] = None
prisma_service: Optional[PrismaService] = None
news_api_manager: Optional[NewsAPIManager] = None
company_mapper: Optional[CompanyMapper] = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """FastAPI lifespan events for startup and shutdown."""
    global kafka_manager, sentiment_producer, redis_manager, prisma_service, news_api_manager, company_mapper
    
    logger.info("Starting Sentiment Aggregator Service...")
    
    try:
        # Initialize Kafka Manager
        kafka_manager = KafkaManager()
        await kafka_manager.start()
        
        # Create Kafka topics for sentiment analysis
        sentiment_topics = [
            "hft-sentiment-news-raw",      # Raw news articles
            "hft-sentiment-analysis",      # Sentiment analysis results
            "hft-sentiment-signals",       # Trading signals from sentiment
            "hft-sentiment-company-news",  # Company-specific news
            "hft-sentiment-breaking-news", # Breaking news alerts
            "hft-sentiment-health"         # Service health events
        ]
        
        for topic in sentiment_topics:
            await kafka_manager.create_topic(topic, num_partitions=3, replication_factor=1)
        
        # Initialize Sentiment Producer
        sentiment_producer = SentimentProducer(kafka_manager)
        await sentiment_producer.start()
        
        # Initialize Redis Manager
        redis_manager = RedisManager()
        await redis_manager.connect()
        
        # Initialize Database Service
        prisma_service = PrismaService()
        await prisma_service.connect()
        
        # Initialize News API Manager
        news_api_manager = NewsAPIManager()
        await news_api_manager.__aenter__()
        
        # Initialize Company Mapper
        company_mapper = CompanyMapper()
        
        logger.info("✅ Sentiment Aggregator Service started successfully")
        
        # Publish startup event
        if sentiment_producer:
            await sentiment_producer.send_sentiment_event({
                "event_type": "service_started",
                "service": "sentiment_aggregator",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "status": "healthy"
            })
        
    except Exception as e:
        logger.error(f"❌ Failed to start Sentiment Aggregator Service: {e}")
        raise
    
    yield
    
    # Shutdown
    logger.info("Shutting down Sentiment Aggregator Service...")
    
    try:
        # Publish shutdown event
        if sentiment_producer:
            await sentiment_producer.send_sentiment_event({
                "event_type": "service_stopping",
                "service": "sentiment_aggregator",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "status": "shutting_down"
            })
        
        # Close all connections
        if news_api_manager:
            await news_api_manager.__aexit__(None, None, None)
        
        if sentiment_producer:
            await sentiment_producer.close()
        
        if kafka_manager:
            await kafka_manager.close()
        
        if redis_manager:
            await redis_manager.close()
        
        if prisma_service:
            await prisma_service.disconnect()
        
        logger.info("✅ Sentiment Aggregator Service shutdown complete")
        
    except Exception as e:
        logger.error(f"❌ Error during shutdown: {e}")

# Create FastAPI app
app = FastAPI(
    title="Sentiment Aggregator Service",
    description="Real-time news sentiment analysis for Indian financial markets",
    version="1.0.0",
    lifespan=lifespan
)

# Dependency to get services
async def get_services():
    """Dependency to get all service instances."""
    return {
        "kafka_manager": kafka_manager,
        "sentiment_producer": sentiment_producer,
        "redis_manager": redis_manager,
        "prisma_service": prisma_service,
        "news_api_manager": news_api_manager,
        "company_mapper": company_mapper
    }

@app.get("/health")
async def health_check(services: dict = Depends(get_services)):
    """Health check endpoint."""
    health_status = {
        "service": "sentiment_aggregator",
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "components": {}
    }
    
    # Check Kafka
    if services["kafka_manager"]:
        try:
            kafka_stats = await services["kafka_manager"].get_stats()
            health_status["components"]["kafka"] = {
                "status": "healthy",
                "stats": kafka_stats
            }
        except Exception as e:
            health_status["components"]["kafka"] = {
                "status": "unhealthy",
                "error": str(e)
            }
            health_status["status"] = "degraded"
    
    # Check Redis
    if services["redis_manager"]:
        try:
            redis_info = await services["redis_manager"].get_info()
            health_status["components"]["redis"] = {
                "status": "healthy",
                "info": redis_info
            }
        except Exception as e:
            health_status["components"]["redis"] = {
                "status": "unhealthy",
                "error": str(e)
            }
            health_status["status"] = "degraded"
    
    # Check Database
    if services["prisma_service"]:
        try:
            db_health = await services["prisma_service"].health_check()
            health_status["components"]["database"] = {
                "status": "healthy" if db_health["healthy"] else "unhealthy",
                "stats": db_health
            }
            if not db_health["healthy"]:
                health_status["status"] = "degraded"
        except Exception as e:
            health_status["components"]["database"] = {
                "status": "unhealthy",
                "error": str(e)
            }
            health_status["status"] = "degraded"
    
    # Check News APIs
    if services["news_api_manager"]:
        try:
            api_stats = services["news_api_manager"].get_manager_stats()
            health_status["components"]["news_apis"] = {
                "status": "healthy",
                "stats": api_stats
            }
        except Exception as e:
            health_status["components"]["news_apis"] = {
                "status": "unhealthy",
                "error": str(e)
            }
            health_status["status"] = "degraded"
    
    return health_status

@app.get("/news/fetch")
async def fetch_news(
    max_articles: int = 50,
    hours_back: int = 24,
    include_breaking: bool = True,
    background_tasks: BackgroundTasks = BackgroundTasks(),
    services: dict = Depends(get_services)
):
    """Fetch news from all sources and publish to Kafka."""
    
    if not services["news_api_manager"]:
        raise HTTPException(status_code=503, detail="News API manager not available")
    
    try:
        # Fetch news from all sources
        result = await services["news_api_manager"].fetch_all_news(
            max_articles=max_articles,
            hours_back=hours_back,
            include_breaking=include_breaking
        )
        
        # Add background task to process and publish articles
        background_tasks.add_task(
            process_and_publish_articles,
            result.articles,
            services
        )
        
        return {
            "status": "success",
            "message": f"Fetched {result.unique_articles} unique articles",
            "result": {
                "total_articles": result.total_articles,
                "unique_articles": result.unique_articles,
                "duplicates_removed": result.duplicates_removed,
                "sources_used": result.sources_used,
                "fetch_time_seconds": result.fetch_time_seconds,
                "errors": result.errors
            }
        }
        
    except Exception as e:
        logger.error(f"Error fetching news: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch news: {str(e)}")

@app.get("/news/company/{company_name}")
async def fetch_company_news(
    company_name: str,
    max_articles: int = 20,
    hours_back: int = 24,
    background_tasks: BackgroundTasks = BackgroundTasks(),
    services: dict = Depends(get_services)
):
    """Fetch news for a specific company."""
    
    if not services["news_api_manager"] or not services["company_mapper"]:
        raise HTTPException(status_code=503, detail="Required services not available")
    
    try:
        # Get company variations and symbols
        company_info = services["company_mapper"].get_company_info(company_name)
        if not company_info:
            raise HTTPException(status_code=404, detail=f"Company '{company_name}' not found")
        
        # Search for company news
        search_terms = [company_info["name"]] + company_info.get("aliases", [])
        result = await services["news_api_manager"].search_company_news(
            company_names=search_terms,
            max_articles=max_articles,
            hours_back=hours_back
        )
        
        # Add background task to process company-specific articles
        background_tasks.add_task(
            process_company_articles,
            result.articles,
            company_info,
            services
        )
        
        return {
            "status": "success",
            "company": company_info,
            "articles_found": result.unique_articles,
            "result": {
                "total_articles": result.total_articles,
                "unique_articles": result.unique_articles,
                "duplicates_removed": result.duplicates_removed,
                "sources_used": result.sources_used,
                "fetch_time_seconds": result.fetch_time_seconds
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching company news: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch company news: {str(e)}")

@app.get("/sentiment/analyze")
async def analyze_sentiment(
    text: str,
    services: dict = Depends(get_services)
):
    """Analyze sentiment of provided text."""
    
    # TODO: Implement sentiment analysis model
    # For now, return a placeholder response
    
    return {
        "status": "success",
        "text": text[:100] + "..." if len(text) > 100 else text,
        "sentiment": {
            "score": 0.0,  # Placeholder
            "label": "neutral",  # Placeholder
            "confidence": 0.0  # Placeholder
        },
        "message": "Sentiment analysis model not yet implemented"
    }

@app.get("/stats")
async def get_service_stats(services: dict = Depends(get_services)):
    """Get comprehensive service statistics."""
    
    stats = {
        "service": "sentiment_aggregator",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "components": {}
    }
    
    # News API Manager stats
    if services["news_api_manager"]:
        stats["components"]["news_apis"] = services["news_api_manager"].get_manager_stats()
    
    # Company Mapper stats
    if services["company_mapper"]:
        stats["components"]["company_mapper"] = services["company_mapper"].get_stats()
    
    # Kafka stats
    if services["kafka_manager"]:
        try:
            stats["components"]["kafka"] = await services["kafka_manager"].get_stats()
        except Exception as e:
            stats["components"]["kafka"] = {"error": str(e)}
    
    # Redis stats
    if services["redis_manager"]:
        try:
            stats["components"]["redis"] = await services["redis_manager"].get_stats()
        except Exception as e:
            stats["components"]["redis"] = {"error": str(e)}
    
    return stats

# Background task functions
async def process_and_publish_articles(articles: List[NewsArticle], services: dict):
    """Process articles and publish to Kafka."""
    
    if not services["sentiment_producer"]:
        logger.warning("Sentiment producer not available - skipping article publishing")
        return
    
    try:
        for article in articles:
            # Publish raw news article
            await services["sentiment_producer"].send_news_article({
                "article_id": article.article_id,
                "title": article.title,
                "content": article.content,
                "url": article.url,
                "source": article.source,
                "published_at": article.published_at.isoformat(),
                "tags": article.tags,
                "timestamp": datetime.now(timezone.utc).isoformat()
            })
        
        logger.info(f"Published {len(articles)} articles to Kafka")
        
    except Exception as e:
        logger.error(f"Error publishing articles to Kafka: {e}")

async def process_company_articles(articles: List[NewsArticle], company_info: dict, services: dict):
    """Process company-specific articles."""
    
    if not services["sentiment_producer"]:
        logger.warning("Sentiment producer not available - skipping company article processing")
        return
    
    try:
        for article in articles:
            # Publish company-specific news
            await services["sentiment_producer"].send_company_news({
                "article_id": article.article_id,
                "company_name": company_info["name"],
                "company_symbol": company_info.get("symbol"),
                "sector": company_info.get("sector"),
                "title": article.title,
                "content": article.content,
                "url": article.url,
                "source": article.source,
                "published_at": article.published_at.isoformat(),
                "tags": article.tags,
                "timestamp": datetime.now(timezone.utc).isoformat()
            })
        
        logger.info(f"Published {len(articles)} company articles for {company_info['name']} to Kafka")
        
    except Exception as e:
        logger.error(f"Error publishing company articles to Kafka: {e}")

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8010,
        reload=True,
        log_level=config.log_level.lower()
    )