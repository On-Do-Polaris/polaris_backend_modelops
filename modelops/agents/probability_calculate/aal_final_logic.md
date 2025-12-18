# AAL (Annual Average Loss) 로직 정의서

**버전**: v2.0
**최종 수정일**: 2025-12-18
**작성자**: On-Do Team

---

## 목차

1. [개요](#1-개요)
2. [공통 프레임워크](#2-공통-프레임워크)
3. [9개 기후 리스크 상세 로직](#3-9개-기후-리스크-상세-로직)
   - [3.1 극심한 고온 (Extreme Heat)](#31-극심한-고온-extreme-heat)
   - [3.2 극심한 한파 (Extreme Cold)](#32-극심한-한파-extreme-cold)
   - [3.3 산불 (Wildfire)](#33-산불-wildfire)
   - [3.4 가뭄 (Drought)](#34-가뭄-drought)
   - [3.5 물부족 (Water Stress)](#35-물부족-water-stress)
   - [3.6 내륙 홍수 (River Flood)](#36-내륙-홍수-river-flood)
   - [3.7 도시 집중 홍수 (Pluvial Flooding)](#37-도시-집중-홍수-pluvial-flooding)
   - [3.8 해수면 상승 (Sea Level Rise)](#38-해수면-상승-sea-level-rise)
   - [3.9 열대성 태풍 (Tropical Cyclone)](#39-열대성-태풍-tropical-cyclone)
4. [학술적 근거 및 참고문헌](#4-학술적-근거-및-참고문헌)

---

## 1. 개요

본 문서는 기후변화 리스크에 따른 **연평균 자산 손실률(AAL, Annual Average Loss)**을 정량화하는 확률 기반 평가 로직을 정의한다.

### 1.1 목적

- 9개 주요 기후 리스크에 대한 자산 손실 확률 및 손상률 계산
- 취약성 점수를 반영한 사이트별 맞춤형 AAL 산출
- SSP 시나리오 기반 미래 기후 시뮬레이션 지원

### 1.2 계산 대상 리스크

| 번호 | 리스크 | 코드명 | 데이터 소스 |
|------|--------|--------|-------------|
| 1 | 극심한 고온 | `extreme_heat` | KMA WSDI |
| 2 | 극심한 한파 | `extreme_cold` | KMA CSDI |
| 3 | 산불 | `wildfire` | KMA 기상 데이터 (FWI 계산) |
| 4 | 가뭄 | `drought` | KMA SPEI12 |
| 5 | 물부족 | `water_stress` | WAMIS + Aqueduct 4.0 |
| 6 | 내륙 홍수 | `river_flood` | KMA RX1DAY |
| 7 | 도시 집중 홍수 | `urban_flood` | KMA RAIN80 + DEM |
| 8 | 해수면 상승 | `sea_level_rise` | CMIP6 zos |
| 9 | 열대성 태풍 | `typhoon` | KMA Best Track |

---

## 2. 공통 프레임워크

모든 리스크는 아래의 통일된 계산 프레임을 따른다.

### 2.1 핵심 파라미터

리스크 `r`, 사이트 `j`, 연도 `t`에 대해:

| 파라미터 | 설명 | 비고 |
|----------|------|------|
| **X_r(t)** | 강도지표 (Intensity Indicator) | 리스크별 물리량 |
| **bin_r[i]** | 강도 구간 (Bins) | 3~5단계 분류 |
| **P_r[i]** | bin별 발생확률 | KDE 또는 카운트 기반 |
| **DR_intensity_r[i]** | bin별 기본 손상률 | 취약성 미반영 |
| **V_score_r(j)** | 취약성 점수 | 0~1, Vulnerability Agent 출력 |
| **F_vuln_r(j)** | 취약성 스케일 계수 | 0.7 ~ 1.3 범위 |
| **DR_r[i, j]** | 최종 손상률 | 기본 손상률 × 취약성 계수 |
| **IR_r** | 보험 보전율 | 선택적 파라미터 (기본 0) |
| **AAL_r(j)** | 연평균 손실률 | 최종 출력 |

### 2.2 계산 단계

#### Step 1: 강도지표 계산

```
X_r(t) = f_r(climate_data, t)
```

- 각 리스크별 고유 물리량 산출
- 예: WSDI, FWI, SPEI12, WSI 등

#### Step 2: Bin 분류

```
X_r(t) ∈ bin_r[i]   →   bin_index = i
```

- 강도지표를 3~5단계 구간으로 분류

#### Step 3: 발생확률 계산

**방법 A: Kernel Density Estimation (KDE)** (샘플 ≥ 30개)

```
P_r[i] = ∫[bin_min, bin_max] KDE(x) dx
```

**방법 B: 이산적 카운트** (샘플 < 30개)

```
P_r[i] = (bin i에 속한 샘플 수) / (전체 샘플 수)
```

- 월별 데이터: 총 월 수로 나눔
- 연별 데이터: 총 연도 수로 나눔

#### Step 4: 취약성 반영

```
F_vuln_r(j) = s_min + (s_max - s_min) × V_score_r(j)
             = 0.7 + 0.6 × V_score_r(j)
```

- `V_score_r(j) = 0` → 취약성 낮음 → `F_vuln = 0.7` (손상률 30% 감소)
- `V_score_r(j) = 0.5` → 취약성 중간 → `F_vuln = 1.0` (손상률 유지)
- `V_score_r(j) = 1` → 취약성 높음 → `F_vuln = 1.3` (손상률 30% 증가)

#### Step 5: 최종 손상률 계산

```
DR_r[i, j] = DR_intensity_r[i] × F_vuln_r(j)
```

#### Step 6: AAL 계산

```
AAL_r(j) = Σ[i=1 to n] P_r[i] × DR_r[i, j] × (1 - IR_r)
```

- `IR_r`: 보험 보전율 (Insurance Recovery Rate)
- 보험이 없으면 `IR_r = 0` → 전체 손실 반영

---

## 3. 9개 기후 리스크 상세 로직

### 3.1 극심한 고온 (Extreme Heat)

#### 3.1.1 개요

- **코드명**: `extreme_heat`
- **사용 데이터**: KMA 연간 극값 지수 WSDI (Warm Spell Duration Index)
- **강도지표**: `X_heat(t) = WSDI(t)`

#### 3.1.2 강도지표 정의

**WSDI (Warm Spell Duration Index)**
- 평년 기준 상위 90분위수 이상 고온이 **연속 6일 이상** 지속된 날의 연간 합계
- KMA 표준 극값 지수 (ETCCDI)

```
X_heat(t) = WSDI(t)  [단위: 일]
```

#### 3.1.3 Bin 정의 (분위수 기반)

| Bin | 구간 | 설명 |
|-----|------|------|
| 1 | WSDI < Q80 | 일반적 수준 |
| 2 | Q80 ≤ WSDI < Q90 | 상위 20% 더위 |
| 3 | Q90 ≤ WSDI < Q95 | 상위 10% 더위 |
| 4 | Q95 ≤ WSDI < Q99 | 상위 5% 더위 |
| 5 | WSDI ≥ Q99 | 상위 1% 극한 |

- 기준기간(1991-2020) 데이터로 분위수 임계값 산출

#### 3.1.4 기본 손상률 (DR_intensity)

| Bin | DR_intensity | 근거 |
|-----|--------------|------|
| 1 | 0.1% | 일상적 수준, 미미한 영향 |
| 2 | 0.3% | 냉방비 증가, 경미한 생산성 저하 |
| 3 | 1.0% | 설비 과부하, 야외작업 중단 |
| 4 | 2.0% | 전력망 부담, 농작물 피해 |
| 5 | 3.5% | 대규모 정전, 인명 피해 위험 |

#### 3.1.5 학술적 근거

- **IPCC AR6 WG2** (2022): 극한 고온 사건 빈도 증가
- **Klein Tank et al. (2009)**: ETCCDI 극값 지수 방법론
- **Perkins-Kirkpatrick & Lewis (2020)**: 폭염 강도-빈도 관계

---

### 3.2 극심한 한파 (Extreme Cold)

#### 3.2.1 개요

- **코드명**: `extreme_cold`
- **사용 데이터**: KMA 연간 극값 지수 CSDI (Cold Spell Duration Index)
- **강도지표**: `X_cold(t) = CSDI(t)`

#### 3.2.2 강도지표 정의

**CSDI (Cold Spell Duration Index)**
- 평년 기준 하위 10분위수 이하 저온이 **연속 6일 이상** 지속된 날의 연간 합계

```
X_cold(t) = CSDI(t)  [단위: 일]
```

#### 3.2.3 Bin 정의

| Bin | 구간 | DR_intensity |
|-----|------|--------------|
| 1 | CSDI < 3 | 0.05% |
| 2 | 3 ≤ CSDI < 7 | 0.20% |
| 3 | 7 ≤ CSDI < 15 | 0.60% |
| 4 | CSDI ≥ 15 | 1.50% |

#### 3.2.4 손상 메커니즘

- **난방 수요 급증**: 전력/가스 소비 증가 → 운영비 상승
- **배관 동파**: 수도관, 소방설비 손상
- **교통 마비**: 도로 결빙, 물류 중단
- **노동생산성 저하**: 야외작업 불가, 건설 지연

---

### 3.3 산불 (Wildfire)

#### 3.3.1 개요

- **코드명**: `wildfire`
- **강도지표**: `X_fire(t) = max[FWI(t,m)]` (연도별 최대 FWI)
- **계산 방식**: 캐나다 ISI 방식 근사

#### 3.3.2 FWI 계산식

**Fire Weather Index (FWI)** - v2.0 개선 버전

```
FWI(t,m) = (1 - RHM/100)^0.5
           × exp(0.05039 × WS_kmh)
           × exp(0.08 × (TA - 5))
           × exp(-0.0005 × RN)
           × 5
```

**입력 변수**:
- `TA`: 월평균 기온 (°C)
- `RHM`: 월평균 상대습도 (%)
- `WS`: 월평균 풍속 (m/s) → km/h 변환
- `RN`: 월 강수량 (mm)

**개선 사항**:
- 습도 영향: 제곱근으로 완화 (`(1 - RHM/100)^0.5`)
- 풍속 영향: 캐나다 ISI 방식 계수 적용 (`0.05039`)
- 온도 계수 강화: 0.05 → 0.08
- 스케일링: ×5 (EFFIS bin 호환)

#### 3.3.3 Bin 정의 (EFFIS 기준)

| Bin | FWI 구간 | EFFIS 분류 | DR_intensity |
|-----|----------|------------|--------------|
| 1 | 0 - 11.2 | Low | 0% |
| 2 | 11.2 - 21.3 | Moderate | 1% |
| 3 | 21.3 - 38 | High | 3% |
| 4 | 38 - 50 | Very High | 10% |
| 5 | ≥ 50 | Extreme | 25% |

#### 3.3.4 학술적 근거

- **Van Wagner (1987)**: 캐나다 FWI 시스템 원본
- **EFFIS (2020)**: 유럽 산불 정보 시스템 분류 기준
- **Abatzoglou et al. (2019)**: 기후변화와 산불 위험도

---

### 3.4 가뭄 (Drought)

#### 3.4.1 개요

- **코드명**: `drought`
- **사용 데이터**: KMA SPEI12 (월별)
- **강도지표**: `X_drought(t) = min[SPEI12(t,m)]` (연도별 최솟값)

#### 3.4.2 강도지표 정의

**SPEI12 (Standardized Precipitation-Evapotranspiration Index, 12개월)**
- 강수량과 증발산량을 동시 고려
- 12개월 누적 기준으로 장기 가뭄 포착

```
X_drought(t) = min[SPEI12(t,m)]  for m=1 to 12
```

- 연도 내 가장 심한 가뭄 상태를 대표값으로 사용

#### 3.4.3 Bin 정의

| Bin | SPEI12 구간 | 가뭄 강도 | DR_intensity |
|-----|-------------|-----------|--------------|
| 1 | > -1 | 정상~약한 가뭄 | 0% |
| 2 | -1.5 < SPEI ≤ -1 | 중간 가뭄 | 2% |
| 3 | -2.0 < SPEI ≤ -1.5 | 심각 가뭄 | 7% |
| 4 | ≤ -2.0 | 극심 가뭄 | 20% |

#### 3.4.4 학술적 근거

- **Vicente-Serrano et al. (2010)**: SPEI 방법론 및 글로벌 검증
- **WMO (2012)**: SPEI를 표준 가뭄 지수로 권장
- **Cook et al. (2018)**: 기후변화와 가뭄 빈도 증가

---

### 3.5 물부족 (Water Stress)

#### 3.5.1 개요

- **코드명**: `water_stress`
- **강도지표**: `WSI(t) = Withdrawal(t) / ARWR(t)`
- **데이터 소스**: WAMIS + Aqueduct 4.0

#### 3.5.2 핵심 개념

**TRWR (Total Renewable Water Resources)**
- 재생 가능 수자원 총량
- 한국: IRWR 기반 (내부 재생 수자원)
- 유역 하류 유량 관측소 연간 총유량으로 계측

**ARWR (Available Renewable Water Resources)**
```
ARWR = TRWR × (1 - α_EFR)
     = TRWR × 0.63
```
- `α_EFR = 0.37`: 환경유지유량 비율 (Ecological Flow Requirement)

**WSI (Water Stress Index)**
```
WSI(t) = Withdrawal(t) / ARWR(t)
```

#### 3.5.3 미래 TRWR 스케일링

**ET0 (Penman-Monteith 기준증발산량) 계산**

```
ET0 = [0.408 × Δ × (Rn - G) + γ × (900/(T+273)) × u2 × (es - ea)]
      / [Δ + γ × (1 + 0.34 × u2)]
```

**필요 변수 (KMA 매핑)**:
- `T`: TA (월평균 기온, °C)
- `u2`: WS (풍속, 10m → 2m 환산)
- `RH`: RHM (상대습도, %)
- `Rs`: SI (일사량, MJ/m²/day)

**보조식**:
1. 포화수증기압: `es = 0.6108 × exp(17.27×T / (T+237.3))`
2. 실제수증기압: `ea = es × RH / 100`
3. 기울기: `Δ = 4098 × es / (T+237.3)²`

**유효강수량 및 스케일링**:
```
P_eff(t) = Σ[P(t,m) - ET0(t,m)]

scale_TRWR(t) = P_eff(t) / P_eff_baseline_mean

TRWR_future(t) = TRWR_baseline × scale_TRWR(t)
```

#### 3.5.4 미래 용수이용량 추정

**Aqueduct 4.0 BWS (Blue Water Stress) 기반 선형 보간**

앵커 연도: 2019, 2030, 2050, 2080

**시나리오 매핑**:
- SSP1-2.6 → `opt` (낙관적)
- SSP2-4.5 → `(opt + bau) / 2` (보간)
- SSP3-7.0 → `bau` (현상유지)
- SSP5-8.5 → `pes` (비관적)

```
Withdrawal_future(t) = Withdrawal_baseline × BWS_ratio(t)
```

#### 3.5.5 Bin 정의 (WRI 기준)

| Bin | WSI 구간 | 물 스트레스 수준 | DR_intensity |
|-----|----------|------------------|--------------|
| 1 | < 0.2 | 낮음 | 1% |
| 2 | 0.2 - 0.4 | 중간 | 3% |
| 3 | 0.4 - 0.8 | 높음 | 7% |
| 4 | ≥ 0.8 | 극심 | 15% |

#### 3.5.6 학술적 근거

- **Hofste et al. (2019)**: Aqueduct 3.0/4.0 방법론
- **Smakhtin et al. (2004)**: 환경유지유량 산정 기준
- **Mekonnen & Hoekstra (2016)**: 글로벌 물 부족 평가

---

### 3.6 내륙 홍수 (River Flood)

#### 3.6.1 개요

- **코드명**: `river_flood`
- **사용 데이터**: KMA RX1DAY (연 최대 일강수량)
- **강도지표**: `X_rflood(t) = RX1DAY(t)`

#### 3.6.2 Bin 정의 (분위수 기반)

기준기간(1991-2020) RX1DAY 분포에서 분위수 계산:

| Bin | 구간 | 설명 | DR_intensity |
|-----|------|------|--------------|
| 1 | < Q80 | 평범~약한 강우 | 0% |
| 2 | Q80 - Q95 | 상위 20% 강우 | 2% |
| 3 | Q95 - Q99 | 상위 5% 강우 | 8% |
| 4 | ≥ Q99 | 상위 1% 극한 강우 | 20% |

#### 3.6.3 학술적 근거

- **IPCC AR6 (2021)**: 극한 강수 빈도 증가
- **Kundzewicz et al. (2014)**: 홍수 리스크 평가 방법론

---

### 3.7 도시 집중 홍수 (Pluvial Flooding)

#### 3.7.1 개요

- **코드명**: `urban_flood`
- **사용 데이터**: KMA RAIN80 (연 최대 시간당 80mm 이상 강우)
- **강도지표**: 침수심 기반

#### 3.7.2 계산 로직

**Step 1: 배수능력 추정** (DEM + 토지피복도 기반)

```
if urban_ratio ≥ 0.7:
    base_capacity = 60 mm/h
elif 0.3 ≤ urban_ratio < 0.7:
    base_capacity = 40 mm/h
else:
    base_capacity = 25 mm/h

if slope < 0.01:
    slope_factor = 0.8
elif 0.01 ≤ slope ≤ 0.03:
    slope_factor = 1.0
else:
    slope_factor = 1.2

drain_capacity = base_capacity × slope_factor
```

**Step 2: 등가 강우강도 및 초과분**

```
R_peak_mmph(t) = c_rain × RAIN80(t)

E_pflood(t,j) = max(0, R_peak_mmph(t) - drain_capacity(j))
```

**Step 3: 침수심 변환**

```
X_pflood(t,j) = k_depth × E_pflood(t,j)
```
- `k_depth`: 보정계수 (튜닝 필요)

#### 3.7.3 Bin 정의

| Bin | 침수심 | DR_intensity | 손상 내역 |
|-----|--------|--------------|-----------|
| 1 | 0 m | 0% | 침수 없음 |
| 2 | 0 - 0.3 m | 5% | 경미 피해 (마감재, 지상층 물품) |
| 3 | 0.3 - 1.0 m | 25% | 건물·설비 피해 |
| 4 | ≥ 1.0 m | 50% | 광범위·중대 피해 |

---

### 3.8 해수면 상승 (Sea Level Rise)

#### 3.8.1 개요

- **코드명**: `sea_level_rise`
- **사용 데이터**: CMIP6 `zos` (해수면 높이, cm)
- **강도지표**: 침수심 기반

#### 3.8.2 계산 로직

**Step 1: 시점별 침수심**

```
inundation_depth(t,τ,j) = max(zos(t,τ)/100 - ground_level(j), 0)
```
- `zos(t,τ)`: 시점 τ의 해수면 높이 (cm → m 변환)
- `ground_level(j)`: 사이트 j의 지반고도 (m, DEM 기반)

**Step 2: 연도별 최대 침수심**

```
X_slr(t,j) = max[inundation_depth(t,τ,j)]  for all τ in year t
```

#### 3.8.3 Bin 정의 (국제 Damage Curve 기반)

| Bin | 침수심 | DR_intensity | 국제 범위 |
|-----|--------|--------------|-----------|
| 1 | 0 m | 0% | 0% |
| 2 | 0 - 0.3 m | 2% | 1-5% |
| 3 | 0.3 - 1.0 m | 15% | 10-30% |
| 4 | ≥ 1.0 m | 35% | 30-55% |

#### 3.8.4 학술적 근거

- **IPCC AR6 WG1 (2021)**: SSP 시나리오별 해수면 상승 전망
- **Oppenheimer et al. (2019)**: 해수면 상승 리스크 평가
- **Huizinga et al. (2017)**: 글로벌 홍수 Depth-Damage 곡선

---

### 3.9 열대성 태풍 (Tropical Cyclone)

#### 3.9.1 개요

- **코드명**: `typhoon`
- **사용 데이터**: KMA 태풍 Best Track API (과거) + SSP 기온 (미래)
- **강도지표**: 누적 노출 지수 `S_tc(t,j)`

#### 3.9.2 계산 로직

**Step 1: 시점별 bin_inst 판정**

각 Best Track 시점 τ에서:

1. 태풍 중심 - 사이트 간 거리 계산 (위경도 → km 변환)
   - 위도 1도 ≈ 111 km
   - 경도 1도 ≈ 111 km × cos(위도)

2. STORM 타원 (폭풍반경, 25 m/s 이상) 내부 여부
   ```
   inside_storm = (x_rot / storm_long)² + (y_rot / storm_short)² ≤ 1
   ```

3. GALE 타원 (강풍반경, 15 m/s 이상) 내부 여부

4. bin_inst 결정:
   ```
   if inside_storm and GRADE == 'TY':
       bin_inst = 3  (TY급)
   elif inside_storm:
       bin_inst = 2  (STS급)
   elif inside_gale and GRADE in ['TS', 'STS', 'TY']:
       bin_inst = 1  (TS급)
   else:
       bin_inst = 0  (영향 없음)
   ```

**Step 2: 연도별 누적 노출 지수**

```
w_tc = [0, 1, 3, 7]  # bin별 가중치

S_tc(t,j) = Σ[w_tc[bin_inst(storm,τ,j)]]  for all (storm,τ) in year t
```

**Step 3: 연도 bin 분류**

```
if S_tc = 0:
    bin_year = 1  (영향 없음)
elif 0 < S_tc ≤ 5:
    bin_year = 2  (약한 노출)
elif 5 < S_tc ≤ 15:
    bin_year = 3  (중간~강한 노출)
else:
    bin_year = 4  (매우 강한 노출)
```

#### 3.9.3 미래 시나리오 추정

**Hybrid Approach: 과거 통계 + 기온 스케일링 + 확률적 시뮬레이션**

**Step 1: Baseline 통계 추출** (2015-2024)
- 과거 S_tc 분포에서 Gamma 분포 피팅
- 파라미터: `shape`, `scale`

**Step 2: 기온 기반 강도 스케일링**
```
intensity_scale(t) = 1.0 + 0.04 × (T_year - T_baseline)
```
- IPCC AR6 근거: 1°C 온난화 시 태풍 강도 4% 증가

**Step 3: Gamma 분포 샘플링**
```
S_tc_future(t) ~ Gamma(shape, scale × intensity_scale(t))
```

#### 3.9.4 Bin 정의

| Bin | S_tc 구간 | DR_intensity |
|-----|-----------|--------------|
| 1 | 0 | 0% |
| 2 | 0 - 5 | 2% |
| 3 | 5 - 15 | 10% |
| 4 | > 15 | 30% |

#### 3.9.5 학술적 근거

- **IPCC AR6 WG1 (2021)**: 온난화와 태풍 강도 증가
- **Knutson et al. (2020)**: 기후변화와 열대저기압 전망
- **KMA (2024)**: 태풍 Best Track 데이터베이스

---

## 4. 학술적 근거 및 참고문헌

### 4.1 국제 기후변화 평가 보고서

1. **IPCC AR6 Working Group I** (2021)
   Climate Change 2021: The Physical Science Basis. Chapter 11: Weather and Climate Extreme Events in a Changing Climate.
   *Cambridge University Press.*
   - 극한 기상 현상 빈도·강도 증가 전망
   - SSP 시나리오별 기온·강수 변화

2. **IPCC AR6 Working Group II** (2022)
   Climate Change 2022: Impacts, Adaptation and Vulnerability.
   *Cambridge University Press.*
   - 기후 리스크 평가 프레임워크
   - 부문별 취약성 평가 방법론

3. **IPCC SREX** (2012)
   Managing the Risks of Extreme Events and Disasters to Advance Climate Change Adaptation.
   - 극한 현상 리스크 관리 지침

4. **IPCC SROCC** (2019)
   Special Report on the Ocean and Cryosphere in a Changing Climate. Chapter 4: Sea Level Rise and Implications.
   - 해수면 상승 전망 및 영향 평가

### 4.2 극값 지수 및 기후 분석 방법론

5. **WMO ETCCDI** (2009)
   Guidelines on Analysis of Extremes in a Changing Climate in Support of Adaptation.
   *WMO-TD No. 1500, WCDMP-72.*
   - ETCCDI 극값 지수 (WSDI, CSDI, RX1DAY 등) 정의
   - 분위수 기반 임계값 산정 방법

6. **Klein Tank, A. M. G. et al.** (2009)
   Guidelines on analysis of extremes in a changing climate in support of informed decisions for adaptation.
   *WMO Technical Document.*

7. **Zhang, X. et al.** (2011)
   Indices for monitoring changes in extremes based on daily temperature and precipitation data.
   *Wiley Interdisciplinary Reviews: Climate Change, 2(6), 851-870.*

### 4.3 극심한 고온 (Extreme Heat)

8. **Met Éireann** (2022)
   Warm Spell Duration Index (WSDI) Key Message.
   - WSDI 지수 해석 및 활용 지침

9. **Burke, M., Hsiang, S. M., & Miguel, E.** (2015)
   Global non-linear effect of temperature on economic production.
   *Nature, 527, 235-239.*
   - 고온이 경제 생산성에 미치는 비선형 영향

10. **Gasparrini, A. et al.** (2015)
    Mortality risk attributable to high and low ambient temperature: a multicountry observational study.
    *The Lancet, 386(9991), 369-375.*
    - 극한 기온과 사망률 관계 분석

### 4.4 극심한 한파 (Extreme Cold)

11. **Sailor, D. J., & Muñoz, J. R.** (1997)
    Sensitivity of electricity and natural gas consumption to climate: U.S. methodology and results.
    *Energy and Buildings, 26(2), 161-174.*
    - 한파가 에너지 소비에 미치는 영향

12. **Makkonen, L., & Tikanmäki, M.** (2019)
    Modeling the friction of ice.
    *Cold Regions Science and Technology, 102, 84-93.*
    - 결빙 및 한파 영향 모델링

13. **IEA** (2021)
    Cold Weather Report: Impact on Energy Systems.
    *International Energy Agency.*
    - 한파의 에너지 시스템 영향 분석

### 4.5 산불 (Wildfire)

14. **Van Wagner, C. E.** (1987)
    Development and structure of the Canadian Forest Fire Weather Index System.
    *Canadian Forestry Service, Forestry Technical Report 35.*
    - 캐나다 FWI 시스템 원본

15. **San-Miguel-Ayanz, J. et al.** (2013)
    European Forest Fire Information System (EFFIS).
    *In: Wildfire Hazards, Risks, and Disasters, Elsevier.*
    - EFFIS FWI 분류 기준

16. **Copernicus EFFIS** (2007)
    Fire Danger Forecast Technical Background.
    *European Forest Fire Information System.*

17. **Natural Resources Canada** (2025)
    Canada's Fire Weather Index System.
    *Canadian Forest Service.*

18. **Kwon, C. et al.** (2019)
    Spatiotemporal Analysis of Forest Fire Danger in South Korea Using the Canadian Fire Weather Index.
    *Forests, 10(5), 389.*
    - 한국 산불 위험도 FWI 적용 연구

19. **Abatzoglou, J. T. et al.** (2019)
    Global emergence of anthropogenic climate change in fire weather indices.
    *Geophysical Research Letters, 46(1), 326-336.*
    - 기후변화와 산불 위험도 증가

### 4.6 가뭄 (Drought)

20. **WMO** (2016)
    Handbook of Drought Indicators and Indices.
    *Integrated Drought Management Programme (IDMP).*

21. **Vicente-Serrano, S. M. et al.** (2010)
    A multiscalar drought index sensitive to global warming: the standardized precipitation evapotranspiration index.
    *Journal of Climate, 23(7), 1696-1718.*
    - SPEI 방법론 및 글로벌 검증

22. **McKee, T. B., Doesken, N. J., & Kleist, J.** (1993)
    The relationship of drought frequency and duration to time scales.
    *Proceedings of the 8th Conference on Applied Climatology, 179-184.*
    - SPI/SPEI 시간 척도 개념

23. **Stagge, J. H. et al.** (2015)
    Candidate distributions for climatological drought indices (SPI and SPEI).
    *International Journal of Climatology, 35(13), 4027-4040.*

24. **Lobell, D. B., Schlenker, W., & Costa-Roberts, J.** (2011)
    Climate trends and global crop production since 1980.
    *Science, 333(6042), 616-620.*
    - 가뭄이 농업 생산에 미치는 영향

25. **Naumann, G. et al.** (2021)
    Global drought trends and future projections.
    *Philosophical Transactions of the Royal Society A, 379(2195).*

26. **Sheffield, J., Wood, E. F., & Roderick, M. L.** (2012)
    Little change in global drought over the past 60 years.
    *Nature, 491, 435-438.*

### 4.7 물부족 (Water Stress)

27. **WRI** (2023)
    Aqueduct 4.0: Updated Decision-Relevant Global Water Risk Indicators.
    *World Resources Institute.*
    - Aqueduct 방법론, BWS 지표

28. **Hofste, R. W. et al.** (2019)
    Aqueduct 3.0: Updated decision-relevant global water risk indicators.
    *World Resources Institute Technical Note.*

29. **Schewe, J. et al.** (2014)
    Multimodel assessment of water scarcity under climate change.
    *PNAS, 111(9), 3245-3250.*

30. **Kummu, M. et al.** (2016)
    The world's road to water scarcity: shortage and stress in the 20th century and pathways towards the 21st.
    *Scientific Reports, 6, 38495.*

31. **Wada, Y. et al.** (2011)
    Global monthly water stress: 1. Water balance and water availability.
    *Water Resources Research, 47(7), W07517.*

32. **Pastor, A. V. et al.** (2014)
    Accounting for environmental flow requirements in global water assessments.
    *Hydrology and Earth System Sciences, 18(12), 5041-5059.*
    - 환경유지유량 산정 방법론

33. **Smakhtin, V. et al.** (2004)
    A pilot global assessment of environmental water requirements and scarcity.
    *Water International, 29(3), 307-317.*

34. **FAO** (1998)
    Crop evapotranspiration - Guidelines for computing crop water requirements.
    *FAO Irrigation and drainage paper 56.*
    - Penman-Monteith ET0 계산 표준

35. **Allen, R. G. et al.** (1998)
    Crop evapotranspiration - Guidelines for computing crop water requirements.
    *FAO Irrigation and drainage paper 56.*

36. **Nature** (2010)
    Minimum service cost impact.
    - 서비스 중단에 따른 최소 비용 영향 분석

### 4.8 내륙 홍수 (River Flood)

37. **Westra, S. et al.** (2013)
    Global increasing trends in annual maximum daily precipitation.
    *Journal of Climate, 26(11), 3904-3918.*
    - 극한 강수 증가 트렌드 분석

38. **Winsemius, H. C. et al.** (2016)
    Global drivers of future river flood risk.
    *Nature Climate Change, 6(4), 381-385.*

39. **Ward, P. J. et al.** (2013)
    Seasonal flood risk monitoring and forecasting.
    *Climatic Change, 116(3-4), 769-786.*

40. **Dottori, F. et al.** (2018)
    Increased human and economic losses from river flooding with anthropogenic warming.
    *Nature Climate Change, 8(9), 781-786.*

41. **Kundzewicz, Z. W. et al.** (2014)
    Flood risk and climate change: global and regional perspectives.
    *Hydrological Sciences Journal, 59(1), 1-28.*

### 4.9 도시 집중 홍수 (Pluvial Flooding)

42. **Huizinga, J. et al.** (2017)
    Global flood depth-damage functions: Methodology and the database with guidelines.
    *EUR 28552 EN, Publications Office of the European Union.*
    - Depth-Damage 곡선

43. **Yin, J. et al.** (2016)
    Assessment of flood hazard and risk in the rapidly urbanizing Yangtze River Delta.
    *Natural Hazards, 79(3), 1915-1931.*

44. **Kellens, W. et al.** (2013)
    Coastal flood risk management: a review of methods.
    *Journal of Flood Risk Management, 6(2), 106-118.*

45. **Hammond, M. J. et al.** (2015)
    Urban flood impact assessment: A state-of-the-art review.
    *Urban Water Journal, 12(1), 14-29.*

46. **MLIT** (2012)
    도시 침수 피해율 실측.
    *일본 국토교통성 (Ministry of Land, Infrastructure, Transport and Tourism).*
    - 일본 도시홍수 피해 실측 데이터

### 4.10 해수면 상승 (Sea Level Rise)

47. **Oppenheimer, M. et al.** (2019)
    Sea Level Rise and Implications for Low-Lying Islands, Coasts and Communities.
    *In IPCC Special Report on the Ocean and Cryosphere in a Changing Climate.*

48. **Fox-Kemper, B. et al.** (2021)
    Ocean, Cryosphere and Sea Level Change.
    *In Climate Change 2021: The Physical Science Basis (IPCC AR6 WG1), Chapter 9.*

49. **Hinkel, J. et al.** (2014)
    Coastal flood damage and adaptation costs under 21st century sea-level rise.
    *PNAS, 111(9), 3292-3297.*

50. **Vousdoukas, M. I. et al.** (2018)
    Global probabilistic projections of extreme sea levels.
    *Nature Communications, 9, 2360.*

51. **Tiggeloven, T. et al.** (2020)
    Global-scale benefit-cost analysis of coastal flood adaptation to different flood risk drivers using structural measures.
    *Nature Communications, 11, 2127.*

### 4.11 열대성 태풍 (Tropical Cyclone)

52. **Knutson, T. et al.** (2020)
    Tropical Cyclones and Climate Change Assessment: Part II. Projected response to anthropogenic warming.
    *Bulletin of the American Meteorological Society, 101(3), E303-E322.*
    - 온난화와 태풍 강도 증가 관계

53. **Emanuel, K.** (2011)
    Global warming effects on U.S. hurricane damage.
    *Weather, Climate, and Society, 3(4), 261-268.*

54. **Klotzbach, P. J. et al.** (2020)
    Surface Pressure a More Skillful Predictor of Normalized Hurricane Damage.
    *Bulletin of the American Meteorological Society, 101(6), E830-E846.*

55. **Mendelsohn, R. et al.** (2012)
    The impact of climate change on global tropical cyclone damage.
    *Nature Climate Change, 2(3), 205-209.*

56. **Lee, C. Y. et al.** (2020)
    Rapid intensification and the bimodal distribution of tropical cyclone intensity.
    *Nature Communications, 11, 1876.*

### 4.12 한국 기후변화 시나리오 및 리스크 평가

57. **KMA** (2020)
    Korean Climate Change Scenario 2020.
    *Korea Meteorological Administration.*
    - SSP 시나리오 기반 한반도 상세 전망

58. **NIE** (2021)
    Korean Climate Change Assessment Report 2020.
    *National Institute of Environmental Research.*

### 4.13 물리적 리스크 평가 방법론

59. **S&P Global** (2023)
    Physical Risk Methodology.
    *S&P Global Sustainable1.*
    - 통합 물리적 기후 리스크 평가 프레임워크

---

## 부록 A: 수식 요약

### A.1 공통 AAL 계산식

```
AAL_r(j) = Σ[i=1 to n] P_r[i] × DR_r[i, j] × (1 - IR_r)

where:
  P_r[i]       = bin i 발생확률
  DR_r[i, j]   = DR_intensity_r[i] × F_vuln_r(j)
  F_vuln_r(j)  = 0.7 + 0.6 × V_score_r(j)
  IR_r         = 보험 보전율
```

### A.2 리스크별 강도지표

| 리스크 | 강도지표 X_r(t) | 시간 단위 |
|--------|-----------------|-----------|
| Extreme Heat | WSDI(t) | 연별 |
| Extreme Cold | CSDI(t) | 연별 |
| Wildfire | max[FWI(t,m)] | 연별 최댓값 |
| Drought | min[SPEI12(t,m)] | 연별 최솟값 |
| Water Stress | WSI(t) = Withdrawal(t) / ARWR(t) | 연별 |
| River Flood | RX1DAY(t) | 연별 |
| Urban Flood | X_pflood(t,j) = k × max(0, R_peak - drain) | 연별 |
| Sea Level Rise | max[inundation_depth(t,τ,j)] | 연별 최댓값 |
| Typhoon | S_tc(t,j) = Σ w_tc[bin_inst] | 연별 누적 |

---

## 부록 B: 데이터 소스

### B.1 KMA (기상청) 기후 데이터

- **WSDI, CSDI**: 극값 지수 (ETCCDI)
- **SPEI12**: 가뭄 지수
- **RX1DAY, RAIN80**: 강수 극값
- **TA, RHM, WS, SI, RN**: 기본 기상 요소
- **SSP 시나리오**: SSP126, SSP245, SSP370, SSP585

### B.2 WAMIS (국가수자원관리종합정보시스템)

- **유량 데이터**: 일유량 관측소 (TRWR 계산)
- **용수이용량**: 생활·공업·농업용수

### B.3 Aqueduct 4.0 (WRI)

- **BWS (Blue Water Stress)**: 미래 물 스트레스 시나리오
- **Baseline**: 2019
- **Projection**: 2030, 2050, 2080

### B.4 CMIP6

- **zos**: 해수면 높이 (SSP 시나리오별)

### B.5 기타

- **DEM**: 지형고도, 경사도
- **토지피복도**: 도시화율 산정
- **KMA Best Track**: 태풍 경로·강도

---

## 부록 C: 변경 이력

| 버전 | 날짜 | 변경 내역 |
|------|------|-----------|
| v1.0 | 2024-11-21 | 초안 작성, 9개 리스크 로직 정의 |
| v1.1 | 2024-11-24 | 분위수 기반 bin 도입 (Heat, Cold, Flood) |
| v1.2 | 2024-12-11 | KDE 방식 확률 계산 추가 |
| v1.3 | 2024-12-14 | Hazard/Exposure 패턴 적용 |
| **v2.0** | **2025-12-18** | **문서 전면 개편: 중복 제거, 학술 근거 정리, 통합 프레임워크 명확화** |

---

**문서 끝**

---

## 라이선스

본 문서는 On-Do Team의 내부 기술 문서로, 무단 배포를 금지합니다.
학술적 인용 시 반드시 출처를 명시하시기 바랍니다.

**연락처**: on-do-team@example.com
**최종 검토자**: [이름], [직책]
**승인일**: 2025-12-18
