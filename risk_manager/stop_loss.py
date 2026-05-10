"""
止损管理器
实现多种止损策略
"""
import pandas as pd
import numpy as np
from typing import Optional, List, Tuple
from utils.logger import log


class StopLossManager:
    """止损管理器"""

    def __init__(self, method: str = "fixed"):
        """
        初始化止损管理器

        Args:
            method: 止损方法
                - fixed: 固定比例止损
                - trailing: 追踪止损
                - atr: ATR 止损
                - time: 时间止损
        """
        self.method = method
        self.positions = {}  # 记录持仓信息

    def record_entry(
        self,
        symbol: str,
        entry_price: float,
        quantity: int,
        entry_date: str,
    ):
        """
        记录入场信息

        Args:
            symbol: 股票代码
            entry_price: 入场价格
            quantity: 数量
            entry_date: 入场日期
        """
        self.positions[symbol] = {
            "entry_price": entry_price,
            "quantity": quantity,
            "entry_date": entry_date,
            "entry_value": entry_price * quantity,
            "highest_price": entry_price,
            "lowest_price": entry_price,
        }
        log.info(f"记录入场: {symbol} @ {entry_price} x {quantity}")

    def update_price(self, symbol: str, current_price: float):
        """
        更新持仓最高/最低价格

        Args:
            symbol: 股票代码
            current_price: 当前价格
        """
        if symbol not in self.positions:
            return

        pos = self.positions[symbol]
        pos["highest_price"] = max(pos["highest_price"], current_price)
        pos["lowest_price"] = min(pos["lowest_price"], current_price)

    def should_stop_loss(
        self,
        symbol: str,
        current_price: float,
        stop_type: str = "fixed",
        stop_pct: float = 0.05,
        atr: Optional[float] = None,
        trailing_pct: float = 0.1,
    ) -> Tuple[bool, str, float]:
        """
        判断是否应该止损

        Args:
            symbol: 股票代码
            current_price: 当前价格
            stop_type: 止损类型
            stop_pct: 止损比例
            atr: ATR 值
            trailing_pct: 追踪止损比例

        Returns:
            (是否止损, 止损原因, 止损价格)
        """
        if symbol not in self.positions:
            return False, "", 0

        entry = self.positions[symbol]["entry_price"]

        if stop_type == "fixed":
            # 固定比例止损
            stop_price = entry * (1 - stop_pct)
            loss_pct = (current_price - entry) / entry

            if current_price <= stop_price:
                reason = f"固定止损 {stop_pct:.1%} (损失 {loss_pct:.1%})"
                return True, reason, stop_price

        elif stop_type == "trailing":
            # 追踪止损
            highest = self.positions[symbol]["highest_price"]
            stop_price = highest * (1 - trailing_pct)

            # 只止损，不止盈（让利润奔跑）
            if current_price <= stop_price and current_price < entry:
                reason = f"追踪止损 {trailing_pct:.1%} (距离高点 {(highest-current_price)/highest:.1%})"
                return True, reason, stop_price

        elif stop_type == "atr":
            # ATR 止损
            if atr is None:
                atr = entry * 0.02  # 默认 2%
            stop_price = current_price - 2 * atr

            if current_price <= stop_price:
                reason = f"ATR 止损 (ATR={atr:.2f})"
                return True, reason, stop_price

        elif stop_type == "double":
            # 双倍止损（固定 + ATR 取严）
            fixed_stop = entry * (1 - stop_pct)
            if atr:
                atr_stop = current_price - 2 * atr
                stop_price = max(fixed_stop, atr_stop)  # 取较严格的
            else:
                stop_price = fixed_stop

            if current_price <= stop_price:
                reason = f"双倍止损 (损失 {(current_price-entry)/entry:.1%})"
                return True, reason, stop_price

        return False, "", 0

    def should_take_profit(
        self,
        symbol: str,
        current_price: float,
        profit_pct: float = 0.1,
    ) -> Tuple[bool, str, float]:
        """
        判断是否应该止盈

        Args:
            symbol: 股票代码
            current_price: 当前价格
            profit_pct: 止盈比例

        Returns:
            (是否止盈, 原因, 止盈价格)
        """
        if symbol not in self.positions:
            return False, "", 0

        entry = self.positions[symbol]["entry_price"]
        profit = (current_price - entry) / entry

        if profit >= profit_pct:
            stop_price = entry * (1 + profit_pct * 0.9)  # 略低于止盈点
            return True, f"止盈 {profit_pct:.1%} (盈利 {profit:.1%})", stop_price

        return False, "", 0

    def time_stop(self, symbol: str, current_date: str, holding_days: int) -> bool:
        """
        时间止损

        Args:
            symbol: 股票代码
            current_date: 当前日期
            holding_days: 持仓天数限制

        Returns:
            是否应该卖出
        """
        if symbol not in self.positions:
            return False

        entry_date = self.positions[symbol]["entry_date"]
        # 简单计算天数差
        entry = pd.to_datetime(entry_date)
        current = pd.to_datetime(current_date)
        days = (current - entry).days

        return days >= holding_days

    def remove_position(self, symbol: str):
        """移除持仓记录"""
        if symbol in self.positions:
            del self.positions[symbol]
            log.info(f"移除 {symbol} 止损记录")

    def get_position_info(self, symbol: str) -> Optional[dict]:
        """获取持仓信息"""
        return self.positions.get(symbol)

    def get_all_positions(self) -> dict:
        """获取所有持仓信息"""
        return self.positions.copy()

    def calculate_unrealized_pnl(self, symbol: str, current_price: float) -> dict:
        """
        计算未实现盈亏

        Args:
            symbol: 股票代码
            current_price: 当前价格

        Returns:
            盈亏信息字典
        """
        if symbol not in self.positions:
            return {}

        pos = self.positions[symbol]
        current_value = current_price * pos["quantity"]
        entry_value = pos["entry_value"]

        pnl = current_value - entry_value
        pnl_pct = pnl / entry_value

        return {
            "symbol": symbol,
            "entry_price": pos["entry_price"],
            "current_price": current_price,
            "quantity": pos["quantity"],
            "entry_value": entry_value,
            "current_value": current_value,
            "pnl": pnl,
            "pnl_pct": pnl_pct,
            "highest_price": pos["highest_price"],
            "highest_pnl_pct": (pos["highest_price"] - pos["entry_price"]) / pos["entry_price"],
        }


# 创建默认实例
stop_loss_manager = StopLossManager()