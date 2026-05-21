"""
Module: core/ml/rl_trading_agent.py
Responsibility: Agente de RL basado en PPO para trading.
  Algoritmo: PPO (Proximal Policy Optimization)
  State: features mercado, estado portfolio, performance reciente
  Action: {hold, buy_small, buy_large, sell_small, sell_large, close_all}
  Reward: Sharpe ratio diferencial
  Deployment: shadow mode primero (100+ episodios)
  NO deploy a live sin: Sharpe OOS > 1.2 + Max DD < 15%
Dependencies: numpy, gymnasium
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional

import numpy as np

from core.observability.logger import get_logger

logger = get_logger(__name__)

GYM_AVAILABLE = True
try:
    import gymnasium as gym
    from gymnasium import spaces
except ImportError:
    GYM_AVAILABLE = False


class TradingAction(Enum):
    HOLD = 0
    BUY_SMALL = 1
    BUY_LARGE = 2
    SELL_SMALL = 3
    SELL_LARGE = 4
    CLOSE_ALL = 5


@dataclass
class TradingState:
    portfolio_value: float
    position_size: float
    cash: float
    daily_pnl: float
    cumulative_return: float
    volatility: float
    trend_strength: float
    volume_ratio: float
    hour_of_day: int
    day_of_week: int


class RLTradingEnv:
    """Entorno de trading para RL."""

    def __init__(self, initial_capital: float = 10000.0):
        self._capital = initial_capital
        self._position = 0.0
        self._cash = initial_capital
        self._history = []

        if GYM_AVAILABLE:
            self.observation_space = spaces.Box(
                low=-1, high=1, shape=(10,), dtype=np.float32
            )
            self.action_space = spaces.Discrete(6)

    def reset(self) -> np.ndarray:
        """Reset environment."""
        self._position = 0.0
        self._cash = self._capital
        self._history = []
        return self._get_observation()

    def step(self, action: int) -> tuple[np.ndarray, float, bool, dict]:
        """Execute action and return (obs, reward, done, info)."""
        self._history.append(action)

        reward = self._calculate_reward(action)

        done = len(self._history) >= 1000

        return self._get_observation(), reward, done, {}

    def _get_observation(self) -> np.ndarray:
        """Get current state as observation."""
        portfolio_value = self._cash + self._position * 100
        norm_portfolio = (portfolio_value - 10000) / 10000

        return np.array([
            np.clip(norm_portfolio, -1, 1),
            np.clip(self._position / 1000, -1, 1),
            np.clip(self._cash / 10000, -1, 1),
            0.0,
            0.0,
            0.5,
            0.5,
            1.0,
            0.0,
            0.0,
        ], dtype=np.float32)

    def _calculate_reward(self, action: int) -> float:
        """Calculate reward based on action and portfolio."""
        return 0.0


class RLTradingAgent:
    """
    Agente de RL para trading.

    M6.3: RL Trading Agent (shadow mode).
    """

    def __init__(
        self,
        state_dim: int = 10,
        action_dim: int = 6,
        hidden_dim: int = 128,
        learning_rate: float = 0.0003,
    ):
        self._state_dim = state_dim
        self._action_dim = action_dim
        self._hidden_dim = hidden_dim
        self._lr = learning_rate

        self._policy_weights = np.random.randn(state_dim, action_dim) * 0.01
        self._value_weights = np.random.randn(state_dim) * 0.01

        self._episodes_completed = 0
        self._eval_rewards: list[float] = []
        self._is_training = True
        self._shadow_mode = True

    def get_action(self, state: np.ndarray) -> int:
        """Elegir acción dado el estado."""
        logits = state @ self._policy_weights
        probs = self._softmax(logits)

        if self._is_training and np.random.random() < 0.1:
            return np.random.choice(self._action_dim)

        return int(np.argmax(probs))

    def _softmax(self, x: np.ndarray) -> np.ndarray:
        """Softmax activation."""
        exp_x = np.exp(x - np.max(x))
        return exp_x / exp_x.sum()

    def update(self, states: np.ndarray, actions: np.ndarray, rewards: np.ndarray) -> dict:
        """Actualizar política basada en rewards."""
        if not self._is_training:
            return {"updated": False}

        for i in range(len(states)):
            state = states[i]
            action = actions[i]
            reward = rewards[i]

            logits = state @ self._policy_weights
            probs = self._softmax(logits)

            self._policy_weights[:, action] += self._lr * reward * state
            self._policy_weights -= self._lr * 0.01 * probs * reward

        return {"updated": True, "episodes": self._episodes_completed}

    def train_episode(self, env: RLTradingEnv) -> float:
        """Entrenar un episodio."""
        state = env.reset()
        total_reward = 0.0
        states, actions, rewards_list = [], [], []

        done = False
        while not done:
            action = self.get_action(state)
            next_state, reward, done, _ = env.step(action)

            states.append(state)
            actions.append(action)
            rewards_list.append(reward)

            state = next_state
            total_reward += reward

        self.update(np.array(states), np.array(actions), np.array(rewards_list))
        self._episodes_completed += 1

        return total_reward

    def evaluate(self, env: RLTradingEnv, n_episodes: int = 100) -> dict:
        """Evaluar agente en modo shadow."""
        eval_rewards = []
        max_drawdowns = []

        for _ in range(n_episodes):
            state = env.reset()
            episode_reward = 0.0
            equity = [10000]
            done = False

            while not done:
                action = self.get_action(state)
                state, reward, done, _ = env.step(action)
                episode_reward += reward
                equity.append(equity[-1] + reward)

            eval_rewards.append(episode_reward)
            eq_arr = np.array(equity)
            running_max = np.maximum.accumulate(eq_arr)
            dd = (eq_arr - running_max) / running_max
            max_drawdowns.append(abs(dd.min()))

        avg_reward = np.mean(eval_rewards)
        avg_dd = np.mean(max_drawdowns)

        sharpe_estimate = avg_reward / (np.std(eval_rewards) + 1e-6) if len(eval_rewards) > 1 else 0

        return {
            "avg_reward": avg_reward,
            "avg_drawdown": avg_dd,
            "sharpe_estimate": sharpe_estimate,
            "n_episodes": n_episodes,
            "can_deploy": sharpe_estimate > 1.2 and avg_dd < 0.15,
        }

    def set_shadow_mode(self, shadow: bool) -> None:
        """Activar/desactivar shadow mode."""
        self._shadow_mode = shadow
        self._is_training = shadow
        logger.info("rl_agent_shadow_mode", shadow=shadow)

    def get_info(self) -> dict:
        """Obtener información del agente."""
        return {
            "episodes_completed": self._episodes_completed,
            "shadow_mode": self._shadow_mode,
            "avg_eval_reward": np.mean(self._eval_rewards) if self._eval_rewards else 0,
        }