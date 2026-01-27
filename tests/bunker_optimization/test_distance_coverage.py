"""
Test script to verify bunker port distance coverage improvements.

This script validates that the new estimated distances significantly reduce
the fallback rate for bunker optimization.
"""

import sys
sys.path.insert(0, '.')

from src.freight_calculator import PortDistanceManager, ALL_BUNKER_PORTS

def test_bunker_port_coverage():
    """Test that all bunker ports have comprehensive coverage."""
    dm = PortDistanceManager('data/Port_Distances.csv')

    # Major load/discharge ports to test
    major_ports = [
        'KAMSAR ANCHORAGE',
        'PORT HEDLAND',
        'ITAGUAI',
        'TUBARAO',
        'DAMPIER',
        'TABONEO',
        'PONTA DA MADEIRA',
        'KRISHNAPATNAM',
        'TELUK RUBIAH',
        'MANGALORE',
        'GWANGYANG',
        'QINGDAO',
        'SHANGHAI',
        'FANGCHENG',
        'CAOFEIDIAN',
        'TIANJIN',
        'LIANYUNGANG',
        'PARADIP',
        'MUNDRA',
        'KANDLA',
        'VIZAG',
        'SALDANHA BAY',
        'ROTTERDAM',
        'VANCOUVER',
        'MAP TA PHUT',
        'XIAMEN',
        'JUBAIL',
        'PORT TALBOT',
    ]

    print("=" * 80)
    print("BUNKER PORT DISTANCE COVERAGE TEST")
    print("=" * 80)
    print()

    # Test each bunker port to all major load ports
    bunker_ports = [
        'Singapore', 'Fujairah', 'Rotterdam', 'Gibraltar',
        'Durban', 'Qingdao', 'Shanghai', 'Port Louis', 'Richards Bay'
    ]

    total_routes = 0
    found_routes = 0
    missing_routes = []

    for bunker in bunker_ports:
        bunker_found = 0
        bunker_total = 0

        for load_port in major_ports:
            bunker_total += 1
            total_routes += 1

            distance = dm.get_distance(bunker, load_port)
            if distance:
                bunker_found += 1
                found_routes += 1
            else:
                missing_routes.append((bunker, load_port))

        coverage_pct = (bunker_found / bunker_total * 100) if bunker_total > 0 else 0
        print(f"{bunker:15s}: {bunker_found:2d}/{bunker_total:2d} routes found ({coverage_pct:5.1f}%)")

    print()
    print("=" * 80)
    print(f"OVERALL COVERAGE: {found_routes}/{total_routes} routes ({found_routes/total_routes*100:.1f}%)")
    print("=" * 80)
    print()

    if missing_routes:
        print(f"Missing Routes ({len(missing_routes)}):")
        for bunker, load_port in missing_routes[:10]:  # Show first 10
            print(f"  {bunker:15s} -> {load_port}")
        if len(missing_routes) > 10:
            print(f"  ... and {len(missing_routes) - 10} more")
    else:
        print("[SUCCESS] All routes found!")

    print()

    # Test vessel positions to bunker ports
    print("=" * 80)
    print("VESSEL POSITION -> BUNKER PORT COVERAGE TEST")
    print("=" * 80)
    print()

    common_vessel_positions = [
        'MAP TA PHUT',
        'GWANGYANG',
        'PORT TALBOT',
        'JUBAIL',
        'PARADIP',
        'QINGDAO',
        'XIAMEN',
        'FANGCHENG',
        'TIANJIN',
        'VIZAG',
        'MUNDRA',
        'KANDLA',
        'ROTTERDAM',
        'SALDANHA BAY',
    ]

    vessel_total = 0
    vessel_found = 0

    for vessel_pos in common_vessel_positions:
        pos_found = 0
        pos_total = 0

        for bunker in bunker_ports:
            pos_total += 1
            vessel_total += 1

            distance = dm.get_distance(vessel_pos, bunker)
            if distance:
                pos_found += 1
                vessel_found += 1

        coverage_pct = (pos_found / pos_total * 100) if pos_total > 0 else 0
        print(f"{vessel_pos:20s}: {pos_found:1d}/{pos_total:1d} bunker ports reachable ({coverage_pct:5.1f}%)")

    print()
    print("=" * 80)
    print(f"OVERALL COVERAGE: {vessel_found}/{vessel_total} routes ({vessel_found/vessel_total*100:.1f}%)")
    print("=" * 80)
    print()

    # Summary
    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"Total Bunker -> Load Port Coverage:     {found_routes}/{total_routes} ({found_routes/total_routes*100:.1f}%)")
    print(f"Total Vessel -> Bunker Port Coverage:   {vessel_found}/{vessel_total} ({vessel_found/vessel_total*100:.1f}%)")
    print()

    overall_total = total_routes + vessel_total
    overall_found = found_routes + vessel_found
    print(f"COMBINED COVERAGE:                       {overall_found}/{overall_total} ({overall_found/overall_total*100:.1f}%)")
    print()

    if overall_found / overall_total >= 0.90:
        print("[EXCELLENT] Coverage >90% - Fallback rate should be <10%")
    elif overall_found / overall_total >= 0.75:
        print("[GOOD] Coverage >75% - Fallback rate should be <25%")
    elif overall_found / overall_total >= 0.50:
        print("[MODERATE] Coverage >50% - Fallback rate ~50%")
    else:
        print("[LOW] Coverage <50% - High fallback rate expected")

    print("=" * 80)

if __name__ == '__main__':
    test_bunker_port_coverage()
