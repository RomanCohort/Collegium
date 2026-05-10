"""
另类因子模块
资金流、情绪、龙虎榜等非传统因子
"""
import pandas as pd
import numpy as np
from typing import Optional
from utils.logger import log


def money_flow_index(
    high: pd.Series,
    low: pd.Series,
    close: pd.Series,
    volume: pd.Series,
    window: int = 14
) -> pd.Series:
    """
    资金流量指标 (MFI)

    Args:
        high, low, close, volume: 价格和成交量数据
        window: 计算窗口

    Returns:
        MFI 序列 (0-100)
    """
    typical_price = (high + low + close) / 3
    raw_money_flow = typical_price * volume

    # 正/负资金流
    positive_flow = raw_money_flow.where(typical_price > typical_price.shift(1), 0)
    negative_flow = raw_money_flow.where(typical_price < typical_price.shift(1), 0)

    positive_sum = positive_flow.rolling(window=window).sum()
    negative_sum = negative_flow.rolling(window=window).sum()

    mfi = 100 - (100 / (1 + positive_sum / negative_sum.replace(0, np.inf)))
    return mfi


def accumulation_distribution(
    high: pd.Series,
    low: pd.Series,
    close: pd.Series,
    volume: pd.Series
) -> pd.Series:
    """
    累积/分布指标 (A/D)
    """
    clv = ((close - low) - (high - close)) / (high - low).replace(0, np.inf)
    return (clv * volume).cumsum()


def chaikin_money_flow(
    high: pd.Series,
    low: pd.Series,
    close: pd.Series,
    volume: pd.Series,
    window: int = 20
) -> pd.Series:
    """
    佳庆资金流 (CMF)
    """
    clv = ((close - low) - (high - close)) / (high - low).replace(0, np.inf)
    return (clv * volume).rolling(window=window).sum() / volume.rolling(window=window).sum()


def force_index(close: pd.Series, volume: pd.Series, window: int = 13) -> pd.Series:
    """
    强力指数
    """
    fi = close.diff() * volume
    return fi.rolling(window=window).mean()


def ease_of_movement(
    high: pd.Series,
    low: pd.Series,
    volume: pd.Series,
    window: int = 14
) -> pd.Series:
    """
    简易波动指标 (EMV)
    """
    distance = ((high + low) / 2) - ((high.shift(1) + low.shift(1)) / 2)
    box_ratio = (volume / 1_000_000) / (high - low).replace(0, np.inf)
    emv = distance / box_ratio.replace(0, np.inf)
    return emv.rolling(window=window).mean()


def volume_price_trend(close: pd.Series, volume: pd.Series) -> pd.Series:
    """
    量价趋势指标 (VPT)
    """
    pct = close.pct_change()
    return (volume * pct).cumsum()


def compute_all_alternative(df: pd.DataFrame) -> pd.DataFrame:
    """
    计算所有另类因子

    Args:
        df: 包含 OHLCV 的 DataFrame

    Returns:
        添加了另类因子的 DataFrame
    """
    df = df.copy()

    # 资金流因子
    df["mfi_14"] = money_flow_index(
        df["high"], df["low"], df["close"], df["volume"], 14
    )
    df["cmf_20"] = chaikin_money_flow(
        df["high"], df["low"], df["close"], df["volume"], 20
    )
    df["ad_line"] = accumulation_distribution(
        df["high"], df["low"], df["close"], df["volume"]
    )
    df["force_index"] = force_index(df["close"], df["volume"])
    df["vpt"] = volume_price_trend(df["close"], df["volume"])

    # 量价背离因子（价格创新高但成交量未创新高）
    price_new_high = df["close"] >= df["close"].rolling(20).max()
    vol_new_high = df["volume"] >= df["volume"].rolling(20).max()
    df["price_vol_divergence"] = (price_new_high & ~vol_new_high).astype(int)

    # 异常放量因子
    vol_ma = df["volume"].rolling(20).mean()
    vol_std = df["volume"].rolling(20).std()
    df["volume_zscore"] = (df["volume"] - vol_ma) / vol_std.replace(0, np.nan)

    log.info(f"计算另类因子完成")
    return df