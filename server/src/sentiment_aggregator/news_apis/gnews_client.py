"""
GNews Client for Indian Financial News
=====================================

GNews API integration for Indian stock market news.
Provides 100 requests/day free tier with multi-language support.
"""

import asyncio
import aiohttp
import logging
import time
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import hashlib

from ..config import config
from .rss_client import NewsArticle

logger = logging.getLogger(__name__)

@dataclass
class GNewsResponse:
    """GNews API response structure."""
    total_articles: int
    articles: List[Dict[str, Any]]
    error: Optional[str] = None

class GNewsClient:
    """GNews API client for Indian financial news."""
    
    def __init__(self):
        """Initialize GNews client."""
        self.api_key = config.gnews_key
        self.base_url = config.gnews_url
        self.rate_limit = config.gnews_rate_limit
        self.enabled = config.gnews_enabled and bool(self.api_key)
        
        # Rate limiting
        self.request_count = 0
        self.last_reset = time.time()
        self.session = None
        
        # Search parameters for Indian markets
        self.default_params = {
            "country": "in",  # India
            "lang": "en",     # English
            "max": 10,        # Articles per request
            "sortby": "publishedAt"
        }
        
        # Financial keywords optimized for Indian markets
        self.financial_keywords = [
            "stock market", "share price", "BSE", "NSE", "Sensex", "Nifty",
            "earnings", "results", "dividend", "IPO", "merger", "acquisition"
        ]
        
        if not self.enabled:
            logger.warning("GNews client disabled - missing API key or disabled in config")
        else:
            logger.info(f"GNews client initialized - {self.rate_limit} requests/day limit")
    
    async def __aenter__(self):
        """Async context manager entry."""
        if self.enabled:
            self.session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=30)
            )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.session:
            await self.session.close()
    
    def _check_rate_limit(self) -> bool:
        """Check if we can make a request within rate limits."""
        if not self.enabled:
            return False
        
        current_time = time.time()
        
        # Reset counter daily
        if current_time - self.last_reset > 86400:  # 24 hours
            self.request_count = 0
            self.last_reset = current_time
        
        return self.request_count < self.rate_limit
    
    def _increment_request_count(self):
        """Increment request counter."""
        self.request_count += 1
    
    async def _make_request(self, params: Dict[str, Any]) -> Optional[GNewsResponse]:
        """Make request to GNews API."""
        if not self.enabled or not self.session:
            return None
        
        if not self._check_rate_limit():
            logger.warning("GNews rate limit exceeded")
            return None
        
        # Add API key to params
        params["apikey"] = self.api_key
        
        try:
            async with self.session.get(self.base_url, params=params) as response:
                self._increment_request_count()
                
                if response.status == 200:
                    data = await response.json()
                    return GNewsResponse(
                        total_articles=data.get("totalArticles", 0),
                        articles=data.get("articles", [])
                    )
                elif response.status == 429:
                    logger.warning("GNews rate limit hit")
                    return GNewsResponse(
                        total_articles=0,
                        articles=[],
                        error="Rate limit exceeded"
                    )
                else:
                    error_text = await response.text()
                    logger.error(f"GNews error {response.status}: {error_text}")
                    return GNewsResponse(
                        total_articles=0,
                        articles=[],
                        error=f"HTTP {response.status}: {error_text}"
                    )
                    
        except Exception as e:
            logger.error(f"GNews request failed: {e}")
            return None
    
    async def search_news(
        self,
        query: str,
        max_articles: int = 10,
        country: str = "in",
        language: str = "en",
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None
    ) -> List[NewsArticle]:
        """Search for news articles."""
        
        params = {
            "q": query,
            "country": country,
            "lang": language,
            "max": min(max_articles, 100),  # GNews max is 100
            "sortby": "publishedAt"
        }
        
        # Add date filters if provided
        if from_date:
            params["from"] = from_date.strftime("%Y-%m-%dT%H:%M:%SZ")
        
        if to_date:
            params["to"] = to_date.strftime("%Y-%m-%dT%H:%M:%SZ")
        
        response = await self._make_request(params)
        
        if not response or response.error:
            logger.warning(f"GNews search failed: {response.error if response else 'No response'}")
            return []
        
        articles = []
        for article_data in response.articles:
            article = self._parse_gnews_article(article_data)
            if article:
                articles.append(article)
        
        logger.info(f"GNews returned {len(articles)} articles for query: {query}")
        return articles
    
    def _parse_gnews_article(self, article_data: Dict[str, Any]) -> Optional[NewsArticle]:
        """Parse GNews article data into NewsArticle."""
        try:
            title = article_data.get("title", "").strip()
            if not title:
                return None
            
            content = article_data.get("content", "") or article_data.get("description", "")
            
            url = article_data.get("url", "")
            if not url:
                return None
            
            # Parse published date
            published_str = article_data.get("publishedAt", "")
            try:
                published_at = datetime.fromisoformat(published_str.replace('Z', '+00:00'))
            except:
                published_at = datetime.now(timezone.utc)
            
            # Extract source
            source_data = article_data.get("source", {})
            source = source_data.get("name", "GNews")
            
            # Generate article ID
            article_id = f"gnews_{hashlib.md5(f'{title}{url}{published_at}'.encode()).hexdigest()[:12]}"
            
            return NewsArticle(
                title=title,
                content=content,
                url=url,
                source=source,
                published_at=published_at,
                article_id=article_id,
                tags=["gnews", "india"]
            )
            
        except Exception as e:
            logger.error(f"Error parsing GNews article: {e}")
            return None
    
    async def fetch_indian_financial_news(
        self,
        max_articles: int = 10,
        hours_back: int = 24
    ) -> List[NewsArticle]:
        """Fetch Indian financial news from the last N hours."""
        
        if not self.enabled:
            logger.info("GNews disabled - skipping fetch")
            return []
        
        # Calculate date range
        to_date = datetime.now(timezone.utc)
        from_date = to_date - timedelta(hours=hours_back)
        
        # Build financial query
        financial_terms = ["stock market", "share price", "BSE", "NSE", "earnings"]
        query = " OR ".join(financial_terms[:3])  # Limit query complexity
        
        articles = await self.search_news(
            query=query,
            max_articles=max_articles,
            country="in",
            language="en",
            from_date=from_date,
            to_date=to_date
        )
        
        return articles
    
    async def search_company_news(
        self,
        company_names: List[str],
        max_articles: int = 10,
        hours_back: int = 24
    ) -> List[NewsArticle]:
        """Search for news about specific companies."""
        
        if not self.enabled or not company_names:
            return []
        
        # Calculate date range
        to_date = datetime.now(timezone.utc)
        from_date = to_date - timedelta(hours=hours_back)
        
        # Build company query (limit to avoid long queries)
        company_query = " OR ".join(company_names[:3])
        
        articles = await self.search_news(
            query=company_query,
            max_articles=max_articles,
            country="in",
            language="en",
            from_date=from_date,
            to_date=to_date
        )
        
        return articles
    
    def get_client_stats(self) -> Dict[str, Any]:
        """Get GNews client statistics."""
        return {
            "enabled": self.enabled,
            "api_key_configured": bool(self.api_key),
            "rate_limit": self.rate_limit,
            "requests_used": self.request_count,
            "requests_remaining": max(0, self.rate_limit - self.request_count),
            "last_reset": self.last_reset,
            "default_country": self.default_params["country"],
            "default_language": self.default_params["lang"],
            "financial_keywords": len(self.financial_keywords)
        }

# Example usage and testing
async def test_gnews_client():
    """Test GNews client functionality."""
    async with GNewsClient() as client:
        print("Testing GNews Client...")
        
        # Get client stats
        stats = client.get_client_stats()
        print(f"GNews Stats: {stats}")
        
        if not client.enabled:
            print("GNews client disabled - add GNEWS_API_KEY to .env file")
            return
        
        # Test Indian financial news
        print("\nFetching Indian financial news...")
        articles = await client.fetch_indian_financial_news(max_articles=3)
        print(f"Fetched {len(articles)} articles")
        
        # Display sample articles
        for i, article in enumerate(articles):
            print(f"\nArticle {i+1}:")
            print(f"Title: {article.title}")
            print(f"Source: {article.source}")
            print(f"Published: {article.published_at}")
            print(f"URL: {article.url}")

if __name__ == "__main__":
    asyncio.run(test_gnews_client())
