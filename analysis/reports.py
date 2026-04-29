"""
报告生成模块
"""

import pandas as pd
from typing import Dict, Optional
from datetime import datetime
from pathlib import Path


class ReportGenerator:
    """
    回测报告生成器
    """

    def __init__(self, output_dir: str = "reports"):
        """
        Args:
            output_dir: 报告输出目录
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def generate_html(self, results: Dict, strategy_name: str = "MultiFactor") -> str:
        """
        生成HTML回测报告

        Args:
            results: 回测结果字典
            strategy_name: 策略名称

        Returns:
            报告文件路径
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = self.output_dir / f"backtest_report_{strategy_name}_{timestamp}.html"

        # 提取数据
        perf = results.get('performance', {})
        basic = perf.get('basic', {})
        risk = perf.get('risk', {})
        risk_adj = perf.get('risk_adjusted', {})
        rel = perf.get('relative', {})
        trading = perf.get('trading', {})
        nav = results.get('nav', pd.DataFrame())

        # 生成净值JSON
        nav_json = ""
        if not nav.empty:
            nav_data = nav[['date', 'nav']].to_dict('records')
            nav_json = str(nav_data)[:1000] + "..."  # 截断避免过长

        html_content = f"""
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>量化回测报告 - {strategy_name}</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
            background-color: #f5f5f5;
        }}
        .header {{
            background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
            color: white;
            padding: 30px;
            border-radius: 10px;
            margin-bottom: 20px;
        }}
        .header h1 {{
            margin: 0 0 10px 0;
        }}
        .header .subtitle {{
            opacity: 0.8;
            font-size: 14px;
        }}
        .card {{
            background: white;
            border-radius: 10px;
            padding: 20px;
            margin-bottom: 20px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }}
        .card h2 {{
            margin-top: 0;
            color: #333;
            border-bottom: 2px solid #2a5298;
            padding-bottom: 10px;
        }}
        .metrics {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
        }}
        .metric {{
            background: #f8f9fa;
            padding: 15px;
            border-radius: 8px;
            text-align: center;
        }}
        .metric .label {{
            font-size: 12px;
            color: #666;
            margin-bottom: 5px;
        }}
        .metric .value {{
            font-size: 24px;
            font-weight: bold;
            color: #1e3c72;
        }}
        .metric .value.positive {{
            color: #28a745;
        }}
        .metric .value.negative {{
            color: #dc3545;
        }}
        .positions-table {{
            width: 100%;
            border-collapse: collapse;
        }}
        .positions-table th, .positions-table td {{
            padding: 10px;
            text-align: right;
            border-bottom: 1px solid #eee;
        }}
        .positions-table th {{
            background: #f8f9fa;
            text-align: right;
        }}
        .positions-table th:first-child, .positions-table td:first-child {{
            text-align: left;
        }}
        .footer {{
            text-align: center;
            color: #666;
            font-size: 12px;
            margin-top: 30px;
            padding: 20px;
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>量化回测报告</h1>
        <div class="subtitle">
            策略: {strategy_name} | 生成时间: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
        </div>
    </div>

    <div class="card">
        <h2>基本信息</h2>
        <div class="metrics">
            <div class="metric">
                <div class="label">回测期间</div>
                <div class="value" style="font-size:16px">{basic.get('start_date', '-')} ~ {basic.get('end_date', '-')}</div>
            </div>
            <div class="metric">
                <div class="label">交易日数</div>
                <div class="value" style="font-size:16px">{basic.get('days', 0)}天</div>
            </div>
            <div class="metric">
                <div class="label">初始资金</div>
                <div class="value" style="font-size:16px">¥{basic.get('initial_cash', 0):,.0f}</div>
            </div>
            <div class="metric">
                <div class="label">最终市值</div>
                <div class="value" style="font-size:16px">¥{basic.get('final_value', 0):,.2f}</div>
            </div>
        </div>
    </div>

    <div class="card">
        <h2>收益指标</h2>
        <div class="metrics">
            <div class="metric">
                <div class="label">总收益率</div>
                <div class="value {'positive' if basic.get('total_return', 0) >= 0 else 'negative'}">
                    {basic.get('total_return_pct', 0):.2f}%
                </div>
            </div>
            <div class="metric">
                <div class="label">年化收益率</div>
                <div class="value {'positive' if basic.get('annual_return', 0) >= 0 else 'negative'}">
                    {basic.get('annual_return_pct', 0):.2f}%
                </div>
            </div>
            <div class="metric">
                <div class="label">Alpha</div>
                <div class="value {'positive' if rel.get('alpha', 0) >= 0 else 'negative'}">
                    {rel.get('alpha', 0):.4f}
                </div>
            </div>
            <div class="metric">
                <div class="label">Beta</div>
                <div class="value">
                    {rel.get('beta', 1):.4f}
                </div>
            </div>
        </div>
    </div>

    <div class="card">
        <h2>风险指标</h2>
        <div class="metrics">
            <div class="metric">
                <div class="label">最大回撤</div>
                <div class="value negative">
                    -{risk.get('max_drawdown_pct', 0):.2f}%
                </div>
            </div>
            <div class="metric">
                <div class="label">年化波动率</div>
                <div class="value">
                    {risk.get('volatility_pct', 0):.2f}%
                </div>
            </div>
            <div class="metric">
                <div class="label">夏普比率</div>
                <div class="value">
                    {risk_adj.get('sharpe_ratio', 0):.3f}
                </div>
            </div>
            <div class="metric">
                <div class="label">索提诺比率</div>
                <div class="value">
                    {risk_adj.get('sortino_ratio', 0):.3f}
                </div>
            </div>
            <div class="metric">
                <div class="label">卡玛比率</div>
                <div class="value">
                    {risk_adj.get('calmar_ratio', 0):.3f}
                </div>
            </div>
        </div>
    </div>

    <div class="card">
        <h2>交易统计</h2>
        <div class="metrics">
            <div class="metric">
                <div class="label">胜率</div>
                <div class="value {'positive' if trading.get('win_rate', 0) >= 0.5 else 'negative'}">
                    {trading.get('win_rate_pct', 0):.2f}%
                </div>
            </div>
            <div class="metric">
                <div class="label">平均日收益</div>
                <div class="value {'positive' if trading.get('avg_return', 0) >= 0 else 'negative'}">
                    {trading.get('avg_return_pct', 0):.4f}%
                </div>
            </div>
        </div>
    </div>

    <div class="footer">
        本报告由量化交易系统自动生成 | QuantSystem v1.0
    </div>
</body>
</html>
        """

        with open(filename, 'w', encoding='utf-8') as f:
            f.write(html_content)

        print(f"HTML报告已生成: {filename}")
        return str(filename)

    def generate_summary(self, results: Dict) -> str:
        """
        生成文字摘要

        Args:
            results: 回测结果

        Returns:
            摘要字符串
        """
        perf = results.get('performance', {})
        basic = perf.get('basic', {})
        risk = perf.get('risk', {})
        risk_adj = perf.get('risk_adjusted', {})

        summary = f"""
===============================================
        多因子量化交易系统 - 回测摘要
===============================================
回测期间: {basic.get('start_date', '-')} ~ {basic.get('end_date', '-')}
初始资金: ¥{basic.get('initial_cash', 0):,.2f}
最终市值: ¥{basic.get('final_value', 0):,.2f}

收益表现:
  总收益率: {basic.get('total_return_pct', 0):.2f}%
  年化收益率: {basic.get('annual_return_pct', 0):.2f}%

风险指标:
  最大回撤: -{risk.get('max_drawdown_pct', 0):.2f}%
  年化波动率: {risk.get('volatility_pct', 0):.2f}%

风险调整收益:
  Sharpe比率: {risk_adj.get('sharpe_ratio', 0):.3f}
  Sortino比率: {risk_adj.get('sortino_ratio', 0):.3f}
  Calmar比率: {risk_adj.get('calmar_ratio', 0):.3f}
===============================================
"""
        return summary
