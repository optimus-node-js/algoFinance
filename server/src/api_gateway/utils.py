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
    """
    if db is None:
        print("❌ Cannot find instrument token without a DB connection.")
        return None
        
    collection = db.instruments
    
    # 1. Check the cache first
    cached_instrument = collection.find_one({"tradingsymbol": symbol})
    if cached_instrument:
        last_updated_ts = cached_instrument.get('last_updated')
        # Ensure the timestamp from the DB is timezone-aware for comparison
        if last_updated_ts:
            last_updated_ts = last_updated_ts.replace(tzinfo=UTC)
            if datetime.now(UTC) - last_updated_ts < timedelta(days=1):
                print(f"✅ Found token for {symbol} in DB cache.")
                return cached_instrument['symboltoken']

    # 2. If not in cache or outdated, fetch from API
    print(f"Token for {symbol} not in cache or outdated. Fetching from API...")
    if smart_connect is None:
        print("❌ Cannot fetch from API without a valid SmartConnect object.")
        return None
    
    try:
        search_result = smart_connect.searchScrip(exchange=exchange, searchscrip=symbol)
        
        if search_result and search_result['status'] and search_result['data']:
            for instrument_data in search_result['data']:
                if instrument_data['tradingsymbol'] == symbol:
                    token = instrument_data['symboltoken']
                    print(f"✅ Found token for {symbol} via API: {token}")
                    
                    # 3. Update the cache in MongoDB
                    instrument_data['last_updated'] = datetime.now(UTC)
                    collection.update_one(
                        {"symboltoken": token},
                        {"$set": instrument_data},
                        upsert=True
                    )
                    print(f"✅ Cached token for {symbol} in DB.")
                    return token
                    
            print(f"❌ Symbol {symbol} not found in API search results.")
            return None
        else:
            print("❌ Failed to search for instrument via API.")
            print("Response:", search_result)
            return None
            
    except Exception as e:
        print(f"❌ An error occurred while searching for instrument: {e}")
        return None

if __name__ == '__main__':
    # This test will no longer work directly as it requires an authenticated smart_connect object.
    # The logic is now tested via the strategy script.
    print("This script is now a utility module. Run simple_strategy.py to test its functionality.") 