# Cargill Ocean Transportation Datathon 2026

## Project Overview

This is a hackathon/datathon project for **SMU-Cargill Ocean Transportation Datathon 2026**. The challenge involves optimizing vessel-cargo assignments for Cargill's Capesize shipping fleet.

## Project Structure

```
cargill_datathon/
├── src/                        # Source code package
│   ├── __init__.py            # Package exports
│   ├── freight_calculator.py  # Core voyage economics engine
│   ├── portfolio_optimizer.py # Portfolio optimization & scenarios
│   └── ml/                    # ML models for port congestion
│       ├── __init__.py
│       ├── feature_engineering.py
│       ├── holiday_calendar.py
│       └── port_congestion_predictor.py
├── data/                       # Data files
│   ├── Port_Distances.csv     # Port-to-port distances (15,533 routes)
│   ├── PortWatch_ports_database.csv
│   └── raw/                   # Large raw data (gitignored)
│       └── Daily_Port_Activity_Data_and_Trade_Estimates.csv
├── models/                     # Saved ML models
│   ├── model_info.json        # Model metadata
│   └── port_delay_v1.joblib   # Trained LightGBM model
├── notebooks/                  # Jupyter notebooks
│   ├── analysis.ipynb         # Main datathon analysis
│   └── ml_training.ipynb      # ML model development
├── scripts/                    # Runnable scripts
│   ├── train_model.py         # Train ML model
│   ├── run_optimizer.py       # Run portfolio optimization
│   └── verify_logic.py        # Verification tests
├── docs/                       # Documentation
│   └── raw_data_spec.md       # Raw data specification
├── CLAUDE.md                   # This file
├── README.md
└── requirements.txt
```

## Quick Start

```bash
# Run portfolio optimization
python scripts/run_optimizer.py

# Train ML model (requires raw data)
python scripts/train_model.py

# Run verification tests
python scripts/verify_logic.py
```

## Problem Statement

Cargill operates a fleet of Capesize bulk carriers and needs to:
1. Assign their 4 owned vessels to 3 committed cargoes (fulfilling existing contracts)
2. Decide whether to hire market vessels for unassigned cargoes
3. Decide whether to bid for additional market cargoes using available vessels
4. Maximize portfolio profit while respecting laycan (loading window) constraints

## Key Findings

**Optimal Portfolio Assignment**:
| Vessel | Cargo | TCE | Profit |
|--------|-------|-----|--------|
| OCEAN HORIZON | EGA Bauxite | $30,879/day | $1,265,746 |
| ANN BELL | CSN Iron Ore | $23,390/day | $1,018,508 |
| **Total** | | | **$2,284,255** |

**Critical Discovery**: Only 2 of 4 Cargill vessels can make ANY cargo laycans due to positioning. BHP Iron Ore cargo requires a market vessel.

## Key Formulas

### TCE (Time Charter Equivalent)
```
TCE = (Net Freight - Voyage Costs) / Total Days

Where:
- Net Freight = Gross Freight × (1 - Commission)
- Voyage Costs = Bunker Cost + Port Costs + Misc ($15,000)
```

### Voyage Duration
```
Total Days = Ballast Days + Laden Days + Loading Days + Discharge Days + Waiting Days
Steaming Days = Distance (nm) / (Speed (kn) × 24)
```

## ML Model

The port congestion predictor uses LightGBM to estimate waiting times at discharge ports:
- **Target ports**: Qingdao, Rizhao, Caofeidian, Fangcheng (China); Mundra, Vizag (India)
- **Features**: Rolling port activity, seasonal factors (CNY, monsoon, typhoon)
- **Output**: Predicted delay days with confidence intervals

Note: The model uses a synthetic target variable (see `src/ml/feature_engineering.py` for methodology).

## Dependencies

See `requirements.txt`. Key packages:
- pandas, numpy: Data processing
- scipy: Optimization algorithms
- lightgbm: ML model
- shap: Model explainability
- matplotlib, seaborn: Visualization
