"""
模拟券商接口 - 用于回测
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional
from dataclasses import dataclass
from datetime import datetime

from ..utils import log


@dataclass
class Order:
    """交易订单"""
    code: str
    direction: str  # 'buy' / 'sell'
    price: float
    quantity: int
    order_type: str = 'market'  # 'market' / 'limit'


@dataclass
class Trade:
    """成交记录"""
    code: str
    direction: str
    price: float
    quantity: int
    commission: float
    stamp_tax: float = 0.0
    timestamp: str = ''


@dataclass
class Position:
    """持仓"""
    code: str
    quantity: int
    avg_cost: float
    current_price: float

    @property
    def market_value(self) -> float:
        return self.quantity * self.current_price

    @property
    def profit(self) -> float:
        return (self.current_price - self.avg_cost) * self.quantity

    @property
    def profit_pct(self) -> float:
        if self.avg_cost == 0:
            return 0
        return (self.current_price - self.avg_cost) / self.avg_cost


class SimBroker:
    """
    模拟券商接口

    模拟真实交易流程:
    1. 下单 -> 成交（考虑滑点）
    2. 计算交易成本（佣金、印花税）
    3. 更新持仓
    """

    def __init__(self, initial_cash: float = 1000000,
                 commission_rate: float = 0.0003,
                 stamp_tax: float = 0.001,
                 slippage: float = 0.001):
        """
        Args:
            initial_cash: 初始资金
            commission_rate: 佣金率（万分之3）
            stamp_tax: 印花税率（千分之1，卖出时收取）
            slippage: 滑点（千分之1）
        """
        self.initial_cash = initial_cash
        self.cash = initial_cash
        self.commission_rate = commission_rate
        self.stamp_tax = stamp_tax
        self.slippage = slippage
        self.positions: Dict[str, Position] = {}
        self.trades: List[Trade] = []
        self.daily_value: List[Dict] = []

    def buy(self, code: str, price: float, quantity: int) -> Optional[Trade]:
        """
        买入股票

        Args:
            code: 股票代码
            price: 当前价格（考虑滑点）
            quantity: 买入数量（手）

        Returns:
            成交记录或None
        """
        # 考虑滑点
        execution_price = price * (1 + self.slippage)

        # 计算交易成本
        turnover = execution_price * quantity
        commission = max(5, turnover * self.commission_rate)  # 最低佣金5元

        total_cost = turnover + commission

        # 检查资金
        if total_cost > self.cash:
            log.warning(f"资金不足，无法买入 {code}: 需要 {total_cost:.2f}, 可用 {self.cash:.2f}")
            return None

        # 更新现金和持仓
        self.cash -= total_cost

        if code in self.positions:
            pos = self.positions[code]
            total_quantity = pos.quantity + quantity
            pos.avg_cost = (pos.avg_cost * pos.quantity + execution_price * quantity) / total_quantity
            pos.quantity = total_quantity
            pos.current_price = execution_price
        else:
            self.positions[code] = Position(
                code=code,
                quantity=quantity,
                avg_cost=execution_price,
                current_price=execution_price
            )

        trade = Trade(
            code=code,
            direction='buy',
            price=execution_price,
            quantity=quantity,
            commission=commission
        )
        self.trades.append(trade)

        log.debug(f"买入 {code}: 价格={execution_price:.2f}, 数量={quantity}, 佣金={commission:.2f}")
        return trade

    def sell(self, code: str, price: float, quantity: int) -> Optional[Trade]:
        """
        卖出股票

        Args:
            code: 股票代码
            price: 当前价格
            quantity: 卖出数量

        Returns:
            成交记录或None
        """
        if code not in self.positions:
            log.warning(f"没有持仓 {code}，无法卖出")
            return None

        pos = self.positions[code]
        if pos.quantity < quantity:
            log.warning(f"持仓不足 {code}: 持有{pos.quantity}, 卖出{quantity}")
            quantity = pos.quantity

        if quantity <= 0:
            return None

        # 考虑滑点（卖出时滑点对投资者不利）
        execution_price = price * (1 - self.slippage)

        # 计算交易成本
        turnover = execution_price * quantity
        commission = max(5, turnover * self.commission_rate)
        stamp = turnover * self.stamp_tax  # 印花税

        total_proceeds = turnover - commission - stamp

        # 更新现金和持仓
        self.cash += total_proceeds

        pos.quantity -= quantity
        if pos.quantity == 0:
            del self.positions[code]
        else:
            pos.current_price = execution_price

        trade = Trade(
            code=code,
            direction='sell',
            price=execution_price,
            quantity=quantity,
            commission=commission,
            stamp_tax=stamp
        )
        self.trades.append(trade)

        log.debug(f"卖出 {code}: 价格={execution_price:.2f}, 数量={quantity}, 佣金={commission:.2f}, 印花税={stamp:.2f}")
        return trade

    def update_prices(self, prices: Dict[str, float]) -> None:
        """
        更新持仓的当前价格

        Args:
            prices: {code: price} 价格字典
        """
        for code, price in prices.items():
            if code in self.positions:
                self.positions[code].current_price = price

    def get_portfolio_value(self) -> float:
        """
        获取总资产市值

        Returns:
            总资产（含现金+持仓市值）
        """
        positions_value = sum(pos.market_value for pos in self.positions.values())
        return self.cash + positions_value

    def get_positions(self) -> pd.DataFrame:
        """
        获取当前持仓

        Returns:
            持仓DataFrame
        """
        if not self.positions:
            return pd.DataFrame()

        data = []
        for code, pos in self.positions.items():
            data.append({
                'code': code,
                'quantity': pos.quantity,
                'avg_cost': pos.avg_cost,
                'current_price': pos.current_price,
                'market_value': pos.market_value,
                'profit': pos.profit,
                'profit_pct': pos.profit_pct,
            })

        df = pd.DataFrame(data)
        df = df.sort_values('market_value', ascending=False)
        return df

    def record_daily_value(self, date: str, benchmark_value: float = None) -> None:
        """
        记录每日市值

        Args:
            date: 日期
            benchmark_value: 基准当日净值
        """
        self.daily_value.append({
            'date': date,
            'cash': self.cash,
            'positions_value': sum(pos.market_value for pos in self.positions.values()),
            'total_value': self.get_portfolio_value(),
            'benchmark_value': benchmark_value,
        })

    def reset(self) -> None:
        """重置账户"""
        self.cash = self.initial_cash
        self.positions = {}
        self.trades = []
        self.daily_value = []
