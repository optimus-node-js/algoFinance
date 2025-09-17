import sys
import os
from datetime import datetime, timedelta, UTC

# Add the src directory to the Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from database.connect import get_db

def find_instrument_token(symbol, db, smart_connect, exchange="NSE"):
    """
    Finds the symboltoken for a given trading symbol.
    First, it checks a local MongoDB cache. If not found or outdated,
    it fetches from the API and updates the cache.
    It intelligently searches for the correct instrument, prioritizing equity symbols.
    """
    if db is None:
        print("❌ Cannot find instrument token without a DB connection.")
        return None

    collection = db.instruments

    # 1. Check the cache first for the equity symbol (e.g., SBIN-EQ)
    equity_symbol = f"{symbol}-EQ"
    cached_instrument = collection.find_one({"tradingsymbol": equity_symbol})
    if cached_instrument:
        last_updated_ts = cached_instrument.get('last_updated')
        if last_updated_ts and isinstance(last_updated_ts, datetime):
            last_updated_ts = last_updated_ts.replace(tzinfo=UTC)
            if datetime.now(UTC) - last_updated_ts < timedelta(days=1):
                print(f"✅ Found token for {equity_symbol} in DB cache.")
                return cached_instrument['symboltoken']

    # 2. If not in cache or outdated, fetch from API
    print(f"Token for {symbol} not in cache or outdated. Fetching from API...")
    if smart_connect is None:
        print("❌ Cannot fetch from API without a valid SmartConnect object.")
        return None

    try:
        search_result = smart_connect.searchScrip(exchange=exchange, searchscrip=symbol)

        if search_result and search_result.get('status') and search_result.get('data'):
            results = search_result['data']
            
            # --- Intelligent Search Logic ---
            exact_match = None
            equity_match = None
            
            for instrument in results:
                # Prioritize the equity instrument (e.g., "SBIN-EQ")
                if instrument.get('tradingsymbol') == equity_symbol:
                    equity_match = instrument
                    break # Found the best match, no need to continue
                # Fallback to an exact match if no equity symbol is found
                if instrument.get('tradingsymbol') == symbol:
                    exact_match = instrument

            selected_instrument = equity_match if equity_match else exact_match
            # --- End of Intelligent Search Logic ---

            if selected_instrument:
                token = selected_instrument['symboltoken']
                tradingsymbol = selected_instrument['tradingsymbol']
                print(f"✅ Found token for {tradingsymbol} via API: {token}")

                # 3. Update the cache in MongoDB
                selected_instrument['last_updated'] = datetime.now(UTC)
                collection.update_one(
                    {"symboltoken": token},
                    {"$set": selected_instrument},
                    upsert=True
                )
                print(f"✅ Cached token for {tradingsymbol} in DB.")
                return token

            # If no suitable instrument was found after checking all results
            print(f"❌ Symbol {symbol} (or its equity variant) not found in API search results.")
            # Optional: Log the full list for debugging
            # print("Full search results:", results)
            return None
        else:
            error_message = search_result.get('message', 'No message provided.')
            print(f"❌ Failed to search for instrument via API. Message: {error_message}")
            return None

    except Exception as e:
        print(f"❌ An error occurred while searching for instrument: {e}")
        return None

if __name__ == '__main__':
    print("This script is now a utility module. Run a backtest or training script to test its functionality.") 