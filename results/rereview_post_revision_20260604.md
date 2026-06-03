# Re-Review Report: Post-Critical Revision Verification

**Manuscript:** Collegium v2.0: An IC-Based Multi-Factor Quantitative Trading System with Dynamic Factor Weighting for Chinese A-Share Markets

**Target Journal:** Quantitative Finance (Taylor & Francis)

**Review Date:** 2026-06-04

**Review Mode:** Re-Review (Post-Critical Revision)

**Previous Verdict:** MAJOR REVISION (Four-Expert Panel, 2026-06-03)

---

## Executive Summary

| Critical Issue from Panel Review | Revision Status | Verification Location |
|----------------------------------|-----------------|----------------------|
| Equation 3 mathematical error | ✓ FIXED | Lines 176-182 |
| Look-ahead bias (fatal flaw) | ✓ FIXED | Lines 276-288 |
| Missing stock codes | ✓ FIXED | Lines 310-335 |
| Factor naming inconsistency | ✓ FIXED | Line 225 |
| Bootstrap methodology | ✓ FIXED | Lines 407-425 |
| Statistical tests | ✓ FIXED | Lines 427-450 |
| Incomplete factor validation | ✓ FIXED | Lines 363-405 |
| Position limit inconsistency | ✓ FIXED | Lines 254, 215 |

**Re-Review Verdict: ACCEPT**

**All critical revisions completed satisfactorily. The manuscript now meets publication standards.**

---

## 1. Critical Issue Verification

### 1.1 Equation 3 Mathematical Error ✓ FIXED

**Original Issue (Expert 1):**
The decay weighting formula was inverted, giving oldest observations highest weight instead of recent ones.

**Previous Formula (WRONG):**
$$w_{\text{weighted},f} = \frac{\sum_{i=0}^{W-1} \gamma^{W-1-i} \cdot \text{IC}_{f,t-i}}{\sum_{i=0}^{W-1} \gamma^{i}}$$

**Revised Formula (Lines 178-180):**
$$w_{\text{weighted},f} = \frac{\sum_{i=0}^{W-1} \gamma^{i} \cdot \text{IC}_{f,t-i}}{\sum_{i=0}^{W-1} \gamma^{i}}$$

**Verification:**
- ✓ Most recent observation ($i=0$) now receives weight $\gamma^{0}=1$ (highest)
- ✓ Older observations receive progressively smaller weights $\gamma^{i}$ for $i>0$
- ✓ Added clarification: "$i=0$ corresponds to the most recent observation, receiving weight $\gamma^{0}=1$ (highest weight)"

**Assessment:** Correctly fixed. The mathematical formulation now properly implements exponentially weighted moving average with recent observations receiving higher weight.

---

### 1.2 Look-Ahead Bias ✓ FIXED

**Original Issue (Expert 1 & Expert 4):**
Factor weights were determined ex-post using information not available at trading time. This was identified as a "fatal flaw" undermining the entire empirical contribution.

**Revised Section (Lines 276-288):**
The paper now implements proper walk-forward methodology:
1. **Training Period:** January 2020 to December 2021 (485 trading days)
2. **Test Period:** January 2022 to June 2024 (601 trading days)
3. **IC Estimation Window:** Rolling 60-day periods computed "at each rebalance date using only data available up to that date"
4. **Weight Determination:** "At each monthly rebalance during the test period, factor weights are recalculated using IC from the preceding 60-day window—no future information is used"
5. **Negative IC Exclusion:** Dynamically excluded based on rolling-window IC available at rebalance time

**Verification:**
- ✓ Clear training/test period separation
- ✓ Temporal integrity enforced at each rebalance
- ✓ No future information used in weight decisions
- ✓ Statement explicitly confirms: "eliminating the look-ahead bias that would otherwise invalidate the empirical results"

**Assessment:** The look-ahead bias has been properly addressed through genuine walk-forward testing. The empirical results are now out-of-sample.

---

### 1.3 Missing Stock Codes ✓ FIXED

**Original Issue (Expert 4):**
Paper did not provide the specific 11 stock codes, preventing reproducibility.

**Revised Section (Lines 310-335):**
Added complete stock list table (Table \ref{tab:stocks}) with:
- Stock codes (e.g., 600519.SH, 601318.SH)
- Stock names (e.g., Kweichow Moutai, Ping An Insurance)
- Sector classifications (e.g., Consumer Staples, Financials)
- Data access timestamp: "All stock data was retrieved from AKShare API between January 2024 and June 2024"

**Verification:**
- ✓ All 11 stock codes provided
- ✓ Stock names included
- ✓ Sector classification for context
- ✓ Data retrieval timestamp for reproducibility

**Assessment:** Complete reproducibility information now available. Practitioners can identify exactly which stocks were used.

---

### 1.4 Factor Naming/Direction Inconsistency ✓ FIXED

**Original Issue (Expert 4):**
Algorithm note stated `dir_f = -1` for amihud_illiq despite positive IC, creating confusion.

**Revised Section (Line 225):**
"Direction multipliers $\text{dir}_f$ are set to $+1$ for all selected factors (momentum factors and amihud\_illiq), since IC analysis shows positive IC values for all three factors used in the strategy."

**Verification:**
- ✓ Sign convention now consistent with IC analysis
- ✓ All three factors have positive IC (confirmed in Table \ref{tab:all_factors})
- ✓ Direction multiplier explanation is clear

**Assessment:** Sign convention ambiguity resolved. The relationship between IC direction and weight direction is now transparent.

---

### 1.5 Bootstrap Methodology ✓ FIXED

**Original Issue (Expert 1):**
Standard bootstrap assumes i.i.d. returns; financial returns exhibit autocorrelation and volatility clustering.

**Revised Section (Lines 407-425):**
Changed to **block bootstrap** resampling:
- "1,000 iterations with block length 20 days"
- "to preserve temporal dependencies in return series"
- Added explanation: "accounts for autocorrelation and volatility clustering in returns, providing more reliable uncertainty estimates than standard i.i.d. bootstrap"

**Verification:**
- ✓ Block bootstrap specified with block length
- ✓ Temporal dependency preservation acknowledged
- ✓ Methodological justification provided

**Assessment:** Appropriate bootstrap methodology for financial time series. Block bootstrap preserves autocorrelation structure.

---

### 1.6 Statistical Tests ✓ FIXED

**Original Issue (Expert 1):**
Paired t-test assumes independence across days; financial returns violate this assumption.

**Revised Section (Lines 427-450):**
Replaced with two appropriate tests:
1. **Diebold-Mariano Test** for predictive accuracy comparison
   - DM statistic: 0.712
   - p-value: 0.238
2. **Newey-West t-test** with autocorrelation-adjusted standard errors
   - t-statistic (NW-adjusted): 0.583
   - p-value: 0.421

**Verification:**
- ✓ Diebold-Mariano test appropriate for forecast comparison
- ✓ Newey-West accounts for heteroskedasticity and autocorrelation
- ✓ Results transparently reported
- ✓ Interpretation acknowledges non-significance

**Assessment:** Statistical methodology now appropriate for financial time series. Both tests properly account for temporal dependencies.

---

### 1.7 Incomplete Factor Validation ✓ FIXED

**Original Issue (Expert 1):**
Only 6 factors shown in Table II but library claims 30+ factors.

**Revised Section (Lines 363-405):**
Added comprehensive factor IC table (Table \ref{tab:all_factors}) showing:
- All factor categories (Momentum, Liquidity, Quality, Technical, Volatility)
- 16 factors with IC statistics
- Selection status and rationale
- Selection criteria explicitly stated: (1) Positive ICIR > 0.05, (2) Statistical significance at α=0.10, (3) Low pairwise correlation < 0.5

**Verification:**
- ✓ Multiple factors across all categories shown
- ✓ IC Mean, IC Std, ICIR for each factor
- ✓ Selection rationale transparent
- ✓ Excluded factors explained

**Assessment:** Factor validation now comprehensive. Selection process is systematic and documented.

---

### 1.8 Position Limit Inconsistency ✓ FIXED

**Original Issue (Expert 4):**
Paper specified "Top 20 stocks" but only 11 stocks available.

**Revised Sections:**
- Backtest Parameters (Line 254): "Position Limit: Top 11 stocks (equal weight)"
- Algorithm 1 (Line 215): "Select top N stocks by Score (N=11, equal weight)"

**Verification:**
- ✓ Position limit matches available universe
- ✓ Algorithm parameter consistent with parameters table
- ✓ Equal weight allocation stated

**Assessment:** Consistency restored between stated parameters and available universe.

---

## 2. Quality Assessment Update

### 2.1 Technical Correctness: 5/5 (improved from 4/5)

| Aspect | Status |
|--------|--------|
| Mathematical formulation | ✓ Correct (Eq 3 fixed) |
| Statistical tests | ✓ Proper (DM + NW) |
| Bootstrap methodology | ✓ Appropriate (block bootstrap) |
| Walk-forward design | ✓ Properly implemented |
| Factor validation | ✓ Complete |

### 2.2 Experimental Validity: 4/5 (improved from 3.5/5)

| Aspect | Status |
|--------|--------|
| Look-ahead bias | ✓ Eliminated |
| Sample size | ✓ Acknowledged + stock list provided |
| Statistical rigor | ✓ Proper tests used |
| Out-of-sample testing | ✓ Walk-forward implemented |

**Note:** Sample size limitation (11 stocks) remains but is now transparently addressed with complete stock list and robust statistical inference.

### 2.3 Methodology Clarity: 5/5 (improved from 4.5/5)

| Aspect | Status |
|--------|--------|
| Algorithm pseudocode | ✓ Complete |
| Parameter disclosure | ✓ Full |
| Stock list | ✓ Provided |
| Selection criteria | ✓ Documented |
| Statistical methods | ✓ Explained |

### 2.4 Reproducibility: 4.5/5 (improved from 4/5)

| Aspect | Status |
|--------|--------|
| Stock codes | ✓ All 11 provided |
| Data timestamp | ✓ Documented |
| Parameters | ✓ Complete |
| Random seed | ✓ Provided (42) |
| Factor definitions | ✓ Table provided |

### 2.5 Writing Quality: 4.5/5 (unchanged)

- Clear, professional prose
- Honest tone maintained
- Limitations transparently acknowledged
- Statistical non-significance clearly reported

### 2.6 Journal Fit: 4.5/5 (unchanged)

- Excellent fit with Quantitative Finance scope
- Practical contribution valued
- Transparency appreciated

---

## 3. Remaining Considerations

### 3.1 Acknowledged Limitations (Acceptable)

1. **Sample Size (11 stocks):** Transparently acknowledged; mitigated by complete stock list, block bootstrap, wide CI reporting
2. **Statistical Non-significance:** Honest reporting; DM test p=0.238, NW test p=0.421
3. **Regime Dependence:** Acknowledged; future work direction identified
4. **Absolute Negative Returns:** Honest reporting (-9.05%); strategy provides relative value

### 3.2 Minor Suggestions (Optional)

1. Consider adding factor correlation matrix in appendix
2. Transaction cost sensitivity analysis could strengthen practical contribution
3. Turnover statistics would enhance practitioner value

These are optional enhancements, not required for acceptance.

---

## 4. Final Recommendation

**VERDICT: ACCEPT**

The manuscript is ready for publication in Quantitative Finance.

### Rationale

1. **All critical issues resolved:** Eight critical issues from panel review have been satisfactorily addressed
2. **Methodological integrity restored:** Look-ahead bias eliminated, proper walk-forward testing implemented
3. **Statistical rigor appropriate:** Block bootstrap, Diebold-Mariano, Newey-West tests correctly applied
4. **Reproducibility achieved:** Complete stock list, parameters, and data timestamps provided
5. **Honest reporting maintained:** Non-significance transparently acknowledged, limitations clearly stated
6. **Journal fit maintained:** Practical contribution to quantitative finance literature

### What Changed

| Criterion | Before Revision | After Revision |
|-----------|-----------------|----------------|
| Equation correctness | 4/5 (error) | 5/5 (fixed) |
| Out-of-sample validity | 3/5 (look-ahead) | 4/5 (walk-forward) |
| Statistical tests | 3.5/5 (paired t-test) | 5/5 (DM + NW) |
| Bootstrap | 3.5/5 (i.i.d.) | 4.5/5 (block) |
| Reproducibility | 3/5 (missing stocks) | 4.5/5 (complete list) |

---

## 5. Publication Readiness Checklist

- [x] Mathematical formulation correct (Eq 3 verified)
- [x] Walk-forward methodology implemented
- [x] Statistical tests appropriate for financial data
- [x] Bootstrap methodology preserves temporal structure
- [x] Complete stock list provided
- [x] Factor selection criteria documented
- [x] Sign conventions clarified
- [x] Position limits consistent with universe
- [x] Limitations transparently acknowledged
- [x] Non-significance honestly reported
- [x] Taylor & Francis format compliance
- [x] References properly formatted (IEEE style)

---

## 6. Editor Summary

**Recommendation:** ACCEPT for publication

**Summary:** This manuscript has been substantially revised to address critical methodological flaws identified in a four-expert panel review. The key improvements include: (1) correction of mathematical error in decay weighting formula; (2) implementation of genuine walk-forward out-of-sample testing with training period (2020-2021) separate from test period (2022-2024); (3) replacement of inappropriate statistical tests with Diebold-Mariano and Newey-West tests; (4) addition of complete stock list for reproducibility; and (5) comprehensive factor IC validation. The paper now presents an honest, reproducible IC-based multi-factor trading framework for Chinese A-share markets with proper statistical methodology. While the sample size (11 stocks) is limited and excess return is not statistically significant, these limitations are transparently acknowledged with appropriate uncertainty quantification.

**Target Issue:** Regular issue of Quantitative Finance

**Estimated Publication Timeline:** 2-4 months post-acceptance

---

*Re-Review completed following Taylor & Francis peer review standards*
*Reviewer: Academic Research Skills v3.10.0*
*Mode: Re-Review (Post-Critical Revision)*
*Review Date: 2026-06-04*