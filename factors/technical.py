"""
技术因子计算模块
包含常用技术分析指标
"""
import pandas as pd
import numpy as np
from typing import Optional


def sma(series: pd.Series, window: int) -> pd.Series:
    """简单移动平均"""
    return series.rolling(window=window).mean()


def ema(series: pd.Series, window: int) -> pd.Series:
    """指数移动平均"""
    return series.ewm(span=window, adjust=False).mean()


def macd(
    close: pd.Series,
    fast: int = 12,
    slow: int = 26,
    signal: int = 9
) -> pd.DataFrame:
    """
    MACD 指标

    Returns:
        DataFrame with columns: macd_dif, macd_dea, macd_hist
    """
    ema_fast = ema(close, fast)
    ema_slow = ema(close, slow)
    dif = ema_fast - ema_slow
    dea = ema(dif, signal)
    hist = 2 * (dif - dea)

    return pd.DataFrame({
        "macd_dif": dif,
        "macd_dea": dea,
        "macd_hist": hist,
    })


def rsi(close: pd.Series, window: int = 14) -> pd.Series:
    """相对强弱指标"""
    delta = close.diff()
    gain = delta.where(delta > 0, 0.0)
    loss = -delta.where(delta < 0, 0.0)

    avg_gain = gain.rolling(window=window).mean()
    avg_loss = loss.rolling(window=window).mean()

    rs = avg_gain / avg_loss.replace(0, np.inf)
    return 100 - (100 / (1 + rs))


def bollinger_bands(
    close: pd.Series,
    window: int = 20,
    num_std: float = 2.0
) -> pd.DataFrame:
    """
    布林带

    Returns:
        DataFrame with columns: bb_upper, bb_middle, bb_lower, bb_width
    """
    middle = sma(close, window)
    std = close.rolling(window=window).std()
    upper = middle + num_std * std
    lower = middle - num_std * std

    return pd.DataFrame({
        "bb_upper": upper,
        "bb_middle": middle,
        "bb_lower": lower,
        "bb_width": (upper - lower) / middle,
    })


def atr(high: pd.Series, low: pd.Series, close: pd.Series, window: int = 14) -> pd.Series:
    """平均真实波幅"""
    tr1 = high - low
    tr2 = (high - close.shift(1)).abs()
    tr3 = (low - close.shift(1)).abs()
    true_range = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    return true_range.rolling(window=window).mean()


def kdj(
    high: pd.Series,
    low: pd.Series,
    close: pd.Series,
    n: int = 9,
    m1: int = 3,
    m2: int = 3
) -> pd.DataFrame:
    """
    KDJ 指标

    Returns:
        DataFrame with columns: k, d, j
    """
    lowest_low = low.rolling(window=n).min()
    highest_high = high.rolling(window=n).max()

    rsv = (close - lowest_low) / (highest_high - lowest_low) * 100
    rsv = rsv.fillna(50)

    k = rsv.ewm(com=m1 - 1, adjust=False).mean()
    d = k.ewm(com=m2 - 1, adjust=False).mean()
    j = 3 * k - 2 * d

    return pd.DataFrame({"k": k, "d": d, "j": j})


def williams_r(
    high: pd.Series,
    low: pd.Series,
    close: pd.Series,
    window: int = 14
) -> pd.Series:
    """威廉指标"""
    highest = high.rolling(window=window).max()
    lowest = low.rolling(window=window).min()
    return (highest - close) / (highest - lowest) * -100


def cci(
    high: pd.Series,
    low: pd.Series,
    close: pd.Series,
    window: int = 20
) -> pd.Series:
    """商品通道指数"""
    typical_price = (high + low + close) / 3
    mean_tp = typical_price.rolling(window=window).mean()
    mean_dev = typical_price.rolling(window=window).apply(
        lambda x: np.abs(x - x.mean()).mean(), raw=True
    )
    return (typical_price - mean_tp) / (0.015 * mean_dev)


def obv(close: pd.Series, volume: pd.Series) -> pd.Series:
    """能量潮指标"""
    direction = close.diff().apply(lambda x: 1 if x > 0 else (-1 if x < 0 else 0))
    return (volume * direction).cumsum()


def vwap(high: pd.Series, low: pd.Series, close: pd.Series, volume: pd.Series) -> pd.Series:
    """成交量加权平均价"""
    typical_price = (high + low + close) / 3
    return (typical_price * volume).cumsum() / volume.cumsum()


def momentum(close: pd.Series, window: int = 10) -> pd.Series:
    """动量指标"""
    return close - close.shift(window)


def rate_of_change(close: pd.Series, window: int = 10) -> pd.Series:
    """变化率"""
    return close.pct_change(periods=window)


def volatility(close: pd.Series, window: int = 20) -> pd.Series:
    """历史波动率"""
    returns = close.pct_change()
    return returns.rolling(window=window).std() * np.sqrt(252)


def volume_ratio(volume: pd.Series, window: int = 5) -> pd.Series:
    """量比"""
    avg_vol = volume.rolling(window=window).mean()
    return volume / avg_vol


def price_channel(high: pd.Series, low: pd.Series, window: int = 20) -> pd.DataFrame:
    """价格通道"""
    upper = high.rolling(window=window).max()
    lower = low.rolling(window=window).min()
    middle = (upper + lower) / 2

    return pd.DataFrame({
        "channel_upper": upper,
        "channel_middle": middle,
        "channel_lower": lower,
    })


def compute_all_technical(df: pd.DataFrame) -> pd.DataFrame:
    """
    计算所有技术因子

    Args:
        df: 包含 open, high, low, close, volume 的 DataFrame

    Returns:
        添加了所有技术指标的 DataFrame
    """
    df = df.copy()

    # 移动平均
    for w in [5, 10, 20, 60, 120]:
        df[f"ma_{w}"] = sma(df["close"], w)
        df[f"ema_{w}"] = ema(df["close"], w)

    # MACD
    macd_df = macd(df["close"])
    df = pd.concat([df, macd_df], axis=1)

    # RSI
    for w in [6, 14, 24]:
        df[f"rsi_{w}"] = rsi(df["close"], w)

    # 布林带
    bb_df = bollinger_bands(df["close"])
    df = pd.concat([df, bb_df], axis=1)

    # ATR
    df["atr_14"] = atr(df["high"], df["low"], df["close"], 14)

    # KDJ
    kdj_df = kdj(df["high"], df["low"], df["close"])
    df = pd.concat([df, kdj_df], axis=1)

    # 成交量指标
    df["volume_ratio"] = volume_ratio(df["volume"])
    df["obv"] = obv(df["close"], df["volume"])

    # 波动率
    df["volatility_20"] = volatility(df["close"], 20)

    # 动量
    df["momentum_10"] = momentum(df["close"], 10)
    df["roc_10"] = rate_of_change(df["close"], 10)

    # 收盘价相对位置
    df["close_position"] = (df["close"] - df["low"]) / (df["high"] - df["low"])

    return df