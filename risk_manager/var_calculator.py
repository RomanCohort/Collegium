"""
风险度量模块
计算 VaR、CVaR 等风险指标
"""
import pandas as pd
import numpy as np
from typing import Optional, Dict, List
from scipy import stats
from utils.logger import log


class RiskCalculator:
    """风险计算器"""

    def __init__(self, confidence_level: float = 0.95):
        """
        初始化风险计算器

        Args:
            confidence_level: 置信水平（默认 95%）
        """
        self.confidence_level = confidence_level

    def var_historical(
        self,
        returns: pd.Series,
        period: int = 252,
        confidence: Optional[float] = None,
    ) -> float:
        """
        历史法 VaR

        Args:
            returns: 收益率序列
            period: 年化周期（默认 252）
            confidence: 置信水平

        Returns:
            VaR 值（负数表示损失）
        """
        if confidence is None:
            confidence = self.confidence_level

        # 非参数方法：从历史分位数获取
        var = np.percentile(returns, (1 - confidence) * 100)
        return var * np.sqrt(period)  # 年化

    def var_parametric(
        self,
        returns: pd.Series,
        period: int = 252,
        confidence: Optional[float] = None,
        method: str = "normal",
    ) -> float:
        """
        参数法 VaR

        Args:
            returns: 收益率序列
            period: 年化周期
            confidence: 置信水平
            method: 分布假设 (normal / t-dist)

        Returns:
            VaR 值
        """
        if confidence is None:
            confidence = self.confidence_level

        mu = returns.mean()
        sigma = returns.std()

        if method == "normal":
            z = stats.norm.ppf(1 - confidence)
            var = mu + sigma * z
        elif method == "t-dist":
            # Student-t 分布
            df = len(returns) - 1
            t_val = stats.t.ppf(1 - confidence, df)
            var = mu + sigma * t_val
        else:
            z = stats.norm.ppf(1 - confidence)
            var = mu + sigma * z

        return var * np.sqrt(period)

    def cvar(
        self,
        returns: pd.Series,
        period: int = 252,
        confidence: Optional[float] = None,
    ) -> float:
        """
        CVaR（条件 VaR / 期望尾部损失）

        Args:
            returns: 收益率序列
            period: 年化周期
            confidence: 置信水平

        Returns:
            CVaR 值
        """
        if confidence is None:
            confidence = self.confidence_level

        var = np.percentile(returns, (1 - confidence) * 100)
        cvar = returns[returns <= var].mean()

        return cvar * np.sqrt(period)

    def max_drawdown(
        self,
        nav: pd.Series,
        return_type: str = "value",
    ) -> Dict[str, any]:
        """
        计算最大回撤及详细信息

        Args:
            nav: 净值序列
            return_type: 返回类型 value/pct

        Returns:
            包含最大回撤及相关信息的字典
        """
        if len(nav) == 0:
            return {"max_dd": 0, "max_dd_pct": 0}

        # 计算累计净值
        cummax = nav.cummax()
        drawdown = (nav - cummax) / cummax

        max_dd = drawdown.min()
        max_dd_idx = drawdown.idxmin()

        # 找到对应的高点
        peak_idx = nav[:max_dd_idx].idxmax()
        peak_value = nav[peak_idx]
        trough_value = nav[max_dd_idx]

        # 计算恢复时间（如果有）
        recovery_idx = None
        recovery_date = None
        if len(nav) > max_dd_idx:
            # 找到恢复到峰值的位置
            after_trough = nav.loc[max_dd_idx:]
            recovered = after_trough[after_trough >= peak_value]
            if len(recovered) > 0:
                recovery_idx = recovered.index[0]

        result = {
            "max_dd": abs(max_dd),
            "max_dd_date": max_dd_idx,
            "peak_date": peak_idx,
            "peak_value": peak_value,
            "trough_value": trough_value,
            "recovery_date": recovery_date,
            "drawdown_duration": (max_dd_idx - peak_idx).days if hasattr(max_dd_idx - peak_idx, 'days') else None,
        }

        return result

    def calmar_ratio(self, returns: pd.Series) -> float:
        """Calmar 比率（年化收益/最大回撤）"""
        annual_return = returns.mean() * 252
        nav = (1 + returns).cumprod()
        max_dd = abs(self.max_drawdown(nav)["max_dd"])

        if max_dd == 0:
            return float('inf')
        return annual_return / max_dd

    def sortino_ratio(
        self,
        returns: pd.Series,
        risk_free_rate: float = 0.0,
        target_return: float = 0.0,
    ) -> float:
        """Sortino 比率（考虑下行风险）"""
        annual_return = returns.mean() * 252 - risk_free_rate

        # 下行波动率
        downside_returns = returns[returns < target_return]
        downside_std = downside_returns.std() * np.sqrt(252)

        if downside_std == 0:
            return float('inf')
        return annual_return / downside_std

    def sharpe_ratio(
        self,
        returns: pd.Series,
        risk_free_rate: float = 0.03,
    ) -> float:
        """夏普比率"""
        excess = returns.mean() * 252 - risk_free_rate
        vol = returns.std() * np.sqrt(252)

        if vol == 0:
            return 0
        return excess / vol

    def information_ratio(
        self,
        returns: pd.Series,
        benchmark_returns: pd.Series,
    ) -> float:
        """信息比率"""
        active_returns = returns - benchmark_returns
        tracking_error = active_returns.std() * np.sqrt(252)

        if tracking_error == 0:
            return 0
        return active_returns.mean() * 252 / tracking_error

    def omega_ratio(
        self,
        returns: pd.Series,
        threshold: float = 0.0,
    ) -> float:
        """Omega 比率（收益/损失超过阈值的比例）"""
        gains = returns[returns > threshold].sum()
        losses = abs(returns[returns < threshold].sum())

        if losses == 0:
            return float('inf')
        return gains / losses

    def tail_ratio(self, returns: pd.Series) -> float:
        """尾部比率（95%分位数 / 5%分位数的绝对值）"""
        upper = np.percentile(returns, 95)
        lower = abs(np.percentile(returns, 5))

        if lower == 0:
            return 0
        return upper / lower

    def skewness_kurtosis(self, returns: pd.Series) -> dict:
        """收益率分布的偏度和峰度"""
        return {
            "skewness": stats.skew(returns),
            "kurtosis": stats.kurtosis(returns),
        }

    def compute_all_metrics(
        self,
        returns: pd.Series,
        nav: Optional[pd.Series] = None,
        benchmark_returns: Optional[pd.Series] = None,
    ) -> Dict[str, float]:
        """
        计算所有风险指标

        Args:
            returns: 收益率序列
            nav: 净值序列（可选）
            benchmark_returns: 基准收益率（可选）

        Returns:
            包含所有指标的字典
        """
        metrics = {
            # 收益指标
            "total_return": (1 + returns).prod() - 1,
            "annual_return": returns.mean() * 252,
            "annual_volatility": returns.std() * np.sqrt(252),

            # 风险指标
            "var_95": self.var_parametric(returns, confidence=0.95),
            "cvar_95": self.cvar(returns, confidence=0.95),
            "max_drawdown": 0,  # 需要 nav
            "tail_ratio": self.tail_ratio(returns),

            # 风险调整收益
            "sharpe_ratio": self.sharpe_ratio(returns),
            "sortino_ratio": self.sortino_ratio(returns),
            "calmar_ratio": 0,  # 需要 nav
            "omega_ratio": self.omega_ratio(returns),
        }

        # 最大回撤需要净值
        if nav is not None:
            dd_info = self.max_drawdown(nav)
            metrics["max_drawdown"] = dd_info["max_dd"]
            metrics["calmar_ratio"] = self.calmar_ratio(returns)

        # 信息比率需要基准
        if benchmark_returns is not None:
            metrics["information_ratio"] = self.information_ratio(returns, benchmark_returns)

        # 分布特征
        dist_stats = self.skewness_kurtosis(returns)
        metrics.update(dist_stats)

        return metrics

    def stress_test(
        self,
        returns: pd.Series,
        scenarios: Optional[Dict[str, List[str]]] = None,
    ) -> Dict[str, any]:
        """
        压力测试

        Args:
            returns: 历史收益率
            scenarios: 压力场景（如历史股灾时期）

        Returns:
            各场景下的损失
        """
        results = {}

        # 默认场景
        default_scenarios = {
            "2008金融危机": returns.index.str.contains("2008"),
            "2015股灾": returns.index.str.contains("2015"),
            "2020疫情": returns.index.str.contains("2020"),
            "2022熊市": returns.index.str.contains("2022"),
        }

        if scenarios is None:
            scenarios = default_scenarios

        for name, condition in scenarios.items():
            try:
                if callable(condition):
                    scenario_returns = returns[condition(returns)]
                else:
                    # 假设 condition 是布尔索引
                    scenario_returns = returns[condition]

                if len(scenario_returns) > 0:
                    results[name] = {
                        "mean_return": scenario_returns.mean(),
                        "max_loss": scenario_returns.min(),
                        "volatility": scenario_returns.std(),
                        "days": len(scenario_returns),
                    }
            except Exception as e:
                log.warning(f"压力测试场景 {name} 计算失败: {e}")

        return results


# 创建默认实例
risk_calculator = RiskCalculator()