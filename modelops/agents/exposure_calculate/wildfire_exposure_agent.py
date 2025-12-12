"""
Wildfire Exposure Agent
Calculates exposure to wildfire hazards.
"""
from typing import Dict, Any, Tuple
import logging
from .base_exposure_agent import BaseExposureAgent

try:
    from modelops.config import hazard_config as config
except ImportError:
    config = None

logger = logging.getLogger(__name__)


class WildfireExposureAgent(BaseExposureAgent):
    """
    Wildfire Exposure calculation agent.

    Evaluates exposure to wildfires based on distance to forest,
    vegetation type, and slope.
    """

    def __init__(self):
        super().__init__()

    def calculate_exposure(self, building_data: Dict[str, Any], spatial_data: Dict[str, Any],
                          **kwargs) -> Dict[str, Any]:
        """
        Calculate wildfire exposure.

        Args:
            building_data: Building information
            spatial_data: Spatial information
            **kwargs: Additional parameters

        Returns:
            Wildfire exposure data
        """
        forest_distance = self._calculate_forest_distance(spatial_data)
        proximity_category, score = self._calculate_wildfire_exposure_score(forest_distance)

        return {
            'distance_to_forest_m': forest_distance,
            'proximity_category': proximity_category,
            'score': score,
            'vegetation_type': self._get_vegetation_type(spatial_data),
            'slope_degree': self._calculate_slope_from_dem(building_data),
        }

    def _calculate_forest_distance(self, landcover_data: Dict) -> float:
        """
        Estimate distance to forest based on land cover data.

        Args:
            landcover_data: Land cover information

        Returns:
            Estimated distance to forest (meters)
        """
        land_use = landcover_data.get('landcover_type', 'urban')

        if land_use == 'forest':
            return 0
        elif land_use == 'agricultural':
            return 300
        elif land_use == 'grassland':
            return 500
        elif land_use == 'residential':
            return 1500
        else:
            return 2000

    def _get_vegetation_type(self, landcover_data: Dict) -> str:
        """Classify vegetation type."""
        land_use = landcover_data.get('landcover_type', 'urban')

        if land_use == 'forest':
            return 'dense_forest'
        elif land_use == 'grassland':
            return 'grassland'
        elif land_use == 'agricultural':
            return 'cultivated'
        else:
            return 'urban'

    def _calculate_slope_from_dem(self, data: Dict) -> float:
        """
        Estimate slope based on DEM data.

        Args:
            data: Building data (includes elevation_m)

        Returns:
            Slope (degrees)
        """
        elevation = data.get('elevation_m', 0)

        if elevation < 100:
            return 2
        elif elevation < 300:
            return 8
        elif elevation < 500:
            return 15
        else:
            return 25

    def _calculate_wildfire_exposure_score(self, distance_m: float) -> Tuple[str, int]:
        """
        Calculate wildfire exposure score based on distance to forest.

        Args:
            distance_m: Distance to forest (meters)

        Returns:
            Tuple of (proximity_category, score)
        """
        if not config:
            return 'low', 10

        thresholds = config.WILDFIRE_EXPOSURE_SCORES
        if distance_m <= thresholds['extreme']['distance_m']:
            return 'extreme', thresholds['extreme']['score']
        elif distance_m <= thresholds['high']['distance_m']:
            return 'high', thresholds['high']['score']
        elif distance_m <= thresholds['medium']['distance_m']:
            return 'medium', thresholds['medium']['score']
        elif distance_m <= thresholds['low']['distance_m']:
            return 'low', thresholds['low']['score']
        else:
            return 'safe', thresholds['safe']['score']
