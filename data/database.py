"""
PostgreSQL数据库连接与表结构管理
"""

import yaml
from pathlib import Path
from typing import Optional, Dict, Any, List
from contextlib import contextmanager

import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import QueuePool

from ..utils import log


class Database:
    """
    PostgreSQL数据库管理类
    """

    def __init__(self, config_path: str = None):
        """
        初始化数据库连接

        Args:
            config_path: 配置文件路径，默认从项目config目录读取
        """
        if config_path is None:
            config_path = Path(__file__).parent.parent / "config" / "config.yaml"

        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)

        db_config = config.get('database', {})
        self.host = db_config.get('host', 'localhost')
        self.port = db_config.get('port', 5432)
        self.database = db_config.get('database', 'quant_db')
        self.user = db_config.get('user', 'postgres')
        self.password = db_config.get('password', 'postgres')
        self.pool_size = db_config.get('pool_size', 5)

        self._engine = None
        self._session_factory = None

    @property
    def engine(self):
        """获取SQLAlchemy引擎"""
        if self._engine is None:
            connection_str = f"postgresql://{self.user}:{self.password}@{self.host}:{self.port}/{self.database}"
            self._engine = create_engine(
                connection_str,
                poolclass=QueuePool,
                pool_size=self.pool_size,
                max_overflow=10,
                echo=False,
            )
            log.info(f"数据库连接已创建: {self.host}:{self.port}/{self.database}")
        return self._engine

    @property
    def session_factory(self):
        """获取Session工厂"""
        if self._session_factory is None:
            self._session_factory = sessionmaker(bind=self.engine)
        return self._session_factory

    @contextmanager
    def session(self) -> Session:
        """
        数据库会话上下文管理器

        Usage:
            with db.session() as session:
                result = session.execute(text("SELECT * FROM stocks"))
        """
        session = self.session_factory()
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            log.error(f"数据库操作失败: {e}")
            raise
        finally:
            session.close()

    def execute(self, sql: str, params: Dict = None) -> List:
        """
        执行SQL查询

        Args:
            sql: SQL语句
            params: 参数字典

        Returns:
            查询结果列表
        """
        with self.session() as session:
            result = session.execute(text(sql), params or {})
            return result.fetchall()

    def read_sql(self, sql: str, params: Dict = None) -> pd.DataFrame:
        """
        读取SQL结果为DataFrame

        Args:
            sql: SQL语句
            params: 参数字典

        Returns:
            结果DataFrame
        """
        return pd.read_sql(text(sql), self.engine, params=params)

    def to_sql(self, df: pd.DataFrame, table: str, if_exists: str = 'append',
               index: bool = False) -> None:
        """
        将DataFrame写入数据库

        Args:
            df: 数据DataFrame
            table: 表名
            if_exists: 'append'/'replace'/'fail'
            index: 是否写入索引
        """
        df.to_sql(table, self.engine, if_exists=if_exists, index=index)
        log.debug(f"已写入 {len(df)} 条数据到表 {table}")

    def table_exists(self, table_name: str) -> bool:
        """
        检查表是否存在

        Args:
            table_name: 表名

        Returns:
            是否存在
        """
        sql = """
            SELECT EXISTS (
                SELECT FROM information_schema.tables
                WHERE table_name = :table_name
            )
        """
        result = self.execute(sql, {'table_name': table_name})
        return result[0][0] if result else False

    def get_columns(self, table_name: str) -> List[str]:
        """
        获取表字段列表

        Args:
            table_name: 表名

        Returns:
            字段名列表
        """
        sql = """
            SELECT column_name FROM information_schema.columns
            WHERE table_name = :table_name
            ORDER BY ordinal_position
        """
        result = self.execute(sql, {'table_name': table_name})
        return [r[0] for r in result]

    def init_tables(self) -> None:
        """
        初始化数据库表结构
        """
        log.info("开始初始化数据库表...")

        table_schemas = {
            # 交易日历表
            "trade_calendar": """
                CREATE TABLE IF NOT EXISTS trade_calendar (
                    date DATE PRIMARY KEY,
                    is_trading_day BOOLEAN DEFAULT TRUE,
                    exchange VARCHAR(10)
                )
            """,

            # 股票列表
            "stock_info": """
                CREATE TABLE IF NOT EXISTS stock_info (
                    code VARCHAR(10) PRIMARY KEY,
                    name VARCHAR(100),
                    exchange VARCHAR(10),
                    industry VARCHAR(100),
                    list_date DATE,
                    market_cap FLOAT,
                    is_enable BOOLEAN DEFAULT TRUE
                )
            """,

            # 股票日线行情
            "stocks_daily": """
                CREATE TABLE IF NOT EXISTS stocks_daily (
                    id SERIAL PRIMARY KEY,
                    code VARCHAR(10),
                    date DATE,
                    open FLOAT,
                    high FLOAT,
                    low FLOAT,
                    close FLOAT,
                    volume BIGINT,
                    amount FLOAT,
                    change_pct FLOAT,
                    UNIQUE(code, date)
                )
            """,

            # ETF日线行情
            "etf_daily": """
                CREATE TABLE IF NOT EXISTS etf_daily (
                    id SERIAL PRIMARY KEY,
                    code VARCHAR(10),
                    date DATE,
                    open FLOAT,
                    high FLOAT,
                    low FLOAT,
                    close FLOAT,
                    volume BIGINT,
                    amount FLOAT,
                    change_pct FLOAT,
                    UNIQUE(code, date)
                )
            """,

            # 指数日线行情
            "index_daily": """
                CREATE TABLE IF NOT EXISTS index_daily (
                    id SERIAL PRIMARY KEY,
                    code VARCHAR(10),
                    date DATE,
                    open FLOAT,
                    high FLOAT,
                    low FLOAT,
                    close FLOAT,
                    volume BIGINT,
                    amount FLOAT,
                    change_pct FLOAT,
                    UNIQUE(code, date)
                )
            """,

            # 财务数据
            "financial_data": """
                CREATE TABLE IF NOT EXISTS financial_data (
                    id SERIAL PRIMARY KEY,
                    code VARCHAR(10),
                    date DATE,
                    report_type VARCHAR(20),
                    total_asset FLOAT,
                    total_liability FLOAT,
                    equity FLOAT,
                    revenue FLOAT,
                    profit FLOAT,
                    pe_ttm FLOAT,
                    pb FLOAT,
                    ps_ttm FLOAT,
                    roe FLOAT,
                    roa FLOAT,
                    debt_ratio FLOAT,
                    gross_margin FLOAT,
                    UNIQUE(code, date, report_type)
                )
            """,

            # 因子数据
            "factor_data": """
                CREATE TABLE IF NOT EXISTS factor_data (
                    id SERIAL PRIMARY KEY,
                    code VARCHAR(10),
                    date DATE,
                    factor_name VARCHAR(50),
                    factor_value FLOAT,
                    UNIQUE(code, date, factor_name)
                )
            """,

            # 回测记录
            "backtest_results": """
                CREATE TABLE IF NOT EXISTS backtest_results (
                    id SERIAL PRIMARY KEY,
                    strategy_name VARCHAR(100),
                    start_date DATE,
                    end_date DATE,
                    initial_cash FLOAT,
                    final_value FLOAT,
                    total_return FLOAT,
                    annual_return FLOAT,
                    sharpe_ratio FLOAT,
                    max_drawdown FLOAT,
                    params TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """,
        }

        with self.session() as session:
            for table_name, schema in table_schemas.items():
                session.execute(text(schema))
                log.debug(f"表 {table_name} 已创建/检查")

        log.info("数据库表初始化完成")

    def create_indexes(self) -> None:
        """创建常用索引以提升查询性能"""
        indexes = [
            "CREATE INDEX IF NOT EXISTS idx_stocks_daily_code_date ON stocks_daily(code, date)",
            "CREATE INDEX IF NOT EXISTS idx_stocks_daily_date ON stocks_daily(date)",
            "CREATE INDEX IF NOT EXISTS idx_etf_daily_code_date ON etf_daily(code, date)",
            "CREATE INDEX IF NOT EXISTS idx_index_daily_code_date ON index_daily(code, date)",
            "CREATE INDEX IF NOT EXISTS idx_financial_code_date ON financial_data(code, date)",
            "CREATE INDEX IF NOT EXISTS idx_factor_code_date ON factor_data(code, date)",
            "CREATE INDEX IF NOT EXISTS idx_factor_date_name ON factor_data(date, factor_name)",
        ]

        with self.session() as session:
            for idx_sql in indexes:
                session.execute(text(idx_sql))

        log.info("数据库索引创建完成")

    def close(self) -> None:
        """关闭数据库连接"""
        if self._engine:
            self._engine.dispose()
            self._engine = None
            log.info("数据库连接已关闭")


# 全局单例
_db_instance: Optional[Database] = None


def get_database(config_path: str = None) -> Database:
    """
    获取数据库单例实例

    Args:
        config_path: 配置文件路径

    Returns:
        Database实例
    """
    global _db_instance
    if _db_instance is None:
        _db_instance = Database(config_path)
    return _db_instance
