"""
RSS Client for Indian Financial News
====================================

Primary news source - unlimited and free RSS feeds from major Indian financial news sources.
Handles RSS feed parsing, caching, and data normalization.
"""

import asyncio
import aiohttp
import feedparser
import logging
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import hashlib
import time

from ..config import config

logger = logging.getLogger(__name__)

@dataclass
class NewsArticle:
    """Standardized news article data structure."""
    title: str
    content: str
    url: str
    source: str
    published_at: datetime
    author: Optional[str] = None
    summary: Optional[str] = None
    tags: List[str] = None
    article_id: Optional[str] = None
    
    def __post_init__(self):
        """Generate article ID and initialize tags."""
        if not self.article_id:
            # Generate unique ID from title + url + published_at
            content_hash = hashlib.md5(
                f"{self.title}{self.url}{self.published_at}".encode()
            ).hexdigest()[:12]
            self.article_id = f"rss_{content_hash}"
        
        if self.tags is None:
            self.tags = []

class RSSClient:
    """RSS feed client for Indian financial news sources."""
    
    def __init__(self):
        """Initialize RSS client with configuration."""
        self.feeds = self._get_active_feeds()
        self.session = None
        self.last_fetch_times = {}
        self.article_cache = {}
        
        logger.info(f"RSS Client initialized with {len(self.feeds)} feeds")
    
    def _get_active_feeds(self) -> Dict[str, List[str]]:
        """Get active RSS feeds from configuration."""
        all_feeds = config.rss_feeds
        active_feeds = {}
        
        for source, feed_urls in all_feeds.items():
            # Filter out empty URLs
            active_urls = [url for url in feed_urls if url.strip()]
            if active_urls:
                active_feeds[source] = active_urls
                logger.info(f"Added {len(active_urls)} feeds for {source}")
        
        return active_feeds
    
    async def __aenter__(self):
        """Async context manager entry."""
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=config.rss_timeout)
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.session:
            await self.session.close()
    
    async def fetch_feed(self, feed_url: str, source: str) -> List[NewsArticle]:
        """Fetch and parse a single RSS feed."""
        try:
            logger.debug(f"Fetching RSS feed: {feed_url}")
            
            # Check rate limiting
            if not self._can_fetch_feed(feed_url):
                logger.debug(f"Rate limited: {feed_url}")
                return []
            
            async with self.session.get(feed_url) as response:
                if response.status != 200:
                    logger.warning(f"RSS feed returned {response.status}: {feed_url}")
                    return []
                
                content = await response.text()
                
            # Parse RSS feed
            feed = feedparser.parse(content)
            
            if feed.bozo:
                logger.warning(f"RSS feed parsing issues: {feed_url}")
            
            articles = []
            max_articles = config.rss_max_articles_per_feed
            
            for entry in feed.entries[:max_articles]:
                try:
                    article = self._parse_rss_entry(entry, source, feed_url)
                    if article and not self._is_duplicate(article):
                        articles.append(article)
                        self.article_cache[article.article_id] = article
                except Exception as e:
                    logger.error(f"Error parsing RSS entry: {e}")
                    continue
            
            # Update last fetch time
            self.last_fetch_times[feed_url] = time.time()
            
            logger.info(f"Fetched {len(articles)} articles from {source}")
            return articles
            
        except asyncio.TimeoutError:
            logger.warning(f"Timeout fetching RSS feed: {feed_url}")
            return []
        except Exception as e:
            logger.error(f"Error fetching RSS feed {feed_url}: {e}")
            return []
    
    def _parse_rss_entry(self, entry, source: str, feed_url: str) -> Optional[NewsArticle]:
        """Parse a single RSS entry into NewsArticle."""
        try:
            # Extract title
            title = getattr(entry, 'title', '').strip()
            if not title:
                return None
            
            # Extract content
            content = ''
            if hasattr(entry, 'content') and entry.content:
                content = entry.content[0].value if isinstance(entry.content, list) else entry.content
            elif hasattr(entry, 'description'):
                content = entry.description
            elif hasattr(entry, 'summary'):
                content = entry.summary
            
            # Clean HTML tags from content
            content = self._clean_html(content)
            
            # Extract URL
            url = getattr(entry, 'link', '')
            if not url:
                return None
            
            # Extract published date
            published_at = self._parse_date(entry)
            
            # Extract author
            author = getattr(entry, 'author', None)
            
            # Extract summary
            summary = getattr(entry, 'summary', None)
            if summary:
                summary = self._clean_html(summary)
            
            # Extract tags
            tags = []
            if hasattr(entry, 'tags'):
                tags = [tag.term for tag in entry.tags if hasattr(tag, 'term')]
            
            return NewsArticle(
                title=title,
                content=content,
                url=url,
                source=source,
                published_at=published_at,
                author=author,
                summary=summary,
                tags=tags
            )
            
        except Exception as e:
            logger.error(f"Error parsing RSS entry: {e}")
            return None
    
    def _parse_date(self, entry) -> datetime:
        """Parse published date from RSS entry."""
        try:
            # Try different date fields
            date_fields = ['published_parsed', 'updated_parsed', 'created_parsed']
            
            for field in date_fields:
                if hasattr(entry, field) and getattr(entry, field):
                    time_struct = getattr(entry, field)
                    return datetime(*time_struct[:6], tzinfo=timezone.utc)
            
            # Fallback to string parsing
            date_strings = ['published', 'updated', 'created']
            for field in date_strings:
                if hasattr(entry, field) and getattr(entry, field):
                    date_str = getattr(entry, field)
                    # Try to parse the date string
                    try:
                        return datetime.fromisoformat(date_str.replace('Z', '+00:00'))
                    except:
                        continue
            
            # Default to current time
            return datetime.now(timezone.utc)
            
        except Exception as e:
            logger.warning(f"Error parsing date: {e}")
            return datetime.now(timezone.utc)
    
    def _clean_html(self, text: str) -> str:
        """Remove HTML tags and clean text."""
        if not text:
            return ""
        
        # Simple HTML tag removal (can be enhanced with BeautifulSoup if needed)
        import re
        clean_text = re.sub(r'<[^>]+>', '', text)
        clean_text = re.sub(r'\s+', ' ', clean_text).strip()
        
        return clean_text
    
    def _can_fetch_feed(self, feed_url: str) -> bool:
        """Check if we can fetch the feed (rate limiting)."""
        last_fetch = self.last_fetch_times.get(feed_url, 0)
        time_since_last = time.time() - last_fetch
        
        return time_since_last >= config.rss_update_interval
    
    def _is_duplicate(self, article: NewsArticle) -> bool:
        """Check if article is a duplicate."""
        return article.article_id in self.article_cache
    
    async def fetch_all_feeds(self) -> List[NewsArticle]:
        """Fetch articles from all RSS feeds."""
        all_articles = []
        
        if not self.session:
            logger.error("RSS client session not initialized")
            return []
        
        # Create tasks for all feeds
        tasks = []
        for source, feed_urls in self.feeds.items():
            for feed_url in feed_urls:
                task = self.fetch_feed(feed_url, source)
                tasks.append(task)
        
        # Execute all tasks concurrently
        try:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for result in results:
                if isinstance(result, Exception):
                    logger.error(f"RSS fetch error: {result}")
                elif isinstance(result, list):
                    all_articles.extend(result)
            
            logger.info(f"Total articles fetched from RSS: {len(all_articles)}")
            return all_articles
            
        except Exception as e:
            logger.error(f"Error fetching RSS feeds: {e}")
            return []
    
    async def fetch_latest_articles(self, max_articles: Optional[int] = None) -> List[NewsArticle]:
        """Fetch latest articles with optional limit."""
        articles = await self.fetch_all_feeds()
        
        if max_articles:
            # Sort by published date and limit
            articles.sort(key=lambda x: x.published_at, reverse=True)
            articles = articles[:max_articles]
        
        return articles
    
    def get_feed_stats(self) -> Dict[str, Any]:
        """Get RSS feed statistics."""
        total_feeds = sum(len(urls) for urls in self.feeds.values())
        cached_articles = len(self.article_cache)
        
        return {
            "total_feeds": total_feeds,
            "active_sources": len(self.feeds),
            "cached_articles": cached_articles,
            "last_fetch_times": len(self.last_fetch_times),
            "sources": list(self.feeds.keys())
        }

# Example usage and testing
async def test_rss_client():
    """Test RSS client functionality."""
    async with RSSClient() as rss_client:
        print("Testing RSS Client...")
        
        # Get stats
        stats = rss_client.get_feed_stats()
        print(f"RSS Stats: {stats}")
        
        # Fetch latest articles
        articles = await rss_client.fetch_latest_articles(max_articles=10)
        print(f"Fetched {len(articles)} articles")
        
        # Display sample articles
        for i, article in enumerate(articles[:3]):
            print(f"\nArticle {i+1}:")
            print(f"Title: {article.title}")
            print(f"Source: {article.source}")
            print(f"Published: {article.published_at}")
            print(f"URL: {article.url}")
            print(f"Content: {article.content[:200]}...")

if __name__ == "__main__":
    asyncio.run(test_rss_client())
