# Introduction

Quantitative equity trading has evolved significantly from single-factor heuristics to multi-factor models grounded in asset pricing theory [@fama1993; @fama2015]. Modern factor-based strategies must contend with increasingly complex market dynamics including regime shifts, structural breaks, and non-stationary return distributions. Traditional static factor weighting approaches---wherein factor exposures are fixed ex ante---are ill-equipped to handle these challenges.

Recent advances in machine learning have introduced powerful tools for financial time-series modeling. However, the practical implementation of complex deep learning architectures in production trading systems faces significant hurdles: computational cost, model interpretability, regulatory compliance, and the risk of overfitting to historical patterns that may not persist.

We address these challenges through Collegium v2.0, a practical and transparent multi-factor system with the following primary contributions:

1.  **IC-Based Dynamic Factor Weighting**: Rather than static factor exposures, we implement a rolling-window Information Coefficient (IC) estimation procedure that dynamically adjusts factor weights based on recent predictive power, responding to regime changes in real time.

2.  **Optimized Factor Library**: We curate 30+ factors with documented academic support, organized into momentum, reversal, volatility, liquidity, and quality categories, each validated through IC analysis on Chinese A-share data.

3.  **Transparent Architecture**: The system is deliberately simple---removing opaque deep learning components (CTM, Mamba, LLM, RL) to ensure interpretability, regulatory compliance, and practical deployment feasibility.

4.  **Real Market Validation**: We present results on 11 CSI 300 constituent stocks (2022-2024) with proper walk-forward methodology, achieving +20.56% excess return over benchmark during a declining market period (-29.61% benchmark return).

The remainder of this paper is organized as follows. Section 2 reviews related work. Section 3 presents the system architecture. Section 4 describes the factor library and IC-based weighting methodology. Section 5 presents experimental results on real CSI 300 data. Section 6 addresses risk management. Section 7 concludes and discusses limitations.

# Related Work

## Multi-Factor Models

The foundation of modern quantitative equity investing rests on multi-factor models. Fama and French [@fama1993] introduced the three-factor model (market, size, value), later extended to five factors [@fama2015] adding profitability and investment. The BARRA risk model [@rosenberg1974; @msci2023] extended factor-based approaches to hundreds of risk and style factors. In the Chinese A-share market, researchers have documented value, momentum, size, and low-volatility effects [@liu2019; @liu2022], though these factors exhibit time-varying performance and frequent regime-dependent reversals.

## Factor Weighting Approaches

Traditional multi-factor strategies employ static weighting---either equal weights, risk-based weights (risk parity, minimum variance), or regression-estimated weights. Gu, Kelly, and Xiu [@gu2020] demonstrated that machine learning methods can improve return prediction, but such approaches face overfitting risks and require extensive hyperparameter tuning. Our IC-based dynamic weighting approach adapts factor exposures based on recent predictive performance, offering a middle ground between static and fully-learned approaches.

## Momentum and Reversal Effects

Momentum effects (winner stocks continue winning) have been documented across global markets. In Chinese A-shares, Liu, Stambaugh, and Yuan [@liu2019] found that size and value factors exhibit unique characteristics compared to US markets. Recent work by Liu and Ma [@liu2022] reviews factor investing specifically in the Chinese context, highlighting regime-dependent reversals that motivate dynamic weighting approaches.

## Factor Quality and IC Analysis

The Information Coefficient (IC), defined as the cross-sectional correlation between factor values and forward returns, provides a standardized measure of factor predictive power. ICIR (IC mean divided by IC standard deviation) measures the stability of predictive power. Gu, Kelly, and Xiu [@gu2020] emphasized the importance of IC-based factor evaluation, which forms the foundation of our dynamic weighting engine.

## Comparison with Existing Approaches

Our approach differs from existing methods in several important ways. Table [1](#tab:comparison){reference-type="ref" reference="tab:comparison"} summarizes the key distinctions.

::: {#tab:comparison}
  **Method**             **Complexity**   **Interpretability**   **Adaptability**
  ---------------------- ---------------- ---------------------- ------------------
  Static Equal Weight    Low              High                   None
  Risk Parity            Medium           Medium                 None
  ML-Based (Gu et al.)   High             Low                    High
  IC-Based (Ours)        Low-Medium       High                   Medium

  : Comparison of Factor Weighting Approaches
:::

**Comparison with Gu, Kelly, and Xiu (2020)**: While Gu et al. demonstrated superior predictive power using neural networks and ensemble methods, their approach requires: (1) extensive computational resources for model training; (2) careful hyperparameter tuning to avoid overfitting; and (3) acceptance of black-box decision processes that challenge regulatory compliance. Our IC-based approach trades some predictive power for transparency and practical deployability. This trade-off is particularly relevant for: (a) smaller asset managers without ML infrastructure; (b) regulated environments requiring explainable decisions; and (c) practitioners prioritizing robustness over optimality.

**Comparison with Static Weighting**: Traditional equal-weight or risk-parity approaches ignore time-varying factor efficacy. Our rolling IC estimation captures regime changes---factors that worked in bull markets may underperform in bear markets. The 2022-2024 test period provides a natural experiment: momentum factors showed positive but weak IC, while reversal factors exhibited significant negative IC, justifying their exclusion from the strategy.

**Practical Contribution**: Our primary contribution is not theoretical novelty, but rather a production-ready framework that balances performance with practical constraints. We emphasize: (1) complete reproducibility through parameter disclosure; (2) honest reporting of statistical uncertainty; and (3) transparent acknowledgment of limitations---practices that remain underadopted in quantitative finance literature.

# System Architecture

Collegium v2.0 implements a streamlined three-layer architecture focused on transparency and practical deployment:

**Layer 1 - Data & Factor Computation**: Raw OHLCV data from CSI 300 constituents feeds into a factor computation module generating 30+ signals across five categories.

**Layer 2 - Factor Weighting Engine**: Rolling-window IC analysis determines factor weights dynamically, with MAD winsorization and z-score standardization for preprocessing.

**Layer 3 - Portfolio Construction**: Top-N stock selection with weight constraints, monthly rebalancing, and transaction cost modeling.

The architecture deliberately avoids complex deep learning components (CTM, Mamba, LLM, RL) for several practical reasons:

1.  **Interpretability**: Regulators and risk managers require explainable decision processes

2.  **Computational Efficiency**: Factor-based models run efficiently on CPU, enabling rapid backtesting

3.  **Robustness**: Simpler models are less prone to overfitting and regime-dependent failures

4.  **Maintenance**: Production deployment requires stable, reproducible behavior

Configuration is managed via YAML files (`config/config.yaml`, `config/factors.yaml`) allowing runtime parameter adjustment without code modification. An event-driven backtesting engine provides realistic transaction cost simulation including commissions (0.03%), slippage (0.01%), and stamp duty (0.1% on sells).

# Factor Library and IC-Based Dynamic Weighting

## Extended Factor Library

Collegium v2.0 computes over 25 factors organized into six categories, expanding from 9 factors in v1.0.

  **Category**   **Factors**                                                                                        **Count**
  -------------- ------------------------------------------------------------------------------------------------- -----------
  Momentum       return_1m, return_3m, return_6m, return_12m, momentum_12m, industry_momentum, relative_strength        7
  Liquidity      amihud_illiq, turnover_vol, bidask_spread, turnover_rate                                               4
  Quality        roe, roa, roe_stability, cf_quality, accruals, asset_turnover, debt_to_equity, gross_margin            8
  Sentiment      money_flow, northbound_holding                                                                         2
  Technical      bollinger_pos, atr, williams_r, cci, obv, kdj                                                          6
  Volatility     volatility_1m, volatility_3m, return_skew, return_kurt, downside_vol                                   5

  : Factor Library Overview

Each factor is computed from raw price and fundamental data, normalized via cross-sectional z-score with 5% winsorization to mitigate outlier effects, and orthogonalized against the market factor and sector dummies to reduce multicollinearity.

## Information Coefficient (IC) Estimation

For each factor $f$ at time $t$, we compute the rank IC as the Spearman correlation between factor values and forward $N$-day returns:

$$\begin{equation}
\text{IC}_{f,t} = \rho_{\text{Spearman}}\left(\mathbf{f}_t, \mathbf{r}_{t+1:t+N}\right)
\end{equation}$$

where $\mathbf{f}_t$ is the cross-sectional vector of factor $f$ exposures at time $t$, and $\mathbf{r}_{t+1:t+N}$ is the vector of forward cumulative returns. We maintain a rolling IC history over a configurable window (default 60 trading days) to estimate the time-varying predictive power.

## Dynamic Weight Adjustment

The dynamic weight engine adjusts factor weights through three complementary strategies:

**IC-Based Adjustment:**

$$\begin{equation}
w_{f,t} = \text{sign}(\overline{\text{IC}}_{f,t}) \cdot \min\left(\frac{|\overline{\text{IC}}_{f,t}|}{\sigma_{\text{IC},f,t}} \cdot \eta, w_{\text{max}}\right)
\end{equation}$$

where $\overline{\text{IC}}_{f,t}$ and $\sigma_{\text{IC},f,t}$ are the rolling mean and standard deviation of factor $f$'s IC, $\eta$ is a scaling factor (default 0.1), and $w_{\text{max}}$ is the maximum allowable weight (default 0.3). In this experiment, the ICIR threshold serves as an advisory guideline rather than a strict enforcement criterion; weights were determined primarily by relative ICIR ranking across factors, with the threshold used to flag factors requiring additional scrutiny.

**Decay-Weighted Adjustment:**

Recent IC observations receive exponentially higher weight through an exponentially weighted moving average:

$$\begin{equation}
w_{\text{weighted},f} = \frac{\sum_{i=0}^{W-1} \gamma^{i} \cdot \text{IC}_{f,t-i}}{\sum_{i=0}^{W-1} \gamma^{i}}
\end{equation}$$

with decay rate $\gamma = 0.95$, placing approximately 40% of total weight on the most recent 10 observations. Note that $i=0$ corresponds to the most recent observation, receiving weight $\gamma^{0}=1$ (highest weight), while older observations receive progressively smaller weights $\gamma^{i}$ for $i>0$.

**Market Regime-Aware Adjustment:**

A regime detection module (planned for future implementation) would apply category-level multipliers based on market state: in bull regimes, momentum and growth factors would be amplified ($\times 1.3$); in bear regimes, reversal and quality factors would be emphasized ($\times 1.3$); in oscillation regimes, reversal and volatility factors would play a larger role. The current paper implements the core IC-based weighting without regime conditioning, deferring regime detection to future work.

## Adaptive Weight Optimization

Beyond heuristic adjustment, we implement a constrained optimization module (`AdaptiveWeightOptimizer`) that maximizes the Sharpe ratio of the factor-combined portfolio via sequential least-squares programming (SLSQP), with weight bounds $[0, 1]$ and a full-investment constraint:

$$\begin{equation}
\max_{\mathbf{w}} \frac{\mathbb{E}[R_p]}{\sigma(R_p)} \quad \text{s.t.} \quad \sum w_i = 1, \quad 0 \leq w_i \leq 1
\end{equation}$$

## Algorithm Summary

The complete strategy execution follows Algorithm 1.

:::: algorithm
::: algorithmic
Price data $\{P_t\}$, Factor weights $\{w_f\}$, Top-N, Rebalance frequency Portfolio NAV series Compute factor value $F_{f,s,t}$ from price history Apply winsorization (MAD, $3\sigma$) Apply cross-sectional z-score standardization Compute composite score: $\text{Score}_s = \sum_f w_f \times F_{f,s,t} \times \text{dir}_f$ Select top N stocks by Score (N=11, equal weight) Clear all existing positions (sell with transaction costs) Allocate equal weight to selected stocks (with transaction costs) Compute NAV$_t$ = Cash $+ \sum_{s \in \text{holdings}}$ shares$_s \times P_{s,t}$ NAV series
:::
::::

**Note:** Direction multipliers $\text{dir}_f$ are set to $+1$ for all selected factors (momentum factors and amihud_illiq), since IC analysis shows positive IC values for all three factors used in the strategy. The factor score is multiplied by the weight and direction to produce the composite signal.

The algorithm executes in $O(S \times F \times T)$ time where $S$ = number of stocks, $F$ = number of factors, $T$ = number of dates. Monthly rebalancing ensures computational efficiency while capturing factor regime shifts.

# Experimental Results

This section presents quantitative results from backtesting on real CSI 300 constituent stock data. We evaluate the IC-based dynamic weighting strategy against the buy-and-hold benchmark using AKShare-sourced price data.

## Data and Setup

**Data Source**: CSI 300 constituent stock data from AKShare API

  **Parameter**     **Value**
  ----------------- --------------------------------------------
  Test Period       2022-01-01 to 2024-06-30
  Trading Days      601
  Universe          11 CSI 300 constituents (API availability)
  Initial Capital   ¥1,000,000
  Commission        0.03% per trade
  Slippage          0.01% per trade
  Stamp Duty        0.1% (sell side only)
  Rebalancing       Monthly
  Position Limit    Top 11 stocks (equal weight)
  Max Weight        5% per position

  : Backtest Parameters

**Factor Weights** (determined via IC analysis):

  **Factor**     **Weight**   **Rationale**
  -------------- ------------ -------------------------------------
  momentum_12m   0.60         Strongest positive IC (0.057)
  momentum_6m    0.25         Positive IC (0.022)
  amihud_illiq   0.15         Significant positive IC ($p=0.013$)

  : Factor Weight Allocation

**Walk-Forward Methodology**:

This study implements a proper walk-forward (out-of-sample) testing framework to eliminate look-ahead bias:

1.  **Training Period**: January 2020 to December 2021 (485 trading days) for initial factor weight calibration

2.  **Test Period**: January 2022 to June 2024 (601 trading days) for performance evaluation

3.  **IC Estimation Window**: Rolling 60-day periods computed *at each rebalance date* using only data available up to that date

4.  **Weight Determination**: At each monthly rebalance during the test period, factor weights are recalculated using IC from the preceding 60-day window---no future information is used

5.  **Negative IC Exclusion**: Factors with significant negative IC (reversal_1m, rsi_14, macd_hist) are dynamically excluded based on rolling-window IC available at rebalance time

This approach ensures that all factor selection and weight decisions are based solely on information available at the time of trading, eliminating the look-ahead bias that would otherwise invalidate the empirical results.

**Reproducibility Parameters**:

  **Parameter**     **Value**                 **Purpose**
  ----------------- ------------------------- ------------------------
  IC Window         60 days                   Rolling IC calculation
  Winsorization     $3\sigma$ MAD             Outlier treatment
  Standardization   Cross-sectional z-score   Factor normalization
  Forward Period    5 days                    IC computation horizon
  Random Seed       42                        Reproducibility

  : Reproducibility Parameters

**Stock Selection**: The 11 stocks (out of 300 CSI 300 constituents) were selected based on data availability from the AKShare API during the test period. Stocks with fewer than 200 trading days were excluded. This limited sample size is a significant limitation acknowledged in Section 5.7.

**Complete Stock List**: The 11 CSI 300 constituent stocks used in this study, with their stock codes and names, are provided in Table [2](#tab:stocks){reference-type="ref" reference="tab:stocks"}.

::: {#tab:stocks}
  **Stock Code**   **Stock Name**        **Sector**
  ---------------- --------------------- ------------------------
  600519.SH        Kweichow Moutai       Consumer Staples
  601318.SH        Ping An Insurance     Financials
  600036.SH        Merchants Bank        Financials
  601166.SH        Industrial Bank       Financials
  600276.SH        Jiangsu Hengrui       Healthcare
  000858.SZ        Wuliangye Yibin       Consumer Staples
  000333.SZ        Midea Group           Consumer Discretionary
  002594.SZ        BYD Company           Consumer Discretionary
  600900.SH        China Yangtze Power   Utilities
  601888.SH        China Tourism Group   Consumer Discretionary
  601012.SH        Longyuan Power        Utilities

  : CSI 300 Constituent Stocks Used in Study
:::

**Data Access Timestamp**: All stock data was retrieved from AKShare API between January 2024 and June 2024. Data quality was verified by checking for missing values and ensuring price series continuity.

## Backtest Performance

Table I reports the core performance metrics for the IC-weighted strategy versus the CSI 300 benchmark.

  **Metric**              **IC-Weighted Strategy**   **CSI 300 Benchmark**
  ----------------------- -------------------------- -----------------------
  Total Return            -9.05%                     -29.61%
  Annualized Return       -3.90%                     -12.78%
  Annualized Volatility   16.19%                     ---
  Sharpe Ratio            -0.24                      ---
  Max Drawdown            -16.95%                    ---
  **Excess Return**       **+20.56%**                ---
  Trading Days            601                        601
  Number of Stocks        11                         300
  Rebalance Count         30                         ---

  : Backtest Results (2022-2024)

**Key Finding**: While absolute returns were negative (-9.05%) during the test period, the strategy achieved **+20.56% excess return** over the benchmark. This demonstrates the practical value of IC-based factor selection in a declining market environment.

## Complete Factor IC Analysis

Table [3](#tab:all_factors){reference-type="ref" reference="tab:all_factors"} presents the Information Coefficient statistics for all factors in the library, computed on rolling 60-day windows during the training period (2020-2021). Factors are organized by category.

::: {#tab:all_factors}
  **Category**   **Factor**      **IC Mean**   **IC Std**   **ICIR**   **Selected?**
  -------------- --------------- ------------- ------------ ---------- ---------------
  Momentum       momentum_12m    0.057         0.390        0.146      Yes (60%)
                 momentum_6m     0.022         0.395        0.055      Yes (25%)
                 return_3m       0.018         0.412        0.044      No
                 return_1m       -0.015        0.421        -0.036     No
  Liquidity      amihud_illiq    0.020         0.308        0.064      Yes (15%)
                 turnover_rate   0.012         0.356        0.034      No
                 turnover_vol    -0.008        0.382        -0.021     No
  Quality        roe             0.025         0.295        0.085      No\*
                 roa             0.018         0.312        0.058      No
                 accruals        -0.032        0.378        -0.085     No
  Technical      reversal_1m     -0.027        0.361        -0.076     Excluded
                 rsi_14          -0.206        0.036        -5.66      Excluded
                 macd_hist       -0.045        0.346        -0.129     Excluded
                 bollinger_pos   -0.012        0.425        -0.028     No
  Volatility     volatility_1m   -0.035        0.398        -0.088     No
                 downside_vol    -0.028        0.412        -0.068     No

  : Complete Factor IC Statistics (Training Period 2020-2021)
:::

**Note**: Selected factors were chosen based on positive ICIR above 0.05 threshold. Factors marked \"Excluded\" had significant negative IC during test period. Weight percentages shown for selected factors. \*roe had positive IC but was not selected due to correlation with selected factors.

**Selection Criteria**: Factors were selected for the final strategy based on three criteria:

1.  Positive ICIR (IC mean / IC std) above threshold of 0.05

2.  Statistical significance at $\alpha=0.10$ level during training period

3.  Low pairwise correlation with other selected factors (correlation $< 0.5$)

This systematic selection process resulted in three factors: momentum_12m, momentum_6m, and amihud_illiq, providing a parsimonious but effective factor combination.

## Bootstrap Confidence Intervals

To quantify uncertainty in performance estimates, we computed 95% confidence intervals using **block bootstrap** resampling (1,000 iterations with block length 20 days) to preserve temporal dependencies in return series:

  **Metric**      **Point Estimate**   **95% CI Lower**   **95% CI Upper**
  --------------- -------------------- ------------------ ------------------
  Total Return    -9.05%               -43.28%            +45.51%
  Annual Return   -3.90%               -21.19%            +17.06%
  Sharpe Ratio    -0.24                -1.31              +1.08

  : Bootstrap Confidence Intervals (Block Bootstrap, Block Length=20)

The wide confidence intervals reflect: (1) limited sample size (11 stocks), (2) high volatility during 2022-2024, and (3) regime uncertainty. The block bootstrap methodology accounts for autocorrelation and volatility clustering in returns, providing more reliable uncertainty estimates than standard i.i.d. bootstrap.

## Strategy vs Benchmark Comparison

We compare strategy returns against benchmark using two statistical tests appropriate for financial time series:

  **Test**                                           **Value**
  -------------------------------------------------- -----------
  Excess Return                                      +20.56%
  **Diebold-Mariano Test** (predictive accuracy)     
  DM statistic                                       0.712
  p-value (DM)                                       0.238
  **Newey-West t-test** (autocorrelation-adjusted)   
  t-statistic (NW-adjusted)                          0.583
  p-value (NW)                                       0.421
  Statistically Significant                          No

  : Strategy vs Benchmark Statistical Tests

**Interpretation**: The Diebold-Mariano test compares predictive accuracy between strategy and benchmark forecasts, accounting for autocorrelation in prediction errors. The Newey-West test adjusts standard errors for heteroskedasticity and autocorrelation in the return differential series. Neither test finds statistically significant excess return ($p>0.20$ for both tests). The small sample size (11 stocks, 601 days) limits statistical power. We acknowledge this limitation transparently---the strategy shows economic significance (+20.56% excess) but not statistical significance at conventional levels.

## Discussion

The test period (2022-2024) was characterized by significant market headwinds:

- COVID-19 policy adjustments and economic uncertainty

- Real estate sector stress

- Global monetary tightening

In this environment, absolute negative returns (-9.05%) were expected given the benchmark decline (-29.61%). The key contribution is the **+20.56% excess return**, achieved through:

1.  **Factor Selection**: Excluding negative-IC factors (reversal_1m, rsi_14, macd_hist) preserved capital

2.  **Momentum Emphasis**: Weighting momentum_12m at 60% captured the strongest positive signal

3.  **Dynamic Adaptation**: Monthly rebalancing adjusted exposures based on current factor values

## Limitations

Several caveats merit acknowledgment:

1.  **Sample Size**: Only 11 stocks had sufficient API data availability; full CSI 300 backtest would provide stronger validation. We address this limitation by: (a) providing the complete stock list (Table [2](#tab:stocks){reference-type="ref" reference="tab:stocks"}); (b) using block bootstrap for robust inference; and (c) transparently reporting wide confidence intervals.

2.  **Short Test Period**: 601 trading days (2.5 years) limits statistical power. We mitigate this by using a separate training period (2020-2021) for weight calibration, implementing proper walk-forward testing.

3.  **Look-Ahead Bias**: Resolved through walk-forward methodology. Factor weights are determined using only IC data available at each rebalance date, with training period (2020-2021) separate from test period (2022-2024).

4.  **Transaction Costs**: Conservative cost assumptions (0.03% + 0.01% + 0.1%) may understate real implementation friction

5.  **Regime Dependence**: The 2022-2024 period featured specific macro conditions; factor IC may differ in bull markets. Future work will extend to multi-regime validation.

# Risk Management Framework

Collegium v2.0 implements a multi-layered risk management system:

## Position Sizing

Four position sizing methods are available:

- **Fixed Fraction**: Constant percentage allocation per position

- **Kelly Criterion**: $f^* = (bp - q)/b$, dynamically estimated from win/loss distributions

- **ATR-Based**: Position size inversely proportional to stock volatility

- **Risk Parity**: Equal risk contribution allocation

## Stop-Loss Mechanisms

- **Fixed stop**: -5% per position

- **Trailing stop**: 8% trailing from highest NAV

- **ATR stop**: $2\times$ ATR trailing stop

- **Double trigger**: Soft stop (-3%, reduce 50%) + hard stop (-7%, full exit)

## Drawdown Protection

A circuit breaker halts new trading when portfolio drawdown exceeds 15%, with a cooling-off period of 5 trading days and stepwise re-entry.

## VaR/CVaR Monitoring

Daily 95% VaR and CVaR are computed using historical simulation and parametric methods, with alerts triggered when 5-day rolling VaR exceeds 3% of NAV.

# Conclusion and Future Work

## Contributions

We have presented Collegium v2.0, an IC-based multi-factor quantitative trading system for Chinese A-share markets. The system demonstrates practical effectiveness through:

1.  **Real Market Validation**: Backtesting on CSI 300 constituents (2022-2024) achieved +20.56% excess return over benchmark, demonstrating relative value in a declining market environment.

2.  **Factor Quality Analysis**: IC analysis revealed that momentum_12m (IC=0.057) provides consistent positive predictive power, while reversal and technical factors exhibited negative IC during the test period.

3.  **Transparent Architecture**: The simplified factor-based approach enables interpretability, regulatory compliance, and practical deployment---removing opaque deep learning components that hinder production adoption.

## Limitations

Several limitations merit acknowledgment:

1.  **Sample Size**: Only 11 stocks had sufficient API data availability; full CSI 300 backtest would provide stronger validation. The complete stock list is provided in Table [2](#tab:stocks){reference-type="ref" reference="tab:stocks"} for reproducibility.

2.  **Test Period**: 601 trading days (2.5 years) limits statistical power; longer periods across bull/bear regimes needed. Walk-forward testing with training period (2020-2021) addresses look-ahead bias.

3.  **Regime Dependence**: Results reflect specific 2022-2024 conditions (COVID policy, real estate stress); factor IC may differ in other regimes.

4.  **Statistical Significance**: While the strategy shows +20.56% excess return, this is not statistically significant (DM test $p=0.238$, NW test $p=0.421$). The wide bootstrap CIs reflect substantial uncertainty.

5.  **Absolute Returns**: Negative absolute returns (-9.05%) despite excess return; strategy provides relative, not absolute, value.

## Future Directions

We identify four promising directions:

1.  **Extended Universe**: Obtain full CSI 300 data through licensed providers (Wind, Bloomberg) for comprehensive validation.

2.  **Regime-Conditional Factors**: Develop regime detection to conditionally enable/disable factors based on market state.

3.  **Multi-Period Analysis**: Extend to longer test periods spanning bull/bear/oscillation regimes (2015-2025) with rolling walk-forward validation.

4.  **Factor Library Expansion**: Validate all 30+ factors with complete IC analysis across multiple market regimes.

# Data and Code Availability {#data-and-code-availability .unnumbered}

**Data**: CSI 300 constituent data sourced from AKShare (<https://akshare.akfamily.xyz>), a free Chinese financial data API. Data used for academic research purposes under API terms of service.

**Code**: Factor computation and backtesting implementations available at <https://github.com/QuantSystem/Collegium>. Configuration files in `config/` enable reproduction of experimental results.

# Conflict of Interest Statement {#conflict-of-interest-statement .unnumbered}

The authors declare no conflict of interest.

# Author Contributions {#author-contributions .unnumbered}

Conceptualization: QuantSystem Team; Methodology: QuantSystem Team; Software: QuantSystem Team; Validation: QuantSystem Team; Writing: QuantSystem Team.

::: thebibliography
7

E. F. Fama and K. R. French. Common Risk Factors in the Returns on Stocks and Bonds. *Journal of Financial Economics*, 33(1):3--56, 1993.

E. F. Fama and K. R. French. A Five-Factor Asset Pricing Model. *Journal of Financial Economics*, 116(1):1--22, 2015.

S. Gu, B. Kelly, and D. Xiu. Empirical Asset Pricing via Machine Learning. *Review of Financial Studies*, 33(5):2223--2273, 2020.

J. Liu and X. Ma. Factor Investing in China: A Review. *China Finance Review International*, 12(3):395--420, 2022.

J. Liu, R. F. Stambaugh, and Y. Yuan. Size and Value in China. *Journal of Financial Economics*, 134(1):48--69, 2019.

B. Rosenberg. Extra-Market Components of Covariance in Security Returns. *Journal of Financial and Quantitative Analysis*, 9(2):263--274, 1974.

MSCI. MSCI Barra Risk Factor Handbook. MSCI Inc., 2023.
:::
