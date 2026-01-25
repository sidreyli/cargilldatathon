#!/usr/bin/env python
"""
Run Portfolio Optimizer
========================
Convenience script to run the portfolio optimization from project root.

Usage:
    python scripts/run_optimizer.py
"""

import os
import sys

# Setup paths
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
SRC_DIR = os.path.join(PROJECT_ROOT, 'src')
DATA_DIR = os.path.join(PROJECT_ROOT, 'data')

# Add src to path
sys.path.insert(0, SRC_DIR)

# Change to project root for relative paths
os.chdir(PROJECT_ROOT)

# Now import and run the optimizer
from src.freight_calculator import (
    FreightCalculator, PortDistanceManager,
    create_cargill_vessels, create_cargill_cargoes,
    create_market_vessels, create_market_cargoes, create_bunker_prices
)
from src.portfolio_optimizer import (
    PortfolioOptimizer, FullPortfolioOptimizer, ScenarioAnalyzer,
    print_full_portfolio_report, print_optimization_report,
    get_ml_port_delays, optimize_with_ml_delays
)

if __name__ == "__main__":
    print("=" * 80)
    print("CARGILL DATATHON 2026 - PORTFOLIO OPTIMIZATION")
    print("=" * 80)
    print(f"Project root: {PROJECT_ROOT}")

    # Initialize
    distance_mgr = PortDistanceManager(os.path.join(DATA_DIR, 'Port_Distances.csv'))
    bunker_prices = create_bunker_prices()
    calculator = FreightCalculator(distance_mgr, bunker_prices)

    # Load data
    cargill_vessels = create_cargill_vessels()
    market_vessels = create_market_vessels()
    cargill_cargoes = create_cargill_cargoes()
    market_cargoes = create_market_cargoes()

    print(f"\nData loaded:")
    print(f"  Cargill Vessels: {len(cargill_vessels)}")
    print(f"  Market Vessels: {len(market_vessels)}")
    print(f"  Cargill Cargoes: {len(cargill_cargoes)}")
    print(f"  Market Cargoes: {len(market_cargoes)}")

    # Run full optimization
    print("\n" + "=" * 80)
    print("FULL PORTFOLIO OPTIMIZATION")
    print("=" * 80)

    full_optimizer = FullPortfolioOptimizer(calculator)
    TARGET_TCE = 18000

    full_result = full_optimizer.optimize_full_portfolio(
        cargill_vessels=cargill_vessels,
        market_vessels=market_vessels,
        cargill_cargoes=cargill_cargoes,
        market_cargoes=market_cargoes,
        target_tce=TARGET_TCE,
    )

    print_full_portfolio_report(full_result)

    # ML-based analysis
    print("\n" + "=" * 80)
    print("ML-BASED PORT DELAY ANALYSIS")
    print("=" * 80)

    ml_delays = get_ml_port_delays(cargill_cargoes, prediction_date='2026-03-15')

    if ml_delays:
        print("\nML-Predicted Port Delays:")
        for port, info in ml_delays.items():
            model_tag = "[ML]" if info['model_used'] == 'ml_model' else "[Fallback]"
            print(f"  {port:20s}: {info['predicted_delay']:.1f} days ({info['congestion_level']}) {model_tag}")

        # Compare baseline vs ML-adjusted
        baseline_result, ml_result, _ = optimize_with_ml_delays(
            calculator, cargill_vessels, cargill_cargoes,
            prediction_date='2026-03-15',
        )

        print(f"\nProfit Comparison:")
        print(f"  Baseline (no delays):    ${baseline_result.total_profit:>12,.0f}")
        print(f"  ML-adjusted:             ${ml_result.total_profit:>12,.0f}")
        print(f"  Impact from delays:      ${ml_result.total_profit - baseline_result.total_profit:>12,.0f}")
    else:
        print("\nML model not available. Run: python scripts/train_model.py")

    print("\n" + "=" * 80)
    print("OPTIMIZATION COMPLETE")
    print("=" * 80)
