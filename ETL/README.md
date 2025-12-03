# SKALA Physical Risk AI - ETL Pipeline

> 최종 수정일: 2025-12-03
> 버전: v01

---

## 개요

SKALA Physical Risk AI 시스템의 ETL(Extract, Transform, Load) 파이프라인입니다.

### ETL 구조

| ETL 유형 | 디렉토리 | 데이터 소스 | 대상 테이블 |
|----------|----------|-------------|-------------|
| **Local ETL** | `local/` | 로컬 파일 (GeoJSON, NetCDF, CSV) | 28개 |
| **API ETL** | `api/` | 외부 OpenAPI | 11개 |

---

## 디렉토리 구조

```
etl/
├── README.md                    # 이 파일
├── local/                       # Local 데이터 ETL
│   ├── .venv/                   # Python 가상환경
│   ├── requirements.txt         # Python 의존성
│   ├── logs/                    # 실행 로그
│   ├── data/                    # 원본 데이터 (DATA_DIR)
│   │   ├── N3A_G0110000/        # 행정구역 GeoJSON
│   │   ├── KMA/                 # 기상청 NetCDF
│   │   └── ...
│   └── scripts/
│       ├── utils.py             # 공통 유틸리티
│       ├── run_all.py           # 전체 실행 스크립트
│       ├── 01_load_admin_regions.py
│       ├── 02_load_weather_stations.py
│       ├── 03_load_grid_station_mappings.py
│       ├── 04_load_population.py
│       ├── 05_load_landcover.py
│       ├── 06_load_dem.py
│       ├── 07_load_drought.py
│       ├── 08_load_climate_grid.py
│       ├── 09_load_sea_level.py
│       ├── 10_load_water_stress.py
│       └── 11_load_site_data.py
│
└── api/                         # 외부 API ETL
    ├── .venv/                   # Python 가상환경
    ├── requirements.txt         # Python 의존성
    ├── logs/                    # 실행 로그
    └── scripts/
        ├── utils.py             # 공통 유틸리티 + API 클라이언트
        ├── run_all.py           # 전체 실행 스크립트
        ├── 01_load_river_info.py
        ├── 02_load_emergency_messages.py
        ├── 03_load_vworld_geocode.py
        ├── 04_load_typhoon.py
        ├── 05_load_wamis.py
        ├── 06_load_buildings.py
        ├── 15_load_disaster_yearbook.py
        └── 16_load_typhoon_besttrack.py
```

---

## 사전 요구사항

### 1. Python 환경

```bash
# Python 3.11+ 필요
python3 --version

# PostGIS 도구 (래스터 데이터용)
brew install gdal postgis  # macOS
apt install gdal-bin postgis  # Ubuntu
```

### 2. 가상환경 설정

```bash
# Local ETL
cd etl/local
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# API ETL
cd ../api
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 3. 환경변수 설정

`.env` 파일을 `db_final_1202/` 루트에 생성:

```bash
# Database
DW_HOST=localhost
DW_PORT=5434
DW_NAME=skala_datawarehouse
DW_USER=skala_dw_user
DW_PASSWORD=skala_dw_2025

# Data Directory (Local ETL)
DATA_DIR=/path/to/your/data

# API Keys (API ETL)
RIVER_API_KEY=your_key_here
EMERGENCYMESSAGE_API_KEY=your_key_here
TYPHOON_API_KEY=your_key_here
PUBLICDATA_API_KEY=your_key_here
VWORLD_API_KEY=your_key_here

# Sample Limit (테스트용)
SAMPLE_LIMIT=0  # 0이면 전체, 숫자면 제한
```

---

## 사용법

### Local ETL 실행

```bash
cd etl/local
source .venv/bin/activate
export PYTHONPATH=.

# 전체 실행
python3 scripts/run_all.py

# 특정 단계만 실행
python3 scripts/run_all.py --only 1,2,3

# 특정 단계 건너뛰기
python3 scripts/run_all.py --skip 6,7

# 단계 목록 확인
python3 scripts/run_all.py --list

# 개별 스크립트 실행
python3 scripts/01_load_admin_regions.py
python3 scripts/08_load_climate_grid.py
```

### API ETL 실행

```bash
cd etl/api
source .venv/bin/activate
export PYTHONPATH=.

# 전체 실행
python3 scripts/run_all.py

# 샘플 제한 (테스트용)
SAMPLE_LIMIT=100 python3 scripts/run_all.py

# 개별 스크립트 실행
python3 scripts/01_load_river_info.py
SAMPLE_LIMIT=10 python3 scripts/06_load_buildings.py
```

---

## Local ETL 스크립트 상세

| 순서 | 스크립트 | 대상 테이블 | 데이터 소스 | 설명 |
|------|----------|-------------|-------------|------|
| 01 | load_admin_regions.py | location_admin | N3A_G0110000/*.geojson | 시군구 행정구역 경계 |
| 02 | load_weather_stations.py | weather_stations | station_info.csv | 기상관측소 정보 |
| 03 | load_grid_station_mappings.py | grid_station_mappings | 계산 생성 | 격자-관측소 매핑 |
| 04 | load_population.py | location_admin | population.csv | 인구 데이터 업데이트 |
| 05 | load_landcover.py | raw_landcover | landcover.tif | 토지피복도 래스터 |
| 06 | load_dem.py | raw_dem | dem.tif | 수치표고모델 래스터 |
| 07 | load_drought.py | raw_drought | MODIS/*.hdf | 가뭄 지수 래스터 |
| 08 | load_climate_grid.py | location_grid, ta_data 등 | KMA/*.nc | 기후 격자 데이터 |
| 09 | load_sea_level.py | sea_level_grid, sea_level_data | KMA/sea_level.nc | 해수면 상승 데이터 |
| 10 | load_water_stress.py | water_stress_rankings | WRI/*.csv | WRI Aqueduct 데이터 |
| 11 | load_site_data.py | site_*_energy_usage | site_data.xlsx | 사업장 에너지 사용량 |

### 실행 순서 의존성

```
01 → 02 → 03 (관측소 매핑은 행정구역 후)
01 → 04 (인구 데이터는 행정구역 후)
01 → 08 (기후 데이터는 행정구역 후)
08 → 09 (해수면은 격자 생성 후)
```

---

## API ETL 스크립트 상세

| 순서 | 스크립트 | 대상 테이블 | API 소스 | 설명 |
|------|----------|-------------|----------|------|
| 01 | load_river_info.py | api_river_info | 재난안전데이터 | 하천 정보 |
| 02 | load_emergency_messages.py | api_emergency_messages | 재난안전데이터 | 긴급재난문자 |
| 03 | load_vworld_geocode.py | api_vworld_geocode | VWorld | 역지오코딩 캐시 |
| 04 | load_typhoon.py | api_typhoon_* | 기상청 | 태풍 정보/경로/TD |
| 05 | load_wamis.py | api_wamis, api_wamis_stations | WAMIS | 용수이용량/관측소 |
| 06 | load_buildings.py | api_buildings | 국토교통부 | 건축물대장 |
| 15 | load_disaster_yearbook.py | api_disaster_yearbook | 행정안전부 | 재해연보 |
| 16 | load_typhoon_besttrack.py | api_typhoon_besttrack | 기상청 | 태풍 베스트트랙 |

### API 키 요구사항

| API | 환경변수 | 발급처 |
|-----|----------|--------|
| 재난안전데이터 | RIVER_API_KEY, EMERGENCYMESSAGE_API_KEY | https://www.safetydata.go.kr |
| 기상청 태풍 | TYPHOON_API_KEY | https://apihub.kma.go.kr |
| 공공데이터포털 | PUBLICDATA_API_KEY | https://www.data.go.kr |
| VWorld | VWORLD_API_KEY | https://www.vworld.kr |
| WAMIS | (키 불필요) | http://www.wamis.go.kr |

---

## 공통 유틸리티

### utils.py 주요 함수

```python
# 로깅 설정
logger = setup_logging("script_name")

# DB 연결
conn = get_db_connection()

# 테이블 확인
exists = table_exists(conn, "table_name")
count = get_row_count(conn, "table_name")

# 데이터 적재
batch_insert(conn, "table_name", columns, data, batch_size=1000)
batch_upsert(conn, "table_name", data_list, unique_columns)

# 데이터 디렉토리 (Local ETL)
data_dir = get_data_dir()

# API 호출 (API ETL)
client = APIClient(logger)
response = client.get(url, params=params, retries=3)
```

### 로깅

로그 파일 위치:
- Local ETL: `etl/local/logs/{script_name}_{YYYYMMDD}.log`
- API ETL: `etl/api/logs/{script_name}_{YYYYMMDD}.log`

로그 형식:
```
2025-12-03 10:30:45 - load_admin_regions - INFO - 행정구역 데이터 로딩 시작
```

---

## 개발표준 준수 사항 (standard.md 기준)

### 준수 항목

| 항목 | 상태 | 비고 |
|------|------|------|
| 파일명 snake_case | O | `01_load_admin_regions.py` |
| Docstring (파일 상단) | O | 개요, 최종 수정일 포함 |
| 함수 docstring (Args/Returns/Raises) | O | Google style |
| Python logging 모듈 사용 | O | `logging.getLogger(__name__)` |
| .env 환경변수 관리 | O | `dotenv` 사용 |

### 개선 필요 항목

| 항목 | 현재 | standard.md 권장 |
|------|------|-----------------|
| 파일 버전 | 일부 누락 | `v00` 형식 명시 필요 |
| 변수 인라인 주석 | 부분적 | 모든 변수에 주석 필요 |
| 로그 포맷 | 간략 | 모듈 경로 포함 형식 권장 |

---

## 문제 해결

### DB 연결 실패

```bash
# 환경변수 확인
echo $DW_HOST $DW_PORT

# DB 컨테이너 상태 확인
docker ps | grep postgres

# 수동 연결 테스트
PGPASSWORD=skala_dw_2025 psql -h localhost -p 5434 -U skala_dw_user -d skala_datawarehouse
```

### 래스터 데이터 적재 실패

```bash
# GDAL 설치 확인
gdalinfo --version

# raster2pgsql 확인
which raster2pgsql

# PostGIS raster 확장 확인
psql -c "SELECT PostGIS_Raster_Lib_Version();"
```

### API 키 오류

```bash
# 환경변수 로드 확인
python3 -c "from dotenv import load_dotenv; load_dotenv('../.env'); import os; print(os.getenv('RIVER_API_KEY'))"

# API 직접 테스트
curl "https://www.safetydata.go.kr/V2/api/DSSP-IF-10720?serviceKey=YOUR_KEY&returnType=json&pageNo=1&numOfRows=1"
```

### 메모리 부족 (기후 데이터)

```bash
# 샘플 제한으로 테스트
SAMPLE_LIMIT=1000 python3 scripts/08_load_climate_grid.py

# 배치 크기 조정 (utils.py)
batch_insert(conn, table, columns, data, batch_size=500)  # 기본 1000 → 500
```

---

## 데이터 검증

### 적재 결과 확인

```sql
-- 테이블별 레코드 수
SELECT 'location_admin' as tbl, COUNT(*) as cnt FROM location_admin
UNION ALL
SELECT 'location_grid', COUNT(*) FROM location_grid
UNION ALL
SELECT 'ta_data', COUNT(*) FROM ta_data
UNION ALL
SELECT 'api_river_info', COUNT(*) FROM api_river_info;
```

### 공간 데이터 검증

```sql
-- 행정구역 경계 확인
SELECT admin_name, ST_Area(geom) as area_m2
FROM location_admin
WHERE level = 2
LIMIT 5;

-- 격자 범위 확인
SELECT MIN(longitude), MAX(longitude), MIN(latitude), MAX(latitude)
FROM location_grid;
```

---

## 참고 문서

- [DB README](../db/README.md) - 데이터베이스 구조
- [통합 ERD](../db/sql/erd.md) - 테이블 상세 설명
- [standard.md](../standard.md) - 개발표준 정의

---

*문서 작성: Claude Code*
*최종 수정: 2025-12-03*
