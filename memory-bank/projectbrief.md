 
# Project Brief: Automated Algorithmic Trading System

## 1. Core Objective

To develop a fully automated, 24/7 algorithmic trading system using Python and the Angel One SmartAPI. The system will be built on a microservices architecture, designed for resilience, scalability, and continuous self-improvement through AI and backtesting.

## 2. Key Technologies

- **Core Language:** Python
- **Primary Broker API:** Angel One SmartAPI
- **Database:** MongoDB (using the `algoFinance` database)
- **Microservice Communication:** RabbitMQ (Message Queue)
- **AI/ML & Backtesting:** MLflow, VectorBT, Scikit-learn, Pandas

## 3. Architectural Principles

- **Microservices:** The system will be composed of small, independent services that communicate via a message queue. This promotes resilience and modularity.
- **Data-Driven:** All trading decisions will be based on real-time and historical market data. AI/ML models will be central to generating trading signals.
- **Automation:** The system is intended to run continuously with no manual intervention required for trading operations.
- **Local Deployment:** The system will be deployed and run on a local machine without containerization (Docker).
- **Self-Improvement & Scalability:** The architecture must support continuous learning, model versioning, and performance tracking (MLOps). It must be scalable to accommodate more complex and powerful predictive models over time.

## 4. Current Status (Phase 9 - Active Implementation)

**System Completion:** 90% Complete - Sentiment Analysis Integration Phase

### **Completed Components:**
- ✅ **Infrastructure:** Docker, Kafka, Redis, PostgreSQL (100% Complete)
- ✅ **Core Services:** Angel One API, Risk Service, Strategy Engine, Market Data (100% Complete)
- ✅ **Service Communication:** Kafka integration across all 10 services (100% Complete)
- ✅ **Database Access:** Centralized Prisma + PostgreSQL (100% Complete)
- ✅ **Live Trading Pipeline:** WebSocket → Kafka → Strategy → Risk → Execution (100% Complete)
- ✅ **Sentiment Aggregator Service:** News APIs, Kafka integration, FastAPI service (90% Complete)
- 🔄 **AI Intelligence Service:** ML models, sentiment analysis, signal generation (10% Complete)

### **Phase 9 Implementation (In Progress):**
**Service 1: Sentiment Aggregator (News Processing)**
- 🔄 **Enhanced Company Mapper:** NSE/BSE database, fuzzy matching (Week 1)
- 🔄 **Intelligent News Filtering:** Multi-factor relevance scoring (Week 2)

**Service 2: AI Intelligence Service (ML Processing)**
- 🔄 **FinBERT Sentiment Model:** ML pipeline, ONNX optimization (Week 3)
- 🔄 **Trading Signal Generation:** AI-driven signals, risk adjustment (Week 4)

### **Remaining Components (10%):**
- ❌ **Advanced AI/ML:** Ensemble methods, progressive learning (30% Complete)
- ❌ **Backtesting Platform:** Vectorbt, Backtrader, performance analytics (20% Complete)
- ❌ **MLOps Infrastructure:** MLflow, model registry, A/B testing (0% Complete)

### **Phase 9 Technical Stack:**
- **News Sources:** RSS feeds, NewsAPI, GNews API
- **ML Framework:** FinBERT (transformers), ONNX Runtime
- **Indian Market Data:** nsepy, indstocks, yfinance
- **Text Processing:** spacy, fuzzywuzzy, sentence-transformers
- **Performance:** Redis caching, async processing, batch inference

### **Expected Outcomes:**
- **Processing Capacity:** 5,000+ articles/day
- **Sentiment Accuracy:** 85%+ classification accuracy
- **Trading Signals:** 50+ sentiment-driven signals/day
- **Latency:** <100ms per article analysis
- **Market Coverage:** 500+ Indian stocks monitored 