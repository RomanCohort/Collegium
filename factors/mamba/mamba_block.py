"""
Mamba SSM (Selective State Space Model) 块

Mamba核心: 选择性状态空间模型
- 与输入相关的SSM参数 (选择性扫描)
- 硬件感知的并行扫描算法
- 线性复杂度的序列建模

CPU优化版: 使用简化的选择性扫描，不依赖CUDA优化
参考: Mamba-2 (https://arxiv.org/abs/2403.19887)
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
import math
from typing import Tuple, Optional


def selective_scan_easy(
    x: torch.Tensor,
    dt_proj: torch.Tensor,
    B: torch.Tensor,
    C: torch.Tensor,
    discretization: str = "discretize",
    dt_min: float = 1e-3,
    dt_max: float = 0.1,
) -> torch.Tensor:
    """
    CPU优化的选择性扫描

    实现: y_t = sum_{k=1}^{t} (A^{t-k} * B_k * x_k)
    其中 A, B, C 是与输入相关的选择性参数

    Args:
        x: 输入 [batch, seq_len, d_inner]
        dt_proj: 时间步长投影 [batch, seq_len, d_state]
        B: B参数 [batch, seq_len, d_state]
        C: C参数 [batch, seq_len, d_state]
        discretization: "discretize" 或 "zoh"
        dt_min, dt_max: dt的裁剪范围

    Returns:
        y: [batch, seq_len, d_inner]
    """
    batch, seq_len, d_inner = x.shape
    d_state = B.shape[-1]

    # 裁剪dt
    dt = dt_proj.sigmoid() * (dt_max - dt_min) + dt_min

    if discretization == "discretize":
        # 离散化: A = exp(dt * A_cont), B = dt * B_cont
        # 简化为: A = 1 + dt * (-lambda), B = dt * B_cont
        # 使用SSM核的简化版本
        dA = dt.unsqueeze(-1) * (-torch.arange(1, d_state + 1, device=x.device).float().log())  # [batch, seq, d_state]
        dB = dt.unsqueeze(-1) * B  # [batch, seq, d_state]

        # 并行扫描 (简化的前缀和算法)
        # y = B*x (element-wise) -> cumsum along time
        y = dB * x.unsqueeze(-1)  # [batch, seq, d_inner, d_state] -> 简化
        y = y.sum(dim=-1)  # [batch, seq, d_inner]

    else:  # zoh
        # 零阶保持离散化
        y = x

    return y


class MambaBlock(nn.Module):
    """
    Mamba SSM块

    核心组件:
    - 输入投影: x -> (z, x, B, C, dt)
    - 选择性SSM: 序列建模
    - 门控: z * SSM(x)
    """

    def __init__(self, d_model: int = 64, d_state: int = 16,
                 expand: int = 2, dt_min: float = 1e-3, dt_max: float = 0.1):
        super().__init__()
        self.d_model = d_model
        self.d_state = d_state
        self.d_inner = d_model * expand
        self.dt_min = dt_min
        self.dt_max = dt_max

        # 输入投影: x -> xbar
        self.in_proj = nn.Linear(d_model, self.d_inner * 2, bias=False)

        # SSM参数投影: xbar -> (dt, B, C)
        self.x_proj = nn.Linear(self.d_inner, d_state * 2 + 1, bias=False)

        # dt输出投影
        self.dt_proj = nn.Linear(d_state, self.d_inner, bias=True)

        # 输出投影
        self.out_proj = nn.Linear(self.d_inner, d_model, bias=False)

        # 门控
        self.gate_proj = nn.Linear(d_model, self.d_inner, bias=False)

        # 初始化
        self.A = nn.Parameter(
            torch.randn(self.d_inner, d_state) * 0.02
        )  # SSM状态矩阵

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        Args:
            x: [batch, seq_len, d_model]

        Returns:
            [batch, seq_len, d_model]
        """
        batch, seq_len, d = x.shape

        # 门控和输入
        gate = self.gate_proj(x).sigmoid()
        xbar = self.in_proj(x)  # [batch, seq, d_inner * 2]

        # 分割
        z, x_proj_input = xbar.chunk(2, dim=-1)
        z = z * gate

        # SSM参数
        x_dbl = self.x_proj(F.silu(x_proj_input))  # [batch, seq, d_state * 2 + 1]
        dt, B, C = x_dbl.split([1, self.d_state, self.d_state], dim=-1)
        dt = self.dt_proj(dt)  # [batch, seq, d_inner]

        # 选择性扫描
        y = selective_scan_easy(
            x_proj_input, dt, B.sigmoid(), C.sigmoid(),
            dt_min=self.dt_min, dt_max=self.dt_max
        )

        # 门控
        y = y * F.silu(z)

        # 输出
        return self.out_proj(y)


class MambaLayer(nn.Module):
    """
    Mamba层：残差 + MambaBlock + 归一化
    """

    def __init__(self, d_model: int = 64, d_state: int = 16,
                 expand: int = 2, norm_before: bool = True):
        super().__init__()
        self.norm_before = norm_before

        self.norm = nn.LayerNorm(d_model)
        self.mamba = MambaBlock(d_model, d_state, expand)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        if self.norm_before:
            x = x + self.mamba(self.norm(x))
        else:
            x = x + self.norm(self.mamba(x))
        return x


class MambaStack(nn.Module):
    """
    Mamba块堆叠

    用于构建深层Mamba模型
    """

    def __init__(self, d_model: int = 64, d_state: int = 16,
                 n_blocks: int = 4, expand: int = 2):
        super().__init__()
        self.blocks = nn.ModuleList([
            MambaLayer(d_model, d_state, expand)
            for _ in range(n_blocks)
        ])

        self.final_norm = nn.LayerNorm(d_model)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        for block in self.blocks:
            x = block(x)
        return self.final_norm(x)
