"""
策略基类
定义统一的策略接口
"""
import pandas as pd
import numpy as np
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime
from utils.logger import log


class SignalType(Enum):
    """信号类型"""
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"


@dataclass
class Signal:
    """交易信号"""
    symbol: str
    signal_type: SignalType
    price: float
    date: str
    strength: float = 1.0       # 信号强度 0-1
    reason: str = ""             # 信号原因
    strategy_name: str = ""      # 策略名称
    quantity: Optional[int] = None  # 建议数量
    stop_loss: Optional[float] = None  # 止损价
    take_profit: Optional[float] = None  # 止盈价

    def to_dict(self) -> dict:
        return {
            "symbol": self.symbol,
            "signal_type": self.signal_type.value,
            "price": self.price,
            "date": self.date,
            "strength": self.strength,
            "reason": self.reason,
            "strategy_name": self.strategy_name,
            "quantity": self.quantity,
            "stop_loss": self.stop_loss,
            "take_profit": self.take_profit,
        }


@dataclass
class Position:
    """持仓"""
    symbol: str
    quantity: int
    entry_price: float
    entry_date: str
    current_price: float = 0
    current_value: float = 0
    pnl: float = 0
    pnl_pct: float = 0
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None

    def update_price(self, price: float):
        self.current_price = price
        self.current_value = self.quantity * price
        self.pnl = self.current_value - (self.quantity * self.entry_price)
        self.pnl_pct = (price - self.entry_price) / self.entry_price


class BaseStrategy(ABC):
    """策略基类"""

    def __init__(self, name: str, params: Optional[Dict] = None):
        """
        初始化策略

        Args:
            name: 策略名称
            params: 策略参数
        """
        self.name = name
        self.params = params or {}
        self.positions: Dict[str, Position] = {}
        self.signals: List[Signal] = []
        self.trade_history: List[Dict] = []

    @abstractmethod
    def generate_signals(self, data: pd.DataFrame) -> List[Signal]:
        """
        生成交易信号（子类必须实现）

        Args:
            data: 行情数据

        Returns:
            信号列表
        """
        pass

    def on_bar(self, date: str, bar_data: pd.DataFrame):
        """
        每根 K 线回调

        Args:
            date: 当前日期
            bar_data: 当日数据
        """
        signals = self.generate_signals(bar_data)
        for signal in signals:
            signal.date = date
            signal.strategy_name = self.name
            self.signals.append(signal)

    def open_position(
        self,
        symbol: str,
        price: float,
        quantity: int,
        date: str,
        stop_loss: Optional[float] = None,
        take_profit: Optional[float] = None,
    ):
        """开仓"""
        self.positions[symbol] = Position(
            symbol=symbol,
            quantity=quantity,
            entry_price=price,
            entry_date=date,
            current_price=price,
            stop_loss=stop_loss,
            take_profit=take_profit,
        )
        log.info(f"[{self.name}] 开仓: {symbol} x {quantity} @ {price:.2f}")

    def close_position(self, symbol: str, price: float, date: str, reason: str = ""):
        """平仓"""
        if symbol not in self.positions:
            return

        pos = self.positions[symbol]
        pos.update_price(price)

        trade_record = {
            "symbol": symbol,
            "entry_price": pos.entry_price,
            "exit_price": price,
            "quantity": pos.quantity,
            "entry_date": pos.entry_date,
            "exit_date": date,
            "pnl": pos.pnl,
            "pnl_pct": pos.pnl_pct,
            "reason": reason,
            "strategy": self.name,
        }
        self.trade_history.append(trade_record)
        del self.positions[symbol]

        log.info(
            f"[{self.name}] 平仓: {symbol} x {pos.quantity} @ {price:.2f} "
            f"PnL: {pos.pnl:.2f} ({pos.pnl_pct:.2%}) | {reason}"
        )

    def get_position(self, symbol: str) -> Optional[Position]:
        """获取持仓"""
        return self.positions.get(symbol)

    def get_all_positions(self) -> Dict[str, Position]:
        """获取所有持仓"""
        return self.positions.copy()

    def get_trade_history(self) -> pd.DataFrame:
        """获取交易历史"""
        if not self.trade_history:
            return pd.DataFrame()
        return pd.DataFrame(self.trade_history)

    def get_signals_as_df(self) -> pd.DataFrame:
        """获取信号历史"""
        if not self.signals:
            return pd.DataFrame()
        return pd.DataFrame([s.to_dict() for s in self.signals])

    def reset(self):
        """重置策略状态"""
        self.positions.clear()
        self.signals.clear()
        self.trade_history.clear()

    def describe(self) -> str:
        """策略描述"""
        return f"{self.name} | 参数: {self.params}"

    def summary(self) -> Dict[str, Any]:
        """策略摘要"""
        trades = self.trade_history
        if not trades:
            return {"name": self.name, "total_trades": 0}

        winning = [t for t in trades if t["pnl"] > 0]
        losing = [t for t in trades if t["pnl"] <= 0]

        return {
            "name": self.name,
            "total_trades": len(trades),
            "winning_trades": len(winning),
            "losing_trades": len(losing),
            "win_rate": len(winning) / len(trades),
            "avg_pnl": np.mean([t["pnl"] for t in trades]),
            "avg_pnl_pct": np.mean([t["pnl_pct"] for t in trades]),
            "total_pnl": sum(t["pnl"] for t in trades),
            "avg_holding_days": np.mean([
                (pd.to_datetime(t["exit_date"]) - pd.to_datetime(t["entry_date"])).days
                for t in trades
            ]),
        }