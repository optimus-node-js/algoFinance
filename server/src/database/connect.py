from pymongo import MongoClient
from pymongo.database import Database
import sys
import os

# Add the src directory to the Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from config.settings import MONGO_URI, DB_NAME

class MongoDBConnection:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(MongoDBConnection, cls).__new__(cls)
            try:
                cls._instance.client = MongoClient(MONGO_URI)
                # The ismaster command is cheap and does not require auth.
                cls._instance.client.admin.command('ismaster')
                print("✅ MongoDB connection successful.")
            except Exception as e:
                print(f"❌ MongoDB connection failed: {e}")
                cls._instance.client = None
        return cls._instance

    def get_database(self) -> Database:
        if self.client and DB_NAME:
            return self.client[DB_NAME]
        elif not DB_NAME:
            print("❌ DB_NAME is not set in your .env file.")
        return None

# Singleton instance
db_connection = MongoDBConnection()

def get_db() -> Database:
    """
    Returns a MongoDB database instance.
    """
    return db_connection.get_database()

if __name__ == "__main__":
    # Example of how to use it
    db = get_db()
    if db is not None:
        print(f"Successfully connected to database: '{DB_NAME}'")
        print("Collections:", db.list_collection_names())
    else:
        print("Could not connect to the database.") 