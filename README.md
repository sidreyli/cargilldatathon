# Cargill Ocean Transportation Datathon 2026
## Freight Calculator & Portfolio Optimizer

---

## Overview

This solution provides a comprehensive freight calculator and portfolio optimization system for Cargill's Capesize vessel fleet. It determines optimal vessel-cargo assignments to maximize profit while respecting laycan constraints.

## Key Features

- **Freight Calculator**: Calculates voyage economics including TCE, fuel costs, port costs, and profit
- **Portfolio Optimizer**: Finds optimal vessel-cargo assignments using Hungarian algorithm or brute-force
- **Scenario Analysis**: Identifies tipping points for bunker prices and port delays
- **Market Vessel Analysis**: Evaluates third-party vessels for unassigned cargoes

## Files Structure

```
cargillDatathon/
├── freight_calculator.py      # Core freight calculation engine
├── portfolio_optimizer.py     # Portfolio optimization & scenario analysis
├── datathon_raw_data.md       # Raw datathon briefing data
├── Port_Distances.csv         # Port-to-port distance data (~15,000 routes)
├── Simple_calculator.xlsx     # Reference Excel calculator
└── README.md                  # This file
```

## Installation

```bash
# Required Python packages
pip install pandas numpy scipy

# Optional for notebooks/visualization
pip install matplotlib seaborn jupyter
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

## Key Results

### Optimal Assignments (Cargill Vessels)

| Vessel | Cargo | TCE ($/day) | Net Profit |
|--------|-------|-------------|------------|
| OCEAN HORIZON | EGA Bauxite (Guinea-China) | ~$30,879 | ~$1,265,746 |
| ANN BELL | CSN Iron Ore (Brazil-China) | ~$23,390 | ~$1,018,508 |

**Total Portfolio Profit: ~$2,284,255**

### Critical Insight

Only 2 of 4 Cargill vessels (ANN BELL and OCEAN HORIZON) can make any of the cargo laycans due to their current positions and ETD dates. The BHP Iron Ore cargo (tight laycan: 7-11 Mar) requires a market vessel.

| Vessel | ETD | BHP (7-11 Mar) | EGA (2-10 Apr) | CSN (1-8 Apr) |
|--------|-----|----------------|----------------|---------------|
| ANN BELL | 25 Feb | CAN | CAN | CAN |
| OCEAN HORIZON | 1 Mar | CAN | CAN | CANNOT |
| PACIFIC GLORY | 10 Mar | CANNOT | CANNOT | CANNOT |
| GOLDEN ASCENT | 8 Mar | CANNOT | CANNOT | CANNOT |

### Scenario Analysis Findings

1. **Bunker Price Sensitivity**: Recommendation changes only if bunker prices increase >82%
2. **Port Delay Impact**: ~$30,000 profit loss per day of delay, but assignments remain stable

---

## Known Issues & Planned Fixes

### Distance Lookup System

The current implementation has potential issues with port distance lookups that may affect voyage calculations.

#### Issue 1: Estimated vs CSV Distance Discrepancies

The code uses hardcoded `estimated_distances` as fallback when CSV lookup fails. Some estimates are inaccurate:

| Route | Code Estimate | CSV Actual | Error |
|-------|--------------|------------|-------|
| CAOFEIDIAN → PORT HEDLAND | 4,200 nm | 3,788 nm | +412 nm (~1.4 days) |
| GWANGYANG → PORT HEDLAND | 3,800 nm | 3,473 nm | +327 nm (~1.1 days) |
| FANGCHENG → PORT HEDLAND | 3,700 nm | 2,843 nm | +857 nm (~2.9 days) |

**Impact**: Overestimated distances = longer calculated voyage times = incorrect laycan feasibility.

#### Issue 2: Port Name Aliasing

The CSV uses specific port name variants that may not match the code:

| Code Uses | CSV Has | Status |
|-----------|---------|--------|
| `GWANGYANG` | `GWANGYANG LNG TERMINAL` | Alias exists but may not match |
| `KAMSAR ANCHORAGE` | `KAMSAR ANCHORAGE`, `PORT KAMSAR` | Multiple variants |
| `QINGDAO` | `QINGDAO`, `DAGANG (QINGDAO)` | Alias exists |

#### Issue 3: Missing Routes in CSV

Routes not in the CSV that require estimates:

- MAP TA PHUT → PORT HEDLAND (~2,800 nm)
- MAP TA PHUT → KAMSAR ANCHORAGE (~9,500 nm)
- MAP TA PHUT → ITAGUAI (~12,500 nm)
- Various India port → load port combinations

### Planned Fix Strategy

#### Phase 1: Improve CSV Lookup Priority
1. Ensure CSV distances are always used when available
2. Add logging when falling back to estimated distances
3. Validate port name normalization logic

#### Phase 2: Correct Estimated Distances
1. Cross-reference estimates against maritime distance calculators
2. Remove estimates that exist in CSV (to force CSV lookup)
3. Add validated estimates for truly missing routes

#### Phase 3: Enhance Port Aliasing
1. Build comprehensive alias map from CSV analysis
2. Add fuzzy matching for port names with typos/variations
3. Add validation warnings for unrecognized ports

#### Phase 4: Add Distance Validation
1. Log source of each distance used (CSV vs estimate)
2. Add unit tests comparing key routes
3. Generate distance audit report

---

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

### Laycan Feasibility
```
Arrival Date = ETD + Ballast Days
Can Make Laycan = (Arrival Date <= Laycan End Date)
```

## Assumptions

| Parameter | Value | Rationale |
|-----------|-------|-----------|
| Speed Mode | Economical | Optimizes fuel consumption |
| Bunker Prices | March 2026 forward curve | Per datathon data |
| Misc Costs | $15,000/voyage | Industry standard |
| Vessel Constants | 3,500 MT | Reserve for bunkers/stores |
| Weather Buffer | Not included | Covered in scenario analysis |

## Data Sources

- **Port Distances**: `Port_Distances.csv` (~15,000 port pairs)
- **Bunker Prices**: March 2026 forward curve from datathon briefing
- **FFA Rates**: Baltic Exchange 5TC = $18,454/day (Mar 2026)

---

## Team

[Your Team Name]

## Contact

For questions about this solution, contact [your email].

---

*Developed for the SMU-Cargill Ocean Transportation Datathon 2026*
