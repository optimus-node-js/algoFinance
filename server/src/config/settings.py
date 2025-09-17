# server/src/config/settings.py
import os
from dotenv import load_dotenv

# Load environment variables from a .env file at the project root
dotenv_path = os.path.join(os.path.dirname(__file__), '..', '..', '..', '.env')
load_dotenv(dotenv_path=dotenv_path)

# --- MongoDB Configuration ---
MONGO_URI = os.getenv("MONGO_URI")
DB_NAME = os.getenv("DB_NAME", "algofinance")

# --- Angel One API Credentials ---
# A dictionary to hold all API keys for easy rotation
API_KEYS = {
    "API_KEY_1": os.getenv("API_KEY"),
    "API_KEY_2": os.getenv("API_KEY_2"),
    "API_KEY_3": os.getenv("API_KEY_3"),
    "API_KEY_4": os.getenv("API_KEY_4"),
    "API_KEY_5": os.getenv("API_KEY_5"),
}

# Primary credentials for login
SECRET_KEY = os.getenv("SECRET_KEY")
CLIENT_ID = os.getenv("CLIENT_ID")
PASSWORD = os.getenv("PASSWORD")
TOTP_SECRET = os.getenv("TOTP_SECRET") 

# --- Validation ---
def validate_credentials():
    """Checks if essential credentials are loaded."""
    if not all([MONGO_URI, DB_NAME, SECRET_KEY, CLIENT_ID, PASSWORD, TOTP_SECRET]):
        raise ValueError("One or more essential environment variables are missing. Check your .env file.")
    
    # Check if at least the primary API key is present
    if not API_KEYS["API_KEY_1"]:
        raise ValueError("Primary API_KEY is missing from .env file.")

    print("✅ Configuration settings loaded and validated successfully.")

# Run validation on import
validate_credentials() 