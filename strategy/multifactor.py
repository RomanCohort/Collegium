"""
多因子选股策略
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional
import yaml
from pathlib import Path

from ..factors.technical import (
    MomentumFactor, ReversalFactor, VolatilityFactor,
    VolumeRatioFactor, MAReturnFactor
)
from ..factors.fundamental import (
    PEFactor, PBFactor, ROEFactor, ROAFactor,
    DebtRatioFactor, GrossMarginFactor,
    RevenueGrowthFactor, ProfitGrowthFactor,
)
from ..factors.preprocess import FactorPreprocessor
from ..utils import log


class MultiFactorStrategy:
    """
    多因子选股策略

    流程:
    1. 计算各因子值
    2. 因子预处理（去极值、标准化、中性化）
    3. 加权合成综合得分
    4. 按得分排名选股
    """

    def __init__(self, config_path: str = None):
        """
        Args:
            config_path: 因子配置文件路径
        """
        if config_path is None:
            config_path = Path(__file__).parent.parent / "config" / "factors.yaml"

        with open(config_path, 'r', encoding='utf-8') as f:
            self.config = yaml.safe_load(f)

        self.factor_weights = self.config.get('default_weights', {})
        self.strategy_params = self.config.get('strategy_params', {})
        self.preprocessor = FactorPreprocessor(
            self.config.get('preprocess', {})
        )

        # 初始化因子
        self.technical_factors = self._init_technical_factors()
        self.fundamental_factors = self._init_fundamental_factors()

    def _init_technical_factors(self) -> Dict[str, object]:
        """初始化技术因子"""
        factors = {
            'return_20d': MomentumFactor(period=20),
            'return_60d': MomentumFactor(period=60),
            'return_120d': MomentumFactor(period=120),
            'reversal_5d': ReversalFactor(period=5),
            'reversal_20d': ReversalFactor(period=20),
            'volatility_20d': VolatilityFactor(period=20),
            'volatility_60d': VolatilityFactor(period=60),
            'volume_ratio_20d': VolumeRatioFactor(period=20),
            'ma_return_20d': MAReturnFactor(period=20),
        }
        return factors

    def _init_fundamental_factors(self) -> Dict[str, object]:
        """初始化基本面因子"""
        factors = {
            'pe_ttm': PEFactor(),
            'pb': PBFactor(),
            'roe': ROEFactor(),
            'roa': ROAFactor(),
            'debt_ratio': DebtRatioFactor(),
            'gross_margin': GrossMarginFactor(),
            'revenue_growth': RevenueGrowthFactor(),
            'profit_growth': ProfitGrowthFactor(),
        }
        return factors

    def calculate_all_factors(self, price_data: pd.DataFrame,
                              financial_data: pd.DataFrame = None) -> pd.DataFrame:
        """
        计算所有因子值

        Args:
            price_data: 价格数据 (code, date, open, high, low, close, volume, amount)
            financial_data: 财务数据 (code, date, pe_ttm, pb, roe, ...)

        Returns:
            所有因子值DataFrame
        """
        log.info("开始计算因子...")

        all_factors = {}

        # 计算技术因子
        for name, factor in self.technical_factors.items():
            try:
                values = factor.calculate(price_data)
                if not values.empty:
                    all_factors[name] = values
                    log.debug(f"因子 {name} 计算完成: {len(values)} 条")
            except Exception as e:
                log.warning(f"因子 {name} 计算失败: {e}")

        # 计算基本面因子
        if financial_data is not None and not financial_data.empty:
            for name, factor in self.fundamental_factors.items():
                try:
                    values = factor.calculate(financial_data)
                    if not values.empty:
                        all_factors[name] = values
                        log.debug(f"因子 {name} 计算完成: {len(values)} 条")
                except Exception as e:
                    log.warning(f"因子 {name} 计算失败: {e}")

        # 合并为DataFrame
        if not all_factors:
            return pd.DataFrame()

        factor_df = pd.DataFrame(all_factors)
        factor_df = factor_df.reset_index()

        log.info(f"因子计算完成: {len(factor_df)} 条, {len(all_factors)} 个因子")
        return factor_df

    def preprocess_factors(self, factor_df: pd.DataFrame) -> pd.DataFrame:
        """
        因子预处理

        Args:
            factor_df: 因子值DataFrame

        Returns:
            预处理后的DataFrame
        """
        if factor_df.empty:
            return factor_df

        # 将宽表转为长表以便预处理
        factor_cols = [c for c in factor_df.columns if c not in ['code', 'date']]

        frames = []
        for col in factor_cols:
            df = factor_df[['code', 'date', col]].copy()
            df = df.rename(columns={col: 'factor_value'})
            df['factor_name'] = col
            frames.append(df)

        long_df = pd.concat(frames, ignore_index=True)
        long_df = long_df.dropna(subset=['factor_value'])

        # 预处理
        processed = self.preprocessor.preprocess(long_df)

        return processed

    def generate_composite_score(self, factor_df: pd.DataFrame) -> pd.DataFrame:
        """
        加权合成综合得分

        Args:
            factor_df: 预处理后的因子值DataFrame

        Returns:
            含综合得分的DataFrame
        """
        # 转回宽表
        if 'factor_name' in factor_df.columns:
            pivot = factor_df.pivot_table(
                index=['code', 'date'],
                columns='factor_name',
                values='factor_value',
                aggfunc='first'
            ).reset_index()
        else:
            pivot = factor_df

        # 计算加权得分
        factor_cols = [c for c in pivot.columns if c not in ['code', 'date']]

        scores = pd.Series(0.0, index=pivot.index)
        total_weight = 0

        for col in factor_cols:
            weight = self.factor_weights.get(col, 0)
            if weight != 0 and col in pivot.columns:
                values = pivot[col].fillna(0)
                scores += values * weight
                total_weight += abs(weight)

        if total_weight > 0:
            scores = scores / total_weight

        pivot['composite_score'] = scores

        return pivot

    def generate_signals(self, price_data: pd.DataFrame,
                        financial_data: pd.DataFrame = None,
                        date: str = None) -> pd.DataFrame:
        """
        生成选股信号

        Args:
            price_data: 价格数据
            financial_data: 财务数据
            date: 指定日期，None则使用最新日期

        Returns:
            选股结果DataFrame (code, date, composite_score)
        """
        # 1. 计算所有因子
        factor_df = self.calculate_all_factors(price_data, financial_data)

        if factor_df.empty:
            log.warning("因子计算结果为空")
            return pd.DataFrame()

        # 2. 生成综合得分
        scored = self.generate_composite_score(factor_df)

        if scored.empty:
            return pd.DataFrame()

        # 3. 按日期筛选
        if date:
            scored = scored[scored['date'] == date]
        else:
            # 取最新日期
            latest_date = scored['date'].max()
            scored = scored[scored['date'] == latest_date]

        # 4. 按得分排序
        scored = scored.sort_values('composite_score', ascending=False)

        # 5. 选出Top N
        top_n = self.strategy_params.get('top_n', 50)
        result = scored.head(top_n)

        log.info(f"选股完成: {len(result)} 只股票")
        return result[['code', 'date', 'composite_score']]
