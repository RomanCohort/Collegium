#!/usr/bin/env python
"""
QuantSystem 主入口
量化交易系统命令行工具
"""
import argparse
import sys
from pathlib import Path
from datetime import datetime, timedelta

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent))

from utils.logger import log
from config.settings import BACKTEST_CONFIG, RISK_CONFIG


def run_backtest(args):
    """运行回测"""
    from data.fetcher import fetcher
    from data.cleaner import cleaner
    from backtest.engine import BacktestEngine
    from backtest.performance import performance_analyzer
    from analysis.report import report_generator
    from strategy.momentum import MomentumStrategy, DualMAStrategy
    from strategy.mean_reversion import MeanReversionStrategy

    log.info("=" * 50)
    log.info("开始回测")
    log.info("=" * 50)

    # 参数
    start_date = args.start_date or (datetime.now() - timedelta(days=365)).strftime("%Y-%m-%d")
    end_date = args.end_date or datetime.now().strftime("%Y-%m-%d")
    initial_capital = args.capital or BACKTEST_CONFIG["initial_capital"]

    log.info(f"回测区间: {start_date} ~ {end_date}")
    log.info(f"初始资金: {initial_capital:,.0f}")

    # 获取数据
    log.info("获取数据...")
    if args.symbols:
        symbols = args.symbols.split(",")
    else:
        # 默认测试股票池
        symbols = ["000001", "600000", "000002", "600036", "000333"]

    all_data = fetcher.get_batch_daily_prices(symbols, start_date, end_date)

    if all_data.empty:
        log.error("无法获取数据，请检查网络或参数")
        return

    # 清洗数据
    log.info("清洗数据...")
    all_data = cleaner.clean_prices(all_data)

    # 选择策略
    strategy_map = {
        "momentum": MomentumStrategy(lookback_period=20),
        "dual_ma": DualMAStrategy(fast_period=5, slow_period=20),
        "mean_reversion": MeanReversionStrategy(window=20),
    }

    strategy = strategy_map.get(args.strategy, DualMAStrategy())
    log.info(f"使用策略: {strategy.name}")

    # 运行回测
    log.info("运行回测引擎...")
    engine = BacktestEngine(strategy, initial_capital=initial_capital)
    results = engine.run(all_data)

    if not results:
        log.error("回测失败")
        return

    # 打印结果
    print("\n" + "=" * 50)
    print("回测结果")
    print("=" * 50)
    print(f"总收益率: {results['total_return']:.2%}")
    print(f"年化收益: {results['annual_return']:.2%}")
    print(f"年化波动: {results['annual_volatility']:.2%}")
    print(f"最大回撤: {results['max_drawdown']:.2%}")
    print(f"夏普比率: {results['sharpe_ratio']:.2f}")
    print(f"总交易次数: {results['total_trades']}")
    print(f"胜率: {results['win_rate']:.2%}")
    print(f"总佣金: {results['total_commission']:.2f}")
    print("=" * 50 + "\n")

    # 生成报告
    if args.report:
        log.info("生成报告...")
        report_path = report_generator.generate(
            results,
            strategy_name=strategy.name,
            save_html=True,
            save_csv=True,
        )
        log.info(f"报告已保存: {report_path}")

    return results


def run_fetch_data(args):
    """获取数据"""
    from data.fetcher import fetcher
    from data.storage import storage

    log.info("获取数据...")

    start_date = args.start_date or "2023-01-01"
    end_date = args.end_date or datetime.now().strftime("%Y-%m-%d")

    if args.symbols:
        symbols = args.symbols.split(",")
    else:
        # 获取股票列表
        stock_list = fetcher.get_stock_list()
        symbols = stock_list["symbol"].tolist()[:100]  # 默认取前100只

    log.info(f"获取 {len(symbols)} 只股票数据...")

    data = fetcher.get_batch_daily_prices(symbols, start_date, end_date)

    if not data.empty:
        storage.save_daily_prices(data)
        log.info(f"数据已保存，共 {len(data)} 条记录")
    else:
        log.warning("未获取到数据")


def run_paper_trading(args):
    """纸面交易"""
    from execution.simulator import PaperTrading
    from strategy.momentum import DualMAStrategy

    log.info("启动纸面交易...")

    strategy = DualMAStrategy()
    paper = PaperTrading(strategy)

    log.info("纸面交易已启动（模拟模式）")
    log.info("按 Ctrl+C 停止")

    # 这里可以添加实时数据订阅逻辑
    print(f"初始资金: {paper.simulator.get_cash():,.0f}")
    print(f"当前状态: {paper.get_status()}")


def show_status(args):
    """显示系统状态"""
    from data.storage import storage

    print("\n" + "=" * 50)
    print("QuantSystem 状态")
    print("=" * 50)

    # 数据状态
    status = storage.get_data_status()
    print(f"股票数量: {status.get('stock_count', 0)}")
    print(f"数据条数: {status.get('record_count', 0)}")
    print(f"日期范围: {status.get('date_range', ('N/A', 'N/A'))}")

    # 配置
    print(f"\n回测配置:")
    print(f"  初始资金: {BACKTEST_CONFIG['initial_capital']:,.0f}")
    print(f"  佣金率: {BACKTEST_CONFIG['commission_rate']:.4%}")
    print(f"  滑点率: {BACKTEST_CONFIG['slippage_rate']:.4%}")

    print(f"\n风控配置:")
    print(f"  单只最大仓位: {RISK_CONFIG['max_position_pct']:.1%}")
    print(f"  最大回撤熔断: {RISK_CONFIG['max_drawdown_stop']:.1%}")

    print("=" * 50 + "\n")


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="QuantSystem - 量化交易系统",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 运行回测
  python main.py backtest --symbols 000001,600000 --start-date 2023-01-01

  # 获取数据
  python main.py fetch --symbols 000001,600000 --start-date 2023-01-01

  # 查看状态
  python main.py status
        """
    )

    subparsers = parser.add_subparsers(dest="command", help="可用命令")

    # 回测命令
    backtest_parser = subparsers.add_parser("backtest", help="运行回测")
    backtest_parser.add_argument("--symbols", type=str, help="股票代码，逗号分隔")
    backtest_parser.add_argument("--start-date", type=str, help="开始日期 YYYY-MM-DD")
    backtest_parser.add_argument("--end-date", type=str, help="结束日期 YYYY-MM-DD")
    backtest_parser.add_argument("--capital", type=float, help="初始资金")
    backtest_parser.add_argument("--strategy", type=str, default="dual_ma",
                                  choices=["momentum", "dual_ma", "mean_reversion"],
                                  help="策略类型")
    backtest_parser.add_argument("--report", action="store_true", help="生成报告")

    # 数据获取命令
    fetch_parser = subparsers.add_parser("fetch", help="获取数据")
    fetch_parser.add_argument("--symbols", type=str, help="股票代码，逗号分隔")
    fetch_parser.add_argument("--start-date", type=str, help="开始日期")
    fetch_parser.add_argument("--end-date", type=str, help="结束日期")

    # 纸面交易命令
    paper_parser = subparsers.add_parser("paper", help="纸面交易")

    # 状态命令
    status_parser = subparsers.add_parser("status", help="显示系统状态")

    args = parser.parse_args()

    if args.command == "backtest":
        run_backtest(args)
    elif args.command == "fetch":
        run_fetch_data(args)
    elif args.command == "paper":
        run_paper_trading(args)
    elif args.command == "status":
        show_status(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()