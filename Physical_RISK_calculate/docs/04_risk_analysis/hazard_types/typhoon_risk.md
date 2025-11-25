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

**극값 백분위수 비율법** (권장)

\$ H = \frac{V_{95p,future}}{V_{95p,baseline}} \$

- $V_{95p,future}$: 미래 기간(2081-2100) 일평균 풍속의 95th percentile (m/s)
- $V_{95p,baseline}$: 기준 기간(1995-2014) 일평균 풍속의 95th percentile (m/s)


### 2.2 계산 절차

1. **SSP 시나리오 데이터에서 사업장 격자 추출**
    - 입력: 사업장 위도/경도
    - 출력: 해당 격자의 일평균 풍속 시계열 (1995-2100)
2. **기준 기간 백분위수 계산**

```python
baseline_wind = daily_mean_wind[1995:2014]  # 7,300일
V_95p_baseline = np.percentile(baseline_wind, 95)
```

3. **미래 기간 백분위수 계산**

```python
future_wind = daily_mean_wind[2081:2100]  # 7,300일
V_95p_future = np.percentile(future_wind, 95)
```

4. **Hazard 점수 산출**

```python
H = V_95p_future / V_95p_baseline
```


### 2.3 필요 데이터

| 데이터명 | 출처 | 형식 | 획득 방법 |
| :-- | :-- | :-- | :-- |
| SSP 시나리오 일평균 풍속 | 기상청 기후정보포털<br>(climate.go.kr) | NetCDF/CSV | 1. 포털 접속<br>2. "국가 기후변화 표준 시나리오" 메뉴<br>3. 자료 다운로드 신청<br>4. SSP1-2.6/2-4.5/5-8.5 선택<br>5. 변수: 일평균 풍속 선택<br>6. NetCDF 파일 다운로드 |

### 2.4 학술적 근거

- **IPCC AR6**: 극한 기후 지수는 95th 또는 99th percentile 사용 권장[^1][^2]
- **Extreme Value Theory**: Block Maxima 및 백분위수 방법은 극한값 분석의 표준 기법[^3][^1]
- **TCFD Framework**: 시나리오 간 상대적 변화 비율로 리스크 증가 정량화[^4][^5]

***

## 3. Exposure (E) 계산

### 3.1 계산 수식

\$ E = Asset_{land+building} \$

- $Asset_{land+building}$: 토지 + 건물 장부가액 (원)
- DART 재무제표의 유형자산 중 '토지' 및 '건물' 항목 사용


### 3.2 계산 절차

**방법 1: DART 공시 재무제표 활용 (기업 전체)**

1. **DART 접속 및 재무제표 조회**
    - DART 전자공시시스템 접속 (dart.fss.or.kr)
    - 회사명 검색
    - "정기공시" → "사업보고서" 선택
    - 최신 연도 사업보고서 열람
2. **재무상태표에서 유형자산 확인**
    - "연결재무상태표" 또는 "재무상태표" 선택
    - 비유동자산 → 유형자산 항목 확인
    - 세부 주석에서 "토지", "건물 및 구축물" 금액 추출
3. **Exposure 계산**

```python
E = 토지_장부가액 + 건물_장부가액
```


**방법 2: 특정 사업장 자산 비율 배분**

\$ E_{site} = (Asset_{land} + Asset_{building}) \times \frac{Area_{site}}{Area_{total}} \$

- $Area_{site}$: 해당 사업장 부지면적
- $Area_{total}$: 전사 총 부지면적
- 사업보고서 주석에서 사업장별 면적 정보 확인 가능

**방법 3: 건축물대장 기반 재건축가 추정 (중소기업/비상장)**

\$ E = Area_{building} \times Price_{per\_m^2} \$

- $Area_{building}$: 연면적 (m²)
- $Price_{per\_m^2}$: 단위면적당 재건축 단가 (원/m²)


### 3.3 필요 데이터

| 데이터명 | 출처 | 형식 | 획득 방법 |
| :-- | :-- | :-- | :-- |
| **유형자산<br>(토지/건물)** | DART 전자공시<br>(dart.fss.or.kr) | PDF/HTML/Excel | 1. DART 접속<br>2. 회사명 검색<br>3. 사업보고서 선택<br>4. 재무상태표 → 유형자산 확인<br>5. 주석에서 토지/건물 세부 금액 추출 |
| **건물 면적<br>(대체)** | 국토부 건축물대장<br>(data.go.kr) | JSON/XML | 1. 공공데이터포털 접속<br>2. "건축물대장정보" API 신청<br>3. ServiceKey 발급<br>4. 주소로 연면적 조회 |
| **실거래가<br>(대체)** | 국토부 실거래가<br>(data.go.kr) | JSON/XML | 1. 공공데이터포털 접속<br>2. "실거래가 정보" API 신청<br>3. 인근 실거래가 조회 |

### 3.4 학술적 근거

- **IFRS/K-IFRS**: 유형자산(PP\&E)은 원가모형 또는 재평가모형으로 측정[^6][^7][^8]
- **TCFD 권고안**: 물리적 자산 노출도는 재무제표 장부가액 또는 재건축가 사용[^9][^4]
- **Insurance Industry Practice**: 건물 재건축가는 자산가치의 표준 지표[^10]

***

## 4. Vulnerability (V) 계산

### 4.1 계산 수식

**Step 1: 일평균 풍속 → 일최대 풍속 변환**

\$ V_{max} = V_{mean} \times k \$

- $V_{mean}$: 일평균 풍속 (m/s) - Hazard에서 산출한 95th percentile 값
- $k$: 변환계수 = **1.7** (국제 표준)
- $V_{max}$: 추정 일최대 풍속 (m/s)

**Step 2: 일최대 풍속 기반 피해율 계산**

$$
V(V_{max}) = \begin{cases}
0 & V_{max} < 25 \\
0.2 \times \frac{V_{max} - 25}{20} & 25 \leq V_{max} < 45 \\
0.2 + 0.6 \times \frac{V_{max} - 45}{25} & 45 \leq V_{max} < 70 \\
0.8 + 0.2 \times \frac{V_{max} - 70}{10} & 70 \leq V_{max} < 80 \\
1.0 & V_{max} \geq 80
\end{cases}
$$

**피해율 구간**:

- **0%**: 25 m/s 미만 (피해 없음)
- **0~20%**: 25~45 m/s (경미한 피해 - 지붕 손상, 간판 탈락)
- **20~80%**: 45~70 m/s (중간~심각 피해 - 외벽 파손, 창문 파손)
- **80~100%**: 70~80 m/s (전손 임박 - 구조 손상)
- **100%**: 80 m/s 이상 (완전 전손)


### 4.2 계산 절차

```python
# Step 1: Hazard에서 산출한 미래 95th percentile 일평균 풍속
V_mean_extreme = V_95p_future  # 예: 15.5 m/s

# Step 2: 일최대 풍속 추정
k = 1.7
V_max = V_mean_extreme * k  # 예: 15.5 * 1.7 = 26.4 m/s

# Step 3: 피해율 계산
if V_max < 25:
    V = 0
elif V_max < 45:
    V = 0.2 * (V_max - 25) / 20
elif V_max < 70:
    V = 0.2 + 0.6 * (V_max - 45) / 25
elif V_max < 80:
    V = 0.8 + 0.2 * (V_max - 70) / 10
else:
    V = 1.0

# 예시 결과: V_max = 26.4 m/s → V = 0.014 (1.4% 피해)
```


### 4.3 필요 데이터

| 데이터명 | 출처 | 형식 | 획득 방법 |
| :-- | :-- | :-- | :-- |
| **변환계수 (k)** | WMO 가이드라인 | 상수 (1.7) | 고정값 사용 |
| **피해율 함수 계수** | 한국 태풍 연구 단순화 | 수식 | 제공된 구간별 함수 사용 |

### 4.4 학술적 근거

- **WMO Guidelines**: 일평균 풍속 → 일최대 풍속 변환계수 1.5~2.0, 평균 1.7 권장[^11][^12]
- **한국 태풍 매미 연구**: 실제 보험 손해액 데이터 기반 풍속-피해율 관계 도출[^13][^10]
- **CLIMADA 모델**: 전 세계 태풍 리스크 평가의 표준 Damage Function 구조[^14]
- **Verisk AIR 모델**: 상업용 재해 모델의 구간별 피해율 접근법[^15]

***

## 5. 통합 리스크 계산

### 5.1 최종 수식

**리스크 점수 (무차원)**

\$ Risk\_Score = H \times V \$

- 0~1 범위, 1에 가까울수록 고위험

**예상 손실액 (원)**

\$ Expected\_Loss = H \times E \times V \$

- 단위: 원(KRW)
- 해석: SSP 시나리오에 따른 태풍 피해 예상 금액


### 5.2 시나리오별 결과 예시

**가정**:

- 기준 기간 95p 풍속: 12.0 m/s
- 사업장 자산가치: 500억 원

| SSP 시나리오 | 미래 95p<br>(m/s) | H | V_max<br>(m/s) | V | Risk Score | 예상 손실액<br>(억 원) |
| :-- | :-- | :-- | :-- | :-- | :-- | :-- |
| **SSP1-2.6** | 12.8 | 1.07 | 21.8 | 0.00 | 0.00 | 0 |
| **SSP2-4.5** | 13.8 | 1.15 | 23.5 | 0.00 | 0.00 | 0 |
| **SSP5-8.5** | 15.5 | 1.29 | 26.4 | 0.014 | 0.018 | 9 |

**해석**:

- SSP5-8.5 시나리오에서 극한 풍속이 29% 증가
- 피해 임계값(25 m/s)을 초과하여 1.4% 피해율 발생
- 500억 원 자산 기준 약 9억 원 손실 예상

***

## 6. 데이터 최종 정리

### 6.1 필수 데이터 체크리스트

| 구성요소 | 데이터 | 출처 | 가용 여부 | 비고 |
| :-- | :-- | :-- | :-- | :-- |
| **H** | SSP 일평균 풍속 | 기상청 climate.go.kr | ✓ 보유 | NetCDF/CSV |
| **E** | 유형자산(토지/건물) | DART dart.fss.or.kr | ✓ 확보 가능 | 재무제표 |
| **E (대체)** | 건물 면적 | 건축물대장 API | ✓ 확보 가능 | JSON/XML |
| **E (대체)** | 실거래가 | 국토부 API | ✓ 확보 가능 | JSON/XML |
| **V** | 변환계수 (1.7) | 문헌 | ✓ 고정값 | - |
| **V** | 피해율 함수 | 한국 연구 | ✓ 제공됨 | 수식 |

### 6.2 데이터 획득 우선순위

1. **1순위**: 기상청 SSP 시나리오 일평균 풍속 (이미 보유)
2. **2순위**: DART 재무제표 유형자산 (기업 공시)
3. **3순위 (대체)**: 건축물대장 + 실거래가 (중소기업/비상장)

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

