"""
Wraps existing FreightCalculator + PortfolioOptimizer with caching.
Pre-computes results on startup for sub-50ms API responses.
"""

import sys
import os
import json
import logging
import time
from typing import Dict, List, Optional, Any
from dataclasses import asdict
from datetime import datetime

logger = logging.getLogger("cargill.calculator")

# Add parent dir so we can import src package
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.freight_calculator import (
    FreightCalculator, PortDistanceManager, BunkerPrices,
    Vessel, Cargo, VoyageResult,
    create_cargill_vessels, create_cargill_cargoes,
    create_market_vessels, create_market_cargoes, create_bunker_prices,
    apply_estimated_freight_rate,
)
from src.portfolio_optimizer import (
    PortfolioOptimizer, ScenarioAnalyzer, PortfolioResult,
    FullPortfolioOptimizer, FullPortfolioResult, VoyageOption,
    get_ml_port_delays,
)


def _voyage_to_dict(v: Vessel, c: Cargo, result: VoyageResult, speed_type: str = "eco") -> dict:
    """Convert VoyageResult dataclass to API-friendly dict."""
    # BUG FIX 1: Calculate days_margin from arrival_date and laycan_end
    # VoyageResult doesn't have days_margin field, so we compute it here
    days_margin = (result.laycan_end - result.arrival_date).total_seconds() / 86400

    # BUG FIX 3: Adjust net_profit for market vessels
    # Market vessels have hire_rate=0, so calculate_voyage() doesn't deduct hire costs.
    # We apply FFA market rate ($18,000/day) to show realistic profit.
    FFA_MARKET_RATE = 18000
    if v.is_cargill:
        net_profit = result.net_profit
    else:
        # Market vessel: apply FFA market hire rate
        voyage_costs = result.total_bunker_cost + result.port_costs + result.misc_costs
        net_profit = result.net_freight - voyage_costs - (FFA_MARKET_RATE * result.total_days)

    return {
        "vessel": v.name,
        "cargo": c.name,
        "speed_type": speed_type,
        "can_make_laycan": result.can_make_laycan,
        "arrival_date": result.arrival_date.strftime("%Y-%m-%d") if hasattr(result.arrival_date, "strftime") else str(result.arrival_date),
        "laycan_end": result.laycan_end.strftime("%Y-%m-%d") if hasattr(result.laycan_end, "strftime") else str(result.laycan_end),
        "days_margin": round(days_margin, 1),
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
        "net_profit": round(net_profit, 0),
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
            # BUG FIX 2: Calculate days_margin for full portfolio assignments
            days_margin = (option.result.laycan_end - option.result.arrival_date).total_seconds() / 86400
            voyage_dict.update({
                "arrival_date": option.result.arrival_date.strftime("%Y-%m-%d") if hasattr(option.result.arrival_date, "strftime") else str(option.result.arrival_date),
                "laycan_end": option.result.laycan_end.strftime("%Y-%m-%d") if hasattr(option.result.laycan_end, "strftime") else str(option.result.laycan_end),
                "days_margin": round(days_margin, 1),
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
        self._portfolio_cache: Optional[list] = None
        self._portfolio_ml_cache: Optional[list] = None
        self._all_voyages_cache: Optional[List[dict]] = None
        self._all_voyages_ml_cache: Optional[List[dict]] = None
        self._bunker_sensitivity_cache: Optional[List[dict]] = None
        self._delay_sensitivity_cache: Optional[List[dict]] = None
        self._china_delay_sensitivity_cache: Optional[List[dict]] = None
        self._tipping_points_cache: Optional[dict] = None
        self._ml_delays_cache: Optional[List[dict]] = None
        self._model_info_cache: Optional[dict] = None

    def initialize(self):
        """Initialize all components and pre-compute results."""
        t0 = time.perf_counter()
        logger.info("Initializing...")

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
        self._compute_portfolio_with_ml()
        self._compute_all_voyages()
        self._compute_all_voyages_with_ml()
        self._compute_scenarios()
        self._load_model_info()
        self._compute_ml_delays()

        logger.info("Ready. Total init: %.2fs", time.perf_counter() - t0)

    def _compute_portfolio(self):
        t = time.perf_counter()
        logger.info("Computing optimal portfolio (full optimization with top 3)...")
        results = self.full_optimizer.optimize_full_portfolio(
            cargill_vessels=self.cargill_vessels,
            market_vessels=self.market_vessels,
            cargill_cargoes=self.cargill_cargoes,
            market_cargoes=self.market_cargoes,
            target_tce=18000,
            dual_speed_mode=True,
            top_n=3,
        )
        self._portfolio_cache = [
            _full_portfolio_to_dict(result, self.vessels_map, self.cargoes_map)
            for result in results
        ]
        logger.info("Portfolio computed in %.2fs (%d options)", time.perf_counter() - t, len(results))

    def _compute_portfolio_with_ml(self):
        """Compute portfolio using ML-predicted port delays."""
        t = time.perf_counter()
        logger.info("Computing optimal portfolio with ML port delays...")
        try:
            # Get ML port delays
            ml_delays = get_ml_port_delays(self.cargill_cargoes)

            # Extract delay values for optimizer
            port_delays_dict = {}
            for port, info in ml_delays.items():
                delay = info.get("predicted_delay", info.get("predicted_delay_days", 0))
                port_delays_dict[port] = delay

            logger.info("ML port delays: %s", port_delays_dict)

            # CRITICAL: Actually pass the delays to the optimizer
            results = self.full_optimizer.optimize_full_portfolio(
                cargill_vessels=self.cargill_vessels,
                market_vessels=self.market_vessels,
                cargill_cargoes=self.cargill_cargoes,
                market_cargoes=self.market_cargoes,
                target_tce=18000,
                dual_speed_mode=True,
                top_n=3,
                port_delays=port_delays_dict,  # NEW - Pass the delays here
            )

            self._portfolio_ml_cache = [
                _full_portfolio_to_dict(result, self.vessels_map, self.cargoes_map)
                for result in results
            ]
            logger.info("ML Portfolio computed in %.2fs (%d options)",
                       time.perf_counter() - t, len(results))
        except Exception as e:
            logger.error("ML Portfolio computation error: %s", e)
            self._portfolio_ml_cache = self._portfolio_cache

    def _compute_all_voyages(self):
        t = time.perf_counter()
        logger.info("Computing all voyages...")
        voyages = []
        all_vessels = self.cargill_vessels + self.market_vessels
        all_cargoes = self.cargill_cargoes + self.market_cargoes

        for v in all_vessels:
            for c in all_cargoes:
                # Skip invalid market-vessel -> market-cargo combinations
                if not v.is_cargill and not c.is_cargill:
                    continue
                try:
                    # Apply estimated freight rate for market cargoes with rate=0
                    effective_cargo = apply_estimated_freight_rate(c)
                    result = self.calculator.calculate_voyage(v, effective_cargo, use_eco_speed=True)
                    voyage_dict = _voyage_to_dict(v, c, result, "eco")
                    # Add vessel and cargo type info
                    voyage_dict["vessel_type"] = "cargill" if v.is_cargill else "market"
                    voyage_dict["cargo_type"] = "cargill" if c.is_cargill else "market"
                    voyages.append(voyage_dict)
                except Exception as e:
                    logger.warning("Voyage calc failed: %s -> %s: %s", v.name, c.name, e)
        self._all_voyages_cache = voyages
        logger.info("All voyages computed in %.2fs (%d combinations)", time.perf_counter() - t, len(voyages))

    def _compute_all_voyages_with_ml(self):
        """Compute all voyages with ML port delays."""
        t = time.perf_counter()
        logger.info("Computing all voyages with ML port delays...")
        try:
            # Get ML port delays
            ml_delays = get_ml_port_delays(self.cargill_cargoes)
            port_delays_dict = {
                port: info.get("predicted_delay", info.get("predicted_delay_days", 0))
                for port, info in ml_delays.items()
            }

            voyages = []
            all_vessels = self.cargill_vessels + self.market_vessels
            all_cargoes = self.cargill_cargoes + self.market_cargoes

            for v in all_vessels:
                for c in all_cargoes:
                    # Skip invalid market-vessel -> market-cargo combinations
                    if not v.is_cargill and not c.is_cargill:
                        continue
                    try:
                        # Apply estimated freight rate for market cargoes with rate=0
                        effective_cargo = apply_estimated_freight_rate(c)

                        # Determine port-specific delay
                        delay = 0.0
                        port_name = effective_cargo.discharge_port.upper()
                        for key, value in port_delays_dict.items():
                            if key.upper() in port_name or port_name in key.upper():
                                delay = value
                                break

                        result = self.calculator.calculate_voyage(
                            v, effective_cargo, use_eco_speed=True, extra_port_delay_days=delay
                        )
                        voyage_dict = _voyage_to_dict(v, c, result, "eco")
                        voyage_dict["vessel_type"] = "cargill" if v.is_cargill else "market"
                        voyage_dict["cargo_type"] = "cargill" if c.is_cargill else "market"
                        voyages.append(voyage_dict)
                    except Exception as e:
                        logger.warning("ML Voyage calc failed: %s -> %s: %s", v.name, c.name, e)

            self._all_voyages_ml_cache = voyages
            logger.info("All ML voyages computed in %.2fs (%d combinations)",
                       time.perf_counter() - t, len(voyages))
        except Exception as e:
            logger.error("ML voyages error: %s", e)
            self._all_voyages_ml_cache = self._all_voyages_cache

    def _compute_scenarios(self):
        t = time.perf_counter()
        logger.info("Computing scenarios...")

        # Bunker sensitivity - use FULL portfolio optimizer for accurate ~5.8M profit
        try:
            logger.info("Computing bunker sensitivity with full portfolio optimizer...")
            bunker_results = []
            import numpy as np
            for mult in np.linspace(0.8, 1.5, 15):
                results = self.full_optimizer.optimize_full_portfolio(
                    cargill_vessels=self.cargill_vessels,
                    market_vessels=self.market_vessels,
                    cargill_cargoes=self.cargill_cargoes,
                    market_cargoes=self.market_cargoes,
                    target_tce=18000,
                    dual_speed_mode=True,
                    top_n=1,
                    bunker_adjustment=mult,
                )
                portfolio = results[0]
                # Get assignment summary
                assignments = []
                for v, c, opt in portfolio.cargill_vessel_assignments:
                    assignments.append(f"{v}->{c[:15]}")
                for v, c, opt in portfolio.market_vessel_assignments:
                    assignments.append(f"{v}->{c[:15]}")

                bunker_results.append({
                    'bunker_multiplier': round(mult, 2),
                    'bunker_change_pct': round((mult - 1) * 100, 1),
                    'total_profit': round(portfolio.total_profit, 0),
                    'avg_tce': round(portfolio.avg_tce, 0),
                    'n_assignments': len(portfolio.cargill_vessel_assignments) + len(portfolio.market_vessel_assignments),
                    'assignments': ', '.join(assignments),
                })
            self._bunker_sensitivity_cache = bunker_results
            logger.info("Bunker sensitivity computed: %d points, baseline profit $%.0f",
                       len(bunker_results), bunker_results[4]['total_profit'] if len(bunker_results) > 4 else 0)
        except Exception as e:
            logger.error("Bunker sensitivity error: %s", e)
            self._bunker_sensitivity_cache = []

        # Port delay sensitivity (removed - general port delays not used)
        self._delay_sensitivity_cache = []

        # China port delay sensitivity - use FULL portfolio optimizer
        try:
            logger.info("Computing China delay sensitivity with full portfolio optimizer...")
            china_results = []
            CHINA_PORTS = ['QINGDAO', 'RIZHAO', 'CAOFEIDIAN', 'FANGCHENG',
                          'LIANYUNGANG', 'SHANGHAI', 'TIANJIN', 'DALIAN']

            delay_days = 0.0
            while delay_days <= 15:
                # Build port delays dict with only China ports having delays
                port_delays = {port: delay_days for port in CHINA_PORTS}

                results = self.full_optimizer.optimize_full_portfolio(
                    cargill_vessels=self.cargill_vessels,
                    market_vessels=self.market_vessels,
                    cargill_cargoes=self.cargill_cargoes,
                    market_cargoes=self.market_cargoes,
                    target_tce=18000,
                    dual_speed_mode=True,
                    top_n=1,
                    port_delays=port_delays,
                )
                portfolio = results[0]

                # Get assignment summary
                assignments = []
                for v, c, opt in portfolio.cargill_vessel_assignments:
                    assignments.append(f"{v}->{c[:15]}")
                for v, c, opt in portfolio.market_vessel_assignments:
                    assignments.append(f"{v}->{c[:15]}")

                china_results.append({
                    'port_delay_days': delay_days,
                    'total_profit': round(portfolio.total_profit, 0),
                    'avg_tce': round(portfolio.avg_tce, 0),
                    'n_assignments': len(portfolio.cargill_vessel_assignments) + len(portfolio.market_vessel_assignments),
                    'assignments': ', '.join(assignments),
                    'unassigned_cargoes': ', '.join(portfolio.unassigned_cargill_cargoes),
                })

                delay_days += 0.5

            self._china_delay_sensitivity_cache = china_results
            logger.info("China delay sensitivity computed: %d points, baseline profit $%.0f",
                       len(china_results), china_results[0]['total_profit'] if china_results else 0)
        except Exception as e:
            logger.error("China delay sensitivity error: %s", e)
            self._china_delay_sensitivity_cache = []

        # Tipping points with FULL portfolio
        try:
            tp = self.scenario_analyzer.find_tipping_points(
                self.cargill_vessels,
                self.cargill_cargoes,
                max_bunker_increase_pct=100,
                max_port_delay_days=60,  # Extended range to find true tipping points
                full_optimizer=self.full_optimizer,
                market_vessels=self.market_vessels,
                market_cargoes=self.market_cargoes,
            )
            self._tipping_points_cache = tp
        except Exception as e:
            logger.error("Tipping points error: %s", e)
            self._tipping_points_cache = {}
        logger.info("Scenarios computed in %.2fs", time.perf_counter() - t)

    def _load_model_info(self):
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        path = os.path.join(project_root, "models", "model_info.json")
        try:
            with open(path) as f:
                raw = json.load(f)
            self._model_info_cache = {
                "model_type": raw.get("model_version", "LightGBM"),
                "training_date": raw.get("training_date", ""),
                "metrics": {
                    "mae": raw.get("test_metrics", {}).get("mae", 0),
                    "rmse": raw.get("test_metrics", {}).get("rmse", 0),
                    "within_1_day": raw.get("test_metrics", {}).get("within_1_day_pct", 0) / 100,
                    "within_2_days": raw.get("test_metrics", {}).get("within_2_days_pct", 0) / 100,
                },
                "feature_importance": [
                    {"feature": k, "importance": v}
                    for k, v in raw.get("shap_analysis", {}).get("shap_feature_importance", {}).items()
                ],
            }
        except Exception:
            self._model_info_cache = {}

    def _compute_ml_delays(self):
        logger.info("Computing ML port delays...")
        try:
            delays = get_ml_port_delays(self.cargill_cargoes)
            self._ml_delays_cache = []
            for port, info in delays.items():
                entry = {"port": port, **info}
                # Rename predicted_delay to predicted_delay_days for frontend compatibility
                if "predicted_delay" in entry and "predicted_delay_days" not in entry:
                    entry["predicted_delay_days"] = entry.pop("predicted_delay")
                self._ml_delays_cache.append(entry)
        except Exception as e:
            logger.error("ML delays error: %s", e)
            self._ml_delays_cache = []

    # ─── Public API ──────────────────────────────────────────

    def get_vessels(self, include_market: bool = False) -> List[dict]:
        vessels = self.cargill_vessels + self.market_vessels if include_market else self.cargill_vessels
        return [
            {
                "name": v.name, "dwt": v.dwt, "hire_rate": v.hire_rate,
                "speed_laden": v.speed_laden, "speed_laden_eco": v.speed_laden_eco,
                "speed_ballast": v.speed_ballast, "speed_ballast_eco": v.speed_ballast_eco,
                "current_port": v.current_port, "etd": v.etd,
                "bunker_rob_vlsfo": v.bunker_rob_vlsfo, "bunker_rob_mgo": v.bunker_rob_mgo,
                "fuel_laden_vlsfo": v.fuel_laden_vlsfo, "fuel_laden_mgo": v.fuel_laden_mgo,
                "fuel_ballast_vlsfo": v.fuel_ballast_vlsfo, "fuel_ballast_mgo": v.fuel_ballast_mgo,
                "fuel_laden_eco_vlsfo": v.fuel_laden_eco_vlsfo, "fuel_laden_eco_mgo": v.fuel_laden_eco_mgo,
                "fuel_ballast_eco_vlsfo": v.fuel_ballast_eco_vlsfo, "fuel_ballast_eco_mgo": v.fuel_ballast_eco_mgo,
                "port_idle_mgo": v.port_idle_mgo, "port_working_mgo": v.port_working_mgo,
                "is_cargill": v.is_cargill,
            }
            for v in vessels
        ]

    def get_cargoes(self, include_market: bool = False) -> List[dict]:
        cargoes = self.cargill_cargoes + self.market_cargoes if include_market else self.cargill_cargoes
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
            for c in cargoes
        ]

    def get_portfolio(self, use_ml_delays: bool = False) -> dict:
        if use_ml_delays:
            portfolios = self._portfolio_ml_cache or self._portfolio_cache or []
        else:
            portfolios = self._portfolio_cache or []
        return {
            "portfolios": portfolios,
            "best": portfolios[0] if portfolios else None,
        }

    def get_all_voyages(self, use_ml_delays: bool = False) -> List[dict]:
        if use_ml_delays:
            return self._all_voyages_ml_cache or self._all_voyages_cache or []
        else:
            return self._all_voyages_cache or []

    def calculate_voyage(self, vessel_name: str, cargo_name: str,
                         use_eco: bool = True, delay: float = 0,
                         bunker_adj: float = 1.0) -> dict:
        v = self.vessels_map.get(vessel_name)
        c = self.cargoes_map.get(cargo_name)
        if not v or not c:
            return {"error": f"Vessel or cargo not found: {vessel_name}, {cargo_name}"}
        # Apply estimated freight rate for market cargoes with rate=0
        effective_cargo = apply_estimated_freight_rate(c)
        result = self.calculator.calculate_voyage(
            v, effective_cargo, use_eco_speed=use_eco,
            extra_port_delay_days=delay,
            bunker_price_adjustment=bunker_adj,
        )
        return _voyage_to_dict(v, c, result, "eco" if use_eco else "warranted")

    def get_bunker_sensitivity(self) -> List[dict]:
        return self._bunker_sensitivity_cache or []

    def get_delay_sensitivity(self) -> List[dict]:
        return self._delay_sensitivity_cache or []

    def get_china_delay_sensitivity(self) -> List[dict]:
        return self._china_delay_sensitivity_cache or []

    def get_tipping_points(self) -> dict:
        return self._tipping_points_cache or {}

    def get_ml_delays(self) -> List[dict]:
        return self._ml_delays_cache or []

    def get_model_info(self) -> dict:
        return self._model_info_cache or {}


# Singleton
calculator_service = CalculatorService()
