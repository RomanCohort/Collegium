"""
回测引擎
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Callable
from datetime import datetime

from .broker import SimBroker
from ..strategy.multifactor import MultiFactorStrategy
from ..strategy.portfolio import PortfolioConstructor
from ..utils import log


class BacktestEngine:
    """
    事件驱动回测引擎

    流程:
    1. 初始化（设置初始资金、参数）
    2. 按日期遍历历史数据
    3. 调仓日：生成信号 -> 构建组合 -> 调仓
    4. 非调仓日：更新价格 -> 记录市值
    5. 汇总结果
    """

    def __init__(self, initial_cash: float = 1000000,
                 commission_rate: float = 0.0003,
                 stamp_tax: float = 0.001,
                 slippage: float = 0.001):
        """
        Args:
            initial_cash: 初始资金
            commission_rate: 佣金率
            stamp_tax: 印花税率
            slippage: 滑点
        """
        self.initial_cash = initial_cash
        self.commission_rate = commission_rate
        self.stamp_tax = stamp_tax
        self.slippage = slippage

        # 回测状态
        self.start_date = None
        self.end_date = None
        self.benchmark_code = None
        self.trade_calendar = None
        self.price_data = None
        self.financial_data = None

        # 策略
        self.strategy = None
        self.portfolio_constructor = None

        # 结果
        self.broker = None
        self.results = {}

    def set_data(self, price_data: pd.DataFrame,
                financial_data: pd.DataFrame = None,
                trade_calendar: pd.DataFrame = None,
                benchmark_data: pd.DataFrame = None):
        """
        设置回测数据

        Args:
            price_data: 价格数据，需包含 [code, date, open, high, low, close, volume]
            financial_data: 财务数据
            trade_calendar: 交易日历
            benchmark_data: 基准数据（指数日线）
        """
        self.price_data = price_data
        self.financial_data = financial_data
        self.trade_calendar = trade_calendar
        self.benchmark_data = benchmark_data

        if trade_calendar is not None and len(trade_calendar) > 0:
            self.trade_calendar = trade_calendar.sort_values('date')

        log.info(f"数据已加载: {len(price_data)} 条行情数据")

    def set_strategy(self, strategy: MultiFactorStrategy,
                    rebalance_freq: str = 'monthly',
                    top_n: int = 50):
        """
        设置策略

        Args:
            strategy: 多因子策略实例
            rebalance_freq: 调仓频率 'daily'/'weekly'/'monthly'
            top_n: 持仓股票数量
        """
        self.strategy = strategy
        self.rebalance_freq = rebalance_freq
        self.top_n = top_n
        self.portfolio_constructor = PortfolioConstructor(
            max_weight=1.0 / top_n,
            min_weight=0.001,
            industry_constraint=True
        )

    def _is_rebalance_day(self, date: str) -> bool:
        """
        判断是否为调仓日

        Args:
            date: 日期 YYYY-MM-DD

        Returns:
            是否调仓
        """
        dt = pd.to_datetime(date)

        if self.rebalance_freq == 'daily':
            return True
        elif self.rebalance_freq == 'weekly':
            return dt.weekday() == 0  # 周一
        elif self.rebalance_freq == 'monthly':
            return dt.day <= 5  # 月初5个交易日
        else:
            return True

    def _get_target_positions(self, date: str) -> Dict[str, float]:
        """
        获取目标持仓

        Args:
            date: 调仓日期

        Returns:
            目标持仓权重 {code: weight}
        """
        # 筛选指定日期的数据
        date_data = self.price_data[self.price_data['date'] == date]
        if date_data.empty:
            return {}

        # 生成选股信号
        signals = self.strategy.generate_signals(
            self.price_data,
            self.financial_data,
            date=date
        )

        if signals.empty:
            return {}

        # 构建组合
        weights = self.portfolio_constructor.construct(
            signals,
            method='score',
        )

        return weights

    def _rebalance(self, date: str, target_weights: Dict[str, float],
                  current_prices: Dict[str, float]) -> None:
        """
        执行调仓

        Args:
            date: 日期
            target_weights: 目标权重
            current_prices: 当前价格
        """
        if not target_weights:
            return

        total_value = self.broker.get_portfolio_value()
        target_positions = {}

        # 计算目标持仓
        for code, weight in target_weights.items():
            target_value = total_value * weight
            price = current_prices.get(code, 0)
            if price > 0:
                quantity = int(target_value / price / 100) * 100  # 取整手
                if quantity > 0:
                    target_positions[code] = quantity

        # 当前持仓
        current_positions = self.broker.positions

        # 调仓
        # 1. 卖出不在目标持仓中的股票
        for code in current_positions:
            if code not in target_positions:
                pos = current_positions[code]
                self.broker.sell(code, current_prices.get(code, pos.current_price), pos.quantity)

        # 2. 买入目标持仓中的股票
        for code, quantity in target_positions.items():
            current_qty = current_positions.get(code, Position(0, 0, 0, 0)).quantity if code in current_positions else 0
            delta_qty = quantity - current_qty

            if delta_qty > 0:
                self.broker.buy(code, current_prices.get(code, 0), delta_qty)
            elif delta_qty < 0:
                self.broker.sell(code, current_prices.get(code, 0), -delta_qty)

    def run(self, start_date: str, end_date: str, benchmark_code: str = '000300.SH') -> Dict:
        """
        运行回测

        Args:
            start_date: 开始日期 YYYY-MM-DD
            end_date: 结束日期 YYYY-MM-DD
            benchmark_code: 基准指数代码

        Returns:
            回测结果字典
        """
        log.info(f"开始回测: {start_date} ~ {end_date}")
        log.info(f"初始资金: {self.initial_cash:,.2f}")

        # 初始化
        self.start_date = start_date
        self.end_date = end_date
        self.benchmark_code = benchmark_code

        self.broker = SimBroker(
            initial_cash=self.initial_cash,
            commission_rate=self.commission_rate,
            stamp_tax=self.stamp_tax,
            slippage=self.slippage
        )

        # 获取交易日列表
        if self.trade_calendar is not None:
            trading_days = self.trade_calendar[
                (self.trade_calendar['date'] >= start_date) &
                (self.trade_calendar['date'] <= end_date)
            ]['date'].tolist()
        else:
            trading_days = sorted(self.price_data['date'].unique())
            trading_days = [d for d in trading_days if start_date <= d <= end_date]

        log.info(f"回测交易日数: {len(trading_days)}")

        # 获取基准净值
        if self.benchmark_data is not None:
            benchmark_df = self.benchmark_data[self.benchmark_data['code'] == benchmark_code]
            if not benchmark_df.empty:
                start_price = benchmark_df[benchmark_df['date'] == start_date]['close'].values
                if len(start_price) > 0:
                    benchmark_df['benchmark_nav'] = benchmark_df['close'] / start_price[0]
                    benchmark_nav_dict = benchmark_df.set_index('date')['benchmark_nav'].to_dict()
                else:
                    benchmark_nav_dict = {}
            else:
                benchmark_nav_dict = {}
        else:
            benchmark_nav_dict = {}

        # 逐日回测
        rebalance_count = 0
        for i, date in enumerate(trading_days):
            date_str = str(date)[:10] if isinstance(date, pd.Timestamp) else str(date)[:10]

            # 获取当日收盘价
            day_data = self.price_data[self.price_data['date'] == date_str]
            prices = {}
            for _, row in day_data.iterrows():
                code = row['code']
                close = row['close']
                if code not in prices:  # 取收盘价
                    prices[code] = close

            # 更新持仓价格
            self.broker.update_prices(prices)

            # 检查是否调仓
            if self._is_rebalance_day(date_str):
                log.info(f"调仓日: {date_str}")
                target_weights = self._get_target_positions(date_str)
                self._rebalance(date_str, target_weights, prices)
                rebalance_count += 1

            # 记录每日市值
            benchmark_nav = benchmark_nav_dict.get(date_str, None)
            self.broker.record_daily_value(date_str, benchmark_nav)

            # 打印进度
            if (i + 1) % 60 == 0:
                total_value = self.broker.get_portfolio_value()
                log.info(f"进度: {i+1}/{len(trading_days)}, 市值: {total_value:,.2f}")

        # 生成结果
        self.results = self._generate_results()
        log.info(f"回测完成! 调仓次数: {rebalance_count}")

        return self.results

    def _generate_results(self) -> Dict:
        """
        生成回测结果
        """
        # 每日净值
        nav_df = pd.DataFrame(self.broker.daily_value)
        if nav_df.empty:
            return {}

        nav_df['nav'] = nav_df['total_value'] / self.initial_cash

        if 'benchmark_value' in nav_df.columns:
            nav_df['benchmark_nav'] = nav_df['benchmark_value'] / nav_df['benchmark_value'].iloc[0]
            nav_df['excess_return'] = nav_df['nav'] - nav_df['benchmark_nav']

        # 计算绩效指标
        performance = self._calculate_performance(nav_df)

        return {
            'nav': nav_df,
            'trades': pd.DataFrame([{
                'code': t.code,
                'direction': t.direction,
                'price': t.price,
                'quantity': t.quantity,
                'commission': t.commission,
                'stamp_tax': t.stamp_tax,
            } for t in self.broker.trades]),
            'positions': self.broker.get_positions(),
            'performance': performance,
        }

    def _calculate_performance(self, nav_df: pd.DataFrame) -> Dict:
        """
        计算绩效指标
        """
        from .performance import PerformanceAnalyzer

        analyzer = PerformanceAnalyzer()
        return analyzer.analyze(nav_df, self.initial_cash)
