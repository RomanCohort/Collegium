"""
回测报告生成模块
"""
import pandas as pd
import numpy as np
from typing import Dict, Optional
from pathlib import Path
from datetime import datetime


class ReportGenerator:
    """回测报告生成器"""

    def __init__(self, output_dir: str = None):
        self.output_dir = Path(output_dir) if output_dir else Path("output")
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def generate(
        self,
        results: dict,
        strategy_name: str = "",
        save_html: bool = True,
        save_csv: bool = True,
    ) -> str:
        """
        生成回测报告

        Args:
            results: 回测结果字典
            strategy_name: 策略名称
            save_html: 是否保存 HTML 报告
            save_csv: 是否保存 CSV

        Returns:
            报告文件路径
        """
        report_time = datetime.now().strftime("%Y%m%d_%H%M%S")
        strategy_name = strategy_name or "strategy"
        prefix = f"{strategy_name}_{report_time}"

        # 保存 CSV
        if save_csv:
            self._save_csv(results, prefix)

        # 生成 HTML 报告
        if save_html:
            html_path = self._generate_html_report(results, prefix)
            return html_path

        return ""

    def _save_csv(self, results: dict, prefix: str):
        """保存 CSV 文件"""
        # 净值序列
        if "nav_series" in results and results["nav_series"] is not None:
            nav_df = results["nav_series"]
            if isinstance(nav_df, pd.DataFrame):
                nav_df.to_csv(self.output_dir / f"{prefix}_nav.csv")

        # 交易记录
        if "trades" in results and not results["trades"].empty:
            results["trades"].to_csv(self.output_dir / f"{prefix}_trades.csv", index=False)

    def _generate_html_report(self, results: dict, prefix: str) -> str:
        """生成 HTML 报告"""
        html_path = self.output_dir / f"{prefix}_report.html"

        # 提取关键指标
        metrics = self._extract_metrics(results)

        html_content = self._build_html(results, metrics)

        with open(html_path, "w", encoding="utf-8") as f:
            f.write(html_content)

        print(f"报告已保存: {html_path}")
        return str(html_path)

    def _extract_metrics(self, results: dict) -> dict:
        """提取关键指标"""
        metrics = {}

        # 收益指标
        metrics["total_return"] = results.get("total_return", 0)
        metrics["annual_return"] = results.get("annual_return", 0)
        metrics["cumulative_return"] = results.get("cumulative_return", 0)

        # 风险指标
        metrics["annual_volatility"] = results.get("annual_volatility", 0)
        metrics["max_drawdown"] = results.get("max_drawdown", 0)
        metrics["sharpe_ratio"] = results.get("sharpe_ratio", 0)

        # 交易统计
        metrics["total_trades"] = results.get("total_trades", 0)
        metrics["win_rate"] = results.get("win_rate", 0)
        metrics["total_commission"] = results.get("total_commission", 0)
        metrics["total_slippage"] = results.get("total_slippage", 0)

        return metrics

    def _build_html(self, results: dict, metrics: dict) -> str:
        """构建 HTML 页面"""
        nav_series = results.get("nav_series")
        trades = results.get("trades")

        # 转换净值为 JSON
        nav_json = "[]"
        if nav_series is not None and isinstance(nav_series, pd.DataFrame):
            nav_json = nav_series.reset_index().to_json(orient="records", date_format="iso")

        trades_json = "[]"
        if trades is not None and not trades.empty:
            trades_json = trades.to_json(orient="records", date_format="iso")

        html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <title>回测报告</title>
    <script src="https://cdn.plot.ly/plotly-2.27.0.min.js"></script>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 40px; background: #f5f5f5; }}
        .container {{ max-width: 1200px; margin: 0 auto; background: white; padding: 30px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
        h1 {{ color: #333; border-bottom: 2px solid #4CAF50; padding-bottom: 10px; }}
        h2 {{ color: #555; margin-top: 30px; }}
        .metrics-grid {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 20px; margin: 20px 0; }}
        .metric-card {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 20px; border-radius: 10px; text-align: center; }}
        .metric-card.green {{ background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%); }}
        .metric-card.red {{ background: linear-gradient(135deg, #eb3349 0%, #f45c43 100%); }}
        .metric-value {{ font-size: 24px; font-weight: bold; margin: 10px 0; }}
        .metric-label {{ font-size: 12px; opacity: 0.9; }}
        .chart {{ margin: 20px 0; }}
        table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
        th, td {{ padding: 12px; text-align: left; border-bottom: 1px solid #ddd; }}
        th {{ background: #4CAF50; color: white; }}
        tr:hover {{ background: #f5f5f5; }}
        .summary {{ background: #f9f9f9; padding: 20px; border-radius: 10px; margin: 20px 0; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>回测报告</h1>
        <p>生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>

        <h2>收益概览</h2>
        <div class="metrics-grid">
            <div class="metric-card">
                <div class="metric-label">总收益率</div>
                <div class="metric-value">{metrics.get('total_return', 0):.2%}</div>
            </div>
            <div class="metric-card green">
                <div class="metric-label">年化收益</div>
                <div class="metric-value">{metrics.get('annual_return', 0):.2%}</div>
            </div>
            <div class="metric-card {'red' if metrics.get('max_drawdown', 0) > 0.1 else ''}">
                <div class="metric-label">最大回撤</div>
                <div class="metric-value">{metrics.get('max_drawdown', 0):.2%}</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">夏普比率</div>
                <div class="metric-value">{metrics.get('sharpe_ratio', 0):.2f}</div>
            </div>
        </div>

        <h2>交易统计</h2>
        <div class="summary">
            <p><strong>总交易次数:</strong> {metrics.get('total_trades', 0)}</p>
            <p><strong>胜率:</strong> {metrics.get('win_rate', 0):.2%}</p>
            <p><strong>总佣金:</strong> {metrics.get('total_commission', 0):.2f}</p>
            <p><strong>总滑点:</strong> {metrics.get('total_slippage', 0):.2f}</p>
        </div>

        <h2>净值曲线</h2>
        <div id="nav-chart" class="chart"></div>

        <h2>回撤曲线</h2>
        <div id="drawdown-chart" class="chart"></div>

        {"<h2>交易记录</h2><div id=\"trades-table\"></div>" if trades is not None and not trades.empty else ""}
    </div>

    <script>
        const navData = {nav_json};
        const tradesData = {trades_json};

        // 绘制净值曲线
        if (navData.length > 0) {{
            const navDates = navData.map(d => d.date || d.Date);
            const navValues = navData.map(d => d.nav || d.NAV || d.nav_value || d.value || 0);

            Plotly.newPlot('nav-chart', [{{
                x: navDates,
                y: navValues,
                type: 'scatter',
                mode: 'lines',
                name: '净值',
                line: {{ color: '#4CAF50', width: 2 }}
            }}], {{
                xaxis: {{ title: '日期' }},
                yaxis: {{ title: '净值' }},
                margin: {{ t: 20 }},
                responsive: true
            }});

            // 绘制回撤曲线
            let cummax = 0;
            let peak = 0;
            const drawdowns = navValues.map(v => {{
                if (v > peak) {{ peak = v; }}
                cummax = peak;
                return (v - cummax) / cummax;
            }});

            Plotly.newPlot('drawdown-chart', [{{
                x: navDates,
                y: drawdowns,
                type: 'scatter',
                mode: 'lines',
                name: '回撤',
                fill: 'tozeroy',
                line: {{ color: '#f44336', width: 1 }},
                fillcolor: 'rgba(244, 67, 54, 0.2)'
            }}], {{
                xaxis: {{ title: '日期' }},
                yaxis: {{ title: '回撤', tickformat: '.1%' }},
                margin: {{ t: 20 }},
                responsive: true
            }});
        }}

        // 交易记录表格
        if (tradesData.length > 0) {{
            const tableDiv = document.getElementById('trades-table');
            let tableHtml = '<table><thead><tr>';
            const keys = Object.keys(tradesData[0]);
            keys.forEach(k => {{ tableHtml += `<th>${{k}}</th>`; }});
            tableHtml += '</tr></thead><tbody>';
            tradesData.forEach(row => {{
                tableHtml += '<tr>';
                keys.forEach(k => {{
                    let val = row[k];
                    if (typeof val === 'number') {{ val = val.toFixed(2); }}
                    tableHtml += `<td>${{val}}</td>`;
                }});
                tableHtml += '</tr>';
            }});
            tableHtml += '</tbody></table>';
            tableDiv.innerHTML = tableHtml;
        }}
    </script>
</body>
</html>"""

        return html


# 创建默认实例
report_generator = ReportGenerator()