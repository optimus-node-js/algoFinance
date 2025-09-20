# Angel One Testing System Rules

## CRITICAL TESTING RULES

### 1. Single Script Policy
- **ONLY** update the existing `test_angel_one_module.py` script
- **NEVER** create new testing scripts or files
- All testing functionality must be in this single comprehensive script

### 2. Automated Testing Requirements
- Automated Angel One login and connection initialization
- Interactive menu system for step-by-step testing
- Coverage of ALL implemented Angel One methods (35+ methods)
- Real-time testing capabilities with live Angel One connection
- Comprehensive reporting and results tracking

### 3. Testing Script Features
- Auto-login with Angel One credentials
- Demo mode when credentials not provided
- Interactive numbered menu system
- Step-by-step testing of each module:
  - Authentication & Connection
  - Market Data Methods
  - Portfolio Management
  - Trading Methods
  - Fund Management
  - Reports & Analytics
  - Advanced Features

### 4. User Experience
- Clear console logging with emojis and formatting
- Real-time status updates
- Connection status display
- Comprehensive test results
- Error handling and graceful failures

### 5. Implementation Standards
- Single comprehensive script handles all testing
- No temporary or placeholder files
- Permanent fixes for all missing components
- Complete method coverage testing
- Professional error handling and reporting

## NEVER DO
- Create multiple testing scripts
- Use shortcuts or temporary solutions
- Skip comprehensive testing coverage
- Create separate testing folders or files

## ALWAYS DO
- Update only the single test_angel_one_module.py
- Implement comprehensive automated testing
- Provide interactive menu-driven experience
- Test ALL Angel One methods and features
- Maintain professional code standards


