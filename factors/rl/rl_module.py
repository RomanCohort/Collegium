"""
反思智能体 + RL强化学习环境

整合:
1. ReflectionAgent: 定期调用DeepSeek进行策略反思
2. TradingEnv: Stable-Baselines3兼容的Gym环境
3. RLReflectiveTrainer: PPO训练反思策略
"""

import os
import json
import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, timedelta
from pathlib import Path
from collections import deque
import torch

from .deepseek_client import DeepSeekClient
from ...utils import log


class ReflectionAgent:
    """
    反思智能体

    核心功能:
    - 定期调用DeepSeek API进行策略反思
    - 维护反思历史和短期记忆
    - 信号置信度评估
    - 权重调整因子生成
    """

    def __init__(self, deepseek_client: DeepSeekClient,
                 reflection_interval: int = 5,
                 cache_ttl_hours: int = 6):
        """
        Args:
            deepseek_client: DeepSeek API客户端
            reflection_interval: 反思间隔(调仓次数)
            cache_ttl_hours: 缓存有效期(小时)
        """
        self.client = deepseek_client
        self.reflection_interval = reflection_interval
        self.cache_ttl = timedelta(hours=cache_ttl_hours)

        # 反思历史
        self.history: List[Dict] = []

        # 短期记忆
        self.short_term_memory: deque = deque(maxlen=100)

        # 反思计数
        self.reflection_count = 0

        # 统计
        self.stats = {
            'total_reflections': 0,
            'avg_confidence': 0.5,
            'avg_adjustment': 1.0,
            'risk_flag_count': 0,
        }

        log.info(f"反思智能体初始化完成，间隔: 每{reflection_interval}次调仓")

    def reflect(self, context: Dict) -> Dict:
        """
        执行反思

        Args:
            context: 市场上下文

        Returns:
            反思结果
        """
        self.reflection_count += 1

        # 检查缓存
        cache_key = self._make_cache_key(context)
        cached = self._get_from_cache(cache_key)
        if cached:
            log.debug(f"使用缓存的反思结果 (key={cache_key[:20]}...)")
            return cached

        # 调用DeepSeek API
        log.info(f"执行反思 (第{self.reflection_count}次)...")
        result = self.client._single_reflection(context)

        # 更新统计
        self._update_stats(result)

        # 存储到历史
        self.history.append({
            'timestamp': datetime.now(),
            'context': context,
            'result': result,
        })

        # 存储到短期记忆
        self.short_term_memory.append({
            'context': context,
            'result': result,
        })

        # 缓存
        self._save_to_cache(cache_key, result)

        return result

    def should_reflect(self) -> bool:
        """判断是否需要反思"""
        return self.reflection_count % self.reflection_interval == 0

    def get_reflection_summary(self) -> str:
        """获取反思摘要"""
        recent = self.history[-5:] if len(self.history) > 5 else self.history

        if not recent:
            return "暂无反思记录"

        avg_conf = np.mean([r['result'].get('confidence', 0) for r in recent])
        avg_adj = np.mean([r['result'].get('weight_adjustment', 1.0) for r in recent])
        recent_flags = []
        for r in recent:
            recent_flags.extend(r['result'].get('risk_flags', []))

        return (
            f"近期反思({len(recent)}次):\n"
            f"  - 平均置信度: {avg_conf:.2f}\n"
            f"  - 平均权重调整: {avg_adj:.2f}\n"
            f"  - 最近风险标记: {recent_flags[:3] if recent_flags else '无'}"
        )

    def get_trend(self, metric: str = 'confidence') -> str:
        """获取指标趋势"""
        if len(self.history) < 2:
            return "数据不足"

        values = [r['result'].get(metric, 0) for r in self.history[-10:]]
        if not values:
            return "数据不足"

        recent = np.mean(values[-3:])
        older = np.mean(values[:-3]) if len(values) > 3 else recent

        if recent > older * 1.1:
            return "上升"
        elif recent < older * 0.9:
            return "下降"
        return "平稳"

    def _make_cache_key(self, context: Dict) -> str:
        """生成缓存键"""
        key_parts = [
            str(context.get('date', '')),
            str(sorted(context.get('codes', [])[:5])),
            str(context.get('trend', ''))[:10],
        ]
        return '_'.join(key_parts)

    def _get_from_cache(self, cache_key: str) -> Optional[Dict]:
        """从缓存获取"""
        cache_dir = Path("cache/reflection")
        cache_dir.mkdir(parents=True, exist_ok=True)
        cache_file = cache_dir / f"{hash(cache_key)}.json"

        if not cache_file.exists():
            return None

        try:
            with open(cache_file, 'r') as f:
                cached = json.load(f)
            if datetime.now() - datetime.fromisoformat(cached['timestamp']) < self.cache_ttl:
                return cached['result']
        except Exception:
            pass
        return None

    def _save_to_cache(self, cache_key: str, result: Dict):
        """保存到缓存"""
        cache_dir = Path("cache/reflection")
        cache_dir.mkdir(parents=True, exist_ok=True)
        cache_file = cache_dir / f"{hash(cache_key)}.json"

        try:
            with open(cache_file, 'w') as f:
                json.dump({
                    'timestamp': datetime.now().isoformat(),
                    'result': result,
                }, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def _update_stats(self, result: Dict):
        """更新统计信息"""
        n = self.stats['total_reflections']
        old_conf = self.stats['avg_confidence']
        old_adj = self.stats['avg_adjustment']

        self.stats['total_reflections'] = n + 1
        self.stats['avg_confidence'] = (old_conf * n + result.get('confidence', 0.5)) / (n + 1)
        self.stats['avg_adjustment'] = (old_adj * n + result.get('weight_adjustment', 1.0)) / (n + 1)
        self.stats['risk_flag_count'] += len(result.get('risk_flags', []))


class TradingEnv:
    """
    交易环境 (Gym兼容格式，供Stable-Baselines3使用)

    Observation:
        - CTM/Mamba输出特征
        - 市场状态特征
        - 历史收益
        - 持仓状态

    Action:
        - 连续: 权重调整因子 (0.5 ~ 1.5)

    Reward:
        - 风险调整收益: Sharpe比率
        - 惩罚: 最大回撤、换手率
    """

    def __init__(self, price_data: pd.DataFrame,
                 benchmark_data: pd.DataFrame,
                 initial_cash: float = 1000000,
                 lookback_window: int = 60):
        """
        Args:
            price_data: 行情数据
            benchmark_data: 基准数据
            initial_cash: 初始资金
            lookback_window: 回看窗口
        """
        self.price_data = price_data
        self.benchmark_data = benchmark_data
        self.initial_cash = initial_cash
        self.lookback_window = lookback_window

        # 环境状态
        self.current_idx = lookback_window
        self.dates = sorted(price_data['date'].unique())
        self.n_steps = len(self.dates) - lookback_window

        # 组合状态
        self.cash = initial_cash
        self.positions: Dict[str, int] = {}
        self.nav_history: List[float] = []

        # 特征维度
        self.obs_dim = 64

        # 动作空间
        self.action_space_low = 0.5
        self.action_space_high = 1.5

        log.info(f"交易环境初始化完成: {self.n_steps}步, 观测维度: {self.obs_dim}")

    def reset(self) -> np.ndarray:
        """重置环境"""
        self.current_idx = self.lookback_window
        self.cash = self.initial_cash
        self.positions = {}
        self.nav_history = [1.0]

        return self._get_observation()

    def step(self, action: np.ndarray) -> Tuple[np.ndarray, float, bool, Dict]:
        """
        执行一步

        Args:
            action: 权重调整因子 (连续值)

        Returns:
            observation, reward, done, info
        """
        adjustment = float(action[0]) if isinstance(action, np.ndarray) else float(action)
        adjustment = np.clip(adjustment, self.action_space_low, self.action_space_high)

        current_date = self.dates[self.current_idx]

        # 更新持仓
        self._update_portfolio(current_date, adjustment)

        # 计算收益
        nav_before = self.nav_history[-1]
        self._update_nav(current_date)
        nav_after = self.nav_history[-1]

        reward = nav_after - nav_before

        # 更新索引
        self.current_idx += 1
        done = self.current_idx >= len(self.dates) - 1

        obs = self._get_observation()
        info = {'date': current_date, 'nav': nav_after}

        return obs, reward, done, info

    def _get_observation(self) -> np.ndarray:
        """获取观测"""
        # 简化版: 使用最近N日的收益特征
        recent_dates = self.dates[max(0, self.current_idx - self.lookback_window):self.current_idx]

        if len(recent_dates) < self.lookback_window:
            padding = self.lookback_window - len(recent_dates)
            obs = np.zeros(padding)
        else:
            obs = np.array([])

        # 计算最近收益
        returns = []
        for i in range(min(20, len(recent_dates))):
            date_idx = self.current_idx - i
            if date_idx > 0:
                day_data = self.price_data[self.price_data['date'] == self.dates[date_idx]]
                if not day_data.empty:
                    returns.append(day_data['close'].pct_change().mean())
                else:
                    returns.append(0)
            else:
                returns.append(0)

        returns = np.array(returns[::-1])  # 时间正序
        if len(returns) < 20:
            returns = np.pad(returns, (20 - len(returns), 0))

        obs = returns

        # 添加持仓状态
        position_value = self.cash / self.initial_cash
        obs = np.concatenate([obs, [position_value]])

        # padding到固定维度
        if len(obs) < self.obs_dim:
            obs = np.pad(obs, (0, self.obs_dim - len(obs)))
        else:
            obs = obs[:self.obs_dim]

        return obs.astype(np.float32)

    def _update_portfolio(self, date: str, adjustment: float):
        """更新组合"""
        day_data = self.price_data[self.price_data['date'] == date]

        # 简化: 不做实际交易，只调整资金使用率
        self.cash = self.initial_cash * adjustment

    def _update_nav(self, date: str):
        """更新净值"""
        self.nav_history.append(self.cash / self.initial_cash)

    @property
    def observation_space(self):
        """观测空间"""
        from gym.spaces import Box
        return Box(low=-10, high=10, shape=(self.obs_dim,), dtype=np.float32)

    @property
    def action_space(self):
        """动作空间"""
        from gym.spaces import Box
        return Box(low=self.action_space_low, high=self.action_space_high, shape=(1,), dtype=np.float32)


class RLReflectiveTrainer:
    """
    RL反思策略训练器

    使用Stable-Baselines3的PPO算法训练权重调整策略
    """

    def __init__(self, env: TradingEnv,
                 model_dir: str = "models/rl",
                 device: str = "cpu"):
        """
        Args:
            env: 交易环境
            model_dir: 模型保存目录
            device: 设备 (cpu/cuda)
        """
        self.env = env
        self.model_dir = Path(model_dir)
        self.model_dir.mkdir(parents=True, exist_ok=True)
        self.device = device
        self.model = None

        log.info(f"RL训练器初始化完成，模型目录: {self.model_dir}")

    def train(self, total_timesteps: int = 50000,
              learning_rate: float = 3e-4,
              n_steps: int = 512,
              batch_size: int = 64,
              n_epochs: int = 10) -> Any:
        """
        训练PPO模型

        Args:
            total_timesteps: 总训练步数
            learning_rate: 学习率
            n_steps: 每次更新收集的步数
            batch_size: 批大小
            n_epochs: 每次更新的训练轮数

        Returns:
            训练好的模型
        """
        try:
            from stable_baselines3 import PPO
            from stable_baselines3.common.vec_env import DummyVecEnv
        except ImportError:
            log.error("请安装stable-baselines3: pip install stable-baselines3")
            return None

        # 创建向量化环境
        vec_env = DummyVecEnv([lambda: self.env])

        # PPO配置
        model = PPO(
            "MlpPolicy",
            vec_env,
            learning_rate=learning_rate,
            n_steps=n_steps,
            batch_size=batch_size,
            n_epochs=n_epochs,
            gamma=0.99,
            gae_lambda=0.95,
            clip_range=0.2,
            ent_coef=0.01,
            verbose=1,
            device=self.device,
        )

        log.info(f"开始训练 PPO: {total_timesteps} timesteps...")

        model.learn(
            total_timesteps=total_timesteps,
            progress_bar=True,
            callback=self._make_callback(),
        )

        # 保存模型
        model_path = self.model_dir / "ppo_reflective"
        model.save(model_path)
        log.info(f"模型已保存: {model_path}")

        self.model = model
        return model

    def _make_callback(self):
        """创建回调函数"""
        try:
            from stable_baselines3.common.callbacks import BaseCallback
        except ImportError:
            return None

        class LoggingCallback(BaseCallback):
            def __init__(self, verbose=0):
                super().__init__(verbose)
                self.episode_count = 0

            def _on_step(self) -> bool:
                if self.n_calls % 1000 == 0:
                    log.info(f"训练进度: {self.n_calls}/{self.locals['total_timesteps']}")
                return True

        return LoggingCallback()

    def evaluate(self, n_episodes: int = 5) -> Dict:
        """
        评估模型

        Args:
            n_episodes: 评估回合数

        Returns:
            评估结果
        """
        if self.model is None:
            log.warning("模型未加载，请先训练或加载模型")
            return {}

        eval_env = TradingEnv(
            self.env.price_data,
            self.env.benchmark_data,
            self.env.initial_cash,
            self.env.lookback_window,
        )

        episode_rewards = []
        episode_navs = []

        for ep in range(n_episodes):
            obs = eval_env.reset()
            done = False
            total_reward = 0
            navs = []

            while not done:
                action, _ = self.model.predict(obs, deterministic=True)
                obs, reward, done, info = eval_env.step(action)
                total_reward += reward
                navs.append(info.get('nav', 0))

            episode_rewards.append(total_reward)
            episode_navs.append(navs)

        results = {
            'mean_reward': np.mean(episode_rewards),
            'std_reward': np.std(episode_rewards),
            'mean_final_nav': np.mean([n[-1] if n else 0 for n in episode_navs]),
            'max_nav': np.max([n[-1] if n else 0 for n in episode_navs]),
        }

        log.info(f"评估结果: mean_reward={results['mean_reward']:.4f}, "
                 f"mean_final_nav={results['mean_final_nav']:.4f}")

        return results

    def load(self, model_name: str = "ppo_reflective"):
        """加载模型"""
        try:
            from stable_baselines3 import PPO
        except ImportError:
            return None

        model_path = self.model_dir / model_name
        if not model_path.exists():
            log.warning(f"模型不存在: {model_path}")
            return None

        self.model = PPO.load(model_path, device=self.device)
        log.info(f"模型已加载: {model_path}")
        return self.model
