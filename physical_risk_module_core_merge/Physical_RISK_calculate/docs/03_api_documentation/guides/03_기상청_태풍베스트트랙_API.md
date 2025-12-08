# 기상청 태풍 베스트트랙 API

## 개요

기상청 태풍 베스트트랙 API는 태풍예보 상황에서 실황분석 자료로 활용되지 못했던 자료들을 확보하여 보다 정밀하게 재분석된 사후 태풍정보를 제공합니다.

**제공 기관**: 기상청  
**API 유형**: REST API  
**데이터 포맷**: Text (공백 구분)  
**인증 방식**: API Key (authKey)

## API 정보

### 1.1 태풍 베스트트랙 조회

- **엔드포인트**: `/api/typ01/url/typ_besttrack.php`
- **Base URL**: `https://apihub.kma.go.kr`
- **보유기간**: 2015~2022년
- **생산주기**: 연 1회 (매년 7월 전년도 자료 업데이트)

## 제공 요소

- **등급**: TD, TS, STS, TY, L
- **태풍호수**: 년도 + 순번 (예: 2201)
- **시간 정보**: 년, 월, 일, 시
- **위치 정보**: 경도, 위도
- **강도 정보**: 중심최대풍속, 중심기압
- **영향 범위**:
  - 강풍(15m/s 이상) 반경: 장반경, 단반경, 방향
  - 폭풍(25m/s 이상) 반경: 장반경, 단반경, 방향
- **태풍이름**: 국제 태풍 이름

---

## 요청 파라미터

| 파라미터 | 타입   | 필수 | 설명                                      |
| -------- | ------ | ---- | ----------------------------------------- |
| year     | STRING | Y    | 태풍발생 년도                             |
| grade    | STRING | N    | 태풍등급 (TD, TS, STS, TY, L)             |
| tcid     | STRING | N    | 태풍호수 (앞 2자리: 년도, 뒤 2자리: 순번) |
| help     | NUMBER | N    | 도움말 (0: 기본, 1: 설명 포함, 2: 값만)   |
| authKey  | STRING | Y    | 인증키                                    |

### 태풍 등급 (grade)

| 코드 | 등급명       | 설명                                    |
| ---- | ------------ | --------------------------------------- |
| TD   | 열대저압부   | 중심최대풍속 14m/s 이상                 |
| TS   | 열대폭풍     | 중심최대풍속 17m/s 이상, 25m/s 미만     |
| STS  | 강한열대폭풍 | 중심최대풍속 25m/s 이상, 33m/s 미만     |
| TY   | 태풍         | 중심최대풍속 33m/s 이상                 |
| L    | 온대저기압   | 열대저기압이 온대저기압으로 변질된 경우 |

---

## 응답 데이터

### 응답 형식

텍스트 형식으로 공백(space)으로 구분된 데이터가 제공됩니다. `#`으로 시작하는 라인은 주석입니다.

### 응답 필드

| 순서 | 변수명      | 의미(단위)                       | 예시      |
| ---- | ----------- | -------------------------------- | --------- |
| 1    | GRADE       | 태풍등급                         | TY        |
| 2    | TCID        | 태풍호수                         | 2211      |
| 3    | YEAR        | 년                               | 2022      |
| 4    | MONTH       | 월                               | 8         |
| 5    | DAY         | 일                               | 29        |
| 6    | HOUR        | 시                               | 12        |
| 7    | LON         | 경도 (°E)                        | 141.2     |
| 8    | LAT         | 위도 (°N)                        | 27.3      |
| 9    | MAX_WS      | 중심최대풍속 (m/s)               | 40        |
| 10   | PS          | 중심기압 (hPa)                   | 955       |
| 11   | GALE_LONG   | 강풍(15m/s) 반경 장반경 (km)     | 160       |
| 12   | GALE_SHORT  | 강풍(15m/s) 반경 단반경 (km)     | 100       |
| 13   | GALE_DIR    | 강풍(15m/s) 반경 단반경 방향 (°) | NE        |
| 14   | STORM_LONG  | 폭풍(25m/s) 반경 장반경 (km)     | 50        |
| 15   | STORM_SHORT | 폭풍(25m/s) 반경 단반경 (km)     | 30        |
| 16   | STORM_DIR   | 폭풍(25m/s) 반경 단반경 방향 (°) | NE        |
| 17   | NAME        | 태풍이름                         | HINNAMNOR |

---

## 샘플 코드

```python
import requests
import os
from dotenv import load_dotenv

load_dotenv()

# 태풍 베스트트랙 조회 (2022년 11호 태풍 힌남노)
url = "https://apihub.kma.go.kr/api/typ01/url/typ_besttrack.php"
params = {
    'year': '2022',
    'grade': 'TY',
    'tcid': '2211',
    'help': '1',  # 설명 포함
    'authKey': os.getenv('KMA_API_KEY')
}

response = requests.get(url, params=params, timeout=30)

if response.status_code == 200:
    content = response.text
    lines = content.strip().split('\n')

    # 주석(#)이 아닌 데이터 라인만 추출
    data_lines = [line for line in lines if line and not line.startswith('#')]

    for data_line in data_lines:
        fields = data_line.split()
        print(f"{fields[2]}-{fields[3]}-{fields[4]} {fields[5]}:00")
        print(f"  위치: {fields[6]}°E, {fields[7]}°N")
        print(f"  풍속: {fields[8]}m/s, 기압: {fields[9]}hPa")
        print(f"  태풍이름: {fields[16]}")
```

---

## 테스트 결과

### ✅ 성공한 테스트 (3/3)

#### 1. 2022년 1호 태풍 (MALAKAS)

- **태풍호수**: 2201
- **등급**: TY (태풍)
- **관측 데이터**: 13개 시간대
- **첫 번째 관측**:
  - 일시: 2022-04-12 06:00
  - 위치: 경도 135.1°E, 위도 15.8°N
  - 중심최대풍속: 37 m/s
  - 중심기압: 965 hPa
  - 강풍반경(15m/s): 장반경 340km, 단반경 260km
  - 폭풍반경(25m/s): 장반경 100km, 단반경 80km

#### 2. 2022년 11호 태풍 (HINNAMNOR - 힌남노)

- **태풍호수**: 2211
- **등급**: TY (태풍)
- **관측 데이터**: 38개 시간대
- **첫 번째 관측**:
  - 일시: 2022-08-29 12:00
  - 위치: 경도 141.2°E, 위도 27.3°N
  - 중심최대풍속: 40 m/s
  - 중심기압: 955 hPa
  - 강풍반경(15m/s): 장반경 160km, 단반경 100km
  - 폭풍반경(25m/s): 장반경 50km, 단반경 30km

> **참고**: 힌남노(HINNAMNOR)는 2022년 9월 한반도에 영향을 준 강력한 태풍

#### 3. 2021년 14호 태풍 (CHANTHU - 찬투)

- **태풍호수**: 2114
- **등급**: TY (태풍)
- **관측 데이터**: 32개 시간대
- **첫 번째 관측**:
  - 일시: 2021-09-07 18:00
  - 위치: 경도 133.5°E, 위도 16.2°N
  - 중심최대풍속: 35 m/s
  - 중심기압: 970 hPa
  - 강풍반경(15m/s): 장반경 130km, 단반경 90km
  - 폭풍반경(25m/s): 장반경 60km, 단반경 40km

---

## 활용 사례

### 1. 기후리스크 분석 - 태풍 위험도 평가

태풍 베스트트랙 데이터를 활용하여 지역별 태풍 영향도를 분석할 수 있습니다.

```python
# 특정 지역(예: 제주도)의 태풍 영향권 여부 판단
jeju_lat = 33.5
jeju_lon = 126.5

for data in typhoon_data:
    # 태풍 중심 위치
    typhoon_lat = float(data[7])
    typhoon_lon = float(data[6])

    # 거리 계산 (haversine 공식 등 사용)
    distance = calculate_distance(jeju_lat, jeju_lon, typhoon_lat, typhoon_lon)

    # 강풍 반경 확인
    gale_radius = float(data[10])  # 장반경

    if distance <= gale_radius:
        print(f"제주도가 강풍 영향권 내에 있음 (거리: {distance}km)")
```

### 2. Physical Risk 계산

```python
# V_hazard (위해도) 계산 예시
# 태풍 강도 = f(중심최대풍속, 중심기압)

max_wind_speed = float(data[8])  # 중심최대풍속 (m/s)
central_pressure = float(data[9])  # 중심기압 (hPa)

# 태풍 강도 지수 계산
typhoon_intensity = (max_wind_speed / 50) * (1000 - central_pressure) / 100

# V_hazard 계산 (0~1 정규화)
V_hazard = min(typhoon_intensity / 10, 1.0)
```

### 3. 시나리오별 태풍 리스크 분석

- **과거 태풍 경로 분석**: 2015~2022년 베스트트랙 데이터 기반
- **지역별 태풍 빈도**: 특정 지역을 통과한 태풍 횟수 집계
- **태풍 강도 추세**: 연도별 태풍 강도 변화 분석
- **영향권 분석**: 강풍/폭풍 반경 기반 피해 예상 지역 식별

---

## 주의사항

1. **타임아웃 설정**

   - API 응답 시간이 길 수 있음 (10~30초)
   - `timeout=30` 이상 권장

2. **데이터 형식**

   - 공백(space)으로 구분된 텍스트 형식
   - `#`으로 시작하는 주석 라인 제외 필요

3. **데이터 보유 기간**

   - 2015~2022년 데이터만 제공
   - 2023년 데이터는 2024년 7월 업데이트 예정

4. **태풍호수 (tcid)**

   - 앞 2자리: 년도 (예: 22 = 2022년)
   - 뒤 2자리: 순번 (01~99)
   - 예: 2211 = 2022년 11호 태풍

5. **등급 변화**
   - 태풍은 시간에 따라 등급이 변할 수 있음
   - TD → TS → STS → TY → L 순으로 발달/약화

---

## 환경변수 설정

```bash
# .env 파일
KMA_API_KEY=your_kma_api_key_here
```

---

## 관련 링크

- **기상청 API 허브**: https://apihub.kma.go.kr
- **태풍 정보**: https://www.weather.go.kr/w/typhoon/index.do
- **기상청**: https://www.kma.go.kr

---

**최종 테스트 일시**: 2025-11-22  
**테스트 결과**: 3/3 성공 (100%)
