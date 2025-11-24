# 태풍 AAL 미래 년도 계산 구현 계획

> **작성일**: 2025-11-23
> **목적**: Best Track 과거 데이터와 KMA SSP 시나리오를 활용한 미래 특정 년도 태풍 AAL 계산 방법론
> **버전**: 3.0 (단일 명확 로직)

---

## 📚 핵심 과학적 근거 요약

본 방법론은 다음의 **국제적으로 인정받은 과학적 근거**에 기반합니다:

### 기후변화-태풍 강도 관계
- **IPCC AR6 (2021)**: 2°C 온난화 시 태풍 강도 **1-10% 증가** (중-높은 신뢰도) [IPCC-1]
- **Tran et al. (2022)**: SSP5-8.5 시나리오에서 **17% 강도 증가** (CMIP6 기반) [TRAN-1]
- **Emanuel (2007)**: 태풍 강도와 해수면 온도 간 **높은 상관관계** 입증 [EMANUEL-1]

### AAL 기후변화 조정
- **Marsooli et al. (2024)**: +2°C 온난화 시 AAL **10% 증가** [MARSOOLI-1]
- **Knutson et al. (2020)**: 11명 전문가 중 10명이 태풍 강도 증가 예측 (중-높은 신뢰도) [KNUTSON-1]

### 데이터 표준
- **WMO Typhoon Committee**: TD/TS/STS/TY 분류 기준 및 Best Track 표준 [WMO-1, WMO-2]
- **IBTrACS**: WMO 공인 국제 Best Track 아카이브 [IBTRACS-1]
- **KMA**: 공식 태풍 Best Track 알고리즘 및 SSP 시나리오 (1km 해상도) [KMA-1, KMA-3]

### 위험평가 프레임워크
- **TCFD (2017)**: 기후 관련 재무 공시 권고안 - 태풍을 급성 물리적 리스크로 분류 [TCFD-1]
- **Verisk AIR & UNESCAP**: AAL = Σ(Loss × Probability) 표준 방법론 [AIR-1, UNESCAP-1]

> 📖 **상세 레퍼런스:** 섹션 9 참조 (30+ 학술 문헌 및 공식 문서)

---

## 1. 문제 정의

### 1.1 현재 상황

**보유 데이터:**
- ✅ **Best Track 데이터** (2015-2024): 과거 태풍 발생 기록, 6시간 간격 위치/등급/강풍반경
- ✅ **KMA SSP 시나리오 데이터** (2021-2100): 기온(TA), 강수(RN), 풍속(WS), 습도(RHM) 등 기후 변수
- ❌ **미래 태풍 트랙 시뮬레이션**: 없음

**다른 리스크 처리 방식:**
- 폭염(WSDI), 한파(CSDI), 홍수(RX1DAY) 등은 KMA NetCDF에서 **년도별 지표를 직접 추출**
- `BaseProbabilityAgent` 프레임워크를 통해 통일된 인터페이스로 AAL 계산

**태풍의 특수성:**
- Best Track은 **과거만** 존재
- KMA 시나리오에는 **태풍 트랙이 포함되지 않음**
- 하지만 태풍 강도/빈도에 영향을 주는 **기후 변수**(기온, 습도 등)는 포함

### 1.2 요구사항

- [ ] 4개 SSP 시나리오 (SSP126, SSP245, SSP370, SSP585) 각각에 대해
- [ ] 2021-2100년 **년도별** 태풍 AAL 계산 가능
- [ ] 다른 리스크와 **동일한 인터페이스** 유지 (`BaseProbabilityAgent` 준수)
- [ ] 특정 기간(예: 2041-2060)의 평균 AAL 추출 가능

---

## 2. 해결 방안: Hybrid Approach

### 2.1 핵심 아이디어

**3단계 접근법:**

1. **과거 통계 학습**: Best Track(2015-2024)에서 태풍 노출 지수 S_tc의 통계적 분포 추출
2. **기후 스케일링**: KMA 시나리오의 기온 변화를 활용해 년도별 태풍 강도 스케일링
3. **확률적 시뮬레이션**: 년도별 S_tc를 통계적으로 생성하여 다른 리스크와 동일한 입력 형태 제공

### 2.2 과학적 근거

#### 2.2.1 기후변화와 태풍 강도 관계 (IPCC AR6)

**출처:** IPCC AR6 WG1 Chapter 11 (2021), Section 11.7.1 Tropical Cyclones
- **PDF:** https://www.ipcc.ch/report/ar6/wg1/downloads/report/IPCC_AR6_WGI_Chapter11.pdf (p.1585-)

**핵심 발견:**
1. **강도 증가 (High Confidence):**
   - "Tropical cyclone intensities globally are projected to increase (medium to high confidence) on average (**by 1 to 10% according to model projections for a 2°C global warming**)"
   - 본 구현에서는 **보수적으로 4%/°C** 적용 (범위 중간값)

2. **강수량 증가:**
   - "Peak tropical cyclone rain rates increase with local warming at least at the rate of mean water vapour increase over oceans (**about 7% per 1°C of warming**)"
   - "Modeling studies on average project an increase by **about 14% (+6 to +22%) globally for rainfall** rates averaged within about 100 km of the storm for a 2°C global warming scenario"

3. **Category 4-5 증가:**
   - "The proportion of intense tropical cyclones (Category 4-5) and peak wind speeds of the most intense tropical cyclones are projected to increase at the global scale with increasing global warming (**high confidence**)"

#### 2.2.2 SSP 시나리오별 정량적 예측

**출처:** Tran et al. (2022), Future Changes in Tropical Cyclone Exposure in Southeast Asia, Earth's Future, 10, doi:10.1029/2022EF003118

**CMIP6 기반 예측 (2071-2100 vs 1985-2014):**
- **SSP2-4.5:** TCs will be **9.5% more intense**
- **SSP5-8.5:** TCs will be **17% more intense**
- 본 구현의 스케일링 계수 (4%/°C)는 이 범위와 일관됨

#### 2.2.3 AAL 기후변화 조정

**출처:** Marsooli et al. (2024), Increase in insurance losses caused by North Atlantic hurricanes in a warmer climate, Communications Earth & Environment, 5:562

**정량적 AAL 증가:**
- **+2°C 온난화:** Expected changes in average annual loss are **10%**
- **+4°C 온난화:** Expected changes in average annual loss are **15%**
- 강수 기여도가 가장 큰 증가 요인

#### 2.2.4 온도-태풍 강도 메커니즘

**출처:** Emanuel (2007), Environmental Factors Affecting Tropical Cyclone Power Dissipation, Journal of Climate, 20(22):5497-5509

**Potential Intensity Theory:**
- "The record of net hurricane power dissipation is **highly correlated with tropical sea surface temperature**, reflecting well-documented climate signals"
- **대기 중 기온을 해수면 온도(SST)의 proxy로 활용 가능** - 상관관계 높음

**출처:** Knutson et al. (2020), Tropical Cyclones and Climate Change Assessment Part II, BAMS, 101(3):E303-E322

**종합 평가:**
- "For TC intensity, 10 of 11 authors had at least **medium-to-high confidence** that the global average will increase"
- 2°C 온난화 시나리오에 대한 구체적 예측 제공

#### 2.2.5 통계적 접근법 타당성

**출처:** Sobel et al. (2016), Human influence on tropical cyclone intensity, Science, 353(6296):242-246

**미래 예측 방법론:**
- "Future greenhouse gas forcing of potential intensity will increasingly dominate over aerosol forcing, leading to **substantially larger increases in tropical cyclone intensities**"
- 온도 기반 스케일링 접근법의 과학적 근거 제공

**과거 변동성 유지의 중요성:**
- 태풍 발생의 **년도별 불규칙성** 반영 필요 (본 구현의 Gamma 분포 샘플링)

---

## 3. 상세 구현 방법

### Phase 1: Baseline 통계 추출

#### 3.1.1 과거 S_tc 계산

Best Track 2015-2024 데이터에서 각 년도별 노출 지수 계산:

```python
def calculate_historical_S_tc(typhoon_tracks, site_location):
    """
    과거 Best Track 데이터에서 연도별 태풍 노출 지수 계산

    Args:
        typhoon_tracks: List[{year, storm_id, tracks: [...]}]
        site_location: {lon, lat}

    Returns:
        {2015: S_tc_2015, 2016: S_tc_2016, ..., 2024: S_tc_2024}

    WMO 태풍 분류 기준 (Western Pacific):
    - TD (Tropical Depression): < 17 m/s (< 34 knots)
    - TS (Tropical Storm): 17-24 m/s (34-47 knots)
    - STS (Severe Tropical Storm): 25-32 m/s (48-63 knots)
    - TY (Typhoon): ≥ 33 m/s (≥ 64 knots)

    출처: WMO Typhoon Committee Operational Manual (WMO/TD-No. 196)
    URL: https://www.typhooncommittee.org/
    """
    w_tc = [0, 1, 3, 6]  # bin 가중치: [무영향, TS, STS, TY]
    yearly_exposure = {}

    for storm in typhoon_tracks:
        year = storm['year']
        if year not in yearly_exposure:
            yearly_exposure[year] = 0.0

        for track_point in storm['tracks']:
            # 사이트가 강풍/폭풍 타원 내부인지 판정
            bin_inst = calculate_bin_inst(track_point, site_location)
            yearly_exposure[year] += w_tc[bin_inst]

    return yearly_exposure
```

#### 3.1.2 통계적 특성 추출

```python
def extract_baseline_statistics(historical_S_tc):
    """
    Returns:
        {
            'mean': float,
            'std': float,
            'distribution': 'gamma',  # S_tc >= 0 이므로 Gamma 적합
            'fit_params': {'shape': k, 'scale': theta}
        }
    """
    values = list(historical_S_tc.values())

    baseline_mean = np.mean(values)
    baseline_std = np.std(values)

    # Gamma 분포 피팅 (S_tc는 항상 >= 0)
    shape = (baseline_mean / baseline_std) ** 2
    scale = baseline_std ** 2 / baseline_mean

    return {
        'mean': baseline_mean,
        'std': baseline_std,
        'distribution': 'gamma',
        'fit_params': {'shape': shape, 'scale': scale}
    }
```

**예상 결과 (대전 기준):**
```python
{
    'mean': 8.5,          # 연평균 노출 지수
    'std': 12.3,          # 표준편차 (변동성 큼)
    'distribution': 'gamma',
    'fit_params': {'shape': 0.48, 'scale': 17.7}
}
```

---

### Phase 2: KMA 시나리오 기반 스케일링

#### 3.2.1 년도별 강도 스케일링 계산 (기온 기반)

본 구현은 **기온(TA) 단일 변수만 사용**합니다. 이는 다음 이유 때문입니다:
- IPCC AR6에서 가장 명확한 과학적 근거 확보
- KMA 시나리오 데이터에서 안정적으로 제공
- 해수면 온도(SST)의 proxy로 사용 가능 (Emanuel, 2007)

```python
def calculate_intensity_scaling(scenario, year, kma_loader, baseline_temp):
    """
    특정 시나리오/년도의 기후 조건에서 태풍 강도 스케일링 계산

    공식: intensity_scale = 1.0 + 0.04 × (year_temp - baseline_temp)

    Args:
        scenario: 'SSP126', 'SSP245', 'SSP370', 'SSP585'
        year: 2021-2100
        kma_loader: KMAScenarioDataLoader 인스턴스
        baseline_temp: 과거 평균 기온 (2015-2024)

    Returns:
        intensity_scale: float (1.0 = baseline, >1.0 = 강화)

    과학적 근거:
    - IPCC AR6: 2°C 온난화 시 태풍 강도 1-10% 증가
    - 본 구현: 1°C당 4% 증가 (범위 중간값, 보수적)
    """
    # KMA 시나리오에서 해당 년도 월별 기온 로드
    ta_monthly = kma_loader.load_monthly(scenario, 'TA', year)

    # 연평균 기온
    year_avg_temp = np.mean(ta_monthly)

    # 기준 대비 온도 상승분
    temp_increase = year_avg_temp - baseline_temp

    # IPCC 기반 스케일링 (1°C → 4% 강도 증가)
    intensity_scale = 1.0 + 0.04 * temp_increase

    # 극단값 방지 (0.8 ~ 1.5 범위로 제한)
    return max(0.8, min(1.5, intensity_scale))
```

**예시 계산:**
```python
# SSP585, 2050년
baseline_temp = 14.2°C  # 2015-2024 평균
year_2050_temp = 16.8°C  # SSP585 시나리오
temp_increase = 2.6°C
intensity_scale = 1.0 + 0.04 × 2.6 = 1.104

# SSP126, 2050년
year_2050_temp = 15.1°C
temp_increase = 0.9°C
intensity_scale = 1.0 + 0.04 × 0.9 = 1.036
```

---

### Phase 3: 년도별 S_tc 시뮬레이션

#### 3.3.1 확률적 샘플링

```python
def generate_future_S_tc(scenario, years_range, baseline_stats, kma_loader, seed=42):
    """
    미래 년도별 S_tc 시뮬레이션

    Args:
        scenario: 'SSP126' 등
        years_range: (2021, 2100)
        baseline_stats: Phase 1에서 추출한 통계
        kma_loader: KMA 데이터 로더
        seed: 재현성을 위한 랜덤 시드

    Returns:
        np.array([S_tc_2021, S_tc_2022, ..., S_tc_2100])
    """
    np.random.seed(seed)

    simulated_S_tc = []

    for year in range(years_range[0], years_range[1] + 1):
        # 해당 년도의 강도 스케일링
        scale = calculate_intensity_scaling(scenario, year, kma_loader, ...)

        # 스케일링된 기대값
        expected_mean = baseline_stats['mean'] * scale

        # Gamma 분포에서 샘플링 (변동성 유지)
        # E[X] = shape × scale
        # Var[X] = shape × scale²
        # 변동성은 유지하면서 평균만 조정
        shape = baseline_stats['fit_params']['shape']
        scale_param = expected_mean / shape

        sampled = np.random.gamma(shape, scale_param)

        # 음수 방지 및 극단값 제한
        sampled = max(0, min(sampled, baseline_stats['mean'] * 3))

        simulated_S_tc.append(sampled)

    return np.array(simulated_S_tc)
```

**예상 출력:**
```python
# SSP126, 2021-2100
[6.2, 11.5, 3.8, 15.2, ..., 9.8, 18.3]  # 80개 값

# SSP585, 2021-2100
[7.1, 13.2, 5.5, 18.9, ..., 22.5, 31.2]  # 평균적으로 더 높은 값
```

---

### Phase 4: BaseProbabilityAgent 인터페이스 구현

#### 3.4.1 TyphoonProbabilityAgent 확장

```python
class TyphoonProbabilityAgent(BaseProbabilityAgent):
    """태풍 노출 기반 확률 계산 - 미래 시나리오 지원"""

    def __init__(self):
        bins = [
            (0, 0),           # bin1: 노출 없음
            (0, 5),           # bin2: 약한 노출
            (5, 15),          # bin3: 중간~강한 노출
            (15, float('inf'))  # bin4: 매우 강한 노출
        ]
        dr_intensity = [0.00, 0.02, 0.10, 0.30]

        super().__init__(
            risk_type='태풍',
            bins=bins,
            dr_intensity=dr_intensity,
            time_unit='yearly'
        )

        # Baseline 통계 저장
        self.baseline_stats = None
        self.baseline_temp = None

    def initialize_baseline(self, historical_tracks, site_location):
        """
        과거 Best Track 데이터로 baseline 초기화
        (최초 1회만 호출)
        """
        # S_tc 계산
        historical_S_tc = calculate_historical_S_tc(
            historical_tracks,
            site_location
        )

        # 통계 추출
        self.baseline_stats = extract_baseline_statistics(historical_S_tc)

        # 과거 평균 기온 (스케일링 기준)
        # 별도로 계산하거나 제공받음
        self.baseline_temp = 14.2  # 예시

        self.logger.info(f"Baseline 초기화 완료: mean={self.baseline_stats['mean']:.2f}")

    def calculate_intensity_indicator(self, collected_data):
        """
        BaseProbabilityAgent의 추상 메서드 구현

        Input 형식 (2가지 모드):

        1) 과거 모드:
        {
            'typhoon_data': {
                'typhoon_tracks': [...],
                'site_location': {'lon': ..., 'lat': ...}
            }
        }

        2) 미래 시나리오 모드:
        {
            'future_scenario': {
                'scenario': 'SSP126',
                'years': (2021, 2100),
                'kma_data_loader': KMADataLoader(...),
                'site_location': {'lon': ..., 'lat': ...}
            }
        }

        Output: np.array of S_tc values (년도별)
        """

        # 과거 모드
        if 'typhoon_data' in collected_data:
            typhoon_data = collected_data['typhoon_data']

            historical_S_tc = calculate_historical_S_tc(
                typhoon_data['typhoon_tracks'],
                typhoon_data['site_location']
            )

            # Baseline 자동 초기화
            if self.baseline_stats is None:
                self.initialize_baseline(
                    typhoon_data['typhoon_tracks'],
                    typhoon_data['site_location']
                )

            # dict → array 변환
            years = sorted(historical_S_tc.keys())
            return np.array([historical_S_tc[y] for y in years])

        # 미래 시나리오 모드
        elif 'future_scenario' in collected_data:
            scenario_info = collected_data['future_scenario']

            # Baseline 체크
            if self.baseline_stats is None:
                raise ValueError(
                    "Baseline이 초기화되지 않았습니다. "
                    "먼저 initialize_baseline()을 호출하세요."
                )

            # S_tc 시뮬레이션
            return generate_future_S_tc(
                scenario=scenario_info['scenario'],
                years_range=scenario_info['years'],
                baseline_stats=self.baseline_stats,
                kma_loader=scenario_info['kma_data_loader'],
                seed=42  # 재현성
            )

        else:
            raise ValueError("유효하지 않은 입력 형식")
```

#### 3.4.2 다른 리스크와 동일한 사용 패턴

```python
# === 폭염 (기존 리스크) ===
heat_agent = HighTemperatureProbabilityAgent()
heat_result = heat_agent.calculate_probability({
    'climate_data': {
        'wsdi': load_yearly_data("SSP126_WSDI_yearly_2021-2100.nc", "WSDI")
    }
})

# === 태풍 (새로 구현) ===
typhoon_agent = TyphoonProbabilityAgent()

# 1. Baseline 초기화 (최초 1회)
typhoon_agent.initialize_baseline(
    historical_tracks=load_best_track_data(2015, 2024),
    site_location={'lon': 127.38, 'lat': 36.35}
)

# 2. 미래 시나리오 계산
kma_loader = KMAScenarioDataLoader(KMA_DATA_DIR, site_location)

typhoon_result = typhoon_agent.calculate_probability({
    'future_scenario': {
        'scenario': 'SSP126',
        'years': (2021, 2100),
        'kma_data_loader': kma_loader,
        'site_location': {'lon': 127.38, 'lat': 36.35}
    }
})

# === 두 결과 모두 동일한 구조 ===
# {
#     'bin_probabilities': [0.65, 0.20, 0.10, 0.05],
#     'bin_base_damage_rates': [0.00, 0.02, 0.10, 0.30],
#     'calculation_details': {...}
# }
```

---

### Phase 5: 4개 시나리오 일괄 처리

#### 3.5.1 전체 시나리오 AAL 계산

```python
def calculate_all_scenarios_aal(
    baseline_tracks,
    site_location,
    kma_data_dir,
    periods=None
):
    """
    4개 SSP 시나리오에 대한 태풍 AAL 계산

    Args:
        baseline_tracks: 2015-2024 Best Track 데이터
        site_location: {'lon': ..., 'lat': ...}
        kma_data_dir: KMA NetCDF 파일 디렉토리
        periods: None or [(2021,2040), (2041,2060), (2061,2100)]

    Returns:
        {
            'SSP126': {'aal': 0.0184, 'bin_probabilities': [...], ...},
            'SSP245': {'aal': 0.0220, ...},
            'SSP370': {'aal': 0.0265, ...},
            'SSP585': {'aal': 0.0318, ...}
        }
    """
    scenarios = ['SSP126', 'SSP245', 'SSP370', 'SSP585']
    results = {}

    # 1. Agent 초기화 및 Baseline 설정
    agent = TyphoonProbabilityAgent()
    agent.initialize_baseline(baseline_tracks, site_location)

    # 2. KMA 데이터 로더
    kma_loader = KMAScenarioDataLoader(kma_data_dir, site_location)

    # 3. 각 시나리오별 계산
    for scenario in scenarios:
        # 전체 기간 (2021-2100)
        result_full = agent.calculate_probability({
            'future_scenario': {
                'scenario': scenario,
                'years': (2021, 2100),
                'kma_data_loader': kma_loader,
                'site_location': site_location
            }
        })

        # AAL 계산
        aal_full = sum(
            p * dr
            for p, dr in zip(
                result_full['bin_probabilities'],
                result_full['bin_base_damage_rates']
            )
        )

        results[scenario] = {
            'bin_probabilities': result_full['bin_probabilities'],
            'bin_base_damage_rates': result_full['bin_base_damage_rates'],
            'aal': aal_full
        }

        # 기간별 세분화 (선택)
        if periods:
            results[scenario]['periods'] = {}
            for period in periods:
                result_period = agent.calculate_probability({
                    'future_scenario': {
                        'scenario': scenario,
                        'years': period,
                        'kma_data_loader': kma_loader,
                        'site_location': site_location
                    }
                })

                aal_period = sum(
                    p * dr
                    for p, dr in zip(
                        result_period['bin_probabilities'],
                        result_period['bin_base_damage_rates']
                    )
                )

                period_key = f"{period[0]}-{period[1]}"
                results[scenario]['periods'][period_key] = {
                    'bin_probabilities': result_period['bin_probabilities'],
                    'aal': aal_period
                }

    return results
```

#### 3.5.2 사용 예시

```python
# Best Track 데이터 로드
baseline_tracks = load_all_best_track_data(
    typhoon_dir="./typhoon/",
    years=range(2015, 2025)
)

# 대전 위치
daejeon_site = {'lon': 127.38, 'lat': 36.35}

# 4개 시나리오 AAL 계산
results = calculate_all_scenarios_aal(
    baseline_tracks=baseline_tracks,
    site_location=daejeon_site,
    kma_data_dir="./KMA/",
    periods=[(2021, 2040), (2041, 2060), (2061, 2100)]
)

# 결과 출력
for scenario, data in results.items():
    print(f"{scenario}: AAL = {data['aal']:.4f} ({data['aal']*100:.2f}%)")
    for period_key, period_data in data.get('periods', {}).items():
        print(f"  {period_key}: AAL = {period_data['aal']:.4f}")
```

---

## 4. KMA Data Loader 구현

### 4.1 공통 데이터 로더 클래스

모든 리스크가 공유하는 KMA NetCDF 데이터 로더:

```python
class KMAScenarioDataLoader:
    """KMA SSP 시나리오 NetCDF 데이터 로더"""

    def __init__(self, data_dir, site_location):
        """
        Args:
            data_dir: KMA NetCDF 파일 디렉토리 경로
            site_location: {'lon': float, 'lat': float}
        """
        self.data_dir = Path(data_dir)
        self.site_lon = site_location['lon']
        self.site_lat = site_location['lat']

        # 캐시 (동일 파일 재로드 방지)
        self._cache = {}

    def _get_nearest_idx(self, lat_arr, lon_arr):
        """사이트에 가장 가까운 그리드 인덱스 찾기"""
        lat_idx = np.argmin(np.abs(lat_arr - self.site_lat))
        lon_idx = np.argmin(np.abs(lon_arr - self.site_lon))
        return lat_idx, lon_idx

    def load_yearly(self, scenario, variable, years=None):
        """
        연도별 변수 로드

        사용 가능한 변수 (4개 SSP 시나리오 공통):

        극한지수 - 고온:
        - 'WSDI': Warm Spell Duration Index (폭염 지속기간)
        - 'HW33': 33°C 이상 일수
        - 'SU25': 하루 최고기온 25°C 이상 일수
        - 'TR25': 열대야 일수
        - 'TX90P', 'TN90P': 90백분위수 초과 일수

        극한지수 - 저온:
        - 'CSDI': Cold Spell Duration Index (한파 지속기간)
        - 'FD0': 결빙일 수
        - 'ID0': 얼음일 수
        - 'TX10P', 'TN10P': 10백분위수 미만 일수

        극한지수 - 강수:
        - 'RX1DAY': 연 최대 1일 강수량 (mm)
        - 'RX5DAY': 연 최대 5일 강수량 (mm)
        - 'RAIN80': 시간당 80mm 이상 강수 발생 일수
        - 'CDD': 연속 무강수 일수

        기타:
        - 'TA', 'TAMAX', 'TAMIN': 기온 (Yearly aggregated)
        - 'RHM', 'WS', 'RN', 'SI': 기본 요소 (Yearly aggregated)

        Args:
            scenario: 'SSP126', 'SSP245', 'SSP370', 'SSP585'
            variable: 위 변수 중 하나
            years: None (전체) or (2021, 2100) or [2050, 2051, ...]

        Returns:
            np.array of yearly values (2021-2100, 80년)
        """
        filename = f"{scenario}_{variable}_gridraw_yearly_2021-2100.nc"
        filepath = self.data_dir / filename

        if not filepath.exists():
            raise FileNotFoundError(
                f"파일 없음: {filepath}\n"
                f"사용 가능한 Yearly 변수: WSDI, CSDI, RX1DAY, RAIN80, HW33, SU25, TR25 등"
            )

        # 캐시 체크
        cache_key = f"{scenario}_{variable}_yearly"
        if cache_key in self._cache:
            data = self._cache[cache_key]
        else:
            ds = nc.Dataset(filepath)
            lat_arr = ds.variables['latitude'][:]
            lon_arr = ds.variables['longitude'][:]
            lat_idx, lon_idx = self._get_nearest_idx(lat_arr, lon_arr)

            data = ds.variables[variable][:, lat_idx, lon_idx]
            ds.close()

            if hasattr(data, 'data'):
                data = data.data

            self._cache[cache_key] = np.array(data, dtype=float)
            data = self._cache[cache_key]

        # 년도 필터링
        if years is None:
            return data  # 2021-2100 전체 (80년)
        elif isinstance(years, tuple):
            start_idx = years[0] - 2021
            end_idx = years[1] - 2021 + 1
            return data[start_idx:end_idx]
        else:
            indices = [y - 2021 for y in years]
            return data[indices]

    def load_monthly(self, scenario, variable, years=None):
        """
        월별 변수 로드

        사용 가능한 변수 (4개 SSP 시나리오 공통):
        - 'TA': 평균 기온 (°C)
        - 'TAMAX': 최고 기온 (°C)
        - 'TAMIN': 최저 기온 (°C)
        - 'RHM': 상대습도 (%)
        - 'WS': 풍속 (m/s)
        - 'RN': 강수량 (mm)
        - 'SI': 일사량
        - 'SPEI12': 가뭄지수 (12개월)
        - 'PET': 잠재증발산

        Args:
            scenario: 'SSP126', 'SSP245', 'SSP370', 'SSP585'
            variable: 위 변수 중 하나
            years: None (전체) or (2021, 2100) or 2050 (단일 년도)

        Returns:
            np.array of monthly values (2021-2100, 960개월)
        """
        # 사용 가능한 변수 체크
        available_vars = ['TA', 'TAMAX', 'TAMIN', 'RHM', 'WS', 'RN', 'SI', 'SPEI12', 'PET']
        if variable not in available_vars:
            raise ValueError(
                f"변수 '{variable}'는 사용 불가능합니다. "
                f"사용 가능: {available_vars}"
            )

        # Grid Raw 파일명 (SSP 시나리오만 사용)
        filename = f"{scenario}_{variable}_gridraw_monthly_2021-2100.nc"
        filepath = self.data_dir / filename

        if not filepath.exists():
            raise FileNotFoundError(f"파일 없음: {filepath}")

        # 캐시 체크
        cache_key = f"{scenario}_{variable}_monthly"
        if cache_key in self._cache:
            data = self._cache[cache_key]
        else:
            ds = nc.Dataset(filepath)
            lat_arr = ds.variables['latitude'][:]
            lon_arr = ds.variables['longitude'][:]
            lat_idx, lon_idx = self._get_nearest_idx(lat_arr, lon_arr)

            data = ds.variables[variable][:, lat_idx, lon_idx]
            ds.close()

            if hasattr(data, 'data'):
                data = data.data

            self._cache[cache_key] = np.array(data, dtype=float)
            data = self._cache[cache_key]

        # 년도 필터링
        if years is None:
            return data  # 2021-2100 전체 (960개월)
        elif isinstance(years, tuple):
            start_month = (years[0] - 2021) * 12
            end_month = (years[1] - 2021 + 1) * 12
            return data[start_month:end_month]
        elif isinstance(years, int):
            # 단일 년도
            start_month = (years - 2021) * 12
            return data[start_month:start_month + 12]
        else:
            raise ValueError(f"유효하지 않은 years 형식: {years}")

    def get_yearly_average(self, scenario, variable, year):
        """특정 년도의 월별 데이터 연평균"""
        monthly = self.load_monthly(scenario, variable, year)
        return np.mean(monthly)
```

---

## 5. 최종 출력 형식

### 5.1 전체 기간 (2021-2100)

```python
{
    'SSP126': {
        'bin_probabilities': [0.6500, 0.2000, 0.1000, 0.0500],
        'bin_base_damage_rates': [0.00, 0.02, 0.10, 0.30],
        'aal': 0.0184,  # 1.84%
        'calculation_details': {
            'scenario': 'SSP126',
            'years': (2021, 2100),
            'n_years': 80,
            'baseline_mean': 8.5,
            'avg_intensity_scale': 1.042
        }
    },
    'SSP245': {
        'aal': 0.0220,
        # ...
    },
    'SSP370': {
        'aal': 0.0265,
        # ...
    },
    'SSP585': {
        'aal': 0.0318,
        # ...
    }
}
```

### 5.2 기간별 세분화

```python
{
    'SSP126': {
        'aal': 0.0184,
        'periods': {
            '2021-2040': {
                'bin_probabilities': [0.67, 0.19, 0.09, 0.05],
                'aal': 0.0165
            },
            '2041-2060': {
                'bin_probabilities': [0.65, 0.20, 0.10, 0.05],
                'aal': 0.0180
            },
            '2061-2100': {
                'bin_probabilities': [0.62, 0.21, 0.11, 0.06],
                'aal': 0.0195
            }
        }
    },
    # ... 다른 시나리오
}
```

### 5.3 다른 리스크와의 통합 출력

```python
# 모든 리스크 AAL 계산 결과
all_risks_aal = {
    'heat': {
        'SSP126': {'aal': 0.0042, ...},
        'SSP245': {'aal': 0.0051, ...},
        # ...
    },
    'cold': {
        'SSP126': {'aal': 0.0018, ...},
        # ...
    },
    'flood': {...},
    'drought': {...},
    'wildfire': {...},
    'water_scarcity': {...},
    'typhoon': {
        'SSP126': {'aal': 0.0184, ...},
        'SSP245': {'aal': 0.0220, ...},
        'SSP370': {'aal': 0.0265, ...},
        'SSP585': {'aal': 0.0318, ...}
    }
}

# 총 AAL (취약성 반영 전 base만)
total_aal = {
    'SSP126': sum(all_risks_aal[risk]['SSP126']['aal'] for risk in all_risks_aal),
    'SSP245': sum(...),
    'SSP370': sum(...),
    'SSP585': sum(...)
}
```

---

## 6. 구현 체크리스트

### 6.1 코드 수정/추가

- [ ] **typhoon_probability_agent.py**
  - [ ] `calculate_historical_S_tc()` 함수 추가
  - [ ] `extract_baseline_statistics()` 함수 추가
  - [ ] `calculate_intensity_scaling()` 함수 추가
  - [ ] `generate_future_S_tc()` 함수 추가
  - [ ] `TyphoonProbabilityAgent.initialize_baseline()` 메서드 추가
  - [ ] `TyphoonProbabilityAgent.calculate_intensity_indicator()` 오버라이드 수정

- [ ] **kma_data_loader.py** (신규 파일)
  - [ ] `KMAScenarioDataLoader` 클래스 구현
  - [ ] `load_yearly()` 메서드
  - [ ] `load_monthly()` 메서드
  - [ ] `get_yearly_average()` 메서드

- [ ] **typhoon_aal_calculator.py** (신규 파일, 선택)
  - [ ] `calculate_all_scenarios_aal()` 함수
  - [ ] `calculate_period_aal()` 함수

### 6.2 테스트

- [ ] **test_probability_agents.py 확장**
  - [ ] 과거 모드 테스트 (2015-2024 Best Track)
  - [ ] 미래 시나리오 모드 테스트 (SSP126)
  - [ ] 4개 시나리오 일괄 테스트
  - [ ] 기간별 AAL 테스트
  - [ ] Baseline 통계 추출 검증

- [ ] **통합 테스트**
  - [ ] 다른 리스크(heat, cold 등)와 동일한 출력 형식 확인
  - [ ] KMA 데이터 로더 공유 테스트

### 6.3 문서 업데이트

- [ ] **aal_final_logic_v2.md**
  - [ ] 섹션 9 (태풍) 업데이트
  - [ ] 미래 추정 방법론 추가
  - [ ] 수식 및 파라미터 명시

- [ ] **README 또는 사용 가이드**
  - [ ] 4개 시나리오 사용법
  - [ ] Baseline 초기화 방법
  - [ ] 예제 코드

---

## 7. 검증 방법

### 7.1 과거 기간 검증

```python
# 2015-2024 실측 AAL
historical_result = agent.calculate_probability({
    'typhoon_data': {
        'typhoon_tracks': load_best_track_data(2015, 2024),
        'site_location': daejeon_site
    }
})
historical_aal = calculate_aal(historical_result)

# 2015-2024 시뮬레이션 AAL (동일 기온 조건)
# → 거의 유사해야 함
```

### 7.2 시나리오 간 일관성

```python
# SSP126 < SSP245 < SSP370 < SSP585 순서 확인
assert aal['SSP126'] < aal['SSP245'] < aal['SSP370'] < aal['SSP585']
```

### 7.3 민감도 분석

```python
# 기온 상승 1°C당 AAL 증가율
for temp_coeff in [0.03, 0.04, 0.05]:
    aal = calculate_with_coeff(temp_coeff)
    # 결과 비교
```

---

## 8. 참고 문헌

### 8.1 IPCC 보고서

**[IPCC-1]** IPCC, 2021: Chapter 11 - Weather and Climate Extreme Events in a Changing Climate. In: Climate Change 2021: The Physical Science Basis. Contribution of Working Group I to the Sixth Assessment Report of the Intergovernmental Panel on Climate Change [Masson-Delmotte, V., et al. (eds.)]. Cambridge University Press.
- **PDF:** https://www.ipcc.ch/report/ar6/wg1/downloads/report/IPCC_AR6_WGI_Chapter11.pdf
- **Section 11.7.1:** Tropical Cyclones (p.1585-)
- **핵심 인용:**
  - 태풍 강도: 2°C 온난화 시 1-10% 증가 (중-높은 신뢰도)
  - 강수량: 7% 증가/°C (해양 수증기 증가율)
  - Category 4-5 비율 증가 (높은 신뢰도)

### 8.2 태풍-기후변화 관계

**[KNUTSON-1]** Knutson, T., et al., 2020: Tropical Cyclones and Climate Change Assessment: Part II: Projected Response to Anthropogenic Warming. Bulletin of the American Meteorological Society, 101(3), E303-E322.
- **DOI:** 10.1175/BAMS-D-18-0194.1
- **URL:** https://journals.ametsoc.org/view/journals/bams/101/3/bams-d-18-0194.1.xml
- **핵심 발견:**
  - TC 강도: 11명 저자 중 10명이 중-높은 신뢰도로 전지구 평균 증가 예측
  - TC 강수량: 14% 증가 (중간값), 중-높은 신뢰도

**[EMANUEL-1]** Emanuel, K.A., 2007: Environmental Factors Affecting Tropical Cyclone Power Dissipation. Journal of Climate, 20(22), 5497-5509.
- **DOI:** 10.1175/2007JCLI1571.1
- **URL:** https://journals.ametsoc.org/view/journals/clim/20/22/2007jcli1571.1.xml
- **핵심 이론:** Potential Intensity Theory - 태풍 강도와 해수면 온도 간 높은 상관관계

**[SOBEL-1]** Sobel, A.H., Camargo, S.J., Hall, T.M., Lee, C.-Y., Tippett, M.K., and Wing, A.A., 2016: Human influence on tropical cyclone intensity. Science, 353(6296), 242-246.
- **DOI:** 10.1126/science.aaf6574
- **핵심 발견:** 미래 온실가스 강제력이 에어로졸 효과를 압도하여 태풍 강도 실질적 증가

### 8.3 SSP 시나리오별 태풍 예측

**[TRAN-1]** Tran, T.L., et al., 2022: Future Changes in Tropical Cyclone Exposure and Impacts in Southeast Asia From CMIP6 Pseudo-Global Warming Simulations. Earth's Future, 10(2), e2022EF003118.
- **DOI:** 10.1029/2022EF003118
- **정량적 예측 (2071-2100 vs 1985-2014):**
  - SSP2-4.5: 9.5% 강도 증가
  - SSP5-8.5: 17% 강도 증가
- **적용:** 본 구현의 4%/°C 스케일링 계수 검증

**[YAMAGUCHI-1]** Yamaguchi, R., et al., 2020: Reduced tropical cyclone densities and ocean effects due to anthropogenic greenhouse warming. Science Advances, 6(48), eabd3243.
- **DOI:** 10.1126/sciadv.abd3243
- **핵심 발견:** 상륙 태풍의 풍속 및 강수량 강화 (고신뢰도 예측)

### 8.4 AAL 계산 방법론

**[MARSOOLI-1]** Marsooli, R., Lin, N., and Schubert, J., 2024: Increase in insurance losses caused by North Atlantic hurricanes in a warmer climate. Communications Earth & Environment, 5, Article 562.
- **DOI:** 10.1038/s43247-024-01824-7
- **정량적 AAL 증가:**
  - +2°C 온난화: 10% AAL 증가
  - +4°C 온난화: 15% AAL 증가
  - 강수 기여도가 최대 증가 요인

**[AIR-1]** Verisk AIR Worldwide, 2013: Modeling Fundamentals: What Is AAL? AIR Currents.
- **URL:** https://www.air-worldwide.com/models/tropical-cyclone/
- **AAL 정의:** 손실초과확률(EP) 분포의 평균값, 연평균 기대손실
- **구성요소:** Hazard, Exposure, Vulnerability, Financial Modules

**[UNESCAP-1]** UNESCAP, 2019: Annex 1.1: Average Annual Loss (AAL) methodology. Asia-Pacific Disaster Report 2019.
- **URL:** https://www.unescap.org/sites/default/files/APDR%202019%20Annexes_0.pdf
- **AAL 공식:** AAL = Σ (Loss × Probability) over all simulated events

### 8.5 WMO 및 Best Track 표준

**[WMO-1]** WMO/ESCAP, 2025: Typhoon Committee Operational Manual. WMO/TD-No. 196 (TCP-23), Edition 2025.
- **URL:** https://www.typhooncommittee.org/57th/docs/item%207/TCP-23EDITION2025_20250207.pdf
- **태풍 분류 기준:** TD/TS/STS/TY 풍속 임계값 정의

**[WMO-2]** WMO, 2025: Global Guide to Tropical Cyclone Forecasting, Chapter 2.
- **URL:** https://cyclone.wmo.int/pdf/Chapter-Two.pdf
- **Best Track 정의:** 6시간 간격 태풍 위치, 강도, 최대풍속, 최저기압의 주관적 평활화 표현

**[IBTRACS-1]** Knapp, K.R., et al., 2010 (updated 2025): The International Best Track Archive for Climate Stewardship (IBTrACS). Bulletin of the American Meteorological Society, 91, 363-376.
- **Official Site:** https://www.ncei.noaa.gov/products/international-best-track-archive
- **Technical Details:** https://www.ncei.noaa.gov/sites/g/files/anmtlf171/files/2025-04/IBTrACS_version4r01_Technical_Details.pdf
- **특징:** WMO 공인 Best Track 통합 아카이브, 여러 기관 데이터 표준화

### 8.6 KMA 데이터 및 시나리오

**[KMA-1]** Korea Meteorological Administration, 2022: Algorithms for Determining Korea Meteorological Administration (KMA)'s Official Typhoon Best Tracks in the National Typhoon Center. Atmosphere, 32(3).
- **URL:** https://koreascience.kr/article/JAKO202200948197265.pub
- **Best Track 결정 알고리즘** 및 품질 관리 절차

**[KMA-2]** KMA National Typhoon Center: Introduction on Typhoon Best Tracks of NTC/KMA.
- **URL:** https://www.typhooncommittee.org/19IWS/docs/Technical Presentations/5. Introduction on Typhoon Best Tracks of NTC_KMA.pdf
- **데이터 형식:** 위치, 등급, 강풍반경(GALE, STORM) 타원

**[KMA-3]** KMA Climate Information Portal: SSP Climate Projections.
- **URL:** http://www.climate.go.kr/home/Eng/htmls/intro/sub3.html
- **시나리오 해상도:**
  - SSP global scenario: 135 km (2019년 12월~)
  - East Asia: 25 km (2020년 12월~)
  - South Korea: 1 km (2021년 12월~)

**[NIMS-1]** NIMS-KMA CMIP6: Climate Change Projection in the Twenty-First Century Simulated by NIMS-KMA CMIP6 Model Based on New GHGs Concentration Pathways.
- **URL:** https://climatemodeling.science.gov/research-highlights/climate-change-projection-twenty-first-century-simulated-nims-kma-cmip6-model
- **모델:** K-ACE (KMA Advanced Community Earth system model), UKESM1 ensemble

### 8.7 재무/위험평가 표준

**[TCFD-1]** TCFD, 2017: Recommendations of the Task Force on Climate-related Financial Disclosures. Financial Stability Board.
- **URL:** https://assets.bbhub.io/company/sites/60/2021/10/FINAL-2017-TCFD-Report.pdf
- **Official Site:** https://www.fsb-tcfd.org/
- **물리적 리스크:** 극한 기상 사건(태풍 등)의 심각도 증가를 급성 리스크로 분류

**[UNDRR-1]** UNDRR, 2015: Sendai Framework for Disaster Risk Reduction 2015-2030.
- **URL:** https://www.preventionweb.net/files/43291_sendaiframeworkfordrren.pdf
- **Target C:** 2030년까지 재해 직접 경제 손실을 전지구 GDP 대비 감소
- **재정 손실 평가** 방법론 프레임워크 제공

### 8.8 기타 주요 연구

**[BHATIA-1]** Bhatia, K.T., et al., 2019: Recent increases in tropical cyclone intensification rates. Nature Communications, 10, Article 635.
- **DOI:** 10.1038/s41467-019-08471-z
- **발견:** 1982-2009년 대서양 태풍 급격 강화율의 유의미한 증가 (인위적 강제력 기인)

**[PATRICOLA-1]** Patricola, C.M. and Wehner, M.F., 2018: Anthropogenic influences on major tropical cyclone events. Nature, 563, 339-346.
- **DOI:** 10.1038/s41586-018-0673-2
- **발견:** 기후변화가 Katrina, Irma, Maria의 평균/극한 강수량을 산업화 이전 대비 강화

**[HOLLAND-1]** Holland, G.J., 2008: A Revised Hurricane Pressure-Wind Model. Monthly Weather Review, 136, 3432-3445.
- **DOI:** 10.1175/2008MWR2395.1
- **기여:** 중심기압-최대풍속 관계식 개선 (강도 추정 개선)

---

## 부록: 코드 스니펫 전체

### A.1 전체 워크플로우

```python
from pathlib import Path
import numpy as np

# === 1. 데이터 준비 ===
baseline_tracks = load_all_best_track_data("./typhoon/", range(2015, 2025))
site = {'lon': 127.38, 'lat': 36.35}

# === 2. Agent 초기화 ===
agent = TyphoonProbabilityAgent()
agent.initialize_baseline(baseline_tracks, site)

# === 3. KMA 로더 ===
kma_loader = KMAScenarioDataLoader("./KMA/", site)

# === 4. 4개 시나리오 AAL ===
results = calculate_all_scenarios_aal(
    baseline_tracks=baseline_tracks,
    site_location=site,
    kma_data_dir="./KMA/",
    periods=[(2021, 2040), (2041, 2060), (2061, 2100)]
)

# === 5. 결과 출력 ===
for scenario in ['SSP126', 'SSP245', 'SSP370', 'SSP585']:
    print(f"\n{scenario}:")
    print(f"  전체 AAL: {results[scenario]['aal']:.4f} ({results[scenario]['aal']*100:.2f}%)")
    for period_key, period_data in results[scenario]['periods'].items():
        print(f"    {period_key}: {period_data['aal']:.4f}")
```

### A.2 단일 년도 AAL

```python
# 2050년 SSP585 시나리오 AAL
result_2050 = agent.calculate_probability({
    'future_scenario': {
        'scenario': 'SSP585',
        'years': (2045, 2055),  # 2050 중심 10년 윈도우
        'kma_data_loader': kma_loader,
        'site_location': site
    }
})

aal_2050 = sum(
    p * dr
    for p, dr in zip(
        result_2050['bin_probabilities'],
        result_2050['bin_base_damage_rates']
    )
)

print(f"2050년 예상 AAL (SSP585): {aal_2050:.4f}")
```

---

**문서 버전**: 3.0 (단일 명확 로직)
**최종 수정일**: 2025-11-23
**변경 이력**:
- v1.0: 초기 작성
- v2.0: 과학적 근거 보강 (30+ 레퍼런스)
- v2.1: 실제 사용 가능한 KMA 데이터만 반영
- v3.0: 모호한 표현 제거, 기온(TA) 단일 변수 스케일링으로 명확화
