"""
因子预处理模块
- 去极值 (Winsorization)
- 标准化 (Standardization)
- 中性化 (Neutralization)
"""

import pandas as pd
import numpy as np
from typing import Optional, List
from ..utils import log


class FactorPreprocessor:
    """
    因子预处理器
    """

    def __init__(self, config: dict = None):
        """
        Args:
            config: 预处理配置
                - winsorize_std: MAD去极值标准差倍数 (默认3.0)
                - standardize_method: 标准化方法 'zscore'/'minmax' (默认'zscore')
        """
        config = config or {}
        self.winsorize_std = config.get('winsorize_std', 3.0)
        self.standardize_method = config.get('standardize_method', 'zscore')

    def winsorize(self, factor_data: pd.Series) -> pd.Series:
        """
        MAD去极值 (Median Absolute Deviation)

        对截面因子数据进行去极值处理：
        1. 计算中位数 median
        2. 计算MAD = median(|x - median|)
        3. 设定上下界: [median - n*MAD, median + n*MAD]
        4. 将超出范围的值截断到边界

        Args:
            factor_data: 截面因子值 (某一天的因子值)

        Returns:
            去极值后的因子值
        """
        median = factor_data.median()
        mad = (factor_data - median).abs().median()

        if mad < 1e-10:
            return factor_data

        lower = median - self.winsorize_std * mad
        upper = median + self.winsorize_std * mad

        return factor_data.clip(lower, upper)

    def standardize(self, factor_data: pd.Series) -> pd.Series:
        """
        Z-score标准化

        Args:
            factor_data: 截面因子值

        Returns:
            标准化后的因子值
        """
        if self.standardize_method == 'zscore':
            mean = factor_data.mean()
            std = factor_data.std()
            if std < 1e-10:
                return factor_data - mean
            return (factor_data - mean) / std
        elif self.standardize_method == 'minmax':
            min_val = factor_data.min()
            max_val = factor_data.max()
            if max_val - min_val < 1e-10:
                return factor_data - min_val
            return (factor_data - min_val) / (max_val - min_val)
        return factor_data

    def neutralize(self, factor_data: pd.Series, industry_data: pd.Series,
                   market_cap_data: pd.Series = None) -> pd.Series:
        """
        行业中性化（和市值中性化）

        使用线性回归去除行业和市值的影响：
        factor = sum(beta_i * industry_i) + gamma * log(market_cap) + residual
        返回residual作为中性化后的因子值

        Args:
            factor_data: 因子值, index为股票代码
            industry_data: 行业分类, index为股票代码
            market_cap_data: 市值数据, index为股票代码 (可选)

        Returns:
            中性化后的因子残差
        """
        # 对齐index
        common_idx = factor_data.index.intersection(industry_data.index)
        if market_cap_data is not None:
            common_idx = common_idx.intersection(market_cap_data.index)

        factor_data = factor_data.loc[common_idx]
        industry_data = industry_data.loc[common_idx]

        # 行业哑变量
        industries = pd.get_dummies(industry_data, drop_first=True)

        # 构建回归矩阵
        X = industries.values.astype(float)

        if market_cap_data is not None:
            mc = market_cap_data.loc[common_idx]
            # 取对数市值
            log_mc = np.log(mc.replace(0, np.nan).dropna())
            # 对齐
            valid_idx = log_mc.index
            factor_data = factor_data.loc[valid_idx]
            X = pd.get_dummies(industry_data.loc[valid_idx], drop_first=True).values.astype(float)
            X = np.column_stack([X, log_mc.values])

        y = factor_data.values.astype(float)

        # OLS回归: y = X @ beta + residual
        try:
            beta = np.linalg.lstsq(X, y, rcond=None)[0]
            residual = y - X @ beta
            return pd.Series(residual, index=factor_data.index, name=factor_data.name)
        except np.linalg.LinAlgError:
            log.warning("中性化回归失败，返回原始值")
            return factor_data

    def preprocess(self, factor_df: pd.DataFrame,
                   industry_col: str = None,
                   market_cap_col: str = None) -> pd.DataFrame:
        """
        完整的因子预处理流程

        按日期分组，对每个截面进行：
        1. 去极值
        2. 标准化
        3. 中性化（可选）

        Args:
            factor_df: 因子数据，需包含 date, code, factor_value 列
            industry_col: 行业列名 (用于中性化)
            market_cap_col: 市值列名 (用于中性化)

        Returns:
            处理后的因子数据
        """
        result_frames = []
        dates = factor_df['date'].unique()

        log.info(f"预处理 {len(dates)} 个截面数据...")

        for date in dates:
            mask = factor_df['date'] == date
            day_data = factor_df[mask].copy()

            if len(day_data) < 10:
                continue

            factor_values = day_data['factor_value']

            # 1. 去极值
            factor_values = self.winsorize(factor_values)

            # 2. 标准化
            factor_values = self.standardize(factor_values)

            # 3. 中性化
            if industry_col and industry_col in day_data.columns:
                factor_data = pd.Series(
                    factor_values.values,
                    index=day_data['code'].values
                )
                industry_data = pd.Series(
                    day_data[industry_col].values,
                    index=day_data['code'].values
                )
                mc_data = None
                if market_cap_col and market_cap_col in day_data.columns:
                    mc_data = pd.Series(
                        day_data[market_cap_col].values,
                        index=day_data['code'].values
                    )

                neutralized = self.neutralize(factor_data, industry_data, mc_data)
                factor_values = neutralized.values

            day_data['factor_value'] = factor_values
            result_frames.append(day_data)

        if not result_frames:
            return pd.DataFrame()

        result = pd.concat(result_frames, ignore_index=True)
        log.info(f"预处理完成: {len(result)} 条数据")
        return result
