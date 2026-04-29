"""
CTM (Continuous Thought Model) 因子引擎

核心思想：将"连续思维"机制引入因子建模
- 多时间尺度推理 (日线/周线/月线)
- 连续思维RNN (GRU内部循环)
- 跨尺度注意力融合

CPU优化版: d_model=64, 无大矩阵运算
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple

from ...utils import log


class MultiScaleEncoder(nn.Module):
    """
    多时间尺度编码器

    将原始OHLCV数据编码为多尺度特征:
    - 日线特征: 每日数据直接编码
    - 周线特征: 5日聚合后编码
    - 月线特征: 20日聚合后编码
    """

    def __init__(self, input_dim: int = 8, d_model: int = 64):
        super().__init__()
        self.d_model = d_model

        # 各尺度独立编码器
        self.daily_encoder = nn.Sequential(
            nn.Linear(input_dim, d_model),
            nn.GELU(),
            nn.LayerNorm(d_model),
        )
        self.weekly_encoder = nn.Sequential(
            nn.Linear(input_dim, d_model),
            nn.GELU(),
            nn.LayerNorm(d_model),
        )
        self.monthly_encoder = nn.Sequential(
            nn.Linear(input_dim, d_model),
            nn.GELU(),
            nn.LayerNorm(d_model),
        )

        # 位置编码
        self.pos_encoding = nn.Parameter(
            torch.randn(1, 500, d_model) * 0.02  # 最多500个时间步
        )

    def _aggregate(self, x: torch.Tensor, window: int) -> torch.Tensor:
        """
        聚合时间窗口数据

        Args:
            x: [batch, seq_len, features]
            window: 聚合窗口大小

        Returns:
            聚合后的张量 [batch, seq_len // window, features]
        """
        batch, seq_len, feat = x.shape
        # 截断到window的整数倍
        trim_len = (seq_len // window) * window
        if trim_len == 0:
            return x.unsqueeze(1)

        x_trimmed = x[:, :trim_len, :]
        # 重塑为 [batch, seq_len // window, window, features]
        x_reshaped = x_trimmed.reshape(batch, trim_len // window, window, feat)
        # 取窗口内的均值和标准差作为特征
        mean = x_reshaped.mean(dim=2)
        std = x_reshaped.std(dim=2)
        return torch.cat([mean, std], dim=-1)[:, :, :feat]  # 保持维度

    def forward(self, x: torch.Tensor) -> List[torch.Tensor]:
        """
        Args:
            x: [batch, seq_len, input_dim] 原始OHLCV数据

        Returns:
            [daily_feat, weekly_feat, monthly_feat] 三个尺度的特征
        """
        seq_len = x.shape[1]

        # 日线编码
        daily = self.daily_encoder(x)
        daily = daily + self.pos_encoding[:, :seq_len, :]

        # 周线编码 (5日聚合)
        weekly_raw = self._aggregate(x, 5)
        weekly = self.weekly_encoder(weekly_raw)
        weekly = weekly + self.pos_encoding[:, :weekly.shape[1], :]

        # 月线编码 (20日聚合)
        monthly_raw = self._aggregate(x, 20)
        monthly = self.monthly_encoder(monthly_raw)
        monthly = monthly + self.pos_encoding[:, :monthly.shape[1], :]

        return [daily, weekly, monthly]


class IntraScaleAttention(nn.Module):
    """
    尺度内自注意力

    在同一时间尺度内计算自注意力，捕捉序列内部依赖关系
    """

    def __init__(self, d_model: int = 64, n_heads: int = 4):
        super().__init__()
        self.n_heads = n_heads
        self.d_head = d_model // n_heads
        assert d_model % n_heads == 0

        self.q_proj = nn.Linear(d_model, d_model)
        self.k_proj = nn.Linear(d_model, d_model)
        self.v_proj = nn.Linear(d_model, d_model)
        self.out_proj = nn.Linear(d_model, d_model)
        self.norm = nn.LayerNorm(d_model)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        Args:
            x: [batch, seq, d_model]

        Returns:
            [batch, seq, d_model]
        """
        residual = x
        batch, seq, d = x.shape

        q = self.q_proj(x).reshape(batch, seq, self.n_heads, self.d_head).transpose(1, 2)
        k = self.k_proj(x).reshape(batch, seq, self.n_heads, self.d_head).transpose(1, 2)
        v = self.v_proj(x).reshape(batch, seq, self.n_heads, self.d_head).transpose(1, 2)

        # 缩放点积注意力
        scale = self.d_head ** -0.5
        attn = (q @ k.transpose(-2, -1)) * scale
        attn = F.softmax(attn, dim=-1)

        out = (attn @ v).transpose(1, 2).reshape(batch, seq, d)
        out = self.out_proj(out)
        return self.norm(residual + out)


class CrossScaleAttention(nn.Module):
    """
    跨尺度注意力融合

    将多个时间尺度的特征通过注意力机制融合
    - 查询来自当前尺度
    - 键值来自所有尺度
    """

    def __init__(self, d_model: int = 64, n_scales: int = 3):
        super().__init__()
        self.n_scales = n_scales
        self.query_proj = nn.Linear(d_model, d_model)
        self.key_proj = nn.Linear(d_model, d_model)
        self.value_proj = nn.Linear(d_model, d_model)
        self.gate = nn.Linear(d_model * n_scales, n_scales)  # 门控
        self.fusion = nn.Linear(d_model * n_scales, d_model)
        self.norm = nn.LayerNorm(d_model)

    def forward(self, scale_features: List[torch.Tensor],
                thought_state: torch.Tensor = None) -> torch.Tensor:
        """
        Args:
            scale_features: 各尺度特征 [batch, seq_i, d_model] × n_scales
            thought_state: 连续思维状态 [batch, d_model]

        Returns:
            融合后特征 [batch, max_seq, d_model]
        """
        # 对齐序列长度（取最长序列的长度）
        max_seq = max(f.shape[1] for f in scale_features)
        aligned = []
        for fea in scale_features:
            if fea.shape[1] < max_seq:
                # 插值对齐
                fea = F.interpolate(
                    fea.transpose(1, 2),
                    size=max_seq,
                    mode='linear',
                    align_corners=False
                ).transpose(1, 2)
            aligned.append(fea)

        # 拼接所有尺度
        concat = torch.cat(aligned, dim=-1)  # [batch, seq, d_model * n_scales]

        # 门控融合
        gate_weights = F.softmax(self.gate(concat), dim=-1)  # [batch, seq, n_scales]

        # 加权融合
        gated_features = []
        for i, fea in enumerate(aligned):
            w = gate_weights[:, :, i:i+1]
            gated_features.append(fea * w)

        fused = self.fusion(torch.cat(gated_features, dim=-1))

        # 融入思维状态
        if thought_state is not None:
            thought_inject = thought_state.unsqueeze(1)  # [batch, 1, d_model]
            fused = fused + thought_inject * 0.1  # 残差注入

        return self.norm(fused)


class CTMLayer(nn.Module):
    """
    CTM核心层：连续思维 + 多时间尺度融合

    流程:
    1. 各尺度内部注意力推理 (IntraScaleAttention)
    2. 连续思维状态更新 (GRU Cell)
    3. 跨尺度注意力融合 (CrossScaleAttention)
    """

    def __init__(self, d_model: int = 64, n_heads: int = 4, n_scales: int = 3,
                 n_thought_steps: int = 3):
        super().__init__()
        self.n_thought_steps = n_thought_steps
        self.n_scales = n_scales

        # 尺度内注意力
        self.intra_attns = nn.ModuleList([
            IntraScaleAttention(d_model, n_heads) for _ in range(n_scales)
        ])

        # 连续思维RNN
        self.thought_rnn = nn.GRUCell(d_model, d_model)
        self.thought_norm = nn.LayerNorm(d_model)

        # 跨尺度融合
        self.cross_scale_attn = CrossScaleAttention(d_model, n_scales)

        # 前馈网络
        self.ffn = nn.Sequential(
            nn.Linear(d_model, d_model * 2),
            nn.GELU(),
            nn.Dropout(0.1),
            nn.Linear(d_model * 2, d_model),
        )
        self.ffn_norm = nn.LayerNorm(d_model)

    def forward(self, multi_scale_features: List[torch.Tensor]) -> Tuple[torch.Tensor, torch.Tensor]:
        """
        Args:
            multi_scale_features: [batch, seq_i, d_model] × n_scales

        Returns:
            fused: 融合后特征 [batch, max_seq, d_model]
            thought_state: 思维状态 [batch, d_model]
        """
        # 1. 尺度内推理
        refined = []
        for i, (fea, attn) in enumerate(zip(multi_scale_features, self.intra_attns)):
            refined.append(attn(fea))

        # 2. 连续思维更新 (多步内部推理)
        # 使用各尺度的平均特征作为初始状态
        batch = refined[0].shape[0]
        device = refined[0].device
        thought_state = torch.zeros(batch, refined[0].shape[-1], device=device)

        for step in range(self.n_thought_steps):
            # 将所有尺度信息压缩并送入GRU
            scale_means = [r.mean(dim=1) for r in refined]
            combined_input = torch.stack(scale_means, dim=1).mean(dim=1)
            thought_state = self.thought_rnn(combined_input, thought_state)
            thought_state = self.thought_norm(thought_state)

        # 3. 跨尺度融合
        fused = self.cross_scale_attn(refined, thought_state)

        # 4. FFN
        fused = self.ffn_norm(fused + self.ffn(fused))

        return fused, thought_state


class ContinuousThoughtModel(nn.Module):
    """
    完整CTM模型

    架构:
    Input → MultiScaleEncoder → CTMLayer × N → FactorHead
    """

    def __init__(self, input_dim: int = 8, d_model: int = 64,
                 n_layers: int = 3, n_heads: int = 4,
                 n_scales: int = 3, n_thought_steps: int = 3,
                 factor_names: List[str] = None):
        super().__init__()

        self.d_model = d_model
        self.factor_names = factor_names or ['ctm_momentum', 'ctm_reversal', 'ctm_volatility']
        n_factors = len(self.factor_names)

        # 多尺度编码器
        self.encoder = MultiScaleEncoder(input_dim, d_model)

        # CTM层堆叠
        self.ctm_layers = nn.ModuleList([
            CTMLayer(d_model, n_heads, n_scales, n_thought_steps)
            for _ in range(n_layers)
        ])

        # 因子预测头
        self.factor_heads = nn.ModuleDict({
            name: nn.Sequential(
                nn.Linear(d_model, d_model // 2),
                nn.GELU(),
                nn.Linear(d_model // 2, 1),
            )
            for name in self.factor_names
        })

        # 最终归一化
        self.output_norm = nn.LayerNorm(n_factors)

    def forward(self, x: torch.Tensor) -> Dict[str, torch.Tensor]:
        """
        Args:
            x: [batch, seq_len, input_dim] 原始OHLCV数据
               标准化后的 (open, high, low, close, volume, amount, change_pct, turnover)

        Returns:
            因子值字典 {factor_name: [batch, 1]}
        """
        # 编码
        multi_scale_features = self.encoder(x)

        # CTM推理
        thought_state = None
        fused = None
        for layer in self.ctm_layers:
            fused, thought_state = layer(multi_scale_features)
            # 将融合结果作为新的第一个尺度输入下一层
            multi_scale_features[0] = fused

        # 取最后一个时间步的特征
        if fused is None:
            raise ValueError("CTM forward failed: no output from CTM layers")

        last_hidden = fused[:, -1, :]  # [batch, d_model]

        # 因子预测
        factors = {}
        for name, head in self.factor_heads.items():
            factors[name] = head(last_hidden)  # [batch, 1]

        return factors

    def predict(self, x: torch.Tensor) -> pd.DataFrame:
        """
        批量预测因子值并转为DataFrame

        Args:
            x: [batch, seq_len, input_dim]

        Returns:
            DataFrame with columns: ctm_momentum, ctm_reversal, ctm_volatility
        """
        self.eval()
        with torch.no_grad():
            factors = self.forward(x)

        result = {}
        for name, values in factors.items():
            result[name] = values.squeeze(-1).cpu().numpy()

        return pd.DataFrame(result)
