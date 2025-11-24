## 공통 프레임

리스크 r, 사이트 j, 연도 t 에 대해:

- 강도지표:
    - `X_r(t)` (또는 SLR의 경우 `X_slr(t, j)` 처럼 사이트 의존)
- bin 분류:
    - `X_r(t) in bin_r[i]`
- bin별 발생확률:
    - `P_r[i] = (해당 bin에 속한 연도 수) / (전체 연도 수)`
- 강도별 기본 손상률(취약성 미반영):
    - `DR_intensity_r[i]` (리스크 r, bin i에 대한 base damage rate)
- 취약성 점수 (Vulnerability Agent 출력):
    - `V_score_r(j)` (0 ~ 1)
- 취약성 스케일 계수:
    - `F_vuln_r(j) = s_r_min + (s_r_max - s_r_min) * V_score_r(j)`
- 최종 손상률:
    - `DR_r[i, j] = DR_intensity_r[i] * F_vuln_r(j)`
- 연평균손실률(AAL):
    - `AAL_r(j) = sum over i [ P_r[i] * DR_r[i, j] * (1 - IR_r) ]`
    - `IR_r` = 리스크 r의 보험 보전율 (없으면 0)

> v9는 이 프레임을 유지한 상태에서, 각 리스크별 X_r(t)와 사용 데이터만 확정한 버전이다.

---

## 1. 극심한 고온 (Extreme Heat) r = "heat"

- 사용 데이터: KMA 연간 극값 지수 `WSDI` (Warm Spell Duration Index)
- 강도지표:
    - `X_heat(t) = WSDI(t)`
- 의미:
    - 평년 기준 상위 분위수 이상 고온이 **연속적으로 지속된 기간의 연간 합**
- bin 예시:
    - `bin1: 0 <= WSDI < 3`
    - `bin2: 3 <= WSDI < 8`
    - `bin3: 8 <= WSDI < 20`
    - `bin4: WSDI >= 20`
- 나머지:
    - `P_heat[i]`, `DR_intensity_heat[i]`, `V_score_heat(j)` 는 v8 구조 그대로.
    
### 1-3. 연도 비율 기반 확률

- 각 bin에 들어간 연도 비율 계산
- `P_heat[i] = (bin i에 속한 연도 수) / (전체 연도 수)`

### 2. Base 손상률 — DR_heat_int[i]

bin별 기준 손상률(예시):

| Bin | WSDI 구간 | DR_heat_int[i] |
| --- | --- | --- |
| bin1 | 낮음 | 0.1% |
| bin2 | 중간 | 0.3% |
| bin3 | 높음 | 1.0% |
| bin4 | 매우 높음 | 2.0% |

### 3. 취약성 점수 적용 — F_heat_vuln(j)

#### 3-1. Vulnerability Score

- Vulnerability Agent 출력
- `V_score_heat(j) ∈ [0, 1]`

#### 3-2. 스케일링 범위

- 최소 스케일: `s_heat_min = 0.7`
- 최대 스케일: `s_heat_max = 1.3`
- 범위 폭: `1.3 – 0.7 = 0.6`

#### 3-3. 스케일 계수

- `F_heat_vuln(j) = 0.7 + 0.6 × V_score_heat(j)`
- 취약성 낮음(V=0) → 0.7
- 취약성 중간(V=0.5) → 1.0
- 취약성 높음(V=1) → 1.3

### 4. 최종 손상률 — DR_heat[i, j]

bin i, 자산 j에 대해:

`DR_heat[i, j] = DR_heat_int[i] × F_heat_vuln(j)`

### 5. AAL 계산 — AAL_heat(j)

보험 보전율(IR_heat)을 고려한 최종 연평균 손실률:

`AAL_heat(j) = Σᵢ P_heat[i] × DR_heat[i, j] × (1 − IR_heat)`

---

## 2. 극심한 한파 (Extreme Cold) r = "cold"

- 사용 데이터: KMA 연간 극값 지수 `CSDI` (Cold Spell Duration Index)
- 강도지표:
    - `X_cold(t) = CSDI(t)`
- 의미:
    - 평년 기준 하위 분위수 이하 저온이 **연속적으로 지속된 기간의 연간 합**
- bin 예시:
    - `bin1: 0 <= CSDI < 3`
    - `bin2: 3 <= CSDI < 7`
    - `bin3: 7 <= CSDI < 15`
    - `bin4: CSDI >= 15`

### 2-1. bin 별 base 손상률

```text
DR_cold_int[1] = 0.0005   # 0.05%
DR_cold_int[2] = 0.0020   # 0.20%
DR_cold_int[3] = 0.0060   # 0.60%
DR_cold_int[4] = 0.0150   # 1.50%
```

### 2-2. 취약성 스케일링 F_cold_vuln(j)

```text
V_score_cold(j) ∈ [0, 1]

s_cold_min = 0.7
s_cold_max = 1.3

F_cold_vuln(j) = s_cold_min + (s_cold_max - s_cold_min) * V_score_cold(j)
               = 0.7 + 0.6 * V_score_cold(j)
```

### 2-3. 최종 손상률

```text
DR_cold[i, j] = DR_cold_int[i] * F_cold_vuln(j)
```

### 2-4. 연간 발생확률 & AAL

```text
P_cold[i] = (X_cold(t)가 bin i에 들어간 연도 수) / (전체 연도 수)

AAL_cold(j) = Σ_i P_cold[i] * DR_cold[i, j] * (1 - IR_cold)
```

---

## 3. 산불 (Wildfire, r = "fire") — FWI 식 사용

### 3-1. FWI 계산

입력:

- `TA(t, m)` : 월별 평균 기온 (°C)
- `RHM(t, m)` : 월별 상대습도 (%)
- `WS(t, m)` : 월별 평균 풍속 (m/s)
- `RN(t, m)` : 월별 강수량 (mm)

FWI 로직

```text
FWI(t, m) = (1 - RHM(t,m) / 100)
            * 0.5 * (WS(t,m) + 1)
            * exp(0.05 * (TA(t,m) - 10))
            * exp(-0.001 * RN(t,m))
```

### 3-2. 산불 강도지표 (월별 FWI)

월별 강도지표:

```text
X_fire(t, m) = FWI(t, m)
```

### 3-3. bin 및 발생확률

bin (EFFIS 기준 압축):

- `bin1: 11.2 <= FWI < 21.3`
- `bin2: 21.3 <= FWI < 38`
- `bin3: 38 <= FWI < 50`
- `bin4: FWI >= 50`

EFFIS FWI 지수 구간:

| 구간 | 의미 | 산불 발생성 |
| --- | --- | --- |
| Very low (<5.2) | 연료가 젖어 있음 | 거의 없음 |
| Low (5.2~11.2) | 불 나도 금방 꺼짐 | 아주 낮음 |
| Moderate (11.2~21.3) | 연료 건조 증가 | **관측상 산불 시작 증가 영역** |
| High (21.3~38) | 확산 가능성 매우 높음 | **본격적 위험 영역** |
| Very High (38~50) | 대형 산불 위험 ↑ | 심각 |
| Extreme (≥50) | 폭발적 확산 | 매우 심각 |

월 기반 발생확률:

```text
P_fire[i] = (#월이 bin i에 속한 개수) / (총월수)
```

### 3-4. base 손상률 DR_intensity_fire[i]

```text
DR_intensity_fire = {0.01, 0.03, 0.10, 0.25}  # 1%, 3%, 10%, 25%
```

취약성:

- `V_score_fire(j)`에 산림거리, 산림밀도, 경사, 건물/시설 특성 등을 반영하고,
- 스케일링 `F_vuln_fire(j)`를 적용해 최종 손상률 계산.

---

## 4. 가뭄 (Drought, r = "drought") — SPEI12

- 사용 데이터: KMA `SPEI12` (Monthly)

월별:

```text
X_drought(t, m) = SPEI12(t, m)
```

### 4-1. bin 정의

- `bin1: SPEI12 > -1`
- `bin2: -1 >= SPEI12 > -1.5`
- `bin3: -1.5 >= SPEI12 > -2.0`
- `bin4: SPEI12 <= -2.0`

### 4-2. bin별 발생확률

```text
P_drought[i] = (#월이 해당 bin에 속한 개수) / (총월수)
```

### 4-3. 강도별 손상률 DR_intensity_drought

```text
DR_base_drought = {
  bin1: 0.00,   # 거의 영향 없음
  bin2: 0.02,   # 중간 가뭄
  bin3: 0.07,   # 심각 가뭄
  bin4: 0.20    # 극심 가뭄
}
```

### 4-4. 취약성 및 최종 손상률

```text
F_vuln_drought(j) = s_min + (s_max - s_min) * V_score_drought(j)
DR_drought[i, j]  = DR_intensity_drought[i] * F_vuln_drought(j)
```

- `s_min`, `s_max`는 취약성 스케일의 하한/상한.

### 4-5. AAL

보험 보전율 `IR_drought` (없으면 0):

```text
AAL_drought(j)
  = Σ_i P_drought[i] * DR_drought[i, j] * (1 - IR_drought)
```

---

## 5. 물부족 (Water Stress, r = "wst")

### 5-1. 재생 가능 수자원 (TRWR)

- `TRWR = IRWR + ERWR`
- 한국은 `ERWR ≈ 0` → 사실상 IRWR 기반
- 실측 접근: **유역 하류 유량 관측소의 연간 총 유량(Volume_y)** 을 기반으로 TRWR 계측

관측 방법:

1. **하류 관측소 선택**
   - 한강권역 → 팔당 또는 하류 본류 등
   - 섬진강 등 좁은 유역은 대표 1개
   - 여러 개면 유역면적 가중평균 가능
2. **연도별 일유량 수집**

```text
http://www.wamis.go.kr:8080/wamis/openapi/wkw/flw_dtdata
?obscd=XXXX
&year=YYYY
&output=json
```

- `fw` = 일유량(m³/s)
- `ymd` = 날짜

3. **Volume_y(년간 총유량) 계산**
   - 일별 `fw_d × 86400` 누적
   - 결측 < 5~10% → 평균 보정
   - 결측 > 20~30% → 해당 연도 제외
4. **TRWR 계산**
   - 유효 연도들의 `Volume_y` 평균 → `TRWR_i` (유역 i의 재생 가능 수자원)

### 5-2. 미래 TRWR 스케일링

- SSP 강수량/ET₀ 변화 → 유효강수량(P − ET₀) 변화율로 스케일링

월별 ET₀ → 연 단위 집계:

```text
ET0_year(t) = Σ_m ET0(t,m)
```

ET0 = [ 0.408 * Δ * (Rn − G) + γ * (900 / (T + 273)) * u2 * (es − ea) ]
      ----------------------------------------------------------------
                 Δ + γ * (1 + 0.34 * u2)

📌 필요 변수 — KMA 매핑
항목	필요 여부	KMA 데이터
T	필수	TA (월평균 기온)
풍속 u2	필수	WS (10m → 2m 환산)
상대습도 RH	필수	RHM
일사량 Rs	필수	SI (그대로 사용)
지면열 G	월 기준 필요 없음	0 사용

📌 보조식
1) 포화수증기압
es = 0.6108 * exp(17.27*T / (T + 237.3))

2) 실제수증기압
ea = es * RH / 100

3) 기울기 Δ
Δ = 4098 * es / (T + 237.3)^2

4) 풍속 보정

WS가 10m 기준일 경우:

u2 = WS * 4.87 / ln(67.8*10 − 5.42)

5) 순복사량

순단파복사량

Rns = (1 − 0.23) * Rs


(Rs = KMA SI)

순장파복사량 (Tmean 기반 근사)

T_K = T + 273.16
Rnl = 4.903e−9 * (T_K^4)
      * (0.34 − 0.14 * sqrt(ea))
      * (1.35 * (Rs/Rso) − 0.35)


순복사량

Rn = Rns − Rnl
G = 0

연 유효강수량(기본형):

```text
P_eff_year(t) = Σ_m [P(t,m) - ET0(t,m)]
```

스케일링 계수 및 미래 TRWR:

```text
scale_TRWR(t)  = P_eff_year(t) / P_eff_baseline_mean
TRWR_future(t) = TRWR_baseline * scale_TRWR(t)
```

### 5-3. 가용 재생 수자원 (ARWR)

pdf 근거:

- `ARWR = TRWR × (1 − αEFR)`
- `αEFR = 0.37`

즉,

```text
ARWR = TRWR * 0.63
```

### 5-4. 수요 (Blue Water Withdrawal)

WAMIS 용수이용량 API 사용:

```text
http://www.wamis.go.kr:8080/wamis/openapi/wks/wks_wiawtaa_lst
```

### 5-5. 강도지표 X_wst(t)

WSI 기반 핵심 지표:

```text
WSI(t) = Withdrawal(t) / ARWR_future(t)
```

- `Withdrawal(t)`: 해당 연도 용수이용량
- `ARWR_future(t)`: 스케일링된 연간 가용 재생 수자원

bin (표준 WRI 구간 압축):

- `bin1: WSI < 0.2`
- `bin2: 0.2 ≤ WSI < 0.4`
- `bin3: 0.4 ≤ WSI < 0.8`
- `bin4: WSI ≥ 0.8`

발생확률 (연도 기반):

```text
P_wst[i] = (WSI(t)가 bin i에 속하는 연도 수) / N
```

### 5-6. base 손상률 DR_intensity_wst[i]

pdf에 손상률 직접 언급 없음 → **자료 부재 → 임의 추정값임을 명시**

| bin | base DR_intensity_wst | 해석 |
| --- | --- | --- |
| 1 | 0.01 | 물공급 의존도 낮음 |
| 2 | 0.03 | 일시 공급 제약 |
| 3 | 0.07 | 생산 차질 빈발 |
| 4 | 0.15 | 공급 중단·가동률 급락 위험 |

### 5-7. 취약성 F_vuln_wst(j)

다른 리스크와 동일한 스케일링:

- 상수도 의존도
- 정수장/취수장 단일 소스 여부
- 비상용 저장탱크 유무
- 산업용수 비율

등을 0~1로 정규화해서 적용:

```text
DR_wst[i, j] = DR_intensity_wst[i] * F_vuln_wst(j)

AAL_wst(j)   = Σ_i P_wst[i] * DR_wst[i, j] * (1 - IR_wst)
```

---

## 6. 내륙 홍수 (River Flood, r = "rflood")

- 사용 데이터: KMA 연간 강수 극값 지수 `RX1DAY` (필요시 `RX5DAY` 보조)

강도지표:

```text
X_rflood(t) = RX1DAY_s(t)
```

- s: 사이트/시나리오
- t: 연도

### 6-1. 기준기간에서 Rx1day 분포 추출

1. 사이트(또는 그리드) s에 대해 기준기간 `W_base` 설정 (예: 1991–2020, 30년)
2. 각 해 t ∈ W_base에 대해 `X_rflood_base^s(t) = RX1DAY_s(t)` 계산
3. 이 30개 값 분포에서 상위 분위수 계산:
   - `Q80_s` : 80퍼센타일
   - `Q95_s` : 95퍼센타일
   - `Q99_s` : 99퍼센타일

### 6-2. bin 정의

- `bin1: X_rflood <  Q80_s`
- `bin2: Q80_s ≤ X_rflood < Q95_s`
- `bin3: Q95_s ≤ X_rflood < Q99_s`
- `bin4: X_rflood ≥ Q99_s`

### 6-3. base 손상률 DR_intensity_rflood[i] (예시)

| bin | 설명 | DR_intensity_rflood[i] |
| --- | --- | --- |
| 1 | 평범~약간 강한 비 | 0.00 |
| 2 | 상위 20% 강우 (Q80~Q95) | 0.02 (2%) |
| 3 | 상위 5% 강우 (Q95~Q99) | 0.08 (8%) |
| 4 | 상위 1% 강우 (≥Q99) | 0.20 (20%) |

### 6-4. 취약성 함수 및 AAL

Vulnerability Agent 점수: `V_score_rflood(j)` (0~1)

```text
F_vuln_rflood(j)
  = s_rflood_min + (s_rflood_max - s_rflood_min) * V_score_rflood(j)

DR_rflood[i, j]
  = DR_intensity_rflood[i] * F_vuln_rflood(j)

AAL_rflood(j)
  = Σ_i P_rflood[i] · DR_rflood[i, j] · (1 - IR_rflood)
```

- `IR_rflood`: 내륙 홍수 보험 보전율 (없으면 0)

---

## 7. 도시 집중 홍수 (Pluvial Flooding, r = "pflood")

- 사용 데이터: KMA `RAIN80` (연 강한 단시간 강우 proxy)

```text
R_peak(t) = RAIN80(t)
```

### 7-1. 배수능력 프록시 (비-KMA, DEM + 토지피복도)

```text
if urban_ratio(j) >= 0.7:
    base_capacity = 60  # mm/h
elif 0.3 <= urban_ratio(j) < 0.7:
    base_capacity = 40
else:
    base_capacity = 25

if slope(j) < 0.01:
    slope_factor = 0.8
elif 0.01 <= slope(j) <= 0.03:
    slope_factor = 1.0
else:
    slope_factor = 1.2

drain_capacity_mmph(j) = base_capacity * slope_factor
```

### 7-2. 등가 강우강도 및 초과분

```text
R_peak_mmph(t) = c_rain * RAIN80(t)

E_pflood(t, j) = max(0, R_peak_mmph(t) - drain_capacity_mmph(j))
```

- `E_pflood` = “배수능력을 넘는 강우강도 초과분(mm/h)”

### 7-3. 침수심 변환 및 bin

```text
X_pflood(t, j) = k_depth * E_pflood(t, j)
```

- `k_depth`: 보정계수 (튜닝 필요)

bin:

- `bin1: X_pflood(t,j) = 0`
- `bin2: 0 < X_pflood < 0.3 m`
- `bin3: 0.3 ≤ X_pflood < 1.0 m`
- `bin4: X_pflood ≥ 1.0 m`

### 7-4. base 손상률 DR_intensity_pflood[i]

| bin | 침수 깊이 | DR_intensity_pflood[i] (예시 base) | 해석 |
| --- | --- | --- | --- |
| 1 | 0 m | 0.00 | 침수 없음 |
| 2 | 0–0.3 m | 0.05 (5%) | 경미~중간 피해 (마감, 지상층 물품) |
| 3 | 0.3–1.0 m | 0.25 (25%) | 본격적인 건물·설비 피해 |
| 4 | ≥ 1.0 m | 0.50 (50%) | 광범위·중대 피해 |

### 7-5. 취약성 및 AAL

```text
F_vuln_pflood(j)
  = s_pflood_min + (s_pflood_max - s_pflood_min) * V_score_pflood(j)

DR_pflood[i, j]
  = DR_intensity_pflood[i] * F_vuln_pflood(j)

AAL_pflood(j)
  = Σ_i P_pflood[i | j] * DR_pflood[i, j] * (1 - IR_pflood)
```

---

## 8. 해수면 상승 (Sea Level Rise, r = "slr") — zos 사용

외부 해양/기후모델 데이터의 `zos` 사용.

입력:

- CMIP6 `zos` (해수면 높이, cm) → m로 변환
- `ground_level(j)` : 사이트 j의 지반고도 또는 기준 높이 (m, DEM/건축물 데이터)

### 8-1. 시점별 침수심

```text
inundation_depth(t, τ, j) = max( zos(t, τ)/100 - ground_level(j), 0 )
```

### 8-2. 연도별 해수면 상승 강도지표 (사이트별)

```text
X_slr(t, j) = max over τ in year t [ inundation_depth(t, τ, j) ]
```

- 해당 연도 동안 사이트가 경험할 수 있는 **최대 침수심**을 강도지표로 사용.

### 8-3. bin 및 base DR

bin:

- `bin1: depth = 0`
- `bin2: 0 < depth < 0.3`
- `bin3: 0.3 ≤ depth < 1.0`
- `bin4: depth ≥ 1.0`

강도별 base DR (국제 Damage Curve 기반 예시):

| 깊이범위 | 국제 Damage Curve 범위 | DR | 비고 |
| --- | --- | --- | --- |
| 0 m | 0% | 0% | 그대로 |
| 0–0.3 m | 1–5% | 2% | 중간값 |
| 0.3–1.0 m | 10–30% | 15% | 중간값 |
| ≥1.0 m | 30–55% | 35% | 중간값 |

### 8-4. 발생확률 및 AAL

```text
P_slr[i] = (해당 bin에 속한 연도 수) / (전체 연도 수)
```

취약성:

```text
F_vuln_slr(j) = s_min + (s_max - s_min) * V_score_slr(j)
DR_slr[i, j]  = DR_base_slr[i] * F_vuln_slr(j)

AAL_slr(j)    = Σ_i P_slr[i] * DR_slr[i, j] * (1 - IR_slr)
```

---

## 9. 열대성 태풍 (Tropical Cyclone, r = "tc")

### 9-1. KMA 태풍 Best Track API

각 태풍 `storm`, 각 시점 `τ` (보통 6시간 간격):

- YEAR, MONTH, DAY, HOUR → 시점 τ가 포함된 연도 t
- LON, LAT → 태풍 중심 위치
- GRADE → TD / TS / STS / TY
- GALE_LONG, GALE_SHORT, GALE_DIR → 강풍(15 m/s 이상) 타원
- STORM_LONG, STORM_SHORT, STORM_DIR → 폭풍(25 m/s 이상) 타원

사이트 j:

- 위치: `(lon_j, lat_j)`

취약성 점수:

- Vulnerability Agent 결과: `V_norm_tc(j) ∈ [0, 1]`

### 9-2. 1단계 — 시점별 bin_inst(storm, τ, j)

시점별 = Best Track의 한 row 기준으로, 사이트가 그 시점에 어느 등급 영향 받았는지 판정.

1. 태풍 중심과 사이트 사이의 (dx, dy) 계산
2. GALE, STORM 각각에 대해 `DIR` 각도만큼 회전 → `(x', y')`
3. 타원 내부 여부 판정:

```text
inside_gale  = (x_gale'  / GALE_LONG)^2  + (y_gale'  / GALE_SHORT)^2  <= 1
inside_storm = (x_storm' / STORM_LONG)^2 + (y_storm' / STORM_SHORT)^2 <= 1
```

4. 시점별 bin 부여 (강도 구간 개념):

```text
bin1: X_tc < 17 m/s        → TS 미만, 영향 거의 없음
bin2: 17 ≤ X_tc < 25 m/s   → TS급 영향
bin3: 25 ≤ X_tc < 33 m/s   → STS급 영향
bin4: X_tc ≥ 33 m/s        → TY급 영향
```

로직 예시:

```text
if inside_storm:
    if GRADE == "TY":
        bin_inst = 4
    else:
        bin_inst = 3
elif inside_gale:
    if GRADE in {"TS", "STS", "TY"}:
        bin_inst = 2
    else:
        bin_inst = 1
else:
    bin_inst = 1
```

### 9-3. 2단계 — 연도별 누적 노출 지수 S_tc(t, j)

bin별 시점 가중치:

```text
w_tc[1] = 0    # 영향 없음
w_tc[2] = 1    # TS급
w_tc[3] = 3    # STS급
w_tc[4] = 6    # TY급
```

연도 t에 대해:

```text
S_tc(t, j) = Σ_(storm, τ in year t) w_tc[ bin_inst(storm, τ, j) ]
```

- STS급이 오래 지속되면 S_tc가 크게 나옴
- TY 한 번 스치고 끝나면 S_tc가 상대적으로 작게 나옴

### 9-4. 3단계 — S_tc(t, j)를 연도 bin_year(t, j)로 변환

노출 지수 임계값 예시:

```text
s2_tc = 5
s3_tc = 15
```

연도 bin 정의:

```text
if S_tc(t, j) == 0:
    bin_year(t, j) = 1      # 태풍 영향 없음 또는 매우 미미
elif 0 < S_tc(t, j) <= s2_tc:
    bin_year(t, j) = 2      # 약한 노출
elif s2_tc < S_tc(t, j) <= s3_tc:
    bin_year(t, j) = 3      # 중간~강한 노출
else:  # S_tc(t, j) > s3_tc
    bin_year(t, j) = 4      # 매우 강한 노출
```

### 9-5. 4단계 — baseline 발생확률 P_tc_baseline[i, j]

분석 기간 T (예: 1980~2020):

```text
P_tc_baseline[i, j]
  = count{ t in T | bin_year(t, j) = i } / |T|
```

### 9-6. 5단계 — base 손상률 & 취약성 스케일링

bin별 base 손상률 (예시):

```text
DR_tc_int[1] = 0.00   # 영향 없음
DR_tc_int[2] = 0.02   # TS급 → 2%
DR_tc_int[3] = 0.10   # STS급 → 10%
DR_tc_int[4] = 0.30   # TY급 → 30%
```

취약성 계수:

```text
s_min_tc = 0.7
s_max_tc = 1.3

F_vuln_tc(j) = s_min_tc + (s_max_tc - s_min_tc) * V_norm_tc(j)
             = 0.7       + 0.6 * V_norm_tc(j)
```

사이트별 최종 손상률:

```text
DR_tc[i, j] = DR_tc_int[i] * F_vuln_tc(j)
```

### 9-7. 6단계 — baseline AAL_tc_baseline(j)

```text
AAL_tc_baseline(j)
  = Σ_i P_tc_baseline[i, j] * DR_tc[i, j]
```

### 9-8. 7단계 — SSP 시나리오 반영

시나리오별, 기간별 AAL을 단순 스케일링:

```text
γ_tc[scenario, horizon]  # 시나리오·기간별 계수
```

예시(형태만):

```text
γ_tc["SSP126"]["short"] = 1.00
γ_tc["SSP126"]["mid"]   = 1.05
γ_tc["SSP126"]["long"]  = 1.10

γ_tc["SSP585"]["short"] = 1.10
γ_tc["SSP585"]["mid"]   = 1.30
γ_tc["SSP585"]["long"]  = 1.60
```

실제 숫자는 문헌·전문가 판단으로 결정해야 하며, 여기서는 **파라미터**로만 정의.

시나리오별 최종 AAL:

```text
AAL_tc_scenario(j, scenario, horizon)
  = γ_tc[scenario, horizon] * AAL_tc_baseline(j)
```

---

## 10. 요약

- 공통 AAL 프레임:

  ```text
  AAL_r(j) = Σ_i P_r[i] * DR_r[i, j] * (1 - IR_r)
  ```

- v9에서 확정한 핵심 포인트 정리:
  - 극심한 고온: `X_heat(t) = WSDI(t)`
  - 극심한 한파: `X_cold(t) = CSDI(t)`
  - 산불: FWI 식으로 `FWI(t,m)` 계산 후 `X_fire(t,m) = FWI(t,m)`
  - 가뭄: `X_drought(t, m) = SPEI12(t, m)`
  - 내륙 홍수: `X_rflood(t) = RX1DAY(t)`
  - 도시 홍수: `X_pflood(t, j) = k_depth * max(0, R_peak_mmph(t) - drain_capacity_mmph(j))`
  - 해수면 상승: zos 기반
    ```text
    inundation_depth(t, τ, j) = max(zos(t, τ)/100 - ground_level(j), 0)
    X_slr(t, j) = max_τ inundation_depth(t, τ, j)
    ```
  - 물부족: 연 단위 WSI 기반
    ```text
    WSI(t) = Withdrawal(t) / ARWR_future(t)
    ```
  - 태풍: Best Track 기반
    ```text
    S_tc(t, j) = Σ_(storm, τ) w_tc[ bin_inst(storm, τ, j) ]
    bin_year(t, j) from S_tc(t, j)
    ```
