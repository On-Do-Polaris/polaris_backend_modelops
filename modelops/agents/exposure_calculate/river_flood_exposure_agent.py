"""
River Flood Exposure Agent
Calculates exposure to river flooding hazards.
"""
from typing import Dict, Any, Tuple
import logging
from .base_exposure_agent import BaseExposureAgent

try:
    from modelops.config import hazard_config as config
except ImportError:
    config = None

logger = logging.getLogger(__name__)


class RiverFloodExposureAgent(BaseExposureAgent):
    """
    River Flood Exposure calculation agent.

    Evaluates exposure to river flooding based on distance to river,
    watershed area, stream order, and flood zone status.
    """

    def __init__(self):
        super().__init__()

    def calculate_exposure(self, building_data: Dict[str, Any], spatial_data: Dict[str, Any],
                          **kwargs) -> Dict[str, Any]:
        """
        Calculate river flood exposure.

        Args:
            building_data: Building information
            spatial_data: Spatial information (not used for this hazard)
            **kwargs: Additional parameters

        Returns:
            River flood exposure data
        """
        if not config:
            logger.warning("Config module not loaded. Using hardcoded defaults.")
            dist_defaults = {'distance_to_river_m': 1000}
            hydro_defaults = {'watershed_area_km2': 2500, 'stream_order': 3}
        else:
            dist_defaults = config.DEFAULT_DISTANCE_VALUES
            hydro_defaults = config.DEFAULT_HYDROLOGICAL_VALUES

        distance_to_river = building_data.get('distance_to_river_m', dist_defaults['distance_to_river_m'])
        proximity_category, score = self._calculate_river_flood_exposure_score(distance_to_river)

        return {
            'distance_to_river_m': distance_to_river,
            'proximity_category': proximity_category,
            'score': score,
            'distance_to_coast_m': building_data.get('distance_to_coast_m', 50000),
            'watershed_area_km2': building_data.get('watershed_area_km2', hydro_defaults['watershed_area_km2']),
            'stream_order': building_data.get('stream_order', hydro_defaults['stream_order']),
            'in_flood_zone': self._is_in_flood_zone(building_data),
        }

    def _is_in_flood_zone(self, data: Dict) -> bool:
        """Check if location is in flood zone."""
        distance_to_river = data.get('distance_to_river_m', 1000)
        elevation = data.get('elevation_m', 50)
        return distance_to_river < 100 and elevation < 50

    def _calculate_river_flood_exposure_score(self, distance_m: float) -> Tuple[str, int]:
        """
        Calculate flood exposure score based on distance to river.

        Returns:
            Tuple of (proximity_category, score)
        """
        if not config:
            return 'low', 10

        thresholds = config.RIVER_FLOOD_EXPOSURE_SCORES
        if distance_m < thresholds['very_high']['distance_m']:
            return 'very_high', thresholds['very_high']['score']
        elif distance_m < thresholds['high']['distance_m']:
            return 'high', thresholds['high']['score']
        elif distance_m < thresholds['medium']['distance_m']:
            return 'medium', thresholds['medium']['score']
        else:
            return 'low', thresholds['low']['score']
