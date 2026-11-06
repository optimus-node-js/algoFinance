# ⚡ algoFinance — AI-Powered Microservice Trading Platform

> An event-driven, containerised algorithmic-trading platform for Indian markets: Angel One SmartAPI execution, Kafka messaging, Redis caching, sentiment aggregation, risk management and AI signal generation — each as an independent microservice.

![Python](https://img.shields.io/badge/Python-3776AB?style=flat-square&logo=python&logoColor=white) ![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=flat-square&logo=fastapi&logoColor=white) ![Apache Kafka](https://img.shields.io/badge/Apache%20Kafka-231F20?style=flat-square&logo=apachekafka&logoColor=white) ![Redis](https://img.shields.io/badge/Redis-DC382D?style=flat-square&logo=redis&logoColor=white) ![Docker](https://img.shields.io/badge/Docker-2496ED?style=flat-square&logo=docker&logoColor=white) ![PostgreSQL](https://img.shields.io/badge/PostgreSQL-4169E1?style=flat-square&logo=postgresql&logoColor=white) ![MongoDB](https://img.shields.io/badge/MongoDB-47A248?style=flat-square&logo=mongodb&logoColor=white) ![Angel One SmartAPI](https://img.shields.io/badge/Angel%20One%20SmartAPI-E4572E?style=flat-square)

---

## 📖 Overview

Retail traders lose to emotion, slow execution and the impossibility of watching markets all day. **algoFinance** is my "fire-and-forget" answer: a fully automated system that ingests live market data and news sentiment, generates AI-driven signals, applies programmatic risk limits and executes through Angel One — with every trade, prediction and market condition logged for continuous model improvement and champion/challenger paper trading.

## 🧩 Services

| Service | Responsibility |
|---|---|
| `angel_one_api` | SmartAPI auth (TOTP auto-login), orders, GTT rules, positions, margin |
| `market_data_streaming` | Live tick/LTP streaming over WebSockets |
| `messaging_enhanced` | Kafka topics for market events, signals and orders |
| `caching_service` | Redis caching of quotes, sessions and hot data |
| `sentiment_aggregator` | Aggregates Indian financial news / social sentiment |
| `ai_intelligence_service` | ML models (scikit-learn) for signal generation |
| `strategy_engine` | Pluggable strategies with health server and config-driven params |
| `risk_service` | Position sizing, exposure limits, stop-loss enforcement |
| `database_service` | Persistence (PostgreSQL/Timescale, MongoDB, Prisma) |

## 🏗️ Architecture

```
 Angel One WS ─▶ market_data_streaming ─┐
 News/Social  ─▶ sentiment_aggregator ──┤
                                        ▼
                                  Kafka (messaging)
                                        │
          ┌────────────── strategy_engine ◀── ai_intelligence_service
          ▼                             │
     risk_service ──▶ angel_one_api (orders) ──▶ database_service
          ▲                                          │
          └──────────── caching_service (Redis) ◀────┘
```

## 🚀 Getting Started

**Prerequisites:** Docker & Docker Compose, an Angel One SmartAPI account.

```bash
git clone https://github.com/optimus-node-js/algoFinance.git
cd algoFinance
```

```bash
cp .env.example .env        # fill in your own Angel One / DB / API credentials
docker compose up --build   # starts every microservice
```

Individual services have their own Dockerfiles (`Dockerfile.angel-one`, `Dockerfile.risk-service`, …) and can be started separately. See [`README.Docker.md`](README.Docker.md) for deployment notes and [`memory-bank/`](memory-bank) for architecture design docs, the HFT roadmap and testing reports.

## 📚 Design Docs

- `memory-bank/hft_architecture_design.md` — system design
- `memory-bank/hft_implementation_roadmap.md` — phased roadmap
- `memory-bank/angel_one_testing_comprehensive.md` — broker API test coverage
- `memory-bank/indian_news_apis_research.md` — sentiment data sources

> 🔐 All credentials that were previously committed have been redacted from history. Supply your own via environment variables.

**Successor:** the paper-trading engine was later rebuilt as a leaner FastAPI service in [Finance-Algo](https://github.com/optimus-node-js/Finance-Algo).

---

## 👤 Author

**Rahul Vishwakarma** — Senior Full Stack Developer · Ahmedabad, India

[![Portfolio](https://img.shields.io/badge/Portfolio-rahul--vishwakarma--portfolio.vercel.app-0A66C2?style=flat-square&logo=vercel&logoColor=white)](https://rahul-vishwakarma-portfolio.vercel.app/)
[![LinkedIn](https://img.shields.io/badge/LinkedIn-Rahul%20Vishwakarma-0A66C2?style=flat-square&logo=linkedin&logoColor=white)](https://linkedin.com/in/rahul-vishwakarma-101346192)
[![Email](https://img.shields.io/badge/Email-karmarahul67%40gmail.com-D14836?style=flat-square&logo=gmail&logoColor=white)](mailto:karmarahul67@gmail.com)
[![GitHub](https://img.shields.io/badge/GitHub-optimus--node--js-181717?style=flat-square&logo=github)](https://github.com/optimus-node-js)

If you find this project useful, consider giving it a ⭐.
