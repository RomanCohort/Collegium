"""
动量策略
基于价格动量的趋势跟踪策略
"""
import pandas as pd
import numpy as np
from typing import List, Dict, Optional
from strategy.base import BaseStrategy, Signal, SignalType
from factors.technical import sma, ema, rsi, macd, atr
from utils.logger import log


class MomentumStrategy(BaseStrategy):
    """
    动量策略

    逻辑：
    1. 价格突破 N 日高点 → 买入信号
    2. 价格跌破 N 日低点 → 卖出信号
    3. RSI 过滤超买超卖
    4. MACD 辅助确认趋势
    """

    def __init__(
        self,
        lookback_period: int = 20,
        holding_period: int = 10,
        rsi_overbought: float = 70,
        rsi_oversold: float = 30,
        use_macd_filter: bool = True,
        min_return_threshold: float = 0.0,
        volume_filter: bool = False,
    ):
        super().__init__(
            name="Momentum",
            params={
                "lookback_period": lookback_period,
                "holding_period": holding_period,
                "rsi_overbought": rsi_overbought,
                "rsi_oversold": rsi_oversold,
                "use_macd_filter": use_macd_filter,
                "min_return_threshold": min_return_threshold,
                "volume_filter": volume_filter,
            }
        )
        self.lookback = lookback_period
        self.holding_period = holding_period
        self.rsi_overbought = rsi_overbought
        self.rsi_oversold = rsi_oversold
        self.use_macd_filter = use_macd_filter
        self.volume_filter = volume_filter

    def generate_signals(self, data: pd.DataFrame) -> List[Signal]:
        """
        生成动量信号

        Args:
            data: 包含 OHLCV 数据的 DataFrame

        Returns:
            信号列表
        """
        signals = []

        if len(data) < self.lookback + 1:
            return signals

        df = data.copy()

        # 计算指标
        df["high_max"] = df["close"].rolling(self.lookback).max()
        df["low_min"] = df["close"].rolling(self.lookback).min()
        df["rsi"] = rsi(df["close"], 14)

        if self.use_macd_filter:
            macd_df = macd(df["close"])
            df["macd_hist"] = macd_df["macd_hist"]

        df["atr_val"] = atr(df["high"], df["low"], df["close"], 14)

        # 取最近数据
        current = df.iloc[-1]
        prev = df.iloc[-2]

        symbol = current.get("symbol", "UNKNOWN")
        date = str(current.get("date", ""))
        price = current["close"]

        # === 买入信号 ===
        # 条件1: 价格突破 lookback 日新高
        breakout_up = prev["close"] <= prev["high_max"] and price > prev["high_max"]

        # 条件2: RSI 不在超买区
        rsi_ok = current["rsi"] < self.rsi_overbought

        # 条件3: MACD 柱状图为正（趋势确认）
        macd_ok = True
        if self.use_macd_filter and "macd_hist" in df.columns:
            macd_ok = current["macd_hist"] > 0

        # 条件4: 成交量放大
        vol_ok = True
        if self.volume_filter and "volume" in df.columns:
            vol_ma = df["volume"].rolling(5).mean().iloc[-1]
            vol_ok = current["volume"] > vol_ma * 1.2 if vol_ma > 0 else True

        if breakout_up and rsi_ok and macd_ok and vol_ok:
            stop_loss = price - 2 * current["atr_val"] if current["atr_val"] > 0 else price * 0.95
            signals.append(Signal(
                symbol=symbol,
                signal_type=SignalType.BUY,
                price=price,
                date=date,
                strength=min(1.0, (price - prev["high_max"]) / prev["high_max"] * 10),
                reason=f"突破{self.lookback}日新高 RSI={current['rsi']:.1f}",
                stop_loss=stop_loss,
                take_profit=price + 4 * current["atr_val"] if current["atr_val"] > 0 else price * 1.1,
            ))

        # === 卖出信号 ===
        # 条件1: 价格跌破 lookback 日新低
        breakout_down = prev["close"] >= prev["low_min"] and price < prev["low_min"]

        # 条件2: RSI 不在超卖区（避免地板割肉）
        rsi_not_oversold = current["rsi"] > self.rsi_oversold

        if breakout_down and rsi_not_oversold:
            signals.append(Signal(
                symbol=symbol,
                signal_type=SignalType.SELL,
                price=price,
                date=date,
                strength=min(1.0, (prev["low_min"] - price) / prev["low_min"] * 10),
                reason=f"跌破{self.lookback}日新低 RSI={current['rsi']:.1f}",
            ))

        # MACD 死叉卖出
        if self.use_macd_filter and "macd_hist" in df.columns:
            if prev["macd_hist"] > 0 and current["macd_hist"] < 0:
                # 只在持仓时发出
                if self.get_position(symbol) is not None:
                    signals.append(Signal(
                        symbol=symbol,
                        signal_type=SignalType.SELL,
                        price=price,
                        date=date,
                        strength=0.7,
                        reason="MACD死叉",
                    ))

        return signals


class DualMAStrategy(BaseStrategy):
    """
    双均线策略

    逻辑：
    1. 快线上穿慢线 → 金叉买入
    2. 快线下穿慢线 → 死叉卖出
    3. 可选：均线斜率过滤
    """

    def __init__(
        self,
        fast_period: int = 5,
        slow_period: int = 20,
        signal_type: str = "cross",
        min_slope: float = 0.0,
    ):
        super().__init__(
            name="DualMA",
            params={
                "fast_period": fast_period,
                "slow_period": slow_period,
                "signal_type": signal_type,
                "min_slope": min_slope,
            }
        )
        self.fast_period = fast_period
        self.slow_period = slow_period
        self.signal_type = signal_type
        self.min_slope = min_slope

    def generate_signals(self, data: pd.DataFrame) -> List[Signal]:
        signals = []

        if len(data) < self.slow_period + 1:
            return signals

        df = data.copy()
        df["fast_ma"] = sma(df["close"], self.fast_period)
        df["slow_ma"] = sma(df["close"], self.slow_period)

        current = df.iloc[-1]
        prev = df.iloc[-2]

        symbol = current.get("symbol", "UNKNOWN")
        date = str(current.get("date", ""))
        price = current["close"]

        # 金叉
        golden_cross = (prev["fast_ma"] <= prev["slow_ma"] and
                        current["fast_ma"] > current["slow_ma"])

        # 死叉
        death_cross = (prev["fast_ma"] >= prev["slow_ma"] and
                       current["fast_ma"] < current["slow_ma"])

        # 均线斜率过滤
        if self.min_slope > 0:
            slow_slope = (current["slow_ma"] - df["slow_ma"].iloc[-5]) / df["slow_ma"].iloc[-5]
            if abs(slow_slope) < self.min_slope:
                return signals

        if golden_cross:
            signals.append(Signal(
                symbol=symbol,
                signal_type=SignalType.BUY,
                price=price,
                date=date,
                strength=0.8,
                reason=f"金叉 MA{self.fast_period}上穿MA{self.slow_period}",
                stop_loss=price * 0.95,
                take_profit=price * 1.1,
            ))

        if death_cross:
            signals.append(Signal(
                symbol=symbol,
                signal_type=SignalType.SELL,
                price=price,
                date=date,
                strength=0.8,
                reason=f"死叉 MA{self.fast_period}下穿MA{self.slow_period}",
            ))

        return signals