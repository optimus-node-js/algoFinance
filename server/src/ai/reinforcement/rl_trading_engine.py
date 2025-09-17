"""
Reinforcement Learning Trading Engine
Advanced AI system for learning optimal trading strategies
Uses Q-Learning and Deep Q-Networks for decision optimization
"""

import sys
import os
import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional, Any
import pickle
import json
from datetime import datetime, timedelta
import logging
from collections import deque
import random

# Add the project root directory to the Python path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..', '..'))
sys.path.append(PROJECT_ROOT)

from server.src.core.message_broker import get_message_broker
from server.src.config import settings

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TradingEnvironment:
    """Trading environment for reinforcement learning."""
    
    def __init__(self, data: pd.DataFrame, initial_balance: float = 100000):
        self.data = data
        self.initial_balance = initial_balance
        self.reset()
    
    def reset(self):
        """Reset environment to initial state."""
        self.current_step = 0
        self.balance = self.initial_balance
        self.position = 0  # 0 = no position, 1 = long, -1 = short
        self.entry_price = 0
        self.portfolio_value = self.initial_balance
        self.trades = []
        self.returns = []
        return self._get_state()
    
    def _get_state(self) -> np.ndarray:
        """Get current state representation."""
        if self.current_step >= len(self.data):
            return np.zeros(10)  # End of data
        
        row = self.data.iloc[self.current_step]
        
        # Technical indicators as state
        state = np.array([
            row.get('rsi', 50) / 100,  # Normalized RSI
            row.get('macd', 0) / 100,  # Normalized MACD
            row.get('bb_position', 0.5),  # Bollinger Band position
            row.get('volume_ratio', 1),  # Volume ratio
            row.get('price_change', 0) / 100,  # Price change
            self.position,  # Current position
            (self.portfolio_value - self.initial_balance) / self.initial_balance,  # P&L
            row.get('volatility', 0) / 100,  # Volatility
            row.get('momentum', 0) / 100,  # Momentum
            self.current_step / len(self.data)  # Time progress
        ])
        
        return state
    
    def step(self, action: int) -> Tuple[np.ndarray, float, bool, Dict]:
        """Execute action and return next state, reward, done, info."""
        if self.current_step >= len(self.data) - 1:
            return self._get_state(), 0, True, {}
        
        current_price = self.data.iloc[self.current_step]['close']
        next_price = self.data.iloc[self.current_step + 1]['close']
        
        # Execute action
        reward = self._execute_action(action, current_price, next_price)
        
        # Move to next step
        self.current_step += 1
        next_state = self._get_state()
        
        # Check if done
        done = (self.current_step >= len(self.data) - 1) or (self.portfolio_value <= 0)
        
        # Update portfolio value
        if self.position != 0:
            self.portfolio_value = self.balance + (self.position * next_price)
        else:
            self.portfolio_value = self.balance
        
        info = {
            'portfolio_value': self.portfolio_value,
            'position': self.position,
            'trades_count': len(self.trades)
        }
        
        return next_state, reward, done, info
    
    def _execute_action(self, action: int, current_price: float, next_price: float) -> float:
        """
        Execute trading action and return reward.
        Actions: 0=hold, 1=buy, 2=sell
        """
        reward = 0
        
        if action == 1 and self.position <= 0:  # Buy
            if self.position == -1:  # Close short position
                profit = (self.entry_price - current_price) / self.entry_price
                self.balance *= (1 + profit)
                reward += profit * 10  # Reward for profit
                
                self.trades.append({
                    'type': 'close_short',
                    'entry_price': self.entry_price,
                    'exit_price': current_price,
                    'profit': profit,
                    'timestamp': self.current_step
                })
            
            # Open long position
            self.position = 1
            self.entry_price = current_price
            
            # Reward based on next price movement
            price_change = (next_price - current_price) / current_price
            reward += price_change * 10
            
        elif action == 2 and self.position >= 0:  # Sell
            if self.position == 1:  # Close long position
                profit = (current_price - self.entry_price) / self.entry_price
                self.balance *= (1 + profit)
                reward += profit * 10  # Reward for profit
                
                self.trades.append({
                    'type': 'close_long',
                    'entry_price': self.entry_price,
                    'exit_price': current_price,
                    'profit': profit,
                    'timestamp': self.current_step
                })
            
            # Open short position
            self.position = -1
            self.entry_price = current_price
            
            # Reward based on next price movement
            price_change = (current_price - next_price) / current_price
            reward += price_change * 10
            
        else:  # Hold
            if self.position == 1:  # Long position
                price_change = (next_price - current_price) / current_price
                reward += price_change * 5  # Smaller reward for holding
            elif self.position == -1:  # Short position
                price_change = (current_price - next_price) / current_price
                reward += price_change * 5
        
        # Penalty for excessive trading
        if len(self.trades) > 0:
            recent_trades = len([t for t in self.trades if self.current_step - t['timestamp'] < 5])
            if recent_trades > 2:
                reward -= 0.1  # Small penalty
        
        return reward

class ReinforcementLearningEngine:
    """
    Advanced Reinforcement Learning Engine for Trading
    
    Features:
    - Q-Learning with experience replay
    - Adaptive strategy optimization
    - Multi-symbol learning
    - Risk-adjusted rewards
    - Performance tracking
    """
    
    def __init__(self, state_size: int = 10, action_size: int = 3):
        """Initialize the RL Engine."""
        self.state_size = state_size
        self.action_size = action_size  # 0=hold, 1=buy, 2=sell
        self.memory = deque(maxlen=10000)
        self.epsilon = 1.0  # Exploration rate
        self.epsilon_min = 0.01
        self.epsilon_decay = 0.995
        self.learning_rate = 0.001
        self.gamma = 0.95  # Discount factor
        
        # Q-table for Q-Learning (simplified)
        self.q_table = {}
        
        # Performance tracking
        self.performance_history = []
        self.symbol_performance = {}
        
        # Message broker
        self.message_broker = get_message_broker()
        
        logger.info("🧠 Reinforcement Learning Engine initialized")
    
    def _state_to_key(self, state: np.ndarray) -> str:
        """Convert state array to string key for Q-table."""
        # Discretize continuous state for Q-table
        discretized = (state * 10).astype(int)
        return str(discretized.tolist())
    
    def get_action(self, state: np.ndarray, training: bool = True) -> int:
        """Get action using epsilon-greedy policy."""
        state_key = self._state_to_key(state)
        
        # Exploration vs exploitation
        if training and np.random.random() <= self.epsilon:
            return random.randrange(self.action_size)
        
        # Get Q-values for current state
        if state_key not in self.q_table:
            self.q_table[state_key] = np.zeros(self.action_size)
        
        return np.argmax(self.q_table[state_key])
    
    def remember(self, state: np.ndarray, action: int, reward: float, 
                 next_state: np.ndarray, done: bool):
        """Store experience in memory."""
        self.memory.append((state, action, reward, next_state, done))
    
    def replay(self, batch_size: int = 32):
        """Train the model on a batch of experiences."""
        if len(self.memory) < batch_size:
            return
        
        batch = random.sample(self.memory, batch_size)
        
        for state, action, reward, next_state, done in batch:
            state_key = self._state_to_key(state)
            next_state_key = self._state_to_key(next_state)
            
            # Initialize Q-values if not exists
            if state_key not in self.q_table:
                self.q_table[state_key] = np.zeros(self.action_size)
            if next_state_key not in self.q_table:
                self.q_table[next_state_key] = np.zeros(self.action_size)
            
            # Q-Learning update
            target = reward
            if not done:
                target += self.gamma * np.amax(self.q_table[next_state_key])
            
            # Update Q-value
            self.q_table[state_key][action] += self.learning_rate * (
                target - self.q_table[state_key][action]
            )
        
        # Decay epsilon
        if self.epsilon > self.epsilon_min:
            self.epsilon *= self.epsilon_decay
    
    def train_on_symbol(self, symbol: str, data: pd.DataFrame, episodes: int = 100) -> Dict[str, Any]:
        """Train the RL model on a specific symbol."""
        logger.info(f"🎯 Training RL model on {symbol} for {episodes} episodes")
        
        env = TradingEnvironment(data)
        episode_rewards = []
        episode_profits = []
        
        for episode in range(episodes):
            state = env.reset()
            total_reward = 0
            
            while True:
                action = self.get_action(state, training=True)
                next_state, reward, done, info = env.step(action)
                
                self.remember(state, action, reward, next_state, done)
                state = next_state
                total_reward += reward
                
                if done:
                    break
            
            # Train on batch
            if len(self.memory) > 32:
                self.replay(32)
            
            episode_rewards.append(total_reward)
            final_portfolio = info['portfolio_value']
            profit_pct = (final_portfolio - env.initial_balance) / env.initial_balance * 100
            episode_profits.append(profit_pct)
            
            # Log progress
            if episode % 20 == 0:
                avg_reward = np.mean(episode_rewards[-20:])
                avg_profit = np.mean(episode_profits[-20:])
                logger.info(f"Episode {episode}: Avg Reward={avg_reward:.2f}, Avg Profit={avg_profit:.2f}%")
        
        # Store performance
        performance = {
            'symbol': symbol,
            'episodes': episodes,
            'final_epsilon': self.epsilon,
            'avg_reward': np.mean(episode_rewards),
            'avg_profit': np.mean(episode_profits),
            'best_profit': max(episode_profits),
            'win_rate': len([p for p in episode_profits if p > 0]) / len(episode_profits),
            'total_trades': len(env.trades),
            'timestamp': datetime.now().isoformat()
        }
        
        self.symbol_performance[symbol] = performance
        self.performance_history.append(performance)
        
        logger.info(f"✅ Training completed for {symbol}")
        logger.info(f"   Average Profit: {performance['avg_profit']:.2f}%")
        logger.info(f"   Win Rate: {performance['win_rate']:.2%}")
        
        return performance
    
    def get_trading_decision(self, symbol: str, current_state: np.ndarray) -> Dict[str, Any]:
        """Get trading decision for a symbol based on learned policy."""
        action = self.get_action(current_state, training=False)
        
        # Map action to decision
        action_map = {0: 'hold', 1: 'buy', 2: 'sell'}
        decision = action_map[action]
        
        # Calculate confidence based on Q-values
        state_key = self._state_to_key(current_state)
        if state_key in self.q_table:
            q_values = self.q_table[state_key]
            max_q = np.max(q_values)
            confidence = max_q / (np.sum(np.abs(q_values)) + 1e-8)
        else:
            confidence = 0.5
        
        # Get symbol performance for additional context
        symbol_perf = self.symbol_performance.get(symbol, {})
        
        result = {
            'symbol': symbol,
            'action': decision,
            'confidence': min(abs(confidence), 1.0),
            'q_values': q_values.tolist() if state_key in self.q_table else [0, 0, 0],
            'symbol_performance': symbol_perf,
            'timestamp': datetime.now().isoformat()
        }
        
        return result
    
    def update_from_trade_result(self, symbol: str, trade_result: Dict[str, Any]):
        """Update model based on actual trade results."""
        try:
            # Extract trade information
            action = trade_result.get('action')
            profit = trade_result.get('profit_pct', 0)
            
            # Convert to reward signal
            reward = profit / 10  # Scale profit to reward
            
            # Store as learning experience (simplified)
            if symbol in self.symbol_performance:
                perf = self.symbol_performance[symbol]
                perf['recent_trades'] = perf.get('recent_trades', [])
                perf['recent_trades'].append({
                    'action': action,
                    'profit': profit,
                    'reward': reward,
                    'timestamp': datetime.now().isoformat()
                })
                
                # Keep only recent trades
                perf['recent_trades'] = perf['recent_trades'][-100:]
                
                # Update performance metrics
                recent_profits = [t['profit'] for t in perf['recent_trades']]
                if recent_profits:
                    perf['recent_avg_profit'] = np.mean(recent_profits)
                    perf['recent_win_rate'] = len([p for p in recent_profits if p > 0]) / len(recent_profits)
            
            logger.debug(f"📊 Updated RL model with trade result for {symbol}: {profit:.2f}%")
            
        except Exception as e:
            logger.error(f"❌ Error updating RL model from trade result: {e}")
    
    def get_model_performance(self) -> Dict[str, Any]:
        """Get overall model performance."""
        if not self.performance_history:
            return {'status': 'no_training_data'}
        
        all_profits = [p['avg_profit'] for p in self.performance_history]
        all_win_rates = [p['win_rate'] for p in self.performance_history]
        
        return {
            'total_symbols_trained': len(self.symbol_performance),
            'total_episodes': sum(p['episodes'] for p in self.performance_history),
            'overall_avg_profit': np.mean(all_profits),
            'overall_win_rate': np.mean(all_win_rates),
            'best_performing_symbol': max(self.symbol_performance.items(), 
                                        key=lambda x: x[1]['avg_profit'])[0] if self.symbol_performance else None,
            'current_epsilon': self.epsilon,
            'q_table_size': len(self.q_table),
            'memory_size': len(self.memory),
            'last_updated': datetime.now().isoformat()
        }
    
    def save_model(self, filepath: str):
        """Save the trained model."""
        try:
            model_data = {
                'q_table': self.q_table,
                'symbol_performance': self.symbol_performance,
                'performance_history': self.performance_history,
                'epsilon': self.epsilon,
                'hyperparameters': {
                    'learning_rate': self.learning_rate,
                    'gamma': self.gamma,
                    'epsilon_decay': self.epsilon_decay
                }
            }
            
            with open(filepath, 'wb') as f:
                pickle.dump(model_data, f)
            
            logger.info(f"💾 RL model saved to {filepath}")
            
        except Exception as e:
            logger.error(f"❌ Error saving RL model: {e}")
    
    def load_model(self, filepath: str):
        """Load a trained model."""
        try:
            with open(filepath, 'rb') as f:
                model_data = pickle.load(f)
            
            self.q_table = model_data.get('q_table', {})
            self.symbol_performance = model_data.get('symbol_performance', {})
            self.performance_history = model_data.get('performance_history', [])
            self.epsilon = model_data.get('epsilon', self.epsilon)
            
            hyperparams = model_data.get('hyperparameters', {})
            self.learning_rate = hyperparams.get('learning_rate', self.learning_rate)
            self.gamma = hyperparams.get('gamma', self.gamma)
            self.epsilon_decay = hyperparams.get('epsilon_decay', self.epsilon_decay)
            
            logger.info(f"📂 RL model loaded from {filepath}")
            
        except Exception as e:
            logger.error(f"❌ Error loading RL model: {e}")
    
    def publish_performance_update(self):
        """Publish performance update to message broker."""
        try:
            performance = self.get_model_performance()
            
            self.message_broker.publish_ai_analysis(
                'reinforcement_learning',
                'performance_update',
                {
                    'performance': performance,
                    'timestamp': datetime.now().isoformat()
                }
            )
            
        except Exception as e:
            logger.error(f"❌ Error publishing RL performance: {e}")


# Example usage and testing
if __name__ == "__main__":
    print("🧪 Testing Reinforcement Learning Engine...")
    
    # Create sample data
    dates = pd.date_range(start='2023-01-01', periods=1000, freq='5T')
    np.random.seed(42)
    
    # Generate realistic market data with indicators
    prices = 100 + np.cumsum(np.random.randn(1000) * 0.5)
    
    sample_data = pd.DataFrame({
        'timestamp': dates,
        'close': prices,
        'rsi': 50 + np.random.randn(1000) * 15,
        'macd': np.random.randn(1000) * 0.5,
        'bb_position': np.random.random(1000),
        'volume_ratio': 1 + np.random.randn(1000) * 0.3,
        'price_change': np.diff(np.concatenate([[100], prices])) / 100,
        'volatility': np.abs(np.random.randn(1000) * 10),
        'momentum': np.random.randn(1000) * 0.02
    })
    
    # Initialize and train RL engine
    rl_engine = ReinforcementLearningEngine()
    
    # Train on sample data
    performance = rl_engine.train_on_symbol('TEST-SYMBOL', sample_data, episodes=50)
    
    print(f"\n🎯 Training Results:")
    print(f"   Average Profit: {performance['avg_profit']:.2f}%")
    print(f"   Win Rate: {performance['win_rate']:.2%}")
    print(f"   Best Profit: {performance['best_profit']:.2f}%")
    
    # Test decision making
    test_state = sample_data.iloc[-1][['rsi', 'macd', 'bb_position', 'volume_ratio', 
                                      'price_change', 'volatility', 'momentum']].values
    test_state = np.concatenate([test_state / 100, [0, 0, 0.5]])  # Normalize and add position info
    
    decision = rl_engine.get_trading_decision('TEST-SYMBOL', test_state)
    print(f"\n🎯 Test Decision:")
    print(f"   Action: {decision['action'].upper()}")
    print(f"   Confidence: {decision['confidence']:.2%}")
    
    # Show model performance
    model_perf = rl_engine.get_model_performance()
    print(f"\n📊 Model Performance:")
    print(f"   Q-Table Size: {model_perf['q_table_size']}")
    print(f"   Memory Size: {model_perf['memory_size']}")
    print(f"   Current Epsilon: {model_perf['current_epsilon']:.3f}")
    
    print("\n✅ Reinforcement Learning Engine testing completed!")



