"""
Simple Market Data Streaming Test
=================================

Test the real-time market data streaming with unified Angel One authentication.
This version demonstrates the core functionality without Kafka dependencies.
"""

import asyncio
import time
import json
from datetime import datetime, UTC
from typing import Dict, Any, List, Optional, Set
import threading

# Add project root to path for imports
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

import logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("market_data_test")

from core.connections import ConnectionManager


class SimpleMarketDataStreamer:
    """
    Simple market data streamer for testing real-time data flow
    with unified Angel One authentication.
    """
    
    def __init__(self):
        """Initialize the simple market data streamer."""
        self.subscribed_symbols: Set[str] = set()
        self.streaming_interval = 2.0  # seconds
        self.is_streaming = False
        self.stream_thread: Optional[threading.Thread] = None
        
        # Performance tracking
        self.ticks_streamed = 0
        self.streaming_errors = 0
        self.start_time = datetime.now()
        self._lock = threading.Lock()
        
        logger.info("SimpleMarketDataStreamer initialized")
    
    def subscribe_symbol(self, symbol: str, exchange: str = "NSE") -> bool:
        """Subscribe to real-time data for a symbol."""
        try:
            symbol_key = f"{exchange}:{symbol}"
            
            with self._lock:
                if symbol_key not in self.subscribed_symbols:
                    self.subscribed_symbols.add(symbol_key)
                    logger.info(f"✅ Subscribed to {symbol_key}")
                    return True
                else:
                    logger.info(f"ℹ️ Already subscribed to {symbol_key}")
                    return True
                    
        except Exception as e:
            logger.error(f"❌ Failed to subscribe to {symbol}: {e}")
            return False
    
    async def fetch_and_stream_tick(self, symbol: str, exchange: str = "NSE") -> bool:
        """
        Fetch real-time tick data using unified Angel One session.
        
        This demonstrates the key feature: NO RE-AUTHENTICATION needed!
        The auto-login session is already available via ConnectionManager.
        """
        try:
            # Get the unified SmartAPI client (already authenticated via auto-login)
            angel_client = ConnectionManager.get_smartapi_client()
            
            if not angel_client:
                logger.error(f"❌ No authenticated Angel One client available for {symbol}")
                return False
            
            logger.info(f"🔗 Using unified authenticated session for {symbol}")
            
            # Get token for the symbol (sample mapping)
            token = self._get_token_for_symbol(symbol, exchange)
            
            if token:
                try:
                    # Fetch LTP data directly from Angel One using the authenticated client
                    ltp_data = angel_client.ltpData(exchange, symbol, token)
                    
                    if ltp_data and ltp_data.get('status'):
                        data = ltp_data.get('data', {})
                        
                        # Create normalized tick data
                        tick_data = {
                            "symbol": symbol,
                            "exchange": exchange,
                            "token": token,
                            "ltp": float(data.get("ltp", 0)),
                            "open": float(data.get("open", 0)),
                            "high": float(data.get("high", 0)),
                            "low": float(data.get("low", 0)),
                            "close": float(data.get("close", 0)),
                            "volume": int(data.get("volume", 0)),
                            "timestamp": datetime.now(UTC).isoformat(),
                            "source": "angel_one_unified_session"
                        }
                        
                        # Calculate change
                        tick_data["change"] = tick_data["ltp"] - tick_data["close"]
                        tick_data["change_percent"] = (tick_data["change"] / tick_data["close"] * 100) if tick_data["close"] else 0
                        
                        # Log the successful data fetch
                        logger.info(f"📊 {symbol}: LTP={tick_data['ltp']:.2f}, Change={tick_data['change']:+.2f} ({tick_data['change_percent']:+.2f}%)")
                        
                        # In a real implementation, this would go to Kafka
                        logger.info(f"🚀 Would stream to Kafka: {json.dumps(tick_data, indent=2)}")
                        
                        with self._lock:
                            self.ticks_streamed += 1
                        
                        return True
                    else:
                        logger.warning(f"⚠️ No LTP data received for {symbol}")
                        return False
                        
                except Exception as api_error:
                    logger.error(f"❌ Angel One API error for {symbol}: {api_error}")
                    with self._lock:
                        self.streaming_errors += 1
                    return False
            else:
                logger.error(f"❌ No token found for {symbol}:{exchange}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Failed to fetch and stream tick for {symbol}: {e}")
            with self._lock:
                self.streaming_errors += 1
            return False
    
    def _get_token_for_symbol(self, symbol: str, exchange: str) -> Optional[str]:
        """Get the token for a symbol."""
        # Sample token mapping - in production, this would be a database lookup
        token_map = {
            "NSE:NIFTY": "99926000",
            "NSE:BANKNIFTY": "99926009", 
            "NSE:RELIANCE": "2885",
            "NSE:TCS": "11536",
            "NSE:INFY": "1594",
            "NSE:HDFCBANK": "1333",
            "NSE:ICICIBANK": "4963",
            "NSE:SBIN": "3045"
        }
        
        symbol_key = f"{exchange}:{symbol}"
        return token_map.get(symbol_key)
    
    def start_streaming(self) -> bool:
        """Start real-time streaming for all subscribed symbols."""
        if self.is_streaming:
            logger.warning("⚠️ Streaming is already active")
            return True
        
        if not self.subscribed_symbols:
            logger.warning("⚠️ No symbols subscribed for streaming")
            return False
        
        try:
            self.is_streaming = True
            logger.info(f"🚀 Starting real-time streaming for {len(self.subscribed_symbols)} symbols")
            
            # Start streaming in a separate thread
            self.stream_thread = threading.Thread(target=self._streaming_loop, daemon=True)
            self.stream_thread.start()
            
            logger.info("✅ Real-time streaming started successfully")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to start streaming: {e}")
            self.is_streaming = False
            return False
    
    def stop_streaming(self) -> bool:
        """Stop real-time streaming."""
        if not self.is_streaming:
            logger.info("ℹ️ Streaming is not active")
            return True
        
        try:
            logger.info("🛑 Stopping real-time streaming...")
            self.is_streaming = False
            
            # Wait for streaming thread to finish
            if self.stream_thread and self.stream_thread.is_alive():
                self.stream_thread.join(timeout=5.0)
                if self.stream_thread.is_alive():
                    logger.warning("⚠️ Streaming thread did not stop gracefully")
            
            logger.info("✅ Real-time streaming stopped successfully")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to stop streaming: {e}")
            return False
    
    def _streaming_loop(self):
        """Main streaming loop that runs in a separate thread."""
        logger.info("📡 Starting streaming loop...")
        
        while self.is_streaming:
            try:
                # Get current subscribed symbols (thread-safe)
                with self._lock:
                    symbols_to_stream = list(self.subscribed_symbols)
                
                if not symbols_to_stream:
                    time.sleep(self.streaming_interval)
                    continue
                
                # Stream data for each subscribed symbol
                for symbol_key in symbols_to_stream:
                    if not self.is_streaming:  # Check if we should stop
                        break
                    
                    try:
                        # Parse exchange and symbol
                        exchange, symbol = symbol_key.split(":", 1)
                        
                        # Fetch and stream (run in async context)
                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)
                        success = loop.run_until_complete(
                            self.fetch_and_stream_tick(symbol, exchange)
                        )
                        loop.close()
                        
                        if not success:
                            logger.debug(f"⚠️ Failed to stream {symbol_key}")
                            
                    except Exception as symbol_error:
                        logger.error(f"❌ Error streaming {symbol_key}: {symbol_error}")
                        with self._lock:
                            self.streaming_errors += 1
                
                # Wait before next streaming cycle
                time.sleep(self.streaming_interval)
                
            except Exception as e:
                logger.error(f"❌ Error in streaming loop: {e}")
                time.sleep(self.streaming_interval)
        
        logger.info("📡 Streaming loop ended")
    
    def get_streaming_stats(self) -> Dict[str, Any]:
        """Get streaming statistics."""
        with self._lock:
            runtime = (datetime.now() - self.start_time).total_seconds()
            
            return {
                'is_streaming': self.is_streaming,
                'subscribed_symbols': len(self.subscribed_symbols),
                'symbols': list(self.subscribed_symbols),
                'ticks_streamed': self.ticks_streamed,
                'streaming_errors': self.streaming_errors,
                'runtime_seconds': runtime,
                'ticks_per_second': self.ticks_streamed / runtime if runtime > 0 else 0,
                'error_rate': self.streaming_errors / (self.ticks_streamed + self.streaming_errors) if (self.ticks_streamed + self.streaming_errors) > 0 else 0,
                'streaming_interval': self.streaming_interval,
                'start_time': self.start_time.isoformat()
            }


async def test_unified_market_data_streaming():
    """
    Test the unified market data streaming system.
    
    This demonstrates:
    1. ✅ Unified Angel One authentication (no re-auth needed)
    2. ✅ Real-time data fetching
    3. ✅ Data normalization
    4. ✅ Streaming simulation (would go to Kafka in production)
    """
    logger.info("🎯 Testing Unified Market Data Streaming System")
    logger.info("=" * 60)
    
    # Initialize the streamer
    streamer = SimpleMarketDataStreamer()
    
    # Subscribe to some symbols
    symbols_to_test = ["NIFTY", "RELIANCE", "TCS"]
    logger.info(f"📋 Subscribing to symbols: {symbols_to_test}")
    
    for symbol in symbols_to_test:
        success = streamer.subscribe_symbol(symbol, "NSE")
        if success:
            logger.info(f"✅ Subscribed to {symbol}")
        else:
            logger.error(f"❌ Failed to subscribe to {symbol}")
    
    # Start streaming
    logger.info("\n🚀 Starting real-time streaming...")
    if streamer.start_streaming():
        logger.info("✅ Streaming started successfully!")
        
        # Let it run for 30 seconds
        logger.info("⏱️ Running streaming test for 30 seconds...")
        await asyncio.sleep(30)
        
        # Get stats
        stats = streamer.get_streaming_stats()
        logger.info("\n📊 Streaming Statistics:")
        logger.info("=" * 40)
        for key, value in stats.items():
            logger.info(f"   {key}: {value}")
        
        # Stop streaming
        logger.info("\n🛑 Stopping streaming...")
        streamer.stop_streaming()
        
        # Final summary
        logger.info("\n🎉 Test Results Summary:")
        logger.info("=" * 40)
        logger.info(f"✅ Ticks Streamed: {stats['ticks_streamed']}")
        logger.info(f"⚠️ Errors: {stats['streaming_errors']}")
        logger.info(f"📈 Success Rate: {((stats['ticks_streamed'] / (stats['ticks_streamed'] + stats['streaming_errors'])) * 100):.1f}%" if (stats['ticks_streamed'] + stats['streaming_errors']) > 0 else "N/A")
        logger.info(f"⚡ Avg Ticks/sec: {stats['ticks_per_second']:.2f}")
        
        if stats['ticks_streamed'] > 0:
            logger.info("🎯 SUCCESS: Real-time market data streaming is working with unified authentication!")
        else:
            logger.warning("⚠️ WARNING: No ticks were streamed successfully")
    else:
        logger.error("❌ Failed to start streaming")


if __name__ == "__main__":
    print("\n" + "="*80)
    print("HFT REAL-TIME MARKET DATA STREAMING TEST")
    print("   Unified Angel One Authentication + Real-time Data Flow")
    print("="*80)
    
    try:
        asyncio.run(test_unified_market_data_streaming())
    except KeyboardInterrupt:
        print("\n⏹️ Test interrupted by user")
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        print("\n" + "="*80)
        print("🏁 Test completed")
        print("="*80)
