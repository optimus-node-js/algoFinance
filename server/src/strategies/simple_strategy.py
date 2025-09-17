import sys
import os
import time

# Add the src directory to the Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from order_management.oms import OrderManager
from api_gateway.utils import find_instrument_token

class SimpleStrategy:
    def __init__(self, oms: OrderManager):
        self.oms = oms
        print("✅ SimpleStrategy initialized.")

    def run(self):
        """
        Runs the strategy logic. For now, it just generates one predefined signal.
        """
        print("▶️ Running SimpleStrategy...")
        
        # In a real system, this signal would come from data analysis.
        # Here, we are hardcoding it for testing the pipeline.
        tradingsymbol = "RELIANCE-EQ"
        
        print(f"Strategy decided to BUY {tradingsymbol}.")

        token = find_instrument_token(self.oms.smart_connect, tradingsymbol)
        
        if token and self.oms.smart_connect:
            print(f"Found token {token}. Handing off to OMS to place order.")
            self.oms.place_order(
                variety="NORMAL",
                tradingsymbol=tradingsymbol,
                symboltoken=token,
                transactiontype="BUY",
                exchange="NSE",
                ordertype="MARKET",
                producttype="INTRADAY",
                duration="DAY",
                quantity=1
            )
        else:
            print(f"❌ Could not execute strategy for {tradingsymbol}. Token or OMS not available.")

if __name__ == '__main__':
    # Initialize the Order Manager
    oms = OrderManager()
    
    # Check if OMS initialized successfully before proceeding
    if oms.initialize():
        # Create the strategy instance and pass it the OMS
        strategy = SimpleStrategy(oms)
        
        # Run the strategy
        strategy.run()
    else:
        print("❌ Strategy could not run because OMS failed to initialize.") 