"""
因子评估模块
- IC (Information Coefficient)
- IR (Information Ratio)
- 分组回测
- 多空收益
"""

import pandas as pd
import numpy as np
from typing import Optional, Dict, List
from ..utils import log


class FactorEvaluator:
    """
    因子评估器
    """

    def __init__(self, periods: List[int] = None, n_groups: int = 10):
        """
        Args:
            periods: IC计算的持有期列表，默认[5, 10, 20]
            n_groups: 分组测试的分组数量
        """
        self.periods = periods or [5, 10, 20]
        self.n_groups = n_groups

    def calculate_ic(self, factor_data: pd.DataFrame,
                     return_data: pd.DataFrame,
                     method: str = 'spearman') -> pd.DataFrame:
        """
        计算因子IC (Information Coefficient)

        IC = corr(factor_t, return_{t+n})

        Args:
            factor_data: 因子数据, 包含 [code, date, factor_value] 列
            return_data: 收益率数据, 包含 [code, date, return] 列
            method: 相关系数方法 'pearson'/'spearman'

        Returns:
            各日期各持有期的IC值DataFrame
        """
        results = {}

        for period in self.periods:
            ic_values = []

            # 合并因子和收益率数据
            return_shifted = return_data.copy()
            return_shifted['future_return'] = return_shifted.groupby('code')['return'].shift(-period)

            merged = pd.merge(
                factor_data[['code', 'date', 'factor_value']],
                return_shifted[['code', 'date', 'future_return']],
                on=['code', 'date'],
                how='inner'
            )

            # 按日期计算截面IC
            for date, group in merged.groupby('date'):
                valid = group.dropna(subset=['factor_value', 'future_return'])
                if len(valid) < 30:
                    continue

                if method == 'spearman':
                    # 秩相关
                    ic = valid['factor_value'].corr(valid['future_return'], method='spearman')
                else:
                    ic = valid['factor_value'].corr(valid['future_return'], method='pearson')

                ic_values.append({'date': date, 'ic': ic})

            if ic_values:
                ic_df = pd.DataFrame(ic_values)
                results[f'ic_{period}d'] = ic_df

        return results

    def calculate_ir(self, ic_results: Dict[str, pd.DataFrame]) -> pd.DataFrame:
        """
        计算IR (Information Ratio)

        IR = mean(IC) / std(IC)

        Args:
            ic_results: calculate_ic的输出

        Returns:
            各因子的IR统计信息
        """
        ir_data = []

        for period_key, ic_df in ic_results.items():
            if ic_df.empty:
                continue

            ic_series = ic_df['ic']
            period = period_key.replace('ic_', '').replace('d', '')

            ir_data.append({
                'period': f'{period}d',
                'ic_mean': ic_series.mean(),
                'ic_std': ic_series.std(),
                'ir': ic_series.mean() / ic_series.std() if ic_series.std() > 0 else 0,
                'ic_positive_ratio': (ic_series > 0).mean(),
                'ic_abs_mean': ic_series.abs().mean(),
                'count': len(ic_series),
            })

        return pd.DataFrame(ir_data)

    def group_test(self, factor_data: pd.DataFrame,
                   return_data: pd.DataFrame,
                   period: int = 20) -> pd.DataFrame:
        """
        因子分组测试

        将股票按因子值分成N组，计算各组收益率差异

        Args:
            factor_data: 因子数据
            return_data: 收益率数据
            period: 持有期

        Returns:
            各组的平均收益率
        """
        # 合并数据
        return_shifted = return_data.copy()
        return_shifted['future_return'] = return_shifted.groupby('code')['return'].shift(-period)

        merged = pd.merge(
            factor_data[['code', 'date', 'factor_value']],
            return_shifted[['code', 'date', 'future_return']],
            on=['code', 'date'],
            how='inner'
        )

        merged = merged.dropna()

        group_returns = []

        for date, group in merged.groupby('date'):
            if len(group) < self.n_groups * 5:
                continue

            # 按因子值分组
            group['factor_group'] = pd.qcut(
                group['factor_value'],
                self.n_groups,
                labels=False,
                duplicates='drop'
            )

            for g_idx, g_data in group.groupby('factor_group'):
                group_returns.append({
                    'date': date,
                    'group': int(g_idx),
                    'return': g_data['future_return'].mean(),
                })

        if not group_returns:
            return pd.DataFrame()

        result = pd.DataFrame(group_returns)
        return result

    def long_short_return(self, group_result: pd.DataFrame) -> pd.Series:
        """
        计算多空组合收益

        做多因子最高组，做空因子最低组

        Args:
            group_result: group_test的输出

        Returns:
            多空组合收益率序列
        """
        if group_result.empty:
            return pd.Series(dtype=float)

        max_group = group_result['group'].max()
        min_group = group_result['group'].min()

        long = group_result[group_result['group'] == max_group].groupby('date')['return'].mean()
        short = group_result[group_result['group'] == min_group].groupby('date')['return'].mean()

        return long - short

    def evaluate(self, factor_data: pd.DataFrame,
                 return_data: pd.DataFrame) -> Dict:
        """
        综合评估因子

        Args:
            factor_data: 因子数据
            return_data: 收益率数据

        Returns:
            评估结果字典
        """
        log.info("开始因子评估...")

        result = {}

        # 1. IC分析
        log.info("计算IC...")
        ic_results = self.calculate_ic(factor_data, return_data)
        result['ic'] = ic_results

        # 2. IR分析
        log.info("计算IR...")
        result['ir'] = self.calculate_ir(ic_results)

        # 3. 分组测试
        log.info("进行分组测试...")
        group_result = self.group_test(factor_data, return_data)
        result['group_test'] = group_result

        # 4. 多空收益
        if not group_result.empty:
            log.info("计算多空收益...")
            result['long_short'] = self.long_short_return(group_result)

        # 打印摘要
        if not result['ir'].empty:
            log.info("\n因子评估摘要:")
            log.info(result['ir'].to_string(index=False))

        return result
