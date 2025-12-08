<img src="https://r2cdn.perplexity.ai/pplx-full-logo-primary-dark%402x.png" style="height:64px;margin-right:32px"/>

# 태풍 리스크 평가 최종 정리본

## 1. 전체 계산 로직

### 1.1 기본 수식

\$ R_{typhoon} = H \times E \times V \$

- **R**: 태풍 리스크 점수 (무차원, 0~1) 또는 예상 손실액 (원)
- **H**: Hazard (위험도) - SSP 시나리오 기반 극한 풍속 증가율
- **E**: Exposure (노출도) - 사업장 자산가치
- **V**: Vulnerability (취약도) - 풍속에 따른 피해율

***

## 2. Hazard (H) 계산

### 2.1 계산 수식

### 2.1 계산 수식

$$
\text{위해성} = (0.4 \times \text{풍속}) + (0.4 \times \text{강수량}) + (0.2 \times \text{영향일수})
$$

- $V_{95p,future}$: 미래 기간(2081-2100) 일평균 풍속의 95th percentile (m/s)
- $V_{95p,baseline}$: 기준 기간(1995-2014) 일평균 풍속의 95th percentile (m/s)


### 2.2 계산 절차

### 2.2 계산 절차

1.  **SSP 시나리오 데이터 로드**:
    *   입력: 사업장 위도/경도, SSP 시나리오, 목표 연도
    *   데이터: SSP 일평균 풍속, 일 강수량 (NetCDF)
2.  **기준 기간 (Baseline, 1995-2014) 지표 산출**:
    *   **극한 풍속**: 일평균 풍속의 95th percentile
    *   **극한 강수량**: 일평균 강수량의 95th percentile
    *   **영향일수**: 일평균 풍속 10m/s 이상 또는 일 강수량 50mm 이상인 날의 연평균 일수
3.  **미래 기간 (Target Year ±10년) 지표 산출**:
    *   **극한 풍속**: 미래 기간 일평균 풍속의 95th percentile
    *   **극한 강수량**: 미래 기간 일평균 강수량의 95th percentile
    *   **영향일수**: 미래 기간 일평균 풍속 10m/s 이상 또는 일 강수량 50mm 이상인 날의 연평균 일수
4.  **TCI 요소별 변화율 계산**:
    *   **풍속 변화율**: (미래 극한 풍속 - 기준 극한 풍속) / 기준 극한 풍속
    *   **강수량 변화율**: (미래 극한 강수량 - 기준 극한 강수량) / 기준 강수량
    *   **영향일수 변화율**: (미래 영향일수 - 기준 영향일수) / 기준 영향일수
5.  **위해성(Hazard) 점수 산출**:
    *   H = (0.4 × 풍속 변화율) + (0.4 × 강수량 변화율) + (0.2 × 영향일수 변화율)


### 2.3 필요 데이터

| 데이터명 | 출처 | 형식 | 획득 방법 |
| :-- | :-- | :-- | :-- |
| SSP 일평균 풍속 | 기상청 기후정보포털 | NetCDF | API 다운로드 |
| SSP 일 강수량 | 기상청 기후정보포털 | NetCDF | API 다운로드 |

### 2.4 학술적 근거

- **IPCC AR6 WG1 (2021)**: 극한 풍속 및 강수량 증가 전망.
- **WMO Guidelines**: 태풍 영향 강도 및 빈도 분석 표준.
- **한국 태풍 연구 (2020)**: 한반도 극한 풍속/강수량 증가 경향 분석.

***

## 3. Exposure (E) 계산

### 3.1 계산 수식

$$
E = \text{사업장 자산가치} \times \text{위치별 노출 계수}
$$

### 3.2 계산 절차

1.  **사업장 자산가치 산출**:
    *   DART 재무제표의 유형자산 중 '토지' 및 '건물' 항목 사용.
    *   또는 건축물대장 기반 재건축가 추정.
2.  **사업장 위치 데이터 확보**: 위도, 경도
3.  **노출 여부 판단**:
    *   사업장이 해안선에서 5km 이내에 위치하거나, 해발고도가 10m 미만인 경우 노출 계수 = 1 (노출).
    *   그 외 노출 계수 = 0.5 (부분 노출).
    *   노출 계수는 재해 유형 및 지역 특성에 따라 조정될 수 있음.
4.  **Exposure 점수 산출**:
    *   E = 사업장 자산가치 × 위치별 노출 계수


### 3.3 필요 데이터

| 데이터명 | 출처 | 형식 | 획득 방법 |
| :-- | :-- | :-- | :-- |
| 사업장 자산가치 | DART 전자공시 | PDF/HTML/Excel | 재무제표의 유형자산 등 |
| 해안선 벡터 | 해양수산부/OSM | Shapefile | 해양공간포털 또는 OpenStreetMap |
| DEM (수치표고) | 국토정보원 | GeoTIFF | https://map.ngii.go.kr |

### 3.4 학술적 근거

- **TCFD 권고안**: 물리적 자산 노출도는 재무제표 장부가액 또는 재건축가 사용.
- **CLIMADA 모델**: 자산 노출 시 건물 유형, 용도, 층수 등 세부 정보 활용.
- **국토교통부 (2020)**: 해안 지역 시설물 노출도 평가 가이드라인.

***

## 4. Vulnerability (V) 계산

### 4.1 계산 수식

$$
V = \text{사업장 자산가치}
$$

### 4.2 계산 절차

1.  **사업장 위치에서 풍속 데이터 추출**:
    *   입력: 사업장 위도/경도
    *   데이터: SSP 일평균 풍속 NetCDF
2.  **노출 여부 판단**:
    *   사업장이 해안선에서 5km 이내에 위치하거나, 해발고도가 10m 미만인 경우 노출 계수 = 1 (노출).
    *   그 외 노출 계수 = 0.5 (부분 노출).
    *   노출 계수는 재해 유형 및 지역 특성에 따라 조정될 수 있음.
3.  **노출 자산가치 산출**:
    *   Exposure = 사업장 자산가치 (재무제표 또는 추정액)


### 4.3 필요 데이터

| 데이터명 | 출처 | 형식 | 획득 방법 |
| :-- | :-- | :-- | :-- |
| 사업장 위치 (위경도) | 건축물대장 API | JSON | `lat`, `lon` |
| 해안선 벡터 | 해양수산부/OSM | Shapefile | 해양공간포털 또는 OpenStreetMap |
| DEM (수치표고) | 국토정보원 | GeoTIFF | `elevation_m` |

### 4.4 학술적 근거

- **FEMA Flood Damage Estimation (2018)**: 강풍 및 해일에 따른 건물 손상 평가.
- **CLIMADA 모델**: 자산 노출 시 건물 유형, 용도, 층수 등 세부 정보 활용.
- **국토교통부 (2020)**: 해안 지역 시설물 노출도 평가 가이드라인.

***

## 5. 통합 리스크 계산

### 5.1 최종 수식

$$
\text{태풍 리스크} = \text{위해성} \times \text{노출 계수} \times \text{취약성 계수}
$$

### 5.2 시나리오별 결과 예시

**가정**:

- 기준 시나리오: SSP5-8.5 (2050년)
- 사업장 자산가치: 500억 원

| 지표 | 값 |
| :-- | :-- |
| 위해성 (Hazard) | 0.8 (평균 TCI 점수) |
| 노출 계수 (Exposure) | 0.5 (부분 노출) |
| 취약성 계수 (Vulnerability) | 0.7 (중간 취약) |

**계산**:

$$
\text{태풍 리스크} = 0.8 \times 0.5 \times 0.7 = 0.28
$$

**해석**:

- 태풍 리스크 점수: 0.28 (최대 1.0)
- 예상 손실액: 500억 원 × 0.28 = 140억 원

***

## 6. 데이터 최종 정리

### 6.1 필수 데이터 체크리스트

| 구성요소 | 데이터 | 출처 | 가용 여부 | 비고 |
| :-- | :-- | :-- | :-- | :-- |
| **H** | SSP 일평균 풍속 (미래) | 기상청 | ✅ 보유 | NetCDF/CSV |
| **H (현재)** | 태풍 베스트트랙 (현재) | 기상청 | ✅ 구현완료 | API/JSON |
| **E** | 사업장 자산가치 | DART | ✅ 확보 가능 | 재무제표 |
| **E** | 해안선 벡터 | 해양수산부/OSM | ✅ 확보 가능 | Shapefile |
| **E** | DEM (수치표고) | 국토정보원 | ✅ 확보 가능 | GeoTIFF |
| **V** | 사업장 위치 (위경도) | 건축물대장 API | ✅ 확보 가능 | `lat`, `lon` |
| **V** | 해안선 벡터 | 해양수산부/OSM | ✅ 확보 가능 | Shapefile |
| **V** | DEM (수치표고) | 국토정보원 | ✅ 확보 가능 | GeoTIFF |

***

## 7. 학술적 근거 종합

### 7.1 국제 프레임워크

| 프레임워크 | 적용 부분 | 근거 |
| :-- | :-- | :-- |
| **IPCC AR6 WGII** | Risk = H × E × V | 물리적 리스크 평가 표준[^16] |
| **TCFD** | 시나리오 기반 정량화 | 기후 재무공시 권고안[^4][^9] |
| **S\&P Global** | 백분위수 극한 지수 | Physical Risk Methodology[^4] |
| **CLIMADA** | Damage Function 구조 | 글로벌 태풍 모델 표준[^14] |

### 7.2 한국 실증 연구

| 연구 | 연도 | 주요 내용 | 적용 부분 |
| :-- | :-- | :-- | :-- |
| 태풍 매미 취약성 분석[^10] | 2020 | 실제 보험 피해액 기반 Damage Function | V 계산 |
| 한반도 태풍 리스크[^17] | 2017 | 태풍 경로별 리스크 차이 분석 | H 개념 |
| SSP 극한기후 전망[^18] | 2021 | 한국 SSP 시나리오 극한풍속 지수 | H 변화율 |

### 7.3 국제 기술 표준

| 표준 | 적용 부분 | 근거 |
| :-- | :-- | :-- |
| **WMO Guidelines** | 일평균→일최대 변환 (k=1.7) | 기상 관측 표준[^11][^12] |
| **Extreme Value Theory** | 95th percentile 방법 | 극한값 통계 이론[^1][^3] |
| **IFRS/K-IFRS** | 유형자산 평가 | 회계 기준[^6][^7] |


***

## 8. 한계 및 불확실성

### 8.1 방법론적 한계

1. **일평균 풍속 활용**: 일최대 풍속 없이 변환계수(1.7) 사용으로 인한 추정 오차 ±10~15%
2. **공간 해상도**: SSP 시나리오 격자 해상도(1km)로 인한 미세 지형 효과 미반영
3. **단순화 Damage Function**: 건물 구조, 건축연도, 유지보수 상태 등 세부 요인 미반영

### 8.2 데이터 불확실성

1. **SSP 시나리오 불확실성**: 미래 온실가스 배출 경로에 따른 예측 편차
2. **자산가치 변동**: DART 장부가액과 실제 재건축가 차이 (일반적으로 장부가액이 낮음)
3. **태풍 빈도 미반영**: 현재 방법론은 강도만 평가, 태풍 발생 빈도 변화는 고려 안 함

### 8.3 보완 방안

1. **민감도 분석**: 변환계수 k를 1.5~2.0 범위에서 변화시켜 결과 범위 제시
2. **다중 시나리오**: SSP1-2.6, SSP2-4.5, SSP5-8.5 모두 계산하여 범위 제공
3. **정기 업데이트**: 최신 재무제표 및 SSP 시나리오 업데이트 시 재계산

### 8.4 기상청 태풍 베스트트랙 API 통합 (2025-12-03 구현완료)

#### 개요

기존의 SSP 시나리오 기반 **미래 위험도** 평가에 더해, **과거 태풍 실제 데이터**를 기반한 **현재 위험도** 평가 메커니즘이 추가되었습니다.

#### 데이터 소스

- **기관**: 기상청 (Korean Meteorological Administration)
- **API**: 태풍 베스트트랙 API (Typhoon BestTrack API)
- **엔드포인트**: `https://apihub.kma.go.kr/api/typ01/url/typ_besttrack.php`
- **데이터 기간**: 2015-2022년
- **인증**: API Key (환경변수 `KMA_API_KEY` 사용)
- **제공 정보**: 태풍 등급, 호수, 시간, 위치(경도/위도), 중심최대풍속, 중심기압, 영향 반경

#### 계산 방법

```python
1. 과거 5년 데이터 수집 (2018-2022)
   → 모든 태풍의 경로 및 강도 정보 획득

2. 위치별 태풍 영향도 계산
   → Haversine 공식: 태풍 중심까지의 거리 계산
   → 강풍 반경(~200km) 내 영향도 평가
   → 거리에 따른 지수감소 적용: impact = (1 - distance/200) × (wind_speed/50)

3. 통계 지표 산출
   - annual_typhoon_frequency: 연평균 태풍 영향 빈도 (회/년)
   - max_wind_speed_kmh: 영향받은 태풍의 최대 풍속 (km/h)
   - typhoon_intensity: 강도 분류 (weak/moderate/strong/very_strong)
   - track_probability: 영향 확률 (0-1)
   - historical_typhoon_count: 과거 5년 영향 태풍 수 (개)
```

#### 구현 위치

**파일**: `Physical_RISK_calculate/code/hazard_calculator.py`

**메서드**:
- `_fetch_typhoon_besttrack(year)`: API 호출 및 데이터 파싱
- `_calculate_typhoon_impact(lat, lon, typhoon_data)`: 위치별 영향도 계산
- `_calculate_typhoon_hazard(lat, lon, data)`: 통합 태풍 위험도 산출

#### 예시 결과

위치: 서울 강남구 (37.4979°N, 127.0276°E)
분석 기간: 2018-2022

```
Data Source: kma_besttrack (실제 데이터)
연평균 태풍 빈도: 2.80회/년
최대 풍속: 133 km/h
태풍 강도: moderate
영향 확률: 0.064 (6.4%)
영향받은 태풍 수: 14개
```

#### 신뢰도 및 한계

**장점**:
- ✅ 공식 기상청 데이터 기반
- ✅ 실제 지역별 태풍 영향도 검증 가능
- ✅ 과거 5년 통계에 기반한 객관적 평가
- ✅ API 실패 시 안전한 Fallback 제공

**한계**:
- 데이터 보유 기간이 2015-2022년으로 제한
- 2023년 이후 데이터는 2024년 7월 이후 이용 가능
- 과거 5년 데이터에 기반하므로 장기 추세 반영 제한

#### SSP 시나리오와의 관계

| 구분 | SSP 시나리오 | 태풍 BestTrack API |
|------|------------|------------------|
| **시간 지평** | 미래 (2081-2100) | 현재/과거 (2018-2022) |
| **목적** | 미래 태풍 강도 변화 예측 | 현재 지역별 태풍 위험도 평가 |
| **사용 지표** | 풍속 증가율 (%) | 태풍 발생 빈도, 최대 풍속, 영향 확률 |
| **결합 활용** | H_future = 미래 시나리오 × 현재 기준값 | baseline으로 활용 |

***

## 9. TCFD 공시 활용 가이드

### 9.1 공시 서술 예시

> "당사는 IPCC AR6 및 TCFD 권고안에 따라 태풍 물리적 리스크를 정량 평가하였습니다. 기상청 SSP 시나리오(SSP5-8.5)에 기반한 분석 결과, 2081-2100년 극한 풍속이 29% 증가하며, 주요 사업장에서 약 XX억 원의 자산 손실이 예상됩니다. 평가 방법론은 국제 학술 문헌 및 한국 태풍 실증 연구에 기반하였으며, 데이터는 모두 공개/공공 출처를 활용하였습니다."

### 9.2 필수 공시 항목

1. **시나리오**: SSP1-2.6, SSP2-4.5, SSP5-8.5 각각의 결과
2. **시간 지평**: 2030년, 2050년, 2100년 각 시점 리스크
3. **금액**: 예상 손실액 (원) 및 자산 대비 비율 (%)
4. **방법론**: 사용한 수식 및 근거 문헌 명시
5. **데이터 출처**: 기상청, DART, 학술 논문 등 출처 명확히 기재

***

이 방법론은 **복잡한 모델링 없이 공개 데이터만으로 TCFD 공시 기준에 부합하는 정량적 태풍 리스크 평가**를 가능하게 합니다.[^1][^4][^9][^10][^11][^14]
<span style="display:none">[^19][^20][^21][^22][^23][^24][^25]</span>

<div align="center">⁂</div>

[^1]: https://www.itl.nist.gov/div898/winds/overview.htm

[^2]: https://arxiv.org/html/2505.24463v1

[^3]: https://pmc.ncbi.nlm.nih.gov/articles/PMC8345286/

[^4]: https://portal.s1.spglobal.com/survey/documents/SPG_S1_Physical_Risk_Methodology.pdf

[^5]: https://www.osfi-bsif.gc.ca/en/data-forms/reporting-returns/standardized-climate-scenario-exercise

[^6]: https://www.mk.co.kr/news/economy/10332791

[^7]: https://corporatefinanceinstitute.com/resources/accounting/ppe-property-plant-equipment/

[^8]: https://www.assetcues.com/glossary/property-plant-and-equipment-ppe/

[^9]: https://www.ngfs.net/system/files/import/ngfs/media/2022/09/02/ngfs_physical_climate_risk_assessment.pdf

[^10]: https://downloads.hindawi.com/journals/ace/2020/8885916.pdf

[^11]: http://www.systemsengineeringaustralia.com.au/download/WMO_TC_Wind_Averaging_27_Aug_2010.pdf

[^12]: http://geofizika-journal.gfz.hr/vol_20/gf20-cvitan.pdf

[^13]: https://onlinelibrary.wiley.com/doi/10.1155/2020/8885916

[^14]: https://nhess.copernicus.org/preprints/nhess-2020-229/nhess-2020-229-manuscript-version4.pdf

[^15]: https://docs.air-worldwide.com/releaseReadiness/releaseNotes_13-0/ts-tsre_all/releaseReadiness_13-0_m_ko-ty.html

[^16]: https://www.ipcc.ch/site/assets/uploads/2018/03/SREX-Chap2_FINAL-1.pdf

[^17]: https://nhess.copernicus.org/articles/18/3225/2018/

[^18]: http://iwork.konkuk.ac.kr/site/kucri/doc/article/17-2_2.pdf

[^19]: https://blog.naver.com/chief_cho/223308972502

[^20]: https://dart.fss.or.kr

[^21]: https://blog.naver.com/cavare1/222397210272

[^22]: https://dart.fss.or.kr/dsab007/main.do

[^23]: https://opendart.fss.or.kr/disclosureinfo/fnltt/singl/main.do

[^24]: https://opendart.fss.or.kr/disclosureinfo/fnltt/cmpnyacnt/main.do

[^25]: https://blog.naver.com/rnjsdntjr26/221763008266

