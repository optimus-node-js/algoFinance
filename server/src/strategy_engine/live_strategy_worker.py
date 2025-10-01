"""
Live Strategy Worker
===================

Enhanced strategy worker that consumes real-time market data from our
unified messaging system and executes trading strategies with live data.
"""

import asyncio
import json
import time
from typing import Dict, Any, List, Optional, Callable
from datetime import datetime, UTC
import threading
import logging

# Add project root to path for imports
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("live_strategy_worker")

from messaging_enhanced.kafka.consumers.market_data_consumer import get_market_data_consumer
from messaging_enhanced.kafka.producers.order_producer import get_order_producer
from strategy_engine.base_strategy_engine import BaseStrategyEngine
from strategy_engine.examples.momentum_strategy import MomentumStrategy
from strategy_engine.risk_integration import RiskIntegrationClient


class LiveStrategyWorker:
    """
    Live strategy worker that processes real-time market data and executes
    trading strategies with integrated risk management.
    """
    
    def __init__(self, worker_id: str = "live_strategy_worker"):
        """Initialize the live strategy worker."""
        self.worker_id = worker_id
        self.is_running = False
        
        # Initialize messaging components
        self.market_consumer = get_market_data_consumer(
            consumer_id=f"{worker_id}_consumer",
            group_id="live_strategy_group"
        )
        self.order_producer = get_order_producer("live_strategy_producer")
        
        # Initialize risk integration
        self.risk_client = RiskIntegrationClient()
        
        # Strategy management
        self.active_strategies: Dict[str, BaseStrategyEngine] = {}
        self.strategy_performance: Dict[str, Dict[str, Any]] = {}
        
        # Performance tracking
        self.messages_processed = 0
        self.signals_generated = 0
        self.orders_sent = 0
        self.processing_errors = 0
        self.start_time = datetime.now()
        self._lock = threading.Lock()
        
        logger.info(f"LiveStrategyWorker '{worker_id}' initialized")
    
    def add_strategy(self, strategy: BaseStrategyEngine) -> bool:
        """
        Add a strategy to the worker.
        
        Args:
            strategy: Strategy instance to add
            
        Returns:
            True if strategy was added successfully
        """
        try:
            strategy_id = strategy.strategy_id
            
            # Set up strategy dependencies
            strategy.set_risk_manager(self.risk_client)
            strategy.set_order_publisher(self.order_producer)
            
            # Add to active strategies
            with self._lock:
                self.active_strategies[strategy_id] = strategy
                self.strategy_performance[strategy_id] = {
                    'signals_generated': 0,
                    'orders_sent': 0,
                    'errors': 0,
                    'last_signal_time': None,
                    'avg_processing_time_ms': 0.0
                }
            
            logger.info(f"Added strategy '{strategy_id}' to worker")
            return True
            
        except Exception as e:
            logger.error(f"Failed to add strategy: {e}")
            return False
    
    def activate_strategy(self, strategy_id: str) -> bool:
        """Activate a strategy."""
        try:
            if strategy_id in self.active_strategies:
                self.active_strategies[strategy_id].activate()
                logger.info(f"Activated strategy '{strategy_id}'")
                return True
            else:
                logger.error(f"Strategy '{strategy_id}' not found")
                return False
        except Exception as e:
            logger.error(f"Failed to activate strategy '{strategy_id}': {e}")
            return False
    
    def deactivate_strategy(self, strategy_id: str) -> bool:
        """Deactivate a strategy."""
        try:
            if strategy_id in self.active_strategies:
                self.active_strategies[strategy_id].deactivate()
                logger.info(f"Deactivated strategy '{strategy_id}'")
                return True
            else:
                logger.error(f"Strategy '{strategy_id}' not found")
                return False
        except Exception as e:
            logger.error(f"Failed to deactivate strategy '{strategy_id}': {e}")
            return False
    
    async def process_market_data(self, symbol: str, market_data: Dict[str, Any], processing_info: Dict[str, Any]):
        """
        Process market data with all active strategies.
        
        Args:
            symbol: Trading symbol
            market_data: Market data tick
            processing_info: Processing metadata
        """
        try:
            processing_start = time.time()
            
            # Process with all active strategies
            for strategy_id, strategy in self.active_strategies.items():
                if not strategy.is_active:
                    continue
                
                try:
                    strategy_start = time.time()
                    
                    # Process market data with strategy
                    await strategy.process_market_data(market_data)
                    
                    # Update strategy performance
                    strategy_time = (time.time() - strategy_start) * 1000  # ms
                    with self._lock:
                        perf = self.strategy_performance[strategy_id]
                        perf['last_signal_time'] = datetime.now(UTC).isoformat()
                        
                        # Update average processing time
                        if perf['avg_processing_time_ms'] == 0:
                            perf['avg_processing_time_ms'] = strategy_time
                        else:
                            perf['avg_processing_time_ms'] = (perf['avg_processing_time_ms'] + strategy_time) / 2
                    
                except Exception as strategy_error:
                    logger.error(f"Strategy '{strategy_id}' error processing {symbol}: {strategy_error}")
                    with self._lock:
                        self.strategy_performance[strategy_id]['errors'] += 1
                        self.processing_errors += 1
            
            # Update overall performance
            total_time = (time.time() - processing_start) * 1000  # ms
            with self._lock:
                self.messages_processed += 1
            
            # Log high latency warnings
            if total_time > 50:  # 50ms threshold
                logger.warning(f"High processing latency: {total_time:.2f}ms for {symbol}")
            
        except Exception as e:
            logger.error(f"Error processing market data for {symbol}: {e}")
            with self._lock:
                self.processing_errors += 1
    
    async def start_processing(self):
        """Start processing market data from Kafka."""
        if self.is_running:
            logger.warning("Worker is already running")
            return
        
        try:
            self.is_running = True
            logger.info(f"Starting live strategy processing for worker '{self.worker_id}'")
            
            # Register market data callback
            self.market_consumer.register_callback(
                "live_strategy_processor",
                self.process_market_data
            )
            
            # Start continuous processing
            self.market_consumer.start_continuous_processing(process_interval=0.01)  # 10ms interval
            
            logger.info("Live strategy processing started successfully")
            
            # Keep processing until stopped
            while self.is_running:
                await asyncio.sleep(1)
                
                # Log periodic stats
                if self.messages_processed > 0 and self.messages_processed % 100 == 0:
                    stats = self.get_performance_stats()
                    logger.info(f"Processed {stats['messages_processed']} messages, "
                              f"{stats['messages_per_second']:.2f} msg/sec")
            
        except Exception as e:
            logger.error(f"Error in live strategy processing: {e}")
            self.is_running = False
            raise
    
    def stop_processing(self):
        """Stop processing market data."""
        if not self.is_running:
            logger.info("Worker is not running")
            return
        
        try:
            logger.info("Stopping live strategy processing...")
            self.is_running = False
            
            # Stop market data consumer
            self.market_consumer.stop_continuous_processing()
            
            # Unregister callback
            self.market_consumer.unregister_callback("live_strategy_processor")
            
            logger.info("Live strategy processing stopped successfully")
            
        except Exception as e:
            logger.error(f"Error stopping live strategy processing: {e}")
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """Get performance statistics."""
        with self._lock:
            runtime = (datetime.now() - self.start_time).total_seconds()
            
            return {
                'worker_id': self.worker_id,
                'is_running': self.is_running,
                'messages_processed': self.messages_processed,
                'signals_generated': self.signals_generated,
                'orders_sent': self.orders_sent,
                'processing_errors': self.processing_errors,
                'runtime_seconds': runtime,
                'messages_per_second': self.messages_processed / runtime if runtime > 0 else 0,
                'error_rate': self.processing_errors / self.messages_processed if self.messages_processed > 0 else 0,
                'active_strategies': len([s for s in self.active_strategies.values() if s.is_active]),
                'total_strategies': len(self.active_strategies),
                'strategy_performance': dict(self.strategy_performance),
                'start_time': self.start_time.isoformat()
            }
    
    def get_strategy_status(self) -> Dict[str, Any]:
        """Get status of all strategies."""
        strategy_status = {}
        
        for strategy_id, strategy in self.active_strategies.items():
            try:
                status = strategy.get_strategy_status()
                status.update(self.strategy_performance[strategy_id])
                strategy_status[strategy_id] = status
            except Exception as e:
                strategy_status[strategy_id] = {
                    'error': f"Failed to get status: {e}",
                    'is_active': strategy.is_active
                }
        
        return strategy_status
    
    async def close(self):
        """Close the worker and cleanup resources."""
        logger.info(f"Closing LiveStrategyWorker '{self.worker_id}'...")
        
        # Stop processing
        self.stop_processing()
        
        # Close risk client
        if self.risk_client:
            await self.risk_client.close()
        
        # Close market consumer
        if self.market_consumer:
            self.market_consumer.close()
        
        # Log final statistics
        stats = self.get_performance_stats()
        logger.info(f"LiveStrategyWorker final stats: {stats}")
        
        logger.info("LiveStrategyWorker closed successfully")


async def test_live_strategy_integration():
    """
    Test the live strategy integration with real-time market data.
    
    This demonstrates:
    1. Real-time market data consumption from Kafka
    2. Strategy execution with live data
    3. Risk integration and validation
    4. Performance monitoring
    """
    logger.info("Testing Live Strategy Integration")
    logger.info("=" * 60)
    
    # Initialize the worker
    worker = LiveStrategyWorker("test_live_worker")
    
    try:
        # Create and add a momentum strategy
        momentum_strategy = MomentumStrategy(
            strategy_id="live_momentum_test",
            symbol="NIFTY",
            short_period=5,
            long_period=20
        )
        
        success = worker.add_strategy(momentum_strategy)
        if success:
            logger.info("Added MomentumStrategy to worker")
            
            # Activate the strategy
            worker.activate_strategy("live_momentum_test")
            logger.info("Activated MomentumStrategy")
            
            # Start processing
            logger.info("Starting live strategy processing...")
            
            # Run processing for 30 seconds
            processing_task = asyncio.create_task(worker.start_processing())
            
            # Monitor for 30 seconds
            for i in range(30):
                await asyncio.sleep(1)
                
                if i % 5 == 0:  # Every 5 seconds
                    stats = worker.get_performance_stats()
                    strategy_status = worker.get_strategy_status()
                    
                    logger.info(f"[{i}s] Messages: {stats['messages_processed']}, "
                              f"Errors: {stats['processing_errors']}, "
                              f"Rate: {stats['messages_per_second']:.2f} msg/sec")
                    
                    for strategy_id, status in strategy_status.items():
                        logger.info(f"  Strategy '{strategy_id}': Active={status.get('is_active', False)}, "
                                  f"Signals={status.get('signals_generated', 0)}")
            
            # Stop processing
            logger.info("Stopping live strategy processing...")
            worker.stop_processing()
            processing_task.cancel()
            
            # Final statistics
            final_stats = worker.get_performance_stats()
            final_strategy_status = worker.get_strategy_status()
            
            logger.info("Final Test Results:")
            logger.info("=" * 40)
            logger.info(f"Messages Processed: {final_stats['messages_processed']}")
            logger.info(f"Processing Errors: {final_stats['processing_errors']}")
            logger.info(f"Average Rate: {final_stats['messages_per_second']:.2f} msg/sec")
            logger.info(f"Error Rate: {final_stats['error_rate']:.2%}")
            
            for strategy_id, status in final_strategy_status.items():
                logger.info(f"Strategy '{strategy_id}':")
                logger.info(f"  Signals Generated: {status.get('signals_generated', 0)}")
                logger.info(f"  Orders Sent: {status.get('orders_sent', 0)}")
                logger.info(f"  Avg Processing Time: {status.get('avg_processing_time_ms', 0):.2f}ms")
            
            if final_stats['messages_processed'] > 0:
                logger.info("SUCCESS: Live strategy integration is working!")
            else:
                logger.warning("WARNING: No messages were processed")
        else:
            logger.error("Failed to add strategy to worker")
    
    except Exception as e:
        logger.error(f"Test failed with error: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        # Cleanup
        await worker.close()


if __name__ == "__main__":
    print("\n" + "="*80)
    print("LIVE STRATEGY ENGINE INTEGRATION TEST")
    print("   Real-time Market Data -> Strategy Execution -> Risk Validation")
    print("="*80)
    
    try:
        asyncio.run(test_live_strategy_integration())
    except KeyboardInterrupt:
        print("\nTest interrupted by user")
    except Exception as e:
        print(f"\nTest failed with error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        print("\n" + "="*80)
        print("Test completed")
        print("="*80)

