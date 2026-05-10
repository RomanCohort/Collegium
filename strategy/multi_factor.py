"""
多因子选股策略
"""
import pandas as pd
import numpy as np
from typing import List, Dict, Optional
from strategy.base import BaseStrategy, Signal, SignalType
from utils.helpers import normalize, winsorize
from utils.logger import log


class MultiFactorStrategy(BaseStrategy):
    """
    多因子选股策略

    因子：
    1. Value（价值）: PE、PB、股息率
    2. Momentum（动量）: 过去N日涨幅
    3. Quality（质量）: ROE、毛利率
    4. Low Vol（低波动）: 历史波动率

    综合打分 → 选择排名前N只股票
    """

    def __init__(
        self,
        top_n: int = 30,
        rebalance_freq: int = 5,
        factor_weights: Optional[Dict[str, float]] = None,
        min_score_threshold: float = 0.0,
    ):
        super().__init__(
            name="MultiFactor",
            params={
                "top_n": top_n,
                "rebalance_freq": rebalance_freq,
                "factor_weights": factor_weights or {
                    "value": 0.25,
                    "momentum": 0.25,
                    "quality": 0.25,
                    "low_vol": 0.25,
                },
                "min_score_threshold": min_score_threshold,
            }
        )
        self.top_n = top_n
        self.rebalance_freq = rebalance_freq
        self.factor_weights = factor_weights or {
            "value": 0.25,
            "momentum": 0.25,
            "quality": 0.25,
            "low_vol": 0.25,
        }
        self.min_score_threshold = min_score_threshold
        self.days_since_rebalance = 0

    def compute_value_score(self, df: pd.DataFrame) -> pd.Series:
        """
        计算价值因子得分

        PE 越低越好，PB 越低越好，股息率越高越好
        """
        scores = pd.Series(0.5, index=df.index)

        if "pe" in df.columns:
            # PE 越低越好 → rank 后取反
            pe_rank = df["pe"].replace([np.inf, -np.inf], np.nan).rank(pct=True, na_option="bottom")
            scores = scores * 0.4 + (1 - pe_rank) * 0.3

        if "pb" in df.columns:
            pb_rank = df["pb"].replace([np.inf, -np.inf], np.nan).rank(pct=True, na_option="bottom")
            scores = scores * 0.6 + (1 - pb_rank) * 0.2

        if "dividend_yield" in df.columns:
            dy_rank = df["dividend_yield"].rank(pct=True, na_option="bottom")
            scores = scores * 0.8 + dy_rank * 0.2

        return scores.clip(0, 1)

    def compute_momentum_score(self, df: pd.DataFrame) -> pd.Series:
        """
        计算动量因子得分

        过去 20 日涨幅越高越好
        """
        scores = pd.Series(0.5, index=df.index)

        if "pct_change_20" in df.columns:
            mom_rank = df["pct_change_20"].rank(pct=True, na_option="bottom")
            scores = mom_rank

        elif "close" in df.columns:
            # 自己计算动量
            ret_20 = df["close"].pct_change(20)
            mom_rank = ret_20.rank(pct=True, na_option="bottom")
            scores = mom_rank

        return scores.clip(0, 1)

    def compute_quality_score(self, df: pd.DataFrame) -> pd.Series:
        """
        计算质量因子得分

        ROE 越高越好，毛利率越高越好
        """
        scores = pd.Series(0.5, index=df.index)

        if "roe" in df.columns:
            roe_rank = df["roe"].rank(pct=True, na_option="bottom")
            scores = roe_rank * 0.5

        if "gross_margin" in df.columns:
            gm_rank = df["gross_margin"].rank(pct=True, na_option="bottom")
            scores = scores + gm_rank * 0.3

        if "debt_ratio" in df.columns:
            # 负债率越低越好
            dr_rank = df["debt_ratio"].rank(pct=True, na_option="bottom")
            scores = scores + (1 - dr_rank) * 0.2

        return scores.clip(0, 1)

    def compute_low_vol_score(self, df: pd.DataFrame) -> pd.Series:
        """
        计算低波动因子得分

        波动率越低越好
        """
        scores = pd.Series(0.5, index=df.index)

        if "volatility_20" in df.columns:
            vol_rank = df["volatility_20"].rank(pct=True, na_option="bottom")
            scores = 1 - vol_rank  # 波动越低分数越高

        return scores.clip(0, 1)

    def compute_composite_score(self, df: pd.DataFrame) -> pd.Series:
        """
        计算综合得分

        各因子加权平均
        """
        factor_scores = {}

        if self.factor_weights.get("value", 0) > 0:
            factor_scores["value"] = self.compute_value_score(df)

        if self.factor_weights.get("momentum", 0) > 0:
            factor_scores["momentum"] = self.compute_momentum_score(df)

        if self.factor_weights.get("quality", 0) > 0:
            factor_scores["quality"] = self.compute_quality_score(df)

        if self.factor_weights.get("low_vol", 0) > 0:
            factor_scores["low_vol"] = self.compute_low_vol_score(df)

        if not factor_scores:
            return pd.Series(0.5, index=df.index)

        # 加权平均
        composite = pd.Series(0, index=df.index)
        total_weight = 0

        for factor_name, score in factor_scores.items():
            weight = self.factor_weights.get(factor_name, 0)
            composite += score * weight
            total_weight += weight

        if total_weight > 0:
            composite /= total_weight

        return composite

    def generate_signals(self, data: pd.DataFrame) -> List[Signal]:
        """
        生成多因子选股信号

        Args:
            data: 多只股票的横截面数据

        Returns:
            信号列表
        """
        signals = []

        self.days_since_rebalance += 1

        # 只在调仓日生成信号
        if self.days_since_rebalance < self.rebalance_freq:
            return signals

        self.days_since_rebalance = 0

        if data.empty:
            return signals

        df = data.copy()

        # 计算综合得分
        df["composite_score"] = self.compute_composite_score(df)

        # 过滤最低分
        df = df[df["composite_score"] >= self.min_score_threshold]

        # 排序选前 N
        df = df.nlargest(self.top_n, "composite_score")

        date = str(df.iloc[0].get("date", "")) if "date" in df.columns else ""

        # 当前持仓
        current_symbols = set(self.positions.keys())
        new_symbols = set(df["symbol"].tolist()) if "symbol" in df.columns else set()

        # 卖出不在新组合中的股票
        for symbol in current_symbols - new_symbols:
            price = self.positions[symbol].current_price
            signals.append(Signal(
                symbol=symbol,
                signal_type=SignalType.SELL,
                price=price,
                date=date,
                strength=0.5,
                reason="多因子调仓移出",
            ))

        # 买入新加入的股票
        for _, row in df.iterrows():
            symbol = row.get("symbol", "")
            if symbol and symbol not in current_symbols:
                signals.append(Signal(
                    symbol=symbol,
                    signal_type=SignalType.BUY,
                    price=row.get("close", 0),
                    date=date,
                    strength=row["composite_score"],
                    reason=f"多因子得分={row['composite_score']:.3f}",
                ))

        return signals