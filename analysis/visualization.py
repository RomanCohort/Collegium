"""
可视化模块
"""
import pandas as pd
import numpy as np
from typing import Optional, List
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use('Agg')  # 非交互式后端
import matplotlib.dates as mdates
from pathlib import Path

# 设置中文字体
plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'Arial Unicode MS']
plt.rcParams['axes.unicode_minus'] = False


class Visualizer:
    """可视化工具"""

    def __init__(self, figsize: tuple = (12, 6), style: str = "seaborn-v0_8"):
        self.figsize = figsize
        self.style = style
        try:
            plt.style.use(style)
        except Exception:
            pass

    def plot_nav_curve(
        self,
        nav_series: pd.Series,
        benchmark: Optional[pd.Series] = None,
        save_path: str = None,
        title: str = "净值曲线",
    ) -> plt.Figure:
        """
        绘制净值曲线

        Args:
            nav_series: 净值序列
            benchmark: 基准净值（可选）
            save_path: 保存路径
            title: 图表标题

        Returns:
            matplotlib Figure
        """
        fig, ax = plt.subplots(figsize=self.figsize)

        ax.plot(nav_series.index, nav_series.values, label="策略", linewidth=2, color="#4CAF50")

        if benchmark is not None:
            aligned = nav_series.reindex(benchmark.index).dropna()
            if len(aligned) > 0:
                ax.plot(aligned.index, benchmark.loc[aligned.index].values,
                        label="基准", linewidth=1.5, color="#2196F3", alpha=0.7)

        ax.set_title(title, fontsize=14, fontweight="bold")
        ax.set_xlabel("日期")
        ax.set_ylabel("净值")
        ax.legend()
        ax.grid(True, alpha=0.3)
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))
        ax.xaxis.set_major_locator(mdates.MonthLocator(interval=3))
        plt.xticks(rotation=45)

        plt.tight_layout()

        if save_path:
            plt.savefig(save_path, dpi=150, bbox_inches="tight")

        return fig

    def plot_drawdown(
        self,
        nav_series: pd.Series,
        save_path: str = None,
        title: str = "回撤曲线",
    ) -> plt.Figure:
        """绘制回撤曲线"""
        fig, ax = plt.subplots(figsize=self.figsize)

        cummax = nav_series.cummax()
        drawdown = (nav_series - cummax) / cummax * 100

        ax.fill_between(drawdown.index, drawdown.values, 0,
                       color="#f44336", alpha=0.3, label="回撤")
        ax.plot(drawdown.index, drawdown.values, color="#f44336", linewidth=1.5)

        ax.set_title(title, fontsize=14, fontweight="bold")
        ax.set_xlabel("日期")
        ax.set_ylabel("回撤 (%)")
        ax.grid(True, alpha=0.3)
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))
        plt.xticks(rotation=45)

        # 标注最大回撤
        max_dd = drawdown.min()
        max_dd_date = drawdown.idxmin()
        ax.annotate(f"最大回撤: {max_dd:.1f}%",
                    xy=(max_dd_date, max_dd),
                    xytext=(10, -20),
                    textcoords="offset points",
                    arrowprops=dict(arrowstyle="->", color="#f44336"),
                    fontsize=10, color="#f44336")

        plt.tight_layout()

        if save_path:
            plt.savefig(save_path, dpi=150, bbox_inches="tight")

        return fig

    def plot_returns_distribution(
        self,
        returns: pd.Series,
        save_path: str = None,
        title: str = "收益分布",
    ) -> plt.Figure:
        """绘制收益分布直方图"""
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))

        # 直方图
        ax1.hist(returns.dropna(), bins=50, color="#4CAF50", alpha=0.7, edgecolor="white")
        ax1.axvline(returns.mean(), color="#f44336", linestyle="--", linewidth=2, label=f"均值: {returns.mean():.4f}")
        ax1.axvline(0, color="#333", linestyle="-", linewidth=1)
        ax1.set_title(f"{title} - 直方图", fontsize=12)
        ax1.set_xlabel("日收益率")
        ax1.set_ylabel("频数")
        ax1.legend()
        ax1.grid(True, alpha=0.3)

        # 箱线图
        ax2.boxplot(returns.dropna(), vert=True, patch_artist=True,
                    boxprops=dict(facecolor="#4CAF50", alpha=0.5))
        ax2.set_title(f"{title} - 箱线图", fontsize=12)
        ax2.set_ylabel("日收益率")
        ax2.grid(True, alpha=0.3)

        plt.tight_layout()

        if save_path:
            plt.savefig(save_path, dpi=150, bbox_inches="tight")

        return fig

    def plot_rolling_metrics(
        self,
        nav_series: pd.Series,
        window: int = 60,
        save_path: str = None,
    ) -> plt.Figure:
        """绘制滚动夏普和回撤"""
        returns = nav_series.pct_change().dropna()

        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8), sharex=True)

        # 滚动夏普
        rolling_mean = returns.rolling(window).mean() * 252
        rolling_vol = returns.rolling(window).std() * np.sqrt(252)
        rolling_sharpe = (rolling_mean - 0.03) / rolling_vol

        ax1.plot(rolling_sharpe.index, rolling_sharpe.values, color="#2196F3", linewidth=1.5)
        ax1.axhline(rolling_sharpe.mean(), color="#4CAF50", linestyle="--", label=f"平均: {rolling_sharpe.mean():.2f}")
        ax1.axhline(0, color="#333", linestyle="-", alpha=0.5)
        ax1.set_title(f"滚动{window}日夏普比率", fontsize=12)
        ax1.set_ylabel("夏普比率")
        ax1.legend()
        ax1.grid(True, alpha=0.3)

        # 滚动最大回撤
        rolling_max = nav_series.rolling(window).max()
        rolling_dd = (nav_series - rolling_max) / rolling_max * 100

        ax2.fill_between(rolling_dd.index, rolling_dd.values, 0,
                        color="#f44336", alpha=0.3)
        ax2.plot(rolling_dd.index, rolling_dd.values, color="#f44336", linewidth=1)
        ax2.set_title(f"滚动{window}日最大回撤", fontsize=12)
        ax2.set_xlabel("日期")
        ax2.set_ylabel("回撤 (%)")
        ax2.grid(True, alpha=0.3)

        plt.tight_layout()

        if save_path:
            plt.savefig(save_path, dpi=150, bbox_inches="tight")

        return fig

    def plot_trade_analysis(
        self,
        trades_df: pd.DataFrame,
        save_path: str = None,
    ) -> plt.Figure:
        """交易分析图"""
        if trades_df.empty or "pnl" not in trades_df.columns:
            return None

        fig, axes = plt.subplots(2, 2, figsize=(14, 10))

        # 累计盈亏
        pnls = trades_df[trades_df["pnl"].notna()]["pnl"]
        if len(pnls) > 0:
            cumulative_pnl = pnls.cumsum()
            axes[0, 0].plot(cumulative_pnl.values, color="#4CAF50", linewidth=2)
            axes[0, 0].axhline(0, color="#333", linestyle="-", alpha=0.5)
            axes[0, 0].set_title("累计盈亏", fontsize=12)
            axes[0, 0].set_xlabel("交易次数")
            axes[0, 0].set_ylabel("累计盈亏")
            axes[0, 0].grid(True, alpha=0.3)

        # 盈亏分布
        winning = pnls[pnls > 0]
        losing = pnls[pnls < 0]
        if len(winning) > 0 and len(losing) > 0:
            axes[0, 1].hist([winning.values, losing.values],
                           bins=30, label=["盈利", "亏损"],
                           color=["#4CAF50", "#f44336"], alpha=0.7)
            axes[0, 1].axvline(0, color="#333", linestyle="-")
            axes[0, 1].legend()
            axes[0, 1].set_title("盈亏分布", fontsize=12)
            axes[0, 1].set_xlabel("盈亏金额")
            axes[0, 1].grid(True, alpha=0.3)

        # 持仓时长 vs 盈亏
        if "holding_days" in trades_df.columns:
            axes[1, 0].scatter(trades_df["holding_days"], trades_df["pnl"],
                              alpha=0.5, color="#2196F3")
            axes[1, 0].axhline(0, color="#333", linestyle="-", alpha=0.5)
            axes[1, 0].set_title("持仓时长 vs 盈亏", fontsize=12)
            axes[1, 0].set_xlabel("持仓天数")
            axes[1, 0].set_ylabel("盈亏")
            axes[1, 0].grid(True, alpha=0.3)

        # 月度盈亏
        if "timestamp" in trades_df.columns:
            trades_df = trades_df.copy()
            trades_df["month"] = pd.to_datetime(trades_df["timestamp"]).dt.to_period("M")
            monthly_pnl = trades_df.groupby("month")["pnl"].sum()
            colors = ["#4CAF50" if v >= 0 else "#f44336" for v in monthly_pnl.values]
            axes[1, 1].bar(range(len(monthly_pnl)), monthly_pnl.values, color=colors, alpha=0.7)
            axes[1, 1].set_title("月度盈亏", fontsize=12)
            axes[1, 1].set_xlabel("月份")
            axes[1, 1].set_ylabel("盈亏")
            axes[1, 1].grid(True, alpha=0.3, axis="y")

        plt.tight_layout()

        if save_path:
            plt.savefig(save_path, dpi=150, bbox_inches="tight")

        return fig

    def plot_factor_returns(
        self,
        factor_data: pd.DataFrame,
        factor_name: str = "factor",
        save_path: str = None,
    ) -> plt.Figure:
        """因子收益分析"""
        if "returns" not in factor_data.columns or "factor_value" not in factor_data.columns:
            return None

        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8), sharex=True)

        # 因子值
        ax1.plot(factor_data.index, factor_data["factor_value"], color="#2196F3", linewidth=1)
        ax1.set_title(f"{factor_name} 因子值", fontsize=12)
        ax1.set_ylabel("因子值")
        ax1.grid(True, alpha=0.3)

        # 分组收益
        if "group" in factor_data.columns:
            for group in factor_data["group"].unique():
                group_data = factor_data[factor_data["group"] == group]
                ax2.plot(group_data.index, group_data["cumulative_return"],
                        label=f"分组 {group}", linewidth=1.5)
            ax2.legend()
        else:
            ax2.plot(factor_data.index, factor_data["cumulative_return"],
                    color="#4CAF50", linewidth=2)

        ax2.set_title(f"{factor_name} 收益", fontsize=12)
        ax2.set_xlabel("日期")
        ax2.set_ylabel("累计收益")
        ax2.grid(True, alpha=0.3)

        plt.tight_layout()

        if save_path:
            plt.savefig(save_path, dpi=150, bbox_inches="tight")

        return fig


# 创建默认实例
visualizer = Visualizer()