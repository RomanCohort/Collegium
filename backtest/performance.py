"""
绩效分析模块
"""
import pandas as pd
import numpy as np
from typing import Dict, Optional
from utils.logger import log
from utils.helpers import sharpe_ratio, max_drawdown, annualized_return, annualized_volatility


class PerformanceAnalyzer:
    """绩效分析器"""

    def __init__(self, risk_free_rate: float = 0.03):
        self.risk_free_rate = risk_free_rate

    def analyze(self, nav_series: pd.Series, benchmark: Optional[pd.Series] = None) -> Dict:
        """
        分析绩效

        Args:
            nav_series: 净值序列
            benchmark: 基准净值序列

        Returns:
            绩效指标字典
        """
        if nav_series.empty:
            return {}

        returns = nav_series.pct_change().dropna()

        metrics = {
            # 收益指标
            "total_return": nav_series.iloc[-1] / nav_series.iloc[0] - 1,
            "annual_return": annualized_return(
                nav_series.iloc[-1] / nav_series.iloc[0] - 1,
                len(nav_series)
            ),
            "monthly_return": returns.mean() * 21,
            "daily_return": returns.mean(),

            # 风险指标
            "annual_volatility": annualized_volatility(returns),
            "max_drawdown": max_drawdown(nav_series),
            "downside_volatility": self._downside_volatility(returns),
            "var_95": returns.quantile(0.05),
            "cvar_95": returns[returns <= returns.quantile(0.05)].mean(),

            # 风险调整收益
            "sharpe_ratio": sharpe_ratio(returns, self.risk_free_rate),
            "sortino_ratio": self._sortino_ratio(returns),
            "calmar_ratio": self._calmar_ratio(nav_series),
            "information_ratio": 0,

            # 分布特征
            "skewness": returns.skew(),
            "kurtosis": returns.kurtosis(),
            "best_day": returns.max(),
            "worst_day": returns.min(),
            "positive_days": (returns > 0).sum() / len(returns),
        }

        # 相对基准
        if benchmark is not None and not benchmark.empty:
            benchmark_returns = benchmark.pct_change().dropna()
            aligned_returns, aligned_benchmark = returns.align(benchmark_returns, join="inner")

            if len(aligned_returns) > 0:
                excess = aligned_returns - aligned_benchmark
                metrics["excess_return"] = excess.mean() * 252
                metrics["tracking_error"] = excess.std() * np.sqrt(252)
                metrics["information_ratio"] = (
                    excess.mean() * 252 / (excess.std() * np.sqrt(252))
                    if excess.std() > 0 else 0
                )
                metrics["beta"] = self._calculate_beta(aligned_returns, aligned_benchmark)
                metrics["alpha"] = self._calculate_alpha(
                    aligned_returns, aligned_benchmark, self.risk_free_rate
                )

        return metrics

    def _downside_volatility(self, returns: pd.Series, target: float = 0) -> float:
        """下行波动率"""
        downside = returns[returns < target]
        if downside.empty:
            return 0
        return downside.std() * np.sqrt(252)

    def _sortino_ratio(self, returns: pd.Series) -> float:
        """Sortino 比率"""
        excess = returns.mean() * 252 - self.risk_free_rate
        downside_vol = self._downside_volatility(returns)
        if downside_vol == 0:
            return 0
        return excess / downside_vol

    def _calmar_ratio(self, nav_series: pd.Series) -> float:
        """Calmar 比率"""
        annual_ret = annualized_return(
            nav_series.iloc[-1] / nav_series.iloc[0] - 1,
            len(nav_series)
        )
        max_dd = abs(max_drawdown(nav_series))
        if max_dd == 0:
            return 0
        return annual_ret / max_dd

    def _calculate_beta(self, returns: pd.Series, benchmark: pd.Series) -> float:
        """计算 Beta"""
        covariance = returns.cov(benchmark)
        variance = benchmark.var()
        if variance == 0:
            return 0
        return covariance / variance

    def _calculate_alpha(
        self,
        returns: pd.Series,
        benchmark: pd.Series,
        rf: float
    ) -> float:
        """计算 Alpha"""
        beta = self._calculate_beta(returns, benchmark)
        excess_return = returns.mean() * 252 - rf
        benchmark_excess = benchmark.mean() * 252 - rf
        return excess_return - beta * benchmark_excess

    def analyze_trades(self, trades_df: pd.DataFrame) -> Dict:
        """
        分析交易记录

        Args:
            trades_df: 交易记录 DataFrame

        Returns:
            交易分析指标
        """
        if trades_df.empty:
            return {}

        # 基本统计
        total_trades = len(trades_df)
        buy_trades = trades_df[trades_df["side"] == "BUY"]
        sell_trades = trades_df[trades_df["side"] == "SELL"]

        # 盈亏分析
        pnls = trades_df[trades_df["pnl"] != 0]["pnl"]
        winning = pnls[pnls > 0]
        losing = pnls[pnls < 0]

        metrics = {
            "total_trades": total_trades,
            "buy_count": len(buy_trades),
            "sell_count": len(sell_trades),
            "total_pnl": pnls.sum() if len(pnls) > 0 else 0,
            "avg_pnl": pnls.mean() if len(pnls) > 0 else 0,
            "winning_trades": len(winning),
            "losing_trades": len(losing),
            "win_rate": len(winning) / len(pnls) if len(pnls) > 0 else 0,
            "avg_win": winning.mean() if len(winning) > 0 else 0,
            "avg_loss": losing.mean() if len(losing) > 0 else 0,
            "profit_factor": abs(winning.sum() / losing.sum()) if len(losing) > 0 and losing.sum() != 0 else float('inf'),
            "max_win": winning.max() if len(winning) > 0 else 0,
            "max_loss": losing.min() if len(losing) > 0 else 0,
            "total_commission": trades_df["commission"].sum(),
            "avg_commission": trades_df["commission"].mean(),
        }

        # 期望值
        if len(pnls) > 0:
            metrics["expectancy"] = (
                metrics["win_rate"] * metrics["avg_win"] +
                (1 - metrics["win_rate"]) * metrics["avg_loss"]
            )

        return metrics

    def monthly_returns(self, nav_series: pd.Series) -> pd.DataFrame:
        """
        计算月度收益

        Args:
            nav_series: 净值序列

        Returns:
            月度收益 DataFrame
        """
        if nav_series.empty:
            return pd.DataFrame()

        monthly = nav_series.resample("M").last()
        monthly_returns = monthly.pct_change().dropna()

        # 构建月度收益表
        df = pd.DataFrame({
            "year": monthly_returns.index.year,
            "month": monthly_returns.index.month,
            "return": monthly_returns.values,
        })

        # 透视表
        pivot = df.pivot(index="year", columns="month", values="return")
        pivot.columns = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
                        "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

        return pivot

    def rolling_sharpe(self, nav_series: pd.Series, window: int = 60) -> pd.Series:
        """滚动夏普比率"""
        returns = nav_series.pct_change()
        rolling_return = returns.rolling(window).mean() * 252
        rolling_vol = returns.rolling(window).std() * np.sqrt(252)

        return (rolling_return - self.risk_free_rate) / rolling_vol

    def underwater_plot_data(self, nav_series: pd.Series) -> pd.Series:
        """水下图数据（回撤序列）"""
        cummax = nav_series.cummax()
        drawdown = (nav_series - cummax) / cummax
        return drawdown


# 创建默认实例
performance_analyzer = PerformanceAnalyzer()