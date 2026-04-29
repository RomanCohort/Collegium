"""
因子基类
"""

from abc import ABC, abstractmethod
from typing import Optional, Dict, Any
import pandas as pd
from ..utils import log


class FactorBase(ABC):
    """
    因子基类，所有因子都需要继承此类
    """

    def __init__(self, name: str, category: str, params: Dict = None):
        """
        Args:
            name: 因子名称
            category: 因子类别 (momentum/reversal/volatility/valuation/quality/growth)
            params: 因子参数
        """
        self.name = name
        self.category = category
        self.params = params or {}

    @abstractmethod
    def calculate(self, data: pd.DataFrame) -> pd.Series:
        """
        计算因子值

        Args:
            data: 包含价格/成交量等数据的DataFrame
                  必需列: code, date, close, open, high, low, volume, amount

        Returns:
            pd.Series: index为(code, date)的多重索引，值为因子值
        """
        pass

    def validate_data(self, data: pd.DataFrame, required_cols: list) -> bool:
        """
        验证数据是否包含所需列

        Args:
            data: 输入数据
            required_cols: 必需列列表

        Returns:
            是否有效
        """
        missing = [col for col in required_cols if col not in data.columns]
        if missing:
            log.warning(f"因子 {self.name} 缺少列: {missing}")
            return False
        return True

    def __repr__(self):
        return f"Factor(name={self.name}, category={self.category}, params={self.params})"


class ReturnFactor(FactorBase):
    """
    收益率因子基类
    """

    def __init__(self, name: str, period: int = 20, **kwargs):
        super().__init__(name, "momentum", kwargs)
        self.period = period

    def calculate(self, data: pd.DataFrame) -> pd.Series:
        if not self.validate_data(data, ['code', 'date', 'close']):
            return pd.Series(dtype=float)

        # 计算收益率
        data = data.sort_values(['code', 'date'])
        returns = data.groupby('code')['close'].pct_change(self.period)
        returns.name = self.name

        return returns.dropna()
