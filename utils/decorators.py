"""
装饰器工具
提供计时、重试、缓存等装饰器
"""
import time
import functools
from typing import Callable, Any
from utils.logger import log


def timer(func: Callable) -> Callable:
    """
    计时装饰器，记录函数执行时间
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.perf_counter()
        result = func(*args, **kwargs)
        end_time = time.perf_counter()
        log.debug(f"{func.__name__} 执行耗时: {end_time - start_time:.4f} 秒")
        return result
    return wrapper


def retry(max_attempts: int = 3, delay: float = 1.0, exceptions: tuple = (Exception,)):
    """
    重试装饰器

    Args:
        max_attempts: 最大重试次数
        delay: 重试间隔（秒）
        exceptions: 需要重试的异常类型
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(1, max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    if attempt == max_attempts:
                        log.error(f"{func.__name__} 重试 {max_attempts} 次后仍失败: {e}")
                        raise
                    log.warning(f"{func.__name__} 第 {attempt} 次失败，{delay}秒后重试: {e}")
                    time.sleep(delay)
            return None
        return wrapper
    return decorator


def cache_result(expire: int = 3600):
    """
    简单的结果缓存装饰器

    Args:
        expire: 缓存过期时间（秒）
    """
    cache = {}

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # 创建缓存键
            key = (func.__name__, args, tuple(sorted(kwargs.items())))
            current_time = time.time()

            if key in cache:
                result, timestamp = cache[key]
                if current_time - timestamp < expire:
                    log.debug(f"{func.__name__} 使用缓存结果")
                    return result

            result = func(*args, **kwargs)
            cache[key] = (result, current_time)
            return result
        return wrapper
    return decorator


def validate_input(*validators: Callable):
    """
    输入验证装饰器

    Args:
        validators: 验证函数列表，每个函数接收对应位置的参数
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            for i, validator in enumerate(validators):
                if i < len(args):
                    if not validator(args[i]):
                        raise ValueError(f"参数 {i} 验证失败: {args[i]}")
            return func(*args, **kwargs)
        return wrapper
    return decorator


def exception_handler(default_return: Any = None, log_error: bool = True):
    """
    异常处理装饰器

    Args:
        default_return: 发生异常时的默认返回值
        log_error: 是否记录错误日志
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                if log_error:
                    log.exception(f"{func.__name__} 执行出错: {e}")
                return default_return
        return wrapper
    return decorator
