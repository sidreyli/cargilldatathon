"""
Portfolio Optimizer & Scenario Analysis
=======================================
Optimizes vessel-cargo assignments across the entire portfolio.

Valid combinations:
1. Cargill vessels -> Cargill cargoes (committed obligations - MUST fulfill)
2. Cargill vessels -> Market cargoes (bidding opportunities)
3. Market vessels -> Cargill cargoes (hire to cover committed cargoes)

NOT valid: Market vessels -> Market cargoes (not Cargill's business model)
"""

import pandas as pd
import numpy as np
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass, field
from itertools import combinations, permutations, product

# Handle both package imports and direct imports (from notebooks)
try:
    from .freight_calculator import (
        FreightCalculator, PortDistanceManager, BunkerPrices,
        Vessel, Cargo, VoyageResult, VoyageConfig,
        create_cargill_vessels, create_cargill_cargoes,
        create_market_vessels, create_market_cargoes, create_bunker_prices
    )
except ImportError:
    from freight_calculator import (
        FreightCalculator, PortDistanceManager, BunkerPrices,
        Vessel, Cargo, VoyageResult, VoyageConfig,
        create_cargill_vessels, create_cargill_cargoes,
        create_market_vessels, create_market_cargoes, create_bunker_prices
    )

try:
    from scipy.optimize import linear_sum_assignment
    HAS_SCIPY = True
except ImportError:
    HAS_SCIPY = False

# China discharge ports for port delay sensitivity analysis
CHINA_DISCHARGE_PORTS = {'QINGDAO', 'RIZHAO', 'CAOFEIDIAN', 'FANGCHENG',
                          'LIANYUNGANG', 'SHANGHAI', 'TIANJIN', 'DALIAN'}

# ML Model availability
try:
    from .ml import PortCongestionPredictor
    HAS_ML_MODEL = True
except ImportError:
    try:
        from ml import PortCongestionPredictor
        HAS_ML_MODEL = True
    except ImportError:
        HAS_ML_MODEL = False


@dataclass
class VoyageOption:
    """A single voyage option with all economics calculated."""
    vessel: Vessel
    cargo: Cargo
    result: Optional[VoyageResult]
    can_make_laycan: bool

    # Economics
    tce: float = 0.0
    net_profit: float = 0.0
    voyage_days: float = 0.0

    # For market vessels: recommended max hire rate
    recommended_hire_rate: float = 0.0

    # For market cargoes: minimum freight rate to break even
    min_freight_rate: float = 0.0
    min_freight_bid: float = 0.0  # Alias for min_freight_rate

    # Classification
    vessel_type: str = ""  # "cargill" or "market"
    cargo_type: str = ""   # "cargill" or "market"

    error: Optional[str] = None


@dataclass
class FullPortfolioResult:
    """Results of a full portfolio optimization including market options."""

    # Core assignments
    cargill_vessel_assignments: List[Tuple[str, str, VoyageOption]]
    market_vessel_assignments: List[Tuple[str, str, VoyageOption]]

    # Unassigned
    unassigned_cargill_vessels: List[str]
    unassigned_cargill_cargoes: List[str]  # These MUST be covered by market vessels!

    # Financials
    total_profit: float
    total_tce: float
    avg_tce: float

    # Market recommendations
    market_vessel_hire_offers: Dict[str, float] = field(default_factory=dict)
    market_cargo_freight_bids: Dict[str, float] = field(default_factory=dict)

    # All voyage options for analysis
    all_options: pd.DataFrame = field(default_factory=pd.DataFrame)


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
        port_delays: Optional[Dict[str, float]] = None,
        dual_speed_mode: bool = False,
    ) -> pd.DataFrame:
        """
        Calculate voyage economics for all vessel-cargo combinations.

        Args:
            vessels: List of vessels
            cargoes: List of cargoes
            use_eco_speed: Whether to use eco speed (ignored if dual_speed_mode=True)
            extra_port_delay: Base extra delay to add to all voyages
            bunker_adjustment: Bunker price multiplier
            port_delays: Optional dict mapping port names to delay days
                         e.g., {"Qingdao": 3.5, "Mundra": 2.0}
                         If provided, overrides extra_port_delay for matching ports
            dual_speed_mode: If True, calculate BOTH eco and warranted speeds for each
                             vessel-cargo pair. This doubles the solution space and allows
                             the optimizer to choose between speed vs fuel consumption tradeoffs.

        Returns DataFrame with all results.
        """
        results = []

        # Determine which speeds to calculate
        if dual_speed_mode:
            speed_options = [True, False]  # [eco, warranted]
        else:
            speed_options = [use_eco_speed]

        for vessel in vessels:
            for cargo in cargoes:
                for eco_speed in speed_options:
                    try:
                        # Determine port-specific delay
                        delay = extra_port_delay
                        if port_delays:
                            # Check for discharge port in port_delays dict
                            port_name = cargo.discharge_port.upper()
                            for key, value in port_delays.items():
                                if key.upper() in port_name or port_name in key.upper():
                                    delay = value
                                    break

                        result = self.calculator.calculate_voyage(
                            vessel, cargo,
                            use_eco_speed=eco_speed,
                            extra_port_delay_days=delay,
                            bunker_price_adjustment=bunker_adjustment,
                        )

                        results.append({
                            'vessel': vessel.name,
                            'cargo': cargo.name,
                            'speed_type': 'eco' if eco_speed else 'warranted',
                            'can_make_laycan': result.can_make_laycan,
                            'arrival_date': result.arrival_date,
                            'laycan_end': result.laycan_end,
                            'days_margin': (result.laycan_end - result.arrival_date).total_seconds() / 86400,
                            'total_days': result.total_days,
                            'cargo_qty': result.cargo_quantity,
                            'net_freight': result.net_freight,
                            'total_bunker_cost': result.total_bunker_cost,
                            'hire_cost': result.hire_cost,
                            'port_costs': result.port_costs,
                            'net_profit': result.net_profit,
                            'tce': result.tce,
                            'vlsfo_consumed': result.vlsfo_consumed,
                            'bunker_port': result.selected_bunker_port or 'No bunker',
                            'bunker_savings': result.bunker_port_savings,
                            'bunker_vlsfo_qty': result.bunker_fuel_vlsfo_qty,
                            'bunker_mgo_qty': result.bunker_fuel_mgo_qty,
                            'result': result,
                        })
                    except Exception as e:
                        results.append({
                            'vessel': vessel.name,
                            'cargo': cargo.name,
                            'speed_type': 'eco' if eco_speed else 'warranted',
                            'can_make_laycan': False,
                            'error': str(e),
                            'tce': np.nan,
                            'net_profit': np.nan,
                            'result': None,
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
        port_delays: Optional[Dict[str, float]] = None,
        dual_speed_mode: bool = False,
    ) -> PortfolioResult:
        """
        Find optimal vessel-cargo assignments.

        Uses the Hungarian algorithm (O(n³)) when scipy is available, falling back
        to brute force enumeration for small problems or when scipy is not installed.

        Args:
            vessels: List of available vessels
            cargoes: List of cargoes to assign
            use_eco_speed: Whether to use economical speed (ignored if dual_speed_mode=True)
            extra_port_delay: Additional port delay days for scenario analysis
            bunker_adjustment: Bunker price multiplier for scenario analysis
            maximize: Optimization target ('profit' or 'tce')
            include_negative_profit: Whether to include negative profit assignments
            dual_speed_mode: If True, calculate BOTH eco and warranted speeds. This allows
                             the optimizer to select warranted speed when it enables meeting
                             laycans or provides better profit despite higher fuel costs.

        Returns:
            PortfolioResult with optimal assignments
        """
        # Calculate all voyage options
        df = self.calculate_all_voyages(
            vessels, cargoes, use_eco_speed, extra_port_delay, bunker_adjustment,
            port_delays=port_delays, dual_speed_mode=dual_speed_mode
        )

        # Filter to only valid voyages (can make laycan)
        valid_df = df[df['can_make_laycan']].copy()

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

        # In dual-speed mode, keep only the BEST speed option for each vessel-cargo pair
        # This simplifies optimization while still exploring warranted speed options
        if dual_speed_mode:
            # Group by vessel-cargo and keep the row with highest value
            value_key = 'net_profit' if maximize == 'profit' else 'tce'
            valid_df = valid_df.loc[valid_df.groupby(['vessel', 'cargo'])[value_key].idxmax()]

        # Get unique vessels and cargoes that have valid options
        valid_vessels = valid_df['vessel'].unique().tolist()
        valid_cargoes = valid_df['cargo'].unique().tolist()

        # Build lookup for results using efficient pandas indexing
        valid_df_indexed = valid_df.set_index(['vessel', 'cargo'])
        voyage_lookup = valid_df_indexed.to_dict('index')

        # Choose optimization method
        n_vessels = len(valid_vessels)
        n_cargoes = len(valid_cargoes)

        # Use Hungarian algorithm for larger problems if scipy available
        if HAS_SCIPY and (n_vessels > 5 or n_cargoes > 5):
            return self._optimize_hungarian(
                vessels, cargoes, valid_vessels, valid_cargoes,
                voyage_lookup, maximize
            )
        else:
            return self._optimize_brute_force(
                vessels, cargoes, valid_vessels, valid_cargoes,
                voyage_lookup, maximize
            )

    def _optimize_hungarian(
        self,
        vessels: List[Vessel],
        cargoes: List[Cargo],
        valid_vessels: List[str],
        valid_cargoes: List[str],
        voyage_lookup: Dict,
        maximize: str,
    ) -> PortfolioResult:
        """
        Optimize assignments using the Hungarian algorithm (O(n³)).
        """
        n_vessels = len(valid_vessels)
        n_cargoes = len(valid_cargoes)

        # Build cost matrix (negative because Hungarian minimizes)
        # Use a large penalty for invalid assignments
        INVALID_PENALTY = 1e12
        cost_matrix = np.full((n_vessels, n_cargoes), INVALID_PENALTY)

        value_key = 'net_profit' if maximize == 'profit' else 'tce'

        for i, vessel in enumerate(valid_vessels):
            for j, cargo in enumerate(valid_cargoes):
                key = (vessel, cargo)
                if key in voyage_lookup:
                    # Negate because Hungarian algorithm minimizes
                    cost_matrix[i, j] = -voyage_lookup[key][value_key]

        # Run Hungarian algorithm
        row_ind, col_ind = linear_sum_assignment(cost_matrix)

        # Build assignments, filtering out invalid ones
        best_assignments = []
        total_profit = 0
        total_tce = 0

        for i, j in zip(row_ind, col_ind):
            if cost_matrix[i, j] < INVALID_PENALTY:
                vessel = valid_vessels[i]
                cargo = valid_cargoes[j]
                key = (vessel, cargo)
                row = voyage_lookup[key]

                # Skip negative profit assignments if the value is negative
                if row['net_profit'] <= 0 and maximize == 'profit':
                    continue

                best_assignments.append((vessel, cargo, row.get('result')))
                total_profit += row['net_profit']
                total_tce += row['tce']

        # Determine unassigned vessels and cargoes
        assigned_vessels = set(a[0] for a in best_assignments)
        assigned_cargoes = set(a[1] for a in best_assignments)

        unassigned_vessels = [v.name for v in vessels if v.name not in assigned_vessels]
        unassigned_cargoes = [c.name for c in cargoes if c.name not in assigned_cargoes]

        return PortfolioResult(
            assignments=best_assignments,
            unassigned_vessels=unassigned_vessels,
            unassigned_cargoes=unassigned_cargoes,
            total_profit=total_profit,
            total_tce=total_tce,
            avg_tce=total_tce / len(best_assignments) if best_assignments else 0,
        )

    def _optimize_brute_force(
        self,
        vessels: List[Vessel],
        cargoes: List[Cargo],
        valid_vessels: List[str],
        valid_cargoes: List[str],
        voyage_lookup: Dict,
        maximize: str,
    ) -> PortfolioResult:
        """
        Optimize assignments using brute force enumeration.

        Suitable for small problems (< 6 vessels/cargoes).
        """

        best_score = float('-inf')
        best_profit = 0
        best_tce = 0
        best_assignments = []

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


class FullPortfolioOptimizer:
    """
    Optimizes the FULL portfolio with valid combinations only:
    1. Cargill vessels -> Cargill cargoes (committed - MUST fulfill)
    2. Cargill vessels -> Market cargoes (opportunity to bid)
    3. Market vessels -> Cargill cargoes (hire when Cargill can't cover)

    NOT valid: Market vessels -> Market cargoes (not our business)

    Key insight: Cargill cargoes MUST be covered. If Cargill vessels can't
    make it, we MUST hire market vessels.
    """

    def __init__(self, calculator: FreightCalculator):
        self.calculator = calculator

    def calculate_all_options(
        self,
        cargill_vessels: List[Vessel],
        market_vessels: List[Vessel],
        cargill_cargoes: List[Cargo],
        market_cargoes: List[Cargo],
        use_eco_speed: bool = True,
        target_tce: float = 18000,  # Target profit/day for calculations
        dual_speed_mode: bool = False,
        port_delays: Dict[str, float] = None,  # Port name -> extra delay days
    ) -> pd.DataFrame:
        """
        Calculate voyage economics for VALID vessel-cargo combinations only.

        Valid combinations:
        1. Cargill vessel → Cargill cargo (committed, must fulfill)
        2. Cargill vessel → Market cargo (opportunity to bid)
        3. Market vessel → Cargill cargo (hire to cover committed cargo)

        NOT valid:
        - Market vessel → Market cargo (not our business model)

        Args:
            port_delays: Dict mapping port names to extra delay days (e.g., from ML predictions)
        """
        results = []
        port_delays = port_delays or {}

        # Determine which speeds to calculate
        if dual_speed_mode:
            speed_options = [True, False]  # [eco, warranted]
        else:
            speed_options = [use_eco_speed]

        def get_port_delay(cargo: Cargo) -> float:
            """Get extra delay for cargo's discharge port."""
            return port_delays.get(cargo.discharge_port, 0)

        # 1. Cargill vessels → Cargill cargoes
        for vessel in cargill_vessels:
            for cargo in cargill_cargoes:
                extra_delay = get_port_delay(cargo)
                for eco_speed in speed_options:
                    option = self._calculate_option(
                        vessel, cargo, "cargill", "cargill",
                        eco_speed, target_tce, extra_delay
                    )
                    speed_type = 'eco' if eco_speed else 'warranted'
                    results.append(self._option_to_dict(option, speed_type))

        # 2. Cargill vessels → Market cargoes
        for vessel in cargill_vessels:
            for cargo in market_cargoes:
                extra_delay = get_port_delay(cargo)
                for eco_speed in speed_options:
                    option = self._calculate_option(
                        vessel, cargo, "cargill", "market",
                        eco_speed, target_tce, extra_delay
                    )
                    speed_type = 'eco' if eco_speed else 'warranted'
                    results.append(self._option_to_dict(option, speed_type))

        # 3. Market vessels → Cargill cargoes ONLY
        for vessel in market_vessels:
            for cargo in cargill_cargoes:
                extra_delay = get_port_delay(cargo)
                for eco_speed in speed_options:
                    option = self._calculate_option(
                        vessel, cargo, "market", "cargill",
                        eco_speed, target_tce, extra_delay
                    )
                    speed_type = 'eco' if eco_speed else 'warranted'
                    results.append(self._option_to_dict(option, speed_type))

        return pd.DataFrame(results)

    def _option_to_dict(self, option: VoyageOption, speed_type: str = 'eco') -> dict:
        """Convert VoyageOption to dictionary for DataFrame."""
        return {
            'vessel': option.vessel.name,
            'cargo': option.cargo.name,
            'vessel_type': option.vessel_type,
            'cargo_type': option.cargo_type,
            'speed_type': speed_type,
            'can_make_laycan': option.can_make_laycan,
            'tce': option.tce,
            'net_profit': option.net_profit,
            'recommended_hire_rate': option.recommended_hire_rate,
            'min_freight_rate': option.min_freight_rate,
            'total_days': option.result.total_days if option.result else 0,
            'cargo_qty': option.result.cargo_quantity if option.result else 0,
            'net_freight': option.result.net_freight if option.result else 0,
            'total_bunker_cost': option.result.total_bunker_cost if option.result else 0,
            'port_costs': option.result.port_costs if option.result else 0,
            'bunker_port': option.result.selected_bunker_port if option.result else 'No bunker',
            'bunker_savings': option.result.bunker_port_savings if option.result else 0,
            'bunker_vlsfo_qty': option.result.bunker_fuel_vlsfo_qty if option.result else 0,
            'bunker_mgo_qty': option.result.bunker_fuel_mgo_qty if option.result else 0,
            'error': option.error,
            'result': option.result,
            'option': option,
        }

    def _calculate_option(
        self,
        vessel: Vessel,
        cargo: Cargo,
        vessel_type: str,
        cargo_type: str,
        use_eco_speed: bool,
        target_tce: float,
        extra_port_delay: float = 0,
    ) -> VoyageOption:
        """Calculate a single voyage option with all economics."""

        try:
            # For market cargoes, temporarily set a rate to calculate voyage
            temp_cargo = cargo
            if cargo.freight_rate == 0:
                # Use FFA rate as estimate (C3 Brazil-China ~$21, C5 WA-China ~$9)
                if 'BRAZIL' in cargo.load_port.upper() or 'ITAGUAI' in cargo.load_port.upper() or 'TUBARAO' in cargo.load_port.upper():
                    estimated_rate = 21.0
                elif 'AUSTRALIA' in cargo.load_port.upper() or 'HEDLAND' in cargo.load_port.upper() or 'DAMPIER' in cargo.load_port.upper():
                    estimated_rate = 9.0
                else:
                    estimated_rate = 15.0  # Default estimate

                # Create temporary cargo with estimated rate
                temp_cargo = Cargo(
                    name=cargo.name, customer=cargo.customer, commodity=cargo.commodity,
                    quantity=cargo.quantity, quantity_tolerance=cargo.quantity_tolerance,
                    laycan_start=cargo.laycan_start, laycan_end=cargo.laycan_end,
                    freight_rate=estimated_rate,
                    load_port=cargo.load_port, load_rate=cargo.load_rate, load_turn_time=cargo.load_turn_time,
                    discharge_port=cargo.discharge_port, discharge_rate=cargo.discharge_rate,
                    discharge_turn_time=cargo.discharge_turn_time,
                    port_cost_load=cargo.port_cost_load, port_cost_discharge=cargo.port_cost_discharge,
                    commission=cargo.commission, is_cargill=cargo.is_cargill,
                    half_freight_threshold=cargo.half_freight_threshold,
                )

            result = self.calculator.calculate_voyage(
                vessel, temp_cargo, use_eco_speed=use_eco_speed,
                extra_port_delay_days=extra_port_delay
            )

            # Calculate economics based on vessel/cargo type combination
            tce = result.tce
            net_profit = result.net_profit
            recommended_hire = 0.0
            min_freight = 0.0

            # For MARKET VESSELS: Calculate max hire rate we'd pay
            if vessel_type == "market":
                # We receive freight, pay voyage costs, and want target_tce as our daily PROFIT
                # Our Profit = Net Freight - Voyage Costs - Hire
                # Hire = Net Freight - Voyage Costs - (target_profit * Days)
                voyage_costs = result.total_bunker_cost + result.port_costs + result.misc_costs
                max_total_hire = result.net_freight - voyage_costs - (target_tce * result.total_days)
                recommended_hire = max_total_hire / result.total_days if result.total_days > 0 else 0
                recommended_hire = max(0, recommended_hire)  # Can't be negative

                # Cargill's profit = Net Freight - Voyage Costs - Hire Paid
                if recommended_hire > 0:
                    net_profit = result.net_freight - voyage_costs - (recommended_hire * result.total_days)
                else:
                    net_profit = result.net_freight - voyage_costs

            # For MARKET CARGOES: Calculate minimum freight rate to bid
            if cargo_type == "market":
                voyage_costs = result.total_bunker_cost + result.port_costs + result.misc_costs

                if vessel_type == "cargill":
                    # For Cargill vessels: We want PROFIT = target_tce per day
                    # Profit = Net Freight - Voyage Costs - Hire
                    # Required Net Freight = Voyage Costs + Hire + (target_profit * Days)
                    hire_cost = vessel.hire_rate * result.total_days
                    required_net_freight = voyage_costs + hire_cost + (target_tce * result.total_days)
                else:
                    # For market vessels on market cargo: unlikely scenario but handle it
                    # We'd pay hire and want profit margin
                    required_net_freight = voyage_costs + (target_tce * result.total_days)

                required_gross_freight = required_net_freight / (1 - cargo.commission)
                min_freight = required_gross_freight / result.cargo_quantity if result.cargo_quantity > 0 else 0

            return VoyageOption(
                vessel=vessel,
                cargo=cargo,
                result=result,
                can_make_laycan=result.can_make_laycan,
                tce=tce,
                net_profit=net_profit,
                voyage_days=result.total_days,
                recommended_hire_rate=recommended_hire,
                min_freight_rate=min_freight,
                min_freight_bid=min_freight,  # Alias
                vessel_type=vessel_type,
                cargo_type=cargo_type,
            )

        except Exception as e:
            return VoyageOption(
                vessel=vessel,
                cargo=cargo,
                result=None,
                can_make_laycan=False,
                tce=0,
                net_profit=0,
                voyage_days=0,
                vessel_type=vessel_type,
                cargo_type=cargo_type,
                error=str(e),
            )

    def _exhaustive_market_assignments(
        self,
        remaining_vessels: List[Vessel],
        vessel_market_lookup: Dict[str, Dict[str, object]],
    ) -> Tuple[float, list]:
        """
        Find the profit-maximizing assignment of remaining Cargill vessels
        to market cargoes by exhaustively searching all valid permutations.

        With at most 4 vessels and 8 market cargoes, the search space is small
        (~3,400 permutations worst case), so brute force is fast and exact.

        Args:
            remaining_vessels: Cargill vessels not assigned to committed cargoes
            vessel_market_lookup: Pre-built dict {vessel_name: {cargo_name: row}}
                where each row meets the minimum daily profit threshold

        Returns:
            (total_profit, list_of_assignment_rows)
        """
        if not remaining_vessels:
            return 0, []

        vessel_names = [v.name for v in remaining_vessels]

        # Collect all market cargoes reachable by any remaining vessel
        all_market_cargoes = list(set(
            cargo
            for vname in vessel_names
            for cargo in vessel_market_lookup.get(vname, {}).keys()
        ))

        n_vessels = len(vessel_names)
        n_cargoes = len(all_market_cargoes)

        best_profit = 0
        best_assignments = []

        # Try all assignment sizes: 0 vessels assigned, 1, ..., min(N, M)
        for k in range(min(n_vessels, n_cargoes) + 1):
            for vessel_idx in combinations(range(n_vessels), k):
                for cargo_idx in permutations(range(n_cargoes), k):
                    total_profit = 0
                    assignments = []
                    valid = True

                    for vi, ci in zip(vessel_idx, cargo_idx):
                        vname = vessel_names[vi]
                        cname = all_market_cargoes[ci]
                        lookup = vessel_market_lookup.get(vname, {})

                        if cname in lookup:
                            total_profit += lookup[cname]['net_profit']
                            assignments.append(lookup[cname])
                        else:
                            valid = False
                            break

                    if valid and total_profit > best_profit:
                        best_profit = total_profit
                        best_assignments = list(assignments)

        return best_profit, best_assignments

    def optimize_full_portfolio(
        self,
        cargill_vessels: List[Vessel],
        market_vessels: List[Vessel],
        cargill_cargoes: List[Cargo],
        market_cargoes: List[Cargo],
        use_eco_speed: bool = True,
        target_tce: float = 18000,
        dual_speed_mode: bool = False,
        top_n: int = 1,
        port_delays: Dict[str, float] = None,  # Port name -> extra delay days
    ) -> List[FullPortfolioResult]:
        """
        Optimize the full portfolio using JOINT OPTIMIZATION.

        Key insight: A Cargill vessel might earn MORE on a market cargo than a
        Cargill cargo. We could hire a market vessel cheaply for the Cargill cargo
        and come out ahead.

        Algorithm:
        1. Generate all valid options
        2. Enumerate all ways to cover Cargill cargoes (using Cargill OR market vessels)
        3. For each coverage, exhaustively assign remaining Cargill vessels to market cargoes
        4. Pick the combination with highest total profit

        Hard constraint: Every Cargill cargo MUST be covered by exactly one vessel.

        Args:
            port_delays: Dict mapping port names to extra delay days (e.g., from ML predictions)
        """

        # Step 1: Calculate all options
        all_options = self.calculate_all_options(
            cargill_vessels, market_vessels,
            cargill_cargoes, market_cargoes,
            use_eco_speed, target_tce, dual_speed_mode,
            port_delays=port_delays
        )

        # Step 2: Filter to valid options (can make laycan)
        valid_options = all_options[all_options['can_make_laycan']].copy()

        # In dual-speed mode, keep only the BEST speed option for each vessel-cargo pair
        if dual_speed_mode:
            # Group by vessel-cargo and keep the row with highest profit
            valid_options = valid_options.loc[
                valid_options.groupby(['vessel', 'cargo'])['net_profit'].idxmax()
            ]

        # FFA market rate for hiring market vessels (5TC March 2026: $18,454/day)
        FFA_MARKET_RATE = 18000

        # Minimum daily profit threshold for market cargo assignments
        MIN_DAILY_PROFIT = 5000

        # Step 3: Build coverage options for each Cargill cargo
        # For each cargo, list all vessels (Cargill + market) that can serve it
        cargo_coverage = {}
        for cargo in cargill_cargoes:
            cargo_coverage[cargo.name] = []

            # Get all valid options for this cargo
            cargo_options = valid_options[valid_options['cargo'] == cargo.name]

            for _, row in cargo_options.iterrows():
                if row['vessel_type'] == 'cargill':
                    # Cargill vessel: use net_profit directly (already includes hire cost)
                    profit = row['net_profit']
                else:
                    # Market vessel: Cargill's profit = Net Freight - Voyage Costs - Hire
                    # Where hire is at FFA market rate
                    hire_cost = FFA_MARKET_RATE * row['total_days']
                    voyage_costs = row['total_bunker_cost'] + row['port_costs'] + 15000  # misc
                    profit = row['net_freight'] - voyage_costs - hire_cost

                cargo_coverage[cargo.name].append({
                    'vessel': row['vessel'],
                    'vessel_type': row['vessel_type'],
                    'profit': profit,
                    'option': row['option'],
                    'total_days': row['total_days'],
                })

        # Check if any Cargill cargo has no coverage
        uncoverable_cargoes = [c for c in cargill_cargoes if len(cargo_coverage[c.name]) == 0]
        if uncoverable_cargoes:
            # Some cargoes cannot be covered - return best effort result
            return [self._build_fallback_result(
                cargill_vessels, market_vessels, cargill_cargoes, market_cargoes,
                valid_options, all_options, uncoverable_cargoes
            )]

        # Step 4: Enumerate all coverage combinations using itertools.product
        # Track top N combinations using a list sorted by profit
        import heapq
        top_combinations = []  # List of (profit, coverage_combo, market_assignments)

        coverage_lists = [cargo_coverage[c.name] for c in cargill_cargoes]

        # Precompute valid market cargo options for each Cargill vessel
        vessel_market_lookup = {}
        for vessel in cargill_vessels:
            vessel_market_lookup[vessel.name] = {}
            vessel_opts = valid_options[
                (valid_options['vessel'] == vessel.name) &
                (valid_options['cargo_type'] == 'market')
            ]
            for _, row in vessel_opts.iterrows():
                if row['total_days'] > 0:
                    daily_profit = row['net_profit'] / row['total_days']
                    if daily_profit > MIN_DAILY_PROFIT and row['net_profit'] > MIN_DAILY_PROFIT * 30:
                        vessel_market_lookup[vessel.name][row['cargo']] = row

        # Log coverage options per cargo
        total_product_combos = 1
        for cargo in cargill_cargoes:
            n_options = len(cargo_coverage[cargo.name])
            total_product_combos *= n_options
            print(f"  Cargo '{cargo.name}': {n_options} vessel options")
        print(f"  Total theoretical combinations (product): {total_product_combos}")

        combo_id = 0
        for coverage_combo in product(*coverage_lists):
            # Check no vessel used twice for Cargill cargoes
            vessels_used = [c['vessel'] for c in coverage_combo]
            if len(vessels_used) != len(set(vessels_used)):
                continue  # Skip invalid (same vessel for multiple cargoes)

            # Calculate profit from Cargill cargo coverage
            coverage_profit = sum(c['profit'] for c in coverage_combo)

            # Step 5: Exhaustively assign remaining Cargill vessels to market cargoes
            used_vessels = set(vessels_used)
            remaining_cargill = [v for v in cargill_vessels if v.name not in used_vessels]

            market_profit, market_assignments = self._exhaustive_market_assignments(
                remaining_cargill, vessel_market_lookup
            )

            # Total profit for this combination
            total_profit = coverage_profit + market_profit

            # Use heapq to maintain top N (min-heap of negated profits)
            combo_id += 1
            if len(top_combinations) < top_n:
                heapq.heappush(top_combinations, (total_profit, combo_id, coverage_combo, list(market_assignments)))
            elif total_profit > top_combinations[0][0]:
                heapq.heapreplace(top_combinations, (total_profit, combo_id, coverage_combo, list(market_assignments)))

        print(f"  Valid portfolio combinations (no vessel reuse): {combo_id}")

        # Step 6: Build results from top N assignments
        if not top_combinations:
            # No valid combination found
            return [self._build_fallback_result(
                cargill_vessels, market_vessels, cargill_cargoes, market_cargoes,
                valid_options, all_options, []
            )]

        # Sort by profit descending and build results
        top_combinations.sort(key=lambda x: -x[0])

        # Market recommendations - find best options for reference (shared across all results)
        hire_offers = {}
        market_on_cargill = valid_options[
            (valid_options['vessel_type'] == 'market') &
            (valid_options['cargo_type'] == 'cargill')
        ]
        for _, row in market_on_cargill.iterrows():
            if row['recommended_hire_rate'] > 0:
                cargo = row['cargo']
                vessel = row['vessel']
                key = f"{vessel} for {cargo}"
                hire_offers[key] = row['recommended_hire_rate']

        freight_bids = {}
        cargill_on_market = valid_options[
            (valid_options['vessel_type'] == 'cargill') &
            (valid_options['cargo_type'] == 'market')
        ]
        for _, row in cargill_on_market.iterrows():
            if row['min_freight_rate'] > 0:
                cargo = row['cargo']
                if cargo not in freight_bids or row['min_freight_rate'] < freight_bids[cargo]:
                    freight_bids[cargo] = row['min_freight_rate']

        # Build results for each top combination
        results = []
        for combo_profit, _, coverage_combo, combo_market_assignments in top_combinations:
            # Build assignment lists
            cargill_assignments = []
            market_assignments = []
            assigned_vessels = set()
            assigned_cargoes = set()

            # Process Cargill cargo coverage
            for i, coverage in enumerate(coverage_combo):
                cargo_name = cargill_cargoes[i].name
                vessel_name = coverage['vessel']
                option = coverage['option']

                if coverage['vessel_type'] == 'cargill':
                    cargill_assignments.append((vessel_name, cargo_name, option))
                else:
                    market_assignments.append((vessel_name, cargo_name, option))

                assigned_vessels.add(vessel_name)
                assigned_cargoes.add(cargo_name)

            # Add market cargo assignments for remaining Cargill vessels
            for row in combo_market_assignments:
                cargill_assignments.append((row['vessel'], row['cargo'], row['option']))
                assigned_vessels.add(row['vessel'])
                assigned_cargoes.add(row['cargo'])

            # Calculate totals
            total_profit = combo_profit
            total_tce = sum(opt.tce for _, _, opt in cargill_assignments if opt and opt.tce)
            total_tce += sum(opt.tce for _, _, opt in market_assignments if opt and opt.tce)
            n_assignments = len(cargill_assignments) + len(market_assignments)
            avg_tce = total_tce / n_assignments if n_assignments > 0 else 0

            # Final unassigned lists
            final_unassigned_vessels = [v.name for v in cargill_vessels if v.name not in assigned_vessels]
            final_unassigned_cargoes = [c.name for c in cargill_cargoes if c.name not in assigned_cargoes]

            results.append(FullPortfolioResult(
                cargill_vessel_assignments=cargill_assignments,
                market_vessel_assignments=market_assignments,
                unassigned_cargill_vessels=final_unassigned_vessels,
                unassigned_cargill_cargoes=final_unassigned_cargoes,
                total_profit=total_profit,
                total_tce=total_tce,
                avg_tce=avg_tce,
                market_vessel_hire_offers=hire_offers,
                market_cargo_freight_bids=freight_bids,
                all_options=all_options,
            ))

        return results

    def _build_fallback_result(
        self,
        cargill_vessels: List[Vessel],
        market_vessels: List[Vessel],
        cargill_cargoes: List[Cargo],
        market_cargoes: List[Cargo],
        valid_options: pd.DataFrame,
        all_options: pd.DataFrame,
        uncoverable_cargoes: List[Cargo],
    ) -> FullPortfolioResult:
        """Build a fallback result when full optimization fails."""

        # Try greedy assignment for whatever we can cover
        assignments = []
        assigned_vessels = set()
        assigned_cargoes = set()

        # Greedy: best profit assignment for each cargo
        for cargo in cargill_cargoes:
            if cargo.name in [c.name for c in uncoverable_cargoes]:
                continue

            cargo_options = valid_options[
                (valid_options['cargo'] == cargo.name) &
                (~valid_options['vessel'].isin(assigned_vessels))
            ].sort_values('net_profit', ascending=False)

            if len(cargo_options) > 0:
                best = cargo_options.iloc[0]
                assign_type = 'cargill_to_cargill' if best['vessel_type'] == 'cargill' else 'market_to_cargill'
                assignments.append((best['vessel'], best['cargo'], best['option'], assign_type))
                assigned_vessels.add(best['vessel'])
                assigned_cargoes.add(best['cargo'])

        cargill_assignments = [(v, c, opt) for v, c, opt, t in assignments if t == 'cargill_to_cargill']
        market_assignments = [(v, c, opt) for v, c, opt, t in assignments if t == 'market_to_cargill']

        total_profit = sum(opt.net_profit for _, _, opt, _ in assignments if opt and opt.net_profit)
        total_tce = sum(opt.tce for _, _, opt, _ in assignments if opt and opt.tce)
        avg_tce = total_tce / len(assignments) if assignments else 0

        return FullPortfolioResult(
            cargill_vessel_assignments=cargill_assignments,
            market_vessel_assignments=market_assignments,
            unassigned_cargill_vessels=[v.name for v in cargill_vessels if v.name not in assigned_vessels],
            unassigned_cargill_cargoes=[c.name for c in cargill_cargoes if c.name not in assigned_cargoes],
            total_profit=total_profit,
            total_tce=total_tce,
            avg_tce=avg_tce,
            market_vessel_hire_offers={},
            market_cargo_freight_bids={},
            all_options=all_options,
        )


def print_full_portfolio_report(result: FullPortfolioResult):
    """Print comprehensive portfolio optimization report."""

    print("\n" + "=" * 80)
    print("FULL PORTFOLIO OPTIMIZATION REPORT")
    print("=" * 80)

    # Cargill vessel assignments
    print("\n" + "-" * 40)
    print("CARGILL VESSEL ASSIGNMENTS")
    print("-" * 40)

    for vessel, cargo, option in result.cargill_vessel_assignments:
        cargo_type = "COMMITTED" if option.cargo_type == "cargill" else "MARKET BID"
        print(f"\n{vessel} -> {cargo} [{cargo_type}]")
        if option.result:
            print(f"  Arrives: {option.result.arrival_date.strftime('%d %b %Y')}")
            print(f"  Duration: {option.result.total_days:.1f} days")
            print(f"  Cargo: {option.result.cargo_quantity:,} MT")
            if option.result.selected_bunker_port:
                print(f"  Bunker Port: {option.result.selected_bunker_port}")
                print(f"  Bunker Fuel: {option.result.bunker_fuel_vlsfo_qty:.0f} MT VLSFO, "
                      f"{option.result.bunker_fuel_mgo_qty:.0f} MT MGO")
                if option.result.bunker_port_savings > 0:
                    print(f"  Bunker Savings: ${option.result.bunker_port_savings:,.0f} "
                          f"(vs load port pricing)")
            print(f"  TCE: ${option.tce:,.0f}/day")
            print(f"  Net Profit: ${option.net_profit:,.0f}")
            if option.cargo_type == "market":
                print(f"  Min Freight Bid: ${option.min_freight_rate:.2f}/MT")

    # Market vessel assignments (for Cargill cargoes)
    if result.market_vessel_assignments:
        print("\n" + "-" * 40)
        print("MARKET VESSELS HIRED FOR CARGILL CARGOES")
        print("-" * 40)

        for vessel, cargo, option in result.market_vessel_assignments:
            print(f"\n{vessel} -> {cargo}")
            if option.result:
                print(f"  Arrives: {option.result.arrival_date.strftime('%d %b %Y')}")
                print(f"  Duration: {option.result.total_days:.1f} days")
                print(f"  Cargo: {option.result.cargo_quantity:,} MT")
                if option.result.selected_bunker_port:
                    print(f"  Bunker Port: {option.result.selected_bunker_port}")
                    print(f"  Bunker Fuel: {option.result.bunker_fuel_vlsfo_qty:.0f} MT VLSFO, "
                          f"{option.result.bunker_fuel_mgo_qty:.0f} MT MGO")
                    if option.result.bunker_port_savings > 0:
                        print(f"  Bunker Savings: ${option.result.bunker_port_savings:,.0f}")
                print(f"  Max Hire Offer: ${option.recommended_hire_rate:,.0f}/day")
                print(f"  Expected TCE: ${option.tce:,.0f}/day")

    # Unassigned warnings
    if result.unassigned_cargill_cargoes:
        print("\n" + "-" * 40)
        print("WARNING: UNASSIGNED CARGILL CARGOES")
        print("-" * 40)
        for cargo in result.unassigned_cargill_cargoes:
            print(f"  [X] {cargo} - NO VESSEL CAN MAKE LAYCAN!")

    if result.unassigned_cargill_vessels:
        print("\n" + "-" * 40)
        print("AVAILABLE CARGILL VESSELS (for market cargoes)")
        print("-" * 40)
        for vessel in result.unassigned_cargill_vessels:
            print(f"  * {vessel}")

    # Summary
    print("\n" + "=" * 40)
    print("PORTFOLIO SUMMARY")
    print("=" * 40)
    print(f"  Total Assignments: {len(result.cargill_vessel_assignments) + len(result.market_vessel_assignments)}")
    print(f"  Cargill Vessels Used: {len(result.cargill_vessel_assignments)}")
    print(f"  Market Vessels Hired: {len(result.market_vessel_assignments)}")
    print(f"  Total Profit: ${result.total_profit:,.0f}")
    print(f"  Average TCE: ${result.avg_tce:,.0f}/day")

    # Market recommendations summary
    print("\n" + "-" * 40)
    print("MARKET RECOMMENDATIONS")
    print("-" * 40)

    if result.market_vessel_hire_offers:
        print("\nMax Hire Rates for Market Vessels (to achieve target TCE):")
        # Get top 5 options
        sorted_hires = sorted(result.market_vessel_hire_offers.items(), key=lambda x: x[1], reverse=True)[:5]
        for vessel, rate in sorted_hires:
            print(f"  * {vessel}: ${rate:,.0f}/day")

    if result.market_cargo_freight_bids:
        print("\nMin Freight Bids for Market Cargoes (to achieve target TCE):")
        sorted_bids = sorted(result.market_cargo_freight_bids.items(), key=lambda x: x[1])[:5]
        for cargo, rate in sorted_bids:
            print(f"  * {cargo[:40]}: ${rate:.2f}/MT")


def get_ml_port_delays(
    cargoes: List[Cargo],
    prediction_date: str = None,
    model_path: str = None,
    data_path: str = None,
) -> Dict[str, Dict]:
    """
    Get ML-predicted port delays for all discharge ports in cargoes.

    Args:
        cargoes: List of Cargo objects
        prediction_date: Date for predictions (default: auto from cargo laycan)
        model_path: Path to saved ML model
        data_path: Path to port activity data

    Returns:
        Dict mapping port names to delay info:
        {
            'Qingdao': {
                'predicted_delay': 4.2,
                'confidence_lower': 3.4,
                'confidence_upper': 5.0,
                'congestion_level': 'medium',
                'model_used': 'ml_model'
            },
            ...
        }
    """
    import os
    from datetime import datetime, timedelta

    # Resolve default paths relative to project root
    if model_path is None or data_path is None:
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        if model_path is None:
            model_path = os.path.join(project_root, 'models', 'port_delay_v1.joblib')
        if data_path is None:
            data_path = os.path.join(project_root, 'data', 'raw', 'Daily_Port_Activity_Data_and_Trade_Estimates.csv')

    if not HAS_ML_MODEL:
        print("Warning: ML model not available, using default delays")
        return {}

    # Initialize predictor
    try:
        predictor = PortCongestionPredictor(
            model_path=model_path,
            data_path=data_path,
        )
    except Exception as e:
        print(f"Warning: Could not initialize ML predictor: {e}")
        return {}

    # Get unique discharge ports
    discharge_ports = list(set(c.discharge_port for c in cargoes))

    # Use prediction date from first cargo laycan if not specified
    if prediction_date is None:
        prediction_date = (datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d')

    results = {}
    for port in discharge_ports:
        try:
            pred = predictor.predict(port, prediction_date)
            results[port] = {
                'predicted_delay': pred.predicted_delay_days,
                'confidence_lower': pred.confidence_lower,
                'confidence_upper': pred.confidence_upper,
                'congestion_level': pred.congestion_level,
                'model_used': pred.model_used,
            }
        except Exception as e:
            print(f"Warning: Could not predict delay for {port}: {e}")
            results[port] = {
                'predicted_delay': 3.0,
                'confidence_lower': 1.5,
                'confidence_upper': 4.5,
                'congestion_level': 'unknown',
                'model_used': 'fallback',
            }

    return results


def optimize_with_ml_delays(
    calculator,
    vessels: List[Vessel],
    cargoes: List[Cargo],
    prediction_date: str = None,
    use_eco_speed: bool = True,
    maximize: str = 'profit',
) -> Tuple[PortfolioResult, PortfolioResult, Dict[str, Dict]]:
    """
    Run portfolio optimization with and without ML-predicted delays.

    Returns comparison of baseline (no delays) vs ML-adjusted optimization.

    Args:
        calculator: FreightCalculator instance
        vessels: List of vessels
        cargoes: List of cargoes
        prediction_date: Date for ML predictions
        use_eco_speed: Whether to use eco speed
        maximize: Optimization target ('profit' or 'tce')

    Returns:
        Tuple of (baseline_result, ml_adjusted_result, port_delays_dict)
    """
    optimizer = PortfolioOptimizer(calculator)

    # Get ML-predicted delays
    ml_delays = get_ml_port_delays(cargoes, prediction_date)

    # Extract just the delay values for the optimizer
    port_delays_dict = {
        port: info['predicted_delay']
        for port, info in ml_delays.items()
    }

    # Baseline optimization (no delays)
    baseline_result = optimizer.optimize_assignments(
        vessels, cargoes,
        use_eco_speed=use_eco_speed,
        maximize=maximize,
        extra_port_delay=0,
    )

    # ML-adjusted optimization
    ml_result = optimizer.optimize_assignments(
        vessels, cargoes,
        use_eco_speed=use_eco_speed,
        maximize=maximize,
        port_delays=port_delays_dict,
    )

    return baseline_result, ml_result, ml_delays


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
    
    def _format_assignments(self, assignments: List[Tuple]) -> List[Dict]:
        """Format assignments as list of dicts with vessel, cargo, profit, tce."""
        result = []
        for vessel_name, cargo_name, voyage_result in assignments:
            result.append({
                'vessel': vessel_name,
                'cargo': cargo_name,
                'profit': round(voyage_result.net_profit, 0) if voyage_result else 0,
                'tce': round(voyage_result.tce, 0) if voyage_result else 0,
            })
        return result

    def _get_china_ports_affected(self, cargoes: List[Cargo]) -> List[str]:
        """Get list of China discharge ports from cargoes."""
        affected = []
        for cargo in cargoes:
            port_upper = cargo.discharge_port.upper()
            for china_port in CHINA_DISCHARGE_PORTS:
                if china_port in port_upper or port_upper in china_port:
                    # Use title case for display
                    affected.append(china_port.title())
                    break
        return list(set(affected))

    def find_tipping_points(
        self,
        vessels: List[Vessel],
        cargoes: List[Cargo],
        max_bunker_increase_pct: float = 100,
        max_port_delay_days: int = 20,
    ) -> Dict:
        """
        Find specific tipping points where recommendations change.

        Args:
            vessels: List of vessels
            cargoes: List of cargoes
            max_bunker_increase_pct: Maximum bunker price increase to search (default 100%)
            max_port_delay_days: Maximum port delay days to search (default 20)

        Returns:
            Dict with 'bunker' and 'port_delay' tipping points (or None if not found),
            plus 'max_bunker_searched' and 'max_delay_searched' for display.
            Each tipping point includes current_best_assignments and next_best_assignments.
        """

        # Baseline
        baseline = self.optimizer.optimize_assignments(vessels, cargoes)
        baseline_assignments = frozenset((a[0], a[1]) for a in baseline.assignments)
        baseline_profit = baseline.total_profit
        baseline_assignments_formatted = self._format_assignments(baseline.assignments)

        tipping_points = {
            'bunker': None,
            'port_delay': None,
            'max_bunker_searched_pct': max_bunker_increase_pct,
            'max_delay_searched_days': max_port_delay_days,
        }

        # Find bunker tipping point (search from 0% to max_bunker_increase_pct)
        max_multiplier = 1.0 + (max_bunker_increase_pct / 100)
        prev_profit = baseline_profit
        prev_portfolio = baseline
        for adj in np.arange(1.0, max_multiplier + 0.01, 0.01):
            portfolio = self.optimizer.optimize_assignments(
                vessels, cargoes, bunker_adjustment=adj
            )
            current_assignments = frozenset((a[0], a[1]) for a in portfolio.assignments)

            if current_assignments != baseline_assignments:
                tipping_points['bunker'] = {
                    'multiplier': round(adj, 2),
                    'change_pct': round((adj - 1) * 100, 1),
                    'old_assignments': list(baseline_assignments),
                    'new_assignments': list(current_assignments),
                    'profit_before': round(prev_profit, 0),
                    'profit_after': round(portfolio.total_profit, 0),
                    'description': f"At +{round((adj - 1) * 100)}% bunker price increase, assignment changes occur.",
                    'current_best_assignments': baseline_assignments_formatted,
                    'next_best_assignments': self._format_assignments(portfolio.assignments),
                }
                break
            prev_profit = portfolio.total_profit
            prev_portfolio = portfolio

        # Find port delay tipping point for CHINA PORTS ONLY
        # Build port_delays dict that only applies delay to China-bound cargoes
        china_cargoes = [c for c in cargoes if any(
            p in c.discharge_port.upper() for p in CHINA_DISCHARGE_PORTS
        )]
        china_ports_affected = self._get_china_ports_affected(china_cargoes)

        prev_profit = baseline_profit
        prev_portfolio = baseline
        for delay in range(1, max_port_delay_days + 1):
            # Create port_delays dict for China ports only
            port_delays = {port: delay for port in CHINA_DISCHARGE_PORTS}

            portfolio = self.optimizer.optimize_assignments(
                vessels, cargoes, port_delays=port_delays
            )
            current_assignments = frozenset((a[0], a[1]) for a in portfolio.assignments)

            if current_assignments != baseline_assignments:
                tipping_points['port_delay'] = {
                    'days': delay,
                    'region': 'china',
                    'ports_affected': china_ports_affected,
                    'old_assignments': list(baseline_assignments),
                    'new_assignments': list(current_assignments),
                    'profit_before': round(prev_profit, 0),
                    'profit_after': round(portfolio.total_profit, 0),
                    'description': f"At +{delay} days port delay in China, assignment changes occur.",
                    'current_best_assignments': baseline_assignments_formatted,
                    'next_best_assignments': self._format_assignments(portfolio.assignments),
                }
                break
            prev_profit = portfolio.total_profit
            prev_portfolio = portfolio

        return tipping_points

    def analyze_port_delay_with_ml(
        self,
        vessels: List[Vessel],
        cargoes: List[Cargo],
        prediction_date: str = None,
    ) -> Dict:
        """
        Analyze port delay impact using ML-predicted delays.

        Uses the PortCongestionPredictor to get per-port delay predictions
        and calculates portfolio impact.

        Args:
            vessels: List of vessels
            cargoes: List of cargoes
            prediction_date: Date for predictions (default: today + 30 days)

        Returns:
            Dict with ML-predicted delays and portfolio comparison
        """
        from datetime import datetime, timedelta

        # Set default prediction date
        if prediction_date is None:
            prediction_date = (datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d')

        result = {
            'prediction_date': prediction_date,
            'port_delays': {},
            'ml_available': False,
            'baseline_profit': 0,
            'ml_adjusted_profit': 0,
            'profit_difference': 0,
        }

        # Try to load ML predictor
        try:
            import os
            from .ml import PortCongestionPredictor

            # Resolve paths relative to project root
            project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            model_path = os.path.join(project_root, 'models', 'port_delay_v1.joblib')
            data_path = os.path.join(project_root, 'data', 'raw', 'Daily_Port_Activity_Data_and_Trade_Estimates.csv')

            predictor = PortCongestionPredictor(
                model_path=model_path,
                data_path=data_path,
            )
            result['ml_available'] = predictor.is_model_available()
        except ImportError:
            predictor = None

        # Get unique discharge ports
        discharge_ports = list(set(c.discharge_port for c in cargoes))

        # Get predictions for each port
        if predictor:
            for port in discharge_ports:
                try:
                    pred_result = predictor.predict(port, prediction_date)
                    result['port_delays'][port] = {
                        'predicted_delay': pred_result.predicted_delay_days,
                        'confidence_lower': pred_result.confidence_lower,
                        'confidence_upper': pred_result.confidence_upper,
                        'congestion_level': pred_result.congestion_level,
                    }
                except Exception as e:
                    result['port_delays'][port] = {
                        'predicted_delay': 3.0,  # Default
                        'error': str(e),
                    }

        # Calculate baseline (no delay)
        baseline = self.optimizer.optimize_assignments(vessels, cargoes)
        result['baseline_profit'] = baseline.total_profit

        # Calculate with ML-predicted delays
        if result['port_delays']:
            port_delays_dict = {
                port: info['predicted_delay']
                for port, info in result['port_delays'].items()
                if 'predicted_delay' in info
            }
            ml_adjusted = self.optimizer.optimize_assignments(
                vessels, cargoes, port_delays=port_delays_dict
            )
            result['ml_adjusted_profit'] = ml_adjusted.total_profit
            result['profit_difference'] = ml_adjusted.total_profit - baseline.total_profit

        return result


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
    print("\n[DATA] SUMMARY")
    print("-" * 40)
    print(f"Total Cargill Vessels: {len(vessels)}")
    print(f"Total Committed Cargoes: {len(cargoes)}")
    print(f"Assignments Made: {len(portfolio.assignments)}")
    print(f"Unassigned Vessels: {len(portfolio.unassigned_vessels)}")
    print(f"Unassigned Cargoes: {len(portfolio.unassigned_cargoes)}")
    
    # Optimal assignments
    print("\n[OK] OPTIMAL ASSIGNMENTS")
    print("-" * 40)
    
    for vessel, cargo, result in portfolio.assignments:
        if result:
            print(f"\n{vessel} -> {cargo}")
            print(f"  [DATE] Arrives: {result.arrival_date.strftime('%d %b %Y')} (Laycan ends: {result.laycan_end.strftime('%d %b %Y')})")
            print(f"  [TIME]  Duration: {result.total_days:.1f} days")
            print(f"  [CARGO] Cargo: {result.cargo_quantity:,} MT")
            if result.selected_bunker_port:
                print(f"  [BUNKER] Port: {result.selected_bunker_port}")
                print(f"  [BUNKER] Fuel: {result.bunker_fuel_vlsfo_qty:.0f} MT VLSFO, "
                      f"{result.bunker_fuel_mgo_qty:.0f} MT MGO")
                if result.bunker_port_savings > 0:
                    print(f"  [BUNKER] Savings: ${result.bunker_port_savings:,.0f}")
            print(f"  [$] Revenue: ${result.net_freight:,.0f}")
            print(f"  [FUEL] Bunker Cost: ${result.total_bunker_cost:,.0f}")
            print(f"  [PORT] Port Costs: ${result.port_costs:,.0f}")
            print(f"  [$$] TCE: ${result.tce:,.0f}/day")
            print(f"  [+] Net Profit: ${result.net_profit:,.0f}")
    
    # Totals
    print("\n" + "-" * 40)
    print(f"[$$] TOTAL PORTFOLIO PROFIT: ${portfolio.total_profit:,.0f}")
    print(f"[DATA] AVERAGE TCE: ${portfolio.avg_tce:,.0f}/day")
    
    # Unassigned items
    if portfolio.unassigned_vessels:
        print("\n[!]  UNASSIGNED VESSELS (Available for market cargoes):")
        for v in portfolio.unassigned_vessels:
            print(f"  * {v}")
    
    if portfolio.unassigned_cargoes:
        print("\n[!]  UNASSIGNED CARGOES (Need market vessels):")
        for c in portfolio.unassigned_cargoes:
            print(f"  * {c}")
    
    # TCE Matrix
    print("\n\n[DATA] TCE COMPARISON MATRIX (USD/day)")
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
    print("\n\n[DATE] LAYCAN FEASIBILITY MATRIX")
    print("=" * 80)
    
    pivot_laycan = all_voyages_df.pivot_table(
        index='vessel',
        columns='cargo',
        values='can_make_laycan',
        aggfunc='first'
    )
    pivot_laycan.columns = [c[:25] + '...' if len(c) > 25 else c for c in pivot_laycan.columns]
    pivot_laycan = pivot_laycan.replace({True: '[OK]', False: '[X]'})
    
    print(pivot_laycan.to_string())


# =============================================================================
# MAIN - RUN COMPLETE ANALYSIS
# =============================================================================

if __name__ == "__main__":
    import os
    import sys

    # Add project root to path for running this file directly
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    sys.path.insert(0, project_root)

    # Data paths relative to project root
    data_dir = os.path.join(project_root, 'data')
    models_dir = os.path.join(project_root, 'models')

    print("=" * 80)
    print("CARGILL DATATHON 2026 - FULL PORTFOLIO OPTIMIZATION")
    print("=" * 80)

    # Initialize
    distance_mgr = PortDistanceManager(os.path.join(data_dir, 'Port_Distances.csv'))
    bunker_prices = create_bunker_prices()
    calculator = FreightCalculator(distance_mgr, bunker_prices)

    # Load ALL data
    cargill_vessels = create_cargill_vessels()
    market_vessels = create_market_vessels()
    cargill_cargoes = create_cargill_cargoes()
    market_cargoes = create_market_cargoes()

    print(f"\n[DATA] DATA LOADED:")
    print(f"  Cargill Vessels: {len(cargill_vessels)}")
    print(f"  Market Vessels: {len(market_vessels)}")
    print(f"  Cargill Cargoes: {len(cargill_cargoes)} (MUST fulfill)")
    print(f"  Market Cargoes: {len(market_cargoes)} (optional)")

    # ==========================================================================
    # FULL PORTFOLIO OPTIMIZATION
    # ==========================================================================

    full_optimizer = FullPortfolioOptimizer(calculator)

    # Target TCE based on FFA 5TC rate for March 2026: $18,454/day
    TARGET_TCE = 18000

    print(f"\n[TARGET] Target TCE: ${TARGET_TCE:,}/day (based on FFA 5TC)")

    # Run full optimization
    full_result = full_optimizer.optimize_full_portfolio(
        cargill_vessels=cargill_vessels,
        market_vessels=market_vessels,
        cargill_cargoes=cargill_cargoes,
        market_cargoes=market_cargoes,
        target_tce=TARGET_TCE,
    )

    # Print comprehensive report
    print_full_portfolio_report(full_result)

    # ==========================================================================
    # DETAILED OPTIONS MATRIX
    # ==========================================================================

    print("\n\n" + "=" * 80)
    print("ALL VOYAGE OPTIONS MATRIX")
    print("=" * 80)

    options_df = full_result.all_options

    # Show Cargill vessels → All cargoes
    print("\n[DATA] CARGILL VESSELS - TCE by Cargo ($/day)")
    print("-" * 60)

    cargill_options = options_df[options_df['vessel_type'] == 'cargill'].copy()
    pivot = cargill_options.pivot_table(
        index='vessel',
        columns='cargo',
        values='tce',
        aggfunc='first'
    )
    pivot.columns = [c[:25] + '...' if len(c) > 25 else c for c in pivot.columns]
    print(pivot.round(0).to_string())

    # Show feasibility
    print("\n\n[DATE] LAYCAN FEASIBILITY (Cargill Vessels)")
    print("-" * 60)

    pivot_laycan = cargill_options.pivot_table(
        index='vessel',
        columns='cargo',
        values='can_make_laycan',
        aggfunc='first'
    )
    pivot_laycan.columns = [c[:25] + '...' if len(c) > 25 else c for c in pivot_laycan.columns]
    pivot_laycan = pivot_laycan.replace({True: '[OK]', False: '[X]'})
    print(pivot_laycan.to_string())

    # Show market vessel options for Cargill cargoes
    print("\n\n[VESSEL] MARKET VESSELS FOR CARGILL CARGOES - Max Hire Rate ($/day)")
    print("-" * 60)

    market_for_cargill = options_df[
        (options_df['vessel_type'] == 'market') &
        (options_df['cargo_type'] == 'cargill') &
        (options_df['can_make_laycan'])
    ].copy()

    if len(market_for_cargill) > 0:
        pivot_market = market_for_cargill.pivot_table(
            index='vessel',
            columns='cargo',
            values='recommended_hire_rate',
            aggfunc='first'
        )
        pivot_market.columns = [c[:30] + '...' if len(c) > 30 else c for c in pivot_market.columns]
        print(pivot_market.round(0).to_string())
    else:
        print("No market vessels can make Cargill cargo laycans!")

    # ==========================================================================
    # LEGACY: Simple optimizer for comparison
    # ==========================================================================

    print("\n\n" + "=" * 80)
    print("COMPARISON: SIMPLE OPTIMIZATION (Cargill only)")
    print("=" * 80)

    optimizer = PortfolioOptimizer(calculator)
    all_voyages = optimizer.calculate_all_voyages(cargill_vessels, cargill_cargoes)

    portfolio = optimizer.optimize_assignments(
        cargill_vessels, cargill_cargoes, maximize='profit'
    )

    print_optimization_report(cargill_vessels, cargill_cargoes, portfolio, all_voyages)
    
    # ==========================================================================
    # SCENARIO ANALYSIS
    # ==========================================================================

    print("\n\n" + "=" * 80)
    print("SCENARIO ANALYSIS")
    print("=" * 80)

    # Initialize scenario analyzer
    analyzer = ScenarioAnalyzer(optimizer)

    # Find tipping points
    tipping_points = analyzer.find_tipping_points(cargill_vessels, cargill_cargoes)
    
    print("\n[SEARCH] TIPPING POINTS")
    print("-" * 40)
    
    max_bunker = tipping_points.get('max_bunker_searched_pct', 100)
    max_delay = tipping_points.get('max_delay_searched_days', 20)

    if tipping_points['bunker']:
        bp = tipping_points['bunker']
        print(f"\n[+] Bunker Price Tipping Point:")
        print(f"   At +{bp['change_pct']:.0f}% bunker price increase, recommendation changes.")
    else:
        print(f"\n[+] Bunker Price: No tipping point found up to +{max_bunker:.0f}% increase")

    if tipping_points['port_delay']:
        delay_tp = tipping_points['port_delay']
        print(f"\n[TIME]  Port Delay Tipping Point:")
        print(f"   At {delay_tp['days']} days additional delay, recommendation changes.")
    else:
        print(f"\n[TIME]  Port Delay: No tipping point found up to {max_delay} days")
    
    # Bunker sensitivity analysis
    print("\n\n[DATA] BUNKER PRICE SENSITIVITY")
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
    print("\n\n[DATA] PORT DELAY SENSITIVITY (China ports)")
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
    print("[!]  CRITICAL ISSUE: UNASSIGNED CARGO")
    print("=" * 80)
    
    print("""
The optimization reveals a key challenge:

* Only 2 Cargill vessels (ANN BELL, OCEAN HORIZON) can make ANY of the laycans
* But there are 3 committed Cargill cargoes

This means you MUST either:
1. Use a MARKET VESSEL to carry one of the committed cargoes
2. Pay demurrage/penalties for missing a cargo commitment

RECOMMENDATION:
For the BHP Iron Ore cargo (Australia-China, laycan March 7-11):
* This is the tightest laycan - only ANN BELL and OCEAN HORIZON can make it
* But assigning them to BHP gives lower profit than other routes
* Consider hiring PACIFIC VANGUARD (market vessel at Caofeidian, ETD Feb 26)
  to carry the BHP cargo
    """)

    # ==========================================================================
    # ML-BASED PORT DELAY ANALYSIS
    # ==========================================================================

    print("\n\n" + "=" * 80)
    print("ML-BASED PORT CONGESTION ANALYSIS")
    print("=" * 80)

    if HAS_ML_MODEL:
        print("\n   Loading ML model and predicting port delays...")

        # Get ML-predicted delays
        ml_delays = get_ml_port_delays(
            cargill_cargoes,
            prediction_date='2026-03-15',
        )

        if ml_delays:
            print("\n   ML-Predicted Port Delays (for March 2026):")
            print("   " + "-" * 50)
            for port, info in ml_delays.items():
                model_tag = "[ML]" if info['model_used'] == 'ml_model' else "[Fallback]"
                print(f"   {port:20s}: {info['predicted_delay']:.1f} days "
                      f"[{info['confidence_lower']:.1f}-{info['confidence_upper']:.1f}] "
                      f"({info['congestion_level']}) {model_tag}")

            # Run comparison
            baseline_result, ml_result, _ = optimize_with_ml_delays(
                calculator, cargill_vessels, cargill_cargoes,
                prediction_date='2026-03-15',
            )

            print("\n   Profit Comparison:")
            print("   " + "-" * 50)
            print(f"   Baseline (no delays):     ${baseline_result.total_profit:>12,.0f}")
            print(f"   ML-adjusted (predicted):  ${ml_result.total_profit:>12,.0f}")
            profit_impact = ml_result.total_profit - baseline_result.total_profit
            print(f"   Impact from port delays:  ${profit_impact:>12,.0f}")

            if baseline_result.assignments != ml_result.assignments:
                print("\n   Note: Assignment strategy changes with ML-predicted delays")
        else:
            print("   [WARN] Could not get ML predictions, using fallback estimates")
    else:
        print("\n   [SKIP] ML model not available")
        print("   To enable: python train_model.py")
