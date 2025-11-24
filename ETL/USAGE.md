# SKALA ETL - 사용 가이드

SKALA ETL 파이프라인의 일반적인 작업 및 사용 사례입니다.

## 목차

- [빠른 참조](#빠른-참조)
- [데이터 로딩](#데이터-로딩)
- [데이터 검증](#데이터-검증)
- [진행 상황 모니터링](#진행-상황-모니터링)
- [일반적인 워크플로우](#일반적인-워크플로우)
- [문제 해결](#문제-해결)
- [성능 최적화](#성능-최적화)

## 빠른 참조

### 환경 설정

```bash
# 가상 환경 활성화
source .venv/bin/activate

# Python 경로 설정
export PYTHONPATH=.

# 선택사항: 테스트를 위한 샘플 모드 설정
export SAMPLE_LIMIT=10
```

### 주요 명령어

```bash
# 10개 샘플로 테스트
./test_sample_load.sh

# 모든 행정구역 로드
python scripts/load_admin_regions.py

# 해수면 데이터 로드
python scripts/load_sea_level_netcdf.py

# 일별 기온 데이터 로드 (TAMAX/TAMIN)
python scripts/load_sgg261_data.py

# 월별 기후 격자 데이터 로드
python scripts/load_monthly_grid_data.py

# 로드된 데이터 확인
docker exec -it skala_datawarehouse psql -U skala_dw_user -d skala_datawarehouse -c "SELECT COUNT(*) FROM location_admin"
```

## 데이터 로딩

### 전체 데이터 로드 (프로덕션)

제한 없이 모든 데이터 로드:

```bash
# 1. Datawarehouse가 실행 중인지 확인
docker ps | grep skala_datawarehouse

# 2. 환경 활성화
source .venv/bin/activate
export PYTHONPATH=.

# 3. 샘플 제한 제거 (설정된 경우)
unset SAMPLE_LIMIT

# 4. 순서대로 스크립트 실행

# 단계 1: 위치 데이터 로드 (먼저 필수!)
python scripts/load_admin_regions.py

# 단계 2: 인구 데이터 로드 (선택사항이지만 권장)
python scripts/load_population.py

# 단계 3: 해수면 데이터 로드
python scripts/load_sea_level_netcdf.py

# 단계 4: 일별 기온 데이터 로드 (TAMAX/TAMIN)
python scripts/load_sgg261_data.py

# 단계 5: 월별 기후 격자 데이터 로드 (TA, RN, WS, RHM, SI, SPEI12)
# 전체 데이터는 2-3시간 소요
python scripts/load_monthly_grid_data.py

# 단계 6: 연별 기후 격자 데이터 로드 (CSDI, WSDI, RX1DAY 등)
# 1-2시간 소요
python scripts/load_yearly_grid_data.py

# 단계 7: 래스터 데이터 로드 (선택사항 - 매우 큼!)
python scripts/load_landcover.py  # 2-3시간
python scripts/load_dem.py         # 30분
python scripts/load_drought.py     # 1시간

# 단계 8: 참조 데이터 로드 (AI 모델 학습용)
python scripts/load_weather_stations.py       # ~5초
python scripts/load_grid_station_mappings.py  # ~30초
python scripts/load_water_stress_rankings.py  # ~1분

# 단계 9: 사이트 에너지 데이터 로드 (사이트별)
export PANGYO_DC_SITE_ID="your-site-uuid"
export PANGYO_CAMPUS_SITE_ID="your-campus-uuid"
python scripts/load_site_dc_power_simple.py         # ~10초
python scripts/load_site_campus_energy_simple.py --year 2024  # ~5초
```

**총 소요 시간**: 전체 데이터 로드 시 약 12-15시간

### 샘플 모드 로드 (테스트)

테스트를 위해 데이터 유형당 10개 샘플만 로드:

```bash
# 샘플 제한 설정
export SAMPLE_LIMIT=10
export PYTHONPATH=.

# 모든 스크립트 빠른 테스트
./test_sample_load.sh

# 또는 개별 실행
python scripts/load_admin_regions.py    # ~10초
python scripts/load_sea_level_netcdf.py  # ~5초
python scripts/load_sgg261_data.py       # ~10초
python scripts/load_monthly_grid_data.py # ~20초
```

**총 소요 시간**: 샘플 모드는 약 2-3분

### 부분 데이터 로드

특정 기후 변수 또는 시나리오만 로드:

**예제 1: SSP2-4.5 시나리오만 로드**

스크립트를 편집하여 시나리오 필터링:

```python
# load_monthly_grid_data.py에서
scenarios = {
    2: {"code": "SSP2-4.5", "file_pattern": "SSP245"}  # SSP2-4.5만
}
```

**예제 2: 기온과 강수량만 로드**

```python
# load_monthly_grid_data.py에서
climate_vars = {
    "TA": {"name": "평균기온", "table": "ta_data", "unit": "°C"},
    "RN": {"name": "강수량", "table": "rn_data", "unit": "mm"}
}
```

## 데이터 검증

### 로드된 행 수 확인

```bash
# Datawarehouse에 연결
docker exec -it skala_datawarehouse psql -U skala_dw_user -d skala_datawarehouse

# 모든 테이블 확인
SELECT
    'location_admin' AS table_name, COUNT(*) AS rows FROM location_admin
UNION ALL
SELECT 'location_grid', COUNT(*) FROM location_grid
UNION ALL
SELECT 'sea_level_grid', COUNT(*) FROM sea_level_grid
UNION ALL
SELECT 'tamax_data', COUNT(*) FROM tamax_data
UNION ALL
SELECT 'tamin_data', COUNT(*) FROM tamin_data
UNION ALL
SELECT 'ta_data', COUNT(*) FROM ta_data
UNION ALL
SELECT 'rn_data', COUNT(*) FROM rn_data
UNION ALL
SELECT 'ws_data', COUNT(*) FROM ws_data
UNION ALL
SELECT 'rhm_data', COUNT(*) FROM rhm_data
UNION ALL
SELECT 'si_data', COUNT(*) FROM si_data
UNION ALL
SELECT 'spei12_data', COUNT(*) FROM spei12_data
UNION ALL
SELECT 'csdi_data', COUNT(*) FROM csdi_data
UNION ALL
SELECT 'wsdi_data', COUNT(*) FROM wsdi_data
UNION ALL
SELECT 'rx1day_data', COUNT(*) FROM rx1day_data
UNION ALL
SELECT 'rx5day_data', COUNT(*) FROM rx5day_data
UNION ALL
SELECT 'cdd_data', COUNT(*) FROM cdd_data
UNION ALL
SELECT 'rain80_data', COUNT(*) FROM rain80_data
UNION ALL
SELECT 'sdii_data', COUNT(*) FROM sdii_data
UNION ALL
SELECT 'ta_yearly_data', COUNT(*) FROM ta_yearly_data
UNION ALL
SELECT 'sea_level_data', COUNT(*) FROM sea_level_data
ORDER BY rows DESC;
```

**예상 결과 (전체 로드)**:
```
table_name       | rows
-----------------+------------
ta_data          | 433,000,000  (451,351개 격자 × 960개월)
rn_data          | 433,000,000
ws_data          | 433,000,000
rhm_data         | 433,000,000
si_data          | 433,000,000
spei12_data      | 433,000,000
csdi_data        | 36,000,000   (451,351개 격자 × 80년)
wsdi_data        | 36,000,000
rx1day_data      | 36,000,000
rx5day_data      | 36,000,000
cdd_data         | 36,000,000
rain80_data      | 36,000,000
sdii_data        | 36,000,000
ta_yearly_data   | 36,000,000   (451,351개 격자 × 80년)
tamax_data       | 7,360,000    (261개 시군구 × 29,219일)
tamin_data       | 7,360,000
location_admin   | 5,259        (5,007개 읍면동 + 252개 시군구)
location_grid    | 451,351
sea_level_grid   | 80
sea_level_data   | 6,880
```

### 데이터 품질 검증

**NULL 값 확인:**

```sql
-- 주요 열에 NULL 값이 있는지 확인
SELECT COUNT(*) AS null_count
FROM ta_data
WHERE value IS NULL;

-- 날짜 범위 확인
SELECT
    MIN(observation_date) AS start_date,
    MAX(observation_date) AS end_date,
    COUNT(DISTINCT observation_date) AS unique_dates
FROM ta_data;

-- Wide Format: 모든 시나리오 컬럼 확인
SELECT
    COUNT(*) AS total_rows,
    COUNT(ssp1) AS ssp1_count,
    COUNT(ssp2) AS ssp2_count,
    COUNT(ssp3) AS ssp3_count,
    COUNT(ssp5) AS ssp5_count
FROM ta_data;
```

**데이터 분포 확인:**

```sql
-- Wide Format: 특정 시나리오(SSP2-4.5) 기온 값 분포 확인
SELECT
    MIN(ssp2) AS min_temp,
    MAX(ssp2) AS max_temp,
    AVG(ssp2) AS avg_temp,
    PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY ssp2) AS median_temp
FROM ta_data
WHERE observation_date BETWEEN '2021-01-01' AND '2021-12-31'
AND ssp2 IS NOT NULL;

-- 공간 커버리지 확인
SELECT
    COUNT(DISTINCT grid_id) AS unique_grids,
    COUNT(*) / COUNT(DISTINCT grid_id) AS avg_records_per_grid
FROM ta_data;
```

## 진행 상황 모니터링

### 로그 보기

각 스크립트는 `logs/` 디렉토리에 로그를 생성합니다:

```bash
# 최신 로그 보기
tail -f logs/load_monthly_grid_data_*.log

# 특정 스크립트 로그 보기
tail -f logs/load_admin_regions_*.log

# 오류 검색
grep -i "error\|failed" logs/*.log

# 성공 검색
grep -i "success\|completed" logs/*.log
```

### 실시간 모니터링

스크립트가 실행되는 동안 진행 상황 모니터링:

```bash
# 다른 터미널에서 행 수 증가 관찰
watch -n 5 'docker exec skala_datawarehouse psql -U skala_dw_user -d skala_datawarehouse -c "SELECT COUNT(*) FROM ta_data"'

# 데이터베이스 크기 모니터링
watch -n 10 'docker exec skala_datawarehouse psql -U skala_dw_user -d skala_datawarehouse -c "SELECT pg_size_pretty(pg_database_size(\"skala_datawarehouse\"))"'

# 활성 연결 확인
docker exec skala_datawarehouse psql -U skala_dw_user -d skala_datawarehouse -c "SELECT count(*) FROM pg_stat_activity WHERE state = 'active'"
```

## 일반적인 워크플로우

### 워크플로우 1: 초기 설정 및 테스트

```bash
# 1. 환경 설정
source .venv/bin/activate
export PYTHONPATH=.

# 2. 샘플 데이터로 테스트
export SAMPLE_LIMIT=10
./test_sample_load.sh

# 3. 샘플 데이터 로드 확인
docker exec -it skala_datawarehouse psql -U skala_dw_user -d skala_datawarehouse -c "\dt"

# 4. 행 수 확인
docker exec -it skala_datawarehouse psql -U skala_dw_user -d skala_datawarehouse -c "SELECT 'location_admin', COUNT(*) FROM location_admin"
```

### 워크플로우 2: 프로덕션 데이터 로드

```bash
# 1. 기존 데이터 삭제 (필요한 경우)
docker exec -i skala_datawarehouse psql -U skala_dw_user -d skala_datawarehouse < ../db/truncate_all_data.sql

# 2. 환경 활성화
source .venv/bin/activate
export PYTHONPATH=.
unset SAMPLE_LIMIT

# 3. 핵심 데이터 로드 (필수)
python scripts/load_admin_regions.py 2>&1 | tee logs/manual_load_admin.log
python scripts/load_population.py 2>&1 | tee logs/manual_load_population.log

# 4. 기후 데이터 로드 (순차적)
python scripts/load_sea_level_netcdf.py 2>&1 | tee logs/manual_load_sealevel.log
python scripts/load_sgg261_data.py 2>&1 | tee logs/manual_load_sgg261.log
python scripts/load_monthly_grid_data.py 2>&1 | tee logs/manual_load_monthly.log
python scripts/load_yearly_grid_data.py 2>&1 | tee logs/manual_load_yearly.log

# 5. 완료 확인
docker exec -it skala_datawarehouse psql -U skala_dw_user -d skala_datawarehouse -c "SELECT 'ta_data', COUNT(*) FROM ta_data"
```

### 워크플로우 3: 증분 데이터 업데이트

기존 테이블에 새 데이터를 추가해야 하는 경우:

```python
# 예: 새로운 월 데이터만 로드
# 기존 데이터를 건너뛰도록 스크립트 수정

# load_monthly_grid_data.py에서 확인 추가:
cursor.execute("""
    SELECT MAX(observation_date)
    FROM ta_data
""")

last_date = cursor.fetchone()[0]
if last_date:
    # last_date 이후의 데이터만 로드
    data = data[data['time'] > last_date]
```

### 워크플로우 4: 실패한 스크립트 재실행

스크립트가 중간에 실패한 경우:

```bash
# 1. 로드된 내용 확인
docker exec -it skala_datawarehouse psql -U skala_dw_user -d skala_datawarehouse -c "SELECT COUNT(*) FROM ta_data"

# 2. 부분 데이터 삭제 (필요한 경우)
docker exec -it skala_datawarehouse psql -U skala_dw_user -d skala_datawarehouse -c "TRUNCATE TABLE ta_data CASCADE"

# 3. 스크립트 재실행
python scripts/load_monthly_grid_data.py
```

## 문제 해결

### 문제: 스크립트가 멈추거나 매우 느림

**증상**: 스크립트가 진행 없이 몇 시간 동안 실행됨

**해결 방법**:

1. **인덱스가 삽입을 느리게 하는지 확인:**
```sql
-- 임시로 인덱스 제거
DROP INDEX IF EXISTS idx_ta_data_date;
DROP INDEX IF EXISTS idx_ta_data_grid;

-- 로드 스크립트 실행

-- 로드 후 인덱스 재생성
CREATE INDEX idx_ta_data_date ON ta_data(observation_date);
CREATE INDEX idx_ta_data_grid ON ta_data(grid_id);
```

2. **autocommit 비활성화:**
```python
# 스크립트에서
conn.autocommit = False
# ... 데이터 로드 ...
conn.commit()
```

3. **배치 삽입 사용:**
```python
# 개별 삽입 대신
cursor.executemany("INSERT INTO ...", batch_data)
conn.commit()
```

### 문제: 디스크 공간 부족

**증상**: `ERROR: could not extend file: No space left on device`

**해결 방법**:

```bash
# 1. 디스크 사용량 확인
df -h

# 2. Docker 볼륨 정리
docker system prune -a --volumes

# 3. 오래된 로그 제거
rm logs/*.log

# 4. 외부 스토리지 사용
# 외부 드라이브 마운트 및 .env에서 DATA_DIR 업데이트
```

### 문제: 메모리 오류

**증상**: `MemoryError: Unable to allocate array`

**해결 방법**:

```bash
# 1. 샘플 모드 사용
export SAMPLE_LIMIT=1000  # 한 번에 1000개 로드

# 2. 배치로 처리
# 스크립트를 수정하여 더 작은 청크로 처리

# 3. 시스템 메모리 증가
# 스왑 공간 추가 (Linux)
sudo fallocate -l 8G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
```

### 문제: 연결 타임아웃

**증상**: `psycopg2.OperationalError: server closed the connection unexpectedly`

**해결 방법**:

1. **PostgreSQL 타임아웃 증가:**
```bash
# postgresql.conf 편집
docker exec -it skala_datawarehouse bash
vi /var/lib/postgresql/data/postgresql.conf

# 추가:
statement_timeout = 0  # statement timeout 비활성화
idle_in_transaction_session_timeout = 0
```

2. **연결 풀링 사용:**
```python
from psycopg2 import pool

db_pool = pool.SimpleConnectionPool(1, 5, **db_config)
conn = db_pool.getconn()
# ... 연결 사용 ...
db_pool.putconn(conn)
```

### 문제: 중복 키 오류

**증상**: `ERROR: duplicate key value violates unique constraint`

**해결 방법**:

```sql
-- Wide Format: 중복 확인
SELECT observation_date, grid_id, COUNT(*)
FROM ta_data
GROUP BY observation_date, grid_id
HAVING COUNT(*) > 1;

-- 중복 삭제 (첫 번째 유지)
DELETE FROM ta_data a USING (
    SELECT MIN(ctid) AS ctid, observation_date, grid_id
    FROM ta_data
    GROUP BY observation_date, grid_id
    HAVING COUNT(*) > 1
) b
WHERE a.observation_date = b.observation_date
AND a.grid_id = b.grid_id
AND a.ctid <> b.ctid;
```

## 성능 최적화

### 대용량 로드 속도 향상

**1. 제약 조건 임시 비활성화:**
```sql
ALTER TABLE ta_data DISABLE TRIGGER ALL;
-- 데이터 로드
ALTER TABLE ta_data ENABLE TRIGGER ALL;
```

**2. INSERT 대신 COPY 사용 (Wide Format):**
```python
from io import StringIO

# CSV 형식으로 데이터 준비 (Wide Format)
buffer = StringIO()
for row in data:
    buffer.write(f"{row['date']},{row['grid_id']},{row['ssp1']},{row['ssp2']},{row['ssp3']},{row['ssp5']}\n")

buffer.seek(0)

# COPY 사용
cursor.copy_from(
    buffer,
    'ta_data',
    columns=('observation_date', 'grid_id', 'ssp1', 'ssp2', 'ssp3', 'ssp5'),
    sep=','
)
conn.commit()
```

**3. 병렬 로딩:**
```bash
# 독립적인 테이블에 대해 여러 스크립트를 병렬로 실행
python scripts/load_monthly_grid_data.py &  # TA, RN 등
python scripts/load_yearly_grid_data.py &   # CSDI, WSDI 등
wait
```

**4. PostgreSQL 튜닝:**
```sql
-- work memory 증가
SET work_mem = '256MB';

-- maintenance work memory 증가
SET maintenance_work_mem = '1GB';

-- 로드 중 autovacuum 비활성화
ALTER TABLE ta_data SET (autovacuum_enabled = false);

-- 로드 후 재활성화
ALTER TABLE ta_data SET (autovacuum_enabled = true);
VACUUM ANALYZE ta_data;
```

### 성능 모니터링

```sql
-- 느린 쿼리 확인
SELECT
    pid,
    now() - query_start AS duration,
    query,
    state
FROM pg_stat_activity
WHERE state != 'idle'
AND now() - query_start > interval '10 seconds'
ORDER BY duration DESC;

-- 테이블 bloat 확인
SELECT
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size,
    pg_size_pretty(pg_relation_size(schemaname||'.'||tablename)) AS table_size,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename) -
                   pg_relation_size(schemaname||'.'||tablename)) AS index_size
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
```

## 모범 사례

1. **항상 먼저 샘플 모드로 테스트:**
   ```bash
   export SAMPLE_LIMIT=10
   ./test_sample_load.sh
   ```

2. **순서대로 데이터 로드:**
   - 핵심 테이블 먼저 (location_admin, location_grid)
   - 그 다음 기후 데이터
   - 마지막으로 래스터 데이터

3. **디스크 공간 모니터링:**
   ```bash
   df -h
   ```

4. **로그 보관:**
   - 로그는 `logs/` 디렉토리에 저장됨
   - 각 실행 후 검토

5. **주요 로드 전 백업:**
   ```bash
   # Datawarehouse 백업
   docker exec skala_datawarehouse pg_dump -U skala_dw_user skala_datawarehouse > \
       backup_pre_load_$(date +%Y%m%d).sql
   ```

6. **로드 후 데이터 검증:**
   - 행 수 확인
   - 날짜 범위 확인
   - NULL 값 확인
   - 데이터 분포 확인

## 참조 데이터 및 사이트 에너지 데이터

### 참조 데이터 로드 (AI 모델 학습용)

**기상 관측소 데이터:**
```bash
# 환경 활성화
source .venv/bin/activate
export PYTHONPATH=.

# 기상 관측소 로드
python scripts/load_weather_stations.py

# 데이터 확인
docker exec -it skala_datawarehouse psql -U skala_dw_user -d skala_datawarehouse -c \
  "SELECT COUNT(*) as total_stations,
          COUNT(DISTINCT basin_code) as basins
   FROM weather_stations"
```

**격자-관측소 매핑 데이터:**
```bash
# 격자-관측소 매핑 로드
python scripts/load_grid_station_mappings.py

# 데이터 확인
docker exec -it skala_datawarehouse psql -U skala_dw_user -d skala_datawarehouse -c \
  "SELECT COUNT(*) as total_mappings,
          COUNT(DISTINCT grid_lat || ',' || grid_lon) as unique_grids,
          COUNT(DISTINCT obscd) as unique_stations
   FROM grid_station_mappings"
```

**WRI Aqueduct 물 스트레스 데이터:**
```bash
# 물 스트레스 순위 로드
python scripts/load_water_stress_rankings.py

# 데이터 확인
docker exec -it skala_datawarehouse psql -U skala_dw_user -d skala_datawarehouse -c \
  "SELECT COUNT(*) as total_records,
          COUNT(DISTINCT name_0) as countries,
          COUNT(DISTINCT indicator_name) as indicators,
          COUNT(DISTINCT year) as years
   FROM water_stress_rankings"
```

### 사이트 에너지 데이터 로드

**판교DC 전력 사용량 (시간별):**
```bash
# 환경 활성화
source .venv/bin/activate
export PYTHONPATH=.

# Site ID 설정 (Application DB에서 조회 필요)
export PANGYO_DC_SITE_ID="your-site-uuid"

# Application DB에서 Site ID 조회
docker exec -it skala_application psql -U skala_app_user -d skala_application -c \
  "SELECT site_id, site_name FROM sites WHERE site_name LIKE '%판교DC%'"

# DC 전력 데이터 로드
python scripts/load_site_dc_power_simple.py

# 데이터 확인
docker exec -it skala_datawarehouse psql -U skala_dw_user -d skala_datawarehouse -c \
  "SELECT
     COUNT(*) as total_records,
     MIN(measurement_date) as start_date,
     MAX(measurement_date) as end_date,
     AVG(total_power_kwh) as avg_total_power,
     AVG(it_power_kwh) as avg_it_power,
     AVG(cooling_power_kwh) as avg_cooling_power
   FROM site_dc_power_usage
   WHERE site_id = '$PANGYO_DC_SITE_ID'"
```

**판교캠퍼스 에너지 사용량 (월별):**
```bash
# Site ID 설정
export PANGYO_CAMPUS_SITE_ID="your-campus-uuid"

# Application DB에서 Site ID 조회
docker exec -it skala_application psql -U skala_app_user -d skala_application -c \
  "SELECT site_id, site_name FROM sites WHERE site_name LIKE '%판교캠퍼스%'"

# 캠퍼스 에너지 데이터 로드 (특정 연도)
python scripts/load_site_campus_energy_simple.py --year 2024

# 데이터 확인
docker exec -it skala_datawarehouse psql -U skala_dw_user -d skala_datawarehouse -c \
  "SELECT
     COUNT(*) as total_records,
     measurement_year,
     AVG(total_power_kwh) as avg_power,
     AVG(gas_usage_m3) as avg_gas,
     AVG(water_usage_m3) as avg_water
   FROM site_campus_energy_usage
   WHERE site_id = '$PANGYO_CAMPUS_SITE_ID'
   GROUP BY measurement_year
   ORDER BY measurement_year"
```

---

**설치 지침은 [SETUP.md](SETUP.md)를 참조하세요**
**일반 정보는 [README.md](README.md)를 참조하세요**
