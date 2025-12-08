# 물부족(Water Scarcity) 리스크 평가 - 최종 정리

---

## 📊 계산 로직

### 1. 전체 프레임워크

**IPCC AR5 Risk Framework (2014)**

```
물부족 리스크 = f(Hazard, Exposure, Vulnerability)
```

**최종 통합 수식**

```
물부족 리스크 = (0.40 × H) + (0.35 × E) + (0.25 × V)
```

**가중치 근거**

- **Hazard (40%)**: 물 가용성 감소 - 가장 직접적 영향
- **Exposure (35%)**: 물 의존 인구·인프라 - 피해 규모 결정
- **Vulnerability (25%)**: 대응 능력 부족 - 리스크 증폭

**학술 근거**

- **IPCC AR6 WG2 Chapter 4 (2022)**: Risk = f(Hazard, Exposure, Vulnerability) - 물 리스크 평가 프레임워크
- **IPCC AR5 (2014)**: Climate Change 2014: Impacts, Adaptation and Vulnerability
- **한국 가뭄 취약성 평가** (2024, KCI): 가중치 구조 검증

---

### 2. Hazard (위해성) 계산

**정의**: 물 가용성 감소로 인한 물리적 위험

**수식**

```
H = 100 × (총 취수량 / 재생가능 수자원량)
```

**세부 계산**

```python
# 재생가능 수자원량
수자원량 = 강수량(mm) × 유역면적(km²) × 유출계수(0.65) × 0.001

# Hazard 점수
H = (취수량 / 수자원량) × 100
```

**점수 해석**

- 0~25: Low stress
- 25~50: Medium stress
- 50~75: High stress
- 75~100: Very high stress
- 100+: Critical stress

**학술 근거**

- UN SDG 6.4.2 (2016): 공식 물 스트레스 지표
- MSCI ESG (2023): 글로벌 ESG 평가 표준
- World Bank (2015): 국제 물 관리 지표

---

### 3. Exposure (노출) 계산

**정의**: 물 부족에 노출된 인구 및 인프라

**수식**

```
E = (0.60 × 인구 노출) + (0.40 × 인프라 노출)
```

**세부 계산**

```python
# 인구 노출
인구_노출 = (유역 인구 / 전국 인구) × 100

# 인프라 노출
인프라_노출 = 상수도_보급률

# Exposure 통합
E = (0.60 × 인구_노출) + (0.40 × 인프라_노출)
```

**가중치 근거**

- **인구 60%**: IPCC AR5 정의 - Exposure의 핵심 요소
- **인프라 40%**: 한국 물 의존도 반영

**학술 근거**

- IPCC AR5 (2014): Exposure = People + Infrastructure
- 한국 광주·전남 연구 (2024, KCI): 인구·인프라 가중치 검증
- 글로벌 홍수 취약성 (2015, 522회 인용): 인구·GDP 노출 평가

---

### 4. Vulnerability (취약성) 계산

**정의**: 물 부족에 대한 대응 능력 (물 공급 중단 시 버틸 수 있는 능력)

**수식**

```
V = \text{Base}(50) + \text{Tank\_Score} + \text{Pipe\_Score} + \text{Saving\_Score}
```

**세부 계산**

**기본 점수**: 50점

**저수조 보유 여부 (Tank_Score)**:
건물에 저수조가 있는지 여부는 단수 시 물 공급 중단에 대응하는 가장 중요한 요소이다. 실제 API 데이터와 법적 의무 설치 기준을 종합하여 평가한다.

- **API 데이터 우선 확인**: 건축물대장 층별개요 API의 `etcPurps` 필드에서 '저수조', '물탱크' 등 키워드 검색.
    - 저수조 보유 확인: 0점
    - 저수조 미확인: +25점
- **API 실패 시 법적 기준 추정**:
    - 연면적 3,000㎡ 이상 또는 6층 이상 건물: 저수조 보유 추정 (0점)
    - 그 외 건물: 저수조 미보유 추정 (+25점)

**배관 노후화 (Pipe_Score)**:
건물 연식이 오래될수록 배관 부식 및 노후화로 인한 누수 위험이 증가하여 물 손실량이 커진다.

- 30년 초과 (`age > 30`): +15점
- 20년 초과 (`age > 20`): +10점

**절수 설비 (Saving_Score)**:
건물에 절수 설비가 잘 갖춰져 있는지는 물 소비 효율성에 영향을 미친다. 신축 건물일수록 절수 설비가 설치되어 있을 가능성이 높다.

- 10년 이내 (`age < 10`): 0점 (절수 설비 보유)
- 10년 초과 (`age > 10`): +10점 (절수 설비 미비)

### 학술 근거

- **환경부 (2020)**: 물재이용 촉진 및 지원에 관한 법률에서 중수도 및 빗물 이용 시설 설치 의무화.
- **국토교통부 (2019)**: 건축물의 설비기준 등에 관한 규칙에서 저수조 설치 기준 및 용량 규정.
- **한국수자원공사 (2019)**: 물 부족 대응 저수조 설치 가이드라인.

### 필요 데이터

| \# | 데이터명 | 출처 | 형식 | 해상도 |
| :-- | :-- | :-- | :-- | :-- |
| 1 | **건축물대장 기본 정보** | 국토교통부 건축물대장 API | - | 지번/도로명 주소 |

**다운로드 경로**:
```
국토교통부 건축물대장 API: https://www.data.go.kr
```

---

### 5. 미래 시나리오 계산

#### 5.1 미래 인구 계산: 구간별 CAGR 방식

**적용 근거**:
- TCFD 시나리오 분석 표준
- 국제 통계 기준 (IMF, World Bank, UN)
- CSV 데이터 최대 활용 (2020, 2025, 2030, 2035, 2040, 2045, 2050)

**계산 방식**:

목표 연도가 속한 5년 구간의 CAGR을 계산하여 보간합니다.

```python
# 1단계: 목표 연도가 속한 구간 판정
# 예) 2032년 → 2030-2035년 구간

# 2단계: 구간 CAGR 계산
r = (P_2035 / P_2030)^(1/5) - 1

# 3단계: 목표 연도 인구 계산
P_2032 = P_2030 × (1 + r)^(2032 - 2030)
       = P_2030 × (1 + r)^2
```

**구체적 예시 (대전시 2032년 인구)**:

```python
# 데이터 (location_admin 테이블)
P_2030 = 1,370,000명  # 대전시 2030년
P_2035 = 1,350,000명  # 대전시 2035년

# CAGR 계산
r = (1,350,000 / 1,370,000)^(1/5) - 1
  = 0.9854^(0.2) - 1
  = -0.00289 = -0.289%

# 2032년 인구
P_2032 = 1,370,000 × (1 - 0.00289)^2
       = 1,370,000 × 0.99423
       = 1,362,085명
```

**시군구 적용 (대전시 유성구)**:

```python
# 현재 인구 비율
ratio = P_유성구_2020 / P_대전시_2020
      = 350,000 / 1,493,000
      = 23.43%

# 미래 유성구 인구
P_유성구_2032 = P_대전시_2032 × ratio
             = 1,362,085 × 23.43%
             = 319,260명
```

#### 5.2 Hazard 미래 예측

**Hazard 공식**:

```python
# 인구 변화 (구간별 CAGR 적용)
인구_비율 = 미래_인구 / 현재_인구

# 강수 변화
강수_비율 = 현재_강수 / 미래_강수

# 미래 Hazard (취수량은 변동 가능)
H_미래 = H_현재 × 인구_비율 × 강수_비율
```

**예시**:

```python
# 현재 (2024년)
H_현재 = 45.0점

# 미래 (2032년)
인구_비율 = 1,362,085 / 1,493,000 = 0.912
강수_비율 = 1,500mm / 1,350mm = 1.111  # 강수 증가

H_미래 = 45.0 × 0.912 × 1.111
       = 45.6점
```

#### 5.3 Exposure 미래 예측

**Exposure 공식**:

```python
# 인구 변화 반영 (구간별 CAGR 적용)
E_미래 = E_현재 × (미래_인구 / 현재_인구)
```

**예시**:

```python
# 현재 (2024년)
E_현재 = 35.2점

# 미래 (2032년)
E_미래 = 35.2 × (1,362,085 / 1,493,000)
       = 35.2 × 0.912
       = 32.1점  # 인구 감소로 노출도 감소
```

#### 5.4 Vulnerability 미래 예측

**Vulnerability 공식**:

```python
# 댐 저수율, 강수 계절성, 상수도 보급률 변화
V_미래 = V_현재 × (1 + ΔCV/100)
```

**예시**:

```python
# 현재 (2024년)
V_현재 = 28.5점

# 강수 계절성 변화
CV_현재 = 45%  (강수량 표준편차 / 평균)
CV_미래 = 52%  (미래 강수 더 불규칙)
ΔCV = 52 - 45 = 7%

# 미래 Vulnerability
V_미래 = 28.5 × (1 + 7/100)
       = 28.5 × 1.07
       = 30.5점
```

---

### 6. 리스크 등급 분류

**최종 점수 → 등급 변환**

| 점수 범위 | 등급         | 설명      | 조치            |
| :-------- | :----------- | :-------- | :-------------- |
| 0~20      | 🟢 Very Low  | 매우 낮음 | 일상 관리       |
| 20~40     | 🟡 Low       | 낮음      | 주기적 모니터링 |
| 40~60     | 🟠 Medium    | 중간      | 대응 계획 수립  |
| 60~80     | 🔴 High      | 높음      | 즉시 대응 필요  |
| 80~100    | ⚫ Very High | 극심함    | 긴급 대응       |

---

## 📁 데이터

### 1. 필요 데이터 목록

**총 5개 데이터 (모두 공개)**

| \#  | 데이터명      | 용도 | 출처       | 갱신 주기 | 접근성  |
| :-- | :------------ | :--- | :--------- | :-------- | :------ |
| 1   | 용수 취수량   | H    | WAMIS      | 연간      | ✅ 공개 |
| 2   | 강수량        | H, V | 기상청     | 일별      | ✅ 공개 |
| 3   | 댐 저수율     | V    | K-water    | 실시간    | ✅ API  |
| 4   | 인구          | E    | 행정안전부 | 월별      | ✅ 공개 |
| 5   | 상수도 보급률 | E, V | 환경부     | 연간      | ✅ 공개 |

**미래 시나리오용 추가 데이터**

| \#  | 데이터명   | 용도 | 출처   | 시간 범위 | 접근성  |
| :-- | :--------- | :--- | :----- | :-------- | :------ |
| 6   | 인구 추계  | H, E | 통계청 | 2025~2072 | ✅ 공개 |
| 7   | SSP 강수량 | H, V | 기상청 | 2025~2100 | ✅ 공개 |

---

### 2. 데이터 수집 방법

#### 2.1 용수 취수량 (WAMIS)

**출처**: 국가수자원관리종합정보시스템
**URL**: http://www.wamis.go.kr

**수집 절차**

```
1. WAMIS 접속
2. 물이용 → 용수이용현황
3. 대권역별 선택 (한강, 낙동강, 금강, 섬진강, 영산강)
4. 연도 선택
5. Excel 다운로드
```

**제공 데이터**

- 생활용수 이용량 (백만 m³/년)
- 공업용수 이용량 (백만 m³/년)
- 농업용수 이용량 (백만 m³/년)
- 총 취수량 = 생활 + 공업 + 농업

**갱신**: 연 1회 (매년 3월경)

---

#### 2.2 강수량 (기상청)

**출처**: 기상자료개방포털
**URL**: https://data.kma.go.kr

**방법 1: 웹 다운로드**

```
1. 기후통계 → 강수량 분석
2. 유역별 강수량 선택
3. 기간 선택 (연도, 월별)
4. CSV 다운로드
```

**방법 2: 공공데이터포털**

```
1. https://data.go.kr 접속
2. "기상청_유역별 강수량 자료" 검색
3. 파일 다운로드
```

**제공 데이터**

- 월별 강수량 (mm)
- 연간 강수량 (mm)
- 1973~현재

**갱신**: 일별 (실시간)

---

#### 2.3 댐 저수율 (K-water)

**출처**: 한국수자원공사 Open API
**URL**: https://data.go.kr

**API 키 발급**

```
1. 공공데이터포털 가입 (무료)
2. "한국수자원공사 다목적댐 운영정보" 검색
3. 활용신청 클릭
4. 승인 (즉시, 자동)
5. API 키 발급 (마이페이지)
```

**API 호출**

```
엔드포인트: http://apis.data.go.kr/B500001/rwis/waterLevel/list
방식: GET
인증: API Key

제공 항목:
- 저수율 (%)
- 저수량 (백만 m³)
- 유입량 (m³/s)
- 방류량 (m³/s)
```

**제공 댐** (21개)

- 한강: 소양강, 충주, 횡성, 평화의
- 낙동강: 안동, 임하, 합천, 남강, 밀양
- 금강: 대청, 용담
- 섬진강: 섬진강, 주암, 동복, 상사
- 영산강: 장성, 담양, 광주, 나주

**갱신**: 1시간마다

**사용 제한**

- 일일 호출: 1,000회
- 초당 호출: 10회
- 무료

---

#### 2.4 인구 (행정안전부)

**출처**: 주민등록 인구통계
**URL**: https://jumin.mois.go.kr

**수집 절차**

```
1. 행정안전부 주민등록 인구통계 접속
2. 시군구별 인구 → 연령별 인구
3. 읍면동별 선택
4. Excel 다운로드
```

**유역별 집계**

```
한강: 서울, 인천, 경기 일부, 강원 일부, 충북 일부
낙동강: 부산, 대구, 울산, 경북, 경남
금강: 대전, 세종, 충남, 충북 일부, 전북 일부
섬진강: 전북 일부, 전남 일부
영산강: 광주, 전남 일부
```

**제공 데이터**

- 읍면동별 인구수
- 남녀별, 연령별

**갱신**: 월 1회 (매월 초)

---

#### 2.5 상수도 보급률 (환경부)

**출처**: 상수도통계
**URL**: https://www.waternow.go.kr

**수집 절차**

```
1. 상수도정보시스템 접속
2. 통계 → 보급률 현황
3. 시군구별 선택
4. Excel 다운로드
```

**제공 데이터**

- 상수도 보급률 (%)
- 급수인구 (명)
- 총인구 (명)

**갱신**: 연 1회 (매년 12월)

---

#### 2.6 인구 추계 (통계청)

**출처**: 장래인구추계
**URL**: https://kosis.kr

**수집 절차**

```
1. 국가통계포털(KOSIS) 접속
2. 인구/가구 → 장래인구추계
3. 시도별 → 연령별
4. Excel 다운로드
```

**제공 데이터**

- 시도별 인구 추계 (2025~2072)
- 중위/고위/저위 추계
- 연령별 세분화

**갱신**: 5년마다 (최근: 2021년 12월)

---

#### 2.7 SSP 강수량 (기상청)

**출처**: 기상청 기후정보포털
**URL**: 기상청 API Hub

**API 다운로드**

```
엔드포인트:
https://apihub-org.kma.go.kr/api/typ01/url/ssp_skorea_file_down.php

파라미터:
- rpt: SSP245, SSP585
- model: 5ENSM (5개 모델 앙상블)
- elem: RN (강수량)
- grid: sgg261 (시군구 261개)
- time_rsltn: monthly
- st_year: 2021
- ed_year: 2100
- frmat: nc (NetCDF)
```

**제공 데이터**

- 시나리오: SSP1-2.6, SSP2-4.5, SSP3-7.0, SSP5-8.5
- 시간: 2021~2100년 (월별)
- 공간: 시군구 261개
- 형식: NetCDF

**갱신**: 고정 (시나리오 데이터)

---

### 3. 데이터 파일 구조

#### WAMIS 용수 취수량 (Excel)

```
유역    연도    생활용수  공업용수  농업용수  총취수량
한강    2024    2,100    800      550      3,450
낙동강  2024    1,800    950      420      3,170
금강    2024    900      450      380      1,730
섬진강  2024    350      120      210      680
영산강  2024    420      180      260      860
```

#### 기상청 강수량 (CSV)

```
유역,연도,1월,2월,3월,4월,5월,6월,7월,8월,9월,10월,11월,12월,연합계
한강,2024,28.5,45.2,74.3,98.7,108.2,145.8,401.5,340.2,159.3,48.1,45.0,29.8,1524.6
낙동강,2024,25.3,38.1,68.5,92.3,115.7,158.2,385.4,352.1,142.8,52.3,41.2,31.5,1503.4
```

#### K-water 댐 저수율 (JSON)

```json
{
  "response": {
    "body": {
      "items": {
        "item": [
          {
            "damName": "소양강댐",
            "totalCapacity": 2900,
            "currentStorage": 2320,
            "storageRate": 80.0,
            "datetime": "2024-11-18 11:00"
          },
          {
            "damName": "충주댐",
            "totalCapacity": 2750,
            "currentStorage": 1925,
            "storageRate": 70.0,
            "datetime": "2024-11-18 11:00"
          }
        ]
      }
    }
  }
}
```

#### 행정안전부 인구 (Excel)

```
시도    시군구  읍면동      인구
서울    강남구  삼성1동     45,231
서울    강남구  삼성2동     38,562
경기    성남시  분당구      412,583
```

#### 환경부 상수도 보급률 (Excel)

```
시도    시군구  총인구    급수인구  보급률
서울    전체    9,500,000  9,500,000  100.0
경기    성남시  925,000    918,000    99.2
경기    용인시  1,080,000  1,070,000  99.1
```

---

### 4. 유역 기본 정보 (고정값)

**유역 면적 및 유출계수**

| 유역   | 면적 (km²) | 유출계수 | 주요 댐                |
| :----- | :--------- | :------- | :--------------------- |
| 한강   | 26,219     | 0.65     | 소양강, 충주           |
| 낙동강 | 23,817     | 0.60     | 안동, 임하, 합천, 남강 |
| 금강   | 9,914      | 0.58     | 대청, 용담             |
| 섬진강 | 4,914      | 0.62     | 섬진강, 주암           |
| 영산강 | 3,469      | 0.55     | 장성, 담양             |

**유역별 포함 행정구역**

```yaml
한강:
  - 서울특별시 (전체)
  - 인천광역시 (일부)
  - 경기도: 고양, 성남, 용인, 수원, 안양, 부천, 광명, 과천, 의왕, 군포, 시흥, 안산, 화성, 평택, 오산 등
  - 강원도: 춘천, 원주, 홍천, 횡성 등
  - 충청북도: 충주, 제천 등

낙동강:
  - 부산광역시 (전체)
  - 대구광역시 (전체)
  - 울산광역시 (전체)
  - 경상북도 (대부분)
  - 경상남도 (대부분)

금강:
  - 대전광역시 (전체)
  - 세종특별자치시 (전체)
  - 충청남도 (대부분)
  - 충청북도 (일부)
  - 전라북도 (일부)

섬진강:
  - 전라북도: 남원, 임실, 순창 등
  - 전라남도: 구례, 곡성, 순천 등

영산강:
  - 광주광역시 (전체)
  - 전라남도: 나주, 화순, 담양, 장성, 영광, 함평, 무안, 목포 등
```

---

### 5. 데이터 자동화 스크립트

#### 전체 통합 코드 (Python)

```python
import requests
import pandas as pd
import numpy as np
from datetime import datetime

class WaterScarcityRiskAssessment:
    """물부족 리스크 평가 통합 클래스"""

    def __init__(self, api_keys):
        self.kwater_api_key = api_keys['kwater']
        self.basin_areas = {
            '한강': 26219, '낙동강': 23817, '금강': 9914,
            '섬진강': 4914, '영산강': 3469
        }
        self.runoff_coef = {
            '한강': 0.65, '낙동강': 0.60, '금강': 0.58,
            '섬진강': 0.62, '영산강': 0.55
        }

    def calculate_hazard(self, basin, year):
        """Hazard 계산"""
        # 1. WAMIS 취수량 (수동 입력 또는 Excel 읽기)
        withdrawal = self.get_wamis_data(basin, year)

        # 2. 기상청 강수량
        precipitation = self.get_kma_precipitation(basin, year)

        # 3. 재생가능 수자원량
        area = self.basin_areas[basin]
        coef = self.runoff_coef[basin]
        water_resource = precipitation * area * coef * 0.001

        # 4. Hazard 점수
        H = (withdrawal / water_resource) * 100

        return H

    def calculate_exposure(self, basin):
        """Exposure 계산"""
        # 1. 인구 노출
        basin_pop = self.get_population(basin)
        total_pop = 51_500_000
        pop_exposure = (basin_pop / total_pop) * 100

        # 2. 인프라 노출
        coverage = self.get_water_coverage(basin)

        # 3. Exposure 통합
        E = (0.60 * pop_exposure) + (0.40 * coverage)

        return E

    def calculate_vulnerability(self, basin, year):
        """Vulnerability 계산"""
        # 1. V1: 저장 취약성
        storage_rate = self.get_kwater_storage(basin)
        V1 = 100 - storage_rate

        # 2. V2: 계절 취약성
        monthly_precip = self.get_monthly_precipitation(basin, year)
        cv = (np.std(monthly_precip, ddof=1) / np.mean(monthly_precip)) * 100
        V2 = min(100, cv)

        # 3. V3: 대응 취약성
        coverage = self.get_water_coverage(basin)
        V3 = 100 - coverage

        # 4. Vulnerability 통합
        V = (V1 + V2 + V3) / 3

        return V

    def calculate_risk(self, basin, year):
        """최종 리스크 계산"""
        H = self.calculate_hazard(basin, year)
        E = self.calculate_exposure(basin)
        V = self.calculate_vulnerability(basin, year)

        risk = (0.40 * H) + (0.35 * E) + (0.25 * V)

        return {
            'basin': basin,
            'year': year,
            'hazard': H,
            'exposure': E,
            'vulnerability': V,
            'risk_score': risk,
            'risk_level': self.get_risk_level(risk)
        }

    def get_kwater_storage(self, basin):
        """K-water API로 댐 저수율 조회"""
        url = "http://apis.data.go.kr/B500001/rwis/waterLevel/list"
        params = {
            'serviceKey': self.kwater_api_key,
            'numOfRows': 50,
            'type': 'json'
        }

        response = requests.get(url, params=params)
        data = response.json()

        # 유역별 댐 매핑
        basin_dams = {
            '한강': ['소양강댐', '충주댐', '횡성댐', '평화의댐'],
            '낙동강': ['안동댐', '임하댐', '합천댐', '남강댐', '밀양댐'],
            '금강': ['대청댐', '용담댐'],
            '섬진강': ['섬진강댐', '주암댐', '동복댐', '상사댐'],
            '영산강': ['장성댐', '담양댐', '광주댐', '나주댐']
        }

        dams = basin_dams[basin]
        total_capacity = 0
        total_storage = 0

        for item in data['response']['body']['items']['item']:
            if item['damName'] in dams:
                total_capacity += float(item['totalCapacity'])
                total_storage += float(item['currentStorage'])

        return (total_storage / total_capacity) * 100 if total_capacity > 0 else 0

    @staticmethod
    def get_risk_level(score):
        """리스크 등급 분류"""
        if score < 20: return 'Very Low'
        elif score < 40: return 'Low'
        elif score < 60: return 'Medium'
        elif score < 80: return 'High'
        else: return 'Very High'


# 사용 예시
api_keys = {
    'kwater': 'YOUR_API_KEY_HERE'
}

assessment = WaterScarcityRiskAssessment(api_keys)
result = assessment.calculate_risk('한강', 2024)

print(f"=== {result['basin']} 유역 물부족 리스크 ({result['year']}) ===")
print(f"Hazard: {result['hazard']:.1f}점")
print(f"Exposure: {result['exposure']:.1f}점")
print(f"Vulnerability: {result['vulnerability']:.1f}점")
print(f"\n최종 리스크: {result['risk_score']:.1f}점 ({result['risk_level']})")
```

---

## 📚 학술 근거

### 프레임워크

- **IPCC AR6 WG2 Chapter 4 (2022)**: *Climate Change 2022: Impacts, Adaptation and Vulnerability* - Water (인용 8,000회+)
- **IPCC AR5 WG2 (2014)**: *Climate Change 2014: Impacts, Adaptation and Vulnerability* - Risk Framework
- **TCFD (2017)**: *Recommendations of the Task Force on Climate-related Financial Disclosures*

### Hazard

- **UN SDG 6.4.2 (2016)**: Level of water stress 공식 지표
- **MSCI ESG (2023)**: 글로벌 ESG 평가 표준
- **World Bank (2015)**: 국제 물 관리 지표

### Exposure

- **IPCC AR5 (2014)**: Exposure 정의
- **한국 광주·전남 연구 (2024, KCI)**: 인구·인프라 가중치
- **글로벌 홍수 취약성 (2015, 522회)**: 인구·GDP 노출

### Vulnerability

- **WRI Aqueduct (2019)**: 동일 가중 원칙
- **GRACE 연구 (2016, 282회)**: 시계열 동등 중요도
- **한국 가뭄 평가 (2024, KCI)**: 3요소 구조 검증
- **K-water WMRI (2016, 3회)**: 댐 저수율 핵심 지표

---

## ✅ 체크리스트

### 데이터 준비

- [ ] WAMIS 용수 취수량 다운로드 (연 1회)
- [ ] 기상청 강수량 데이터 다운로드 (연 1회)
- [ ] K-water API 키 발급 (최초 1회)
- [ ] 행정안전부 인구 데이터 다운로드 (연 1회)
- [ ] 환경부 상수도 보급률 다운로드 (연 1회)

### 미래 시나리오

- [ ] 통계청 인구 추계 다운로드 (5년 1회)
- [ ] 기상청 SSP 강수량 다운로드 (최초 1회)

### 계산 및 검증

- [ ] Hazard 계산 완료
- [ ] Exposure 계산 완료
- [ ] Vulnerability 계산 완료
- [ ] 최종 리스크 점수 산출
- [ ] 리스크 등급 분류

### TCFD 보고서

- [ ] 방법론 설명 작성
- [ ] 데이터 출처 명시
- [ ] 학술 근거 인용
- [ ] 리스크 평가 결과 정리
- [ ] 대응 방안 수립

---

## 📞 문의처

### 데이터 관련

- **WAMIS**: http://www.wamis.go.kr (☎ 044-201-7232)
- **기상청**: https://data.kma.go.kr (☎ 02-2181-0900)
- **K-water**: https://www.water.or.kr (☎ 1577-0600)
- **환경부**: https://www.waternow.go.kr (☎ 044-201-7164)

### API 관련

- **공공데이터포털**: https://data.go.kr (☎ 02-2100-2999)

---

**마지막 업데이트**: 2025년 11월 18일
**문서 버전**: 1.0
**작성 근거**: IPCC AR5, UN SDG 6.4.2, 한국 학술 연구 (2024)
