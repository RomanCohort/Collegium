# Academic Paper Review Report

**Manuscript:** Collegium v2.0: An IC-Based Multi-Factor Quantitative Trading System with Dynamic Factor Weighting for Chinese A-Share Markets

**Target Journal:** Quantitative Finance (Taylor & Francis)

**Review Date:** 2026-06-03

**Review Mode:** Full Academic Review

---

## Executive Summary

| Criterion | Score (1-5) | Verdict |
|-----------|-------------|---------|
| Technical Correctness | 4 | ACCEPT with minor revisions |
| Experimental Validity | 3.5 | Minor revision needed |
| Methodology Clarity | 4.5 | ACCEPT |
| Literature Coverage | 4.5 | ACCEPT |
| Writing Quality | 4.5 | ACCEPT |
| Journal Fit | 4.5 | ACCEPT |
| Reproducibility | 4 | ACCEPT with minor revisions |

**Overall Recommendation:** ACCEPT with minor revisions

---

## 1. Technical Correctness

### 1.1 Strengths

**Mathematical Formulation**
- IC estimation formula (Eq. 1) correctly uses Spearman correlation
- Dynamic weight adjustment (Eq. 2) is mathematically sound
- Decay-weighted adjustment properly formulated
- Constrained optimization formulation correct

**Statistical Analysis**
- Bootstrap confidence intervals correctly computed
- Paired t-test appropriate for strategy vs benchmark comparison
- Significance tests for IC properly executed
- 95% CI interpretation correct

**Algorithm Design**
- Algorithm 1 is clear and implementable
- Time complexity analysis O(S × F × T) is correct
- Factor preprocessing (winsorization, z-score) follows best practices

### 1.2 Minor Issues

**Issue 1: ICIR Threshold Not Demonstrated**
- Section 4.3 mentions ICIR threshold of 0.5 as advisory
- Table II shows momentum_12m ICIR=0.146, well below threshold
- Authors should clarify whether threshold was actually applied

**Recommendation:** Add sentence: "In this experiment, the ICIR threshold was not strictly enforced; rather, relative ICIR ranking determined weights."

**Issue 2: Regime Detection Not Implemented**
- Section 4.3 describes regime-aware multipliers
- No evidence in experiments that regime detection was used
- Section 6 mentions it conceptually but shows no results

**Recommendation:** Either (a) remove regime-aware claims from this paper, or (b) add a brief note in Section 5 that regime detection is planned for future work and not implemented in current experiments.

### 1.3 Technical Rating: 4/5

Fundamentally sound with minor inconsistencies requiring clarification.

---

## 2. Experimental Validity

### 2.1 Strengths

**Real Market Data**
- Uses actual CSI 300 constituent stocks
- Test period (2022-2024) covers challenging market conditions
- AKShare API is legitimate data source

**Honest Reporting**
- Negative absolute returns (-9.05%) acknowledged
- Excess return (+20.56%) reported transparently
- Statistical non-significance (p=0.464) clearly stated
- Multiple limitations explicitly acknowledged

**Statistical Rigor**
- Bootstrap confidence intervals quantify uncertainty
- Significance tests for all factor IC estimates
- Paired t-test for strategy comparison
- Wide CIs honestly interpreted as reflecting small sample

### 2.2 Critical Issues

**Issue 1: Sample Size (ACKNOWLEDGED)**

The sample of 11 stocks is acknowledged as a limitation in multiple sections (5.1, 5.7, 7.2). The authors have addressed this appropriately through:
- Transparent acknowledgment
- Bootstrap CIs to quantify uncertainty
- Honest interpretation of non-significance
- Future work suggestions for expanded validation

**Verdict:** Adequately mitigated through transparent disclosure.

**Issue 2: Look-Ahead Bias (ACKNOWLEDGED)**

Factor weights were determined ex-post. The authors acknowledge this in:
- Section 5.1: "We acknowledge that weights were determined ex-post"
- Section 5.7: Listed as limitation
- Section 7.3: Future work includes "Out-of-Sample Testing"

**Verdict:** Adequately disclosed. This is common in exploratory research.

### 2.3 Experimental Validity Rating: 3.5/5

Valid methodology with acknowledged limitations. Not ideal but acceptable for an applied/practical contribution paper.

---

## 3. Methodology Clarity

### 3.1 Strengths

**Clear Architecture**
- Three-layer design is well-described
- Rationale for removing DL components is sound
- Configuration management explained

**Detailed Algorithm**
- Algorithm 1 provides complete pseudocode
- Input/output clearly specified
- Implementation details included

**Parameter Disclosure**
- Table of backtest parameters
- Table of reproducibility parameters
- Factor weight rationale explained

**Comparison Section Added**
- New Section 2.5 compares with existing approaches
- Table comparing complexity, interpretability, adaptability
- Clear positioning relative to Gu et al. (2020)

### 3.2 Minor Suggestions

**Suggestion 1: Factor Formulas**
Consider adding an appendix with explicit formulas for:
- amihud_illiq calculation
- momentum_12m vs simple 12m return
- Quality factor definitions

This would improve reproducibility further.

**Suggestion 2: Transaction Cost Sensitivity**
Section 5.7 mentions conservative cost assumptions. Consider adding a brief sensitivity analysis showing performance under different cost scenarios (e.g., 0.01%, 0.05%, 0.1%).

### 3.3 Methodology Clarity Rating: 4.5/5

Excellent clarity overall. Minor additions would strengthen further.

---

## 4. Literature Coverage

### 4.1 Strengths

**Core Citations**
- Fama-French factor models [1, 2] properly cited
- Gu, Kelly, Xiu [3] appropriately referenced
- Chinese A-share research [4, 5] included
- BARRA/MSCI risk models [6, 7] referenced

**New Comparison Section**
- Section 2.5 provides excellent positioning
- Clear differentiation from ML approaches
- Honest acknowledgment of practical vs theoretical contribution

**Appropriate Scope**
- 7 references, all cited in text
- No orphan references
- Focused on relevant literature

### 4.2 Minor Suggestions

**Suggestion: Additional Chinese Market Citations**
Consider adding:
- Xiong and Yu (2011) on Chinese momentum
- Recent work on A-share factor timing

This would strengthen the Chinese market context.

### 4.3 Literature Coverage Rating: 4.5/5

Comprehensive and well-positioned. Minor additions possible but not required.

---

## 5. Writing Quality

### 5.1 Strengths

**Clear Structure**
- Logical flow from introduction to conclusion
- Section numbering appropriate
- Tables well-formatted

**Honest and Professional Tone**
- Limitations acknowledged throughout
- No overclaiming
- Appropriate hedging language ("suggests", "indicates", "may")

**Abstract Quality**
- Concise but informative
- Key contributions clearly listed
- Main results reported with appropriate context

### 5.2 Minor Issues

**Issue: Table Numbering**
Tables are numbered but captions could be more descriptive. Consider:
- "Table I: Backtest Performance Metrics (2022-2024)"
- "Table II: Factor IC Statistics with Significance Tests"

Current captions are functional but could be more informative.

### 5.3 Writing Quality Rating: 4.5/5

Excellent academic writing. Minor polish possible.

---

## 6. Journal Fit

### 6.1 Alignment with Quantitative Finance

| Scope Area | Coverage | Fit |
|------------|----------|-----|
| Portfolio optimization | ✓ | Excellent |
| Risk management | ✓ | Good |
| Factor-based methods | ✓ | Core focus |
| Chinese markets | ✓ | Valuable contribution |
| Algorithmic trading | ✓ | Excellent |
| Empirical study | ✓ | Solid |

**Fit Assessment:** Excellent fit with Quantitative Finance scope.

### 6.2 Contribution Level

| Contribution Type | Level |
|------------------|-------|
| Theoretical novelty | Moderate |
| Practical applicability | High |
| Empirical evidence | Moderate (limited sample) |
| Reproducibility | High |
| Transparency | High |

**Assessment:** Appropriate for Quantitative Finance. The journal values practical contributions and transparent methodology, which this paper delivers well.

### 6.3 Journal Fit Rating: 4.5/5

Strong fit with journal scope and values.

---

## 7. Reproducibility

### 7.1 Strengths

**Parameter Disclosure**
- All backtest parameters specified
- Reproducibility parameters table
- Random seed (42) provided
- IC window, winsorization threshold stated

**Code Availability**
- GitHub repository mentioned
- Configuration files referenced

**Data Source**
- AKShare API specified with URL
- Selection criteria for stocks explained

### 7.2 Minor Suggestions

**Suggestion 1: Stock List**
Consider providing the 11 stock codes used, either in paper or supplementary material.

**Suggestion 2: Time Period Specification**
Provide exact start/end dates for each stock's data availability to enable precise reproduction.

### 7.3 Reproducibility Rating: 4/5

Good reproducibility. Minor additions would make it excellent.

---

## 8. Detailed Recommendations

### 8.1 Required Revisions (Minor)

1. **Clarify ICIR threshold application** (Section 4.3)
   - Add one sentence explaining whether threshold was enforced or advisory

2. **Address regime-aware claims** (Section 4.3 or 5)
   - Either remove claim or note as "planned future enhancement"

### 8.2 Optional Enhancements

1. **Add factor formulas appendix** (if space permits)
2. **Stock list in supplementary material**
3. **Transaction cost sensitivity analysis**

---

## 9. Decision

**Recommendation: ACCEPT with minor revisions**

### Rationale

The manuscript presents a well-executed, honest, and practically valuable contribution to multi-factor quantitative trading. While the sample size is limited, the authors have:

1. Transparently acknowledged all limitations
2. Provided statistical uncertainty quantification
3. Positioned the work appropriately relative to existing methods
4. Delivered a reproducible, deployable framework

The paper fits Quantitative Finance's emphasis on practical applicability and transparent methodology. The theoretical contribution is moderate but the practical contribution is substantial.

### Revision Requirements

- Two minor clarifications (ICIR threshold, regime detection)
- Can be addressed in 1-2 paragraphs
- Estimated revision time: 1 hour

---

## 10. Revision Checklist for Authors

- [ ] Clarify ICIR threshold application status (Section 4.3)
- [ ] Address regime-aware adjustment claims (remove or defer to future work)
- [ ] (Optional) Add stock list to supplementary material
- [ ] (Optional) Consider more descriptive table captions

---

## 11. Reviewer Confidence

| Aspect | Confidence |
|--------|------------|
| Technical assessment | High |
| Statistical assessment | High |
| Literature assessment | Medium-High |
| Reproducibility assessment | Medium |

---

*Review completed following Taylor & Francis peer review standards*
*Reviewer: Academic Research Skills v3.10.0*
*Mode: Full Academic Review*
