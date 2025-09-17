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

class MarketDataService:
    """
    Market Data Service for Angel One API integration.
    Handles LTP, quotes, option chains, and market status information.
    """
    
    def __init__(self):
        self.db = get_db()
        self.rabbit_connection = None
        self.rabbit_channel = None
        self._setup_rabbitmq()
    
    def _setup_rabbitmq(self):
        """Sets up RabbitMQ connection for market data updates."""
        try:
            self.rabbit_connection = pika.BlockingConnection(pika.ConnectionParameters('localhost'))
            self.rabbit_channel = self.rabbit_connection.channel()
            
            # Declare exchange for market data updates
            self.rabbit_channel.exchange_declare(
                exchange='market_data_updates_exchange', 
                exchange_type='topic',
                durable=True
            )
            print("✅ Market Data Service RabbitMQ connection established.")
        except pika.exceptions.AMQPConnectionError as e:
            print(f"❌ Market Data Service RabbitMQ connection failed: {e}")
            self.rabbit_connection = None
            self.rabbit_channel = None

    @ConnectionManager.api_request
    def get_ltp(self, exchange: str, tradingsymbol: str, symboltoken: str) -> Dict[str, Any]:
        """
        Get Last Traded Price (LTP) for a specific instrument.
        Args:
            exchange: Exchange name (NSE, BSE, etc.)
            tradingsymbol: Trading symbol
            symboltoken: Instrument token
        Returns: Dictionary containing LTP data or error info.
        """
        smart_connect = ConnectionManager.get_smartapi_client()
        if not smart_connect:
            return {"status": "error", "message": "No SmartAPI connection available"}
        
        try:
            print(f"💰 Fetching LTP for {tradingsymbol} ({symboltoken})...")
            
            response = smart_connect.ltpData(exchange, tradingsymbol, symboltoken)
            
            if response.get('status') is True or response.get('status') == 'success':
                ltp_data = {
                    "status": "success",
                    "timestamp": datetime.now(UTC).isoformat(),
                    "exchange": exchange,
                    "tradingsymbol": tradingsymbol,
                    "symboltoken": symboltoken,
                    "ltp_info": response.get('data', {})
                }
                
                # Store in database
                self._store_ltp_data(ltp_data)
                
                # Publish to message queue
                self._publish_market_update("ltp", ltp_data)
                
                print(f"✅ Successfully fetched LTP for {tradingsymbol}")
                return ltp_data
            else:
                error_msg = response.get('message', f'Error response: {response}')
                print(f"❌ Error fetching LTP: {error_msg}")
                return {"status": "error", "message": error_msg}
                
        except Exception as e:
            error_msg = f"Exception in get_ltp: {str(e)}"
            print(f"❌ {error_msg}")
            # Add specific handling for JSON parsing errors
            if "parse" in str(e).lower() or "json" in str(e).lower():
                print("🔍 JSON parsing error detected - checking API response format")
            return {"status": "error", "message": error_msg}

    @ConnectionManager.api_request  
    def get_quote(self, exchange: str, tradingsymbol: str, symboltoken: str) -> Dict[str, Any]:
        """
        Get detailed quote information using LTP as fallback since getMarketData has server issues.
        Args:
            exchange: Exchange name (NSE, BSE, etc.)
            tradingsymbol: Trading symbol
            symboltoken: Instrument token
        Returns: Dictionary containing quote data or error info.
        """
        smart_connect = ConnectionManager.get_smartapi_client()
        if not smart_connect:
            return {"status": "error", "message": "No SmartAPI connection available"}
        
        try:
            print(f"📊 Fetching quote for {tradingsymbol} ({symboltoken})...")
            
            # First try getMarketData with proper error handling
            try:
                exchange_tokens = [{
                    "exchange": exchange,
                    "tokens": [symboltoken]
                }]
                
                response = smart_connect.getMarketData("FULL", exchange_tokens)
                
                if response and response.get('status') is True:
                    quote_data = {
                        "status": "success",
                        "timestamp": datetime.now(UTC).isoformat(),
                        "exchange": exchange,
                        "tradingsymbol": tradingsymbol,
                        "symboltoken": symboltoken,
                        "quote_info": response.get('data', {}),
                        "data_source": "getMarketData"
                    }
                    
                    # Store in database
                    self._store_quote_data(quote_data)
                    
                    # Publish to message queue
                    self._publish_market_update("quote", quote_data)
                    
                    print(f"✅ Successfully fetched quote for {tradingsymbol} using getMarketData")
                    return quote_data
                    
            except Exception as market_data_error:
                print(f"⚠️ getMarketData failed: {market_data_error}, falling back to LTP...")
            
            # Fallback to LTP if getMarketData fails
            ltp_response = smart_connect.ltpData(exchange, tradingsymbol, symboltoken)
            
            if ltp_response and ltp_response.get('status') is True:
                quote_data = {
                    "status": "success",
                    "timestamp": datetime.now(UTC).isoformat(),
                    "exchange": exchange,
                    "tradingsymbol": tradingsymbol,
                    "symboltoken": symboltoken,
                    "quote_info": ltp_response.get('data', {}),
                    "data_source": "ltpData_fallback"
                }
                
                # Store in database
                self._store_quote_data(quote_data)
                
                # Publish to message queue
                self._publish_market_update("quote", quote_data)
                
                print(f"✅ Successfully fetched quote for {tradingsymbol} using LTP fallback")
                return quote_data
            else:
                error_msg = ltp_response.get('message', f'Error response: {ltp_response}')
                print(f"❌ Error fetching quote (LTP fallback): {error_msg}")
                return {"status": "error", "message": error_msg}
                
        except Exception as e:
            error_msg = f"Exception in get_quote: {str(e)}"
            print(f"❌ {error_msg}")
            return {"status": "error", "message": error_msg}

    @ConnectionManager.api_request
    def get_candle_data(self, exchange: str, tradingsymbol: str, symboltoken: str, interval: str = "ONE_MINUTE", fromdate: str = None, todate: str = None) -> Dict[str, Any]:
        """
        Get OHLC candle data for a specific instrument.
        Args:
            exchange: Exchange name (NSE, BSE, etc.)
            tradingsymbol: Trading symbol
            symboltoken: Instrument token
            interval: Candle interval (ONE_MINUTE, FIVE_MINUTE, etc.)
            fromdate: Start date (YYYY-MM-DD HH:MM format)
            todate: End date (YYYY-MM-DD HH:MM format)
        Returns: Dictionary containing candle data or error info.
        """
        smart_connect = ConnectionManager.get_smartapi_client()
        if not smart_connect:
            return {"status": "error", "message": "No SmartAPI connection available"}
        
        try:
            print(f"📈 Fetching candle data for {tradingsymbol} ({symboltoken})...")
            
            # Set default dates if not provided (last 1 day)
            from datetime import datetime, timedelta
            if not todate:
                todate = datetime.now().strftime("%Y-%m-%d %H:%M")
            if not fromdate:
                fromdate = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d %H:%M")
            
            response = smart_connect.getCandleData(
                exchange=exchange,
                symboltoken=symboltoken,
                interval=interval,
                fromdate=fromdate,
                todate=todate
            )
            
            if response and response.get('status') is True:
                candle_data = {
                    "status": "success",
                    "timestamp": datetime.now().isoformat(),
                    "exchange": exchange,
                    "tradingsymbol": tradingsymbol,
                    "symboltoken": symboltoken,
                    "interval": interval,
                    "fromdate": fromdate,
                    "todate": todate,
                    "candle_info": response.get('data', []),
                    "total_candles": len(response.get('data', [])) if response.get('data') else 0
                }
                
                # Store in database
                self._store_candle_data(candle_data)
                
                # Publish to message queue
                self._publish_market_update("candle_data", candle_data)
                
                print(f"✅ Successfully fetched {candle_data['total_candles']} candles for {tradingsymbol}")
                return candle_data
            else:
                error_msg = response.get('message', f'Error response: {response}')
                print(f"❌ Error fetching candle data: {error_msg}")
                return {"status": "error", "message": error_msg}
                
        except Exception as e:
            error_msg = f"Exception in get_candle_data: {str(e)}"
            print(f"❌ {error_msg}")
            return {"status": "error", "message": error_msg}

    @ConnectionManager.api_request
    def search_instruments(self, exchange: str, searchscrip: str) -> Dict[str, Any]:
        """
        Search for instruments by symbol name.
        Args:
            exchange: Exchange name (NSE, BSE, etc.)
            searchscrip: Search string for instrument
        Returns: Dictionary containing search results or error info.
        """
        smart_connect = ConnectionManager.get_smartapi_client()
        if not smart_connect:
            return {"status": "error", "message": "No SmartAPI connection available"}
        
        try:
            print(f"🔍 Searching instruments for '{searchscrip}' on {exchange}...")
            
            response = smart_connect.searchScrip(exchange, searchscrip)
            
            if response.get('status') is True or response.get('status') == 'success':
                search_data = {
                    "status": "success",
                    "timestamp": datetime.now(UTC).isoformat(),
                    "exchange": exchange,
                    "search_term": searchscrip,
                    "results": response.get('data', []),
                    "total_results": len(response.get('data', [])) if response.get('data') else 0
                }
                
                # Store in database
                self._store_search_results(search_data)
                
                # Publish to message queue
                self._publish_market_update("instrument_search", search_data)
                
                print(f"✅ Found {search_data['total_results']} instruments for '{searchscrip}'")
                return search_data
            else:
                error_msg = response.get('message', f'Error response: {response}')
                print(f"❌ Error searching instruments: {error_msg}")
                return {"status": "error", "message": error_msg}
                
        except Exception as e:
            error_msg = f"Exception in search_instruments: {str(e)}"
            print(f"❌ {error_msg}")
            return {"status": "error", "message": error_msg}

    @ConnectionManager.api_request
    def get_allholding_data(self) -> Dict[str, Any]:
        """
        Get all holding data with current market prices.
        Returns: Dictionary containing all holdings with market data or error info.
        """
        smart_connect = ConnectionManager.get_smartapi_client()
        if not smart_connect:
            return {"status": "error", "message": "No SmartAPI connection available"}
        
        try:
            print("📈 Fetching all holdings with market data...")
            response = smart_connect.allholding()
            
            if response.get('status') is True or response.get('status') == 'success':
                allholding_data = {
                    "status": "success",
                    "timestamp": datetime.now(UTC).isoformat(),
                    "holdings_with_market_data": response.get('data', {}),
                }
                
                # Store in database
                self._store_allholding_data(allholding_data)
                
                # Publish to message queue
                self._publish_market_update("allholding", allholding_data)
                
                print("✅ Successfully fetched all holdings with market data")
                return allholding_data
            else:
                error_msg = response.get('message', f'Error response: {response}')
                print(f"❌ Error fetching all holdings: {error_msg}")
                return {"status": "error", "message": error_msg}
                
        except Exception as e:
            error_msg = f"Exception in get_allholding_data: {str(e)}"
            print(f"❌ {error_msg}")
            return {"status": "error", "message": error_msg}

    def get_market_summary(self, symbols: List[Dict[str, str]] = None) -> Dict[str, Any]:
        """
        Generate comprehensive market data summary for specified symbols.
        Args:
            symbols: List of symbol dictionaries with exchange, tradingsymbol, symboltoken
        Returns: Dictionary containing market summary or error info.
        """
        try:
            print("📊 Generating market data summary...")
            
            # Default symbols if none provided (major indices)
            if not symbols:
                symbols = [
                    {"exchange": "NSE", "tradingsymbol": "NIFTY 50", "symboltoken": "26000"},
                    {"exchange": "NSE", "tradingsymbol": "NIFTY BANK", "symboltoken": "26009"}
                ]
            
            summary_data = {
                "status": "success",
                "timestamp": datetime.now(UTC).isoformat(),
                "symbols_count": len(symbols),
                "market_data": []
            }
            
            # Fetch data for each symbol
            for symbol in symbols:
                try:
                    # Get LTP
                    ltp_data = self.get_ltp(
                        symbol['exchange'], 
                        symbol['tradingsymbol'], 
                        symbol['symboltoken']
                    )
                    
                    # Get detailed quote
                    quote_data = self.get_quote(
                        symbol['exchange'], 
                        symbol['tradingsymbol'], 
                        symbol['symboltoken']
                    )
                    
                    symbol_summary = {
                        "symbol": symbol,
                        "ltp": ltp_data,
                        "quote": quote_data
                    }
                    
                    summary_data["market_data"].append(symbol_summary)
                    
                except Exception as e:
                    print(f"❌ Error fetching data for {symbol['tradingsymbol']}: {e}")
                    continue
            
            # Store summary in database
            self._store_market_summary(summary_data)
            
            print(f"✅ Market summary generated for {len(summary_data['market_data'])} symbols")
            return summary_data
            
        except Exception as e:
            error_msg = f"Exception in get_market_summary: {str(e)}"
            print(f"❌ {error_msg}")
            return {"status": "error", "message": error_msg}

    def _store_ltp_data(self, ltp_data: Dict[str, Any]):
        """Store LTP data in MongoDB."""
        if self.db is not None:
            try:
                collection = self.db.market_ltp_data
                collection.insert_one(ltp_data)
                print("✅ LTP data stored in database")
            except Exception as e:
                print(f"❌ Error storing LTP data: {e}")

    def _store_quote_data(self, quote_data: Dict[str, Any]):
        """Store quote data in MongoDB."""
        if self.db is not None:
            try:
                collection = self.db.market_quote_data
                collection.insert_one(quote_data)
                print("✅ Quote data stored in database")
            except Exception as e:
                print(f"❌ Error storing quote data: {e}")

    def _store_search_results(self, search_data: Dict[str, Any]):
        """Store search results in MongoDB."""
        if self.db is not None:
            try:
                collection = self.db.instrument_search_results
                collection.insert_one(search_data)
                print("✅ Search results stored in database")
            except Exception as e:
                print(f"❌ Error storing search results: {e}")

    def _store_allholding_data(self, allholding_data: Dict[str, Any]):
        """Store all holdings data in MongoDB."""
        if self.db is not None:
            try:
                collection = self.db.market_allholding_data
                collection.insert_one(allholding_data)
                print("✅ All holdings data stored in database")
            except Exception as e:
                print(f"❌ Error storing all holdings data: {e}")

    def _store_candle_data(self, candle_data: Dict[str, Any]):
        """Store candle data in MongoDB."""
        if self.db is not None:
            try:
                collection = self.db.market_candle_data
                collection.insert_one(candle_data)
                print("✅ Candle data stored in database")
            except Exception as e:
                print(f"❌ Error storing candle data: {e}")

    def _store_market_summary(self, summary_data: Dict[str, Any]):
        """Store market summary in MongoDB."""
        if self.db is not None:
            try:
                collection = self.db.market_summary
                collection.insert_one(summary_data)
                print("✅ Market summary stored in database")
            except Exception as e:
                print(f"❌ Error storing market summary: {e}")

    def _publish_market_update(self, update_type: str, data: Dict[str, Any]):
        """Publish market data updates to RabbitMQ."""
        if self.rabbit_channel:
            try:
                routing_key = f"market.{update_type}"
                message = {
                    "type": update_type,
                    "timestamp": datetime.now(UTC).isoformat(),
                    "data": data
                }
                
                self.rabbit_channel.basic_publish(
                    exchange='market_data_updates_exchange',
                    routing_key=routing_key,
                    body=json.dumps(message),
                    properties=pika.BasicProperties(delivery_mode=2)  # Persistent message
                )
                print(f"✅ Market update published: {routing_key}")
            except Exception as e:
                print(f"❌ Error publishing market update: {e}")

    def start_market_monitoring(self, symbols: List[Dict[str, str]] = None, interval_seconds: int = 60):
        """
        Start continuous market data monitoring service.
        Args:
            symbols: List of symbols to monitor
            interval_seconds: How often to refresh market data (default: 1 minute)
        """
        import time
        import threading
        
        def monitor_loop():
            while True:
                try:
                    print(f"🔄 Starting market data refresh cycle...")
                    self.get_market_summary(symbols)
                    print(f"⏰ Next market data refresh in {interval_seconds} seconds")
                    time.sleep(interval_seconds)
                except KeyboardInterrupt:
                    print("❕ Market monitoring stopped by user")
                    break
                except Exception as e:
                    print(f"❌ Error in market monitoring: {e}")
                    time.sleep(30)  # Wait 30 seconds before retrying
        
        monitor_thread = threading.Thread(target=monitor_loop, daemon=True)
        monitor_thread.start()
        print(f"✅ Market monitoring started (refresh every {interval_seconds}s)")
        return monitor_thread

    def close(self):
        """Close RabbitMQ connections gracefully."""
        if self.rabbit_connection and self.rabbit_connection.is_open:
            self.rabbit_connection.close()
            print("❕ Market Data Service RabbitMQ connection closed.")


if __name__ == '__main__':
    # Test the Market Data Service
    print("🚀 Starting Market Data Service Test...")
    
    market_service = MarketDataService()
    
    try:
        # Test search functionality first
        print("\n1. Testing Instrument Search...")
        search_results = market_service.search_instruments("NSE", "RELIANCE")
        print(f"Search Results Status: {search_results.get('status')}")
        
        # Use search results for further testing if available
        test_symbol = None
        if search_results.get('status') == 'success' and search_results.get('total_results', 0) > 0:
            # Find RELIANCE-EQ (main equity symbol) from search results
            reliance_eq = None
            for result in search_results['results']:
                if result.get('tradingsymbol') == 'RELIANCE-EQ':
                    reliance_eq = result
                    break
            
            if reliance_eq:
                test_symbol = {
                    "exchange": reliance_eq.get('exchange', 'NSE'),
                    "tradingsymbol": reliance_eq.get('tradingsymbol', 'RELIANCE-EQ'),
                    "symboltoken": reliance_eq.get('symboltoken', '2885')
                }
            else:
                # Use first result if RELIANCE-EQ not found
                first_result = search_results['results'][0]
                test_symbol = {
                    "exchange": first_result.get('exchange', 'NSE'),
                    "tradingsymbol": first_result.get('tradingsymbol', 'RELIANCE-EQ'),
                    "symboltoken": first_result.get('symboltoken', '2885')
                }
        else:
            # Fallback to a known symbol
            test_symbol = {
                "exchange": "NSE",
                "tradingsymbol": "RELIANCE",
                "symboltoken": "2885"
            }
        
        print(f"\n2. Testing LTP for {test_symbol['tradingsymbol']}...")
        ltp_data = market_service.get_ltp(
            test_symbol['exchange'],
            test_symbol['tradingsymbol'],
            test_symbol['symboltoken']
        )
        print(f"LTP Status: {ltp_data.get('status')}")
        
        print(f"\n3. Testing Quote for {test_symbol['tradingsymbol']}...")
        quote_data = market_service.get_quote(
            test_symbol['exchange'],
            test_symbol['tradingsymbol'],
            test_symbol['symboltoken']
        )
        print(f"Quote Status: {quote_data.get('status')}")
        
        print("\n4. Testing All Holdings...")
        allholding_data = market_service.get_allholding_data()
        print(f"All Holdings Status: {allholding_data.get('status')}")
        
        print("\n5. Testing Market Summary...")
        market_summary = market_service.get_market_summary([test_symbol])
        print(f"Market Summary Status: {market_summary.get('status')}")
        
        print("\n✅ Market Data Service testing completed!")
        
    except KeyboardInterrupt:
        print("\n❕ Testing interrupted by user")
    except Exception as e:
        print(f"\n❌ Error during testing: {e}")
    finally:
        market_service.close()
