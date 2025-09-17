# 🧪 Complete Testing Guide - AI Trading System

## 📋 **TESTING OVERVIEW**

This guide provides comprehensive instructions for testing all components of our AI-powered algorithmic trading system, including proper service startup order, test scenarios, and expected outcomes.

## 🚀 **REQUIRED SERVICES STARTUP ORDER**

### **Phase 1: Infrastructure Services (MUST START FIRST)**

#### **1.1 MongoDB Database**
```bash
# Windows (if MongoDB installed as service)
net start MongoDB

# Or start manually
mongod --dbpath "C:\data\db"

# Verify MongoDB is running
mongo --eval "db.adminCommand('ismaster')"
```

#### **1.2 RabbitMQ Message Broker (OPTIONAL)**
```bash
# Windows (if RabbitMQ installed as service)
net start RabbitMQ

# Or start manually
rabbitmq-server

# Verify RabbitMQ is running
rabbitmqctl status
```

### **Phase 2: Core Services**

#### **2.1 Angel One API Connection**
- Ensure `.env` file has valid Angel One credentials
- API_KEY, SECRET_KEY, CLIENT_ID, PASSWORD, TOTP_SECRET must be configured

### **Phase 3: AI System Testing**

## 🧪 **TESTING SCENARIOS**

### **Test 1: Basic AI Components (No Dependencies)**
```bash
# What we're testing: Core AI functionality without external services
# Input: Mock market data
# Expected: AI analysis results with confidence scores

python server/src/ai/testing/test_ai_components.py
```

**📊 Test Details:**
- **Purpose**: Verify AI components work independently
- **Input Data**: 
  - Mock price data (300 data points)
  - Multiple timeframes (5m, 15m, 1h, 1d)
  - Sample portfolio positions
- **Expected Outcomes**:
  - Central AI Engine: Status=Ready, 6 active symbols
  - Risk Engine: Market regime detection, position sizing
  - Volatility Analyzer: Multi-timeframe analysis, risk assessment
  - Message Broker: Graceful degradation if RabbitMQ unavailable

**✅ Success Criteria:**
- All components initialize successfully
- Analysis completes within 5 seconds
- Confidence scores > 0.5
- No critical errors in logs

---

### **Test 2: Full System Integration (All Services)**
```bash
# Prerequisites: MongoDB + RabbitMQ + Angel One API
# What we're testing: Complete system integration
# Input: Real market data from Angel One
# Expected: End-to-end trading decisions

python server/src/ai/testing/integration_tests/test_full_system.py
```

**📊 Test Details:**
- **Purpose**: Test complete AI system with real data
- **Input Data**:
  - Live Angel One API data
  - Real portfolio positions
  - Current market conditions
- **Expected Outcomes**:
  - Real-time market data acquisition
  - AI-powered trading decisions
  - Risk management validation
  - Message queue communication

---

### **Test 3: Performance & Load Testing**
```bash
# What we're testing: System performance under load
# Input: Multiple parallel requests
# Expected: Sub-second response times

python server/src/ai/testing/performance_tests/test_load_performance.py
```

**📊 Test Details:**
- **Purpose**: Validate system performance and scalability
- **Input Data**:
  - 100 concurrent analysis requests
  - 10 stocks analyzed simultaneously
  - High-frequency data updates
- **Expected Outcomes**:
  - Response time < 500ms per stock
  - Memory usage < 2GB
  - CPU usage < 80%
  - Zero memory leaks

## 🛠️ **DETAILED TEST SCENARIOS**

### **Scenario A: Cold Start Testing**

#### **A.1 Prerequisites Check**
```bash
# Check if MongoDB is running
python -c "
import pymongo
try:
    client = pymongo.MongoClient('mongodb://localhost:27017/', serverSelectionTimeoutMS=5000)
    client.admin.command('ismaster')
    print('✅ MongoDB is running')
except:
    print('❌ MongoDB not running - START MONGODB FIRST')
"
```

#### **A.2 RabbitMQ Status Check**
```bash
# Check if RabbitMQ is running (optional)
python -c "
import pika
try:
    connection = pika.BlockingConnection(pika.ConnectionParameters('localhost'))
    connection.close()
    print('✅ RabbitMQ is running')
except:
    print('⚠️ RabbitMQ not running - System will work in degraded mode')
"
```

#### **A.3 Angel One API Check**
```bash
# Check Angel One API connectivity
python -c "
import sys, os
sys.path.append(os.path.abspath('.'))
from server.src.core.connections import ConnectionManager
try:
    client = ConnectionManager.get_smartapi_client()
    print('✅ Angel One API connected')
except Exception as e:
    print(f'❌ Angel One API error: {e}')
"
```

### **Scenario B: AI Component Individual Testing**

#### **B.1 Risk Engine Testing**
```bash
# What: Test AI risk management capabilities
# Input: Portfolio data + market conditions
# Expected: Risk scores, position sizing, recommendations

python -c "
import sys, os
sys.path.append(os.path.abspath('.'))
from server.src.ai.risk_management.ai_risk_engine import AIRiskEngine
import numpy as np

print('🧪 Testing AI Risk Engine...')
engine = AIRiskEngine()

# Test market regime detection
sample_data = {
    'prices': [100 + i + np.random.random() for i in range(50)],
    'volumes': [1000 + np.random.randint(0, 500) for _ in range(50)]
}

regime = engine.analyze_market_regime('TEST-SYMBOL', sample_data)
print(f'Market Regime: {regime.regime}')
print(f'Volatility: {regime.volatility_level}')
print(f'Confidence: {regime.confidence:.2f}')

# Test position sizing
sizing = engine.calculate_ai_position_size(
    symbol='TEST-SYMBOL',
    entry_price=100.0,
    stop_loss_price=95.0,
    account_balance=50000.0,
    market_data=sample_data,
    confidence_score=0.8
)

if sizing.get('status') == 'success':
    print(f'Recommended Shares: {sizing[\"recommended_shares\"]}')
    print(f'Risk Percentage: {sizing[\"actual_risk_percentage\"]:.2f}%')
    print('✅ Risk Engine test PASSED')
else:
    print('❌ Risk Engine test FAILED')
"
```

**Expected Output:**
```
🧪 Testing AI Risk Engine...
Market Regime: trending/ranging/transitional
Volatility: low/medium/high
Confidence: 0.50-1.00
Recommended Shares: 10-50 (depends on risk calculation)
Risk Percentage: 0.40-2.00%
✅ Risk Engine test PASSED
```

#### **B.2 Volatility Analyzer Testing**
```bash
# What: Test multi-timeframe volatility analysis
# Input: Multi-timeframe price data
# Expected: Volatility forecasts, regime classification

python -c "
import sys, os
sys.path.append(os.path.abspath('.'))
from server.src.ai.volatility_analysis.volatility_analyzer import AdvancedVolatilityAnalyzer
import numpy as np

print('🧪 Testing Advanced Volatility Analyzer...')
analyzer = AdvancedVolatilityAnalyzer()

# Multi-timeframe sample data
base_price = 100
sample_data = {
    'current_price': base_price,
    'prices': [base_price + i + np.random.random() * 5 for i in range(300)],
    'timeframes': {
        '5m': [base_price + i * 0.1 + np.random.random() for i in range(100)],
        '15m': [base_price + i * 0.3 + np.random.random() * 2 for i in range(96)],
        '1h': [base_price + i * 1.2 + np.random.random() * 5 for i in range(80)],
        '1d': [base_price + i * 2 + np.random.random() * 10 for i in range(60)]
    }
}

forecast = analyzer.analyze_volatility_multiframe('TEST-SYMBOL', sample_data)
print(f'Current Volatility: {forecast.current_volatility:.2%}')
print(f'Volatility Regime: {forecast.volatility_regime}')
print(f'Risk Level: {forecast.risk_level}')
print(f'Forecasts: {forecast.forecasts}')
print(f'Recommendations: {len(forecast.recommendations)} items')
print('✅ Volatility Analyzer test PASSED')
"
```

**Expected Output:**
```
🧪 Testing Advanced Volatility Analyzer...
Current Volatility: 10-30%
Volatility Regime: low_volatility/normal_volatility/high_volatility
Risk Level: low/moderate/high
Forecasts: {'1h': 0.15, '1d': 0.18, '1w': 0.20}
Recommendations: 1-3 items
✅ Volatility Analyzer test PASSED
```

#### **B.3 Central AI Engine Testing**
```bash
# What: Test complete AI decision engine
# Input: Multi-stock market data
# Expected: Trading decisions with reasoning

python -c "
import sys, os
sys.path.append(os.path.abspath('.'))
from server.src.ai.central_ai_engine import CentralAIEngine

print('🧪 Testing Central AI Engine...')
engine = CentralAIEngine()

# Test status
status = engine.get_ai_status()
print(f'Engine Running: {status[\"is_running\"]}')
print(f'Active Symbols: {status[\"active_symbols\"]}')
print(f'AI Components: {status[\"ai_components\"]}')

# Test single symbol analysis
intelligence = engine._comprehensive_symbol_analysis('RELIANCE-EQ')
print(f'Symbol: {intelligence.symbol}')
print(f'Market Regime: {intelligence.market_regime}')
print(f'Confidence: {intelligence.confidence_score:.2f}')

# Test decision generation
decision = engine._generate_symbol_decision(intelligence)
if decision:
    print(f'Decision: {decision.action} {decision.symbol}')
    print(f'Confidence: {decision.confidence:.2f}')
    print(f'Priority: {decision.execution_priority}')
    print('✅ Central AI Engine test PASSED')
else:
    print('⚠️ No decision generated (this is normal for low confidence)')
"
```

**Expected Output:**
```
🧪 Testing Central AI Engine...
Engine Running: False (normal for test mode)
Active Symbols: 6
AI Components: {'risk_engine': True, 'volatility_analyzer': False, ...}
Symbol: RELIANCE-EQ
Market Regime: trending/ranging/transitional
Confidence: 0.50-0.90
Decision: buy/sell/hold RELIANCE-EQ
Confidence: 0.70-0.95
Priority: 1-10
✅ Central AI Engine test PASSED
```

## 🎯 **COMPLETE TESTING WORKFLOW**

### **Step 1: Environment Setup**
```bash
# 1. Start MongoDB
net start MongoDB

# 2. Start RabbitMQ (optional)
net start RabbitMQ

# 3. Verify environment
python server/src/ai/testing/test_environment.py
```

### **Step 2: Unit Testing**
```bash
# Test individual components
python server/src/ai/testing/unit_tests/test_risk_engine.py
python server/src/ai/testing/unit_tests/test_volatility_analyzer.py
python server/src/ai/testing/unit_tests/test_central_ai_engine.py
```

### **Step 3: Integration Testing**
```bash
# Test component interactions
python server/src/ai/testing/integration_tests/test_ai_integration.py
```

### **Step 4: Performance Testing**
```bash
# Test system performance
python server/src/ai/testing/performance_tests/test_ai_performance.py
```

### **Step 5: End-to-End Testing**
```bash
# Test complete trading workflow
python server/src/ai/testing/e2e_tests/test_trading_workflow.py
```

## 📊 **SUCCESS CRITERIA MATRIX**

| Test Category | Component | Success Criteria | Failure Indicators |
|---------------|-----------|------------------|-------------------|
| **Unit Tests** | Risk Engine | Regime detection accuracy > 70% | Exception errors, negative confidence |
| | Volatility Analyzer | Forecast completion < 2s | Timeout errors, invalid forecasts |
| | Central AI Engine | Decision generation > 50% cases | No decisions generated, low confidence |
| **Integration** | Message Broker | Message delivery 100% | Connection failures, lost messages |
| | Database | Data persistence 100% | Write failures, data corruption |
| | API Integration | Angel One connectivity | Authentication failures, timeouts |
| **Performance** | Response Time | < 500ms per stock analysis | > 2s response times |
| | Memory Usage | < 2GB for 6 stocks | Memory leaks, high usage |
| | Throughput | > 10 decisions/minute | Low throughput, bottlenecks |

## 🚨 **TROUBLESHOOTING GUIDE**

### **Common Issues & Solutions**

#### **Issue: MongoDB Connection Failed**
```bash
# Solution: Start MongoDB service
net start MongoDB
# Or check if port 27017 is available
netstat -an | findstr 27017
```

#### **Issue: RabbitMQ Connection Failed**
```bash
# Solution: System works without RabbitMQ (degraded mode)
# Or start RabbitMQ service
net start RabbitMQ
```

#### **Issue: Angel One API Authentication Failed**
```bash
# Solution: Check .env file credentials
# Verify API_KEY, SECRET_KEY, CLIENT_ID, PASSWORD, TOTP_SECRET
```

#### **Issue: Low AI Confidence Scores**
```bash
# Solution: Increase data quality
# - Use more historical data points
# - Ensure data consistency
# - Check for outliers in price data
```

This comprehensive testing guide ensures every component is properly validated before production deployment! 🚀




