"""
Cargill Ocean Transportation Datathon 2026 - Freight Calculator
================================================================
A professional freight calculator for Capesize vessel voyage analysis.

This module calculates:
- Voyage duration (ballast + laden legs)
- Fuel consumption (at sea and in port)
- All costs (bunker, hire, port, commissions)
- Revenue and profit
- Time Charter Equivalent (TCE)
"""

import pandas as pd
import numpy as np
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Tuple, Set
from datetime import datetime, timedelta


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class Vessel:
    """Represents a Capesize vessel with all operational parameters."""
    name: str
    dwt: int                          # Deadweight tonnage
    hire_rate: float                  # USD per day
    
    # Speed in knots
    speed_laden: float
    speed_ballast: float
    speed_laden_eco: float
    speed_ballast_eco: float
    
    # Fuel consumption (MT per day)
    fuel_laden_vlsfo: float
    fuel_laden_mgo: float
    fuel_ballast_vlsfo: float
    fuel_ballast_mgo: float
    fuel_laden_eco_vlsfo: float
    fuel_laden_eco_mgo: float
    fuel_ballast_eco_vlsfo: float
    fuel_ballast_eco_mgo: float
    
    # Port consumption (vessels consume MGO at port, not VLSFO)
    port_idle_mgo: float
    port_working_mgo: float
    
    # Current position
    current_port: str
    etd: str                          # Estimated time of departure (date string)
    bunker_rob_vlsfo: float           # Remaining on board
    bunker_rob_mgo: float
    
    # Ownership flag (with default)
    is_cargill: bool = True


@dataclass
class Cargo:
    """Represents a cargo with loading/discharge specifications."""
    name: str
    customer: str
    commodity: str
    quantity: int                     # MT
    quantity_tolerance: float         # e.g., 0.10 for +/- 10%
    
    # Dates
    laycan_start: str                 # Loading window start
    laycan_end: str                   # Loading window end
    
    # Freight
    freight_rate: float               # USD per MT
    
    # Load port
    load_port: str
    load_rate: int                    # MT per day (PWWD SHINC)
    load_turn_time: float             # hours
    
    # Discharge port
    discharge_port: str
    discharge_rate: int               # MT per day
    discharge_turn_time: float        # hours
    
    # Costs
    port_cost_load: float             # USD
    port_cost_discharge: float        # USD
    commission: float                 # As decimal (e.g., 0.0375 for 3.75%)
    
    # Fields with defaults must come last
    is_cargill: bool = True
    half_freight_threshold: Optional[int] = None  # If cargo > this, half freight applies


@dataclass
class VoyageConfig:
    """Configuration constants for voyage calculations."""
    misc_costs: float = 15000  # Typical for Capesize (canal fees, surveys, etc.)
    vessel_constants: float = 3500  # Reserve for bunkers/stores on vessel (MT)
    port_delay_load_fraction: float = 0.5  # Fraction of extra delay at load port
    min_voyage_days: float = 0.001  # Minimum days to avoid division by zero
    bunker_threshold_mt: float = 50.0  # Minimum fuel to trigger bunkering stop


@dataclass
class BunkerPrices:
    """Bunker prices at various ports."""
    prices: Dict[str, Dict[str, float]] = field(default_factory=dict)
    
    def get_price(self, port: str, fuel_type: str = 'VLSFO') -> float:
        """Get bunker price at port, with fallback to Singapore."""
        port_upper = port.upper()
        
        # Direct match
        for p, prices in self.prices.items():
            if p.upper() in port_upper or port_upper in p.upper():
                return prices.get(fuel_type, prices.get('VLSFO', 490))
        
        # Regional fallback
        if any(x in port_upper for x in ['CHINA', 'QINGDAO', 'FANGCHENG', 'CAOFEIDIAN', 'LIANYUNGANG']):
            return self.prices.get('Qingdao', {}).get(fuel_type, 643)
        if any(x in port_upper for x in ['SINGAPORE', 'THAILAND', 'MAP TA PHUT']):
            return self.prices.get('Singapore', {}).get(fuel_type, 490)
        if any(x in port_upper for x in ['AUSTRALIA', 'HEDLAND', 'DAMPIER']):
            return self.prices.get('Singapore', {}).get(fuel_type, 490)
        if any(x in port_upper for x in ['BRAZIL', 'ITAGUAI', 'TUBARAO', 'MADEIRA']):
            return self.prices.get('Gibraltar', {}).get(fuel_type, 474)
        if any(x in port_upper for x in ['GUINEA', 'KAMSAR', 'AFRICA']):
            return self.prices.get('Gibraltar', {}).get(fuel_type, 474)
        if any(x in port_upper for x in ['INDIA', 'PARADIP', 'MUNDRA', 'KANDLA']):
            return self.prices.get('Fujairah', {}).get(fuel_type, 478)
        
        # Default to Singapore
        return self.prices.get('Singapore', {}).get(fuel_type, 490)


# All available bunkering ports (evaluate all candidates for each voyage)
ALL_BUNKER_PORTS = [
    'Singapore',      # SE Asia hub
    'Fujairah',       # Middle East hub
    'Rotterdam',      # NW Europe hub
    'Gibraltar',      # Med/Atlantic hub
    'Durban',         # Southern Africa hub
    'Qingdao',        # China hub
    'Shanghai',       # China hub
    'Port Louis',     # Indian Ocean hub
    'Richards Bay',   # South African hub
]


def get_bunker_candidates(vessel_port: str, load_port: str) -> List[str]:
    """
    Get all bunker port candidates.
    Returns all 9 ports for comprehensive optimization.
    """
    return ALL_BUNKER_PORTS


@dataclass
class VoyageResult:
    """Results of a voyage calculation."""
    vessel_name: str
    cargo_name: str
    
    # Timing
    ballast_days: float
    laden_days: float
    load_days: float
    discharge_days: float
    total_days: float
    
    # Can vessel make the laycan?
    arrival_date: datetime
    laycan_start: datetime
    laycan_end: datetime
    can_make_laycan: bool
    waiting_days: float
    
    # Cargo
    cargo_quantity: int
    
    # Revenue
    gross_freight: float
    commission_cost: float
    net_freight: float
    
    # Costs
    bunker_cost_vlsfo: float
    bunker_cost_mgo: float
    total_bunker_cost: float
    hire_cost: float
    port_costs: float
    misc_costs: float
    total_costs: float
    
    # Profit metrics
    gross_profit: float
    net_profit: float
    tce: float                        # Time Charter Equivalent
    
    # Fuel consumption
    vlsfo_consumed: float
    mgo_consumed: float
    
    # Bunker status
    bunker_needed_vlsfo: float
    bunker_needed_mgo: float

    # Bunkering stop information
    num_bunkering_stops: int
    extra_bunkering_days: float
    bunkering_lumpsum_fee: float
    extra_mgo_for_bunker: float

    # Explicit bunkering port routing
    selected_bunker_port: Optional[str]          # Which port was selected
    bunker_port_savings: float                   # Savings vs worst option
    ballast_leg_to_bunker: float                 # Distance: current → bunker (nm)
    bunker_to_load_leg: float                    # Distance: bunker → load (nm)
    direct_ballast_distance: float               # Original: current → load (nm)
    bunker_fuel_vlsfo_qty: float                 # VLSFO quantity purchased (MT)
    bunker_fuel_mgo_qty: float                   # MGO quantity purchased (MT)


# =============================================================================
# PORT DISTANCE MANAGER
# =============================================================================

import warnings
import logging

# Configure logging for distance lookups
logging.basicConfig(level=logging.INFO)
distance_logger = logging.getLogger('PortDistanceManager')


class DistanceSource:
    """Enum-like class for distance sources."""
    CSV = 'CSV'
    CSV_REVERSE = 'CSV_REVERSE'
    ESTIMATE = 'ESTIMATE'
    NOT_FOUND = 'NOT_FOUND'


class PortDistanceManager:
    """
    Manages port-to-port distance lookups with fuzzy matching.

    Lookup priority:
    1. CSV file (direct match)
    2. CSV file (reverse direction)
    3. Estimated distances (hardcoded fallback)

    Logging:
    - INFO: When estimated distances are used
    - WARNING: When no distance is found
    """

    def __init__(self, csv_path: str = 'Port_Distances.csv', verbose: bool = False):
        self.verbose = verbose
        self.df = pd.read_csv(csv_path)
        self.df['PORT_NAME_FROM'] = self.df['PORT_NAME_FROM'].str.upper()
        self.df['PORT_NAME_TO'] = self.df['PORT_NAME_TO'].str.upper()

        # Build lookup dict for speed
        self.distances = {}
        for _, row in self.df.iterrows():
            key = (row['PORT_NAME_FROM'], row['PORT_NAME_TO'])
            self.distances[key] = row['DISTANCE']

        # Track usage statistics
        self._lookup_stats = {'csv': 0, 'csv_reverse': 0, 'estimate': 0, 'not_found': 0}
        self._estimate_usage = {}  # Track which estimates are actually used

        # Port name mapping for common variations
        self.port_aliases = {
            'QINGDAO': ['QINGDAO', 'DAGANG (QINGDAO)'],
            'KAMSAR': ['KAMSAR ANCHORAGE', 'PORT KAMSAR'],
            'KAMSAR ANCHORAGE': ['KAMSAR ANCHORAGE', 'PORT KAMSAR'],  # Allow both directions
            'SINGAPORE': ['SINGAPORE'],
            'PORT HEDLAND': ['PORT HEDLAND'],
            'ITAGUAI': ['ITAGUAI'],
            'TUBARAO': ['TUBARAO'],
            'GWANGYANG': ['GWANGYANG LNG TERMINAL', 'GWANGYANG'],
            'FANGCHENG': ['FANGCHENG'],
            'MAP TA PHUT': ['MAP TA PHUT'],
            'DAMPIER': ['DAMPIER'],
            'SALDANHA BAY': ['SALDANHA BAY'],
            'ROTTERDAM': ['ROTTERDAM'],
            'CAOFEIDIAN': ['CAOFEIDIAN'],
            'LIANYUNGANG': ['LIANYUNGANG'],
            'PARADIP': ['PARADIP'],
            'MUNDRA': ['MUNDRA'],
            'KANDLA': ['KANDLA'],
            'PONTA DA MADEIRA': ['PONTA DA MADEIRA', 'SAO LUIS'],
            'TIANJIN': ['TIANJIN', 'XINGANG'],
            'TABONEO': ['TABONEO'],
            'KRISHNAPATNAM': ['KRISHNAPATNAM'],
            'VANCOUVER': ['VANCOUVER', 'VANCOUVER (CANADA)'],  # Added CSV variant
            'MANGALORE': ['MANGALORE', 'NEW MANGALORE'],
            'TELUK RUBIAH': ['TELUK RUBIAH'],
            'PORT TALBOT': ['PORT TALBOT'],
            'XIAMEN': ['XIAMEN'],
            'JINGTANG': ['JINGTANG'],
            'VIZAG': ['VIZAG', 'VISAKHAPATNAM'],
            'JUBAIL': ['JUBAIL'],
            'SHANGHAI': ['SHANGHAI'],
        }
        
        # =================================================================
        # ESTIMATED DISTANCES - Only for routes NOT in Port_Distances.csv
        # =================================================================
        # These are fallback estimates used ONLY when CSV lookup fails.
        # CSV lookup takes priority and should cover most routes.
        #
        # NOTE: Estimates were validated against CSV on 2026-01-25.
        #       Routes that exist in CSV have been removed.
        #       Remaining estimates are for routes truly missing from CSV.
        # =================================================================

        self.estimated_distances = {
            # -----------------------------------------------------------------
            # MAP TA PHUT (Thailand) - Limited coverage in CSV
            # Vessel: OCEAN HORIZON starts here
            # -----------------------------------------------------------------
            ('MAP TA PHUT', 'PORT HEDLAND'): 2800,       # ~9.3 days at 12.5 kn
            ('MAP TA PHUT', 'KAMSAR ANCHORAGE'): 9500,   # ~31.7 days at 12.5 kn
            ('MAP TA PHUT', 'ITAGUAI'): 12500,           # ~41.7 days at 12.5 kn
            ('MAP TA PHUT', 'DAMPIER'): 2700,            # Similar to Port Hedland
            ('MAP TA PHUT', 'TUBARAO'): 12600,           # Similar to Itaguai
            ('MAP TA PHUT', 'SALDANHA BAY'): 6800,       # Via Indian Ocean

            # -----------------------------------------------------------------
            # GWANGYANG (S. Korea) - CSV only has LNG Terminal variant
            # Vessel: PACIFIC GLORY, MOUNTAIN TRADER start here
            # Note: PORT HEDLAND route exists via GWANGYANG LNG TERMINAL alias
            # -----------------------------------------------------------------
            ('GWANGYANG', 'KAMSAR ANCHORAGE'): 11500,    # ~38.3 days at 12.5 kn
            ('GWANGYANG', 'ITAGUAI'): 11800,             # ~39.3 days at 12.5 kn
            ('GWANGYANG', 'TUBARAO'): 11700,             # Similar to Itaguai
            ('GWANGYANG', 'SALDANHA BAY'): 9200,         # Via Indian Ocean

            # -----------------------------------------------------------------
            # PORT TALBOT (Wales, UK) - Limited coverage in CSV
            # Vessel: IRON CENTURY starts here
            # Note: ITAGUAI and TUBARAO routes exist in CSV
            # -----------------------------------------------------------------
            ('PORT TALBOT', 'KAMSAR ANCHORAGE'): 2800,   # ~9.3 days at 12.5 kn
            ('PORT TALBOT', 'PORT HEDLAND'): 11500,      # ~38.3 days at 12.5 kn
            ('PORT TALBOT', 'DAMPIER'): 11600,           # Similar to Port Hedland
            ('PORT TALBOT', 'VANCOUVER'): 7800,          # Via Atlantic/Panama

            # -----------------------------------------------------------------
            # JUBAIL (Saudi Arabia) - Limited coverage in CSV
            # Vessel: TITAN LEGACY starts here
            # Note: TUBARAO route exists in CSV
            # -----------------------------------------------------------------
            ('JUBAIL', 'KAMSAR ANCHORAGE'): 6500,        # ~21.7 days at 12.5 kn
            ('JUBAIL', 'PORT HEDLAND'): 5200,            # ~17.3 days at 12.5 kn
            ('JUBAIL', 'ITAGUAI'): 9800,                 # ~32.7 days at 12.5 kn
            ('JUBAIL', 'TABONEO'): 4500,                 # ~15 days at 12.5 kn
            ('JUBAIL', 'DAMPIER'): 5100,                 # Similar to Port Hedland

            # -----------------------------------------------------------------
            # India ports - Various coverage gaps
            # Vessels: ATLANTIC FORTUNE (Paradip), POLARIS SPIRIT (Kandla),
            #          NAVIS PRIDE (Mundra), ZENITH GLORY (Vizag)
            # -----------------------------------------------------------------
            ('PARADIP', 'PORT HEDLAND'): 4100,           # ~13.7 days at 12.5 kn
            ('PARADIP', 'KAMSAR ANCHORAGE'): 7600,       # ~25.3 days at 12.5 kn
            ('PARADIP', 'ITAGUAI'): 10200,               # ~34 days at 12.5 kn

            ('MUNDRA', 'KAMSAR ANCHORAGE'): 6200,        # ~20.7 days at 12.5 kn
            ('MUNDRA', 'PORT HEDLAND'): 4800,            # ~16 days at 12.5 kn
            ('MUNDRA', 'ITAGUAI'): 9500,                 # ~31.7 days at 12.5 kn

            ('KANDLA', 'PORT HEDLAND'): 4900,            # ~16.3 days at 12.5 kn
            ('KANDLA', 'KAMSAR ANCHORAGE'): 6100,        # ~20.3 days at 12.5 kn
            ('KANDLA', 'ITAGUAI'): 9400,                 # ~31.3 days at 12.5 kn

            # VIZAG routes - some exist in CSV, keeping only missing ones
            ('VIZAG', 'PORT HEDLAND'): 4200,             # ~14 days at 12.5 kn
            ('VIZAG', 'ITAGUAI'): 10500,                 # ~35 days at 12.5 kn

            # -----------------------------------------------------------------
            # XIAMEN (China) - Limited coverage in CSV
            # Vessel: EVEREST OCEAN starts here
            # -----------------------------------------------------------------
            ('XIAMEN', 'KAMSAR ANCHORAGE'): 12200,       # ~40.7 days at 12.5 kn

            # -----------------------------------------------------------------
            # Cargo route estimates (load port -> discharge port)
            # -----------------------------------------------------------------
            ('KAMSAR ANCHORAGE', 'MANGALORE'): 7200,     # Guinea Alumina cargo
            ('TUBARAO', 'TELUK RUBIAH'): 10800,          # Vale Malaysia cargo

            # -----------------------------------------------------------------
            # Additional market cargo routes (added based on warnings)
            # -----------------------------------------------------------------
            # TABONEO (Indonesia) routes for Adaro Coal cargo
            ('QINGDAO', 'TABONEO'): 2400,                # ~8 days at 12.5 kn
            ('GWANGYANG', 'TABONEO'): 2200,              # ~7.3 days at 12.5 kn

            # PONTA DA MADEIRA (Brazil) routes for Vale cargo
            ('MAP TA PHUT', 'PONTA DA MADEIRA'): 12600,  # ~42 days at 12.5 kn
            ('GWANGYANG', 'PONTA DA MADEIRA'): 11900,    # ~39.7 days at 12.5 kn

            # VANCOUVER (Canada) routes for Teck coal cargo
            ('MAP TA PHUT', 'VANCOUVER'): 7200,          # ~24 days at 12.5 kn

            # DAMPIER (Australia) routes for Rio Tinto cargo
            ('GWANGYANG', 'DAMPIER'): 3500,              # ~11.7 days at 12.5 kn

            # ROTTERDAM (Netherlands) market vessel position routes
            ('ROTTERDAM', 'KAMSAR ANCHORAGE'): 3200,     # ~10.7 days at 12.5 kn
            ('ROTTERDAM', 'PORT HEDLAND'): 11500,        # ~38.3 days at 12.5 kn

            # -----------------------------------------------------------------
            # Singapore hub - reference point
            # -----------------------------------------------------------------
            ('SINGAPORE', 'PORT HEDLAND'): 1678,         # Well-known route
        }

        # Pre-build normalized lookup for estimated distances
        self._normalized_estimates: Dict[Tuple[str, str], float] = {}
        for (port_from, port_to), distance in self.estimated_distances.items():
            # Add both directions
            self._normalized_estimates[(port_from.upper(), port_to.upper())] = distance
            self._normalized_estimates[(port_to.upper(), port_from.upper())] = distance
    
    def _normalize_port(self, port: str) -> List[str]:
        """Get possible port names for fuzzy matching."""
        port_upper = port.upper().strip()
        
        for standard, aliases in self.port_aliases.items():
            if any(alias in port_upper or port_upper in alias for alias in aliases):
                return [a.upper() for a in aliases]
            if standard in port_upper or port_upper in standard:
                return [a.upper() for a in aliases]
        
        return [port_upper]
    
    def get_distance(self, port_from: str, port_to: str) -> Optional[float]:
        """
        Get distance between two ports in nautical miles.

        Lookup priority:
        1. CSV direct match
        2. CSV reverse match
        3. Estimated distances (logs warning)

        Returns None if not found (logs error).
        """
        distance, source, matched_from, matched_to = self.get_distance_with_source(port_from, port_to)
        return distance

    def get_distance_with_source(self, port_from: str, port_to: str) -> Tuple[Optional[float], str, Optional[str], Optional[str]]:
        """
        Get distance with source information for auditing.

        Returns:
            Tuple of (distance, source, matched_from_port, matched_to_port)
            source is one of: 'CSV', 'CSV_REVERSE', 'ESTIMATE', 'NOT_FOUND'
        """
        from_options = self._normalize_port(port_from)
        to_options = self._normalize_port(port_to)

        # Try all combinations in main distance table
        for f in from_options:
            for t in to_options:
                # Direct lookup
                if (f, t) in self.distances:
                    self._lookup_stats['csv'] += 1
                    return self.distances[(f, t)], DistanceSource.CSV, f, t
                # Reverse lookup
                if (t, f) in self.distances:
                    self._lookup_stats['csv_reverse'] += 1
                    return self.distances[(t, f)], DistanceSource.CSV_REVERSE, t, f

        # Check pre-normalized estimated distances (O(1) lookup per combination)
        for f in from_options:
            for t in to_options:
                if (f, t) in self._normalized_estimates:
                    self._lookup_stats['estimate'] += 1
                    # Track which estimates are being used
                    key = (port_from.upper(), port_to.upper())
                    self._estimate_usage[key] = self._estimate_usage.get(key, 0) + 1

                    if self.verbose:
                        distance_logger.info(
                            f"Using ESTIMATED distance: {port_from} -> {port_to} = "
                            f"{self._normalized_estimates[(f, t)]:,.0f} nm (not in CSV)"
                        )
                    return self._normalized_estimates[(f, t)], DistanceSource.ESTIMATE, f, t

        # Not found
        self._lookup_stats['not_found'] += 1
        distance_logger.warning(f"Distance NOT FOUND: {port_from} -> {port_to}")
        return None, DistanceSource.NOT_FOUND, None, None

    def get_lookup_stats(self) -> Dict:
        """Get statistics on distance lookup sources."""
        total = sum(self._lookup_stats.values())
        return {
            'total_lookups': total,
            'csv_lookups': self._lookup_stats['csv'],
            'csv_reverse_lookups': self._lookup_stats['csv_reverse'],
            'estimate_lookups': self._lookup_stats['estimate'],
            'not_found': self._lookup_stats['not_found'],
            'estimates_used': dict(self._estimate_usage),
        }

    def print_lookup_report(self):
        """Print a summary report of distance lookup sources."""
        stats = self.get_lookup_stats()
        print("\n" + "=" * 60)
        print("DISTANCE LOOKUP AUDIT REPORT")
        print("=" * 60)
        print(f"Total lookups:        {stats['total_lookups']}")
        print(f"  CSV (direct):       {stats['csv_lookups']}")
        print(f"  CSV (reverse):      {stats['csv_reverse_lookups']}")
        print(f"  Estimates used:     {stats['estimate_lookups']}")
        print(f"  Not found:          {stats['not_found']}")

        if stats['estimates_used']:
            print("\nEstimated distances used:")
            for (from_p, to_p), count in sorted(stats['estimates_used'].items()):
                dist = self.get_distance(from_p, to_p)
                print(f"  {from_p} -> {to_p}: {dist:,.0f} nm (used {count}x)")

        if stats['not_found'] > 0:
            print("\n[WARNING] Some routes were not found!")
        print("=" * 60)

    def validate_port(self, port: str) -> Tuple[bool, List[str], bool]:
        """
        Validate a port name and check if it exists in CSV.

        Returns:
            Tuple of (is_valid, normalized_names, has_csv_routes)
            - is_valid: True if port has an alias mapping
            - normalized_names: List of normalized port name variants
            - has_csv_routes: True if any routes exist in CSV for this port
        """
        normalized = self._normalize_port(port)
        is_aliased = normalized != [port.upper().strip()]

        # Check if any routes exist in CSV
        has_csv_routes = False
        for norm_port in normalized:
            for (f, t) in self.distances.keys():
                if f == norm_port or t == norm_port:
                    has_csv_routes = True
                    break
            if has_csv_routes:
                break

        return is_aliased or has_csv_routes, normalized, has_csv_routes

    def validate_all_ports(self, ports: List[str]) -> Dict[str, Dict]:
        """
        Validate a list of port names.

        Returns dict with validation results for each port.
        """
        results = {}
        for port in ports:
            is_valid, normalized, has_csv = self.validate_port(port)
            results[port] = {
                'is_valid': is_valid,
                'normalized': normalized,
                'has_csv_routes': has_csv,
                'status': 'OK' if has_csv else ('ALIAS_ONLY' if is_valid else 'UNKNOWN')
            }
        return results

    def print_port_validation_report(self, ports: List[str]):
        """Print a validation report for the given ports."""
        results = self.validate_all_ports(ports)

        print("\n" + "=" * 60)
        print("PORT NAME VALIDATION REPORT")
        print("=" * 60)

        ok_ports = [p for p, r in results.items() if r['status'] == 'OK']
        alias_ports = [p for p, r in results.items() if r['status'] == 'ALIAS_ONLY']
        unknown_ports = [p for p, r in results.items() if r['status'] == 'UNKNOWN']

        print(f"\nValidated ports: {len(ok_ports)}")
        for port in ok_ports:
            norm = results[port]['normalized']
            print(f"  [OK] {port} -> {norm}")

        if alias_ports:
            print(f"\nAlias-only ports (may need estimates): {len(alias_ports)}")
            for port in alias_ports:
                norm = results[port]['normalized']
                print(f"  [ALIAS] {port} -> {norm}")

        if unknown_ports:
            print(f"\n[WARNING] Unknown ports: {len(unknown_ports)}")
            for port in unknown_ports:
                print(f"  [?] {port}")

        print("=" * 60)


# =============================================================================
# FREIGHT CALCULATOR
# =============================================================================

class FreightCalculator:
    """
    Professional freight calculator for Capesize voyage analysis.

    Calculates voyage economics including:
    - Duration (steaming, port time)
    - Fuel consumption and costs
    - Revenue and commissions
    - Time Charter Equivalent (TCE)
    """

    def __init__(
        self,
        distance_manager: PortDistanceManager,
        bunker_prices: BunkerPrices,
        config: Optional[VoyageConfig] = None,
    ):
        self.distances = distance_manager
        self.bunker_prices = bunker_prices
        self.config = config or VoyageConfig()

    def _parse_date(self, date_str: str, field_name: str) -> datetime:
        """Parse a date string with helpful error message."""
        try:
            return datetime.strptime(date_str, '%d %b %Y')
        except ValueError as e:
            raise ValueError(
                f"Invalid date format for {field_name}: '{date_str}'. "
                f"Expected format: 'DD Mon YYYY' (e.g., '25 Feb 2026'). Error: {e}"
            )

    def find_optimal_bunker_port(
        self,
        vessel: Vessel,
        cargo: Cargo,
        bunker_needed_vlsfo: float,
        bunker_needed_mgo: float,
        current_speed_ballast: float,
        fuel_consumption_rate_vlsfo: float,  # MT/day at sea
        fuel_consumption_rate_mgo: float,
        hire_rate: float,
    ) -> Tuple[Optional[str], float, float, float, float]:
        """
        Find optimal bunkering port for the voyage.

        Returns:
            (selected_port, leg1_distance, leg2_distance, savings, bunker_cost)
        """
        # Get direct distance baseline
        direct_distance = self.distances.get_distance(vessel.current_port, cargo.load_port)
        if not direct_distance:
            # Fallback: assume bunkering at load port
            return None, 0, direct_distance or 0, 0, 0

        # Get candidate bunker ports (all 9 ports)
        candidates = get_bunker_candidates(vessel.current_port, cargo.load_port)

        # Baseline: bunker at load port (current behavior)
        load_port_vlsfo_price = self.bunker_prices.get_price(cargo.load_port, 'VLSFO')
        load_port_mgo_price = self.bunker_prices.get_price(cargo.load_port, 'MGO')
        baseline_cost = (
            bunker_needed_vlsfo * load_port_vlsfo_price +
            bunker_needed_mgo * load_port_mgo_price +
            5000.0  # Lumpsum fee
        )

        # Evaluate each candidate
        best_port = None
        best_cost = baseline_cost
        best_leg1 = 0
        best_leg2 = direct_distance
        best_bunker_cost = baseline_cost

        for bunker_port in candidates:
            # Calculate route distances
            leg1 = self.distances.get_distance(vessel.current_port, bunker_port)
            leg2 = self.distances.get_distance(bunker_port, cargo.load_port)

            if not leg1 or not leg2:
                continue  # Skip if distances unavailable

            # Calculate detour distance (can be negative if bunker port is on the way)
            detour_distance = (leg1 + leg2) - direct_distance

            # Get bunker prices at this port
            vlsfo_price = self.bunker_prices.get_price(bunker_port, 'VLSFO')
            mgo_price = self.bunker_prices.get_price(bunker_port, 'MGO')

            # Cost components
            bunker_fuel_cost = (
                bunker_needed_vlsfo * vlsfo_price +
                bunker_needed_mgo * mgo_price
            )
            lumpsum_fee = 5000.0

            # Detour costs (if detour > 0)
            if detour_distance > 0:
                detour_days = detour_distance / (current_speed_ballast * 24)
                detour_fuel_cost = (
                    detour_days * fuel_consumption_rate_vlsfo * vlsfo_price +
                    detour_days * fuel_consumption_rate_mgo * mgo_price
                )
                detour_hire_cost = detour_days * hire_rate
            else:
                # Negative detour = bunker port is on the way (saves distance)
                detour_days = detour_distance / (current_speed_ballast * 24)  # Negative
                detour_fuel_cost = (
                    detour_days * fuel_consumption_rate_vlsfo * vlsfo_price +
                    detour_days * fuel_consumption_rate_mgo * mgo_price
                )  # Negative (savings)
                detour_hire_cost = detour_days * hire_rate  # Negative (savings)

            # Total cost
            total_cost = bunker_fuel_cost + lumpsum_fee + detour_fuel_cost + detour_hire_cost

            # Select if better (or equal cost but closer distance - tiebreaker)
            if total_cost < best_cost or (
                abs(total_cost - best_cost) < 1000 and  # Within $1K
                (leg1 + leg2) < (best_leg1 + best_leg2)
            ):
                best_cost = total_cost
                best_port = bunker_port
                best_leg1 = leg1
                best_leg2 = leg2
                best_bunker_cost = bunker_fuel_cost + lumpsum_fee

        # Calculate savings vs baseline
        savings = baseline_cost - best_cost

        return best_port, best_leg1, best_leg2, savings, best_bunker_cost
    
    def calculate_voyage(
        self,
        vessel: Vessel,
        cargo: Cargo,
        use_eco_speed: bool = False,
        extra_port_delay_days: float = 0,
        bunker_price_adjustment: float = 1.0,  # Multiplier for scenario analysis
        custom_ballast_distance: Optional[float] = None,
        custom_laden_distance: Optional[float] = None,
    ) -> VoyageResult:
        """
        Calculate complete voyage economics.
        
        Args:
            vessel: Vessel object with all specs
            cargo: Cargo object with all requirements
            use_eco_speed: Whether to use economical speed (slower, less fuel)
            extra_port_delay_days: Additional port delay for scenario analysis
            bunker_price_adjustment: Multiplier for bunker prices (1.1 = +10%)
            custom_ballast_distance: Override ballast leg distance
            custom_laden_distance: Override laden leg distance
        
        Returns:
            VoyageResult with all calculated values
        """
        
        # -----------------------------------------------------------------
        # 1. DISTANCES
        # -----------------------------------------------------------------
        if custom_ballast_distance:
            ballast_distance = custom_ballast_distance
        else:
            ballast_distance = self.distances.get_distance(vessel.current_port, cargo.load_port)
            if ballast_distance is None:
                raise ValueError(f"Cannot find distance: {vessel.current_port} → {cargo.load_port}")
        
        if custom_laden_distance:
            laden_distance = custom_laden_distance
        else:
            laden_distance = self.distances.get_distance(cargo.load_port, cargo.discharge_port)
            if laden_distance is None:
                raise ValueError(f"Cannot find distance: {cargo.load_port} → {cargo.discharge_port}")
        
        # -----------------------------------------------------------------
        # 2. SPEEDS AND STEAMING TIMES
        # -----------------------------------------------------------------
        if use_eco_speed:
            speed_ballast = vessel.speed_ballast_eco
            speed_laden = vessel.speed_laden_eco
            fuel_ballast_vlsfo = vessel.fuel_ballast_eco_vlsfo
            fuel_ballast_mgo = vessel.fuel_ballast_eco_mgo
            fuel_laden_vlsfo = vessel.fuel_laden_eco_vlsfo
            fuel_laden_mgo = vessel.fuel_laden_eco_mgo
        else:
            speed_ballast = vessel.speed_ballast
            speed_laden = vessel.speed_laden
            fuel_ballast_vlsfo = vessel.fuel_ballast_vlsfo
            fuel_ballast_mgo = vessel.fuel_ballast_mgo
            fuel_laden_vlsfo = vessel.fuel_laden_vlsfo
            fuel_laden_mgo = vessel.fuel_laden_mgo
        
        # Steaming time in days
        ballast_days = ballast_distance / (speed_ballast * 24)
        laden_days = laden_distance / (speed_laden * 24)
        
        # -----------------------------------------------------------------
        # 3. CARGO QUANTITY (considering DWT and tolerance)
        # -----------------------------------------------------------------
        # Owner's option: can load up to quantity * (1 + tolerance)
        # But limited by vessel capacity (DWT minus bunkers/stores/constants)
        max_by_cargo = int(cargo.quantity * (1 + cargo.quantity_tolerance))
        min_by_cargo = int(cargo.quantity * (1 - cargo.quantity_tolerance))
        max_by_vessel = vessel.dwt - self.config.vessel_constants

        # Maximize cargo within constraints (owner's option to load more)
        total_cargo_qty = min(max_by_cargo, max_by_vessel)

        # Ensure we meet minimum cargo requirement
        if total_cargo_qty < min_by_cargo:
            raise ValueError(f"Vessel {vessel.name} cannot meet minimum cargo requirement for {cargo.name}")

        # Check half freight threshold - split into full rate and half rate quantities
        full_freight_qty = total_cargo_qty
        half_freight_qty = 0
        if cargo.half_freight_threshold and total_cargo_qty > cargo.half_freight_threshold:
            full_freight_qty = cargo.half_freight_threshold
            half_freight_qty = total_cargo_qty - cargo.half_freight_threshold
        
        # -----------------------------------------------------------------
        # 4. PORT TIME
        # -----------------------------------------------------------------
        # Loading time = cargo / load_rate + turn_time
        load_days = total_cargo_qty / cargo.load_rate + cargo.load_turn_time / 24

        # Discharge time = cargo / discharge_rate + turn_time
        discharge_days = total_cargo_qty / cargo.discharge_rate + cargo.discharge_turn_time / 24

        # Add scenario delay (configurable split between load/discharge ports)
        load_delay_fraction = self.config.port_delay_load_fraction
        load_days += extra_port_delay_days * load_delay_fraction
        discharge_days += extra_port_delay_days * (1 - load_delay_fraction)
        
        # -----------------------------------------------------------------
        # 5. LAYCAN CHECK
        # -----------------------------------------------------------------
        etd = self._parse_date(vessel.etd, f"vessel {vessel.name} ETD")
        arrival_at_loadport = etd + timedelta(days=ballast_days)
        laycan_start = self._parse_date(cargo.laycan_start, f"cargo {cargo.name} laycan_start")
        laycan_end = self._parse_date(cargo.laycan_end, f"cargo {cargo.name} laycan_end")
        
        can_make_laycan = arrival_at_loadport <= laycan_end
        
        # Waiting time if arrive early (in fractional days for precision)
        waiting_days = 0.0
        if arrival_at_loadport < laycan_start:
            waiting_days = (laycan_start - arrival_at_loadport).total_seconds() / 86400
        
        # -----------------------------------------------------------------
        # 6. TOTAL VOYAGE DURATION
        # -----------------------------------------------------------------
        total_days = ballast_days + waiting_days + load_days + laden_days + discharge_days
        
        # -----------------------------------------------------------------
        # 7. FUEL CONSUMPTION
        # -----------------------------------------------------------------
        # At sea - ballast
        vlsfo_ballast = ballast_days * fuel_ballast_vlsfo
        mgo_ballast = ballast_days * fuel_ballast_mgo
        
        # At sea - laden
        vlsfo_laden = laden_days * fuel_laden_vlsfo
        mgo_laden = laden_days * fuel_laden_mgo
        
        # In port - working (vessels consume MGO at port)
        working_days = load_days + discharge_days - (cargo.load_turn_time + cargo.discharge_turn_time) / 24
        mgo_working = working_days * vessel.port_working_mgo

        # In port - idle (waiting + turn times)
        idle_days = waiting_days + (cargo.load_turn_time + cargo.discharge_turn_time) / 24
        mgo_idle = idle_days * vessel.port_idle_mgo

        # Total fuel
        # Port consumption uses MGO (not VLSFO) per Cargill operational requirements
        vlsfo_consumed = vlsfo_ballast + vlsfo_laden
        mgo_consumed = mgo_ballast + mgo_laden + mgo_working + mgo_idle
        
        # -----------------------------------------------------------------
        # 8. BUNKER COSTS
        # -----------------------------------------------------------------
        # Get bunker prices (use load port region for simplicity)
        vlsfo_price = self.bunker_prices.get_price(cargo.load_port, 'VLSFO') * bunker_price_adjustment
        mgo_price = self.bunker_prices.get_price(cargo.load_port, 'MGO') * bunker_price_adjustment
        
        bunker_cost_vlsfo = vlsfo_consumed * vlsfo_price
        bunker_cost_mgo = mgo_consumed * mgo_price
        total_bunker_cost = bunker_cost_vlsfo + bunker_cost_mgo
        
        # Bunker needed (vs remaining on board)
        bunker_needed_vlsfo = max(0, vlsfo_consumed - vessel.bunker_rob_vlsfo)
        bunker_needed_mgo = max(0, mgo_consumed - vessel.bunker_rob_mgo)

        # -----------------------------------------------------------------
        # 8a. EXPLICIT BUNKERING PORT ROUTING & OPTIMIZATION
        # -----------------------------------------------------------------

        total_bunker_needed = bunker_needed_vlsfo + bunker_needed_mgo
        needs_bunkering = total_bunker_needed > self.config.bunker_threshold_mt

        if needs_bunkering:
            # Find optimal bunker port
            (
                selected_bunker_port,
                leg1_distance,  # current_port → bunker_port
                leg2_distance,  # bunker_port → load_port
                bunker_savings,
                bunker_fuel_cost_at_port,
            ) = self.find_optimal_bunker_port(
                vessel=vessel,
                cargo=cargo,
                bunker_needed_vlsfo=bunker_needed_vlsfo,
                bunker_needed_mgo=bunker_needed_mgo,
                current_speed_ballast=speed_ballast,
                fuel_consumption_rate_vlsfo=fuel_ballast_vlsfo,
                fuel_consumption_rate_mgo=fuel_ballast_mgo,
                hire_rate=vessel.hire_rate,
            )

            # Update ballast distance to use explicit routing
            if selected_bunker_port:
                # Recalculate ballast leg with explicit routing
                ballast_distance = leg1_distance + leg2_distance
                ballast_days = ballast_distance / (speed_ballast * 24)

                # Recalculate ballast fuel consumption with updated distance
                vlsfo_ballast = ballast_days * fuel_ballast_vlsfo
                mgo_ballast = ballast_days * fuel_ballast_mgo

                # Update total fuel
                vlsfo_consumed = vlsfo_ballast + vlsfo_laden
                mgo_consumed = mgo_ballast + mgo_laden + mgo_working + mgo_idle

                # Recalculate bunker needs (may change slightly due to detour)
                bunker_needed_vlsfo = max(0, vlsfo_consumed - vessel.bunker_rob_vlsfo)
                bunker_needed_mgo = max(0, mgo_consumed - vessel.bunker_rob_mgo)

                # Get bunker prices at selected port
                vlsfo_price = self.bunker_prices.get_price(selected_bunker_port, 'VLSFO') * bunker_price_adjustment
                mgo_price = self.bunker_prices.get_price(selected_bunker_port, 'MGO') * bunker_price_adjustment
            else:
                # Fallback: use load port as bunker location
                selected_bunker_port = cargo.load_port
                leg1_distance = 0
                leg2_distance = ballast_distance
                bunker_savings = 0

            # Bunkering stop costs
            extra_bunkering_days = 1.0
            extra_mgo_for_bunker = 1.0 * vessel.port_idle_mgo
            bunkering_lumpsum_fee = 5000.0
            num_bunkering_stops = 1

            # Update voyage variables
            idle_days += extra_bunkering_days
            mgo_idle += extra_mgo_for_bunker
            mgo_consumed += extra_mgo_for_bunker
            total_days += extra_bunkering_days

            # Recalculate costs with selected bunker port prices
            bunker_cost_vlsfo = vlsfo_consumed * vlsfo_price
            bunker_cost_mgo = mgo_consumed * mgo_price
            total_bunker_cost = bunker_cost_vlsfo + bunker_cost_mgo

            # Store original direct distance for reporting
            direct_ballast_distance = self.distances.get_distance(
                vessel.current_port, cargo.load_port
            )
            if direct_ballast_distance is None:
                direct_ballast_distance = ballast_distance

        else:
            # No bunkering needed
            selected_bunker_port = None
            bunker_savings = 0
            leg1_distance = 0
            leg2_distance = ballast_distance
            direct_ballast_distance = ballast_distance
            extra_bunkering_days = 0.0
            extra_mgo_for_bunker = 0.0
            bunkering_lumpsum_fee = 0.0
            num_bunkering_stops = 0

        # -----------------------------------------------------------------
        # 9. REVENUE
        # -----------------------------------------------------------------
        gross_freight = full_freight_qty * cargo.freight_rate
        if half_freight_qty > 0:
            gross_freight += half_freight_qty * cargo.freight_rate * 0.5

        commission_cost = gross_freight * cargo.commission
        net_freight = gross_freight - commission_cost

        # -----------------------------------------------------------------
        # 10. OTHER COSTS
        # -----------------------------------------------------------------
        # Hire cost (only for Cargill vessels with hire rate)
        if vessel.is_cargill:
            hire_cost = total_days * vessel.hire_rate
        else:
            hire_cost = 0  # Market vessel - hire handled separately

        # Port costs
        port_costs = cargo.port_cost_load + cargo.port_cost_discharge

        # Miscellaneous (canal fees, surveys, etc.)
        misc_costs = self.config.misc_costs
        
        # -----------------------------------------------------------------
        # 11. PROFIT CALCULATION
        # -----------------------------------------------------------------
        total_costs = total_bunker_cost + hire_cost + port_costs + misc_costs + bunkering_lumpsum_fee
        
        # Gross profit (before hire)
        gross_profit = net_freight - total_bunker_cost - port_costs - misc_costs
        
        # Net profit (after hire) - for Cargill vessels
        net_profit = net_freight - total_costs
        
        # -----------------------------------------------------------------
        # 12. TCE (Time Charter Equivalent)
        # -----------------------------------------------------------------
        # TCE = (Net Freight - Voyage Costs) / Total Days
        # Voyage costs = bunker + port costs (exclude hire)
        voyage_costs = total_bunker_cost + port_costs + misc_costs
        tce = (net_freight - voyage_costs) / total_days if total_days > self.config.min_voyage_days else 0
        
        # -----------------------------------------------------------------
        # 13. BUILD RESULT
        # -----------------------------------------------------------------
        return VoyageResult(
            vessel_name=vessel.name,
            cargo_name=cargo.name,
            
            # Timing
            ballast_days=round(ballast_days, 2),
            laden_days=round(laden_days, 2),
            load_days=round(load_days, 2),
            discharge_days=round(discharge_days, 2),
            total_days=round(total_days, 2),
            
            # Laycan
            arrival_date=arrival_at_loadport,
            laycan_start=laycan_start,
            laycan_end=laycan_end,
            can_make_laycan=can_make_laycan,
            waiting_days=round(waiting_days, 2),
            
            # Cargo
            cargo_quantity=total_cargo_qty,
            
            # Revenue
            gross_freight=round(gross_freight, 2),
            commission_cost=round(commission_cost, 2),
            net_freight=round(net_freight, 2),
            
            # Costs
            bunker_cost_vlsfo=round(bunker_cost_vlsfo, 2),
            bunker_cost_mgo=round(bunker_cost_mgo, 2),
            total_bunker_cost=round(total_bunker_cost, 2),
            hire_cost=round(hire_cost, 2),
            port_costs=round(port_costs, 2),
            misc_costs=round(misc_costs, 2),
            total_costs=round(total_costs, 2),
            
            # Profit
            gross_profit=round(gross_profit, 2),
            net_profit=round(net_profit, 2),
            tce=round(tce, 2),
            
            # Fuel
            vlsfo_consumed=round(vlsfo_consumed, 2),
            mgo_consumed=round(mgo_consumed, 2),
            bunker_needed_vlsfo=round(bunker_needed_vlsfo, 2),
            bunker_needed_mgo=round(bunker_needed_mgo, 2),

            # Bunkering stop information
            num_bunkering_stops=num_bunkering_stops,
            extra_bunkering_days=round(extra_bunkering_days, 2),
            bunkering_lumpsum_fee=round(bunkering_lumpsum_fee, 2),
            extra_mgo_for_bunker=round(extra_mgo_for_bunker, 2),

            # Explicit bunkering port routing
            selected_bunker_port=selected_bunker_port,
            bunker_port_savings=round(bunker_savings, 2),
            ballast_leg_to_bunker=round(leg1_distance, 2),
            bunker_to_load_leg=round(leg2_distance, 2),
            direct_ballast_distance=round(direct_ballast_distance, 2),
            bunker_fuel_vlsfo_qty=round(bunker_needed_vlsfo, 2),
            bunker_fuel_mgo_qty=round(bunker_needed_mgo, 2),
        )


# =============================================================================
# DATA SETUP - CARGILL DATATHON 2026
# =============================================================================

def create_cargill_vessels() -> List[Vessel]:
    """Create Cargill's 4 Capesize vessels from the datathon data."""
    
    vessels = [
        Vessel(
            name="ANN BELL",
            dwt=180803,
            hire_rate=11750,
            speed_laden=13.5, speed_ballast=14.5,
            speed_laden_eco=12.0, speed_ballast_eco=12.5,
            fuel_laden_vlsfo=60, fuel_laden_mgo=2.0,
            fuel_ballast_vlsfo=55, fuel_ballast_mgo=2.0,
            fuel_laden_eco_vlsfo=42, fuel_laden_eco_mgo=2.0,
            fuel_ballast_eco_vlsfo=38, fuel_ballast_eco_mgo=2.0,
            port_idle_mgo=2.0, port_working_mgo=3.0,
            current_port="QINGDAO",
            etd="25 Feb 2026",
            bunker_rob_vlsfo=401.3, bunker_rob_mgo=45.1,
            is_cargill=True
        ),
        Vessel(
            name="OCEAN HORIZON",
            dwt=181550,
            hire_rate=15750,
            speed_laden=13.8, speed_ballast=14.8,
            speed_laden_eco=12.3, speed_ballast_eco=12.8,
            fuel_laden_vlsfo=61, fuel_laden_mgo=1.8,
            fuel_ballast_vlsfo=56.5, fuel_ballast_mgo=1.8,
            fuel_laden_eco_vlsfo=43, fuel_laden_eco_mgo=1.8,
            fuel_ballast_eco_vlsfo=39.5, fuel_ballast_eco_mgo=1.8,
            port_idle_mgo=1.8, port_working_mgo=3.2,
            current_port="MAP TA PHUT",
            etd="1 Mar 2026",
            bunker_rob_vlsfo=265.8, bunker_rob_mgo=64.3,
            is_cargill=True
        ),
        Vessel(
            name="PACIFIC GLORY",
            dwt=182320,
            hire_rate=14800,
            speed_laden=13.5, speed_ballast=14.2,
            speed_laden_eco=12.2, speed_ballast_eco=12.7,
            fuel_laden_vlsfo=59, fuel_laden_mgo=1.9,
            fuel_ballast_vlsfo=54, fuel_ballast_mgo=1.9,
            fuel_laden_eco_vlsfo=44, fuel_laden_eco_mgo=1.9,
            fuel_ballast_eco_vlsfo=40, fuel_ballast_eco_mgo=1.9,
            port_idle_mgo=2.0, port_working_mgo=3.0,
            current_port="GWANGYANG",
            etd="10 Mar 2026",
            bunker_rob_vlsfo=601.9, bunker_rob_mgo=98.1,
            is_cargill=True
        ),
        Vessel(
            name="GOLDEN ASCENT",
            dwt=179965,
            hire_rate=13950,
            speed_laden=13.0, speed_ballast=14.0,
            speed_laden_eco=11.8, speed_ballast_eco=12.3,
            fuel_laden_vlsfo=58, fuel_laden_mgo=2.0,
            fuel_ballast_vlsfo=53, fuel_ballast_mgo=2.0,
            fuel_laden_eco_vlsfo=41, fuel_laden_eco_mgo=2.0,
            fuel_ballast_eco_vlsfo=37, fuel_ballast_eco_mgo=2.0,
            port_idle_mgo=1.9, port_working_mgo=3.1,
            current_port="FANGCHENG",
            etd="8 Mar 2026",
            bunker_rob_vlsfo=793.3, bunker_rob_mgo=17.1,
            is_cargill=True
        ),
    ]
    
    return vessels


def create_market_vessels() -> List[Vessel]:
    """Create market vessels (3rd party) from the datathon data."""
    
    vessels = [
        Vessel(
            name="ATLANTIC FORTUNE", dwt=181200, hire_rate=0,
            speed_laden=13.8, speed_ballast=14.6,
            speed_laden_eco=12.3, speed_ballast_eco=12.9,
            fuel_laden_vlsfo=60, fuel_laden_mgo=2.0,
            fuel_ballast_vlsfo=56, fuel_ballast_mgo=2.0,
            fuel_laden_eco_vlsfo=43, fuel_laden_eco_mgo=2.0,
            fuel_ballast_eco_vlsfo=39.5, fuel_ballast_eco_mgo=2.0,
            port_idle_mgo=2.0, port_working_mgo=3.0,
            current_port="PARADIP", etd="2 Mar 2026",
            bunker_rob_vlsfo=512.4, bunker_rob_mgo=38.9,
            is_cargill=False
        ),
        Vessel(
            name="PACIFIC VANGUARD", dwt=182050, hire_rate=0,
            speed_laden=13.6, speed_ballast=14.3,
            speed_laden_eco=12.0, speed_ballast_eco=12.5,
            fuel_laden_vlsfo=59, fuel_laden_mgo=1.9,
            fuel_ballast_vlsfo=54, fuel_ballast_mgo=1.9,
            fuel_laden_eco_vlsfo=42, fuel_laden_eco_mgo=1.9,
            fuel_ballast_eco_vlsfo=38, fuel_ballast_eco_mgo=1.9,
            port_idle_mgo=1.9, port_working_mgo=3.0,
            current_port="CAOFEIDIAN", etd="26 Feb 2026",
            bunker_rob_vlsfo=420.3, bunker_rob_mgo=51.0,
            is_cargill=False
        ),
        Vessel(
            name="CORAL EMPEROR", dwt=180450, hire_rate=0,
            speed_laden=13.4, speed_ballast=14.1,
            speed_laden_eco=11.9, speed_ballast_eco=12.3,
            fuel_laden_vlsfo=58, fuel_laden_mgo=2.0,
            fuel_ballast_vlsfo=53, fuel_ballast_mgo=2.0,
            fuel_laden_eco_vlsfo=40, fuel_laden_eco_mgo=2.0,
            fuel_ballast_eco_vlsfo=36.5, fuel_ballast_eco_mgo=2.0,
            port_idle_mgo=2.0, port_working_mgo=3.1,
            current_port="ROTTERDAM", etd="5 Mar 2026",
            bunker_rob_vlsfo=601.7, bunker_rob_mgo=42.3,
            is_cargill=False
        ),
        Vessel(
            name="EVEREST OCEAN", dwt=179950, hire_rate=0,
            speed_laden=13.7, speed_ballast=14.5,
            speed_laden_eco=12.4, speed_ballast_eco=12.8,
            fuel_laden_vlsfo=61, fuel_laden_mgo=1.8,
            fuel_ballast_vlsfo=56.5, fuel_ballast_mgo=1.8,
            fuel_laden_eco_vlsfo=43.5, fuel_laden_eco_mgo=1.8,
            fuel_ballast_eco_vlsfo=39, fuel_ballast_eco_mgo=1.8,
            port_idle_mgo=1.8, port_working_mgo=3.0,
            current_port="XIAMEN", etd="3 Mar 2026",
            bunker_rob_vlsfo=478.2, bunker_rob_mgo=56.4,
            is_cargill=False
        ),
        Vessel(
            name="POLARIS SPIRIT", dwt=181600, hire_rate=0,
            speed_laden=13.9, speed_ballast=14.7,
            speed_laden_eco=12.5, speed_ballast_eco=13.0,
            fuel_laden_vlsfo=62, fuel_laden_mgo=1.9,
            fuel_ballast_vlsfo=57, fuel_ballast_mgo=1.9,
            fuel_laden_eco_vlsfo=44, fuel_laden_eco_mgo=1.9,
            fuel_ballast_eco_vlsfo=40, fuel_ballast_eco_mgo=1.9,
            port_idle_mgo=2.0, port_working_mgo=3.1,
            current_port="KANDLA", etd="28 Feb 2026",
            bunker_rob_vlsfo=529.8, bunker_rob_mgo=47.1,
            is_cargill=False
        ),
        Vessel(
            name="IRON CENTURY", dwt=182100, hire_rate=0,
            speed_laden=13.5, speed_ballast=14.2,
            speed_laden_eco=12.0, speed_ballast_eco=12.5,
            fuel_laden_vlsfo=59, fuel_laden_mgo=2.1,
            fuel_ballast_vlsfo=54, fuel_ballast_mgo=2.1,
            fuel_laden_eco_vlsfo=41, fuel_laden_eco_mgo=2.1,
            fuel_ballast_eco_vlsfo=37.5, fuel_ballast_eco_mgo=2.1,
            port_idle_mgo=2.1, port_working_mgo=3.2,
            current_port="PORT TALBOT", etd="9 Mar 2026",
            bunker_rob_vlsfo=365.6, bunker_rob_mgo=60.7,
            is_cargill=False
        ),
        Vessel(
            name="MOUNTAIN TRADER", dwt=180890, hire_rate=0,
            speed_laden=13.3, speed_ballast=14.0,
            speed_laden_eco=12.1, speed_ballast_eco=12.6,
            fuel_laden_vlsfo=58, fuel_laden_mgo=2.0,
            fuel_ballast_vlsfo=53, fuel_ballast_mgo=2.0,
            fuel_laden_eco_vlsfo=42, fuel_laden_eco_mgo=2.0,
            fuel_ballast_eco_vlsfo=38, fuel_ballast_eco_mgo=2.0,
            port_idle_mgo=2.0, port_working_mgo=3.1,
            current_port="GWANGYANG", etd="6 Mar 2026",
            bunker_rob_vlsfo=547.1, bunker_rob_mgo=32.4,
            is_cargill=False
        ),
        Vessel(
            name="NAVIS PRIDE", dwt=181400, hire_rate=0,
            speed_laden=13.8, speed_ballast=14.5,
            speed_laden_eco=12.6, speed_ballast_eco=13.0,
            fuel_laden_vlsfo=61, fuel_laden_mgo=1.8,
            fuel_ballast_vlsfo=56, fuel_ballast_mgo=1.8,
            fuel_laden_eco_vlsfo=44, fuel_laden_eco_mgo=1.8,
            fuel_ballast_eco_vlsfo=39, fuel_ballast_eco_mgo=1.8,
            port_idle_mgo=1.8, port_working_mgo=3.0,
            current_port="MUNDRA", etd="27 Feb 2026",
            bunker_rob_vlsfo=493.8, bunker_rob_mgo=45.2,
            is_cargill=False
        ),
        Vessel(
            name="AURORA SKY", dwt=179880, hire_rate=0,
            speed_laden=13.4, speed_ballast=14.1,
            speed_laden_eco=12.0, speed_ballast_eco=12.5,
            fuel_laden_vlsfo=58, fuel_laden_mgo=2.0,
            fuel_ballast_vlsfo=53, fuel_ballast_mgo=2.0,
            fuel_laden_eco_vlsfo=41, fuel_laden_eco_mgo=2.0,
            fuel_ballast_eco_vlsfo=37.5, fuel_ballast_eco_mgo=2.0,
            port_idle_mgo=2.0, port_working_mgo=3.1,
            current_port="JINGTANG", etd="4 Mar 2026",
            bunker_rob_vlsfo=422.7, bunker_rob_mgo=29.8,
            is_cargill=False
        ),
        Vessel(
            name="ZENITH GLORY", dwt=182500, hire_rate=0,
            speed_laden=13.9, speed_ballast=14.6,
            speed_laden_eco=12.4, speed_ballast_eco=12.9,
            fuel_laden_vlsfo=61, fuel_laden_mgo=1.9,
            fuel_ballast_vlsfo=56.5, fuel_ballast_mgo=1.9,
            fuel_laden_eco_vlsfo=43.5, fuel_laden_eco_mgo=1.9,
            fuel_ballast_eco_vlsfo=39, fuel_ballast_eco_mgo=1.9,
            port_idle_mgo=1.9, port_working_mgo=3.1,
            current_port="VIZAG", etd="7 Mar 2026",
            bunker_rob_vlsfo=502.3, bunker_rob_mgo=44.6,
            is_cargill=False
        ),
        Vessel(
            name="TITAN LEGACY", dwt=180650, hire_rate=0,
            speed_laden=13.5, speed_ballast=14.2,
            speed_laden_eco=12.2, speed_ballast_eco=12.7,
            fuel_laden_vlsfo=59, fuel_laden_mgo=2.0,
            fuel_ballast_vlsfo=54, fuel_ballast_mgo=2.0,
            fuel_laden_eco_vlsfo=42, fuel_laden_eco_mgo=2.0,
            fuel_ballast_eco_vlsfo=38, fuel_ballast_eco_mgo=2.0,
            port_idle_mgo=2.0, port_working_mgo=3.0,
            current_port="JUBAIL", etd="1 Mar 2026",
            bunker_rob_vlsfo=388.5, bunker_rob_mgo=53.1,
            is_cargill=False
        ),
    ]

    return vessels


def create_cargill_cargoes() -> List[Cargo]:
    """Create Cargill's 3 committed cargoes from the datathon data."""
    
    cargoes = [
        Cargo(
            name="EGA Bauxite (Guinea-China)",
            customer="EGA",
            commodity="Bauxite",
            quantity=180000,
            quantity_tolerance=0.10,
            laycan_start="2 Apr 2026",
            laycan_end="10 Apr 2026",
            freight_rate=23.0,
            load_port="KAMSAR ANCHORAGE",
            load_rate=30000,
            load_turn_time=12,
            discharge_port="QINGDAO",
            discharge_rate=25000,
            discharge_turn_time=12,
            port_cost_load=0,
            port_cost_discharge=0,
            commission=0.0125,
            is_cargill=True
        ),
        Cargo(
            name="BHP Iron Ore (Australia-China)",
            customer="BHP",
            commodity="Iron Ore",
            quantity=160000,
            quantity_tolerance=0.10,
            half_freight_threshold=176000,
            laycan_start="7 Mar 2026",
            laycan_end="11 Mar 2026",
            freight_rate=9.0,
            load_port="PORT HEDLAND",
            load_rate=80000,
            load_turn_time=12,
            discharge_port="LIANYUNGANG",
            discharge_rate=30000,
            discharge_turn_time=24,
            port_cost_load=260000,
            port_cost_discharge=120000,
            commission=0.0375,
            is_cargill=True
        ),
        Cargo(
            name="CSN Iron Ore (Brazil-China)",
            customer="CSN",
            commodity="Iron Ore",
            quantity=180000,
            quantity_tolerance=0.10,
            laycan_start="1 Apr 2026",
            laycan_end="8 Apr 2026",
            freight_rate=22.30,
            load_port="ITAGUAI",
            load_rate=60000,
            load_turn_time=6,
            discharge_port="QINGDAO",
            discharge_rate=30000,
            discharge_turn_time=24,
            port_cost_load=75000,
            port_cost_discharge=90000,
            commission=0.0375,
            is_cargill=True
        ),
    ]
    
    return cargoes


def create_market_cargoes() -> List[Cargo]:
    """Create market cargoes (3rd party) from the datathon data."""
    
    cargoes = [
        Cargo(
            name="Rio Tinto Iron Ore (Australia-China)",
            customer="Rio Tinto", commodity="Iron Ore",
            quantity=170000, quantity_tolerance=0.10,
            laycan_start="12 Mar 2026", laycan_end="18 Mar 2026",
            freight_rate=0,  # Need to bid
            load_port="DAMPIER", load_rate=80000, load_turn_time=12,
            discharge_port="QINGDAO", discharge_rate=30000, discharge_turn_time=24,
            port_cost_load=240000, port_cost_discharge=0,
            commission=0.0375, is_cargill=False
        ),
        Cargo(
            name="Vale Iron Ore (Brazil-China)",
            customer="Vale", commodity="Iron Ore",
            quantity=190000, quantity_tolerance=0.10,
            laycan_start="3 Apr 2026", laycan_end="10 Apr 2026",
            freight_rate=0,  # Need to bid
            load_port="PONTA DA MADEIRA", load_rate=60000, load_turn_time=12,
            discharge_port="CAOFEIDIAN", discharge_rate=30000, discharge_turn_time=24,
            port_cost_load=75000, port_cost_discharge=95000,
            commission=0.0375, is_cargill=False
        ),
        Cargo(
            name="Anglo American Iron Ore (S.Africa-China)",
            customer="Anglo American", commodity="Iron Ore",
            quantity=180000, quantity_tolerance=0.10,
            laycan_start="15 Mar 2026", laycan_end="22 Mar 2026",
            freight_rate=0,
            load_port="SALDANHA BAY", load_rate=55000, load_turn_time=6,
            discharge_port="TIANJIN", discharge_rate=25000, discharge_turn_time=24,
            port_cost_load=180000, port_cost_discharge=0,
            commission=0.0375, is_cargill=False
        ),
        Cargo(
            name="BHP Iron Ore (Australia-S.Korea)",
            customer="BHP", commodity="Iron Ore",
            quantity=165000, quantity_tolerance=0.10,
            laycan_start="9 Mar 2026", laycan_end="15 Mar 2026",
            freight_rate=0,
            load_port="PORT HEDLAND", load_rate=80000, load_turn_time=12,
            discharge_port="GWANGYANG", discharge_rate=30000, discharge_turn_time=24,
            port_cost_load=230000, port_cost_discharge=0,
            commission=0.0375, is_cargill=False
        ),
        Cargo(
            name="Adaro Coal (Indonesia-India)",
            customer="Adaro", commodity="Thermal Coal",
            quantity=150000, quantity_tolerance=0.10,
            laycan_start="10 Apr 2026", laycan_end="15 Apr 2026",
            freight_rate=0,  # Need to bid
            load_port="TABONEO", load_rate=35000, load_turn_time=12,
            discharge_port="KRISHNAPATNAM", discharge_rate=25000, discharge_turn_time=24,
            port_cost_load=90000, port_cost_discharge=0,
            commission=0.025, is_cargill=False  # 2.50% broker commission
        ),
        Cargo(
            name="Teck Coking Coal (Canada-China)",
            customer="Teck Resources", commodity="Coking Coal",
            quantity=160000, quantity_tolerance=0.10,
            laycan_start="18 Mar 2026", laycan_end="26 Mar 2026",
            freight_rate=0,  # Need to bid
            load_port="VANCOUVER", load_rate=45000, load_turn_time=12,
            discharge_port="FANGCHENG", discharge_rate=25000, discharge_turn_time=24,
            port_cost_load=180000, port_cost_discharge=110000,
            commission=0.0375, is_cargill=False
        ),
        Cargo(
            name="Guinea Alumina Bauxite (Guinea-India)",
            customer="Guinea Alumina Corp", commodity="Bauxite",
            quantity=175000, quantity_tolerance=0.10,
            laycan_start="10 Apr 2026", laycan_end="18 Apr 2026",
            freight_rate=0,  # Need to bid
            load_port="KAMSAR ANCHORAGE", load_rate=30000, load_turn_time=0,  # No turn time specified
            discharge_port="MANGALORE", discharge_rate=25000, discharge_turn_time=12,
            port_cost_load=150000, port_cost_discharge=0,
            commission=0.025, is_cargill=False  # 2.50% broker commission
        ),
        Cargo(
            name="Vale Malaysia Iron Ore (Brazil-Malaysia)",
            customer="Vale Malaysia", commodity="Iron Ore",
            quantity=180000, quantity_tolerance=0.10,
            laycan_start="25 Mar 2026", laycan_end="2 Apr 2026",
            freight_rate=0,  # Need to bid
            load_port="TUBARAO", load_rate=60000, load_turn_time=6,
            discharge_port="TELUK RUBIAH", discharge_rate=25000, discharge_turn_time=24,
            port_cost_load=85000, port_cost_discharge=80000,
            commission=0.0375, is_cargill=False
        ),
    ]

    return cargoes


def create_bunker_prices() -> BunkerPrices:
    """Create bunker prices from the datathon forward curve (March 2026 values)."""
    
    prices = BunkerPrices(prices={
        'Singapore': {'VLSFO': 490, 'MGO': 649},
        'Fujairah': {'VLSFO': 478, 'MGO': 638},
        'Durban': {'VLSFO': 437, 'MGO': 510},
        'Rotterdam': {'VLSFO': 467, 'MGO': 613},
        'Gibraltar': {'VLSFO': 474, 'MGO': 623},
        'Port Louis': {'VLSFO': 454, 'MGO': 583},
        'Qingdao': {'VLSFO': 643, 'MGO': 833},
        'Shanghai': {'VLSFO': 645, 'MGO': 836},
        'Richards Bay': {'VLSFO': 441, 'MGO': 519},
    })
    
    return prices


# =============================================================================
# MAIN - DEMONSTRATION
# =============================================================================

if __name__ == "__main__":
    print("=" * 80)
    print("CARGILL OCEAN TRANSPORTATION DATATHON 2026 - FREIGHT CALCULATOR")
    print("=" * 80)
    
    # Initialize
    distance_mgr = PortDistanceManager('Port_Distances.csv')
    bunker_prices = create_bunker_prices()
    calculator = FreightCalculator(distance_mgr, bunker_prices)
    
    # Load data
    cargill_vessels = create_cargill_vessels()
    cargill_cargoes = create_cargill_cargoes()
    
    print("\n📦 CARGILL VESSELS:")
    for v in cargill_vessels:
        print(f"  • {v.name:20} | DWT: {v.dwt:,} MT | At: {v.current_port:15} | ETD: {v.etd}")
    
    print("\n📦 CARGILL COMMITTED CARGOES:")
    for c in cargill_cargoes:
        print(f"  • {c.name[:40]:40} | {c.quantity:,} MT | Laycan: {c.laycan_start} - {c.laycan_end}")
    
    # Calculate all voyage combinations
    print("\n" + "=" * 80)
    print("VOYAGE ANALYSIS - ALL COMBINATIONS")
    print("=" * 80)
    
    results = []
    
    for vessel in cargill_vessels:
        for cargo in cargill_cargoes:
            try:
                result = calculator.calculate_voyage(vessel, cargo, use_eco_speed=True)
                results.append(result)
                
                laycan_status = "✅ CAN MAKE" if result.can_make_laycan else "❌ CANNOT MAKE"
                
                print(f"\n{vessel.name} → {cargo.name[:35]}")
                print(f"  Laycan: {laycan_status} (Arrives: {result.arrival_date.strftime('%d %b')})")
                print(f"  Duration: {result.total_days:.1f} days (Ballast: {result.ballast_days:.1f} + Laden: {result.laden_days:.1f} + Port: {result.load_days + result.discharge_days:.1f})")
                print(f"  Cargo: {result.cargo_quantity:,} MT")
                print(f"  Revenue: ${result.net_freight:,.0f} (after {cargo.commission*100:.2f}% commission)")
                print(f"  Bunker: ${result.total_bunker_cost:,.0f} ({result.vlsfo_consumed:.0f} MT VLSFO)")
                print(f"  Port Costs: ${result.port_costs:,.0f}")
                print(f"  Hire Cost: ${result.hire_cost:,.0f}")
                print(f"  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
                print(f"  💰 TCE: ${result.tce:,.0f}/day | Net Profit: ${result.net_profit:,.0f}")
                
            except Exception as e:
                print(f"\n{vessel.name} → {cargo.name[:35]}")
                print(f"  ⚠️  Error: {e}")
    
    # Summary table
    print("\n" + "=" * 80)
    print("SUMMARY - TCE COMPARISON MATRIX (USD/day)")
    print("=" * 80)
    
    # Create summary dataframe
    summary_data = []
    for r in results:
        summary_data.append({
            'Vessel': r.vessel_name,
            'Cargo': r.cargo_name[:25],
            'TCE': r.tce,
            'Can Make Laycan': r.can_make_laycan,
            'Net Profit': r.net_profit
        })
    
    df = pd.DataFrame(summary_data)
    print("\n")
    print(df.to_string(index=False))
    
    # Best assignments
    print("\n" + "=" * 80)
    print("RECOMMENDED ASSIGNMENTS (Highest TCE)")
    print("=" * 80)
    
    valid_results = [r for r in results if r.can_make_laycan]
    if valid_results:
        # Sort by TCE
        valid_results.sort(key=lambda x: x.tce, reverse=True)
        
        assigned_vessels = set()
        assigned_cargoes = set()
        recommendations = []
        
        for r in valid_results:
            if r.vessel_name not in assigned_vessels and r.cargo_name not in assigned_cargoes:
                recommendations.append(r)
                assigned_vessels.add(r.vessel_name)
                assigned_cargoes.add(r.cargo_name)
        
        total_profit = 0
        for r in recommendations:
            print(f"\n✅ {r.vessel_name} → {r.cargo_name[:35]}")
            print(f"   TCE: ${r.tce:,.0f}/day | Profit: ${r.net_profit:,.0f}")
            total_profit += r.net_profit
        
        print(f"\n💰 TOTAL PORTFOLIO PROFIT: ${total_profit:,.0f}")
