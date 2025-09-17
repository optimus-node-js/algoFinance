# server/src/core/connections.py
import os
import sys
from threading import Lock, current_thread
from pymongo import MongoClient
from SmartApi.smartConnect import SmartConnect
from limiter import Limiter
import pyotp
import itertools

# Add the project root directory to the Python path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.append(PROJECT_ROOT)

# Import settings from the centralized config file
from server.src.config import settings

class ConnectionManager:
    """
    A thread-safe singleton manager for handling database and API connections.
    It now uses a pool of API keys for rate limiting and rotates through them.
    """
    _mongo_client = None
    _smartapi_clients = {}  # A dictionary to hold clients for each API key
    _api_key_cycler = None
    _lock = Lock()

    # Define rate limits based on Angel One documentation using the new limiter library
    # Orders: 20 requests/sec, Others: 10 requests/sec
    # We use a slightly more conservative limit to be safe.
    rate_limiter_orders = Limiter(rate=18, capacity=20, consume=1)
    rate_limiter_data = Limiter(rate=9, capacity=10, consume=1)

    @classmethod
    def get_mongodb_client(cls):
        with cls._lock:
            if cls._mongo_client is None:
                print("Initializing MongoDB connection for the first time...")
                try:
                    cls._mongo_client = MongoClient(settings.MONGO_URI)
                    # The ismaster command is cheap and does not require auth.
                    cls._mongo_client.admin.command('ismaster')
                    print("✅ MongoDB connection successful.")
                except Exception as e:
                    print(f"❌ MongoDB connection failed: {e}")
                    cls._mongo_client = None
            return cls._mongo_client

    @classmethod
    def get_smartapi_client(cls):
        """
        Provides a rate-limited SmartAPI client.
        It uses a pool of API keys and rotates them to distribute load.
        """
        with cls._lock:
            if not cls._api_key_cycler:
                # Filter out keys that are not set in the .env file
                valid_keys = {k: v for k, v in settings.API_KEYS.items() if v}
                if not valid_keys:
                    raise ValueError("No Angel One API keys are set in the .env file.")
                cls._api_key_cycler = itertools.cycle(valid_keys.items())

            current_key_name, current_api_key = next(cls._api_key_cycler)
            
            if current_key_name not in cls._smartapi_clients:
                print(f"Initializing Angel One SmartAPI connection for '{current_key_name}'...")
                try:
                    client = SmartConnect(current_api_key)
                    
                    # We can assert that TOTP_SECRET is a string because settings.py validates it on import
                    assert settings.TOTP_SECRET is not None
                    totp = pyotp.TOTP(settings.TOTP_SECRET).now()
                    login_data = client.generateSession(
                        settings.CLIENT_ID,
                        settings.PASSWORD,
                        totp
                    )
                    
                    if login_data['status'] and login_data['data']['jwtToken']:
                        print(f"✅ Angel One login successful for '{current_key_name}'.")
                        # Store the refresh token in the client for profile API calls
                        if 'refreshToken' in login_data['data']:
                            client.refreshToken = login_data['data']['refreshToken']
                        cls._smartapi_clients[current_key_name] = client
                    else:
                        raise ConnectionError(f"Login failed for '{current_key_name}': {login_data.get('message')}")

                except Exception as e:
                    print(f"❌ Angel One SmartAPI connection failed for '{current_key_name}': {e}")
                    # Remove the failed client so it can be retried later
                    if current_key_name in cls._smartapi_clients:
                        del cls._smartapi_clients[current_key_name]
                    return None
            
            return cls._smartapi_clients[current_key_name]

    @classmethod
    def api_request(cls, func):
        """
        A decorator to wrap API calls with the appropriate rate limiter.
        It intelligently selects the limiter based on the function name.
        """
        def wrapper(*args, **kwargs):
            # Choose the limiter based on the function being decorated
            if "order" in func.__name__.lower():
                limiter = cls.rate_limiter_orders
                # print("DEBUG: Using ORDER rate limiter.") # Optional: for debugging
            else:
                limiter = cls.rate_limiter_data
                # print("DEBUG: Using DATA rate limiter.") # Optional: for debugging
            
            with limiter:
                return func(*args, **kwargs)
        return wrapper

# --- Cleanup ---
# Ensure connections are closed gracefully if needed, though singletons usually live for the app's lifetime.
# This part might be expanded later for a more graceful shutdown sequence.
def close_all_connections():
    with ConnectionManager._lock:
        if ConnectionManager._mongo_client:
            ConnectionManager._mongo_client.close()
            print("MongoDB connection closed.")
        # SmartAPI library does not have an explicit close(), but you can add logout logic
        for key, client in ConnectionManager._smartapi_clients.items():
             if hasattr(client, 'terminateSession'):
                 client.terminateSession(settings.CLIENT_ID)
                 print(f"Terminated session for API key {key}.") 