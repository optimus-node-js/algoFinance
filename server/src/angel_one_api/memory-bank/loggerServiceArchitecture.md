# Angel One Logger Service Architecture

## 🎯 **LOGGER SERVICE OVERVIEW**

**Service Type**: Comprehensive Logging Infrastructure  
**Backend**: Loguru with custom extensions  
**Status**: FULLY OPERATIONAL (Production Ready)  
**Version**: 1.0.0  
**Database Integration**: Conditional storage in `logs_angelone` table  

---

## 🏗️ **ARCHITECTURE DESIGN**

### **🎨 SCOPE-BASED ORGANIZATION**
```
Angel One Logger Service
├── 🔵 API_METHODS     - Blue family (method calls, parameters, responses)
├── 🟢 SERVICES        - Green family (business logic, coordination)  
├── 🟡 INFRASTRUCTURE  - Yellow family (rate limiting, system events)
├── 🟣 TESTING         - Purple family (test execution, results)
├── 🔴 ERRORS          - Red family (failures, exceptions, critical issues)
├── 🟠 PERFORMANCE     - Orange family (timing, metrics, optimization)
└── 🟫 DATABASE        - Brown family (DB operations, storage)
```

### **📁 FILE STRUCTURE**
```
angel_one_api/logger/
├── __init__.py                  # Main exports and quick setup functions
├── config.py                    # Centralized configuration and settings
├── angel_logger.py              # Main logger service controller
├── scope_loggers.py             # Pre-configured scope-specific loggers
├── handlers.py                  # Custom handlers (console, file, performance, error)
├── formatters.py                # Color-coded formatters for different scopes
├── db_handler.py                # Database logging with batch processing
└── logs/                        # Organized log file storage
    ├── angel_one_main.log       # Main module logs
    ├── api_methods/             # API Methods scope logs
    │   ├── get_ltp_data.log
    │   ├── place_order.log
    │   └── [28 method logs...]
    ├── services/                # Services scope logs
    │   ├── authentication.log
    │   ├── market_data.log
    │   ├── portfolio.log
    │   ├── fund_management.log
    │   └── alerts.log
    ├── infrastructure/          # Infrastructure scope logs
    │   ├── rate_limiter.log
    │   ├── interface.log
    │   └── system.log
    ├── testing/                 # Testing scope logs
    │   └── test_execution.log
    └── errors/                  # Error-specific logs
        ├── critical_errors.log
        ├── api_failures.log
        ├── rate_limit_issues.log
        └── database_failures.log
```

---

## 🎨 **COLOR-CODED CONSOLE OUTPUT**

### **VISUAL LOG IDENTIFICATION SYSTEM**
```
🔵 [API] get_ltp_data: 📥 Fetching LTP for RELIANCE (token: 2885) | K1 | 250.5ms
🟢 [SVC] 📊 market_data: Processing bulk LTP request (50 symbols) | 1.2s
🟡 [INF] ⚡ rate_limiter: Selected API key 3 (load: 23%) | emergency_brake: false
🟣 [TST] 🧪 test_suite: Running portfolio management tests | success: 90.4%
🔴 [ERR] ❌ api_methods: Rate limit exceeded for place_order | [API003]
🟠 [PERF] ⚡ interface: ✅ API operation completed | 125.3ms | success
```

### **SCOPE INDICATORS**
- **🔵 API**: API method calls with method icons (📥📤🔍🔧)
- **🟢 SVC**: Service operations with service icons (🔐📊💰💳🚨⚙️)
- **🟡 INF**: Infrastructure events with system icons (⚡🎯🛡️📊)
- **🟣 TST**: Testing operations with test icons (🧪✅❌📋)
- **🔴 ERR**: Error events with severity icons (💥❌⚠️ℹ️)
- **🟠 PERF**: Performance metrics with timing icons (⚡🟢🟡🟠🔴)

---

## 🔧 **CORE COMPONENTS**

### **1. ANGEL LOGGER SERVICE (`angel_logger.py`)**
**Central controller for all logging operations**

#### **Key Features:**
- **Scope Management**: Automatic logger creation for each scope/component
- **Session Context**: Global session and API key tracking
- **Health Monitoring**: Comprehensive health checks and statistics
- **Database Integration**: Configurable database logging with batching
- **Graceful Shutdown**: Clean shutdown with log flushing

#### **Main Interface:**
```python
class AngelOneLogger:
    def get_scope_logger(scope, component, db_store=True) -> ScopeLogger
    def set_global_context(session_id, **context)
    def log_api_call(method, params, response, timing, api_key_id, success, db_store)
    def log_rate_limit_event(method, api_key_id, action, details, db_store)
    def log_service_operation(service, operation, data, success, duration, db_store)
    def get_comprehensive_stats() -> Dict[str, Any]
    def health_check() -> Dict[str, Any]
```

### **2. SCOPE LOGGERS (`scope_loggers.py`)**
**Pre-configured loggers for each development scope**

#### **Available Loggers:**
```python
api_methods_logger = ScopeLogger(LogScope.API_METHODS)
services_logger = ScopeLogger(LogScope.SERVICES)
infrastructure_logger = ScopeLogger(LogScope.INFRASTRUCTURE)
testing_logger = ScopeLogger(LogScope.TESTING)
performance_logger = ScopeLogger(LogScope.PERFORMANCE)
error_logger = ScopeLogger(LogScope.ERRORS)
database_logger = ScopeLogger(LogScope.DATABASE)
```

#### **ScopeLogger Features:**
- **Automatic Context**: Session ID and API key tracking
- **Performance Timing**: Built-in timing context manager
- **Error Handling**: Enhanced error logging with stack traces
- **Database Control**: Conditional storage via `db_store` parameter
- **Statistics**: Comprehensive logging statistics per scope

### **3. DATABASE HANDLER (`db_handler.py`)**
**Async database logging with batch processing**

#### **Key Features:**
- **Batch Processing**: Efficient batch inserts (default: 100 logs per batch)
- **Async Operations**: Non-blocking database operations
- **Conditional Storage**: `dbStore` parameter controls database logging
- **Error Recovery**: Backup failed logs to file
- **Performance**: Background worker thread for processing

#### **Database Schema (logs_angelone table):**
```sql
CREATE TABLE logs_angelone (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    timestamp DATETIME NOT NULL,
    level VARCHAR(20) NOT NULL,
    scope VARCHAR(50) NOT NULL,
    component VARCHAR(100) NOT NULL,
    message TEXT NOT NULL,
    extra_data JSON DEFAULT NULL,
    session_id VARCHAR(100) DEFAULT NULL,
    api_key_id VARCHAR(50) DEFAULT NULL,
    error_traceback TEXT DEFAULT NULL,
    INDEX idx_timestamp (timestamp),
    INDEX idx_scope_component (scope, component),
    INDEX idx_session (session_id),
    INDEX idx_level (level)
);
```

### **4. CUSTOM HANDLERS (`handlers.py`)**
**Specialized handlers for different logging destinations**

#### **Handler Types:**
- **ConsoleHandler**: Color-coded console output with scope filtering
- **FileHandler**: Automatic rotation with scope-based file organization
- **PerformanceHandler**: Specialized performance metrics collection
- **ErrorHandler**: Enhanced error tracking with categorization

#### **Handler Features:**
- **Async Operations**: Non-blocking I/O for all handlers
- **Context Management**: Automatic session and API key context
- **Statistics**: Real-time performance and error statistics
- **Filtering**: Scope and component-based log filtering

### **5. FORMATTERS (`formatters.py`)**
**Custom formatters with color coding and structured output**

#### **Formatter Types:**
- **AngelOneFormatter**: Base formatter with scope-based coloring
- **PerformanceFormatter**: Specialized for timing and performance data
- **ApiMethodFormatter**: Specialized for API method calls
- **ServiceFormatter**: Specialized for service operations
- **ErrorFormatter**: Enhanced error context and severity indicators

---

## ⚙️ **CONFIGURATION SYSTEM**

### **LOGGER CONFIG (`config.py`)**
**Centralized configuration management**

#### **Key Settings:**
```python
class LoggerConfig:
    # Log levels
    default_level = LogLevel.INFO
    console_level = LogLevel.INFO
    file_level = LogLevel.DEBUG
    database_level = LogLevel.INFO
    
    # File rotation
    max_file_size = "10 MB"
    max_files = 10
    rotation_time = "1 day"
    
    # Database settings
    database_enabled = True
    database_table = "logs_angelone"
    batch_size = 100
    batch_timeout = 5.0
    
    # Performance settings
    async_logging = True
    buffer_size = 1000
    flush_interval = 1.0
```

#### **Environment Overrides:**
- `ANGEL_ONE_LOG_LEVEL`: Set global log level
- `ANGEL_ONE_DB_LOGGING`: Enable/disable database logging
- `ANGEL_ONE_LOG_DIR`: Custom log directory

---

## 🚀 **USAGE PATTERNS**

### **1. BASIC SCOPE LOGGING**
```python
# Import scope-specific logger
from angel_one_api.logger import api_methods_logger

# Log with automatic context
api_methods_logger.info("API call started", {
    "method": "get_ltp_data", 
    "symbol": "RELIANCE"
})

# Performance timing
with api_methods_logger.timer("api_call_get_ltp"):
    result = await get_ltp_data("RELIANCE", "2885")

# Error logging with context
api_methods_logger.error("API call failed", 
                        error=exception, 
                        error_code="API001",
                        extra={"symbol": "RELIANCE"})
```

### **2. COMPONENT-SPECIFIC LOGGING**
```python
# Get logger for specific component
from angel_one_api.logger import get_api_logger

logger = get_api_logger("get_ltp_data")
logger.set_context(session_id="sess123", api_key_id="key1")

# All logs now include context automatically
logger.info("Processing LTP request")
logger.performance("ltp_fetch", 0.25, True)
```

### **3. DATABASE STORAGE CONTROL**
```python
# Log without database storage
logger.debug("Debug information", db_store=False)

# Log with database storage (default)
logger.error("Critical error", db_store=True)

# Configure database logging
from angel_one_api.logger import configure_database_logging
configure_database_logging(enabled=True, batch_size=50, batch_timeout=3.0)
```

### **4. DECORATOR PATTERNS**
```python
# API method decoration
from angel_one_api.logger import log_api_method

@log_api_method("get_ltp_data")
async def get_ltp_data(symbol, token):
    # Automatic logging of entry, exit, timing, and errors
    return await fetch_ltp(symbol, token)

# Service operation decoration
from angel_one_api.logger import log_service_operation

@log_service_operation("market_data")
def process_bulk_request(symbols):
    # Automatic service operation logging
    return process_symbols(symbols)
```

---

## 📊 **MONITORING & STATISTICS**

### **LOGGER HEALTH CHECK**
```python
from angel_one_api.logger import get_logger_health

health = get_logger_health()
# Returns:
{
    "status": "healthy",
    "timestamp": "2025-09-20T15:30:00Z",
    "components": {
        "logger_service": {"status": "healthy", "loggers_count": 12},
        "database_handler": {"status": "healthy", "queue_size": 5},
        "log_directories": {"status": "healthy", "path": "/logs"}
    }
}
```

### **COMPREHENSIVE STATISTICS**
```python
from angel_one_api.logger import get_logger_stats

stats = get_logger_stats()
# Returns:
{
    "angel_one_logger": {
        "initialized": True,
        "total_loggers": 12,
        "session_id": "sess123",
        "database_enabled": True
    },
    "scope_loggers": {
        "api_methods_default": {
            "scope": "API_METHODS",
            "total_logs": 1250,
            "error_logs": 15,
            "performance_logs": 450
        }
    },
    "database_handler": {
        "total_logs": 1100,
        "successful_inserts": 1095,
        "failed_inserts": 5,
        "queue_size": 3
    }
}
```

---

## 🔄 **INTEGRATION WITH EXISTING SYSTEMS**

### **REPLACED OLD LOGGING**
- ✅ **Removed**: Old `logs/` folder and basic Python logging
- ✅ **Updated**: All 43+ files now use new logger service
- ✅ **Enhanced**: Color-coded console output with scope identification
- ✅ **Improved**: Structured logging with context and performance tracking

### **DATABASE INTEGRATION**
- ✅ **Connects**: Uses existing database service outside angel_one_api
- ✅ **Batches**: Efficient batch processing for performance
- ✅ **Conditional**: `dbStore` parameter controls storage
- ✅ **Resilient**: Backup to file if database unavailable

### **RATE LIMITER INTEGRATION**
- ✅ **Enhanced**: Rate limiting events logged with full context
- ✅ **Performance**: API call timing and success tracking
- ✅ **Monitoring**: Real-time rate limit utilization logging
- ✅ **Alerts**: Emergency brake events logged for analysis

---

## 🎯 **OPERATIONAL BENEFITS**

### **FOR DEVELOPERS**
- **🎨 Visual Identification**: Instant scope recognition with colors
- **🔧 Easy Debugging**: Scope-specific log files for focused analysis
- **📊 Performance Insights**: Built-in timing and metrics
- **🎯 Context Aware**: Automatic session and API key tracking

### **FOR OPERATIONS**
- **📈 Centralized Monitoring**: Single point for all Angel One logs
- **🗄️ Searchable History**: Database storage with indexed queries
- **📁 Organized Files**: Scope-based file organization
- **🔍 Health Monitoring**: Real-time logger service health checks

### **FOR ANALYTICS**
- **📊 Performance Metrics**: Comprehensive timing and success data
- **📈 Usage Patterns**: API method usage statistics
- **🚨 Error Analysis**: Categorized error tracking and trends
- **💹 Capacity Planning**: Rate limiting utilization analysis

---

## 🔮 **FUTURE ENHANCEMENTS**

### **PLANNED FEATURES**
- **📡 Real-time Dashboard**: Live log monitoring interface
- **🔔 Smart Alerting**: Intelligent error and performance alerts
- **☁️ Cloud Integration**: Support for cloud logging services
- **📱 Mobile Alerts**: Critical error notifications to mobile devices

### **SCALABILITY IMPROVEMENTS**
- **🔄 Auto-scaling**: Dynamic log retention based on volume
- **⚡ Performance**: Further optimization for high-volume logging
- **🌐 Distributed**: Support for distributed logging across services
- **🤖 AI Analysis**: Machine learning for log pattern analysis

---

**The Angel One Logger Service provides enterprise-grade logging infrastructure that scales with the project while maintaining excellent performance and comprehensive monitoring capabilities.** 🎯
