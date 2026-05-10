# QuantSystem

A股量化交易系统

## 功能模块

- **data**: 数据获取、存储、清洗
- **factors**: 技术因子、基本面因子、另类因子
- **strategy**: 动量策略、均值回归、多因子选股
- **risk_manager**: 仓位管理、止损、回撤熔断
- **backtest**: 回测引擎、绩效分析
- **execution**: 模拟交易
- **analysis**: 报告生成、可视化
- **monitoring**: 实时监控

## 快速开始

```bash
# 安装依赖
pip install pandas numpy akshare loguru matplotlib plotly scipy statsmodels

# 运行回测
python main.py backtest --symbols 000001,600000 --start-date 2023-01-01 --report

# 获取数据
python main.py fetch --symbols 000001,600000

# 查看状态
python main.py status
```

## 项目结构

```
QuantSystem/
├── config/          # 配置文件
├── data/            # 数据模块
├── factors/         # 因子计算
├── strategy/        # 交易策略
├── risk_manager/    # 风控模块
├── backtest/        # 回测引擎
├── execution/       # 执行模块
├── analysis/        # 分析报告
├── monitoring/      # 监控模块
├── utils/           # 工具函数
├── tests/           # 单元测试
└── main.py          # 主入口
```

## 策略示例

```python
from strategy.momentum import DualMAStrategy
from backtest.engine import BacktestEngine

strategy = DualMAStrategy(fast_period=5, slow_period=20)
engine = BacktestEngine(strategy, initial_capital=1000000)
results = engine.run(data)
```

## 风控配置

在 `config/settings.py` 中配置：

- 单只股票最大仓位: 20%
- 最大回撤熔断: 15%
- 单笔亏损上限: 2%
- 行业集中度限制: 30%
