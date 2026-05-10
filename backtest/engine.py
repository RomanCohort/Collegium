"""
回测引擎
"""
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Callable
from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum
from config.settings import BACKTEST_CONFIG
from strategy.base import BaseStrategy, Signal, SignalType, Position
from risk_manager.position_sizer import PositionSizer
from risk_manager.stop_loss import StopLossManager
from risk_manager.drawdown_guard import DrawdownGuard
from utils.logger import log
from utils.helpers import annualized_return, annualized_volatility, sharpe_ratio, max_drawdown


class OrderType(Enum):
    MARKET = "MARKET"
    LIMIT = "LIMIT"


class OrderStatus(Enum):
    PENDING = "PENDING"
    FILLED = "FILLED"
    CANCELLED = "CANCELLED"


@dataclass
class Order:
    """订单"""
    symbol: str
    order_type: OrderType
    side: str  # BUY / SELL
    quantity: int
    price: Optional[float] = None  # None = 市价单
    status: OrderStatus = OrderStatus.PENDING
    filled_price: float = 0
    filled_quantity: int = 0
    commission: float = 0
    slippage: float = 0
    timestamp: str = ""
    order_id: str = ""


@dataclass
class Trade:
    """成交记录"""
    symbol: str
    side: str
    quantity: int
    price: float
    commission: float
    slippage: float
    timestamp: str
    pnl: float = 0
    strategy: str = ""


class Broker:
    """模拟券商"""

    def __init__(self, config: dict = None):
        self.config = config or BACKTEST_CONFIG
        self.commission_rate = self.config.get("commission_rate", 0.0003)
        self.slippage_rate = self.config.get("slippage_rate", 0.0001)
        self.stamp_duty = self.config.get("stamp_duty", 0.001)
        self.min_commission = self.config.get("min_commission", 5)

    def execute_order(
        self,
        order: Order,
        market_price: float,
        timestamp: str,
    ) -> Trade:
        """
        执行订单

        Args:
            order: 订单
            market_price: 市场价格
            timestamp: 时间戳

        Returns:
            成交记录
        """
        # 计算滑点
        if order.side == "BUY":
            slippage = market_price * self.slippage_rate
            filled_price = market_price + slippage
        else:
            slippage = market_price * self.slippage_rate
            filled_price = market_price - slippage

        # 计算佣金
        amount = filled_price * order.quantity
        commission = max(amount * self.commission_rate, self.min_commission)

        # 印花税（仅卖出）
        if order.side == "SELL":
            commission += amount * self.stamp_duty

        return Trade(
            symbol=order.symbol,
            side=order.side,
            quantity=order.quantity,
            price=filled_price,
            commission=commission,
            slippage=slippage * order.quantity,
            timestamp=timestamp,
            strategy=order.order_id.split("_")[0] if order.order_id else "",
        )


class BacktestEngine:
    """回测引擎"""

    def __init__(
        self,
        strategy: BaseStrategy,
        initial_capital: float = None,
        config: dict = None,
    ):
        self.strategy = strategy
        self.initial_capital = initial_capital or BACKTEST_CONFIG["initial_capital"]
        self.config = config or BACKTEST_CONFIG

        # 组件
        self.broker = Broker(self.config)
        self.position_sizer = PositionSizer()
        self.stop_loss_manager = StopLossManager()
        self.drawdown_guard = DrawdownGuard()

        # 状态
        self.cash = self.initial_capital
        self.positions: Dict[str, Position] = {}
        self.trades: List[Trade] = []
        self.orders: List[Order] = []
        self.daily_nav: List[dict] = []

        # 统计
        self.total_commission = 0
        self.total_slippage = 0

    def run(self, data: pd.DataFrame) -> dict:
        """
        运行回测

        Args:
            data: 行情数据，需包含 date, symbol, open, high, low, close, volume

        Returns:
            回测结果
        """
        log.info(f"开始回测: {self.strategy.name}")
        log.info(f"初始资金: {self.initial_capital:,.0f}")

        # 按日期分组
        if "date" not in data.columns:
            log.error("数据缺少 date 列")
            return {}

        dates = data["date"].unique()
        dates = sorted(dates)

        for date in dates:
            daily_data = data[data["date"] == date]
            self._process_day(date, daily_data)

        # 计算结果
        results = self._calculate_results()

        log.info(f"回测完成: 总收益 {results['total_return']:.2%}")
        return results

    def _process_day(self, date, daily_data: pd.DataFrame):
        """处理单日数据"""
        date_str = str(date)[:10]

        # 1. 更新持仓价格
        for symbol, pos in self.positions.items():
            symbol_data = daily_data[daily_data["symbol"] == symbol]
            if not symbol_data.empty:
                pos.update_price(symbol_data.iloc[0]["close"])

        # 2. 检查止损/止盈
        self._check_stop_loss(date_str, daily_data)

        # 3. 生成信号
        signals = self.strategy.generate_signals(daily_data)

        # 4. 执行信号
        for signal in signals:
            self._execute_signal(signal, date_str, daily_data)

        # 5. 记录每日净值
        self._record_daily_nav(date_str)

        # 6. 更新回撤熔断
        nav = self._calculate_nav()
        self.drawdown_guard.update_nav(date_str, nav)

    def _check_stop_loss(self, date: str, daily_data: pd.DataFrame):
        """检查止损止盈"""
        positions_to_close = []

        for symbol, pos in list(self.positions.items()):
            symbol_data = daily_data[daily_data["symbol"] == symbol]
            if symbol_data.empty:
                continue

            current_price = symbol_data.iloc[0]["close"]

            # 止损检查
            should_stop, reason, stop_price = self.stop_loss_manager.should_stop_loss(
                symbol=symbol,
                current_price=current_price,
                stop_type="trailing",
                trailing_pct=0.08,
            )

            if should_stop:
                positions_to_close.append((symbol, current_price, reason))
                continue

            # 止盈检查
            should_take, reason, take_price = self.stop_loss_manager.should_take_profit(
                symbol=symbol,
                current_price=current_price,
                profit_pct=0.15,
            )

            if should_take:
                positions_to_close.append((symbol, current_price, reason))

        # 平仓
        for symbol, price, reason in positions_to_close:
            self._close_position(symbol, price, date, reason)

    def _execute_signal(self, signal: Signal, date: str, daily_data: pd.DataFrame):
        """执行信号"""
        if self.drawdown_guard.is_paused:
            log.warning(f"交易暂停，跳过信号: {signal.symbol}")
            return

        symbol_data = daily_data[daily_data["symbol"] == signal.symbol]
        if symbol_data.empty:
            return

        if signal.signal_type == SignalType.BUY:
            self._open_position(signal, date, symbol_data)
        elif signal.signal_type == SignalType.SELL:
            if signal.symbol in self.positions:
                self._close_position(signal.symbol, signal.price, date, signal.reason)

    def _open_position(self, signal: Signal, date: str, symbol_data: pd.DataFrame):
        """开仓"""
        price = symbol_data.iloc[0]["close"]

        # 计算仓位
        pos_info = self.position_sizer.calculate_position_size(
            capital=self.cash,
            price=price,
            stop_loss_pct=0.08,
        )

        quantity = pos_info["quantity"]
        if quantity <= 0:
            return

        # 检查资金
        required = quantity * price * (1 + self.broker.commission_rate)
        if required > self.cash:
            quantity = int(self.cash / price / (1 + self.broker.commission_rate) / 100) * 100
            if quantity <= 0:
                return

        # 创建订单
        order = Order(
            symbol=signal.symbol,
            order_type=OrderType.MARKET,
            side="BUY",
            quantity=quantity,
            timestamp=date,
            order_id=f"{self.strategy.name}_{signal.symbol}_{date}",
        )

        # 执行
        trade = self.broker.execute_order(order, price, date)

        # 更新状态
        self.cash -= trade.price * trade.quantity + trade.commission
        self.total_commission += trade.commission
        self.total_slippage += trade.slippage

        self.positions[signal.symbol] = Position(
            symbol=signal.symbol,
            quantity=trade.quantity,
            entry_price=trade.price,
            entry_date=date,
            current_price=trade.price,
            stop_loss=signal.stop_loss,
            take_profit=signal.take_profit,
        )

        # 记录止损
        self.stop_loss_manager.record_entry(
            symbol=signal.symbol,
            entry_price=trade.price,
            quantity=trade.quantity,
            entry_date=date,
        )

        self.trades.append(trade)
        self.strategy.open_position(
            signal.symbol, trade.price, trade.quantity, date,
            stop_loss=signal.stop_loss, take_profit=signal.take_profit
        )

        log.info(f"[{date}] 买入 {signal.symbol} x {quantity} @ {trade.price:.2f}")

    def _close_position(self, symbol: str, price: float, date: str, reason: str):
        """平仓"""
        if symbol not in self.positions:
            return

        pos = self.positions[symbol]
        quantity = pos.quantity

        order = Order(
            symbol=symbol,
            order_type=OrderType.MARKET,
            side="SELL",
            quantity=quantity,
            timestamp=date,
            order_id=f"{self.strategy.name}_{symbol}_{date}",
        )

        trade = self.broker.execute_order(order, price, date)

        # 计算盈亏
        pnl = (trade.price - pos.entry_price) * quantity - trade.commission

        self.cash += trade.price * quantity - trade.commission
        self.total_commission += trade.commission
        self.total_slippage += trade.slippage

        trade.pnl = pnl
        self.trades.append(trade)

        self.strategy.close_position(symbol, trade.price, date, reason)
        self.stop_loss_manager.remove_position(symbol)
        del self.positions[symbol]

        log.info(f"[{date}] 卖出 {symbol} x {quantity} @ {trade.price:.2f} PnL: {pnl:.2f}")

    def _calculate_nav(self) -> float:
        """计算净值"""
        position_value = sum(p.current_value for p in self.positions.values())
        return self.cash + position_value

    def _record_daily_nav(self, date: str):
        """记录每日净值"""
        nav = self._calculate_nav()
        position_value = sum(p.current_value for p in self.positions.values())

        self.daily_nav.append({
            "date": date,
            "nav": nav,
            "cash": self.cash,
            "position_value": position_value,
            "position_count": len(self.positions),
        })

    def _calculate_results(self) -> dict:
        """计算回测结果"""
        if not self.daily_nav:
            return {}

        nav_df = pd.DataFrame(self.daily_nav)
        nav_df["date"] = pd.to_datetime(nav_df["date"])
        nav_df = nav_df.set_index("date").sort_index()

        # 计算收益率
        nav_df["returns"] = nav_df["nav"].pct_change()
        nav_df["cumulative_return"] = (1 + nav_df["returns"]).cumprod() - 1

        # 基本指标
        total_return = nav_df["nav"].iloc[-1] / self.initial_capital - 1
        annual_return = annualized_return(total_return, len(nav_df))

        # 风险指标
        returns = nav_df["returns"].dropna()
        annual_vol = annualized_volatility(returns)
        sharpe = sharpe_ratio(returns)
        max_dd = max_drawdown(nav_df["nav"])

        # 交易统计
        trades_df = pd.DataFrame([t.__dict__ for t in self.trades]) if self.trades else pd.DataFrame()

        winning_trades = trades_df[trades_df["pnl"] > 0] if not trades_df.empty else pd.DataFrame()
        losing_trades = trades_df[trades_df["pnl"] < 0] if not trades_df.empty else pd.DataFrame()

        results = {
            # 收益指标
            "total_return": total_return,
            "annual_return": annual_return,
            "cumulative_return": nav_df["cumulative_return"].iloc[-1],

            # 风险指标
            "annual_volatility": annual_vol,
            "max_drawdown": max_dd,
            "sharpe_ratio": sharpe,

            # 交易统计
            "total_trades": len(self.trades),
            "winning_trades": len(winning_trades),
            "losing_trades": len(losing_trades),
            "win_rate": len(winning_trades) / len(trades_df) if len(trades_df) > 0 else 0,
            "total_commission": self.total_commission,
            "total_slippage": self.total_slippage,

            # 数据
            "nav_series": nav_df,
            "trades": trades_df,
            "positions": self.positions,
        }

        return results

    def get_nav_series(self) -> pd.Series:
        """获取净值曲线"""
        if not self.daily_nav:
            return pd.Series()
        nav_df = pd.DataFrame(self.daily_nav)
        return nav_df.set_index("date")["nav"]

    def get_trade_history(self) -> pd.DataFrame:
        """获取交易历史"""
        if not self.trades:
            return pd.DataFrame()
        return pd.DataFrame([t.__dict__ for t in self.trades])