# DB 스키마 불일치 리포트

> **작성일**: 2025-12-12
> **작성자**: ModelOPS 개발팀
> **대상**: DB 담당자
> **목적**: ERD 문서와 실제 구현 코드 간 스키마 차이점 정리

---

## 📌 요약 (Executive Summary)

ERD 문서 ([erd (5).md](erd%20(5).md) v14)와 실제 ModelOPS 코드 간 **3개 테이블**에서 **스키마 불일치**가 발견되었습니다.

**영향 범위:**
- `exposure_results` 테이블: 컬럼 1개 누락, PK 구조 불일치
- `vulnerability_results` 테이블: PK 구조 불일치
- `aal_scaled_results` 테이블: PK 구조 불일치

**조치 필요 사항:**
1. DB 스키마에 누락된 컬럼 추가 또는 ERD 문서 수정
2. Primary Key 제약조건 정합성 확인

---

## 🔍 상세 불일치 내용

### 1. exposure_results 테이블

#### 1.1 누락된 컬럼: `normalized_asset_value`

**ERD 문서 (v14):**
```sql
| 컬럼명 | 타입 | 설명 | 실제 사용 |
|--------|------|------|----------|
| latitude | DECIMAL(9,6) PK | 격자 위도 | ✅ 모든 조회 |
| longitude | DECIMAL(9,6) PK | 격자 경도 | ✅ 모든 조회 |
| risk_type | VARCHAR(50) PK | 위험 유형 (9가지) | ✅ 리스크별 필터링 |
| site_id | UUID | 사업장 ID | ✅ 사업장 조회 |
| exposure_score | REAL | 노출도 점수 (0.0~1.0) | ✅ Physical Risk 계산 |
| proximity_factor | REAL | 근접도 계수 (0.0~1.0) | ✅ ModelOPS |
| normalized_asset_value | REAL | 정규화 자산가치 (0.0~1.0) | ✅ E Score 계산 |  ⬅️ ERD에 명시됨
| calculated_at | TIMESTAMP | 계산 시점 | ✅ 캐시 무효화 판단 |
```

**실제 DB 스키마 (schema_extensions.sql):**
```sql
CREATE TABLE IF NOT EXISTS exposure_results (
    latitude NUMERIC NOT NULL,
    longitude NUMERIC NOT NULL,
    risk_type VARCHAR(50) NOT NULL,
    exposure_score REAL,  -- 0.0 ~ 1.0
    proximity_factor REAL,  -- 위험 요소와의 근접도
    calculated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (latitude, longitude, risk_type)
);
-- ❌ normalized_asset_value 컬럼이 없음
-- ❌ site_id 컬럼이 없음
```

**실제 코드 사용 (connection.py:425-442):**
```python
cursor.execute("""
    INSERT INTO exposure_results
    (latitude, longitude, risk_type, exposure_score, proximity_factor,
     normalized_asset_value, calculated_at)  # ⬅️ normalized_asset_value 사용
    VALUES (%s, %s, %s, %s, %s, %s, NOW())
    ...
""", (
    result['latitude'],
    result['longitude'],
    result['risk_type'],
    result.get('exposure_score', 0.0),
    result.get('proximity_factor', 0.0),
    result.get('normalized_asset_value', 0.0)  # ⬅️ 값 삽입 시도
))
```

**현재 상태:**
- 코드는 `normalized_asset_value` 컬럼에 데이터를 삽입하려고 시도
- DB 스키마에는 해당 컬럼이 없음
- **결과**: 데이터 삽입 시 에러 발생 가능성 있음

**integrated_risk_agent.py:563-564에서의 처리:**
```python
# 3. normalized_asset_value
normalized_asset_value = None  # 현재는 None으로 설정
```
→ 현재는 항상 `None`을 전달하지만, 컬럼이 없으면 에러 발생

#### 1.2 Primary Key 구조 불일치: `site_id` 누락

**ERD 문서:**
- PK: `(latitude, longitude, risk_type)` + `site_id` 포함 (명시적 PK 표기는 없지만 사업장별 조회 가능하다고 기술)

**실제 DB 스키마:**
- PK: `(latitude, longitude, risk_type)`
- `site_id` 컬럼 없음

**영향:**
- ERD에는 "사업장별로 저장"된다고 기술되어 있으나, 실제로는 격자 좌표별로 저장됨
- 사업장 ID로 직접 조회 불가능 (좌표를 알아야 조회 가능)

---

### 2. vulnerability_results 테이블

#### 2.1 Primary Key 구조 불일치: `site_id` 누락

**ERD 문서 (라인 792-796):**
```
| 컬럼명 | 타입 | 설명 | 역할 | 실제 사용 |
|--------|------|------|------|----------|
| latitude | DECIMAL(9,6) PK | 격자 위도 | 위치 식별 | ✅ 좌표 기반 조회 |
| longitude | DECIMAL(9,6) PK | 격자 경도 | 위치 식별 | ✅ 좌표 기반 조회 |
| risk_type | VARCHAR(50) PK | 위험 유형 (9가지) | 리스크별 V Score 구분 | ✅ 리스크별 필터링 |
| site_id | UUID | 사업장 ID | Application DB sites.id 참조 | ✅ 사업장 조회 |  ⬅️ ERD에 명시됨
```

**실제 DB 스키마 (schema_extensions.sql:24-35):**
```sql
CREATE TABLE IF NOT EXISTS vulnerability_results (
    latitude NUMERIC NOT NULL,
    longitude NUMERIC NOT NULL,
    risk_type VARCHAR(50) NOT NULL,
    vulnerability_score REAL,
    vulnerability_level VARCHAR(20),
    factors JSONB,
    calculated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (latitude, longitude, risk_type),
    ...
);
-- ❌ site_id 컬럼이 없음
```

**실제 코드 사용 (connection.py:466-483):**
```python
cursor.execute("""
    INSERT INTO vulnerability_results
    (latitude, longitude, risk_type, vulnerability_score,
     vulnerability_level, factors, calculated_at)
    VALUES (%s, %s, %s, %s, %s, %s::jsonb, NOW())
    ...
""", (
    result['latitude'],
    result['longitude'],
    result['risk_type'],
    ...
))
# site_id를 사용하지 않음
```

**영향:**
- ERD 문서와 실제 구현 모두 `site_id`를 사용하지 않음
- 그러나 ERD 문서에는 "사업장 조회"에 사용된다고 기술됨
- **결론**: ERD 문서의 오류 (컬럼 설명이 잘못됨)

---

### 3. aal_scaled_results 테이블

#### 3.1 Primary Key 구조 불일치: `site_id` 누락

**ERD 문서 (라인 876-880):**
```
| 컬럼명 | 타입 | 설명 | 역할 | 실제 사용 |
|--------|------|------|------|----------|
| latitude | DECIMAL(9,6) PK | 격자 위도 | 위치 식별 | ✅ 좌표 기반 조회 |
| longitude | DECIMAL(9,6) PK | 격자 경도 | 위치 식별 | ✅ 좌표 기반 조회 |
| risk_type | VARCHAR(50) PK | 위험 유형 (9가지) | 리스크별 AAL 구분 | ✅ 리스크별 필터링 |
| site_id | UUID | 사업장 ID | Application DB sites.id 참조 | ✅ 사업장 조회 |  ⬅️ ERD에 명시됨
```

**실제 DB 스키마 (schema_extensions.sql:49-62):**
```sql
CREATE TABLE IF NOT EXISTS aal_scaled_results (
    latitude NUMERIC NOT NULL,
    longitude NUMERIC NOT NULL,
    risk_type VARCHAR(50) NOT NULL,
    base_aal REAL,
    vulnerability_scale REAL,
    final_aal REAL,
    insurance_rate REAL DEFAULT 0.0,
    expected_loss BIGINT,
    calculated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (latitude, longitude, risk_type),
    ...
);
-- ❌ site_id 컬럼이 없음
```

**실제 코드 사용 (connection.py:505-526):**
```python
cursor.execute("""
    INSERT INTO aal_scaled_results
    (latitude, longitude, risk_type, base_aal, vulnerability_scale,
     final_aal, insurance_rate, expected_loss, calculated_at)
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, NOW())
    ...
""", (
    result['latitude'],
    result['longitude'],
    result['risk_type'],
    ...
))
# site_id를 사용하지 않음
```

**영향:**
- ERD와 실제 구현 모두 `site_id`를 사용하지 않음
- ERD 쿼리 예시 (라인 853-860)에는 `site_id`로 조회하는 쿼리가 명시되어 있으나 실제로는 불가능
- **결론**: ERD 문서의 오류

---

## 📋 조치 필요 사항

### Priority 1: 즉시 조치 필요 (Critical)

#### 1. exposure_results 테이블 - `normalized_asset_value` 컬럼 추가

**옵션 A: DB 스키마 수정 (권장)**
```sql
ALTER TABLE exposure_results
ADD COLUMN normalized_asset_value REAL;

COMMENT ON COLUMN exposure_results.normalized_asset_value
IS '정규화된 자산가치 (0.0-1.0)';
```

**옵션 B: 코드 수정**
```python
# connection.py:425-442 수정
cursor.execute("""
    INSERT INTO exposure_results
    (latitude, longitude, risk_type, exposure_score, proximity_factor,
     calculated_at)  # normalized_asset_value 제거
    VALUES (%s, %s, %s, %s, %s, NOW())
    ...
""", (
    result['latitude'],
    result['longitude'],
    result['risk_type'],
    result.get('exposure_score', 0.0),
    result.get('proximity_factor', 0.0)
    # normalized_asset_value 제거
))
```

**권장**: **옵션 A (DB 스키마 수정)**
- 이유: ERD 문서에 명시된 대로 자산가치 정보가 향후 필요할 수 있음
- `integrated_risk_agent.py:564`에서 현재는 `None`을 사용하지만, 향후 실제 값 계산 가능

---

### Priority 2: 문서 정합성 확인 (High)

#### 2. ERD 문서 수정 - `site_id` 관련 설명 수정

**현재 ERD 오류:**
- 3개 테이블 모두 `site_id` 컬럼이 있다고 기술되어 있으나 실제로는 없음
- 쿼리 예시에 `WHERE site_id = 'uuid-site-id'` 사용 불가능

**수정 필요 사항:**

1. **exposure_results 테이블 (ERD 라인 714-723)**
   - ❌ 삭제: `site_id | UUID | 사업장 ID | Application DB sites.id 참조 | ✅ 사업장 조회`
   - ✅ 추가 설명: "사업장별 조회는 좌표 변환 후 (latitude, longitude)로 수행"

2. **vulnerability_results 테이블 (ERD 라인 791-800)**
   - ❌ 삭제: `site_id | UUID | 사업장 ID | Application DB sites.id 참조 | ✅ 사업장 조회`
   - ✅ 추가 설명: "사업장 위치 좌표 기반 조회"

3. **aal_scaled_results 테이블 (ERD 라인 875-886)**
   - ❌ 삭제: `site_id | UUID | 사업장 ID | Application DB sites.id 참조 | ✅ 사업장 조회`
   - ✅ 추가 설명: "사업장별 AAL 집계는 Application DB에서 좌표 조인으로 수행"

4. **쿼리 예시 수정 (ERD 라인 700-712, 774-789, 852-872)**
   - ❌ 삭제: `WHERE site_id = 'uuid-site-id'` 쿼리
   - ✅ 수정: `WHERE latitude = 37.50 AND longitude = 127.00` 쿼리로 변경

---

### Priority 3: 데이터 모델 개선 검토 (Medium)

#### 3. 사업장별 조회 성능 개선 검토

**현재 구조의 한계:**
- ModelOPS 결과 테이블은 격자 좌표 기반 저장 (`latitude`, `longitude`)
- 사업장 정보는 Application DB에 UUID로 저장
- 사업장별 리스크 조회 시 매번 좌표 변환 + 조인 필요

**개선 방안 (장기 계획):**

**옵션 1: site_id 컬럼 추가 (정규화)**
```sql
-- 3개 테이블에 site_id 추가
ALTER TABLE exposure_results ADD COLUMN site_id UUID;
ALTER TABLE vulnerability_results ADD COLUMN site_id UUID;
ALTER TABLE aal_scaled_results ADD COLUMN site_id UUID;

-- 복합 인덱스 추가
CREATE INDEX idx_exposure_site ON exposure_results(site_id, risk_type);
CREATE INDEX idx_vulnerability_site ON vulnerability_results(site_id, risk_type);
CREATE INDEX idx_aal_scaled_site ON aal_scaled_results(site_id, risk_type);
```

**장점:**
- 사업장별 조회 성능 향상 (좌표 조인 불필요)
- ERD 문서와 일치
- Application DB와 직접 FK 연결 가능

**단점:**
- 데이터 중복 (동일 좌표에 여러 사업장 존재 시)
- 기존 데이터 마이그레이션 필요
- ModelOPS Agent 코드 수정 필요

**옵션 2: 뷰(View) 생성 (비정규화)**
```sql
-- 사업장별 리스크 조회용 뷰 생성
CREATE VIEW v_site_risk_results AS
SELECT
    s.site_id,
    s.site_name,
    e.risk_type,
    e.exposure_score,
    v.vulnerability_score,
    a.final_aal,
    a.expected_loss
FROM application.sites s
JOIN datawarehouse.exposure_results e
    ON e.latitude = s.latitude AND e.longitude = s.longitude
JOIN datawarehouse.vulnerability_results v
    ON v.latitude = s.latitude AND v.longitude = s.longitude
    AND v.risk_type = e.risk_type
JOIN datawarehouse.aal_scaled_results a
    ON a.latitude = s.latitude AND a.longitude = s.longitude
    AND a.risk_type = e.risk_type;
```

**장점:**
- 기존 스키마 유지
- 코드 수정 불필요
- 논리적 데이터 모델 개선

**단점:**
- 조회 성능은 옵션 1보다 낮음
- 복잡한 조인 쿼리

---

## 🔧 즉시 적용 가능한 SQL 스크립트

### 스크립트 1: exposure_results 컬럼 추가

```sql
-- exposure_results 테이블에 normalized_asset_value 컬럼 추가
ALTER TABLE exposure_results
ADD COLUMN IF NOT EXISTS normalized_asset_value REAL;

COMMENT ON COLUMN exposure_results.normalized_asset_value
IS '정규화된 자산가치 (0.0-1.0, 현재 미사용 - 향후 확장)';

-- 기존 데이터에 기본값 설정 (NULL 허용)
UPDATE exposure_results
SET normalized_asset_value = NULL
WHERE normalized_asset_value IS NULL;
```

**적용 후 확인:**
```sql
-- 컬럼 추가 확인
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_name = 'exposure_results'
ORDER BY ordinal_position;
```

---

## 📊 영향 범위 분석

### 1. 현재 운영 중인 시스템에 미치는 영향

| 항목 | 영향도 | 설명 |
|------|--------|------|
| **데이터 삽입** | 🔴 High | `normalized_asset_value` 컬럼 누락으로 INSERT 실패 가능성 |
| **데이터 조회** | 🟡 Medium | `site_id` 부재로 사업장별 직접 조회 불가 (좌표 변환 필요) |
| **리포트 생성** | 🟢 Low | 현재 코드는 좌표 기반 조회로 동작하므로 영향 없음 |
| **API 응답** | 🟢 Low | FastAPI는 좌표 기반 조회 사용 중 |

### 2. 코드 수정 필요 파일

| 파일 경로 | 수정 필요 여부 | 이유 |
|----------|---------------|------|
| `modelops/database/schema_extensions.sql` | ✅ 필수 | `normalized_asset_value` 컬럼 추가 |
| `modelops/database/connection.py` | ⚠️ 선택 | 옵션 B 선택 시 수정 필요 |
| `modelops/agents/risk_assessment/integrated_risk_agent.py` | ⚠️ 향후 | `normalized_asset_value` 계산 로직 구현 시 |
| `docs/erd (5).md` | ✅ 필수 | `site_id` 관련 설명 수정 |

---

## ✅ 권장 조치 순서

### Phase 1: 긴급 수정 (1일 내)

1. ✅ **DB 스키마 수정**
   ```bash
   # schema_extensions.sql 수정
   # exposure_results에 normalized_asset_value 컬럼 추가
   psql -h [DB_HOST] -U [DB_USER] -d datawarehouse -f schema_extensions.sql
   ```

2. ✅ **스키마 변경 적용**
   ```sql
   ALTER TABLE exposure_results ADD COLUMN normalized_asset_value REAL;
   ```

3. ✅ **코드 동작 확인**
   ```bash
   # ModelOPS 배치 작업 테스트
   python -m modelops.batch.ondemand_risk_batch --test
   ```

### Phase 2: 문서 정합성 확보 (3일 내)

4. ✅ **ERD 문서 수정**
   - `site_id` 컬럼 설명 삭제
   - 쿼리 예시 수정
   - 데이터 모델 설명 보완

5. ✅ **변경 이력 기록**
   - ERD v14 → v15 업데이트
   - 제·개정 이력 추가

### Phase 3: 장기 개선 (선택, 1개월 내)

6. ⚠️ **성능 개선 검토**
   - 사업장별 조회 패턴 분석
   - `site_id` 컬럼 추가 또는 뷰 생성 검토
   - 인덱스 최적화

---

## 📞 문의 및 협의 사항

**담당자 연락처:**
- ModelOPS 개발팀: [연락처]
- DB 관리팀: [연락처]

**협의 필요 사항:**
1. `normalized_asset_value` 컬럼 추가 일정
2. ERD 문서 수정 검토 및 승인
3. `site_id` 컬럼 추가 여부 (장기 계획)

**첨부 파일:**
- 실제 DB 스키마: `modelops/database/schema_extensions.sql`
- ERD 문서: `docs/erd (5).md`
- 코드 참조: `modelops/database/connection.py`

---

## 📝 체크리스트

### DB 담당자 확인 사항

- [ ] `exposure_results` 테이블에 `normalized_asset_value` 컬럼 추가 완료
- [ ] 컬럼 추가 후 데이터 삽입 테스트 완료
- [ ] ERD 문서 v15 업데이트 완료
- [ ] `site_id` 관련 설명 수정 완료
- [ ] 변경사항 운영 환경 반영 완료

### 개발팀 확인 사항

- [ ] 스키마 변경 후 코드 동작 검증 완료
- [ ] `normalized_asset_value` 계산 로직 구현 계획 수립
- [ ] 사업장별 조회 성능 모니터링 시작
- [ ] 문서 업데이트 내용 확인 완료

---

**리포트 종료**
