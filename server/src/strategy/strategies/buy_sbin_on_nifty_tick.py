from strategy.base_strategy import BaseStrategy

class BuySbinOnNiftyTick(BaseStrategy):
    """
    A simple example strategy that buys one share of SBIN-EQ
    whenever it detects a tick from the NIFTY 50 index.
    """
    def execute(self, market_data: dict):
        if market_data.get('token') == '26000':
            print("   💡 [Strategy: BuySbinOnNiftyTick] NIFTY 50 tick detected. Firing BUY signal.")
            
            if self.publish_order:
                order_details = {
                    "variety": "NORMAL",
                    "tradingsymbol": "SBIN-EQ",
                    "transactiontype": "BUY",
                    "exchange": "NSE",
                    "ordertype": "MARKET",
                    "producttype": "INTRADAY",
                    "duration": "DAY",
                    "quantity": 1
                }
                self.publish_order(order_details)
            else:
                print("   ❌ [Strategy: BuySbinOnNiftyTick] publish_order method not set.") 