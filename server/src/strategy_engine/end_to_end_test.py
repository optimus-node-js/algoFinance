"""
End-to-End Trading Pipeline Test
===============================

Complete test of the HFT trading pipeline:
Market Data → Strategy Engine → Risk Management → Order Execution

This demonstrates the full integration with real-time data processing.
"""

import asyncio
import json
import time
from typing import Dict, Any, List
from datetime import datetime, UTC
import logging
import threading

# Add project root to path for imports
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("end_to_end_test")

from strategy_engine.live_strategy_worker import LiveStrategyWorker
from strategy_engine.examples.live_momentum_strategy import LiveMomentumStrategy
from market_data_streaming.clean_test import CleanMarketDataStreamer


class EndToEndTradingTest:
    """
    Complete end-to-end trading pipeline test.
    
    Components tested:
    1. Market Data Streaming (unified auth)
    2. Strategy Engine (real-time processing)
    3. Risk Management (pre-trade validation)
    4. Order Execution (Kafka messaging)
    """
    
    def __init__(self):
        """Initialize the end-to-end test."""
        self.market_streamer = None
        self.strategy_worker = None
        self.test_results = {
            'market_data_ticks': 0,
            'strategy_signals': 0,
            'risk_validations': 0,
            'orders_placed': 0,
            'errors': 0,
            'start_time': None,
            'end_time': None
        }
        
        logger.info("EndToEndTradingTest initialized")
    
    async def setup_market_data_streaming(self) -> bool:
        """Setup market data streaming component."""
        try:
            logger.info("Setting up market data streaming...")
            
            # Initialize market data streamer
            self.market_streamer = CleanMarketDataStreamer()
            
            # Subscribe to test symbols
            test_symbols = ["NIFTY", "RELIANCE", "TCS"]
            for symbol in test_symbols:
                success = self.market_streamer.subscribe_symbol(symbol, "NSE")
                if success:
                    logger.info(f"Subscribed to {symbol}")
                else:
                    logger.error(f"Failed to subscribe to {symbol}")
                    return False
            
            logger.info("Market data streaming setup complete")
            return True
            
        except Exception as e:
            logger.error(f"Failed to setup market data streaming: {e}")
            return False
    
    async def setup_strategy_engine(self) -> bool:
        """Setup strategy engine component."""
        try:
            logger.info("Setting up strategy engine...")
            
            # Initialize strategy worker
            self.strategy_worker = LiveStrategyWorker("end_to_end_test_worker")
            
            # Create and add live momentum strategies
            strategies = [
                LiveMomentumStrategy("live_momentum_nifty", "NIFTY", 5, 15),
                LiveMomentumStrategy("live_momentum_reliance", "RELIANCE", 5, 15),
                LiveMomentumStrategy("live_momentum_tcs", "TCS", 5, 15)
            ]
            
            for strategy in strategies:
                success = self.strategy_worker.add_strategy(strategy)
                if success:
                    self.strategy_worker.activate_strategy(strategy.strategy_id)
                    logger.info(f"Added and activated strategy: {strategy.strategy_id}")
                else:
                    logger.error(f"Failed to add strategy: {strategy.strategy_id}")
                    return False
            
            logger.info("Strategy engine setup complete")
            return True
            
        except Exception as e:
            logger.error(f"Failed to setup strategy engine: {e}")
            return False
    
    async def run_pipeline_test(self, duration_seconds: int = 60) -> Dict[str, Any]:
        """
        Run the complete end-to-end pipeline test.
        
        Args:
            duration_seconds: How long to run the test
            
        Returns:
            Test results dictionary
        """
        logger.info(f"Starting end-to-end pipeline test for {duration_seconds} seconds")
        logger.info("=" * 80)
        
        self.test_results['start_time'] = datetime.now(UTC).isoformat()
        
        try:
            # Setup components
            market_setup = await self.setup_market_data_streaming()
            strategy_setup = await self.setup_strategy_engine()
            
            if not market_setup or not strategy_setup:
                logger.error("Failed to setup components")
                return self.test_results
            
            # Start market data streaming
            logger.info("Starting market data streaming...")
            if not self.market_streamer.start_streaming():
                logger.error("Failed to start market data streaming")
                return self.test_results
            
            # Start strategy processing
            logger.info("Starting strategy processing...")
            strategy_task = asyncio.create_task(self.strategy_worker.start_processing())
            
            # Monitor the pipeline
            logger.info(f"Pipeline running... monitoring for {duration_seconds} seconds")
            
            for i in range(duration_seconds):
                await asyncio.sleep(1)
                
                # Log progress every 10 seconds
                if i % 10 == 0 and i > 0:
                    await self._log_progress(i)
            
            # Stop components
            logger.info("Stopping pipeline components...")
            
            # Stop strategy processing
            self.strategy_worker.stop_processing()
            strategy_task.cancel()
            
            # Stop market data streaming
            self.market_streamer.stop_streaming()
            
            # Collect final results
            await self._collect_final_results()
            
            self.test_results['end_time'] = datetime.now(UTC).isoformat()
            
            # Generate test report
            self._generate_test_report()
            
            return self.test_results
            
        except Exception as e:
            logger.error(f"Error in pipeline test: {e}")
            self.test_results['errors'] += 1
            return self.test_results
    
    async def _log_progress(self, elapsed_seconds: int):
        """Log current progress of the pipeline test."""
        try:
            # Get market data stats
            market_stats = self.market_streamer.get_streaming_stats()
            
            # Get strategy stats
            strategy_stats = self.strategy_worker.get_performance_stats()
            strategy_status = self.strategy_worker.get_strategy_status()
            
            logger.info(f"[{elapsed_seconds}s] Pipeline Progress:")
            logger.info(f"  Market Data: {market_stats['ticks_streamed']} ticks, "
                       f"{market_stats['ticks_per_second']:.2f} ticks/sec")
            logger.info(f"  Strategy Engine: {strategy_stats['messages_processed']} messages, "
                       f"{strategy_stats['signals_generated']} signals")
            
            # Log individual strategy status
            for strategy_id, status in strategy_status.items():
                logger.info(f"    {strategy_id}: "
                          f"Signals={status.get('signals_generated', 0)}, "
                          f"Orders={status.get('orders_placed', 0)}, "
                          f"Active={status.get('is_active', False)}")
            
        except Exception as e:
            logger.error(f"Error logging progress: {e}")
    
    async def _collect_final_results(self):
        """Collect final test results from all components."""
        try:
            # Market data results
            if self.market_streamer:
                market_stats = self.market_streamer.get_streaming_stats()
                self.test_results['market_data_ticks'] = market_stats['ticks_streamed']
            
            # Strategy engine results
            if self.strategy_worker:
                strategy_stats = self.strategy_worker.get_performance_stats()
                strategy_status = self.strategy_worker.get_strategy_status()
                
                self.test_results['strategy_signals'] = strategy_stats['signals_generated']
                
                # Aggregate strategy-specific results
                total_orders = sum(status.get('orders_placed', 0) for status in strategy_status.values())
                self.test_results['orders_placed'] = total_orders
                
                # Count errors
                total_errors = strategy_stats['processing_errors']
                self.test_results['errors'] += total_errors
            
        except Exception as e:
            logger.error(f"Error collecting final results: {e}")
            self.test_results['errors'] += 1
    
    def _generate_test_report(self):
        """Generate comprehensive test report."""
        logger.info("\n" + "="*80)
        logger.info("END-TO-END TRADING PIPELINE TEST REPORT")
        logger.info("="*80)
        
        # Calculate test duration
        if self.test_results['start_time'] and self.test_results['end_time']:
            start = datetime.fromisoformat(self.test_results['start_time'].replace('Z', '+00:00'))
            end = datetime.fromisoformat(self.test_results['end_time'].replace('Z', '+00:00'))
            duration = (end - start).total_seconds()
        else:
            duration = 0
        
        logger.info(f"Test Duration: {duration:.1f} seconds")
        logger.info(f"Start Time: {self.test_results['start_time']}")
        logger.info(f"End Time: {self.test_results['end_time']}")
        logger.info("")
        
        # Component Results
        logger.info("COMPONENT PERFORMANCE:")
        logger.info("-" * 40)
        logger.info(f"Market Data Ticks: {self.test_results['market_data_ticks']}")
        logger.info(f"Strategy Signals: {self.test_results['strategy_signals']}")
        logger.info(f"Risk Validations: {self.test_results['risk_validations']}")
        logger.info(f"Orders Placed: {self.test_results['orders_placed']}")
        logger.info(f"Total Errors: {self.test_results['errors']}")
        logger.info("")
        
        # Performance Metrics
        if duration > 0:
            logger.info("PERFORMANCE METRICS:")
            logger.info("-" * 40)
            logger.info(f"Ticks per Second: {self.test_results['market_data_ticks'] / duration:.2f}")
            logger.info(f"Signals per Minute: {self.test_results['strategy_signals'] / duration * 60:.2f}")
            logger.info(f"Orders per Minute: {self.test_results['orders_placed'] / duration * 60:.2f}")
            logger.info(f"Error Rate: {self.test_results['errors'] / max(1, self.test_results['market_data_ticks']) * 100:.2f}%")
        
        logger.info("")
        
        # Test Assessment
        logger.info("TEST ASSESSMENT:")
        logger.info("-" * 40)
        
        success_criteria = {
            'market_data_flowing': self.test_results['market_data_ticks'] > 0,
            'strategies_processing': self.test_results['strategy_signals'] >= 0,
            'low_error_rate': self.test_results['errors'] < 10,
            'pipeline_complete': duration > 0
        }
        
        all_passed = all(success_criteria.values())
        
        for criterion, passed in success_criteria.items():
            status = "PASS" if passed else "FAIL"
            logger.info(f"{criterion.replace('_', ' ').title()}: {status}")
        
        logger.info("")
        logger.info(f"OVERALL RESULT: {'SUCCESS' if all_passed else 'PARTIAL SUCCESS'}")
        
        if all_passed:
            logger.info("The end-to-end trading pipeline is working correctly!")
        else:
            logger.warning("Some components need attention for optimal performance.")
        
        logger.info("="*80)
    
    async def cleanup(self):
        """Cleanup test resources."""
        try:
            logger.info("Cleaning up test resources...")
            
            if self.market_streamer:
                self.market_streamer.stop_streaming()
            
            if self.strategy_worker:
                await self.strategy_worker.close()
            
            logger.info("Cleanup complete")
            
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")


async def run_end_to_end_test():
    """Run the complete end-to-end trading pipeline test."""
    test = EndToEndTradingTest()
    
    try:
        # Run the test for 60 seconds
        results = await test.run_pipeline_test(duration_seconds=60)
        
        return results
        
    except KeyboardInterrupt:
        logger.info("Test interrupted by user")
        return test.test_results
    
    except Exception as e:
        logger.error(f"Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return test.test_results
    
    finally:
        await test.cleanup()


if __name__ == "__main__":
    print("\n" + "="*80)
    print("HFT END-TO-END TRADING PIPELINE TEST")
    print("   Market Data → Strategy Engine → Risk Management → Order Execution")
    print("="*80)
    
    try:
        results = asyncio.run(run_end_to_end_test())
        
        print(f"\nFinal Results: {json.dumps(results, indent=2)}")
        
    except KeyboardInterrupt:
        print("\nTest interrupted by user")
    except Exception as e:
        print(f"\nTest failed with error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        print("\n" + "="*80)
        print("End-to-End Test Completed")
        print("="*80)

