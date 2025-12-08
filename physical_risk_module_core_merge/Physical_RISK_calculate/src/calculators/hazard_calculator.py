#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Hazard Calculator (H)
위험 강도 계산: 그 지역에 얼마나 강한 재난이 발생하는가?
"""

from typing import Dict, Tuple
import os
import math
import requests
from ..data.building_data_fetcher import BuildingDataFetcher
from ..data.disaster_api_fetcher import DisasterAPIFetcher
from ..common import config

# dotenv 로드 시도 (선택사항)
try:
    from dotenv import load_dotenv
    DOTENV_AVAILABLE = True
except ImportError:
    DOTENV_AVAILABLE = False

# 실제 데이터 로더
try:
    from ..data.climate_data_loader import ClimateDataLoader
    CLIMATE_LOADER_AVAILABLE = True
except ImportError:
    CLIMATE_LOADER_AVAILABLE = False
    print("⚠️ [경고] climate_data_loader 모듈을 찾을 수 없습니다.")

try:
    from ..data.spatial_data_loader import SpatialDataLoader
    SPATIAL_LOADER_AVAILABLE = True
except ImportError:
    SPATIAL_LOADER_AVAILABLE = False
    print("⚠️ [경고] spatial_data_loader 모듈을 찾을 수 없습니다.")

# TCFD 개선 로직 모듈
try:
    from .fwi_calculator import FWICalculator
    FWI_AVAILABLE = True
except ImportError:
    FWI_AVAILABLE = False
    print("⚠️ [경고] fwi_calculator 모듈을 찾을 수 없습니다.")

try:
    from ..data.wamis_fetcher import WamisFetcher
    WAMIS_AVAILABLE = True
except ImportError:
    WAMIS_AVAILABLE = False
    print("⚠️ [경고] wamis_fetcher 모듈을 찾을 수 없습니다.")


class HazardCalculator:
    """
    위험 강도(Hazard) 계산기

    입력: 위/경도
    출력: 9개 물리적 리스크별 Hazard 강도

    Hazard 정의:
    - 그 지역에 재난이 얼마나 자주, 강하게 발생하는가?
    - 기후 시나리오, 재난 이력, 지형 분석 기반

    데이터 소스:
    - KMA SSP 시나리오: 기후변화 시나리오 (2021-2100)
    - 토지피복도: 환경부 중분류
    - NDVI: MODIS 위성 식생지수
    - 토양수분: SMAP L4
    - 재난 이력: 재난안전데이터 API
    """

    def __init__(self, scenario: str = 'SSP245', target_year: int = 2030):
        """
        Args:
            scenario: SSP 시나리오 (SSP126, SSP245, SSP370, SSP585)
            target_year: 분석 연도 (2021-2100)
        """
        # 환경변수 로드
        env_path = os.path.join(os.path.dirname(__file__), '..', '.env')
        if DOTENV_AVAILABLE:
            load_dotenv(env_path)
        else:
            # 수동으로 .env 파일 로드
            self._load_env_file(env_path)

        self.building_fetcher = BuildingDataFetcher()
        self.disaster_fetcher = DisasterAPIFetcher()

        # 태풍 API 설정
        self.kma_api_key = os.getenv("KMA_API_KEY")
        self.typhoon_api_base_url = "https://apihub.kma.go.kr/api/typ01/url/typ_besttrack.php"

        # 실제 데이터 로더 초기화
        self.scenario = scenario
        self.target_year = target_year

        if CLIMATE_LOADER_AVAILABLE:
            self.climate_loader = ClimateDataLoader(scenario=scenario)
        else:
            self.climate_loader = None

        if SPATIAL_LOADER_AVAILABLE:
            self.spatial_loader = SpatialDataLoader()
        else:
            self.spatial_loader = None

        # TCFD 개선 로직 모듈 초기화
        if FWI_AVAILABLE:
            self.fwi_calculator = FWICalculator()
        else:
            self.fwi_calculator = None

        if WAMIS_AVAILABLE:
            self.wamis_fetcher = WamisFetcher()
        else:
            self.wamis_fetcher = None

    def _load_env_file(self, env_path: str):
        """
        .env 파일 수동 로드 (dotenv 없을 때)
        """
        try:
            if os.path.exists(env_path):
                with open(env_path, 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith('#'):
                            if '=' in line:
                                key, value = line.split('=', 1)
                                os.environ[key.strip()] = value.strip()
        except Exception as e:
            print(f"⚠️ .env 파일 로드 실패: {e}")

    def calculate(self, lat: float, lon: float) -> Dict:
        """
        위/경도 → 9개 리스크별 Hazard 강도

        Args:
            lat: 위도
            lon: 경도

        Returns:
            Hazard 강도 딕셔너리
        """
        print(f"\n{'='*80}")
        print(f"[Hazard Calculator] 위험 강도 계산")
        print(f"{'='*80}")
        print(f"위치: ({lat}, {lon})")

        # 기초 데이터 수집
        building_data = self.building_fetcher.fetch_all_building_data(lat, lon)

        # 9개 리스크별 Hazard 계산
        hazard = {
            'extreme_heat': self._calculate_heat_hazard(lat, lon, building_data),
            'extreme_cold': self._calculate_cold_hazard(lat, lon, building_data),
            'drought': self._calculate_drought_hazard(lat, lon, building_data),
            'river_flood': self._calculate_river_flood_hazard(lat, lon, building_data),
            'urban_flood': self._calculate_urban_flood_hazard(lat, lon, building_data),
            'sea_level_rise': self._calculate_sea_level_rise_hazard(lat, lon, building_data),
            'typhoon': self._calculate_typhoon_hazard(lat, lon, building_data),
            'wildfire': self._calculate_wildfire_hazard(lat, lon, building_data),
            'water_stress': self._calculate_water_stress_hazard(lat, lon, building_data),
        }

        print(f"\n✅ Hazard 계산 완료")
        self._print_summary(hazard)

        return hazard

    # ========================================================================
    # 1. 극심한 고온 (Extreme Heat)
    # ========================================================================

    def _calculate_heat_hazard(self, lat: float, lon: float, data: Dict) -> Dict:
        """
        극심한 고온 Hazard - HCI (Heat Compound Index) 기반

        근거:
        - 워드 문서: 물리적 리스크 스코어링 로직 정의 v0.3
        - IPCC AR6 + TCFD 공식 지표 (ETCCDI)
        - 기상청 KMA SSP 1km 격자 시나리오

        HCI 공식: 4개 ETCCDI 지표의 가중평균
        HCI = 0.3×(SU25/100) + 0.3×(WSDI/30) + 0.2×(TR25/50) + 0.2×(TX90P/100)

        분류 기준:
        - HCI > 0.8: 극심함 (Extreme)
        - HCI > 0.6: 매우 높음 (Very High)
        - HCI > 0.4: 높음 (High)
        - HCI > 0.2: 보통 (Moderate)
        - HCI ≤ 0.2: 낮음 (Low)
        """
        try:
            if self.climate_loader:
                heat_data = self.climate_loader.get_extreme_heat_data(lat, lon, self.target_year)

                # Step 1: ETCCDI 지표 추출
                su25 = heat_data['heatwave_days_per_year']      # 폭염일수 (≥33°C)
                wsdi = heat_data['heat_wave_duration']           # 폭염 지속일수
                tr25 = heat_data['tropical_nights']              # 열대야일수 (≥25°C)
                tx90p = su25  # TX90P ≈ SU25 (근사값)

                # Step 2: 절대값 기준 정규화 (0~1)
                su25_norm = min(su25 / 100.0, 1.0)
                wsdi_norm = min(wsdi / 30.0, 1.0)
                tr25_norm = min(tr25 / 50.0, 1.0)
                tx90p_norm = min(tx90p / 100.0, 1.0)

                # Step 3: HCI 계산 (가중평균)
                hci = 0.3 * su25_norm + 0.3 * wsdi_norm + 0.2 * tr25_norm + 0.2 * tx90p_norm

                # Step 4: 등급 분류
                if hci > 0.8:
                    intensity = 'extreme'
                elif hci > 0.6:
                    intensity = 'very_high'
                elif hci > 0.4:
                    intensity = 'high'
                elif hci > 0.2:
                    intensity = 'moderate'
                else:
                    intensity = 'low'

                return {
                    'hci_index': hci,
                    'annual_max_temp_celsius': heat_data['annual_max_temp_celsius'],
                    'heatwave_days_per_year': su25,
                    'heat_wave_duration': wsdi,
                    'tropical_nights': tr25,
                    'etccdi_normalized': {
                        'su25_norm': su25_norm,
                        'wsdi_norm': wsdi_norm,
                        'tr25_norm': tr25_norm,
                        'tx90p_norm': tx90p_norm,
                    },
                    'heatwave_intensity': intensity,
                    'climate_scenario': self.scenario,
                    'trend': 'increasing',
                    'year': self.target_year,
                    'data_source': heat_data['data_source'],
                    'note': f'HCI {hci:.3f} (ETCCDI 가중평균: SU25 30% + WSDI 30% + TR25 20% + TX90P 20%)',
                }
            else:
                # Fallback: 전국 평균값
                hci = 0.4  # 한반도 평년 수준
                return {
                    'hci_index': hci,
                    'annual_max_temp_celsius': 38.5,
                    'heatwave_days_per_year': 25,
                    'heat_wave_duration': 10,
                    'tropical_nights': 15,
                    'heatwave_intensity': 'high',
                    'climate_scenario': self.scenario,
                    'trend': 'increasing',
                    'year': self.target_year,
                    'data_source': 'fallback (KMA SSP 전국 평균)',
                    'note': 'HCI 0.4 (fallback)',
                }
        except Exception as e:
            print(f"⚠️ [TCFD 경고] 극심한 고온 데이터 조회 실패: {e}")
            hci = 0.4
            return {
                'hci_index': hci,
                'annual_max_temp_celsius': 38.5,
                'heatwave_days_per_year': 25,
                'heat_wave_duration': 10,
                'tropical_nights': 15,
                'heatwave_intensity': 'high',
                'climate_scenario': self.scenario,
                'trend': 'increasing',
                'year': self.target_year,
                'data_source': 'fallback (에러)',
                'note': 'HCI 0.4 (fallback)',
            }

    # ========================================================================
    # 2. 극심한 극심한 한파 (Extreme Cold)
    # ========================================================================

    def _calculate_cold_hazard(self, lat: float, lon: float, data: Dict) -> Dict:
        """
        극심한 한파 Hazard - CCI (Cold Compound Index) 기반

        근거:
        - 워드 문서: 물리적 리스크 스코어링 로직 정의 v0.3
        - IPCC AR6 + TCFD 공식 지표 (ETCCDI)
        - 기상청 KMA SSP 1km 격자 시나리오

        CCI 공식: 4개 ETCCDI 지표의 가중평균 (Heat과 동일 구조)
        CCI = 0.3×(TX10p/30) + 0.3×(CSIx/20) + 0.2×(FD/50) + 0.2×(절대최저/20)

        분류 기준:
        - CCI > 0.8: 극심함 (Extreme)
        - CCI > 0.6: 매우 높음 (Very High)
        - CCI > 0.4: 높음 (High)
        - CCI > 0.2: 보통 (Moderate)
        - CCI ≤ 0.2: 낮음 (Low)
        """
        try:
            if self.climate_loader:
                cold_data = self.climate_loader.get_extreme_cold_data(lat, lon, self.target_year)

                # Step 1: ETCCDI 지표 추출
                tx10p = cold_data['coldwave_days_per_year']      # 한파일수 (≤절대최저 10백분위수)
                csix = cold_data['cold_wave_duration']           # 한파 지속일수
                fd = cold_data['ice_days']                       # 서리일 또는 결빙일
                tn_abs = abs(cold_data['annual_min_temp_celsius'])  # 절대최저기온

                # Step 2: 절대값 기준 정규화 (0~1)
                tx10p_norm = min(tx10p / 30.0, 1.0)
                csix_norm = min(csix / 20.0, 1.0)
                fd_norm = min(fd / 50.0, 1.0)
                tn_norm = min(tn_abs / 20.0, 1.0)

                # Step 3: CCI 계산 (가중평균)
                cci = 0.3 * tx10p_norm + 0.3 * csix_norm + 0.2 * fd_norm + 0.2 * tn_norm

                # Step 4: 등급 분류
                if cci > 0.8:
                    intensity = 'extreme'
                elif cci > 0.6:
                    intensity = 'very_high'
                elif cci > 0.4:
                    intensity = 'high'
                elif cci > 0.2:
                    intensity = 'moderate'
                else:
                    intensity = 'low'

                return {
                    'cci_index': cci,
                    'annual_min_temp_celsius': cold_data['annual_min_temp_celsius'],
                    'coldwave_days_per_year': tx10p,
                    'cold_wave_duration': csix,
                    'ice_days': fd,
                    'etccdi_normalized': {
                        'tx10p_norm': tx10p_norm,
                        'csix_norm': csix_norm,
                        'fd_norm': fd_norm,
                        'tn_norm': tn_norm,
                    },
                    'coldwave_intensity': intensity,
                    'climate_scenario': self.scenario,
                    'trend': 'decreasing',
                    'year': self.target_year,
                    'data_source': cold_data['data_source'],
                    'note': f'CCI {cci:.3f} (ETCCDI 가중평균: TX10p 30% + CSIx 30% + FD 20% + Tn절대값 20%)',
                }
            else:
                # Fallback: 전국 평균값
                cci = 0.35  # 한반도 평년 수준
                return {
                    'cci_index': cci,
                    'annual_min_temp_celsius': -15.0,
                    'coldwave_days_per_year': 10,
                    'cold_wave_duration': 8,
                    'ice_days': 5,
                    'coldwave_intensity': 'moderate',
                    'climate_scenario': self.scenario,
                    'trend': 'decreasing',
                    'year': self.target_year,
                    'data_source': 'fallback (KMA SSP 전국 평균)',
                    'note': 'CCI 0.35 (fallback)',
                }
        except Exception as e:
            print(f"⚠️ [TCFD 경고] 극심한 한파 데이터 조회 실패: {e}")
            cci = 0.35
            return {
                'cci_index': cci,
                'annual_min_temp_celsius': -15.0,
                'coldwave_days_per_year': 10,
                'cold_wave_duration': 8,
                'ice_days': 5,
                'coldwave_intensity': 'moderate',
                'climate_scenario': self.scenario,
                'trend': 'decreasing',
                'year': self.target_year,
                'data_source': 'fallback (에러)',
                'note': 'CCI 0.35 (fallback)',
            }

    # ========================================================================
    # 3. 가뭄 (Drought)
    # ========================================================================

    def _calculate_drought_hazard(self, lat: float, lon: float, data: Dict) -> Dict:
        """
        가뭄 Hazard - SPEI-12 (Standardized Precipitation Evapotranspiration Index) 기반

        근거:
        - SPEI-12: Vicente-Serrano et al. (2010) - 기후변화 시나리오에 적합
        - KMA SSP 기후 시나리오 데이터 (2021-2100)
        - IPCC AR6 drought assessment methodology
        - 한국 가뭄 평가 기준 (기상청, 수자원위원회)

        SPEI (Standardized Precipitation Evapotranspiration Index):
        - 강수량 + 증발산량을 고려한 표준정규분포 변환
        - SPEI = (P - ET - μ) / σ (P: 강수량, ET: 증발산량, μ: 평균, σ: 표준편차)
        - 범위: -3 to +3 (일반적으로)
        - SPI보다 기후변화 영향(온도 상승, 증발산량 증가) 반영에 우수

        SPEI-12 해석 기준 (12개월 누적, 장기 가뭄 평가):
        - SPEI ≥ 2.0: 매우 습함 (극히 드문)
        - 1.5 to 2.0: 습함
        - 1.0 to 1.5: 약간 습함
        - -0.5 to 1.0: 정상
        - -1.0 to -0.5: 약간 건조
        - -1.5 to -1.0: 건조 (가뭄 시작)
        - -2.0 to -1.5: 심한 가뭄
        - < -2.0: 극심한 가뭄 (매우 드문)
        """
        try:
            if self.climate_loader:
                drought_data = self.climate_loader.get_drought_data(lat, lon, self.target_year)

                # 토양수분 데이터 추가
                if self.spatial_loader:
                    soil_data = self.spatial_loader.get_soil_moisture_data(lat, lon)
                    drought_indicator = soil_data['drought_indicator']
                    soil_moisture = soil_data['soil_moisture']
                else:
                    drought_indicator = 'normal'
                    soil_moisture = 0.2

                # Step 1: SPEI-12 데이터 추출 (KMA 제공 데이터)
                spei12 = drought_data.get('spei12_index')
                annual_rainfall = drought_data['annual_rainfall_mm']
                cdd = drought_data['consecutive_dry_days']

                # Step 2: SPEI-12 사용 또는 Fallback
                if spei12 is not None:
                    # KMA SPEI-12 데이터 사용 (최선)
                    final_spei = float(spei12)
                    final_spei = max(-3.0, min(3.0, final_spei))  # -3 to +3 범위
                    data_source_type = 'KMA_SPEI12'
                else:
                    # Fallback: 강수량 기반 SPI 추정 (차선)
                    params = config.DROUGHT_HAZARD_PARAMS
                    korea_mean_rainfall = params['korea_mean_rainfall']
                    korea_std_rainfall = params['korea_std_rainfall']
                    spi_estimated = (annual_rainfall - korea_mean_rainfall) / korea_std_rainfall

                    # CDD 정규화 (한반도 평균 10일, 극한 40일)
                    cdd_normalized = (cdd - params['cdd_norm_avg']) / params['cdd_norm_std']

                    # 복합 가뭄지수 (강수 60%, CDD 40%)
                    final_spei = (spi_estimated * 0.6) + (cdd_normalized * 0.4)
                    final_spei = max(-3.0, min(3.0, final_spei))
                    data_source_type = 'SPI_fallback'

                # Step 3: 가뭄 심도 분류 (SPEI 기준, SPI와 동일)
                if final_spei < -2.0:
                    drought_severity = 'extreme'      # 극심한 가뭄
                    drought_frequency = 0.02  # 매우 드문: 50년 1회
                elif final_spei < -1.5:
                    drought_severity = 'severe'       # 심한 가뭄
                    drought_frequency = 0.05  # 드문: 20년 1회
                elif final_spei < -1.0:
                    drought_severity = 'moderate'     # 중간 가뭄
                    drought_frequency = 0.10  # 10년 1회
                elif final_spei < -0.5:
                    drought_severity = 'mild'        # 경미한 가뭄
                    drought_frequency = 0.15  # 약 7년 1회
                elif final_spei < 1.0:
                    drought_severity = 'normal'       # 정상
                    drought_frequency = 0.01  # 매우 드문
                else:
                    drought_severity = 'wet'         # 습함 (가뭄 아님)
                    drought_frequency = 0.01

                return {
                    'annual_rainfall_mm': annual_rainfall,
                    'consecutive_dry_days': cdd,
                    'rainfall_intensity': drought_data['rainfall_intensity'],
                    'soil_moisture': soil_moisture,
                    'drought_indicator': drought_indicator,
                    'spei12_index': final_spei,
                    'drought_severity': drought_severity,
                    'drought_frequency': drought_frequency,
                    'drought_duration_months': max(1, int(cdd / 30)),
                    'trend': 'stable',
                    'climate_scenario': self.scenario,
                    'year': self.target_year,
                    'data_source': f'KMA SPEI-12 (Vicente-Serrano 2010) + SMAP soil ({data_source_type})',
                    'note': 'SPEI-12 < -2.0: 극심한 가뭄 | -1.5~-2.0: 심한 | -1.0~-1.5: 중간 | -0.5~-1.0: 경미 | -0.5~1.0: 정상',
                }
            else:
                # Fallback: 통계 기반
                return {
                    'annual_rainfall_mm': 1200,
                    'consecutive_dry_days': 15,
                    'rainfall_intensity': 10.0,
                    'soil_moisture': 0.2,
                    'drought_indicator': 'normal',
                    'spei12_index': 0.0,  # 정상값
                    'drought_severity': 'normal',
                    'drought_frequency': 0.01,
                    'drought_duration_months': 0,
                    'trend': 'stable',
                    'climate_scenario': self.scenario,
                    'year': self.target_year,
                    'data_source': 'SPEI-12 (fallback: national average)',
                    'note': '실제 데이터 조회 실패 - 전국 평균값 사용',
                }
        except Exception as e:
            print(f"⚠️ [TCFD 경고] 가뭄 데이터 조회 실패: {e}")
            # Fallback
            return {
                'annual_rainfall_mm': 1200,
                'consecutive_dry_days': 15,
                'rainfall_intensity': 10.0,
                'soil_moisture': 0.2,
                'drought_indicator': 'normal',
                'spei12_index': 0.0,
                'drought_severity': 'normal',
                'drought_frequency': 0.01,
                'drought_duration_months': 0,
                'trend': 'stable',
                'climate_scenario': self.scenario,
                'year': self.target_year,
                'data_source': 'SPEI-12 (fallback)',
                'note': '오류 발생 - 전국 평균값 사용',
            }

    # ========================================================================
    # 4. 하천 홍수 (River Flood)
    # ========================================================================

    def _calculate_twi(self, lat: float, lon: float) -> float:
        """
        TWI (Topographic Wetness Index) 계산
        TWI = ln(A / tan(β))
        A: 상위 유역면적, β: 경사도 (토지피복도와 위치 기반 추정)

        반환: TWI 값 (0~15 일반적 범위)

        근거: USGS Topographic Wetness Index 표준
        """
        try:
            # 토지피복도 기반 지형 특성 추정
            if self.spatial_loader:
                landcover = self.spatial_loader.get_landcover_data(lat, lon)
                landcover_type = landcover.get('landcover_type', 'urban')

                # 토지피복도에 따른 기본 TWI 값 (경험적 추정)
                # 산림/초지: 높은 토양포화도 → 높은 TWI
                # 도시: 포장도로 많음 → 낮은 TWI
                # 농지: 중간 수준
                if landcover_type == 'forest':
                    twi = 10.5  # 산림: 높은 습도
                elif landcover_type == 'grassland':
                    twi = 9.0   # 초지: 중간~높은 습도
                elif landcover_type == 'agricultural':
                    twi = 7.5   # 농지: 중간 습도
                elif landcover_type == 'water':
                    twi = 14.0  # 수역: 최고 습도
                else:
                    twi = 6.5   # 도시/포장지: 낮은 습도

                return twi
            else:
                # Fallback: 기본 TWI 값 (중간 취약도)
                return 7.0
        except Exception as e:
            # 에러 발생 시 기본값 사용 (경고 메시지 없음 - 이미 테스트에서 경고함)
            return 7.0

    def _calculate_river_flood_hazard(self, lat: float, lon: float, data: Dict) -> Dict:
        """
        하천 홍수 Hazard - TWI (지형 취약도) + 강수량 기반

        Hazard Score = 0.4 × TWI_score + 0.6 × 강수_score
        과학적 근거: USGS 표준 지형 지수, 수문학 표준 (Beven & Kirkby 1979)
        """
        try:
            # 재난 API에서 하천 정보 가져오기
            try:
                river_info = self.disaster_fetcher.get_nearest_river_info(lat, lon)
                river_name = river_info.get('river_name', '알수없음')
                river_grade = river_info.get('river_grade', 3)
                watershed_area = river_info.get('watershed_area_km2', 2500)
            except:
                river_name = data.get('river_name', '알수없음')
                river_grade = 3
                watershed_area = data.get('watershed_area_km2', 2500)

            # Step 1: TWI 기반 지형 취약도 계산
            twi = self._calculate_twi(lat, lon)

            # TWI를 0-1 점수로 정규화
            # TWI > 10: 매우 높은 홍수위험 (0.9)
            # TWI 7-10: 높은 홍수위험 (0.6-0.9)
            # TWI 5-7: 중간 홍수위험 (0.3-0.6)
            # TWI < 5: 낮은 홍수위험 (0-0.3)
            if twi > 10:
                twi_score = 0.9
            elif twi > 7:
                twi_score = 0.5 + (twi - 7) / 6  # 0.5 ~ 0.9
            else:
                twi_score = twi / 20  # 0 ~ 0.35

            # Step 2: 강수량 기반 홍수 빈도
            if self.climate_loader:
                flood_data = self.climate_loader.get_flood_data(lat, lon, self.target_year)
                extreme_rainfall = flood_data['max_1day_rainfall_mm']
                heavy_rain_days = flood_data['heavy_rain_days']

                # 강수량을 0-1 점수로 정규화
                # > 300mm: 0.9 (극한 강수)
                # 200-300mm: 0.6-0.9
                # 100-200mm: 0.3-0.6
                # < 100mm: 0-0.3
                if extreme_rainfall > 300:
                    rainfall_score = 0.9
                elif extreme_rainfall > 200:
                    rainfall_score = 0.5 + (extreme_rainfall - 200) / 200
                else:
                    rainfall_score = extreme_rainfall / 300

                data_source = flood_data['data_source']
            else:
                extreme_rainfall = 250
                heavy_rain_days = 5
                rainfall_score = 0.7
                data_source = 'fallback'

            # Step 3: 결합 점수 (TWI 40% + 강수 60%)
            hazard_score = (twi_score * 0.4) + (rainfall_score * 0.6)

            # 홍수 빈도 (점수 → 확률)
            # 0.0-0.2: 0.01 (100년 1회)
            # 0.2-0.4: 0.02 (50년 1회)
            # 0.4-0.6: 0.05 (20년 1회)
            # 0.6-0.8: 0.1 (10년 1회)
            # > 0.8: 0.2 (5년 1회)
            if hazard_score > 0.8:
                flood_frequency = 0.2
            elif hazard_score > 0.6:
                flood_frequency = 0.1
            elif hazard_score > 0.4:
                flood_frequency = 0.05
            elif hazard_score > 0.2:
                flood_frequency = 0.02
            else:
                flood_frequency = 0.01

            return {
                'hazard_score': min(hazard_score, 1.0),
                'twi': twi,
                'twi_score': twi_score,
                'extreme_rainfall_1day_mm': extreme_rainfall,
                'rainfall_score': rainfall_score,
                'heavy_rain_days': heavy_rain_days,
                'flood_frequency': flood_frequency,
                'river_name': river_name,
                'river_grade': river_grade,
                'watershed_area_km2': watershed_area,
                'stream_order': data.get('stream_order', 3),
                'historical_flood_count': data.get('flood_history_count', 0),
                'climate_scenario': self.scenario,
                'year': self.target_year,
                'data_source': f'TWI (DEM) + KMA {data_source}',
                'note': f'TWI 기반 지형 취약도(0.4 가중) + 강수량(0.6 가중) = 복합 홍수 위험도',
            }
        except Exception as e:
            print(f"⚠️ [TCFD 경고] 하천 홍수 데이터 조회 실패: {e}")
            return {
                'hazard_score': 0.5,
                'twi': 7.0,
                'twi_score': 0.35,
                'extreme_rainfall_1day_mm': 250,
                'rainfall_score': 0.7,
                'heavy_rain_days': 5,
                'flood_frequency': 0.05,
                'river_name': '알수없음',
                'river_grade': 3,
                'watershed_area_km2': 2500,
                'historical_flood_count': 0,
                'climate_scenario': self.scenario,
                'year': self.target_year,
                'data_source': 'fallback (TWI + rainfall)',
                'note': '데이터 조회 실패 - 기본값 사용',
            }

    # ========================================================================
    # 5. 도시 홍수 (Urban Flood)
    # ========================================================================

    def _calculate_urban_flood_hazard(self, lat: float, lon: float, data: Dict) -> Dict:
        """
        도시 홍수 Hazard - 토지피복도 + 건물밀도 + 강수량 기반

        Hazard Score = 0.5 × 배수능력_점수 + 0.5 × 강수_초과량_점수
        과학적 근거: 도시수문학 표준 (투수율 기반), 건물밀도-배수망 연관성
        """
        try:
            # Step 1: 토지피복도 기반 배수능력 추정
            if self.spatial_loader:
                landcover = self.spatial_loader.get_landcover_data(lat, lon)
                impervious_ratio = landcover['impervious_ratio']
                landcover_type = landcover.get('landcover_type', 'urban')  # urban/forest/agricultural/water
            else:
                impervious_ratio = 0.7
                landcover_type = 'urban'

            # 토지피복도 기반 배수능력 (mm/hr)
            # 근거: 도시지역 투수율 차이에 의한 우수 배제 능력
            if landcover_type == 'water':
                drainage_capacity = 0  # 수역 - 침수
            elif landcover_type == 'forest':
                drainage_capacity = 8  # 산림 - 높은 침투율
            elif landcover_type == 'agricultural':
                drainage_capacity = 15  # 농경지
            elif impervious_ratio > 0.75:
                drainage_capacity = 75  # 고밀도 상업지역 (포장률 75% 이상)
            elif impervious_ratio > 0.6:
                drainage_capacity = 55  # 중밀도 주거지역 (포장률 60~75%)
            else:
                drainage_capacity = 40  # 저밀도 주거/농촌

            # Step 2: 건물밀도 기반 배수망 발달도 보정
            # 근거: 건물이 많을수록 배수관거 발달 가능성 높음 (중국 도시연구 2023)
            try:
                building_count = data.get('building_count', 100)
                area_km2 = data.get('area_km2', 1.0)
                building_density = building_count / max(area_km2, 0.1)  # 건물/km²

                # 건물 밀도 보정계수 (0.7 ~ 1.0)
                # 건물 밀도 > 1000개/km²: 1.0 (우수망 잘 발달)
                # 건물 밀도 500-1000: 0.9
                # 건물 밀도 100-500: 0.8
                # 건물 밀도 < 100: 0.7
                if building_density > 1000:
                    drainage_correction = 1.0
                elif building_density > 500:
                    drainage_correction = 0.9
                elif building_density > 100:
                    drainage_correction = 0.8
                else:
                    drainage_correction = 0.7

                effective_drainage = drainage_capacity * drainage_correction
            except:
                effective_drainage = drainage_capacity * 0.8

            # Step 3: 강수량 기반 침수 위험
            if self.climate_loader:
                flood_data = self.climate_loader.get_flood_data(lat, lon, self.target_year)
                extreme_rainfall_1day = flood_data['max_1day_rainfall_mm']
                heavy_rain_days = flood_data['heavy_rain_days']

                # 1시간 강수량 추정 (1일 강수량 / 12)
                extreme_rainfall_1hr = extreme_rainfall_1day / 12

                # 강수 초과량 = 강수량 - 배수능력
                # 양수면 침수 가능성 있음
                rainfall_excess = extreme_rainfall_1hr - effective_drainage

                # 강수 초과량을 0-1 점수로 정규화
                # 초과량 > 30mm: 0.9 (심각한 침수)
                # 초과량 15-30mm: 0.5-0.9
                # 초과량 0-15mm: 0-0.5
                # 초과량 < 0: 0 (배수 충분)
                if rainfall_excess < 0:
                    rainfall_excess_score = 0
                elif rainfall_excess > 30:
                    rainfall_excess_score = 0.9
                else:
                    rainfall_excess_score = rainfall_excess / 30 * 0.9

                data_source = flood_data['data_source']
            else:
                extreme_rainfall_1day = 100
                heavy_rain_days = 5
                extreme_rainfall_1hr = extreme_rainfall_1day / 12
                rainfall_excess = max(extreme_rainfall_1hr - effective_drainage, 0)
                rainfall_excess_score = min(rainfall_excess / 30 * 0.9, 0.9)
                data_source = 'fallback'

            # Step 4: 배수능력 점수화 (정규화)
            # effective_drainage 0~100mm/hr → 0~1 점수
            drainage_score = min(1.0, effective_drainage / 80)  # 80mm/hr = 완벽한 배수

            # Step 5: 결합 점수 (배수능력 50% + 강수 초과량 50%)
            hazard_score = (1 - drainage_score) * 0.5 + rainfall_excess_score * 0.5

            # 홍수 빈도 (점수 → 확률)
            if hazard_score > 0.8:
                flood_frequency = 0.15
            elif hazard_score > 0.6:
                flood_frequency = 0.1
            elif hazard_score > 0.4:
                flood_frequency = 0.05
            elif hazard_score > 0.2:
                flood_frequency = 0.02
            else:
                flood_frequency = 0.01

            return {
                'hazard_score': min(hazard_score, 1.0),
                'drainage_capacity_mm_hr': drainage_capacity,
                'drainage_correction': drainage_correction if 'drainage_correction' in locals() else 0.8,
                'effective_drainage_mm_hr': effective_drainage,
                'drainage_score': drainage_score,
                'extreme_rainfall_1day_mm': extreme_rainfall_1day,
                'extreme_rainfall_1hr_mm': extreme_rainfall_1hr,
                'rainfall_excess_mm': max(rainfall_excess, 0),
                'rainfall_excess_score': rainfall_excess_score,
                'heavy_rain_days': heavy_rain_days,
                'impervious_surface_ratio': impervious_ratio,
                'landcover_type': landcover_type,
                'building_density': building_density if 'building_density' in locals() else 0,
                'flood_frequency': flood_frequency,
                'historical_flood_count': data.get('flood_history_count', 0),
                'climate_scenario': self.scenario,
                'year': self.target_year,
                'data_source': f'토지피복도 + 건물밀도 + KMA {data_source}',
                'note': f'배수능력 점수(50%) + 강수 초과량(50%) = 도시 침수 위험도',
            }
        except Exception as e:
            print(f"⚠️ [TCFD 경고] 도시 홍수 데이터 조회 실패: {e}")
            return {
                'hazard_score': 0.5,
                'drainage_capacity_mm_hr': 50,
                'drainage_correction': 0.8,
                'effective_drainage_mm_hr': 40,
                'drainage_score': 0.5,
                'extreme_rainfall_1day_mm': 100,
                'extreme_rainfall_1hr_mm': 8,
                'rainfall_excess_mm': 0,
                'rainfall_excess_score': 0.5,
                'heavy_rain_days': 5,
                'impervious_surface_ratio': 0.7,
                'landcover_type': 'urban',
                'building_density': 500,
                'flood_frequency': 0.05,
                'historical_flood_count': 0,
                'climate_scenario': self.scenario,
                'year': self.target_year,
                'data_source': 'fallback (landcover + building + rainfall)',
                'note': '데이터 조회 실패 - 기본값 사용',
            }

    # ========================================================================
    # 6. 해수면 상승 (Sea Level Rise) - CMIP6 SSP 시나리오 기반
    # ========================================================================

    def _calculate_sea_level_rise_hazard(self, lat: float, lon: float, data: Dict) -> Dict:
        """
        해수면 상승 Hazard 계산 - KMA CMIP6 SSP 시나리오 기반

        데이터 소스:
        - climate_data_loader.get_sea_level_rise_data()
        - NetCDF 파일: data/sea_level_rise/ssp*_slr_annual_mean_2015-2100.nc

        내륙 지역 처리:
        - 해안 10km 이상: slr_cm = 0.0 (영향 없음)
        - 해안 10km 이내: 실제 CMIP6 데이터 값
        """
        distance_to_coast = data.get('distance_to_coast_m', 50000)

        # Step 1: 해안 노출도 판단
        coastal_exposure = distance_to_coast < 10000  # 10km 이내

        if not coastal_exposure:
            # 내륙 지역: 해수면 상승 영향 없음
            return {
                'slr_m': 0.0,
                'slr_cm': 0.0,
                'sea_level_rise_cm': 0.0,
                'storm_surge_height_m': 0.0,
                'coastal_exposure': False,
                'flood_frequency': 0.0,
                'data_source': 'CMIP6 SSP (내륙 지역)',
                'note': '내륙 지역 - 해수면 상승 영향 없음'
            }

        # Step 2: 해안 지역 - 실제 CMIP6 데이터 호출
        try:
            if self.climate_loader:
                # KMA CMIP6 SSP 시나리오 데이터 조회
                slr_data = self.climate_loader.get_sea_level_rise_data(
                    lat=lat,
                    lon=lon,
                    year=self.target_year
                )

                # 응답 데이터 구조
                slr_cm = slr_data.get('slr_increase_cm', 0.0)

                # 해수면 상승량 → 폭풍 해일 높이 추정 (경험식)
                # 기준: FEMA 및 IPCC AR6
                if slr_cm >= 0:
                    storm_surge = 0.5 + (slr_cm / 100) * 2.0  # 선형 추정
                else:
                    storm_surge = 0.5  # 최소값

                # Hazard 강도 분류
                if slr_cm >= 100:
                    flood_frequency = 0.5  # 2년 1회 이상
                elif slr_cm >= 50:
                    flood_frequency = 0.1  # 10년 1회
                else:
                    flood_frequency = 0.02  # 50년 1회

                return {
                    'slr_m': slr_data.get('slr_m', 0.0),
                    'slr_cm': slr_cm,
                    'sea_level_rise_cm': slr_cm,
                    'storm_surge_height_m': min(storm_surge, 5.0),  # 최대 5m
                    'coastal_exposure': True,
                    'flood_frequency': flood_frequency,
                    'baseline_year': slr_data.get('baseline_year', 2015),
                    'data_source': slr_data.get('data_source', 'CMIP6 SSP'),
                }
            else:
                # climate_loader 없을 경우 fallback
                raise ValueError("climate_loader not initialized")

        except Exception as e:
            print(f"⚠️ [TCFD 경고] 해수면 상승 데이터 조회 실패: {e}")
            # Fallback: IPCC AR6 평균값
            return {
                'slr_m': 0.3,
                'slr_cm': 30,
                'sea_level_rise_cm': 30,
                'storm_surge_height_m': 1.5,
                'coastal_exposure': True,
                'flood_frequency': 0.02,
                'data_source': 'CMIP6 SSP (fallback)',
                'note': f'데이터 조회 실패 - IPCC AR6 평균값 사용'
            }

    # ========================================================================
    # 7. 태풍 (Typhoon) - KMA BestTrack API 연동
    # ========================================================================

    def _fetch_typhoon_besttrack(self, year: int) -> Dict:
        """
        기상청 태풍 베스트트랙 API에서 특정 년도의 모든 태풍 데이터 조회

        Args:
            year: 조회 연도 (2015-2022)

        Returns:
            {'typhoons': [...], 'data_source': 'kma_besttrack' or 'fallback'}
        """
        try:
            if not self.kma_api_key:
                print("⚠️ [TCFD 경고] KMA_API_KEY가 설정되지 않았습니다.")
                return {'typhoons': [], 'data_source': 'fallback'}

            # 모든 태풍 등급 조회 (TY: 태풍만 조회하면 부족하므로 전체 조회)
            params = {
                'year': str(year),
                'help': '2',  # 값만 표시 (더 빠른 응답)
                'authKey': self.kma_api_key
            }

            response = requests.get(self.typhoon_api_base_url, params=params, timeout=30)

            if response.status_code == 200:
                # 응답 데이터 파싱 (공백으로 구분된 텍스트)
                typhoons = []
                lines = response.text.strip().split('\n')

                # 주석(#)이 아닌 라인만 처리
                for line in lines:
                    if line and not line.startswith('#'):
                        fields = line.split()
                        if len(fields) >= 10:
                            typhoons.append({
                                'grade': fields[0],        # 태풍 등급
                                'tcid': fields[1],         # 태풍호수
                                'year': int(fields[2]),
                                'month': int(fields[3]),
                                'day': int(fields[4]),
                                'hour': int(fields[5]),
                                'lon': float(fields[6]),   # 경도
                                'lat': float(fields[7]),   # 위도
                                'max_wind_speed': int(fields[8]),  # 중심최대풍속 (m/s)
                                'central_pressure': int(fields[9]),  # 중심기압 (hPa)
                            })

                return {'typhoons': typhoons, 'data_source': 'kma_besttrack'}
            else:
                print(f"⚠️ [TCFD 경고] 태풍 API 조회 실패: HTTP {response.status_code}")
                return {'typhoons': [], 'data_source': 'fallback'}

        except Exception as e:
            print(f"⚠️ [TCFD 경고] 태풍 베스트트랙 API 조회 실패: {e}")
            return {'typhoons': [], 'data_source': 'fallback'}

    def _calculate_typhoon_impact(self, lat: float, lon: float, typhoon_data: Dict, rx1day_mm: float = None) -> Tuple[float, int, Dict]:
        """
        위치별 태풍 영향도 계산 (TCI 방식)

        TCI (Typhoon Comprehensive Index) = 0.55×Wind + 0.45×Rain
        (TCFD 정합성: Duration 제거, SSP Rx1day 사용)

        Args:
            lat, lon: 위치의 위도, 경도
            typhoon_data: 태풍 정보 딕셔너리
            rx1day_mm: SSP 시나리오 기반 1일 최대 강수량 (mm) - 기본값 None (추정 사용)

        Returns:
            (TCI값_0to1, 최대풍속_ms, TCI상세정보)
        """
        import math

        def haversine_distance(lat1, lon1, lat2, lon2):
            """두 지점 간 거리 계산 (km)"""
            R = 6371  # 지구 반지름 (km)
            dlat = math.radians(lat2 - lat1)
            dlon = math.radians(lon2 - lon1)
            a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1)) * \
                math.cos(math.radians(lat2)) * math.sin(dlon/2)**2
            c = 2 * math.asin(math.sqrt(a))
            return R * c

        try:
            params = config.TYPHOON_HAZARD_PARAMS
            typhoon_lat = typhoon_data.get('lat', 0)
            typhoon_lon = typhoon_data.get('lon', 0)
            max_wind = typhoon_data.get('max_wind_speed', 0)  # m/s

            # 태풍 중심까지의 거리 계산
            distance_km = haversine_distance(lat, lon, typhoon_lat, typhoon_lon)

            # 강풍 반경
            gale_radius = params['gale_radius_km']

            if distance_km >= gale_radius:
                # 영향권 밖
                return 0, 0, {'tci': 0, 'wind_norm': 0, 'rain_norm': 0}

            # ========== TCI 계산 (0.55×Wind + 0.45×Rain) ==========

            # 1. Wind 정규화 (0~1)
            wind_normalized = min(max_wind / params['wind_norm_max_ms'], 1.0)

            # 2. Rain 정규화 (0~1)
            if rx1day_mm is not None:
                # SSP 시나리오 Rx1day 데이터 사용
                rain_normalized = min(rx1day_mm / params['rain_norm_max_mm'], 1.0)
                rain_source = 'ssp_rx1day'
            else:
                # Fallback: 태풍 등급 기반 추정
                if max_wind >= 33:
                    estimated_rx1day = params['estimated_rx1day']['strong']
                elif max_wind >= 25:
                    estimated_rx1day = params['estimated_rx1day']['medium']
                else:
                    estimated_rx1day = params['estimated_rx1day']['weak']
                rain_normalized = min(estimated_rx1day / params['rain_norm_max_mm'], 1.0)
                rain_source = 'estimated_from_wind'

            # TCI 계산 (TCFD 정합성: 0.55:0.45)
            tci = 0.55 * wind_normalized + 0.45 * rain_normalized

            # 거리 감쇠 적용
            distance_factor = 1.0 - (distance_km / gale_radius)
            tci_adjusted = tci * distance_factor

            tci_details = {
                'tci': tci_adjusted,
                'wind_norm': wind_normalized,
                'rain_norm': rain_normalized,
                'rain_source': rain_source,
                'distance_km': distance_km,
                'distance_factor': distance_factor,
            }

            return tci_adjusted, max_wind, tci_details

        except Exception as e:
            return 0, 0, {'tci': 0, 'wind_norm': 0, 'rain_norm': 0}

    def _calculate_typhoon_hazard(self, lat: float, lon: float, data: Dict) -> Dict:
        """
        태풍 Hazard 계산 - KMA 베스트트랙 API 기반 (TCI 방식)

        과거 데이터 분석하여 지역별 태풍 영향도 계산
        TCI = 0.55×Wind + 0.45×Rain (TCFD 정합성 개선)
        """
        try:
            # 과거 태풍 데이터 수집
            typhoon_impacts = []  # TCI 값들
            max_wind_speeds = []

            # 설정 파일에서 분석 기간을 동적으로 생성
            period_params = config.TYPHOON_HAZARD_PARAMS['typhoon_analysis_period']
            end_year = period_params['end_year']
            num_years = period_params['num_years']
            years_to_check = range(end_year, end_year - num_years, -1)

            # TODO: SSP 시나리오 Rx1day 데이터 통합 필요
            # 현재는 rx1day_mm=None (태풍 강도 기반 추정 사용)
            rx1day_mm = None

            for year in years_to_check:
                result = self._fetch_typhoon_besttrack(year)
                if result['data_source'] == 'kma_besttrack' and result['typhoons']:
                    for typhoon in result['typhoons']:
                        # TCI 기반 영향도 계산 (rx1day: SSP 데이터 또는 추정)
                        tci, wind_speed, tci_details = self._calculate_typhoon_impact(lat, lon, typhoon, rx1day_mm=rx1day_mm)
                        if tci > 0:
                            typhoon_impacts.append(tci)
                            max_wind_speeds.append(wind_speed)

            # 통계 계산
            if typhoon_impacts:
                annual_frequency = len(typhoon_impacts) / num_years
                avg_max_wind = sum(max_wind_speeds) / len(max_wind_speeds)
                max_wind_kmh = max(max_wind_speeds) * 3.6  # m/s → km/h
                avg_impact = sum(typhoon_impacts) / len(typhoon_impacts)

                # 강도 분류
                if max_wind_kmh >= 180:
                    typhoon_intensity = 'very_strong'
                elif max_wind_kmh >= 140:
                    typhoon_intensity = 'strong'
                elif max_wind_kmh >= 100:
                    typhoon_intensity = 'moderate'
                else:
                    typhoon_intensity = 'weak'

                return {
                    'annual_typhoon_frequency': annual_frequency,
                    'max_wind_speed_kmh': int(max_wind_kmh),
                    'typhoon_intensity': typhoon_intensity,
                    'track_probability': min(avg_impact, 1.0),
                    'historical_typhoon_count': len(typhoon_impacts),
                    'data_source': 'kma_besttrack',
                }
            else:
                # API 데이터 없을 경우 fallback
                print(f"⚠️ [TCFD 경고] 해당 위치의 태풍 영향 데이터 없음 ({lat}, {lon})")
                return {
                    'annual_typhoon_frequency': 1.5,  # 한반도 평균
                    'max_wind_speed_kmh': 120,
                    'typhoon_intensity': 'moderate',
                    'track_probability': 0.1,
                    'historical_typhoon_count': 0,
                    'data_source': 'fallback',
                }

        except Exception as e:
            print(f"⚠️ [TCFD 경고] 태풍 해저드 계산 실패: {e}")
            return {
                'annual_typhoon_frequency': 1.5,
                'max_wind_speed_kmh': 120,
                'typhoon_intensity': 'moderate',
                'track_probability': 0.1,
                'historical_typhoon_count': 0,
                'data_source': 'fallback',
            }

    # ========================================================================
    # 8. 산불 (Wildfire)
    # ========================================================================

    def _calculate_wildfire_hazard(self, lat: float, lon: float, data: Dict) -> Dict:
        """
        산불 Hazard - Canadian FWI (Fire Weather Index) 시스템 기반

        근거:
        - Canadian Forest Service FWI System (standard since 1987)
        - IPCC AR6 wildfire risk assessment methodology
        - 대한민국 산림청 산불위험예보정보 활용

        FWI 6-subsystem approach:
        1. FFMC: 세밀한 연료 수분 (fine fuel moisture code, 0-101)
        2. DMC: 중간 연료 수분 (duff moisture code, 0-647)
        3. DC: 깊은 토양 건조도 (drought code, 0-1000+)
        4. ISI: 초기 확산 지수 (initial spread index, 0-37)
        5. BUI: 연료 축적 지수 (buildup index, 0-292)
        6. FWI: 최종 화재 기상 지수 (fire weather index, 0-81+)
        """
        # Step 1: NDVI 식생 데이터
        if self.spatial_loader:
            ndvi_data = self.spatial_loader.get_ndvi_data(lat, lon)
            vegetation_fuel = ndvi_data['wildfire_fuel']
            vegetation_health = ndvi_data['vegetation_health']
            ndvi = ndvi_data['ndvi']
        else:
            vegetation_fuel = 'medium'
            vegetation_health = 'fair'
            ndvi = 0.4

        # Step 2: 토지피복도 데이터
        if self.spatial_loader:
            landcover = self.spatial_loader.get_landcover_data(lat, lon)
            landcover_type = landcover['landcover_type']
            vegetation_ratio = landcover['vegetation_ratio']
        else:
            landcover_type = 'mixed'
            vegetation_ratio = 0.3

        # Step 3: 기후 데이터 (Canadian FWI 입력값: 온도, 습도, 강수, 풍속)
        try:
            if self.climate_loader:
                fwi_input = self.climate_loader.get_fwi_input_data(lat, lon, self.target_year)
                daily_max_temp = fwi_input['temperature']
                relative_humidity = fwi_input['relative_humidity']
                wind_speed = fwi_input['wind_speed']  # m/s
                
                # 강수량 및 건조일수 데이터는 별도 get_drought_data에서 가져옴
                drought_data = self.climate_loader.get_drought_data(lat, lon, self.target_year)
                annual_rainfall = drought_data['annual_rainfall_mm']
                dry_days = drought_data['consecutive_dry_days']
            else:
                raise ValueError("ClimateLoader not available")

        except Exception as e:
            print(f"⚠️ [TCFD 경고] FWI 기후 데이터 로드 실패: {e}. Fallback 값 사용.")
            daily_max_temp = 35.0
            relative_humidity = 40.0
            wind_speed = 2.5  # m/s
            annual_rainfall = 1200
            dry_days = 15


        # Step 4: Canadian FWI 계산 (간단 근사 버전)
        # 정식 FWI는 6개 서브인덱스를 순차적으로 계산하지만,
        # 여기서는 간단한 근사를 사용하여 계산 편의성과 현실성 균형

        # FFMC (Fine Fuel Moisture Code): 세밀한 연료 수분
        # 온도와 습도에 의존
        ffmc = 85 - (relative_humidity / 100) * 50 + (daily_max_temp / 50) * 15
        ffmc = max(0, min(101, ffmc))  # 0-101 범위

        # DC (Drought Code): 깊은 토양 건조도
        # 연강수 부족 시 증가
        if annual_rainfall < 500:
            dc = 400  # 심한 건조
        elif annual_rainfall < 1000:
            dc = 250  # 중간 건조
        elif annual_rainfall < 1500:
            dc = 150  # 경미한 건조
        else:
            dc = 50   # 정상

        # ISI (Initial Spread Index): 초기 확산 지수
        # 풍속과 온도에 의존
        isi = (wind_speed / 5) * 20 + (daily_max_temp / 40) * 15
        isi = max(0, min(37, isi))  # 0-37 범위

        # BUI (Buildup Index): 연료 축적 지수
        # DC와 DMC의 합성 (여기서는 DC만 사용)
        bui = dc * 0.8

        # FWI (Fire Weather Index): 최종 화재 기상 지수
        # FFMC, ISI, BUI의 함수
        # 정식: FWI = 0.85 × B + 0.25 × A (복잡한 변환식)
        # 간단 근사: 정규화된 지수 계산
        fwi_normalized = (ffmc / 101) * 0.4 + (isi / 37) * 0.3 + (bui / 292) * 0.3
        fwi = fwi_normalized * 81  # 0-81 범위로 정규화

        # Step 5: 위험도 지수 계산 (0-100 스케일)
        # FWI를 0-100 스케일로 변환
        wildfire_risk_index = (fwi / 81) * 100

        # 토지피복도에 따른 조정 (다항 계수 아님, 환경 민감도 가중)
        if landcover_type == 'forest':
            wildfire_risk_index *= 1.3  # 산림은 화재 확산 위험 높음
        elif landcover_type == 'grassland':
            wildfire_risk_index *= 1.2  # 초지는 중간 위험
        elif landcover_type == 'agricultural':
            wildfire_risk_index *= 0.8  # 농지는 관리되므로 위험 낮음

        wildfire_risk_index = min(wildfire_risk_index, 100)

        # Step 6: 가연성 분류 (Canadian FWI 기준)
        if fwi > 60:
            flammability = 'extreme'  # 극심한 위험
            fire_freq = 0.20
        elif fwi > 40:
            flammability = 'high'     # 높은 위험
            fire_freq = 0.10
        elif fwi > 20:
            flammability = 'moderate' # 중간 위험
            fire_freq = 0.05
        elif fwi > 10:
            flammability = 'low'      # 낮은 위험
            fire_freq = 0.02
        else:
            flammability = 'very_low' # 극히 낮은 위험
            fire_freq = 0.01

        return {
            'wildfire_risk_index': wildfire_risk_index,
            'annual_fire_frequency': fire_freq,
            'fire_weather_index': fwi,
            'fwi_subsystems': {
                'FFMC': ffmc,           # 세밀한 연료 수분 (0-101)
                'DC': dc,               # 깊은 토양 건조도 (0-1000+)
                'ISI': isi,             # 초기 확산 지수 (0-37)
                'BUI': bui,             # 연료 축적 지수 (0-292)
            },
            'vegetation_flammability': flammability,
            'ndvi': ndvi,
            'vegetation_fuel': vegetation_fuel,
            'landcover_type': landcover_type,
            'max_temp_celsius': daily_max_temp,
            'relative_humidity_percent': relative_humidity,
            'dry_days': dry_days,
            'annual_rainfall_mm': annual_rainfall,
            'wind_speed_ms': wind_speed,
            'climate_scenario': self.scenario,
            'year': self.target_year,
            'data_source': 'Canadian FWI System + KMA climate data (IPCC AR6)',
            'note': 'FWI ≥ 60: 극심한 위험 | 40-60: 높은 위험 | 20-40: 중간 | 10-20: 낮음 | <10: 극히 낮음',
        }

    # ========================================================================
    # 9. 물부족 (Water Stress)
    # ========================================================================

    def _calculate_water_stress_hazard(self, lat: float, lon: float, data: Dict) -> Dict:
        """
        물부족 Hazard 계산 - WAMIS 용수 이용량 + 기후 강수량 기반

        데이터 소스:
        - WAMIS Open API: 용수 이용량 (생활용수, 공업용수, 농업용수)
        - 기후 데이터: 연강수량 (RN, mm/year)

        계산 방식:
        1. 좌표 → 권역 정보 추출 (VWorld API + WAMIS 매핑)
        2. 권역별 용수 이용량 조회 (WAMIS API)
        3. 권역별 연강수량 조회 (기후모델)
        4. 유역면적 기반 물수급량 계산
        5. 물부족지수 = 용수이용량 / 물수급량
        """
        try:
            if not self.wamis_fetcher or not self.climate_loader:
                raise ValueError("WAMIS 또는 Climate 데이터 로더 초기화 실패")

            # Step 1: 좌표 → 권역 정보 추출
            watershed_info = self.wamis_fetcher.get_watershed_from_coords(lat, lon)
            major_watershed = watershed_info['major_watershed']
            watershed_area_km2 = watershed_info['watershed_area_km2']
            runoff_coef = watershed_info['runoff_coef']

            # Step 2: 권역별 용수 이용량 조회 (단위: 천 m³/년)
            # 주의: 2030년 데이터가 없으면 최신 데이터로 폴백
            try:
                water_usage = self.wamis_fetcher.get_water_usage(major_watershed, year=self.target_year)
            except ValueError as e:
                if '데이터 없음' in str(e):
                    print(f"   ⚠️  {self.target_year}년 데이터 없음, 최신 데이터로 조회 재시도...")
                    water_usage = self.wamis_fetcher.get_water_usage(major_watershed)  # 최신 데이터로 폴백
                else:
                    raise

            # 용수 이용량 합산 (천 m³/년 → m³/day)
            # 1년 = 365일, 1천 m³ = 1000 m³
            water_demand_annually_m3 = (
                water_usage['domestic'] +
                water_usage['industrial'] +
                water_usage['agricultural']
            ) * 1000  # 천 m³ → m³
            water_demand_m3_per_day = water_demand_annually_m3 / 365

            # Step 3: 권역별 연강수량 조회 (단위: mm/year)
            drought_data = self.climate_loader.get_drought_data(lat, lon, year=self.target_year)
            annual_rainfall_mm = drought_data.get('annual_rainfall_mm', 1200.0)

            # Step 4: 물수급량 계산
            # 공식: 물수급량 = 강수량(mm) × 유역면적(km²) × 유출계수 × 1000 (단위 변환)
            # 계산 원리:
            #   - 1mm 강수량 × 1km² = 1mm × 10^6 m² = 0.001m × 10^6 m² = 1000 m³
            # 결과 단위: m³/year
            rainfall_runoff_m3_annually = (
                annual_rainfall_mm *
                watershed_area_km2 *
                runoff_coef * 1000
            )
            water_supply_m3_per_day = rainfall_runoff_m3_annually / 365

            # Step 5: 물부족지수 (Water Stress Index)
            if water_supply_m3_per_day > 0:
                stress_index = water_demand_m3_per_day / water_supply_m3_per_day
            else:
                stress_index = float('inf')  # 공급 불가능

            # Step 6: 공급비율
            supply_ratio = min(water_supply_m3_per_day / water_demand_m3_per_day, 1.0) if water_demand_m3_per_day > 0 else 0.0

            # Step 7: 스트레스 수준 분류 (UN-Water 기준)
            # - stress_index < 1.0: No stress (충분)
            # - 1.0 ≤ stress_index < 1.5: Mild stress
            # - 1.5 ≤ stress_index < 2.0: Moderate stress
            # - stress_index ≥ 2.0: Severe stress
            if stress_index < 1.0:
                stress_level = 'low'
                drought_frequency = 0.01
            elif stress_index < 1.5:
                stress_level = 'mild'
                drought_frequency = 0.05
            elif stress_index < 2.0:
                stress_level = 'medium'
                drought_frequency = 0.10
            else:
                stress_level = 'high'
                drought_frequency = 0.20

            return {
                'watershed': major_watershed,
                'water_demand_m3_per_day': water_demand_m3_per_day,
                'water_supply_m3_per_day': water_supply_m3_per_day,
                'water_stress_index': stress_index,
                'supply_ratio': supply_ratio,
                'annual_rainfall_mm': annual_rainfall_mm,
                'watershed_area_km2': watershed_area_km2,
                'drought_frequency': drought_frequency,
                'stress_level': stress_level,
                'data_source': 'WAMIS API + KMA Climate (실제 데이터)',
                'note': f'{major_watershed} 유역 ({watershed_area_km2:.0f}km²)'
            }

        except Exception as e:
            print(f"⚠️ [TCFD 경고] 물부족 데이터 조회 실패: {e}")
            # Fallback: 보수적 추정값 (전국 평균)
            return {
                'watershed': 'unknown',
                'water_demand_m3_per_day': 500000,
                'water_supply_m3_per_day': 450000,
                'water_stress_index': 1.11,
                'supply_ratio': 0.9,
                'annual_rainfall_mm': 1200.0,
                'watershed_area_km2': 15000,
                'drought_frequency': 0.10,
                'stress_level': 'medium',
                'data_source': 'Fallback (통계 기반 평균값)',
                'note': '실제 데이터 조회 실패 - 전국 평균값 사용'
            }

    # ========================================================================
    # Helper Methods
    # ========================================================================

    def _print_summary(self, hazard: Dict):
        """Hazard 요약 출력"""
        print(f"\n🌡️  극심한 고온: 최고기온 {hazard['extreme_heat']['annual_max_temp_celsius']}°C, 극심한 고온 {hazard['extreme_heat']['heatwave_days_per_year']}일/년")
        print(f"❄️  극심한 극심한 한파: 최저기온 {hazard['extreme_cold']['annual_min_temp_celsius']}°C, 극심한 한파 {hazard['extreme_cold']['coldwave_days_per_year']}일/년")
        print(f"🏜️  가뭄: 연강수량 {hazard['drought']['annual_rainfall_mm']}mm, SPEI {hazard['drought']['spei12_index']:.2f}")

        # 하천 홍수: 위험도 점수 + 주요 지표 표시
        rf_hazard = hazard['river_flood'].get('hazard_score', 0.5)
        rf_twi = hazard['river_flood'].get('twi', 7.0)
        print(f"🌊 하천 홍수: 위험도 {rf_hazard:.2f}, TWI {rf_twi:.1f}, 하천 '{hazard['river_flood']['river_name']}', 유역 {hazard['river_flood']['watershed_area_km2']}km²")

        # 도시 홍수: 위험도 점수 + 배수능력 표시
        uf_hazard = hazard['urban_flood'].get('hazard_score', 0.5)
        uf_drainage = hazard['urban_flood'].get('effective_drainage_mm_hr', 50)
        print(f"🏙️  도시 홍수: 위험도 {uf_hazard:.2f}, 배수능력 {uf_drainage:.0f}mm/hr, 강수 {hazard['urban_flood']['extreme_rainfall_1hr_mm']:.1f}mm/hr")

        print(f"🌊 해수면 상승: 노출 {hazard['sea_level_rise']['coastal_exposure']}, 해일 {hazard['sea_level_rise']['storm_surge_height_m']}m")
        print(f"🌀 태풍: 연평균 {hazard['typhoon']['annual_typhoon_frequency']}회, 최대풍속 {hazard['typhoon']['max_wind_speed_kmh']}km/h")
        print(f"🔥 산불: 위험지수 {hazard['wildfire']['wildfire_risk_index']}/100")
        water_demand = hazard['water_stress']['water_demand_m3_per_day']
        water_supply = hazard['water_stress']['water_supply_m3_per_day']
        stress_index = hazard['water_stress'].get('water_stress_index', 1.0)
        print(f"💧 수자원: {hazard['water_stress'].get('watershed', 'unknown')} 유역, 수요 {water_demand/1000:.0f}천m³/일, 공급 {water_supply/1000:.0f}천m³/일, 스트레스지수 {stress_index:.2f}, 레벨 {hazard['water_stress']['stress_level']}")


if __name__ == "__main__":
    # 테스트
    calculator = HazardCalculator()

    # 테스트 1: 서울 강남
    print("\n" + "="*80)
    print("테스트 1: 서울 강남")
    result1 = calculator.calculate(37.5172, 127.0473)

    # 테스트 2: 대전 유성
    print("\n" + "="*80)
    print("테스트 2: 대전 유성")
    result2 = calculator.calculate(36.38296731680909, 127.3954419423826)
