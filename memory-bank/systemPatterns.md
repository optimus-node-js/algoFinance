# System Design & Patterns

This document outlines the core architectural patterns and design decisions that govern the project.

## 1. System Architecture: Microservices via Message Queue

The system is designed as a set of decoupled microservices that communicate asynchronously via a RabbitMQ message queue.

-   **Data Ingestion Service (`live_data_stream.py`):** Connects to the broker's real-time API, fetches market data, enriches it with technical features, and publishes it to the `market_data` queue.
-   **Strategy Service (`strategy_runner.py`):** Subscribes to the `market_data` queue. It dynamically loads one or more strategy modules, which analyze the data and may produce trading signals.
-   **Order Management Service (`order_manager.py`):** Subscribes to an `orders` queue. It receives order requests from the Strategy Service and executes them via the broker's API. It uses manual message acknowledgements to ensure order requests are not lost.

This architecture ensures that services are independent, scalable, and resilient. A failure in one service (e.g., the Strategy Service) will not bring down the entire system.

## 2. Configuration Management

Application configuration, especially sensitive data like API keys and database URIs, is managed externally via a `.env` file in the project root.

-   **`.env` file:** This file is git-ignored and contains all environment-specific variables.
-   **`python-dotenv` library:** Used to load the `.env` file.
-   **`server/src/config/settings.py`:** A centralized module that loads the environment variables and makes them available to the rest of the application. It also performs validation on import to ensure all critical settings are present, preventing the app from running with an incomplete configuration.

This pattern keeps credentials out of the codebase and allows for different configurations between development and production environments.

## 3. Connection Management: Singleton with Rate Limiting

All external connections (MongoDB, Angel One SmartAPI) are managed by a thread-safe singleton class: `ConnectionManager`.

-   **Singleton Pattern:** Ensures that only one instance of the connection manager exists, preventing redundant connections and providing a single point of control.
-   **Lazy Initialization:** Connections are only established when they are first requested, improving application startup time.
-   **API Key Rotation:** The manager loads multiple API keys from the `settings.py` module and cycles through them for each request. This distributes the API call load across all available keys, making it easier to stay within rate limits.
-   **Rate Limiting:** The `ConnectionManager` uses the `ratelimiter` library to enforce API call frequency limits. It uses separate limiters for data-retrieval calls (e.g., 9 calls/sec) and order placement calls (e.g., 18 calls/sec), which have different limits according to the broker's documentation. This is implemented via a decorator (`@ConnectionManager.api_request`) that automatically applies the correct limit based on the function it wraps.

## 4. Dynamic Strategy Loading

The backtesting engine (`run_backtest.py`) and the live strategy runner can dynamically load any strategy class at runtime.

-   **File Naming Convention:** Strategy files are named in `snake_case` (e.g., `ml_strategy.py`) and must contain a class that inherits from `BaseStrategy`.
-   **Intelligent Loading:** The runner script takes a `CamelCase` class name as an argument (e.g., `MlStrategy`). It converts this to the corresponding filename, imports the module, and then inspects the module to find the actual `BaseStrategy` subclass. This makes the loading process robust to minor differences in naming and case.
-   **Dynamic Instantiation:** The loader also inspects the strategy's constructor (`__init__`). If it finds parameters it can provide (like a `symbol_token`), it passes them during instantiation. This allows strategies to request specific context without creating a rigid, hardcoded dependency in the runner. 