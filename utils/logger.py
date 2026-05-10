"""
日志工具模块
使用 loguru 提供结构化日志
"""
import sys
from pathlib import Path
from loguru import logger
from config.settings import LOG_DIR, LOG_CONFIG


def setup_logger(name: str = "quant"):
    """
    配置并返回 logger 实例

    Args:
        name: logger 名称

    Returns:
        配置好的 logger 实例
    """
    # 移除默认 handler
    logger.remove()

    # 控制台输出
    logger.add(
        sys.stdout,
        level=LOG_CONFIG["level"],
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
               "<level>{level: <8}</level> | "
               "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
               "<level>{message}</level>",
        colorize=True,
    )

    # 文件输出 - 普通日志
    logger.add(
        LOG_DIR / "{time:YYYY-MM-DD}.log",
        level="INFO",
        format=LOG_CONFIG["format"],
        rotation=LOG_CONFIG["rotation"],
        retention=LOG_CONFIG["retention"],
        encoding="utf-8",
    )

    # 文件输出 - 错误日志单独存放
    logger.add(
        LOG_DIR / "error_{time:YYYY-MM-DD}.log",
        level="ERROR",
        format=LOG_CONFIG["format"],
        rotation=LOG_CONFIG["rotation"],
        retention=LOG_CONFIG["retention"],
        encoding="utf-8",
    )

    # 文件输出 - 交易日志（用于复盘）
    logger.add(
        LOG_DIR / "trades_{time:YYYY-MM-DD}.log",
        level="INFO",
        format=LOG_CONFIG["format"],
        filter=lambda record: record["extra"].get("type") == "trade",
        rotation=LOG_CONFIG["rotation"],
        retention="90 days",  # 交易日志保留更久
        encoding="utf-8",
    )

    return logger.bind(name=name)


# 全局 logger 实例
log = setup_logger()


def trade_log(action: str, symbol: str, price: float, quantity: int, **kwargs):
    """
    记录交易日志

    Args:
        action: 买入/卖出
        symbol: 股票代码
        price: 成交价格
        quantity: 成交数量
        **kwargs: 其他信息（策略名、信号等）
    """
    extra_info = " | ".join([f"{k}={v}" for k, v in kwargs.items()])
    log.bind(type="trade").info(
        f"TRADE | {action} | {symbol} | 价格:{price:.2f} | 数量:{quantity} | {extra_info}"
    )


def signal_log(strategy: str, symbol: str, signal: str, reason: str = ""):
    """
    记录信号日志

    Args:
        strategy: 策略名称
        symbol: 股票代码
        signal: 信号类型（BUY/SELL/HOLD）
        reason: 信号原因
    """
    log.bind(type="trade").info(
        f"SIGNAL | {strategy} | {symbol} | {signal} | {reason}"
    )
