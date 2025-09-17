import sys
import os
import pandas as pd
from datetime import datetime, timedelta

# Add the parent 'src' directory to the path to allow for absolute imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from strategy.base_strategy import BaseStrategy

class RsiStrategy(BaseStrategy):
    """
    A simple trading strategy based on the Relative Strength Index (RSI).
    - Buys when RSI crosses below a lower threshold (e.g., 30).
    - Sells when RSI crosses above an upper threshold (e.g., 70).
    """
    def __init__(self, rsi_lower=30, rsi_upper=70):
        super().__init__()
        self.rsi_lower = rsi_lower
        self.rsi_upper = rsi_upper
        self.last_signal_time = datetime.min # To prevent spamming orders

    def execute(self, market_data: dict):
        """
        Receives enriched market data and executes the RSI logic.
        """
        # --- Basic Checks ---
        if self.publish_order is None:
            print("RsiStrategy: ❌ Cannot execute without a publisher.")
            return

        required_keys = ['RSI_14', 'token', 'close']
        if not all(key in market_data for key in required_keys):
            # This might happen for the first few ticks before features are generated.
            # print(f"RsiStrategy: Skipping tick due to missing data. Keys: {market_data.keys()}")
            return
        
        # --- Throttle to one signal per minute ---
        if datetime.now() - self.last_signal_time < timedelta(seconds=60):
            return

        # --- Strategy Logic ---
        rsi_value = market_data['RSI_14']
        
        order_details = None
        if rsi_value < self.rsi_lower:
            # Oversold condition -> Generate BUY signal
            print(f"RsiStrategy: 💡 BUY signal triggered for token {market_data['token']} at RSI {rsi_value:.2f}")
            order_details = self._create_order_details(market_data, "BUY")
            
        elif rsi_value > self.rsi_upper:
            # Overbought condition -> Generate SELL signal
            print(f"RsiStrategy: 💡 SELL signal triggered for token {market_data['token']} at RSI {rsi_value:.2f}")
            order_details = self._create_order_details(market_data, "SELL")

        if order_details:
            self.publish_order(order_details)
            self.last_signal_time = datetime.now()

    def _create_order_details(self, market_data, transaction_type):
        """Helper to construct the order dictionary."""
        return {
            "variety": "NORMAL",
            "tradingsymbol": f"TOKEN-{market_data['token']}", # Placeholder, real mapping needed
            "symboltoken": market_data['token'],
            "transactiontype": transaction_type,
            "exchange": "NSE", 
            "ordertype": "MARKET",
            "producttype": "INTRADAY",
            "duration": "DAY",
            "quantity": 1
        }

    def generate_signals(self, historical_data: pd.DataFrame) -> tuple:
        """
        Generates trading signals for backtesting.
        Note: This requires the historical_data DataFrame to already have the RSI_14 column.
        """
        if 'RSI_14' not in historical_data.columns:
            raise ValueError("Historical data must contain 'RSI_14' column for RsiStrategy.")
            
        entries = historical_data['RSI_14'] < self.rsi_lower
        exits = historical_data['RSI_14'] > self.rsi_upper
        
        return entries, exits 