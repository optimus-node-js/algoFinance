import argparse
import sys
import importlib
from datetime import datetime

from server.src.api_gateway.auth import AngelOneAuth
from server.src.data_ingestion.historical import HistoricalDataHandler
from server.src.api_gateway.utils import find_instrument_token
from server.src.backtesting.runner import BacktestRunner

def main():
    parser = argparse.ArgumentParser(description="Run a backtest for a given strategy.")
    parser.add_argument("--strategy", required=True, help="The name of the strategy class to test (e.g., SmaCrossover).")
    parser.add_argument("--symbol", required=True, help="The trading symbol to backtest on (e.g., 'SBIN-EQ').")
    parser.add_argument("--start", required=True, help="Start date for backtesting (YYYY-MM-DD).")
    parser.add_argument("--end", required=True, help="End date for backtesting (YYYY-MM-DD).")
    parser.add_argument("--interval", default="1_DAY", help="Candle interval (e.g., '5_MINUTE', '1_DAY').")

    args = parser.parse_args()

    try:
        # 1. Dynamically import the strategy class
        # Convert CamelCase strategy name to snake_case for the filename
        strategy_file_name = ''.join(['_' + i.lower() if i.isupper() else i for i in args.strategy]).lstrip('_')
        strategy_module_name = f"server.src.strategy.strategies.{strategy_file_name}"
        strategy_class_name = args.strategy
        
        print(f"Attempting to load strategy '{strategy_class_name}' from module '{strategy_module_name}'...")
        StrategyClass = getattr(importlib.import_module(strategy_module_name), strategy_class_name)
        strategy_instance = StrategyClass()
        print(f"✅ Strategy '{strategy_class_name}' loaded successfully.")

        # 2. Get historical data
        print("Authenticating...")
        auth = AngelOneAuth()
        if not auth.login():
            print("❌ Authentication failed. Cannot proceed.")
            sys.exit(1)

        data_handler = HistoricalDataHandler(auth)
        
        print(f"Finding token for {args.symbol}...")
        token = find_instrument_token(args.symbol, data_handler.db, data_handler.smart_connect)
        if not token:
            print(f"❌ Could not find token for symbol {args.symbol}.")
            sys.exit(1)
        
        start_date_str = f"{args.start} 09:15"
        end_date_str = f"{args.end} 15:30"
        
        historical_data = data_handler.get_historical_data(
            symbol_token=token,
            from_date=start_date_str,
            to_date=end_date_str,
            interval=args.interval
        )

        if historical_data.empty:
            print("❌ No historical data fetched. Aborting backtest.")
            sys.exit(1)

        # 3. Run the backtest
        runner = BacktestRunner(strategy_instance, historical_data, args.symbol)
        runner.run()

    except ImportError:
        print(f"❌ Strategy module or class not found. Make sure '{strategy_module_name}.py' exists and contains a class named '{strategy_class_name}'.")
        sys.exit(1)
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 