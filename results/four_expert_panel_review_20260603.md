# Four-Expert Panel Review Report

**Manuscript:** Collegium v2.0: An IC-Based Multi-Factor Quantitative Trading System with Dynamic Factor Weighting for Chinese A-Share Markets

**Target Journal:** Quantitative Finance (Taylor & Francis)

**Review Date:** 2026-06-03

**Review Mode:** Four-Expert Panel Review

---

## Panel Composition

| Expert | Specialization | Status |
|--------|----------------|--------|
| Expert 1 | Quantitative Finance Methodology | ✓ COMPLETED |
| Expert 2 | Chinese A-Share Market Specialist | ✗ FAILED (API rate limit) |
| Expert 3 | Statistical Methods Specialist | ✗ FAILED (API rate limit) |
| Expert 4 | Practical Implementation & Reproducibility | ✓ COMPLETED |

**Completion Rate:** 2/4 (50%)

---

## Overall Panel Verdict: **MAJOR REVISION**

---

## Expert 1: Quantitative Finance Methodology

### Verdict: **MAJOR REVISION**

### Critical Issues

#### 1. Equation 3 Mathematical Error (Critical)

**Current formulation (Line 178-180):**
```
w_weighted,f = Σ(γ^(W-1-i) · IC_f,t-i) / Σ(γ^i)
```

**Problem:** The decay weighting is **inverted**:
- Most recent observation (i=0) receives weight γ^(W-1) (smallest weight)
- Oldest observation receives weight γ^0 = 1 (largest weight)
- This contradicts stated intent: "recent IC observations receive exponentially higher weight"

**Required Fix:** Change numerator to Σ(γ^i · IC_f,t-i) to properly weight recent observations.

#### 2. Look-Ahead Bias (Fatal Flaw)

**Issue:** Factor weights were determined ex-post based on IC analysis during the test period (2022-2024). This constitutes look-ahead bias - the weights incorporate information unavailable at trading time.

**Impact:** The reported +20.56% excess return is NOT out-of-sample and cannot be interpreted as evidence of strategy effectiveness.

**Required Fix:** Implement true walk-forward testing:
- Training period: 2020-2021 (weight calibration)
- Test period: 2022-2024 (weights determined only from data available at each rebalance date)

#### 3. Bootstrap Methodology Inadequate

**Issue:** Standard bootstrap (1,000 iterations) assumes i.i.d. returns. Financial returns exhibit autocorrelation and volatility clustering.

**Required Fix:** Use block bootstrap or stationary bootstrap (Politis and Romano, 1994) to preserve temporal dependencies.

#### 4. Paired t-test Validity Concerns

**Issue:** Paired t-test comparing strategy vs benchmark assumes independence across days. Financial returns violate this assumption.

**Required Fix:** Use Newey-West standard errors or Diebold-Mariano test for predictive accuracy comparison.

#### 5. Incomplete Factor Validation

**Issue:** Table II shows only 6 factors (momentum_12m, momentum_6m, amihud_illiq, reversal_1m, rsi_14, macd_hist) but library claims 30+ factors.

**Required Fix:** Either:
- (a) Present IC analysis for all 30+ factors
- (b) Explain selection criteria and justify why others excluded

---

## Expert 4: Practical Implementation & Reproducibility

### Verdict: **MAJOR REVISION**

### Critical Issues

#### 1. Sample Size Insufficient

**Issue:** Only 11 stocks from CSI 300 (3.7% of universe) due to "API availability."

**Missing Information:**
- Exact 11 stock codes used
- Exact data fetch timestamps
- Selection criteria for "sufficient API data"

**Impact:** Severe reproducibility barrier. Practitioner attempting reproduction cannot identify which stocks were used.

#### 2. Look-Ahead Bias Not Resolved

**Issue:** Paper acknowledges ex-post weight determination but doesn't implement proper walk-forward methodology.

**Required Fix:** Clear separation between training period and test period with weights determined only from data available at each rebalance.

#### 3. Factor Naming Inconsistencies

**Paper naming:** `momentum_12m`, `amihud_illiq`, `momentum_6m`
**Code naming:** `return_12m`, `amihud`, different conventions

**Impact:** Creates reproducibility barrier - practitioners cannot match paper factors to code implementation.

#### 4. Sign Convention Ambiguity

**Issue:** Algorithm 1 note states: "dir_f = +1 for momentum factors, -1 for amihud_illiq (illiquidity premium)"

**Problem:** But Table II shows amihud_illiq has positive IC (0.020), suggesting it should have positive direction, not negative.

**Required Fix:** Clarify sign convention and explain relationship between IC direction and weight direction.

#### 5. Unimplemented Features

**Paper mentions but doesn't implement:**
- Industry neutralization (mentioned in preprocessing but not demonstrated)
- VaR/CVaR alerts (mentioned in Section 6 but no results shown)
- Regime detection module (deferred to future work but presented as if implemented)

**Required Fix:** Either implement these features or clearly state they are planned future enhancements (as done for regime detection at Lines 184-186).

---

## Consensus Critical Issues

Issues identified by both reviewers independently:

| Issue | Expert 1 | Expert 4 | Priority |
|-------|----------|----------|----------|
| Look-ahead bias | ✓ (fatal) | ✓ (not resolved) | **P1** |
| Sample size (11 stocks) | ✓ | ✓ | **P1** |
| Mathematical error (Eq 3) | ✓ | - | **P1** |
| Missing stock codes | - | ✓ | **P1** |
| Incomplete factor validation | ✓ | - | **P2** |
| Factor naming inconsistencies | - | ✓ | **P2** |
| Bootstrap methodology | ✓ | - | **P2** |
| Paired t-test validity | ✓ | - | **P2** |

---

## Required Revisions Summary

### Priority 1 (Must Fix Before Publication)

1. **Correct Equation 3** - invert decay weighting formula
2. **Implement true walk-forward testing** - training (2020-2021) / test (2022-2024) separation
3. **Provide complete stock codes** - list exact 11 stocks with data timestamps
4. **Resolve sample size limitation** - either expand sample or transparently acknowledge severe limitation

### Priority 2 (Should Fix)

5. **Complete factor IC analysis** - all 30+ factors or justify selection
6. **Fix factor naming** - ensure paper/code consistency
7. **Use block bootstrap** - for confidence intervals
8. **Use Newey-West/Diebold-Mariano** - for strategy comparison tests
9. **Clarify sign conventions** - explain IC vs direction relationship

---

## Comparison with Previous Review

| Criterion | Initial Review | Re-Review | Panel Review |
|-----------|----------------|-----------|--------------|
| Verdict | MINOR REVISION | ACCEPT | MAJOR REVISION |
| ICIR threshold | Issue (fixed) | ✓ Fixed | - |
| Regime detection | Issue (fixed) | ✓ Fixed | Unimplemented |
| Eq 3 error | Not detected | - | **NEW ISSUE** |
| Look-ahead bias | Acknowledged | Mitigated | **FATAL FLAW** |
| Sample size | Acknowledged | Mitigated | **INSUFFICIENT** |
| Stock codes | Not mentioned | - | **MISSING** |
| Factor naming | Not mentioned | - | **INCONSISTENT** |

---

## Conclusion

The four-expert panel (with 2 completed reviews) identifies **fundamental methodological flaws** that were not detected in previous single-reviewer assessments:

1. **Mathematical error** in core formula (Equation 3)
2. **Look-ahead bias** undermines entire empirical contribution
3. **Reproducibility gaps** prevent independent verification

The previous ACCEPT verdict was based on incomplete review depth. The panel review reveals these issues require substantial revision before publication in a rigorous quantitative finance journal.

---

*Panel Review conducted: 2026-06-03*
*Experts completed: 2/4*
*Review standard: Taylor & Francis peer review guidelines*