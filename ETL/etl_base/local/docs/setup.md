# SKALA ETL - 설치 가이드

SKALA ETL 파이프라인의 완전한 설치 및 구성 가이드입니다.

## 목차

- [사전 요구사항](#사전-요구사항)
- [설치](#설치)
- [구성](#구성)
- [데이터 준비](#데이터-준비)
- [테스트](#테스트)
- [문제 해결](#문제-해결)

## 사전 요구사항

### 필수 소프트웨어

1. **Python 3.9 이상**
   ```bash
   python --version
   # 출력 예시: Python 3.9.x 이상
   ```

2. **PostgreSQL 16 with PostGIS 3.4**
   - SKALA Datawarehouse가 실행 중이어야 합니다
   - 다운로드: [skala-database](https://github.com/your-org/skala-database)
   ```bash
   # Datawarehouse 실행 확인
   docker ps | grep skala_datawarehouse
   ```

3. **GDAL 3.0 이상** (raster 데이터 처리용)
   ```bash
   # macOS
   brew install gdal postgis
   gdal-config --version
   # 출력 예시: 3.12.0 이상

   # Linux (Ubuntu/Debian)
   sudo apt-get install gdal-bin libgdal-dev
   gdal-config --version

   # Linux (CentOS/RHEL)
   sudo yum install gdal gdal-devel
   gdal-config --version
   ```

   **필요한 GDAL 도구:** `gdal_translate`, `gdalinfo`, `raster2pgsql`

   **사용되는 ETL 스크립트:**
   - `load_landcover.py` - 토지피복 GeoTIFF 데이터 처리
   - `load_dem.py` - 디지털 고도 모델 ASCII grid 처리
   - `load_drought.py` - 가뭄 지수 HDF5 데이터 처리

4. **uv (권장) 또는 pip**
   ```bash
   # uv 설치 (pip보다 빠른 대안)
   curl -LsSf https://astral.sh/uv/install.sh | sh

   # 또는 pip 사용 (Python과 함께 제공됨)
   pip --version
   ```

### 시스템 요구사항

| 구성 요소 | 최소 사양 | 권장 사양 |
|-----------|---------|-------------|
| CPU | 2 코어 | 4+ 코어 |
| RAM | 8 GB | 16+ GB |
| 디스크 공간 | 50 GB 여유 | 200+ GB 여유 |
| OS | Linux, macOS, Windows 10+ | Linux, macOS |

### 네트워크 액세스

ETL 스크립트는 Datawarehouse에 대한 네트워크 액세스가 필요합니다:
- **호스트**: localhost (또는 원격 호스트)
- **포트**: 5433 (기본 Datawarehouse 포트)
- **프로토콜**: PostgreSQL wire protocol

연결 테스트:
```bash
psql -h localhost -p 5433 -U skala_dw_user -d skala_datawarehouse -c "SELECT 1"
```

## 설치

### 1단계: 저장소 클론

```bash
git clone https://github.com/your-org/skala-etl.git
cd skala-etl
```

### 2단계: 가상 환경 생성

**옵션 A: uv 사용 (권장 - 더 빠름)**

```bash
# 가상 환경 생성
uv venv

# 가상 환경 활성화
source .venv/bin/activate  # macOS/Linux
# 또는
.venv\Scripts\activate  # Windows

# 의존성 설치
uv pip install -r requirements.txt
```

**옵션 B: pip 사용**

```bash
# 가상 환경 생성
python -m venv .venv

# 가상 환경 활성화
source .venv/bin/activate  # macOS/Linux
# 또는
.venv\Scripts\activate  # Windows

# pip 업그레이드
pip install --upgrade pip

# 의존성 설치
pip install -r requirements.txt
```

### 3단계: 설치 확인

```bash
# GDAL 도구 확인
gdal-config --version
gdalinfo --version
which raster2pgsql

# Python 패키지 확인
python -c "import psycopg2, geopandas, netCDF4, rasterio; print('모든 패키지가 설치되었습니다')"

# 예상 출력:
# GDAL 3.x.x
# GDAL 3.x.x, released ...
# /opt/homebrew/bin/raster2pgsql (macOS) 또는 /usr/bin/raster2pgsql (Linux)
# 모든 패키지가 설치되었습니다
```

### 4단계: 환경 설정

1. **환경 변수 템플릿 복사:**
```bash
cp .env.example .env
```

2. **`.env` 파일 편집:**
```bash
# 선호하는 에디터 사용
nano .env
# 또는
vim .env
# 또는
code .env
```

3. **Datawarehouse 연결 구성:**
```bash
# Datawarehouse 데이터베이스 연결
DW_HOST=localhost          # Datawarehouse가 원격 서버에 있으면 변경
DW_PORT=5433               # 기본 Datawarehouse 포트
DW_NAME=skala_datawarehouse
DW_USER=skala_dw_user
DW_PASSWORD=안전한_비밀번호로_변경  # ⚠️ 중요: 변경 필수!

# 데이터 디렉토리
DATA_DIR=./data            # 데이터 파일 위치
LOGS_DIR=./logs            # 로그 저장 위치

# 로깅 레벨
LOG_LEVEL=INFO             # DEBUG, INFO, WARNING, ERROR
```

**보안 참고사항:**
- `.env` 파일을 **절대 버전 관리에 커밋하지 말것**
- 개발과 프로덕션에 **다른 비밀번호** 사용
- 프로덕션 자격 증명은 안전한 비밀번호 관리자에 저장

## 데이터 준비

### 데이터 디렉토리 구조

다음 디렉토리 구조 생성:

```bash
mkdir -p data/administrative_regions
mkdir -p data/climate/monthly_grid
mkdir -p data/climate/yearly_grid
mkdir -p data/climate/sea_level
mkdir -p data/climate/sgg261
mkdir -p data/population
mkdir -p data/raster/dem
mkdir -p data/raster/landcover
mkdir -p data/raster/drought
mkdir -p logs
```

### 필수 데이터 파일

적절한 디렉토리에 데이터 파일 배치:

**1. 행정구역** (필수)
```
data/administrative_regions/
└── emd_5174.shp            # 한국 행정구역 경계
    emd_5174.shx
    emd_5174.dbf
    emd_5174.prj
    emd_5174.cpg
```

**2. 인구 데이터** (선택)
```
data/population/
└── population_projections.xlsx  # 지역별 인구 예측
```

**3. 기후 데이터 - 해수면** (해수면 분석에 필수)
```
data/climate/sea_level/
├── SSP126_SeaLevel_2015-2100.nc
├── SSP245_SeaLevel_2015-2100.nc
├── SSP370_SeaLevel_2015-2100.nc
└── SSP585_SeaLevel_2015-2100.nc
```

**4. 기후 데이터 - 일별 (TAMAX/TAMIN)**
```
data/climate/sgg261/
├── SSP126_TAMAX_sgg261_yearly_2021-2100.asc  # tar.gz 형식
├── SSP126_TAMIN_sgg261_yearly_2021-2100.asc
├── SSP245_TAMAX_sgg261_yearly_2021-2100.asc
├── SSP245_TAMIN_sgg261_yearly_2021-2100.asc
├── SSP370_TAMAX_sgg261_yearly_2021-2100.asc
├── SSP370_TAMIN_sgg261_yearly_2021-2100.asc
├── SSP585_TAMAX_sgg261_yearly_2021-2100.asc
└── SSP585_TAMIN_sgg261_yearly_2021-2100.asc
```

**5. 기후 데이터 - 월별 격자**
```
data/climate/monthly_grid/
├── TA_SSP126_monthly_2021-2100.nc   # 기온
├── TA_SSP245_monthly_2021-2100.nc
├── TA_SSP370_monthly_2021-2100.nc
├── TA_SSP585_monthly_2021-2100.nc
├── RN_SSP126_monthly_2021-2100.nc   # 강수량
├── RN_SSP245_monthly_2021-2100.nc
├── RN_SSP370_monthly_2021-2100.nc
├── RN_SSP585_monthly_2021-2100.nc
# ... (WS, RHM, SI, SPEI12)
```

**6. 기후 데이터 - 연별 격자**
```
data/climate/yearly_grid/
├── CSDI_SSP126_yearly_2021-2100.nc
├── CSDI_SSP245_yearly_2021-2100.nc
# ... (WSDI, RX1DAY, RX5DAY, CDD, RAIN80, SDII, TA)
```

**7. 래스터 데이터 - 토지피복**
```
data/raster/landcover/
└── *.tif  # 240개 GeoTIFF 파일
```

**8. 래스터 데이터 - DEM**
```
data/raster/dem/
└── *.asc  # 44개 ASCII grid 파일
```

**9. 래스터 데이터 - 가뭄**
```
data/raster/drought/
├── MODIS_drought_2020-2024.h5
└── SMAP_drought_2020-2024.h5
```

### 데이터 출처

| 데이터 유형 | 출처 | 형식 | 크기 |
|-----------|--------|--------|------|
| 행정구역 경계 | 통계청 SGIS | Shapefile | ~50 MB |
| 인구 | 통계청 | Excel | <1 MB |
| 기후 (SSP) | 기상청 | NetCDF | ~500 GB |
| 해수면 | 기상청 | NetCDF | ~100 MB |
| 토지피복 | 환경부 | GeoTIFF | ~500 GB |
| DEM | 국토지리정보원 | ASCII | ~10 GB |
| 가뭄 | NASA MODIS/SMAP | HDF5 | ~5 GB |

## 테스트

### 샘플 데이터로 빠른 테스트

데이터 유형별 10개 샘플로 ETL 파이프라인 테스트:

```bash
# 샘플 모드 설정
export SAMPLE_LIMIT=10
export PYTHONPATH=.

# 테스트 스크립트 실행
chmod +x test_sample_load.sh
./test_sample_load.sh
```

**예상 출력:**
```
🧪 SKALA ETL 샘플 로드 테스트
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📍 SAMPLE_LIMIT=10 설정
✅ 샘플 모드 활성화됨

🗺️  행정구역 로드 중 (10개 샘플)
✅ 271개 지역 로드됨 (10개 읍면동 + 261개 자동 생성 시군구)

🌊 해수면 데이터 로드 중 (10개 샘플)
✅ 10개 격자점과 10개 데이터 행 로드됨

🌡️  TAMAX/TAMIN 데이터 로드 중 (10개 샘플)
✅ TAMAX 10행 로드됨
✅ TAMIN 10행 로드됨

📊 월별 격자 데이터 로드 중 (10개 샘플)
✅ TA: 40행 (4 SSP × 10)
✅ RN: 40행 (4 SSP × 10)
✅ WS: 40행 (4 SSP × 10)
✅ RHM: 40행 (4 SSP × 10)
✅ SI: 40행 (4 SSP × 10)
✅ SPEI12: 40행 (4 SSP × 10)

🎉 모든 샘플 데이터가 성공적으로 로드되었습니다!
```

### 수동 테스트

개별 스크립트 테스트:

```bash
# 환경 설정
export SAMPLE_LIMIT=10
export PYTHONPATH=.

# 행정구역 테스트
python scripts/load_admin_regions.py

# 해수면 데이터 테스트
python scripts/load_sea_level_netcdf.py

# TAMAX/TAMIN 테스트
python scripts/load_sgg261_data.py

# 월별 격자 데이터 테스트
python scripts/load_monthly_grid_data.py
```

### 로드된 데이터 확인

```bash
# Datawarehouse 접속
docker exec -it skala_datawarehouse psql -U skala_dw_user -d skala_datawarehouse

# 행 개수 확인
SELECT 'location_admin', COUNT(*) FROM location_admin
UNION ALL
SELECT 'location_grid', COUNT(*) FROM location_grid
UNION ALL
SELECT 'sea_level_grid', COUNT(*) FROM sea_level_grid
UNION ALL
SELECT 'tamax_data', COUNT(*) FROM tamax_data
UNION ALL
SELECT 'ta_data', COUNT(*) FROM ta_data
UNION ALL
SELECT 'rn_data', COUNT(*) FROM rn_data;
```

**예상 결과 (샘플 모드):**
```
 location_admin  | 271   (10 + 261 자동 생성)
 location_grid   | 10
 sea_level_grid  | 10
 tamax_data      | 10
 ta_data         | 40    (4 SSP × 10)
 rn_data         | 40    (4 SSP × 10)
```

## 문제 해결

### 문제 1: psycopg2 설치 오류

**오류:**
```
Error: pg_config executable not found
```

**해결 방법 (macOS):**
```bash
# PostgreSQL 클라이언트 설치
brew install postgresql

# 또는 바이너리 패키지 사용
pip install psycopg2-binary
```

**해결 방법 (Linux):**
```bash
# Ubuntu/Debian
sudo apt-get install libpq-dev python3-dev

# CentOS/RHEL
sudo yum install postgresql-devel python3-devel

# 그 다음 psycopg2 설치
pip install psycopg2
```

**해결 방법 (Windows):**
```bash
# 바이너리 패키지 사용
pip install psycopg2-binary
```

### 문제 2: GDAL/Rasterio 설치 오류

**오류:**
```
ERROR: Failed building wheel for rasterio
```

**해결 방법 (macOS):**
```bash
# GDAL 설치
brew install gdal

# rasterio 설치
pip install rasterio
```

**해결 방법 (Linux):**
```bash
# Ubuntu/Debian
sudo apt-get install gdal-bin libgdal-dev

# GDAL 버전 설정
export GDAL_VERSION=$(gdal-config --version)
pip install GDAL==$GDAL_VERSION
pip install rasterio
```

**해결 방법 (Windows):**
```bash
# 미리 빌드된 휠 다운로드
# https://www.lfd.uci.edu/~gohlke/pythonlibs/#rasterio
pip install rasterio-1.3.x-cpxx-cpxx-win_amd64.whl
```

### 문제 3: NetCDF4 설치 오류

**해결 방법 (macOS):**
```bash
brew install netcdf hdf5
pip install netCDF4
```

**해결 방법 (Linux):**
```bash
sudo apt-get install libnetcdf-dev libhdf5-dev
pip install netCDF4
```

### 문제 4: Datawarehouse 연결 실패

**오류:**
```
psycopg2.OperationalError: could not connect to server
```

**해결 방법:**
```bash
# 1. Datawarehouse 실행 확인
docker ps | grep skala_datawarehouse

# 2. 실행 중이 아니면 시작
cd ../db
./start_databases.sh

# 3. .env에서 연결 설정 확인
cat .env | grep DW_

# 4. 수동으로 연결 테스트
psql -h localhost -p 5433 -U skala_dw_user -d skala_datawarehouse
```

### 문제 5: 스크립트 권한 거부

**오류:**
```
-bash: ./test_sample_load.sh: Permission denied
```

**해결 방법:**
```bash
chmod +x *.sh
chmod +x scripts/*.sh
```

### 문제 6: 데이터 파일을 찾을 수 없음

**오류:**
```
FileNotFoundError: data/climate/monthly_grid/TA_*.nc
```

**해결 방법:**
```bash
# 1. 데이터 디렉토리 구조 확인
ls -R data/

# 2. .env에서 DATA_DIR 확인
echo $DATA_DIR

# 3. 필요시 DATA_DIR 업데이트
export DATA_DIR=/path/to/your/data

# 4. 또는 파일을 예상 위치로 이동
mkdir -p data/climate/monthly_grid
mv /path/to/*.nc data/climate/monthly_grid/
```

### 문제 7: 메모리 부족

**오류:**
```
MemoryError: Unable to allocate array
```

**해결 방법:**
```bash
# 1. 테스트에 샘플 모드 사용
export SAMPLE_LIMIT=10

# 2. 다른 애플리케이션을 닫아 메모리 확보

# 3. 시스템 스왑 공간 증가 (Linux)
sudo dd if=/dev/zero of=/swapfile bs=1G count=8
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile

# 4. 전체 로드를 위해 더 많은 RAM이 있는 머신 사용 (16GB+)
```

### 문제 8: 트랜잭션 중단 오류

**오류:**
```
InFailedSqlTransaction: current transaction is aborted
```

**해결 방법:**
모든 스크립트에 자동 `conn.rollback()` 포함. 여전히 오류가 발생하면:

```python
# psql에서:
ROLLBACK;

# 또는 스크립트 재시작 - 자동으로 롤백됨
python scripts/load_admin_regions.py
```

## 고급 구성

### 사용자 정의 데이터 경로

`.env`에서 경로 수정:

```bash
# 외부 데이터 디렉토리 지정
DATA_DIR=/mnt/external/skala_data

# 다른 로그 위치 사용
LOGS_DIR=/var/log/skala_etl
```

### 데이터베이스 연결 풀링

여러 스크립트에서 더 나은 성능:

```python
# scripts/db_config.py에서
from psycopg2 import pool

db_pool = pool.SimpleConnectionPool(
    minconn=1,
    maxconn=10,
    host=os.getenv("DW_HOST"),
    port=os.getenv("DW_PORT"),
    dbname=os.getenv("DW_NAME"),
    user=os.getenv("DW_USER"),
    password=os.getenv("DW_PASSWORD")
)
```

### 병렬 처리

독립적인 데이터셋의 빠른 로딩:

```bash
# 여러 스크립트를 병렬로 실행
python scripts/load_admin_regions.py &
python scripts/load_population.py &
python scripts/load_sea_level_netcdf.py &
wait
```

### 로깅 구성

스크립트에서 로깅 사용자 정의:

```python
import logging

logging.basicConfig(
    level=logging.DEBUG,  # 더 상세하게
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/debug.log'),
        logging.StreamHandler()
    ]
)
```

## 다음 단계

설치 완료 후:

1. ✅ ETL 환경 준비 완료
2. ⏭️ 샘플 테스트 실행: `./test_sample_load.sh`
3. ⏭️ 전체 데이터 로드: [USAGE.md](USAGE.md) 참조
4. ⏭️ Datawarehouse에서 데이터 검증
5. ⏭️ FastAPI를 로드된 데이터에 연결

## 지원

여기에서 다루지 않은 문제:

1. 일반 작업은 [USAGE.md](USAGE.md) 확인
2. [GitHub Issues](https://github.com/your-org/skala-etl/issues) 검토
3. 의존성 문서 확인:
   - [psycopg2](https://www.psycopg.org/docs/)
   - [geopandas](https://geopandas.org/)
   - [netCDF4-python](https://unidata.github.io/netcdf4-python/)
   - [rasterio](https://rasterio.readthedocs.io/)
4. SKALA 팀에 문의

---

**설치 완료! ETL 파이프라인이 데이터 로딩 준비가 되었습니다.**
