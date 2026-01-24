"""
Portfolio Optimizer & Scenario Analysis
=======================================
Optimizes vessel-cargo assignments across the entire portfolio.
"""

import pandas as pd
import numpy as np
from itertools import permutations, product
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
from freight_calculator import (
    FreightCalculator, PortDistanceManager, BunkerPrices,
    Vessel, Cargo, VoyageResult,
    create_cargill_vessels, create_cargill_cargoes, 
    create_market_vessels, create_bunker_prices
)


@dataclass
class PortfolioResult:
    """Results of a portfolio optimization."""
    assignments: List[Tuple[str, str, VoyageResult]]  # (vessel, cargo, result)
    unassigned_vessels: List[str]
    unassigned_cargoes: List[str]
    total_profit: float
    total_tce: float
    avg_tce: float


class PortfolioOptimizer:
    """
    Optimizes vessel-cargo assignments to maximize portfolio profit.
    """
    
    def __init__(self, calculator: FreightCalculator):
        self.calculator = calculator
    
    def calculate_all_voyages(
        self,
        vessels: List[Vessel],
        cargoes: List[Cargo],
        use_eco_speed: bool = True,
        extra_port_delay: float = 0,
        bunker_adjustment: float = 1.0,
    ) -> pd.DataFrame:
        """
        Calculate voyage economics for all vessel-cargo combinations.
        
        Returns DataFrame with all results.
        """
        results = []
        
        for vessel in vessels:
            for cargo in cargoes:
                try:
                    result = self.calculator.calculate_voyage(
                        vessel, cargo,
                        use_eco_speed=use_eco_speed,
                        extra_port_delay_days=extra_port_delay,
                        bunker_price_adjustment=bunker_adjustment,
                    )
                    
                    results.append({
                        'vessel': vessel.name,
                        'cargo': cargo.name,
                        'can_make_laycan': result.can_make_laycan,
                        'arrival_date': result.arrival_date,
                        'laycan_end': result.laycan_end,
                        'days_margin': (result.laycan_end - result.arrival_date).days,
                        'total_days': result.total_days,
                        'cargo_qty': result.cargo_quantity,
                        'net_freight': result.net_freight,
                        'total_bunker_cost': result.total_bunker_cost,
                        'hire_cost': result.hire_cost,
                        'port_costs': result.port_costs,
                        'net_profit': result.net_profit,
                        'tce': result.tce,
                        'vlsfo_consumed': result.vlsfo_consumed,
                        'result': result,
                    })
                except Exception as e:
                    results.append({
                        'vessel': vessel.name,
                        'cargo': cargo.name,
                        'can_make_laycan': False,
                        'error': str(e),
                        'tce': -999999,
                        'net_profit': -999999,
                    })
        
        return pd.DataFrame(results)
    
    def optimize_assignments(
        self,
        vessels: List[Vessel],
        cargoes: List[Cargo],
        use_eco_speed: bool = True,
        extra_port_delay: float = 0,
        bunker_adjustment: float = 1.0,
        maximize: str = 'profit',  # 'profit' or 'tce'
        include_negative_profit: bool = False,  # Whether to assign voyages with negative profit
    ) -> PortfolioResult:
        """
        Find optimal vessel-cargo assignments using brute force enumeration.

        Uses Hungarian algorithm approach: enumerate all possible one-to-one assignments
        between vessels and cargoes, selecting the combination that maximizes profit or TCE.

        For small numbers of vessels/cargoes, brute force is fast and guaranteed optimal.
        """
        from itertools import permutations, combinations

        # Calculate all voyage options
        df = self.calculate_all_voyages(
            vessels, cargoes, use_eco_speed, extra_port_delay, bunker_adjustment
        )

        # Filter to only valid voyages (can make laycan)
        valid_df = df[df['can_make_laycan'] == True].copy()

        # Optionally filter out negative profit voyages
        if not include_negative_profit:
            valid_df = valid_df[valid_df['net_profit'] > 0]

        if len(valid_df) == 0:
            return PortfolioResult(
                assignments=[],
                unassigned_vessels=[v.name for v in vessels],
                unassigned_cargoes=[c.name for c in cargoes],
                total_profit=0,
                total_tce=0,
                avg_tce=0,
            )

        # Get unique vessels and cargoes that have valid options
        valid_vessels = valid_df['vessel'].unique().tolist()
        valid_cargoes = valid_df['cargo'].unique().tolist()

        # Build lookup for results
        voyage_lookup = {}
        for _, row in valid_df.iterrows():
            key = (row['vessel'], row['cargo'])
            voyage_lookup[key] = row

        # Try all possible assignment combinations
        best_score = float('-inf')
        best_profit = 0
        best_tce = 0
        best_assignments = []

        # We need to try different assignment sizes (1 to min(vessels, cargoes))
        # because fewer high-profit assignments may beat more low-profit ones
        n_vessels = len(valid_vessels)
        n_cargoes = len(valid_cargoes)
        max_assignments = min(n_vessels, n_cargoes)

        # Try all possible assignment sizes
        for num_assignments in range(1, max_assignments + 1):
            # Try all combinations of vessels to use
            for vessel_subset in combinations(valid_vessels, num_assignments):
                # Try all permutations of cargoes to assign to these vessels
                for cargo_perm in permutations(valid_cargoes, num_assignments):
                    assignments = []
                    total_profit = 0
                    total_tce = 0
                    valid_assignment = True

                    for vessel, cargo in zip(vessel_subset, cargo_perm):
                        key = (vessel, cargo)

                        if key in voyage_lookup:
                            row = voyage_lookup[key]
                            assignments.append((vessel, cargo, row.get('result')))
                            total_profit += row['net_profit']
                            total_tce += row['tce']
                        else:
                            valid_assignment = False
                            break

                    if valid_assignment and len(assignments) > 0:
                        # Calculate score based on optimization target
                        if maximize == 'profit':
                            score = total_profit
                        elif maximize == 'tce':
                            score = total_tce / len(assignments)  # Average TCE
                        else:
                            score = total_profit

                        if score > best_score:
                            best_score = score
                            best_profit = total_profit
                            best_tce = total_tce
                            best_assignments = assignments

        # Determine unassigned vessels and cargoes
        assigned_vessels = set(a[0] for a in best_assignments)
        assigned_cargoes = set(a[1] for a in best_assignments)

        unassigned_vessels = [v.name for v in vessels if v.name not in assigned_vessels]
        unassigned_cargoes = [c.name for c in cargoes if c.name not in assigned_cargoes]

        return PortfolioResult(
            assignments=best_assignments,
            unassigned_vessels=unassigned_vessels,
            unassigned_cargoes=unassigned_cargoes,
            total_profit=best_profit,
            total_tce=best_tce,
            avg_tce=best_tce / len(best_assignments) if best_assignments else 0,
        )


class ScenarioAnalyzer:
    """
    Performs scenario analysis to find tipping points.
    """
    
    def __init__(self, optimizer: PortfolioOptimizer):
        self.optimizer = optimizer
    
    def analyze_bunker_sensitivity(
        self,
        vessels: List[Vessel],
        cargoes: List[Cargo],
        price_range: Tuple[float, float] = (0.8, 1.5),
        steps: int = 20,
    ) -> pd.DataFrame:
        """
        Analyze how bunker price changes affect optimal assignments.
        
        Returns DataFrame showing tipping points.
        """
        results = []
        
        adjustments = np.linspace(price_range[0], price_range[1], steps)
        
        for adj in adjustments:
            portfolio = self.optimizer.optimize_assignments(
                vessels, cargoes,
                bunker_adjustment=adj,
            )
            
            results.append({
                'bunker_multiplier': adj,
                'bunker_change_pct': (adj - 1) * 100,
                'total_profit': portfolio.total_profit,
                'avg_tce': portfolio.avg_tce,
                'n_assignments': len(portfolio.assignments),
                'assignments': ', '.join([f"{a[0]}->{a[1][:20]}" for a in portfolio.assignments]),
            })
        
        return pd.DataFrame(results)
    
    def analyze_port_delay_sensitivity(
        self,
        vessels: List[Vessel],
        cargoes: List[Cargo],
        max_delay_days: int = 15,
    ) -> pd.DataFrame:
        """
        Analyze how port delays affect optimal assignments.
        
        Returns DataFrame showing tipping points.
        """
        results = []
        
        for delay in range(0, max_delay_days + 1):
            portfolio = self.optimizer.optimize_assignments(
                vessels, cargoes,
                extra_port_delay=delay,
            )
            
            results.append({
                'port_delay_days': delay,
                'total_profit': portfolio.total_profit,
                'avg_tce': portfolio.avg_tce,
                'n_assignments': len(portfolio.assignments),
                'assignments': ', '.join([f"{a[0]}->{a[1][:20]}" for a in portfolio.assignments]),
                'unassigned_cargoes': ', '.join(portfolio.unassigned_cargoes),
            })
        
        return pd.DataFrame(results)
    
    def find_tipping_points(
        self,
        vessels: List[Vessel],
        cargoes: List[Cargo],
    ) -> Dict:
        """
        Find specific tipping points where recommendations change.
        """
        
        # Baseline
        baseline = self.optimizer.optimize_assignments(vessels, cargoes)
        baseline_assignments = frozenset((a[0], a[1]) for a in baseline.assignments)
        
        tipping_points = {
            'bunker': None,
            'port_delay': None,
        }
        
        # Find bunker tipping point
        for adj in np.arange(1.0, 2.0, 0.01):
            portfolio = self.optimizer.optimize_assignments(
                vessels, cargoes, bunker_adjustment=adj
            )
            current_assignments = frozenset((a[0], a[1]) for a in portfolio.assignments)
            
            if current_assignments != baseline_assignments:
                tipping_points['bunker'] = {
                    'multiplier': adj,
                    'change_pct': (adj - 1) * 100,
                    'old_assignments': list(baseline_assignments),
                    'new_assignments': list(current_assignments),
                }
                break
        
        # Find port delay tipping point
        for delay in range(1, 20):
            portfolio = self.optimizer.optimize_assignments(
                vessels, cargoes, extra_port_delay=delay
            )
            current_assignments = frozenset((a[0], a[1]) for a in portfolio.assignments)
            
            if current_assignments != baseline_assignments:
                tipping_points['port_delay'] = {
                    'days': delay,
                    'old_assignments': list(baseline_assignments),
                    'new_assignments': list(current_assignments),
                }
                break
        
        return tipping_points


def print_optimization_report(
    vessels: List[Vessel],
    cargoes: List[Cargo],
    portfolio: PortfolioResult,
    all_voyages_df: pd.DataFrame,
):
    """Print a comprehensive optimization report."""
    
    print("\n" + "=" * 80)
    print("PORTFOLIO OPTIMIZATION REPORT")
    print("=" * 80)
    
    # Summary
    print("\n📊 SUMMARY")
    print("-" * 40)
    print(f"Total Cargill Vessels: {len(vessels)}")
    print(f"Total Committed Cargoes: {len(cargoes)}")
    print(f"Assignments Made: {len(portfolio.assignments)}")
    print(f"Unassigned Vessels: {len(portfolio.unassigned_vessels)}")
    print(f"Unassigned Cargoes: {len(portfolio.unassigned_cargoes)}")
    
    # Optimal assignments
    print("\n✅ OPTIMAL ASSIGNMENTS")
    print("-" * 40)
    
    for vessel, cargo, result in portfolio.assignments:
        if result:
            print(f"\n{vessel} → {cargo}")
            print(f"  📅 Arrives: {result.arrival_date.strftime('%d %b %Y')} (Laycan ends: {result.laycan_end.strftime('%d %b %Y')})")
            print(f"  ⏱️  Duration: {result.total_days:.1f} days")
            print(f"  📦 Cargo: {result.cargo_quantity:,} MT")
            print(f"  💵 Revenue: ${result.net_freight:,.0f}")
            print(f"  ⛽ Bunker Cost: ${result.total_bunker_cost:,.0f}")
            print(f"  🏢 Port Costs: ${result.port_costs:,.0f}")
            print(f"  💰 TCE: ${result.tce:,.0f}/day")
            print(f"  📈 Net Profit: ${result.net_profit:,.0f}")
    
    # Totals
    print("\n" + "-" * 40)
    print(f"💰 TOTAL PORTFOLIO PROFIT: ${portfolio.total_profit:,.0f}")
    print(f"📊 AVERAGE TCE: ${portfolio.avg_tce:,.0f}/day")
    
    # Unassigned items
    if portfolio.unassigned_vessels:
        print("\n⚠️  UNASSIGNED VESSELS (Available for market cargoes):")
        for v in portfolio.unassigned_vessels:
            print(f"  • {v}")
    
    if portfolio.unassigned_cargoes:
        print("\n⚠️  UNASSIGNED CARGOES (Need market vessels):")
        for c in portfolio.unassigned_cargoes:
            print(f"  • {c}")
    
    # TCE Matrix
    print("\n\n📊 TCE COMPARISON MATRIX (USD/day)")
    print("=" * 80)
    
    pivot = all_voyages_df.pivot_table(
        index='vessel',
        columns='cargo',
        values='tce',
        aggfunc='first'
    )
    
    # Rename columns for display
    pivot.columns = [c[:25] + '...' if len(c) > 25 else c for c in pivot.columns]
    
    print(pivot.round(0).to_string())
    
    # Laycan feasibility
    print("\n\n📅 LAYCAN FEASIBILITY MATRIX")
    print("=" * 80)
    
    pivot_laycan = all_voyages_df.pivot_table(
        index='vessel',
        columns='cargo',
        values='can_make_laycan',
        aggfunc='first'
    )
    pivot_laycan.columns = [c[:25] + '...' if len(c) > 25 else c for c in pivot_laycan.columns]
    pivot_laycan = pivot_laycan.replace({True: '✅', False: '❌'})
    
    print(pivot_laycan.to_string())


# =============================================================================
# MAIN - RUN COMPLETE ANALYSIS
# =============================================================================

if __name__ == "__main__":
    print("=" * 80)
    print("CARGILL DATATHON 2026 - PORTFOLIO OPTIMIZATION")
    print("=" * 80)
    
    # Initialize
    distance_mgr = PortDistanceManager('Port_Distances.csv')
    bunker_prices = create_bunker_prices()
    calculator = FreightCalculator(distance_mgr, bunker_prices)
    optimizer = PortfolioOptimizer(calculator)
    analyzer = ScenarioAnalyzer(optimizer)
    
    # Load data
    cargill_vessels = create_cargill_vessels()
    cargill_cargoes = create_cargill_cargoes()
    
    # Calculate all voyages
    all_voyages = optimizer.calculate_all_voyages(cargill_vessels, cargill_cargoes)
    
    # Optimize
    portfolio = optimizer.optimize_assignments(
        cargill_vessels, cargill_cargoes, maximize='profit'
    )
    
    # Print report
    print_optimization_report(cargill_vessels, cargill_cargoes, portfolio, all_voyages)
    
    # ==========================================================================
    # SCENARIO ANALYSIS
    # ==========================================================================
    
    print("\n\n" + "=" * 80)
    print("SCENARIO ANALYSIS")
    print("=" * 80)
    
    # Find tipping points
    tipping_points = analyzer.find_tipping_points(cargill_vessels, cargill_cargoes)
    
    print("\n🔍 TIPPING POINTS")
    print("-" * 40)
    
    if tipping_points['bunker']:
        bp = tipping_points['bunker']
        print(f"\n📈 Bunker Price Tipping Point:")
        print(f"   At +{bp['change_pct']:.0f}% bunker price increase, recommendation changes.")
    else:
        print(f"\n📈 Bunker Price: No tipping point found up to +100% increase")
    
    if tipping_points['port_delay']:
        pd_tp = tipping_points['port_delay']
        print(f"\n⏱️  Port Delay Tipping Point:")
        print(f"   At {pd_tp['days']} days additional delay, recommendation changes.")
    else:
        print(f"\n⏱️  Port Delay: No tipping point found up to 20 days")
    
    # Bunker sensitivity analysis
    print("\n\n📊 BUNKER PRICE SENSITIVITY")
    print("-" * 40)
    
    bunker_analysis = analyzer.analyze_bunker_sensitivity(
        cargill_vessels, cargill_cargoes,
        price_range=(0.9, 1.3),
        steps=9
    )
    
    print("\nBunker Change | Total Profit    | Avg TCE")
    print("-" * 50)
    for _, row in bunker_analysis.iterrows():
        print(f"  {row['bunker_change_pct']:+5.0f}%     | ${row['total_profit']:>12,.0f} | ${row['avg_tce']:>8,.0f}/day")
    
    # Port delay sensitivity
    print("\n\n📊 PORT DELAY SENSITIVITY (China ports)")
    print("-" * 40)
    
    delay_analysis = analyzer.analyze_port_delay_sensitivity(
        cargill_vessels, cargill_cargoes,
        max_delay_days=10
    )
    
    print("\nDelay Days | Total Profit    | Avg TCE    | Unassigned Cargoes")
    print("-" * 70)
    for _, row in delay_analysis.iterrows():
        print(f"    {row['port_delay_days']:2.0f}     | ${row['total_profit']:>12,.0f} | ${row['avg_tce']:>8,.0f}/day | {row['unassigned_cargoes'][:30]}")
    
    # ==========================================================================
    # CRITICAL INSIGHT: HANDLING THE 3RD CARGO
    # ==========================================================================
    
    print("\n\n" + "=" * 80)
    print("⚠️  CRITICAL ISSUE: UNASSIGNED CARGO")
    print("=" * 80)
    
    print("""
The optimization reveals a key challenge:

• Only 2 Cargill vessels (ANN BELL, OCEAN HORIZON) can make ANY of the laycans
• But there are 3 committed Cargill cargoes

This means you MUST either:
1. Use a MARKET VESSEL to carry one of the committed cargoes
2. Pay demurrage/penalties for missing a cargo commitment

RECOMMENDATION:
For the BHP Iron Ore cargo (Australia-China, laycan March 7-11):
• This is the tightest laycan - only ANN BELL and OCEAN HORIZON can make it
• But assigning them to BHP gives lower profit than other routes
• Consider hiring PACIFIC VANGUARD (market vessel at Caofeidian, ETD Feb 26)
  to carry the BHP cargo
    """)
