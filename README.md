# Collegium - AI-Enhanced Quantitative Trading System

> 多时间尺度推理量化交易系统 | CTM + Mamba + DeepSeek 反思增强

[English](#english) | [中文](#中文)

---

## English

### Overview

Collegium is an AI-enhanced multi-factor quantitative trading system designed for A-share/ETF markets. It integrates deep learning models (CTM, Mamba) with LLM-driven reflective reasoning (DeepSeek) to generate more robust trading signals.

### Architecture

```
Collegium/
├── config/              # Configuration files
├── data/                # Data layer (AKShare + PostgreSQL)
├── factors/             # Factor engine
│   ├── ctm/            # CTM (Continuous Thought Model)
│   ├── mamba/         # Mamba SSM (Selective State Space Model)
│   └── rl/            # LLM Reinforcement Learning (DeepSeek + SB3)
├── strategy/           # Trading strategies
├── backtest/          # Backtesting engine
├── analysis/           # Visualization & reporting
├── models/            # Trained models
└── main.py             # Entry point
```

### Key Features

- **Multi-Factor Model**: 10+ technical factors + fundamental factors
- **CTM (Continuous Thought Model)**: Multi-time-scale reasoning via GRU + cross-scale attention
- **Mamba SSM**: Selective state space model for temporal pattern recognition
- **DeepSeek Reflection**: LLM-driven signal validation and risk assessment
- **PPO Training**: Stable-Baselines3 reinforcement learning for strategy optimization
- **Full Backtesting**: Event-driven backtest engine with transaction costs

### Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Traditional backtest
python main.py backtest --start 2024-01-01 --end 2025-01-01

# Train CTM model
python main.py train_ctm --epochs 50

# Train Mamba reasoner
python main.py train_mamba --epochs 30

# Train RL reflective policy
python main.py train_rl --timesteps 50000

# AI-enhanced backtest
python main.py ai_backtest \
    --ctm-model models/ctm/best.pt \
    --mamba-model models/mamba/temporal_reasoner.pt \
    --deepseek-key YOUR_DEEPSEEK_API_KEY
```

### AI Enhancement Layers

| Layer | Model | Function |
|-------|-------|----------|
| 1 | Traditional Factors | Momentum/Reversal/Volatility/PE/PB/ROE |
| 2 | CTM | Multi-time-scale internal reasoning → ctm_momentum/ctm_reversal/ctm_volatility |
| 3 | Mamba | Pattern recognition → trend classification / market regime / anomaly detection |
| 4 | DeepSeek | Reflective reasoning → confidence / weight adjustment / risk flags |

### Requirements

- Python 3.10+
- PyTorch 2.0+ (CPU version)
- PostgreSQL (for data storage)
- DeepSeek API key (for LLM reflection)

---

## 中文

### 简介

Collegium 是一个 AI 增强的多因子量化交易系统，专为 A 股/ETF 市场设计。它集成了深度学习模型（CTM、Mamba）和 LLM 驱动的反思推理（DeepSeek），生成更鲁棒的交易信号。

### 系统架构

```
Collegium/
├── config/              # 配置文件
├── data/                # 数据层 (AKShare + PostgreSQL)
├── factors/             # 因子引擎
│   ├── ctm/            # CTM (连续思维模型)
│   ├── mamba/          # Mamba SSM (选择性状态空间模型)
│   └── rl/             # LLM强化学习 (DeepSeek + SB3)
├── strategy/           # 交易策略
├── backtest/          # 回测引擎
├── analysis/           # 可视化与报告
├── models/             # 训练好的模型
└── main.py             # 入口
```

### 核心功能

- **多因子模型**: 10+ 技术因子 + 基本面因子
- **CTM 连续思维模型**: GRU + 跨尺度注意力融合的多时间尺度推理
- **Mamba SSM**: 选择性状态空间模型，用于时序模式识别
- **DeepSeek 反思**: LLM 驱动的信号验证与风险评估
- **PPO 强化学习**: Stable-Baselines3 训练的反思策略
- **完整回测**: 事件驱动回测引擎，含交易成本

### 快速开始

```bash
# 安装依赖
pip install -r requirements.txt

# 传统回测
python main.py backtest --start 2024-01-01 --end 2025-01-01

# 训练 CTM 模型
python main.py train_ctm --epochs 50

# 训练 Mamba 推理器
python main.py train_mamba --epochs 30

# 训练 RL 反思策略
python main.py train_rl --timesteps 50000

# AI 增强回测
python main.py ai_backtest \
    --ctm-model models/ctm/best.pt \
    --mamba-model models/mamba/temporal_reasoner.pt \
    --deepseek-key YOUR_DEEPSEEK_API_KEY
```

### AI 增强层次

| 层次 | 模型 | 功能 |
|------|------|------|
| 1 | 传统因子 | 动量/反转/波动率/估值/质量/成长 |
| 2 | CTM | 多时间尺度内部推理 → ctm_momentum/ctm_reversal/ctm_volatility |
| 3 | Mamba | 模式识别 → 趋势分类/市场状态/异常检测 |
| 4 | DeepSeek | 反思推理 → 置信度/权重调整/风险标记 |

### 注意事项

- 本系统仅供研究和学习使用
- 实盘交易请谨慎评估风险
- 过去表现不代表未来收益

### License

MIT License

---

## 联系我 / Contact

如果你觉得这个项目有帮助，欢迎 star！

For questions or collaboration, feel free to open an issue.
