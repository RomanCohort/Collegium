"""
基本面因子计算模块
包含价值、质量、成长等基本面因子
"""
import pandas as pd
import numpy as np
from typing import Optional
from utils.logger import log


def pe_ratio(price: pd.Series, eps: pd.Series) -> pd.Series:
    """市盈率"""
    return price / eps.replace(0, np.nan)


def pb_ratio(price: pd.Series, bvps: pd.Series) -> pd.Series:
    """市净率"""
    return price / bvps.replace(0, np.nan)


def ps_ratio(price: pd.Series, revenue_per_share: pd.Series) -> pd.Series:
    """市销率"""
    return price / revenue_per_share.replace(0, np.nan)


def roe(net_income: pd.Series, equity: pd.Series) -> pd.Series:
    """净资产收益率"""
    return net_income / equity.replace(0, np.nan)


def roa(net_income: pd.Series, total_assets: pd.Series) -> pd.Series:
    """总资产收益率"""
    return net_income / total_assets.replace(0, np.nan)


def gross_margin(revenue: pd.Series, cost: pd.Series) -> pd.Series:
    """毛利率"""
    return (revenue - cost) / revenue.replace(0, np.nan)


def net_margin(net_income: pd.Series, revenue: pd.Series) -> pd.Series:
    """净利率"""
    return net_income / revenue.replace(0, np.nan)


def debt_ratio(total_liabilities: pd.Series, total_assets: pd.Series) -> pd.Series:
    """资产负债率"""
    return total_liabilities / total_assets.replace(0, np.nan)


def current_ratio(current_assets: pd.Series, current_liabilities: pd.Series) -> pd.Series:
    """流动比率"""
    return current_assets / current_liabilities.replace(0, np.nan)


def revenue_growth(revenue: pd.Series) -> pd.Series:
    """营收增长率（同比）"""
    return revenue.pct_change(4)  # 假设季频数据


def earnings_growth(earnings: pd.Series) -> pd.Series:
    """盈利增长率（同比）"""
    return earnings.pct_change(4)


def dividend_yield(dividend: pd.Series, price: pd.Series) -> pd.Series:
    """股息率"""
    return dividend / price.replace(0, np.nan)


def earnings_yield(eps: pd.Series, price: pd.Series) -> pd.Series:
    """盈利收益率 = 1/PE"""
    return eps / price.replace(0, np.nan)


def compute_value_factors(df: pd.DataFrame) -> pd.DataFrame:
    """
    计算价值因子

    Args:
        df: 包含价格和财务数据的 DataFrame
            需要列: close, eps, bvps, revenue_per_share, dividend

    Returns:
        添加了价值因子的 DataFrame
    """
    df = df.copy()

    if "eps" in df.columns and "close" in df.columns:
        df["pe"] = pe_ratio(df["close"], df["eps"])
        df["earnings_yield"] = earnings_yield(df["eps"], df["close"])

    if "bvps" in df.columns and "close" in df.columns:
        df["pb"] = pb_ratio(df["close"], df["bvps"])

    if "revenue_per_share" in df.columns and "close" in df.columns:
        df["ps"] = ps_ratio(df["close"], df["revenue_per_share"])

    if "dividend" in df.columns and "close" in df.columns:
        df["dividend_yield"] = dividend_yield(df["dividend"], df["close"])

    return df


def compute_quality_factors(df: pd.DataFrame) -> pd.DataFrame:
    """
    计算质量因子

    Args:
        df: 包含财务数据的 DataFrame

    Returns:
        添加了质量因子的 DataFrame
    """
    df = df.copy()

    if all(col in df.columns for col in ["net_income", "equity"]):
        df["roe"] = roe(df["net_income"], df["equity"])

    if all(col in df.columns for col in ["net_income", "total_assets"]):
        df["roa"] = roa(df["net_income"], df["total_assets"])

    if all(col in df.columns for col in ["revenue", "cost"]):
        df["gross_margin"] = gross_margin(df["revenue"], df["cost"])

    if all(col in df.columns for col in ["net_income", "revenue"]):
        df["net_margin"] = net_margin(df["net_income"], df["revenue"])

    if all(col in df.columns for col in ["total_liabilities", "total_assets"]):
        df["debt_ratio"] = debt_ratio(df["total_liabilities"], df["total_assets"])

    return df


def compute_growth_factors(df: pd.DataFrame) -> pd.DataFrame:
    """
    计算成长因子

    Args:
        df: 包含财务数据的 DataFrame

    Returns:
        添加了成长因子的 DataFrame
    """
    df = df.copy()

    if "revenue" in df.columns:
        df["revenue_growth"] = revenue_growth(df["revenue"])

    if "net_income" in df.columns:
        df["earnings_growth"] = earnings_growth(df["net_income"])

    return df


def compute_all_fundamental(df: pd.DataFrame) -> pd.DataFrame:
    """
    计算所有基本面因子

    Args:
        df: 包含价格和财务数据的 DataFrame

    Returns:
        添加了所有基本面因子的 DataFrame
    """
    df = compute_value_factors(df)
    df = compute_quality_factors(df)
    df = compute_growth_factors(df)

    log.info(f"计算基本面因子完成，共 {len(df.columns)} 列")
    return df