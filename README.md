# Cargill Ocean Transportation Datathon 2026
## Full-Stack Freight Calculator & Portfolio Optimizer

---

## Overview

A comprehensive freight analytics platform for Cargill's Capesize vessel fleet. The system optimizes vessel-cargo assignments across both Cargill-owned vessels and market opportunities to maximize portfolio profit.

### Key Result: **$5.8M Total Portfolio Profit**

The optimizer recommends deploying all 4 Cargill vessels on higher-margin market cargoes while hiring market vessels at competitive rates to fulfill committed cargo obligations.

---

## Features

### Core Analytics
- **Freight Calculator**: Full voyage economics including TCE, bunker costs, port costs, and net profit
- **Portfolio Optimizer**: Hungarian algorithm optimization across Cargill + market vessels/cargoes
- **Dual Speed Analysis**: Compares eco vs warranted speed for each voyage
- **Bunker Optimization**: Identifies optimal bunkering ports along routes

### Scenario Analysis
- **Bunker Price Sensitivity**: Impact of ±50% fuel price changes on assignments
- **Port Delay Sensitivity**: Effect of congestion delays on profitability
- **Tipping Point Analysis**: Identifies when optimal assignments change

#### Tipping Point Details

The system identifies critical thresholds where optimal strategy changes:

- **Bunker Price Threshold**: +31% increase (1.31x multiplier)
  - At this point, high-speed voyages become uneconomical
  - Portfolio strategy shifts to eco-speed and shorter routes
  - Profit degrades from $5.8M to $4.0M

- **China Port Delay Threshold**: +46 days additional delay
  - Baseline portfolio remains optimal up to 45 days of delays
  - Demonstrates high resilience of the optimized portfolio
  - At 46 days, profit degrades 59.7% but re-optimization provides minimal advantage ($98)

### ML-Powered Insights
- **Port Congestion Predictor**: Random Forest model predicting port delays
- **Feature Engineering**: Day of week, seasonality, cargo type patterns

### Interactive Web Application
- **Dashboard**: Real-time portfolio overview with KPIs and assignment matrix
- **Voyages Explorer**: Compare all 144 vessel-cargo combinations
- **Scenario Simulator**: Interactive what-if analysis
- **AI Chat Assistant**: Claude-powered natural language queries

---

## Project Structure

```
cargillDatathon/
├── api/                          # FastAPI Backend
│   ├── main.py                   # API entry point
│   ├── routes/                   # REST endpoints
│   │   ├── portfolio.py          # Portfolio & vessel APIs
│   │   ├── voyage.py             # Voyage calculation APIs
│   │   ├── scenario.py           # Scenario analysis APIs
│   │   ├── ml_routes.py          # ML prediction APIs
│   │   └── chat.py               # AI chat endpoint
│   └── services/
│       ├── calculator_service.py # Pre-computed results cache
│       └── chat_service.py       # Claude API integration
│
├── frontend/                     # React + Vite Frontend
│   ├── src/
│   │   ├── components/
│   │   │   ├── dashboard/        # Portfolio dashboard
│   │   │   ├── voyages/          # Voyage comparison table
│   │   │   ├── scenarios/        # Sensitivity charts
│   │   │   ├── ml/               # ML insights page
│   │   │   └── chat/             # AI chat panel
│   │   ├── api/                  # API client & React Query hooks
│   │   └── types/                # TypeScript definitions
│   └── package.json
│
├── src/                          # Core Python Analytics
│   ├── freight_calculator.py     # Voyage economics engine
│   ├── portfolio_optimizer.py    # Optimization algorithms
│   └── ml/                       # Machine learning models
│       ├── port_congestion_predictor.py
│       └── feature_engineering.py
│
├── data/
│   ├── Port_Distances.csv        # 15,000+ port-pair distances
│   └── PortWatch_ports_database.csv
│
├── notebooks/
│   ├── analysis.ipynb            # Exploratory analysis
│   └── ml_training.ipynb         # Model training
│
├── start_dev.bat                 # Windows dev server script
├── start_dev.sh                  # Unix dev server script
└── requirements.txt              # Python dependencies
```

---

## Quick Start

### Prerequisites
- Python 3.10+ with Anaconda
- Node.js 18+
- Anthropic API key (optional, for AI chat)

### Installation

```bash
# Clone the repository
git clone https://github.com/sidreyli/cargillDatathon.git
cd cargillDatathon

# Install Python dependencies
pip install -r requirements.txt

# Install frontend dependencies
cd frontend
npm install
cd ..
```

### Running the Application

```bash
# Terminal 1: Backend
conda activate cargill
uvicorn api.main:app --reload --port 8000

# Terminal 2: Frontend
cd frontend
npm run dev
```

### Access the Application
- **Frontend**: http://localhost:5173
- **API Docs**: http://localhost:8000/docs

---

## Key Results

### Optimal Portfolio Assignment

| Vessel (Cargill) | Assigned Cargo | TCE | Net Profit |
|------------------|----------------|-----|------------|
| ANN BELL | Vale Malaysia Iron Ore (Brazil-Malaysia) | $22,614/day | $915,509 |
| OCEAN HORIZON | BHP Iron Ore (Australia-S.Korea) | $27,036/day | $350,978 |
| PACIFIC GLORY | Teck Coking Coal (Canada-China) | $29,426/day | $708,408 |
| GOLDEN ASCENT | Adaro Coal (Indonesia-India) | $35,181/day | $1,169,745 |

### Market Vessel Hires (for Cargill Cargoes)

| Hired Vessel | Cargo | Duration | TCE | Net Profit |
|--------------|-------|----------|-----|------------|
| IRON CENTURY | EGA Bauxite (Guinea-China) | 77.7 days | $38,782/day | $1,398,960 |
| ATLANTIC FORTUNE | BHP Iron Ore (Australia-China) | 29.8 days | $18,052/day | $536,040 |
| CORAL EMPEROR | CSN Iron Ore (Brazil-China) | 77.9 days | $31,375/day | $1,402,380 |

### Portfolio Summary
- **Total Profit**: $5,803,558
- **Average TCE**: $28,924/day
- **Cargill Fleet Utilization**: 100% (4/4 vessels deployed)
- **All laycans met** using eco speed

---

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/portfolio/optimize` | GET | Get optimal portfolio assignment |
| `/api/portfolio/all-voyages` | GET | Get all 144 voyage combinations |
| `/api/voyage/calculate` | POST | Calculate specific voyage economics |
| `/api/scenario/bunker` | GET | Bunker price sensitivity analysis |
| `/api/scenario/port-delay` | GET | Port delay sensitivity analysis |
| `/api/ml/port-delays` | GET | ML-predicted port congestion |
| `/api/chat` | POST | AI chat (streaming SSE) |
| `/api/chat/sync` | POST | AI chat (non-streaming) |

---

## Environment Variables

Create a `.env` file in the project root:

```env
ANTHROPIC_API_KEY=sk-ant-api03-your-key-here
```

The AI chat feature works without an API key (falls back to rule-based responses), but provides richer answers with Claude integration.

---

## Technology Stack

### Backend
- **FastAPI** - High-performance async Python API
- **Uvicorn** - ASGI server
- **Pandas/NumPy** - Data processing
- **SciPy** - Hungarian algorithm optimization
- **Scikit-learn** - ML models

### Frontend
- **React 18** - UI framework
- **TypeScript** - Type safety
- **Vite** - Build tool
- **TailwindCSS** - Styling
- **React Query** - Data fetching
- **Recharts** - Visualizations
- **Framer Motion** - Animations

### AI Integration
- **Claude API** - Natural language chat with tool calling

---

## Methodology

### TCE Calculation
```
TCE = (Net Freight - Voyage Costs) / Total Voyage Days

Net Freight = Gross Freight × (1 - Commission)
Voyage Costs = Bunker Cost + Port Costs + Hire Cost + Misc
```

### Portfolio Optimization
1. Calculate economics for all vessel-cargo pairs (144 combinations)
2. Filter to feasible assignments (can make laycan)
3. Apply Hungarian algorithm to maximize total profit
4. Recommend market vessel hires for unfulfilled cargoes

### Bunker Optimization
For each voyage, evaluates bunkering at:
- Origin port
- En-route ports (Fujairah, Singapore, Gibraltar, etc.)
- Destination port

Selects the port with lowest total cost (price × quantity + deviation).

---

## Data Sources

- **Port Distances**: CSV with 15,000+ maritime routes
- **Bunker Prices**: March 2026 forward curve
- **FFA Rates**: Baltic Exchange 5TC = $18,454/day
- **Port Data**: PortWatch database

---

## Team

Sidharth Rajesh
Makendra Prasad

