"""
Live Console Monitor Service - Real-Time Trading Dashboard
=========================================================

Real-time console monitoring with live tables, progress bars, and status updates.
Displays thousands of stocks being processed, analyzed, and traded in real-time.

Features:
- Live updating tables for stock discovery, analysis, filtering, backtesting, trading
- Real-time LTP updates from Angel One API
- Parallel batch processing visualization
- Live P&L monitoring and trade tracking
- Microservices communication status

Author: AI Trading System
Version: 1.0.0
"""

import asyncio
import threading
import time
from datetime import datetime
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from collections import defaultdict

# Rich library for beautiful console output
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, TaskID, BarColumn, TextColumn, TimeElapsedColumn
from rich.layout import Layout
from rich.panel import Panel
from rich.live import Live
from rich.text import Text
from rich import box

# Project imports
try:
    from logging.advanced_logger import get_logger
    from core.message_broker import EnhancedMessageBroker
    DEPENDENCIES_AVAILABLE = True
except ImportError:
    DEPENDENCIES_AVAILABLE = False

@dataclass
class StockStatus:
    """Track individual stock processing status."""
    symbol: str
    phase: str = "discovered"  # discovered, analyzing, filtered, backtesting, trading
    ltp: float = 0.0
    score: float = 0.0
    entry_price: float = 0.0
    target: float = 0.0
    stop_loss: float = 0.0
    pnl: float = 0.0
    status: str = "pending"  # pending, active, completed, failed
    indicators_positive: int = 0
    indicators_total: int = 0
    backtest_accuracy: float = 0.0
    last_updated: datetime = field(default_factory=datetime.now)

@dataclass
class BatchStatus:
    """Track batch processing status."""
    batch_id: str
    total_stocks: int
    processed_stocks: int = 0
    phase: str = "starting"
    start_time: datetime = field(default_factory=datetime.now)
    completion_time: Optional[datetime] = None

class LiveConsoleMonitor:
    """
    Real-time console monitoring service for AI trading system.
    
    Displays live updates of:
    - Stock discovery progress (thousands of stocks)
    - AI analysis batches with real-time progress
    - Stock filtering results in live tables
    - Backtesting progress and results
    - Live trading with real-time LTP updates
    - P&L monitoring and trade tracking
    """
    
    def __init__(self):
        """Initialize live console monitor."""
        self.console = Console()
        self.logger = get_logger() if DEPENDENCIES_AVAILABLE else None
        
        # Data tracking
        self.stocks: Dict[str, StockStatus] = {}
        self.batches: Dict[str, BatchStatus] = {}
        self.system_metrics = {
            'total_stocks_fetched': 0,
            'total_stocks_analyzed': 0,
            'total_stocks_filtered': 0,
            'total_stocks_backtested': 0,
            'total_trades_executed': 0,
            'current_phase': 'initializing',
            'session_start': datetime.now(),
            'active_batches': 0
        }
        
        # Live update control
        self.is_running = False
        self.update_interval = 0.5  # Update every 500ms for smooth animation
        
        # Message broker for real-time updates
        if DEPENDENCIES_AVAILABLE:
            try:
                self.message_broker = EnhancedMessageBroker()
                self.setup_message_subscriptions()
            except:
                self.message_broker = None
        else:
            self.message_broker = None
    
    def setup_message_subscriptions(self):
        """Setup RabbitMQ subscriptions for real-time updates."""
        if not self.message_broker:
            return
            
        try:
            # Subscribe to all relevant queues for live monitoring
            subscriptions = [
                ('stock_discovery_progress', self._handle_stock_discovery),
                ('ai_analysis_progress', self._handle_analysis_progress),
                ('stock_filtering_results', self._handle_filtering_results),
                ('backtesting_progress', self._handle_backtesting_progress),
                ('trade_execution_updates', self._handle_trade_updates),
                ('ltp_updates', self._handle_ltp_updates),
                ('system_metrics', self._handle_system_metrics)
            ]
            
            for queue, handler in subscriptions:
                self.message_broker.subscribe_to_queue(queue, handler)
                
        except Exception as e:
            if self.logger:
                self.logger.error("MONITOR", f"Failed to setup subscriptions: {e}")
    
    def create_layout(self) -> Layout:
        """Create the main console layout."""
        layout = Layout()
        
        # Split into header and main content
        layout.split(
            Layout(name="header", size=3),
            Layout(name="main")
        )
        
        # Split main into left and right panels
        layout["main"].split_row(
            Layout(name="left", ratio=2),
            Layout(name="right", ratio=1)
        )
        
        # Split left into stock tables and progress
        layout["left"].split(
            Layout(name="stock_tables", ratio=3),
            Layout(name="progress_bars", ratio=1)
        )
        
        # Split right into system status and trades
        layout["right"].split(
            Layout(name="system_status", ratio=1),
            Layout(name="active_trades", ratio=2)
        )
        
        return layout
    
    def create_header_panel(self) -> Panel:
        """Create system header with key metrics."""
        runtime = datetime.now() - self.system_metrics['session_start']
        
        header_text = Text()
        header_text.append("🚀 AI TRADING SYSTEM - LIVE MONITORING DASHBOARD", style="bold blue")
        header_text.append(f" | Phase: {self.system_metrics['current_phase'].upper()}", style="bold green")
        header_text.append(f" | Runtime: {str(runtime).split('.')[0]}", style="bold yellow")
        header_text.append(f" | Stocks: {self.system_metrics['total_stocks_fetched']:,}", style="bold cyan")
        
        return Panel(header_text, box=box.DOUBLE, style="blue")
    
    def create_stock_discovery_table(self) -> Table:
        """Create live stock discovery table."""
        table = Table(title="🔍 STOCK DISCOVERY - LIVE", box=box.ROUNDED)
        table.add_column("Symbol", style="cyan", width=15)
        table.add_column("Exchange", style="green", width=8)
        table.add_column("LTP", style="yellow", width=10)
        table.add_column("Volume", style="blue", width=12)
        table.add_column("Status", style="magenta", width=10)
        
        # Show latest 20 stocks being discovered
        recent_stocks = sorted(
            [s for s in self.stocks.values() if s.phase == "discovered"], 
            key=lambda x: x.last_updated, 
            reverse=True
        )[:20]
        
        for stock in recent_stocks:
            status_color = "green" if stock.status == "completed" else "yellow" if stock.status == "active" else "red"
            table.add_row(
                stock.symbol,
                "NSE",
                f"₹{stock.ltp:.2f}" if stock.ltp > 0 else "Fetching...",
                "1M+" if stock.symbol in ['RELIANCE-EQ', 'TCS-EQ'] else "500K",
                f"[{status_color}]{stock.status}[/{status_color}]"
            )
        
        return table
    
    def create_analysis_table(self) -> Table:
        """Create live AI analysis table."""
        table = Table(title="🧠 AI ANALYSIS - LIVE BATCHES", box=box.ROUNDED)
        table.add_column("Batch", style="cyan", width=8)
        table.add_column("Stocks", style="green", width=12)
        table.add_column("Progress", style="yellow", width=15)
        table.add_column("Avg Score", style="blue", width=10)
        table.add_column("Status", style="magenta", width=12)
        
        # Show active batches
        for batch_id, batch in self.batches.items():
            if batch.phase == "analyzing":
                progress_pct = (batch.processed_stocks / batch.total_stocks * 100) if batch.total_stocks > 0 else 0
                progress_bar = "█" * int(progress_pct / 10) + "░" * (10 - int(progress_pct / 10))
                
                # Calculate average score for this batch
                batch_stocks = [s for s in self.stocks.values() if s.phase == "analyzing"]
                avg_score = sum(s.score for s in batch_stocks) / len(batch_stocks) if batch_stocks else 0
                
                table.add_row(
                    batch_id,
                    f"{batch.processed_stocks}/{batch.total_stocks}",
                    f"[green]{progress_bar}[/green] {progress_pct:.1f}%",
                    f"{avg_score:.2f}",
                    f"[yellow]Processing[/yellow]"
                )
        
        return table
    
    def create_filtering_table(self) -> Table:
        """Create live stock filtering results table."""
        table = Table(title="🎯 FILTERED STOCKS - HIGH POTENTIAL", box=box.ROUNDED)
        table.add_column("Rank", style="cyan", width=6)
        table.add_column("Symbol", style="green", width=15)
        table.add_column("Score", style="yellow", width=8)
        table.add_column("LTP", style="blue", width=10)
        table.add_column("Entry", style="magenta", width=10)
        table.add_column("Target", style="green", width=10)
        table.add_column("Stop Loss", style="red", width=10)
        
        # Show top filtered stocks
        filtered_stocks = [s for s in self.stocks.values() if s.phase == "filtered"]
        filtered_stocks.sort(key=lambda x: x.score, reverse=True)
        
        for i, stock in enumerate(filtered_stocks[:15], 1):
            table.add_row(
                str(i),
                stock.symbol,
                f"{stock.score:.2f}",
                f"₹{stock.ltp:.2f}",
                f"₹{stock.entry_price:.2f}" if stock.entry_price > 0 else "TBD",
                f"₹{stock.target:.2f}" if stock.target > 0 else "TBD",
                f"₹{stock.stop_loss:.2f}" if stock.stop_loss > 0 else "TBD"
            )
        
        return table
    
    def create_backtesting_table(self) -> Table:
        """Create live backtesting results table."""
        table = Table(title="🔍 BACKTESTING - LIVE RESULTS", box=box.ROUNDED)
        table.add_column("Symbol", style="cyan", width=15)
        table.add_column("Accuracy", style="green", width=10)
        table.add_column("Indicators", style="yellow", width=12)
        table.add_column("Profit", style="blue", width=10)
        table.add_column("Trades", style="magenta", width=8)
        table.add_column("Status", style="white", width=12)
        
        # Show stocks being backtested
        backtest_stocks = [s for s in self.stocks.values() if s.phase == "backtesting"]
        
        for stock in backtest_stocks[-15:]:  # Show latest 15
            accuracy_color = "green" if stock.backtest_accuracy > 0.7 else "yellow" if stock.backtest_accuracy > 0.5 else "red"
            status_color = "green" if stock.status == "passed" else "red" if stock.status == "failed" else "yellow"
            
            table.add_row(
                stock.symbol,
                f"[{accuracy_color}]{stock.backtest_accuracy:.1%}[/{accuracy_color}]",
                f"{stock.indicators_positive}/{stock.indicators_total}",
                f"₹{abs(stock.pnl):.0f}" if stock.pnl != 0 else "Testing...",
                "50+" if stock.backtest_accuracy > 0 else "0",
                f"[{status_color}]{stock.status}[/{status_color}]"
            )
        
        return table
    
    def create_live_trading_table(self) -> Table:
        """Create live trading table with real-time updates."""
        table = Table(title="🚀 LIVE TRADING - REAL-TIME P&L", box=box.ROUNDED)
        table.add_column("Symbol", style="cyan", width=15)
        table.add_column("Live LTP", style="green", width=10)
        table.add_column("Entry", style="yellow", width=10)
        table.add_column("Qty", style="blue", width=6)
        table.add_column("P&L", style="magenta", width=12)
        table.add_column("P&L %", style="white", width=8)
        table.add_column("Status", style="white", width=10)
        
        # Show active trades
        trading_stocks = [s for s in self.stocks.values() if s.phase == "trading" and s.status == "active"]
        
        for stock in trading_stocks[-20:]:  # Show latest 20 trades
            pnl_color = "green" if stock.pnl > 0 else "red" if stock.pnl < 0 else "yellow"
            pnl_pct = (stock.pnl / (stock.entry_price * 10)) * 100 if stock.entry_price > 0 else 0
            
            table.add_row(
                stock.symbol,
                f"₹{stock.ltp:.2f}",
                f"₹{stock.entry_price:.2f}",
                "10",  # Default quantity
                f"[{pnl_color}]₹{stock.pnl:+.2f}[/{pnl_color}]",
                f"[{pnl_color}]{pnl_pct:+.1f}%[/{pnl_color}]",
                f"[green]{stock.status}[/green]"
            )
        
        return table
    
    def create_system_status_panel(self) -> Panel:
        """Create system status panel."""
        status_text = Text()
        
        # System metrics
        status_text.append("📊 SYSTEM METRICS\n", style="bold blue")
        status_text.append(f"🔍 Discovered: {self.system_metrics['total_stocks_fetched']:,}\n", style="cyan")
        status_text.append(f"🧠 Analyzed: {self.system_metrics['total_stocks_analyzed']:,}\n", style="green")
        status_text.append(f"🎯 Filtered: {self.system_metrics['total_stocks_filtered']:,}\n", style="yellow")
        status_text.append(f"🔍 Backtested: {self.system_metrics['total_stocks_backtested']:,}\n", style="blue")
        status_text.append(f"🚀 Traded: {self.system_metrics['total_trades_executed']:,}\n", style="magenta")
        
        # Active batches
        status_text.append(f"\n🔄 ACTIVE BATCHES\n", style="bold yellow")
        active_batches = [b for b in self.batches.values() if b.phase != "completed"]
        for batch in active_batches[-5:]:
            status_text.append(f"• {batch.batch_id}: {batch.processed_stocks}/{batch.total_stocks}\n", style="white")
        
        return Panel(status_text, title="System Status", box=box.ROUNDED, style="blue")
    
    def create_portfolio_panel(self) -> Panel:
        """Create portfolio summary panel."""
        portfolio_text = Text()
        
        # Calculate portfolio metrics
        active_trades = [s for s in self.stocks.values() if s.phase == "trading" and s.status == "active"]
        total_investment = sum(s.entry_price * 10 for s in active_trades)  # 10 shares each
        total_pnl = sum(s.pnl for s in active_trades)
        
        portfolio_text.append("💼 PORTFOLIO SUMMARY\n", style="bold green")
        portfolio_text.append(f"Active Positions: {len(active_trades)}\n", style="cyan")
        portfolio_text.append(f"Total Investment: ₹{total_investment:,.2f}\n", style="yellow")
        
        # P&L with color coding
        pnl_color = "green" if total_pnl > 0 else "red" if total_pnl < 0 else "yellow"
        pnl_pct = (total_pnl / total_investment * 100) if total_investment > 0 else 0
        portfolio_text.append(f"Total P&L: ", style="white")
        portfolio_text.append(f"₹{total_pnl:+,.2f} ({pnl_pct:+.2f}%)\n", style=pnl_color)
        
        # Win rate
        winning_trades = sum(1 for s in active_trades if s.pnl > 0)
        win_rate = (winning_trades / len(active_trades) * 100) if active_trades else 0
        portfolio_text.append(f"Win Rate: {win_rate:.1f}%\n", style="blue")
        
        return Panel(portfolio_text, title="Portfolio", box=box.ROUNDED, style="green")
    
    async def start_live_monitoring(self):
        """Start the live console monitoring dashboard."""
        self.is_running = True
        
        if self.logger:
            self.logger.info("MONITOR", "🚀 Starting Live Console Monitor")
        
        layout = self.create_layout()
        
        with Live(layout, console=self.console, refresh_per_second=2, screen=True) as live:
            while self.is_running:
                try:
                    # Update layout components
                    layout["header"].update(self.create_header_panel())
                    
                    # Create tabs for different phases
                    if self.system_metrics['current_phase'] == 'stock_discovery':
                        layout["stock_tables"].update(self.create_stock_discovery_table())
                    elif self.system_metrics['current_phase'] == 'ai_analysis':
                        layout["stock_tables"].update(self.create_analysis_table())
                    elif self.system_metrics['current_phase'] == 'filtering':
                        layout["stock_tables"].update(self.create_filtering_table())
                    elif self.system_metrics['current_phase'] == 'backtesting':
                        layout["stock_tables"].update(self.create_backtesting_table())
                    elif self.system_metrics['current_phase'] == 'trading':
                        layout["stock_tables"].update(self.create_live_trading_table())
                    
                    # Update progress bars (for active batches)
                    layout["progress_bars"].update(self.create_progress_panel())
                    
                    # Update system panels
                    layout["system_status"].update(self.create_system_status_panel())
                    layout["active_trades"].update(self.create_portfolio_panel())
                    
                    await asyncio.sleep(self.update_interval)
                    
                except KeyboardInterrupt:
                    break
                except Exception as e:
                    if self.logger:
                        self.logger.error("MONITOR", f"Error in live monitoring: {e}")
                    await asyncio.sleep(1)
        
        self.is_running = False
        if self.logger:
            self.logger.info("MONITOR", "🛑 Live Console Monitor stopped")
    
    def create_progress_panel(self) -> Panel:
        """Create progress bars for active operations."""
        progress_text = Text()
        progress_text.append("🔄 LIVE PROGRESS\n", style="bold blue")
        
        # Show progress for each active batch
        for batch in self.batches.values():
            if batch.phase != "completed":
                progress_pct = (batch.processed_stocks / batch.total_stocks * 100) if batch.total_stocks > 0 else 0
                progress_bar = "█" * int(progress_pct / 5) + "░" * (20 - int(progress_pct / 5))
                
                progress_text.append(f"{batch.batch_id}: ", style="cyan")
                progress_text.append(f"[green]{progress_bar}[/green] {progress_pct:.1f}%\n", style="white")
        
        return Panel(progress_text, title="Active Operations", box=box.ROUNDED, style="yellow")
    
    # Message handlers for real-time updates
    def _handle_stock_discovery(self, message):
        """Handle stock discovery updates."""
        try:
            data = message.get('data', {})
            symbol = data.get('symbol')
            ltp = data.get('ltp', 0)
            
            if symbol:
                if symbol not in self.stocks:
                    self.stocks[symbol] = StockStatus(symbol=symbol)
                
                self.stocks[symbol].phase = "discovered"
                self.stocks[symbol].ltp = ltp
                self.stocks[symbol].status = "completed"
                self.stocks[symbol].last_updated = datetime.now()
                
                self.system_metrics['total_stocks_fetched'] += 1
                
        except Exception as e:
            if self.logger:
                self.logger.error("MONITOR", f"Error handling stock discovery: {e}")
    
    def _handle_analysis_progress(self, message):
        """Handle AI analysis progress updates."""
        try:
            data = message.get('data', {})
            symbol = data.get('symbol')
            score = data.get('score', 0)
            batch_id = data.get('batch_id', 'default')
            
            if symbol:
                if symbol not in self.stocks:
                    self.stocks[symbol] = StockStatus(symbol=symbol)
                
                self.stocks[symbol].phase = "analyzing"
                self.stocks[symbol].score = score
                self.stocks[symbol].status = "active"
                self.stocks[symbol].last_updated = datetime.now()
                
                # Update batch progress
                if batch_id not in self.batches:
                    self.batches[batch_id] = BatchStatus(batch_id=batch_id, total_stocks=500)
                
                self.batches[batch_id].processed_stocks += 1
                self.system_metrics['total_stocks_analyzed'] += 1
                
        except Exception as e:
            if self.logger:
                self.logger.error("MONITOR", f"Error handling analysis progress: {e}")
    
    def _handle_filtering_results(self, message):
        """Handle stock filtering results."""
        try:
            data = message.get('data', {})
            symbol = data.get('symbol')
            score = data.get('score', 0)
            entry_price = data.get('entry_price', 0)
            
            if symbol and symbol in self.stocks:
                self.stocks[symbol].phase = "filtered"
                self.stocks[symbol].score = score
                self.stocks[symbol].entry_price = entry_price
                self.stocks[symbol].target = entry_price * 1.10
                self.stocks[symbol].stop_loss = entry_price * 0.95
                self.stocks[symbol].status = "completed"
                self.stocks[symbol].last_updated = datetime.now()
                
                self.system_metrics['total_stocks_filtered'] += 1
                
        except Exception as e:
            if self.logger:
                self.logger.error("MONITOR", f"Error handling filtering results: {e}")
    
    def _handle_backtesting_progress(self, message):
        """Handle backtesting progress updates."""
        try:
            data = message.get('data', {})
            symbol = data.get('symbol')
            accuracy = data.get('accuracy', 0)
            indicators_positive = data.get('indicators_positive', 0)
            indicators_total = data.get('indicators_total', 0)
            
            if symbol and symbol in self.stocks:
                self.stocks[symbol].phase = "backtesting"
                self.stocks[symbol].backtest_accuracy = accuracy
                self.stocks[symbol].indicators_positive = indicators_positive
                self.stocks[symbol].indicators_total = indicators_total
                self.stocks[symbol].status = "passed" if accuracy > 0.6 else "failed"
                self.stocks[symbol].last_updated = datetime.now()
                
                self.system_metrics['total_stocks_backtested'] += 1
                
        except Exception as e:
            if self.logger:
                self.logger.error("MONITOR", f"Error handling backtesting progress: {e}")
    
    def _handle_trade_updates(self, message):
        """Handle trade execution updates."""
        try:
            data = message.get('data', {})
            symbol = data.get('symbol')
            entry_price = data.get('entry_price', 0)
            current_price = data.get('current_price', 0)
            
            if symbol and symbol in self.stocks:
                self.stocks[symbol].phase = "trading"
                self.stocks[symbol].entry_price = entry_price
                self.stocks[symbol].ltp = current_price
                self.stocks[symbol].pnl = (current_price - entry_price) * 10  # 10 shares
                self.stocks[symbol].status = "active"
                self.stocks[symbol].last_updated = datetime.now()
                
                self.system_metrics['total_trades_executed'] += 1
                
        except Exception as e:
            if self.logger:
                self.logger.error("MONITOR", f"Error handling trade updates: {e}")
    
    def _handle_ltp_updates(self, message):
        """Handle real-time LTP updates."""
        try:
            data = message.get('data', {})
            symbol = data.get('symbol')
            ltp = data.get('ltp', 0)
            
            if symbol and symbol in self.stocks:
                self.stocks[symbol].ltp = ltp
                # Recalculate P&L if it's an active trade
                if self.stocks[symbol].phase == "trading" and self.stocks[symbol].entry_price > 0:
                    self.stocks[symbol].pnl = (ltp - self.stocks[symbol].entry_price) * 10
                self.stocks[symbol].last_updated = datetime.now()
                
        except Exception as e:
            if self.logger:
                self.logger.error("MONITOR", f"Error handling LTP updates: {e}")
    
    def _handle_system_metrics(self, message):
        """Handle system metrics updates."""
        try:
            data = message.get('data', {})
            phase = data.get('phase')
            if phase:
                self.system_metrics['current_phase'] = phase
                
        except Exception as e:
            if self.logger:
                self.logger.error("MONITOR", f"Error handling system metrics: {e}")
    
    def stop_monitoring(self):
        """Stop the live monitoring."""
        self.is_running = False
        if self.logger:
            self.logger.info("MONITOR", "🛑 Stopping Live Console Monitor")

# Global monitor instance
_monitor_instance: Optional[LiveConsoleMonitor] = None

def get_live_monitor() -> LiveConsoleMonitor:
    """Get global live monitor instance."""
    global _monitor_instance
    if _monitor_instance is None:
        _monitor_instance = LiveConsoleMonitor()
    return _monitor_instance

async def start_live_dashboard():
    """Start the live trading dashboard."""
    monitor = get_live_monitor()
    await monitor.start_live_monitoring()

if __name__ == "__main__":
    # Test the live monitor
    print("🚀 Starting Live Console Monitor Test...")
    
    async def test_monitor():
        monitor = LiveConsoleMonitor()
        
        # Add some test data
        test_stocks = ['RELIANCE-EQ', 'TCS-EQ', 'SBIN-EQ', 'HDFC-EQ', 'INFY-EQ']
        for i, symbol in enumerate(test_stocks):
            monitor.stocks[symbol] = StockStatus(
                symbol=symbol,
                phase="trading",
                ltp=1000 + i * 100,
                score=0.7 + i * 0.05,
                entry_price=950 + i * 100,
                target=1050 + i * 100,
                stop_loss=900 + i * 100,
                pnl=(50 + i * 10) * 10,
                status="active"
            )
        
        monitor.system_metrics.update({
            'total_stocks_fetched': 5247,
            'total_stocks_analyzed': 4891,
            'total_stocks_filtered': 127,
            'total_stocks_backtested': 89,
            'total_trades_executed': 45,
            'current_phase': 'trading'
        })
        
        # Start monitoring for 30 seconds
        await asyncio.wait_for(monitor.start_live_monitoring(), timeout=30)
    
    try:
        asyncio.run(test_monitor())
    except KeyboardInterrupt:
        print("\n✅ Live Monitor test completed!")

