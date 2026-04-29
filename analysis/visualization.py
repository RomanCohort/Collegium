"""
可视化模块
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib import rcParams

# 设置中文字体
rcParams['font.sans-serif'] = ['SimHei', 'DejaVu Sans', 'Arial Unicode MS']
rcParams['axes.unicode_minus'] = False


class Visualizer:
    """
    回测结果可视化
    """

    def __init__(self, figsize: tuple = (14, 8)):
        """
        Args:
            figsize: 图形大小
        """
        self.figsize = figsize

    def plot_nav(self, nav_df: pd.DataFrame,
                benchmark_col: str = 'benchmark_nav',
                title: str = "净值曲线") -> plt.Figure:
        """
        绘制净值曲线

        Args:
            nav_df: 净值DataFrame，需包含 date, nav 列
            benchmark_col: 基准净值列名
            title: 图表标题

        Returns:
            matplotlib Figure
        """
        fig, ax = plt.subplots(figsize=self.figsize)

        nav_df = nav_df.copy()
        nav_df['date'] = pd.to_datetime(nav_df['date'])

        # 组合净值
        ax.plot(nav_df['date'], nav_df['nav'], label='组合净值', linewidth=2, color='#1f77b4')

        # 基准净值
        if benchmark_col in nav_df.columns:
            ax.plot(nav_df['date'], nav_df[benchmark_col],
                   label='基准净值', linewidth=1.5, color='gray', alpha=0.7)

        ax.set_xlabel('日期', fontsize=12)
        ax.set_ylabel('净值', fontsize=12)
        ax.set_title(title, fontsize=14, fontweight='bold')
        ax.legend(loc='upper left')
        ax.grid(True, alpha=0.3)

        # 日期格式
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
        ax.xaxis.set_major_locator(mdates.MonthLocator(interval=3))
        plt.xticks(rotation=45)

        plt.tight_layout()
        return fig

    def plot_drawdown(self, nav_df: pd.DataFrame, title: str = "回撤曲线") -> plt.Figure:
        """
        绘制回撤曲线

        Args:
            nav_df: 净值DataFrame
            title: 图表标题

        Returns:
            matplotlib Figure
        """
        fig, ax = plt.subplots(figsize=self.figsize)

        nav_df = nav_df.copy()
        nav_df['date'] = pd.to_datetime(nav_df['date'])

        # 计算回撤
        nav = nav_df['nav'].values
        peak = np.maximum.accumulate(nav)
        drawdown = (nav - peak) / peak * 100  # 转为百分比

        ax.fill_between(nav_df['date'], drawdown, 0,
                       color='red', alpha=0.3, label='回撤')
        ax.plot(nav_df['date'], drawdown, color='red', linewidth=1)

        ax.set_xlabel('日期', fontsize=12)
        ax.set_ylabel('回撤 (%)', fontsize=12)
        ax.set_title(title, fontsize=14, fontweight='bold')
        ax.legend(loc='lower left')
        ax.grid(True, alpha=0.3)

        ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
        ax.xaxis.set_major_locator(mdates.MonthLocator(interval=3))
        plt.xticks(rotation=45)

        plt.tight_layout()
        return fig

    def plot_returns(self, nav_df: pd.DataFrame, title: str = "收益分布") -> plt.Figure:
        """
        绘制收益分布直方图

        Args:
            nav_df: 净值DataFrame
            title: 图表标题

        Returns:
            matplotlib Figure
        """
        fig, axes = plt.subplots(1, 2, figsize=(14, 5))

        nav_df = nav_df.copy()
        nav_df['date'] = pd.to_datetime(nav_df['date'])

        # 日收益率
        returns = nav_df['nav'].pct_change().dropna() * 100

        # 直方图
        axes[0].hist(returns, bins=50, color='steelblue', alpha=0.7, edgecolor='white')
        axes[0].axvline(returns.mean(), color='red', linestyle='--', label=f'均值: {returns.mean():.2f}%')
        axes[0].axvline(0, color='black', linestyle='-', linewidth=0.5)
        axes[0].set_xlabel('日收益率 (%)', fontsize=12)
        axes[0].set_ylabel('频数', fontsize=12)
        axes[0].set_title('日收益率分布', fontsize=14)
        axes[0].legend()
        axes[0].grid(True, alpha=0.3)

        # 滚动收益
        rolling_returns = returns.rolling(window=20).mean() * 20  # 20日滚动收益
        axes[1].plot(nav_df['date'].iloc[1:], rolling_returns.iloc[1:],
                    color='steelblue', linewidth=1)
        axes[1].axhline(0, color='black', linestyle='-', linewidth=0.5)
        axes[1].set_xlabel('日期', fontsize=12)
        axes[1].set_ylabel('收益 (%)', fontsize=12)
        axes[1].set_title('20日滚动收益', fontsize=14)
        axes[1].grid(True, alpha=0.3)

        axes[1].xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
        axes[1].xaxis.set_major_locator(mdates.MonthLocator(interval=3))
        plt.setp(axes[1].xaxis.get_majorticklabels(), rotation=45)

        plt.suptitle(title, fontsize=14, fontweight='bold')
        plt.tight_layout()
        return fig

    def plot_ic(self, ic_results: Dict[str, pd.DataFrame],
               title: str = "IC分析") -> plt.Figure:
        """
        绘制IC分析图

        Args:
            ic_results: IC结果字典 {period: ic_df}
            title: 图表标题

        Returns:
            matplotlib Figure
        """
        fig, axes = plt.subplots(2, 1, figsize=(14, 10))

        for period, ic_df in ic_results.items():
            ic_df = ic_df.copy()
            ic_df['date'] = pd.to_datetime(ic_df['date'])

            # IC时序图
            axes[0].plot(ic_df['date'], ic_df['ic'], label=period, linewidth=1, alpha=0.8)
            axes[0].axhline(0, color='black', linestyle='-', linewidth=0.5)

            # IC柱状图（累计）
            if period == list(ic_results.keys())[0]:  # 只画第一个
                ic_cumsum = ic_df['ic'].cumsum()
                axes[1].bar(ic_df['date'], ic_cumsum, width=1, alpha=0.5)

        axes[0].set_xlabel('日期', fontsize=12)
        axes[0].set_ylabel('IC', fontsize=12)
        axes[0].set_title('IC时序图', fontsize=14)
        axes[0].legend()
        axes[0].grid(True, alpha=0.3)

        axes[1].set_xlabel('日期', fontsize=12)
        axes[1].set_ylabel('IC累计', fontsize=12)
        axes[1].set_title('IC累计', fontsize=14)
        axes[1].grid(True, alpha=0.3)

        plt.suptitle(title, fontsize=14, fontweight='bold')
        plt.tight_layout()
        return fig

    def plot_group_returns(self, group_result: pd.DataFrame,
                          n_groups: int = 10,
                          title: str = "分组收益") -> plt.Figure:
        """
        绘制分组收益图

        Args:
            group_result: 分组测试结果
            n_groups: 分组数

        Returns:
            matplotlib Figure
        """
        fig, ax = plt.subplots(figsize=(10, 6))

        # 计算每组平均收益
        group_returns = group_result.groupby('group')['return'].mean() * 100

        colors = plt.cm.RdYlGn(np.linspace(0, 1, n_groups))
        bars = ax.bar(range(n_groups), group_returns.values, color=colors, edgecolor='white')

        # 添加数值标签
        for bar, val in zip(bars, group_returns.values):
            height = bar.get_height()
            ax.annotate(f'{val:.2f}%',
                       xy=(bar.get_x() + bar.get_width() / 2, height),
                       xytext=(0, 3 if height >= 0 else -15),
                       textcoords="offset points",
                       ha='center', va='bottom' if height >= 0 else 'top',
                       fontsize=9)

        ax.set_xlabel('因子分组 (1=低因子值, 10=高因子值)', fontsize=12)
        ax.set_ylabel('平均收益 (%)', fontsize=12)
        ax.set_title(title, fontsize=14, fontweight='bold')
        ax.set_xticks(range(n_groups))
        ax.set_xticklabels([str(i+1) for i in range(n_groups)])
        ax.axhline(0, color='black', linestyle='-', linewidth=0.5)
        ax.grid(True, alpha=0.3, axis='y')

        plt.tight_layout()
        return fig

    def plot_positions(self, positions_df: pd.DataFrame,
                      title: str = "持仓分布") -> plt.Figure:
        """
        绘制持仓分布饼图

        Args:
            positions_df: 持仓DataFrame
            title: 图表标题

        Returns:
            matplotlib Figure
        """
        if positions_df.empty:
            fig, ax = plt.subplots(figsize=(8, 6))
            ax.text(0.5, 0.5, '无持仓数据', ha='center', va='center', fontsize=14)
            ax.axis('off')
            return fig

        fig, axes = plt.subplots(1, 2, figsize=(14, 6))

        # 市值分布
        top_n = min(10, len(positions_df))
        top_positions = positions_df.head(top_n).copy()
        top_positions['label'] = top_positions['code']

        colors = plt.cm.Set3(range(top_n))
        axes[0].pie(top_positions['market_value'], labels=top_positions['label'],
                   autopct='%1.1f%%', colors=colors, startangle=90)
        axes[0].set_title(f'市值分布 (Top {top_n})', fontsize=14)

        # 行业分布（如果有）
        if 'industry' in positions_df.columns:
            industry_value = positions_df.groupby('industry')['market_value'].sum()
            industry_value = industry_value.sort_values(ascending=False)
            colors = plt.cm.Pastel1(range(len(industry_value)))
            axes[1].pie(industry_value.values, labels=industry_value.index,
                       autopct='%1.1f%%', colors=colors, startangle=90)
            axes[1].set_title('行业分布', fontsize=14)
        else:
            # 收益分布
            axes[1].barh(top_positions['code'], top_positions['profit_pct'] * 100,
                        color=['green' if x >= 0 else 'red' for x in top_positions['profit_pct']])
            axes[1].set_xlabel('收益率 (%)', fontsize=12)
            axes[1].set_title('各持仓收益 (%)', fontsize=14)
            axes[1].grid(True, alpha=0.3, axis='x')

        plt.suptitle(title, fontsize=14, fontweight='bold')
        plt.tight_layout()
        return fig

    def save_figure(self, fig: plt.Figure, filename: str,
                   dpi: int = 150) -> None:
        """
        保存图表到文件

        Args:
            fig: matplotlib Figure
            filename: 文件名
            dpi: 分辨率
        """
        fig.savefig(filename, dpi=dpi, bbox_inches='tight')
        print(f"图表已保存: {filename}")
