"""
通用工具函数
"""
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Union, List, Optional


def date_range(start_date: str, end_date: str) -> List[str]:
    """
    生成日期范围列表（仅交易日）

    Args:
        start_date: 开始日期 YYYY-MM-DD
        end_date: 结束日期 YYYY-MM-DD

    Returns:
        日期字符串列表
    """
    dates = pd.date_range(start_date, end_date, freq="B")  # B = 工作日
    return [d.strftime("%Y-%m-%d") for d in dates]


def trading_days(start_date: str, end_date: str) -> int:
    """
    计算交易日数量

    Args:
        start_date: 开始日期
        end_date: 结束日期

    Returns:
        交易日数量
    """
    return len(date_range(start_date, end_date))


def format_number(value: float, decimal: int = 2) -> str:
    """
    格式化数字显示（添加单位）

    Args:
        value: 数值
        decimal: 小数位数

    Returns:
        格式化后的字符串
    """
    abs_value = abs(value)
    sign = "-" if value < 0 else ""

    if abs_value >= 1e8:
        return f"{sign}{abs_value / 1e8:.{decimal}f}亿"
    elif abs_value >= 1e4:
        return f"{sign}{abs_value / 1e4:.{decimal}f}万"
    else:
        return f"{sign}{abs_value:.{decimal}f}"


def pct_change(current: float, previous: float) -> float:
    """
    计算百分比变化

    Args:
        current: 当前值
        previous: 之前值

    Returns:
        百分比变化
    """
    if previous == 0:
        return 0.0
    return (current - previous) / abs(previous)


def annualized_return(total_return: float, days: int) -> float:
    """
    计算年化收益率

    Args:
        total_return: 总收益率
        days: 持有天数

    Returns:
        年化收益率
    """
    if days <= 0:
        return 0.0
    return (1 + total_return) ** (252 / days) - 1


def annualized_volatility(returns: pd.Series) -> float:
    """
    计算年化波动率

    Args:
        returns: 日收益率序列

    Returns:
        年化波动率
    """
    return returns.std() * np.sqrt(252)


def sharpe_ratio(returns: pd.Series, risk_free_rate: float = 0.03) -> float:
    """
    计算夏普比率

    Args:
        returns: 日收益率序列
        risk_free_rate: 无风险利率（年化）

    Returns:
        夏普比率
    """
    excess_returns = returns.mean() * 252 - risk_free_rate
    vol = annualized_volatility(returns)
    if vol == 0:
        return 0.0
    return excess_returns / vol


def max_drawdown(nav_series: pd.Series) -> float:
    """
    计算最大回撤

    Args:
        nav_series: 净值序列

    Returns:
        最大回撤
    """
    cumulative = nav_series.cummax()
    drawdown = (nav_series - cumulative) / cumulative
    return drawdown.min()


def calmar_ratio(annual_return: float, max_dd: float) -> float:
    """
    计算 Calmar 比率

    Args:
        annual_return: 年化收益
        max_dd: 最大回撤（正数）

    Returns:
        Calmar 比率
    """
    if max_dd == 0:
        return float('inf')
    return annual_return / abs(max_dd)


def winsorize(series: pd.Series, limits: tuple = (0.01, 0.01)) -> pd.Series:
    """
    缩尾处理（去除极端值）

    Args:
        series: 数据序列
        limits: 上下限比例

    Returns:
    处理后的序列
    """
    lower_limit = series.quantile(limits[0])
    upper_limit = series.quantile(1 - limits[1])
    return series.clip(lower_limit, upper_limit)


def normalize(series: pd.Series, method: str = "zscore") -> pd.Series:
    """
    标准化处理

    Args:
        series: 数据序列
        method: 标准化方法 (zscore / minmax / rank)

    Returns:
        标准化后的序列
    """
    if method == "zscore":
        return (series - series.mean()) / series.std()
    elif method == "minmax":
        return (series - series.min()) / (series.max() - series.min())
    elif method == "rank":
        return series.rank(pct=True)
    else:
        return series


def get_industry_mapping() -> dict:
    """
    获取申万一级行业映射

    Returns:
        行业代码到名称的映射
    """
    return {
        "801010": "农林牧渔",
        "801020": "采掘",
        "801030": "化工",
        "801040": "钢铁",
        "801050": "有色金属",
        "801080": "电子",
        "801110": "家用电器",
        "801120": "食品饮料",
        "801130": "纺织服装",
        "801140": "轻工制造",
        "801150": "医药生物",
        "801160": "公用事业",
        "801170": "交通运输",
        "801180": "房地产",
        "801200": "商业贸易",
        "801210": "休闲服务",
        "801230": "综合",
        "801710": "建筑材料",
        "801720": "建筑装饰",
        "801730": "电气设备",
        "801740": "国防军工",
        "801750": "计算机",
        "801760": "传媒",
        "801770": "通信",
        "801780": "银行",
        "801790": "非银金融",
        "801880": "汽车",
        "801890": "机械设备",
    }
