# 코드 모듈 상세 가이드

## 목차
1. [메인 모듈](#1-메인-모듈)
2. [계산 모듈](#2-계산-모듈)
3. [데이터 로더 모듈](#3-데이터-로더-모듈)
4. [유틸리티 모듈](#4-유틸리티-모듈)
5. [의존성 관계](#5-의존성-관계)

---

## 1. 메인 모듈

### 1.1 risk_calculator.py

**역할**: 메인 오케스트레이터 - H, E, V를 조합하여 최종 리스크 점수 산출

#### 클래스: RiskCalculator

```python
class RiskCalculator:
    """
    물리적 기후 리스크 점수 산출

    공식: Risk = Hazard × Exposure × Vulnerability
    """

    def __init__(self, scenario='SSP245', target_year=2030):
        self.scenario = scenario          # SSP 시나리오
        self.target_year = target_year    # 분석 연도

        # 하위 계산기 초기화
        self.hazard_calculator = HazardCalculator(scenario, target_year)
        self.exposure_calculator = ExposureCalculator()
        self.vulnerability_calculator = VulnerabilityCalculator()
```

#### 주요 메서드

##### calculate_all_risks()

```python
def calculate_all_risks(
    self,
    location: Union[str, Tuple[float, float]]
) -> Dict:
    """
    9개 리스크별 점수 산출

    Args:
        location: 주소(str) 또는 (lat, lon) 튜플

    Returns:
        {
            'extreme_heat': {
                'risk_score': 76.5,      # 최종 리스크 점수 (0-100)
                'risk_level': 'high',    # 리스크 등급 (low/medium/high/very_high)
                'hazard_score': 85.0,
                'exposure_score': 90.0,
                'vulnerability_score': 80.0,
                'data_sources': ['KMA_SSP_gridraw', 'building_api'],
                'tcfd_warnings': []
            },
            ...
        }
    """
    # 1. E 계산 (Exposure)
    exposure = self.exposure_calculator.calculate(location)
    lat = exposure['location']['latitude']
    lon = exposure['location']['longitude']

    # 2. H 계산 (Hazard)
    hazard = self.hazard_calculator.calculate(lat, lon)

    # 3. V 계산 (Vulnerability)
    vulnerability = self.vulnerability_calculator.calculate(hazard, exposure)

    # 4. Risk = H × E × V
    risks = {}
    for risk_name in RISK_TYPES:
        H = hazard[risk_name]['hazard_score']
        E = exposure[f'{risk_name}_exposure']['exposure_score']
        V = vulnerability[risk_name]['vulnerability_score']

        risk_score = (H * E * V) / 10000  # 0-100 스케일

        risks[risk_name] = {
            'risk_score': risk_score,
            'risk_level': self._classify_risk_level(risk_score),
            'hazard_score': H,
            'exposure_score': E,
            'vulnerability_score': V,
            ...
        }

    return risks
```

##### _classify_risk_level()

```python
def _classify_risk_level(self, score: float) -> str:
    """
    리스크 점수 → 등급 분류

    Args:
        score: 0-100 점수

    Returns:
        'low' | 'medium' | 'high' | 'very_high'
    """
    if score >= 75:
        return 'very_high'  # 매우 높음
    elif score >= 50:
        return 'high'        # 높음
    elif score >= 25:
        return 'medium'      # 보통
    else:
        return 'low'         # 낮음
```

#### 사용 예시

```python
from risk_calculator import RiskCalculator

# 초기화
calculator = RiskCalculator(
    scenario='SSP245',
    target_year=2030
)

# 주소로 계산
result = calculator.calculate_all_risks("대전광역시 유성구 엑스포로 325")

# 좌표로 계산
result = calculator.calculate_all_risks((36.383, 127.395))

# 결과 출력
print(f"극한 고온 리스크: {result['extreme_heat']['risk_score']:.1f}점")
print(f"리스크 등급: {result['extreme_heat']['risk_level']}")
```

---

## 2. 계산 모듈

### 2.1 hazard_calculator.py

**역할**: 재난 강도(Hazard) 계산 - 각 지역에 얼마나 강한 재난이 발생하는가?

#### 클래스: HazardCalculator

```python
class HazardCalculator:
    """
    9개 물리적 리스크별 Hazard 강도 계산

    데이터 소스:
    - KMA SSP 시나리오 (NetCDF)
    - 재난안전데이터 API
    - NDVI 위성 데이터
    - 토지피복도
    """

    def __init__(self, scenario='SSP245', target_year=2030):
        self.scenario = scenario
        self.target_year = target_year

        # 데이터 로더 초기화
        self.climate_loader = ClimateDataLoader(scenario=scenario)
        self.spatial_loader = SpatialDataLoader()
        self.building_fetcher = BuildingDataFetcher()
        self.disaster_fetcher = DisasterAPIFetcher()
```

#### 주요 메서드

##### calculate()

```python
def calculate(self, lat: float, lon: float) -> Dict:
    """
    9개 리스크별 Hazard 계산

    Returns:
        {
            'extreme_heat': {
                'annual_max_temp_celsius': 38.3,
                'heatwave_days_per_year': 154,
                'heatwave_intensity': 'very_high',
                'hazard_score': 85.0,
                'data_source': 'KMA_SSP_gridraw'
            },
            ...
        }
    """
    # 공통 데이터 수집
    data = self.building_fetcher.fetch_all_building_data(lat, lon)

    return {
        'extreme_heat': self._calculate_heat_hazard(lat, lon, data),
        'extreme_cold': self._calculate_cold_hazard(lat, lon, data),
        'drought': self._calculate_drought_hazard(lat, lon, data),
        'inland_flood': self._calculate_inland_flood_hazard(lat, lon, data),
        'urban_flood': self._calculate_urban_flood_hazard(lat, lon, data),
        'coastal_flood': self._calculate_coastal_flood_hazard(lat, lon, data),
        'typhoon': self._calculate_typhoon_hazard(lat, lon, data),
        'wildfire': self._calculate_wildfire_hazard(lat, lon, data),
        'water_stress': self._calculate_water_stress_hazard(lat, lon, data),
    }
```

##### _calculate_heat_hazard()

```python
def _calculate_heat_hazard(self, lat, lon, data) -> Dict:
    """
    극한 고온 Hazard 계산

    데이터 소스: KMA SSP (TXx, SU25, TR25, WSDIx)
    """
    # KMA SSP 데이터 로드
    heat_data = self.climate_loader.get_extreme_heat_data(lat, lon, self.target_year)

    # 폭염 강도 판단
    heatwave_days = heat_data['heatwave_days_per_year']
    if heatwave_days > 30:
        intensity = 'very_high'
        hazard_score = 90
    elif heatwave_days > 20:
        intensity = 'high'
        hazard_score = 75
    elif heatwave_days > 10:
        intensity = 'medium'
        hazard_score = 50
    else:
        intensity = 'low'
        hazard_score = 25

    return {
        'annual_max_temp_celsius': heat_data['annual_max_temp_celsius'],
        'heatwave_days_per_year': heatwave_days,
        'tropical_nights': heat_data['tropical_nights'],
        'heat_wave_duration': heat_data['heat_wave_duration'],
        'heatwave_intensity': intensity,
        'hazard_score': hazard_score,
        'climate_scenario': self.scenario,
        'year': self.target_year,
        'data_source': heat_data['data_source']
    }
```

##### _calculate_wildfire_hazard()

```python
def _calculate_wildfire_hazard(self, lat, lon, data) -> Dict:
    """
    산불 Hazard 계산

    데이터 소스:
    - NDVI (식생 밀도)
    - 토지피복도 (토지 유형)
    - KMA SSP (온도, 건조도)
    """
    # 1. NDVI 식생 데이터
    ndvi_data = self.spatial_loader.get_ndvi_data(lat, lon)
    vegetation_fuel = ndvi_data['wildfire_fuel']  # low/medium/high
    ndvi = ndvi_data['ndvi']

    # 2. 토지피복도
    landcover = self.spatial_loader.get_landcover_data(lat, lon)
    landcover_type = landcover['landcover_type']  # forest/urban/agricultural

    # 3. 기후 데이터
    heat_data = self.climate_loader.get_extreme_heat_data(lat, lon, self.target_year)
    drought_data = self.climate_loader.get_drought_data(lat, lon, self.target_year)

    max_temp = heat_data['annual_max_temp_celsius']
    dry_days = drought_data['consecutive_dry_days']

    # 4. FWI (Fire Weather Index) 계산
    fwi = (max_temp - 20) * 2 + dry_days
    if fwi < 0:
        fwi = 0

    # 5. 산불 위험 지수 계산
    risk_index = 30  # 기본값

    # 식생 연료 고려
    if vegetation_fuel == 'high':
        risk_index += 30
    elif vegetation_fuel == 'medium':
        risk_index += 15

    # 토지피복 고려
    if landcover_type == 'forest':
        risk_index += 20
    elif landcover_type == 'grassland':
        risk_index += 10

    # 기후 고려
    if dry_days > 20:
        risk_index += 10

    risk_index = min(risk_index, 100)

    # 6. Hazard Score
    if risk_index > 70:
        hazard_score = 85
    elif risk_index > 50:
        hazard_score = 65
    else:
        hazard_score = 40

    return {
        'wildfire_risk_index': risk_index,
        'fire_weather_index': fwi,
        'ndvi': ndvi,
        'vegetation_fuel': vegetation_fuel,
        'landcover_type': landcover_type,
        'max_temp_celsius': max_temp,
        'dry_days': dry_days,
        'hazard_score': hazard_score,
        'data_source': 'NDVI + landcover + climate'
    }
```

---

### 2.2 exposure_calculator.py

**역할**: 노출도(Exposure) 계산 - 건물이 재난에 얼마나 노출되어 있는가?

#### 클래스: ExposureCalculator

```python
class ExposureCalculator:
    """
    노출도 계산기

    입력: 위/경도 또는 주소
    출력: 건물 위치, 특성, 인프라 정보
    """

    def __init__(self):
        self.fetcher = BuildingDataFetcher()
```

#### 주요 메서드

##### calculate()

```python
def calculate(self, location: Union[str, Tuple]) -> Dict:
    """
    노출도 계산

    Args:
        location: 주소(str) 또는 (lat, lon) 튜플

    Returns:
        {
            'location': {...},
            'building': {...},
            'flood_exposure': {...},
            'heat_exposure': {...},
            'typhoon_exposure': {...},
            'wildfire_exposure': {...},
            'infrastructure': {...},
            'metadata': {...}
        }
    """
    # 1. 주소 → 좌표 변환
    if isinstance(location, str):
        lat, lon = self._address_to_coords(location)
    else:
        lat, lon = location

    # 2. 건축물 데이터 수집
    raw_data = self.fetcher.fetch_all_building_data(lat, lon)

    # 3. 노출도 구조화
    exposure = self._structure_exposure_data(raw_data, lat, lon)

    return exposure
```

##### _address_to_coords()

```python
def _address_to_coords(self, address: str) -> Tuple[float, float]:
    """
    주소 → 좌표 변환 (V-World API)

    도로명 주소와 지번 주소 모두 지원

    Args:
        address: '대전광역시 유성구 엑스포로 325'
                 또는 '대전광역시 유성구 원촌동 140-1'

    Returns:
        (latitude, longitude)
    """
    VWORLD_KEY = os.getenv("VWORLD_API_KEY")
    url = "https://api.vworld.kr/req/address"

    # 도로명 주소 먼저 시도, 실패 시 지번 주소 시도
    for address_type in ['ROAD', 'PARCEL']:
        params = {
            'service': 'address',
            'request': 'getcoord',
            'format': 'json',
            'crs': 'epsg:4326',
            'address': address,
            'type': address_type,
            'key': VWORLD_KEY
        }

        try:
            response = requests.get(url, params=params, timeout=10)
            data = response.json()

            if data['response']['status'] == 'OK':
                result = data['response']['result']
                if result and 'point' in result:
                    lon = float(result['point']['x'])
                    lat = float(result['point']['y'])
                    print(f"✅ 주소 변환 성공 ({address_type}): {address} → ({lat}, {lon})")
                    return lat, lon
        except Exception as e:
            print(f"⚠️ {address_type} 타입 시도 실패: {e}")
            continue

    raise ValueError(f"주소를 좌표로 변환 실패: {address}")
```

##### _structure_exposure_data()

```python
def _structure_exposure_data(self, raw_data: Dict, lat: float, lon: float) -> Dict:
    """
    building_data_fetcher 결과 → 노출도 구조화
    """
    return {
        # 위치 정보
        'location': {
            'latitude': lat,
            'longitude': lon,
            'elevation_m': raw_data.get('elevation_m', 0),
            'land_use': self._classify_land_use(raw_data),
        },

        # 건물 기본 정보
        'building': {
            'floors_above': raw_data.get('ground_floors', 3),
            'floors_below': raw_data.get('basement_floors', 0),
            'building_type': raw_data.get('building_type', '주택'),
            'structure': raw_data.get('structure', '철근콘크리트조'),
            'build_year': raw_data.get('build_year', 1995),
            'building_age': raw_data.get('building_age', 30),
            'has_piloti': raw_data.get('has_piloti', False),
        },

        # 재난별 노출도
        'flood_exposure': {
            'distance_to_river_m': raw_data.get('distance_to_river_m', 1000),
            'distance_to_coast_m': raw_data.get('distance_to_coast_m', 50000),
            'stream_order': raw_data.get('stream_order', 3),
            'exposure_score': self._calc_flood_exposure_score(raw_data),
        },

        'heat_exposure': {
            'urban_heat_island': self._estimate_uhi_intensity(raw_data),
            'exposure_score': self._calc_heat_exposure_score(raw_data),
        },

        'typhoon_exposure': {
            'distance_to_coast_m': raw_data.get('distance_to_coast_m', 50000),
            'coastal_exposure': raw_data.get('distance_to_coast_m', 50000) < 10000,
            'exposure_score': self._calc_typhoon_exposure_score(raw_data),
        },

        # 메타데이터
        'metadata': {
            'data_source': 'building_data_fetcher',
            'data_quality': self._assess_data_quality(raw_data),
            'tcfd_warnings': raw_data.get('tcfd_warnings', []),
        }
    }
```

---

### 2.3 vulnerability_calculator.py

**역할**: 취약성(Vulnerability) 계산 - 건물이 재난에 얼마나 취약한가?

#### 클래스: VulnerabilityCalculator

```python
class VulnerabilityCalculator:
    """
    취약성 계산기

    계산 방식: Hazard + Exposure 조합으로 Vulnerability 산출
    """
```

#### 주요 메서드

##### calculate()

```python
def calculate(self, hazard: Dict, exposure: Dict) -> Dict:
    """
    9개 리스크별 취약성 계산

    Args:
        hazard: hazard_calculator 결과
        exposure: exposure_calculator 결과

    Returns:
        {
            'extreme_heat': {
                'vulnerability_score': 80,
                'vulnerability_factors': [...],
                'vulnerability_level': 'high'
            },
            ...
        }
    """
    return {
        'extreme_heat': self._calc_heat_vulnerability(
            hazard['extreme_heat'], exposure
        ),
        'extreme_cold': self._calc_cold_vulnerability(
            hazard['extreme_cold'], exposure
        ),
        'drought': self._calc_drought_vulnerability(
            hazard['drought'], exposure
        ),
        'inland_flood': self._calc_flood_vulnerability(
            hazard['inland_flood'], exposure, 'inland'
        ),
        'urban_flood': self._calc_flood_vulnerability(
            hazard['urban_flood'], exposure, 'urban'
        ),
        'coastal_flood': self._calc_flood_vulnerability(
            hazard['coastal_flood'], exposure, 'coastal'
        ),
        'typhoon': self._calc_typhoon_vulnerability(
            hazard['typhoon'], exposure
        ),
        'wildfire': self._calc_wildfire_vulnerability(
            hazard['wildfire'], exposure
        ),
        'water_stress': self._calc_water_stress_vulnerability(
            hazard['water_stress'], exposure
        ),
    }
```

##### _calc_flood_vulnerability()

```python
def _calc_flood_vulnerability(self, hazard, exposure, flood_type) -> Dict:
    """
    홍수 취약성 계산

    고려 요소:
    - 지하층 존재 여부 (+30)
    - 건물 노후도 (+20)
    - 하천 거리 (+20)
    - 침수 이력 (+10)
    - 필로티 구조 (-10)
    """
    vuln = 50  # 기본값

    factors = []

    # 1. 지하층
    basement = exposure['building']['floors_below']
    if basement > 0:
        vuln += 30
        factors.append(f"지하층 {basement}층 (+30)")

    # 2. 건물 노후도
    age = exposure['building']['building_age']
    if age > 30:
        vuln += 20
        factors.append(f"노후 건물 {age}년 (+20)")
    elif age > 20:
        vuln += 10
        factors.append(f"중고 건물 {age}년 (+10)")

    # 3. 하천 거리 (내륙 홍수만)
    if flood_type == 'inland':
        dist_river = exposure['flood_exposure']['distance_to_river_m']
        if dist_river < 100:
            vuln += 20
            factors.append(f"하천 {dist_river}m (+20)")
        elif dist_river < 500:
            vuln += 10
            factors.append(f"하천 {dist_river}m (+10)")

    # 4. 침수 이력
    flood_history = hazard.get('historical_flood_count', 0)
    if flood_history > 10:
        vuln += 10
        factors.append(f"침수 이력 {flood_history}건 (+10)")

    # 5. 필로티 구조 (배수 유리)
    if exposure['building']['has_piloti']:
        vuln -= 10
        factors.append("필로티 구조 (-10)")

    # 최대 100으로 제한
    vuln = min(vuln, 100)

    # 등급 판단
    if vuln >= 75:
        level = 'very_high'
    elif vuln >= 50:
        level = 'high'
    elif vuln >= 25:
        level = 'medium'
    else:
        level = 'low'

    return {
        'vulnerability_score': vuln,
        'vulnerability_factors': factors,
        'vulnerability_level': level
    }
```

---

## 3. 데이터 로더 모듈

### 3.1 climate_data_loader.py

**역할**: KMA SSP 시나리오 NetCDF 데이터 로드

#### 클래스: ClimateDataLoader

```python
class ClimateDataLoader:
    """
    KMA SSP 시나리오 기후 데이터 로더

    데이터 경로: Physical_RISK_calculate/data/KMA/gridraw/SSP245/yearly/
    파일 형식: NetCDF (.nc), gzip 압축
    """

    def __init__(self, base_dir=None, scenario='SSP245'):
        self.scenario = scenario
        self.kma_dir = os.path.join(base_dir, 'KMA', 'gridraw', scenario, 'yearly')
        self._cache = {}  # 캐시
```

#### 주요 메서드

##### get_extreme_heat_data()

```python
def get_extreme_heat_data(self, lat: float, lon: float, year: int = 2030) -> Dict:
    """
    극한 고온 데이터 추출

    변수: TXx, SU25, TR25, WSDIx

    Returns:
        {
            'annual_max_temp_celsius': 38.3,
            'heatwave_days_per_year': 154,
            'tropical_nights': 23,
            'heat_wave_duration': 18.2,
            'climate_scenario': 'SSP245',
            'year': 2030,
            'data_source': 'KMA_SSP_gridraw'
        }
    """
    try:
        txx = self._extract_value('TXx', lat, lon, year)
        su25 = self._extract_value('SU25', lat, lon, year)
        tr25 = self._extract_value('TR25', lat, lon, year)
        wsdix = self._extract_value('WSDIx', lat, lon, year)

        return {
            'annual_max_temp_celsius': float(txx),
            'heatwave_days_per_year': int(su25),
            'tropical_nights': int(tr25),
            'heat_wave_duration': float(wsdix),
            'climate_scenario': self.scenario,
            'year': year,
            'data_source': 'KMA_SSP_gridraw'
        }
    except Exception as e:
        # Fallback
        return self._fallback_heat_data(year)
```

##### _extract_value()

```python
def _extract_value(self, variable: str, lat: float, lon: float, year: int) -> Optional[float]:
    """
    NetCDF 파일에서 특정 위치/연도의 값 추출

    처리 과정:
    1. gzip 압축 해제
    2. 임시 파일 생성
    3. NetCDF 데이터셋 열기
    4. 좌표 → 격자 인덱스 변환
    5. 값 추출
    """
    # 1. 파일 경로
    filename = f"{self.scenario}_{variable}_gridraw_yearly_2021-2100.nc"
    filepath = os.path.join(self.kma_dir, filename)

    if not os.path.exists(filepath):
        return None

    # 2. 캐시 확인
    cache_key = f"{variable}"
    if cache_key in self._cache:
        dataset = self._cache[cache_key]
    else:
        # 3. gzip 압축 해제
        with open(filepath, 'rb') as f:
            magic = f.read(2)
            is_gzipped = (magic == b'\x1f\x8b')

        if is_gzipped:
            with gzip.open(filepath, 'rb') as gz_file:
                nc_data = gz_file.read()

            # 임시 파일 생성
            tmp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.nc')
            tmp_file.write(nc_data)
            tmp_file.close()

            # NetCDF 열기
            dataset = nc.Dataset(tmp_file.name, 'r')

            # 임시 파일 경로 저장
            if not hasattr(self, '_tmp_files'):
                self._tmp_files = []
            self._tmp_files.append(tmp_file.name)
        else:
            dataset = nc.Dataset(filepath, 'r')

        self._cache[cache_key] = dataset

    # 4. 좌표 → 격자 인덱스 변환
    lats = dataset.variables['latitude'][:]
    lons = dataset.variables['longitude'][:]
    lat_idx = np.abs(lats - lat).argmin()
    lon_idx = np.abs(lons - lon).argmin()

    # 5. 연도 인덱스 (2021-2100 → 0-79)
    year_idx = year - 2021

    # 6. 값 추출: (time, latitude, longitude)
    value = dataset.variables[variable][year_idx, lat_idx, lon_idx]

    return float(value)
```

---

### 3.2 spatial_data_loader.py

**역할**: 공간 데이터 로드 (토지피복도, NDVI, 토양수분, 행정구역)

#### 클래스: SpatialDataLoader

```python
class SpatialDataLoader:
    """
    공간 데이터 로더

    - 토지피복도: GeoTIFF
    - NDVI: MODIS HDF
    - 토양수분: SMAP HDF5
    - 행정구역: Shapefile
    """

    def __init__(self, base_dir=None):
        self.landcover_dir = os.path.join(base_dir, 'landcover', 'ME_GROUNDCOVERAGE_50000')
        self.drought_dir = os.path.join(base_dir, 'drought')
        self.geodata_dir = os.path.join(base_dir, 'geodata')

        self._landcover_cache = {}
        self._admin_boundary = None
```

#### 주요 메서드

##### get_landcover_data()

```python
def get_landcover_data(self, lat: float, lon: float) -> Dict:
    """
    토지피복도 데이터 추출

    Returns:
        {
            'landcover_type': 'urban',
            'impervious_ratio': 0.7,
            'vegetation_ratio': 0.1,
            'urban_intensity': 'high',
            'data_source': 'ME_GROUNDCOVERAGE_50000'
        }
    """
    # 1. 토지피복도 타일 찾기
    tif_files = [f for f in os.listdir(self.landcover_dir) if f.endswith('.tif')]

    value = None
    for tif_file in tif_files:
        filepath = os.path.join(self.landcover_dir, tif_file)
        with rasterio.open(filepath) as src:
            # 좌표가 타일 범위 내에 있는지 확인
            bounds = src.bounds
            if bounds.left <= lon <= bounds.right and bounds.bottom <= lat <= bounds.top:
                # 래스터 값 추출
                row, col = rowcol(src.transform, lon, lat)
                if 0 <= row < src.height and 0 <= col < src.width:
                    value = src.read(1)[row, col]
                    break

    # 2. 토지피복 분류
    if 1 <= value <= 10:      # 도시
        landcover_type = 'urban'
        impervious = 0.7
        vegetation = 0.1
        urban = 'high'
    elif 31 <= value <= 50:   # 산림
        landcover_type = 'forest'
        impervious = 0.0
        vegetation = 0.9
        urban = 'low'
    # ...

    return {
        'landcover_type': landcover_type,
        'impervious_ratio': impervious,
        'vegetation_ratio': vegetation,
        'urban_intensity': urban,
        'raw_value': int(value),
        'data_source': 'ME_GROUNDCOVERAGE_50000'
    }
```

---

### 3.3 building_data_fetcher.py

**역할**: 건축물대장 API 호출 및 데이터 수집

#### 클래스: BuildingDataFetcher

```python
class BuildingDataFetcher:
    """
    건축물대장 API 통합 데이터 수집기

    API:
    - 국토교통부 건축물대장
    - 재난안전데이터 (침수 이력, 하천 정보)
    - V-World (주소 변환)
    """

    def __init__(self):
        self.api_key = os.getenv("BUILDING_API_KEY")
```

#### 주요 메서드

##### fetch_all_building_data()

```python
def fetch_all_building_data(self, lat: float, lon: float) -> Dict:
    """
    위/경도 → 모든 건물 데이터 수집

    수집 데이터:
    - 건축물 정보 (층수, 용도, 구조, 건축연도)
    - 고도 (DEM)
    - 하천/해안 거리
    - 침수 이력
    - 하천 정보

    Returns:
        {
            'ground_floors': 5,
            'basement_floors': 1,
            'building_type': '업무시설',
            'structure': '철근콘크리트조',
            'build_year': 2006,
            'building_age': 18,
            'has_piloti': True,
            'elevation_m': 34.5,
            'distance_to_river_m': 1000,
            'distance_to_coast_m': 100000,
            'stream_order': 3,
            'flood_history_count': 54,
            'river_name': '갑천',
            'river_grade': 1,
            'watershed_area_km2': 2500,
            'tcfd_warnings': []
        }
    """
    # 1. 건축물대장 API
    building_info = self._fetch_building_info(lat, lon)

    # 2. DEM 고도 추출
    elevation_info = self._fetch_elevation(lat, lon)

    # 3. 하천/해안 거리 계산
    distance_info = self._calc_distances(lat, lon)

    # 4. 재난 이력
    disaster_info = self._fetch_disaster_history(lat, lon)

    # 5. 통합
    return {
        **building_info,
        **elevation_info,
        **distance_info,
        **disaster_info
    }
```

---

### 3.4 disaster_api_fetcher.py

**역할**: 재난안전데이터 API 호출

#### 클래스: DisasterAPIFetcher

```python
class DisasterAPIFetcher:
    """
    재난안전데이터 API

    데이터:
    - 자연재해 위험지구
    - 하천 대장
    - 재난 통계
    """
```

#### 주요 메서드

```python
def get_flood_history(self, lat: float, lon: float) -> Dict:
    """침수 이력 조회"""

def get_nearest_river_info(self, lat: float, lon: float) -> Dict:
    """하천 정보 조회"""
```

---

### 3.5 stream_order_simple.py

**역할**: DEM 고도 및 하천 차수 계산

#### 클래스: StreamOrderCalculator

```python
class StreamOrderCalculator:
    """
    DEM 기반 하천 차수 계산

    알고리즘: D8 Flow Accumulation
    """

    def __init__(self, dem_dir=None):
        self.dem_dir = Path(dem_dir) if dem_dir else Path(__file__).parent.parent / "data" / "DEM"
```

#### 주요 메서드

```python
def get_stream_order(self, lat: float, lon: float) -> Dict:
    """
    위/경도 → 고도 및 하천 차수

    Returns:
        {
            'elevation_m': 34.5,
            'stream_order': 3,
            'watershed_area_km2': 2500,
            'flow_accumulation': 5000
        }
    """
    # 1. DEM 파일 찾기
    dem_file = self.find_dem_file(lat, lon)

    # 2. 고도 추출
    elevation = self._extract_elevation(dem_file, lat, lon)

    # 3. Flow Accumulation 계산
    flow_acc = self._calc_flow_accumulation(dem_file, lat, lon)

    # 4. 하천 차수 판단
    stream_order = self._classify_stream_order(flow_acc)

    return {
        'elevation_m': elevation,
        'stream_order': stream_order,
        'flow_accumulation': flow_acc,
        'watershed_area_km2': flow_acc * 0.000025  # 5m × 5m 격자
    }
```

---

## 4. 유틸리티 모듈

### 4.1 거리 계산 (Haversine)

```python
def haversine_distance(lat1, lon1, lat2, lon2) -> float:
    """
    두 좌표 간 거리 계산 (Haversine 공식)

    Returns:
        거리 (미터)
    """
    R = 6371000  # 지구 반지름 (미터)

    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)

    a = sin(dlat/2)**2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon/2)**2
    c = 2 * atan2(sqrt(a), sqrt(1-a))

    return R * c
```

---

## 5. 의존성 관계

```
risk_calculator.py
├── hazard_calculator.py
│   ├── climate_data_loader.py
│   ├── spatial_data_loader.py
│   ├── building_data_fetcher.py
│   └── disaster_api_fetcher.py
├── exposure_calculator.py
│   └── building_data_fetcher.py
│       ├── stream_order_simple.py
│       └── disaster_api_fetcher.py
└── vulnerability_calculator.py
```

### 라이브러리 의존성

```python
# 필수
import numpy as np
import requests
import os
from typing import Dict, Tuple, Optional, Union
from pathlib import Path
from dotenv import load_dotenv

# NetCDF 처리
import netCDF4 as nc
import gzip
import tempfile

# 공간 데이터 처리
import rasterio
from rasterio.transform import rowcol
import h5py
from pyhdf.SD import SD, SDC
import geopandas as gpd
from shapely.geometry import Point

# XML 파싱 (건축물대장 API)
import xml.etree.ElementTree as ET
```

---

**문서 버전**: 1.0.0 (2024-11-24)
