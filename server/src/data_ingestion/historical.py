import pandas as pd
import sys
import os

# Add the project root directory to the Python path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.append(PROJECT_ROOT)

from server.src.core.connections import ConnectionManager
from server.src.config import settings

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
    def __init__(self):
        # The __init__ is now simpler. Connections are fetched when needed.
        mongo_client = ConnectionManager.get_mongodb_client()
        self.db = mongo_client[settings.DB_NAME] if mongo_client and settings.DB_NAME else None
        self.instrument_collection = self.db.instruments if self.db is not None else None

    @ConnectionManager.api_request
    def get_historical_data(self, symbol_token: str, from_date: str, to_date: str, interval: str):
        """
        Fetches historical data for a given symbol token and date range.
        This method is decorated to be rate-limited.
        """
        smart_connect = ConnectionManager.get_smartapi_client()
        if smart_connect is None:
            print("❌ Cannot fetch historical data without a SmartAPI connection.")
            return pd.DataFrame()

        print(f"Fetching historical data for token {symbol_token} from {from_date} to {to_date}...")
        try:
            api_interval = INTERVAL_MAP.get(interval.upper())
            if not api_interval:
                raise ValueError(f"Invalid interval '{interval}'. Supported intervals are: {list(INTERVAL_MAP.keys())}")

            params = {
                "exchange": "NSE",
                "symboltoken": symbol_token,
                "interval": api_interval,
                "fromdate": from_date,
                "todate": to_date
            }
            
            response = smart_connect.getCandleData(params)

            # The API returns a dictionary on success, with the candle data in the 'data' key.
            if isinstance(response, dict) and response.get("status") is True and response.get("data"):
                df = pd.DataFrame(response['data'], columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
                df['timestamp'] = pd.to_datetime(df['timestamp'])
                df.set_index('timestamp', inplace=True)
                print(f"✅ Successfully fetched {len(df)} data points.")
                return df
            
            # The API returns a dictionary on error/no data
            elif isinstance(response, dict) and response.get("status") is False:
                error_message = response.get("message", "No message")
                print(f"❌ An error occurred while fetching historical data: {error_message}")
                return pd.DataFrame()

            else:
                # This handles cases where the API call is successful but returns no data (e.g., market holidays)
                print("✅ API call successful, but no data returned for the given period.")
                return pd.DataFrame()
        except Exception as e:
            print(f"❌ An error occurred while fetching historical data: {e}")
            return pd.DataFrame()

if __name__ == '__main__':
    # This block is for direct testing of the handler
    print("Running historical data handler example...")
    
    # Import settings to use the validated DB_NAME
    from server.src.config import settings
    from server.src.api_gateway.utils import find_instrument_token

    # No longer need to instantiate handler, just get clients from the manager
    db_client = ConnectionManager.get_mongodb_client()
    smart_api_client = ConnectionManager.get_smartapi_client()

    if db_client and smart_api_client and settings.DB_NAME:
        db = db_client[settings.DB_NAME]
        token = find_instrument_token('SBIN-EQ', db, smart_api_client)
        
        # We create an instance only when we are ready to call the method
        handler = HistoricalDataHandler()
        if token:
            data = handler.get_historical_data(
                symbol_token=token,
                from_date='2023-01-01 09:15',
                to_date='2023-01-05 15:30',
                interval='5_MINUTE'
            )
            if not data.empty:
                print(data.head())
        else:
            print("Token not found for symbol, cannot run example.")
    else:
        print("Connection failed, cannot run example.") 