"""
基本面因子实现
"""

import pandas as pd
import numpy as np
from typing import Dict, Optional

from .base import FactorBase
from ..utils import log


class PEFactor(FactorBase):
    """市盈率因子（低估值）"""

    def __init__(self, **kwargs):
        super().__init__("pe_ttm", "valuation", kwargs)

    def calculate(self, data: pd.DataFrame) -> pd.Series:
        """使用数据中的pe_ttm列"""
        if 'pe_ttm' not in data.columns:
            log.warning("PE因子需要pe_ttm列")
            return pd.Series(dtype=float)

        return data.set_index(['code', 'date'])['pe_ttm']


class PBFactor(FactorBase):
    """市净率因子（低估值）"""

    def __init__(self, **kwargs):
        super().__init__("pb", "valuation", kwargs)

    def calculate(self, data: pd.DataFrame) -> pd.Series:
        if 'pb' not in data.columns:
            log.warning("PB因子需要pb列")
            return pd.Series(dtype=float)

        return data.set_index(['code', 'date'])['pb']


class PSFactor(FactorBase):
    """市销率因子"""

    def __init__(self, **kwargs):
        super().__init__("ps_ttm", "valuation", kwargs)

    def calculate(self, data: pd.DataFrame) -> pd.Series:
        if 'ps_ttm' not in data.columns:
            log.warning("PS因子需要ps_ttm列")
            return pd.Series(dtype=float)

        return data.set_index(['code', 'date'])['ps_ttm']


class ROEFactor(FactorBase):
    """净资产收益率因子（高质量）"""

    def __init__(self, **kwargs):
        super().__init__("roe", "quality", kwargs)

    def calculate(self, data: pd.DataFrame) -> pd.Series:
        if 'roe' not in data.columns:
            log.warning("ROE因子需要roe列")
            return pd.Series(dtype=float)

        return data.set_index(['code', 'date'])['roe']


class ROAFactor(FactorBase):
    """资产收益率因子"""

    def __init__(self, **kwargs):
        super().__init__("roa", "quality", kwargs)

    def calculate(self, data: pd.DataFrame) -> pd.Series:
        if 'roa' not in data.columns:
            log.warning("ROA因子需要roa列")
            return pd.Series(dtype=float)

        return data.set_index(['code', 'date'])['roa']


class DebtRatioFactor(FactorBase):
    """资产负债率因子（低负债）"""

    def __init__(self, **kwargs):
        super().__init__("debt_ratio", "quality", kwargs)

    def calculate(self, data: pd.DataFrame) -> pd.Series:
        if 'debt_ratio' not in data.columns:
            log.warning("资产负债率因子需要debt_ratio列")
            return pd.Series(dtype=float)

        return data.set_index(['code', 'date'])['debt_ratio']


class GrossMarginFactor(FactorBase):
    """毛利率因子"""

    def __init__(self, **kwargs):
        super().__init__("gross_margin", "quality", kwargs)

    def calculate(self, data: pd.DataFrame) -> pd.Series:
        if 'gross_margin' not in data.columns:
            log.warning("毛利率因子需要gross_margin列")
            return pd.Series(dtype=float)

        return data.set_index(['code', 'date'])['gross_margin']


class RevenueGrowthFactor(FactorBase):
    """营收增长率因子"""

    def __init__(self, **kwargs):
        super().__init__("revenue_growth", "growth", kwargs)

    def calculate(self, data: pd.DataFrame) -> pd.Series:
        if 'revenue_growth' not in data.columns:
            log.warning("营收增长率因子需要revenue_growth列")
            return pd.Series(dtype=float)

        return data.set_index(['code', 'date'])['revenue_growth']


class ProfitGrowthFactor(FactorBase):
    """利润增长率因子"""

    def __init__(self, **kwargs):
        super().__init__("profit_growth", "growth", kwargs)

    def calculate(self, data: pd.DataFrame) -> pd.Series:
        if 'profit_growth' not in data.columns:
            log.warning("利润增长率因子需要profit_growth列")
            return pd.Series(dtype=float)

        return data.set_index(['code', 'date'])['profit_growth']


class OperatingCashFlowFactor(FactorBase):
    """经营现金流因子"""

    def __init__(self, **kwargs):
        super().__init__("ocf", "quality", kwargs)

    def calculate(self, data: pd.DataFrame) -> pd.Series:
        if 'ocf' not in data.columns:
            return pd.Series(dtype=float)

        return data.set_index(['code', 'date'])['ocf']


class CurrentRatioFactor(FactorBase):
    """流动比率因子"""

    def __init__(self, **kwargs):
        super().__init__("current_ratio", "quality", kwargs)

    def calculate(self, data: pd.DataFrame) -> pd.Series:
        if 'current_ratio' not in data.columns:
            return pd.Series(dtype=float)

        return data.set_index(['code', 'date'])['current_ratio']


# ==================== 复合因子 ====================

class CompositeFactor(FactorBase):
    """
    复合因子 - 将多个因子按权重组合
    """

    def __init__(self, name: str, factors: list, weights: Dict[str, float], **kwargs):
        super().__init__(name, "composite", kwargs)
        self.factors = factors
        self.weights = weights

    def calculate(self, data: pd.DataFrame) -> pd.Series:
        """
        计算复合因子值（加权平均）
        """
        composite_values = None

        for factor in self.factors:
            factor_values = factor.calculate(data)
            weight = self.weights.get(factor.name, 0)

            if composite_values is None:
                composite_values = factor_values * weight
            else:
                composite_values = composite_values + factor_values * weight

        return composite_values.dropna()
