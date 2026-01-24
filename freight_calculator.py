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
from typing import Optional, List, Dict, Tuple
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')


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
    
    # Port consumption
    port_idle_vlsfo: float
    port_working_vlsfo: float
    
    # Current position
    current_port: str
    etd: str                          # Estimated time of departure (date string)
    bunker_rob_vlsfo: float           # Remaining on board
    bunker_rob_mgo: float
    
    # Ownership flag (with default)
    is_cargill: bool = True
    port_mgo: float = 0.0             # Usually included in at-sea consumption


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


# =============================================================================
# PORT DISTANCE MANAGER
# =============================================================================

class PortDistanceManager:
    """Manages port-to-port distance lookups with fuzzy matching."""
    
    def __init__(self, csv_path: str = 'Port_Distances.csv'):
        self.df = pd.read_csv(csv_path)
        self.df['PORT_NAME_FROM'] = self.df['PORT_NAME_FROM'].str.upper()
        self.df['PORT_NAME_TO'] = self.df['PORT_NAME_TO'].str.upper()
        
        # Build lookup dict for speed
        self.distances = {}
        for _, row in self.df.iterrows():
            key = (row['PORT_NAME_FROM'], row['PORT_NAME_TO'])
            self.distances[key] = row['DISTANCE']
        
        # Port name mapping for common variations
        self.port_aliases = {
            'QINGDAO': ['QINGDAO', 'DAGANG (QINGDAO)'],
            'KAMSAR': ['KAMSAR ANCHORAGE', 'PORT KAMSAR'],
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
            'VANCOUVER': ['VANCOUVER'],
            'MANGALORE': ['MANGALORE', 'NEW MANGALORE'],
            'TELUK RUBIAH': ['TELUK RUBIAH'],
            'PORT TALBOT': ['PORT TALBOT'],
            'XIAMEN': ['XIAMEN'],
            'JINGTANG': ['JINGTANG'],
            'VIZAG': ['VIZAG', 'VISAKHAPATNAM'],
            'JUBAIL': ['JUBAIL'],
            'SHANGHAI': ['SHANGHAI'],
        }
        
        # Estimated distances for missing routes (based on typical shipping distances)
        self.estimated_distances = {
            # Existing estimates
            ('SINGAPORE', 'PORT HEDLAND'): 1678,
            ('MAP TA PHUT', 'PORT HEDLAND'): 2800,
            ('MAP TA PHUT', 'KAMSAR ANCHORAGE'): 9500,
            ('MAP TA PHUT', 'ITAGUAI'): 12500,
            ('GWANGYANG', 'KAMSAR ANCHORAGE'): 11500,
            ('GWANGYANG', 'PORT HEDLAND'): 3800,
            ('GWANGYANG', 'ITAGUAI'): 11800,

            # New vessel positions to load ports
            ('PORT TALBOT', 'KAMSAR ANCHORAGE'): 2800,
            ('PORT TALBOT', 'PORT HEDLAND'): 11500,
            ('PORT TALBOT', 'ITAGUAI'): 5200,
            ('PORT TALBOT', 'DAMPIER'): 11600,
            ('PORT TALBOT', 'TUBARAO'): 5100,
            ('PORT TALBOT', 'VANCOUVER'): 7800,

            ('JUBAIL', 'KAMSAR ANCHORAGE'): 6500,
            ('JUBAIL', 'PORT HEDLAND'): 5200,
            ('JUBAIL', 'ITAGUAI'): 9800,
            ('JUBAIL', 'TABONEO'): 4500,
            ('JUBAIL', 'TUBARAO'): 9700,

            ('JINGTANG', 'KAMSAR ANCHORAGE'): 12500,
            ('JINGTANG', 'PORT HEDLAND'): 4100,
            ('JINGTANG', 'ITAGUAI'): 12000,

            ('VIZAG', 'KAMSAR ANCHORAGE'): 7800,
            ('VIZAG', 'PORT HEDLAND'): 4200,
            ('VIZAG', 'ITAGUAI'): 10500,
            ('VIZAG', 'TABONEO'): 2100,

            ('MUNDRA', 'KAMSAR ANCHORAGE'): 6200,
            ('MUNDRA', 'PORT HEDLAND'): 4800,
            ('MUNDRA', 'ITAGUAI'): 9500,

            ('KANDLA', 'PORT HEDLAND'): 4900,
            ('KANDLA', 'KAMSAR ANCHORAGE'): 6100,

            # New cargo routes
            ('TABONEO', 'KRISHNAPATNAM'): 2400,
            ('VANCOUVER', 'FANGCHENG'): 5500,
            ('VANCOUVER', 'QINGDAO'): 5200,
            ('KAMSAR ANCHORAGE', 'MANGALORE'): 7200,
            ('TUBARAO', 'TELUK RUBIAH'): 10800,
            ('TUBARAO', 'QINGDAO'): 11500,

            # China internal routes
            ('FANGCHENG', 'KAMSAR ANCHORAGE'): 12000,
            ('FANGCHENG', 'PORT HEDLAND'): 3700,
            ('FANGCHENG', 'ITAGUAI'): 11600,

            ('XIAMEN', 'PORT HEDLAND'): 3600,
            ('XIAMEN', 'KAMSAR ANCHORAGE'): 12200,
            ('XIAMEN', 'ITAGUAI'): 11900,

            ('CAOFEIDIAN', 'PORT HEDLAND'): 4200,
            ('CAOFEIDIAN', 'KAMSAR ANCHORAGE'): 12600,
            ('CAOFEIDIAN', 'ITAGUAI'): 12100,

            # Rotterdam routes
            ('ROTTERDAM', 'PORT HEDLAND'): 11500,
            ('ROTTERDAM', 'KAMSAR ANCHORAGE'): 3200,
            ('ROTTERDAM', 'ITAGUAI'): 5500,
        }
    
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
        """Get distance between two ports in nautical miles."""
        from_options = self._normalize_port(port_from)
        to_options = self._normalize_port(port_to)
        
        # Try all combinations
        for f in from_options:
            for t in to_options:
                # Direct lookup
                if (f, t) in self.distances:
                    return self.distances[(f, t)]
                # Reverse lookup
                if (t, f) in self.distances:
                    return self.distances[(t, f)]
        
        # Check estimated distances
        for f in from_options:
            for t in to_options:
                key1 = (f, t)
                key2 = (t, f)
                for k in [key1, key2]:
                    for est_key, dist in self.estimated_distances.items():
                        if (est_key[0] in k[0] or k[0] in est_key[0]) and \
                           (est_key[1] in k[1] or k[1] in est_key[1]):
                            return dist
        
        return None


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
    
    def __init__(self, distance_manager: PortDistanceManager, bunker_prices: BunkerPrices):
        self.distances = distance_manager
        self.bunker_prices = bunker_prices
    
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
        # Typical Capesize constants ~3000-5000 MT for bunkers, stores, etc.
        max_by_cargo = int(cargo.quantity * (1 + cargo.quantity_tolerance))
        min_by_cargo = int(cargo.quantity * (1 - cargo.quantity_tolerance))
        max_by_vessel = vessel.dwt - 3500  # Reserve for bunkers/stores

        # Maximize cargo within constraints (owner's option to load more)
        cargo_qty = min(max_by_cargo, max_by_vessel)

        # Ensure we meet minimum cargo requirement
        if cargo_qty < min_by_cargo:
            raise ValueError(f"Vessel {vessel.name} cannot meet minimum cargo requirement for {cargo.name}")
        
        # Check half freight threshold
        half_freight_qty = 0
        if cargo.half_freight_threshold and cargo_qty > cargo.half_freight_threshold:
            half_freight_qty = cargo_qty - cargo.half_freight_threshold
            cargo_qty = cargo.half_freight_threshold  # For full freight calculation
        
        # -----------------------------------------------------------------
        # 4. PORT TIME
        # -----------------------------------------------------------------
        # Loading time = cargo / load_rate + turn_time
        load_days = (cargo_qty + half_freight_qty) / cargo.load_rate + cargo.load_turn_time / 24
        
        # Discharge time = cargo / discharge_rate + turn_time
        discharge_days = (cargo_qty + half_freight_qty) / cargo.discharge_rate + cargo.discharge_turn_time / 24
        
        # Add scenario delay
        load_days += extra_port_delay_days / 2  # Split delay between ports
        discharge_days += extra_port_delay_days / 2
        
        # -----------------------------------------------------------------
        # 5. LAYCAN CHECK
        # -----------------------------------------------------------------
        etd = datetime.strptime(vessel.etd, '%d %b %Y')
        arrival_at_loadport = etd + timedelta(days=ballast_days)
        laycan_start = datetime.strptime(cargo.laycan_start, '%d %b %Y')
        laycan_end = datetime.strptime(cargo.laycan_end, '%d %b %Y')
        
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
        
        # In port - working
        working_days = load_days + discharge_days - (cargo.load_turn_time + cargo.discharge_turn_time) / 24
        vlsfo_working = working_days * vessel.port_working_vlsfo
        
        # In port - idle (waiting + turn times)
        idle_days = waiting_days + (cargo.load_turn_time + cargo.discharge_turn_time) / 24
        vlsfo_idle = idle_days * vessel.port_idle_vlsfo
        
        # Total fuel
        vlsfo_consumed = vlsfo_ballast + vlsfo_laden + vlsfo_working + vlsfo_idle
        mgo_consumed = mgo_ballast + mgo_laden
        
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
        # 9. REVENUE
        # -----------------------------------------------------------------
        gross_freight = cargo_qty * cargo.freight_rate
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
        
        # Miscellaneous (canal fees, surveys, etc.) - estimate
        misc_costs = 15000  # Typical for Capesize
        
        # -----------------------------------------------------------------
        # 11. PROFIT CALCULATION
        # -----------------------------------------------------------------
        total_costs = total_bunker_cost + hire_cost + port_costs + misc_costs
        
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
        tce = (net_freight - voyage_costs) / total_days if total_days > 0 else 0
        
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
            cargo_quantity=cargo_qty + half_freight_qty,
            
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
            port_idle_vlsfo=2.0, port_working_vlsfo=3.0,
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
            port_idle_vlsfo=1.8, port_working_vlsfo=3.2,
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
            port_idle_vlsfo=2.0, port_working_vlsfo=3.0,
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
            port_idle_vlsfo=1.9, port_working_vlsfo=3.1,
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
            port_idle_vlsfo=2.0, port_working_vlsfo=3.0,
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
            port_idle_vlsfo=1.9, port_working_vlsfo=3.0,
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
            port_idle_vlsfo=2.0, port_working_vlsfo=3.1,
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
            port_idle_vlsfo=1.8, port_working_vlsfo=3.0,
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
            port_idle_vlsfo=2.0, port_working_vlsfo=3.1,
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
            port_idle_vlsfo=2.1, port_working_vlsfo=3.2,
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
            port_idle_vlsfo=2.0, port_working_vlsfo=3.1,
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
            port_idle_vlsfo=1.8, port_working_vlsfo=3.0,
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
            port_idle_vlsfo=2.0, port_working_vlsfo=3.1,
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
            port_idle_vlsfo=1.9, port_working_vlsfo=3.1,
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
            port_idle_vlsfo=2.0, port_working_vlsfo=3.0,
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
