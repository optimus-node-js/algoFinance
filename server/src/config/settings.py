import os
from dotenv import load_dotenv

# Build a more robust path to the project's root directory
# This assumes settings.py is in server/src/config
# It goes up three levels to find the project root where .env is located.
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
dotenv_path = os.path.join(PROJECT_ROOT, '.env')

load_dotenv(dotenv_path=dotenv_path)

# MongoDB Config
MONGO_URI = os.getenv("MONGO_URI")
DB_NAME = os.getenv("DB_NAME")

# Angel One API Config
API_KEY = os.getenv("API_KEY")
SECRET_KEY = os.getenv("SECRET_KEY")
CLIENT_ID = os.getenv("CLIENT_ID")
PASSWORD = os.getenv("PASSWORD")
TOTP_SECRET = os.getenv("TOTP_SECRET") 