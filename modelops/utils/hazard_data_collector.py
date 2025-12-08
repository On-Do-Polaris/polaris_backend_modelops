from typing import Dict, Any, Optional
import os
import logging
from dotenv import load_dotenv

# 로거 설정
logger = logging.getLogger(__name__)

# 데이터 로더 및 페처 임포트
try:
    from modelops.data_loaders.building_data_fetcher import BuildingDataFetcher
    from modelops.data_loaders.disaster_api_fetcher import DisasterAPIFetcher
    from modelops.data_loaders.climate_data_loader import ClimateDataLoader
    from modelops.data_loaders.spatial_data_loader import SpatialDataLoader
    from modelops.data_loaders.wamis_fetcher import WamisFetcher
    from modelops.utils.fwi_calculator import FWICalculator
    from modelops.config import hazard_config as config
    DATA_LOADERS_AVAILABLE = True
except ImportError as e:
    logger.error(f"Failed to import data loaders: {e}")
    DATA_LOADERS_AVAILABLE = False
    # Mock classes for graceful degradation
    BuildingDataFetcher = None
    DisasterAPIFetcher = None
    ClimateDataLoader = None
    SpatialDataLoader = None
    WamisFetcher = None
    FWICalculator = None
    config = None


class HazardDataCollector:
    """
    각 Hazard Agent가 필요로 하는 데이터를 수집하고 준비하는 중앙 유틸리티 클래스.
    HazardCalculator의 데이터 수집 로직을 이관함.
    """

    def __init__(self, scenario: str = 'SSP245', target_year: int = 2030):
        """
        Args:
            scenario: SSP 시나리오 (SSP126, SSP245, SSP370, SSP585)
            target_year: 분석 연도 (2021-2100)
        """
        self.scenario = scenario
        self.target_year = target_year
        self._load_environment()

        if not DATA_LOADERS_AVAILABLE:
            logger.warning("데이터 로더를 사용할 수 없습니다. Mock 모드로 실행됩니다.")
            self.building_fetcher = None
            self.disaster_fetcher = None
            self.climate_loader = None
            self.spatial_loader = None
            self.wamis_fetcher = None
            self.fwi_calculator = None
            return

        # 데이터 로더 초기화 (Lazy loading을 고려할 수도 있으나, 현재는 생성 시 초기화)
        try:
            self.building_fetcher = BuildingDataFetcher() if BuildingDataFetcher else None
        except Exception as e:
            logger.warning(f"BuildingDataFetcher 초기화 실패: {e}")
            self.building_fetcher = None

        try:
            self.disaster_fetcher = DisasterAPIFetcher() if DisasterAPIFetcher else None
        except Exception as e:
            logger.warning(f"DisasterAPIFetcher 초기화 실패: {e}")
            self.disaster_fetcher = None

        # ClimateDataLoader는 scenario 의존성 있음
        try:
            self.climate_loader = ClimateDataLoader(scenario=scenario) if ClimateDataLoader else None
        except Exception as e:
            logger.warning(f"ClimateDataLoader 초기화 실패: {e}")
            self.climate_loader = None

        try:
            self.spatial_loader = SpatialDataLoader() if SpatialDataLoader else None
        except Exception as e:
            logger.warning(f"SpatialDataLoader 초기화 실패: {e}")
            self.spatial_loader = None

        try:
            self.wamis_fetcher = WamisFetcher() if WamisFetcher else None
        except Exception as e:
            logger.warning(f"WamisFetcher 초기화 실패: {e}")
            self.wamis_fetcher = None

        try:
            self.fwi_calculator = FWICalculator() if FWICalculator else None
        except Exception as e:
            logger.warning(f"FWICalculator 초기화 실패: {e}")
            self.fwi_calculator = None

        # KMA API Key 확인
        self.kma_api_key = os.getenv("KMA_API_KEY")
        if not self.kma_api_key:
            logger.warning("KMA_API_KEY가 설정되지 않았습니다. 일부 기능이 제한될 수 있습니다.")

    def _load_environment(self):
        """환경 변수 로드"""
        # 프로젝트 루트의 .env 파일 로드 시도
        # 현재 위치: modelops/utils/hazard_data_collector.py
        # 루트: ../../.env
        env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), '.env')
        if os.path.exists(env_path):
            load_dotenv(env_path)
        else:
            logger.warning(f".env 파일을 찾을 수 없습니다: {env_path}")

    def collect_data(self, lat: float, lon: float, risk_type: str) -> Dict[str, Any]:
        """
        특정 리스크 유형에 필요한 데이터를 수집합니다.

        Args:
            lat: 위도
            lon: 경도
            risk_type: 리스크 유형 (예: 'extreme_heat', 'river_flood')

        Returns:
            에이전트 계산에 필요한 'collected_data' 딕셔너리
        """
        # 1. 기본 메타데이터 및 공통 데이터
        collected_data = {
            'latitude': lat,
            'longitude': lon,
            'risk_type': risk_type,
            'scenario': self.scenario,
            'target_year': self.target_year,
            'building_data': {}, # 기본적으로 비어있음, 필요 시 채움
            'climate_data': {},
            'spatial_data': {},
            'disaster_data': {},
            'extra_data': {}
        }

        # 2. 건물 정보 (모든 리스크 분석의 기초가 될 수 있으므로 기본 수집 고려, 
        #    하지만 성능을 위해 필요할 때만 수집하는 것이 좋을 수 있음.
        #    HazardCalculator에서는 fetch_all_building_data를 항상 호출했음.)
        try:
            collected_data['building_data'] = self.building_fetcher.fetch_all_building_data(lat, lon)
        except Exception as e:
            logger.warning(f"건물 데이터 수집 실패: {e}")

        # 3. 리스크 유형별 특화 데이터 수집
        if risk_type == 'extreme_heat':
            self._collect_heat_data(lat, lon, collected_data)
        elif risk_type == 'extreme_cold':
            self._collect_cold_data(lat, lon, collected_data)
        elif risk_type == 'drought':
            self._collect_drought_data(lat, lon, collected_data)
        elif risk_type == 'river_flood':
            self._collect_river_flood_data(lat, lon, collected_data)
        elif risk_type == 'urban_flood':
            self._collect_urban_flood_data(lat, lon, collected_data)
        elif risk_type == 'sea_level_rise':
            self._collect_slr_data(lat, lon, collected_data)
        elif risk_type == 'typhoon':
            self._collect_typhoon_data(lat, lon, collected_data)
        elif risk_type == 'wildfire':
            self._collect_wildfire_data(lat, lon, collected_data)
        elif risk_type == 'water_stress':
            self._collect_water_stress_data(lat, lon, collected_data)
        elif risk_type == 'exposure':
            self._collect_exposure_data(lat, lon, collected_data)
        
        return collected_data

    # --- 리스크별 데이터 수집 헬퍼 메서드 ---

    def _collect_exposure_data(self, lat: float, lon: float, data: Dict):
        """Exposure 계산에 필요한 데이터 수집 (Landcover 등)"""
        if self.spatial_loader:
            data['spatial_data'].update(self.spatial_loader.get_landcover_data(lat, lon))
            # NDVI 등 추가 데이터가 필요할 수 있음
            data['spatial_data'].update(self.spatial_loader.get_ndvi_data(lat, lon))

    def _collect_heat_data(self, lat: float, lon: float, data: Dict):
        if self.climate_loader:
            data['climate_data'] = self.climate_loader.get_extreme_heat_data(lat, lon, self.target_year)

    def _collect_cold_data(self, lat: float, lon: float, data: Dict):
        if self.climate_loader:
            data['climate_data'] = self.climate_loader.get_extreme_cold_data(lat, lon, self.target_year)

    def _collect_drought_data(self, lat: float, lon: float, data: Dict):
        if self.climate_loader:
            data['climate_data'] = self.climate_loader.get_drought_data(lat, lon, self.target_year)
        if self.spatial_loader:
            data['spatial_data'] = self.spatial_loader.get_soil_moisture_data(lat, lon)

    def _collect_river_flood_data(self, lat: float, lon: float, data: Dict):
        # TWI 계산을 위한 데이터 등 (Spatial Loader 기능 확인 필요)
        if self.spatial_loader:
            data['spatial_data'] = self.spatial_loader.get_landcover_data(lat, lon)
            # TWI 계산 로직은 HazardCalculator 내부에 있었음. 
            # 이를 Agent로 옮길지, 여기서 미리 계산해서 줄지 결정 필요.
            # Agent 로직이 복잡하므로 Agent로 옮기는 것이 원칙이나, 
            # 데이터 수집 단계에서 가공된 데이터를 주는 것이 더 깔끔할 수 있음.
            # 일단 원본 데이터를 최대한 제공하는 방향으로 작성.
        
        if self.disaster_fetcher:
            data['disaster_data'] = self.disaster_fetcher.get_nearest_river_info(lat, lon)
        
        if self.climate_loader:
            data['climate_data'] = self.climate_loader.get_flood_data(lat, lon, self.target_year)

    def _collect_urban_flood_data(self, lat: float, lon: float, data: Dict):
        if self.spatial_loader:
            data['spatial_data'] = self.spatial_loader.get_landcover_data(lat, lon)
        
        if self.climate_loader:
            data['climate_data'] = self.climate_loader.get_flood_data(lat, lon, self.target_year)
            
        # 건물 밀도 등을 위한 building_count는 이미 building_data에 포함되어 있다고 가정
        # data['building_data']['building_count'] 확인 필요

    def _collect_slr_data(self, lat: float, lon: float, data: Dict):
        # 해안 거리 계산 등은 별도 로직이 필요할 수 있음 (HazardCalculator에서는 distance_to_coast_m을 data에서 가져옴)
        # SpatialLoader가 이를 제공하는지 확인 필요. 없다면 BuildingFetcher나 외부 API 사용해야 함.
        # 여기서는 일단 ClimateLoader 호출
        if self.climate_loader:
            data['climate_data'] = self.climate_loader.get_sea_level_rise_data(lat, lon, self.target_year)
        
        # 해안 거리 정보가 building_data나 spatial_data에 있어야 함.
        # 예시: data['extra_data']['distance_to_coast_m'] = ...

    def _collect_typhoon_data(self, lat: float, lon: float, data: Dict):
        if not self.disaster_fetcher:
            return

        typhoons_all = []
        
        # 분석 기간 설정 (config 사용)
        end_year = 2022
        num_years = 10
        
        if config and hasattr(config, 'TYPHOON_HAZARD_PARAMS'):
            period_params = config.TYPHOON_HAZARD_PARAMS.get('typhoon_analysis_period', {})
            end_year = period_params.get('end_year', 2022)
            num_years = period_params.get('num_years', 10)
            
        years_to_check = range(end_year, end_year - num_years, -1)
        
        for year in years_to_check:
            # fetch_typhoon_besttrack 메서드가 DisasterAPIFetcher에 추가되었다고 가정
            if hasattr(self.disaster_fetcher, 'fetch_typhoon_besttrack'):
                result = self.disaster_fetcher.fetch_typhoon_besttrack(year)
                if result.get('typhoons'):
                    typhoons_all.extend(result['typhoons'])
                
        data['typhoon_data'] = {
            'typhoons': typhoons_all,
            'analysis_period_years': num_years,
            'end_year': end_year
        }

    def _collect_wildfire_data(self, lat: float, lon: float, data: Dict):
        if self.spatial_loader:
            data['spatial_data'].update(self.spatial_loader.get_ndvi_data(lat, lon))
            data['spatial_data'].update(self.spatial_loader.get_landcover_data(lat, lon))
        
        if self.climate_loader:
            # FWI Input Data
            data['climate_data'] = self.climate_loader.get_fwi_input_data(lat, lon, self.target_year)
            # 가뭄 데이터도 필요함
            drought = self.climate_loader.get_drought_data(lat, lon, self.target_year)
            data['climate_data'].update(drought) # 병합

    def _collect_water_stress_data(self, lat: float, lon: float, data: Dict):
        if self.wamis_fetcher:
            try:
                watershed_info = self.wamis_fetcher.get_watershed_from_coords(lat, lon)
                data['wamis_data']['watershed_info'] = watershed_info
                
                # 용수 사용량
                major_watershed = watershed_info.get('major_watershed')
                if major_watershed:
                     data['wamis_data']['water_usage'] = self.wamis_fetcher.get_water_usage(major_watershed, year=self.target_year)
            except Exception as e:
                logger.warning(f"WAMIS 데이터 수집 실패: {e}")

        if self.climate_loader:
            data['climate_data'] = self.climate_loader.get_drought_data(lat, lon, self.target_year)
