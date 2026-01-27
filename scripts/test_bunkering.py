"""
Test script to verify bunkering stop costs implementation.
"""
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.freight_calculator import (
    FreightCalculator,
    PortDistanceManager,
    create_cargill_vessels,
    create_cargill_cargoes,
    create_bunker_prices,
)

def main():
    print("=" * 80)
    print("BUNKERING STOP COSTS VERIFICATION TEST")
    print("=" * 80)

    # Initialize calculator
    distance_mgr = PortDistanceManager(project_root / 'data' / 'Port_Distances.csv')
    bunker_prices = create_bunker_prices()
    calculator = FreightCalculator(distance_mgr, bunker_prices)

    vessels = create_cargill_vessels()
    cargoes = create_cargill_cargoes()

    # Test Case 1: Find a voyage that triggers bunkering
    print("\n" + "=" * 80)
    print("TEST CASE 1: Long voyage with low ROB (should trigger bunkering)")
    print("=" * 80)

    # OCEAN HORIZON has low ROB (265.8 VLSFO, 64.3 MGO)
    # CSN cargo is Brazil-China (very long voyage)
    vessel = [v for v in vessels if v.name == "OCEAN HORIZON"][0]
    cargo = [c for c in cargoes if "CSN" in c.name][0]

    result = calculator.calculate_voyage(vessel, cargo, use_eco_speed=False)

    print(f"\nVessel: {result.vessel_name}")
    print(f"Cargo: {result.cargo_name}")
    print(f"Total voyage days: {result.total_days:.2f}")
    print(f"\nFuel Consumption:")
    print(f"  VLSFO consumed: {result.vlsfo_consumed:.2f} MT")
    print(f"  MGO consumed: {result.mgo_consumed:.2f} MT")
    print(f"  VLSFO ROB: {vessel.bunker_rob_vlsfo:.2f} MT")
    print(f"  MGO ROB: {vessel.bunker_rob_mgo:.2f} MT")
    print(f"\nBunker Needed:")
    print(f"  VLSFO needed: {result.bunker_needed_vlsfo:.2f} MT")
    print(f"  MGO needed: {result.bunker_needed_mgo:.2f} MT")
    print(f"  Total needed: {result.bunker_needed_vlsfo + result.bunker_needed_mgo:.2f} MT")
    print(f"\n{'='*40}")
    print(f"BUNKERING STOP TRIGGERED: {result.num_bunkering_stops == 1}")
    print(f"{'='*40}")
    print(f"  Bunkering stops: {result.num_bunkering_stops}")
    print(f"  Extra days: {result.extra_bunkering_days:.2f}")
    print(f"  Extra MGO consumed: {result.extra_mgo_for_bunker:.2f} MT")
    print(f"  Lumpsum fee: ${result.bunkering_lumpsum_fee:,.2f}")
    print(f"\nTotal Costs Breakdown:")
    print(f"  Bunker cost: ${result.total_bunker_cost:,.2f}")
    print(f"  Hire cost: ${result.hire_cost:,.2f}")
    print(f"  Port costs: ${result.port_costs:,.2f}")
    print(f"  Misc costs: ${result.misc_costs:,.2f}")
    print(f"  Bunkering lumpsum: ${result.bunkering_lumpsum_fee:,.2f}")
    print(f"  -------------------------")
    print(f"  TOTAL: ${result.total_costs:,.2f}")

    # Test Case 2: Vessel with high ROB (should NOT trigger bunkering)
    print("\n\n" + "=" * 80)
    print("TEST CASE 2: Vessel with high ROB (should NOT trigger bunkering)")
    print("=" * 80)

    # PACIFIC GLORY has high ROB (601.9 VLSFO, 98.1 MGO)
    # BHP cargo is shorter route
    vessel = [v for v in vessels if v.name == "PACIFIC GLORY"][0]
    cargo = [c for c in cargoes if "BHP" in c.name][0]

    result = calculator.calculate_voyage(vessel, cargo, use_eco_speed=False)

    print(f"\nVessel: {result.vessel_name}")
    print(f"Cargo: {result.cargo_name}")
    print(f"Total voyage days: {result.total_days:.2f}")
    print(f"\nFuel Consumption:")
    print(f"  VLSFO consumed: {result.vlsfo_consumed:.2f} MT")
    print(f"  MGO consumed: {result.mgo_consumed:.2f} MT")
    print(f"  VLSFO ROB: {vessel.bunker_rob_vlsfo:.2f} MT")
    print(f"  MGO ROB: {vessel.bunker_rob_mgo:.2f} MT")
    print(f"\nBunker Needed:")
    print(f"  VLSFO needed: {result.bunker_needed_vlsfo:.2f} MT")
    print(f"  MGO needed: {result.bunker_needed_mgo:.2f} MT")
    print(f"  Total needed: {result.bunker_needed_vlsfo + result.bunker_needed_mgo:.2f} MT")
    print(f"\n{'='*40}")
    print(f"BUNKERING STOP TRIGGERED: {result.num_bunkering_stops == 1}")
    print(f"{'='*40}")
    print(f"  Bunkering stops: {result.num_bunkering_stops}")
    print(f"  Extra days: {result.extra_bunkering_days:.2f}")
    print(f"  Extra MGO consumed: {result.extra_mgo_for_bunker:.2f} MT")
    print(f"  Lumpsum fee: ${result.bunkering_lumpsum_fee:,.2f}")
    print(f"\nTotal Costs Breakdown:")
    print(f"  Bunker cost: ${result.total_bunker_cost:,.2f}")
    print(f"  Hire cost: ${result.hire_cost:,.2f}")
    print(f"  Port costs: ${result.port_costs:,.2f}")
    print(f"  Misc costs: ${result.misc_costs:,.2f}")
    print(f"  Bunkering lumpsum: ${result.bunkering_lumpsum_fee:,.2f}")
    print(f"  -------------------------")
    print(f"  TOTAL: ${result.total_costs:,.2f}")

    # Test Case 3: Edge case around threshold
    print("\n\n" + "=" * 80)
    print("TEST CASE 3: Summary of all combinations")
    print("=" * 80)

    print(f"\n{'Vessel':<20} {'Cargo':<40} {'Bunker Needed':<15} {'Stop?':<10}")
    print("-" * 85)

    for vessel in vessels:
        for cargo in cargoes:
            result = calculator.calculate_voyage(vessel, cargo, use_eco_speed=False)
            total_needed = result.bunker_needed_vlsfo + result.bunker_needed_mgo
            triggered = "YES" if result.num_bunkering_stops == 1 else "NO"
            print(f"{vessel.name:<20} {cargo.name[:38]:<40} {total_needed:>10.1f} MT   {triggered:<10}")

    print("\n" + "=" * 80)
    print("TEST COMPLETE")
    print("=" * 80)

if __name__ == "__main__":
    main()
