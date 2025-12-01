"""
Exposure Agent (E 계산)
노출도 계산: normalized_asset_value × proximity_to_hazard
"""

from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


class ExposureAgent:
    """노출도 (E) 계산 Agent"""

    def __init__(self):
        """ExposureAgent 초기화"""
        self.risk_types = [
            'extreme_heat', 'extreme_cold', 'wildfire', 'drought',
            'water_stress', 'sea_level_rise', 'river_flood',
            'urban_flood', 'typhoon'
        ]

    def calculate_exposure(
        self,
        latitude: float,
        longitude: float,
        risk_type: str,
        building_info: Dict[str, Any],
        asset_info: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        노출도 계산

        E = normalized_asset_value × proximity_to_hazard

        Args:
            latitude: 위도
            longitude: 경도
            risk_type: 리스크 유형
            building_info: 건물 정보
            asset_info: 자산 정보 (현재 None)

        Returns:
            {
                'exposure_score': 0.0 ~ 1.0,
                'proximity_factor': 0.0 ~ 1.0,
                'normalized_asset_value': 0.0 ~ 1.0,
                'calculation_details': {...}
            }
        """
        try:
            # 1. 자산 가치 정규화 (현재는 건물 면적 기반으로 간단 계산)
            normalized_asset = self._normalize_asset_value(building_info, asset_info)

            # 2. 위험 요소 근접도 계산
            proximity = self._calculate_proximity_factor(
                latitude, longitude, risk_type, building_info
            )

            # 3. 노출도 = 자산 가치 × 근접도
            exposure_score = normalized_asset * proximity

            return {
                'exposure_score': round(exposure_score, 4),
                'proximity_factor': round(proximity, 4),
                'normalized_asset_value': round(normalized_asset, 4),
                'calculation_details': {
                    'risk_type': risk_type,
                    'latitude': latitude,
                    'longitude': longitude,
                    'building_area': building_info.get('total_area', 0)
                }
            }

        except Exception as e:
            logger.error(f"Exposure 계산 실패 ({risk_type}): {e}")
            return {
                'exposure_score': 0.0,
                'proximity_factor': 0.0,
                'normalized_asset_value': 0.0,
                'error': str(e)
            }

    def _normalize_asset_value(
        self,
        building_info: Dict[str, Any],
        asset_info: Optional[Dict[str, Any]]
    ) -> float:
        """
        자산 가치 정규화 (0.0 ~ 1.0)

        현재는 자산 정보가 없으므로 건물 면적 기반으로 간단 계산
        """
        if asset_info and asset_info.get('total_asset_value'):
            # 자산 가치가 있을 경우 (미래 구현)
            asset_value = asset_info['total_asset_value']
            # 예시: 1000억원을 1.0으로 정규화
            max_asset = 100_000_000_000  # 1000억
            return min(1.0, asset_value / max_asset)

        # 건물 면적 기반 간단 정규화
        total_area = building_info.get('total_area', 0) or 0

        if total_area <= 0:
            return 0.5  # 기본값

        # 면적 정규화: 10,000㎡를 1.0으로
        max_area = 10_000
        normalized = min(1.0, total_area / max_area)

        # 최소값 0.1 보장 (너무 작은 값 방지)
        return max(0.1, normalized)

    def _calculate_proximity_factor(
        self,
        latitude: float,
        longitude: float,
        risk_type: str,
        building_info: Dict[str, Any]
    ) -> float:
        """
        위험 요소 근접도 계산 (0.0 ~ 1.0)

        리스크 유형별 근접도 계산 로직
        - 침수: 저층 건물일수록 높음
        - 해수면 상승: 해안 근접도
        - 폭염/혹한: 건물 특성 기반
        - 기타: 기본 근접도
        """
        if risk_type in ['river_flood', 'urban_flood']:
            # 침수 리스크: 지하층 있으면 근접도 증가
            floors_below = building_info.get('floors_below', 0) or 0
            floors_above = building_info.get('floors_above', 1) or 1

            if floors_below > 0:
                # 지하층 있으면 높은 근접도
                return min(1.0, 0.7 + (floors_below * 0.1))
            elif floors_above <= 3:
                # 저층 건물
                return 0.8
            else:
                # 고층 건물
                return 0.5

        elif risk_type == 'sea_level_rise':
            # 해수면 상승: 해안 근접도 (현재는 기본값)
            # TODO: 실제 해안선 거리 계산 필요
            return 0.6

        elif risk_type in ['extreme_heat', 'extreme_cold']:
            # 폭염/혹한: 건물 전체 영향
            return 0.9

        elif risk_type == 'typhoon':
            # 태풍: 고층 건물일수록 높음
            floors_above = building_info.get('floors_above', 1) or 1
            return min(1.0, 0.5 + (floors_above * 0.05))

        elif risk_type in ['wildfire', 'drought', 'water_stress']:
            # 산불, 가뭄, 물 부족: 중간 근접도
            return 0.6

        else:
            # 기본 근접도
            return 0.7
