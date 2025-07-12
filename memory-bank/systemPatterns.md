 
# System Patterns

## 1. Primary Architectural Pattern: Microservices

The system is designed as a collection of independent, single-responsibility services that communicate asynchronously.

- **Rationale:** This pattern promotes resilience (the failure of one non-critical service doesn't crash the system), scalability (services can be scaled independently if needed), and maintainability (it's easier to update or debug a small, focused service).
- **Implementation:** Services will run as separate Python processes.

## 2. Communication Pattern: Message Queue (Pub/Sub)

Services will communicate via a central message queue using a "Publish/Subscribe" model.

- **Technology:** RabbitMQ
- **How it Works:**
    - A "producer" service publishes a message (e.g., a new piece of market data, a trade signal) to a specific topic/exchange on the queue.
    - "Consumer" services subscribe to the topics they are interested in and receive messages as they arrive.
- **Rationale:** This decouples the services. The Data Ingestion service, for example, does not need to know which services consume its data; it only needs to publish it. This makes it easy to add new consumers (e.g., a new strategy service) without changing the producer.

## 3. Data Storage Strategy

A unified data store will be used for simplicity in this initial version.

- **Technology:** MongoDB
- **Schema Design:**
    - **Time-Series Collections:** For high-volume, ordered data like market ticks (`market_data_ticks`). This is a native MongoDB feature that provides optimized storage and querying for this data type.
    - **Standard Collections:** For all other data, including `order_logs`, `strategies`, `risk_rules`, and `backtest_results`. This data is relational in nature but can be effectively modeled in a document database for flexibility.

## 4. Configuration Management

- **Method:** Configurations (e.g., database connection strings, API keys, strategy parameters) will be managed via external files (e.g., `.env` or `config.ini`).
- **Rationale:** This separates configuration from code, which is a security best practice. It allows for changing settings without modifying and redeploying the application code. Credentials should **never** be hard-coded. 