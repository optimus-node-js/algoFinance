import sys
import os
from datetime import datetime
import pandas as pd

# Add the parent 'src' directory to the path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from database.connect import get_db
from api_gateway.auth import AngelOneAuth

# Define constants for candle intervals supported by the API
INTERVAL_MAP = {
    "1_MINUTE": "ONE_MINUTE",
    "3_MINUTE": "THREE_MINUTE",
    "5_MINUTE": "FIVE_MINUTE",
    "10_MINUTE": "TEN_MINUTE",
    "15_MINUTE": "FIFTEEN_MINUTE",
    "30_MINUTE": "THIRTY_MINUTE",
    "1_HOUR": "ONE_HOUR",
    "1_DAY": "ONE_DAY",
}

class HistoricalDataHandler:
    """
    Handles fetching and caching of historical candlestick data.
    """
    def __init__(self, auth_session: AngelOneAuth):
        if not auth_session or not auth_session.smart_connect:
            raise ValueError("A valid, authenticated AngelOneAuth session is required.")
        self.smart_connect = auth_session.smart_connect
        self.db = get_db()
        self.candles_collection = self.db.market_data_candles if self.db is not None else None

    def get_historical_data(self, symbol_token: str, from_date: str, to_date: str, interval: str) -> pd.DataFrame:
        """
        Fetches historical data, utilizing a DB cache first.
        Returns a pandas DataFrame with OHLCV data.
        """
        if self.candles_collection is None:
            print("❌ Cannot get historical data without a DB connection.")
            return pd.DataFrame()

        # For now, we will fetch directly from the API. Caching will be added later.
        print(f"Fetching historical data for token {symbol_token} from {from_date} to {to_date}...")

        try:
            api_interval = INTERVAL_MAP.get(interval.upper())
            if not api_interval:
                raise ValueError(f"Invalid interval '{interval}'. Supported intervals are: {list(INTERVAL_MAP.keys())}")

            historic_param = {
                "exchange": "NSE",
                "symboltoken": symbol_token,
                "interval": api_interval,
                "fromdate": from_date,
                "todate": to_date
            }
            
            raw_data = self.smart_connect.getCandleData(historic_param)

            if not raw_data or raw_data.get("status") is not True or not raw_data.get("data"):
                print("❌ Failed to fetch historical data from API.")
                print("API Response:", raw_data.get("message", "No message"))
                return pd.DataFrame()

            # --- Process and Format Data ---
            df = pd.DataFrame(raw_data['data'], columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            df.set_index('timestamp', inplace=True)
            
            print(f"✅ Successfully fetched {len(df)} data points.")
            
            # TODO: Add data to MongoDB cache here.

            return df

        except Exception as e:
            print(f"❌ An error occurred while fetching historical data: {e}")
            return pd.DataFrame()

if __name__ == '__main__':
    # Example of how to use the handler
    print("Running historical data handler example...")
    auth = AngelOneAuth()
    if auth.login():
        handler = HistoricalDataHandler(auth)
        
        # We need to find the token for a symbol first
        from api_gateway.utils import find_instrument_token
        symbol = "SBIN-EQ"
        token = find_instrument_token(symbol, handler.db, handler.smart_connect)

        if token:
            data = handler.get_historical_data(
                symbol_token=token,
                from_date="2024-01-01 09:15",
                to_date="2024-01-05 15:30",
                interval="5_MINUTE"
            )
            if not data.empty:
                print("\nFetched Data Sample:")
                print(data.head())
    else:
        print("Login failed, cannot run example.") 