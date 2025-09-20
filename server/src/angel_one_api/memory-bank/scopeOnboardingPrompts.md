# Angel One API Module - Scope Onboarding Prompts

## 🎯 **REUSABLE ONBOARDING PROMPTS**

### **PURPOSE**
These prompts enable developers to quickly onboard to specific development scopes within the Angel One API module. Each prompt provides focused context for a particular area of work.

### **USAGE INSTRUCTIONS**
1. **Identify your scope** from the 5 primary development areas
2. **Copy the relevant prompt** for your scope
3. **Paste the prompt** when starting work in that area
4. **Get focused context** tailored to your development needs

---

## 🔥 **SCOPE 1: API METHODS ONBOARDING PROMPT**

### **PROMPT FOR API METHODS DEVELOPERS**
```
I'm working on the Angel One API Methods scope in the Angel One API module. Please provide focused context for:

SCOPE: API Methods Development
LOCATION: angel_one_api/methods/ directory (28 individual method files)
FOCUS: Individual Angel One SmartAPI method implementation and maintenance

KEY AREAS:
- Understanding method-per-file pattern implementation
- Angel One SmartConnect SDK integration patterns
- Rate limiting integration for each method
- Parameter validation and error handling
- Helper function development and enhancement
- Response formatting and data processing

CURRENT STATUS:
- 28/28 methods implemented (100% complete)
- All methods use distributed rate limiting
- 925 req/sec total capacity across 5 API keys
- 90.4% success rate with real data testing

SPECIFIC FOCUS:
[Specify which method(s) you're working on: get_ltp_data, place_order, get_candle_data, etc.]

TASK TYPE:
[Specify: New method implementation, Bug fix, Enhancement, Performance optimization, Testing]

Please provide:
1. Method-specific implementation patterns and best practices
2. Rate limiting integration requirements for this method
3. Common issues and troubleshooting for this method
4. Helper function opportunities and patterns
5. Testing approach for this specific method
6. Performance considerations and optimization opportunities

Show relevant code examples and explain the method-per-file pattern as implemented in this project.
```

### **WHEN TO USE THIS PROMPT**
- ✅ Adding new Angel One API methods
- ✅ Fixing bugs in existing methods
- ✅ Enhancing method functionality
- ✅ Optimizing method performance
- ✅ Understanding method implementation patterns

---

## 🏗️ **SCOPE 2: SERVICES ONBOARDING PROMPT**

### **PROMPT FOR SERVICES DEVELOPERS**
```
I'm working on the Services scope in the Angel One API module. Please provide focused context for:

SCOPE: Service-Oriented Architecture Development
LOCATION: authentication/, market_data/, portfolio/, fund_management/, alerts/ directories
FOCUS: Service modules with business logic and cross-method coordination

KEY AREAS:
- Service-oriented architecture patterns
- Business logic implementation across multiple API methods
- Service-specific caching and optimization strategies
- Cross-cutting concerns within service domains
- Service health monitoring and statistics
- Complex data processing and analysis

CURRENT STATUS:
- 5/5 services implemented (100% complete)
- Authentication: Multi-key auth, session management, token refresh
- Market Data: Live feeds, historical data, instruments, quotes
- Portfolio: Holdings, positions, P&L, analytics, tracking
- Fund Management: RMS data, margin tracking
- Alerts: Price alerts, portfolio monitoring

SPECIFIC FOCUS:
[Specify which service: Authentication, Market Data, Portfolio, Fund Management, Alerts]

TASK TYPE:
[Specify: New service feature, Service enhancement, Performance optimization, Integration work, Business logic]

Please provide:
1. Service architecture patterns and design principles
2. Cross-method coordination strategies
3. Caching and optimization approaches for this service
4. Service interface design patterns
5. Error handling and recovery patterns at service level
6. Health monitoring and statistics implementation
7. Integration patterns with other services

Show relevant service implementation examples and explain the SOA patterns used in this project.
```

### **WHEN TO USE THIS PROMPT**
- ✅ Developing business logic spanning multiple API methods
- ✅ Implementing service-level features
- ✅ Working on cross-cutting concerns
- ✅ Optimizing service performance
- ✅ Understanding service architecture patterns

---

## ⚡ **SCOPE 3: INFRASTRUCTURE ONBOARDING PROMPT**

### **PROMPT FOR INFRASTRUCTURE DEVELOPERS**
```
I'm working on the Infrastructure scope in the Angel One API module. Please provide focused context for:

SCOPE: Rate Limiting & System Infrastructure
LOCATION: rate_limiter/ directory, interface.py, system initialization
FOCUS: Distributed rate limiting, system infrastructure, and performance engineering

KEY AREAS:
- Distributed rate limiting algorithm implementation
- Token bucket and sliding window algorithms
- Multi-key load balancing and selection
- Emergency brake and recovery systems
- Performance monitoring and statistics
- Configuration management for rate limits
- System initialization and setup

CURRENT STATUS:
- 925 req/sec total capacity with 5 API keys
- Zero rate violations with intelligent prevention
- Token bucket + sliding window hybrid algorithm
- Emergency brake with auto-recovery
- Real-time per-method per-key tracking

SPECIFIC FOCUS:
[Specify: Rate limiting algorithms, Load balancing, Performance optimization, Monitoring, Configuration]

TASK TYPE:
[Specify: Algorithm enhancement, Performance tuning, Monitoring improvement, Configuration update, Capacity scaling]

Please provide:
1. Rate limiting algorithm design and implementation
2. Multi-key load balancing strategies
3. Emergency brake and recovery mechanisms
4. Performance monitoring and metrics collection
5. Configuration management patterns
6. System initialization and setup procedures
7. Capacity planning and scaling approaches

Show relevant infrastructure code examples and explain the distributed rate limiting architecture.
```

### **WHEN TO USE THIS PROMPT**
- ✅ Working on rate limiting algorithms
- ✅ Optimizing system performance
- ✅ Implementing monitoring and alerting
- ✅ Scaling system capacity
- ✅ Understanding infrastructure patterns

---

## 🧪 **SCOPE 4: TESTING ONBOARDING PROMPT**

### **PROMPT FOR TESTING DEVELOPERS**
```
I'm working on the Testing scope in the Angel One API module. Please provide focused context for:

SCOPE: Testing & Quality Assurance
LOCATION: testing/ directory, comprehensive test infrastructure
FOCUS: Automated testing, quality validation, and real data testing

KEY AREAS:
- Comprehensive automated testing with real Angel One API
- Interactive testing workflows and user interfaces
- Safety features for live trading operations
- Test reporting and analysis
- Quality assurance across all system components
- Performance testing and validation

CURRENT STATUS:
- 90.4% success rate (47 passed, 5 failed tests)
- Real data testing with live Angel One API (no mocks)
- Interactive menu system for step-by-step testing
- Safety features protecting live trading operations
- Complete coverage of all 28 methods + 5 services

SPECIFIC FOCUS:
[Specify: Test category - Authentication, Market Data, Portfolio, Trading, Fund Management, Reports, Advanced Features, Integration]

TASK TYPE:
[Specify: New test development, Test improvement, Bug investigation, Performance testing, Safety enhancement]

Please provide:
1. Testing framework architecture and patterns
2. Real data testing strategies and best practices
3. Interactive testing workflow design
4. Safety feature implementation for live trading
5. Test reporting and analysis approaches
6. Quality assurance methodologies
7. Performance testing and validation techniques

Show relevant testing code examples and explain the real data testing approach used in this project.
```

### **WHEN TO USE THIS PROMPT**
- ✅ Developing new test cases
- ✅ Improving test coverage
- ✅ Investigating test failures
- ✅ Implementing safety features
- ✅ Understanding testing architecture

---

## 📚 **SCOPE 5: DOCUMENTATION ONBOARDING PROMPT**

### **PROMPT FOR DOCUMENTATION DEVELOPERS**
```
I'm working on the Documentation scope in the Angel One API module. Please provide focused context for:

SCOPE: Documentation & Knowledge Management
LOCATION: memory-bank/, docs/ directories, comprehensive documentation system
FOCUS: Technical documentation, knowledge management, and developer onboarding

KEY AREAS:
- Complete API method documentation and references
- Architecture and design pattern documentation
- Testing procedures and result documentation
- Onboarding and training material development
- Progress tracking and metrics documentation
- Historical decision and evolution documentation

CURRENT STATUS:
- Complete memory bank system with 7 core files
- 100% API method documentation coverage
- Comprehensive testing guide with real results
- Architecture documentation with patterns and principles
- Historical documentation preserved in docs/ directory

SPECIFIC FOCUS:
[Specify: Memory bank files, API reference, Testing guides, Architecture docs, Onboarding materials, Progress tracking]

TASK TYPE:
[Specify: New documentation, Documentation update, Process improvement, Onboarding enhancement, Knowledge organization]

Please provide:
1. Documentation architecture and organization patterns
2. Memory bank system structure and maintenance
3. API reference documentation standards
4. Onboarding material development approaches
5. Progress tracking and metrics documentation
6. Knowledge management best practices
7. Documentation maintenance and update procedures

Show relevant documentation examples and explain the memory bank system used in this project.
```

### **WHEN TO USE THIS PROMPT**
- ✅ Creating new documentation
- ✅ Updating existing documentation
- ✅ Improving onboarding processes
- ✅ Organizing knowledge systems
- ✅ Understanding documentation architecture

---

## 🎯 **SPECIALIZED ONBOARDING PROMPTS**

### **EMERGENCY TROUBLESHOOTING PROMPT**
```
I need to troubleshoot an urgent issue in the Angel One API module. Please provide emergency context for:

ISSUE TYPE: [Rate limiting violation, API method failure, Service disruption, Authentication issue, Performance problem]
AFFECTED SCOPE: [API Methods, Services, Infrastructure, Testing, Documentation]
SEVERITY: [Critical - Production down, High - Degraded performance, Medium - Functionality affected, Low - Minor issue]

IMMEDIATE CONTEXT NEEDED:
1. Current system status and health check procedures
2. Common issues and their quick resolutions
3. Emergency procedures and rollback options
4. Logging and debugging approaches
5. Contact information and escalation procedures
6. Known workarounds and temporary fixes

SYSTEM STATUS:
- Current success rate: 90.4%
- Rate limiting status: 925 req/sec capacity
- Known limitations: 5 failed tests (SDK limitations)
- Emergency brake status: [Operational/Triggered]

Please provide immediate troubleshooting steps and emergency procedures.
```

### **PERFORMANCE OPTIMIZATION PROMPT**
```
I'm working on performance optimization for the Angel One API module. Please provide focused context for:

OPTIMIZATION SCOPE: [Rate limiting, API response times, Memory usage, Caching efficiency, Bulk operations]
CURRENT METRICS: 
- Total capacity: 925 req/sec
- Success rate: 90.4%
- Response times: Sub-second for most operations
- Memory usage: ~100MB under full load

TARGET IMPROVEMENTS:
[Specify: Increase capacity, Reduce response times, Optimize memory, Improve cache hit rates, Enhance bulk operations]

Please provide:
1. Current performance bottlenecks and profiling data
2. Optimization strategies and implementation approaches
3. Performance testing and validation procedures
4. Monitoring and metrics collection improvements
5. Capacity planning and scaling considerations
6. Best practices for performance optimization

Focus on actionable optimization techniques with measurable improvements.
```

### **INTEGRATION DEVELOPMENT PROMPT**
```
I'm working on integration features for the Angel One API module. Please provide context for:

INTEGRATION TYPE: [New Angel One methods, External system integration, Service enhancement, Cross-system communication]
INTEGRATION SCOPE: [Single method, Service module, Cross-service, System-wide]

REQUIREMENTS:
[Specify: New functionality, Performance requirements, Compatibility needs, Security considerations]

Please provide:
1. Integration patterns and best practices
2. Compatibility and backward compatibility considerations
3. Testing strategies for integration features
4. Documentation requirements for new integrations
5. Performance impact assessment
6. Error handling and recovery for integrations

Show integration examples and explain the integration patterns used in this project.
```

---

## 📋 **PROMPT USAGE GUIDELINES**

### **BEST PRACTICES**
1. **Be Specific**: Include specific files, methods, or components you're working on
2. **State Your Task**: Clearly specify what you want to accomplish
3. **Provide Context**: Include any relevant background or constraints
4. **Ask for Examples**: Request code examples and practical guidance
5. **Specify Output**: Indicate what format or detail level you need

### **CUSTOMIZATION TIPS**
- **Modify Focus Areas**: Adjust the focus areas based on your specific needs
- **Add Constraints**: Include any technical or business constraints
- **Specify Timeline**: Mention if you need quick fixes vs comprehensive solutions
- **Include Dependencies**: Note any dependencies or integration requirements

### **COMBINATION PROMPTS**
You can combine prompts when working across multiple scopes:
```
I'm working across multiple scopes in the Angel One API module:
- PRIMARY SCOPE: [Main focus area]
- SECONDARY SCOPE: [Supporting area]
- INTEGRATION POINTS: [How they connect]

Please provide focused context for both areas and their integration...
```

---

**These onboarding prompts enable rapid context switching and focused development across all areas of the Angel One API module, ensuring developers can quickly get up to speed in any scope.** 🚀
