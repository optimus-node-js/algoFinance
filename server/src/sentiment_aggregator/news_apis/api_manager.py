"""
News API Manager
===============

Centralized manager for coordinating multiple news sources.
Handles rate limiting, deduplication, and intelligent source selection.
"""

import asyncio
import logging
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Optional, Set
from dataclasses import dataclass, field
import hashlib
from collections import defaultdict

from ..config import config
from .rss_client import RSSClient, NewsArticle
from .newsapi_client import NewsAPIClient
from .gnews_client import GNewsClient

logger = logging.getLogger(__name__)

@dataclass
class NewsSourceStats:
    """Statistics for a news source."""
    name: str
    enabled: bool
    articles_fetched: int = 0
    requests_made: int = 0
    errors: int = 0
    last_fetch: Optional[datetime] = None
    rate_limit_hits: int = 0
    avg_response_time: float = 0.0
    
@dataclass
class NewsAggregationResult:
    """Result of news aggregation from multiple sources."""
    articles: List[NewsArticle] = field(default_factory=list)
    total_articles: int = 0
    unique_articles: int = 0
    duplicates_removed: int = 0
    sources_used: List[str] = field(default_factory=list)
    fetch_time_seconds: float = 0.0
    errors: List[str] = field(default_factory=list)

class NewsAPIManager:
    """Centralized manager for all news sources."""
    
    def __init__(self):
        """Initialize the news API manager."""
        self.rss_client = RSSClient()
        self.newsapi_client = NewsAPIClient()
        self.gnews_client = GNewsClient()
        
        # Source statistics
        self.source_stats = {
            "rss": NewsSourceStats("RSS Feeds", True),
            "newsapi": NewsSourceStats("NewsAPI", self.newsapi_client.enabled),
            "gnews": NewsSourceStats("GNews", self.gnews_client.enabled)
        }
        
        # Deduplication cache
        self.seen_articles: Set[str] = set()
        self.article_cache: Dict[str, NewsArticle] = {}
        
        # Configuration
        self.max_articles_per_source = config.max_articles_per_source
        self.deduplication_enabled = config.deduplication_enabled
        self.similarity_threshold = config.similarity_threshold
        
        logger.info(f"NewsAPIManager initialized with {len([s for s in self.source_stats.values() if s.enabled])} enabled sources")
    
    async def __aenter__(self):
        """Async context manager entry."""
        # Initialize all clients
        await self.rss_client.__aenter__()
        await self.newsapi_client.__aenter__()
        await self.gnews_client.__aenter__()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        # Close all clients
        await self.rss_client.__aexit__(exc_type, exc_val, exc_tb)
        await self.newsapi_client.__aexit__(exc_type, exc_val, exc_tb)
        await self.gnews_client.__aexit__(exc_type, exc_val, exc_tb)
    
    def _generate_article_hash(self, article: NewsArticle) -> str:
        """Generate a hash for article deduplication."""
        # Use title and URL for deduplication
        content = f"{article.title.lower().strip()}{article.url}"
        return hashlib.md5(content.encode()).hexdigest()
    
    def _is_duplicate(self, article: NewsArticle) -> bool:
        """Check if article is a duplicate."""
        if not self.deduplication_enabled:
            return False
        
        article_hash = self._generate_article_hash(article)
        return article_hash in self.seen_articles
    
    def _add_to_cache(self, article: NewsArticle):
        """Add article to deduplication cache."""
        if self.deduplication_enabled:
            article_hash = self._generate_article_hash(article)
            self.seen_articles.add(article_hash)
            self.article_cache[article_hash] = article
    
    def _update_source_stats(self, source: str, articles_count: int, errors: int = 0, response_time: float = 0.0):
        """Update statistics for a source."""
        if source in self.source_stats:
            stats = self.source_stats[source]
            stats.articles_fetched += articles_count
            stats.requests_made += 1
            stats.errors += errors
            stats.last_fetch = datetime.now(timezone.utc)
            
            # Update average response time
            if response_time > 0:
                if stats.avg_response_time == 0:
                    stats.avg_response_time = response_time
                else:
                    stats.avg_response_time = (stats.avg_response_time + response_time) / 2
    
    async def fetch_all_news(
        self,
        max_articles: int = 100,
        hours_back: int = 24,
        include_breaking: bool = True
    ) -> NewsAggregationResult:
        """Fetch news from all available sources."""
        
        start_time = datetime.now()
        result = NewsAggregationResult()
        
        # Prepare tasks for parallel execution
        tasks = []
        
        # RSS feeds (always available, no rate limits)
        if self.source_stats["rss"].enabled:
            tasks.append(self._fetch_rss_news(max_articles // 2, hours_back))
        
        # NewsAPI (if enabled and within rate limits)
        if self.source_stats["newsapi"].enabled:
            tasks.append(self._fetch_newsapi_news(max_articles // 4, hours_back))
        
        # GNews (if enabled and within rate limits)
        if self.source_stats["gnews"].enabled:
            tasks.append(self._fetch_gnews_news(max_articles // 4, hours_back))
        
        # Execute all tasks in parallel
        if tasks:
            try:
                results = await asyncio.gather(*tasks, return_exceptions=True)
                
                # Process results
                for i, task_result in enumerate(results):
                    if isinstance(task_result, Exception):
                        source_name = ["rss", "newsapi", "gnews"][i]
                        error_msg = f"{source_name} fetch failed: {str(task_result)}"
                        result.errors.append(error_msg)
                        logger.error(error_msg)
                    elif isinstance(task_result, tuple):
                        source_articles, source_name = task_result
                        result.sources_used.append(source_name)
                        
                        # Add articles with deduplication
                        for article in source_articles:
                            if not self._is_duplicate(article):
                                result.articles.append(article)
                                self._add_to_cache(article)
                            else:
                                result.duplicates_removed += 1
                        
                        result.total_articles += len(source_articles)
                
            except Exception as e:
                error_msg = f"Parallel news fetch failed: {str(e)}"
                result.errors.append(error_msg)
                logger.error(error_msg)
        
        # Fetch breaking news if requested
        if include_breaking:
            try:
                breaking_articles = await self._fetch_breaking_news(max_articles // 10)
                for article in breaking_articles:
                    if not self._is_duplicate(article):
                        result.articles.append(article)
                        self._add_to_cache(article)
                        # Tag as breaking news
                        article.tags.append("breaking")
            except Exception as e:
                result.errors.append(f"Breaking news fetch failed: {str(e)}")
        
        # Sort articles by published date (newest first)
        result.articles.sort(key=lambda x: x.published_at, reverse=True)
        
        # Limit final results
        if len(result.articles) > max_articles:
            result.articles = result.articles[:max_articles]
        
        result.unique_articles = len(result.articles)
        result.fetch_time_seconds = (datetime.now() - start_time).total_seconds()
        
        logger.info(f"Aggregated {result.unique_articles} unique articles from {len(result.sources_used)} sources "
                   f"({result.duplicates_removed} duplicates removed) in {result.fetch_time_seconds:.2f}s")
        
        return result
    
    async def _fetch_rss_news(self, max_articles: int, hours_back: int) -> tuple[List[NewsArticle], str]:
        """Fetch news from RSS feeds."""
        start_time = datetime.now()
        
        try:
            articles = await self.rss_client.fetch_all_feeds(
                max_articles_per_feed=max_articles // len(self.rss_client.rss_feeds),
                hours_back=hours_back
            )
            
            response_time = (datetime.now() - start_time).total_seconds()
            self._update_source_stats("rss", len(articles), 0, response_time)
            
            return articles, "RSS Feeds"
            
        except Exception as e:
            self._update_source_stats("rss", 0, 1)
            raise e
    
    async def _fetch_newsapi_news(self, max_articles: int, hours_back: int) -> tuple[List[NewsArticle], str]:
        """Fetch news from NewsAPI."""
        start_time = datetime.now()
        
        try:
            articles = await self.newsapi_client.fetch_indian_financial_news(
                max_articles=max_articles,
                hours_back=hours_back
            )
            
            response_time = (datetime.now() - start_time).total_seconds()
            self._update_source_stats("newsapi", len(articles), 0, response_time)
            
            return articles, "NewsAPI"
            
        except Exception as e:
            self._update_source_stats("newsapi", 0, 1)
            raise e
    
    async def _fetch_gnews_news(self, max_articles: int, hours_back: int) -> tuple[List[NewsArticle], str]:
        """Fetch news from GNews."""
        start_time = datetime.now()
        
        try:
            articles = await self.gnews_client.fetch_indian_financial_news(
                max_articles=max_articles,
                hours_back=hours_back
            )
            
            response_time = (datetime.now() - start_time).total_seconds()
            self._update_source_stats("gnews", len(articles), 0, response_time)
            
            return articles, "GNews"
            
        except Exception as e:
            self._update_source_stats("gnews", 0, 1)
            raise e
    
    async def _fetch_breaking_news(self, max_articles: int) -> List[NewsArticle]:
        """Fetch breaking news from all sources."""
        breaking_articles = []
        
        # Try NewsAPI first (better for breaking news)
        if self.source_stats["newsapi"].enabled:
            try:
                articles = await self.newsapi_client.fetch_breaking_news(max_articles // 2)
                breaking_articles.extend(articles)
            except Exception as e:
                logger.warning(f"NewsAPI breaking news failed: {e}")
        
        # Try GNews
        if self.source_stats["gnews"].enabled:
            try:
                articles = await self.gnews_client.fetch_breaking_news(max_articles // 2)
                breaking_articles.extend(articles)
            except Exception as e:
                logger.warning(f"GNews breaking news failed: {e}")
        
        return breaking_articles
    
    async def search_company_news(
        self,
        company_names: List[str],
        max_articles: int = 50,
        hours_back: int = 24
    ) -> NewsAggregationResult:
        """Search for news about specific companies across all sources."""
        
        start_time = datetime.now()
        result = NewsAggregationResult()
        
        # Prepare tasks for parallel company search
        tasks = []
        
        if self.source_stats["rss"].enabled:
            tasks.append(self._search_rss_companies(company_names, max_articles // 3, hours_back))
        
        if self.source_stats["newsapi"].enabled:
            tasks.append(self._search_newsapi_companies(company_names, max_articles // 3, hours_back))
        
        if self.source_stats["gnews"].enabled:
            tasks.append(self._search_gnews_companies(company_names, max_articles // 3, hours_back))
        
        # Execute searches in parallel
        if tasks:
            try:
                results = await asyncio.gather(*tasks, return_exceptions=True)
                
                for i, task_result in enumerate(results):
                    if isinstance(task_result, Exception):
                        source_name = ["rss", "newsapi", "gnews"][i]
                        error_msg = f"{source_name} company search failed: {str(task_result)}"
                        result.errors.append(error_msg)
                    elif isinstance(task_result, tuple):
                        source_articles, source_name = task_result
                        result.sources_used.append(source_name)
                        
                        for article in source_articles:
                            if not self._is_duplicate(article):
                                result.articles.append(article)
                                self._add_to_cache(article)
                            else:
                                result.duplicates_removed += 1
                        
                        result.total_articles += len(source_articles)
                        
            except Exception as e:
                result.errors.append(f"Company search failed: {str(e)}")
        
        # Sort and limit results
        result.articles.sort(key=lambda x: x.published_at, reverse=True)
        if len(result.articles) > max_articles:
            result.articles = result.articles[:max_articles]
        
        result.unique_articles = len(result.articles)
        result.fetch_time_seconds = (datetime.now() - start_time).total_seconds()
        
        return result
    
    async def _search_rss_companies(self, companies: List[str], max_articles: int, hours_back: int) -> tuple[List[NewsArticle], str]:
        """Search RSS feeds for company news."""
        # RSS doesn't support direct company search, so we fetch all and filter
        articles = await self.rss_client.fetch_all_feeds(max_articles, hours_back)
        
        # Filter articles that mention any of the companies
        company_articles = []
        for article in articles:
            article_text = f"{article.title} {article.content}".lower()
            if any(company.lower() in article_text for company in companies):
                company_articles.append(article)
        
        return company_articles, "RSS Feeds"
    
    async def _search_newsapi_companies(self, companies: List[str], max_articles: int, hours_back: int) -> tuple[List[NewsArticle], str]:
        """Search NewsAPI for company news."""
        articles = await self.newsapi_client.search_company_news(companies, max_articles, hours_back)
        return articles, "NewsAPI"
    
    async def _search_gnews_companies(self, companies: List[str], max_articles: int, hours_back: int) -> tuple[List[NewsArticle], str]:
        """Search GNews for company news."""
        articles = await self.gnews_client.search_company_news(companies, max_articles, hours_back)
        return articles, "GNews"
    
    def get_manager_stats(self) -> Dict[str, Any]:
        """Get comprehensive manager statistics."""
        return {
            "sources": {name: {
                "enabled": stats.enabled,
                "articles_fetched": stats.articles_fetched,
                "requests_made": stats.requests_made,
                "errors": stats.errors,
                "last_fetch": stats.last_fetch.isoformat() if stats.last_fetch else None,
                "rate_limit_hits": stats.rate_limit_hits,
                "avg_response_time": stats.avg_response_time
            } for name, stats in self.source_stats.items()},
            "cache": {
                "seen_articles": len(self.seen_articles),
                "cached_articles": len(self.article_cache),
                "deduplication_enabled": self.deduplication_enabled
            },
            "config": {
                "max_articles_per_source": self.max_articles_per_source,
                "similarity_threshold": self.similarity_threshold
            }
        }
    
    def clear_cache(self):
        """Clear the deduplication cache."""
        self.seen_articles.clear()
        self.article_cache.clear()
        logger.info("News deduplication cache cleared")

# Example usage and testing
async def test_api_manager():
    """Test the news API manager."""
    async with NewsAPIManager() as manager:
        print("Testing News API Manager...")
        
        # Get manager stats
        stats = manager.get_manager_stats()
        print(f"Manager Stats: {stats}")
        
        # Test general news fetch
        print("\nFetching general financial news...")
        result = await manager.fetch_all_news(max_articles=10, hours_back=24)
        
        print(f"Aggregation Result:")
        print(f"  Total articles: {result.total_articles}")
        print(f"  Unique articles: {result.unique_articles}")
        print(f"  Duplicates removed: {result.duplicates_removed}")
        print(f"  Sources used: {result.sources_used}")
        print(f"  Fetch time: {result.fetch_time_seconds:.2f}s")
        print(f"  Errors: {result.errors}")
        
        # Display sample articles
        for i, article in enumerate(result.articles[:3]):
            print(f"\nArticle {i+1}:")
            print(f"  Title: {article.title}")
            print(f"  Source: {article.source}")
            print(f"  Published: {article.published_at}")
            print(f"  Tags: {article.tags}")
        
        # Test company search
        print("\nSearching for company news...")
        company_result = await manager.search_company_news(
            company_names=["Reliance", "TCS", "Infosys"],
            max_articles=5
        )
        print(f"Found {company_result.unique_articles} company articles")

if __name__ == "__main__":
    asyncio.run(test_api_manager())
