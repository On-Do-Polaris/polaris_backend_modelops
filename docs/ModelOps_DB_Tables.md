# ModelOps Results Database Structure

**버전**: v07 (SSP 시나리오 및 연도별 데이터 지원)
**작성일**: 2025-12-13

---

## 📋 테이블 구조 (DBML 형식)

### 1. `hazard_results` - Hazard Score (H)

```dbml
Table hazard_results {
  id serial [pk, increment, note: '고유 ID']
  latitude decimal(9,6) [not null, note: '격자 위도']
  longitude decimal(9,6) [not null, note: '격자 경도']
  risk_type varchar(50) [not null, note: '위험 유형 (9가지)']
  target_year integer [not null, note: '목표 연도 (2021~2050)']

  ssp126_score_100 real [note: 'SSP1-2.6 위험도 (0~100)']
  ssp245_score_100 real [note: 'SSP2-4.5 위험도 (0~100)']
  ssp370_score_100 real [note: 'SSP3-7.0 위험도 (0~100)']
  ssp585_score_100 real [note: 'SSP5-8.5 위험도 (0~100)']

  Note: '''
    격자별 Hazard 점수 (4개 시나리오, 연도별)
    예상 행 수: 451,351 grids × 9 types × 80 years = 약 3,251만 rows
  '''

  indexes {
    (latitude, longitude, risk_type, target_year) [unique]
    risk_type
    target_year
    (latitude, longitude)
  }
}
```

---

### 2. `probability_results` - Probability & AAL (P(H))

```dbml
Table probability_results {
  id serial [pk, increment, note: '고유 ID']
  latitude decimal(9,6) [not null, note: '격자 위도']
  longitude decimal(9,6) [not null, note: '격자 경도']
  risk_type varchar(50) [not null, note: '위험 유형 (9가지)']
  target_year integer [not null, note: '목표 연도 (2021~2100)']

  ssp126_base_aal real [note: 'SSP1-2.6 기본 AAL']
  ssp245_base_aal real [note: 'SSP2-4.5 기본 AAL']
  ssp370_base_aal real [note: 'SSP3-7.0 기본 AAL']
  ssp585_aal real [note: 'SSP5-8.5 연간 평균 손실률 (0.0~1.0)']

  damage_rates jsonb [note: 'Bin별 적용 손상률 (예: [0.0, 0.02, 0.07, 0.20])']

  ssp126_bin_probs jsonb [note: 'SSP1-2.6 bin별 확률 [0.65, 0.25, 0.08, 0.015, 0.005]']
  ssp245_bin_probs jsonb [note: 'SSP2-4.5 bin별 확률']
  ssp370_bin_probs jsonb [note: 'SSP3-7.0 bin별 확률']
  ssp585_bin_probs jsonb [note: 'SSP5-8.5 bin별 확률']

  Note: '''
    격자별 확률 및 AAL (4개 시나리오, 연도별)
    예상 행 수: 451,351 grids × 9 types × 80 years = 약 3,251만 rows
  '''

  indexes {
    (latitude, longitude, risk_type, target_year) [unique]
    risk_type
    target_year
    (latitude, longitude)
  }
}
```

---

### 3. `exposure_results` - Exposure Score (E)

```dbml
Table exposure_results {
  id serial [pk, increment, note: '고유 ID']
  site_id uuid [not null, note: 'Application DB sites.id 참조']
  latitude decimal(9,6) [not null, note: '격자 위도']
  longitude decimal(9,6) [not null, note: '격자 경도']
  risk_type varchar(50) [not null, note: '위험 유형 (9가지)']
  target_year integer [not null, note: '목표 연도 (2021~2100)']

  exposure_score real [not null, note: '노출도 점수 (0.0~1.0)']
  proximity_factor real [note: '근접도 계수']
  normalized_asset_value real [note: '정규화 자산가치']

  Note: '''
    Site별 Exposure 점수 (시나리오 독립적, 연도별)
    예상 행 수: 실제 site 분석 시 생성
  '''

  indexes {
    (site_id, risk_type, target_year) [unique]
    site_id
    risk_type
    target_year
    (latitude, longitude)
    exposure_score
  }
}
```

---

### 4. `vulnerability_results` - Vulnerability Score (V)

```dbml
Table vulnerability_results {
  id serial [pk, increment, note: '고유 ID']
  site_id uuid [not null, note: 'Application DB sites.id 참조']
  latitude decimal(9,6) [not null, note: '격자 위도']
  longitude decimal(9,6) [not null, note: '격자 경도']
  risk_type varchar(50) [not null, note: '위험 유형 (9가지)']
  target_year integer [not null, note: '목표 연도 (2021~2100)']

  vulnerability_score real [not null, note: '취약성 점수 (0~100)']
  factors jsonb [note: '취약성 요인 상세 (건물 연식, 구조 등)']

  Note: '''
    Site별 Vulnerability 점수 (시나리오 독립적, 연도별)
    예상 행 수: 실제 site 분석 시 생성
    factors 예시: {"building_age": 25, "structure_type": "철근콘크리트", "seismic_design": false}
  '''

  indexes {
    (site_id, risk_type, target_year) [unique]
    site_id
    risk_type
    target_year
    (latitude, longitude)
    vulnerability_level
    vulnerability_score
  }
}
```

---

### 5. `aal_scaled_results` - AAL Scaled with Vulnerability

```dbml
Table aal_scaled_results {
  id serial [pk, increment, note: '고유 ID']
  site_id uuid [not null, note: 'Application DB sites.id 참조']
  latitude decimal(9,6) [not null, note: '격자 위도']
  longitude decimal(9,6) [not null, note: '격자 경도']
  risk_type varchar(50) [not null, note: '위험 유형 (9가지)']
  target_year integer [not null, note: '목표 연도 (2021~2100)']

  vulnerability_scale real [not null, note: 'F_vuln 계수 (0.9~1.1)']

  ssp126_final_aal real [note: 'SSP1-2.6 최종 AAL']
  ssp245_final_aal real [note: 'SSP2-4.5 최종 AAL']
  ssp370_final_aal real [note: 'SSP3-7.0 최종 AAL']
  ssp585_final_aal real [note: 'SSP5-8.5 최종 AAL']

  Note: '''
    Site별 Vulnerability 반영 최종 AAL (4개 시나리오, 연도별)
    예상 행 수: 실제 site 분석 시 생성
    공식: final_aal = base_aal × F_vuln × (1 - insurance_rate)
    예상 손실액(expected_loss) = final_aal × 자산가치(asset_value)
  '''

  indexes {
    (site_id, risk_type, target_year) [unique]
    site_id
    risk_type
    target_year
    (latitude, longitude)
  }
}
```

---

### 7. `site_risk_summary` - Site별 리스크 요약

```dbml
Table site_risk_summary {
  id serial [pk, increment, note: '고유 ID']
  site_id uuid [not null, note: 'Application DB sites.id 참조']
  scenario varchar(10) [not null, note: 'SSP 시나리오 (SSP126/SSP245/SSP370/SSP585)']
  target_year integer [not null, note: '목표 연도 (2021~2100)']

  total_physical_risk_score real [note: '9개 리스크 타입 평균']
  total_aal_percentage real [note: '9개 리스크 타입 AAL 합계 (%)']
  total_combined_score real [note: '9개 리스크 타입 통합 점수 평균']

  highest_risk_type varchar(50) [note: '가장 높은 리스크 타입']
  highest_risk_score real [note: '가장 높은 리스크 점수']

  overall_risk_grade varchar(20) [note: '전체 등급 (A/B/C/D/F)']

  Note: '''
    Site별 9개 리스크 타입 통합 요약 (시나리오별, 연도별)
    예상 행 수: 1,000 sites × 4 scenarios × 80 years = 약 32만 rows
  '''

  indexes {
    (site_id, scenario, target_year) [unique]
    site_id
    scenario
    target_year
    overall_risk_grade
    total_combined_score
  }
}
```

---

## 📊 데이터 크기 요약

| 테이블명 | 총 행 수 | 비고 |
|---------|---------|------|
| `hazard_results` | **약 3,251만 rows** | 451K grids × 9 types × 80 years |
| `probability_results` | **약 3,251만 rows** | 451K grids × 9 types × 80 years |
| `exposure_results` | **수십만 rows** | 실제 site 분석 시 생성 (1,000 sites × 9 types × 80 years = 72만) |
| `vulnerability_results` | **수십만 rows** | 실제 site 분석 시 생성 (1,000 sites × 9 types × 80 years = 72만) |
| `aal_scaled_results` | **수십만 rows** | 실제 site 분석 시 생성 (1,000 sites × 9 types × 80 years = 72만) |
| `site_risk_results` | **약 72만 rows** | 1,000 sites × 9 types × 80 years |
| `site_risk_summary` | **약 8만 rows** | 1,000 sites × 80 years |

---

## 🔑 핵심 설계 원칙

1. **시나리오를 컬럼으로 분리** → 4개 시나리오(`ssp126`, `ssp245`, `ssp370`, `ssp585`)를 각각 컬럼으로 저장
2. **연도는 행으로 분리** → 2021~2100년(80개)을 각각 행으로 저장
3. **행 개수 최소화** → 1.3억 rows → **3,251만 rows** (4배 감소)
4. **site_id 필수화** → E, V, AAL Scaled 테이블은 site_id를 PK에 포함
5. **JSONB 최소화** → bin_probabilities, factors만 JSONB 사용, 나머지는 표준 컬럼
6. **쿼리 단순화** → 표준 SQL만 사용, 복잡한 파싱 불필요
7. **시나리오 비교 용이** → 같은 행에 4개 시나리오 값 모두 존재

---

## 📝 9가지 리스크 타입

1. `extreme_heat` - 극한 폭염
2. `extreme_cold` - 극한 한파
3. `wildfire` - 산불
4. `drought` - 가뭄
5. `water_stress` - 물 부족
6. `sea_level_rise` - 해수면 상승
7. `river_flood` - 하천 홍수
8. `urban_flood` - 도시 침수
9. `typhoon` - 태풍

---

## 📝 SSP 시나리오 정의

- **SSP126 (SSP1-2.6)**: 지속가능 발전 경로, 온도 상승 1.5°C 제한 목표
- **SSP245 (SSP2-4.5)**: 중간 경로 (기본 시나리오)
- **SSP370 (SSP3-7.0)**: 지역 경쟁 경로
- **SSP585 (SSP5-8.5)**: 화석연료 집약 경로, 최악 시나리오

---

**문서 종료**
