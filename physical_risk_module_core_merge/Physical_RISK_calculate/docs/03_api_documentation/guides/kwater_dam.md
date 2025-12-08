# K-water 댐 저수율 (수문 운영 정보) API

## API 개요

- **출처**: 한국수자원공사 (K-water)
- **링크**:
  - K-water 환경데이터마트: https://data.edmgr.kr
  - 공공데이터포털: https://www.data.go.kr/data/15099110/openapi.do
- **API 키**: `4b2f121a7492c996d0dca08a311bb9ae1063ae49a3ef40ed955de1f617da8bce`
- **데이터 타입**: JSON/XML
- **데이터 설명**: K-water 관리 댐 (다목적댐 21개소, 용수댐, 홍수조절댐) 실시간 운영정보 (10분 단위)

## 사용 목적

본 프로젝트에서 K-water 댐 저수율 API는 다음 기후 리스크 평가에 사용됩니다:

- **물부족 취약성 평가**: 댐 저수상황 모니터링
- **가뭄 취약성 평가**: 저수율 기반 가뭄 심각도 평가

## API 엔드포인트

```
GET http://apis.data.go.kr/B500001/rwis/waterLevel/list
```

또는

```
GET https://data.edmgr.kr/api/damWaterLevel
```

## 요청 파라미터

| 파라미터 | 타입 | 필수 | 설명 | 예시 |
|---------|------|------|------|------|
| `serviceKey` | String | O | 공공데이터포털 인증키 (Decoding) | `4b2f121a...` |
| `damCode` | String | X | 댐 코드 (7자리) | `3200700` (소양강댐) |
| `obsDate` | String | X | 관측일자 (YYYYMMDD) | `20250122` |
| `obsTime` | String | X | 관측시각 (HHMM) | `1430` |
| `pageNo` | Integer | X | 페이지 번호 (기본값: 1) | `1` |
| `numOfRows` | Integer | X | 한 페이지 결과 수 (기본값: 10) | `100` |
| `dataType` | String | X | 응답 형식 (JSON/XML) | `JSON` |

## 주요 댐 코드

### 다목적댐 (21개소)

| 댐 코드 | 댐명 | 위치 | 총저수량 (백만㎥) |
|--------|------|------|------------------|
| `3200700` | 소양강댐 | 강원 춘천 | 2,900 |
| `4100110` | 충주댐 | 충북 충주 | 2,750 |
| `3100110` | 안동댐 | 경북 안동 | 1,248 |
| `3100120` | 임하댐 | 경북 안동 | 595 |
| `3200100` | 대청댐 | 대전/충북 | 1,490 |
| `2100100` | 주암댐 | 전남 순천 | 457 |
| `2100110` | 주암조절댐 | 전남 순천 | 250 |
| `2100200` | 장흥댐 | 전남 장흥 | 191 |
| `3400100` | 섬진강댐 | 전북 임실 | 466 |
| `3400300` | 운문댐 | 경북 청도 | 160 |
| `3400900` | 남강댐 | 경남 진주 | 309 |
| `3401300` | 합천댐 | 경남 합천 | 790 |
| `3401400` | 밀양댐 | 경남 밀양 | 73.6 |
| `3401500` | 보령댐 | 충남 보령 | 116.9 |
| `3401600` | 부안댐 | 전북 부안 | 50.4 |
| `3401700` | 영천댐 | 경북 영천 | 106 |
| `3402000` | 용담댐 | 전북 진안 | 815 |
| `3403100` | 횡성댐 | 강원 횡성 | 86.9 |
| `3403200` | 군위댐 | 경북 군위 | 48.5 |
| `3403300` | 영주댐 | 경북 영주 | 181.1 |
| `3403400` | 보현산댐 | 경북 영천 | 22.8 |

## 응답 데이터

### JSON 응답 형식

```json
{
  "response": {
    "header": {
      "resultCode": "00",
      "resultMsg": "NORMAL_SERVICE"
    },
    "body": {
      "items": [
        {
          "damCode": "3200700",
          "damName": "소양강댐",
          "obsDate": "20250122",
          "obsTime": "1430",
          "inflow": "125.5",              // 유입량 (m³/s)
          "outflow": "85.2",              // 방류량 (m³/s)
          "waterLevel": "185.32",         // 저수위 (EL.m)
          "storage": "2145.8",            // 저수량 (백만㎥)
          "storageRate": "74.0",          // 저수율 (%)
          "fullWaterLevel": "193.5",      // 만수위 (EL.m)
          "totalStorage": "2900.0",       // 총저수량 (백만㎥)
          "rainfall_yesterday": "0.0",    // 전일 강우량 (mm)
          "rainfall_today": "12.5",       // 금일 강우량 (mm)
          "rainfall_cumulative": "125.3"  // 누적 강우량 (mm)
        }
      ],
      "numOfRows": 10,
      "pageNo": 1,
      "totalCount": 1
    }
  }
}
```

## Python 사용 예시

### 1. 댐 저수율 조회

```python
import requests
from typing import Optional, List, Dict
from datetime import datetime

def get_dam_water_level(
    api_key: str,
    dam_code: Optional[str] = None,
    obs_date: Optional[str] = None
) -> List[Dict]:
    """
    K-water 댐 저수율 정보를 조회합니다.

    Args:
        api_key: 공공데이터포털 API 키
        dam_code: 댐 코드 (7자리, 미입력 시 전체 조회)
        obs_date: 관측일자 (YYYYMMDD, 미입력 시 최신)

    Returns:
        List[Dict]: 댐 저수율 정보 리스트
    """
    url = "http://apis.data.go.kr/B500001/rwis/waterLevel/list"

    params = {
        "serviceKey": api_key,
        "pageNo": 1,
        "numOfRows": 100,
        "dataType": "JSON"
    }

    if dam_code:
        params["damCode"] = dam_code
    if obs_date:
        params["obsDate"] = obs_date

    try:
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()

        data = response.json()

        if data['response']['header']['resultCode'] == '00':
            items = data['response']['body']['items']
            return items if isinstance(items, list) else [items]
        else:
            print(f"API Error: {data['response']['header']['resultMsg']}")
            return []

    except requests.exceptions.RequestException as e:
        print(f"Request failed: {e}")
        return []
    except Exception as e:
        print(f"Error: {e}")
        return []

# 사용 예시
api_key = "4b2f121a7492c996d0dca08a311bb9ae1063ae49a3ef40ed955de1f617da8bce"

# 소양강댐 저수율 조회
soyang_dam = get_dam_water_level(api_key, dam_code="3200700")

if soyang_dam:
    dam = soyang_dam[0]
    print(f"댐명: {dam['damName']}")
    print(f"저수율: {dam['storageRate']}%")
    print(f"저수량: {dam['storage']} 백만㎥")
    print(f"유입량: {dam['inflow']} m³/s")
    print(f"방류량: {dam['outflow']} m³/s")
```

### 2. 전국 주요 댐 저수율 현황

```python
def get_all_major_dams_status(api_key: str) -> List[Dict]:
    """
    전국 주요 다목적댐 저수율 현황을 조회합니다.

    Args:
        api_key: API 키

    Returns:
        List[Dict]: 전국 댐 저수율 현황
    """
    major_dams = [
        "3200700",  # 소양강댐
        "4100110",  # 충주댐
        "3100110",  # 안동댐
        "3200100",  # 대청댐
        "3402000",  # 용담댐
        "3400900",  # 남강댐
        "3401300",  # 합천댐
        "3401500",  # 보령댐
    ]

    dam_status = []

    for dam_code in major_dams:
        data = get_dam_water_level(api_key, dam_code=dam_code)
        if data:
            dam = data[0]
            dam_status.append({
                '댐명': dam['damName'],
                '저수율_%': float(dam['storageRate']),
                '저수량_백만m3': float(dam['storage']),
                '총저수량_백만m3': float(dam['totalStorage']),
                '유입량_m3_s': float(dam['inflow']),
                '방류량_m3_s': float(dam['outflow'])
            })

    # 저수율 낮은 순 정렬
    dam_status.sort(key=lambda x: x['저수율_%'])

    return dam_status

# 사용 예시
all_dams = get_all_major_dams_status(api_key)

print("전국 주요 댐 저수율 현황")
print("-" * 70)
for dam in all_dams:
    print(f"{dam['댐명']:10s} | 저수율: {dam['저수율_%']:5.1f}% | "
          f"저수량: {dam['저수량_백만m3']:7.1f} 백만㎥")
```

### 3. 가뭄 심각도 평가 (저수율 기반)

```python
def assess_drought_severity(storage_rate: float) -> Dict:
    """
    댐 저수율을 기반으로 가뭄 심각도를 평가합니다.

    Args:
        storage_rate: 저수율 (%)

    Returns:
        Dict: 가뭄 심각도 정보
    """
    if storage_rate >= 80:
        severity = "정상"
        level = 0
        description = "가뭄 위험 없음"
    elif storage_rate >= 60:
        severity = "관심"
        level = 1
        description = "정상 범위, 지속 모니터링 필요"
    elif storage_rate >= 40:
        severity = "주의"
        level = 2
        description = "가뭄 주의단계, 용수 절약 권장"
    elif storage_rate >= 20:
        severity = "경계"
        level = 3
        description = "가뭄 경계단계, 용수 제한 필요"
    else:
        severity = "심각"
        level = 4
        description = "가뭄 심각단계, 비상급수 대책 필요"

    return {
        '저수율_%': storage_rate,
        '가뭄심각도': severity,
        '심각도레벨': level,
        '설명': description
    }

# 사용 예시
soyang_dam = get_dam_water_level(api_key, dam_code="3200700")
if soyang_dam:
    storage_rate = float(soyang_dam[0]['storageRate'])
    severity = assess_drought_severity(storage_rate)

    print(f"댐명: {soyang_dam[0]['damName']}")
    print(f"저수율: {severity['저수율_%']}%")
    print(f"가뭄 심각도: {severity['가뭄심각도']} (Level {severity['심각도레벨']})")
    print(f"설명: {severity['설명']}")
```

### 4. 시계열 저수율 추세 분석

```python
import pandas as pd
from datetime import datetime, timedelta

def analyze_storage_trend(
    api_key: str,
    dam_code: str,
    days: int = 30
) -> Dict:
    """
    최근 N일간 댐 저수율 추세를 분석합니다.

    Args:
        api_key: API 키
        dam_code: 댐 코드
        days: 분석 기간 (일)

    Returns:
        Dict: 저수율 추세 분석 결과
    """
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)

    storage_rates = []
    dates = []

    current_date = start_date
    while current_date <= end_date:
        obs_date = current_date.strftime("%Y%m%d")
        data = get_dam_water_level(api_key, dam_code=dam_code, obs_date=obs_date)

        if data:
            storage_rates.append(float(data[0]['storageRate']))
            dates.append(current_date)

        current_date += timedelta(days=1)

    if not storage_rates:
        return None

    df = pd.DataFrame({
        'date': dates,
        'storage_rate': storage_rates
    })

    # 추세 분석
    trend = "감소" if storage_rates[-1] < storage_rates[0] else "증가"
    change = storage_rates[-1] - storage_rates[0]
    avg_rate = sum(storage_rates) / len(storage_rates)
    min_rate = min(storage_rates)
    max_rate = max(storage_rates)

    return {
        '분석기간_일': days,
        '시작저수율_%': round(storage_rates[0], 2),
        '종료저수율_%': round(storage_rates[-1], 2),
        '평균저수율_%': round(avg_rate, 2),
        '최소저수율_%': round(min_rate, 2),
        '최대저수율_%': round(max_rate, 2),
        '변화량_%p': round(change, 2),
        '추세': trend
    }

# 사용 예시
trend = analyze_storage_trend(api_key, dam_code="3200700", days=30)
if trend:
    print(f"최근 {trend['분석기간_일']}일간 저수율 추세")
    print(f"현재 저수율: {trend['종료저수율_%']}%")
    print(f"평균 저수율: {trend['평균저수율_%']}%")
    print(f"변화량: {trend['변화량_%p']}%p ({trend['추세']})")
```

### 5. 물부족 리스크 점수 계산

```python
def calculate_water_stress_score(api_key: str, region_dams: List[str]) -> float:
    """
    특정 지역 댐들의 저수율을 기반으로 물부족 리스크 점수를 계산합니다.

    Args:
        api_key: API 키
        region_dams: 지역 댐 코드 리스트

    Returns:
        float: 물부족 리스크 점수 (0~100)
    """
    storage_rates = []

    for dam_code in region_dams:
        data = get_dam_water_level(api_key, dam_code=dam_code)
        if data:
            storage_rates.append(float(data[0]['storageRate']))

    if not storage_rates:
        return 0.0

    # 평균 저수율 계산
    avg_storage = sum(storage_rates) / len(storage_rates)

    # 물부족 리스크 점수 (저수율이 낮을수록 점수 높음)
    risk_score = 100 - avg_storage

    return round(risk_score, 2)

# 사용 예시 (충청권 댐)
chungcheong_dams = [
    "3200100",  # 대청댐
    "3401500",  # 보령댐
]

risk_score = calculate_water_stress_score(api_key, chungcheong_dams)
print(f"충청권 물부족 리스크 점수: {risk_score}/100")
```

## 프로젝트 내 사용 위치

본 API는 다음 리스크 계산 모듈에서 사용됩니다:

1. **물부족 리스크** ([water_stress_risk.py](../code/water_stress_risk.py))
   - 댐 저수상황 모니터링
   - 물부족 취약성 평가

2. **가뭄 리스크** ([drought_risk.py](../code/drought_risk.py))
   - 저수율 기반 가뭄 심각도 평가
   - 가뭄 취약성 평가

## 주의사항

1. **API 키 관리**: API 키는 [api_key.md](api_key.md)에 별도로 관리됩니다.
2. **데이터 갱신**: 댐 운영 정보는 10분 단위로 갱신됩니다.
3. **결측값 처리**: 일부 댐은 특정 시간대 데이터가 누락될 수 있으므로 예외 처리가 필요합니다.
4. **댐 코드**: 댐 코드는 7자리이며, K-water 환경데이터마트에서 확인 가능합니다.
5. **저수율 해석**: 저수율은 총저수량 대비 현재 저수량의 비율입니다.

## 가뭄 심각도 기준

| 저수율 | 심각도 | 조치사항 |
|--------|--------|----------|
| 80% 이상 | 정상 | 정상 운영 |
| 60~80% | 관심 | 지속 모니터링 |
| 40~60% | 주의 | 용수 절약 권장 |
| 20~40% | 경계 | 용수 제한 |
| 20% 미만 | 심각 | 비상급수 대책 |

## 참고 문서

- K-water 환경데이터마트: https://data.edmgr.kr
- 공공데이터포털 수문 운영 정보: https://www.data.go.kr/data/15099110/openapi.do
- K-water 실시간 댐 정보: https://www.water.or.kr
- 국가가뭄정보포털: https://www.drought.go.kr
