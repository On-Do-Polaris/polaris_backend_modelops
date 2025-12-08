# 기후 리스크 리포트 작성용 LLM 프롬프트 가이드라인

**문서 버전**: 1.0
**작성일**: 2025-12-02
**목적**: AI Agent가 기후 리스크 평가 리포트 작성 시 사용할 데이터와 프롬프트 지침

---

## 목차
1. [개요](#1-개요)
2. [사용 가능한 데이터 소스](#2-사용-가능한-데이터-소스)
3. [리스크별 프롬프트 가이드라인](#3-리스크별-프롬프트-가이드라인)
4. [프롬프트 템플릿](#4-프롬프트-템플릿)
5. [인사이트 도출 예시](#5-인사이트-도출-예시)

---

## 1. 개요

### 1.1 목적
LLM이 기후 리스크 평가 결과(H, E, V, AAL)를 기반으로 **근거 있는 인사이트**를 제공하기 위한 가이드라인입니다.

### 1.2 핵심 원칙
✅ **데이터 기반 분석**: 모든 주장은 실제 계산된 데이터로 뒷받침
✅ **정량적 근거**: 점수, 확률, 손상률 등 구체적 수치 제시
✅ **실행 가능한 권고사항**: 단순 설명이 아닌 의사결정 지원
✅ **투명성**: 계산 방법론 및 데이터 출처 명시

---

## 2. 사용 가능한 데이터 소스

### 2.1 데이터베이스 테이블

#### A. **probability_results** (확률 및 AAL)
```sql
SELECT
    latitude,
    longitude,
    risk_type,
    probability AS aal,  -- Annual Average Loss (연평균 손실률)
    bin_data,            -- bin별 상세 확률 및 손상률 (JSONB)
    calculated_at
FROM probability_results
WHERE latitude = ? AND longitude = ?
```

**bin_data 구조 예시**:
```json
{
  "bins": [
    {
      "bin": 1,
      "range": "0 ~ 5일",
      "probability": 0.6234,      // 60.23% 확률
      "base_damage_rate": 0.001   // 0.1% 손상률
    },
    {
      "bin": 2,
      "range": "5 ~ 10일",
      "probability": 0.2891,
      "base_damage_rate": 0.003
    },
    ...
  ],
  "formula": "AAL = Σ(P[i] × DR[i])",
  "time_unit": "yearly",
  "total_years": 30
}
```

#### B. **hazard_results** (위험 강도)
```sql
SELECT
    latitude,
    longitude,
    risk_type,
    hazard_score,        -- 0-1 스케일
    hazard_score_100,    -- 0-100 스케일
    hazard_level,        -- MINIMAL, LOW, MEDIUM, HIGH, CRITICAL
    calculated_at
FROM hazard_results
WHERE latitude = ? AND longitude = ?
```

**hazard_level 기준**:
- MINIMAL: < 20점
- LOW: 20-40점
- MEDIUM: 40-60점
- HIGH: 60-80점
- CRITICAL: 80+ 점

#### C. **vulnerability_results** (취약성)
```sql
SELECT
    latitude,
    longitude,
    risk_type,
    vulnerability_score,  -- 0-100 스케일
    vulnerability_level,  -- LOW, MEDIUM, HIGH
    factors,             -- 취약성 요인 (JSONB)
    calculated_at
FROM vulnerability_results
WHERE latitude = ? AND longitude = ?
```

**factors 구조 예시**:
```json
{
  "building_age": 35,
  "structure": "철근콘크리트",
  "main_purpose": "업무시설",
  "floors_below": 2,
  "has_piloti": false,
  "age_penalty": 20,
  "structure_adjustment": -10,
  "basement_penalty": 25
}
```

#### D. **exposure_results** (노출도)
```sql
SELECT
    latitude,
    longitude,
    risk_type,
    exposure_score,      -- 0-1 스케일
    proximity_factor,    -- 위험원과의 근접도
    calculated_at
FROM exposure_results
WHERE latitude = ? AND longitude = ?
```

#### E. **aal_scaled_results** (최종 AAL)
```sql
SELECT
    latitude,
    longitude,
    risk_type,
    base_aal,            -- 기본 AAL (probability_results에서)
    vulnerability_scale, -- F_vuln (0.9 ~ 1.1)
    final_aal,           -- base_aal × F_vuln × (1 - insurance_rate)
    insurance_rate,
    expected_loss,       -- final_aal × 자산가치
    calculated_at
FROM aal_scaled_results
WHERE latitude = ? AND longitude = ?
```

**AAL Scaling 공식**:
```
F_vuln = 0.9 + 0.2 × (V_score / 100)
final_AAL = base_AAL × F_vuln × (1 - insurance_rate)
expected_loss = final_AAL × asset_value
```

#### F. **기후 데이터** (Datawarehouse)
```sql
-- 예: 극한 고온 데이터
SELECT
    year,
    month,
    wsdi,  -- Warm Spell Duration Index
    ta,    -- 평균 기온
FROM wsdi_data
WHERE latitude = ? AND longitude = ?
ORDER BY year, month
```

**9대 리스크별 기후 변수**:
| 리스크 | 변수명 | 설명 |
|--------|--------|------|
| extreme_heat | WSDI | 폭염 지속 기간 지수 |
| extreme_cold | CSDI | 한파 지속 기간 지수 |
| drought | SPEI12 | 가뭄 지수 (12개월) |
| river_flood | RX5DAY | 5일 최대 강수량 |
| urban_flood | RX1DAY | 1일 최대 강수량 |
| wildfire | FWI | 산불 위험 지수 |
| water_stress | WSI | 물 부족 지수 |
| typhoon | S_tc | 태풍 노출 지수 |
| sea_level_rise | ZOS | 해수면 높이 |

---

## 3. 리스크별 프롬프트 가이드라인

### 3.1 극한 고온 (Extreme Heat)

#### 제공해야 할 정보
1. **현재 위험 수준**
   ```
   - Hazard Score: 75/100 (HIGH)
   - WSDI 평균: 15.3일 (최근 10년)
   - WSDI 추세: +2.1일/10년 증가
   ```

2. **AAL 및 손실 예측**
   ```
   - Base AAL: 0.0234 (2.34%)
   - Vulnerability Scale: 1.08 (건물 연식 35년, 목조 구조)
   - Final AAL: 0.0253 (2.53%)
   - 예상 연간 손실: 25,300,000원 (자산가치 10억 가정)
   ```

3. **bin별 확률 분포**
   ```
   - bin1 (WSDI < 5일): 32.1% 발생, 0.1% 손상률
   - bin2 (5-10일): 28.9% 발생, 0.3% 손상률
   - bin3 (10-15일): 24.5% 발생, 1.0% 손상률
   - bin4 (15-20일): 10.2% 발생, 2.0% 손상률
   - bin5 (20일+): 4.3% 발생, 3.5% 손상률 → **핵심 리스크**
   ```

4. **취약성 요인 분석**
   ```
   - 건물 연식 35년 (+20점 페널티)
   - 목조 구조 (+15점 페널티) → 단열 취약
   - 업무시설 (+10점) → 높은 냉방 부하
   - 총 취약성 점수: 85/100 (HIGH)
   ```

#### 인사이트 도출 방향
- **극심한 폭염(bin5) 빈도 증가 추세** → SSP 시나리오별 미래 전망
- **노후 건물 + 목조 구조** → 냉방 효율 개선 필요
- **업무시설 특성** → 근무 시간대 집중 리스크

#### 권고사항 예시
```
1. [긴급] 극심한 폭염(WSDI 20일+) 발생 시 냉방 설비 과부하 위험
   - 발생 확률: 4.3% (연간 약 2주 중 3일)
   - 예상 손상률: 3.5%
   - 권고: 예비 냉방 설비 확보, 온도 모니터링 시스템 도입

2. [중기] 건물 단열 개선으로 취약성 20% 감소 가능
   - 현재 V_score: 85 → 개선 후 68 예상
   - AAL 절감 효과: 2.53% → 2.01% (약 520만원/년 절감)

3. [장기] SSP5-8.5 시나리오 하 2050년 폭염일 30% 증가 전망
   - 현재 AAL 대비 1.5배 증가 예상
```

---

### 3.2 하천 홍수 (River Flood)

#### 제공해야 할 정보
1. **강수 강도 분석**
   ```
   - Hazard Score: 62/100 (HIGH)
   - RX5DAY 최대값: 287mm (2023년)
   - RX5DAY 90th percentile: 195mm
   ```

2. **지하층 침수 리스크**
   ```
   - 지하 2층 보유 (+25점 취약성)
   - 필로티 구조 없음 (+10점)
   - 홍수 위험 구역 내 위치 (+15점)
   - 총 취약성: 90/100 (CRITICAL)
   ```

3. **bin별 강수 시나리오**
   ```
   - bin1 (< 100mm): 65% 확률, 0.5% 손상
   - bin2 (100-150mm): 20% 확률, 2% 손상
   - bin3 (150-200mm): 10% 확률, 5% 손상
   - bin4 (200-250mm): 3% 확률, 10% 손상
   - bin5 (250mm+): 2% 확률, 20% 손상 → **재난 수준**
   ```

#### 인사이트 도출 방향
- **지하층 침수 시 복구 비용 막대** → bin4, bin5 집중 대응
- **최근 10년 극한 강수 빈도 증가** → 배수 시스템 한계 도달
- **홍수 위험 구역** → 지자체 방재 계획 확인 필요

#### 권고사항 예시
```
1. [최우선] 지하층 방수 및 배수 시스템 강화
   - 200mm+ 강수 시 침수 확률: 5%
   - 침수 발생 시 예상 손실: 자산의 20% (2억원)
   - ROI: 5년 내 회수 가능 (연간 4천만원 리스크 감소)

2. [중기] 홍수 조기 경보 시스템 연동
   - RX5DAY 150mm+ 예보 시 자동 알림
   - 지하층 자산 사전 이동 프로토콜 수립

3. [장기] 지하 공간 용도 전환 검토
   - 고가 자산 지상층 이전
   - 지하층 → 주차장 또는 비상 저장소로 전환
```

---

### 3.3 가뭄 (Drought)

#### 제공해야 할 정보
1. **가뭄 심도 분석**
   ```
   - Hazard Score: 45/100 (MEDIUM)
   - SPEI-12 평균: -0.8 (경미한 가뭄)
   - SPEI-12 최저: -2.3 (극심한 가뭄, 2022년)
   ```

2. **용수 의존도**
   ```
   - 업무시설: 중간 의존도
   - 비상 급수 시설: 없음 (+20점 취약성)
   - 물 저장 용량: 1일치
   - 총 취약성: 55/100 (MEDIUM)
   ```

3. **bin별 가뭄 기간**
   ```
   - bin1 (정상, SPEI > -0.5): 70% 확률, 0% 손상
   - bin2 (경미, -1.0 < SPEI < -0.5): 18% 확률, 0.5% 손상
   - bin3 (중등도, -1.5 < SPEI < -1.0): 8% 확률, 2% 손상
   - bin4 (심각, -2.0 < SPEI < -1.5): 3% 확률, 5% 손상
   - bin5 (극심, SPEI < -2.0): 1% 확률, 10% 손상
   ```

#### 인사이트 도출 방향
- **가뭄의 점진적 특성** → 조기 경보 시 대응 가능
- **비상 급수 부재** → 업무 연속성 리스크
- **기후변화로 가뭄 빈도 증가** → 물 관리 전략 필요

#### 권고사항 예시
```
1. [중기] 비상 급수 시스템 구축
   - 현재 1일 저장 → 7일로 확대
   - 비용: 약 2천만원
   - 연간 리스크 절감: 약 500만원 (AAL 0.8% → 0.5%)

2. [단기] 물 절약 및 재활용 시스템
   - 우수 집수 시스템 도입
   - 절수 기기 설치 (화장실, 냉각탑 등)
   - 연간 용수비 10% 절감 + 리스크 감소

3. [장기] 가뭄 모니터링 및 대응 절차 수립
   - SPEI-12 < -1.0 시 1단계 절수
   - SPEI-12 < -1.5 시 2단계 절수 + 비상 급수 준비
```

---

### 3.4 산불 (Wildfire)

#### 제공해야 할 정보
1. **산불 위험 지수**
   ```
   - Hazard Score: 38/100 (LOW-MEDIUM)
   - FWI 평균: 12.5 (보통)
   - FWI 최대: 45.3 (매우 높음, 봄철)
   ```

2. **건물 위치 및 구조**
   ```
   - 산림과의 거리: 500m (근접)
   - 방화벽: 없음 (+20점 취약성)
   - 목조 구조 (+15점)
   - 소방도로 접근성: 양호 (-10점)
   - 총 취약성: 65/100 (MEDIUM-HIGH)
   ```

3. **계절별 산불 위험**
   ```
   - 봄(3-5월): FWI 평균 25.3 (HIGH)
   - 여름(6-8월): FWI 평균 8.1 (LOW)
   - 가을(9-11월): FWI 평균 15.7 (MEDIUM)
   - 겨울(12-2월): FWI 평균 18.2 (MEDIUM)
   ```

#### 인사이트 도출 방향
- **봄철 집중 리스크** → 3-5월 특별 관리
- **목조 구조 + 방화벽 부재** → 화재 확산 속도 빠름
- **산림 근접성** → 산불 비화 직접 영향권

#### 권고사항 예시
```
1. [긴급] 방화벽 및 방화 구역 설치
   - 건물 주변 30m 방화대 조성
   - 불연성 외벽 마감재 교체
   - 비용: 약 5천만원
   - AAL 절감: 1.2% → 0.6% (연간 600만원 절감)

2. [단기] 봄철 산불 대응 체계 강화
   - 3-5월 FWI 30+ 예보 시 비상 체제
   - 소화 장비 점검 및 비상 연락망 구축
   - 직원 산불 대피 훈련

3. [중기] 건물 외벽 및 지붕 불연화
   - 목조 외벽 → 불연재 교체
   - 취약성 65 → 40으로 감소
   - 보험료 절감 효과 추가
```

---

## 4. 프롬프트 템플릿

### 4.1 전체 리포트 생성 프롬프트

```markdown
# 역할
당신은 기후 리스크 분석 전문가입니다. IPCC AR6 방법론을 기반으로 건물의 기후 리스크를 평가하고, 데이터 기반 인사이트와 실행 가능한 권고사항을 제공합니다.

# 입력 데이터
## 1. 위치 정보
- 위도: {latitude}
- 경도: {longitude}
- 주소: {address}

## 2. 건물 정보
- 건물 연식: {building_age}년
- 구조: {structure}
- 주용도: {main_purpose}
- 지하층: {floors_below}층
- 지상층: {floors_above}층
- 연면적: {total_area}m²

## 3. 리스크 점수 (9대 기후 리스크)
{risk_scores_table}

## 4. 상세 데이터
### 극한 고온 (Extreme Heat)
- Hazard Score: {h_score}/100 ({h_level})
- Vulnerability Score: {v_score}/100
- Base AAL: {base_aal}%
- Final AAL: {final_aal}%
- bin별 확률 분포:
{bin_distribution}

[... 다른 8개 리스크 동일 형식 ...]

# 출력 형식
다음 구조로 리포트를 작성하세요:

## 1. 종합 요약 (Executive Summary)
- 전체 리스크 수준 평가 (HIGH/MEDIUM/LOW)
- 최우선 대응 리스크 3개
- 총 예상 연간 손실 (AAL 합계 × 자산가치)

## 2. 리스크별 상세 분석 (각 리스크당)
### 2.1 극한 고온
#### 현황
- Hazard 수준 및 추세
- 과거 데이터 분석 (최근 10년)
- bin별 발생 확률 및 손상률

#### 취약성 분석
- 건물 특성상 취약 요인 (구체적 점수 근거)
- 취약성이 AAL에 미치는 영향

#### 예상 손실
- Base AAL vs Final AAL 비교
- 연간 예상 손실액 (정량적)
- 최악의 시나리오 (bin5 발생 시)

#### 인사이트
- 데이터에서 도출된 핵심 인사이트 2-3개
- 타 리스크와의 복합 영향 (있는 경우)

[... 9개 리스크 전부 작성 ...]

## 3. 우선순위별 권고사항
### 최우선 (즉시 실행)
1. [리스크명] 권고사항
   - 배경: (데이터 근거)
   - 조치: (구체적 실행 방안)
   - 효과: (정량적 AAL 절감)
   - 투자 회수 기간

### 중기 (6개월 이내)
[동일 형식]

### 장기 (1년 이상)
[동일 형식]

## 4. 기후 시나리오별 전망
- SSP1-2.6 (저탄소): 리스크 추세
- SSP2-4.5 (중도): 리스크 추세
- SSP3-7.0 (고탄소): 리스크 추세
- SSP5-8.5 (최악): 리스크 추세

# 작성 원칙
1. 모든 수치는 입력 데이터에서만 사용 (추측 금지)
2. 권고사항은 ROI 또는 비용 대비 효과 제시
3. 전문 용어는 쉽게 풀어 설명
4. 긍정적 측면도 언급 (잘 관리된 부분)
5. 비교 기준 제시 (전국 평균, 동일 용도 건물 평균 등)
```

---

### 4.2 단일 리스크 분석 프롬프트

```markdown
# 역할
당신은 {risk_name} 전문 분석가입니다.

# 입력 데이터
- Hazard Score: {h_score}/100
- Vulnerability Score: {v_score}/100
- AAL: {aal}%
- bin 분포: {bins}
- 취약성 요인: {v_factors}
- 기후 데이터: {climate_data}

# 분석 요청
다음 질문에 데이터 기반으로 답변하세요:

1. 현재 이 건물의 {risk_name} 리스크 수준은 어느 정도인가?
   - Hazard, Vulnerability, AAL 종합 평가
   - 전국 평균 대비 수준 (높음/보통/낮음)

2. 왜 이런 리스크 수준이 나왔는가?
   - Hazard가 높은/낮은 이유 (기후 데이터 근거)
   - Vulnerability가 높은/낮은 이유 (건물 특성 근거)
   - AAL 계산 과정 설명

3. 어떤 시나리오에서 큰 손실이 발생하는가?
   - 최악의 bin (bin4, bin5) 분석
   - 발생 확률 × 손상률 = 리스크

4. 무엇을 해야 하는가?
   - 즉시 조치 사항 (높은 ROI)
   - 중장기 개선 방안
   - 각 조치의 예상 AAL 절감 효과

# 출력 형식
Markdown 형식, 2000자 이내, 비전문가도 이해 가능한 언어
```

---

### 4.3 비교 분석 프롬프트

```markdown
# 역할
당신은 기후 리스크 비교 분석 전문가입니다.

# 입력 데이터
## 건물 A (현재 건물)
{building_a_data}

## 건물 B (비교 대상)
{building_b_data}

# 분석 요청
두 건물의 리스크를 비교 분석하고, 차이가 발생하는 이유를 데이터로 설명하세요.

## 1. 전체 리스크 비교
- 총 AAL 비교
- 가장 큰 차이를 보이는 리스크 3개

## 2. 리스크별 상세 비교
각 리스크에 대해:
- Hazard 차이 (위치 차이로 인한)
- Vulnerability 차이 (건물 특성 차이로 인한)
- AAL 차이 (종합)

## 3. 차이 발생 원인 분석
- 위치 요인 (위도, 경도, 지형)
- 건물 요인 (연식, 구조, 용도)
- 상호작용 효과

## 4. 권고사항
- 건물 A가 건물 B 수준으로 리스크를 낮추려면?
- 필요한 투자 및 예상 효과
```

---

## 5. 인사이트 도출 예시

### 5.1 우수 사례: 데이터 기반 인사이트

#### ✅ Good Example
```
"극한 고온 리스크 분석 결과, 이 건물은 WSDI 20일 이상 극심한 폭염이
발생할 확률이 연간 4.3%입니다. 이는 약 25년에 1회 발생하는 수준이지만,
발생 시 손상률이 3.5%로 매우 높습니다.

건물의 취약성 점수 85/100은 주로 다음 요인에서 기인합니다:
- 건물 연식 35년 (+20점): 노후 단열재로 인한 냉방 효율 저하
- 목조 구조 (+15점): 열전도율이 철근콘크리트 대비 3배 높음
- 업무시설 (+10점): 근무 시간대(09:00-18:00) 냉방 부하 집중

bin별 분석 결과, bin3-5 (WSDI 10일 이상)의 누적 확률이 39%로,
전국 평균 28%보다 11%p 높습니다. 이는 해당 지역의 도시열섬 효과로
야간 최저 기온이 주변 지역보다 평균 2.3°C 높기 때문입니다.

권고: 건물 단열 개선 시 취약성을 85 → 68로 감소시킬 수 있으며,
이는 Final AAL을 2.53% → 2.01%로 낮춰 연간 약 520만원을 절감합니다.
투자 비용 약 3천만원 대비 6년 내 회수 가능합니다."
```

**우수한 이유**:
- ✅ 구체적 수치 제시 (4.3%, 25년, 3.5%)
- ✅ 취약성 요인별 정량적 기여도 (+20, +15, +10)
- ✅ 비교 기준 제시 (전국 평균 28%)
- ✅ 원인 분석 (도시열섬, 2.3°C)
- ✅ 실행 가능한 권고 (구체적 효과, ROI)

---

#### ❌ Bad Example
```
"이 건물은 극한 고온에 취약합니다. 여름철 기온이 높아지면
냉방 비용이 증가하고 직원들이 불편을 겪을 수 있습니다.
건물이 오래되어 에너지 효율이 낮으므로 개선이 필요합니다.
기후변화로 앞으로 더 더워질 것으로 예상되니 대비가 필요합니다."
```

**문제점**:
- ❌ 모호한 표현 ("취약합니다", "높아지면", "증가하고")
- ❌ 근거 없는 주장 (구체적 수치 없음)
- ❌ 실행 불가능한 권고 ("개선이 필요", "대비가 필요")
- ❌ 정량적 효과 제시 없음
- ❌ 입력 데이터 미활용 (bin 분포, 취약성 요인 등)

---

### 5.2 복합 리스크 분석 인사이트

```
"이 건물은 극한 고온(AAL 2.53%)과 가뭄(AAL 0.82%)이
동시에 발생할 복합 리스크가 존재합니다.

과거 데이터 분석 결과, WSDI 15일+ 폭염이 발생한 해(2018, 2022)에
SPEI-12 < -1.0 가뭄이 동반 발생했습니다. 이는 북태평양 고기압의
강화로 고온·건조 날씨가 지속되는 기후 패턴 때문입니다.

복합 리스크 시나리오:
1. 폭염으로 냉방 수요 급증 (+냉방 부하 30%)
2. 가뭄으로 냉각수 공급 부족 (냉각탑 효율 -20%)
3. 결과: 냉방 시스템 과부하 → 장비 고장 위험 2배 증가

단일 리스크 대응만으로는 불충분하며, 통합적 접근이 필요합니다:
- 물 저장 용량 확대 (1일 → 7일)
- 공냉식 냉각 시스템 추가 (수냉식 백업)
- 예상 투자: 5천만원
- 복합 리스크 AAL 절감: 3.35% → 2.1% (연간 1,250만원 절감)
```

---

### 5.3 시계열 추세 분석 인사이트

```
"극한 고온 리스크의 시계열 분석 결과, 다음 추세가 확인됩니다:

[2010-2020년] WSDI 평균: 8.2일
[2021-2024년] WSDI 평균: 13.7일 (+67% 증가)

bin4-5 (WSDI 15일+) 극심한 폭염의 발생 빈도:
- 2010-2015: 0회 (0%)
- 2016-2020: 1회 (20%)
- 2021-2024: 2회 (50%) → **가속화**

이 추세를 SSP 시나리오에 대입하면:
- SSP1-2.6 (저탄소): 2050년 WSDI 평균 16.5일 (+21%)
- SSP2-4.5 (중도): 2050년 WSDI 평균 19.8일 (+45%)
- SSP5-8.5 (최악): 2050년 WSDI 평균 24.3일 (+77%)

현재 AAL 2.53%는 SSP5-8.5 시나리오 하에서 2050년 4.48%까지
증가할 것으로 예상됩니다. 이는 연간 손실이 2,530만원 → 4,480만원으로
1.77배 증가하는 것을 의미합니다.

따라서 현재 시점의 리스크 관리 투자는 미래 손실을 고려할 때
더욱 높은 ROI를 제공합니다. 예를 들어, 현재 3천만원 투자로
30년간 총 13.5억원의 손실을 예방할 수 있습니다 (NPV 기준, 할인율 3%)."
```

---

## 6. 프롬프트 체크리스트

리포트 생성 전 다음 항목을 확인하세요:

### 데이터 완전성
- [ ] 9개 리스크 전부 H, V, AAL 데이터 있음
- [ ] bin별 확률 분포 데이터 있음
- [ ] 취약성 요인(factors) 상세 데이터 있음
- [ ] 건물 정보 완전함 (연식, 구조, 용도 등)
- [ ] 위치 정보 정확함 (위도, 경도)

### 계산 정확성
- [ ] AAL 공식 올바르게 적용: Σ(P[i] × DR[i])
- [ ] Vulnerability Scale 올바름: 0.9 + 0.2 × (V/100)
- [ ] Final AAL 올바름: base_AAL × F_vuln × (1 - IR)
- [ ] 모든 %는 소수점으로 표현 (2.53% = 0.0253)

### 인사이트 품질
- [ ] 모든 주장에 데이터 근거 있음
- [ ] 정량적 수치 포함 (%, 점수, 금액 등)
- [ ] 비교 기준 명시 (전국 평균, 과거 데이터 등)
- [ ] 원인 분석 포함 (왜 이런 결과가 나왔는가)
- [ ] 실행 가능한 권고사항 (구체적, 측정 가능)

### 권고사항 품질
- [ ] 우선순위 명확 (긴급/중기/장기)
- [ ] ROI 또는 비용 대비 효과 제시
- [ ] 실행 방법 구체적 (누가, 언제, 어떻게)
- [ ] 예상 AAL 절감 효과 정량화
- [ ] 투자 회수 기간 산정

### 가독성
- [ ] 비전문가도 이해 가능한 언어
- [ ] 전문 용어는 괄호로 설명 추가
- [ ] 문단 구조 명확 (헤더, 리스트, 표 활용)
- [ ] 핵심 인사이트 **굵게** 강조
- [ ] 긴 숫자는 쉼표 사용 (1,250만원)

---

## 7. 데이터 접근 코드 예시

### 7.1 Python으로 데이터 조회

```python
from modelops.database.connection import DatabaseConnection

def get_risk_report_data(latitude: float, longitude: float) -> dict:
    """리포트 작성에 필요한 모든 데이터 조회"""

    data = {
        'location': {'latitude': latitude, 'longitude': longitude},
        'risks': {}
    }

    # 9개 리스크
    risk_types = [
        'extreme_heat', 'extreme_cold', 'drought',
        'river_flood', 'urban_flood', 'wildfire',
        'water_stress', 'typhoon', 'sea_level_rise'
    ]

    with DatabaseConnection.get_connection() as conn:
        cursor = conn.cursor()

        for risk_type in risk_types:
            # Hazard
            cursor.execute("""
                SELECT hazard_score, hazard_score_100, hazard_level
                FROM hazard_results
                WHERE latitude = %s AND longitude = %s AND risk_type = %s
            """, (latitude, longitude, risk_type))
            hazard = cursor.fetchone()

            # Probability (AAL + bin data)
            cursor.execute("""
                SELECT probability, bin_data
                FROM probability_results
                WHERE latitude = %s AND longitude = %s AND risk_type = %s
            """, (latitude, longitude, risk_type))
            prob = cursor.fetchone()

            # Vulnerability
            cursor.execute("""
                SELECT vulnerability_score, vulnerability_level, factors
                FROM vulnerability_results
                WHERE latitude = %s AND longitude = %s AND risk_type = %s
            """, (latitude, longitude, risk_type))
            vuln = cursor.fetchone()

            # AAL Scaled
            cursor.execute("""
                SELECT base_aal, vulnerability_scale, final_aal, expected_loss
                FROM aal_scaled_results
                WHERE latitude = %s AND longitude = %s AND risk_type = %s
            """, (latitude, longitude, risk_type))
            aal = cursor.fetchone()

            # 데이터 통합
            data['risks'][risk_type] = {
                'hazard': dict(hazard) if hazard else None,
                'probability': dict(prob) if prob else None,
                'vulnerability': dict(vuln) if vuln else None,
                'aal': dict(aal) if aal else None
            }

    return data


def format_prompt_for_llm(data: dict) -> str:
    """데이터를 LLM 프롬프트 형식으로 변환"""

    prompt = f"""
# 위치 정보
- 위도: {data['location']['latitude']}
- 경도: {data['location']['longitude']}

# 리스크별 데이터
"""

    for risk_type, risk_data in data['risks'].items():
        if not risk_data['hazard']:
            continue

        prompt += f"\n## {risk_type.replace('_', ' ').title()}\n"
        prompt += f"- Hazard Score: {risk_data['hazard']['hazard_score_100']}/100 ({risk_data['hazard']['hazard_level']})\n"
        prompt += f"- Vulnerability Score: {risk_data['vulnerability']['vulnerability_score']}/100\n"
        prompt += f"- Base AAL: {risk_data['aal']['base_aal']:.4f} ({risk_data['aal']['base_aal']*100:.2f}%)\n"
        prompt += f"- Final AAL: {risk_data['aal']['final_aal']:.4f} ({risk_data['aal']['final_aal']*100:.2f}%)\n"

        # bin 분포
        if risk_data['probability'] and risk_data['probability']['bin_data']:
            bins = risk_data['probability']['bin_data'].get('bins', [])
            prompt += "- bin 분포:\n"
            for bin_info in bins:
                prompt += f"  * bin{bin_info['bin']} ({bin_info['range']}): "
                prompt += f"P={bin_info['probability']*100:.1f}%, DR={bin_info['base_damage_rate']*100:.2f}%\n"

    return prompt
```

---

## 8. 버전 관리

| 버전 | 날짜 | 변경 내용 |
|------|------|-----------|
| 1.0 | 2025-12-02 | 초안 작성 |

---

## 9. 참고 자료

- IPCC AR6 WG1 Chapter 12: https://www.ipcc.ch/report/ar6/wg1/chapter/chapter-12/
- [AAL_METHODOLOGY.md](AAL_METHODOLOGY.md): AAL 계산 상세 방법론
- [modelops_handover/02_CALCULATION_LOGIC.md](modelops_handover/02_CALCULATION_LOGIC.md): H, V, E 계산 로직
- [modelops_handover/03_DATA_SCHEMA.md](modelops_handover/03_DATA_SCHEMA.md): 데이터베이스 스키마

---

**문의**: AI Agent 개발팀
