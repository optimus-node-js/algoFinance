# Microservice Testing Guide - Day 2 Caching Integration

## 🎯 **SERVICES TO RUN FOR TESTING**

### **Required Services (in order):**

1. **Redis Server** (if available locally)
   ```bash
   # Windows (if Redis installed):
   redis-server
   
   # Or use Docker:
   docker run -d -p 6379:6379 redis:alpine
   ```

2. **Angel One API Service** 
   ```bash
   # Terminal 1: Run Angel One FastAPI server
   cd "D:\Personal Projects\Finance Server"
   python -m server.src.angel_one_api --port 8000
   ```

3. **Kafka (if testing messaging integration)**
   ```bash
   # Terminal 2: Start Kafka (if available)
   # Or we'll test in degraded mode
   ```

## 🧪 **TEST SCENARIOS**

### **Test 1: Standalone Caching Service**
- **Services Required**: None (graceful degradation)
- **What it tests**: Basic caching operations without external dependencies

### **Test 2: Redis Integration**
- **Services Required**: Redis Server
- **What it tests**: Full Redis functionality, async/sync operations

### **Test 3: Angel One API Integration** 
- **Services Required**: Angel One API Service + Redis (optional)
- **What it tests**: Idempotency for API calls, response caching

### **Test 4: Full Microservice Communication**
- **Services Required**: Angel One API + Redis + Kafka (optional)
- **What it tests**: End-to-end communication, caching layer performance

## 📋 **TESTING SEQUENCE**

1. **Basic Tests** (No external services needed)
2. **Redis Tests** (You start Redis)
3. **API Integration Tests** (You start Angel One API)
4. **Full Integration Tests** (All services running)

The test script will guide you step-by-step on which services to start when!


