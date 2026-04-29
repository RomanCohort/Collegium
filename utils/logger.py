"""
日志模块 - 基于loguru的统一日志管理
"""

import sys
from pathlib import Path
from loguru import logger
import yaml


def setup_logger(config_path: str = None) -> logger:
    """
    配置日志系统

    Args:
        config_path: 配置文件路径，默认为config/config.yaml

    Returns:
        配置好的logger对象
    """
    # 移除默认的handler
    logger.remove()

    # 默认配置
    log_config = {
        "level": "INFO",
        "format": "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        "console": True,
        "file": "logs/quant.log",
        "rotation": "100 MB",  # 日志文件达到100MB时轮转
        "retention": "30 days",  # 保留30天
        "compression": "zip",  # 压缩旧日志
    }

    # 尝试加载配置文件
    if config_path and Path(config_path).exists():
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                loaded_config = yaml.safe_load(f)
                if loaded_config and 'logging' in loaded_config:
                    log_config.update(loaded_config['logging'])
        except Exception as e:
            print(f"加载日志配置失败: {e}")

    # 添加控制台输出
    if log_config.get("console", True):
        logger.add(
            sys.stderr,
            level=log_config.get("level", "INFO"),
            format=log_config.get("format"),
            colorize=True,
        )

    # 添加文件输出
    log_file = log_config.get("file")
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        logger.add(
            log_file,
            level=log_config.get("level", "INFO"),
            format=log_config.get("format"),
            rotation=log_config.get("rotation", "100 MB"),
            retention=log_config.get("retention", "30 days"),
            compression=log_config.get("compression", "zip"),
            encoding="utf-8",
        )

    return logger


# 默认导出已配置好的logger
_log = setup_logger()
log = _log

__all__ = ['log', 'setup_logger']
