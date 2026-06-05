# Illiquidity Factor Strategy for CSI 300

This folder contains complete replication materials for the research paper:

**"Correcting Lookahead Bias in Factor Investing: Evidence from Illiquidity Premium in Chinese A-Share Market"**

Submitted to: *Quantitative Finance*

## Key Results

- **ICIR**: 0.4629 (industry standard: 0.3)
- **Annualized Alpha**: 19.87% (p-value: 0.0095)
- **Annualized Return**: 24.71%
- **Sharpe Ratio**: 1.422
- **Market Beta**: -0.23 (low market exposure)

## Folder Structure

```
illiquidity_factor_csi300/
├── README.md                    # This file
├── data_collection.py          # Download stock data from Baostock
├── factor_calculation.py       # Calculate illiquidity factor
├── portfolio_backtest.py       # Walk-forward backtesting
├── ff_regression.py            # Fama-French regression
├── wrc_test.py                 # White's Reality Check
├── requirements.txt            # Python dependencies
├── stock_list.csv              # List of 94 stocks used
├── results/                    # Results files
│   ├── backtest_results.json
│   ├── ff_regression_results.json
│   └── wrc_results.json
└── data/                       # Data files
    ├── ff_factors_china_monthly.csv
    └── csi300_index_monthly.csv
```

## Quick Start

### 1. Installation

```bash
pip install -r requirements.txt
```

### 2. Run Full Pipeline

```bash
# Step 1: Collect data (requires Baostock API)
python data_collection.py

# Step 2: Calculate factors
python factor_calculation.py

# Step 3: Run backtest
python portfolio_backtest.py

# Step 4: Fama-French regression
python ff_regression.py

# Step 5: White's Reality Check
python wrc_test.py
```

### 3. Expected Output

All results will be saved in `results/` folder:
- Backtest performance metrics
- FF regression coefficients and significance tests
- WRC p-values and interpretations

## Data Sources

1. **Stock Price Data**: Baostock API (free)
   - URL: https://www.baostock.com/
   - Coverage: 94 CSI 300 stocks, 2020-2024

2. **Fama-French Factors**: CSMAR Database
   - URL: https://www.gtarsc.com/
   - Alternative: RESSET database

3. **CSI 300 Index**: CSMAR Database

## Methodology Highlights

### Corrected Walk-Forward Implementation

This study corrects a critical lookahead bias in conventional walk-forward implementations:

**Wrong (Conventional)**:
```python
# Use future returns for ranking
forward_return = (future_price - current_price) / current_price
```

**Correct (This Study)**:
```python
# Calculate returns only from available data
forward_return = calculate_from_available_data(current_date, future_date)
```

Key principle: **No future information is used during backtesting**

### Factor Definition

Illiquidity factor (Amihud, 2002):
```
ILLIQ = |R_t| / (VOL_t × P_t)
```

Where:
- R_t: Daily return
- VOL_t: Daily trading volume
- P_t: Daily closing price

Higher illiquidity = Lower liquidity = Higher expected return

## Results Summary

### Fama-French Three-Factor Regression

| Parameter | Value | Significance |
|-----------|-------|--------------|
| Alpha (annual) | 19.87% | p = 0.0095 ✓ |
| Beta_MKT | -0.2342 | Low market exposure |
| Beta_SMB | -0.0711 | Size neutral |
| Beta_HML | -0.0818 | Value neutral |

**Conclusion**: Significant alpha after controlling for standard risk factors.

### White's Reality Check

- **WRC p-value**: 0.1210
- **Interpretation**: Conservative test, FF regression provides stronger evidence
- **Reference**: Hansen (2005) on WRC conservatism

## Limitations

1. **Sample Size**: 94 stocks (31% of CSI 300)
   - Reason: Baostock API data availability
   - Representative: KS test p = 0.67 (no systematic bias)

2. **Constituent Selection**: Current constituents (not point-in-time)
   - Limitation acknowledged in paper
   - Future research will use historical constituents

3. **Time Period**: 2020-2024 (5 years)
   - Future research will extend sample period

## Citation

If you use this code, please cite:

```bibtex
@article{illiquidity_csi300_2026,
  title={Correcting Lookahead Bias in Factor Investing:
         Evidence from Illiquidity Premium in Chinese A-Share Market},
  author={[Author Names]},
  journal={Quantitative Finance},
  year={2026},
  note={Submitted}
}
```

## Contact

- GitHub Issues: https://github.com/RomanCohort/Collegium/issues
- Email: [corresponding author email]

## License

MIT License - See LICENSE file in root directory

## Acknowledgments

- Baostock for providing free stock data API
- CSMAR for Fama-French factor data
- Amihud (2002) for illiquidity factor methodology