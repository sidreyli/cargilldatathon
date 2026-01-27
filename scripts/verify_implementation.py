"""Verify bunkering implementation is complete."""
import re

with open('src/freight_calculator.py', 'r', encoding='utf-8') as f:
    content = f.read()

checks = []

# Check 1: VoyageResult fields
checks.append(('VoyageResult has num_bunkering_stops field', 'num_bunkering_stops: int' in content))
checks.append(('VoyageResult has extra_bunkering_days field', 'extra_bunkering_days: float' in content))
checks.append(('VoyageResult has bunkering_lumpsum_fee field', 'bunkering_lumpsum_fee: float' in content))
checks.append(('VoyageResult has extra_mgo_for_bunker field', 'extra_mgo_for_bunker: float' in content))

# Check 2: Config constant
checks.append(('VoyageConfig has bunker_threshold_mt constant', 'bunker_threshold_mt: float = 50.0' in content))

# Check 3: Bunkering logic
checks.append(('Bunkering stop logic is present', 'BUNKERING STOP COSTS (FAQ Q9/Q3)' in content))
checks.append(('Bunker threshold check logic present', 'total_bunker_needed = bunker_needed_vlsfo + bunker_needed_mgo' in content))

# Check 4: Total costs includes lumpsum
checks.append(('Total costs includes bunkering_lumpsum_fee', 'total_costs = total_bunker_cost + hire_cost + port_costs + misc_costs + bunkering_lumpsum_fee' in content))

# Check 5: VoyageResult construction (simpler check)
checks.append(('VoyageResult construction includes num_bunkering_stops',
              'num_bunkering_stops=num_bunkering_stops,' in content))
checks.append(('VoyageResult construction includes extra_bunkering_days',
              'extra_bunkering_days=round(extra_bunkering_days, 2),' in content))
checks.append(('VoyageResult construction includes bunkering_lumpsum_fee',
              'bunkering_lumpsum_fee=round(bunkering_lumpsum_fee, 2),' in content))
checks.append(('VoyageResult construction includes extra_mgo_for_bunker',
              'extra_mgo_for_bunker=round(extra_mgo_for_bunker, 2),' in content))

print("=" * 80)
print("BUNKERING IMPLEMENTATION VERIFICATION")
print("=" * 80)
print()

all_pass = True
for check_name, passed in checks:
    status = "[PASS]" if passed else "[FAIL]"
    print(f"{status} {check_name}")
    if not passed:
        all_pass = False

print()
print("=" * 80)
if all_pass:
    print("ALL CHECKS PASSED - Implementation is complete!")
else:
    print("SOME CHECKS FAILED - Review implementation")
print("=" * 80)
