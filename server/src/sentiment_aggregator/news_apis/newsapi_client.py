"""
NewsAPI Client for Indian Financial News
=======================================

NewsAPI.org integration for Indian stock market news.
Provides 2,000 requests/day free tier with access to major Indian financial sources.
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
class NewsAPIResponse:
    """NewsAPI response structure."""
    status: str
    total_results: int
    articles: List[Dict[str, Any]]
    error_code: Optional[str] = None
    error_message: Optional[str] = None

class NewsAPIClient:
    """NewsAPI.org client for Indian financial news."""
    
    def __init__(self):
        """Initialize NewsAPI client."""
        self.api_key = config.newsapi_key
        self.base_url = config.newsapi_url
        self.rate_limit = config.newsapi_rate_limit
        self.enabled = config.newsapi_enabled and bool(self.api_key)
        
        # Rate limiting
        self.request_count = 0
        self.last_reset = time.time()
        self.session = None
        
        # Indian financial sources
        self.indian_sources = [
            "the-times-of-india",
            "the-hindu", 
            "business-standard",
            "financial-express"
        ]
        
        # Financial keywords for Indian markets
        self.financial_keywords = [
            "stock market", "share price", "BSE", "NSE", "Sensex", "Nifty",
            "earnings", "results", "dividend", "IPO", "merger", "acquisition",
            "revenue", "profit", "quarterly results", "SEBI", "RBI"
        ]
        
        if not self.enabled:
            logger.warning("NewsAPI client disabled - missing API key or disabled in config")
        else:
            logger.info(f"NewsAPI client initialized - {self.rate_limit} requests/day limit")
    
    async def __aenter__(self):
        """Async context manager entry."""
        if self.enabled:
            self.session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=30),
                headers={"X-API-Key": self.api_key}
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
    
    async def _make_request(self, params: Dict[str, Any]) -> Optional[NewsAPIResponse]:
        """Make request to NewsAPI."""
        if not self.enabled or not self.session:
            return None
        
        if not self._check_rate_limit():
            logger.warning("NewsAPI rate limit exceeded")
            return None
        
        try:
            async with self.session.get(self.base_url, params=params) as response:
                self._increment_request_count()
                
                if response.status == 200:
                    data = await response.json()
                    return NewsAPIResponse(
                        status=data.get("status", "error"),
                        total_results=data.get("totalResults", 0),
                        articles=data.get("articles", [])
                    )
                elif response.status == 429:
                    logger.warning("NewsAPI rate limit hit")
                    return NewsAPIResponse(
                        status="error",
                        total_results=0,
                        articles=[],
                        error_code="rateLimitExceeded",
                        error_message="Rate limit exceeded"
                    )
                else:
                    error_data = await response.json()
                    logger.error(f"NewsAPI error {response.status}: {error_data}")
                    return NewsAPIResponse(
                        status="error",
                        total_results=0,
                        articles=[],
                        error_code=error_data.get("code"),
                        error_message=error_data.get("message")
                    )
                    
        except Exception as e:
            logger.error(f"NewsAPI request failed: {e}")
            return None
    
    async def search_everything(
        self,
        query: str,
        sources: Optional[List[str]] = None,
        domains: Optional[List[str]] = None,
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None,
        language: str = "en",
        sort_by: str = "publishedAt",
        page_size: int = 100
    ) -> List[NewsArticle]:
        """Search for articles using everything endpoint."""
        
        params = {
            "q": query,
            "language": language,
            "sortBy": sort_by,
            "pageSize": min(page_size, 100)  # Max 100 per request
        }
        
        if sources:
            params["sources"] = ",".join(sources)
        
        if domains:
            params["domains"] = ",".join(domains)
        
        if from_date:
            params["from"] = from_date.isoformat()
        
        if to_date:
            params["to"] = to_date.isoformat()
        
        response = await self._make_request(params)
        
        if not response or response.status != "ok":
            logger.warning(f"NewsAPI search failed: {response.error_message if response else 'No response'}")
            return []
        
        articles = []
        for article_data in response.articles:
            article = self._parse_newsapi_article(article_data)
            if article:
                articles.append(article)
        
        logger.info(f"NewsAPI returned {len(articles)} articles for query: {query}")
        return articles
    
    def _parse_newsapi_article(self, article_data: Dict[str, Any]) -> Optional[NewsArticle]:
        """Parse NewsAPI article data into NewsArticle."""
        try:
            title = article_data.get("title", "").strip()
            if not title or title.lower() == "[removed]":
                return None
            
            content = article_data.get("content", "") or article_data.get("description", "")
            if not content or content.lower() == "[removed]":
                content = article_data.get("description", "")
            
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
            source = source_data.get("name", "NewsAPI")
            
            # Extract author
            author = article_data.get("author")
            
            # Generate article ID
            article_id = f"newsapi_{hashlib.md5(f'{title}{url}{published_at}'.encode()).hexdigest()[:12]}"
            
            return NewsArticle(
                title=title,
                content=content,
                url=url,
                source=source,
                published_at=published_at,
                author=author,
                article_id=article_id,
                tags=["newsapi"]
            )
            
        except Exception as e:
            logger.error(f"Error parsing NewsAPI article: {e}")
            return None
    
    async def fetch_indian_financial_news(
        self,
        max_articles: int = 100,
        hours_back: int = 24
    ) -> List[NewsArticle]:
        """Fetch Indian financial news from the last N hours."""
        
        if not self.enabled:
            logger.info("NewsAPI disabled - skipping fetch")
            return []
        
        # Calculate date range
        to_date = datetime.now(timezone.utc)
        from_date = to_date - timedelta(hours=hours_back)
        
        # Build query for Indian financial news
        query_parts = [
            "(India OR Indian)",
            "AND",
            f"({' OR '.join(self.financial_keywords[:5])})"  # Limit query length
        ]
        query = " ".join(query_parts)
        
        # Indian domains for better targeting
        indian_domains = [
            "economictimes.indiatimes.com",
            "business-standard.com", 
            "livemint.com",
            "financialexpress.com",
            "moneycontrol.com"
        ]
        
        articles = await self.search_everything(
            query=query,
            domains=indian_domains,
            from_date=from_date,
            to_date=to_date,
            page_size=max_articles
        )
        
        return articles
    
    async def search_company_news(
        self,
        company_names: List[str],
        max_articles: int = 50,
        hours_back: int = 24
    ) -> List[NewsArticle]:
        """Search for news about specific companies."""
        
        if not self.enabled or not company_names:
            return []
        
        # Calculate date range
        to_date = datetime.now(timezone.utc)
        from_date = to_date - timedelta(hours=hours_back)
        
        # Build query with company names
        company_query = " OR ".join(f'"{name}"' for name in company_names[:5])  # Limit companies
        query = f"({company_query}) AND (India OR Indian)"
        
        articles = await self.search_everything(
            query=query,
            from_date=from_date,
            to_date=to_date,
            page_size=max_articles
        )
        
        return articles
    
    async def fetch_breaking_news(self, max_articles: int = 20) -> List[NewsArticle]:
        """Fetch breaking financial news from India."""
        
        if not self.enabled:
            return []
        
        # Recent news (last 2 hours)
        to_date = datetime.now(timezone.utc)
        from_date = to_date - timedelta(hours=2)
        
        # Breaking news keywords
        breaking_keywords = [
            "breaking", "urgent", "alert", "announces", "reports",
            "earnings", "results", "merger", "acquisition"
        ]
        
        query = f"India AND ({' OR '.join(breaking_keywords[:3])})"
        
        articles = await self.search_everything(
            query=query,
            from_date=from_date,
            to_date=to_date,
            sort_by="publishedAt",
            page_size=max_articles
        )
        
        return articles
    
    def get_client_stats(self) -> Dict[str, Any]:
        """Get NewsAPI client statistics."""
        return {
            "enabled": self.enabled,
            "api_key_configured": bool(self.api_key),
            "rate_limit": self.rate_limit,
            "requests_used": self.request_count,
            "requests_remaining": max(0, self.rate_limit - self.request_count),
            "last_reset": self.last_reset,
            "indian_sources": len(self.indian_sources),
            "financial_keywords": len(self.financial_keywords)
        }

# Example usage and testing
async def test_newsapi_client():
    """Test NewsAPI client functionality."""
    async with NewsAPIClient() as client:
        print("Testing NewsAPI Client...")
        
        # Get client stats
        stats = client.get_client_stats()
        print(f"NewsAPI Stats: {stats}")
        
        if not client.enabled:
            print("NewsAPI client disabled - add NEWSAPI_KEY to .env file")
            return
        
        # Test Indian financial news
        print("\nFetching Indian financial news...")
        articles = await client.fetch_indian_financial_news(max_articles=5)
        print(f"Fetched {len(articles)} articles")
        
        # Display sample articles
        for i, article in enumerate(articles[:3]):
            print(f"\nArticle {i+1}:")
            print(f"Title: {article.title}")
            print(f"Source: {article.source}")
            print(f"Published: {article.published_at}")
            print(f"URL: {article.url}")
            print(f"Content: {article.content[:200]}...")
        
        # Test company search
        print("\nSearching for company news...")
        company_articles = await client.search_company_news(
            company_names=["Reliance", "TCS", "Infosys"],
            max_articles=3
        )
        print(f"Found {len(company_articles)} company articles")

if __name__ == "__main__":
    asyncio.run(test_newsapi_client())