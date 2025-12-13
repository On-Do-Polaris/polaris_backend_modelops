# DB 마이그레이션 요청: location_admin 테이블 인구 필드 추가

**작성일**: 2025-12-13
**요청자**: ModelOps Team
**우선순위**: Medium
**예상 작업 시간**: 1-2시간 (마이그레이션 + 검증)

---

## 1. 배경 및 목적

### 문제점
현재 `location_admin` 테이블은 시도별(level=1) 미래 인구 데이터만 보유하고 있으며, **읍면동(level=3) 단위의 현재 인구 데이터가 없습니다.**

### 필요성
Physical Risk 계산 시 읍면동별 미래 인구를 추정하기 위해 다음과 같은 계산 방식을 사용합니다:

```
미래 읍면동 인구 = (시도별 미래 인구) × (읍면동 현재 인구 / 시도별 현재 인구)
```

**현재 문제**:
- 읍면동 현재 인구 데이터가 없어 비율 계산 불가
- SGIS API로 매번 조회 시 성능 저하 및 API 호출 제한

**해결 방안**:
- 읍면동별 최신 인구 데이터를 DB에 저장
- 연 1회 또는 분기별 ETL로 업데이트

---

## 2. 테이블 스키마 변경

### 2.1 대상 테이블
- **테이블명**: `location_admin`
- **데이터베이스**: `datawarehouse`
- **현재 행 수**: 5,259 rows

### 2.2 추가할 컬럼

| 컬럼명 | 데이터 타입 | NULL 허용 | 기본값 | 설명 |
|--------|------------|----------|--------|------|
| `population_current` | `integer` | YES | `NULL` | SGIS API에서 조회한 최신 인구 (읍면동별, level=3) |
| `population_current_year` | `integer` | YES | `NULL` | 최신 인구 기준 연도 (예: 2024) |

### 2.3 데이터 채우기 계획

| level | 설명 | `population_current` | `population_current_year` |
|-------|------|---------------------|--------------------------|
| 1 | 시도 | `NULL` (비워둠) | `NULL` |
| 2 | 시군구 | `NULL` (비워둠) | `NULL` |
| 3 | 읍면동 | SGIS API 조회 후 저장 | `2024` |

**참고**: 시도(level=1)와 시군구(level=2)는 의도적으로 비워둡니다.

---

## 3. DB 마이그레이션 스크립트

### 3.1 컬럼 추가 (DDL)

```sql
-- location_admin 테이블에 인구 필드 추가
ALTER TABLE location_admin
ADD COLUMN population_current integer,
ADD COLUMN population_current_year integer;

-- 컬럼 코멘트 추가 (PostgreSQL)
COMMENT ON COLUMN location_admin.population_current IS 'SGIS API 최신 인구 (읍면동별, level=3)';
COMMENT ON COLUMN location_admin.population_current_year IS '최신 인구 기준 연도 (예: 2024)';
```

### 3.2 Rollback 스크립트

```sql
-- 롤백이 필요한 경우
ALTER TABLE location_admin
DROP COLUMN IF EXISTS population_current,
DROP COLUMN IF EXISTS population_current_year;
```

### 3.3 검증 쿼리

```sql
-- 1. 컬럼 추가 확인
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_name = 'location_admin'
  AND column_name IN ('population_current', 'population_current_year');

-- 2. 데이터 확인 (ETL 후 실행)
SELECT
    level,
    COUNT(*) as total_rows,
    COUNT(population_current) as filled_rows,
    MIN(population_current_year) as min_year,
    MAX(population_current_year) as max_year
FROM location_admin
GROUP BY level
ORDER BY level;

-- 예상 결과:
-- level | total_rows | filled_rows | min_year | max_year
-- ------|-----------|-------------|----------|----------
--   1   |    17     |      0      |   NULL   |   NULL
--   2   |   250     |      0      |   NULL   |   NULL
--   3   |  4,992    |   4,992     |   2024   |   2024
```

---

## 4. ETL 작업 필요 사항

### 4.1 데이터 소스
- **API**: SGIS (Statistical Geographic Information Service)
- **제공기관**: 통계청
- **도메인**: `https://sgisapi.mods.go.kr` (2025년 11월 20일 변경)

### 4.2 API 인증 정보

**환경변수 필요**:
```bash
SGIS_SERVICE_ID=your_service_id_here
SGIS_SECURITY_KEY=your_security_key_here
```

**주의사항**:
- API 키는 SGIS 공식 사이트(https://sgis.mods.go.kr)에서 발급
- 일일 호출 횟수 제한 있음 (대량 조회 시 주의)
- Token 유효기간 있음 (accessTimeout 참고)

### 4.3 ETL 프로세스 개요

```
1. SGIS OAuth 토큰 발급
   └─> https://sgisapi.mods.go.kr/OpenAPI3/auth/authentication.json

2. location_admin에서 level=3 (읍면동) 데이터 조회
   └─> SELECT admin_code, admin_name FROM location_admin WHERE level = 3

3. 각 읍면동별로 SGIS API 호출
   └─> https://sgisapi.mods.go.kr/OpenAPI3/stats/searchpopulation.json
   └─> 파라미터: year=2024, adm_cd={행정구역코드}, gender=0

4. 응답 데이터 파싱 후 DB 업데이트
   └─> UPDATE location_admin SET
       population_current = {인구수},
       population_current_year = 2024
       WHERE admin_code = {행정구역코드}
```

### 4.4 API 요청 예시

**Python 예제 코드**:
```python
import requests

# 1. OAuth 토큰 발급
auth_url = "https://sgisapi.mods.go.kr/OpenAPI3/auth/authentication.json"
auth_params = {
    'consumer_key': 'YOUR_SERVICE_ID',
    'consumer_secret': 'YOUR_SECURITY_KEY'
}
auth_response = requests.get(auth_url, params=auth_params)
access_token = auth_response.json()['result']['accessToken']

# 2. 인구통계 조회 (서울 강남구 읍면동별)
stats_url = "https://sgisapi.mods.go.kr/OpenAPI3/stats/searchpopulation.json"
stats_params = {
    'accessToken': access_token,
    'year': '2024',
    'adm_cd': '11230',  # 서울 강남구
    'low_search': '1',  # 1단계 하위 (읍면동)
    'gender': '0'  # 전체
}
stats_response = requests.get(stats_url, params=stats_params)
data = stats_response.json()

# 3. 결과 파싱
for item in data['result']:
    print(f"{item['adm_nm']}: {item['population']}명")
```

**응답 예시**:
```json
{
  "id": "API_0302",
  "result": [
    {
      "adm_cd": "11230580",
      "adm_nm": "삼성1동",
      "population": "11344"
    }
  ],
  "errMsg": "Success",
  "errCd": 0
}
```

---

## 5. 실행 계획

### 5.1 사전 준비 (완료 필요)
- [ ] SGIS API 키 발급 (개발/운영 환경별)
- [ ] 환경변수 설정 (.env 파일 또는 Secret Manager)
- [ ] ETL 스크립트 작성 및 테스트

### 5.2 마이그레이션 단계

| 단계 | 작업 | 담당 | 예상 시간 |
|------|------|------|----------|
| 1 | DB 백업 | DB 담당자 | 10분 |
| 2 | DDL 실행 (컬럼 추가) | DB 담당자 | 5분 |
| 3 | 검증 쿼리 실행 | DB 담당자 | 5분 |
| 4 | ETL 스크립트 실행 | ModelOps/ETL 담당자 | 30-60분 |
| 5 | 데이터 검증 | DB + ModelOps | 10분 |
| 6 | DBML 문서 업데이트 | DB 담당자 | 5분 |

### 5.3 배포 일정 (제안)
- **개발 환경**: 2025-12-14 (금)
- **스테이징 환경**: 2025-12-16 (월)
- **운영 환경**: 2025-12-18 (수)

---

## 6. 영향도 분석

### 6.1 기존 기능 영향
- **영향 없음**: 신규 컬럼 추가만 수행하며 기존 데이터 변경 없음
- **호환성**: NOT NULL 제약이 없어 기존 쿼리 영향 없음

### 6.2 성능 영향
- **조회 성능**: 컬럼 2개 추가로 미미한 영향 (인덱스 불필요)
- **저장 공간**: 약 5,000 rows × 8 bytes × 2 = 약 80KB 증가

### 6.3 관련 시스템
- **영향받는 시스템**:
  - Physical Risk Module (`exposure_calculator.py`)
  - Exposure Calculate Agents
  - Future Population Projection

---

## 7. 참고 자료

### 7.1 SGIS API 문서
- **공식 사이트**: https://sgis.mods.go.kr
- **API 문서**: https://sgis.mods.go.kr/developer/html/newOpenApi/api/dataApi/addressBoundary.html
- **내부 문서**: `polaris_backend_modelops/physical_risk_module_core_merge/Physical_RISK_calculate/docs/03_api_documentation/guides/05_SGIS_인구통계_API.md`

### 7.2 관련 코드
- **인구 계산 로직**: `polaris_backend_modelops/physical_risk_module_core_merge/Physical_RISK_calculate/src/calculators/exposure_calculator.py`
  - `interpolate_population_by_cagr()`: CAGR 기반 미래 인구 계산
  - `get_sigungu_future_population()`: 시군구별 미래 인구 비례 계산

- **ETL 참고 스크립트**: `polaris_backend_modelops/ETL/etl_base/local/scripts/04_load_population.py`

### 7.3 DBML 스키마
- **파일**: `polaris_backend_modelops/docs/dbml/Datawarehouse.dbml`
- **테이블**: `location_admin` (Line 26-56)

---

## 8. 리스크 및 대응 방안

| 리스크 | 가능성 | 영향도 | 대응 방안 |
|--------|--------|--------|----------|
| SGIS API 호출 제한 초과 | 중 | 중 | 배치 크기 조절, 재시도 로직 추가 |
| API 키 만료 | 낮 | 높 | 만료 전 알림, 자동 갱신 로직 |
| 행정구역 코드 불일치 | 중 | 중 | 매핑 테이블 사전 검증 |
| ETL 중단 | 낮 | 중 | 체크포인트 저장, 이어서 실행 가능 |

---

## 9. 문의 및 승인

### 문의처
- **ModelOps Team**: 인구 계산 로직 및 ETL 스크립트
- **DB Team**: 마이그레이션 실행 및 검증

### 승인 필요
- [ ] DB 팀장 승인
- [ ] ModelOps 팀장 승인
- [ ] 배포 일정 확정

---

## 부록: 도메인 변경 공지

**2025년 11월 20일부터 SGIS 도메인 주소가 변경되었습니다.**

| 구분 | 변경 전 URL | 변경 후 URL |
|------|------------|------------|
| SGIS 포털 | `sgis.kostat.go.kr` | `sgis.mods.go.kr` |
| SGIS 개발지원센터 오픈API | `sgisapi.kostat.go.kr` | `sgisapi.mods.go.kr` |
| SGIS 사전제공 통계지도 | `ndsm.kostat.go.kr` | `ndsm.mods.go.kr` |

⚠️ **기존 URL은 사용 불가하므로 반드시 새 URL로 업데이트 필요**

---

**End of Document**
