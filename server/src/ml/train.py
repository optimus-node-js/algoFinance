import sys
import os
import argparse
import pandas as pd
import numpy as np
from datetime import datetime
import joblib

# Add the project root directory to the Python path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
sys.path.append(PROJECT_ROOT)

from server.src.core.connections import ConnectionManager
from server.src.data_ingestion.historical import HistoricalDataHandler
from server.src.api_gateway.utils import find_instrument_token
from server.src.ml.features import FeatureEngine
from server.src.config import settings # Import the centralized settings

from sklearn.model_selection import train_test_split
from sklearn.ensemble import GradientBoostingClassifier # Use a more powerful model
from sklearn.metrics import classification_report
from sklearn.preprocessing import StandardScaler

def train_model(symbol: str, start_date: str, end_date: str, interval: str, prediction_window: int):
    """
    Fetches data, engineers features, trains a model, and saves it.
    """
    print("--- Starting Model Training ---")

    # 1. Fetch historical data using the new ConnectionManager
    db_client = ConnectionManager.get_mongodb_client()
    smart_api_client = ConnectionManager.get_smartapi_client()

    if not db_client or not smart_api_client:
        print("❌ Could not establish connections. Aborting training.")
        return

    data_handler = HistoricalDataHandler()
    
    print(f"Finding token for {symbol}...")
    db = db_client[settings.DB_NAME]
    token = find_instrument_token(symbol, db, smart_api_client)
    if not token:
        print(f"❌ Could not find token for symbol {symbol}.")
        return
    
    start_date_str = f"{start_date} 09:15"
    end_date_str = f"{end_date} 15:30"
    
    historical_data = data_handler.get_historical_data(
        symbol_token=token,
        from_date=start_date_str,
        to_date=end_date_str,
        interval=interval
    )

    if historical_data.empty:
        print("❌ No historical data fetched. Aborting training.")
        return

    # 2. Add features
    print("\nEnriching data with features...")
    feature_engine = FeatureEngine()
    data_with_features = feature_engine.add_features(historical_data.copy())
    print("✅ Feature enrichment complete.")

    # 3. Define the prediction target
    print(f"\nCreating target variable (price change over next {prediction_window} periods)...")
    data_with_features['future_close'] = data_with_features['close'].shift(-prediction_window)
    data_with_features['target'] = (data_with_features['future_close'] > data_with_features['close']).astype(int)
    
    data_with_features.dropna(inplace=True)
    print(f"Target distribution:\n{data_with_features['target'].value_counts(normalize=True)}")

    # 4. Select features and define X and y
    features = [col for col in data_with_features.columns if col.isupper() and '_L' not in col and '_S' not in col]
    
    if not features:
        print("❌ No features were generated. Check the FeatureEngine configuration. Aborting.")
        return
        
    print(f"\nUsing {len(features)} features for training: {features}")
    X = data_with_features[features]
    y = data_with_features['target']
    
    # 5. Split data into training and testing sets
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)
    print(f"\nData split into {len(X_train)} training samples and {len(X_test)} testing samples.")

    # 6. Scale features
    print("\nScaling features...")
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)
    
    # 7. Train the Gradient Boosting model
    print("\nTraining Gradient Boosting model...")
    model = GradientBoostingClassifier(n_estimators=100, learning_rate=0.1, max_depth=3, random_state=42)
    model.fit(X_train_scaled, y_train)
    print("✅ Model training complete.")
    
    # 8. Evaluate the model
    print("\n--- Model Evaluation ---")
    y_pred = model.predict(X_test_scaled)
    print(classification_report(y_test, y_pred))
    
    # 9. Save the trained model and scaler
    model_dir = "server/src/ml/models"
    os.makedirs(model_dir, exist_ok=True)
    model_filename = os.path.join(model_dir, f"{symbol.replace('-EQ', '')}_{interval}_model.joblib")
    scaler_filename = os.path.join(model_dir, f"{symbol.replace('-EQ', '')}_{interval}_scaler.joblib")
    
    joblib.dump(model, model_filename)
    joblib.dump(scaler, scaler_filename)
    print(f"\n✅ Model saved to {model_filename}")
    print(f"✅ Scaler saved to {scaler_filename}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Train a classification model for trading signals.")
    parser.add_argument("--symbol", required=True, help="Trading symbol (e.g., 'SBIN-EQ').")
    parser.add_argument("--start", required=True, help="Start date (YYYY-MM-DD).")
    parser.add_argument("--end", required=True, help="End date (YYYY-MM-DD).")
    parser.add_argument("--interval", default="1_DAY", help="Candle interval (e.g., 5_MINUTE, 1_DAY).")
    parser.add_argument("--window", type=int, default=5, help="Prediction window (number of periods into the future).")
    
    args = parser.parse_args()
    
    train_model(
        symbol=args.symbol,
        start_date=args.start,
        end_date=args.end,
        interval=args.interval.upper(),
        prediction_window=args.window
    ) 