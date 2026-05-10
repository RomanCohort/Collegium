"""
回撤熔断器
当回撤超过阈值时自动停止交易
"""
import pandas as pd
import numpy as np
from typing import Optional, Dict
from utils.logger import log


class DrawdownGuard:
    """回撤熔断器"""

    def __init__(
        self,
        max_drawdown: float = 0.15,
        recovery_threshold: float = 0.05,
        cooldown_days: int = 5,
    ):
        """
        初始化回撤熔断器

        Args:
            max_drawdown: 最大允许回撤（超过则停止交易）
            recovery_threshold: 恢复阈值（从底部回升多少后恢复交易）
            cooldown_days: 冷却期天数
        """
        self.max_drawdown = max_drawdown
        self.recovery_threshold = recovery_threshold
        self.cooldown_days = cooldown_days

        # 状态跟踪
        self.high_water_mark = 0
        self.current_drawdown = 0
        self.is_paused = False
        self.pause_reason = ""
        self.pause_date = None
        self.resume_date = None

        # 历史记录
        self.history = []
        self.peak_dates = []  # 记录每个新高的日期

    def update_nav(self, date: str, nav: float):
        """
        更新净值

        Args:
            date: 当前日期
            nav: 当前净值
        """
        record = {"date": date, "nav": nav}

        # 更新新高
        if nav > self.high_water_mark:
            self.high_water_mark = nav
            self.peak_dates.append({"date": date, "nav": nav})
            log.info(f"新净值高点: {nav:.4f}")

        # 计算当前回撤
        if self.high_water_mark > 0:
            self.current_drawdown = (self.high_water_mark - nav) / self.high_water_mark
        else:
            self.current_drawdown = 0

        record["drawdown"] = self.current_drawdown
        self.history.append(record)

        # 检查是否需要熔断
        self._check_drawdown()

    def _check_drawdown(self):
        """检查回撤是否触发熔断"""
        if self.is_paused:
            return

        if self.current_drawdown >= self.max_drawdown:
            self.is_paused = True
            self.pause_reason = f"回撤 {self.current_drawdown:.1%} 超过阈值 {self.max_drawdown:.1%}"
            log.warning(f"⚠️ 交易熔断！原因: {self.pause_reason}")
            log.warning(f"⚠️ 当前回撤: {self.current_drawdown:.1%} | 新高: {self.high_water_mark:.4f}")

    def can_trade(self) -> tuple:
        """
        检查是否允许交易

        Returns:
            (是否允许, 原因)
        """
        if not self.is_paused:
            return True, "正常交易"

        # 检查是否可以从暂停中恢复
        if self.resume_date is None:
            return False, f"交易暂停: {self.pause_reason}"

        return False, f"交易暂停: {self.pause_reason}"

    def manual_pause(self, reason: str):
        """手动暂停交易"""
        self.is_paused = True
        self.pause_reason = reason
        log.warning(f"⚠️ 手动暂停交易: {reason}")

    def manual_resume(self):
        """手动恢复交易"""
        if self.is_paused:
            self.is_paused = False
            self.pause_reason = ""
            log.info("✅ 交易已恢复")
            return True
        return False

    def get_status(self) -> dict:
        """获取当前状态"""
        return {
            "is_paused": self.is_paused,
            "pause_reason": self.pause_reason,
            "high_water_mark": self.high_water_mark,
            "current_drawdown": self.current_drawdown,
            "max_drawdown_limit": self.max_drawdown,
        }

    def get_drawdown_series(self) -> pd.DataFrame:
        """
        获取回撤序列

        Returns:
            回撤数据 DataFrame
        """
        if not self.history:
            return pd.DataFrame()

        return pd.DataFrame(self.history)

    def get_max_drawdown(self) -> float:
        """获取历史最大回撤"""
        if not self.history:
            return 0
        return max(r["drawdown"] for r in self.history)

    def get_recovery_info(self) -> dict:
        """
        获取恢复信息

        Returns:
            恢复状态字典
        """
        if not self.peak_dates:
            return {"peak_nav": self.high_water_mark, "recovery_pct": 0}

        last_peak = self.peak_dates[-1]

        # 从最低点恢复
        if len(self.history) > 0:
            current_nav = self.history[-1]["nav"]
            lowest_nav = min(r["nav"] for r in self.history)
            recovery = (current_nav - lowest_nav) / lowest_nav if lowest_nav > 0 else 0

            return {
                "last_peak_date": last_peak["date"],
                "peak_nav": last_peak["nav"],
                "lowest_nav": lowest_nav,
                "current_nav": current_nav,
                "recovery_pct": recovery,
            }

        return {}


# 创建默认实例
drawdown_guard = DrawdownGuard()