"""
QuantSystem - 多因子量化交易系统
主入口
"""

import argparse
import yaml
from pathlib import Path
from datetime import datetime, timedelta

import pandas as pd
import torch
import torch.utils.data

from data.collector import DataCollector
from data.database import Database, get_database
from factors import (
    FactorPreprocessor, FactorEvaluator,
    MomentumFactor, VolatilityFactor,
)
from strategy import MultiFactorStrategy, PortfolioConstructor
from backtest import BacktestEngine, PerformanceAnalyzer
from analysis import Visualizer, ReportGenerator
from utils import log, setup_logger


def run_backtest(config_path: str = None,
                 start_date: str = None,
                 end_date: str = None,
                 initial_cash: float = 1000000):
    """
    运行回测流程

    Args:
        config_path: 配置文件路径
        start_date: 回测起始日期
        end_date: 回测结束日期
        initial_cash: 初始资金
    """
    log.info("=" * 50)
    log.info("多因子量化交易系统 - 启动")
    log.info("=" * 50)

    # 默认配置
    if config_path is None:
        config_path = Path(__file__).parent / "config" / "config.yaml"

    if start_date is None:
        start_date = (datetime.now() - timedelta(days=365 * 2)).strftime("%Y-%m-%d")
    if end_date is None:
        end_date = datetime.now().strftime("%Y-%m-%d")

    log.info(f"回测期间: {start_date} ~ {end_date}")
    log.info(f"初始资金: {initial_cash:,.2f}")

    # ========== Step 1: 数据采集 ==========
    log.info("\n--- Step 1: 数据采集 ---")
    collector = DataCollector(config_path)

    # 获取交易日历
    log.info("获取交易日历...")
    trade_calendar = collector.calendar.get_trade_calendar()
    log.info(f"交易日历: {len(trade_calendar)} 个交易日")

    # 获取股票列表
    log.info("获取股票列表...")
    stock_list = collector.stock.get_stock_list()
    log.info(f"股票数量: {len(stock_list)}")

    # 获取指数数据
    log.info("获取指数数据(沪深300)...")
    benchmark_data = collector.stock.get_index_daily(
        '000300', start_date.replace('-', ''), end_date.replace('-', '')
    )
    log.info(f"基准数据: {len(benchmark_data)} 条")

    # 获取成分股数据（示例：沪深300部分成分股）
    log.info("获取股票行情数据...")
    sample_codes = stock_list['code'].head(100).tolist()  # 取前100只做演示
    price_data = collector.stock.get_stock_daily_batch(
        sample_codes,
        start_date.replace('-', ''),
        end_date.replace('-', '')
    )
    log.info(f"行情数据: {len(price_data)} 条")

    if price_data.empty:
        log.error("无法获取行情数据，请检查网络连接")
        return

    # ========== Step 2: 因子计算 ==========
    log.info("\n--- Step 2: 因子计算 ---")
    strategy = MultiFactorStrategy(
        Path(__file__).parent / "config" / "factors.yaml"
    )

    factor_data = strategy.calculate_all_factors(price_data)
    log.info(f"因子计算完成: {len(factor_data)} 条")

    # ========== Step 3: 回测 ==========
    log.info("\n--- Step 3: 回测 ---")
    engine = BacktestEngine(
        initial_cash=initial_cash,
    )
    engine.set_data(
        price_data=price_data,
        trade_calendar=trade_calendar,
        benchmark_data=benchmark_data,
    )
    engine.set_strategy(
        strategy=strategy,
        rebalance_freq='monthly',
        top_n=30,
    )

    results = engine.run(start_date, end_date)

    # ========== Step 4: 分析与报告 ==========
    log.info("\n--- Step 4: 分析与报告 ---")
    if results:
        # 绩效分析
        analyzer = PerformanceAnalyzer()
        analyzer.print_summary(results['performance'])

        # 可视化
        viz = Visualizer()
        if 'nav' in results:
            nav_fig = viz.plot_nav(results['nav'])
            viz.save_figure(nav_fig, "reports/nav_curve.png")

            dd_fig = viz.plot_drawdown(results['nav'])
            viz.save_figure(dd_fig, "reports/drawdown.png")

            ret_fig = viz.plot_returns(results['nav'])
            viz.save_figure(ret_fig, "reports/returns.png")

        # 生成报告
        report_gen = ReportGenerator("reports")
        report_path = report_gen.generate_html(results)
        log.info(f"报告已生成: {report_path}")

        # 保存摘要
        summary = report_gen.generate_summary(results)
        log.info(summary)

    log.info("回测完成!")


def run_data_update(config_path: str = None):
    """
    更新数据（增量）

    Args:
        config_path: 配置文件路径
    """
    log.info("开始数据更新...")

    collector = DataCollector(config_path)
    data = collector.initialize_data()

    for key, df in data.items():
        if not df.empty:
            log.info(f"{key}: {len(df)} 条数据")

    log.info("数据更新完成")


def run_ai_backtest(config_path: str = None,
                    start_date: str = None,
                    end_date: str = None,
                    initial_cash: float = 1000000,
                    ctm_model: str = None,
                    mamba_model: str = None,
                    deepseek_key: str = None):
    """
    运行AI增强回测 (CTM + Mamba + DeepSeek反思)

    Args:
        config_path: 配置文件路径
        start_date: 回测起始日期
        end_date: 回测结束日期
        initial_cash: 初始资金
        ctm_model: CTM模型路径
        mamba_model: Mamba模型路径
        deepseek_key: DeepSeek API密钥
    """
    from strategy.ctm_strategy import CTMEnhancedStrategy

    log.info("=" * 50)
    log.info("多因子量化交易系统 - AI增强模式")
    log.info("CTM + Mamba + DeepSeek 反思推理")
    log.info("=" * 50)

    if config_path is None:
        config_path = Path(__file__).parent / "config" / "config.yaml"

    if start_date is None:
        start_date = (datetime.now() - timedelta(days=365 * 2)).strftime("%Y-%m-%d")
    if end_date is None:
        end_date = datetime.now().strftime("%Y-%m-%d")

    # ========== Step 1: 初始化AI策略 ==========
    log.info("\n--- Step 1: 初始化AI策略 ---")
    strategy = CTMEnhancedStrategy(
        Path(__file__).parent / "config" / "factors.yaml"
    )

    # 加载AI模型
    strategy.load_models(
        ctm_model_path=ctm_model,
        mamba_model_path=mamba_model,
        deepseek_api_key=deepseek_key,
    )

    log.info(f"CTM: {'启用' if strategy.ctm_enabled else '未启用'}")
    log.info(f"Mamba: {'启用' if strategy.mamba_enabled else '未启用'}")
    log.info(f"DeepSeek反思: {'启用' if strategy.reflection_enabled else '未启用'}")

    # ========== Step 2: 数据采集 ==========
    log.info("\n--- Step 2: 数据采集 ---")
    collector = DataCollector(config_path)

    trade_calendar = collector.calendar.get_trade_calendar()
    stock_list = collector.stock.get_stock_list()

    benchmark_data = collector.stock.get_index_daily(
        '000300', start_date.replace('-', ''), end_date.replace('-', '')
    )

    sample_codes = stock_list['code'].head(100).tolist()
    price_data = collector.stock.get_stock_daily_batch(
        sample_codes,
        start_date.replace('-', ''),
        end_date.replace('-', '')
    )

    if price_data.empty:
        log.error("无法获取行情数据")
        return

    # ========== Step 3: 回测 ==========
    log.info("\n--- Step 3: AI增强回测 ---")
    engine = BacktestEngine(initial_cash=initial_cash)
    engine.set_data(
        price_data=price_data,
        trade_calendar=trade_calendar,
        benchmark_data=benchmark_data,
    )

    # 直接使用CTM增强策略
    from backtest.engine import BacktestEngine as BE
    engine._get_target_positions = lambda date: _ai_target_positions(
        strategy, price_data, None, date
    )

    results = engine.run(start_date, end_date)

    # ========== Step 4: 分析报告 ==========
    if results:
        analyzer = PerformanceAnalyzer()
        analyzer.print_summary(results['performance'])

        viz = Visualizer()
        if 'nav' in results:
            nav_fig = viz.plot_nav(results['nav'], title="AI增强策略净值曲线")
            viz.save_figure(nav_fig, "reports/ai_nav_curve.png")

        report_gen = ReportGenerator("reports")
        report_path = report_gen.generate_html(results, strategy_name="CTM_Enhanced")
        log.info(f"报告已生成: {report_path}")

    log.info("AI增强回测完成!")


def _ai_target_positions(strategy, price_data, financial_data, date):
    """AI策略目标持仓"""
    try:
        signals = strategy.generate_signals(
            price_data, financial_data, date=date
        )
        if signals.empty:
            return {}

        constructor = PortfolioConstructor(max_weight=0.05)
        return constructor.construct(signals, method='score')
    except Exception as e:
        log.error(f"AI策略信号生成失败: {e}")
        return {}


def run_ctm_train(config_path: str = None,
                  epochs: int = 50,
                  batch_size: int = 32):
    """
    训练CTM因子模型

    Args:
        config_path: 配置文件路径
        epochs: 训练轮数
        batch_size: 批大小
    """
    from factors.ctm import CTMTrainer, StockTimeSeriesDataset

    log.info("=" * 50)
    log.info("CTM模型训练")
    log.info("=" * 50)

    # 获取数据
    collector = DataCollector(config_path)
    stock_list = collector.stock.get_stock_list()
    sample_codes = stock_list['code'].head(200).tolist()

    end_date = datetime.now().strftime("%Y%m%d")
    start_date = (datetime.now() - timedelta(days=365 * 3)).strftime("%Y%m%d")

    price_data = collector.stock.get_stock_daily_batch(
        sample_codes, start_date, end_date
    )

    if price_data.empty:
        log.error("无法获取训练数据")
        return

    # 构建数据集
    dataset = StockTimeSeriesDataset(price_data, seq_len=120, min_seq_len=60)

    # 训练/验证分割
    n = len(dataset)
    train_n = int(n * 0.8)
    train_data = torch.utils.data.Subset(dataset, range(train_n))
    val_data = torch.utils.data.Subset(dataset, range(train_n, n))

    # 训练
    trainer = CTMTrainer(device='cpu', model_dir="models/ctm")
    history = trainer.train(
        train_data=train_data,
        val_data=val_data,
        epochs=epochs,
        batch_size=batch_size,
    )

    log.info("CTM模型训练完成!")


def run_mamba_train(config_path: str = None,
                    epochs: int = 30,
                    batch_size: int = 32):
    """
    训练Mamba时序推理模型

    Args:
        config_path: 配置文件路径
        epochs: 训练轮数
        batch_size: 批大小
    """
    from factors.mamba import TemporalReasonerTrainer
    from factors.ctm import StockTimeSeriesDataset

    log.info("=" * 50)
    log.info("Mamba时序推理器训练")
    log.info("=" * 50)

    collector = DataCollector(config_path)
    stock_list = collector.stock.get_stock_list()
    sample_codes = stock_list['code'].head(200).tolist()

    end_date = datetime.now().strftime("%Y%m%d")
    start_date = (datetime.now() - timedelta(days=365 * 3)).strftime("%Y%m%d")

    price_data = collector.stock.get_stock_daily_batch(
        sample_codes, start_date, end_date
    )

    if price_data.empty:
        log.error("无法获取训练数据")
        return

    dataset = StockTimeSeriesDataset(price_data, seq_len=120)

    trainer = TemporalReasonerTrainer(device='cpu', model_dir="models/mamba")
    trainer.train(dataset, epochs=epochs, batch_size=batch_size)

    log.info("Mamba模型训练完成!")


def run_rl_train(config_path: str = None,
                 total_timesteps: int = 50000):
    """
    训练RL反思策略

    Args:
        config_path: 配置文件路径
        total_timesteps: 总训练步数
    """
    from factors.rl import TradingEnv, RLReflectiveTrainer

    log.info("=" * 50)
    log.info("RL反思策略训练")
    log.info("=" * 50)

    collector = DataCollector(config_path)
    stock_list = collector.stock.get_stock_list()

    end_date = datetime.now().strftime("%Y%m%d")
    start_date = (datetime.now() - timedelta(days=365 * 2)).strftime("%Y%m%d")

    benchmark_data = collector.stock.get_index_daily('000300', start_date, end_date)
    price_data = collector.stock.get_stock_daily_batch(
        stock_list['code'].head(100).tolist(), start_date, end_date
    )

    if price_data.empty:
        log.error("无法获取训练数据")
        return

    env = TradingEnv(price_data, benchmark_data, lookback_window=60)

    trainer = RLReflectiveTrainer(env, model_dir="models/rl", device="cpu")
    trainer.train(total_timesteps=total_timesteps)

    results = trainer.evaluate(n_episodes=5)
    log.info(f"评估结果: {results}")

    log.info("RL策略训练完成!")


def main():
    parser = argparse.ArgumentParser(description="多因子量化交易系统")
    parser.add_argument('command',
                       choices=['backtest', 'ai_backtest', 'update', 'factor_test',
                               'train_ctm', 'train_mamba', 'train_rl'],
                       help='命令: backtest(传统回测) / ai_backtest(AI增强回测) / '
                            'update(更新数据) / train_ctm(训练CTM) / '
                            'train_mamba(训练Mamba) / train_rl(训练RL)')
    parser.add_argument('--start', type=str, help='开始日期 YYYY-MM-DD')
    parser.add_argument('--end', type=str, help='结束日期 YYYY-MM-DD')
    parser.add_argument('--cash', type=float, default=1000000, help='初始资金')
    parser.add_argument('--config', type=str, help='配置文件路径')
    parser.add_argument('--ctm-model', type=str, help='CTM模型路径')
    parser.add_argument('--mamba-model', type=str, help='Mamba模型路径')
    parser.add_argument('--deepseek-key', type=str, help='DeepSeek API密钥')
    parser.add_argument('--epochs', type=int, default=50, help='训练轮数')
    parser.add_argument('--timesteps', type=int, default=50000, help='RL训练步数')

    args = parser.parse_args()

    if args.command == 'backtest':
        run_backtest(args.config, args.start, args.end, args.cash)
    elif args.command == 'ai_backtest':
        run_ai_backtest(args.config, args.start, args.end, args.cash,
                       args.ctm_model, args.mamba_model, args.deepseek_key)
    elif args.command == 'update':
        run_data_update(args.config)
    elif args.command == 'train_ctm':
        run_ctm_train(args.config, args.epochs)
    elif args.command == 'train_mamba':
        run_mamba_train(args.config, args.epochs)
    elif args.command == 'train_rl':
        run_rl_train(args.config, args.timesteps)


if __name__ == '__main__':
    main()
