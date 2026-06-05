#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
run_ff_regression.py - 运行FF三因子回归检验Alpha

使用真实FF因子数据检验illiquidity策略的Alpha

作者：QuantLab
日期：2026-06-05
"""

import pandas as pd
import numpy as np
from scipy import stats
from sklearn.linear_model import LinearRegression
import json
import sys
import io
import warnings
warnings.filterwarnings('ignore')

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

print("="*70)
print("FF三因子回归 - Alpha检验")
print("="*70)

# ========================================
# 1. 加载FF因子数据
# ========================================

print("\n[第一部分] 加载数据")
print("="*70)

print("\n[1.1] 加载FF三因子数据...")
ff_df = pd.read_csv('./data/ff_factors_china_monthly.csv')
print(f"  FF因子数据: {len(ff_df)} 个月")
print(ff_df.head())

print("\n[1.2] 加载CSI 300指数数据...")
csi300_df = pd.read_csv('./data/csi300_index_monthly.csv')
csi300_df = csi300_df[(csi300_df['date'] >= '2020-01') & (csi300_df['date'] <= '2024-12')]
print(f"  CSI 300数据: {len(csi300_df)} 个月")

# ========================================
# 2. 计算illiquidity策略收益
# ========================================

print("\n" + "="*70)
print("[第二部分] 计算illiquidity策略月度收益")
print("="*70)

print("\n[2.1] 加载股票数据...")
data = pd.read_parquet('./results/baostock_data_20260605_174130.parquet')
data = data.sort_values(['code', 'date'])

print(f"  股票数据: {len(data)} 条, {data['code'].nunique()} 只股票")

# 计算illiquidity因子
print("\n[2.2] 计算illiquidity因子...")
for code, group in data.groupby('code'):
    idx = group.index
    data.loc[idx, 'illiquidity'] = 1 / (group['volume'] * group['close'])

# 转换为月度数据
print("\n[2.3] 转换为月度频率...")
data['date'] = pd.to_datetime(data['date'])
data['month'] = data['date'].dt.to_period('M')

# 计算每月末的因子值
monthly_data = data.groupby(['code', 'month']).last().reset_index()
monthly_data['month'] = monthly_data['month'].astype(str)

print(f"  月度数据: {len(monthly_data)} 条")

# ========================================
# 3. 构建月度组合收益
# ========================================

print("\n" + "="*70)
print("[第三部分] 构建月度组合收益")
print("="*70)

# 获取调仓日期
dates = sorted(monthly_data['month'].unique())
print(f"\n  可用月份: {len(dates)} 个")

# 筛选2020-2024
dates = [d for d in dates if d >= '2020-01' and d <= '2024-12']
print(f"  2020-2024月份: {len(dates)} 个")

# 月度调仓
np.random.seed(42)
portfolio_returns = []

print("\n[3.1] 月度调仓回测...")

for i, month in enumerate(dates[:-1]):
    # 获取该月数据
    month_data = monthly_data[monthly_data['month'] == month].copy()

    if len(month_data) < 20:
        continue

    # 标准化illiquidity
    month_data['illiquidity'] = month_data['illiquidity'].clip(
        lower=month_data['illiquidity'].quantile(0.01),
        upper=month_data['illiquidity'].quantile(0.99)
    )
    month_data['illiquidity'] = (month_data['illiquidity'] - month_data['illiquidity'].mean()) / \
                                 month_data['illiquidity'].std()

    # 选择高分股票（高illiquidity = 低流动性）
    top_stocks = month_data.nlargest(20, 'illiquidity')['code'].tolist()

    # 计算下月收益
    next_month = dates[dates.index(month) + 1]
    next_month_data = monthly_data[monthly_data['month'] == next_month]

    if len(next_month_data) == 0:
        continue

    # 计算持有期收益
    period_return = 0
    valid_stocks = 0

    for code in top_stocks:
        stock_curr = month_data[month_data['code'] == code]
        stock_next = next_month_data[next_month_data['code'] == code]

        if len(stock_curr) > 0 and len(stock_next) > 0:
            r = stock_next['close'].values[0] / stock_curr['close'].values[0] - 1
            period_return += r
            valid_stocks += 1

    if valid_stocks > 0:
        period_return = period_return / valid_stocks - 0.002  # 扣除交易成本

        portfolio_returns.append({
            'month': month,
            'return': period_return,
            'n_stocks': valid_stocks
        })

portfolio_df = pd.DataFrame(portfolio_returns)
print(f"\n  有效调仓期: {len(portfolio_df)} 个月")

# ========================================
# 4. 合并FF因子和组合收益
# ========================================

print("\n" + "="*70)
print("[第四部分] 合并FF因子和组合收益")
print("="*70)

# 重命名列以便合并
portfolio_df = portfolio_df.rename(columns={'month': 'date'})

# 合并
regression_df = portfolio_df.merge(ff_df, on='date', how='inner')

print(f"\n  合并后数据: {len(regression_df)} 个月")
print("\n  回归数据预览:")
print(regression_df.head(10))

# ========================================
# 5. FF三因子回归
# ========================================

print("\n" + "="*70)
print("[第五部分] FF三因子回归")
print("="*70)

print("\n[5.1] 回归模型:")
print("  R_portfolio = α + β_MKT × MKT + β_SMB × SMB + β_HML × HML + ε")

# 准备数据
X = regression_df[['MKT', 'SMB', 'HML']].values
y = regression_df['return'].values

# 运行回归
model = LinearRegression()
model.fit(X, y)

# 提取系数
alpha = model.intercept_
beta_mkt, beta_smb, beta_hml = model.coef_

# 计算R²
y_pred = model.predict(X)
residuals = y - y_pred
r_squared = 1 - np.sum(residuals**2) / np.sum((y - np.mean(y))**2)

# Alpha显著性检验
n = len(y)
p = 4  # 参数数量（alpha + 3个beta）
alpha_std = np.std(residuals) / np.sqrt(n)
alpha_t = alpha / alpha_std
alpha_p = 2 * (1 - stats.t.cdf(abs(alpha_t), n - p))

print("\n[5.2] 回归结果:")
print(f"  α (Alpha): {alpha:.6f}")
print(f"  β_MKT: {beta_mkt:.4f}")
print(f"  β_SMB: {beta_smb:.4f}")
print(f"  β_HML: {beta_hml:.4f}")
print(f"  R²: {r_squared:.4f}")

print("\n[5.3] Alpha显著性检验:")
print(f"  Alpha t统计量: {alpha_t:.3f}")
print(f"  Alpha p值: {alpha_p:.4f}")

if alpha_p < 0.05:
    print(f"  ✅ Alpha显著！策略有真正的超额收益")
else:
    print(f"  ❌ Alpha不显著，收益可能来自因子暴露")

# ========================================
# 6. 因子暴露解读
# ========================================

print("\n" + "="*70)
print("[第六部分] 因子暴露解读")
print("="*70)

print("\n[6.1] 因子暴露分析:")

if beta_mkt < 0.8:
    print(f"  ✓ 低市场暴露 (β_MKT={beta_mkt:.4f})")
    print("    说明：策略收益不完全来自市场风险")
elif beta_mkt > 1.2:
    print(f"  ⚠️ 高市场暴露 (β_MKT={beta_mkt:.4f})")
    print("    说明：策略可能放大了市场风险")
else:
    print(f"  中性市场暴露 (β_MKT={beta_mkt:.4f})")

if beta_smb > 0.3:
    print(f"  ⚠️ 倾向小市值 (β_SMB={beta_smb:.4f})")
elif beta_smb < -0.3:
    print(f"  ⚠️ 倾向大市值 (β_SMB={beta_smb:.4f})")
else:
    print(f"  ✓ 规模中性 (β_SMB={beta_smb:.4f})")

if beta_hml > 0.3:
    print(f"  ⚠️ 倾向价值股 (β_HML={beta_hml:.4f})")
elif beta_hml < -0.3:
    print(f"  ⚠️ 倾向成长股 (β_HML={beta_hml:.4f})")
else:
    print(f"  ✓ 价值中性 (β_HML={beta_hml:.4f})")

print("\n[6.2] Alpha解读:")
if alpha_p < 0.05:
    print(f"  ✅ Alpha显著 (p={alpha_p:.4f})")
    print(f"  ✅ 月度Alpha: {alpha:.4%}")
    print(f"  ✅ 年化Alpha: {alpha*12:.4%}")
    print("\n  结论：")
    print("  策略在控制市场、规模、价值因子后，仍有显著超额收益")
    print("  这证明了illiquidity因子的独立定价能力")
else:
    print(f"  ❌ Alpha不显著 (p={alpha_p:.4f})")
    print(f"  月度Alpha: {alpha:.4%}")
    print(f"  年化Alpha: {alpha*12:.4%}")
    print("\n  结论：")
    print("  策略收益可由FF三因子解释，无独立Alpha")

# ========================================
# 7. 与CSI 300对比
# ========================================

print("\n" + "="*70)
print("[第七部分] 与CSI 300基准对比")
print("="*70)

# 计算累计收益
portfolio_cum = (1 + regression_df['return']).cumprod()
csi300_cum = (1 + regression_df['CSI300_return']).cumprod()

portfolio_total = portfolio_cum.iloc[-1] - 1
csi300_total = csi300_cum.iloc[-1] - 1

print(f"\n[7.1] 累计收益对比:")
print(f"  策略累计收益: {portfolio_total:.2%}")
print(f"  CSI 300累计收益: {csi300_total:.2%}")
print(f"  超额收益: {portfolio_total - csi300_total:.2%}")

# Sharpe比率
portfolio_sharpe = regression_df['return'].mean() / regression_df['return'].std() * np.sqrt(12)
csi300_sharpe = regression_df['CSI300_return'].mean() / regression_df['CSI300_return'].std() * np.sqrt(12)

print(f"\n[7.2] Sharpe比率对比:")
print(f"  策略Sharpe: {portfolio_sharpe:.3f}")
print(f"  CSI 300 Sharpe: {csi300_sharpe:.3f}")

# ========================================
# 8. 总结
# ========================================

print("\n" + "="*70)
print("[总结] FF回归分析完成")
print("="*70)

results = {
    'ff_regression': {
        'alpha': round(alpha, 6),
        'alpha_annual': round(alpha * 12, 6),
        'beta_mkt': round(beta_mkt, 4),
        'beta_smb': round(beta_smb, 4),
        'beta_hml': round(beta_hml, 4),
        'r_squared': round(r_squared, 4),
        'alpha_t_stat': round(alpha_t, 3),
        'alpha_p_value': round(alpha_p, 4),
        'alpha_significant': alpha_p < 0.05
    },
    'performance': {
        'portfolio_return': round(portfolio_total, 4),
        'csi300_return': round(csi300_total, 4),
        'excess_return': round(portfolio_total - csi300_total, 4),
        'portfolio_sharpe': round(portfolio_sharpe, 3),
        'csi300_sharpe': round(csi300_sharpe, 3)
    },
    'interpretation': {
        'low_market_exposure': beta_mkt < 0.8,
        'alpha_source': 'Independent illiquidity factor' if alpha_p < 0.05 else 'Factor exposure'
    }
}

with open('./results/ff_regression_results.json', 'w') as f:
    json.dump(results, f, indent=2)

print("\n✅ 完成内容:")
print("  1. FF三因子回归")
print("  2. Alpha显著性检验")
print("  3. 因子暴露解读")
print("  4. 与CSI 300对比")

print("\n📁 结果文件:")
print("  - ./results/ff_regression_results.json")

print("\n🎯 关键发现:")
if alpha_p < 0.05:
    print(f"  ✅ Alpha显著 (p={alpha_p:.4f})")
    print(f"  ✅ 年化Alpha: {alpha*12:.2%}")
    print(f"  ✅ 策略有真正的超额收益")
else:
    print(f"  ⚠️ Alpha不显著 (p={alpha_p:.4f})")
    print(f"  ⚠️ 收益可能来自因子暴露而非Alpha")

print("\n" + "="*70)
print("FF回归分析完成！")
print("="*70)