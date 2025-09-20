# Angel One API Module - System Patterns & Architecture

## 🏗️ **SYSTEM ARCHITECTURE OVERVIEW**

### **ARCHITECTURAL STYLE**
**Service-Oriented Architecture (SOA)** with **Distributed Rate Limiting**
- Independent service modules with clear boundaries
- Centralized rate limiting across all operations
- Unified interface for consistent access patterns
- Method-per-file design for independent maintenance

### **DESIGN PHILOSOPHY**
```
MODULARITY → RELIABILITY → PERFORMANCE → MAINTAINABILITY
```

---

## 🎯 **CORE ARCHITECTURAL PATTERNS**

### **1. DISTRIBUTED RATE LIMITING PATTERN**

#### **Pattern Structure**
```
API Request → Rate Controller → Key Selector → Angel One API
              ↓
              Token Bucket → Sliding Window → Emergency Brake
              ↓
              Load Balancer → Available Key → Execute
```

#### **Implementation Details**
```python
class DistributedRateController:
    """
    Central rate limiting system managing 5 API keys
    - Token bucket algorithm for burst handling
    - Sliding window for precise enforcement
    - Intelligent key selection based on availability
    - Emergency brake for violation prevention
    """
    
    def select_optimal_key(self, method_name: str) -> str:
        """Select best available key for specific method"""
        
    def enforce_rate_limit(self, key: str, method: str) -> bool:
        """Check and enforce rate limits before API call"""
        
    def emergency_brake(self, violation_count: int) -> None:
        """Auto-protection from rate violations"""
```

#### **Benefits**
- **Zero Violations**: Intelligent prevention system
- **5x Capacity**: Distributed processing across keys
- **Automatic Recovery**: Emergency brake with auto-reset
- **Optimal Performance**: Smart key selection per method

#### **When to Use**
- ✅ All Angel One API calls (mandatory)
- ✅ High-frequency trading operations
- ✅ Bulk data processing scenarios
- ✅ Production environments

#### **When NOT to Use**
- ❌ Non-Angel One API calls
- ❌ Internal system communications
- ❌ Testing with mock responses

---

### **2. SERVICE-ORIENTED ARCHITECTURE PATTERN**

#### **Pattern Structure**
```
Unified Interface
├── Authentication Service (session & token management)
├── Market Data Service (live feeds & historical data)
├── Portfolio Service (holdings & positions)
├── Fund Management Service (RMS & margins)
└── Alerts Service (monitoring & notifications)
```

#### **Service Design Principles**
```python
class ServiceModule:
    """
    Base pattern for all service modules
    - Single responsibility per service
    - Independent lifecycle management
    - Consistent error handling
    - Clear service boundaries
    """
    
    def __init__(self):
        self.initialize_dependencies()
        self.setup_error_handling()
        self.configure_logging()
    
    async def health_check(self) -> Dict[str, Any]:
        """Standard health check interface"""
        
    def get_service_stats(self) -> Dict[str, Any]:
        """Standard metrics interface"""
```

#### **Service Boundaries**
- **Authentication**: Login, session, token management
- **Market Data**: LTP, historical, instruments, quotes
- **Portfolio**: Holdings, positions, P&L, analytics
- **Fund Management**: RMS, margins, fund limits
- **Alerts**: Price alerts, portfolio monitoring

#### **Inter-Service Communication**
- **Direct Calls**: Services call each other directly
- **Shared State**: Rate controller and auth state shared
- **Event Handling**: Error events propagated to all services
- **Unified Interface**: Single entry point coordinates services

---

### **3. METHOD-PER-FILE PATTERN**

#### **Pattern Structure**
```
methods/
├── get_ltp_data.py          # Single responsibility: LTP fetching
├── place_order.py           # Single responsibility: Order placement
├── get_candle_data.py       # Single responsibility: Historical data
└── [25 more methods...]     # Each method in dedicated file
```

#### **File Template Pattern**
```python
"""
Individual Angel One API Method
- Single API method implementation
- Consistent error handling
- Rate limiting integration
- Helper functions included
"""

from ..rate_limiter import get_rate_controller
from ..utils import validate_parameters, format_response

async def primary_method(params) -> Dict[str, Any]:
    """Main API method implementation"""
    # 1. Parameter validation
    # 2. Rate limiting check
    # 3. API call execution
    # 4. Response formatting
    # 5. Error handling

def helper_function_1(params):
    """Enhanced functionality for primary method"""

def helper_function_2(params):
    """Additional convenience functions"""
```

#### **Benefits**
- **Easy Debugging**: Isolate issues to specific files
- **Independent Fixes**: Change one method without affecting others
- **Clear Testing**: Test individual methods in isolation
- **Simple Enhancement**: Add features to specific methods

#### **Naming Convention**
- **Primary Files**: `{action}_{resource}.py` (e.g., `get_ltp_data.py`)
- **Helper Functions**: `{primary_name}_{variant}` (e.g., `get_bulk_ltp_data`)
- **Constants**: `METHOD_CONFIG`, `DEFAULT_PARAMS`
- **Exceptions**: `{MethodName}Error` (e.g., `LTPDataError`)

---

### **4. UNIFIED INTERFACE PATTERN**

#### **Pattern Structure**
```
AngelOneInterface (Facade)
├── configure() → Setup and authentication
├── get_ltp() → Market data methods
├── place_order() → Trading methods
├── get_positions() → Portfolio methods
└── health_check() → Management methods
```

#### **Interface Design**
```python
class AngelOneInterface:
    """
    Unified facade for all Angel One operations
    - Single entry point for all functionality
    - Consistent error handling across methods
    - Automatic authentication management
    - Built-in rate limiting and caching
    """
    
    async def configure(self, api_keys: Dict) -> bool:
        """One-time setup for all operations"""
        
    async def get_ltp(self, symbol: str) -> float:
        """Simplified LTP with auto-token resolution"""
        
    async def quick_order(self, symbol: str, qty: int, side: str) -> str:
        """Simplified order placement"""
        
    async def get_portfolio_summary(self) -> Dict:
        """Complete portfolio in one call"""
```

#### **Facade Benefits**
- **Simplified API**: Complex operations made simple
- **Consistent Interface**: Same patterns across all methods
- **Error Handling**: Unified error management
- **Backward Compatibility**: Existing code continues to work

---

### **5. MULTI-KEY MANAGEMENT PATTERN**

#### **Pattern Structure**
```
API Key Pool
├── Key 1 → Method Limits → Token Bucket → Sliding Window
├── Key 2 → Method Limits → Token Bucket → Sliding Window
├── Key 3 → Method Limits → Token Bucket → Sliding Window
├── Key 4 → Method Limits → Token Bucket → Sliding Window
└── Key 5 → Method Limits → Token Bucket → Sliding Window
```

#### **Key Management Strategy**
```python
class MultiKeyManager:
    """
    Intelligent management of multiple API keys
    - Per-key per-method rate tracking
    - Optimal key selection algorithm
    - Automatic failover on limits
    - Health monitoring per key
    """
    
    def select_best_key(self, method: str) -> str:
        """Algorithm: lowest load score wins"""
        # load_score = (1 - token_availability) * 0.7 + usage_percentage * 0.3
        
    def track_usage(self, key: str, method: str) -> None:
        """Real-time usage tracking per key per method"""
        
    def health_check_keys(self) -> Dict[str, bool]:
        """Monitor key health and availability"""
```

#### **Load Balancing Algorithm**
1. **Phase 1**: Find keys with immediate availability
2. **Phase 2**: Calculate load score for available keys
3. **Phase 3**: Select key with lowest load score
4. **Phase 4**: Track usage and update availability

---

## 🔧 **TECHNICAL DESIGN PATTERNS**

### **6. TOKEN BUCKET + SLIDING WINDOW PATTERN**

#### **Hybrid Rate Limiting Implementation**
```python
class HybridRateLimiter:
    """
    Combines token bucket for bursts with sliding window for precision
    - Token bucket: Handle burst requests efficiently
    - Sliding window: Precise rate enforcement over time
    - Combined: Best of both algorithms
    """
    
    def __init__(self, requests_per_second: int):
        self.token_bucket = TokenBucket(requests_per_second)
        self.sliding_window = SlidingWindow(requests_per_second)
    
    def can_proceed(self) -> bool:
        """Both algorithms must approve request"""
        return (
            self.token_bucket.consume_token() and 
            self.sliding_window.can_proceed()
        )
```

#### **Algorithm Benefits**
- **Burst Handling**: Token bucket allows bursts up to bucket size
- **Precise Enforcement**: Sliding window prevents sustained overuse
- **Smooth Performance**: Combined approach optimizes for both speed and compliance

### **7. ASYNC-FIRST PATTERN**

#### **Async Design Throughout**
```python
# All API methods are async for non-blocking operations
async def get_ltp_data(symbol: str, token: str) -> Dict[str, Any]:
    """Non-blocking API calls with proper async/await"""
    
# Service methods support async patterns
class MarketDataService:
    async def get_bulk_ltp(self, symbols: List[str]) -> Dict[str, float]:
        """Concurrent processing of multiple symbols"""
        tasks = [self.get_ltp(symbol) for symbol in symbols]
        results = await asyncio.gather(*tasks)
        return dict(zip(symbols, results))
```

#### **Concurrency Benefits**
- **Non-blocking**: Multiple API calls can run concurrently
- **Better Performance**: Parallel processing of bulk operations
- **Resource Efficiency**: Better utilization of I/O wait time

### **8. CONFIGURATION-DRIVEN PATTERN**

#### **Centralized Configuration**
```python
# api_limit_config.py - Single source of truth
ANGEL_ONE_API_LIMITS = {
    "get_ltp_data": APIMethodLimit(
        method_name="get_ltp_data",
        requests_per_second=10,
        priority=APIPriority.HIGH
    ),
    # ... all 28 methods configured
}

# Rate controller uses configuration
class RateController:
    def __init__(self):
        self.limits = ANGEL_ONE_API_LIMITS
        self.enforcers = {
            method: self._create_enforcer(config)
            for method, config in self.limits.items()
        }
```

#### **Configuration Benefits**
- **Single Source**: All limits defined in one place
- **Easy Updates**: Change limits without code changes
- **Consistency**: Same configuration across all components

---

## 📊 **SYSTEM COMPONENTS & RELATIONSHIPS**

### **COMPONENT ARCHITECTURE**
```
┌─────────────────────────────────────────────────────────────┐
│                    Unified Interface                         │
│  (Single entry point for all Angel One operations)         │
└─────────────┬───────────────────────────────────────────────┘
              │
┌─────────────▼───────────────────────────────────────────────┐
│                 Rate Controller                             │
│   (Central rate limiting for all API calls)               │
└─────┬─────┬─────┬─────┬─────┬─────────────────────────────┘
      │     │     │     │     │
      ▼     ▼     ▼     ▼     ▼
   ┌──────┬──────┬──────┬──────┬──────┐
   │ Key1 │ Key2 │ Key3 │ Key4 │ Key5 │
   └──────┴──────┴──────┴──────┴──────┘
              │
   ┌──────────▼──────────┐
   │    Service Layer     │
   │ ┌─────┬─────┬─────┐ │
   │ │Auth │Mkt  │Port │ │
   │ │Mgmt │Data │folio│ │
   │ └─────┴─────┴─────┘ │
   └─────────────────────┘
              │
   ┌──────────▼──────────┐
   │    Method Layer     │
   │ ┌─────────────────┐ │
   │ │ 28 Individual   │ │
   │ │ Method Files    │ │
   │ └─────────────────┘ │
   └─────────────────────┘
```

### **DATA FLOW PATTERNS**

#### **1. API Request Flow**
```
User Request → Unified Interface → Rate Controller → Service → Method → Angel One
     ↓              ↓                   ↓             ↓        ↓         ↓
Response ← Format Response ← Track Usage ← Process ← Format ← API Response
```

#### **2. Error Handling Flow**
```
Error Occurred → Method Catches → Service Handles → Interface Formats → User
     ↓              ↓               ↓                 ↓               ↓
 Log Error → Classify Error → Apply Recovery → Standard Format → Clear Message
```

#### **3. Rate Limiting Flow**
```
API Call → Check Limits → Select Key → Execute → Track Usage → Update Limits
   ↓            ↓           ↓         ↓         ↓              ↓
Block/Allow → Key Health → Available → Success → Statistics → Next Request
```

---

## 🎯 **PATTERN USAGE GUIDELINES**

### **WHEN TO USE EACH PATTERN**

#### **Distributed Rate Limiting**
- ✅ **ALWAYS**: Every Angel One API call
- ✅ **High Volume**: Bulk operations and frequent calls
- ✅ **Production**: All production environments
- ❌ **Testing**: Mock API calls or internal operations

#### **Service-Oriented Architecture**
- ✅ **Large Features**: Multi-step operations requiring coordination
- ✅ **Cross-cutting**: Features spanning multiple API methods
- ✅ **Complex Logic**: Business logic beyond simple API calls
- ❌ **Simple Operations**: Single API method calls

#### **Method-Per-File**
- ✅ **Individual Methods**: Each Angel One API method
- ✅ **Independent Features**: Features that can stand alone
- ✅ **Debugging**: When isolation is important
- ❌ **Tightly Coupled**: Features that must work together

#### **Unified Interface**
- ✅ **User-Facing**: All external API access
- ✅ **Simplification**: Complex operations made simple
- ✅ **Consistency**: Standard interface across features
- ❌ **Internal**: Service-to-service communication

---

## 🔧 **DESIGN PRINCIPLES**

### **SOLID PRINCIPLES APPLICATION**

#### **Single Responsibility Principle (SRP)**
- **Each Method File**: One API method per file
- **Each Service**: One business domain per service
- **Each Class**: One clear responsibility

#### **Open/Closed Principle (OCP)**
- **Extension**: Add new methods without modifying existing
- **Configuration**: Change behavior through configuration
- **Plugins**: New services can be added easily

#### **Liskov Substitution Principle (LSP)**
- **Interface Compliance**: All methods follow same interface pattern
- **Service Contracts**: Services implement consistent contracts
- **Error Handling**: Consistent error response formats

#### **Interface Segregation Principle (ISP)**
- **Focused Services**: Services expose only relevant methods
- **Method Interfaces**: Each method has minimal interface
- **Client-Specific**: Clients depend only on methods they use

#### **Dependency Inversion Principle (DIP)**
- **Rate Controller**: High-level modules depend on abstractions
- **Service Dependencies**: Services depend on interfaces
- **Configuration**: Dependencies injected through configuration

---

## 📈 **PATTERN BENEFITS & TRADEOFFS**

### **BENEFITS ACHIEVED**

#### **Modularity**
- **Independent Development**: Teams can work on different services
- **Isolated Testing**: Test components in isolation
- **Easy Debugging**: Problems isolated to specific components
- **Incremental Deployment**: Deploy individual services

#### **Scalability**
- **Horizontal Scaling**: Add more API keys for capacity
- **Service Scaling**: Scale individual services independently
- **Load Distribution**: Intelligent load balancing across keys
- **Performance Optimization**: Optimize individual components

#### **Maintainability**
- **Clear Structure**: Easy to understand and navigate
- **Single Point Changes**: Fix issues in one place
- **Documentation**: Clear patterns for documentation
- **Knowledge Transfer**: Patterns make onboarding easier

### **TRADEOFFS CONSIDERED**

#### **Complexity vs. Capability**
- **Added Complexity**: More moving parts to manage
- **Increased Capability**: Much more powerful and flexible
- **Decision**: Complexity justified by enterprise requirements

#### **Performance vs. Safety**
- **Rate Limiting Overhead**: Small performance cost
- **Safety Guarantee**: Zero API violations
- **Decision**: Safety more important than marginal performance

#### **Flexibility vs. Simplicity**
- **More Configuration**: More options to configure
- **Greater Flexibility**: Can adapt to many scenarios
- **Decision**: Flexibility needed for production deployment

---

**This system architecture represents a mature, enterprise-grade design that balances performance, reliability, maintainability, and scalability while maintaining clear patterns and principles throughout.** 🏗️
