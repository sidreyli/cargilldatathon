"""
Holiday Calendar for Port Congestion Prediction
================================================
Contains Chinese New Year, Indian holidays, and monsoon season dates
that affect port congestion levels.
"""

from datetime import datetime, date
from typing import Dict, Tuple, Optional


class HolidayCalendar:
    """
    Calendar for holidays and seasonal events affecting port congestion.

    Covers:
    - Chinese New Year (major impact on China ports)
    - Golden Week China (Oct 1-7)
    - Indian Monsoon (June-September, affects west coast ports)
    - Diwali (October-November)
    """

    # Chinese New Year dates (start, end) - includes extended holidays
    CNY_DATES: Dict[int, Tuple[str, str]] = {
        2019: ('2019-02-05', '2019-02-19'),
        2020: ('2020-01-25', '2020-02-08'),
        2021: ('2021-02-12', '2021-02-26'),
        2022: ('2022-02-01', '2022-02-15'),
        2023: ('2023-01-22', '2023-02-05'),
        2024: ('2024-02-10', '2024-02-24'),
        2025: ('2025-01-29', '2025-02-12'),
        2026: ('2026-02-17', '2026-03-03'),
        2027: ('2027-02-06', '2027-02-20'),
    }

    # Diwali dates (approximate, varies by year)
    DIWALI_DATES: Dict[int, Tuple[str, str]] = {
        2019: ('2019-10-25', '2019-10-30'),
        2020: ('2020-11-12', '2020-11-17'),
        2021: ('2021-11-02', '2021-11-07'),
        2022: ('2022-10-22', '2022-10-27'),
        2023: ('2023-11-10', '2023-11-15'),
        2024: ('2024-10-29', '2024-11-03'),
        2025: ('2025-10-18', '2025-10-23'),
        2026: ('2026-11-06', '2026-11-11'),
    }

    # Golden Week China (fixed dates each year)
    GOLDEN_WEEK_START = '10-01'
    GOLDEN_WEEK_END = '10-07'

    # Indian Monsoon (Southwest monsoon - affects west coast ports like Mundra)
    MONSOON_INDIA_START = '06-01'
    MONSOON_INDIA_END = '09-30'

    # China Typhoon Season (affects southern and eastern coastal ports)
    TYPHOON_SEASON_START = '07-01'
    TYPHOON_SEASON_END = '10-31'

    # Winter Impact (affects northern China ports - ice/fog)
    WINTER_NORTH_CHINA_START = '12-01'
    WINTER_NORTH_CHINA_END = '02-28'

    @classmethod
    def is_cny(cls, check_date: date) -> bool:
        """Check if date falls within Chinese New Year period."""
        year = check_date.year
        if year not in cls.CNY_DATES:
            return False

        start_str, end_str = cls.CNY_DATES[year]
        start = datetime.strptime(start_str, '%Y-%m-%d').date()
        end = datetime.strptime(end_str, '%Y-%m-%d').date()

        return start <= check_date <= end

    @classmethod
    def cny_proximity_days(cls, check_date: date) -> int:
        """
        Calculate days to/from nearest CNY period.

        Returns:
            Positive: days until CNY starts
            Negative: days since CNY ended
            Zero: within CNY period
        """
        year = check_date.year

        # Check current year
        if year in cls.CNY_DATES:
            start_str, end_str = cls.CNY_DATES[year]
            start = datetime.strptime(start_str, '%Y-%m-%d').date()
            end = datetime.strptime(end_str, '%Y-%m-%d').date()

            if check_date < start:
                return (start - check_date).days
            elif check_date > end:
                # Check next year
                if year + 1 in cls.CNY_DATES:
                    next_start_str, _ = cls.CNY_DATES[year + 1]
                    next_start = datetime.strptime(next_start_str, '%Y-%m-%d').date()
                    return (next_start - check_date).days
                return -(check_date - end).days
            else:
                return 0  # Within CNY

        return 365  # Default if year not found

    @classmethod
    def is_golden_week(cls, check_date: date) -> bool:
        """Check if date falls within China Golden Week (Oct 1-7)."""
        month = check_date.month
        day = check_date.day
        return month == 10 and 1 <= day <= 7

    @classmethod
    def is_monsoon_india(cls, check_date: date) -> bool:
        """Check if date falls within Indian monsoon season (June-September)."""
        month = check_date.month
        return 6 <= month <= 9

    @classmethod
    def is_typhoon_season(cls, check_date: date) -> bool:
        """Check if date falls within China typhoon season (July-October)."""
        month = check_date.month
        return 7 <= month <= 10

    @classmethod
    def is_winter_north_china(cls, check_date: date) -> bool:
        """Check if date falls within northern China winter (Dec-Feb)."""
        month = check_date.month
        return month in (12, 1, 2)

    @classmethod
    def get_monsoon_intensity(cls, check_date: date) -> float:
        """
        Get monsoon intensity factor (0.0 to 1.0).

        Peak intensity in July-August, lower at start/end of season.
        """
        month = check_date.month
        if month < 6 or month > 9:
            return 0.0
        # June: 0.5, July: 1.0, August: 1.0, September: 0.5
        intensity_map = {6: 0.5, 7: 1.0, 8: 1.0, 9: 0.5}
        return intensity_map.get(month, 0.0)

    @classmethod
    def get_typhoon_risk(cls, check_date: date) -> float:
        """
        Get typhoon risk factor (0.0 to 1.0).

        Peak risk in August-September, moderate in July and October.
        """
        month = check_date.month
        if month < 7 or month > 10:
            return 0.0
        # July: 0.4, August: 1.0, September: 1.0, October: 0.3
        risk_map = {7: 0.4, 8: 1.0, 9: 1.0, 10: 0.3}
        return risk_map.get(month, 0.0)

    @classmethod
    def is_diwali(cls, check_date: date) -> bool:
        """Check if date falls within Diwali period."""
        year = check_date.year
        if year not in cls.DIWALI_DATES:
            return False

        start_str, end_str = cls.DIWALI_DATES[year]
        start = datetime.strptime(start_str, '%Y-%m-%d').date()
        end = datetime.strptime(end_str, '%Y-%m-%d').date()

        return start <= check_date <= end

    @classmethod
    def get_seasonal_features(cls, check_date: date, country: str = 'CHN') -> Dict[str, float]:
        """
        Get all seasonal features for a given date and country.

        Args:
            check_date: Date to check
            country: ISO3 country code ('CHN' for China, 'IND' for India,
                     'KOR' for South Korea, 'MYS' for Malaysia, 'ZAF' for South Africa)

        Returns:
            Dict with all seasonal indicator features
        """
        features = {
            'is_cny': 1.0 if cls.is_cny(check_date) else 0.0,
            'cny_proximity_days': cls.cny_proximity_days(check_date),
            'is_golden_week': 1.0 if cls.is_golden_week(check_date) else 0.0,
            'is_monsoon_india': 1.0 if cls.is_monsoon_india(check_date) else 0.0,
            'is_diwali': 1.0 if cls.is_diwali(check_date) else 0.0,
            # Weather factors
            'is_typhoon_season': 1.0 if cls.is_typhoon_season(check_date) else 0.0,
            'typhoon_risk': cls.get_typhoon_risk(check_date),
            'is_winter_north_china': 1.0 if cls.is_winter_north_china(check_date) else 0.0,
            'monsoon_intensity': cls.get_monsoon_intensity(check_date),
        }

        # Apply country-specific logic
        if country == 'CHN':
            features['is_monsoon_india'] = 0.0
            features['is_diwali'] = 0.0
            features['monsoon_intensity'] = 0.0
        elif country == 'IND':
            features['is_cny'] = 0.0
            features['cny_proximity_days'] = 0
            features['is_golden_week'] = 0.0
            features['is_typhoon_season'] = 0.0
            features['typhoon_risk'] = 0.0
            features['is_winter_north_china'] = 0.0
        elif country in ('KOR', 'MYS', 'ZAF'):
            # South Korea, Malaysia, South Africa - minimal holiday impact
            features['is_cny'] = 0.0
            features['cny_proximity_days'] = 0
            features['is_golden_week'] = 0.0
            features['is_monsoon_india'] = 0.0
            features['is_diwali'] = 0.0
            features['monsoon_intensity'] = 0.0
            # Korea has some typhoon risk
            if country == 'KOR':
                features['typhoon_risk'] = cls.get_typhoon_risk(check_date) * 0.5
            else:
                features['is_typhoon_season'] = 0.0
                features['typhoon_risk'] = 0.0
            features['is_winter_north_china'] = 0.0

        return features
