# ModelOps 이관 문서 - 03. 데이터 스키마

**문서 버전**: 1.0
**작성일**: 2025-12-01

---

## 1. 입력 데이터 구조

### 1.1 건물 정보 (Building Info)

```json
{
  "building_age": 25,
  "structure": "철근콘크리트",
  "main_purpose": "업무시설",
  "floors_below": 2,
  "floors_above": 10,
  "has_piloti": false,
  "has_seismic_design": true,
  "fire_access": true,
  "location": {
    "latitude": 37.5665,
    "longitude": 126.9780,
    "elevation": 38.5,
    "admin_code": "1101010100"
  }
}
```

**필드 설명**:
| 필드 | 타입 | 설명 | 필수 여부 |
|------|------|------|----------|
| `building_age` | integer | 건물 연식 (년) | 필수 |
| `structure` | string | 건물 구조 | 필수 |
| `main_purpose` | string | 주용도 | 필수 |
| `floors_below` | integer | 지하층 수 | 필수 |
| `floors_above` | integer | 지상층 수 | 필수 |
| `has_piloti` | boolean | 필로티 구조 여부 | 필수 |
| `has_seismic_design` | boolean | 내진 설계 여부 | 필수 |
| `fire_access` | boolean | 소방차 진입 가능 여부 | 필수 |
| `location.latitude` | float | 위도 | 필수 |
| `location.longitude` | float | 경도 | 필수 |
| `location.elevation` | float | 해발 고도 (m) | 선택 |
| `location.admin_code` | string | 행정구역 코드 | 선택 |

---

### 1.2 자산 정보 (Asset Info)

```json
{
  "total_asset_value": 50000000000,
  "insurance_coverage_rate": 0.7,
  "floor_area": 5000.0
}
```

**필드 설명**:
| 필드 | 타입 | 설명 | 예시 |
|------|------|------|------|
| `total_asset_value` | integer | 총 자산 가치 (원) | 500억원 |
| `insurance_coverage_rate` | float | 보험 보전율 (0-1) | 0.7 (70%) |
| `floor_area` | float | 연면적 (m²) | 5000.0 |

---

### 1.3 기후 데이터 (Climate Data)

```json
{
  "grid_id": 12345,
  "scenario_id": 2,
  "start_year": 2025,
  "end_year": 2050,
  "variables": {
    "wsdi": [3.2, 4.1, 5.3, 6.8, ...],
    "csdi": [2.1, 1.8, 1.5, 1.2, ...],
    "fwi": [25.3, 28.1, 31.5, ...],
    "spei12": [-0.5, -0.8, -1.2, ...],
    "wsi": [0.3, 0.35, 0.42, ...],
    "slr_depth": [0.0, 0.001, 0.002, ...],
    "rx1day": [85, 92, 98, ...],
    "rain80": [12, 15, 18, ...],
    "tc_exposure": [8, 12, 15, ...]
  }
}
```

**변수 설명**:
| 변수 | 전체 명칭 | 리스크 | 단위 |
|------|----------|--------|------|
| `wsdi` | Warm Spell Duration Index | Extreme Heat | 일수 |
| `csdi` | Cold Spell Duration Index | Extreme Cold | 일수 |
| `fwi` | Fire Weather Index | Wildfire | 지수 |
| `spei12` | 12-month SPEI | Drought | 지수 |
| `wsi` | Water Stress Index | Water Stress | 지수 (0-1) |
| `slr_depth` | Sea Level Rise Depth | Sea Level Rise | m |
| `rx1day` | Max 1-day Rainfall | River Flood | mm |
| `rain80` | Days with >80mm Rain | Urban Flood | 일수 |
| `tc_exposure` | Tropical Cyclone Exposure | Typhoon | 지수 |

---

## 2. 출력 데이터 구조

### 2.1 Vulnerability Score 출력

```json
{
  "site_id": "uuid-12345",
  "building_hash": "sha256-abcd1234...",
  "vulnerability_scores": {
    "extreme_heat": {
      "score": 65.0,
      "level": "high",
      "factors": {
        "building_age": 25,
        "insulation_quality": "fair",
        "cooling_capacity": "standard"
      }
    },
    "extreme_cold": {
      "score": 55.0,
      "level": "medium",
      "factors": {...}
    },
    // ... 나머지 7개 리스크
  },
  "computed_at": "2025-12-01T10:30:00Z"
}
```

---

### 2.2 Hazard Score 출력

```json
{
  "grid_id": 12345,
  "hazard_scores": {
    "extreme_heat": {
      "ssp1_2.6": {"short_term": 0.45, "mid_term": 0.52, "long_term": 0.58},
      "ssp2_4.5": {"short_term": 0.50, "mid_term": 0.60, "long_term": 0.68},
      "ssp3_7.0": {"short_term": 0.55, "mid_term": 0.68, "long_term": 0.78},
      "ssp5_8.5": {"short_term": 0.60, "mid_term": 0.75, "long_term": 0.85}
    },
    // ... 나머지 8개 리스크
  },
  "computed_at": "2025-11-30T00:00:00Z"
}
```

---

### 2.3 AAL 출력

```json
{
  "site_id": "uuid-12345",
  "aal_results": {
    "extreme_heat": {
      "ssp2_4.5": {
        "base_aal": 0.0012,
        "vulnerability_scale": 1.05,
        "final_aal_percentage": 0.38,
        "expected_loss": 190000000,
        "risk_level": "moderate"
      },
      // ... 나머지 SSP
    },
    // ... 나머지 8개 리스크
  },
  "total_expected_loss": {
    "ssp1_2.6": 850000000,
    "ssp2_4.5": 1200000000,
    "ssp3_7.0": 1650000000,
    "ssp5_8.5": 2100000000
  },
  "computed_at": "2025-12-01T10:35:00Z"
}
```

---

### 2.4 Physical Risk Score 출력

```json
{
  "site_id": "uuid-12345",
  "physical_risk_scores": {
    "extreme_heat": {
      "ssp2_4.5": {
        "score": 62.5,
        "hazard": 0.60,
        "exposure": 0.65,
        "vulnerability": 65.0,
        "risk_level": "high"
      },
      // ... 나머지 SSP
    },
    // ... 나머지 8개 리스크
  },
  "computed_at": "2025-12-01T10:35:00Z"
}
```

---

## 3. DB 테이블 스키마

### 3.1 Hazard Batch Results (배치 결과 저장)

```sql
CREATE TABLE modelops_hazard_scores (
    hazard_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    grid_id INTEGER NOT NULL,
    scenario_id INTEGER NOT NULL,  -- 1=SSP1-2.6, 2=SSP2-4.5, 3=SSP3-7.0, 4=SSP5-8.5
    risk_type VARCHAR(50) NOT NULL,  -- extreme_heat, extreme_cold, ...
    time_period VARCHAR(20) NOT NULL,  -- short_term, mid_term, long_term
    score DECIMAL(5,4) NOT NULL,  -- 0.0000 ~ 1.0000
    percentile DECIMAL(5,2),  -- 백분위수
    computed_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT chk_scenario CHECK (scenario_id BETWEEN 1 AND 4),
    CONSTRAINT chk_score CHECK (score BETWEEN 0 AND 1),
    INDEX idx_grid_scenario (grid_id, scenario_id, risk_type, time_period)
);
```

**예시 데이터**:
```sql
INSERT INTO modelops_hazard_scores (grid_id, scenario_id, risk_type, time_period, score, percentile)
VALUES (12345, 2, 'extreme_heat', 'mid_term', 0.6000, 78.5);
```

---

### 3.2 Vulnerability Cache (요청별 결과 캐싱)

```sql
CREATE TABLE modelops_vulnerability_cache (
    cache_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    site_id UUID NOT NULL,
    building_hash VARCHAR(64) NOT NULL,  -- SHA256(building_info JSON)
    risk_type VARCHAR(50) NOT NULL,
    score DECIMAL(5,2) NOT NULL,  -- 0.00 ~ 100.00
    level VARCHAR(20) NOT NULL,  -- very_low, low, medium, high, very_high
    factors JSONB,  -- 취약성 요인 상세
    computed_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP WITH TIME ZONE,  -- TTL: computed_at + 24시간

    UNIQUE (site_id, building_hash, risk_type),
    INDEX idx_site_hash (site_id, building_hash),
    INDEX idx_expires (expires_at)
);
```

**예시 데이터**:
```sql
INSERT INTO modelops_vulnerability_cache (
    site_id, building_hash, risk_type, score, level, factors, expires_at
) VALUES (
    'uuid-12345',
    'sha256-abcd1234...',
    'extreme_heat',
    65.0,
    'high',
    '{"building_age": 25, "insulation_quality": "fair"}'::jsonb,
    CURRENT_TIMESTAMP + INTERVAL '24 hours'
);
```

---

### 3.3 AAL Cache

```sql
CREATE TABLE modelops_aal_cache (
    cache_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    site_id UUID NOT NULL,
    risk_type VARCHAR(50) NOT NULL,
    scenario_id INTEGER NOT NULL,
    base_aal DECIMAL(8,6) NOT NULL,  -- 0.000000 ~ 1.000000
    final_aal_percentage DECIMAL(8,4) NOT NULL,  -- 백분율
    expected_loss BIGINT,  -- 예상 손실액 (원)
    vulnerability_scale DECIMAL(5,4),  -- F_vuln
    risk_level VARCHAR(20),
    computed_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP WITH TIME ZONE,

    UNIQUE (site_id, risk_type, scenario_id),
    INDEX idx_site_risk (site_id, risk_type),
    INDEX idx_expires (expires_at)
);
```

**예시 데이터**:
```sql
INSERT INTO modelops_aal_cache (
    site_id, risk_type, scenario_id,
    base_aal, final_aal_percentage, expected_loss, vulnerability_scale, risk_level,
    expires_at
) VALUES (
    'uuid-12345',
    'extreme_heat',
    2,  -- SSP2-4.5
    0.001200,
    0.38,
    190000000,
    1.05,
    'moderate',
    CURRENT_TIMESTAMP + INTERVAL '24 hours'
);
```

---

## 4. 캐시 관리 전략

### 4.1 TTL (Time To Live)

| 데이터 유형 | TTL | 근거 |
|------------|-----|------|
| Hazard Scores | 무기한 (배치 업데이트) | 기후 데이터 변경 주기 느림 |
| Vulnerability Cache | 24시간 | 건물 정보 변경 가능성 |
| AAL Cache | 24시간 | 취약성 또는 자산 정보 변경 가능성 |

### 4.2 캐시 무효화 (Invalidation)

**조건**:
1. 건물 정보 변경 시 → Vulnerability, AAL 캐시 삭제
2. 자산 정보 변경 시 → AAL 캐시 삭제
3. TTL 만료 시 → 자동 삭제

**구현**:
```sql
-- TTL 만료 캐시 자동 정리 (일일 배치)
DELETE FROM modelops_vulnerability_cache WHERE expires_at < CURRENT_TIMESTAMP;
DELETE FROM modelops_aal_cache WHERE expires_at < CURRENT_TIMESTAMP;
```

---

## 5. 데이터 검증 규칙

### 5.1 입력 검증

| 필드 | 검증 규칙 | 오류 메시지 |
|------|----------|-----------|
| `building_age` | 0 ≤ age ≤ 100 | "Building age must be between 0 and 100" |
| `floors_below` | 0 ≤ floors ≤ 10 | "Underground floors must be between 0 and 10" |
| `floors_above` | 1 ≤ floors ≤ 200 | "Above-ground floors must be between 1 and 200" |
| `latitude` | -90 ≤ lat ≤ 90 | "Invalid latitude" |
| `longitude` | -180 ≤ lon ≤ 180 | "Invalid longitude" |
| `total_asset_value` | > 0 | "Asset value must be positive" |
| `insurance_coverage_rate` | 0 ≤ rate ≤ 1 | "Insurance rate must be between 0 and 1" |

### 5.2 출력 검증

| 필드 | 검증 규칙 |
|------|----------|
| `vulnerability score` | 0 ≤ score ≤ 100 |
| `hazard score` | 0 ≤ score ≤ 1 |
| `exposure score` | 0 ≤ score ≤ 1 |
| `base_aal` | 0 ≤ aal ≤ 1 |
| `final_aal_percentage` | 0 ≤ percentage ≤ 100 |

---

## 다음 문서

👉 [04. API 명세](./04_API_SPECIFICATION.md)
