# ModelOps 이관 문서 - 02. 계산 로직 명세

**문서 버전**: 1.0
**작성일**: 2025-12-01

---

## 1. Vulnerability (V) Score 계산

### 1.1 극한 고온 (Extreme Heat) 취약성

**입력 데이터**:
- `building_age`: 건물 연식 (년)
- `structure`: 구조 (철근콘크리트, 목조, 벽돌 등)
- `main_purpose`: 주용도 (업무시설, 상업시설, 주거시설 등)

**계산 공식**:
```python
score = 50  # 기본값

# 건물 연식 가점
if age > 30:
    score += 20
elif age > 20:
    score += 10

# 구조 가점/감점
if '목조' in structure or '벽돌' in structure:
    score += 15  # 단열 취약
elif '철근콘크리트' in structure:
    score -= 10  # 단열 양호

# 용도 가점
if main_purpose in ['업무시설', '상업시설']:
    score += 10  # 냉방 부하 높음

# 0-100 범위로 정규화
score = max(0, min(100, score))
```

**출력**: 0-100 점수 (높을수록 취약)

---

### 1.2 극한 한파 (Extreme Cold) 취약성

**계산 공식**:
```python
score = 50

if age > 30:
    score += 20  # 노후 건물 → 단열 취약
elif age > 20:
    score += 10

if '목조' in structure:
    score += 15  # 목조 → 한파 취약

score = max(0, min(100, score))
```

---

### 1.3 가뭄 (Drought) 취약성

**추가 입력**:
- `water_supply_available`: 비상 급수 가능 여부 (boolean)

**계산 공식**:
```python
score = 30  # 가뭄은 건물 직접 피해 적음

# 용수 의존도
if main_purpose in ['공장', '숙박시설']:
    score += 30

# 비상 급수
if not water_supply_available:
    score += 20

score = max(0, min(100, score))
```

---

### 1.4 하천 홍수 (River Flood) 취약성

**추가 입력**:
- `floors_below`: 지하층 수
- `has_piloti`: 필로티 구조 여부 (boolean)
- `in_flood_zone`: 홍수 위험 구역 여부 (boolean)

**계산 공식**:
```python
score = 40

# 지하층 (침수 시 큰 피해)
if floors_below > 0:
    score += 25

# 필로티 (침수 피해 감소)
if has_piloti:
    score -= 20

# 건물 연식 (방수 성능 저하)
if building_age > 30:
    score += 15

# 홍수 위험 구역
if in_flood_zone:
    score += 20

score = max(0, min(100, score))
```

---

### 1.5 도시 홍수 (Urban Flood) 취약성

**계산 공식**: 하천 홍수와 유사
```python
score = 40

if floors_below > 0:
    score += 20

if has_piloti:
    score -= 15

if building_age > 30:
    score += 10

score = max(0, min(100, score))
```

---

### 1.6 해수면 상승 (Sea Level Rise) 취약성

**추가 입력**:
- `elevation`: 해발 고도 (m)

**계산 공식**:
```python
score = 20  # 해안 지역 아니면 낮은 기본값

if elevation < 5:  # 5m 미만
    score += 40

if floors_below > 0:
    score += 30

if has_piloti:
    score -= 15

score = max(0, min(100, score))
```

---

### 1.7 태풍 (Typhoon) 취약성

**추가 입력**:
- `floors_above`: 지상층 수
- `has_seismic_design`: 내진 설계 여부 (boolean)

**계산 공식**:
```python
score = 50

if floors_above > 10:  # 고층 건물
    score += 20

if building_age > 30:
    score += 15

if not has_seismic_design:
    score += 20  # 내진 설계 없으면 태풍에도 취약

score = max(0, min(100, score))
```

---

### 1.8 산불 (Wildfire) 취약성

**추가 입력**:
- `fire_access`: 소방차 진입 가능성 (boolean)

**계산 공식**:
```python
score = 30  # 도심 지역은 낮은 기본값

if '목조' in structure:
    score += 30  # 목조 → 화재 취약

if building_age > 30:
    score += 15

if not fire_access:
    score += 20

score = max(0, min(100, score))
```

---

### 1.9 물부족 (Water Stress) 취약성

**계산 공식**: 가뭄과 유사
```python
score = 30

if main_purpose in ['공장', '숙박시설', '병원']:
    score += 30

if not water_supply_available:
    score += 25

score = max(0, min(100, score))
```

---

## 2. Exposure (E) Score 계산

**입력 데이터**:
- `total_asset_value`: 총 자산 가치 (원)
- `floor_area`: 연면적 (m²)
- `proximity_to_hazard`: 위험 근접도 (0-1)

**계산 공식**:
```python
# 자산 가치 정규화 (0-1)
normalized_value = min(total_asset_value / 100_000_000_000, 1.0)  # 1000억 기준

# 노출도 계산
exposure_score = normalized_value * proximity_to_hazard

# 0-1 범위로 정규화
exposure_score = max(0.0, min(1.0, exposure_score))
```

**출력**: 0-1 점수

---

## 3. Hazard (H) Score 계산

### 3.1 데이터 소스
- **기후 모델**: CMIP6 (Coupled Model Intercomparison Project Phase 6)
- **SSP 시나리오**: 4개 (SSP1-2.6, SSP2-4.5, SSP3-7.0, SSP5-8.5)
- **공간 해상도**: 0.25° × 0.25° 그리드

### 3.2 계산 방법

**입력**:
- `grid_id`: 그리드 ID
- `scenario_id`: SSP 시나리오 (1~4)
- `year_range`: 분석 연도 범위 (예: 2025-2050)
- `variable`: 기후 변수 (WSDI, CSDI, FWI 등)

**계산 공식** (백분위수 기반):
```python
# 1. 시계열 데이터 추출
time_series = get_climate_data(grid_id, scenario_id, variable, year_range)

# 2. 기준값 계산 (1985-2014 평균)
baseline = get_baseline_data(grid_id, variable)

# 3. 변화율 계산
anomaly = (time_series - baseline) / baseline

# 4. 백분위수 기반 정규화
percentile_value = np.percentile(anomaly, 95)  # 95th percentile

# 5. 0-1 범위로 스케일링
h_score = min(percentile_value / max_expected_change, 1.0)
h_score = max(0.0, h_score)
```

**출력**: 0-1 점수 (9개 리스크 × 4개 SSP)

---

## 4. AAL (Average Annual Loss) 계산

### 4.1 Base AAL 계산

**입력**:
- `climate_data`: 기후 시계열 데이터 (연단위)
- `risk_type`: 리스크 타입

**공식**:
```
base_aal = Σ_i [P_r[i] × DR_intensity_r[i]]
```

**단계별 계산**:

1. **Bin 분류**:
```python
# Extreme Heat 예시
bins = [0, 3, 8, 20, float('inf')]  # WSDI 기준
base_damage_rates = [0.001, 0.003, 0.010, 0.020]  # 0.1%, 0.3%, 1.0%, 2.0%
```

2. **확률 계산**:
```python
for i in range(len(bins) - 1):
    count = sum((data >= bins[i]) & (data < bins[i+1]))
    probability[i] = count / total_count
```

3. **Base AAL 계산**:
```python
base_aal = sum(probability[i] * base_damage_rates[i] for i in range(len(bins)-1))
```

---

### 4.2 리스크별 Bin 경계 및 손상률

| 리스크 | 변수 | Bin 1 | Bin 2 | Bin 3 | Bin 4 | 손상률 1 | 손상률 2 | 손상률 3 | 손상률 4 |
|--------|------|-------|-------|-------|-------|----------|----------|----------|----------|
| Extreme Heat | WSDI | 0-3 | 3-8 | 8-20 | 20+ | 0.1% | 0.3% | 1.0% | 2.0% |
| Extreme Cold | CSDI | 0-3 | 3-7 | 7-15 | 15+ | 0.05% | 0.20% | 0.60% | 1.50% |
| Wildfire | FWI | 11.2-21.3 | 21.3-38 | 38-50 | 50+ | 1% | 3% | 10% | 25% |
| Drought | SPEI12 | <-2.0 | -2.0~-1.5 | -1.5~-1.0 | >-1.0 | 20% | 7% | 2% | 0% |
| Water Stress | WSI | 0-0.2 | 0.2-0.4 | 0.4-0.8 | 0.8+ | 1% | 3% | 7% | 15% |
| Sea Level Rise | Depth (m) | 0-0.001 | 0.001-0.3 | 0.3-1.0 | 1.0+ | 0% | 2% | 15% | 35% |
| River Flood | RX1DAY | 0-80 | 80-95 | 95-99 | 99+ | 0% | 2% | 8% | 20% |
| Urban Flood | Depth (m) | 0-0.3 | 0.3-1.0 | 1.0+ | - | 0% | 5% | 25% | 50% |
| Typhoon | TC_EXP | 0-5 | 5-15 | 15+ | - | 0% | 2% | 10% | 30% |

---

### 4.3 취약성 스케일링

**공식**:
```
F_vuln = s_min + (s_max - s_min) × (V_score / 100)
```

**파라미터**:
- `s_min = 0.9` (최소 스케일 계수)
- `s_max = 1.1` (최대 스케일 계수)
- `V_score`: 취약성 점수 (0-100)

**예시**:
- V_score = 0 → F_vuln = 0.9 (10% 감소)
- V_score = 50 → F_vuln = 1.0 (변화 없음)
- V_score = 100 → F_vuln = 1.1 (10% 증가)

---

### 4.4 최종 AAL 계산

**공식**:
```
AAL_final = base_aal × F_vuln × (1 - insurance_rate)
```

**입력**:
- `base_aal`: 기본 연평균 손실률
- `F_vuln`: 취약성 스케일 계수
- `insurance_rate`: 보험 보전율 (0-1)

**출력**:
- `final_aal_percentage`: 최종 AAL (백분율)
- `expected_loss`: 예상 손실액 (원) = total_asset_value × final_aal_percentage / 100

---

## 5. Physical Risk Score 계산

**공식**:
```
Physical_Risk_Score = (H + E + V) / 3
```

**변환**:
- H: 0-1 → 0-100 (× 100)
- E: 0-1 → 0-100 (× 100)
- V: 이미 0-100

**최종 점수**: 0-100 스케일

**리스크 등급**:
- 0-20: Very Low
- 20-40: Low
- 40-60: Medium
- 60-80: High
- 80-100: Very High

---

## 다음 문서

👉 [03. 데이터 스키마](./03_DATA_SCHEMA.md)
