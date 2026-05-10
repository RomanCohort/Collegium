"""
数据存储模块
支持本地缓存和数据库存储
"""
import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime
from typing import Optional, List
import sqlite3
from contextlib import contextmanager
from config.settings import DATA_DIR, DATABASE_CONFIG
from utils.logger import log
from utils.decorators import timer


class DataStorage:
    """数据存储管理器"""

    def __init__(self, storage_type: str = "sqlite"):
        """
        初始化存储器

        Args:
            storage_type: 存储类型 (sqlite / csv / parquet)
        """
        self.storage_type = storage_type
        self.data_dir = DATA_DIR
        self.data_dir.mkdir(parents=True, exist_ok=True)

        if storage_type == "sqlite":
            self.db_path = DATABASE_CONFIG["path"]
            self._init_database()

    def _init_database(self):
        """初始化数据库表结构"""
        with self._get_connection() as conn:
            # 日线数据表
            conn.execute("""
                CREATE TABLE IF NOT EXISTS daily_prices (
                    symbol TEXT,
                    date TEXT,
                    open REAL,
                    close REAL,
                    high REAL,
                    low REAL,
                    volume REAL,
                    amount REAL,
                    pct_change REAL,
                    turnover REAL,
                    PRIMARY KEY (symbol, date)
                )
            """)

            # 股票信息表
            conn.execute("""
                CREATE TABLE IF NOT EXISTS stock_info (
                    symbol TEXT PRIMARY KEY,
                    name TEXT,
                    industry TEXT,
                    list_date TEXT,
                    update_time TEXT
                )
            """)

            # 财务数据表
            conn.execute("""
                CREATE TABLE IF NOT EXISTS financial_data (
                    symbol TEXT,
                    report_date TEXT,
                    roe REAL,
                    pe REAL,
                    pb REAL,
                    total_revenue REAL,
                    net_profit REAL,
                    PRIMARY KEY (symbol, report_date)
                )
            """)

            # 因子数据表
            conn.execute("""
                CREATE TABLE IF NOT EXISTS factor_data (
                    symbol TEXT,
                    date TEXT,
                    factor_name TEXT,
                    factor_value REAL,
                    PRIMARY KEY (symbol, date, factor_name)
                )
            """)

            conn.commit()
            log.info("数据库初始化完成")

    @contextmanager
    def _get_connection(self):
        """获取数据库连接"""
        conn = sqlite3.connect(self.db_path)
        try:
            yield conn
        finally:
            conn.close()

    @timer
    def save_daily_prices(self, df: pd.DataFrame, overwrite: bool = False):
        """
        保存日线数据

        Args:
            df: 日线数据 DataFrame
            overwrite: 是否覆盖已有数据
        """
        if df.empty:
            return

        if self.storage_type == "sqlite":
            with self._get_connection() as conn:
                if overwrite:
                    # 删除已有数据
                    symbols = df["symbol"].unique().tolist()
                    conn.execute(
                        f"DELETE FROM daily_prices WHERE symbol IN ({','.join(['?']*len(symbols))})",
                        symbols
                    )

                # 插入新数据
                df_to_save = df.copy()
                df_to_save["date"] = df_to_save["date"].astype(str)

                df_to_save[["symbol", "date", "open", "close", "high", "low",
                           "volume", "amount", "pct_change", "turnover"]].to_sql(
                    "daily_prices",
                    conn,
                    if_exists="append",
                    index=False
                )
                conn.commit()
                log.info(f"保存 {len(df)} 条日线数据到数据库")

        elif self.storage_type == "csv":
            # 按股票代码分文件存储
            for symbol in df["symbol"].unique():
                symbol_df = df[df["symbol"] == symbol]
                file_path = self.data_dir / f"daily_{symbol}.csv"
                if file_path.exists() and not overwrite:
                    existing = pd.read_csv(file_path)
                    symbol_df = pd.concat([existing, symbol_df]).drop_duplicates(
                        subset=["date"], keep="last"
                    )
                symbol_df.to_csv(file_path, index=False)
            log.info(f"保存 {len(df)} 条日线数据到 CSV")

        elif self.storage_type == "parquet":
            file_path = self.data_dir / "daily_prices.parquet"
            if file_path.exists() and not overwrite:
                existing = pd.read_parquet(file_path)
                df = pd.concat([existing, df]).drop_duplicates(
                    subset=["symbol", "date"], keep="last"
                )
            df.to_parquet(file_path, index=False)
            log.info(f"保存 {len(df)} 条日线数据到 Parquet")

    @timer
    def load_daily_prices(
        self,
        symbol: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> pd.DataFrame:
        """
        加载日线数据

        Args:
            symbol: 股票代码（可选，不指定则加载全部）
            start_date: 开始日期
            end_date: 结束日期

        Returns:
            日线数据 DataFrame
        """
        if self.storage_type == "sqlite":
            with self._get_connection() as conn:
                query = "SELECT * FROM daily_prices"
                conditions = []
                params = []

                if symbol:
                    conditions.append("symbol = ?")
                    params.append(symbol)
                if start_date:
                    conditions.append("date >= ?")
                    params.append(start_date)
                if end_date:
                    conditions.append("date <= ?")
                    params.append(end_date)

                if conditions:
                    query += " WHERE " + " AND ".join(conditions)

                df = pd.read_sql_query(query, conn, params=params)
                if not df.empty:
                    df["date"] = pd.to_datetime(df["date"])
                return df

        elif self.storage_type == "csv":
            if symbol:
                file_path = self.data_dir / f"daily_{symbol}.csv"
                if file_path.exists():
                    df = pd.read_csv(file_path)
                    df["date"] = pd.to_datetime(df["date"])
                    if start_date:
                        df = df[df["date"] >= pd.to_datetime(start_date)]
                    if end_date:
                        df = df[df["date"] <= pd.to_datetime(end_date)]
                    return df
                return pd.DataFrame()
            else:
                # 加载所有 CSV 文件
                all_files = list(self.data_dir.glob("daily_*.csv"))
                if not all_files:
                    return pd.DataFrame()
                dfs = [pd.read_csv(f) for f in all_files]
                df = pd.concat(dfs, ignore_index=True)
                df["date"] = pd.to_datetime(df["date"])
                return df

        elif self.storage_type == "parquet":
            file_path = self.data_dir / "daily_prices.parquet"
            if file_path.exists():
                df = pd.read_parquet(file_path)
                if symbol:
                    df = df[df["symbol"] == symbol]
                if start_date:
                    df = df[df["date"] >= pd.to_datetime(start_date)]
                if end_date:
                    df = df[df["date"] <= pd.to_datetime(end_date)]
                return df
            return pd.DataFrame()

    def save_stock_info(self, df: pd.DataFrame):
        """保存股票基本信息"""
        if df.empty:
            return

        with self._get_connection() as conn:
            df.to_sql("stock_info", conn, if_exists="replace", index=False)
            conn.commit()
            log.info(f"保存 {len(df)} 条股票信息")

    def load_stock_info(self) -> pd.DataFrame:
        """加载股票基本信息"""
        with self._get_connection() as conn:
            try:
                return pd.read_sql_query("SELECT * FROM stock_info", conn)
            except:
                return pd.DataFrame()

    def save_factor_data(self, df: pd.DataFrame, factor_name: str):
        """
        保存因子数据

        Args:
            df: 因子数据（包含 symbol, date, factor_value）
            factor_name: 因子名称
        """
        if df.empty:
            return

        df["factor_name"] = factor_name

        with self._get_connection() as conn:
            # 删除该因子的旧数据
            conn.execute(
                "DELETE FROM factor_data WHERE factor_name = ?",
                (factor_name,)
            )
            df.to_sql("factor_data", conn, if_exists="append", index=False)
            conn.commit()
            log.info(f"保存因子 {factor_name} 数据 {len(df)} 条")

    def load_factor_data(
        self,
        factor_name: str,
        date: Optional[str] = None
    ) -> pd.DataFrame:
        """
        加载因子数据

        Args:
            factor_name: 因子名称
            date: 日期（可选）

        Returns:
            因子数据 DataFrame
        """
        with self._get_connection() as conn:
            query = "SELECT symbol, date, factor_value FROM factor_data WHERE factor_name = ?"
            params = [factor_name]

            if date:
                query += " AND date = ?"
                params.append(date)

            df = pd.read_sql_query(query, conn, params=params)
            return df

    def get_data_status(self) -> dict:
        """
        获取数据状态统计

        Returns:
            数据状态字典
        """
        status = {}

        with self._get_connection() as conn:
            # 股票数量
            result = conn.execute("SELECT COUNT(DISTINCT symbol) FROM daily_prices").fetchone()
            status["stock_count"] = result[0] if result else 0

            # 数据条数
            result = conn.execute("SELECT COUNT(*) FROM daily_prices").fetchone()
            status["record_count"] = result[0] if result else 0

            # 数据日期范围
            result = conn.execute("SELECT MIN(date), MAX(date) FROM daily_prices").fetchone()
            status["date_range"] = (result[0], result[1]) if result else (None, None)

            # 最后更新时间
            result = conn.execute("SELECT MAX(update_time) FROM stock_info").fetchone()
            status["last_update"] = result[0] if result else None

        return status


# 创建默认实例
storage = DataStorage()