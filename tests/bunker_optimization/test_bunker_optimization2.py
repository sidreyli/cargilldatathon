"""Test script for bunker port optimization with better route."""

from src.freight_calculator import (
    FreightCalculator, PortDistanceManager,
    create_bunker_prices, create_cargill_vessels, create_cargill_cargoes
)

# Initialize
dm = PortDistanceManager('data/Port_Distances.csv')
bp = create_bunker_prices()
calc = FreightCalculator(dm, bp)

# Load data
vessels = create_cargill_vessels()
cargoes = create_cargill_cargoes()

# Test ANN BELL (QINGDAO) -> EGA Bauxite (KAMSAR -> QINGDAO)
# This should test bunker ports along the Africa route
vessel = vessels[0]  # ANN BELL at QINGDAO
cargo = cargoes[0]   # EGA Bauxite (Guinea-China)

print("=" * 80)
print("BUNKER PORT OPTIMIZATION TEST")
print("=" * 80)
print(f"\nVessel: {vessel.name} (currently at {vessel.current_port})")
print(f"  ROB: {vessel.bunker_rob_vlsfo:.0f} MT VLSFO, {vessel.bunker_rob_mgo:.0f} MT MGO")
print(f"\nCargo: {cargo.name}")
print(f"  Route: {cargo.load_port} -> {cargo.discharge_port}")

# Check available bunker port prices
print("\n" + "-" * 80)
print("BUNKER PORT PRICES (March 2026)")
print("-" * 80)
for port in ['Singapore', 'Fujairah', 'Rotterdam', 'Gibraltar', 'Durban',
             'Qingdao', 'Shanghai', 'Port Louis', 'Richards Bay']:
    vlsfo = bp.get_price(port, 'VLSFO')
    mgo = bp.get_price(port, 'MGO')
    print(f"  {port:20} VLSFO: ${vlsfo}/MT, MGO: ${mgo}/MT")

result = calc.calculate_voyage(vessel, cargo, use_eco_speed=True)

print("\n" + "-" * 80)
print("VOYAGE RESULTS")
print("-" * 80)
print(f"Selected Bunker Port: {result.selected_bunker_port or 'No bunkering needed'}")

if result.selected_bunker_port:
    print(f"\nBunker Port Details:")
    print(f"  Port: {result.selected_bunker_port}")
    print(f"  VLSFO Price: ${bp.get_price(result.selected_bunker_port, 'VLSFO')}/MT")
    print(f"  MGO Price: ${bp.get_price(result.selected_bunker_port, 'MGO')}/MT")
    print(f"  Quantity: {result.bunker_fuel_vlsfo_qty:.0f} MT VLSFO, {result.bunker_fuel_mgo_qty:.0f} MT MGO")
    print(f"  Savings: ${result.bunker_port_savings:,.0f} (vs load port)")

    print(f"\nRouting:")
    print(f"  Direct distance: {result.direct_ballast_distance:.0f} nm ({vessel.current_port} -> {cargo.load_port})")
    print(f"  Leg 1: {result.ballast_leg_to_bunker:.0f} nm ({vessel.current_port} -> {result.selected_bunker_port})")
    print(f"  Leg 2: {result.bunker_to_load_leg:.0f} nm ({result.selected_bunker_port} -> {cargo.load_port})")
    print(f"  Total routed: {result.ballast_leg_to_bunker + result.bunker_to_load_leg:.0f} nm")
    detour = (result.ballast_leg_to_bunker + result.bunker_to_load_leg) - result.direct_ballast_distance
    print(f"  Detour: {detour:+.0f} nm")

print(f"\nVoyage Economics:")
print(f"  Total Days: {result.total_days:.1f} days")
print(f"  Bunker Cost: ${result.total_bunker_cost:,.0f}")
print(f"  TCE: ${result.tce:,.0f}/day")
print(f"  Net Profit: ${result.net_profit:,.0f}")
print(f"  Can Make Laycan: {'YES' if result.can_make_laycan else 'NO'}")

print("\n" + "=" * 80)
print("TEST COMPLETED")
print("=" * 80)
