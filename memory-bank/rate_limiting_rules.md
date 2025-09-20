# Rate Limiting System Rules

## CRITICAL RULES

### 1. Rate Limiting Must Always Be Maintained
- **NEVER** bypass or remove rate limiting from Angel One API methods
- **NEVER** create "simple" versions that skip rate limiting
- Rate limiting is essential to prevent API hits from exceeding limits
- Each API key has specific rate limits that must be respected

### 2. Fix Rate Controller Issues Properly
- If rate controller is not initialized, fix the initialization
- If rate limiting fails, fix the rate controller configuration
- Never work around rate limiting by removing it

### 3. Rate Limiting System Purpose
- Prevents exceeding Angel One API rate limits
- Protects API keys from being blocked
- Ensures system stability and compliance
- Essential for production use

### 4. Error Resolution Approach
- Rate controller errors → Fix rate controller initialization
- Rate limiting failures → Fix rate controller configuration  
- API parameter errors → Fix API method parameters
- Never remove rate limiting as a "solution"

## NEVER DO
- Remove rate limiting decorators
- Create bypass methods without rate limiting
- Skip rate controller initialization
- Work around rate limiting issues

## ALWAYS DO
- Maintain rate limiting on all Angel One API methods
- Fix rate controller initialization issues properly
- Respect API rate limits for each endpoint
- Keep rate limiting system functional and active


