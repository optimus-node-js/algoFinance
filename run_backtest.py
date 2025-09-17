import argparse
import sys
import importlib
import re
from datetime import datetime
import inspect

from server.src.core.connections import ConnectionManager
from server.src.data_ingestion.historical import HistoricalDataHandler
from server.src.api_gateway.utils import find_instrument_token
from server.src.backtesting.runner import BacktestRunner
from server.src.ml.features import FeatureEngine
from server.src.strategy.base_strategy import BaseStrategy
from server.src.config import settings # Import the centralized settings

def to_snake_case(name):
    """Converts a PascalCase or CamelCase string to snake_case."""
    s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
    return re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1).lower()

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
        strategy_file_name = to_snake_case(args.strategy)
        strategy_module_name = f"server.src.strategy.strategies.{strategy_file_name}"
        strategy_class_name = args.strategy
        
        print(f"Attempting to load strategy '{strategy_class_name}' from module '{strategy_module_name}'...")
        
        # 1. Get database and api clients from the connection manager
        db_client = ConnectionManager.get_mongodb_client()
        smart_api_client = ConnectionManager.get_smartapi_client()
        
        if not db_client or not smart_api_client:
            print("❌ Could not establish connections. Aborting backtest.")
            sys.exit(1)

        # 2. Get historical data (we need the token first)
        data_handler = HistoricalDataHandler()
        
        print(f"Finding token for {args.symbol}...")
        # Use the DB name from settings for consistency
        db = db_client[settings.DB_NAME]
        token = find_instrument_token(args.symbol, db, smart_api_client)
        if not token:
            print(f"❌ Could not find token for symbol {args.symbol}.")
            sys.exit(1)

        # 3. Now, instantiate the strategy with the token
        module = importlib.import_module(strategy_module_name)
        
        # Intelligently find the strategy class in the module
        StrategyClass = None
        for name, obj in inspect.getmembers(module, inspect.isclass):
            if issubclass(obj, BaseStrategy) and obj is not BaseStrategy:
                StrategyClass = obj
                strategy_class_name = name # Use the actual class name found
                break

        if not StrategyClass:
            print(f"❌ Could not find a valid strategy class in '{strategy_module_name}.py'.")
            sys.exit(1)

        # Instantiate the strategy, passing the token if the constructor accepts it
        strategy_signature = inspect.signature(StrategyClass.__init__)
        if 'symbol_token' in strategy_signature.parameters:
            strategy_instance = StrategyClass(symbol_token=token)
        else:
            strategy_instance = StrategyClass()
        print(f"✅ Strategy '{strategy_class_name}' loaded successfully.")
        
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

        # 3. Add features to the historical data
        print("\nEnriching historical data with technical features...")
        feature_engine = FeatureEngine()
        enriched_data = feature_engine.add_features(historical_data)
        print("✅ Data enrichment complete.")

        # 4. Run the backtest using the enriched data
        runner = BacktestRunner(strategy_instance, enriched_data, args.symbol)
        runner.run()

    except ImportError:
        print(f"❌ Strategy module or class not found. Make sure '{strategy_module_name}.py' exists and contains a class named '{strategy_class_name}'.")
        sys.exit(1)
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 