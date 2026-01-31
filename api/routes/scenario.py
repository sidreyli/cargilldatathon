from fastapi import APIRouter
from ..services.calculator_service import calculator_service

router = APIRouter(prefix="/api/scenario", tags=["scenario"])


@router.get("/bunker")
def get_bunker_sensitivity():
    """Get bunker price sensitivity analysis."""
    return calculator_service.get_bunker_sensitivity()


@router.get("/port-delay")
def get_delay_sensitivity():
    """Get port delay sensitivity analysis."""
    return calculator_service.get_delay_sensitivity()


@router.get("/china-port-delay")
def get_china_delay_sensitivity():
    """Get China port delay sensitivity analysis."""
    return calculator_service.get_china_delay_sensitivity()


@router.get("/tipping-points")
def get_tipping_points():
    """Get tipping point thresholds where assignments change."""
    return calculator_service.get_tipping_points()
