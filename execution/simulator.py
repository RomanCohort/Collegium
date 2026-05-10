"""
模拟交易执行模块
"""
import pandas as pd
import numpy as np
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass
from config.settings import BACKTEST_CONFIG
from utils.logger import log, trade_log


@dataclass
class ExecutionResult:
    """执行结果"""
    success: bool
    order_id: str
    symbol: str
    side: str
    quantity: int
    price: float
    commission: float
    timestamp: str
    error: str = ""


class Simulator:
    """模拟交易器（用于 Paper Trading）"""

    def __init__(self, config: dict = None):
        self.config = config or BACKTEST_CONFIG
        self.cash = self.config["initial_capital"]
        self.positions: Dict[str, Dict] = {}
        self.orders: List[Dict] = {}
        self.order_counter = 0
        self.commission_rate = self.config.get("commission_rate", 0.0003)
        self.slippage_rate = self.config.get("slippage_rate", 0.0001)

    def get_cash(self) -> float:
        """获取可用资金"""
        return self.cash

    def get_position_value(self) -> float:
        """获取持仓市值"""
        return sum(
            pos["quantity"] * pos["current_price"]
            for pos in self.positions.values()
        )

    def get_total_value(self) -> float:
        """获取总资产"""
        return self.cash + self.get_position_value()

    def get_positions(self) -> Dict[str, Dict]:
        """获取当前持仓"""
        return self.positions.copy()

    def submit_order(
        self,
        symbol: str,
        side: str,
        quantity: int,
        price: Optional[float] = None,
        order_type: str = "MARKET",
    ) -> ExecutionResult:
        """
        提交订单

        Args:
            symbol: 股票代码
            side: BUY / SELL
            quantity: 数量
            price: 价格（市价单为 None）
            order_type: MARKET / LIMIT

        Returns:
            执行结果
        """
        self.order_counter += 1
        order_id = f"ORD_{datetime.now().strftime('%Y%m%d%H%M%S')}_{self.order_counter}"

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        if order_type == "MARKET":
            # 市价单：使用参考价格
            if price is None:
                return ExecutionResult(
                    success=False,
                    order_id=order_id,
                    symbol=symbol,
                    side=side,
                    quantity=quantity,
                    price=0,
                    commission=0,
                    timestamp=timestamp,
                    error="市价单需要提供参考价格",
                )

            # 执行
            return self._execute_order(order_id, symbol, side, quantity, price, timestamp)

        else:
            # 限价单：暂不实现
            log.info(f"限价单 {order_id}: {symbol} {side} x {quantity} @ {price}")
            return ExecutionResult(
                success=True,
                order_id=order_id,
                symbol=symbol,
                side=side,
                quantity=quantity,
                price=price,
                commission=0,
                timestamp=timestamp,
                error="限价单已提交（待撮合）",
            )

    def _execute_order(
        self,
        order_id: str,
        symbol: str,
        side: str,
        quantity: int,
        price: float,
        timestamp: str,
    ) -> ExecutionResult:
        """执行订单"""
        # 计算滑点
        if side == "BUY":
            filled_price = price * (1 + self.slippage_rate)
        else:
            filled_price = price * (1 - self.slippage_rate)

        # 计算佣金
        amount = filled_price * quantity
        commission = max(amount * self.commission_rate, 5)

        # 印花税（仅卖出）
        if side == "SELL":
            stamp_duty = amount * 0.001
            commission += stamp_duty

        # 检查资金/持仓
        if side == "BUY":
            required = amount + commission
            if required > self.cash:
                return ExecutionResult(
                    success=False,
                    order_id=order_id,
                    symbol=symbol,
                    side=side,
                    quantity=quantity,
                    price=price,
                    commission=0,
                    timestamp=timestamp,
                    error=f"资金不足（需要 {required:.2f}，可用 {self.cash:.2f}）",
                )
        else:
            if symbol not in self.positions:
                return ExecutionResult(
                    success=False,
                    order_id=order_id,
                    symbol=symbol,
                    side=side,
                    quantity=quantity,
                    price=price,
                    commission=0,
                    timestamp=timestamp,
                    error="无持仓",
                )
            if self.positions[symbol]["quantity"] < quantity:
                return ExecutionResult(
                    success=False,
                    order_id=order_id,
                    symbol=symbol,
                    side=side,
                    quantity=quantity,
                    price=price,
                    commission=0,
                    timestamp=timestamp,
                    error=f"持仓不足（需要 {quantity}，持有 {self.positions[symbol]['quantity']}）",
                )

        # 更新资金和持仓
        if side == "BUY":
            self.cash -= (amount + commission)

            if symbol in self.positions:
                # 追加
                pos = self.positions[symbol]
                total_qty = pos["quantity"] + quantity
                pos["avg_price"] = (pos["avg_price"] * pos["quantity"] + filled_price * quantity) / total_qty
                pos["quantity"] = total_qty
                pos["current_price"] = filled_price
            else:
                # 新建持仓
                self.positions[symbol] = {
                    "symbol": symbol,
                    "quantity": quantity,
                    "avg_price": filled_price,
                    "current_price": filled_price,
                    "entry_date": timestamp,
                }

            trade_log("买入", symbol, filled_price, quantity, strategy="paper")

        else:
            self.cash += (amount - commission)

            pos = self.positions[symbol]
            pnl = (filled_price - pos["avg_price"]) * quantity

            pos["quantity"] -= quantity
            if pos["quantity"] <= 0:
                del self.positions[symbol]

            trade_log("卖出", symbol, filled_price, quantity, pnl=f"{pnl:.2f}")

        log.info(f"成交 {order_id}: {symbol} {side} x {quantity} @ {filled_price:.2f} 佣金 {commission:.2f}")

        return ExecutionResult(
            success=True,
            order_id=order_id,
            symbol=symbol,
            side=side,
            quantity=quantity,
            price=filled_price,
            commission=commission,
            timestamp=timestamp,
        )

    def update_prices(self, price_data: Dict[str, float]):
        """
        更新持仓价格

        Args:
            price_data: {symbol: current_price}
        """
        for symbol, price in price_data.items():
            if symbol in self.positions:
                self.positions[symbol]["current_price"] = price

    def get_pnl_summary(self) -> Dict:
        """获取盈亏汇总"""
        total_value = self.get_total_value()
        position_pnl = sum(
            (pos["current_price"] - pos["avg_price"]) * pos["quantity"]
            for pos in self.positions.values()
        )

        return {
            "cash": self.cash,
            "position_value": self.get_position_value(),
            "total_value": total_value,
            "total_pnl": total_value - self.config["initial_capital"],
            "total_pnl_pct": (total_value / self.config["initial_capital"] - 1),
            "position_pnl": position_pnl,
        }


class PaperTrading:
    """纸面交易（模拟实盘环境）"""

    def __init__(self, strategy, initial_capital: float = None):
        self.strategy = strategy
        self.simulator = Simulator()
        self.history: List[Dict] = []

    def tick(self, date: str, price_data: Dict[str, float]):
        """
        处理 tick 数据

        Args:
            date: 当前日期
            price_data: {symbol: price}
        """
        # 更新价格
        self.simulator.update_prices(price_data)

        # 生成信号并执行
        for symbol, price in price_data.items():
            if symbol in self.strategy.positions:
                continue  # 已有持仓，暂不追加

        # 记录快照
        snapshot = {
            "date": date,
            **self.simulator.get_pnl_summary(),
            "positions": len(self.simulator.positions),
        }
        self.history.append(snapshot)

    def get_status(self) -> Dict:
        """获取当前状态"""
        return self.simulator.get_pnl_summary()

    def get_history(self) -> pd.DataFrame:
        """获取历史记录"""
        return pd.DataFrame(self.history)