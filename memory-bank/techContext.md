 
# Tech Context

This document outlines the specific technologies and libraries chosen for the project.

## 1. Core Platform
- **Python:** Version 3.10+ will be used for all services.
- **Environment Management:** A `requirements.txt` file will be used to manage Python dependencies. It is recommended to use a virtual environment (e.g., `venv`) to isolate project dependencies.

## 2. Broker Integration
- **Angel One SmartAPI:** The exclusive API for all trading, portfolio, and data-related functionality.
- **`smartapi-python`:** The official Python SDK provided by Angel One. This will be the primary tool for REST API calls and WebSocket connections.
- **`pyotp`:** This library will be required to handle the Time-based One-Time Password (TOTP) generation needed for the Angel One login process.

## 3. Data Layer
- **MongoDB:** The sole database for the system.
- **`pymongo`:** The standard, official Python driver for interacting with the MongoDB server. It will be used for all database operations.
- **`pandas`:** Essential for data manipulation, analysis, and cleaning. It will be used heavily in the Data Ingestion, Strategy, and Backtesting services.

## 4. Microservices & Communication
- **FastAPI:** Will be used to build the API Gateway service due to its high performance and ease of use.
- **`pika`:** The recommended Python client for interacting with the RabbitMQ message queue.
- **`uvicorn`:** The server that will run the FastAPI-based API Gateway.

## 5. AI/ML & Backtesting
- **`scikit-learn`:** The primary library for building initial machine learning models.
- **`mlflow`:** Will be used for its Model Registry capabilities, allowing for versioning and management of trained models.
- **`vectorbt`:** A powerful and fast library for backtesting trading strategies on historical data.
- **`numpy`:** A fundamental package for numerical computation, required by many other data-related libraries.

## 6. Local Development
- **No Docker:** As per the project requirements, the system will be run directly on the host machine. This requires manual installation and management of:
    - Python 3.10+
    - MongoDB Server
    - RabbitMQ Server 