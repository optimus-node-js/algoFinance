import sys
import os
import joblib
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# Add the project root directory to the Python path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..', '..'))
sys.path.append(PROJECT_ROOT)

from server.src.strategy.base_strategy import BaseStrategy

class MlStrategy(BaseStrategy):
    """
    A trading strategy that uses a pre-trained machine learning model
    to generate BUY and SELL signals.
    """
    def __init__(self, symbol_token: str | None = None, interval: str = "1_DAY"):
        super().__init__()
        self.symbol_token = symbol_token
        self.interval = interval
        self.model = None
        self.scaler = None
        self.last_signal_time = datetime.min
        self.features = ['SMA_20', 'SMA_50', 'EMA_20', 'EMA_50', 'RSI_14', 'MACD_12_26_9', 'BBL_5_2.0', 'BBM_5_2.0', 'BBU_5_2.0', 'BBB_5_2.0', 'BBP_5_2.0', 'ADX_14', 'DMP_14', 'DMN_14']
        
        if self.symbol_token:
            self._load_model_and_scaler()

    def _load_model_and_scaler(self):
        """Loads the trained model and scaler for the given symbol."""
        if not self.symbol_token:
            print("⚠️ MlStrategy: Cannot load model without a symbol token.")
            return

        # A real implementation would map the token back to a symbol like 'SBIN'
        # For this example, we'll hardcode it based on a known token.
        symbol_map = {"3045": "SBIN"}
        symbol = symbol_map.get(str(self.symbol_token))

        if not symbol:
            print(f"⚠️ MlStrategy: No symbol mapping found for token {self.symbol_token}.")
            return

        model_dir = "server/src/ml/models"
        model_filename = os.path.join(model_dir, f"{symbol}_{self.interval}_model.joblib")
        scaler_filename = os.path.join(model_dir, f"{symbol}_{self.interval}_scaler.joblib")

        if os.path.exists(model_filename) and os.path.exists(scaler_filename):
            print(f"✅ MlStrategy: Loading model and scaler from {model_dir} for {symbol}...")
            self.model = joblib.load(model_filename)
            self.scaler = joblib.load(scaler_filename)
        else:
            print(f"❌ MlStrategy: Model or scaler not found for symbol {symbol} and interval {self.interval}.")

    def execute(self, market_data: dict):
        """
        Receives enriched market data and executes the ML model logic.
        """
        if self.model is None or self.scaler is None:
            return

        if self.publish_order is None:
            print("MlStrategy: ❌ Cannot execute without a publisher.")
            return
            
        # Throttle to one signal per minute
        if datetime.now() - self.last_signal_time < timedelta(seconds=60):
            return

        # Prepare feature vector from the incoming data
        try:
            feature_values = [market_data[feature] for feature in self.features]
            feature_vector = np.array(feature_values).reshape(1, -1)
        except KeyError as e:
            # print(f"MlStrategy: Skipping tick due to missing feature: {e}")
            return

        # Scale features and make prediction
        scaled_features = self.scaler.transform(feature_vector)
        prediction = self.model.predict(scaled_features)[0]

        order_details = None
        if prediction == 1:
            # Model predicts price will go UP -> Generate BUY signal
            print(f"MlStrategy: 💡 BUY signal triggered for token {market_data['token']} by ML model.")
            order_details = self._create_order_details(market_data, "BUY")
            
        elif prediction == 0:
            # Model predicts price will go DOWN -> Generate SELL signal
            print(f"MlStrategy: 💡 SELL signal triggered for token {market_data['token']} by ML model.")
            order_details = self._create_order_details(market_data, "SELL")

        if order_details:
            self.publish_order(order_details)
            self.last_signal_time = datetime.now()

    def generate_signals(self, historical_data: pd.DataFrame) -> tuple:
        """
        Generates trading signals for backtesting.
        """
        if self.model is None or self.scaler is None:
            raise ValueError("Model and scaler must be loaded before generating signals.")
        
        if not all(feature in historical_data.columns for feature in self.features):
            raise ValueError("Historical data is missing required feature columns for the model.")

        X = historical_data[self.features]
        X_scaled = self.scaler.transform(X)
        
        predictions = self.model.predict(X_scaled)
        
        entries = pd.Series(predictions == 1, index=historical_data.index)
        exits = pd.Series(predictions == 0, index=historical_data.index)
        
        return entries, exits

    def _create_order_details(self, market_data, transaction_type):
        """Helper to construct the order dictionary."""
        return {
            "variety": "NORMAL",
            "tradingsymbol": f"TOKEN-{market_data['token']}",
            "symboltoken": market_data['token'],
            "transactiontype": transaction_type,
            "exchange": "NSE", 
            "ordertype": "MARKET",
            "producttype": "INTRADAY",
            "duration": "DAY",
            "quantity": 1
        } 