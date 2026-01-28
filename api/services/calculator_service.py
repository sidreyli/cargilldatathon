"""
Wraps existing FreightCalculator + PortfolioOptimizer with caching.
Pre-computes results on startup for sub-50ms API responses.
"""

import sys
import os
import json
from typing import Dict, List, Optional, Any
from dataclasses import asdict
from datetime import datetime

# Add parent dir so we can import src package
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.freight_calculator import (
    FreightCalculator, PortDistanceManager, BunkerPrices,
    Vessel, Cargo, VoyageResult,
    create_cargill_vessels, create_cargill_cargoes,
    create_market_vessels, create_market_cargoes, create_bunker_prices,
)
from src.portfolio_optimizer import (
    PortfolioOptimizer, ScenarioAnalyzer, PortfolioResult,
    FullPortfolioOptimizer, FullPortfolioResult, VoyageOption,
    get_ml_port_delays,
)


def _voyage_to_dict(v: Vessel, c: Cargo, result: VoyageResult, speed_type: str = "eco") -> dict:
    """Convert VoyageResult dataclass to API-friendly dict."""
    return {
        "vessel": v.name,
        "cargo": c.name,
        "speed_type": speed_type,
        "can_make_laycan": result.can_make_laycan,
        "arrival_date": result.arrival_date.strftime("%Y-%m-%d") if hasattr(result.arrival_date, "strftime") else str(result.arrival_date),
        "laycan_end": result.laycan_end.strftime("%Y-%m-%d") if hasattr(result.laycan_end, "strftime") else str(result.laycan_end),
        "days_margin": round(result.days_margin if hasattr(result, "days_margin") else 0, 1),
        "total_days": round(result.total_days, 1),
        "ballast_days": round(result.ballast_days, 1),
        "laden_days": round(result.laden_days, 1),
        "load_days": round(result.load_days, 1),
        "discharge_days": round(result.discharge_days, 1),
        "waiting_days": round(result.waiting_days, 1),
        "cargo_qty": int(result.cargo_quantity),
        "gross_freight": round(result.gross_freight, 0),
        "net_freight": round(result.net_freight, 0),
        "commission_cost": round(result.commission_cost, 0),
        "total_bunker_cost": round(result.total_bunker_cost, 0),
        "bunker_cost_vlsfo": round(result.bunker_cost_vlsfo, 0),
        "bunker_cost_mgo": round(result.bunker_cost_mgo, 0),
        "hire_cost": round(result.hire_cost, 0),
        "port_costs": round(result.port_costs, 0),
        "misc_costs": round(result.misc_costs, 0),
        "net_profit": round(result.net_profit, 0),
        "tce": round(result.tce, 0),
        "vlsfo_consumed": round(result.vlsfo_consumed, 1),
        "mgo_consumed": round(result.mgo_consumed, 1),
        "bunker_port": result.selected_bunker_port,
        "bunker_savings": round(result.bunker_port_savings, 0),
    }


def _portfolio_to_dict(portfolio: PortfolioResult, vessels_map: dict, cargoes_map: dict) -> dict:
    """Convert PortfolioResult to API-friendly dict."""
    assignments = []
    for vessel_name, cargo_name, result in portfolio.assignments:
        v = vessels_map[vessel_name]
        c = cargoes_map[cargo_name]
        assignments.append({
            "vessel": vessel_name,
            "cargo": cargo_name,
            "voyage": _voyage_to_dict(v, c, result),
        })
    return {
        "assignments": assignments,
        "unassigned_vessels": portfolio.unassigned_vessels,
        "unassigned_cargoes": portfolio.unassigned_cargoes,
        "total_profit": round(portfolio.total_profit, 0),
        "total_tce": round(portfolio.total_tce, 0),
        "avg_tce": round(portfolio.avg_tce, 0),
    }


def _full_portfolio_to_dict(result: FullPortfolioResult, vessels_map: dict, cargoes_map: dict) -> dict:
    """Convert FullPortfolioResult to API-friendly dict."""
    assignments = []
    
    # Cargill vessel assignments
    for vessel_name, cargo_name, option in result.cargill_vessel_assignments:
        v = option.vessel
        c = option.cargo
        voyage_dict = {
            "vessel": vessel_name,
            "cargo": cargo_name,
            "vessel_type": option.vessel_type,
            "cargo_type": option.cargo_type,
            "speed_type": "eco",  # Default to eco
            "can_make_laycan": option.can_make_laycan,
            "total_days": round(option.voyage_days, 1),
            "net_profit": round(option.net_profit, 0),
            "tce": round(option.tce, 0),
        }
        if option.result:
            voyage_dict.update({
                "arrival_date": option.result.arrival_date.strftime("%Y-%m-%d") if hasattr(option.result.arrival_date, "strftime") else str(option.result.arrival_date),
                "laycan_end": option.result.laycan_end.strftime("%Y-%m-%d") if hasattr(option.result.laycan_end, "strftime") else str(option.result.laycan_end),
                "ballast_days": round(option.result.ballast_days, 1),
                "laden_days": round(option.result.laden_days, 1),
                "load_days": round(option.result.load_days, 1),
                "discharge_days": round(option.result.discharge_days, 1),
                "cargo_qty": int(option.result.cargo_quantity),
                "gross_freight": round(option.result.gross_freight, 0),
                "net_freight": round(option.result.net_freight, 0),
                "total_bunker_cost": round(option.result.total_bunker_cost, 0),
                "hire_cost": round(option.result.hire_cost, 0),
                "port_costs": round(option.result.port_costs, 0),
                "bunker_port": option.result.selected_bunker_port,
            })
        assignments.append({
            "vessel": vessel_name,
            "cargo": cargo_name,
            "voyage": voyage_dict,
        })
    
    # Market vessel assignments (hired to cover Cargill cargoes)
    market_hires = []
    for vessel_name, cargo_name, option in result.market_vessel_assignments:
        hire_info = {
            "vessel": vessel_name,
            "cargo": cargo_name,
            "duration_days": round(option.voyage_days, 1),
            "recommended_hire_rate": round(option.recommended_hire_rate, 0),
            "tce": round(option.tce, 0),
            "net_profit": round(option.net_profit, 0),
        }
        # Include voyage details if available
        if option.result:
            hire_info.update({
                "ballast_days": round(option.result.ballast_days, 1),
                "laden_days": round(option.result.laden_days, 1),
                "load_days": round(option.result.load_days, 1),
                "discharge_days": round(option.result.discharge_days, 1),
                "cargo_qty": int(option.result.cargo_quantity),
                "gross_freight": round(option.result.gross_freight, 0),
                "net_freight": round(option.result.net_freight, 0),
                "total_bunker_cost": round(option.result.total_bunker_cost, 0),
                "hire_cost": round(option.result.hire_cost, 0),
                "port_costs": round(option.result.port_costs, 0),
            })
        market_hires.append(hire_info)
    
    return {
        "assignments": assignments,
        "market_vessel_hires": market_hires,
        "unassigned_vessels": result.unassigned_cargill_vessels,
        "unassigned_cargoes": result.unassigned_cargill_cargoes,
        "total_profit": round(result.total_profit, 0),
        "total_tce": round(result.total_tce, 0),
        "avg_tce": round(result.avg_tce, 0),
    }


class CalculatorService:
    """Singleton service that pre-computes and caches optimization results."""

    def __init__(self):
        self.calculator: Optional[FreightCalculator] = None
        self.optimizer: Optional[PortfolioOptimizer] = None
        self.full_optimizer: Optional[FullPortfolioOptimizer] = None
        self.scenario_analyzer: Optional[ScenarioAnalyzer] = None
        self.cargill_vessels: List[Vessel] = []
        self.cargill_cargoes: List[Cargo] = []
        self.market_vessels: List[Vessel] = []
        self.market_cargoes: List[Cargo] = []
        self.bunker_prices: Optional[BunkerPrices] = None
        self.vessels_map: Dict[str, Vessel] = {}
        self.cargoes_map: Dict[str, Cargo] = {}

        # Cached results
        self._portfolio_cache: Optional[dict] = None
        self._all_voyages_cache: Optional[List[dict]] = None
        self._bunker_sensitivity_cache: Optional[List[dict]] = None
        self._delay_sensitivity_cache: Optional[List[dict]] = None
        self._tipping_points_cache: Optional[dict] = None
        self._ml_delays_cache: Optional[List[dict]] = None
        self._model_info_cache: Optional[dict] = None

    def initialize(self):
        """Initialize all components and pre-compute results."""
        print("[CalculatorService] Initializing...")

        # Create data
        self.cargill_vessels = create_cargill_vessels()
        self.cargill_cargoes = create_cargill_cargoes()
        self.market_vessels = create_market_vessels()
        self.market_cargoes = create_market_cargoes()
        self.bunker_prices = create_bunker_prices()

        # Maps for all vessels and cargoes
        self.vessels_map = {v.name: v for v in self.cargill_vessels + self.market_vessels}
        self.cargoes_map = {c.name: c for c in self.cargill_cargoes + self.market_cargoes}

        # Build calculator
        # __file__ is .../cargillDatathon/api/services/calculator_service.py
        # We need to go up 3 levels to get to cargillDatathon
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        # Try multiple possible paths for the distance CSV
        csv_candidates = [
            os.path.join(project_root, "data", "Port_Distances.csv"),
            os.path.join(project_root, "data", "raw", "Port_Distances_v2.csv"),
            os.path.join(project_root, "data", "raw", "Port_Distances.csv"),
        ]
        csv_path = None
        for candidate in csv_candidates:
            if os.path.exists(candidate):
                csv_path = candidate
                break
        distance_manager = PortDistanceManager(csv_path=csv_path)
        self.calculator = FreightCalculator(distance_manager, self.bunker_prices)
        self.optimizer = PortfolioOptimizer(self.calculator)
        self.full_optimizer = FullPortfolioOptimizer(self.calculator)
        self.scenario_analyzer = ScenarioAnalyzer(self.optimizer)

        # Pre-compute
        self._compute_portfolio()
        self._compute_all_voyages()
        self._compute_scenarios()
        self._load_model_info()
        self._compute_ml_delays()

        print("[CalculatorService] Ready.")

    def _compute_portfolio(self):
        print("[CalculatorService] Computing optimal portfolio (full optimization)...")
        full_result = self.full_optimizer.optimize_full_portfolio(
            cargill_vessels=self.cargill_vessels,
            market_vessels=self.market_vessels,
            cargill_cargoes=self.cargill_cargoes,
            market_cargoes=self.market_cargoes,
            target_tce=18000,
            dual_speed_mode=True,
        )
        self._portfolio_cache = _full_portfolio_to_dict(full_result, self.vessels_map, self.cargoes_map)

    def _compute_all_voyages(self):
        print("[CalculatorService] Computing all voyages...")
        voyages = []
        all_vessels = self.cargill_vessels + self.market_vessels
        all_cargoes = self.cargill_cargoes + self.market_cargoes
        
        for v in all_vessels:
            for c in all_cargoes:
                try:
                    result = self.calculator.calculate_voyage(v, c, use_eco_speed=True)
                    voyage_dict = _voyage_to_dict(v, c, result, "eco")
                    # Add vessel and cargo type info
                    voyage_dict["vessel_type"] = "cargill" if v.is_cargill else "market"
                    voyage_dict["cargo_type"] = "cargill" if c.is_cargill else "market"
                    voyages.append(voyage_dict)
                except Exception as e:
                    print(f"  Warning: {v.name} -> {c.name}: {e}")
        self._all_voyages_cache = voyages

    def _compute_scenarios(self):
        print("[CalculatorService] Computing scenarios...")
        # Bunker sensitivity
        try:
            df = self.scenario_analyzer.analyze_bunker_sensitivity(
                self.cargill_vessels, self.cargill_cargoes,
                price_range=(0.8, 1.5), steps=15,
            )
            self._bunker_sensitivity_cache = df.to_dict(orient="records")
        except Exception as e:
            print(f"  Bunker sensitivity error: {e}")
            self._bunker_sensitivity_cache = []

        # Port delay sensitivity
        try:
            df = self.scenario_analyzer.analyze_port_delay_sensitivity(
                self.cargill_vessels, self.cargill_cargoes,
                max_delay_days=15,
            )
            self._delay_sensitivity_cache = df.to_dict(orient="records")
        except Exception as e:
            print(f"  Delay sensitivity error: {e}")
            self._delay_sensitivity_cache = []

        # Tipping points
        try:
            tp = self.scenario_analyzer.find_tipping_points(
                self.cargill_vessels, self.cargill_cargoes,
            )
            self._tipping_points_cache = tp
        except Exception as e:
            print(f"  Tipping points error: {e}")
            self._tipping_points_cache = {}

    def _load_model_info(self):
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        path = os.path.join(project_root, "models", "model_info.json")
        try:
            with open(path) as f:
                self._model_info_cache = json.load(f)
        except Exception:
            self._model_info_cache = {}

    def _compute_ml_delays(self):
        print("[CalculatorService] Computing ML port delays...")
        try:
            delays = get_ml_port_delays(self.cargill_cargoes)
            self._ml_delays_cache = [
                {"port": port, **info} for port, info in delays.items()
            ]
        except Exception as e:
            print(f"  ML delays error: {e}")
            self._ml_delays_cache = []

    # ─── Public API ──────────────────────────────────────────

    def get_vessels(self) -> List[dict]:
        return [
            {
                "name": v.name, "dwt": v.dwt, "hire_rate": v.hire_rate,
                "speed_laden": v.speed_laden, "speed_laden_eco": v.speed_laden_eco,
                "speed_ballast": v.speed_ballast, "speed_ballast_eco": v.speed_ballast_eco,
                "current_port": v.current_port, "etd": v.etd,
                "bunker_rob_vlsfo": v.bunker_rob_vlsfo, "bunker_rob_mgo": v.bunker_rob_mgo,
                "is_cargill": v.is_cargill,
            }
            for v in self.cargill_vessels
        ]

    def get_cargoes(self) -> List[dict]:
        return [
            {
                "name": c.name, "customer": c.customer, "commodity": c.commodity,
                "quantity": c.quantity, "quantity_tolerance": c.quantity_tolerance,
                "laycan_start": c.laycan_start, "laycan_end": c.laycan_end,
                "freight_rate": c.freight_rate,
                "load_port": c.load_port, "discharge_port": c.discharge_port,
                "load_rate": c.load_rate, "discharge_rate": c.discharge_rate,
                "port_cost_load": c.port_cost_load, "port_cost_discharge": c.port_cost_discharge,
                "commission": c.commission, "is_cargill": c.is_cargill,
            }
            for c in self.cargill_cargoes
        ]

    def get_portfolio(self) -> dict:
        return self._portfolio_cache or {}

    def get_all_voyages(self) -> List[dict]:
        return self._all_voyages_cache or []

    def calculate_voyage(self, vessel_name: str, cargo_name: str,
                         use_eco: bool = True, delay: float = 0,
                         bunker_adj: float = 1.0) -> dict:
        v = self.vessels_map.get(vessel_name)
        c = self.cargoes_map.get(cargo_name)
        if not v or not c:
            return {"error": f"Vessel or cargo not found: {vessel_name}, {cargo_name}"}
        result = self.calculator.calculate_voyage(
            v, c, use_eco_speed=use_eco,
            extra_port_delay_days=delay,
            bunker_price_adjustment=bunker_adj,
        )
        return _voyage_to_dict(v, c, result, "eco" if use_eco else "warranted")

    def get_bunker_sensitivity(self) -> List[dict]:
        return self._bunker_sensitivity_cache or []

    def get_delay_sensitivity(self) -> List[dict]:
        return self._delay_sensitivity_cache or []

    def get_tipping_points(self) -> dict:
        return self._tipping_points_cache or {}

    def get_ml_delays(self) -> List[dict]:
        return self._ml_delays_cache or []

    def get_model_info(self) -> dict:
        return self._model_info_cache or {}


# Singleton
calculator_service = CalculatorService()
