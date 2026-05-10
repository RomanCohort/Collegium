"""
QuantSystem 全局配置
"""
import os
from pathlib import Path
from datetime import datetime

# 项目根目录
PROJECT_ROOT = Path(__file__).parent.parent.absolute()

# 数据目录
DATA_DIR = PROJECT_ROOT / "data" / "cache"
LOG_DIR = PROJECT_ROOT / "logs"

# 确保目录存在
DATA_DIR.mkdir(parents=True, exist_ok=True)
LOG_DIR.mkdir(parents=True, exist_ok=True)

# 数据源配置
DATA_SOURCE = "akshare"  # akshare / tushare / local

# 回测配置
BACKTEST_CONFIG = {
    "initial_capital": 1000000,  # 初始资金 100万
    "commission_rate": 0.0003,   # 佣金率 0.03%
    "slippage_rate": 0.0001,     # 滑点率 0.01%
    "stamp_duty": 0.001,         # 印花税 0.1%（仅卖出）
    "min_commission": 5,         # 最低佣金 5元
    "benchmark": "000300",       # 沪深300作为基准
}

# 风控配置
RISK_CONFIG = {
    "max_position_pct": 0.2,     # 单只股票最大仓位 20%
    "max_sector_pct": 0.3,       # 单行业最大仓位 30%
    "max_drawdown_stop": 0.15,   # 最大回撤熔断阈值 15%
    "single_loss_limit": 0.02,   # 单笔亏损上限 2%
    "max_leverage": 1.0,         # 最大杠杆（无杠杆）
}

# 策略默认参数
STRATEGY_DEFAULTS = {
    "momentum": {
        "lookback_period": 20,
        "holding_period": 10,
    },
    "mean_reversion": {
        "window": 20,
        "entry_zscore": 2.0,
        "exit_zscore": 0.5,
    },
    "multi_factor": {
        "top_n": 30,              # 选股数量
        "rebalance_freq": 5,      # 调仓频率（天）
    },
}

# 日志配置
LOG_CONFIG = {
    "level": "INFO",
    "format": "{time:YYYY-MM-DD HH:mm:ss} | {level} | {name} | {message}",
    "rotation": "10 MB",
    "retention": "30 days",
}

# 监控配置
MONITOR_CONFIG = {
    "alert_email": None,         # 告警邮箱（可选）
    "dashboard_port": 8501,      # Streamlit 端口
    "update_interval": 60,       # 更新间隔（秒）
}

# 数据库配置（可选）
DATABASE_CONFIG = {
    "type": "sqlite",            # sqlite / postgresql
    "path": DATA_DIR / "quant.db",
}