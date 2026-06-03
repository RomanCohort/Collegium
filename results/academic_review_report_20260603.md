# Academic Paper Review Report

**Manuscript:** Collegium v2.0: An IC-Based Multi-Factor Quantitative Trading System with Dynamic Factor Weighting for Chinese A-Share Markets

**Target Journal:** IEEE Access

**Review Date:** 2026-06-03

**Review Mode:** Full Academic Review

---

## Executive Summary

| Criterion | Score (1-5) | Verdict |
|-----------|-------------|---------|
| Technical Correctness | 4 | ACCEPT with minor revisions |
| Experimental Validity | 3 | MAJOR REVISION needed |
| Methodology Clarity | 4 | ACCEPT with minor revisions |
| Literature Coverage | 4 | ACCEPT |
| Writing Quality | 4 | ACCEPT with minor revisions |
| IEEE Format Compliance | 5 | ACCEPT |
| Reproducibility | 3 | MAJOR REVISION needed |

**Overall Recommendation:** MAJOR REVISION required before acceptance

---

## 1. Technical Correctness

### 1.1 Strengths

**Mathematical Formulation (Section 4)**
- IC estimation formula (Eq. 1) is correctly defined using Spearman correlation
- Dynamic weight adjustment formula (Eq. 2) is mathematically sound
- Decay-weighted adjustment formulation is appropriate

**Factor Library Design**
- 30+ factors across 6 categories is comprehensive
- Factor categories align with academic literature (momentum, liquidity, quality, etc.)
- Preprocessing pipeline (winsorization, z-score standardization) is standard practice

### 1.2 Issues Identified

**Issue 1: ICIR Threshold Inconsistency**
- Section 4.3 states ICIR threshold of 0.5 for weight reduction
- Table II shows momentum_12m ICIR=0.146, momentum_6m ICIR=0.055
- Neither factor meets the 0.5 threshold, yet both receive positive weights
- **Recommendation:** Clarify how ICIR threshold is actually applied, or revise the threshold value

**Issue 2: Regime-Aware Adjustment Not Demonstrated**
- Section 4.3 describes regime-aware multipliers (bull/bear/oscillation)
- Section 5 experiments do not show regime detection results
- No evidence this mechanism was actually used
- **Recommendation:** Either demonstrate regime detection in experiments, or remove this claim

**Issue 3: Amihud Illiquidity Direction**
- Table I shows amihud_illiq with "Negative (illiquidity premium)" direction
- The standard Amihud illiquidity factor should have positive IC if illiquidity premium exists
- The IC=0.020 positive suggests higher illiquidity → higher returns
- **Recommendation:** Clarify the sign convention and factor construction

### 1.3 Technical Rating: 4/5

The methodology is fundamentally sound, but inconsistencies between described mechanisms and experimental implementation need clarification.

---

## 2. Experimental Validity

### 2.1 Strengths

**Real Market Data**
- Uses actual CSI 300 constituent stocks (not simulated)
- Test period (2022-2024) covers challenging market conditions
- Excess return of +20.56% over benchmark is notable

**Honest Reporting**
- Negative absolute returns (-9.05%) acknowledged
- Limitations section clearly addresses sample size and test period issues
- No overclaiming of unrealistic performance

### 2.2 Critical Issues

**Issue 1: Sample Size Inadequate (CRITICAL)**
- Only 11 stocks tested out of CSI 300 universe
- This represents only 3.7% of the intended universe
- Statistical significance of IC estimates is questionable
- **Recommendation:** This is the most critical issue. Options:
  - (a) Obtain full CSI 300 data from licensed provider (Bloomberg, Wind, etc.)
  - (b) Frame as pilot study and clearly acknowledge limitation
  - (c) Use alternative free data sources (Tushare Pro, Baostock with retry)

**Issue 2: Look-Ahead Bias in Factor Weight Determination**
- Factor weights (momentum_12m=0.6, momentum_6m=0.25, amihud=0.15) were determined ex-post
- True out-of-sample testing requires weight determination before the test period
- Section 5.5 acknowledges this, but it remains a validity concern
- **Recommendation:** Implement walk-forward optimization:
  - Train window: 2020-2021
  - Test window: 2022-2024
  - Rolling weight updates

**Issue 3: Missing Statistical Significance Tests**
- No t-statistics, p-values, or confidence intervals for IC estimates
- No statistical test comparing strategy vs benchmark
- ICIR values reported but no significance assessment
- **Recommendation:** Add statistical tests:
  - IC significance: t-test against null IC=0
  - Strategy vs benchmark: paired t-test on daily returns
  - Confidence intervals for performance metrics

**Issue 4: Benchmark Comparison Methodology**
- Strategy holds only 11 stocks; benchmark is CSI 300 (300 stocks)
- Not a fair comparison due to different risk profiles
- **Recommendation:** Compare against:
  - Equal-weighted 11-stock portfolio
  - Random 11-stock selection baseline
  - CSI 300 adjusted for comparable concentration

### 2.3 Experimental Validity Rating: 3/5

The experimental framework has fundamental limitations that undermine the validity of conclusions. Major revision with expanded dataset and proper statistical testing is required.

---

## 3. Methodology Clarity

### 3.1 Strengths

**Clear Architecture Description**
- Three-layer architecture is well-described
- Rationale for removing deep learning components is reasonable
- Figure would help (currently missing)

**Detailed Factor Specification**
- Factor categories and examples clearly listed
- IC formula with mathematical notation provided
- Weight adjustment mechanisms described

### 3.2 Issues

**Issue 1: Missing Algorithm Pseudocode**
- No pseudocode for the complete strategy execution
- Difficult to understand exact order of operations
- **Recommendation:** Add Algorithm 1: IC-Weighted Factor Strategy

**Issue 2: Factor Computation Details**
- Exact formulas for each factor not provided
- amihud_illiq construction details vague
- **Recommendation:** Add appendix with factor formulas

**Issue 3: Portfolio Construction Method**
- "Top-N stock selection" mentioned but exact method unclear
- How are factor values combined into composite score?
- **Recommendation:** Specify:
  - Composite score formula
  - Weight application method
  - Rebalancing trigger conditions

### 3.3 Methodology Clarity Rating: 4/5

Generally clear, but additional algorithmic details would improve reproducibility.

---

## 4. Literature Coverage

### 4.1 Strengths

**Relevant Citations**
- Fama-French factor models [4], [5] appropriately cited
- Chinese A-share research [14], [15] included
- IC analysis methodology [8] referenced

**Appropriate Scope**
- Related work section focused on relevant topics
- Not over-citing tangential deep learning literature

### 4.2 Issues

**Issue 1: Missing Recent IC-Based Weighting Literature**
- No citation to recent IC-based dynamic weighting papers
- Literature on factor timing/IC timing should be included
- **Recommendation:** Add citations:
  - Green, Hand, Zhang (2017) on factor characteristics
  - Arnott et al. on factor timing

**Issue 2: Chinese A-Share Factor Literature Incomplete**
- Only [14], [15] cover Chinese market
- Missing relevant papers on A-share momentum/liquidity effects
- **Recommendation:** Add:
  - Xiong and Yu (2011) on Chinese momentum
  - Carpenter, Whitelaw (2017) on Chinese stock market

**Issue 3: Some References Unused in Text**
- References [3], [6], [7], [9]-[13], [16], [17], [19], [20], [22]-[26] appear in reference list but not cited in text
- This suggests removed content (CTM, Mamba, LLM, RL sections) left orphan references
- **Recommendation:** Remove unused references or add citations

### 4.3 Literature Coverage Rating: 4/5

Core literature is covered, but orphan references need cleanup and additional Chinese market citations would strengthen the paper.

---

## 5. Writing Quality

### 5.1 Strengths

**Clear Structure**
- Logical flow from introduction to conclusion
- Section numbering appropriate
- Tables well-formatted

**Honest Tone**
- Limitations acknowledged
- No overclaiming
- Appropriate hedging language

### 5.2 Issues

**Issue 1: Abstract Too Technical**
- Abstract contains many specific numbers (-9.05%, +20.56%, IC=0.057)
- Should focus on contribution and high-level findings
- **Recommendation:** Simplify abstract to emphasize contribution

**Issue 2: Index Terms Too Long**
- 8 terms is excessive for IEEE Access
- **Recommendation:** Reduce to 4-5 key terms

**Issue 3: Typos and Minor Errors**
- Line 67: "CTM, Mamba, LLM, RL" mentioned but these components removed
- Section 4.1: "over 25 factors" vs "30+ factors" inconsistency
- **Recommendation:** Proofread and ensure consistency

### 5.3 Writing Quality Rating: 4/5

Writing is clear overall with minor issues requiring attention.

---

## 6. IEEE Access Format Compliance

### 6.1 Compliance Check

| Requirement | Status | Notes |
|-------------|--------|-------|
| Title page | ✓ | Author, Journal, Date present |
| Abstract | ✓ | Present with Index Terms |
| Index Terms | ✓ | Present (reduce count) |
| Section numbering | ✓ | Correct format |
| Figure/Table numbering | ✓ | Tables I, II correct |
| Reference format | ✓ | IEEE [1]-[27] format |
| Conflict of Interest | ✓ | Present |
| Author Contributions | ✓ | Present |
| Data Availability | ✓ | Present |

### 6.2 IEEE Format Rating: 5/5

Fully compliant with IEEE Access requirements.

---

## 7. Reproducibility

### 7.1 Issues

**Issue 1: Data Source Limitation**
- AKShare API mentioned but specific function calls not provided
- 11 stocks selected but selection criteria unclear
- **Recommendation:** Provide:
  - List of 11 stock codes used
  - AKShare function names
  - Date range of successful data retrieval

**Issue 2: Parameter Values Not Fully Specified**
- Rolling IC window: stated as 60 days (default)
- Decay rate γ: stated as 0.95
- Scaling factor η: stated as 0.1
- But actual values used in experiments unclear
- **Recommendation:** Add table of all hyperparameters used

**Issue 3: Code Repository**
- GitHub link provided but repository may not be public
- No specific commit/version referenced
- **Recommendation:** Ensure repository is public with clear README

**Issue 4: Random Seed**
- No mention of random seed for reproducibility
- **Recommendation:** Specify seed used and provide deterministic code

### 7.2 Reproducibility Rating: 3/5

Insufficient detail for independent reproduction of results.

---

## 8. Detailed Recommendations

### 8.1 Major Revisions Required

1. **Expand Dataset (CRITICAL)**
   - Obtain at least 50-100 CSI 300 stocks
   - If impossible, frame clearly as pilot study with limitations
   - Consider alternative data sources (Tushare Pro free tier offers more)

2. **Implement Proper Out-of-Sample Testing**
   - Use 2020-2021 data for factor weight determination
   - Test on 2022-2024 data with those weights
   - Or use rolling walk-forward optimization

3. **Add Statistical Significance Tests**
   - t-tests for IC significance
   - Bootstrap confidence intervals for performance metrics
   - Diebold-Mariano test for strategy vs benchmark

4. **Provide Full Reproducibility Package**
   - List of 11 stock codes with selection criteria
   - All hyperparameter values
   - Random seed
   - Complete code in public repository

### 8.2 Minor Revisions

1. Remove orphan references [3], [6], [7], [9]-[13], [16], [17], [19], [20], [22]-[26] or add citations
2. Clarify ICIR threshold application in Section 4.3
3. Remove or demonstrate regime-aware adjustment mechanism
4. Reduce Index Terms to 4-5 key terms
5. Add pseudocode for strategy execution
6. Improve benchmark comparison methodology

---

## 9. Decision

**Recommendation: MAJOR REVISION**

The paper presents a sound methodology with honest reporting, but the experimental validation has fundamental limitations:

1. Sample size (11 stocks) is inadequate for strong conclusions
2. Look-ahead bias in factor weight determination
3. Missing statistical significance tests
4. Insufficient reproducibility details

After addressing these issues, the paper could be suitable for IEEE Access publication.

---

## 10. Revision Checklist for Authors

- [ ] Expand dataset to 50+ stocks OR clearly frame as pilot study
- [ ] Implement walk-forward out-of-sample testing
- [ ] Add statistical significance tests with p-values
- [ ] Provide complete reproducibility details (stock list, parameters, code)
- [ ] Remove orphan references or add citations
- [ ] Clarify ICIR threshold application
- [ ] Add algorithm pseudocode
- [ ] Improve benchmark comparison methodology

---

*Review conducted following IEEE Access peer review standards*
*Reviewer: Academic Research Skills v3.10.0*
