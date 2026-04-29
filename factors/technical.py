"""
技术因子实现
"""

import pandas as pd
import numpy as np
from typing import Optional

from .base import FactorBase
from ..utils import log


class MomentumFactor(FactorBase):
    """动量因子 - 过去N日收益率"""

    def __init__(self, period: int = 20, **kwargs):
        super().__init__(f"return_{period}d", "momentum", {"period": period})
        self.period = period

    def calculate(self, data: pd.DataFrame) -> pd.Series:
        if not self.validate_data(data, ['code', 'date', 'close']):
            return pd.Series(dtype=float)

        data = data.sort_values(['code', 'date'])
        returns = data.groupby('code')['close'].pct_change(self.period)
        return returns.dropna()


class ReversalFactor(FactorBase):
    """反转因子 - 过去N日反转"""

    def __init__(self, period: int = 5, **kwargs):
        super().__init__(f"reversal_{period}d", "reversal", {"period": period})
        self.period = period

    def calculate(self, data: pd.DataFrame) -> pd.Series:
        if not self.validate_data(data, ['code', 'date', 'close']):
            return pd.Series(dtype=float)

        data = data.sort_values(['code', 'date'])
        # 反转因子取负的收益率（跌的股票未来可能涨）
        returns = data.groupby('code')['close'].pct_change(self.period)
        return (-returns).dropna()


class VolatilityFactor(FactorBase):
    """波动率因子 - 过去N日收益率标准差"""

    def __init__(self, period: int = 20, **kwargs):
        super().__init__(f"volatility_{period}d", "volatility", {"period": period})
        self.period = period

    def calculate(self, data: pd.DataFrame) -> pd.Series:
        if not self.validate_data(data, ['code', 'date', 'close']):
            return pd.Series(dtype=float)

        data = data.sort_values(['code', 'date'])

        # 计算日收益率
        returns = data.groupby('code')['close'].pct_change()
        data['return'] = returns

        # 计算滚动波动率
        volatility = data.groupby('code')['return'].transform(
            lambda x: x.rolling(self.period, min_periods=self.period // 2).std()
        )

        return volatility.dropna()


class TurnoverRateFactor(FactorBase):
    """换手率因子"""

    def __init__(self, **kwargs):
        super().__init__("turnover_rate", "volume", kwargs)

    def calculate(self, data: pd.DataFrame) -> pd.Series:
        if not self.validate_data(data, ['code', 'date', 'volume']):
            return pd.Series(dtype=float)

        # 使用akshare返回的换手率数据（如果有）
        if 'turnover_rate' in data.columns:
            return data.set_index(['code', 'date'])['turnover_rate']

        # 否则从成交量和股本估算
        # 这里简化处理，实际需要股票总股本数据
        return pd.Series(dtype=float)


class VolumeRatioFactor(FactorBase):
    """量比因子 - 当前成交量/过去N日平均成交量"""

    def __init__(self, period: int = 20, **kwargs):
        super().__init__(f"volume_ratio_{period}d", "volume", {"period": period})
        self.period = period

    def calculate(self, data: pd.DataFrame) -> pd.Series:
        if not self.validate_data(data, ['code', 'date', 'volume']):
            return pd.Series(dtype=float)

        data = data.sort_values(['code', 'date'])

        # 计算成交量移动平均
        ma_volume = data.groupby('code')['volume'].transform(
            lambda x: x.rolling(self.period, min_periods=self.period // 2).mean()
        )

        # 计算量比
        volume_ratio = data['volume'] / ma_volume

        return volume_ratio.dropna()


class MAReturnFactor(FactorBase):
    """均线偏离因子"""

    def __init__(self, period: int = 20, **kwargs):
        super().__init__(f"ma_return_{period}d", "momentum", {"period": period})
        self.period = period

    def calculate(self, data: pd.DataFrame) -> pd.Series:
        if not self.validate_data(data, ['code', 'date', 'close']):
            return pd.Series(dtype=float)

        data = data.sort_values(['code', 'date'])

        # 计算收盘价均线
        ma = data.groupby('code')['close'].transform(
            lambda x: x.rolling(self.period, min_periods=self.period // 2).mean()
        )

        # 计算偏离度
        ma_return = (data['close'] - ma) / ma

        return ma_return.dropna()


class RSIFactor(FactorBase):
    """RSI相对强弱指标"""

    def __init__(self, period: int = 14, **kwargs):
        super().__init__(f"rsi_{period}d", "momentum", {"period": period})
        self.period = period

    def calculate(self, data: pd.DataFrame) -> pd.Series:
        if not self.validate_data(data, ['code', 'date', 'close']):
            return pd.Series(dtype=float)

        data = data.sort_values(['code', 'date'])

        # 计算价格变化
        delta = data.groupby('code')['close'].diff()

        # 分离涨跌
        gain = delta.where(delta > 0, 0)
        loss = (-delta).where(delta < 0, 0)

        # 计算平均涨跌幅
        avg_gain = data.groupby('code')['gain'].transform(
            lambda x: x.rolling(self.period, min_periods=self.period // 2).mean()
        )
        avg_loss = data.groupby('code')['loss'].transform(
            lambda x: x.rolling(self.period, min_periods=self.period // 2).mean()
        )

        # 计算RSI
        rs = avg_gain / avg_loss.replace(0, np.nan)
        rsi = 100 - (100 / (1 + rs))

        return rsi.dropna()


class MACDFactor(FactorBase):
    """MACD指标"""

    def __init__(self, fast: int = 12, slow: int = 26, signal: int = 9, **kwargs):
        super().__init__("macd", "momentum",
                        {"fast": fast, "slow": slow, "signal": signal})
        self.fast = fast
        self.slow = slow
        self.signal = signal

    def calculate(self, data: pd.DataFrame) -> pd.Series:
        if not self.validate_data(data, ['code', 'date', 'close']):
            return pd.Series(dtype=float)

        data = data.sort_values(['code', 'date'])

        def calc_macd(series):
            # 快线EMA
            ema_fast = series.ewm(span=self.fast, adjust=False).mean()
            # 慢线EMA
            ema_slow = series.ewm(span=self.slow, adjust=False).mean()
            # DIF
            dif = ema_fast - ema_slow
            # DEA
            dea = dif.ewm(span=self.signal, adjust=False).mean()
            # MACD柱
            macd = (dif - dea) * 2
            return macd

        macd = data.groupby('code')['close'].transform(calc_macd)
        return macd.dropna()


# ==================== 因子工厂 ====================

class FactorFactory:
    """因子工厂，根据配置创建因子"""

    _FACTOR_CLASSES = {
        'return': MomentumFactor,
        'reversal': ReversalFactor,
        'volatility': VolatilityFactor,
        'turnover_rate': TurnoverRateFactor,
        'volume_ratio': VolumeRatioFactor,
        'ma_return': MAReturnFactor,
        'rsi': RSIFactor,
        'macd': MACDFactor,
    }

    @classmethod
    def create(cls, name: str, category: str, params: dict = None) -> FactorBase:
        """
        创建因子实例

        Args:
            name: 因子名称
            category: 因子类别
            params: 因子参数

        Returns:
            因子实例
        """
        # 从因子名称推断类型
        for prefix, cls in cls._FACTOR_CLASSES.items():
            if name.startswith(prefix):
                # 提取参数
                factor_params = params or {}
                return cls(**factor_params)

        # 默认返回动量因子
        return MomentumFactor(period=20)

    @classmethod
    def create_from_config(cls, factor_configs: list) -> list:
        """
        从配置文件创建多个因子

        Args:
            factor_configs: 因子配置列表

        Returns:
            因子实例列表
        """
        factors = []
        for config in factor_configs:
            name = config.get('name')
            category = config.get('category', 'momentum')
            params = config.get('params', {})
            factor = cls.create(name, category, params)
            factors.append(factor)
        return factors
