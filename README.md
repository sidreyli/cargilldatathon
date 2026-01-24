# 🚢 Cargill Ocean Transportation Datathon 2026
## Freight Calculator & Portfolio Optimizer

---

## Overview

This solution provides a comprehensive freight calculator and portfolio optimization system for Cargill's Capesize vessel fleet. It determines optimal vessel-cargo assignments to maximize profit while respecting laycan constraints.

## Key Features

- **Freight Calculator**: Calculates voyage economics including TCE, fuel costs, port costs, and profit
- **Portfolio Optimizer**: Finds optimal vessel-cargo assignments using brute-force optimization
- **Scenario Analysis**: Identifies tipping points for bunker prices and port delays
- **Market Vessel Analysis**: Evaluates third-party vessels for unassigned cargoes

## Files Structure

```
cargill_datathon/
├── freight_calculator.py      # Core freight calculation engine
├── portfolio_optimizer.py     # Portfolio optimization & scenario analysis
├── datathon_analysis.ipynb    # Jupyter notebook with full analysis
├── Port_Distances.csv         # Port-to-port distance data
├── Simple_calculator.xlsx     # Reference Excel calculator
└── README.md                  # This file
```

## Installation

```bash
# Required Python packages
pip install pandas numpy matplotlib seaborn jupyter
```

## Quick Start

### Run the Freight Calculator
```bash
python freight_calculator.py
```

### Run Portfolio Optimization
```bash
python portfolio_optimizer.py
```

### Open Jupyter Notebook
```bash
jupyter notebook datathon_analysis.ipynb
```

## Key Results

### Optimal Assignments (Cargill Vessels)

| Vessel | Cargo | TCE ($/day) | Net Profit |
|--------|-------|-------------|------------|
| OCEAN HORIZON | EGA Bauxite (Guinea-China) | $30,879 | $1,265,746 |
| ANN BELL | CSN Iron Ore (Brazil-China) | $23,390 | $1,018,508 |

**Total Portfolio Profit: $2,284,255**

### Critical Insight

Only 2 of 4 Cargill vessels (ANN BELL and OCEAN HORIZON) can make any of the cargo laycans due to their current positions. The BHP Iron Ore cargo requires a market vessel.

### Scenario Analysis Findings

1. **Bunker Price Sensitivity**: Recommendation changes only if bunker prices increase >82%
2. **Port Delay Impact**: ~$30,000 profit loss per day of delay, but assignments remain stable

## Methodology

### TCE Calculation
```
TCE = (Net Freight - Voyage Costs) / Total Voyage Days

Where:
- Net Freight = Gross Freight × (1 - Commission)
- Voyage Costs = Bunker Cost + Port Costs + Miscellaneous
```

### Voyage Duration
```
Total Days = Ballast Days + Laden Days + Loading Days + Discharge Days + Waiting Days

Steaming Days = Distance (nm) / (Speed (kn) × 24)
Port Days = Cargo Quantity / Handling Rate + Turn Time
```

## Assumptions

| Parameter | Value | Rationale |
|-----------|-------|-----------|
| Speed Mode | Economical | Optimizes fuel consumption |
| Bunker Prices | March 2026 forward curve | Per datathon data |
| Misc Costs | $15,000/voyage | Industry standard |
| Weather Buffer | Not included | Covered in scenario analysis |

## Team

[Your Team Name]

## Contact

For questions about this solution, contact [your email].

---

*Developed for the SMU-Cargill Ocean Transportation Datathon 2026*
