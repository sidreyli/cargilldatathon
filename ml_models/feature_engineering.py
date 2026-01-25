"""
Feature Engineering for Port Congestion Prediction
===================================================
Creates lag features, rolling statistics, and temporal features
from port activity data.
"""

import pandas as pd
import numpy as np
from datetime import datetime, date
from typing import List, Dict, Optional, Tuple

from .holiday_calendar import HolidayCalendar


class FeatureEngineer:
    """
    Feature engineering pipeline for port congestion prediction.

    Creates features including:
    - Temporal features (day of week, month, quarter)
    - Lag features (7, 14, 30 day lags)
    - Rolling statistics (mean, std, sum)
    - Momentum indicators
    - Seasonal/holiday features
    """

    # Target ports for the model
    TARGET_PORTS = {
        'port1069': {'name': 'Qingdao', 'country': 'CHN', 'base_delay': 3.0},
        'port1105': {'name': 'Rizhao', 'country': 'CHN', 'base_delay': 3.0},
        'port339': {'name': 'Fangcheng', 'country': 'CHN', 'base_delay': 3.0},
        'port1266': {'name': 'Caofeidian', 'country': 'CHN', 'base_delay': 3.5},
        'port777': {'name': 'Mundra', 'country': 'IND', 'base_delay': 2.0},
        'port1367': {'name': 'Vizag', 'country': 'IND', 'base_delay': 2.0},
    }

    # Lag periods for feature creation
    LAG_PERIODS = [7, 14, 30]

    # Rolling window sizes
    ROLLING_WINDOWS = [7, 14, 30]

    def __init__(self, port_database_path: Optional[str] = None):
        """
        Initialize feature engineer.

        Args:
            port_database_path: Path to PortWatch_ports_database.csv for capacity data
        """
        self.port_capacities = {}
        if port_database_path:
            self._load_port_capacities(port_database_path)

    def _load_port_capacities(self, path: str):
        """Load port capacity information from database."""
        try:
            df = pd.read_csv(path)
            for _, row in df.iterrows():
                port_id = row['portid']
                if port_id in self.TARGET_PORTS:
                    # Use vessel_count_dry_bulk as capacity proxy
                    # Normalized to daily capacity (annual vessel count / 365)
                    annual_vessels = row.get('vessel_count_dry_bulk', 0)
                    daily_capacity = annual_vessels / 365 if annual_vessels > 0 else 3.0
                    self.port_capacities[port_id] = {
                        'vessel_count_dry_bulk': annual_vessels,
                        'daily_capacity': daily_capacity,
                    }
        except Exception as e:
            print(f"Warning: Could not load port capacities: {e}")

    def get_port_capacity(self, port_id: str) -> float:
        """Get daily vessel capacity for a port."""
        if port_id in self.port_capacities:
            return self.port_capacities[port_id]['daily_capacity']
        # Default capacity estimates
        defaults = {
            'port1069': 3.5,  # Qingdao - major port
            'port1105': 4.8,  # Rizhao
            'port339': 3.6,   # Fangcheng
            'port1266': 7.8,  # Caofeidian
            'port777': 1.2,   # Mundra
            'port1367': 3.3,  # Vizag
        }
        return defaults.get(port_id, 3.0)

    def create_target_variable(
        self,
        df: pd.DataFrame,
        port_id: str,
        scaling_factor: float = 5.0,
    ) -> pd.Series:
        """
        Create congestion proxy target variable.

        Formula:
        delay_days = base_delay + scaling_factor * (portcalls/baseline_capacity - 1)

        Args:
            df: DataFrame with 'portcalls_dry_bulk' column
            port_id: Port identifier
            scaling_factor: How much delay increases per unit congestion

        Returns:
            Series with delay_days values
        """
        if port_id not in self.TARGET_PORTS:
            raise ValueError(f"Unknown port: {port_id}")

        base_delay = self.TARGET_PORTS[port_id]['base_delay']
        baseline_capacity = self.get_port_capacity(port_id)

        # Calculate congestion ratio
        congestion_ratio = df['portcalls_dry_bulk'] / baseline_capacity

        # Apply delay formula
        delay_days = base_delay + scaling_factor * (congestion_ratio - 1)

        # Apply 7-day rolling average for smoothing
        delay_days = delay_days.rolling(window=7, min_periods=1).mean()

        # Clip to reasonable range [0, 15] days
        delay_days = delay_days.clip(lower=0, upper=15)

        return delay_days

    def create_lag_features(
        self,
        df: pd.DataFrame,
        column: str,
        lags: Optional[List[int]] = None,
    ) -> pd.DataFrame:
        """
        Create lag features for a column.

        Args:
            df: Input DataFrame
            column: Column to create lags for
            lags: List of lag periods (default: [7, 14, 30])

        Returns:
            DataFrame with lag features
        """
        lags = lags or self.LAG_PERIODS
        result = pd.DataFrame(index=df.index)

        for lag in lags:
            result[f'{column}_lag{lag}'] = df[column].shift(lag)

        return result

    def create_rolling_features(
        self,
        df: pd.DataFrame,
        column: str,
        windows: Optional[List[int]] = None,
    ) -> pd.DataFrame:
        """
        Create rolling statistics features.

        Args:
            df: Input DataFrame
            column: Column to create rolling stats for
            windows: List of window sizes (default: [7, 14, 30])

        Returns:
            DataFrame with rolling features
        """
        windows = windows or self.ROLLING_WINDOWS
        result = pd.DataFrame(index=df.index)

        for window in windows:
            # Rolling mean
            result[f'{column}_rolling{window}_mean'] = (
                df[column].rolling(window=window, min_periods=1).mean()
            )
            # Rolling std
            result[f'{column}_rolling{window}_std'] = (
                df[column].rolling(window=window, min_periods=1).std()
            )

        # Rolling sum for import volumes
        if 'import' in column.lower():
            for window in [7, 30]:
                result[f'{column}_rolling{window}_sum'] = (
                    df[column].rolling(window=window, min_periods=1).sum()
                )

        return result

    def create_momentum_features(
        self,
        df: pd.DataFrame,
        column: str,
    ) -> pd.DataFrame:
        """
        Create momentum indicators (short-term vs long-term trends).

        Args:
            df: Input DataFrame
            column: Column to create momentum for

        Returns:
            DataFrame with momentum features
        """
        result = pd.DataFrame(index=df.index)

        # 7-day vs 30-day momentum
        rolling_7 = df[column].rolling(window=7, min_periods=1).mean()
        rolling_30 = df[column].rolling(window=30, min_periods=1).mean()

        result[f'{column}_momentum'] = (rolling_7 / rolling_30) - 1

        # Handle division by zero
        result[f'{column}_momentum'] = result[f'{column}_momentum'].replace(
            [np.inf, -np.inf], 0
        ).fillna(0)

        return result

    def create_temporal_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Create temporal features from date column.

        Args:
            df: DataFrame with 'date' column

        Returns:
            DataFrame with temporal features
        """
        result = pd.DataFrame(index=df.index)

        # Ensure date column is datetime
        if 'date' in df.columns:
            dates = pd.to_datetime(df['date'])
        else:
            dates = pd.to_datetime(df.index)

        # Use prefixed names to avoid conflicts with existing columns
        result['feat_day_of_week'] = dates.dt.dayofweek
        result['feat_month'] = dates.dt.month
        result['feat_week_of_year'] = dates.dt.isocalendar().week.astype(int)
        result['feat_quarter'] = dates.dt.quarter
        result['feat_day_of_month'] = dates.dt.day
        result['feat_is_weekend'] = (dates.dt.dayofweek >= 5).astype(int)

        return result

    def create_holiday_features(
        self,
        df: pd.DataFrame,
        country: str = 'CHN',
    ) -> pd.DataFrame:
        """
        Create holiday and seasonal features.

        Args:
            df: DataFrame with 'date' column
            country: Country code for holiday selection

        Returns:
            DataFrame with holiday features
        """
        result = pd.DataFrame(index=df.index)

        # Ensure date column is datetime
        if 'date' in df.columns:
            dates = pd.to_datetime(df['date'])
        else:
            dates = pd.to_datetime(df.index)

        # Apply holiday calendar
        for i, d in enumerate(dates):
            features = HolidayCalendar.get_seasonal_features(d.date(), country)
            for key, value in features.items():
                if key not in result.columns:
                    result[key] = np.nan
                result.iloc[i, result.columns.get_loc(key)] = value

        return result

    def create_port_features(self, port_id: str) -> Dict[str, float]:
        """
        Create static port features.

        Args:
            port_id: Port identifier

        Returns:
            Dict with port-level features
        """
        if port_id not in self.TARGET_PORTS:
            return {'port_capacity_ratio': 1.0, 'is_china': 0, 'is_india': 0}

        port_info = self.TARGET_PORTS[port_id]
        capacity = self.get_port_capacity(port_id)

        return {
            'port_capacity_ratio': capacity / 3.0,  # Normalized to average
            'is_china': 1 if port_info['country'] == 'CHN' else 0,
            'is_india': 1 if port_info['country'] == 'IND' else 0,
        }

    def engineer_features(
        self,
        df: pd.DataFrame,
        port_id: str,
        include_target: bool = True,
    ) -> pd.DataFrame:
        """
        Full feature engineering pipeline.

        Args:
            df: Raw DataFrame with columns: date, portcalls_dry_bulk, import_dry_bulk
            port_id: Port identifier
            include_target: Whether to include target variable

        Returns:
            DataFrame with all engineered features
        """
        result = df.copy()
        country = self.TARGET_PORTS.get(port_id, {}).get('country', 'CHN')

        # Lag features for port calls
        lag_features = self.create_lag_features(result, 'portcalls_dry_bulk')
        result = pd.concat([result, lag_features], axis=1)

        # Rolling features for port calls
        rolling_features = self.create_rolling_features(result, 'portcalls_dry_bulk')
        result = pd.concat([result, rolling_features], axis=1)

        # Rolling features for imports if available
        if 'import_dry_bulk' in result.columns:
            import_rolling = self.create_rolling_features(result, 'import_dry_bulk')
            result = pd.concat([result, import_rolling], axis=1)

            import_momentum = self.create_momentum_features(result, 'import_dry_bulk')
            result = pd.concat([result, import_momentum], axis=1)

        # Temporal features
        temporal_features = self.create_temporal_features(result)
        result = pd.concat([result, temporal_features], axis=1)

        # Holiday features
        holiday_features = self.create_holiday_features(result, country)
        result = pd.concat([result, holiday_features], axis=1)

        # Port static features
        port_features = self.create_port_features(port_id)
        for key, value in port_features.items():
            result[key] = value

        # Add port_id as categorical
        result['port_id'] = port_id

        # Target variable
        if include_target:
            result['delay_days'] = self.create_target_variable(result, port_id)

        return result

    def get_feature_columns(self) -> List[str]:
        """Get list of feature column names for model training."""
        return [
            # Lag features
            'portcalls_dry_bulk_lag7',
            'portcalls_dry_bulk_lag14',
            'portcalls_dry_bulk_lag30',
            # Rolling features
            'portcalls_dry_bulk_rolling7_mean',
            'portcalls_dry_bulk_rolling7_std',
            'portcalls_dry_bulk_rolling14_mean',
            'portcalls_dry_bulk_rolling14_std',
            'portcalls_dry_bulk_rolling30_mean',
            'portcalls_dry_bulk_rolling30_std',
            # Import features
            'import_dry_bulk_rolling7_mean',
            'import_dry_bulk_rolling7_sum',
            'import_dry_bulk_rolling30_sum',
            'import_dry_bulk_momentum',
            # Temporal features (prefixed to avoid conflicts)
            'feat_day_of_week',
            'feat_month',
            'feat_week_of_year',
            'feat_quarter',
            'feat_is_weekend',
            # Holiday features
            'is_cny',
            'cny_proximity_days',
            'is_golden_week',
            'is_monsoon_india',
            'is_diwali',
            # Port features
            'port_capacity_ratio',
            'is_china',
            'is_india',
        ]
