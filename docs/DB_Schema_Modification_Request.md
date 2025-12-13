# DB 스키마 수정 요청서

## 📌 요청 배경

현재 ModelOPS 시스템은 **2021~2100년(80개 연도) × 4개 SSP 시나리오별** 기후 리스크를 계산해야 하지만, 현재 DB 스키마에는 시나리오와 연도 정보를 저장할 컬럼이 없습니다.

### 문제점
- `hazard_results`, `probability_results`, `exposure_results`, `vulnerability_results`, `aal_scaled_results` 테이블에 **시나리오(scenario)** 및 **연도(year)** 컬럼이 누락됨
- 동일 좌표에 대해 여러 시나리오/연도별 결과를 구분할 수 없음
- 현재 PK는 `(latitude, longitude, risk_type)`만 포함하여 중복 저장 불가

---

## 🎯 수정 목표

**2021~2100년(80년) × 4개 시나리오(SSP126, SSP245, SSP370, SSP585) × 9개 리스크별** 계산 결과를 모두 저장 가능하도록 스키마 변경

---

## 📋 수정 대상 테이블 (5개)

### 1. `probability_results` (확률/AAL 결과)

#### 현재 스키마
```sql
Table probability_results {
  latitude decimal(9,6) [not null]
  longitude decimal(9,6) [not null]
  risk_type varchar(50) [not null]
  aal real
  bin_probabilities jsonb
  bin_data jsonb
  calculation_details jsonb
  calculated_at timestamp

  indexes {
    (latitude, longitude, risk_type) [pk]  -- ❌ 시나리오/연도 없음
  }
}
```

#### 수정 후 스키마
```sql
Table probability_results {
  latitude decimal(9,6) [not null]
  longitude decimal(9,6) [not null]
  risk_type varchar(50) [not null]
  scenario varchar(10) [not null]        -- ✅ 추가: SSP126/SSP245/SSP370/SSP585
  year integer [not null]                -- ✅ 추가: 2021~2100
  aal real
  bin_probabilities jsonb
  bin_data jsonb
  calculation_details jsonb
  calculated_at timestamp

  indexes {
    (latitude, longitude, risk_type, scenario, year) [pk]  -- ✅ PK 확장
    (scenario, year)                                        -- ✅ 시나리오/연도 조회용
    risk_type
    (latitude, longitude)
    aal
    calculated_at
  }
}
```

#### 마이그레이션 전략
```sql
-- Step 1: 새 컬럼 추가 (기본값 포함)
ALTER TABLE probability_results
ADD COLUMN scenario varchar(10) DEFAULT 'SSP245',
ADD COLUMN year integer DEFAULT 2030;

-- Step 2: 기존 데이터에 기본값 적용
UPDATE probability_results
SET scenario = 'SSP245', year = 2030
WHERE scenario IS NULL OR year IS NULL;

-- Step 3: NOT NULL 제약조건 추가
ALTER TABLE probability_results
ALTER COLUMN scenario SET NOT NULL,
ALTER COLUMN year SET NOT NULL;

-- Step 4: 기존 PK 삭제 후 새 PK 생성
ALTER TABLE probability_results DROP CONSTRAINT probability_results_pkey;
ALTER TABLE probability_results
ADD PRIMARY KEY (latitude, longitude, risk_type, scenario, year);

-- Step 5: 인덱스 추가
CREATE INDEX idx_probability_scenario_year ON probability_results(scenario, year);
```

---

### 2. `hazard_results` (Hazard 점수)

#### 현재 스키마
```sql
Table hazard_results {
  latitude decimal(9,6) [not null]
  longitude decimal(9,6) [not null]
  risk_type varchar(50) [not null]
  hazard_score real [not null]
  hazard_score_100 real [not null]
  hazard_level varchar(20) [not null]
  calculated_at timestamp

  indexes {
    (latitude, longitude, risk_type) [pk]  -- ❌ 시나리오/연도 없음
  }
}
```

#### 수정 후 스키마
```sql
Table hazard_results {
  latitude decimal(9,6) [not null]
  longitude decimal(9,6) [not null]
  risk_type varchar(50) [not null]
  scenario varchar(10) [not null]        -- ✅ 추가
  year integer [not null]                -- ✅ 추가
  hazard_score real [not null]
  hazard_score_100 real [not null]
  hazard_level varchar(20) [not null]
  calculated_at timestamp

  indexes {
    (latitude, longitude, risk_type, scenario, year) [pk]  -- ✅ PK 확장
    (scenario, year)                                        -- ✅ 추가
    risk_type
    (latitude, longitude)
    hazard_level
    hazard_score_100
    calculated_at
  }
}
```

#### 마이그레이션 SQL
```sql
ALTER TABLE hazard_results
ADD COLUMN scenario varchar(10) DEFAULT 'SSP245',
ADD COLUMN year integer DEFAULT 2030;

UPDATE hazard_results
SET scenario = 'SSP245', year = 2030
WHERE scenario IS NULL OR year IS NULL;

ALTER TABLE hazard_results
ALTER COLUMN scenario SET NOT NULL,
ALTER COLUMN year SET NOT NULL;

ALTER TABLE hazard_results DROP CONSTRAINT hazard_results_pkey;
ALTER TABLE hazard_results
ADD PRIMARY KEY (latitude, longitude, risk_type, scenario, year);

CREATE INDEX idx_hazard_scenario_year ON hazard_results(scenario, year);
```

---

### 3. `exposure_results` (노출도)

#### 현재 스키마
```sql
Table exposure_results {
  latitude decimal(9,6) [not null]
  longitude decimal(9,6) [not null]
  risk_type varchar(50) [not null]
  site_id uuid
  exposure_score real
  proximity_factor real
  normalized_asset_value real
  calculated_at timestamp

  indexes {
    (latitude, longitude, risk_type) [pk]  -- ❌ 시나리오/연도 없음
  }
}
```

#### 수정 후 스키마
```sql
Table exposure_results {
  latitude decimal(9,6) [not null]
  longitude decimal(9,6) [not null]
  risk_type varchar(50) [not null]
  scenario varchar(10) [not null]        -- ✅ 추가
  year integer [not null]                -- ✅ 추가
  site_id uuid
  exposure_score real
  proximity_factor real
  normalized_asset_value real
  calculated_at timestamp

  indexes {
    (latitude, longitude, risk_type, scenario, year) [pk]  -- ✅ PK 확장
    (scenario, year)                                        -- ✅ 추가
    risk_type
    (latitude, longitude)
    site_id
    exposure_score
    calculated_at
  }
}
```

#### 마이그레이션 SQL
```sql
ALTER TABLE exposure_results
ADD COLUMN scenario varchar(10) DEFAULT 'SSP245',
ADD COLUMN year integer DEFAULT 2030;

UPDATE exposure_results
SET scenario = 'SSP245', year = 2030
WHERE scenario IS NULL OR year IS NULL;

ALTER TABLE exposure_results
ALTER COLUMN scenario SET NOT NULL,
ALTER COLUMN year SET NOT NULL;

ALTER TABLE exposure_results DROP CONSTRAINT exposure_results_pkey;
ALTER TABLE exposure_results
ADD PRIMARY KEY (latitude, longitude, risk_type, scenario, year);

CREATE INDEX idx_exposure_scenario_year ON exposure_results(scenario, year);
```

---

### 4. `vulnerability_results` (취약성)

#### 현재 스키마
```sql
Table vulnerability_results {
  latitude decimal(9,6) [not null]
  longitude decimal(9,6) [not null]
  risk_type varchar(50) [not null]
  site_id uuid
  vulnerability_score real
  vulnerability_level varchar(20)
  factors jsonb
  calculated_at timestamp

  indexes {
    (latitude, longitude, risk_type) [pk]  -- ❌ 시나리오/연도 없음
  }
}
```

#### 수정 후 스키마
```sql
Table vulnerability_results {
  latitude decimal(9,6) [not null]
  longitude decimal(9,6) [not null]
  risk_type varchar(50) [not null]
  scenario varchar(10) [not null]        -- ✅ 추가
  year integer [not null]                -- ✅ 추가
  site_id uuid
  vulnerability_score real
  vulnerability_level varchar(20)
  factors jsonb
  calculated_at timestamp

  indexes {
    (latitude, longitude, risk_type, scenario, year) [pk]  -- ✅ PK 확장
    (scenario, year)                                        -- ✅ 추가
    risk_type
    (latitude, longitude)
    site_id
    vulnerability_level
    vulnerability_score
    calculated_at
  }
}
```

#### 마이그레이션 SQL
```sql
ALTER TABLE vulnerability_results
ADD COLUMN scenario varchar(10) DEFAULT 'SSP245',
ADD COLUMN year integer DEFAULT 2030;

UPDATE vulnerability_results
SET scenario = 'SSP245', year = 2030
WHERE scenario IS NULL OR year IS NULL;

ALTER TABLE vulnerability_results
ALTER COLUMN scenario SET NOT NULL,
ALTER COLUMN year SET NOT NULL;

ALTER TABLE vulnerability_results DROP CONSTRAINT vulnerability_results_pkey;
ALTER TABLE vulnerability_results
ADD PRIMARY KEY (latitude, longitude, risk_type, scenario, year);

CREATE INDEX idx_vulnerability_scenario_year ON vulnerability_results(scenario, year);
```

---

### 5. `aal_scaled_results` (최종 AAL)

#### 현재 스키마
```sql
Table aal_scaled_results {
  latitude decimal(9,6) [not null]
  longitude decimal(9,6) [not null]
  risk_type varchar(50) [not null]
  site_id uuid
  base_aal real
  vulnerability_scale real
  final_aal real
  insurance_rate real [default: 0.0]
  expected_loss bigint
  calculated_at timestamp

  indexes {
    (latitude, longitude, risk_type) [pk]  -- ❌ 시나리오/연도 없음
  }
}
```

#### 수정 후 스키마
```sql
Table aal_scaled_results {
  latitude decimal(9,6) [not null]
  longitude decimal(9,6) [not null]
  risk_type varchar(50) [not null]
  scenario varchar(10) [not null]        -- ✅ 추가
  year integer [not null]                -- ✅ 추가
  site_id uuid
  base_aal real
  vulnerability_scale real
  final_aal real
  insurance_rate real [default: 0.0]
  expected_loss bigint
  calculated_at timestamp

  indexes {
    (latitude, longitude, risk_type, scenario, year) [pk]  -- ✅ PK 확장
    (scenario, year)                                        -- ✅ 추가
    risk_type
    site_id
    (latitude, longitude)
    final_aal
    expected_loss
    calculated_at
  }
}
```

#### 마이그레이션 SQL
```sql
ALTER TABLE aal_scaled_results
ADD COLUMN scenario varchar(10) DEFAULT 'SSP245',
ADD COLUMN year integer DEFAULT 2030;

UPDATE aal_scaled_results
SET scenario = 'SSP245', year = 2030
WHERE scenario IS NULL OR year IS NULL;

ALTER TABLE aal_scaled_results
ALTER COLUMN scenario SET NOT NULL,
ALTER COLUMN year SET NOT NULL;

ALTER TABLE aal_scaled_results DROP CONSTRAINT aal_scaled_results_pkey;
ALTER TABLE aal_scaled_results
ADD PRIMARY KEY (latitude, longitude, risk_type, scenario, year);

CREATE INDEX idx_aal_scaled_scenario_year ON aal_scaled_results(scenario, year);
```

---

## 📊 데이터 용량 예측

### 현재 용량
- 각 테이블: ~4.06M rows (451,351 격자 × 9 리스크)

### 수정 후 예상 용량
- **80년 × 4 시나리오 = 320배 증가**
- 각 테이블: ~1.3B rows (4.06M × 320)
- 5개 테이블 총합: **~6.5B rows**

### 디스크 용량 예측 (대략)
- `probability_results`: ~250 GB
- `hazard_results`: ~180 GB
- `exposure_results`: ~150 GB
- `vulnerability_results`: ~200 GB
- `aal_scaled_results`: ~180 GB
- **총 예상 용량: ~1 TB**

---

## ⚠️ 주의사항

### 1. 기존 데이터 처리
- 현재 저장된 데이터는 **SSP245 시나리오, 2030년**으로 간주
- 마이그레이션 시 기본값으로 `scenario='SSP245', year=2030` 설정

### 2. 애플리케이션 코드 수정 필요
다음 파일들의 SQL 쿼리 수정 필요:
- `modelops/database/connection.py`
  - `save_hazard_results()`
  - `save_probability_results()`
  - `save_exposure_results()`
  - `save_vulnerability_results()`
  - `save_aal_scaled_results()`
  - `fetch_hazard_results()`
  - `fetch_probability_results()`

### 3. 배치 프로세서 수정 필요
- `modelops/batch/hazard_batch.py`
- `modelops/batch/probability_batch.py`

### 4. 인덱스 성능
- `(scenario, year)` 복합 인덱스 추가로 시나리오/연도별 조회 성능 확보
- PK에 scenario, year 포함으로 중복 방지

---

## 📅 마이그레이션 단계

### Phase 1: 스키마 변경 (Downtime 필요)
1. 백업 수행
2. 5개 테이블에 `scenario`, `year` 컬럼 추가
3. 기존 데이터에 기본값 설정
4. PK 및 인덱스 재생성

### Phase 2: 애플리케이션 코드 수정
1. DatabaseConnection 클래스 수정
2. Batch 프로세서 수정
3. 테스트 환경에서 검증

### Phase 3: 배치 재실행
1. 2021~2100년 × 4 시나리오별 계산 실행
2. 진행률 모니터링

---

## ✅ 승인 요청

위 스키마 변경을 승인해 주시기 바랍니다.

- **예상 작업 시간**: 2~3일
- **Downtime**: 약 2~4시간 (마이그레이션 시)
- **디스크 용량**: 추가 1TB 필요

---

## 📎 참고 문서

- ERD: `docs/Datawarehouse.dbml`
- 기후 데이터 범위: 2021~2100년 (NetCDF 파일)
- SSP 시나리오: SSP126, SSP245, SSP370, SSP585

---

**작성일**: 2025-12-12
**작성자**: ModelOPS 팀
**검토 요청**: DB 팀
