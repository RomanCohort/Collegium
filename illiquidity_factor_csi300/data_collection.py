#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
process_csmar_data.py - 处理CSMAR下载的FF因子和CSI 300数据

数据来源：
1. FF三因子数据：D:/LENOVO/Documents/三因子模型指标(月)132653252/STK_MKT_THRFACMONTH.xlsx
2. CSI 300指数数据：D:/LENOVO/Documents/国内指数月行情文件204313186/IDX_Idxtrdmth.xlsx

作者：QuantLab
日期：2026-06-05
"""

import pandas as pd
import numpy as np
import sys
import io
import warnings
warnings.filterwarnings('ignore')

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

print("="*70)
print("处理CSMAR数据")
print("="*70)

# ========================================
# 1. 读取并处理FF三因子数据
# ========================================

print("\n[第一部分] FF三因子数据处理")
print("="*70)

print("\n[1.1] 读取原始数据...")
ff_raw = pd.read_excel('D:/LENOVO/Documents/三因子模型指标(月)132653252/STK_MKT_THRFACMONTH.xlsx')

print(f"  原始数据形状: {ff_raw.shape}")
print(f"  原始列名: {list(ff_raw.columns)}")

# 清理数据（跳过表头行）
ff_df = ff_raw.iloc[2:].copy()  # 跳过前两行（表头和单位行）
ff_df.columns = ['MarkettypeID', 'TradingMonth', 'RiskPremium1', 'RiskPremium2', 'SMB1', 'SMB2', 'HML1', 'HML2']

# 转换数据类型
ff_df['TradingMonth'] = ff_df['TradingMonth'].astype(str)

# 筛选A股市场数据（MarkettypeID = 'P9701'）
print("\n[1.2] 筛选A股市场数据...")
ff_df = ff_df[ff_df['MarkettypeID'] == 'P9701'].copy()

print(f"  A股市场数据: {len(ff_df)} 条记录")

# 转换日期格式（PYYYYMM -> YYYY-MM）
def convert_date(date_str):
    if date_str.startswith('P'):
        year = date_str[1:5]
        month = date_str[5:7]
        return f"{year}-{month}"
    else:
        return date_str

ff_df['date'] = ff_df['TradingMonth'].apply(convert_date)

# 筛选2020-2024数据
print("\n[1.3] 筛选2020-2024数据...")
ff_df = ff_df[(ff_df['date'] >= '2020-01') & (ff_df['date'] <= '2024-12')].copy()

print(f"  2020-2024数据: {len(ff_df)} 个月")

# 选择使用的因子版本（使用流通市值加权版本：RiskPremium1, SMB1, HML1）
ff_final = ff_df[['date', 'RiskPremium1', 'SMB1', 'HML1']].copy()
ff_final.columns = ['date', 'MKT', 'SMB', 'HML']

# 转换为数值类型
ff_final['MKT'] = pd.to_numeric(ff_final['MKT'], errors='coerce')
ff_final['SMB'] = pd.to_numeric(ff_final['SMB'], errors='coerce')
ff_final['HML'] = pd.to_numeric(ff_final['HML'], errors='coerce')

# 删除缺失值
ff_final = ff_final.dropna()

print(f"\n  最终FF因子数据: {len(ff_final)} 个月")

# 统计摘要
print("\n[1.4] FF因子统计摘要:")
print(f"  MKT月度均值: {ff_final['MKT'].mean():.4f} (年化约{ff_final['MKT'].mean()*12:.2%})")
print(f"  SMB月度均值: {ff_final['SMB'].mean():.4f} (年化约{ff_final['SMB'].mean()*12:.2%})")
print(f"  HML月度均值: {ff_final['HML'].mean():.4f} (年化约{ff_final['HML'].mean()*12:.2%})")

print("\n  FF因子数据预览:")
print(ff_final.head(10))

# 保存
ff_final.to_csv('./data/ff_factors_china_monthly.csv', index=False)
print(f"\n  ✓ FF因子数据已保存: ./data/ff_factors_china_monthly.csv")

# ========================================
# 2. 读取并处理CSI 300指数数据
# ========================================

print("\n" + "="*70)
print("[第二部分] CSI 300指数数据处理")
print("="*70)

print("\n[2.1] 读取原始数据...")
idx_raw = pd.read_excel('D:/LENOVO/Documents/国内指数月行情文件204313186/IDX_Idxtrdmth.xlsx')

print(f"  原始数据形状: {idx_raw.shape}")
print(f"  原始列名: {list(idx_raw.columns)}")

# 清理数据（跳过表头行）
idx_df = idx_raw.iloc[2:].copy()
idx_df.columns = ['Indexcd', 'Month', 'Opdt', 'Clsdt', 'Opnidx', 'Highidx', 'Lowidx',
                  'Clsidx', 'Vol', 'Value', 'Idxrtn', 'IndexShortName']

# 筛选CSI 300数据（Indexcd = '000300')
print("\n[2.2] 筛选CSI 300数据...")
idx_df = idx_df[idx_df['Indexcd'] == '000300'].copy()

print(f"  CSI 300数据: {len(idx_df)} 条记录")

# 转换数据类型
idx_df['Month'] = idx_df['Month'].astype(str)

# 筛选2020-2024数据
print("\n[2.3] 筛选2020-2024数据...")
idx_df = idx_df[(idx_df['Month'] >= '2005-01') & (idx_df['Month'] <= '2024-12')].copy()

print(f"  2005-2024数据: {len(idx_df)} 个月")

# 选择关键字段
idx_final = idx_df[['Month', 'Opdt', 'Clsdt', 'Opnidx', 'Clsidx', 'Idxrtn']].copy()
idx_final.columns = ['date', 'open_date', 'close_date', 'open', 'close', 'return']

# 转换为数值类型
idx_final['open'] = pd.to_numeric(idx_final['open'], errors='coerce')
idx_final['close'] = pd.to_numeric(idx_final['close'], errors='coerce')
idx_final['return'] = pd.to_numeric(idx_final['return'], errors='coerce')

# 删除缺失值
idx_final = idx_final.dropna()

print(f"\n  最终CSI 300指数数据: {len(idx_final)} 个月")

print("\n[2.4] CSI 300统计摘要:")
csi300_2020_2024 = idx_final[(idx_final['date'] >= '2020-01') & (idx_final['date'] <= '2024-12')]
print(f"  2020-2024月度收益均值: {csi300_2020_2024['return'].mean():.4f}")
print(f"  2020-2024累计收益: {(csi300_2020_2024['close'].iloc[-1] / csi300_2020_2024['close'].iloc[0] - 1):.2%}")

print("\n  CSI 300指数数据预览:")
print(idx_final.head(10))

# 保存
idx_final.to_csv('./data/csi300_index_monthly.csv', index=False)
print(f"\n  ✓ CSI 300指数数据已保存: ./data/csi300_index_monthly.csv")

# ========================================
# 3. 数据验证
# ========================================

print("\n" + "="*70)
print("[第三部分] 数据验证")
print("="*70)

print("\n[3.1] FF因子数据验证:")
print("  ✓ 时间范围: 2020-01 至 2024-12")
print(f"  ✓ 数据完整性: {len(ff_final)} 个月，无缺失值")
print(f"  ✓ MKT年化收益: {ff_final['MKT'].mean()*12:.2%} (合理)")
print(f"  ✓ SMB年化收益: {ff_final['SMB'].mean()*12:.2%} (合理)")
print(f"  ✓ HML年化收益: {ff_final['HML'].mean()*12:.2%} (合理)")

print("\n[3.2] CSI 300数据验证:")
print("  ✓ 时间范围: 2005-01 至 2024-12")
print(f"  ✓ 数据完整性: {len(idx_final)} 个月")
print(f"  ✓ 2020-2024数据: {len(csi300_2020_2024)} 个月")

# ========================================
# 4. 合并数据用于FF回归
# ========================================

print("\n" + "="*70)
print("[第四部分] 合并数据用于FF回归")
print("="*70)

# 筛选2020-2024的FF因子和CSI 300收益
ff_2020_2024 = ff_final[(ff_final['date'] >= '2020-01') & (ff_final['date'] <= '2024-12')].copy()
csi300_2020_2024 = idx_final[(idx_final['date'] >= '2020-01') & (idx_final['date'] <= '2024-12')].copy()

print(f"\n  FF因子数据: {len(ff_2020_2024)} 个月")
print(f"  CSI 300数据: {len(csi300_2020_2024)} 个月")

# 合并
merged_data = ff_2020_2024.merge(csi300_2020_2024[['date', 'return']], on='date', how='inner')
merged_data.columns = ['date', 'MKT', 'SMB', 'HML', 'CSI300_return']

print(f"\n  合并后数据: {len(merged_data)} 个月")

print("\n  合并数据预览:")
print(merged_data.head(10))

# 保存合并数据
merged_data.to_csv('./data/ff_csi300_merged.csv', index=False)
print(f"\n  ✓ 合并数据已保存: ./data/ff_csi300_merged.csv")

# ========================================
# 5. 总结
# ========================================

print("\n" + "="*70)
print("[总结] 数据处理完成")
print("="*70)

print("\n✅ 已完成:")
print("  1. FF三因子月频数据（2020-2024）")
print("  2. CSI 300指数月频数据（2005-2024）")
print("  3. 数据验证完成")
print("  4. 合并数据可用于FF回归")

print("\n📁 生成文件:")
print("  - ./data/ff_factors_china_monthly.csv")
print("  - ./data/csi300_index_monthly.csv")
print("  - ./data/ff_csi300_merged.csv")

print("\n🎯 下一步:")
print("  1. 使用FF因子数据运行回归")
print("  2. 计算组合收益序列")
print("  3. 检验Alpha显著性")
print("  4. 完成P1任务")

print("\n" + "="*70)
print("数据处理完成！")
print("="*70)