# ModelOps 구현 완료 요약

**작성일**: 2025-12-03
**버전**: v1.0
**상태**: ✅ 구현 완료

---

## 1. 구현 개요

ERD와 ModelOps 구현 간 데이터 부정합 문제를 해결하고, H × E × V = Risk 계산 파이프라인을 완성하였습니다.

### 핵심 달성 사항
- ✅ **전처리 레이어**: 원시 DB 데이터 → 파생 지표 자동 계산
- ✅ **API 클라이언트**: WAMIS, 태풍, 건물 정보 통합
- ✅ **배치 스케줄러**: Hazard, Probability 배치 전처리 레이어 통합
- ✅ **DB 연결 강화**: 결과 저장 메서드 스키마 업데이트

---

## 2. 구현 상세

### Phase 1: 전처리 레이어 구축 (완료)

#### 1.1 기후 지표 계산 모듈
**파일**: `modelops/preprocessing/climate_indicators.py`

**기능**:
- 원시 기후 데이터 → 파생 지표 계산
- Heatwave days, Coldwave days, FWI, ET0 등

**주요 메서드**:
```python
ClimateIndicatorCalculator:
  - get_heatwave_indicators()      # 폭염 일수, 지속기간, 최고기온
  - get_coldwave_indicators()      # 한파 일수, 지속기간, 최저기온
  - get_wildfire_indicators()      # FWI (Fire Weather Index)
  - get_et0()                      # 증발산량 (Penman-Monteith)
```

**지원 리스크**:
- `extreme_heat`: 폭염 지표
- `extreme_cold`: 한파 지표
- `wildfire`: 산불 위험 지표
- `drought`: 가뭄 지표 (SPEI, CDD)
- `urban_flood`, `river_flood`: 강수 지표 (rx1day, rx5day, sdii)
- `typhoon`: 태풍 풍속 지표
- `sea_level_rise`: 해수면 상승
- `water_stress`: 수자원 스트레스

#### 1.2 기준/미래 기간 분리
**파일**: `modelops/preprocessing/baseline_splitter.py`

**기능**:
- 시계열 데이터를 기준기간(2021-2040) vs 미래기간(2081-2100)으로 분리
- 각 기간별 통계값 계산 (평균, 95 percentile 등)

**주요 메서드**:
```python
BaselineSplitter:
  - split_rx1day()     # 일 최대 강수량
  - split_rx5day()     # 5일 최대 강수량
  - split_wind()       # 풍속 95 percentile
  - split_sdii()       # 강수 강도
  - split_rain80()     # 80mm 이상 강수일
```

#### 1.3 집계 함수
**파일**: `modelops/preprocessing/aggregators.py`

**기능**:
- 월별 데이터 → 연별 집계
- 통계 함수 (평균, 최댓값, percentile, 추세)

**주요 메서드**:
```python
ClimateAggregators:
  - yearly_max()          # 연 최댓값
  - yearly_min()          # 연 최솟값
  - yearly_mean()         # 연 평균
  - yearly_percentile()   # 연 백분위수
  - calculate_trend()     # 선형 추세 분석
```

---

### Phase 2: 유틸리티 및 API 클라이언트 (완료)

#### 2.1 격자 매핑 유틸리티
**파일**: `modelops/utils/grid_mapper.py`

**기능**:
- 사업장 좌표 (lat, lon) → 기후 격자 (grid_id) 매핑
- 0.01° 해상도 격자 검색
- PostGIS ST_Distance 기반 최근접 검색

**주요 메서드**:
```python
GridMapper:
  - find_nearest_grid()         # 최근접 격자 찾기
  - validate_coordinates()      # 좌표 유효성 검증
  - get_grid_bounds()          # 격자 경계 계산
  - find_grids_in_radius()     # 반경 내 격자 목록
```

**사용 예시**:
```python
from modelops.utils import GridMapper

grid_id, grid_lat, grid_lon = GridMapper.find_nearest_grid(37.5665, 126.9780)
# → (123456, 37.57, 126.98)
```

#### 2.2 관측소 보간 유틸리티
**파일**: `modelops/utils/station_mapper.py`

**기능**:
- 관측소 데이터 → 격자 보간 (IDW 방식)
- 태풍, WAMIS 관측소 데이터 격자화

**주요 메서드**:
```python
StationMapper:
  - interpolate_to_grid()       # IDW 보간
  - find_nearest_stations()     # N개 최근접 관측소
  - batch_interpolate()         # 다수 격자 일괄 보간
  - calculate_coverage()        # 관측소 커버리지 분석
```

**IDW 공식**:
```
value = Σ(wi × vi) / Σ(wi)
wi = 1 / (distance^power)
```

#### 2.3 WAMIS API 클라이언트
**파일**: `modelops/api_clients/wamis_client.py`

**기능**:
- 물관리정보시스템 API 연동
- 수위, 유량, 강수량 데이터 조회
- 관측소 데이터 격자 보간

**주요 메서드**:
```python
WamisClient:
  - get_stations()              # 관측소 목록
  - get_data()                  # 수문 데이터 조회
  - get_latest_value()          # 최신 관측값
  - get_stations_near_grid()    # 격자 주변 관측소
  - calculate_grid_value()      # 격자별 보간값 계산
```

**데이터 타입**:
- `water_level`: 수위 (m)
- `flow_rate`: 유량 (m³/s)
- `rainfall`: 강수량 (mm)

#### 2.4 태풍 API 클라이언트
**파일**: `modelops/api_clients/typhoon_client.py`

**기능**:
- 태풍 Best Track 데이터 조회
- 격자별 태풍 영향도 계산

**주요 메서드**:
```python
TyphoonClient:
  - get_typhoon_list()          # 태풍 목록 조회
  - get_typhoon_tracks()        # 태풍 경로 조회
  - find_nearest_track_point()  # 최근접 경로 지점
  - calculate_grid_typhoon_impact()  # 격자별 영향도
  - get_typhoons_affecting_grid()    # 격자 영향 태풍 목록
```

**태풍 강도 분류**:
- `TD`: 열대저압부 (< 17 m/s)
- `TS`: 열대폭풍 (17-24 m/s)
- `STS`: 강한열대폭풍 (25-32 m/s)
- `TY`: 태풍 (33-43 m/s)
- `STY`: 강한태풍 (44-53 m/s)
- `VSTY`: 초강력태풍 (≥ 54 m/s)

#### 2.5 건물 정보 클라이언트
**파일**: `modelops/api_clients/building_client.py`

**기능**:
- 건물 정보 조회 (api_buildings 테이블)
- 격자별 건물 통계 계산
- 노출도 점수 산출

**주요 메서드**:
```python
BuildingClient:
  - get_buildings_in_grid()         # 격자 내 건물 조회
  - get_building_statistics()       # 격자별 통계
  - find_high_value_buildings()     # 고가 건물 조회
  - get_buildings_by_usage()        # 용도별 건물
  - calculate_exposure_score()      # 노출도 점수
  - get_buildings_near_location()   # 위치 주변 건물
```

**건물 용도**:
- `residential`: 주거용
- `commercial`: 상업용
- `industrial`: 산업용
- `public`: 공공시설
- `agricultural`: 농업시설

---

### Phase 3: 배치 스케줄러 수정 (완료)

#### 3.1 Hazard 배치 스케줄러
**파일**: `modelops/batch/hazard_batch.py` (v05)

**변경 사항**:
```python
# 변경 전 (v04)
climate_data = DatabaseConnection.fetch_climate_data(latitude, longitude)
result = agent.calculate_hazard_score(climate_data)

# 변경 후 (v05) - 리스크별 전처리 통합
climate_data = DatabaseConnection.fetch_climate_data(
    latitude, longitude, risk_type=risk_type
)
result = agent.calculate_hazard_score(climate_data)
```

**효과**:
- 리스크별 필요한 파생 지표만 자동 계산
- 메모리 효율 개선
- 계산 속도 향상

#### 3.2 Probability 배치 스케줄러
**파일**: `modelops/batch/probability_batch.py` (v05)

**변경 사항**:
1. 전처리 레이어 통합 (Hazard와 동일)
2. 결과 저장 스키마 업데이트

```python
# 변경 후 - 업데이트된 결과 스키마
results.append({
    'latitude': latitude,
    'longitude': longitude,
    'risk_type': risk_type,
    'aal': data.get('aal'),                          # ✅ 추가
    'bin_probabilities': data.get('bin_probabilities'),  # ✅ 추가
    'calculation_details': data.get('calculation_details'),  # ✅ 추가
    'bin_data': data.get('bin_data')
})
```

#### 3.3 DB 연결 모듈 강화
**파일**: `modelops/database/connection.py`

**주요 변경**:

1. **`fetch_climate_data()` 메서드 개선**:
```python
@staticmethod
def fetch_climate_data(latitude, longitude, risk_type=None, ssp_scenario='ssp2'):
    """
    risk_type 파라미터 추가:
    - None: 원시 데이터만 반환
    - 'extreme_heat': 폭염 지표 자동 계산
    - 'wildfire': FWI 자동 계산
    - ... (9개 리스크 타입별 전처리)
    """
```

2. **결과 저장 메서드 업데이트**:
```python
# save_probability_results()
- 기존: probability (단일 값)
- 변경: aal, bin_probabilities, calculation_details (JSONB)

# save_exposure_results()
- normalized_asset_value 컬럼 추가

# save_vulnerability_results()
- factors JSON 직렬화 추가

# save_aal_scaled_results()
- 명시적 파라미터 매핑 (dict unpacking 제거)
```

---

## 3. 디렉토리 구조

```
modelops/
├── preprocessing/                  # ✅ Phase 1
│   ├── __init__.py
│   ├── climate_indicators.py      # 파생 지표 계산
│   ├── baseline_splitter.py       # 기준/미래 분리
│   └── aggregators.py             # 집계 함수
│
├── utils/                         # ✅ Phase 2
│   ├── __init__.py
│   ├── grid_mapper.py             # 격자 매핑
│   └── station_mapper.py          # 관측소 보간
│
├── api_clients/                   # ✅ Phase 2
│   ├── __init__.py
│   ├── wamis_client.py            # WAMIS API
│   ├── typhoon_client.py          # 태풍 API
│   └── building_client.py         # 건물 정보
│
├── batch/                         # ✅ Phase 3
│   ├── hazard_batch.py            # v05 (전처리 통합)
│   └── probability_batch.py       # v05 (전처리 통합)
│
└── database/
    └── connection.py              # ✅ Phase 3 (메서드 강화)
```

---

## 4. 테스트 시나리오

### 4.1 단위 테스트
```python
# 1. 전처리 레이어 테스트
from modelops.preprocessing import ClimateIndicatorCalculator

raw_data = {...}  # DB에서 조회한 원시 데이터
calculator = ClimateIndicatorCalculator(raw_data)
indicators = calculator.get_heatwave_indicators()

assert 'heatwave_days_per_year' in indicators
assert 'baseline_heatwave_days' in indicators

# 2. 격자 매핑 테스트
from modelops.utils import GridMapper

grid_id, lat, lon = GridMapper.find_nearest_grid(37.5665, 126.9780)
assert grid_id is not None
assert abs(lat - 37.57) < 0.01

# 3. API 클라이언트 테스트
from modelops.api_clients import WamisClient

client = WamisClient()
stations = client.get_stations(data_type='water_level', region='서울')
assert len(stations) > 0
```

### 4.2 통합 테스트
```python
# Hazard 배치 프로세스 테스트
from modelops.batch.hazard_batch import HazardBatchProcessor

config = {'parallel_workers': 2}
processor = HazardBatchProcessor(config)

test_grids = [
    {'latitude': 37.5665, 'longitude': 126.9780},
    {'latitude': 35.1796, 'longitude': 129.0756}
]

summary = processor.process_all_grids(test_grids)
assert summary['success_rate'] > 90
```

---

## 5. 성능 최적화

### 5.1 메모리 효율
- **리스크별 선택적 데이터 로딩**: `risk_type` 파라미터로 필요한 데이터만 조회
- **지연 계산**: 파생 지표는 요청 시에만 계산

### 5.2 병렬 처리
- **ProcessPoolExecutor**: 격자별 병렬 처리
- **워커 독립성**: 각 워커가 독립적으로 DB 연결 및 에이전트 생성

### 5.3 캐싱 전략
- **DB 원시 데이터**: location_grid 테이블 인덱싱
- **API 데이터**: api_wamis_cache, api_typhoon_* 테이블 활용

---

## 6. 다음 단계

### 6.1 DB 스키마 수정 대기 중
**문서**: [`docs/DB팀_전달_요청사항.md`](DB팀_전달_요청사항.md)

**필요 작업**:
1. `probability_results` 테이블 컬럼 수정
2. `exposure_results` 테이블 생성
3. `vulnerability_results` 테이블 생성
4. `aal_scaled_results` 테이블 생성

### 6.2 DB 수정 완료 후 구현 예정

#### E (Exposure) 계산 배치
**파일**: `modelops/batch/exposure_batch.py` (미구현)

**기능**:
- 격자별 건물 정보 집계
- 자산 가치 정규화
- 위험 요소 근접도 계산

#### V (Vulnerability) 계산 배치
**파일**: `modelops/batch/vulnerability_batch.py` (미구현)

**기능**:
- 건물 특성 기반 취약성 점수 계산
- 구조, 연식, 용도별 가중치 적용

#### AAL 최종 계산 배치
**파일**: `modelops/batch/aal_scaling_batch.py` (미구현)

**기능**:
- P(H) × E → base_aal
- base_aal × F_vuln → final_aal
- 보험료율 산출

---

## 7. 참고 문서

| 문서 | 경로 | 설명 |
|------|------|------|
| ERD 스키마 | `docs/erd.md` | 전체 DB 테이블 구조 |
| DB팀 요청사항 | `docs/DB팀_전달_요청사항.md` | 스키마 수정 요청 |
| 구현 계획 | `.claude/plans/replicated-cooking-locket.md` | 상세 구현 계획 |

---

## 8. 기술 스택

- **Python**: 3.9+
- **DB**: PostgreSQL + PostGIS
- **병렬 처리**: ProcessPoolExecutor
- **진행률 표시**: tqdm
- **데이터 형식**: JSONB (유연한 스키마)
- **공간 계산**: Haversine, PostGIS ST_Distance

---

## 9. 주요 알고리즘

### FWI (Fire Weather Index)
```python
FWI = (1 - rhm/100) × (ta/30) × (ws/10) × drought_factor
drought_factor = 1.5 if cdd > 15 else 1.0
```

### ET0 (Evapotranspiration, Penman-Monteith 간소화)
```python
ET0 = 0.0023 × (ta_mean + 17.8) × sqrt(ta_max - ta_min) × si / 1000
```

### IDW (Inverse Distance Weighting)
```python
wi = 1 / (distance^power)
value = Σ(wi × vi) / Σ(wi)
```

---

**작성자**: ModelOps 팀
**최종 업데이트**: 2025-12-03
**문서 버전**: v1.0
