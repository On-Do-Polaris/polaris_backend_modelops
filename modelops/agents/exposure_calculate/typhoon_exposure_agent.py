"""
Typhoon Exposure Agent
Calculates exposure to typhoon hazards.
"""
from typing import Dict, Any
import logging
from .base_exposure_agent import BaseExposureAgent

try:
    from modelops.config import hazard_config as config
except ImportError:
    config = None

logger = logging.getLogger(__name__)


class TyphoonExposureAgent(BaseExposureAgent):
    """
    Typhoon Exposure calculation agent.

    Evaluates exposure to typhoons based on distance to coast.
    """

    def __init__(self):
        super().__init__()

    def calculate_exposure(self, building_data: Dict[str, Any], spatial_data: Dict[str, Any],
                          **kwargs) -> Dict[str, Any]:
        """
        Calculate typhoon exposure.

        Args:
            building_data: Building information
            spatial_data: Spatial information (not used for this hazard)
            **kwargs: Additional parameters

        Returns:
            Typhoon exposure data
        """
        if not config:
            logger.warning("Config module not loaded. Using hardcoded defaults.")
            dist_defaults = {'distance_to_coast_m': 50000}
        else:
            dist_defaults = config.DEFAULT_DISTANCE_VALUES

        distance_to_coast = building_data.get('distance_to_coast_m', dist_defaults['distance_to_coast_m'])

        return {
            'distance_to_coast_m': distance_to_coast,
            'coastal_exposure': distance_to_coast < 10000,
            'coastal_distance_score': self._calculate_typhoon_distance_score(distance_to_coast),
            'exposure_level': self._classify_typhoon_exposure_level(distance_to_coast),
        }

    def _calculate_typhoon_distance_score(self, distance_m: float) -> int:
        """
        Calculate typhoon exposure score based on distance to coast.

        Args:
            distance_m: Distance to coast (meters)

        Returns:
            Exposure score
        """
        if not config:
            return 10

        thresholds = config.TYPHOON_EXPOSURE_SCORES
        if distance_m < thresholds['very_high']['distance_m']:
            return thresholds['very_high']['score']
        elif distance_m < thresholds['high']['distance_m']:
            return thresholds['high']['score']
        elif distance_m < thresholds['medium']['distance_m']:
            return thresholds['medium']['score']
        else:
            return thresholds['low']['score']

    def _classify_typhoon_exposure_level(self, distance_m: float) -> str:
        """
        Classify typhoon exposure level.

        Args:
            distance_m: Distance to coast (meters)

        Returns:
            Exposure level (critical/high/medium/low)
        """
        if not config:
            return 'low'

        thresholds = config.TYPHOON_EXPOSURE_SCORES
        if distance_m < thresholds['very_high']['distance_m']:
            return 'critical'
        elif distance_m < thresholds['high']['distance_m']:
            return 'high'
        elif distance_m < thresholds['medium']['distance_m']:
            return 'medium'
        else:
            return 'low'
