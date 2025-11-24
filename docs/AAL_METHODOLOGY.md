# 9대 기후 리스크 연평균손실(AAL) 산출 방법론

## 목차
1. [개요](#1-개요)
2. [AAL 산출 프레임워크](#2-aal-산출-프레임워크)
3. [확률 계산 방법론](#3-확률-계산-방법론)
4. [9대 리스크별 상세 로직](#4-9대-리스크별-상세-로직)
5. [시각화 프로세스](#5-시각화-프로세스)
6. [참고 문헌](#6-참고-문헌)

---

## 1. 개요

### 1.1 목적
본 문서는 기후 리스크 평가를 위한 연평균손실(Annual Average Loss, AAL) 산출 방법론을 상세히 기술합니다. IPCC AR6 기후변화 리스크 프레임워크를 기반으로 9대 기후 리스크에 대한 확률 및 손상률을 계산하고, SSP(Shared Socioeconomic Pathways) 시나리오별 미래 전망을 제공합니다.

### 1.2 대상 리스크
| 번호 | 리스크명 (한글) | 리스크명 (영문) | 강도지표 |
|------|----------------|----------------|---------|
| 1 | 극심한 고온 | Extreme Heat | WSDI (Warm Spell Duration Index) |
| 2 | 극심한 한파 | Extreme Cold | CSDI (Cold Spell Duration Index) |
| 3 | 가뭄 | Drought | SPEI-12 |
| 4 | 하천 홍수 | Inland Flood | RX1DAY |
| 5 | 도시 홍수 | Urban Flood | RAIN80 |
| 6 | 산불 | Wildfire | FWI (Fire Weather Index) |
| 7 | 물부족 | Water Scarcity | WSI (Water Stress Index) |
| 8 | 태풍 | Typhoon | S_tc (Cumulative Exposure Index) |
| 9 | 해수면 상승 | Sea Level Rise | Inundation Depth (ZOS 기반) |

### 1.3 SSP 시나리오
- **SSP1-2.6 (SSP126)**: 지속가능 발전 시나리오 (저탄소)
- **SSP2-4.5 (SSP245)**: 중도 시나리오
- **SSP3-7.0 (SSP370)**: 지역 경쟁 시나리오
- **SSP5-8.5 (SSP585)**: 화석연료 의존 시나리오 (고탄소)

---

## 2. AAL 산출 프레임워크

### 2.1 IPCC AR6 기후 리스크 프레임워크
IPCC 제6차 평가보고서(AR6)는 기후 리스크를 다음과 같이 정의합니다:

> **Risk = f(Hazard, Exposure, Vulnerability)**

- **Hazard (위험요소)**: 기후 관련 물리적 현상의 발생 가능성 및 강도
- **Exposure (노출도)**: 위험요소에 노출된 자산의 가치
- **Vulnerability (취약성)**: 기후 충격에 대한 민감도 및 적응 역량

**참고문헌**: IPCC, 2021: Climate Change 2021: The Physical Science Basis. Chapter 12: Climate Change Information for Regional Impact and for Risk Assessment.
- URL: https://www.ipcc.ch/report/ar6/wg1/chapter/chapter-12/

### 2.2 AAL 공식

본 시스템에서 AAL은 다음과 같이 계산됩니다:

```
AAL = Σ P[i] × DR[i] × (1 - IR)
```

| 변수 | 설명 | 비고 |
|------|------|------|
| P[i] | bin i의 발생확률 | KDE 기반 연속적 확률 |
| DR[i] | bin i의 손상률 (Damage Rate) | 리스크별 사전 정의 |
| IR | 보험 적용률 (Insurance Rate) | 현재 0으로 설정 |

### 2.3 bin 기반 확률-손상률 매핑

각 리스크는 강도지표 값에 따라 4~5개의 bin으로 분류됩니다:

```
bin1 (낮음) → bin2 (중간) → bin3 (높음) → bin4 (매우 높음) → [bin5 (극심)]
```

각 bin에는 해당 강도 수준에서의 기대 손상률(DR_intensity)이 할당됩니다.

---

## 3. 확률 계산 방법론

### 3.1 Kernel Density Estimation (KDE)

기존의 이산적 확률 계산(단순 빈도 기반) 방식은 윈도우 크기에 따라 확률이 0%, 20%, 40% 등 이산적인 값으로 제한되는 문제가 있습니다.

이를 해결하기 위해 **Kernel Density Estimation (KDE)** 기반의 연속적 확률 계산 방식을 적용합니다.

#### 3.1.1 KDE 원리

KDE는 관측된 데이터 포인트를 기반으로 연속적인 확률 밀도 함수(PDF)를 추정하는 비모수적 방법입니다.

```
f̂(x) = (1/nh) Σ K((x - x_i) / h)
```

| 변수 | 설명 |
|------|------|
| n | 샘플 수 |
| h | 대역폭 (bandwidth) |
| K | 커널 함수 (가우시안) |
| x_i | i번째 관측값 |

**참고문헌**:
- Silverman, B.W. (1986). Density Estimation for Statistics and Data Analysis. Chapman and Hall.
- SciPy Documentation: Kernel Density Estimation
  - URL: https://docs.scipy.org/doc/scipy/tutorial/stats/kernel_density_estimation.html

#### 3.1.2 대역폭 선택 (Scott's Rule)

대역폭 h는 Scott's Rule을 사용하여 자동 선택됩니다:

```
h = n^(-1/5) × σ
```

여기서 σ는 데이터의 표준편차입니다.

#### 3.1.3 bin별 확률 계산

각 bin에 대한 확률은 해당 구간에서 KDE 함수를 적분하여 계산됩니다:

```python
P[i] = ∫_{bin_min}^{bin_max} f̂(x) dx
```

SciPy의 `scipy.integrate.quad` 함수를 사용하여 수치 적분을 수행합니다.

### 3.2 구현 코드 (base_probability_agent.py)

```python
from scipy.stats import gaussian_kde
from scipy.integrate import quad

def _calculate_bin_probabilities(self, intensity_values: np.ndarray) -> List[float]:
    """
    bin별 발생확률 P_r[i] 계산 (KDE 기반 연속적 확률)
    """
    if len(intensity_values) < 3:
        # 샘플이 너무 적으면 기존 방식 사용
        return self._calculate_bin_probabilities_count(intensity_values)

    try:
        # Kernel Density Estimation
        kde = gaussian_kde(intensity_values, bw_method='scott')

        probabilities = []
        for i in range(len(self.bins)):
            bin_min, bin_max = self.bins[i]

            # 무한대 처리
            if bin_max == float('inf'):
                bin_max = np.max(intensity_values) * 1.2
            if bin_min == float('-inf'):
                bin_min = np.min(intensity_values) * 0.8

            # bin 구간 내에서 KDE 적분
            prob, _ = quad(kde, bin_min, bin_max, limit=100)
            probabilities.append(max(0.0, min(1.0, prob)))

        # 정규화 (합이 1이 되도록)
        total = sum(probabilities)
        if total > 0:
            probabilities = [p / total for p in probabilities]

        return probabilities

    except Exception as e:
        # KDE 계산 실패 시 기존 방식으로 전환
        return self._calculate_bin_probabilities_count(intensity_values)
```

---

## 4. 9대 리스크별 상세 로직

### 4.1 극심한 고온 (Extreme Heat)

#### 강도지표: WSDI (Warm Spell Duration Index)

WSDI는 ETCCDI(Expert Team on Climate Change Detection and Indices)에서 정의한 27개 기후 극한 지수 중 하나입니다.

**정의**: 최고기온이 기준기간(1961-1990) 90백분위수를 최소 6일 연속 초과하는 기간의 연간 일수 합계

**참고문헌**:
- WMO/ETCCDI, 2009: Guidelines on Analysis of extremes in a changing climate in support of informed decisions for adaptation.
  - URL: https://etccdi.pacificclimate.org/list_27_indices.shtml
- Zhang, X., et al. (2011). Indices for monitoring changes in extremes based on daily temperature and precipitation data. WIREs Climate Change.

#### bin 구간 및 손상률

| bin | WSDI 범위 | 손상률 (DR) | 설명 |
|-----|----------|------------|------|
| 1 | 0 ≤ WSDI < 3 | 0.1% | 낮음 |
| 2 | 3 ≤ WSDI < 8 | 0.3% | 중간 |
| 3 | 8 ≤ WSDI < 20 | 1.0% | 높음 |
| 4 | WSDI ≥ 20 | 2.0% | 매우 높음 |

---

### 4.2 극심한 한파 (Extreme Cold)

#### 강도지표: CSDI (Cold Spell Duration Index)

**정의**: 최저기온이 기준기간 10백분위수를 최소 6일 연속 하회하는 기간의 연간 일수 합계

**참고문헌**: ETCCDI (상동)

#### bin 구간 및 손상률

| bin | CSDI 범위 | 손상률 (DR) | 설명 |
|-----|----------|------------|------|
| 1 | 0 ≤ CSDI < 3 | 0.05% | 낮음 |
| 2 | 3 ≤ CSDI < 7 | 0.20% | 중간 |
| 3 | 7 ≤ CSDI < 15 | 0.60% | 높음 |
| 4 | CSDI ≥ 15 | 1.50% | 매우 높음 |

---

### 4.3 가뭄 (Drought)

#### 강도지표: SPEI-12 (Standardized Precipitation-Evapotranspiration Index, 12개월)

SPEI는 강수량과 잠재증발산량을 모두 고려한 다중 시간 규모 가뭄 지수입니다.

**계산 방식**:
1. 월별 기후수분밸런스 D = P - ET0 계산
2. 12개월 이동 합계
3. 로그-로지스틱 분포 피팅 후 표준화

**참고문헌**:
- Vicente-Serrano, S.M., Beguería, S., and López-Moreno, J.I. (2010). A Multiscalar Drought Index Sensitive to Global Warming: The Standardized Precipitation Evapotranspiration Index. Journal of Climate, 23(7), 1696-1718.
  - DOI: https://doi.org/10.1175/2009JCLI2909.1

#### bin 구간 및 손상률 (월별 데이터 사용)

| bin | SPEI-12 범위 | 손상률 (DR) | 설명 |
|-----|-------------|------------|------|
| 1 | SPEI > -1 | 0% | 정상~약한 가뭄 |
| 2 | -1.5 < SPEI ≤ -1 | 2% | 중간 가뭄 |
| 3 | -2.0 < SPEI ≤ -1.5 | 7% | 심각 가뭄 |
| 4 | SPEI ≤ -2.0 | 20% | 극심 가뭄 |

---

### 4.4 하천 홍수 (Inland Flood)

#### 강도지표: RX1DAY

ETCCDI 지수 중 하나로, 연간 1일 최대 강수량을 의미합니다.

**정의**: 연간 일 강수량 최댓값 (mm)

**참고문헌**: ETCCDI (상동)

#### bin 구간 및 손상률 (분위수 기반 동적 설정)

bin 경계는 기준기간(예: 1991-2020) 데이터의 분위수를 기반으로 동적으로 설정됩니다:

| bin | RX1DAY 범위 | 손상률 (DR) | 설명 |
|-----|------------|------------|------|
| 1 | < Q80 | 0% | 평범한 강우 |
| 2 | Q80 ≤ RX1DAY < Q95 | 2% | 상위 20% 강우 |
| 3 | Q95 ≤ RX1DAY < Q99 | 8% | 상위 5% 강우 |
| 4 | ≥ Q99 | 20% | 상위 1% 강우 |

---

### 4.5 도시 홍수 (Urban Flood)

#### 강도지표: RAIN80

**정의**: 연간 일 강수량 80mm 이상인 날의 수 (호우일수)

#### bin 구간 및 손상률

| bin | RAIN80 범위 | 손상률 (DR) | 설명 |
|-----|------------|------------|------|
| 1 | < 1일 | 0% | 호우 거의 없음 |
| 2 | 1 ≤ RAIN80 < 3일 | 5% | 낮은 빈도 |
| 3 | 3 ≤ RAIN80 < 5일 | 15% | 중간 빈도 |
| 4 | ≥ 5일 | 35% | 높은 빈도 |

---

### 4.6 산불 (Wildfire)

#### 강도지표: FWI (Fire Weather Index)

FWI는 캐나다 산림청에서 개발한 산불 위험 지수로, 기상 조건을 기반으로 산불 발생 및 확산 위험을 평가합니다.

**계산 방식** (간략화된 버전):
```
FWI = (1 - RHM/100) × 0.5 × (WS + 1) × exp(0.05 × (TA - 10)) × exp(-0.001 × RN)
```

| 변수 | 설명 |
|------|------|
| TA | 월평균 기온 (°C) |
| RHM | 상대습도 (%) |
| WS | 평균 풍속 (m/s) |
| RN | 강수량 (mm) |

**참고문헌**:
- Van Wagner, C.E. (1987). Development and Structure of the Canadian Forest Fire Weather Index System. Forestry Technical Report 35, Canadian Forestry Service.
- EFFIS (European Forest Fire Information System): FWI Classification
  - URL: https://effis.jrc.ec.europa.eu/about-effis/technical-background/fire-danger-forecast

#### bin 구간 및 손상률 (EFFIS 기준)

| bin | FWI 범위 | 손상률 (DR) | EFFIS 등급 |
|-----|---------|------------|-----------|
| 1 | 0 ≤ FWI < 11.2 | 0% | Low |
| 2 | 11.2 ≤ FWI < 21.3 | 1% | Moderate |
| 3 | 21.3 ≤ FWI < 38 | 3% | High |
| 4 | 38 ≤ FWI < 50 | 10% | Very High |
| 5 | FWI ≥ 50 | 25% | Extreme |

---

### 4.7 물부족 (Water Scarcity)

#### 강도지표: WSI (Water Stress Index)

WSI는 WRI(World Resources Institute)의 Aqueduct 프레임워크에서 정의한 물 스트레스 지수입니다.

**계산 방식**:
```
WSI = Withdrawal / ARWR
ARWR = TRWR × 0.63
```

| 변수 | 설명 |
|------|------|
| Withdrawal | 연간 용수이용량 (m³/year) |
| TRWR | Total Renewable Water Resources |
| ARWR | Available Renewable Water Resources |
| 0.63 | 환경유지유량(EFR) 차감 계수 (1 - 0.37) |

#### 미래 용수이용량 추정: Aqueduct 4.0

WRI Aqueduct 4.0은 CMIP6 기반 SSP 시나리오별 미래 물 스트레스를 제공합니다.

**참고문헌**:
- Kuzma, S., Saccoccia, L., and Chertock, M. (2023). Aqueduct 4.0: Updated Decision-Relevant Global Water Risk Indicators. World Resources Institute.
  - URL: https://www.wri.org/research/aqueduct-40-updated-decision-relevant-global-water-risk-indicators
  - Technical Note: https://www.wri.org/technical-notes/aqueduct-40-technical-note

#### Aqueduct-SSP 시나리오 매핑

| SSP 시나리오 | Aqueduct 시나리오 | 설명 |
|-------------|------------------|------|
| SSP1-2.6 | opt (Optimistic) | 지속가능 발전 |
| SSP2-4.5 | (opt + bau) / 2 | 중도 시나리오 보간 |
| SSP3-7.0 | bau (Business as Usual) | 현재 추세 지속 |
| SSP5-8.5 | pes (Pessimistic) | 고탄소 시나리오 |

#### bin 구간 및 손상률 (WRI 기준)

| bin | WSI 범위 | 손상률 (DR) | WRI 분류 |
|-----|---------|------------|---------|
| 1 | WSI < 0.2 | 1% | Low Stress |
| 2 | 0.2 ≤ WSI < 0.4 | 3% | Low-Medium Stress |
| 3 | 0.4 ≤ WSI < 0.8 | 7% | Medium-High Stress |
| 4 | WSI ≥ 0.8 | 15% | High-Extremely High Stress |

---

### 4.8 태풍 (Typhoon)

#### 강도지표: S_tc (Cumulative Exposure Index)

연도별 누적 태풍 노출 지수로, 사이트가 태풍의 영향권에 노출된 강도와 시간을 종합적으로 반영합니다.

**계산 방식**:
```
S_tc(t) = Σ_{storm} Σ_{τ} w_tc[bin_inst(storm, τ)]
```

| 변수 | 설명 |
|------|------|
| bin_inst | 시점별 태풍 영향 등급 (0-3) |
| w_tc | bin별 가중치 [0, 1, 3, 6] |

#### 시점별 영향 등급 판정

1. **타원 영향권 판정**: KMA Best Track 데이터의 GALE/STORM 반경 정보를 사용하여 사이트가 태풍 영향권 내에 있는지 판정
2. **위경도 → km 변환**: `1도 위도 ≈ 111km`, `1도 경도 ≈ 111km × cos(위도)`
3. **등급 결정**:
   - STORM 타원 내 + TY급: bin4 (가중치 6)
   - STORM 타원 내 + STS급 이하: bin3 (가중치 3)
   - GALE 타원 내 + TS급 이상: bin2 (가중치 1)
   - 영향권 외: bin1 (가중치 0)

#### 미래 태풍 강도 추정: IPCC AR6 기반 스케일링

IPCC AR6는 온난화에 따른 열대성 저기압(태풍)의 강도 변화를 다음과 같이 전망합니다:

> "2°C 온난화 시 열대성 저기압의 평균 최대풍속은 1-10% 증가할 가능성이 높다"

본 시스템에서는 보수적인 중간값을 적용합니다:
```
intensity_scale = 1.0 + 0.04 × ΔT
```

여기서 ΔT는 기준기간 대비 기온 상승량(°C)입니다.

**참고문헌**:
- IPCC, 2021: Chapter 11: Weather and Climate Extreme Events in a Changing Climate.
  - URL: https://www.ipcc.ch/report/ar6/wg1/chapter/chapter-11/
- Knutson, T.R., et al. (2020). Tropical cyclones and climate change assessment: Part II: Projected response to anthropogenic warming. Bulletin of the American Meteorological Society.

#### bin 구간 및 손상률

| bin | S_tc 범위 | 손상률 (DR) | 설명 |
|-----|----------|------------|------|
| 1 | S_tc = 0 | 0% | 영향 없음 |
| 2 | 0 < S_tc ≤ 5 | 2% | 약한 노출 |
| 3 | 5 < S_tc ≤ 15 | 10% | 중간~강한 노출 |
| 4 | S_tc > 15 | 30% | 매우 강한 노출 |

#### 확률적 미래 추정 (Gamma 분포)

미래 S_tc는 과거 통계를 기반으로 Gamma 분포에서 샘플링됩니다:

```python
shape = (mean / std)^2
scale = std^2 / mean
S_tc_future ~ Gamma(shape, scale × intensity_scale)
```

---

### 4.9 해수면 상승 (Sea Level Rise)

#### 강도지표: Inundation Depth (침수 깊이)

CMIP6 해수면 높이(ZOS) 데이터와 사이트 지반고도를 비교하여 침수 깊이를 계산합니다.

**계산 방식**:
```
inundation_depth = max(ZOS/100 - ground_level, 0)
X_slr(t) = max_{τ ∈ year t}(inundation_depth)
```

| 변수 | 설명 |
|------|------|
| ZOS | 해수면 높이 (cm, CMIP6) |
| ground_level | 사이트 지반고도 (m) |

**참고문헌**:
- IPCC, 2021: Chapter 9: Ocean, Cryosphere and Sea Level Change.
  - URL: https://www.ipcc.ch/report/ar6/wg1/chapter/chapter-9/

#### bin 구간 및 손상률 (국제 Damage Curve 기반)

침수 피해 함수는 여러 국제 연구에서 검증된 깊이-피해 관계를 기반으로 합니다.

| bin | 침수 깊이 | 손상률 (DR) | 설명 |
|-----|----------|------------|------|
| 1 | 0 m | 0% | 침수 없음 |
| 2 | 0 < depth < 0.3m | 2% | 경미 피해 |
| 3 | 0.3m ≤ depth < 1.0m | 15% | 중간 피해 |
| 4 | depth ≥ 1.0m | 35% | 심각 피해 |

**참고문헌**:
- Huizinga, J., de Moel, H., and Szewczyk, W. (2017). Global flood depth-damage functions. JRC Technical Reports. European Commission.
  - DOI: https://doi.org/10.2760/16510

---

## 5. 시각화 프로세스

### 5.1 시각화 구성

각 리스크에 대해 2×2 레이아웃의 시각화를 생성합니다:

```
┌─────────────────────────────────────┐
│ [1] SSP126 bin별 발생확률 (좌상)    │
│ [2] SSP585 bin별 발생확률 (우상)    │
│ [3] AAL 비교 (SSP126 vs SSP585)     │
│ [4] 빈 슬롯 또는 추가 정보          │
└─────────────────────────────────────┘
```

### 5.2 시각화 코드 (visualize_aal_with_kde.py)

```python
def calculate_yearly_probs_with_agent(agent, yearly_data, window=5):
    """에이전트의 KDE 기반 확률 계산 사용"""
    years = sorted(yearly_data.keys())
    yearly_probs = {}

    for year in years:
        window_data = [
            yearly_data[y] for y in years
            if abs(y - year) <= window // 2
        ]

        collected_data = {'climate_data': {data_key: window_data}}
        result = agent.calculate_probability(collected_data)
        yearly_probs[year] = result['bin_probabilities']

    return yearly_probs

def calculate_aal(yearly_probs, dr_intensity):
    """AAL 계산: Σ P[i] × DR[i] × (1 - IR), V_score=1.0, IR=0.0"""
    aal_values = {}

    for year, probs in yearly_probs.items():
        aal = sum(p * dr for p, dr in zip(probs, dr_intensity))
        aal_values[year] = aal

    return aal_values
```

### 5.3 생성된 시각화 파일

| 파일명 | 리스크 |
|--------|--------|
| heat_wave_aal.png | 극심한 고온 |
| cold_wave_aal.png | 극심한 한파 |
| drought_aal.png | 가뭄 |
| inland_flood_aal.png | 하천 홍수 |
| urban_flood_aal.png | 도시 홍수 |
| wildfire_aal.png | 산불 |
| water_scarcity_aal.png | 물부족 |
| typhoon_aal.png | 태풍 |
| coastal_flood_aal.png | 해수면 상승 |
| all_risks_aal_summary.png | 전체 요약 |

---

## 6. 참고 문헌

### 6.1 IPCC 보고서
1. IPCC, 2021: Climate Change 2021: The Physical Science Basis. Contribution of Working Group I to the Sixth Assessment Report.
   - Chapter 9: Ocean, Cryosphere and Sea Level Change
   - Chapter 11: Weather and Climate Extreme Events
   - Chapter 12: Climate Change Information for Regional Impact and Risk Assessment
   - URL: https://www.ipcc.ch/report/ar6/wg1/

### 6.2 기후 극한 지수
2. WMO/ETCCDI, 2009: Guidelines on Analysis of extremes in a changing climate.
   - URL: https://etccdi.pacificclimate.org/list_27_indices.shtml

3. Zhang, X., et al. (2011). Indices for monitoring changes in extremes based on daily temperature and precipitation data. WIREs Climate Change, 2, 851-870.

### 6.3 가뭄 지수
4. Vicente-Serrano, S.M., Beguería, S., and López-Moreno, J.I. (2010). A Multiscalar Drought Index Sensitive to Global Warming: The Standardized Precipitation Evapotranspiration Index. Journal of Climate, 23(7), 1696-1718.
   - DOI: https://doi.org/10.1175/2009JCLI2909.1

### 6.4 산불 위험 지수
5. Van Wagner, C.E. (1987). Development and Structure of the Canadian Forest Fire Weather Index System. Forestry Technical Report 35, Canadian Forestry Service.

6. EFFIS Technical Background
   - URL: https://effis.jrc.ec.europa.eu/about-effis/technical-background/fire-danger-forecast

### 6.5 물 스트레스
7. Kuzma, S., Saccoccia, L., and Chertock, M. (2023). Aqueduct 4.0: Updated Decision-Relevant Global Water Risk Indicators. World Resources Institute.
   - URL: https://www.wri.org/research/aqueduct-40-updated-decision-relevant-global-water-risk-indicators

### 6.6 열대성 저기압
8. Knutson, T.R., et al. (2020). Tropical cyclones and climate change assessment: Part II: Projected response to anthropogenic warming. Bulletin of the American Meteorological Society, 101(3), E303-E322.

### 6.7 침수 피해 함수
9. Huizinga, J., de Moel, H., and Szewczyk, W. (2017). Global flood depth-damage functions. JRC Technical Reports. European Commission.
   - DOI: https://doi.org/10.2760/16510

### 6.8 통계적 방법론
10. Silverman, B.W. (1986). Density Estimation for Statistics and Data Analysis. Chapman and Hall.

11. SciPy Documentation: Kernel Density Estimation
    - URL: https://docs.scipy.org/doc/scipy/tutorial/stats/kernel_density_estimation.html

### 6.9 재해 손실 모델링
12. Verisk Analytics: AAL (Average Annual Loss) Methodology
    - URL: https://www.verisk.com/blog/modeling-fundamentals--what-is-aal-/

13. Swiss Re Institute (2021): Natural catastrophes in 2020. sigma No 1/2021.

---

## 변경 이력

| 날짜 | 버전 | 변경 내용 |
|------|------|----------|
| 2025-11-24 | v1.0 | 최초 작성 |

---

*본 문서는 AIOPS 기후 리스크 평가 시스템의 AAL 산출 방법론을 기술합니다.*
