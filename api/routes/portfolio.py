from fastapi import APIRouter, Query
from ..services.calculator_service import calculator_service

router = APIRouter(prefix="/api", tags=["portfolio"])


@router.get("/vessels")
def get_vessels():
    """Get all Cargill vessels."""
    return calculator_service.get_vessels()


@router.get("/cargoes")
def get_cargoes():
    """Get all Cargill cargoes."""
    return calculator_service.get_cargoes()


@router.get("/portfolio/optimize")
def optimize_portfolio(use_ml_delays: bool = Query(False)):
    """Get cached optimal vessel-cargo assignments.

    Args:
        use_ml_delays: If True, use ML-predicted port delays for optimization.
    """
    return calculator_service.get_portfolio(use_ml_delays=use_ml_delays)


@router.get("/portfolio/all-voyages")
def get_all_voyages(use_ml_delays: bool = Query(False)):
    """Get all voyage combinations with economics.

    Args:
        use_ml_delays: If True, use ML-predicted port delays for calculations.
    """
    return calculator_service.get_all_voyages(use_ml_delays=use_ml_delays)
