"""Quick test to verify bunkering cost calculation."""
from src.freight_calculator import FreightCalculator, PortDistanceManager, create_cargill_vessels, create_cargill_cargoes, create_bunker_prices
from pathlib import Path

project_root = Path('.')
distance_mgr = PortDistanceManager(project_root / 'data' / 'Port_Distances.csv', verbose=False)
bunker_prices = create_bunker_prices()
calculator = FreightCalculator(distance_mgr, bunker_prices)

vessels = create_cargill_vessels()
cargo = [c for c in create_cargill_cargoes() if 'CSN' in c.name][0]

# Calculate for ANN BELL (hire: $11,750/day, idle MGO: 2.0 MT/day)
vessel = [v for v in vessels if v.name == 'ANN BELL'][0]
result = calculator.calculate_voyage(vessel, cargo, use_eco_speed=False)

print(f'Vessel: {result.vessel_name}')
print(f'Cargo: {result.cargo_name}')
print(f'')
print(f'Expected Bunkering Stop Cost Calculation:')
print(f'  Hire rate: ${vessel.hire_rate:,.0f}/day')
print(f'  Extra days: {result.extra_bunkering_days:.1f} day')
print(f'  Extra hire cost: ${vessel.hire_rate * result.extra_bunkering_days:,.0f}')
print(f'  ')
print(f'  Idle MGO rate: {vessel.port_idle_mgo:.1f} MT/day')
print(f'  Extra MGO: {result.extra_mgo_for_bunker:.1f} MT')
print(f'  MGO price: $833/MT (approx)')
print(f'  Extra MGO cost: ~${result.extra_mgo_for_bunker * 833:,.0f}')
print(f'  ')
print(f'  Lumpsum fee: ${result.bunkering_lumpsum_fee:,.0f}')
print(f'  ')
print(f'Total bunkering stop impact: ${vessel.hire_rate + (result.extra_mgo_for_bunker * 833) + result.bunkering_lumpsum_fee:,.0f}')
print(f'')
print(f'Actual values from calculation:')
print(f'  Bunkering stops: {result.num_bunkering_stops}')
print(f'  Extra days: {result.extra_bunkering_days:.2f}')
print(f'  Extra MGO: {result.extra_mgo_for_bunker:.2f} MT')
print(f'  Lumpsum fee: ${result.bunkering_lumpsum_fee:,.2f}')
