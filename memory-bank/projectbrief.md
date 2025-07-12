 
# Project Brief: Automated Algorithmic Trading System

## 1. Core Objective

To develop a fully automated, 24/7 algorithmic trading system using Python and the Angel One SmartAPI. The system will be built on a microservices architecture, designed for resilience, scalability, and continuous self-improvement through AI and backtesting.

## 2. Key Technologies

- **Core Language:** Python
- **Primary Broker API:** Angel One SmartAPI
- **Database:** MongoDB (using the `algoFinance` database)
- **Microservice Communication:** RabbitMQ (Message Queue)
- **AI/ML & Backtesting:** MLflow, VectorBT, Scikit-learn, Pandas

## 3. Architectural Principles

- **Microservices:** The system will be composed of small, independent services that communicate via a message queue. This promotes resilience and modularity.
- **Data-Driven:** All trading decisions will be based on real-time and historical market data. AI/ML models will be central to generating trading signals.
- **Automation:** The system is intended to run continuously with no manual intervention required for trading operations.
- **Local Deployment:** The system will be deployed and run on a local machine without containerization (Docker).

## 4. Initial Scope (Phase 1)

The initial development will focus on establishing the foundational framework:
- Securely connecting to the Angel One API.
- Ingesting and storing real-time market data in MongoDB.
- Implementing a core workflow for placing, managing, and logging orders.
- Creating a basic, non-AI trading strategy to validate the end-to-end pipeline. 