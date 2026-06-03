# Stage 2.5: INTEGRITY Verification Report

**Paper:** Collegium v2.0: An AI-Enhanced Multi-Factor Quantitative Trading System
**Target Journal:** IEEE Access
**Verification Date:** 2026-06-03
**Status:** ⚠️ MAJOR REVISION REQUIRED

---

## Executive Summary

The paper draft requires significant revision before IEEE Access submission. Three critical issues were identified:

1. **Data Integrity Gap**: Paper claims results from virtual market simulation, but recent real CSI300 backtest shows negative absolute returns (-9.05% total) though positive excess returns (+20.56% over benchmark)
2. **Citation Issues**: 3 references require verification/update for IEEE Access format
3. **Claims vs Evidence Mismatch**: Paper claims "significant excess returns" based on synthetic data, but real data results are modest

---

## 1. Citation Verification (27 References)

### 1.1 References Verified ✓ (24/27)

| # | Reference | Status | Notes |
|---|-----------|--------|-------|
| 1 | Araci (2019) FinBERT | ✓ Valid | arXiv:1908.10063 exists |
| 2 | Chen et al. (2022) GNN | ✓ Valid | Quant Finance 22(7):1251-1266 |
| 3 | DeepSeek-AI (2024) | ✓ Valid | arXiv:2405.04434 exists |
| 4 | Fama & French (1993) | ✓ Valid | JFE 33(1):3-56 |
| 5 | Fama & French (2015) | ✓ Valid | JFE 116(1):1-22 |
| 6 | Graves (2016) ACT | ✓ Valid | arXiv:1603.08983 |
| 7 | Gu & Dao (2023) Mamba | ✓ Valid | arXiv:2312.00752 |
| 8 | Gu, Kelly, Xiu (2020) | ✓ Valid | RFS 33(5):2223-2273 |
| 9 | Hochreiter & Schmidhuber (1997) | ✓ Valid | Neural Computation 9(8) |
| 10 | Jiang et al. (2017) DRL | ✓ Valid | arXiv:1706.10059 |
| 11 | Kim et al. (2024) Earnings | ✓ Valid | JFE 152:103748 |
| 12 | Kim & Lee (2025) LLM Survey | ⚠️ Check | Future date - verify publication |
| 13 | Liang et al. (2018) | ✓ Valid | arXiv:1808.09940 |
| 14 | Liu & Ma (2022) China Review | ✓ Valid | CFRI 12(3) |
| 15 | Liu, Stambaugh, Yuan (2019) | ✓ Valid | JFE 134(1):48-69 |
| 16 | Liu et al. (2024) SSM | ⚠️ Check | Verify Quant Finance 24(5) |
| 17 | Moody et al. (1998) | ✓ Valid | J Forecasting 17(5-6) |
| 18 | MSCI (2023) Barra Handbook | ✓ Valid | Industry report |
| 19 | Nevmyvaka et al. (2006) | ✓ Valid | WWW Conference |
| 20 | OpenAI (2023) GPT-4 | ✓ Valid | arXiv:2303.08774 |
| 21 | Rosenberg (1974) | ✓ Valid | JFQA 9(2) |
| 22 | Schulman et al. (2017) PPO | ✓ Valid | arXiv:1707.06347 |
| 23 | Sen et al. (2019) TCN | ⚠️ Check | Verify KDD proceedings |
| 24 | Spooner et al. (2018) | ✓ Valid | AAMAS proceedings |
| 25 | Vaswani et al. (2017) | ✓ Valid | NeurIPS 30 |
| 26 | Wang et al. (2024) | ✓ Valid | JFDS 6(2):112-130 |
| 27 | Zhang et al. (2021) | ✓ Valid | Expert Syst Appl 182 |

### 1.2 References Requiring Action

**#12 Kim & Lee (2025)**: Future-dated reference
- Issue: Publication date is 2025, but current date is 2026-06-03
- Action: Verify if this paper was actually published in Digital Finance 7(1), or update to "forthcoming"

**#16 Liu et al. (2024)**: Volume verification needed
- Verify Quantitative Finance 24(5):891-910 actually exists

**#23 Sen et al. (2019)**: Proceedings verification
- Verify KDD 2019 proceedings page numbers

---

## 2. Data Integrity Verification

### 2.1 Paper Claims vs Actual Results

#### Virtual Market Results (Paper Table 2)
| Metric | Benchmark | v2.0 | v2.1 |
|--------|-----------|------|------|
| Annual Return | 5.57% | 37.30% | 38.5% |
| Sharpe Ratio | — | 2.385 | 2.65 |
| Max Drawdown | — | 95.04% | 82.5% |

#### Real CSI300 Backtest Results (2022-01-01 to 2024-06-30)
| Metric | Value |
|--------|-------|
| Total Return | -9.05% |
| Annual Return | -3.90% |
| Sharpe Ratio | -0.24 |
| Max Drawdown | -16.95% |
| Benchmark Return | -29.61% |
| **Excess Return** | **+20.56%** |
| Trading Days | 601 |
| Stocks | 11 |

### 2.2 IC Analysis Results

#### Paper Claims (Table 4)
| Factor | IC Mean | ICIR |
|--------|---------|------|
| ma_return_20d | 0.703 | 4.95 |
| return_20d | 0.444 | 2.15 |
| **Average** | **0.0312** | **0.82** |

#### Actual Measured IC (2026-06-03)
| Factor | IC Mean | ICIR | Positive% |
|--------|---------|------|-----------|
| momentum_12m | 0.057 | 0.146 | 58.1% |
| momentum_6m | 0.022 | 0.055 | 53.5% |
| amihud_illiq | 0.020 | 0.064 | 53.4% |
| reversal_1m | -0.027 | -0.076 | 46.9% |
| macd_hist | -0.045 | -0.129 | 45.4% |

### 2.3 Critical Discrepancies

1. **Return Sign Mismatch**: Paper claims +37-38% annual returns, real data shows -3.9% annual return
2. **Sharpe Ratio**: Paper claims 2.38-2.65, real data shows -0.24
3. **IC Values**: Paper shows very high IC (0.44-0.70), actual measured IC is 0.02-0.06
4. **Positive Signal**: Real data shows +20.56% excess return over benchmark, which IS valuable

---

## 3. Originality Check

### 3.1 Architecture Originality ✓
- CTM v2 multi-time-scale reasoning: Novel contribution
- Mamba for regime detection: Novel application
- LLM reflective reasoning layer: Novel integration

### 3.2 Potential Issues
- DeepSeek integration section heavily references DeepSeek-AI (2024) - ensure sufficient original analysis
- PPO implementation uses standard Stable-Baselines3 - acknowledge this is not novel

---

## 4. Claims vs Evidence Assessment

### 4.1 Overstated Claims

**Original Claim (Abstract):**
> "We evaluate the system on a calibrated synthetic market exhibiting known factor structures"

**Issue:** Paper presents synthetic results as primary validation, but:
- Real CSI300 backtest shows negative absolute returns
- Excess return (+20.56%) is meaningful but not highlighted

**Recommended Revision:**
> "We evaluate the system on both synthetic market simulation and real CSI300 constituent data (2022-2024). While absolute returns were negative during the test period (-9.05%), the strategy achieved +20.56% excess return over the benchmark, demonstrating relative value in a declining market."

### 4.2 Supported Claims ✓
- Multi-factor framework implementation
- IC-based dynamic weighting mechanism
- Mamba regime classification architecture
- Modular system design

### 4.3 Unsupported Claims
- "Significant positive returns" - not supported by real data
- "Sharpe ratio above 2.3" - not achieved in real markets
- High IC values (0.44-0.70) - actual values are 0.02-0.06

---

## 5. IEEE Access Format Compliance

### 5.1 Required Changes

1. **Journal Header**: Change from "Journal of Financial Data Science" to "IEEE Access"
2. **Reference Format**: IEEE uses numbered references [1]-[27], not author-year
3. **Section Numbering**: Current format is acceptable
4. **Abstract**: Add "Index Terms" section for IEEE

### 5.2 Missing Elements
- Conflict of Interest Statement
- Data Availability Statement (exists but needs IEEE format)
- Author Contributions section
- Funding acknowledgment

---

## 6. Recommended Actions

### Priority 1: Data Integrity (CRITICAL)
1. **Add Real Market Results Section** with:
   - CSI300 backtest: 2022-01-01 to 2024-06-30
   - Total return: -9.05%, Sharpe: -0.24
   - Excess return: +20.56% vs benchmark (-29.61%)
   - Framing: "outperformed benchmark in declining market"

2. **Revise Claims** to match evidence:
   - Change "positive returns" to "excess returns over benchmark"
   - Update IC values to reflect actual measurements (0.02-0.06 range)
   - Acknowledge synthetic vs real performance gap

### Priority 2: Citation Updates
1. Verify Kim & Lee (2025) publication status
2. Verify Liu et al. (2024) volume/page numbers
3. Convert to IEEE numbered reference format

### Priority 3: IEEE Format
1. Add Index Terms after abstract
2. Add Conflict of Interest statement
3. Add Author Contributions section
4. Update journal header

---

## 7. Verification Summary

| Category | Status | Action Required |
|----------|--------|-----------------|
| Citations | ⚠️ 24/27 verified | Verify 3 references |
| Data Integrity | ❌ FAIL | Add real results, revise claims |
| Originality | ✓ PASS | Minor clarifications |
| IEEE Format | ⚠️ PARTIAL | Convert references, add sections |

---

## 8. Next Steps

1. **IMMEDIATE**: Revise Section 10 (Results) to include real CSI300 backtest
2. **REQUIRED**: Update all performance claims to reflect actual evidence
3. **REQUIRED**: Convert references to IEEE format
4. **RECOMMENDED**: Add discussion of synthetic vs real performance gap
5. **RECOMMENDED**: Emphasize excess return over benchmark as key contribution

**Integrity Status:** ⚠️ Conditional Pass - Revision Required
**Recommendation:** Proceed to Stage 3 (Review) after addressing Priority 1 items

---

*Report generated by Academic Research Skills v3.10.0*
*INTEGRITY verification module*
