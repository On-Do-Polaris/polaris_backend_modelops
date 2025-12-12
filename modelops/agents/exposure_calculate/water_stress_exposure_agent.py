"""
Water Stress Exposure Agent
Calculates exposure to water stress hazards.
"""
from typing import Dict, Any
import logging
from .base_exposure_agent import BaseExposureAgent

try:
    from modelops.config import hazard_config as config
except ImportError:
    config = None

logger = logging.getLogger(__name__)


class WaterStressExposureAgent(BaseExposureAgent):
    """
    Water Stress Exposure calculation agent.

    Evaluates exposure to water stress based on water dependency,
    storage capacity, and backup supply.
    """

    def __init__(self):
        super().__init__()

    def calculate_exposure(self, building_data: Dict[str, Any], spatial_data: Dict[str, Any],
                          **kwargs) -> Dict[str, Any]:
        """
        Calculate water stress exposure.

        Args:
            building_data: Building information
            spatial_data: Spatial information (not used for this hazard)
            **kwargs: Additional parameters

        Returns:
            Water stress exposure data
        """
        water_dependency = self._classify_water_dependency(building_data)
        water_storage = self._estimate_water_storage(building_data)

        return {
            'water_dependency': water_dependency,
            'water_storage_capacity': water_storage,
            'backup_water_supply': building_data.get('backup_water_supply', False),
            'score': self._calculate_water_stress_exposure_score(building_data),
        }

    def _classify_water_dependency(self, data: Dict) -> str:
        """
        Classify water dependency.

        Args:
            data: Building data

        Returns:
            Water dependency (high/medium/low)
        """
        building_purpose = data.get('main_purpose', 'residential')

        high_keywords = ['factory', 'manufacturing', 'cooling', 'car_wash', 'bath', 'power']
        medium_keywords = ['office', 'commercial', 'retail']

        if any(keyword in building_purpose for keyword in high_keywords):
            return 'high'
        elif any(keyword in building_purpose for keyword in medium_keywords):
            return 'medium'
        else:
            return 'low'

    def _estimate_water_storage(self, data: Dict) -> str:
        """
        Estimate water storage capacity based on building floors.

        Args:
            data: Building data

        Returns:
            Storage capacity (large/medium/limited)
        """
        ground_floors = data.get('ground_floors', 3)

        if ground_floors > 10:
            return 'large'
        elif ground_floors > 5:
            return 'medium'
        else:
            return 'limited'

    def _calculate_water_stress_exposure_score(self, data: Dict) -> int:
        """
        Calculate water stress exposure score.

        Args:
            data: Building data

        Returns:
            Exposure score (0-100)
        """
        water_dependency = self._classify_water_dependency(data)
        water_storage = self._estimate_water_storage(data)

        # Base score from water dependency
        if water_dependency == 'high':
            score = 70
        elif water_dependency == 'medium':
            score = 50
        else:
            score = 30

        # Adjust for storage capacity
        if water_storage == 'limited':
            score += 20
        elif water_storage == 'medium':
            score += 10

        return min(score, 100)
