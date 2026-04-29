"""
通用工具函数
"""

import pandas as pd
import numpy as np
from typing import Union, List, Optional
from datetime import datetime, timedelta


def format_code(code: str) -> str:
    """
    格式化股票代码
    - 6位股票代码补齐
    - 添加交易所后缀(.SH/.SZ)

    Args:
        code: 股票代码

    Returns:
        格式化后的代码，如 '000001.SZ'
    """
    code = str(code).zfill(6)

    # 判断交易所
    if code.startswith(('000', '001', '002', '003', '300')):
        return f"{code}.SZ"  # 深圳
    else:
        return f"{code}.SH"  # 上海


def parse_code(full_code: str) -> tuple:
    """
    解析完整股票代码

    Args:
        full_code: 如 '000001.SZ'

    Returns:
        (code, exchange) -> ('000001', 'SZ')
    """
    if '.' in full_code:
        code, exchange = full_code.split('.')
        return code, exchange
    return full_code, ''


def trading_date_offset(date: Union[str, datetime], offset: int,
                       trade_calendar: pd.DataFrame = None) -> str:
    """
    计算交易日偏移

    Args:
        date: 起始日期，格式YYYY-MM-DD或datetime
        offset: 偏移天数，正数往后，负数往前
        trade_calendar: 交易日期表DataFrame，需包含date列

    Returns:
        偏移后的交易日，格式YYYY-MM-DD
    """
    if isinstance(date, str):
        date = pd.to_datetime(date)

    if trade_calendar is not None and len(trade_calendar) > 0:
        dates = pd.to_datetime(trade_calendar['date']).sort_values().values
        current_idx = np.searchsorted(dates, date)

        new_idx = current_idx + offset
        new_idx = np.clip(new_idx, 0, len(dates) - 1)

        result = pd.Timestamp(dates[new_idx])
    else:
        # 简单估计：每年约250个交易日
        result = date + timedelta(days=offset)

    return result.strftime('%Y-%m-%d')


def get_date_range(start: str, end: str) -> List[str]:
    """
    生成日期序列

    Args:
        start: 起始日期 YYYY-MM-DD
        end: 结束日期 YYYY-MM-DD

    Returns:
        日期列表
    """
    return pd.date_range(start, end, freq='D').strftime('%Y-%m-%d').tolist()


def resample_turnover(date: str, trade_calendar: pd.DataFrame) -> str:
    """
    获取调仓日（按月/周对齐到最近交易日）

    Args:
        date: 目标日期
        trade_calendar: 交易日期表

    Returns:
        最近的有效交易日
    """
    target = pd.to_datetime(date)
    dates = pd.to_datetime(trade_calendar['date']).sort_values()

    # 找最近的不早于target的交易日
    valid_dates = dates[dates >= target]
    if len(valid_dates) > 0:
        return valid_dates.iloc[0].strftime('%Y-%m-%d')

    # 如果target之后没有，取前一个
    return dates[dates <= target].iloc[-1].strftime('%Y-%m-%d')


def nan_to_zero(df: Union[pd.DataFrame, pd.Series], copy: bool = False) -> Union[pd.DataFrame, pd.Series]:
    """
    将NaN替换为0

    Args:
        df: 输入数据
        copy: 是否返回副本

    Returns:
        处理后的数据
    """
    if copy:
        return df.fillna(0)
    return df.fillna(0)


def winsorize(series: pd.Series, n_std: float = 3.0) -> pd.Series:
    """
    MAD去极值方法

    Args:
        series: 输入序列
        n_std: 标准差倍数，默认3倍

    Returns:
        去极值后的序列
    """
    median = series.median()
    mad = (series - median).abs().median()
    if mad == 0:
        return series

    lower = median - n_std * mad
    upper = median + n_std * mad
    return series.clip(lower, upper)


def standardize(series: pd.Series, method: str = 'zscore') -> pd.Series:
    """
    标准化序列

    Args:
        series: 输入序列
        method: 'zscore' 或 'minmax'

    Returns:
        标准化后的序列
    """
    if method == 'zscore':
        mean = series.mean()
        std = series.std()
        if std == 0:
            return series - mean
        return (series - mean) / std
    elif method == 'minmax':
        min_val = series.min()
        max_val = series.max()
        if max_val == min_val:
            return series - min_val
        return (series - min_val) / (max_val - min_val)
    return series


def rank_normalize(series: pd.Series) -> pd.Series:
    """
    排名归一化到[0,1]

    Args:
        series: 输入序列

    Returns:
        归一化后的序列
    """
    return series.rank(pct=True)
