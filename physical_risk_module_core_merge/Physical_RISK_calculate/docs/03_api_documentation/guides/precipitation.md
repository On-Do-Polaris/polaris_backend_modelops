# 기상청 강수량 데이터 API (AWS/ASOS)

## API 개요

- **출처**: 기상청 기후정보포털, 기상자료개방포털
- **링크**:
  - 기후정보포털: https://climate.go.kr
  - 기상자료개방포털: https://data.kma.go.kr
  - AWS API: https://data.go.kr/data/15084817/openapi.do
  - ASOS API: https://data.go.kr/data/15084817/openapi.do
- **API 키**: `4b2f121a7492c996d0dca08a311bb9ae1063ae49a3ef40ed955de1f617da8bce`
- **데이터 타입**: JSON/XML
- **데이터 설명**:
  - **관측 데이터**: AWS 10분/시간단위, ASOS 시간/일 단위 강수량
  - **시나리오 데이터**: NetCDF 형태의 일별 강수량 및 극한강수지수 (RX1DAY, RX5DAY, SDII 등)

## 사용 목적

본 프로젝트에서 기상청 강수량 API는 다음 기후 리스크 평가에 사용됩니다:

- **도시홍수 위해성 평가**: RX1DAY (일최대강수량), SDII (강수강도)
- **내륙홍수 위해성 평가**: RX5DAY (5일최대강수량)
- **가뭄 위해성 평가**: 누적강수량, SPI (표준강수지수) 계산
- **물부족 위해성 평가**: 강수량 추이 분석

## API 엔드포인트

### 1. AWS (자동기상관측) API

```
GET https://apihub.kma.go.kr/api/typ01/url/kma_aws.php
```

### 2. ASOS (종관기상관측) API

```
GET https://apihub.kma.go.kr/api/typ01/url/kma_asos.php
```

### 3. 재난안전데이터 공유플랫폼 AWS 10분주기 API

```
GET https://www.safetydata.go.kr/V2/api/DSSP-IF-00026
```

## 요청 파라미터

### AWS/ASOS 공통 파라미터

| 파라미터 | 타입 | 필수 | 설명 | 예시 |
|---------|------|------|------|------|
| `serviceKey` | String | O | 공공데이터포털 인증키 (Decoding) | `4b2f121a...` |
| `stn` | String | O | 관측소코드 (AWS ID 또는 ASOS 지점번호) | `108` (서울) |
| `tm` | String | O | 관측시각 (YYYYMMDDHH24MI) | `202501221430` |
| `pageNo` | Integer | X | 페이지번호 (기본값: 1) | `1` |
| `numOfRows` | Integer | X | 한 페이지 결과 수 (기본값: 10) | `100` |
| `dataType` | String | X | 응답 형식 (JSON/XML, 기본값: XML) | `JSON` |

### 재난안전데이터 AWS 10분주기 파라미터

| 파라미터 | 타입 | 필수 | 설명 | 예시 |
|---------|------|------|------|------|
| `serviceKey` | String | O | 서비스 키 | `98ZFVI407K6KCP66` |
| `AWS_OBSVTR_CD` | String | O | AWS관측소코드 (3자리) | `108` |
| `OBSRVN_HR` | String | O | 관측시간 (YYYYMMDDHHMM) | `202501221430` |
| `returnType` | String | X | 응답 형식 (json/xml) | `json` |

## 응답 데이터

### AWS 응답 필드

```json
{
  "response": {
    "header": {
      "resultCode": "00",
      "resultMsg": "NORMAL_SERVICE"
    },
    "body": {
      "items": {
        "item": [
          {
            "stnId": "108",           // 관측소 ID
            "stnNm": "서울",          // 관측소 명
            "tm": "202501221430",     // 관측시각
            "rn": "12.5",             // 강수량 (mm)
            "rn_day": "35.2",         // 일강수량 (mm)
            "ws": "3.2",              // 풍속 (m/s)
            "ta": "18.5",             // 기온 (℃)
            "hm": "65.0"              // 습도 (%)
          }
        ]
      },
      "totalCount": 1,
      "pageNo": 1,
      "numOfRows": 10
    }
  }
}
```

### ASOS 응답 필드

```json
{
  "response": {
    "header": {
      "resultCode": "00",
      "resultMsg": "NORMAL_SERVICE"
    },
    "body": {
      "items": {
        "item": [
          {
            "stnId": "108",           // 지점번호
            "stnNm": "서울",          // 지점명
            "tm": "2025-01-22 14:00", // 관측시각
            "rn_day": "35.2",         // 일강수량 (mm)
            "rn_1hr": "12.5",         // 1시간 강수량 (mm)
            "ta": "18.5",             // 기온 (℃)
            "hm": "65.0",             // 습도 (%)
            "ws": "3.2"               // 풍속 (m/s)
          }
        ]
      },
      "totalCount": 1
    }
  }
}
```

## Python 사용 예시

### 1. AWS 강수량 데이터 조회

```python
import requests
from datetime import datetime

def get_aws_precipitation(station_code: str, obs_time: str, api_key: str) -> dict:
    """
    AWS 강수량 데이터를 조회합니다.

    Args:
        station_code: AWS 관측소 코드 (예: '108')
        obs_time: 관측시각 (YYYYMMDDHHMM 형식)
        api_key: 공공데이터포털 API 키

    Returns:
        dict: 강수량 데이터
    """
    url = "https://apihub.kma.go.kr/api/typ01/url/kma_aws.php"

    params = {
        "serviceKey": api_key,
        "stn": station_code,
        "tm": obs_time,
        "dataType": "JSON",
        "numOfRows": 100
    }

    try:
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()

        data = response.json()

        if data['response']['header']['resultCode'] == '00':
            items = data['response']['body']['items']['item']
            return items
        else:
            print(f"API Error: {data['response']['header']['resultMsg']}")
            return None

    except requests.exceptions.RequestException as e:
        print(f"Request failed: {e}")
        return None

# 사용 예시
api_key = "4b2f121a7492c996d0dca08a311bb9ae1063ae49a3ef40ed955de1f617da8bce"
station = "108"  # 서울
obs_time = datetime.now().strftime("%Y%m%d%H%M")

data = get_aws_precipitation(station, obs_time, api_key)
if data:
    for item in data:
        print(f"관측소: {item['stnNm']}")
        print(f"강수량: {item['rn']} mm")
        print(f"일강수량: {item['rn_day']} mm")
```

### 2. ASOS 일강수량 조회

```python
def get_asos_daily_precipitation(station_code: str, date: str, api_key: str) -> float:
    """
    ASOS 일강수량 데이터를 조회합니다.

    Args:
        station_code: ASOS 지점번호 (예: '108')
        date: 관측날짜 (YYYYMMDD 형식)
        api_key: 공공데이터포털 API 키

    Returns:
        float: 일강수량 (mm)
    """
    url = "https://apihub.kma.go.kr/api/typ01/url/kma_asos.php"

    params = {
        "serviceKey": api_key,
        "stn": station_code,
        "tm": f"{date}0000",  # 일 단위는 0000으로 설정
        "dataType": "JSON",
        "numOfRows": 1
    }

    try:
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()

        data = response.json()

        if data['response']['header']['resultCode'] == '00':
            item = data['response']['body']['items']['item'][0]
            return float(item['rn_day']) if item['rn_day'] else 0.0
        else:
            print(f"API Error: {data['response']['header']['resultMsg']}")
            return 0.0

    except Exception as e:
        print(f"Error: {e}")
        return 0.0
```

### 3. 극한강수지수 계산 (RX1DAY, RX5DAY)

```python
import pandas as pd
from datetime import datetime, timedelta

def calculate_rx1day(station_code: str, start_date: str, end_date: str, api_key: str) -> float:
    """
    RX1DAY (일최대강수량)을 계산합니다.

    Args:
        station_code: ASOS 지점번호
        start_date: 시작날짜 (YYYYMMDD)
        end_date: 종료날짜 (YYYYMMDD)
        api_key: API 키

    Returns:
        float: RX1DAY 값 (mm)
    """
    start = datetime.strptime(start_date, "%Y%m%d")
    end = datetime.strptime(end_date, "%Y%m%d")

    daily_precip = []

    current = start
    while current <= end:
        date_str = current.strftime("%Y%m%d")
        precip = get_asos_daily_precipitation(station_code, date_str, api_key)
        daily_precip.append(precip)
        current += timedelta(days=1)

    return max(daily_precip) if daily_precip else 0.0

def calculate_rx5day(station_code: str, start_date: str, end_date: str, api_key: str) -> float:
    """
    RX5DAY (5일최대강수량)을 계산합니다.

    Args:
        station_code: ASOS 지점번호
        start_date: 시작날짜 (YYYYMMDD)
        end_date: 종료날짜 (YYYYMMDD)
        api_key: API 키

    Returns:
        float: RX5DAY 값 (mm)
    """
    start = datetime.strptime(start_date, "%Y%m%d")
    end = datetime.strptime(end_date, "%Y%m%d")

    daily_precip = []

    current = start
    while current <= end:
        date_str = current.strftime("%Y%m%d")
        precip = get_asos_daily_precipitation(station_code, date_str, api_key)
        daily_precip.append(precip)
        current += timedelta(days=1)

    # 5일 이동합 계산
    df = pd.DataFrame({'precip': daily_precip})
    rolling_sum = df['precip'].rolling(window=5).sum()

    return rolling_sum.max() if len(rolling_sum) > 0 else 0.0
```

## 프로젝트 내 사용 위치

본 API는 다음 리스크 계산 모듈에서 사용됩니다:

1. **도시홍수 리스크** ([urban_flood_risk.py](../code/urban_flood_risk.py))
   - RX1DAY 계산을 통한 일최대강수량 평가
   - SDII (강수강도) 계산

2. **내륙홍수 리스크** ([river_flood_risk.py](../code/river_flood_risk.py))
   - RX5DAY 계산을 통한 5일최대강수량 평가

3. **가뭄 리스크** ([drought_risk.py](../code/drought_risk.py))
   - 누적강수량 분석
   - SPI (표준강수지수) 계산

4. **물부족 리스크** ([water_stress_risk.py](../code/water_stress_risk.py))
   - 강수량 추이 분석

## 주의사항

1. **API 키 관리**: API 키는 [api_key.md](api_key.md)에 별도로 관리됩니다.
2. **요청 제한**: 공공데이터포털 API는 일일 요청 횟수 제한이 있을 수 있습니다.
3. **데이터 지연**: 실시간 데이터의 경우 관측소별로 10분~1시간 지연이 발생할 수 있습니다.
4. **결측값 처리**: 강수량이 없는 경우 `null` 또는 빈 문자열로 반환될 수 있으므로 예외 처리가 필요합니다.
5. **관측소 코드**: 주요 관측소 코드는 다음과 같습니다:
   - 서울: 108
   - 부산: 159
   - 대구: 143
   - 인천: 112
   - 광주: 156
   - 대전: 133
   - 울산: 152
   - 세종: 239
   - 제주: 184

## 참고 문서

- 기상청 기후정보포털: https://climate.go.kr
- 기상자료개방포털: https://data.kma.go.kr
- 공공데이터포털 AWS API: https://data.go.kr/data/15084817/openapi.do
- 재난안전데이터 공유플랫폼: https://www.safetydata.go.kr
