'''
파일명: drought_hscore_agent.py
설명: 가뭄(Drought) 리스크 Hazard 점수(H) 산출 Agent
업데이트: HazardCalculator 로직 통합 (SPEI-12 기반)
'''
from typing import Dict, Any
from .base_hazard_hscore_agent import BaseHazardHScoreAgent
try:
    from modelops.config import hazard_config as config
except ImportError:
    # config 로드 실패 시 기본값 사용을 위해 try-except 처리
    config = None


class DroughtHScoreAgent(BaseHazardHScoreAgent):
    """
    가뭄(Drought) 리스크 Hazard 점수(H) 산출 Agent

    계산 방법론:
    - SPEI-12 (Standardized Precipitation Evapotranspiration Index) 기반
    - SPEI = (P - ET - μ) / σ
    - 범위: -3 to +3 (일반적), 낮을수록 가뭄 심각
    
    점수 변환 (Hazard Score):
    - SPEI 값을 0~1 Hazard Score로 역변환
    - SPEI ≤ -2.0 → Score 1.0 (Extreme)
    - SPEI ≥ 0.0 → Score 0.0 (Normal/Wet)
    """

    def __init__(self):
        super().__init__(risk_type='drought')

    def calculate_hazard(self, collected_data: Dict[str, Any]) -> float:
        """
        가뭄 Hazard 점수 계산

        Args:
            collected_data: 수집된 데이터 딕셔너리
                - climate_data: ClimateDataLoader 데이터 (spei12_index, annual_rainfall_mm 등)
                - spatial_data: SpatialDataLoader 데이터 (soil_moisture 등)

        Returns:
            Hazard 점수 (0.0 ~ 1.0)
        """
        climate_data = collected_data.get('climate_data', {})
        spatial_data = collected_data.get('spatial_data', {})

        # 데이터 부재 시 기본값
        if not climate_data:
            return 0.2  # 평년 수준

        try:
            # 1. 데이터 추출
            spei12 = climate_data.get('spei12_index')
            annual_rainfall = climate_data.get('annual_rainfall_mm', 1200.0)
            cdd = climate_data.get('consecutive_dry_days', 15)
            
            final_spei = 0.0
            
            # 2. SPEI-12 값 결정 (실제 데이터 vs Fallback 추정)
            if spei12 is not None:
                # KMA SPEI-12 데이터 사용
                final_spei = float(spei12)
                final_spei = max(-3.0, min(3.0, final_spei))
            else:
                # Fallback: 강수량 기반 SPI 추정
                # config에서 파라미터 로드
                if config and hasattr(config, 'DROUGHT_HAZARD_PARAMS'):
                    params = config.DROUGHT_HAZARD_PARAMS
                    korea_mean_rainfall = params.get('korea_mean_rainfall', 1300.0)
                    korea_std_rainfall = params.get('korea_std_rainfall', 300.0)
                    cdd_norm_avg = params.get('cdd_norm_avg', 10.0)
                    cdd_norm_std = params.get('cdd_norm_std', 10.0)
                else:
                    # 하드코딩된 기본값
                    korea_mean_rainfall = 1300.0
                    korea_std_rainfall = 300.0
                    cdd_norm_avg = 10.0
                    cdd_norm_std = 10.0

                # SPI 추정
                if korea_std_rainfall > 0:
                    spi_estimated = (annual_rainfall - korea_mean_rainfall) / korea_std_rainfall
                else:
                    spi_estimated = 0.0
                
                # CDD 정규화
                if cdd_norm_std > 0:
                    cdd_normalized = (cdd - cdd_norm_avg) / cdd_norm_std
                else:
                    cdd_normalized = 0.0
                
                # 가뭄 지수는 CDD가 길수록(-), 강수량이 적을수록(-) 심각해야 함
                # SPI는 양수면 습함, 음수면 건조
                # CDD 정규화값은 양수면 건조함. 따라서 부호 반대로 적용해야 SPI와 스케일 맞음
                # 복합 가뭄지수 = SPI(60%) - CDD_norm(40%)
                final_spei = (spi_estimated * 0.6) - (cdd_normalized * 0.4)
                final_spei = max(-3.0, min(3.0, final_spei))

            # 3. Hazard Score 변환 (0.0 ~ 1.0)
            # SPEI -2.5 이하일 때 1.0 (Extreme)
            # SPEI 0.0 이상일 때 0.0 (Normal)
            # 선형 변환: Score = -SPEI / 2.5
            if final_spei >= 0:
                hazard_score = 0.0
            else:
                hazard_score = min(1.0, -final_spei / 2.5)

            # 상세 결과 기록
            if 'calculation_details' not in collected_data:
                collected_data['calculation_details'] = {}
            
            collected_data['calculation_details']['drought'] = {
                'spei12': final_spei,
                'hazard_score_raw': hazard_score,
                'annual_rainfall': annual_rainfall,
                'cdd': cdd
            }

            return round(hazard_score, 4)

        except Exception as e:
            self.logger.error(f"Drought 계산 중 오류 발생: {e}")
            return 0.2