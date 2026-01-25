"""
Port Congestion Predictor
=========================
Main predictor class for port delay estimation using ML model.
Integrates with FreightCalculator for voyage planning.
"""

import os
import pandas as pd
import numpy as np
from dataclasses import dataclass
from datetime import datetime, date, timedelta
from typing import Dict, Optional, Tuple, List, Union
from pathlib import Path

try:
    import joblib
    HAS_JOBLIB = True
except ImportError:
    HAS_JOBLIB = False

try:
    import lightgbm as lgb
    HAS_LIGHTGBM = True
except ImportError:
    HAS_LIGHTGBM = False

from .feature_engineering import FeatureEngineer
from .holiday_calendar import HolidayCalendar


@dataclass
class PredictionResult:
    """Result of a port delay prediction."""
    port: str
    date: datetime
    predicted_delay_days: float
    confidence_lower: float  # 10th percentile
    confidence_upper: float  # 90th percentile
    congestion_level: str    # "low", "medium", "high"
    model_used: str          # "ml_model" or "fallback"


class PortCongestionPredictor:
    """
    ML-based port congestion predictor for bulk carrier discharge ports.

    Target ports:
    - China: Qingdao, Rizhao, Caofeidian, Fangcheng
    - India: Mundra, Vizag

    Usage:
        predictor = PortCongestionPredictor('saved_models/port_delay_v1.joblib')
        result = predictor.predict("Qingdao", "2026-03-15")
        delay = predictor.get_delay_for_voyage("Qingdao", "2026-03-15")
    """

    # Port name to ID mapping
    PORT_MAPPING: Dict[str, str] = {
        'qingdao': 'port1069',
        'rizhao': 'port1105',
        'fangcheng': 'port339',
        'caofeidian': 'port1266',
        'mundra': 'port777',
        'vizag': 'port1367',
        'visakhapatnam': 'port1367',
        # Add common variations
        'lianyungang': 'port1069',  # Nearby Qingdao, use same model
        'tianjin': 'port1266',      # Use Caofeidian model
    }

    # Port ID to country mapping
    PORT_COUNTRIES: Dict[str, str] = {
        'port1069': 'CHN',
        'port1105': 'CHN',
        'port339': 'CHN',
        'port1266': 'CHN',
        'port777': 'IND',
        'port1367': 'IND',
    }

    # Default delays when model unavailable
    DEFAULT_DELAYS: Dict[str, float] = {
        'qingdao': 4.0,
        'rizhao': 3.5,
        'caofeidian': 4.5,
        'fangcheng': 3.0,
        'mundra': 2.5,
        'vizag': 2.0,
        'lianyungang': 4.0,
        'tianjin': 4.5,
    }

    def __init__(
        self,
        model_path: Optional[str] = None,
        data_path: Optional[str] = None,
        port_database_path: Optional[str] = None,
    ):
        """
        Initialize the predictor.

        Args:
            model_path: Path to saved LightGBM model (.joblib)
            data_path: Path to Daily_Port_Activity_Data_and_Trade_Estimates.csv
            port_database_path: Path to PortWatch_ports_database.csv
        """
        self.model = None
        self.model_path = model_path
        self.data_path = data_path
        self._data_cache: Optional[pd.DataFrame] = None
        self._feature_engineer = FeatureEngineer(port_database_path)

        # Try to load model
        if model_path and os.path.exists(model_path):
            self._load_model(model_path)

        # Load data for feature creation
        if data_path and os.path.exists(data_path):
            self._load_data(data_path)

    def _load_model(self, path: str) -> bool:
        """Load trained LightGBM model from file."""
        if not HAS_JOBLIB:
            print("Warning: joblib not installed, cannot load model")
            return False

        try:
            self.model = joblib.load(path)
            return True
        except Exception as e:
            print(f"Warning: Could not load model from {path}: {e}")
            return False

    def _load_data(self, path: str) -> bool:
        """Load port activity data for feature creation."""
        try:
            df = pd.read_csv(path)
            df['date'] = pd.to_datetime(df['date'])
            self._data_cache = df
            return True
        except Exception as e:
            print(f"Warning: Could not load data from {path}: {e}")
            return False

    def is_model_available(self) -> bool:
        """Check if ML model is loaded and ready."""
        return self.model is not None

    def _normalize_port_name(self, port: str) -> str:
        """Normalize port name to lowercase key."""
        return port.lower().strip().replace(' ', '')

    def _get_port_id(self, port: str) -> Optional[str]:
        """Get port ID from port name."""
        normalized = self._normalize_port_name(port)
        return self.PORT_MAPPING.get(normalized)

    def _parse_date(self, date_input: Union[str, date, datetime]) -> date:
        """Parse date from various formats."""
        if isinstance(date_input, datetime):
            return date_input.date()
        elif isinstance(date_input, date):
            return date_input
        elif isinstance(date_input, str):
            # Try common formats
            for fmt in ['%Y-%m-%d', '%d %b %Y', '%d-%m-%Y', '%m/%d/%Y']:
                try:
                    return datetime.strptime(date_input, fmt).date()
                except ValueError:
                    continue
            raise ValueError(f"Cannot parse date: {date_input}")
        else:
            raise TypeError(f"Invalid date type: {type(date_input)}")

    def _get_seasonal_adjustment(self, check_date: date, port_id: str) -> float:
        """
        Calculate seasonal adjustment to base delay.

        Returns additional delay days based on:
        - CNY pre-rush (increases congestion)
        - Golden Week
        - Monsoon (India ports)
        """
        country = self.PORT_COUNTRIES.get(port_id, 'CHN')
        adjustment = 0.0

        if country == 'CHN':
            # CNY effect - congestion builds up before CNY
            cny_proximity = HolidayCalendar.cny_proximity_days(check_date)
            if 0 < cny_proximity <= 14:
                # Pre-CNY rush
                adjustment += 2.0 * (1 - cny_proximity / 14)
            elif HolidayCalendar.is_cny(check_date):
                # During CNY - lower congestion as port slows
                adjustment -= 1.0

            # Golden Week
            if HolidayCalendar.is_golden_week(check_date):
                adjustment += 1.5

        elif country == 'IND':
            # Monsoon effect on west coast ports
            if port_id == 'port777' and HolidayCalendar.is_monsoon_india(check_date):
                # Mundra - west coast, affected by monsoon
                adjustment += 1.5

            # Diwali
            if HolidayCalendar.is_diwali(check_date):
                adjustment += 1.0

        return adjustment

    def predict(
        self,
        port: str,
        date_input: Union[str, date, datetime],
    ) -> PredictionResult:
        """
        Predict delay in days for a port on a given date.

        Args:
            port: Port name (e.g., "Qingdao", "Mundra")
            date_input: Prediction date

        Returns:
            PredictionResult with predicted delay and confidence intervals
        """
        check_date = self._parse_date(date_input)
        normalized_port = self._normalize_port_name(port)
        port_id = self._get_port_id(port)

        # Use ML model if available
        if self.is_model_available() and port_id and self._data_cache is not None:
            try:
                prediction = self._predict_with_model(port_id, check_date)
                return prediction
            except Exception as e:
                print(f"Warning: ML prediction failed, using fallback: {e}")

        # Fallback to rule-based prediction
        return self._predict_fallback(normalized_port, port_id, check_date)

    def _predict_with_model(self, port_id: str, check_date: date) -> PredictionResult:
        """Make prediction using trained ML model."""
        # Get recent data for the port
        port_data = self._data_cache[self._data_cache['portid'] == port_id].copy()
        port_data = port_data.sort_values('date')

        # Get most recent 60 days of data
        latest_date = port_data['date'].max()
        recent_data = port_data[port_data['date'] >= latest_date - timedelta(days=60)]

        if len(recent_data) < 30:
            raise ValueError("Insufficient recent data for prediction")

        # Engineer features for prediction
        features_df = self._feature_engineer.engineer_features(
            recent_data, port_id, include_target=False
        )

        # Get the latest row for prediction
        latest_features = features_df.iloc[-1:]

        # Get feature columns
        feature_cols = self._feature_engineer.get_feature_columns()
        available_cols = [c for c in feature_cols if c in latest_features.columns]
        X = latest_features[available_cols].values

        # Make prediction
        prediction = self.model.predict(X)[0]

        # Apply seasonal adjustment
        seasonal_adj = self._get_seasonal_adjustment(check_date, port_id)
        prediction += seasonal_adj

        # Clip to valid range
        prediction = np.clip(prediction, 0, 15)

        # Calculate confidence intervals (approximate)
        # Use 20% uncertainty for confidence bounds
        uncertainty = prediction * 0.2 + 0.5
        lower = max(0, prediction - uncertainty)
        upper = min(15, prediction + uncertainty)

        # Determine congestion level
        if prediction <= 2:
            level = "low"
        elif prediction <= 5:
            level = "medium"
        else:
            level = "high"

        port_name = FeatureEngineer.TARGET_PORTS.get(port_id, {}).get('name', port_id)

        return PredictionResult(
            port=port_name,
            date=datetime.combine(check_date, datetime.min.time()),
            predicted_delay_days=round(prediction, 1),
            confidence_lower=round(lower, 1),
            confidence_upper=round(upper, 1),
            congestion_level=level,
            model_used="ml_model",
        )

    def _predict_fallback(
        self,
        normalized_port: str,
        port_id: Optional[str],
        check_date: date,
    ) -> PredictionResult:
        """Make prediction using rule-based fallback."""
        # Get base delay
        base_delay = self.DEFAULT_DELAYS.get(normalized_port, 3.5)

        # Apply seasonal adjustment
        if port_id:
            seasonal_adj = self._get_seasonal_adjustment(check_date, port_id)
        else:
            seasonal_adj = 0.0

        prediction = base_delay + seasonal_adj
        prediction = np.clip(prediction, 0, 15)

        # Wider confidence intervals for fallback
        lower = max(0, prediction - 1.5)
        upper = min(15, prediction + 2.0)

        # Determine congestion level
        if prediction <= 2:
            level = "low"
        elif prediction <= 5:
            level = "medium"
        else:
            level = "high"

        return PredictionResult(
            port=normalized_port.title(),
            date=datetime.combine(check_date, datetime.min.time()),
            predicted_delay_days=round(prediction, 1),
            confidence_lower=round(lower, 1),
            confidence_upper=round(upper, 1),
            congestion_level=level,
            model_used="fallback",
        )

    def get_delay_for_voyage(
        self,
        discharge_port: str,
        eta_date: Union[str, date, datetime],
        cargo_quantity: int = 170000,
    ) -> float:
        """
        Get predicted delay for voyage planning.

        Direct integration point with FreightCalculator.

        Args:
            discharge_port: Discharge port name
            eta_date: Estimated arrival date at discharge port
            cargo_quantity: Cargo quantity in MT (for future volume-based adjustments)

        Returns:
            Predicted delay in days (float)
        """
        result = self.predict(discharge_port, eta_date)
        return result.predicted_delay_days

    def get_delays_for_ports(
        self,
        ports: List[str],
        date_input: Union[str, date, datetime],
    ) -> Dict[str, float]:
        """
        Get predicted delays for multiple ports.

        Args:
            ports: List of port names
            date_input: Prediction date

        Returns:
            Dict mapping port names to predicted delays
        """
        return {
            port: self.predict(port, date_input).predicted_delay_days
            for port in ports
        }

    def get_supported_ports(self) -> List[str]:
        """Get list of supported port names."""
        return list(self.PORT_MAPPING.keys())


# Convenience function for quick predictions
def predict_port_delay(
    port: str,
    date_input: Union[str, date, datetime],
    model_path: Optional[str] = None,
) -> float:
    """
    Quick prediction function without managing predictor instance.

    Args:
        port: Port name
        date_input: Prediction date
        model_path: Optional path to saved model

    Returns:
        Predicted delay in days
    """
    predictor = PortCongestionPredictor(model_path=model_path)
    return predictor.get_delay_for_voyage(port, date_input)
