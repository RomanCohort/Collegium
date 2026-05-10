"""
均值回归策略
"""
import pandas as pd
import numpy as np
from typing import List
from strategy.base import BaseStrategy, Signal, SignalType
from factors.technical import sma, bollinger_bands, rsi
from utils.helpers import normalize
from utils.logger import log


class MeanReversionStrategy(BaseStrategy):
    """
    均值回归策略

    逻辑：
    1. Z-score 超过阈值 → 价格偏离均值过大 → 买入/卖出
    2. RSI 辅助确认超买/超卖
    3. 布林带作为辅助通道
    """

    def __init__(
        self,
        window: int = 20,
        entry_zscore: float = 2.0,
        exit_zscore: float = 0.5,
        use_bollinger: bool = False,
        rsi_filter: bool = True,
        max_holding_days: int = 30,
    ):
        super().__init__(
            name="MeanReversion",
            params={
                "window": window,
                "entry_zscore": entry_zscore,
                "exit_zscore": exit_zscore,
                "use_bollinger": use_bollinger,
                "rsi_filter": rsi_filter,
                "max_holding_days": max_holding_days,
            }
        )
        self.window = window
        self.entry_zscore = entry_zscore
        self.exit_zscore = exit_zscore
        self.use_bollinger = use_bollinger
        self.rsi_filter = rsi_filter
        self.max_holding_days = max_holding_days

    def generate_signals(self, data: pd.DataFrame) -> List[Signal]:
        signals = []

        if len(data) < self.window + 1:
            return signals

        df = data.copy()

        # 计算 Z-score
        df["mean"] = df["close"].rolling(self.window).mean()
        df["std"] = df["close"].rolling(self.window).std()
        df["zscore"] = (df["close"] - df["mean"]) / df["std"].replace(0, np.nan)

        # RSI
        if self.rsi_filter:
            df["rsi"] = rsi(df["close"], 14)

        # 布林带
        if self.use_bollinger:
            bb = bollinger_bands(df["close"], self.window)
            df = pd.concat([df, bb], axis=1)

        current = df.iloc[-1]
        prev = df.iloc[-2]

        symbol = current.get("symbol", "UNKNOWN")
        date = str(current.get("date", ""))
        price = current["close"]
        zscore = current["zscore"]

        if np.isnan(zscore):
            return signals

        # 检查是否持仓
        position = self.get_position(symbol)

        # === 买入信号：价格低于均值超过阈值（超卖回归）===
        if zscore < -self.entry_zscore:
            # RSI 确认超卖
            rsi_ok = True
            if self.rsi_filter and "rsi" in df.columns:
                rsi_ok = current["rsi"] < 30

            # 布林带确认：价格触及下轨
            bb_ok = True
            if self.use_bollinger and "bb_lower" in df.columns:
                bb_ok = price <= current["bb_lower"] * 1.01

            if rsi_ok and bb_ok and position is None:
                signals.append(Signal(
                    symbol=symbol,
                    signal_type=SignalType.BUY,
                    price=price,
                    date=date,
                    strength=min(1.0, abs(zscore) / self.entry_zscore),
                    reason=f"Z-score={zscore:.2f} 超卖回归",
                    stop_loss=price * (1 - abs(zscore) * 0.01),
                    take_profit=current["mean"],
                ))

        # === 卖出信号：价格高于均值超过阈值（超买回归）===
        if zscore > self.entry_zscore:
            rsi_ok = True
            if self.rsi_filter and "rsi" in df.columns:
                rsi_ok = current["rsi"] > 70

            bb_ok = True
            if self.use_bollinger and "bb_upper" in df.columns:
                bb_ok = price >= current["bb_upper"] * 0.99

            if rsi_ok and bb_ok and position is None:
                signals.append(Signal(
                    symbol=symbol,
                    signal_type=SignalType.SELL,
                    price=price,
                    date=date,
                    strength=min(1.0, abs(zscore) / self.entry_zscore),
                    reason=f"Z-score={zscore:.2f} 超买回归",
                ))

        # === 出场信号：Z-score 回归到均值附近 ===
        if position is not None:
            # 做多仓位的出场
            if position.quantity > 0 and zscore > -self.exit_zscore:
                signals.append(Signal(
                    symbol=symbol,
                    signal_type=SignalType.SELL,
                    price=price,
                    date=date,
                    strength=0.6,
                    reason=f"Z-score回归至{zscore:.2f} 平仓",
                ))

            # 做空仓位的出场（如果支持）
            if position.quantity < 0 and zscore < self.exit_zscore:
                signals.append(Signal(
                    symbol=symbol,
                    signal_type=SignalType.BUY,
                    price=price,
                    date=date,
                    strength=0.6,
                    reason=f"Z-score回归至{zscore:.2f} 平仓",
                ))

            # 时间止损
            if position is not None:
                holding_days = (pd.to_datetime(date) - pd.to_datetime(position.entry_date)).days
                if holding_days >= self.max_holding_days:
                    signals.append(Signal(
                        symbol=symbol,
                        signal_type=SignalType.SELL if position.quantity > 0 else SignalType.BUY,
                        price=price,
                        date=date,
                        strength=0.4,
                        reason=f"持仓{holding_days}天超限",
                    ))

        return signals


class PairsTradingStrategy(BaseStrategy):
    """
    配对交易策略

    逻辑：
    1. 找到两只相关性高的股票
    2. 计算价差的 Z-score
    3. 价差偏离均值时，做多一只做空另一只
    4. 价差回归时平仓
    """

    def __init__(
        self,
        lookback: int = 60,
        entry_spread: float = 2.0,
        exit_spread: float = 0.0,
        min_correlation: float = 0.7,
    ):
        super().__init__(
            name="PairsTrading",
            params={
                "lookback": lookback,
                "entry_spread": entry_spread,
                "exit_spread": exit_spread,
                "min_correlation": min_correlation,
            }
        )
        self.lookback = lookback
        self.entry_spread = entry_spread
        self.exit_spread = exit_spread
        self.min_correlation = min_correlation

    def find_cointegrated_pairs(
        self,
        price_data: dict,
        p_value_threshold: float = 0.05,
    ) -> List[tuple]:
        """
        寻找协整对

        Args:
            price_data: {symbol: price_series}
            p_value_threshold: p 值阈值

        Returns:
            协整对列表 [(symbol_a, symbol_b, p_value)]
        """
        from statsmodels.tsa.stattools import coint

        pairs = []
        symbols = list(price_data.keys())

        for i in range(len(symbols)):
            for j in range(i + 1, len(symbols)):
                s1 = price_data[symbols[i]].dropna()
                s2 = price_data[symbols[j]].dropna()

                # 对齐
                common_idx = s1.index.intersection(s2.index)
                if len(common_idx) < self.lookback:
                    continue

                s1 = s1.loc[common_idx]
                s2 = s2.loc[common_idx]

                # 检查相关性
                corr = s1.corr(s2)
                if corr < self.min_correlation:
                    continue

                # 协整检验
                try:
                    score, pvalue, _ = coint(s1, s2)
                    if pvalue < p_value_threshold:
                        pairs.append((symbols[i], symbols[j], pvalue))
                except Exception:
                    continue

        # 按 p 值排序
        pairs.sort(key=lambda x: x[2])
        return pairs

    def generate_signals(self, data: pd.DataFrame) -> List[Signal]:
        """配对交易需要特殊处理，这里为接口兼容"""
        return []