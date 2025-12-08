# Code vs. Methodology (PDF v1.1) Discrepancy Report

**Date:** 2025-12-05  
**Status:** Analysis Complete  
**Scope:** Comparison between `hazard_calculator.py` and `[2조.온도(On-Do)]_231.물리적 리스크 스코어링 로직 정의_v1.1.pdf`

---

## 1. Summary of Critical Methodological Differences

| Risk Type           | Component    | PDF v1.1 Definition                                                       | Current Code Implementation                                             | Impact / Note                                                        |
| :------------------ | :----------- | :------------------------------------------------------------------------ | :---------------------------------------------------------------------- | :------------------------------------------------------------------- |
| **4. Drought**      | Hazard Index | SPEI (Precip + Temp + Evapotranspiration)                                 | SPI (Precipitation only)                                                | **Critical.** Code lacks Evapotranspiration logic required by PDF.   |
| **5. Water Stress** | Data Source  | WRI Aqueduct (Global Baseline Water Stress), Scale: 0-5 (Global Standard) | WAMIS + KMA (Korean Local Data), Local Demand vs. Supply                | **Critical.** Code deviates from PDF's global standard mandate.      |
| **7. River Flood**  | Logic        | Climate Only, RX1DAY (Precipitation)                                      | Compound Risk: Precipitation (0.6) + TWI (0.4)                          | **High.** Code adds terrain analysis (DEM data), not in PDF.         |
| **8. Urban Flood**  | Logic        | Climate Only, RX1DAY (Precipitation)                                      | Capacity Model: Rainfall - Drainage Capacity (Landcover/Imperviousness) | **High.** Code simulates drainage system failure, PDF uses rainfall. |
| **2. Extreme Cold** | Indices      | ID0 (Ice Days, Max Temp < 0°C)                                            | Abs Min Temp (Absolute minimum temperature value)                       | **Medium.** Code substitutes value for frequency count.              |

---

## 2. Detailed Parameter & Numerical Differences

### 2.1. Extreme Heat (HCI)

- Logic: Matches (Weighted Average of 4 Indices).
- Weights: Matches (0.3, 0.3, 0.2, 0.2).
- Normalization Constants:
  - TX90P: Matches (/100).
  - WSDI: Matches (/30).
  - TR25: Matches (/50).
  - SU25: Matches (/100).
- **Verdict:** ✅ MATCH

### 2.2. Extreme Cold (CCI)

- Logic: Weighted Average of 4 Indices.
- Weights: Matches (0.3, 0.3, 0.2, 0.2).
- Indices & Normalization:
  - TN10P: PDF uses /80, Code uses /30.
  - CSDI: Matches (/20).
  - FD0: Matches (/50 in code vs 100 in PDF).
  - ID0 vs AbsMin: PDF uses ID0 / 50, Code uses AbsMinTemp / 20.
- **Verdict:** ⚠️ NUMERICAL MISMATCH

### 2.3. Wildfire (FWI)

- Logic: Matches (Canadian FWI System).
- Normalization:
  - PDF: FWI / 50.
  - Code: FWI / 81.
- **Verdict:** ⚠️ NUMERICAL MISMATCH

### 2.4. Drought (SPI vs SPEI)

- Logic: **MISMATCH**
- Thresholds:
  - PDF: Extreme < -2.4.
  - Code: Extreme < -2.0.
- **Verdict:** ❌ METHOD MISMATCH

### 2.5. Water Stress

- Logic: **MISMATCH**
- Thresholds:
  - PDF: WRI > 80% (Score 5.0).
  - Code: Demand/Supply Ratio > 1.0.
- **Verdict:** ❌ METHOD MISMATCH

### 2.6. Sea Level Rise

- Logic:
  - PDF: Sea Level Anomaly (m).
  - Code: Sea Level Anomaly (m) + Storm Surge estimation.
- Normalization:
  - PDF: 1.0m = 100% Risk.
  - Code: 1.0m = 100% Risk.
- **Verdict:** ⚠️ MINOR LOGIC ADDITION

### 2.7. River Flood

- Logic: **MISMATCH**
- Normalization:
  - PDF: RX1DAY / 300mm.
  - Code: (TWI Score _ 0.4) + (Precip Score _ 0.6), Precip normalized by 300mm.
- **Verdict:** ❌ METHOD MISMATCH

### 2.8. Urban Flood

- Logic: **MISMATCH**
- Normalization:
  - PDF: RX1DAY / 200mm.
  - Code: Drainage Capacity Model.
- **Verdict:** ❌ METHOD MISMATCH

### 2.9. Typhoon (TCI)

- Logic: Matches (Wind + Rain weighted average).
- Weights: Matches (0.55 Wind + 0.45 Rain).
- Normalization:
  - Wind: PDF 40 m/s, Code 50 m/s.
  - Rain: PDF 400 mm, Code 500 mm.
- **Verdict:** ⚠️ NUMERICAL MISMATCH

---

## 3. Exposure (`exposure_calculator.py`) Analysis

The `exposure_calculator.py` script largely aligns with the corrected logic described in `logic_doc_changes.md`. It defines the "what is exposed" component of the risk equation.

| Risk Type              | PDF v1.1 Definition (per `logic_doc_changes.md`)                                    | Current Code Implementation                                                                      | Verdict      |
| :--------------------- | :---------------------------------------------------------------------------------- | :----------------------------------------------------------------------------------------------- | :----------- |
| **Drought**            | Water Dependency (High/Medium/Low based on building use) + Rainfall + Water Storage | Implements this exactly. `_classify_water_dependency` and `_estimate_water_storage` added as per fix. | ✅ MATCH     |
| **Typhoon**            | 4-tiered coastal distance scoring (<5km, 5-20km, 20-50km, >50km)                   | `_calculate_typhoon_distance_score` implements the 4-tiered scoring.                           | ✅ MATCH     |
| **Sea Level Rise**     | Coastal distance scoring (e.g., <100m, <500m, <1000m)                                | `_calculate_coastal_distance_score` implements multi-tiered scoring.                           | ✅ MATCH     |
| **Wildfire**           | Forest proximity scoring (<100m, 100-500m, etc.)                                    | `_calculate_wildfire_exposure_score` implements the tiered distance scoring.                   | ✅ MATCH     |
| **River Flood**        | River proximity scoring (<100m, 100-300m, etc.)                                     | `_calculate_river_flood_exposure_score` implements tiered distance scoring.                    | ✅ MATCH     |
| **Urban Flood**        | Imperviousness based on land use (Commercial, Residential, etc.)                    | `_calculate_urban_flood_exposure_score` uses building type as a proxy for imperviousness.        | ✅ MATCH     |

---

## 4. Vulnerability (`vulnerability_calculator.py`) Analysis

The `vulnerability_calculator.py` script correctly models the structural weakness of an asset, separating it from exposure factors, in alignment with the H-E-V framework fixes in `logic_doc_changes.md`.

| Risk Type              | PDF v1.1 Definition (per `logic_doc_changes.md`)                                    | Current Code Implementation                                                                                               | Verdict      |
| :--------------------- | :---------------------------------------------------------------------------------- | :------------------------------------------------------------------------------------------------------------------------ | :----------- |
| **Drought**            | **Soil Subsidence Risk** (proxied by basement presence) & **Foundation Stability** (age) | `_calculate_drought_vulnerability` correctly uses `has_basement` and `building_age` for scoring, removing water dependency. | ✅ MATCH     |
| **Water Stress**       | **Water Storage Capacity** (Water Tank) & **Pipe Condition** (age)                  | Uses API data for water tank presence with a fallback to legal requirements. Uses age for pipe condition.           | ✅ MATCH     |
| **Sea Level Rise**     | **Elevation (m)** is the primary factor. Low elevation is high vulnerability.       | `_calculate_sea_level_rise_vulnerability` is centered on `elevation_m`, with scores like `+50` for `< 3m`.          | ✅ MATCH     |
| **Wildfire**           | **Fire Resistance** of materials (e.g., Concrete vs. Wood)                          | Scoring reflects high risk for '목조' (wood, +40) and low base risk (30) for concrete.                                 | ✅ MATCH     |
| **Typhoon**            | **Structural Strength** (concrete vs. wood), **age**, and **height**                | Scoring parameters (base 50, wood +30) and factors match the documented corrected values.                                   | ✅ MATCH     |
| **River Flood**        | **First Floor Elevation**, basement, waterproofing (age)                            | Uses `has_piloti` as a proxy for first-floor elevation and includes basement and age factors.                               | ✅ MATCH     |

---

## 5. Recommendations for Refactoring

1. **Structure:** Modular refactoring (`src/core`, `src/data`, etc.) to isolate calculation logic blocks.
2. **Drought:** Refactor to accept Temperature data, preparing for SPEI implementation to match PDF.
3. **Water Stress:** Rename risk calculator to "Local Water Balance" or implement WRI fallback.
4. **Floods:** Document deviation as "Advanced/Local Model" if keeping terrain/drainage logic.
5. **Parameters:** Standardize numerical differences (Typhoon, Cold) to match PDF unless justified.

---

## 6. Overall Conclusion

The analysis of `exposure_calculator.py` and `vulnerability_calculator.py` shows that they are consistent with the methodological corrections outlined in `logic_doc_changes.md` and `code_docx_diff.md`. These files appear to represent the "to-be" state after fixing discrepancies with the original PDF documentation.

- **H-E-V Framework Adherence:** The separation between Exposure (locational/situational factors) and Vulnerability (inherent structural weaknesses) has been correctly implemented, especially for Drought, Water Stress, and Sea Level Rise.
- **Data-driven Logic:** The code has been upgraded to use more sophisticated, data-driven logic (e.g., API data for water tanks, elevation for SLR) instead of relying on simple proxies or hardcoded values.
- **Consistency:** Numerical values and scoring logic largely match the specified values in the analysis documents.

The remaining discrepancies noted in this report primarily concern `hazard_calculator.py` or older components like `risk_calculator.py`. The `exposure` and `vulnerability` components are up-to-date.

---

## 7. 하드코딩 및 임시 구현 분석 (Hardcoding and Temporary Implementation Analysis)

코드 전반에 걸쳐 `fallback` 로직을 제외하고 실제 데이터가 아닌 하드코딩된 값, 임시 추정치, 또는 전국 평균값 등이 사용되는 부분을 분석했습니다.

### 7.1. `exposure_calculator.py`

데이터 부재 시의 기본값 처리 및 아직 실제 데이터가 연동되지 않은 지표에 대한 임시 구현이 다수 존재합니다.

- **기본값 (Default Values):** `_structure_exposure_data` 함수에서 `raw_data.get(key, default_value)` 형태로 거의 모든 지표(고도, 층수, 건축연도, 하천/해안 거리 등)에 하드코딩된 기본값을 사용합니다. 데이터 조회 실패 시 이 값들이 분석에 직접 사용됩니다.
- **규칙 기반 추정 (Rule-based Estimations):**
  - **녹지 근접도 (`_estimate_green_space_proximity`):** 실제 공간 데이터 대신 토지 이용 종류로 추정합니다.
  - **건물 방향 (`_estimate_building_orientation`):** 위도(latitude) 값으로 일괄 추정합니다.
  - **산림 거리 (`_calculate_forest_distance`):** 토지 이용 종류로 추정합니다.
  - **경사도 (`_calculate_slope_from_dem`):** 고도(elevation) 값으로 추정합니다.
  - **배수 용량 (`_estimate_drainage_capacity`):** 건물 연식으로 추정합니다.
  
### 7.2. `vulnerability_calculator.py`

모든 취약성 평가 로직이 임의의 '기본 점수(base score)'에서 시작하여 일관성이 부족할 수 있습니다.

- **기본 점수 (Base Scores):** 모든 `_calculate_*_vulnerability` 함수가 `score = 50`, `score = 40` 등 과학적 근거가 명확하지 않은 고정된 값에서 계산을 시작합니다.

### 7.3. `hazard_calculator.py`

데이터 로더 의존도가 높지만, 핵심 로직에서 여전히 하드코딩된 통계치나 추정 공식을 사용합니다.

- **가뭄 (Drought):** SPI 지수 계산 시, 지역별 과거 데이터가 아닌 **전국 평균 강수량(1200mm) 및 표준편차(250mm)를 하드코딩**하여 사용합니다.
- **하천 홍수 (River Flood):** TWI(지형 습윤 지수)를 DEM 데이터로부터 직접 계산하는 대신, **토지피복도에 따른 경험적 추정치**를 사용합니다.
- **도시 홍수 (Urban Flood):** 배수 용량을 실제 데이터 없이, **불투수율/건물밀도에 따른 규칙 기반의 하드코딩된 값**으로 계산합니다.
- **태풍 (Typhoon):**
  - 분석 기간이 **최근 5년으로 고정**되어 있습니다.
  - **강풍 반경(`gale_radius`)이 200km로 하드코딩**되어 있습니다.
  - SSP 강수량 데이터가 없을 경우, **태풍 등급에 따른 강수량 추정치**를 사용합니다.
- **산불 (Wildfire):**
  - **평균 풍속이 2.5m/s로 하드코딩**되어 있습니다.
  - 상대 습도를 **연 강수량을 이용한 단순 공식으로 추정**합니다.
  - 최종 위험 지수 계산 시 **토지피복도에 따른 고정 가중치**를 적용합니다.
