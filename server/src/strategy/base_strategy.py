from abc import ABC, abstractmethod
import pandas as pd

class BaseStrategy(ABC):
    """
    Abstract base class for all trading strategies.
    
    Each strategy must implement the 'execute' method.
    The 'publish_order' method will be provided by the StrategyService
    when the strategy is loaded.
    """
    def __init__(self):
        self.publish_order = None

    @abstractmethod
    def execute(self, market_data: dict):
        """
        The core logic of the strategy. This method is called for every
        incoming market data tick.

        :param market_data: A dictionary representing the market data tick.
        """
        pass 

    @abstractmethod
    def generate_signals(self, historical_data: pd.DataFrame) -> tuple:
        """
        Generates trading signals for backtesting based on historical data.

        :param historical_data: A pandas DataFrame with OHLCV data.
        :return: A tuple containing two pandas Series: (entries, exits).
                 Both Series should be boolean arrays indicating entry/exit points.
        """
        pass 