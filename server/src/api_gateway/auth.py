import sys
import os
import pyotp
from SmartApi import SmartConnect

# Add the src directory to the Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from config.settings import API_KEY, SECRET_KEY, CLIENT_ID, PASSWORD, TOTP_SECRET

class AngelOneAuth:
    def __init__(self):
        self.api_key = API_KEY
        self.secret_key = SECRET_KEY
        self.client_id = CLIENT_ID
        self.password = PASSWORD
        self.totp_secret = TOTP_SECRET
        self.smart_connect = None
        self.feed_token = None
        self.jwt_token = None

    def login(self):
        """
        Logs into Angel One and establishes a session.
        Returns True on success, False on failure.
        """
        print("Attempting to log in to Angel One...")
        if not all([self.api_key, self.secret_key, self.client_id, self.password, self.totp_secret]):
            print("❌ Error: Missing one or more API credentials in the .env file.")
            return False

        try:
            self.smart_connect = SmartConnect(self.api_key)
            
            # Generate TOTP
            totp = pyotp.TOTP(self.totp_secret).now()

            data = {
                "clientcode": self.client_id,
                "password": self.password,
                "totp": totp
            }
            
            session_data = self.smart_connect.generateSession(
                data["clientcode"], 
                data["password"], 
                data["totp"]
            )

            if session_data and session_data['status'] and session_data['data']:
                self.jwt_token = session_data['data']['jwtToken']
                self.feed_token = session_data['data']['feedToken']
                print("✅ Angel One login successful.")
                print(f"Feed Token: {self.feed_token}")
                return True
            else:
                print("❌ Angel One login failed.")
                print("Response:", session_data)
                return False

        except Exception as e:
            print(f"❌ An error occurred during login: {e}")
            return False

if __name__ == '__main__':
    auth = AngelOneAuth()
    auth.login() 