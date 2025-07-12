import pandas as pd
import pandas_ta as ta

class FeatureEngine:
    """
    A class to encapsulate the logic for generating technical analysis features.
    This makes the feature generation process modular and configurable.
    """
    def __init__(self):
        """
        Initializes the FeatureEngine and defines the strategy for feature generation.
        """
        self.strategy = ta.Strategy(
            name="CommonIndicators",
            description="A collection of common technical analysis indicators.",
            ta=[
                {"kind": "sma", "length": 20},
                {"kind": "sma", "length": 50},
                {"kind": "sma", "length": 200},
                {"kind": "ema", "length": 20},
                {"kind": "ema", "length": 50},
                {"kind": "rsi"},
                {"kind": "macd"},
                {"kind": "bbands"},
                {"kind": "atr"},
                {"kind": "adx"},
            ]
        )
        print("✅ FeatureEngine initialized with 'CommonIndicators' strategy.")

    def add_features(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        Generates and appends technical analysis features to the given OHLCV data.

        :param data: A pandas DataFrame with 'open', 'high', 'low', 'close', 'volume' columns.
        :return: The original DataFrame with the new feature columns appended.
        """
        if not isinstance(data, pd.DataFrame):
            raise TypeError("Input 'data' must be a pandas DataFrame.")
        
        required_columns = {'open', 'high', 'low', 'close', 'volume'}
        if not required_columns.issubset(data.columns):
            raise ValueError(f"Input DataFrame must contain all of the following columns: {required_columns}")

        print("Generating technical features...")

        # Apply the pre-defined strategy to the data
        data.ta.strategy(self.strategy)
        
        # pandas-ta might produce columns with NaNs at the beginning of the series
        # where there isn't enough data. We'll backfill and then forward-fill.
        data.bfill(inplace=True)
        data.ffill(inplace=True)

        print(f"✅ Feature generation complete. Added {len(self.strategy.ta)} indicators.")
        
        return data

if __name__ == '__main__':
    # Example of how to use the feature generator
    print("Running FeatureEngine example...")
    
    # Create a sample OHLCV DataFrame
    dummy_data = {
        'open': [100, 102, 101, 103, 105] * 20,
        'high': [103, 104, 103, 106, 107] * 20,
        'low': [99, 101, 100, 102, 104] * 20,
        'close': [102, 103, 102, 105, 106] * 20,
        'volume': [1000, 1200, 1100, 1500, 1600] * 20
    }
    df = pd.DataFrame(dummy_data)
    
    # Instantiate the engine and add features
    feature_engine = FeatureEngine()
    df_with_features = feature_engine.add_features(df)
    
    print("\n--- DataFrame with Features ---")
    print(df_with_features.head())
    print("\nColumns added:")
    print(list(df_with_features.columns)) 