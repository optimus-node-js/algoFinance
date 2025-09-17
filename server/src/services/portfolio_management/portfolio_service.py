import sys
import os
import json
import pika
from datetime import datetime, UTC
from typing import Dict, List, Optional, Any

# Add the project root directory to the Python path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
sys.path.append(PROJECT_ROOT)

from server.src.core.connections import ConnectionManager
from server.src.database.connect import get_db

class PortfolioService:
    """
    Portfolio Management Service for Angel One API integration.
    Handles holdings, positions, fund details, and portfolio analytics.
    """
    
    def __init__(self):
        self.db = get_db()
        self.rabbit_connection = None
        self.rabbit_channel = None
        self._setup_rabbitmq()
    
    def _setup_rabbitmq(self):
        """Sets up RabbitMQ connection for portfolio updates."""
        try:
            self.rabbit_connection = pika.BlockingConnection(pika.ConnectionParameters('localhost'))
            self.rabbit_channel = self.rabbit_connection.channel()
            
            # Declare exchange for portfolio updates
            self.rabbit_channel.exchange_declare(
                exchange='portfolio_updates_exchange', 
                exchange_type='topic',
                durable=True
            )
            print("✅ Portfolio Service RabbitMQ connection established.")
        except pika.exceptions.AMQPConnectionError as e:
            print(f"❌ Portfolio Service RabbitMQ connection failed: {e}")
            self.rabbit_connection = None
            self.rabbit_channel = None

    @ConnectionManager.api_request
    def get_holdings(self) -> Dict[str, Any]:
        """
        Fetch current stock holdings from Angel One API.
        Returns: Dictionary containing holdings data or error info.
        """
        smart_connect = ConnectionManager.get_smartapi_client()
        if not smart_connect:
            return {"status": "error", "message": "No SmartAPI connection available"}
        
        try:
            print("📊 Fetching holdings from Angel One API...")
            response = smart_connect.holding()
            
            if response.get('status') and response.get('data'):
                holdings_data = {
                    "status": "success",
                    "timestamp": datetime.now(UTC).isoformat(),
                    "holdings": response['data'],
                    "total_holdings": len(response['data']) if response['data'] else 0
                }
                
                # Store in database
                self._store_holdings(holdings_data)
                
                # Publish to message queue
                self._publish_portfolio_update("holdings", holdings_data)
                
                print(f"✅ Successfully fetched {holdings_data['total_holdings']} holdings")
                return holdings_data
            else:
                error_msg = response.get('message', 'Unknown error fetching holdings')
                print(f"❌ Error fetching holdings: {error_msg}")
                return {"status": "error", "message": error_msg}
                
        except Exception as e:
            error_msg = f"Exception in get_holdings: {str(e)}"
            print(f"❌ {error_msg}")
            return {"status": "error", "message": error_msg}

    @ConnectionManager.api_request  
    def get_positions(self) -> Dict[str, Any]:
        """
        Fetch current positions (day and net) from Angel One API.
        Returns: Dictionary containing positions data or error info.
        """
        smart_connect = ConnectionManager.get_smartapi_client()
        if not smart_connect:
            return {"status": "error", "message": "No SmartAPI connection available"}
        
        try:
            print("📈 Fetching positions from Angel One API...")
            response = smart_connect.position()
            
            if response.get('status') is True or response.get('status') == 'success':
                positions_data = {
                    "status": "success",
                    "timestamp": datetime.now(UTC).isoformat(),
                    "positions": response.get('data', []),
                    "total_positions": len(response.get('data', [])) if response.get('data') else 0
                }
                
                # Store in database
                self._store_positions(positions_data)
                
                # Publish to message queue
                self._publish_portfolio_update("positions", positions_data)
                
                print(f"✅ Successfully fetched {positions_data['total_positions']} positions")
                return positions_data
            else:
                error_msg = response.get('message', f'Error response: {response}')
                print(f"❌ Error fetching positions: {error_msg}")
                return {"status": "error", "message": error_msg}
                
        except Exception as e:
            error_msg = f"Exception in get_positions: {str(e)}"
            print(f"❌ {error_msg}")
            return {"status": "error", "message": error_msg}

    @ConnectionManager.api_request
    def get_funds(self) -> Dict[str, Any]:
        """
        Fetch fund details and margin information from Angel One API.
        Returns: Dictionary containing fund/margin data or error info.
        """
        smart_connect = ConnectionManager.get_smartapi_client()
        if not smart_connect:
            return {"status": "error", "message": "No SmartAPI connection available"}
        
        try:
            print("💰 Fetching fund details from Angel One API...")
            response = smart_connect.rmsLimit()
            
            if response.get('status') and response.get('data'):
                funds_data = {
                    "status": "success",
                    "timestamp": datetime.now(UTC).isoformat(),
                    "funds": response['data']
                }
                
                # Store in database
                self._store_funds(funds_data)
                
                # Publish to message queue
                self._publish_portfolio_update("funds", funds_data)
                
                print("✅ Successfully fetched fund details")
                return funds_data
            else:
                error_msg = response.get('message', 'Unknown error fetching funds')
                print(f"❌ Error fetching funds: {error_msg}")
                return {"status": "error", "message": error_msg}
                
        except Exception as e:
            error_msg = f"Exception in get_funds: {str(e)}"
            print(f"❌ {error_msg}")
            return {"status": "error", "message": error_msg}

    @ConnectionManager.api_request
    def get_profile(self) -> Dict[str, Any]:
        """
        Fetch user profile information from Angel One API.
        Returns: Dictionary containing profile data or error info.
        """
        smart_connect = ConnectionManager.get_smartapi_client()
        if not smart_connect:
            return {"status": "error", "message": "No SmartAPI connection available"}
        
        try:
            print("👤 Fetching profile from Angel One API...")
            # Get refresh token from the smart_connect client
            refresh_token = getattr(smart_connect, 'refreshToken', None)
            
            if refresh_token:
                response = smart_connect.getProfile(refresh_token)
            else:
                raise Exception("Refresh token not available for profile retrieval")
            
            if response.get('status') and response.get('data'):
                profile_data = {
                    "status": "success",
                    "timestamp": datetime.now(UTC).isoformat(),
                    "profile": response['data']
                }
                
                # Store in database
                self._store_profile(profile_data)
                
                print("✅ Successfully fetched profile information")
                return profile_data
            else:
                error_msg = response.get('message', 'Unknown error fetching profile')
                print(f"❌ Error fetching profile: {error_msg}")
                return {"status": "error", "message": error_msg}
                
        except Exception as e:
            error_msg = f"Exception in get_profile: {str(e)}"
            print(f"❌ {error_msg}")
            return {"status": "error", "message": error_msg}

    def get_portfolio_summary(self) -> Dict[str, Any]:
        """
        Generate a comprehensive portfolio summary combining all data.
        Returns: Dictionary containing complete portfolio analysis.
        """
        try:
            print("📋 Generating portfolio summary...")
            
            # Fetch all portfolio components
            holdings = self.get_holdings()
            positions = self.get_positions()
            funds = self.get_funds()
            profile = self.get_profile()
            
            # Calculate portfolio metrics
            portfolio_summary = {
                "status": "success",
                "timestamp": datetime.now(UTC).isoformat(),
                "summary": {
                    "holdings_count": holdings.get('total_holdings', 0),
                    "positions_count": positions.get('total_positions', 0),
                    "account_status": "active" if all([
                        holdings.get('status') == 'success',
                        positions.get('status') == 'success', 
                        funds.get('status') == 'success'
                    ]) else "error"
                },
                "details": {
                    "holdings": holdings,
                    "positions": positions,
                    "funds": funds,
                    "profile": profile
                }
            }
            
            # Store summary in database
            self._store_portfolio_summary(portfolio_summary)
            
            print("✅ Portfolio summary generated successfully")
            return portfolio_summary
            
        except Exception as e:
            error_msg = f"Exception in get_portfolio_summary: {str(e)}"
            print(f"❌ {error_msg}")
            return {"status": "error", "message": error_msg}

    def _store_holdings(self, holdings_data: Dict[str, Any]):
        """Store holdings data in MongoDB."""
        if self.db is not None:
            try:
                collection = self.db.portfolio_holdings
                collection.insert_one(holdings_data)
                print("✅ Holdings data stored in database")
            except Exception as e:
                print(f"❌ Error storing holdings: {e}")

    def _store_positions(self, positions_data: Dict[str, Any]):
        """Store positions data in MongoDB."""
        if self.db is not None:
            try:
                collection = self.db.portfolio_positions
                collection.insert_one(positions_data)
                print("✅ Positions data stored in database")
            except Exception as e:
                print(f"❌ Error storing positions: {e}")

    def _store_funds(self, funds_data: Dict[str, Any]):
        """Store funds data in MongoDB."""
        if self.db is not None:
            try:
                collection = self.db.portfolio_funds
                collection.insert_one(funds_data)
                print("✅ Funds data stored in database")
            except Exception as e:
                print(f"❌ Error storing funds: {e}")

    def _store_profile(self, profile_data: Dict[str, Any]):
        """Store profile data in MongoDB."""
        if self.db is not None:
            try:
                collection = self.db.user_profile
                collection.insert_one(profile_data)
                print("✅ Profile data stored in database")
            except Exception as e:
                print(f"❌ Error storing profile: {e}")

    def _store_portfolio_summary(self, summary_data: Dict[str, Any]):
        """Store portfolio summary in MongoDB."""
        if self.db is not None:
            try:
                collection = self.db.portfolio_summary
                collection.insert_one(summary_data)
                print("✅ Portfolio summary stored in database")
            except Exception as e:
                print(f"❌ Error storing portfolio summary: {e}")

    def _publish_portfolio_update(self, update_type: str, data: Dict[str, Any]):
        """Publish portfolio updates to RabbitMQ."""
        if self.rabbit_channel:
            try:
                routing_key = f"portfolio.{update_type}"
                message = {
                    "type": update_type,
                    "timestamp": datetime.now(UTC).isoformat(),
                    "data": data
                }
                
                self.rabbit_channel.basic_publish(
                    exchange='portfolio_updates_exchange',
                    routing_key=routing_key,
                    body=json.dumps(message),
                    properties=pika.BasicProperties(delivery_mode=2)  # Persistent message
                )
                print(f"✅ Portfolio update published: {routing_key}")
            except Exception as e:
                print(f"❌ Error publishing portfolio update: {e}")

    def start_portfolio_monitoring(self, interval_seconds: int = 300):
        """
        Start continuous portfolio monitoring service.
        Args:
            interval_seconds: How often to refresh portfolio data (default: 5 minutes)
        """
        import time
        import threading
        
        def monitor_loop():
            while True:
                try:
                    print(f"🔄 Starting portfolio refresh cycle...")
                    self.get_portfolio_summary()
                    print(f"⏰ Next portfolio refresh in {interval_seconds} seconds")
                    time.sleep(interval_seconds)
                except KeyboardInterrupt:
                    print("❕ Portfolio monitoring stopped by user")
                    break
                except Exception as e:
                    print(f"❌ Error in portfolio monitoring: {e}")
                    time.sleep(60)  # Wait 1 minute before retrying
        
        monitor_thread = threading.Thread(target=monitor_loop, daemon=True)
        monitor_thread.start()
        print(f"✅ Portfolio monitoring started (refresh every {interval_seconds}s)")
        return monitor_thread

    def close(self):
        """Close RabbitMQ connections gracefully."""
        if self.rabbit_connection and self.rabbit_connection.is_open:
            self.rabbit_connection.close()
            print("❕ Portfolio Service RabbitMQ connection closed.")


if __name__ == '__main__':
    # Test the Portfolio Service
    print("🚀 Starting Portfolio Service Test...")
    
    portfolio_service = PortfolioService()
    
    try:
        # Test all portfolio functions
        print("\n1. Testing Holdings...")
        holdings = portfolio_service.get_holdings()
        print(f"Holdings Status: {holdings.get('status')}")
        
        print("\n2. Testing Positions...")
        positions = portfolio_service.get_positions()
        print(f"Positions Status: {positions.get('status')}")
        
        print("\n3. Testing Funds...")
        funds = portfolio_service.get_funds()
        print(f"Funds Status: {funds.get('status')}")
        
        print("\n4. Testing Profile...")
        profile = portfolio_service.get_profile()
        print(f"Profile Status: {profile.get('status')}")
        
        print("\n5. Testing Portfolio Summary...")
        summary = portfolio_service.get_portfolio_summary()
        print(f"Portfolio Summary Status: {summary.get('status')}")
        
        print("\n✅ Portfolio Service testing completed!")
        
    except KeyboardInterrupt:
        print("\n❕ Testing interrupted by user")
    except Exception as e:
        print(f"\n❌ Error during testing: {e}")
    finally:
        portfolio_service.close()
