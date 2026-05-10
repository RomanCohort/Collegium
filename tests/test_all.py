"""
单元测试
"""
import unittest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta


class TestDataFetcher(unittest.TestCase):
    """数据获取测试"""

    def test_stock_list(self):
        """测试获取股票列表"""
        from data.fetcher import DataFetcher
        fetcher = DataFetcher(cache_enabled=False)
        # 不实际调用 API，只测试初始化
        self.assertIsNotNone(fetcher)

    def test_daily_prices_format(self):
        """测试日线数据格式"""
        # 模拟数据
        df = pd.DataFrame({
            "date": pd.date_range("2024-01-01", periods=10),
            "open": [10.0] * 10,
            "close": [10.5] * 10,
            "high": [11.0] * 10,
            "low": [9.5] * 10,
            "volume": [1000000] * 10,
        })
        self.assertEqual(len(df), 10)
        self.assertIn("close", df.columns)


class TestDataCleaner(unittest.TestCase):
    """数据清洗测试"""

    def test_clean_prices(self):
        """测试价格清洗"""
        from data.cleaner import DataCleaner
        cleaner = DataCleaner()

        df = pd.DataFrame({
            "date": pd.date_range("2024-01-01", periods=10),
            "open": [10.0, np.nan, 10.2, 10.3, 10.4, 10.5, 10.6, 10.7, 10.8, 10.9],
            "close": [10.1, 10.1, 10.2, 10.3, 10.4, 10.5, 10.6, 10.7, 10.8, 10.9],
            "high": [10.5] * 10,
            "low": [9.8] * 10,
            "volume": [1000000] * 10,
        })

        cleaned = cleaner.clean_prices(df)
        self.assertLessEqual(cleaned.isnull().sum().sum(), 0)


class TestTechnicalFactors(unittest.TestCase):
    """技术因子测试"""

    def test_sma(self):
        """测试简单移动平均"""
        from factors.technical import sma
        series = pd.Series([1, 2, 3, 4, 5, 6, 7, 8, 9, 10])
        result = sma(series, 5)
        self.assertEqual(result.iloc[-1], 8.0)

    def test_rsi(self):
        """测试 RSI"""
        from factors.technical import rsi
        np.random.seed(42)
        prices = pd.Series(100 + np.cumsum(np.random.randn(100) * 0.02))
        rsi_values = rsi(prices, 14)
        self.assertTrue((rsi_values.dropna() >= 0).all() and (rsi_values.dropna() <= 100).all())

    def test_macd(self):
        """测试 MACD"""
        from factors.technical import macd
        prices = pd.Series([10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20] * 3)
        macd_df = macd(prices)
        self.assertIn("macd_dif", macd_df.columns)
        self.assertIn("macd_dea", macd_df.columns)


class TestPositionSizer(unittest.TestCase):
    """仓位管理测试"""

    def test_fixed_position(self):
        """测试固定比例仓位"""
        from risk_manager.position_sizer import PositionSizer
        sizer = PositionSizer(method="fixed")
        result = sizer.calculate_position_size(
            capital=100000,
            price=10.0,
            stop_loss_pct=0.05,
        )
        self.assertGreater(result["quantity"], 0)
        self.assertLessEqual(result["position_pct"], 0.2)

    def test_atr_position(self):
        """测试 ATR 仓位"""
        from risk_manager.position_sizer import PositionSizer
        sizer = PositionSizer(method="atr")
        result = sizer.calculate_position_size(
            capital=100000,
            price=10.0,
            stop_loss_pct=0.05,
            atr=0.5,
        )
        self.assertGreater(result["quantity"], 0)


class TestStopLoss(unittest.TestCase):
    """止损测试"""

    def test_fixed_stop_loss(self):
        """测试固定止损"""
        from risk_manager.stop_loss import StopLossManager
        manager = StopLossManager()
        manager.record_entry("000001", 10.0, 1000, "2024-01-01")

        should_stop, reason, price = manager.should_stop_loss(
            symbol="000001",
            current_price=9.0,
            stop_type="fixed",
            stop_pct=0.05,
        )
        self.assertTrue(should_stop)

    def test_trailing_stop(self):
        """测试追踪止损"""
        from risk_manager.stop_loss import StopLossManager
        manager = StopLossManager()
        manager.record_entry("000001", 10.0, 1000, "2024-01-01")
        manager.update_price("000001", 12.0)  # 更新最高价

        should_stop, reason, price = manager.should_stop_loss(
            symbol="000001",
            current_price=10.5,
            stop_type="trailing",
            trailing_pct=0.1,
        )
        self.assertTrue(should_stop)


class TestDrawdownGuard(unittest.TestCase):
    """回撤熔断测试"""

    def test_drawdown_trigger(self):
        """测试回撤触发"""
        from risk_manager.drawdown_guard import DrawdownGuard
        guard = DrawdownGuard(max_drawdown=0.1)

        guard.update_nav("2024-01-01", 1.0)
        guard.update_nav("2024-01-02", 1.1)
        guard.update_nav("2024-01-03", 0.95)  # 回撤约 13.6%

        self.assertTrue(guard.is_paused)


class TestStrategies(unittest.TestCase):
    """策略测试"""

    def setUp(self):
        """设置测试数据"""
        np.random.seed(42)
        dates = pd.date_range("2024-01-01", periods=100)
        self.test_data = pd.DataFrame({
            "date": dates,
            "symbol": "000001",
            "open": 10.0 + np.cumsum(np.random.randn(100) * 0.1),
            "close": 10.0 + np.cumsum(np.random.randn(100) * 0.1),
            "high": 10.5 + np.cumsum(np.random.randn(100) * 0.1),
            "low": 9.5 + np.cumsum(np.random.randn(100) * 0.1),
            "volume": 1000000 + np.random.randint(-100000, 100000, 100),
        })

    def test_momentum_strategy(self):
        """测试动量策略"""
        from strategy.momentum import MomentumStrategy
        strategy = MomentumStrategy(lookback_period=10)
        signals = strategy.generate_signals(self.test_data)
        self.assertIsInstance(signals, list)

    def test_dual_ma_strategy(self):
        """测试双均线策略"""
        from strategy.momentum import DualMAStrategy
        strategy = DualMAStrategy(fast_period=5, slow_period=20)
        signals = strategy.generate_signals(self.test_data)
        self.assertIsInstance(signals, list)

    def test_mean_reversion_strategy(self):
        """测试均值回归策略"""
        from strategy.mean_reversion import MeanReversionStrategy
        strategy = MeanReversionStrategy(window=20)
        signals = strategy.generate_signals(self.test_data)
        self.assertIsInstance(signals, list)


class TestBacktestEngine(unittest.TestCase):
    """回测引擎测试"""

    def setUp(self):
        """设置测试数据"""
        np.random.seed(42)
        dates = pd.date_range("2024-01-01", periods=100)
        self.test_data = pd.DataFrame({
            "date": dates.tolist() * 3,
            "symbol": ["000001"] * 100 + ["000002"] * 100 + ["000003"] * 100,
            "open": 10.0 + np.cumsum(np.random.randn(300) * 0.1),
            "close": 10.0 + np.cumsum(np.random.randn(300) * 0.1),
            "high": 10.5 + np.cumsum(np.random.randn(300) * 0.1),
            "low": 9.5 + np.cumsum(np.random.randn(300) * 0.1),
            "volume": 1000000 + np.random.randint(-100000, 100000, 300),
        })

    def test_backtest_run(self):
        """测试回测运行"""
        from backtest.engine import BacktestEngine
        from strategy.momentum import DualMAStrategy

        strategy = DualMAStrategy(fast_period=5, slow_period=20)
        engine = BacktestEngine(strategy, initial_capital=100000)

        results = engine.run(self.test_data)

        self.assertIn("total_return", results)
        self.assertIn("sharpe_ratio", results)
        self.assertIn("max_drawdown", results)


class TestPerformanceAnalyzer(unittest.TestCase):
    """绩效分析测试"""

    def test_analyze(self):
        """测试绩效分析"""
        from backtest.performance import PerformanceAnalyzer

        nav_series = pd.Series(
            [1.0, 1.02, 1.01, 1.03, 1.05, 1.04, 1.06, 1.08, 1.07, 1.10],
            index=pd.date_range("2024-01-01", periods=10)
        )

        analyzer = PerformanceAnalyzer()
        metrics = analyzer.analyze(nav_series)

        self.assertIn("total_return", metrics)
        self.assertIn("sharpe_ratio", metrics)
        self.assertIn("max_drawdown", metrics)


if __name__ == "__main__":
    unittest.main()
