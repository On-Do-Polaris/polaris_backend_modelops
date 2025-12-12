"""
Extreme Heat Exposure Agent
Calculates exposure to extreme heat hazards.
"""
from typing import Dict, Any
import logging
from .base_exposure_agent import BaseExposureAgent

try:
    from modelops.config import hazard_config as config
except ImportError:
    config = None

logger = logging.getLogger(__name__)


class ExtremeHeatExposureAgent(BaseExposureAgent):
    """
    Extreme Heat Exposure calculation agent.

    Evaluates exposure to extreme heat based on urban heat island effect,
    green space proximity, building orientation, and land use.
    """

    def __init__(self):
        super().__init__()

    def calculate_exposure(self, building_data: Dict[str, Any], spatial_data: Dict[str, Any],
                          **kwargs) -> Dict[str, Any]:
        """
        Calculate extreme heat exposure.

        Args:
            building_data: Building information
            spatial_data: Spatial information
            **kwargs: Additional parameters (latitude, longitude)

        Returns:
            Extreme heat exposure data
        """
        latitude = kwargs.get('latitude', 0.0)
        longitude = kwargs.get('longitude', 0.0)

        uhi_risk = self._classify_uhi_risk(spatial_data)

        return {
            'urban_heat_island': self._estimate_uhi_intensity(building_data),
            'green_space_nearby': self._estimate_green_space_proximity(spatial_data),
            'building_orientation': self._estimate_building_orientation(latitude, longitude),
            'uhi_risk': uhi_risk,
            'score': self._calculate_heat_exposure_score(spatial_data),
        }

    def _estimate_uhi_intensity(self, data: Dict) -> str:
        """Estimate urban heat island intensity."""
        building_type = data.get('building_type', 'residential')
        if 'commercial' in building_type or 'office' in building_type:
            return 'high'
        elif 'residential' in building_type:
            return 'medium'
        else:
            return 'low'

    def _estimate_green_space_proximity(self, landcover_data: Dict) -> bool:
        """Evaluate proximity to green spaces."""
        land_use = landcover_data.get('landcover_type', 'urban')
        vegetation_ratio = landcover_data.get('vegetation_ratio', 0.0)
        return vegetation_ratio > 0.3 or land_use in ['agricultural', 'grassland', 'forest']

    def _estimate_building_orientation(self, lat: float, lon: float) -> str:
        """Estimate building orientation based on latitude."""
        if lat > 37.5:
            return 'north'
        elif lat > 35:
            return 'mixed'
        else:
            return 'south'

    def _classify_uhi_risk(self, landcover_data: Dict) -> str:
        """Classify urban heat island risk."""
        land_use = landcover_data.get('landcover_type', 'urban')
        if land_use in ['commercial', 'industrial']:
            return 'high'
        elif land_use == 'residential':
            return 'medium'
        else:
            return 'low'

    def _calculate_heat_exposure_score(self, landcover_data: Dict) -> int:
        """
        Calculate heat exposure score.

        Reference: High=70, Medium=50, Low=30
        """
        if not config:
            return 50

        uhi_risk = self._classify_uhi_risk(landcover_data)
        scores = config.EXTREME_HEAT_EXPOSURE_SCORES

        if uhi_risk == 'high':
            return scores['high']
        elif uhi_risk == 'medium':
            return scores['medium']
        else:
            return scores['low']
