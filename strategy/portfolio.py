"""
组合构建模块
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional
from ..utils import log


class PortfolioConstructor:
    """
    投资组合构建器

    支持多种权重分配方法:
    - 等权重
    - 市值加权
    - 因子得分加权
    - 风险平价
    """

    def __init__(self, max_weight: float = 0.05, min_weight: float = 0.01,
                 industry_constraint: bool = False):
        """
        Args:
            max_weight: 单只股票最大权重
            min_weight: 单只股票最小权重
            industry_constraint: 是否启用行业约束
        """
        self.max_weight = max_weight
        self.min_weight = min_weight
        self.industry_constraint = industry_constraint

    def equal_weight(self, codes: List[str]) -> Dict[str, float]:
        """
        等权重分配

        Args:
            codes: 股票代码列表

        Returns:
            股票权重字典 {code: weight}
        """
        n = len(codes)
        if n == 0:
            return {}

        weight = 1.0 / n
        return {code: weight for code in codes}

    def market_cap_weight(self, codes: List[str],
                         market_caps: Dict[str, float]) -> Dict[str, float]:
        """
        市值加权

        Args:
            codes: 股票代码列表
            market_caps: 市值字典 {code: market_cap}

        Returns:
            股票权重字典
        """
        total_cap = sum(market_caps.get(code, 0) for code in codes)
        if total_cap == 0:
            return self.equal_weight(codes)

        weights = {}
        for code in codes:
            cap = market_caps.get(code, 0)
            weights[code] = cap / total_cap

        return self._clip_weights(weights)

    def score_weight(self, signals: pd.DataFrame,
                     score_col: str = 'composite_score') -> Dict[str, float]:
        """
        因子得分加权

        权重与得分成正比

        Args:
            signals: 选股信号DataFrame，含code和得分列
            score_col: 得分列名

        Returns:
            股票权重字典
        """
        if signals.empty:
            return {}

        scores = signals.set_index('code')[score_col]

        # 确保得分为正
        scores = scores - scores.min() + 0.01

        total = scores.sum()
        if total == 0:
            return self.equal_weight(signals['code'].tolist())

        weights = (scores / total).to_dict()
        return self._clip_weights(weights)

    def risk_parity_weight(self, codes: List[str],
                          covariance: pd.DataFrame) -> Dict[str, float]:
        """
        风险平价权重分配

        每只股票的风险贡献相等

        Args:
            codes: 股票代码列表
            covariance: 协方差矩阵

        Returns:
            股票权重字典
        """
        n = len(codes)
        if n == 0:
            return {}

        if covariance.empty:
            return self.equal_weight(codes)

        # 简化的风险平价: 权重与波动率成反比
        variances = np.diag(covariance.values)
        vols = np.sqrt(np.maximum(variances, 1e-10))

        # 逆波动率加权
        inv_vols = 1.0 / vols
        weights = inv_vols / inv_vols.sum()

        return dict(zip(codes, weights))

    def _clip_weights(self, weights: Dict[str, float]) -> Dict[str, float]:
        """
        裁剪权重到允许范围内

        Args:
            weights: 原始权重

        Returns:
            裁剪后的权重
        """
        clipped = {}
        for code, w in weights.items():
            clipped[code] = np.clip(w, 0, self.max_weight)

        # 重新归一化
        total = sum(clipped.values())
        if total > 0:
            clipped = {code: w / total for code, w in clipped.items()}

        return clipped

    def apply_industry_constraint(self, weights: Dict[str, float],
                                  industries: Dict[str, str],
                                  max_industry_weight: float = 0.30) -> Dict[str, float]:
        """
        应用行业约束

        Args:
            weights: 原始权重
            industries: 股票行业映射 {code: industry}
            max_industry_weight: 单个行业最大权重

        Returns:
            约束后的权重
        """
        # 按行业汇总权重
        industry_weights = {}
        for code, weight in weights.items():
            industry = industries.get(code, 'unknown')
            industry_weights[industry] = industry_weights.get(industry, 0) + weight

        # 裁剪行业权重
        adjusted = {}
        for code, weight in weights.items():
            industry = industries.get(code, 'unknown')
            ind_w = industry_weights[industry]

            if ind_w > max_industry_weight:
                # 按比例缩减
                scale = max_industry_weight / ind_w
                adjusted[code] = weight * scale
            else:
                adjusted[code] = weight

        # 归一化
        total = sum(adjusted.values())
        if total > 0:
            adjusted = {code: w / total for code, w in adjusted.items()}

        return adjusted

    def construct(self, signals: pd.DataFrame,
                  method: str = 'equal',
                  market_caps: Dict[str, float] = None,
                  covariance: pd.DataFrame = None,
                  industries: Dict[str, str] = None) -> Dict[str, float]:
        """
        构建投资组合

        Args:
            signals: 选股信号
            method: 权重方法 'equal'/'market_cap'/'score'/'risk_parity'
            market_caps: 市值数据
            covariance: 协方差矩阵
            industries: 行业映射

        Returns:
            股票权重字典
        """
        codes = signals['code'].tolist()

        if method == 'equal':
            weights = self.equal_weight(codes)
        elif method == 'market_cap':
            weights = self.market_cap_weight(codes, market_caps or {})
        elif method == 'score':
            weights = self.score_weight(signals)
        elif method == 'risk_parity':
            weights = self.risk_parity_weight(codes, covariance or pd.DataFrame())
        else:
            log.warning(f"未知权重方法: {method}，使用等权重")
            weights = self.equal_weight(codes)

        # 行业约束
        if self.industry_constraint and industries:
            weights = self.apply_industry_constraint(weights, industries)

        log.info(f"组合构建完成: {len(weights)} 只股票, 方法={method}")
        return weights
