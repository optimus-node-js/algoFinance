import pandas as pd
import vectorbt as vbt
import sys
import os
from datetime import datetime, UTC

# Add the project root directory to the Python path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.append(PROJECT_ROOT)

from server.src.database.connect import get_db
from server.src.strategy.base_strategy import BaseStrategy

class BacktestRunner:
    def __init__(self, strategy: BaseStrategy, historical_data: pd.DataFrame, symbol: str):
        if not isinstance(strategy, BaseStrategy):
            raise TypeError("Strategy must be an instance of a class that inherits from BaseStrategy.")
        if not isinstance(historical_data, pd.DataFrame) or historical_data.empty:
            raise ValueError("Historical data must be a non-empty pandas DataFrame.")
        if 'close' not in historical_data.columns:
             raise ValueError("Historical data must contain a 'close' column.")

        self.strategy = strategy
        self.data = historical_data
        self.symbol = symbol
        self.db = get_db()
        self.results_collection = self.db.backtest_results if self.db is not None else None
    
    def run(self):
        """
        Runs the backtest and saves the results.
        """
        print(f"\n--- Running Backtest for {type(self.strategy).__name__} on {self.symbol} ---")
        
        # 1. Generate signals from the strategy
        entries, exits = self.strategy.generate_signals(self.data)
        
        # 2. Run the simulation using vectorbt
        portfolio = vbt.Portfolio.from_signals(
            self.data['close'], 
            entries, 
            exits, 
            freq='D', # Set frequency to 'Daily' for correct metric calculation
            init_cash=100000
        )
        
        # 3. Get performance stats
        stats = portfolio.stats()
        
        print("\n--- Backtest Results ---")
        print(stats)
        
        # 4. Save results to database
        if self.results_collection is not None:
            # The `stats` object can be a DataFrame for grouped backtests.
            # We only save to DB if it's a Series (for a single run).
            if isinstance(stats, pd.Series):
                self._save_results(stats)
            else:
                print("\n⚠️ Backtest generated multi-column stats (grouped backtest). Results not saved to DB.")
        else:
            print("⚠️ Could not save results to DB. No database connection.")
            
        return stats

    def _save_results(self, stats: pd.Series):
        """
        Formats and saves the backtest results to MongoDB.
        """
        # Convert numpy types to native Python types for JSON/BSON serialization
        def convert_type(value):
            if pd.isna(value):
                return None
            if isinstance(value, (pd.Timestamp, datetime)):
                return value
            if isinstance(value, pd.Timedelta):
                return str(value) # Convert timedelta to string
            if hasattr(value, 'item'):
                return value.item() # General method for numpy types
            return value

        duration = stats.get('Duration')
        duration_days = duration.days if isinstance(duration, pd.Timedelta) else None

        result_doc = {
            "strategy_name": type(self.strategy).__name__,
            "symbol": self.symbol,
            "backtest_timestamp": datetime.now(UTC),
            "start_date": convert_type(stats.get('Start')),
            "end_date": convert_type(stats.get('End')),
            "duration_days": convert_type(duration_days),
            "initial_cash": convert_type(stats.get('Initial Cash')),
            "final_value": convert_type(stats.get('End Value')),
            "total_return_pct": convert_type(stats.get('Total Return [%]')),
            "sharpe_ratio": convert_type(stats.get('Sharpe Ratio')),
            "max_drawdown_pct": convert_type(stats.get('Max Drawdown [%]')),
            "win_rate_pct": convert_type(stats.get('Win Rate [%]')),
            "total_trades": convert_type(stats.get('Total Trades')),
            "profit_factor": convert_type(stats.get('Profit Factor')),
            "full_stats": {k: convert_type(v) for k, v in stats.to_dict().items()}
        }

        if self.results_collection is None:
            print("\n⚠️ Could not save results to DB. Collection not available.")
            return
        
        try:
            self.results_collection.insert_one(result_doc)
            print("\n✅ Backtest results saved to database.")
        except Exception as e:
            print(f"\n❌ Error saving backtest results to DB: {e}") 