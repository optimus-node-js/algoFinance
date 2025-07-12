# Active Context

## Current Focus: Phase 3 - AI/ML Integration & Feature Engineering

The immediate priority is to build a robust feature engineering pipeline. This will serve as the foundation for all future AI/ML models by transforming raw market data into meaningful features that predictive models can consume.

## Next Steps

1.  **Verify Environment:** Re-install all dependencies from `server/requirements.txt` to ensure the new Python 3.11 environment is stable and correctly configured.
2.  **Create Feature Engineering Module:** Develop a dedicated `FeatureEngine` class within `server/src/ml/feature_engineering.py`. This module will be responsible for generating a wide array of technical indicators using the `pandas-ta` library.
3.  **Integrate with Data Pipeline:** Modify the `Data Ingestion Service` to pass raw data through the `FeatureEngine` before publishing it to the message queue, thereby enriching the data stream for all consumer services.
4.  **Update Downstream Services:** Adapt the `Strategy Service` and `Backtesting Engine` to utilize the newly available features.

## Key Decisions & Considerations

- **Library Choice:** `pandas-ta` is the chosen library for feature generation due to its comprehensive set of indicators and seamless integration with Pandas DataFrames.
- **Modularity:** The `FeatureEngine` will be designed as a standalone, reusable component to ensure that the same feature generation logic is applied consistently across both live trading and backtesting.
- **Performance:** Feature generation can be computationally intensive. The implementation should be optimized for speed to minimize latency in the live data pipeline. 