"""
实时监控模块
使用 Streamlit 构建监控面板
"""
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, Optional
import json
from pathlib import Path
from utils.logger import log


class MonitoringDashboard:
    """监控面板数据提供者"""

    def __init__(self, data_dir: str = None):
        self.data_dir = Path(data_dir) if data_dir else Path("data/monitoring")
        self.data_dir.mkdir(parents=True, exist_ok=True)

        # 状态文件
        self.status_file = self.data_dir / "status.json"
        self.alerts_file = self.data_dir / "alerts.json"

    def update_status(self, status: Dict):
        """更新状态"""
        status["update_time"] = datetime.now().isoformat()
        with open(self.status_file, "w") as f:
            json.dump(status, f, indent=2, ensure_ascii=False)

    def get_status(self) -> Dict:
        """获取状态"""
        if self.status_file.exists():
            with open(self.status_file, "r") as f:
                return json.load(f)
        return {}

    def add_alert(self, alert: Dict):
        """添加告警"""
        alert["time"] = datetime.now().isoformat()
        alerts = self.get_alerts()
        alerts.append(alert)
        # 保留最近 100 条
        alerts = alerts[-100:]
        with open(self.alerts_file, "w") as f:
            json.dump(alerts, f, indent=2, ensure_ascii=False)

    def get_alerts(self, limit: int = 50) -> list:
        """获取告警"""
        if self.alerts_file.exists():
            with open(self.alerts_file, "r") as f:
                alerts = json.load(f)
                return alerts[-limit:]
        return []

    def clear_alerts(self):
        """清除告警"""
        with open(self.alerts_file, "w") as f:
            json.dump([], f)


class AlertManager:
    """告警管理器"""

    def __init__(self, config: Dict = None):
        self.config = config or {}
        self.thresholds = {
            "max_drawdown": 0.15,
            "daily_loss": 0.03,
            "position_concentration": 0.3,
            "signal_anomaly": 0.5,
        }
        self.thresholds.update(self.config.get("thresholds", {}))
        self.alerts = []

    def check_drawdown(self, current_drawdown: float) -> Optional[Dict]:
        """检查回撤告警"""
        if current_drawdown < -self.thresholds["max_drawdown"]:
            alert = {
                "type": "DRAWDOWN",
                "level": "CRITICAL",
                "message": f"回撤 {current_drawdown:.1%} 超过阈值 {self.thresholds['max_drawdown']:.1%}",
                "value": current_drawdown,
                "threshold": self.thresholds["max_drawdown"],
            }
            self.alerts.append(alert)
            return alert
        return None

    def check_daily_loss(self, daily_pnl_pct: float) -> Optional[Dict]:
        """检查日亏损告警"""
        if daily_pnl_pct < -self.thresholds["daily_loss"]:
            alert = {
                "type": "DAILY_LOSS",
                "level": "WARNING",
                "message": f"日亏损 {daily_pnl_pct:.1%} 超过阈值 {self.thresholds['daily_loss']:.1%}",
                "value": daily_pnl_pct,
                "threshold": self.thresholds["daily_loss"],
            }
            self.alerts.append(alert)
            return alert
        return None

    def check_concentration(self, positions: Dict, total_value: float) -> Optional[Dict]:
        """检查集中度告警"""
        if not positions or total_value <= 0:
            return None

        max_position_pct = max(
            pos.get("value", 0) / total_value
            for pos in positions.values()
        )

        if max_position_pct > self.thresholds["position_concentration"]:
            alert = {
                "type": "CONCENTRATION",
                "level": "WARNING",
                "message": f"最大持仓占比 {max_position_pct:.1%} 超过阈值 {self.thresholds['position_concentration']:.1%}",
                "value": max_position_pct,
                "threshold": self.thresholds["position_concentration"],
            }
            self.alerts.append(alert)
            return alert
        return None

    def get_recent_alerts(self, hours: int = 24) -> list:
        """获取最近告警"""
        cutoff = datetime.now() - timedelta(hours=hours)
        return [
            a for a in self.alerts
            if datetime.fromisoformat(a.get("time", "2000-01-01")) > cutoff
        ]


# Streamlit 面板代码（独立运行）
DASHBOARD_CODE = '''
"""
监控面板 - Streamlit 应用
运行: streamlit run dashboard.py
"""
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import json
from pathlib import Path
from datetime import datetime, timedelta

# 页面配置
st.set_page_config(
    page_title="QuantSystem 监控面板",
    page_icon="📊",
    layout="wide",
)

# 数据目录
DATA_DIR = Path("data/monitoring")

@st.cache_data(ttl=5)
def load_status():
    status_file = DATA_DIR / "status.json"
    if status_file.exists():
        with open(status_file, "r") as f:
            return json.load(f)
    return {}

@st.cache_data(ttl=5)
def load_alerts():
    alerts_file = DATA_DIR / "alerts.json"
    if alerts_file.exists():
        with open(alerts_file, "r") as f:
            return json.load(f)
    return []

def main():
    st.title("📊 QuantSystem 监控面板")

    # 加载数据
    status = load_status()
    alerts = load_alerts()

    # 顶部指标卡片
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        total_value = status.get("total_value", 0)
        st.metric("总资产", f"¥{total_value:,.0f}")

    with col2:
        daily_pnl = status.get("daily_pnl", 0)
        daily_pnl_pct = status.get("daily_pnl_pct", 0)
        st.metric("今日盈亏", f"¥{daily_pnl:,.0f}", f"{daily_pnl_pct:.2%}")

    with col3:
        positions = status.get("positions", 0)
        st.metric("持仓数量", positions)

    with col4:
        drawdown = status.get("drawdown", 0)
        st.metric("当前回撤", f"{drawdown:.2%}")

    st.divider()

    # 告警区域
    st.subheader("⚠️ 告警")
    if alerts:
        alert_df = pd.DataFrame(alerts[-10:])
        st.dataframe(alert_df[["time", "type", "level", "message"]], use_container_width=True)
    else:
        st.info("暂无告警")

    st.divider()

    # 持仓详情
    st.subheader("📈 持仓详情")
    positions_data = status.get("positions_data", [])
    if positions_data:
        pos_df = pd.DataFrame(positions_data)
        st.dataframe(pos_df, use_container_width=True)
    else:
        st.info("暂无持仓")

    # 更新时间
    st.caption(f"最后更新: {status.get('update_time', 'N/A')}")

if __name__ == "__main__":
    main()
'''


def create_dashboard_file():
    """创建 Streamlit 面板文件"""
    dashboard_path = Path("monitoring/dashboard.py")
    dashboard_path.parent.mkdir(parents=True, exist_ok=True)
    with open(dashboard_path, "w", encoding="utf-8") as f:
        f.write(DASHBOARD_CODE)
    print(f"面板文件已创建: {dashboard_path}")
    print("运行命令: streamlit run monitoring/dashboard.py")


# 创建默认实例
monitoring_dashboard = MonitoringDashboard()
alert_manager = AlertManager()