"""
绩效分析模块
"""

import pandas as pd
import numpy as np
from typing import Dict, Optional


class PerformanceAnalyzer:
    """
    绩效分析器

    计算各类绩效指标:
    - 收益指标: 累计收益、年化收益
    - 风险指标: 最大回撤、波动率
    - 风险调整收益: Sharpe、Sortino、Calmar
    - 相对指标: Alpha、Beta、跟踪误差、信息比率
    """

    def __init__(self, risk_free_rate: float = 0.03):
        """
        Args:
            risk_free_rate: 无风险利率（年化）
        """
        self.risk_free_rate = risk_free_rate

    def calculate_returns(self, nav_df: pd.DataFrame) -> pd.Series:
        """
        计算日收益率

        Args:
            nav_df: 净值DataFrame，需包含 date, nav 列

        Returns:
            日收益率Series
        """
        nav_df = nav_df.sort_values('date')
        returns = nav_df['nav'].pct_change()
        return returns.dropna()

    def annualized_return(self, total_return: float, days: int) -> float:
        """
        计算年化收益率

        Args:
            total_return: 累计收益率
            days: 交易日天数

        Returns:
            年化收益率
        """
        if days <= 0:
            return 0
        years = days / 252
        if years <= 0:
            return 0
        return (1 + total_return) ** (1 / years) - 1

    def max_drawdown(self, nav_df: pd.DataFrame) -> tuple:
        """
        计算最大回撤

        Args:
            nav_df: 净值DataFrame

        Returns:
            (max_drawdown, max_drawdown_pct, peak_date, trough_date)
        """
        nav = nav_df['nav'].values
        dates = nav_df['date'].values

        peak = np.maximum.accumulate(nav)
        drawdown = (nav - peak) / peak

        max_dd = drawdown.min()
        max_dd_idx = drawdown.argmin()
        max_dd_date = dates[max_dd_idx]

        # 找峰值
        peak_idx = nav[:max_dd_idx + 1].argmax()
        peak_date = dates[peak_idx]
        peak_value = nav[peak_idx]

        return abs(max_dd), abs(max_dd) / peak_value if peak_value > 0 else 0, peak_date, max_dd_date

    def sharpe_ratio(self, returns: pd.Series, periods_per_year: int = 252) -> float:
        """
        计算Sharpe比率

        Args:
            returns: 收益率序列
            periods_per_year: 年化周期数（252交易日）

        Returns:
            Sharpe比率
        """
        if len(returns) < 2:
            return 0

        mean_return = returns.mean()
        std_return = returns.std()

        if std_return == 0:
            return 0

        excess_return = mean_return - self.risk_free_rate / periods_per_year
        return excess_return / std_return * np.sqrt(periods_per_year)

    def sortino_ratio(self, returns: pd.Series, periods_per_year: int = 252) -> float:
        """
        计算Sortino比率

        Args:
            returns: 收益率序列
            periods_per_year: 年化周期数

        Returns:
            Sortino比率
        """
        if len(returns) < 2:
            return 0

        mean_return = returns.mean()
        downside_returns = returns[returns < 0]

        if len(downside_returns) == 0 or downside_returns.std() == 0:
            return 0

        excess_return = mean_return - self.risk_free_rate / periods_per_year
        downside_std = downside_returns.std()

        return excess_return / downside_std * np.sqrt(periods_per_year)

    def calmar_ratio(self, annual_return: float, max_drawdown: float) -> float:
        """
        计算Calmar比率

        Args:
            annual_return: 年化收益率
            max_drawdown: 最大回撤

        Returns:
            Calmar比率
        """
        if max_drawdown == 0:
            return 0
        return annual_return / max_drawdown

    def alpha_beta(self, portfolio_returns: pd.Series,
                   benchmark_returns: pd.Series) -> tuple:
        """
        计算Alpha和Beta

        使用回归: Rp = alpha + beta * Rb + epsilon

        Args:
            portfolio_returns: 组合收益率
            benchmark_returns: 基准收益率

        Returns:
            (alpha, beta)
        """
        # 对齐
        aligned = pd.DataFrame({
            'portfolio': portfolio_returns,
            'benchmark': benchmark_returns
        }).dropna()

        if len(aligned) < 10:
            return 0, 1

        p_returns = aligned['portfolio'].values
        b_returns = aligned['benchmark'].values

        # OLS回归
        X = np.column_stack([np.ones(len(b_returns)), b_returns])
        beta = np.linalg.lstsq(X, p_returns, rcond=None)[0]

        alpha = beta[0] * 252  # 年化alpha
        beta_value = beta[1]

        return alpha, beta_value

    def turnover(self, trades_df: pd.DataFrame, nav_df: pd.DataFrame) -> float:
        """
        计算换手率

        Args:
            trades_df: 交易记录
            nav_df: 净值记录

        Returns:
            平均换手率
        """
        if trades_df.empty or nav_df.empty:
            return 0

        # 按日期统计交易金额
        trades_df = trades_df.copy()
        trades_df['trade_value'] = trades_df['price'] * trades_df['quantity']

        daily_turnover = []
        nav_values = nav_df.set_index('date')['total_value']

        for date in trades_df['date'].unique():
            day_trades = trades_df[trades_df['date'] == date]
            trade_value = day_trades['trade_value'].sum()

            if date in nav_values.index:
                nav_value = nav_values.loc[date]
                if nav_value > 0:
                    daily_turnover.append(trade_value / nav_value)

        return np.mean(daily_turnover) if daily_turnover else 0

    def analyze(self, nav_df: pd.DataFrame, initial_cash: float) -> Dict:
        """
        综合绩效分析

        Args:
            nav_df: 净值DataFrame
            initial_cash: 初始资金

        Returns:
            绩效指标字典
        """
        nav_df = nav_df.sort_values('date').reset_index(drop=True)

        # 基本信息
        days = len(nav_df)
        total_value = nav_df['nav'].iloc[-1] * initial_cash
        total_return = nav_df['nav'].iloc[-1] - 1

        # 收益率序列
        returns = self.calculate_returns(nav_df)

        # 年化收益
        annual_return = self.annualized_return(total_return, days)

        # 最大回撤
        max_dd, max_dd_pct, peak_date, trough_date = self.max_drawdown(nav_df)

        # 夏普比率
        sharpe = self.sharpe_ratio(returns)

        # 索提诺比率
        sortino = self.sortino_ratio(returns)

        # 卡玛比率
        calmar = self.calmar_ratio(annual_return, max_dd_pct)

        # Alpha/Beta（如果有基准）
        alpha, beta = 0, 1
        if 'benchmark_nav' in nav_df.columns:
            bench_returns = nav_df['benchmark_nav'].pct_change().dropna()
            aligned_portfolio = returns.iloc[:len(bench_returns)]
            alpha, beta = self.alpha_beta(aligned_portfolio, bench_returns)

        # 收益波动率
        volatility = returns.std() * np.sqrt(252)

        # 胜率
        win_rate = (returns > 0).mean()

        return {
            'basic': {
                'start_date': str(nav_df['date'].iloc[0])[:10],
                'end_date': str(nav_df['date'].iloc[-1])[:10],
                'days': days,
                'initial_cash': initial_cash,
                'final_value': total_value,
                'total_return': total_return,
                'total_return_pct': total_return * 100,
                'annual_return': annual_return,
                'annual_return_pct': annual_return * 100,
            },
            'risk': {
                'max_drawdown': max_dd_pct,
                'max_drawdown_pct': max_dd_pct * 100,
                'volatility': volatility,
                'volatility_pct': volatility * 100,
                'peak_date': str(peak_date)[:10] if peak_date else '',
                'trough_date': str(trough_date)[:10] if trough_date else '',
            },
            'risk_adjusted': {
                'sharpe_ratio': sharpe,
                'sortino_ratio': sortino,
                'calmar_ratio': calmar,
            },
            'relative': {
                'alpha': alpha,
                'beta': beta,
            },
            'trading': {
                'win_rate': win_rate,
                'win_rate_pct': win_rate * 100,
                'avg_return': returns.mean(),
                'avg_return_pct': returns.mean() * 100,
            }
        }

    def print_summary(self, results: Dict) -> None:
        """
        打印绩效摘要
        """
        basic = results['basic']
        risk = results['risk']
        risk_adj = results['risk_adjusted']
        rel = results['relative']
        trading = results['trading']

        print("\n" + "=" * 50)
        print("回测绩效摘要")
        print("=" * 50)
        print(f"回测期间: {basic['start_date']} ~ {basic['end_date']} ({basic['days']}天)")
        print(f"初始资金: {basic['initial_cash']:,.2f}")
        print(f"最终市值: {basic['final_value']:,.2f}")
        print(f"总收益率: {basic['total_return_pct']:.2f}%")
        print(f"年化收益率: {basic['annual_return_pct']:.2f}%")
        print()
        print(f"最大回撤: {risk['max_drawdown_pct']:.2f}%")
        print(f"年化波动率: {risk['volatility_pct']:.2f}%")
        print()
        print(f"Sharpe比率: {risk_adj['sharpe_ratio']:.3f}")
        print(f"Sortino比率: {risk_adj['sortino_ratio']:.3f}")
        print(f"Calmar比率: {risk_adj['calmar_ratio']:.3f}")
        print()
        print(f"Alpha: {rel['alpha']:.4f}")
        print(f"Beta: {rel['beta']:.4f}")
        print()
        print(f"胜率: {trading['win_rate_pct']:.2f}%")
        print("=" * 50)
