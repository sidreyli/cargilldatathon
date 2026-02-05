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
            # Bunker port aliases
            'FUJAIRAH': ['FUJAIRAH'],
            'GIBRALTAR': ['GIBRALTAR'],
            'DURBAN': ['DURBAN'],
            'PORT LOUIS': ['PORT LOUIS'],
            'RICHARDS BAY': ['RICHARDS BAY'],
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

            # =================================================================
            # BUNKER PORT DISTANCES - Added to reduce fallback rate
            # =================================================================
            # Distances from all 9 major bunker ports to common load/discharge
            # ports. These are great circle estimates optimized for the bunker
            # optimization algorithm to find optimal bunkering locations.
            # =================================================================

            # -----------------------------------------------------------------
            # SINGAPORE (SE Asia Hub) - to major load ports
            # -----------------------------------------------------------------
            ('SINGAPORE', 'KAMSAR ANCHORAGE'): 8500,     # Singapore to Guinea
            ('SINGAPORE', 'ITAGUAI'): 11200,             # Singapore to Brazil
            ('SINGAPORE', 'TUBARAO'): 11300,             # Singapore to Brazil
            ('SINGAPORE', 'DAMPIER'): 1750,              # Singapore to Australia
            ('SINGAPORE', 'TABONEO'): 680,               # Singapore to Indonesia
            ('SINGAPORE', 'PONTA DA MADEIRA'): 11400,    # Singapore to Brazil
            ('SINGAPORE', 'KRISHNAPATNAM'): 1850,        # Singapore to India
            ('SINGAPORE', 'TELUK RUBIAH'): 220,          # Singapore to Malaysia
            ('SINGAPORE', 'MANGALORE'): 2100,            # Singapore to India
            ('SINGAPORE', 'GWANGYANG'): 2460,            # Singapore to S.Korea
            ('SINGAPORE', 'QINGDAO'): 2460,              # Singapore to China
            ('SINGAPORE', 'SHANGHAI'): 2200,             # Singapore to China
            ('SINGAPORE', 'FANGCHENG'): 1300,            # Singapore to China
            ('SINGAPORE', 'CAOFEIDIAN'): 2650,           # Singapore to China
            ('SINGAPORE', 'TIANJIN'): 2700,              # Singapore to China
            ('SINGAPORE', 'LIANYUNGANG'): 2550,          # Singapore to China
            ('SINGAPORE', 'PARADIP'): 1950,              # Singapore to India
            ('SINGAPORE', 'MUNDRA'): 2400,               # Singapore to India
            ('SINGAPORE', 'KANDLA'): 2500,               # Singapore to India
            ('SINGAPORE', 'VIZAG'): 1900,                # Singapore to India
            ('SINGAPORE', 'SALDANHA BAY'): 5600,         # Singapore to S.Africa
            ('SINGAPORE', 'ROTTERDAM'): 9200,            # Singapore to Netherlands
            ('SINGAPORE', 'VANCOUVER'): 6800,            # Singapore to Canada
            ('SINGAPORE', 'MAP TA PHUT'): 763,           # Singapore to Thailand
            ('SINGAPORE', 'XIAMEN'): 1650,               # Singapore to China
            ('SINGAPORE', 'JINGTANG'): 2750,             # Singapore to China
            ('SINGAPORE', 'JUBAIL'): 3900,               # Singapore to Saudi Arabia
            ('SINGAPORE', 'PORT TALBOT'): 10500,         # Singapore to Wales

            # -----------------------------------------------------------------
            # FUJAIRAH (Middle East Hub) - to major load ports
            # -----------------------------------------------------------------
            ('FUJAIRAH', 'KAMSAR ANCHORAGE'): 6200,      # Fujairah to Guinea
            ('FUJAIRAH', 'PORT HEDLAND'): 5300,          # Fujairah to Australia
            ('FUJAIRAH', 'ITAGUAI'): 9800,               # Fujairah to Brazil
            ('FUJAIRAH', 'TUBARAO'): 9900,               # Fujairah to Brazil
            ('FUJAIRAH', 'DAMPIER'): 5400,               # Fujairah to Australia
            ('FUJAIRAH', 'TABONEO'): 4600,               # Fujairah to Indonesia
            ('FUJAIRAH', 'PONTA DA MADEIRA'): 10000,     # Fujairah to Brazil
            ('FUJAIRAH', 'KRISHNAPATNAM'): 2900,         # Fujairah to India
            ('FUJAIRAH', 'TELUK RUBIAH'): 3950,          # Fujairah to Malaysia
            ('FUJAIRAH', 'MANGALORE'): 1900,             # Fujairah to India
            ('FUJAIRAH', 'GWANGYANG'): 6800,             # Fujairah to S.Korea
            ('FUJAIRAH', 'QINGDAO'): 6800,               # Fujairah to China
            ('FUJAIRAH', 'SHANGHAI'): 6500,              # Fujairah to China
            ('FUJAIRAH', 'FANGCHENG'): 5600,             # Fujairah to China
            ('FUJAIRAH', 'CAOFEIDIAN'): 6950,            # Fujairah to China
            ('FUJAIRAH', 'TIANJIN'): 7000,               # Fujairah to China
            ('FUJAIRAH', 'LIANYUNGANG'): 6850,           # Fujairah to China
            ('FUJAIRAH', 'PARADIP'): 2400,               # Fujairah to India
            ('FUJAIRAH', 'MUNDRA'): 1100,                # Fujairah to India
            ('FUJAIRAH', 'KANDLA'): 1000,                # Fujairah to India
            ('FUJAIRAH', 'VIZAG'): 2650,                 # Fujairah to India
            ('FUJAIRAH', 'SALDANHA BAY'): 5000,          # Fujairah to S.Africa
            ('FUJAIRAH', 'ROTTERDAM'): 6800,             # Fujairah to Netherlands
            ('FUJAIRAH', 'VANCOUVER'): 10500,            # Fujairah to Canada
            ('FUJAIRAH', 'MAP TA PHUT'): 3400,           # Fujairah to Thailand
            ('FUJAIRAH', 'XIAMEN'): 5900,                # Fujairah to China
            ('FUJAIRAH', 'JINGTANG'): 7050,              # Fujairah to China
            ('FUJAIRAH', 'JUBAIL'): 1050,                # Fujairah to Saudi Arabia
            ('FUJAIRAH', 'PORT TALBOT'): 7800,           # Fujairah to Wales

            # -----------------------------------------------------------------
            # ROTTERDAM (NW Europe Hub) - to major load ports
            # -----------------------------------------------------------------
            ('ROTTERDAM', 'PORT HEDLAND'): 11500,        # Rotterdam to Australia
            ('ROTTERDAM', 'ITAGUAI'): 6200,              # Rotterdam to Brazil
            ('ROTTERDAM', 'TUBARAO'): 6300,              # Rotterdam to Brazil
            ('ROTTERDAM', 'DAMPIER'): 11600,             # Rotterdam to Australia
            ('ROTTERDAM', 'TABONEO'): 10100,             # Rotterdam to Indonesia
            ('ROTTERDAM', 'PONTA DA MADEIRA'): 6400,     # Rotterdam to Brazil
            ('ROTTERDAM', 'KRISHNAPATNAM'): 8900,        # Rotterdam to India
            ('ROTTERDAM', 'TELUK RUBIAH'): 9600,         # Rotterdam to Malaysia
            ('ROTTERDAM', 'MANGALORE'): 8200,            # Rotterdam to India
            ('ROTTERDAM', 'GWANGYANG'): 12500,           # Rotterdam to S.Korea
            ('ROTTERDAM', 'QINGDAO'): 12500,             # Rotterdam to China
            ('ROTTERDAM', 'SHANGHAI'): 12200,            # Rotterdam to China
            ('ROTTERDAM', 'FANGCHENG'): 11300,           # Rotterdam to China
            ('ROTTERDAM', 'CAOFEIDIAN'): 12650,          # Rotterdam to China
            ('ROTTERDAM', 'TIANJIN'): 12700,             # Rotterdam to China
            ('ROTTERDAM', 'LIANYUNGANG'): 12550,         # Rotterdam to China
            ('ROTTERDAM', 'PARADIP'): 8600,              # Rotterdam to India
            ('ROTTERDAM', 'MUNDRA'): 7900,               # Rotterdam to India
            ('ROTTERDAM', 'KANDLA'): 7800,               # Rotterdam to India
            ('ROTTERDAM', 'VIZAG'): 8850,                # Rotterdam to India
            ('ROTTERDAM', 'SALDANHA BAY'): 7000,         # Rotterdam to S.Africa
            ('ROTTERDAM', 'VANCOUVER'): 7800,            # Rotterdam to Canada
            ('ROTTERDAM', 'MAP TA PHUT'): 9900,          # Rotterdam to Thailand
            ('ROTTERDAM', 'XIAMEN'): 11600,              # Rotterdam to China
            ('ROTTERDAM', 'JINGTANG'): 12750,            # Rotterdam to China
            ('ROTTERDAM', 'JUBAIL'): 6800,               # Rotterdam to Saudi Arabia
            ('ROTTERDAM', 'PORT TALBOT'): 650,           # Rotterdam to Wales
            ('ROTTERDAM', 'SINGAPORE'): 9200,            # Rotterdam to Singapore

            # -----------------------------------------------------------------
            # GIBRALTAR (Med/Atlantic Hub) - to major load ports
            # -----------------------------------------------------------------
            ('GIBRALTAR', 'KAMSAR ANCHORAGE'): 2500,     # Gibraltar to Guinea
            ('GIBRALTAR', 'PORT HEDLAND'): 11200,        # Gibraltar to Australia
            ('GIBRALTAR', 'ITAGUAI'): 5400,              # Gibraltar to Brazil
            ('GIBRALTAR', 'TUBARAO'): 5500,              # Gibraltar to Brazil
            ('GIBRALTAR', 'DAMPIER'): 11300,             # Gibraltar to Australia
            ('GIBRALTAR', 'TABONEO'): 9600,              # Gibraltar to Indonesia
            ('GIBRALTAR', 'PONTA DA MADEIRA'): 5600,     # Gibraltar to Brazil
            ('GIBRALTAR', 'KRISHNAPATNAM'): 8200,        # Gibraltar to India
            ('GIBRALTAR', 'TELUK RUBIAH'): 8900,         # Gibraltar to Malaysia
            ('GIBRALTAR', 'MANGALORE'): 7500,            # Gibraltar to India
            ('GIBRALTAR', 'GWANGYANG'): 12200,           # Gibraltar to S.Korea
            ('GIBRALTAR', 'QINGDAO'): 12200,             # Gibraltar to China
            ('GIBRALTAR', 'SHANGHAI'): 11900,            # Gibraltar to China
            ('GIBRALTAR', 'FANGCHENG'): 11000,           # Gibraltar to China
            ('GIBRALTAR', 'CAOFEIDIAN'): 12350,          # Gibraltar to China
            ('GIBRALTAR', 'TIANJIN'): 12400,             # Gibraltar to China
            ('GIBRALTAR', 'LIANYUNGANG'): 12250,         # Gibraltar to China
            ('GIBRALTAR', 'PARADIP'): 7900,              # Gibraltar to India
            ('GIBRALTAR', 'MUNDRA'): 7200,               # Gibraltar to India
            ('GIBRALTAR', 'KANDLA'): 7100,               # Gibraltar to India
            ('GIBRALTAR', 'VIZAG'): 8150,                # Gibraltar to India
            ('GIBRALTAR', 'SALDANHA BAY'): 5800,         # Gibraltar to S.Africa
            ('GIBRALTAR', 'ROTTERDAM'): 1750,            # Gibraltar to Netherlands
            ('GIBRALTAR', 'VANCOUVER'): 8900,            # Gibraltar to Canada
            ('GIBRALTAR', 'MAP TA PHUT'): 9200,          # Gibraltar to Thailand
            ('GIBRALTAR', 'XIAMEN'): 11300,              # Gibraltar to China
            ('GIBRALTAR', 'JINGTANG'): 12450,            # Gibraltar to China
            ('GIBRALTAR', 'JUBAIL'): 6100,               # Gibraltar to Saudi Arabia
            ('GIBRALTAR', 'PORT TALBOT'): 1450,          # Gibraltar to Wales
            ('GIBRALTAR', 'SINGAPORE'): 8800,            # Gibraltar to Singapore

            # -----------------------------------------------------------------
            # DURBAN (Southern Africa Hub) - to major load ports
            # -----------------------------------------------------------------
            ('DURBAN', 'KAMSAR ANCHORAGE'): 5400,        # Durban to Guinea
            ('DURBAN', 'PORT HEDLAND'): 5100,            # Durban to Australia
            ('DURBAN', 'ITAGUAI'): 5800,                 # Durban to Brazil
            ('DURBAN', 'TUBARAO'): 5900,                 # Durban to Brazil
            ('DURBAN', 'DAMPIER'): 5200,                 # Durban to Australia
            ('DURBAN', 'TABONEO'): 5850,                 # Durban to Indonesia
            ('DURBAN', 'PONTA DA MADEIRA'): 6000,        # Durban to Brazil
            ('DURBAN', 'KRISHNAPATNAM'): 3700,           # Durban to India
            ('DURBAN', 'TELUK RUBIAH'): 4900,            # Durban to Malaysia
            ('DURBAN', 'MANGALORE'): 3400,               # Durban to India
            ('DURBAN', 'GWANGYANG'): 7400,               # Durban to S.Korea
            ('DURBAN', 'QINGDAO'): 7400,                 # Durban to China
            ('DURBAN', 'SHANGHAI'): 7100,                # Durban to China
            ('DURBAN', 'FANGCHENG'): 6200,               # Durban to China
            ('DURBAN', 'CAOFEIDIAN'): 7550,              # Durban to China
            ('DURBAN', 'TIANJIN'): 7600,                 # Durban to China
            ('DURBAN', 'LIANYUNGANG'): 7450,             # Durban to China
            ('DURBAN', 'PARADIP'): 3500,                 # Durban to India
            ('DURBAN', 'MUNDRA'): 3200,                  # Durban to India
            ('DURBAN', 'KANDLA'): 3100,                  # Durban to India
            ('DURBAN', 'VIZAG'): 3750,                   # Durban to India
            ('DURBAN', 'SALDANHA BAY'): 850,             # Durban to S.Africa
            ('DURBAN', 'ROTTERDAM'): 7000,               # Durban to Netherlands
            ('DURBAN', 'VANCOUVER'): 12200,              # Durban to Canada
            ('DURBAN', 'MAP TA PHUT'): 4700,             # Durban to Thailand
            ('DURBAN', 'XIAMEN'): 6500,                  # Durban to China
            ('DURBAN', 'JINGTANG'): 7650,                # Durban to China
            ('DURBAN', 'JUBAIL'): 4000,                  # Durban to Saudi Arabia
            ('DURBAN', 'PORT TALBOT'): 7700,             # Durban to Wales
            ('DURBAN', 'SINGAPORE'): 4900,               # Durban to Singapore

            # -----------------------------------------------------------------
            # QINGDAO (China Hub) - to major load ports
            # -----------------------------------------------------------------
            ('QINGDAO', 'KAMSAR ANCHORAGE'): 11800,      # Qingdao to Guinea
            ('QINGDAO', 'PORT HEDLAND'): 3300,           # Qingdao to Australia
            ('QINGDAO', 'ITAGUAI'): 12200,               # Qingdao to Brazil
            ('QINGDAO', 'TUBARAO'): 12100,               # Qingdao to Brazil
            ('QINGDAO', 'DAMPIER'): 3400,                # Qingdao to Australia
            ('QINGDAO', 'PONTA DA MADEIRA'): 12300,      # Qingdao to Brazil
            ('QINGDAO', 'KRISHNAPATNAM'): 3050,          # Qingdao to India
            ('QINGDAO', 'TELUK RUBIAH'): 2350,           # Qingdao to Malaysia
            ('QINGDAO', 'MANGALORE'): 3450,              # Qingdao to India
            ('QINGDAO', 'GWANGYANG'): 520,               # Qingdao to S.Korea
            ('QINGDAO', 'SHANGHAI'): 380,                # Qingdao to China
            ('QINGDAO', 'FANGCHENG'): 1420,              # Qingdao to China
            ('QINGDAO', 'CAOFEIDIAN'): 280,              # Qingdao to China
            ('QINGDAO', 'TIANJIN'): 330,                 # Qingdao to China
            ('QINGDAO', 'LIANYUNGANG'): 180,             # Qingdao to China
            ('QINGDAO', 'PARADIP'): 3150,                # Qingdao to India
            ('QINGDAO', 'MUNDRA'): 3700,                 # Qingdao to India
            ('QINGDAO', 'KANDLA'): 3800,                 # Qingdao to India
            ('QINGDAO', 'VIZAG'): 3000,                  # Qingdao to India
            ('QINGDAO', 'SALDANHA BAY'): 8800,           # Qingdao to S.Africa
            ('QINGDAO', 'ROTTERDAM'): 12500,             # Qingdao to Netherlands
            ('QINGDAO', 'VANCOUVER'): 5200,              # Qingdao to Canada
            ('QINGDAO', 'MAP TA PHUT'): 2000,            # Qingdao to Thailand
            ('QINGDAO', 'XIAMEN'): 850,                  # Qingdao to China
            ('QINGDAO', 'JINGTANG'): 240,                # Qingdao to China
            ('QINGDAO', 'JUBAIL'): 6800,                 # Qingdao to Saudi Arabia
            ('QINGDAO', 'PORT TALBOT'): 13200,           # Qingdao to Wales
            ('QINGDAO', 'SINGAPORE'): 2460,              # Qingdao to Singapore
            ('QINGDAO', 'FUJAIRAH'): 6800,               # Qingdao to Fujairah

            # -----------------------------------------------------------------
            # SHANGHAI (China Hub) - to major load ports
            # -----------------------------------------------------------------
            ('SHANGHAI', 'KAMSAR ANCHORAGE'): 12200,     # Shanghai to Guinea
            ('SHANGHAI', 'PORT HEDLAND'): 3238,          # Shanghai to Australia
            ('SHANGHAI', 'ITAGUAI'): 12100,              # Shanghai to Brazil
            ('SHANGHAI', 'TUBARAO'): 12000,              # Shanghai to Brazil
            ('SHANGHAI', 'DAMPIER'): 3350,               # Shanghai to Australia
            ('SHANGHAI', 'TABONEO'): 1900,               # Shanghai to Indonesia
            ('SHANGHAI', 'PONTA DA MADEIRA'): 12200,     # Shanghai to Brazil
            ('SHANGHAI', 'KRISHNAPATNAM'): 2950,         # Shanghai to India
            ('SHANGHAI', 'TELUK RUBIAH'): 2100,          # Shanghai to Malaysia
            ('SHANGHAI', 'MANGALORE'): 3350,             # Shanghai to India
            ('SHANGHAI', 'GWANGYANG'): 490,              # Shanghai to S.Korea
            ('SHANGHAI', 'QINGDAO'): 380,                # Shanghai to China
            ('SHANGHAI', 'FANGCHENG'): 1100,             # Shanghai to China
            ('SHANGHAI', 'CAOFEIDIAN'): 520,             # Shanghai to China
            ('SHANGHAI', 'TIANJIN'): 570,                # Shanghai to China
            ('SHANGHAI', 'LIANYUNGANG'): 240,            # Shanghai to China
            ('SHANGHAI', 'PARADIP'): 3050,               # Shanghai to India
            ('SHANGHAI', 'MUNDRA'): 3600,                # Shanghai to India
            ('SHANGHAI', 'KANDLA'): 3700,                # Shanghai to India
            ('SHANGHAI', 'VIZAG'): 2900,                 # Shanghai to India
            ('SHANGHAI', 'SALDANHA BAY'): 9200,          # Shanghai to S.Africa
            ('SHANGHAI', 'ROTTERDAM'): 12200,            # Shanghai to Netherlands
            ('SHANGHAI', 'VANCOUVER'): 5400,             # Shanghai to Canada
            ('SHANGHAI', 'MAP TA PHUT'): 1750,           # Shanghai to Thailand
            ('SHANGHAI', 'XIAMEN'): 420,                 # Shanghai to China
            ('SHANGHAI', 'JINGTANG'): 480,               # Shanghai to China
            ('SHANGHAI', 'JUBAIL'): 6500,                # Shanghai to Saudi Arabia
            ('SHANGHAI', 'PORT TALBOT'): 12900,          # Shanghai to Wales
            ('SHANGHAI', 'SINGAPORE'): 2200,             # Shanghai to Singapore
            ('SHANGHAI', 'FUJAIRAH'): 6500,              # Shanghai to Fujairah

            # -----------------------------------------------------------------
            # PORT LOUIS (Indian Ocean Hub) - to major load ports
            # -----------------------------------------------------------------
            ('PORT LOUIS', 'KAMSAR ANCHORAGE'): 5600,    # Port Louis to Guinea
            ('PORT LOUIS', 'PORT HEDLAND'): 3600,        # Port Louis to Australia
            ('PORT LOUIS', 'ITAGUAI'): 6600,             # Port Louis to Brazil
            ('PORT LOUIS', 'TUBARAO'): 6700,             # Port Louis to Brazil
            ('PORT LOUIS', 'DAMPIER'): 3700,             # Port Louis to Australia
            ('PORT LOUIS', 'TABONEO'): 3900,             # Port Louis to Indonesia
            ('PORT LOUIS', 'PONTA DA MADEIRA'): 6800,    # Port Louis to Brazil
            ('PORT LOUIS', 'KRISHNAPATNAM'): 2400,       # Port Louis to India
            ('PORT LOUIS', 'TELUK RUBIAH'): 3300,        # Port Louis to Malaysia
            ('PORT LOUIS', 'MANGALORE'): 2100,           # Port Louis to India
            ('PORT LOUIS', 'GWANGYANG'): 5900,           # Port Louis to S.Korea
            ('PORT LOUIS', 'QINGDAO'): 5900,             # Port Louis to China
            ('PORT LOUIS', 'SHANGHAI'): 5600,            # Port Louis to China
            ('PORT LOUIS', 'FANGCHENG'): 4700,           # Port Louis to China
            ('PORT LOUIS', 'CAOFEIDIAN'): 6050,          # Port Louis to China
            ('PORT LOUIS', 'TIANJIN'): 6100,             # Port Louis to China
            ('PORT LOUIS', 'LIANYUNGANG'): 5950,         # Port Louis to China
            ('PORT LOUIS', 'PARADIP'): 2200,             # Port Louis to India
            ('PORT LOUIS', 'MUNDRA'): 1900,              # Port Louis to India
            ('PORT LOUIS', 'KANDLA'): 1800,              # Port Louis to India
            ('PORT LOUIS', 'VIZAG'): 2450,               # Port Louis to India
            ('PORT LOUIS', 'SALDANHA BAY'): 1950,        # Port Louis to S.Africa
            ('PORT LOUIS', 'ROTTERDAM'): 7800,           # Port Louis to Netherlands
            ('PORT LOUIS', 'VANCOUVER'): 10800,          # Port Louis to Canada
            ('PORT LOUIS', 'MAP TA PHUT'): 3200,         # Port Louis to Thailand
            ('PORT LOUIS', 'XIAMEN'): 5000,              # Port Louis to China
            ('PORT LOUIS', 'JINGTANG'): 6150,            # Port Louis to China
            ('PORT LOUIS', 'JUBAIL'): 2700,              # Port Louis to Saudi Arabia
            ('PORT LOUIS', 'PORT TALBOT'): 8500,         # Port Louis to Wales
            ('PORT LOUIS', 'SINGAPORE'): 3300,           # Port Louis to Singapore
            ('PORT LOUIS', 'FUJAIRAH'): 2500,            # Port Louis to Fujairah

            # -----------------------------------------------------------------
            # RICHARDS BAY (South African Hub) - to major load ports
            # -----------------------------------------------------------------
            ('RICHARDS BAY', 'KAMSAR ANCHORAGE'): 5600,  # Richards Bay to Guinea
            ('RICHARDS BAY', 'PORT HEDLAND'): 5300,      # Richards Bay to Australia
            ('RICHARDS BAY', 'ITAGUAI'): 6000,           # Richards Bay to Brazil
            ('RICHARDS BAY', 'TUBARAO'): 6100,           # Richards Bay to Brazil
            ('RICHARDS BAY', 'DAMPIER'): 5400,           # Richards Bay to Australia
            ('RICHARDS BAY', 'TABONEO'): 6050,           # Richards Bay to Indonesia
            ('RICHARDS BAY', 'PONTA DA MADEIRA'): 6200,  # Richards Bay to Brazil
            ('RICHARDS BAY', 'KRISHNAPATNAM'): 3900,     # Richards Bay to India
            ('RICHARDS BAY', 'TELUK RUBIAH'): 5100,      # Richards Bay to Malaysia
            ('RICHARDS BAY', 'MANGALORE'): 3600,         # Richards Bay to India
            ('RICHARDS BAY', 'GWANGYANG'): 7600,         # Richards Bay to S.Korea
            ('RICHARDS BAY', 'QINGDAO'): 7600,           # Richards Bay to China
            ('RICHARDS BAY', 'SHANGHAI'): 7300,          # Richards Bay to China
            ('RICHARDS BAY', 'FANGCHENG'): 6400,         # Richards Bay to China
            ('RICHARDS BAY', 'CAOFEIDIAN'): 7750,        # Richards Bay to China
            ('RICHARDS BAY', 'TIANJIN'): 7800,           # Richards Bay to China
            ('RICHARDS BAY', 'LIANYUNGANG'): 7650,       # Richards Bay to China
            ('RICHARDS BAY', 'PARADIP'): 3700,           # Richards Bay to India
            ('RICHARDS BAY', 'MUNDRA'): 3400,            # Richards Bay to India
            ('RICHARDS BAY', 'KANDLA'): 3300,            # Richards Bay to India
            ('RICHARDS BAY', 'VIZAG'): 3950,             # Richards Bay to India
            ('RICHARDS BAY', 'SALDANHA BAY'): 900,       # Richards Bay to S.Africa
            ('RICHARDS BAY', 'ROTTERDAM'): 7200,         # Richards Bay to Netherlands
            ('RICHARDS BAY', 'VANCOUVER'): 12400,        # Richards Bay to Canada
            ('RICHARDS BAY', 'MAP TA PHUT'): 4900,       # Richards Bay to Thailand
            ('RICHARDS BAY', 'XIAMEN'): 6700,            # Richards Bay to China
            ('RICHARDS BAY', 'JINGTANG'): 7850,          # Richards Bay to China
            ('RICHARDS BAY', 'JUBAIL'): 4200,            # Richards Bay to Saudi Arabia
            ('RICHARDS BAY', 'PORT TALBOT'): 7900,       # Richards Bay to Wales
            ('RICHARDS BAY', 'SINGAPORE'): 5100,         # Richards Bay to Singapore
            ('RICHARDS BAY', 'FUJAIRAH'): 4100,          # Richards Bay to Fujairah

            # =================================================================
            # VESSEL CURRENT POSITIONS TO BUNKER PORTS
            # =================================================================
            # Common vessel positions to bunker ports for the first leg of
            # bunker routing (vessel_current_port -> bunker_port)
            # =================================================================

            # MAP TA PHUT (common vessel position) to bunker ports
            ('MAP TA PHUT', 'SINGAPORE'): 763,           # Thailand to Singapore
            ('MAP TA PHUT', 'FUJAIRAH'): 3400,           # Thailand to Fujairah
            ('MAP TA PHUT', 'ROTTERDAM'): 9900,          # Thailand to Rotterdam
            ('MAP TA PHUT', 'GIBRALTAR'): 9200,          # Thailand to Gibraltar
            ('MAP TA PHUT', 'DURBAN'): 4700,             # Thailand to Durban
            ('MAP TA PHUT', 'QINGDAO'): 2000,            # Thailand to Qingdao
            ('MAP TA PHUT', 'SHANGHAI'): 1750,           # Thailand to Shanghai
            ('MAP TA PHUT', 'PORT LOUIS'): 3200,         # Thailand to Port Louis
            ('MAP TA PHUT', 'RICHARDS BAY'): 4900,       # Thailand to Richards Bay

            # GWANGYANG (common vessel position) to bunker ports
            ('GWANGYANG', 'SINGAPORE'): 2460,            # S.Korea to Singapore
            ('GWANGYANG', 'FUJAIRAH'): 6800,             # S.Korea to Fujairah
            ('GWANGYANG', 'ROTTERDAM'): 12500,           # S.Korea to Rotterdam
            ('GWANGYANG', 'GIBRALTAR'): 12200,           # S.Korea to Gibraltar
            ('GWANGYANG', 'DURBAN'): 7400,               # S.Korea to Durban
            ('GWANGYANG', 'QINGDAO'): 520,               # S.Korea to Qingdao
            ('GWANGYANG', 'SHANGHAI'): 490,              # S.Korea to Shanghai
            ('GWANGYANG', 'PORT LOUIS'): 5900,           # S.Korea to Port Louis
            ('GWANGYANG', 'RICHARDS BAY'): 7600,         # S.Korea to Richards Bay

            # PORT TALBOT (common vessel position) to bunker ports
            ('PORT TALBOT', 'SINGAPORE'): 10500,         # Wales to Singapore
            ('PORT TALBOT', 'FUJAIRAH'): 7800,           # Wales to Fujairah
            ('PORT TALBOT', 'ROTTERDAM'): 650,           # Wales to Rotterdam
            ('PORT TALBOT', 'GIBRALTAR'): 1450,          # Wales to Gibraltar
            ('PORT TALBOT', 'DURBAN'): 7700,             # Wales to Durban
            ('PORT TALBOT', 'QINGDAO'): 13200,           # Wales to Qingdao
            ('PORT TALBOT', 'SHANGHAI'): 12900,          # Wales to Shanghai
            ('PORT TALBOT', 'PORT LOUIS'): 8500,         # Wales to Port Louis
            ('PORT TALBOT', 'RICHARDS BAY'): 7900,       # Wales to Richards Bay

            # JUBAIL (common vessel position) to bunker ports
            ('JUBAIL', 'SINGAPORE'): 3900,               # Saudi Arabia to Singapore
            ('JUBAIL', 'FUJAIRAH'): 1050,                # Saudi Arabia to Fujairah
            ('JUBAIL', 'ROTTERDAM'): 6800,               # Saudi Arabia to Rotterdam
            ('JUBAIL', 'GIBRALTAR'): 6100,               # Saudi Arabia to Gibraltar
            ('JUBAIL', 'DURBAN'): 4000,                  # Saudi Arabia to Durban
            ('JUBAIL', 'QINGDAO'): 6800,                 # Saudi Arabia to Qingdao
            ('JUBAIL', 'SHANGHAI'): 6500,                # Saudi Arabia to Shanghai
            ('JUBAIL', 'PORT LOUIS'): 2700,              # Saudi Arabia to Port Louis
            ('JUBAIL', 'RICHARDS BAY'): 4200,            # Saudi Arabia to Richards Bay

            # PARADIP (common vessel position) to bunker ports
            ('PARADIP', 'SINGAPORE'): 1950,              # India to Singapore
            ('PARADIP', 'FUJAIRAH'): 2400,               # India to Fujairah
            ('PARADIP', 'ROTTERDAM'): 8600,              # India to Rotterdam
            ('PARADIP', 'GIBRALTAR'): 7900,              # India to Gibraltar
            ('PARADIP', 'DURBAN'): 3500,                 # India to Durban
            ('PARADIP', 'QINGDAO'): 3150,                # India to Qingdao
            ('PARADIP', 'SHANGHAI'): 3050,               # India to Shanghai
            ('PARADIP', 'PORT LOUIS'): 2200,             # India to Port Louis
            ('PARADIP', 'RICHARDS BAY'): 3700,           # India to Richards Bay

            # QINGDAO (common vessel position) to bunker ports
            ('QINGDAO', 'SINGAPORE'): 2460,              # China to Singapore
            ('QINGDAO', 'ROTTERDAM'): 12500,             # China to Rotterdam
            ('QINGDAO', 'GIBRALTAR'): 12200,             # China to Gibraltar
            ('QINGDAO', 'DURBAN'): 7400,                 # China to Durban
            ('QINGDAO', 'SHANGHAI'): 380,                # China to Shanghai
            ('QINGDAO', 'PORT LOUIS'): 5900,             # China to Port Louis
            ('QINGDAO', 'RICHARDS BAY'): 7600,           # China to Richards Bay

            # XIAMEN (common vessel position) to bunker ports
            ('XIAMEN', 'SINGAPORE'): 1650,               # China to Singapore
            ('XIAMEN', 'FUJAIRAH'): 5900,                # China to Fujairah
            ('XIAMEN', 'ROTTERDAM'): 11600,              # China to Rotterdam
            ('XIAMEN', 'GIBRALTAR'): 11300,              # China to Gibraltar
            ('XIAMEN', 'DURBAN'): 6500,                  # China to Durban
            ('XIAMEN', 'QINGDAO'): 850,                  # China to Qingdao
            ('XIAMEN', 'SHANGHAI'): 420,                 # China to Shanghai
            ('XIAMEN', 'PORT LOUIS'): 5000,              # China to Port Louis
            ('XIAMEN', 'RICHARDS BAY'): 6700,            # China to Richards Bay

            # FANGCHENG (common vessel position) to bunker ports
            ('FANGCHENG', 'SINGAPORE'): 1300,            # China to Singapore
            ('FANGCHENG', 'FUJAIRAH'): 5600,             # China to Fujairah
            ('FANGCHENG', 'ROTTERDAM'): 11300,           # China to Rotterdam
            ('FANGCHENG', 'GIBRALTAR'): 11000,           # China to Gibraltar
            ('FANGCHENG', 'DURBAN'): 6200,               # China to Durban
            ('FANGCHENG', 'QINGDAO'): 1420,              # China to Qingdao
            ('FANGCHENG', 'SHANGHAI'): 1100,             # China to Shanghai
            ('FANGCHENG', 'PORT LOUIS'): 4700,           # China to Port Louis
            ('FANGCHENG', 'RICHARDS BAY'): 6400,         # China to Richards Bay

            # TIANJIN (common vessel position) to bunker ports
            ('TIANJIN', 'SINGAPORE'): 2700,              # China to Singapore
            ('TIANJIN', 'FUJAIRAH'): 7000,               # China to Fujairah
            ('TIANJIN', 'ROTTERDAM'): 12700,             # China to Rotterdam
            ('TIANJIN', 'GIBRALTAR'): 12400,             # China to Gibraltar
            ('TIANJIN', 'DURBAN'): 7600,                 # China to Durban
            ('TIANJIN', 'QINGDAO'): 330,                 # China to Qingdao
            ('TIANJIN', 'SHANGHAI'): 570,                # China to Shanghai
            ('TIANJIN', 'PORT LOUIS'): 6100,             # China to Port Louis
            ('TIANJIN', 'RICHARDS BAY'): 7800,           # China to Richards Bay

            # VIZAG (common vessel position) to bunker ports
            ('VIZAG', 'SINGAPORE'): 1900,                # India to Singapore
            ('VIZAG', 'FUJAIRAH'): 2650,                 # India to Fujairah
            ('VIZAG', 'ROTTERDAM'): 8850,                # India to Rotterdam
            ('VIZAG', 'GIBRALTAR'): 8150,                # India to Gibraltar
            ('VIZAG', 'DURBAN'): 3750,                   # India to Durban
            ('VIZAG', 'QINGDAO'): 3000,                  # India to Qingdao
            ('VIZAG', 'SHANGHAI'): 2900,                 # India to Shanghai
            ('VIZAG', 'PORT LOUIS'): 2450,               # India to Port Louis
            ('VIZAG', 'RICHARDS BAY'): 3950,             # India to Richards Bay

            # MUNDRA (common vessel position) to bunker ports
            ('MUNDRA', 'SINGAPORE'): 2400,               # India to Singapore
            ('MUNDRA', 'FUJAIRAH'): 1100,                # India to Fujairah
            ('MUNDRA', 'ROTTERDAM'): 7900,               # India to Rotterdam
            ('MUNDRA', 'GIBRALTAR'): 7200,               # India to Gibraltar
            ('MUNDRA', 'DURBAN'): 3200,                  # India to Durban
            ('MUNDRA', 'QINGDAO'): 3700,                 # India to Qingdao
            ('MUNDRA', 'SHANGHAI'): 3600,                # India to Shanghai
            ('MUNDRA', 'PORT LOUIS'): 1900,              # India to Port Louis
            ('MUNDRA', 'RICHARDS BAY'): 3400,            # India to Richards Bay

            # KANDLA (common vessel position) to bunker ports
            ('KANDLA', 'SINGAPORE'): 2500,               # India to Singapore
            ('KANDLA', 'FUJAIRAH'): 1000,                # India to Fujairah
            ('KANDLA', 'ROTTERDAM'): 7800,               # India to Rotterdam
            ('KANDLA', 'GIBRALTAR'): 7100,               # India to Gibraltar
            ('KANDLA', 'DURBAN'): 3100,                  # India to Durban
            ('KANDLA', 'QINGDAO'): 3800,                 # India to Qingdao
            ('KANDLA', 'SHANGHAI'): 3700,                # India to Shanghai
            ('KANDLA', 'PORT LOUIS'): 1800,              # India to Port Louis
            ('KANDLA', 'RICHARDS BAY'): 3300,            # India to Richards Bay

            # ROTTERDAM (common vessel position) to bunker ports
            ('ROTTERDAM', 'SINGAPORE'): 9200,            # Netherlands to Singapore
            ('ROTTERDAM', 'FUJAIRAH'): 6800,             # Netherlands to Fujairah
            ('ROTTERDAM', 'GIBRALTAR'): 1750,            # Netherlands to Gibraltar
            ('ROTTERDAM', 'DURBAN'): 7000,               # Netherlands to Durban
            ('ROTTERDAM', 'QINGDAO'): 12500,             # Netherlands to Qingdao
            ('ROTTERDAM', 'SHANGHAI'): 12200,            # Netherlands to Shanghai
            ('ROTTERDAM', 'PORT LOUIS'): 7800,           # Netherlands to Port Louis
            ('ROTTERDAM', 'RICHARDS BAY'): 7200,         # Netherlands to Richards Bay

            # SALDANHA BAY (common vessel position) to bunker ports
            ('SALDANHA BAY', 'SINGAPORE'): 5600,         # S.Africa to Singapore
            ('SALDANHA BAY', 'FUJAIRAH'): 5000,          # S.Africa to Fujairah
            ('SALDANHA BAY', 'ROTTERDAM'): 7000,         # S.Africa to Rotterdam
            ('SALDANHA BAY', 'GIBRALTAR'): 5800,         # S.Africa to Gibraltar
            ('SALDANHA BAY', 'DURBAN'): 850,             # S.Africa to Durban
            ('SALDANHA BAY', 'QINGDAO'): 8800,           # S.Africa to Qingdao
            ('SALDANHA BAY', 'SHANGHAI'): 9200,          # S.Africa to Shanghai
            ('SALDANHA BAY', 'PORT LOUIS'): 1950,        # S.Africa to Port Louis
            ('SALDANHA BAY', 'RICHARDS BAY'): 900,       # S.Africa to Richards Bay
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

        # Same-port check — distance is 0 if ports resolve to the same name
        common = set(from_options) & set(to_options)
        if common:
            matched = next(iter(common))
            self._lookup_stats['csv'] += 1
            return 0.0, DistanceSource.CSV, matched, matched

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


# =============================================================================
# FREIGHT RATE ESTIMATION HELPERS
# =============================================================================

# FFA-based estimated rates for market cargoes with freight_rate == 0
_BRAZIL_ORIGINS = {"TUBARAO", "PONTA DA MADEIRA", "ITAGUAI"}
_AUSTRALIA_ORIGINS = {"HEDLAND", "DAMPIER"}


def estimate_freight_rate(cargo: Cargo) -> float:
    """Return an estimated freight rate for a cargo.

    If the cargo already has a non-zero freight rate, return it as-is.
    Otherwise estimate using FFA benchmarks:
      - Brazil origins (C3): $21/ton
      - Australia origins (C5): $9/ton
      - All others: $15/ton
    """
    if cargo.freight_rate != 0:
        return cargo.freight_rate

    port = cargo.load_port.upper()
    if any(origin in port for origin in _BRAZIL_ORIGINS):
        return 21.0
    if any(origin in port for origin in _AUSTRALIA_ORIGINS):
        return 9.0
    return 15.0


def apply_estimated_freight_rate(cargo: Cargo) -> Cargo:
    """Return a new Cargo with an estimated freight rate applied.

    If the cargo already has a non-zero freight rate, return it unchanged.
    """
    if cargo.freight_rate != 0:
        return cargo

    rate = estimate_freight_rate(cargo)
    return Cargo(
        name=cargo.name, customer=cargo.customer, commodity=cargo.commodity,
        quantity=cargo.quantity, quantity_tolerance=cargo.quantity_tolerance,
        laycan_start=cargo.laycan_start, laycan_end=cargo.laycan_end,
        freight_rate=rate,
        load_port=cargo.load_port, load_rate=cargo.load_rate,
        load_turn_time=cargo.load_turn_time,
        discharge_port=cargo.discharge_port, discharge_rate=cargo.discharge_rate,
        discharge_turn_time=cargo.discharge_turn_time,
        port_cost_load=cargo.port_cost_load, port_cost_discharge=cargo.port_cost_discharge,
        commission=cargo.commission, is_cargill=cargo.is_cargill,
        half_freight_threshold=cargo.half_freight_threshold,
    )


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
