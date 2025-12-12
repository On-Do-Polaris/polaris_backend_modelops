"""
Urban Flood Exposure Agent
Calculates exposure to urban flooding hazards.
"""
from typing import Dict, Any, Tuple
import logging
from .base_exposure_agent import BaseExposureAgent

try:
    from modelops.config import hazard_config as config
except ImportError:
    config = None

logger = logging.getLogger(__name__)


class UrbanFloodExposureAgent(BaseExposureAgent):
    """
    Urban Flood Exposure calculation agent.

    Evaluates exposure to urban flooding based on impervious surface ratio
    and drainage capacity.
    """

    def __init__(self):
        super().__init__()

    def calculate_exposure(self, building_data: Dict[str, Any], spatial_data: Dict[str, Any],
                          **kwargs) -> Dict[str, Any]:
        """
        Calculate urban flood exposure.

        Args:
            building_data: Building information
            spatial_data: Spatial information
            **kwargs: Additional parameters

        Returns:
            Urban flood exposure data
        """
        land_use = spatial_data.get('landcover_type', 'urban')
        urban_intensity, score, imperviousness_percent = self._calculate_urban_flood_exposure_score(building_data)

        return {
            'urban_intensity': urban_intensity,
            'score': score,
            'imperviousness_percent': imperviousness_percent,
            'impervious_surface_ratio': self._estimate_impervious_surface_ratio(spatial_data),
            'drainage_capacity': self._estimate_drainage_capacity(building_data),
            'urban_area': land_use in ['urban', 'commercial', 'residential', 'mixed-use', 'industrial'],
        }

    def _estimate_impervious_surface_ratio(self, landcover_data: Dict) -> float:
        """Estimate impervious surface ratio."""
        return landcover_data.get('impervious_ratio', 0.6)

    def _estimate_drainage_capacity(self, data: Dict) -> str:
        """Estimate drainage capacity based on building age."""
        build_year = data.get('build_year')
        current_year = 2025
        if build_year is None:
            return 'standard'

        building_age = current_year - build_year
        if building_age < 10:
            return 'good'
        elif building_age < 30:
            return 'standard'
        else:
            return 'poor'

    def _calculate_urban_flood_exposure_score(self, data: Dict) -> Tuple[str, int, int]:
        """
        Calculate urban flood exposure score.

        Returns:
            Tuple of (risk_level, score, imperviousness_percent)
        """
        if not config:
            return 'low', 20, 35

        building_type = data.get('building_type', 'residential')
        if 'commercial' in building_type or 'office' in building_type:
            return 'high', 80, 85
        elif 'residential' in building_type or 'apartment' in building_type:
            return 'medium', 50, 65
        else:
            return 'low', 20, 35
