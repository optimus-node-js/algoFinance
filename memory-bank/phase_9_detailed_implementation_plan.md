# Phase 9: Sentiment Analysis Implementation Plan
## Detailed Technical Roadmap

### 🎯 **OVERVIEW**
Complete the remaining 10% of the Sentiment Aggregator Service with advanced ML capabilities, comprehensive Indian stock market integration, and production-ready sentiment analysis.

---

## 📋 **IMPLEMENTATION ROADMAP**

### **Week 1: Enhanced Company Mapper & Stock Integration**

#### **1.1 Company Mapper Enhancement**
**Current Status**: Basic implementation exists
**Target**: Production-ready company-to-symbol mapping

**Key Components:**
- **NSE/BSE Company Database**: 3,000+ companies with aliases
- **Fuzzy Matching**: Handle variations like "Reliance" vs "RIL" vs "Reliance Industries"
- **Sector Classification**: Auto-categorize by industry (IT, Banking, Pharma, etc.)
- **Real-time Updates**: Sync with live NSE/BSE data

**Python Packages to Integrate:**
```python
# Primary packages for Indian stock data
pip install nsepy indstocks yfinance
pip install fuzzywuzzy python-levenshtein
pip install pandas numpy
```

**Implementation Files:**
- `enhanced_company_mapper.py` - Advanced mapping with ML
- `stock_data_fetcher.py` - Real-time NSE/BSE integration
- `company_database.json` - Comprehensive company database

#### **1.2 Stock Market Data Integration**
**Packages & Use Cases:**

1. **`nsepy`** - NSE Official Data
   - Historical stock prices
   - Live market indices (Nifty, Sensex)
   - Corporate actions & dividends
   - **Use**: Validate company mappings, price correlation

2. **`indstocks`** - Comprehensive Indian Market Data
   - Real-time stock prices
   - Company fundamentals
   - Financial statements
   - Market depth data
   - **Use**: Enrich news context, validate sentiment impact

3. **`yfinance`** - Global Financial Data
   - Indian stocks with .NS/.BO suffixes
   - Historical data for backtesting
   - Options & derivatives data
   - **Use**: Cross-validation, international exposure

4. **`TA-Lib`** - Technical Analysis
   - RSI, MACD, Bollinger Bands
   - Volume indicators
   - Trend analysis
   - **Use**: Correlate sentiment with technical signals

---

### **Week 2: Intelligent News Filtering System**

#### **2.1 Relevance Scoring Algorithm**
**Multi-factor Scoring System:**

```python
Relevance Score = (
    0.3 × Financial_Keywords_Score +
    0.2 × Company_Mention_Score +
    0.2 × Source_Credibility_Score +
    0.15 × Recency_Score +
    0.1 × Market_Hours_Score +
    0.05 × Article_Length_Score
)
```

**Key Features:**
- **Financial Keywords**: "earnings", "revenue", "profit", "loss", "merger", "IPO"
- **Source Credibility**: Economic Times (0.9), Mint (0.85), Business Standard (0.8)
- **Market Hours Boost**: Higher scores during trading hours
- **Company Context**: Direct mentions vs indirect references

#### **2.2 Advanced Filtering Mechanisms**
- **Duplicate Detection**: Content similarity using TF-IDF
- **Spam Filtering**: Remove promotional/advertisement content
- **Language Processing**: Handle Hindi company names, transliteration
- **Market Impact Assessment**: Filter based on potential price impact

**Implementation Files:**
- `news_relevance_scorer.py` - Multi-factor scoring
- `content_filter.py` - Spam/duplicate detection
- `market_impact_analyzer.py` - Impact assessment

---

### **Week 3: Advanced Sentiment Analysis Model**

#### **3.1 FinBERT Integration**
**Model Selection**: FinBERT (Financial BERT) - State-of-the-art for financial sentiment

**Key Features:**
- **Pre-trained**: On financial news corpus
- **Fine-tuned**: For Indian market terminology
- **Multi-class**: Positive, Negative, Neutral with confidence scores
- **Context-aware**: Understands financial jargon

**Python Packages:**
```python
pip install transformers torch
pip install sentence-transformers
pip install scikit-learn joblib
pip install nltk spacy
```

#### **3.2 Indian Market Adaptation**
**Custom Training Data:**
- Indian financial news corpus (10K+ articles)
- Manual labeling for Indian context
- Company-specific sentiment patterns
- Sector-wise sentiment variations

**Model Architecture:**
```
Input: News Article Text
↓
FinBERT Tokenization
↓
Transformer Layers (12 layers)
↓
Classification Head
↓
Output: [Positive: 0.7, Negative: 0.2, Neutral: 0.1]
```

#### **3.3 ML Pipeline Implementation**
**Components:**
- **Model Serving**: ONNX for <50ms inference
- **Batch Processing**: Process multiple articles simultaneously
- **Caching**: Redis cache for repeated content
- **Fallback**: Rule-based sentiment for model failures

**Implementation Files:**
- `finbert_sentiment_model.py` - Core model implementation
- `ml_inference_pipeline.py` - Production inference pipeline
- `model_trainer.py` - Training and fine-tuning scripts
- `sentiment_cache.py` - Redis-based caching

---

### **Week 4: Production Integration & Testing**

#### **4.1 Service Integration**
**Database Schema Updates:**
```sql
-- Add sentiment analysis results
ALTER TABLE news_articles ADD COLUMN sentiment_score DECIMAL(3,2);
ALTER TABLE news_articles ADD COLUMN sentiment_label VARCHAR(20);
ALTER TABLE news_articles ADD COLUMN confidence_score DECIMAL(3,2);
ALTER TABLE news_articles ADD COLUMN relevance_score DECIMAL(3,2);
```

**Kafka Topics Enhancement:**
- `hft-sentiment-analysis-results` - ML model outputs
- `hft-sentiment-trading-signals` - Actionable trading signals
- `hft-sentiment-model-health` - Model performance metrics

#### **4.2 Performance Optimization**
**Targets:**
- **Latency**: <100ms per article analysis
- **Throughput**: 1000+ articles/minute
- **Accuracy**: >85% sentiment classification
- **Availability**: 99.9% uptime

**Optimization Techniques:**
- **Model Quantization**: Reduce model size by 75%
- **Batch Processing**: Process 50 articles simultaneously
- **Async Processing**: Non-blocking sentiment analysis
- **Load Balancing**: Multiple model instances

---

## 🔧 **TECHNICAL ARCHITECTURE**

### **Enhanced Service Flow:**
```
News Articles (RSS/API)
↓
Company Mapper (Enhanced)
↓
Relevance Filtering (Multi-factor)
↓
Sentiment Analysis (FinBERT)
↓
Trading Signal Generation
↓
Kafka → Strategy Engine → Angel One API
```

### **Database Integration:**
```python
# Store enhanced results
await prisma_service.news_article.create({
    "title": article.title,
    "content": article.content,
    "company_symbol": mapped_symbol,
    "sentiment_score": sentiment_result.score,
    "sentiment_label": sentiment_result.label,
    "confidence_score": sentiment_result.confidence,
    "relevance_score": relevance_score,
    "market_impact": impact_assessment
})
```

### **Redis Caching Strategy:**
```python
# Cache sentiment results
cache_key = f"sentiment:{article_hash}"
cached_result = await redis_manager.get(cache_key)
if not cached_result:
    sentiment = await finbert_model.analyze(article.content)
    await redis_manager.set(cache_key, sentiment, expire=3600)
```

---

## 📊 **EXPECTED OUTCOMES**

### **Performance Metrics:**
- **News Processing**: 5,000+ articles/day
- **Company Mapping**: 95%+ accuracy
- **Sentiment Analysis**: 85%+ accuracy
- **Relevance Filtering**: 80% noise reduction
- **Trading Signals**: 50+ signals/day

### **Business Impact:**
- **Real-time Sentiment**: Live market sentiment tracking
- **Trading Automation**: Sentiment-driven trade execution
- **Risk Management**: Early warning system for negative sentiment
- **Portfolio Optimization**: Sentiment-weighted position sizing

---

## 🚀 **INTEGRATION WITH EXISTING SERVICES**

### **Angel One API Integration:**
```python
# Generate trading signal from sentiment
if sentiment_score > 0.7 and confidence > 0.8:
    signal = {
        "symbol": company_symbol,
        "action": "BUY",
        "sentiment_score": sentiment_score,
        "confidence": confidence,
        "quantity": calculate_position_size(sentiment_score)
    }
    await angel_one_api.place_order(signal)
```

### **Strategy Engine Integration:**
```python
# Feed sentiment data to strategy engine
sentiment_signal = {
    "type": "SENTIMENT_SIGNAL",
    "symbol": company_symbol,
    "sentiment": sentiment_score,
    "impact": market_impact,
    "timestamp": datetime.now()
}
await strategy_engine.process_signal(sentiment_signal)
```

### **Risk Service Integration:**
```python
# Risk assessment based on sentiment
if sentiment_score < -0.5:  # Very negative
    risk_alert = {
        "type": "SENTIMENT_RISK",
        "symbol": company_symbol,
        "risk_level": "HIGH",
        "reason": f"Negative sentiment: {sentiment_score}"
    }
    await risk_service.trigger_alert(risk_alert)
```

---

## 📈 **SUCCESS METRICS**

### **Technical KPIs:**
- **Latency**: <100ms sentiment analysis
- **Throughput**: 1000+ articles/minute
- **Accuracy**: >85% sentiment classification
- **Uptime**: 99.9% service availability

### **Business KPIs:**
- **Signal Quality**: 70%+ profitable signals
- **Risk Reduction**: 30% fewer adverse positions
- **Alpha Generation**: 2-5% additional returns
- **Market Coverage**: 500+ stocks monitored

---

## 🎯 **NEXT STEPS**

1. **Week 1**: Start with Company Mapper enhancement
2. **Week 2**: Implement news filtering system
3. **Week 3**: Deploy FinBERT sentiment model
4. **Week 4**: Integration testing and optimization

**Ready to begin implementation?** Let me know which component you'd like to start with first!

