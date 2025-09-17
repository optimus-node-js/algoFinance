"""
AI Trading System - Main Entry Point
===================================

Starts the complete AI trading system with:
- All 9 microservices running independently
- Live console monitoring with real-time tables
- Bulk processing of thousands of stocks
- Real-time LTP monitoring and trade execution
- Comprehensive logging and reporting

Usage:
    python server/src/start_ai_trading_system.py

Author: AI Trading System
Version: 1.0.0
"""

import asyncio
import sys
import os
import signal
from datetime import datetime

# Add project root to path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.append(PROJECT_ROOT)

# Import dependencies with proper error handling
DEPENDENCIES_AVAILABLE = True
service_launcher_module = None
ai_master_module = None
live_monitor_module = None
logger_module = None

try:
    # Import each module separately to identify specific issues
    import sys
    sys.path.append('server/src')
    
    from orchestration.service_launcher import get_service_launcher
    service_launcher_module = get_service_launcher
    print("✅ Service launcher imported")
except ImportError as e:
    print(f"⚠️ Service launcher import error: {e}")
    DEPENDENCIES_AVAILABLE = False

try:
    from ai.master.ai_master_orchestrator import AIMasterOrchestrator, CURRENT_TRADING_MODE
    ai_master_module = AIMasterOrchestrator
    print("✅ AI Master imported")
except ImportError as e:
    print(f"⚠️ AI Master import error: {e}")
    DEPENDENCIES_AVAILABLE = False

try:
    from monitoring.live_console_monitor import get_live_monitor
    live_monitor_module = get_live_monitor
    print("✅ Live monitor imported")
except ImportError as e:
    print(f"⚠️ Live monitor import error: {e}")

try:
    # Import logger carefully
    import logging
    logger_module = logging.getLogger("AI_TRADING_SYSTEM")
    print("✅ Logger imported")
except ImportError as e:
    print(f"⚠️ Logger import error: {e}")

class AITradingSystemManager:
    """
    Main manager for the complete AI trading system.
    
    Coordinates:
    - All 9 microservices
    - AI Master orchestration
    - Live console monitoring
    - Real-time data processing
    """
    
    def __init__(self):
        """Initialize the trading system manager."""
        self.logger = logger_module
        self.service_launcher = service_launcher_module() if service_launcher_module else None
        self.live_monitor = live_monitor_module() if live_monitor_module else None
        self.ai_master = None
        self.is_running = False
        
        # Setup signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals."""
        print(f"\n🛑 Received shutdown signal ({signum})")
        self.stop_system()
    
    async def start_complete_system(self):
        """Start the complete AI trading system."""
        self.is_running = True
        
        print("🚀 AI TRADING SYSTEM - COMPLETE STARTUP")
        print("=" * 60)
        print(f"🎯 Trading Mode: PAPER TRADING")
        print(f"⏰ Session Start: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 60)
        
        if self.logger:
            self.logger.info("🚀 Starting Complete AI Trading System")
        
        try:
            # Step 1: Start all microservices
            print("📡 STEP 1: Starting All Microservices...")
            if self.service_launcher:
                await self.service_launcher.start_all_services()
                print("✅ All microservices started successfully")
            else:
                print("⚠️ Service launcher not available")
            
            # Step 2: Initialize AI Master Orchestrator
            print("🧠 STEP 2: Initializing AI Master Orchestrator...")
            if ai_master_module:
                self.ai_master = ai_master_module()
                print("✅ AI Master initialized")
            else:
                print("⚠️ AI Master not available")
            
            # Step 3: Start live console monitoring
            print("📊 STEP 3: Starting Live Console Monitor...")
            if self.live_monitor:
                # Start live monitor in background
                monitor_task = asyncio.create_task(self.live_monitor.start_live_monitoring())
                print("✅ Live console monitor started")
            else:
                print("⚠️ Live monitor not available")
            
            # Step 4: Start AI Master operations
            print("⚡ STEP 4: Starting AI Master Operations...")
            print("🔥 BULK PROCESSING MODE: Processing thousands of stocks simultaneously")
            print("📈 REAL-TIME MONITORING: Live LTP updates and trade tracking")
            print("🎯 MICROSERVICES: All 9 services running independently")
            print()
            print("⚡ Press Ctrl+C to stop the system")
            print("=" * 60)
            
            # Start the AI Master engine
            await self.ai_master.start_master_engine()
            
        except KeyboardInterrupt:
            print("\n🛑 System shutdown requested...")
        except Exception as e:
            print(f"❌ System error: {e}")
            if self.logger:
                self.logger.error("SYSTEM", f"System error: {e}")
        finally:
            await self.stop_system()
    
    async def stop_system(self):
        """Stop the complete system gracefully."""
        if not self.is_running:
            return
            
        self.is_running = False
        
        print("🛑 Shutting down AI Trading System...")
        
        if self.logger:
            self.logger.info("SYSTEM", "🛑 Shutting down complete system")
        
        try:
            # Stop AI Master
            if self.ai_master:
                await self.ai_master.shutdown()
                print("✅ AI Master stopped")
            
            # Stop live monitor
            if self.live_monitor:
                self.live_monitor.stop_monitoring()
                print("✅ Live monitor stopped")
            
            # Stop all microservices
            if self.service_launcher:
                self.service_launcher.stop_all_services()
                print("✅ All microservices stopped")
            
            print("✅ AI Trading System shutdown complete")
            
        except Exception as e:
            print(f"❌ Error during shutdown: {e}")
            if self.logger:
                self.logger.error("SYSTEM", f"Shutdown error: {e}")

def show_system_info():
    """Show system information and requirements."""
    print("🚀 AI TRADING SYSTEM - REAL-TIME BULK PROCESSING")
    print("=" * 60)
    print("📊 FEATURES:")
    print("   • Bulk processing of thousands of stocks (no cycles)")
    print("   • Real-time live console with animated tables")
    print("   • 9 independent microservices with RabbitMQ communication")
    print("   • Live LTP updates from Angel One API")
    print("   • Real-time P&L monitoring and trade tracking")
    print("   • Parallel batch processing with threading")
    print("   • Comprehensive backtesting validation")
    print()
    print("🔧 REQUIREMENTS:")
    print("   • RabbitMQ server running")
    print("   • MongoDB connection")
    print("   • Angel One API credentials in .env")
    print("   • Rich and Textual libraries installed")
    print()
    print("⚡ MICROSERVICES:")
    print("   1. Message Broker Service")
    print("   2. Stock Discovery Service")
    print("   3. Trade Execution Service")
    print("   4. Portfolio Management Service")
    print("   5. Order Book Service")
    print("   6. Market Data Service")
    print("   7. Risk Management Service")
    print("   8. Strategy Service")
    print("   9. Data Ingestion Service")
    print("=" * 60)

async def main():
    """Main entry point for the AI trading system."""
    show_system_info()
    
    if not DEPENDENCIES_AVAILABLE:
        print("❌ Dependencies not available. Please check imports.")
        return
    
    # Create and start the trading system
    system_manager = AITradingSystemManager()
    
    try:
        await system_manager.start_complete_system()
    except KeyboardInterrupt:
        print("\n⏹️ System stopped by user")
    except Exception as e:
        print(f"❌ System error: {e}")

if __name__ == "__main__":
    print("🎯 Starting AI Trading System...")
    asyncio.run(main())
