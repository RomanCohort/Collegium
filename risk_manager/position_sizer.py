"""
仓位管理器
根据风险和资金决定下单数量
"""
import pandas as pd
import numpy as np
from typing import Optional, Dict
from config.settings import RISK_CONFIG
from utils.logger import log


class PositionSizer:
    """仓位管理器"""

    def __init__(self, method: str = "fixed", **kwargs):
        """
        初始化仓位管理器

        Args:
            method: 仓位计算方法
                - fixed: 固定比例
                - kelly: Kelly公式
                - atr: ATR动态调整
                - risk_parity: 风险平价
        """
        self.method = method
        self.config = RISK_CONFIG.copy()
        self.config.update(kwargs)

    def calculate_position_size(
        self,
        capital: float,
        price: float,
        stop_loss_pct: float,
        atr: Optional[float] = None,
        volatility: Optional[float] = None,
        win_rate: Optional[float] = None,
        avg_win: Optional[float] = None,
        avg_loss: Optional[float] = None,
    ) -> Dict[str, any]:
        """
        计算仓位

        Args:
            capital: 可用资金
            price: 当前价格
            stop_loss_pct: 止损比例
            atr: ATR 值（用于 ATR 仓位管理）
            volatility: 波动率（用于其他方法）
            win_rate: 胜率（用于 Kelly）
            avg_win: 平均盈利（用于 Kelly）
            avg_loss: 平均亏损（用于 Kelly）

        Returns:
            包含数量和金额的字典
        """
        if price <= 0:
            log.warning("价格无效，无法计算仓位")
            return {"quantity": 0, "amount": 0, "position_pct": 0}

        if self.method == "fixed":
            return self._fixed_position(capital, price)
        elif self.method == "kelly":
            return self._kelly_position(capital, price, win_rate, avg_win, avg_loss)
        elif self.method == "atr":
            return self._atr_position(capital, price, stop_loss_pct, atr)
        elif self.method == "risk_parity":
            return self._risk_parity_position(capital, price, volatility, stop_loss_pct)
        else:
            log.warning(f"未知仓位方法 {self.method}，使用固定比例")
            return self._fixed_position(capital, price)

    def _fixed_position(self, capital: float, price: float) -> Dict[str, any]:
        """固定比例仓位"""
        max_pct = self.config.get("max_position_pct", 0.2)
        max_amount = capital * max_pct
        quantity = int(max_amount / price / 100) * 100  # 整手
        return {
            "quantity": quantity,
            "amount": quantity * price,
            "position_pct": (quantity * price) / capital,
            "method": "fixed",
        }

    def _kelly_position(
        self,
        capital: float,
        price: float,
        win_rate: Optional[float],
        avg_win: Optional[float],
        avg_loss: Optional[float],
    ) -> Dict[str, any]:
        """Kelly公式仓位"""
        if win_rate is None or avg_win is None or avg_loss is None:
            log.warning("Kelly 公式需要 win_rate, avg_win, avg_loss")
            return self._fixed_position(capital, price)

        # Kelly = (WinRate * RR - (1 - WinRate)) / RR
        # RR = avg_win / avg_loss
        rr = abs(avg_win / avg_loss) if avg_loss != 0 else 1
        kelly = (win_rate * rr - (1 - win_rate)) / rr

        # 使用半 Kelly（更保守）
        kelly = kelly * 0.5
        kelly = max(0, min(kelly, 0.25))  # 限制最大 25%

        max_amount = capital * kelly
        quantity = int(max_amount / price / 100) * 100
        return {
            "quantity": quantity,
            "amount": quantity * price,
            "position_pct": (quantity * price) / capital,
            "method": "kelly",
            "kelly_pct": kelly,
        }

    def _atr_position(
        self,
        capital: float,
        price: float,
        stop_loss_pct: float,
        atr: Optional[float],
    ) -> Dict[str, any]:
        """ATR 动态仓位"""
        if atr is None or atr <= 0:
            # 无 ATR 时使用固定止损
            stop_price = price * (1 - stop_loss_pct)
            risk_per_share = price - stop_price
        else:
            # ATR 止损
            stop_price = price - 2 * atr
            risk_per_share = 2 * atr

        if risk_per_share <= 0:
            return self._fixed_position(capital, price)

        # 单笔风险不超过 1.5%
        max_risk = capital * self.config.get("single_loss_limit", 0.02)
        quantity = int(max_risk / risk_per_share / 100) * 100

        return {
            "quantity": quantity,
            "amount": quantity * price,
            "position_pct": (quantity * price) / capital,
            "stop_price": stop_price,
            "risk_per_share": risk_per_share,
            "method": "atr",
        }

    def _risk_parity_position(
        self,
        capital: float,
        price: float,
        volatility: Optional[float],
        stop_loss_pct: float,
    ) -> Dict[str, any]:
        """风险平价仓位"""
        # 目标波动率调整
        target_vol = 0.15  # 目标年化波动率 15%

        if volatility is None or volatility == 0:
            vol = target_vol
        else:
            vol = volatility

        # 计算所需仓位以达到目标波动率
        daily_vol = vol / np.sqrt(252)
        position_pct = min(daily_vol / 0.01, 0.2)  # 最大 20%

        max_amount = capital * position_pct
        quantity = int(max_amount / price / 100) * 100

        return {
            "quantity": quantity,
            "amount": quantity * price,
            "position_pct": (quantity * price) / capital,
            "target_vol": target_vol,
            "method": "risk_parity",
        }

    def adjust_for_concentration(
        self,
        current_position_value: float,
        new_position_value: float,
        total_capital: float,
        industry: str,
        industry_positions: Dict[str, float],
    ) -> float:
        """
        根据集中度调整仓位

        Args:
            current_position_value: 当前持仓价值
            new_position_value: 新增仓位价值
            total_capital: 总资金
            industry: 行业
            industry_positions: 各行业当前仓位 {行业: 金额}

        Returns:
            调整后的仓位金额
        """
        total_pct = (current_position_value + new_position_value) / total_capital

        # 单只股票仓位限制
        if total_pct > self.config.get("max_position_pct", 0.2):
            new_position_value = total_capital * self.config.get("max_position_pct", 0.2) - current_position_value

        # 行业集中度限制
        max_sector_pct = self.config.get("max_sector_pct", 0.3)
        current_industry_pct = industry_positions.get(industry, 0) / total_capital

        if current_industry_pct + (new_position_value / total_capital) > max_sector_pct:
            available = total_capital * max_sector_pct - industry_positions.get(industry, 0)
            new_position_value = max(0, available)

        return new_position_value

    def validate_position(
        self,
        quantity: int,
        price: float,
        total_capital: float,
        existing_positions: Dict[str, int],
        symbol: str,
    ) -> tuple:
        """
        验证仓位是否符合风控要求

        Returns:
            (是否有效, 错误信息)
        """
        position_value = quantity * price
        position_pct = position_value / total_capital

        # 超过最大仓位
        if position_pct > self.config.get("max_position_pct", 0.2):
            return False, f"单只仓位超过限制 ({position_pct:.1%} > {self.config['max_position_pct']:.1%})"

        # 总仓位超过限制
        total_exposure = sum(q * p for q, p in existing_positions.items())
        total_pct = (total_exposure + position_value) / total_capital

        if total_pct > 0.95:  # 留 5% 现金
            return False, f"总仓位过高 ({total_pct:.1%})"

        return True, ""


# 创建默认实例
position_sizer = PositionSizer()