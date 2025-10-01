# Phase 9: Restructured File System Architecture
## Separated Services Implementation Structure

### 🏗️ **OVERVIEW**
Restructured architecture separating news aggregation from AI/ML processing:
- **Sentiment Aggregator Service:** News collection, filtering, company mapping only
- **AI Intelligence Service:** ML models, sentiment analysis, signal generation

---

## 📁 **CURRENT SENTIMENT AGGREGATOR STRUCTURE**

```
server/src/sentiment_aggregator/
├── __init__.py                          ✅ EXISTS
├── main.py                              ✅ EXISTS - FastAPI service
├── config.py                            ✅ EXISTS - Configuration management
├── .env                                 ✅ EXISTS - Environment variables
├── README.md                            ✅ EXISTS - Service documentation
│
├── news_apis/                           ✅ EXISTS
│   ├── __init__.py                      ✅ EXISTS
│   ├── rss_client.py                    ✅ EXISTS - RSS feeds
│   ├── newsapi_client.py                ✅ EXISTS - NewsAPI integration
│   ├── gnews_client.py                  ✅ EXISTS - GNews integration
│   └── api_manager.py                   ✅ EXISTS - Multi-source coordination
│
└── data_processing/                     ✅ EXISTS
    ├── __init__.py                      ✅ EXISTS
    └── company_mapper.py                ✅ EXISTS - Basic company mapping
```

---

## 🚀 **RESTRUCTURED IMPLEMENTATION**

### **SERVICE 1: Sentiment Aggregator (News Only)**

```
server/src/sentiment_aggregator/
│
├── stock_integration/                   🆕 NEW DIRECTORY
│   ├── __init__.py                      🆕 NEW
│   ├── enhanced_company_mapper.py       🆕 NEW - Advanced company mapping
│   ├── stock_data_fetcher.py           🆕 NEW - NSE/BSE data integration
│   ├── sector_classifier.py            🆕 NEW - Industry classification
│   ├── fuzzy_matcher.py                🆕 NEW - Advanced name matching
│   └── market_data_validator.py        🆕 NEW - Data validation
│
├── filtering/                          🆕 NEW DIRECTORY
│   ├── __init__.py                     🆕 NEW
│   ├── news_relevance_scorer.py       🆕 NEW - Multi-factor scoring
│   ├── content_filter.py              🆕 NEW - Spam/duplicate detection
│   ├── market_impact_analyzer.py      🆕 NEW - Impact assessment
│   └── source_credibility_manager.py  🆕 NEW - Source rating system
│
└── databases/                          🆕 NEW DIRECTORY
    ├── company_database.json           🆕 NEW - 3,000+ Indian companies
    ├── sector_mapping.json             🆕 NEW - Sector classifications
    ├── company_aliases.json            🆕 NEW - Name variations
    └── source_credibility.json         🆕 NEW - Source ratings
```

### **SERVICE 2: AI Intelligence Service**

```
server/src/ai_intelligence_service/     🆕 NEW SERVICE
│
├── __init__.py                         🆕 NEW
├── main.py                             🆕 NEW - FastAPI service
├── config.py                           🆕 NEW - AI/ML configuration
│
├── ml_models/                          🆕 NEW DIRECTORY
│   ├── __init__.py                     🆕 NEW
│   ├── finbert_sentiment_model.py      🆕 NEW - Core FinBERT implementation
│   ├── model_trainer.py               🆕 NEW - Training and fine-tuning
│   ├── model_optimizer.py             🆕 NEW - ONNX optimization
│   └── inference_pipeline.py          🆕 NEW - Production inference
│
├── signal_generation/                  🆕 NEW DIRECTORY
│   ├── __init__.py                     🆕 NEW
│   ├── sentiment_signal_generator.py  🆕 NEW - Core signal generation
│   ├── trading_signal_optimizer.py    🆕 NEW - Signal optimization
│   └── risk_adjusted_signals.py       🆕 NEW - Risk-adjusted sizing
│
├── integration/                        🆕 NEW DIRECTORY
│   ├── __init__.py                     🆕 NEW
│   ├── sentiment_aggregator_client.py 🆕 NEW - News service client
│   ├── strategy_engine_connector.py   🆕 NEW - Strategy Engine integration
│   └── database_connector.py          🆕 NEW - Database service client
│
└── models/                             🆕 NEW DIRECTORY
    ├── finbert_base/                   🆕 NEW - Pre-trained model
    ├── finbert_indian/                 🆕 NEW - Fine-tuned model
    └── onnx_models/                    🆕 NEW - Optimized models
```

## 📊 **SERVICE COMMUNICATION FLOW**

```
News Sources (RSS/API) 
↓
Sentiment Aggregator Service (Port 8010)
├── News Collection & Filtering
├── Company Mapping
├── Relevance Scoring
└── Publish to Kafka: hft-news-processed

↓ Kafka Communication ↓

AI Intelligence Service (Port 8011)
├── Consume News from Kafka
├── FinBERT Sentiment Analysis  
├── Trading Signal Generation
└── Publish to Kafka: hft-sentiment-signals

↓ Kafka Communication ↓

Strategy Engine ← Risk Service ← Angel One API
```

---

## 📊 **COMPLETE FINAL STRUCTURE**

```
server/src/sentiment_aggregator/
├── __init__.py                              ✅ EXISTS
├── main.py                                  📝 ENHANCED - Add new endpoints
├── config.py                                📝 ENHANCED - Add ML config
├── .env                                     📝 ENHANCED - Add ML environment vars
├── README.md                                📝 ENHANCED - Update documentation
│
├── news_apis/                               ✅ EXISTS
│   ├── __init__.py                          ✅ EXISTS
│   ├── rss_client.py                        ✅ EXISTS
│   ├── newsapi_client.py                    ✅ EXISTS
│   ├── gnews_client.py                      ✅ EXISTS
│   └── api_manager.py                       ✅ EXISTS
│
├── data_processing/                         📝 ENHANCED
│   ├── __init__.py                          ✅ EXISTS
│   ├── company_mapper.py                    📝 ENHANCED
│   └── enhanced_company_processor.py       🆕 NEW
│
├── stock_integration/                       🆕 NEW - Week 1
│   ├── __init__.py
│   ├── enhanced_company_mapper.py
│   ├── stock_data_fetcher.py
│   ├── sector_classifier.py
│   ├── fuzzy_matcher.py
│   └── market_data_validator.py
│
├── filtering/                               🆕 NEW - Week 2
│   ├── __init__.py
│   ├── news_relevance_scorer.py
│   ├── content_filter.py
│   ├── market_impact_analyzer.py
│   ├── source_credibility_manager.py
│   └── quality_assessor.py
│
├── scoring/                                 🆕 NEW - Week 2
│   ├── __init__.py
│   ├── relevance_algorithms.py
│   ├── keyword_analyzer.py
│   ├── temporal_scorer.py
│   └── composite_scorer.py
│
├── ml_models/                               🆕 NEW - Week 3
│   ├── __init__.py
│   ├── finbert_sentiment_model.py
│   ├── model_trainer.py
│   ├── model_optimizer.py
│   ├── inference_pipeline.py
│   └── model_validator.py
│
├── ml_pipeline/                             🆕 NEW - Week 3
│   ├── __init__.py
│   ├── batch_processor.py
│   ├── async_processor.py
│   ├── sentiment_cache.py
│   ├── queue_manager.py
│   └── health_monitor.py
│
├── signal_generation/                       🆕 NEW - Week 4
│   ├── __init__.py
│   ├── sentiment_signal_generator.py
│   ├── trading_signal_optimizer.py
│   ├── risk_adjusted_signals.py
│   ├── signal_validator.py
│   └── portfolio_impact_analyzer.py
│
├── integration/                             🆕 NEW - Week 4
│   ├── __init__.py
│   ├── strategy_engine_connector.py
│   ├── risk_service_connector.py
│   ├── angel_one_connector.py
│   └── kafka_signal_publisher.py
│
├── monitoring/                              🆕 NEW - Week 4
│   ├── __init__.py
│   ├── performance_monitor.py
│   ├── latency_tracker.py
│   ├── accuracy_tracker.py
│   ├── alert_manager.py
│   └── dashboard_metrics.py
│
├── production/                              🆕 NEW - Week 4
│   ├── __init__.py
│   ├── production_validator.py
│   ├── load_tester.py
│   ├── deployment_checker.py
│   └── health_checker.py
│
├── databases/                               🆕 NEW - Week 1-2
│   ├── __init__.py
│   ├── company_database.json               (3,000+ companies)
│   ├── sector_mapping.json
│   ├── company_aliases.json
│   ├── market_cap_data.json
│   ├── source_credibility.json
│   ├── financial_keywords.json
│   └── market_hours_config.json
│
├── models/                                  🆕 NEW - Week 3
│   ├── finbert_base/                       (Pre-trained model)
│   ├── finbert_indian/                     (Fine-tuned model)
│   ├── onnx_models/                        (Optimized models)
│   └── model_metadata.json
│
├── training_data/                           🆕 NEW - Week 3
│   ├── indian_financial_corpus.json
│   ├── labeled_sentiment_data.json
│   └── validation_dataset.json
│
├── tests/                                   🆕 NEW - All Weeks
│   ├── __init__.py
│   ├── test_company_mapper.py
│   ├── test_news_filtering.py
│   ├── test_sentiment_model.py
│   ├── test_signal_generation.py
│   └── test_integration.py
│
└── logs/                                    🆕 NEW - All Weeks
    ├── sentiment_analysis.log
    ├── model_performance.log
    ├── signal_generation.log
    └── integration.log
```

---

## 🔧 **IMPLEMENTATION DEPENDENCIES**

### **Python Packages to Install:**
```bash
# Week 1: Stock Integration
pip install nsepy indstocks yfinance
pip install fuzzywuzzy python-levenshtein
pip install pandas numpy

# Week 2: News Filtering
pip install scikit-learn nltk spacy
pip install textblob langdetect

# Week 3: ML Models
pip install transformers torch
pip install onnx onnxruntime
pip install sentence-transformers

# Week 4: Production
pip install prometheus-client
pip install psutil memory-profiler
```

### **Model Files to Download:**
```bash
# FinBERT Pre-trained Model
models/finbert_base/
├── config.json
├── pytorch_model.bin
├── tokenizer.json
├── tokenizer_config.json
└── vocab.txt
```

---

## 📊 **INTEGRATION POINTS**

### **Database Schema Updates:**
```sql
-- Add sentiment analysis columns
ALTER TABLE news_articles ADD COLUMN sentiment_score DECIMAL(3,2);
ALTER TABLE news_articles ADD COLUMN sentiment_label VARCHAR(20);
ALTER TABLE news_articles ADD COLUMN confidence_score DECIMAL(3,2);
ALTER TABLE news_articles ADD COLUMN relevance_score DECIMAL(3,2);
ALTER TABLE news_articles ADD COLUMN market_impact DECIMAL(3,2);

-- Add company mapping columns
ALTER TABLE news_articles ADD COLUMN mapped_companies TEXT[];
ALTER TABLE news_articles ADD COLUMN primary_company VARCHAR(100);
ALTER TABLE news_articles ADD COLUMN sector VARCHAR(50);
```

### **Kafka Topics:**
```yaml
# New topics for Phase 9
hft-sentiment-enhanced-analysis    # Enhanced sentiment results
hft-sentiment-trading-signals      # Trading signals
hft-sentiment-model-health         # Model performance metrics
hft-sentiment-company-mapping      # Company mapping results
```

### **Redis Cache Keys:**
```python
# Cache key patterns
sentiment:article:{hash}           # Sentiment results
company:mapping:{company_name}     # Company mappings
relevance:score:{article_hash}     # Relevance scores
model:health:{timestamp}           # Model health data
```

---

## 🚀 **IMPLEMENTATION ORDER**

### **Week 1 Priority Files:**
1. `stock_integration/enhanced_company_mapper.py`
2. `databases/company_database.json`
3. `stock_integration/stock_data_fetcher.py`
4. `stock_integration/fuzzy_matcher.py`

### **Week 2 Priority Files:**
1. `filtering/news_relevance_scorer.py`
2. `scoring/relevance_algorithms.py`
3. `filtering/content_filter.py`
4. `databases/source_credibility.json`

### **Week 3 Priority Files:**
1. `ml_models/finbert_sentiment_model.py`
2. `ml_pipeline/inference_pipeline.py`
3. `ml_pipeline/sentiment_cache.py`
4. `models/finbert_base/` (download)

### **Week 4 Priority Files:**
1. `signal_generation/sentiment_signal_generator.py`
2. `integration/strategy_engine_connector.py`
3. `monitoring/performance_monitor.py`
4. `production/production_validator.py`

---

## ✅ **READY TO START IMPLEMENTATION**

The file system architecture is now complete and ready for step-by-step implementation. Each week builds upon the previous week's work, maintaining clean separation of concerns and modular design.

**Next Step:** Begin Week 1 implementation with Enhanced Company Mapper!

