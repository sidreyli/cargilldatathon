# Bunkering Stop Costs Implementation

## Overview

Successfully implemented accurate bunkering stop costs per Cargill FAQ Q9/Q3. The system now accounts for the costs of stopping at a bunkering port when vessels need to refuel beyond their remaining on board (ROB) inventory.

## Implementation Date
2026-01-27

## What Was Added

### 1. New Fields in VoyageResult

```python
# Bunkering stop information
num_bunkering_stops: int           # Number of bunkering stops (0 or 1)
extra_bunkering_days: float        # Extra voyage days due to bunkering
bunkering_lumpsum_fee: float       # $5,000 lumpsum fee
extra_mgo_for_bunker: float        # Additional MGO consumed during bunker stop
```

### 2. Configuration Constant

```python
bunker_threshold_mt: float = 50.0  # Minimum fuel to trigger bunkering stop
```

**Rationale**: Vessels don't stop at port for tiny fuel amounts. A 50 MT threshold represents a realistic minimum bunker order (~$30K value at typical prices).

### 3. Bunkering Logic

When total bunker needed (VLSFO + MGO) exceeds 50 MT:
1. **Extra voyage time**: +1.0 day
2. **Idle MGO consumption**: 1.0 day × vessel's port_idle_mgo rate
3. **Lumpsum fee**: $5,000 to bunkering port
4. **Cascading cost impacts**:
   - Hire cost increases (1 extra day × hire rate)
   - MGO bunker cost increases (extra idle consumption)
   - Total costs include bunkering lumpsum fee

## Cost Impact Example

**Vessel**: ANN BELL (hire: $11,750/day, idle MGO: 2.0 MT/day)
**Bunkering stop costs**:
- Hire cost: +$11,750 (1 day)
- MGO cost: +$1,666 (2.0 MT × $833/MT)
- Lumpsum fee: +$5,000
- **Total**: ~$18,416 per bunkering stop

## Files Modified

| File | Changes | Lines |
|------|---------|-------|
| `src/freight_calculator.py` | Add VoyageResult fields | After line 187 |
| `src/freight_calculator.py` | Add VoyageConfig constant | After line 104 |
| `src/freight_calculator.py` | Insert bunkering logic | After line 767 |
| `src/freight_calculator.py` | Update total_costs | Line 797 |
| `src/freight_calculator.py` | Update VoyageResult return | Before line 861 |

**Total**: 1 file, 5 modification points

## Test Results

### All Vessel-Cargo Combinations (Cargill Fleet)

All 12 combinations trigger bunkering stops (all need >50 MT fuel):

| Vessel | Cargo | Bunker Needed | Bunkering Stop? |
|--------|-------|---------------|-----------------|
| ANN BELL | EGA Bauxite | 3,553.4 MT | YES |
| ANN BELL | BHP Iron Ore | 831.3 MT | YES |
| ANN BELL | CSN Iron Ore | 3,625.8 MT | YES |
| OCEAN HORIZON | EGA Bauxite | 3,391.5 MT | YES |
| OCEAN HORIZON | BHP Iron Ore | 832.6 MT | YES |
| OCEAN HORIZON | CSN Iron Ore | 3,908.4 MT | YES |
| PACIFIC GLORY | EGA Bauxite | 3,318.5 MT | YES |
| PACIFIC GLORY | BHP Iron Ore | 594.1 MT | YES |
| PACIFIC GLORY | CSN Iron Ore | 3,402.2 MT | YES |
| GOLDEN ASCENT | EGA Bauxite | 3,028.9 MT | YES |
| GOLDEN ASCENT | BHP Iron Ore | 364.6 MT | YES |
| GOLDEN ASCENT | CSN Iron Ore | 3,093.7 MT | YES |

### Detailed Test Case: OCEAN HORIZON on CSN Cargo

```
Vessel: OCEAN HORIZON
Cargo: CSN Iron Ore (Brazil-China)
Total voyage days: 80.68

Fuel Consumption:
  VLSFO consumed: 4,082.61 MT
  MGO consumed: 157.68 MT
  VLSFO ROB: 265.80 MT
  MGO ROB: 64.30 MT

Bunker Needed:
  VLSFO needed: 3,816.81 MT
  MGO needed: 91.58 MT
  Total needed: 3,908.39 MT

========================================
BUNKERING STOP TRIGGERED: True
========================================
  Bunkering stops: 1
  Extra days: 1.00
  Extra MGO consumed: 1.80 MT
  Lumpsum fee: $5,000.00

Total Costs Breakdown:
  Bunker cost: $2,033,390.48
  Hire cost: $1,270,655.66 (includes 1 extra day)
  Port costs: $165,000.00
  Misc costs: $15,000.00
  Bunkering lumpsum: $5,000.00
  -------------------------
  TOTAL: $3,489,046.15
```

## Optimizer Impact

### New Portfolio Profit: $5,779,571

After implementing bunkering costs, the portfolio optimizer still achieves strong profitability:

**Assignments**:
- ANN BELL → Vale Malaysia ($915,509)
- OCEAN HORIZON → BHP S.Korea ($326,992)
- PACIFIC GLORY → Teck Coal ($708,408)
- GOLDEN ASCENT → Adaro Coal ($1,169,745)

**Market Vessels Hired**:
- IRON CENTURY → EGA Bauxite
- ATLANTIC FORTUNE → BHP Australia-China
- CORAL EMPEROR → CSN Iron Ore

## Accuracy Improvement

**Before**: Bunkering stops were "free" (only fuel purchase tracked)
**After**: Each bunkering stop correctly adds ~$15-20K depending on vessel

**Financial Impact**:
- More accurate voyage cost modeling
- Better reflects real-world shipping operations
- Closes gap identified in FAQ Q9/Q3 analysis

## Edge Cases Handled

| Scenario | Bunker Needed | Behavior |
|----------|---------------|----------|
| Small need (5 MT) | 5 MT | No bunkering stop (< 50 MT threshold) |
| Sufficient ROB | 0 MT | No bunkering stop |
| Only VLSFO (100 MT) | 100 MT VLSFO | Bunkering stop triggered |
| Only MGO (75 MT) | 75 MT MGO | Bunkering stop triggered |
| Edge (50 MT exactly) | 50 MT | No bunkering (threshold is `> 50`) |
| Edge (50.1 MT) | 50.1 MT | Bunkering stop triggered |

## Code Location

**Primary implementation**: `src/freight_calculator.py:765-815`

**Key logic**:
```python
total_bunker_needed = bunker_needed_vlsfo + bunker_needed_mgo
needs_bunkering = total_bunker_needed > self.config.bunker_threshold_mt
num_bunkering_stops = 1 if needs_bunkering else 0

if needs_bunkering:
    extra_bunkering_days = 1.0
    extra_mgo_for_bunker = 1.0 * vessel.port_idle_mgo
    bunkering_lumpsum_fee = 5000.0

    # Update voyage variables
    idle_days += extra_bunkering_days
    mgo_idle += extra_mgo_for_bunker
    mgo_consumed += extra_mgo_for_bunker
    total_days += extra_bunkering_days

    # Recalculate costs
    bunker_cost_mgo = mgo_consumed * mgo_price
    total_bunker_cost = bunker_cost_vlsfo + bunker_cost_mgo
```

## Verification

✅ VoyageResult has 4 new fields
✅ VoyageConfig has `bunker_threshold_mt = 50.0`
✅ Bunkering logic inserted after bunker_needed calculation
✅ `total_costs` includes `bunkering_lumpsum_fee`
✅ VoyageResult construction includes new fields
✅ All variables updated in correct order
✅ No syntax errors
✅ Optimizer runs successfully
✅ Sample voyage results show bunkering fields
✅ Profit values change appropriately when bunkering triggered

## References

- **Cargill FAQ Q9/Q3**: Bunkering stop costs clarification
- **Implementation Plan**: `PLAN.md` (if exists)
- **Test Scripts**:
  - `scripts/test_bunkering.py` - Comprehensive verification
  - `scripts/test_bunkering_cost.py` - Cost calculation verification

## Next Steps

Consider future enhancements:
1. **Multiple bunkering stops**: For extremely long voyages
2. **Regional bunker prices**: Use actual bunker port prices instead of load port proxy
3. **Bunker port selection**: Optimize which port to stop at (currently implicit)
4. **Dynamic threshold**: Adjust 50 MT threshold based on route economics

---

**Implementation Status**: ✅ Complete and verified
**Date**: 2026-01-27
**Impact**: More accurate voyage costing, ~$15-20K per bunkering stop
