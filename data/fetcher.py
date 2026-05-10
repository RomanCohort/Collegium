"""
数据获取模块
使用 akshare 获取 A 股数据
"""
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import List, Optional, Union
import akshare as ak
from utils.logger import log
from utils.decorators import retry, timer, cache_result


class DataFetcher:
    """A股数据获取器"""

    def __init__(self, cache_enabled: bool = True):
        """
        初始化数据获取器

        Args:
            cache_enabled: 是否启用缓存
        """
        self.cache_enabled = cache_enabled
        self._stock_list_cache = None

    @retry(max_attempts=3, delay=2.0)
    @timer
    def get_stock_list(self, market: str = "A股") -> pd.DataFrame:
        """
        获取股票列表

        Args:
            market: 市场类型

        Returns:
            股票列表 DataFrame
        """
        log.info(f"获取 {market} 股票列表")

        try:
            # 获取 A 股实时行情数据（包含股票代码和名称）
            stock_info = ak.stock_zh_a_spot_em()
            stock_info = stock_info.rename(columns={
                "代码": "symbol",
                "名称": "name",
            })
            stock_info["symbol"] = stock_info["symbol"].astype(str)

            # 过滤 ST 和退市股票
            stock_info = stock_info[~stock_info["name"].str.contains("ST|退市|N")]

            log.info(f"获取到 {len(stock_info)} 只股票")
            return stock_info[["symbol", "name"]]
        except Exception as e:
            log.error(f"获取股票列表失败: {e}")
            raise

    @retry(max_attempts=3, delay=2.0)
    @timer
    def get_daily_prices(
        self,
        symbol: str,
        start_date: str,
        end_date: str,
        adjust: str = "qfq"
    ) -> pd.DataFrame:
        """
        获取日线数据

        Args:
            symbol: 股票代码（如 000001）
            start_date: 开始日期 YYYY-MM-DD
            end_date: 结束日期 YYYY-MM-DD
            adjust: 复权类型 qfq(前复权)/hfq(后复权)/None(不复权)

        Returns:
            日线数据 DataFrame
        """
        log.info(f"获取 {symbol} 日线数据: {start_date} ~ {end_date}")

        try:
            # 使用东方财富数据源
            df = ak.stock_zh_a_hist(
                symbol=symbol,
                period="daily",
                start_date=start_date.replace("-", ""),
                end_date=end_date.replace("-", ""),
                adjust=adjust
            )

            if df.empty:
                log.warning(f"股票 {symbol} 无数据")
                return pd.DataFrame()

            # 标准化列名
            df = df.rename(columns={
                "日期": "date",
                "开盘": "open",
                "收盘": "close",
                "最高": "high",
                "最低": "low",
                "成交量": "volume",
                "成交额": "amount",
                "振幅": "amplitude",
                "涨跌幅": "pct_change",
                "涨跌额": "change",
                "换手率": "turnover",
            })

            df["date"] = pd.to_datetime(df["date"])
            df["symbol"] = symbol
            df = df.sort_values("date").reset_index(drop=True)

            return df
        except Exception as e:
            log.error(f"获取 {symbol} 日线数据失败: {e}")
            return pd.DataFrame()

    @timer
    def get_batch_daily_prices(
        self,
        symbols: List[str],
        start_date: str,
        end_date: str,
        adjust: str = "qfq"
    ) -> pd.DataFrame:
        """
        批量获取多只股票日线数据

        Args:
            symbols: 股票代码列表
            start_date: 开始日期
            end_date: 结束日期
            adjust: 复权类型

        Returns:
            合并的日线数据 DataFrame
        """
        log.info(f"批量获取 {len(symbols)} 只股票日线数据")

        all_data = []
        failed_symbols = []

        for i, symbol in enumerate(symbols):
            try:
                df = self.get_daily_prices(symbol, start_date, end_date, adjust)
                if not df.empty:
                    all_data.append(df)
            except Exception:
                failed_symbols.append(symbol)

            # 进度显示
            if (i + 1) % 50 == 0:
                log.info(f"已获取 {i + 1}/{len(symbols)} 只股票数据")

        if failed_symbols:
            log.warning(f"以下股票获取失败: {failed_symbols[:10]}...")

        if all_data:
            result = pd.concat(all_data, ignore_index=True)
            log.info(f"成功获取 {len(all_data)} 只股票数据，共 {len(result)} 条记录")
            return result
        else:
            return pd.DataFrame()

    @retry(max_attempts=3, delay=2.0)
    def get_index_data(
        self,
        index_code: str = "000300",
        start_date: str = None,
        end_date: str = None
    ) -> pd.DataFrame:
        """
        获取指数数据

        Args:
            index_code: 指数代码
            start_date: 开始日期
            end_date: 结束日期

        Returns:
            指数数据 DataFrame
        """
        log.info(f"获取指数 {index_code} 数据")

        try:
            # 沪深300
            if index_code == "000300":
                df = ak.index_stock_hist_weight_csindex(symbol="000300")
                # 获取指数行情
                df = ak.stock_zh_index_daily(symbol="sh000300")
            else:
                df = ak.stock_zh_index_daily(symbol=f"sh{index_code}")

            if df.empty:
                return pd.DataFrame()

            df = df.rename(columns={
                "date": "date",
                "open": "open",
                "close": "close",
                "high": "high",
                "low": "low",
                "volume": "volume",
            })

            df["date"] = pd.to_datetime(df["date"])
            df = df.sort_values("date").reset_index(drop=True)

            # 过滤日期范围
            if start_date:
                df = df[df["date"] >= pd.to_datetime(start_date)]
            if end_date:
                df = df[df["date"] <= pd.to_datetime(end_date)]

            return df
        except Exception as e:
            log.error(f"获取指数数据失败: {e}")
            return pd.DataFrame()

    @retry(max_attempts=3, delay=2.0)
    def get_financial_data(self, symbol: str) -> pd.DataFrame:
        """
        获取财务数据

        Args:
            symbol: 股票代码

        Returns:
            财务数据 DataFrame
        """
        log.info(f"获取 {symbol} 财务数据")

        try:
            # 主要财务指标
            df = ak.stock_financial_analysis_indicator(symbol=symbol)

            if df.empty:
                return pd.DataFrame()

            return df
        except Exception as e:
            log.warning(f"获取 {symbol} 财务数据失败: {e}")
            return pd.DataFrame()

    @retry(max_attempts=3, delay=2.0)
    def get_industry_data(self) -> pd.DataFrame:
        """
        获取行业分类数据

        Returns:
            行业分类 DataFrame
        """
        log.info("获取行业分类数据")

        try:
            # 申万一级行业分类
            df = ak.stock_board_industry_name_em()
            return df
        except Exception as e:
            log.error(f"获取行业数据失败: {e}")
            return pd.DataFrame()

    @retry(max_attempts=3, delay=2.0)
    def get_stock_industry(self, symbol: str) -> str:
        """
        获取单只股票所属行业

        Args:
            symbol: 股票代码

        Returns:
            行业名称
        """
        try:
            df = ak.stock_individual_info_em(symbol=symbol)
            if df.empty:
                return "未知"

            # 查找行业信息
            industry_row = df[df["item"] == "行业"]
            if not industry_row.empty:
                return industry_row["value"].values[0]
            return "未知"
        except Exception:
            return "未知"

    def get_trading_calendar(self, year: int = None) -> List[str]:
        """
        获取交易日历

        Args:
            year: 年份，默认当前年

        Returns:
            交易日列表
        """
        if year is None:
            year = datetime.now().year

        log.info(f"获取 {year} 年交易日历")

        try:
            # 使用 akshare 交易日历
            df = ak.tool_trade_date_hist_sina()
            dates = df["trade_date"].astype(str).tolist()
            # 过滤指定年份
            dates = [d for d in dates if d.startswith(str(year))]
            return dates
        except Exception as e:
            log.error(f"获取交易日历失败: {e}")
            # 返回工作日作为备选
            start = datetime(year, 1, 1)
            end = datetime(year, 12, 31)
            return [d.strftime("%Y-%m-%d") for d in pd.date_range(start, end, freq="B")]


# 创建默认实例
fetcher = DataFetcher()