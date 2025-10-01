"""
AI Intelligence Service
======================

Advanced AI/ML service for financial sentiment analysis and trading signal generation.
Processes news data from Sentiment Aggregator and generates actionable trading signals.

Components:
- FinBERT sentiment analysis model
- Trading signal generation
- Risk-adjusted position sizing
- Integration with existing HFT infrastructure

Service Communication:
- Consumes: News data from Sentiment Aggregator via Kafka
- Produces: Trading signals to Strategy Engine via Kafka
- Database: Stores ML results in centralized PostgreSQL
- Cache: Uses Redis for model inference caching
"""

__version__ = "1.0.0"
__service_name__ = "ai_intelligence_service"
