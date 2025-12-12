"""
Drought Exposure Agent
Calculates exposure to drought hazards.
"""
from typing import Dict, Any
import logging
from .base_exposure_agent import BaseExposureAgent

try:
    from modelops.config import hazard_config as config
except ImportError:
    config = None

logger = logging.getLogger(__name__)


class DroughtExposureAgent(BaseExposureAgent):
    """
    Drought Exposure calculation agent.

    Evaluates exposure to drought based on annual rainfall and water dependency.
    """

    def __init__(self):
        super().__init__()

    def calculate_exposure(self, building_data: Dict[str, Any], spatial_data: Dict[str, Any],
                          **kwargs) -> Dict[str, Any]:
        """
        Calculate drought exposure.

        Args:
            building_data: Building information
            spatial_data: Spatial information (not used for this hazard)
            **kwargs: Additional parameters

        Returns:
            Drought exposure data
        """
        if not config:
            logger.warning("Config module not loaded. Using hardcoded defaults.")
            hydro_defaults = {'annual_rainfall_mm': 1200}
        else:
            hydro_defaults = config.DEFAULT_HYDROLOGICAL_VALUES

        annual_rainfall = building_data.get('annual_rainfall_mm', hydro_defaults['annual_rainfall_mm'])
        water_dependency = self._classify_water_dependency(building_data)

        return {
            'annual_rainfall_mm': annual_rainfall,
            'water_dependency': water_dependency,
            'score': self._calculate_drought_exposure_score(water_dependency, annual_rainfall),
        }

    def _classify_water_dependency(self, data: Dict) -> str:
        """Classify water dependency."""
        building_purpose = data.get('main_purpose', 'residential')

        high_keywords = ['factory', 'manufacturing', 'cooling', 'car_wash', 'bath', 'power']
        medium_keywords = ['office', 'commercial', 'retail']

        if any(keyword in building_purpose for keyword in high_keywords):
            return 'high'
        elif any(keyword in building_purpose for keyword in medium_keywords):
            return 'medium'
        else:
            return 'low'

    def _calculate_drought_exposure_score(self, water_dependency: str, annual_rainfall_mm: float) -> int:
        """
        Calculate drought exposure score.

        Args:
            water_dependency: Water dependency (high/medium/low)
            annual_rainfall_mm: Annual rainfall (mm)

        Returns:
            Exposure score (0-100)
        """
        if water_dependency == 'high':
            score = 80
        elif water_dependency == 'medium':
            score = 50
        else:
            score = 30

        # Lower rainfall increases exposure
        if annual_rainfall_mm < 1000:
            score += 10

        return score
