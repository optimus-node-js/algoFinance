# Indian Market News APIs Research

## 🇮🇳 **BEST FREE NEWS APIs FOR INDIAN MARKETS**

**Research Date:** December 2024  
**Focus:** Indian Stock Market News Sources  
**Requirement:** Free/Low-cost APIs with good coverage

---

## 📰 **RECOMMENDED FREE NEWS APIs**

### **1. NewsAPI.org - PRIMARY CHOICE**
- **URL:** https://newsapi.org/
- **Free Tier:** 60,000 requests/month (2,000/day)
- **Indian Sources:** Economic Times, Business Standard, Hindu BusinessLine, Mint
- **Coverage:** Excellent for Indian financial news
- **Rate Limit:** 1,000 requests/day (free)

**Indian Financial Sources Available:**
- Economic Times (economictimes.indiatimes.com)
- Business Standard (business-standard.com)
- The Hindu BusinessLine (thehindubusinessline.com)
- Mint (livemint.com)
- Financial Express (financialexpress.com)

### **2. GNews API - SECONDARY CHOICE**
- **URL:** https://gnews.io/
- **Free Tier:** 100 requests/day
- **Coverage:** Good Indian news coverage
- **Language:** English and Hindi support
- **Rate Limit:** 100 requests/day (free)

### **3. RSS Feeds - UNLIMITED & FREE**
- **Cost:** Completely Free
- **Rate Limit:** No limits
- **Reliability:** High
- **Coverage:** Excellent for Indian markets

**Major Indian Financial RSS Feeds:**
```bash
# Economic Times
https://economictimes.indiatimes.com/rssfeedstopstories.cms
https://economictimes.indiatimes.com/markets/rssfeeds/1977021501.cms

# Moneycontrol
https://www.moneycontrol.com/rss/business.xml
https://www.moneycontrol.com/rss/results.xml
https://www.moneycontrol.com/rss/marketreports.xml

# Business Standard
https://www.business-standard.com/rss/markets-106.rss
https://www.business-standard.com/rss/finance-103.rss

# Mint (Hindustan Times)
https://www.livemint.com/rss/markets
https://www.livemint.com/rss/companies

# Financial Express
https://www.financialexpress.com/market/rss/
https://www.financialexpress.com/industry/rss/

# Hindu BusinessLine
https://www.thehindubusinessline.com/markets/?service=rss
https://www.thehindubusinessline.com/companies/?service=rss
```

### **4. Alpha Vantage - PREMIUM FEATURES**
- **URL:** https://www.alphavantage.co/
- **Free Tier:** 5 API requests/minute, 500/day
- **Features:** News sentiment analysis included
- **Coverage:** Global + Indian markets
- **Limitation:** Very low rate limits

---

## 🔧 **NEWS AGGREGATION STRATEGY**

### **How Our News Aggregator Will Work:**

#### **1. Multi-Source Data Collection**
```python
# News Sources Priority:
1. RSS Feeds (Primary) - Unlimited, reliable
2. NewsAPI.org (Secondary) - 2,000 requests/day
3. GNews API (Tertiary) - 100 requests/day
4. Alpha Vantage (Premium) - Sentiment analysis
```

#### **2. Stock-Related Filtering Strategy**

**Method 1: Company Name Matching**
```python
# Indian Stock Companies Database
INDIAN_COMPANIES = {
    "RELIANCE": ["Reliance Industries", "RIL", "Mukesh Ambani"],
    "TCS": ["Tata Consultancy Services", "TCS", "Tata"],
    "INFY": ["Infosys", "Infosys Limited", "Narayana Murthy"],
    "HDFCBANK": ["HDFC Bank", "HDFC", "Housing Development"],
    "ICICIBANK": ["ICICI Bank", "ICICI", "Industrial Credit"],
    "HINDUNILVR": ["Hindustan Unilever", "HUL", "Unilever"],
    "ITC": ["ITC Limited", "Indian Tobacco Company"],
    "SBIN": ["State Bank of India", "SBI", "State Bank"],
    "BHARTIARTL": ["Bharti Airtel", "Airtel", "Bharti"],
    "KOTAKBANK": ["Kotak Mahindra Bank", "Kotak Bank"]
}
```

**Method 2: Financial Keywords Filtering**
```python
# Financial Keywords for Indian Markets
FINANCIAL_KEYWORDS = [
    # Market Terms
    "stock market", "share price", "market cap", "BSE", "NSE",
    "Sensex", "Nifty", "equity", "shares", "trading",
    
    # Corporate Actions
    "earnings", "results", "dividend", "bonus", "split",
    "IPO", "FPO", "buyback", "merger", "acquisition",
    
    # Financial Metrics
    "revenue", "profit", "loss", "growth", "quarterly results",
    "annual results", "guidance", "outlook", "forecast",
    
    # Regulatory
    "SEBI", "RBI", "regulatory", "compliance", "listing"
]
```

**Method 3: Sector-Based Filtering**
```python
# Indian Market Sectors
SECTORS = {
    "BANKING": ["bank", "banking", "financial services", "NBFC"],
    "IT": ["software", "technology", "IT services", "digital"],
    "PHARMA": ["pharmaceutical", "drugs", "medicine", "healthcare"],
    "AUTO": ["automobile", "automotive", "cars", "vehicles"],
    "FMCG": ["consumer goods", "FMCG", "retail", "consumer"],
    "ENERGY": ["oil", "gas", "energy", "power", "electricity"],
    "METALS": ["steel", "metals", "mining", "iron", "copper"],
    "TELECOM": ["telecom", "telecommunications", "mobile", "broadband"]
}
```

#### **3. News Processing Pipeline**

```python
# News Aggregation Flow:
1. Fetch Articles → RSS Feeds + APIs
2. Content Filtering → Stock/Financial keywords
3. Company Mapping → Match to stock symbols
4. Relevance Scoring → Rate article importance
5. Duplicate Removal → Avoid duplicate news
6. Sentiment Analysis → Positive/Negative/Neutral
7. Kafka Publishing → Real-time signal distribution
```

---

## 🔑 **ENVIRONMENT CONFIGURATION**

### **Required .env Variables:**

```bash
# News APIs
NEWSAPI_KEY=your_newsapi_key_here
GNEWS_API_KEY=your_gnews_key_here
ALPHA_VANTAGE_KEY=your_alpha_vantage_key_here

# News API URLs
NEWSAPI_URL=https://newsapi.org/v2/everything
GNEWS_URL=https://gnews.io/api/v4/search
ALPHA_VANTAGE_NEWS_URL=https://www.alphavantage.co/query

# RSS Feed Configuration
RSS_FEEDS_ENABLED=true
RSS_UPDATE_INTERVAL=300  # 5 minutes
RSS_MAX_ARTICLES_PER_FEED=50

# News Processing Configuration
NEWS_PROCESSING_ENABLED=true
NEWS_RELEVANCE_THRESHOLD=0.7
NEWS_SENTIMENT_THRESHOLD=0.6
NEWS_CACHE_TTL=3600  # 1 hour

# Kafka Topics for News
KAFKA_NEWS_TOPIC=hft-news-articles
KAFKA_SENTIMENT_TOPIC=hft-sentiment-signals
KAFKA_COMPANY_NEWS_TOPIC=hft-company-news

# Rate Limiting
NEWSAPI_RATE_LIMIT=2000  # per day
GNEWS_RATE_LIMIT=100     # per day
RSS_RATE_LIMIT=0         # unlimited

# Language and Region
NEWS_LANGUAGE=en
NEWS_COUNTRY=in
NEWS_REGION=india
```

---

## 🚀 **IMPLEMENTATION ARCHITECTURE**

### **News Aggregator Service Structure:**

```bash
server/src/sentiment_aggregator/
├── __init__.py
├── news_apis/
│   ├── __init__.py
│   ├── newsapi_client.py       # NewsAPI.org integration
│   ├── gnews_client.py         # GNews API integration
│   ├── rss_client.py           # RSS feeds aggregation
│   ├── alpha_vantage_client.py # Alpha Vantage news
│   └── api_manager.py          # Multi-API coordination
├── data_processing/
│   ├── __init__.py
│   ├── news_filter.py          # Stock-related filtering
│   ├── company_mapper.py       # Company name → ticker mapping
│   ├── relevance_scorer.py     # Article relevance scoring
│   ├── duplicate_filter.py     # Remove duplicate articles
│   └── data_normalizer.py      # Standardize article format
├── nlp_pipeline/
│   ├── __init__.py
│   ├── sentiment_analyzer.py   # Sentiment scoring
│   ├── keyword_extractor.py    # Financial keyword extraction
│   ├── entity_recognizer.py    # Named entity recognition
│   └── confidence_scorer.py    # Sentiment confidence
├── signal_publisher.py         # Kafka signal publishing
├── news_cache.py              # Redis caching
├── monitoring.py              # Performance monitoring
└── main.py                    # News aggregator service
```

### **Data Flow:**

```
RSS Feeds + APIs → Content Filtering → Company Mapping → 
Relevance Scoring → Duplicate Removal → Sentiment Analysis → 
Kafka Publishing → Strategy Engine Consumption
```

---

## 📊 **EXPECTED PERFORMANCE**

### **Daily News Processing Capacity:**
- **RSS Feeds:** 5,000+ articles/day (unlimited)
- **NewsAPI:** 2,000 articles/day (free tier)
- **GNews:** 100 articles/day (free tier)
- **Total:** 7,000+ articles/day

### **Processing Speed:**
- **Article Filtering:** <10ms per article
- **Sentiment Analysis:** <50ms per article
- **Company Mapping:** <5ms per article
- **Total Processing:** <100ms per article

### **Coverage:**
- **500+ Indian stocks** with news coverage
- **Real-time processing** within 5 minutes of publication
- **Multi-language support** (English + Hindi)
- **Sector-wise coverage** across all major sectors

---

## 🎯 **NEXT STEPS**

### **Phase 1: Setup (Days 1-2)**
1. **API Registration:** Get free API keys
2. **Environment Configuration:** Setup .env variables
3. **RSS Feed Testing:** Validate RSS feed URLs
4. **Basic Integration:** Test API connectivity

### **Phase 2: Implementation (Days 3-7)**
1. **News Clients:** Build API client classes
2. **Filtering Logic:** Implement stock-related filtering
3. **Company Database:** Create Indian companies mapping
4. **Data Pipeline:** Build processing pipeline

### **Phase 3: Integration (Days 8-10)**
1. **Kafka Integration:** Publish news signals
2. **Sentiment Analysis:** Basic sentiment scoring
3. **Caching Layer:** Redis caching for performance
4. **Monitoring:** Performance and error monitoring

**🚀 Ready to implement the Indian market news aggregation system!**
