# DB팀 ERD 수정 요청사항

> 작성일: 2025-12-03
> 요청팀: ModelOps
> 우선순위: 🔴 필수

---

## 요약

ModelOps의 H × E × V = Risk 계산 결과를 저장하기 위해 **4가지 ERD 수정**이 필요합니다:
1. `probability_results` 테이블 컬럼 수정 (1개)
2. 결과 저장 테이블 추가 (3개)

**기존 ERD는 올바르게 설계되어 있으며**, 원시 데이터 및 API 캐시 테이블은 수정 불필요합니다.

---

## 수정 요청 상세

### 1. probability_results 테이블 컬럼 수정 ⚠️

#### 현재 구조 (ERD v05)
```sql
CREATE TABLE probability_results (
  latitude DECIMAL(9,6),
  longitude DECIMAL(9,6),
  risk_type VARCHAR(50),
  probability REAL,          -- ❌ 단일 값만 저장 가능
  bin_data JSONB,
  calculated_at TIMESTAMP,
  PRIMARY KEY (latitude, longitude, risk_type)
);
```

#### 수정 후 구조
```sql
CREATE TABLE probability_results (
  latitude DECIMAL(9,6),
  longitude DECIMAL(9,6),
  risk_type VARCHAR(50),
  aal REAL,                      -- ✅ 연간 평균 손실률 (0.0~1.0)
  bin_probabilities JSONB,       -- ✅ bin별 발생확률 배열 [0.65, 0.25, 0.08, ...]
  calculation_details JSONB,     -- ✅ 계산 상세정보
  calculated_at TIMESTAMP DEFAULT NOW(),
  PRIMARY KEY (latitude, longitude, risk_type)
);
```

#### Migration SQL
```sql
-- 기존 컬럼 제거
ALTER TABLE probability_results DROP COLUMN IF EXISTS probability;

-- 새 컬럼 추가
ALTER TABLE probability_results
ADD COLUMN aal REAL,
ADD COLUMN bin_probabilities JSONB,
ADD COLUMN calculation_details JSONB;

-- bin_data 컬럼은 유지 (하위 호환성)
```

#### 변경 사유
- ModelOps Probability 에이전트는 **강도별 bin 확률**을 계산 (bin 1~5)
- `probability` 단일 값으로는 bin별 확률 저장 불가
- `aal` (연간 평균 손실률) = AAL 계산의 기초값
- `bin_probabilities` = 강도 bin별 발생확률 (예: [0.65, 0.25, 0.08, 0.015, 0.005])

#### 데이터 예시
```json
{
  "aal": 0.125,
  "bin_probabilities": [0.65, 0.25, 0.08, 0.015, 0.005],
  "calculation_details": {
    "formula": "P(H) = event_count / total_years",
    "time_unit": "yearly",
    "total_years": 80,
    "bins": [
      {"bin": 1, "range": "0-20%", "probability": 0.65},
      {"bin": 2, "range": "20-40%", "probability": 0.25},
      {"bin": 3, "range": "40-60%", "probability": 0.08},
      {"bin": 4, "range": "60-80%", "probability": 0.015},
      {"bin": 5, "range": "80-100%", "probability": 0.005}
    ]
  }
}
```

---

### 2. exposure_results 테이블 추가 ✅

```sql
CREATE TABLE exposure_results (
  latitude DECIMAL(9,6),
  longitude DECIMAL(9,6),
  risk_type VARCHAR(50),
  exposure_score REAL,              -- 노출도 점수 (0.0~1.0)
  proximity_factor REAL,            -- 근접도 계수
  normalized_asset_value REAL,      -- 정규화된 자산가치
  calculated_at TIMESTAMP DEFAULT NOW(),
  PRIMARY KEY (latitude, longitude, risk_type)
);

CREATE INDEX idx_exposure_risk ON exposure_results(risk_type);
CREATE INDEX idx_exposure_time ON exposure_results(calculated_at);
```

#### 용도
- ModelOps Exposure Agent가 계산한 **E (노출도)** 점수 저장
- 리스크별로 사업장의 자산 노출 정도 산출

---

### 3. vulnerability_results 테이블 추가 ✅

```sql
CREATE TABLE vulnerability_results (
  latitude DECIMAL(9,6),
  longitude DECIMAL(9,6),
  risk_type VARCHAR(50),
  vulnerability_score REAL,         -- 취약성 점수 (0~100)
  vulnerability_level VARCHAR(20),  -- 등급: very_low, low, medium, high, very_high
  factors JSONB,                    -- 취약성 요인 상세
  calculated_at TIMESTAMP DEFAULT NOW(),
  PRIMARY KEY (latitude, longitude, risk_type)
);

CREATE INDEX idx_vuln_risk ON vulnerability_results(risk_type);
CREATE INDEX idx_vuln_level ON vulnerability_results(vulnerability_level);
CREATE INDEX idx_vuln_time ON vulnerability_results(calculated_at);
```

#### 용도
- ModelOps Vulnerability Agent가 계산한 **V (취약성)** 점수 저장
- 건물 특성 (연식, 구조, 층수 등) 기반 리스크별 취약성 산출

#### factors JSONB 예시
```json
{
  "building_age": 25,
  "structure": "철근콘크리트",
  "main_purpose": "업무시설",
  "floors_below": 2,
  "floors_above": 10,
  "has_piloti": false,
  "has_seismic_design": true
}
```

---

### 4. aal_scaled_results 테이블 추가 ✅

```sql
CREATE TABLE aal_scaled_results (
  latitude DECIMAL(9,6),
  longitude DECIMAL(9,6),
  risk_type VARCHAR(50),
  base_aal REAL,                    -- 기본 AAL (probability_results.aal)
  vulnerability_scale REAL,         -- F_vuln (취약성 스케일 계수: 0.9~1.1)
  final_aal REAL,                   -- 최종 AAL = base_aal × F_vuln × (1 - insurance_rate)
  insurance_rate REAL DEFAULT 0.0,  -- 보험 보전율 (0~1)
  expected_loss BIGINT,             -- 예상 손실액 (원)
  calculated_at TIMESTAMP DEFAULT NOW(),
  PRIMARY KEY (latitude, longitude, risk_type)
);

CREATE INDEX idx_aal_risk ON aal_scaled_results(risk_type);
CREATE INDEX idx_aal_final ON aal_scaled_results(final_aal DESC);
CREATE INDEX idx_aal_time ON aal_scaled_results(calculated_at);
```

#### 용도
- ModelOps AAL Scaling Agent가 계산한 **최종 AAL** 저장
- 취약성 점수로 보정한 연간 평균 손실률

#### 계산 공식
```
F_vuln = 0.9 + (V_score / 100) × 0.2  (범위: 0.9 ~ 1.1)
final_aal = base_aal × F_vuln × (1 - insurance_rate)
expected_loss = final_aal × asset_value
```

---

## 기존 테이블 확인 (수정 불필요)

다음 ERD 테이블들은 **그대로 유지**됩니다:

### ✅ 유지되는 테이블
1. **hazard_results** - H (위험도) 점수 저장 (이미 올바름)
2. **location_grid** - 격자 참조 테이블 (ModelOps가 사용)
3. **기후 데이터 테이블 (17개)** - tamax_data, tamin_data, ta_data, rn_data, ws_data 등
4. **API 캐시 테이블 (11개)** - api_wamis, api_typhoon_*, api_buildings 등
5. **sites** (Application DB) - 사업장 위경도 정보

### 📋 ModelOps가 처리할 사항 (DB 수정 불필요)
- **파생 지표 계산**: DB 원시 데이터 → ModelOps 전처리 레이어에서 heatwave_days, FWI 등 계산
- **외부 API 호출**: WAMIS, 태풍, 건물 정보 → ModelOps API 클라이언트에서 처리
- **격자 매핑**: 사업장 좌표 → 격자 → ModelOps 매핑 로직
- **BWS 시나리오**: water_stress_rankings 테이블 → ModelOps 코드에서 시나리오 매핑

---

## 영향도 분석

### 기존 시스템 영향
- ❌ **기존 데이터 손실 없음**: probability_results 외 테이블은 수정 없음
- ⚠️ **probability_results 마이그레이션 필요**: `probability` 컬럼 → `aal` + `bin_probabilities`
- ✅ **신규 테이블 3개 추가**: exposure_results, vulnerability_results, aal_scaled_results
- ✅ **하위 호환성 유지**: bin_data 컬럼 유지

### 예상 데이터 규모
| 테이블 | 예상 레코드 수 | 설명 |
|--------|---------------|------|
| probability_results | ~4.06M | 451,351 grids × 9 risk types |
| exposure_results | ~4.06M | 동일 |
| vulnerability_results | ~4.06M | 동일 |
| aal_scaled_results | ~4.06M | 동일 |

---

## 배포 계획

### Phase 1: 스키마 수정 (DB팀)
1. 개발 환경에서 스키마 수정 테스트
2. ModelOps팀과 통합 테스트
3. 스테이징 환경 배포
4. 프로덕션 배포

### Phase 2: ModelOps 코드 배포 (ModelOps팀)
- DB 스키마 완료 후 전처리 레이어 및 배치 스크립트 배포

---

## 문의 및 검토

### 담당자
- ModelOps팀: [담당자명]
- DB팀: [담당자명]

### 검토 요청사항
1. 테이블 Primary Key 전략 확인 (latitude, longitude, risk_type 복합키)
2. JSONB 인덱싱 전략 (필요 시 GIN 인덱스 추가)
3. 파티셔닝 전략 (격자 수가 많아 파티션 고려 가능)
4. calculated_at 기반 데이터 보존 정책 (구 버전 데이터 삭제 여부)

---

## 첨부 파일
- 상세 계획: `C:\Users\Administrator\.claude\plans\replicated-cooking-locket.md`
- ERD 문서: `c:\Users\Administrator\Desktop\backend_aiops\docs\erd.md`
