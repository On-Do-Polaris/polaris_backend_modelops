"""
Base Exposure Agent with common utilities for all exposure calculations.
"""
from typing import Dict, Any
import logging

try:
    from modelops.config import hazard_config as config
except ImportError:
    config = None

logger = logging.getLogger(__name__)


class BaseExposureAgent:
    """
    Base class for all exposure calculation agents.

    Provides common utility methods that are shared across different hazard types.
    """

    def __init__(self):
        pass

    def calculate_exposure(self, building_data: Dict[str, Any], spatial_data: Dict[str, Any],
                          **kwargs) -> Dict[str, Any]:
        """
        Calculate exposure for a specific hazard type.
        Must be implemented by child classes.

        Args:
            building_data: Building information
            spatial_data: Spatial information
            **kwargs: Additional parameters (e.g., latitude, longitude)

        Returns:
            Exposure data dictionary
        """
        raise NotImplementedError("Subclasses must implement calculate_exposure()")

    def _get_config_or_default(self, config_key: str, default_value: Any) -> Any:
        """
        Get configuration value or return default.

        Args:
            config_key: Configuration key to lookup
            default_value: Default value if config is not available

        Returns:
            Configuration value or default
        """
        if not config:
            return default_value
        return getattr(config, config_key, default_value)
