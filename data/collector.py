"""
数据采集模块 - 基于AKShare的数据获取
"""

import time
from typing import Optional, List, Dict, Union
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd
import numpy as np
import akshare as ak
import yaml

from ..utils import log, format_code


class BaseCollector:
    """数据采集基类"""

    def __init__(self, config_path: str = None):
        if config_path is None:
            config_path = Path(__file__).parent.parent / "config" / "config.yaml"

        with open(config_path, 'r', encoding='utf-8') as f:
            self.config = yaml.safe_load(f)

        self.data_config = self.config.get('data_source', {}).get('akshare', {})
        self.retry_times = self.data_config.get('retry_times', 3)
        self.retry_delay = self.data_config.get('retry_delay', 5)
        self.timeout = self.data_config.get('timeout', 30)

    def _retry_request(self, func, *args, **kwargs) -> Optional[pd.DataFrame]:
        """
        带重试的请求

        Args:
            func: 请求函数
            args, kwargs: 函数参数

        Returns:
            数据DataFrame或None
        """
        for i in range(self.retry_times):
            try:
                result = func(*args, **kwargs)
                return result
            except Exception as e:
                log.warning(f"请求失败 (尝试 {i+1}/{self.retry_times}): {e}")
                if i < self.retry_times - 1:
                    time.sleep(self.retry_delay)
        log.error(f"请求最终失败: {func.__name__}")
        return None


class TradeCalendarCollector(BaseCollector):
    """交易日历采集器"""

    def get_trade_calendar(self, start_year: int = None, end_year: int = None) -> pd.DataFrame:
        """
        获取交易日历

        Args:
            start_year: 起始年份
            end_year: 结束年份

        Returns:
            交易日历DataFrame
        """
        if start_year is None:
            start_year = datetime.now().year - 5
        if end_year is None:
            end_year = datetime.now().year

        all_dates = []
        for year in range(start_year, end_year + 1):
            try:
                df = self._retry_request(
                    ak.tool_trade_date_hist_sina,
                    exchange="sh"
                )
                if df is not None:
                    dates = df['trade_date'].tolist()
                    all_dates.extend([d for d in dates if str(d)[:4] == str(year)])
                    log.info(f"获取 {year} 年交易日历: {len(dates)} 个交易日")
            except Exception as e:
                log.error(f"获取 {year} 年交易日历失败: {e}")

        df_calendar = pd.DataFrame({
            'date': all_dates,
            'is_trading_day': True,
            'exchange': 'SH'
        })
        df_calendar['date'] = pd.to_datetime(df_calendar['date'])
        return df_calendar


class StockDataCollector(BaseCollector):
    """股票数据采集器"""

    def get_stock_list(self) -> pd.DataFrame:
        """
        获取A股股票列表

        Returns:
            股票信息DataFrame
        """
        result = []

        # 沪市A股
        try:
            df_sh = self._retry_request(ak.stock_info_sh_name_code, indicator="A股")
            if df_sh is not None:
                df_sh['exchange'] = 'SH'
                result.append(df_sh)
        except Exception as e:
            log.warning(f"获取沪市股票列表失败: {e}")

        # 深市A股
        try:
            df_sz = self._retry_request(ak.stock_info_sz_name_code, indicator="A股列表")
            if df_sz is not None:
                df_sz['exchange'] = 'SZ'
                result.append(df_sz)
        except Exception as e:
            log.warning(f"获取深市股票列表失败: {e}")

        if not result:
            return pd.DataFrame()

        df = pd.concat(result, ignore_index=True)
        df.columns = ['code', 'name', 'exchange']

        # 标准化字段
        df['list_date'] = pd.NaT
        df['industry'] = ''
        df['market_cap'] = np.nan
        df['is_enable'] = True

        return df

    def get_stock_daily(self, code: str, start_date: str = None,
                       end_date: str = None, adjust: str = "hfq") -> pd.DataFrame:
        """
        获取单只股票日线数据

        Args:
            code: 股票代码 (6位数字)
            start_date: 起始日期 YYYYMMDD
            end_date: 结束日期 YYYYMMDD
            adjust: 复权类型 hfq(后复权)/qfq(前复权)/空(不复权)

        Returns:
            日线行情DataFrame
        """
        if start_date is None:
            start_date = (datetime.now() - timedelta(days=365*3)).strftime("%Y%m%d")
        if end_date is None:
            end_date = datetime.now().strftime("%Y%m%d")

        try:
            df = self._retry_request(
                ak.stock_zh_a_hist,
                symbol=code,
                period="daily",
                start_date=start_date,
                end_date=end_date,
                adjust=adjust
            )

            if df is None or df.empty:
                return pd.DataFrame()

            # 标准化列名
            df = df.rename(columns={
                '日期': 'date',
                '开盘': 'open',
                '最高': 'high',
                '最低': 'low',
                '收盘': 'close',
                '成交量': 'volume',
                '成交额': 'amount',
                '涨跌幅': 'change_pct',
            })
            df['code'] = code
            df['date'] = pd.to_datetime(df['date'])

            # 保留需要的列
            cols = ['code', 'date', 'open', 'high', 'low', 'close', 'volume', 'amount', 'change_pct']
            df = df[[c for c in cols if c in df.columns]]

            return df

        except Exception as e:
            log.error(f"获取股票 {code} 日线数据失败: {e}")
            return pd.DataFrame()

    def get_stock_daily_batch(self, codes: List[str], start_date: str = None,
                             end_date: str = None, adjust: str = "hfq") -> pd.DataFrame:
        """
        批量获取股票日线数据

        Args:
            codes: 股票代码列表
            start_date: 起始日期
            end_date: 结束日期
            adjust: 复权类型

        Returns:
            合并的日线数据DataFrame
        """
        all_data = []
        total = len(codes)

        for i, code in enumerate(codes):
            if (i + 1) % 50 == 0:
                log.info(f"获取股票日线数据进度: {i+1}/{total}")

            df = self.get_stock_daily(code, start_date, end_date, adjust)
            if not df.empty:
                all_data.append(df)

            # 避免请求过快
            time.sleep(0.1)

        if not all_data:
            return pd.DataFrame()

        return pd.concat(all_data, ignore_index=True)

    def get_index_daily(self, code: str, start_date: str = None,
                       end_date: str = None) -> pd.DataFrame:
        """
        获取指数日线数据

        Args:
            code: 指数代码，如 'sh000300'
            start_date: 起始日期 YYYYMMDD
            end_date: 结束日期 YYYYMMDD

        Returns:
            指数日线DataFrame
        """
        if start_date is None:
            start_date = (datetime.now() - timedelta(days=365*3)).strftime("%Y%m%d")
        if end_date is None:
            end_date = datetime.now().strftime("%Y%m%d")

        try:
            # 处理指数代码格式
            if code.startswith('000') or code.startswith('399'):
                # 沪深指数
                df = self._retry_request(
                    ak.stock_zh_index_daily,
                    symbol=f"sh{code}" if code.startswith('000') else f"sz{code}"
                )
            else:
                df = self._retry_request(
                    ak.stock_zh_index_daily,
                    symbol=code
                )

            if df is None or df.empty:
                return pd.DataFrame()

            df = df.rename(columns={
                'date': 'date',
                'open': 'open',
                'high': 'high',
                'low': 'low',
                'close': 'close',
                'volume': 'volume',
            })
            df['code'] = code
            df['date'] = pd.to_datetime(df['date'])

            return df

        except Exception as e:
            log.error(f"获取指数 {code} 日线数据失败: {e}")
            return pd.DataFrame()


class ETFDataCollector(BaseCollector):
    """ETF数据采集器"""

    def get_etf_list(self) -> pd.DataFrame:
        """
        获取ETF基金列表

        Returns:
            ETF信息DataFrame
        """
        try:
            df = self._retry_request(ak.fund_etf_category_sina)
            if df is not None:
                df.columns = ['code', 'name', 'type', 'exchange']
                return df
        except Exception as e:
            log.error(f"获取ETF列表失败: {e}")
        return pd.DataFrame()

    def get_etf_daily(self, code: str, start_date: str = None,
                     end_date: str = None) -> pd.DataFrame:
        """
        获取ETF日线数据

        Args:
            code: ETF代码
            start_date: 起始日期
            end_date: 结束日期

        Returns:
            ETF日线DataFrame
        """
        if start_date is None:
            start_date = (datetime.now() - timedelta(days=365*3)).strftime("%Y%m%d")
        if end_date is None:
            end_date = datetime.now().strftime("%Y%m%d")

        try:
            df = self._retry_request(
                ak.fund_etf_hist_sina,
                symbol=code
            )

            if df is None or df.empty:
                return pd.DataFrame()

            df = df.rename(columns={
                'date': 'date',
                'open': 'open',
                'high': 'high',
                'low': 'low',
                'close': 'close',
                'volume': 'volume',
            })
            df['code'] = code
            df['date'] = pd.to_datetime(df['date'])

            return df

        except Exception as e:
            log.error(f"获取ETF {code} 日线数据失败: {e}")
            return pd.DataFrame()


class FinancialDataCollector(BaseCollector):
    """财务数据采集器"""

    def get_financial_indicator(self, code: str) -> pd.DataFrame:
        """
        获取财务指标数据

        Args:
            code: 股票代码

        Returns:
            财务指标DataFrame
        """
        try:
            df = self._retry_request(
                ak.stock_financial_analysis_indicator,
                symbol=code
            )

            if df is None or df.empty:
                return pd.DataFrame()

            df['code'] = code
            return df

        except Exception as e:
            log.error(f"获取股票 {code} 财务指标失败: {e}")
            return pd.DataFrame()

    def get_stock_pe_pb(self, code: str) -> pd.DataFrame:
        """
        获取PE/PB估值数据

        Args:
            code: 股票代码

        Returns:
            估值数据DataFrame
        """
        try:
            df = self._retry_request(
                ak.stock_a_pe_and_pb_indicator,
                symbol=code
            )

            if df is None or df.empty:
                return pd.DataFrame()

            return df

        except Exception as e:
            log.error(f"获取股票 {code} PE/PB失败: {e}")
            return pd.DataFrame()


class DataCollector:
    """
    统一数据采集接口
    """

    def __init__(self, config_path: str = None):
        self.stock = StockDataCollector(config_path)
        self.etf = ETFDataCollector(config_path)
        self.financial = FinancialDataCollector(config_path)
        self.calendar = TradeCalendarCollector(config_path)

    def initialize_data(self, start_date: str = None, end_date: str = None) -> Dict[str, pd.DataFrame]:
        """
        初始化基础数据

        Args:
            start_date: 起始日期
            end_date: 结束日期

        Returns:
            各类数据的字典
        """
        log.info("开始初始化基础数据...")

        data = {}

        # 1. 交易日历
        log.info("获取交易日历...")
        data['trade_calendar'] = self.calendar.get_trade_calendar()

        # 2. 股票列表
        log.info("获取股票列表...")
        data['stock_list'] = self.stock.get_stock_list()

        # 3. 主要指数
        log.info("获取指数数据...")
        index_codes = ['000300', '000905', '000852']  # 沪深300, 中证500, 中证1000
        index_data = []
        for code in index_codes:
            df = self.stock.get_index_daily(code, start_date, end_date)
            if not df.empty:
                index_data.append(df)
        if index_data:
            data['index_daily'] = pd.concat(index_data, ignore_index=True)

        log.info(f"数据初始化完成: {list(data.keys())}")
        return data
