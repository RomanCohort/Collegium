"""
CTM增强策略

融合传统因子 + CTM因子 + Mamba推理 + DeepSeek反思
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional
from pathlib import Path
import yaml

from .multifactor import MultiFactorStrategy
from ..factors.ctm import ContinuousThoughtModel, CTMTrainer
from ..factors.mamba import TemporalReasoner
from ..factors.rl import DeepSeekClient, ReflectionAgent
from ..utils import log


class CTMEnhancedStrategy:
    """
    CTM增强的多因子选股策略

    融合层次:
    Layer 1: 传统技术因子 (Momentum/Reversal/Volatility)
    Layer 2: CTM因子 (多时间尺度推理)
    Layer 3: Mamba推理 (趋势/市场状态/异常检测)
    Layer 4: DeepSeek反思 (信号置信度和调整)

    选股流程:
    1. 计算传统因子
    2. 计算CTM因子
    3. 获取Mamba推理结果
    4. 计算综合得分 = 传统因子加权 + CTM因子加权 * 推理置信度
    5. DeepSeek反思验证
    6. 最终调仓决策
    """

    def __init__(self, config_path: str = None):
        """
        Args:
            config_path: 配置文件路径
        """
        if config_path is None:
            config_path = Path(__file__).parent.parent / "config" / "factors.yaml"

        with open(config_path, 'r', encoding='utf-8') as f:
            self.config = yaml.safe_load(f)

        # 底层传统策略
        self.base_strategy = MultiFactorStrategy(config_path)

        # CTM模型
        self.ctm_model: Optional[ContinuousThoughtModel] = None
        self.ctm_enabled = False

        # Mamba推理器
        self.mamba_reasoner: Optional[TemporalReasoner] = None
        self.mamba_enabled = False

        # DeepSeek反思智能体
        self.deepseek_client: Optional[DeepSeekClient] = None
        self.reflection_agent: Optional[ReflectionAgent] = None
        self.reflection_enabled = False

        # 模型路径
        self.model_dir = Path(__file__).parent.parent / "models"
        self.model_dir.mkdir(parents=True, exist_ok=True)

        # 策略参数
        self.strategy_params = self.config.get('strategy_params', {})
        self.ctm_weight = 0.3  # CTM因子权重
        self.mamba_adjustment = True  # 是否启用Mamba调整

        log.info("CTM增强策略初始化完成")

    def load_models(self, ctm_model_path: str = None,
                   mamba_model_path: str = None,
                   deepseek_api_key: str = None):
        """
        加载AI模型

        Args:
            ctm_model_path: CTM模型路径
            mamba_model_path: Mamba模型路径
            deepseek_api_key: DeepSeek API密钥
        """
        # 加载CTM模型
        if ctm_model_path and Path(ctm_model_path).exists():
            try:
                self.ctm_model = ContinuousThoughtModel()
                checkpoint = torch.load(ctm_model_path, map_location='cpu')
                self.ctm_model.load_state_dict(checkpoint['model_state_dict'])
                self.ctm_model.eval()
                self.ctm_enabled = True
                log.info(f"CTM模型已加载: {ctm_model_path}")
            except Exception as e:
                log.warning(f"CTM模型加载失败: {e}")

        # 加载Mamba模型
        if mamba_model_path and Path(mamba_model_path).exists():
            try:
                self.mamba_reasoner = TemporalReasoner()
                checkpoint = torch.load(mamba_model_path, map_location='cpu')
                self.mamba_reasoner.load_state_dict(checkpoint['model_state_dict'])
                self.mamba_reasoner.eval()
                self.mamba_enabled = True
                log.info(f"Mamba推理器已加载: {mamba_model_path}")
            except Exception as e:
                log.warning(f"Mamba模型加载失败: {e}")

        # 初始化DeepSeek客户端
        if deepseek_api_key:
            try:
                self.deepseek_client = DeepSeekClient(api_key=deepseek_api_key)
                self.reflection_agent = ReflectionAgent(
                    self.deepseek_client,
                    reflection_interval=5,
                    cache_ttl_hours=6
                )
                self.reflection_enabled = True
                log.info("DeepSeek反思智能体已初始化")
            except Exception as e:
                log.warning(f"DeepSeek初始化失败: {e}")

    def calculate_ctm_factors(self, price_data: pd.DataFrame) -> pd.DataFrame:
        """
        计算CTM因子

        Args:
            price_data: 行情数据

        Returns:
            CTM因子值DataFrame
        """
        if not self.ctm_enabled or self.ctm_model is None:
            return pd.DataFrame()

        try:
            trainer = CTMTrainer(model=self.ctm_model, device='cpu')
            ctm_factors = trainer.predict_factors(price_data)
            return ctm_factors
        except Exception as e:
            log.warning(f"CTM因子计算失败: {e}")
            return pd.DataFrame()

    def get_mamba_reasoning(self, stock_data: pd.DataFrame) -> Dict:
        """
        获取Mamba推理结果

        Args:
            stock_data: 单只股票数据

        Returns:
            推理结果字典
        """
        if not self.mamba_enabled or self.mamba_reasoner is None:
            return {
                'trend': 'unknown',
                'confidence': 0.5,
                'anomaly_score': 0,
            }

        try:
            reasoning = self.mamba_reasoner.predict(stock_data)
            return reasoning
        except Exception as e:
            log.warning(f"Mamba推理失败: {e}")
            return {'trend': 'unknown', 'confidence': 0.5, 'anomaly_score': 0}

    def apply_reflection(self, signals: pd.DataFrame,
                        market_context: Dict) -> pd.DataFrame:
        """
        应用DeepSeek反思

        Args:
            signals: 选股信号
            market_context: 市场上下文

        Returns:
            调整后的信号
        """
        if not self.reflection_enabled or self.reflection_agent is None:
            return signals

        # 准备上下文
        context = {
            'date': market_context.get('date', ''),
            'codes': signals['code'].tolist() if not signals.empty else [],
            'scores': signals['composite_score'].mean() if not signals.empty else 0,
            'trend': market_context.get('trend', 'unknown'),
            'volatility': market_context.get('volatility', 0),
            'anomaly_score': market_context.get('anomaly_score', 0),
            'recent_returns': market_context.get('recent_returns', []),
            'market_sentiment': market_context.get('market_sentiment', 'neutral'),
        }

        # 执行反思
        reflection = self.reflection_agent.reflect(context)

        # 调整信号
        if not signals.empty:
            confidence = reflection.get('confidence', 0.5)
            weight_adj = reflection.get('weight_adjustment', 1.0)

            # 调整综合得分
            signals = signals.copy()
            signals['refined_score'] = signals['composite_score'] * confidence * weight_adj
            signals['risk_flags'] = [reflection.get('risk_flags', [])] * len(signals)

            # 风险标记筛选
            if reflection.get('risk_flags'):
                log.warning(f"风险标记: {reflection['risk_flags']}")
                # 可以根据风险标记过滤股票

        return signals

    def generate_signals(self, price_data: pd.DataFrame,
                         financial_data: pd.DataFrame = None,
                         market_context: Dict = None,
                         date: str = None) -> pd.DataFrame:
        """
        生成选股信号

        Args:
            price_data: 行情数据
            financial_data: 财务数据
            market_context: 市场上下文
            date: 指定日期

        Returns:
            选股结果DataFrame
        """
        log.info("开始生成CTM增强信号...")

        # 1. 传统因子
        log.info("Step 1: 计算传统因子...")
        base_signals = self.base_strategy.generate_signals(
            price_data, financial_data, date
        )

        if base_signals.empty:
            log.warning("传统因子信号为空")
            return pd.DataFrame()

        # 2. CTM因子
        ctm_factors = pd.DataFrame()
        if self.ctm_enabled:
            log.info("Step 2: 计算CTM因子...")
            ctm_factors = self.calculate_ctm_factors(price_data)

        # 3. Mamba推理
        reasoning = {}
        if self.mamba_enabled and market_context:
            log.info("Step 3: Mamba时序推理...")
            # 对代表性股票做推理
            sample_codes = base_signals['code'].head(10).tolist()
            sample_data = price_data[price_data['code'].isin(sample_codes)]
            if not sample_data.empty:
                sample_stock = sample_data[sample_data['code'] == sample_codes[0]]
                reasoning = self.get_mamba_reasoning(sample_stock)

        # 4. 融合信号
        log.info("Step 4: 信号融合...")
        signals = self._fuse_signals(
            base_signals, ctm_factors, reasoning
        )

        # 5. DeepSeek反思
        if self.reflection_enabled and market_context:
            log.info("Step 5: DeepSeek反思...")
            context = {
                **market_context,
                'date': date,
                'trend': reasoning.get('trend', 'unknown'),
                'anomaly_score': reasoning.get('anomaly_score', 0),
            }
            signals = self.apply_reflection(signals, context)

        # 排序并返回
        score_col = 'refined_score' if 'refined_score' in signals.columns else 'composite_score'
        signals = signals.sort_values(score_col, ascending=False)

        top_n = self.strategy_params.get('top_n', 50)
        result = signals.head(top_n)

        log.info(f"信号生成完成: {len(result)} 只股票")
        return result

    def _fuse_signals(self, base_signals: pd.DataFrame,
                     ctm_factors: pd.DataFrame,
                     reasoning: Dict) -> pd.DataFrame:
        """
        融合多源信号

        Args:
            base_signals: 传统因子信号
            ctm_factors: CTM因子
            reasoning: Mamba推理结果

        Returns:
            融合后的信号
        """
        signals = base_signals.copy()

        # CTM因子融合
        if not ctm_factors.empty and 'ctm_momentum' in ctm_factors.columns:
            # 将CTM因子合并
            merged = signals.merge(
                ctm_factors[['code', 'date', 'ctm_momentum', 'ctm_reversal', 'ctm_volatility']],
                on=['code', 'date'],
                how='left'
            )

            # CTM因子加权融合
            # momentum方向调整
            momentum_adj = merged['ctm_momentum'].fillna(0)
            # reversal方向调整
            reversal_adj = merged['ctm_reversal'].fillna(0)

            # 综合得分 = 传统得分 + CTM贡献
            merged['composite_score'] = (
                merged['composite_score'] * (1 - self.ctm_weight) +
                momentum_adj * self.ctm_weight * 0.5 +
                reversal_adj * self.ctm_weight * 0.5
            )

            signals = merged

        # Mamba推理调整
        if reasoning and self.mamba_adjustment:
            confidence = reasoning.get('confidence', 0.5)
            trend = reasoning.get('trend', 'unknown')
            anomaly = reasoning.get('anomaly_score', 0)

            # 趋势调整
            trend_factor = {'上涨': 1.1, '震荡': 1.0, '下跌': 0.9}.get(trend, 1.0)

            # 异常调整
            anomaly_factor = max(0.8, 1 - anomaly * 0.2)

            # 综合调整
            adjustment = trend_factor * anomaly_factor * confidence

            signals = signals.copy()
            signals['composite_score'] = signals['composite_score'] * adjustment
            signals['reasoning'] = str(reasoning)

        return signals


# 需要的import
import torch
