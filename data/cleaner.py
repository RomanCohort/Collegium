"""
数据清洗模块
处理缺失值、异常值、复权等
"""
import pandas as pd
import numpy as np
from typing import Optional
from utils.logger import log
from utils.helpers import winsorize


class DataCleaner:
    """数据清洗器"""

    def __init__(self):
        pass

    def clean_prices(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        清洗价格数据

        Args:
            df: 原始价格数据

        Returns:
            清洗后的数据
        """
        if df.empty:
            return df

        df = df.copy()

        # 1. 处理缺失值
        df = self._handle_missing(df)

        # 2. 处理异常值
        df = self._handle_outliers(df)

        # 3. 处理停牌数据
        df = self._handle_suspension(df)

        # 4. 计算衍生指标
        df = self._calculate_derivatives(df)

        return df

    def _handle_missing(self, df: pd.DataFrame) -> pd.DataFrame:
        """处理缺失值"""
        # 删除关键列缺失的行
        key_cols = ["open", "close", "high", "low"]
        df = df.dropna(subset=key_cols)

        # 成交量缺失填充为 0
        if "volume" in df.columns:
            df["volume"] = df["volume"].fillna(0)

        # 成交额缺失填充为 0
        if "amount" in df.columns:
            df["amount"] = df["amount"].fillna(0)

        return df

    def _handle_outliers(self, df: pd.DataFrame) -> pd.DataFrame:
        """处理异常值"""
        # 价格异常：涨跌幅超过 20%（排除新股上市首日）
        if "pct_change" in df.columns:
            # 标记异常涨跌幅
            abnormal = df["pct_change"].abs() > 20
            if abnormal.any():
                log.warning(f"发现 {abnormal.sum()} 条异常涨跌幅数据")
                # 对于异常数据，使用前一日收盘价填充
                # 这里不删除，只是标记
                df["is_abnormal"] = abnormal

        # 成交量异常：超过均值 10 倍
        if "volume" in df.columns:
            vol_mean = df["volume"].mean()
            vol_outlier = df["volume"] > vol_mean * 10
            if vol_outlier.any():
                df.loc[vol_outlier, "volume"] = vol_mean * 10

        return df

    def _handle_suspension(self, df: pd.DataFrame) -> pd.DataFrame:
        """处理停牌数据"""
        # 成交量为 0 可能是停牌
        if "volume" in df.columns:
            zero_vol = df["volume"] == 0
            if zero_vol.any():
                # 标记停牌
                df["is_suspended"] = zero_vol
                log.info(f"发现 {zero_vol.sum()} 个停牌日")

        return df

    def _calculate_derivatives(self, df: pd.DataFrame) -> pd.DataFrame:
        """计算衍生指标"""
        # 收盘价相对位置（在当日最高最低之间的位置）
        if all(col in df.columns for col in ["close", "high", "low"]):
            df["close_position"] = (df["close"] - df["low"]) / (df["high"] - df["low"])

        # 日内振幅
        if all(col in df.columns for col in ["high", "low", "close"]):
            df["intraday_range"] = (df["high"] - df["low"]) / df["close"].shift(1)

        # 成交量相对变化
        if "volume" in df.columns:
            df["volume_ratio"] = df["volume"] / df["volume"].rolling(5).mean()

        return df

    def adjust_prices(
        self,
        df: pd.DataFrame,
        adjust_type: str = "qfq"
    ) -> pd.DataFrame:
        """
        价格复权处理

        Args:
            df: 原始数据
            adjust_type: 复权类型 qfq/hfq/none

        Returns:
            复权后的数据
        """
        # akshare 数据已支持复权参数，这里做补充处理
        # 如果数据已经复权，跳过
        if adjust_type == "none" or df.empty:
            return df

        return df

    def fill_missing_dates(
        self,
        df: pd.DataFrame,
        start_date: str,
        end_date: str,
        method: str = "ffill"
    ) -> pd.DataFrame:
        """
        填充缺失日期

        Args:
            df: 原始数据
            start_date: 开始日期
            end_date: 结束日期
            method: 填充方法 ffill/bfill/interpolate

        Returns:
            填充后的数据
        """
        if df.empty:
            return df

        df = df.copy()
        df = df.set_index("date")

        # 生成完整日期序列（工作日）
        full_dates = pd.date_range(start_date, end_date, freq="B")
        df = df.reindex(full_dates)

        # 填充方法
        if method == "ffill":
            df = df.ffill()
        elif method == "bfill":
            df = df.bfill()
        elif method == "interpolate":
            df = df.interpolate()

        df = df.reset_index()
        df = df.rename(columns={"index": "date"})

        return df

    def align_multiple_stocks(
        self,
        df_list: list,
        method: str = "inner"
    ) -> pd.DataFrame:
        """
        对齐多只股票的日期

        Args:
            df_list: 多个股票 DataFrame 列表
            method: 对齐方式 inner/outer

        Returns:
            对齐后的合并 DataFrame
        """
        if not df_list:
            return pd.DataFrame()

        # 获取所有日期的交集/并集
        all_dates = set()
        for df in df_list:
            if not df.empty:
                dates = set(df["date"].tolist())
                if method == "inner":
                    if not all_dates:
                        all_dates = dates
                    else:
                        all_dates = all_dates.intersection(dates)
                else:
                    all_dates = all_dates.union(dates)

        if not all_dates:
            return pd.DataFrame()

        # 对齐每只股票
        aligned_dfs = []
        for df in df_list:
            if not df.empty:
                aligned = df[df["date"].isin(all_dates)]
                aligned_dfs.append(aligned)

        return pd.concat(aligned_dfs, ignore_index=True)

    def validate_data(self, df: pd.DataFrame) -> dict:
        """
        数据质量验证

        Args:
            df: 待验证数据

        Returns:
            验证结果字典
        """
        result = {
            "is_valid": True,
            "issues": [],
            "stats": {}
        }

        if df.empty:
            result["is_valid"] = False
            result["issues"].append("数据为空")
            return result

        # 检查缺失值
        missing_pct = df.isnull().mean()
        for col, pct in missing_pct.items():
            if pct > 0.1:
                result["issues"].append(f"列 {col} 缺失率 {pct:.1%}")

        # 检查数据范围
        if "close" in df.columns:
            if (df["close"] <= 0).any():
                result["issues"].append("存在负数或零价格")

        # 检查日期连续性
        if "date" in df.columns:
            dates = df["date"].sort_values()
            gaps = dates.diff().dropna()
            large_gaps = gaps[gaps > pd.Timedelta(days=7)]
            if len(large_gaps) > 0:
                result["issues"].append(f"存在 {len(large_gaps)} 个超过 7 天的日期缺口")

        # 统计信息
        result["stats"] = {
            "row_count": len(df),
            "date_range": (df["date"].min(), df["date"].max()) if "date" in df.columns else None,
            "missing_rate": df.isnull().mean().mean(),
        }

        result["is_valid"] = len(result["issues"]) == 0

        return result


# 创建默认实例
cleaner = DataCleaner()