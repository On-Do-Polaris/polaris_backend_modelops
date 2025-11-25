# 기상청 API 가이드

## 개요

기상청에서 제공하는 기상 관측 및 예보 정보 API입니다.

**API 키**:

- `.env` 파일의 `KMA_API_KEY` (기상청 API Hub용)
- `.env` 파일의 `PUBLICDATA_API_KEY` (공공데이터포털용)

---

## 1. 태풍 정보 API

### 기본 정보

- **제공기관**: 기상청
- **서비스명**: 태풍 정보 조회
- **링크**: https://apihub.kma.go.kr
- **응답형식**: JSON/고정길이 텍스트

### 용도

- 태풍 위해성 평가 (과거 태풍 이력, 강도, 경로)

### API 엔드포인트

```
https://apihub.kma.go.kr/api/typ01/typhoonInfo
```

### 요청 파라미터

| 파라미터   | 타입    | 필수 | 설명              | 예시 |
| ---------- | ------- | ---- | ----------------- | ---- |
| serviceKey | String  | O    | 기상청 API 키     | -    |
| tm         | String  | X    | 년도 (YYYY)       | 2024 |
| pageNo     | Integer | X    | 페이지번호        | 1    |
| numOfRows  | Integer | X    | 한 페이지 결과 수 | 10   |
| dataType   | String  | X    | 응답형식          | JSON |

### 주요 출력 정보

- 태풍명 (국제명, 한글명)
- 태풍번호/호수
- 위도/경도(°)
- 중심기압(hPa)
- 최대풍속(m/s)
- 강풍반경(km)
- 이동방향(°), 이동속도(km/h)
- 태풍등급 (TD, TS, STS, TY)

### Python 예제

```python
import requests
import os
from dotenv import load_dotenv

load_dotenv()
API_KEY = os.getenv('KMA_API_KEY')

url = "https://apihub.kma.go.kr/api/typ01/typhoonInfo"

params = {
    'serviceKey': API_KEY,
    'tm': '2024',
    'pageNo': '1',
    'numOfRows': '10',
    'dataType': 'JSON'
}

response = requests.get(url, params=params)
data = response.json()
```

### 테스트 결과

⚠️ **인증 실패** - API 키 유효성 확인 필요

```
{
  "result": {
    "status": 401,
    "message": "유효한 인증키가 아닙니다."
  }
}
```

---

## 2. 단기예보 조회 API

### 기본 정보

- **제공기관**: 기상청 (공공데이터포털)
- **서비스명**: 동네예보 정보조회 서비스
- **링크**: https://www.data.go.kr/data/15084084/openapi.do
- **응답형식**: JSON/XML

### 용도

- 단기 기상예보 (기온, 강수량, 풍속 등)
- 실시간 기상 모니터링

### API 엔드포인트

```
http://apis.data.go.kr/1360000/VilageFcstInfoService_2.0/getVilageFcst
```

### 요청 파라미터

| 파라미터   | 타입    | 필수 | 설명                | 예시     |
| ---------- | ------- | ---- | ------------------- | -------- |
| serviceKey | String  | O    | 공공데이터 API 키   | -        |
| base_date  | String  | O    | 발표일자 (YYYYMMDD) | 20241122 |
| base_time  | String  | O    | 발표시각 (HH00)     | 0500     |
| nx         | Integer | O    | 예보지점 X좌표      | 60       |
| ny         | Integer | O    | 예보지점 Y좌표      | 127      |
| pageNo     | Integer | X    | 페이지번호          | 1        |
| numOfRows  | Integer | X    | 한 페이지 결과 수   | 10       |
| dataType   | String  | X    | 응답형식            | JSON     |

### 예보 항목

| 항목 | 설명                                    | 단위 |
| ---- | --------------------------------------- | ---- |
| TMP  | 1시간 기온                              | ℃    |
| REH  | 습도                                    | %    |
| SKY  | 하늘상태 (맑음1,구름많음3,흐림4)        | -    |
| PTY  | 강수형태 (없음0,비1,비/눈2,눈3,소나기4) | -    |
| PCP  | 1시간 강수량                            | mm   |
| WSD  | 풍속                                    | m/s  |

### Python 예제

```python
import requests
import os
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()
API_KEY = os.getenv('PUBLICDATA_API_KEY')

url = "http://apis.data.go.kr/1360000/VilageFcstInfoService_2.0/getVilageFcst"

params = {
    'serviceKey': API_KEY,
    'base_date': datetime.now().strftime('%Y%m%d'),
    'base_time': '0500',
    'nx': '60',  # 서울 격자 X
    'ny': '127',  # 서울 격자 Y
    'pageNo': '1',
    'numOfRows': '100',
    'dataType': 'JSON'
}

response = requests.get(url, params=params)
data = response.json()
```

### 테스트 결과

⚠️ **인증 실패** - 공공데이터포털에서 기상청 API 활용신청 승인 필요

---

## 3. 지상 관측 자료 (ASOS) API

### 기본 정보

- **제공기관**: 기상청 (공공데이터포털)
- **서비스명**: 종관기상관측 (ASOS)
- **링크**: https://www.data.go.kr/data/15084084/openapi.do
- **응답형식**: JSON/XML

### 용도

- 과거 기상 데이터 수집
- 폭염/한파/가뭄 위해성 평가

### API 엔드포인트 (일별 자료)

```
http://apis.data.go.kr/1360000/AsosDalyInfoService/getWthrDataList
```

### API 엔드포인트 (시간별 자료)

```
http://apis.data.go.kr/1360000/AsosHourlyInfoService/getWthrDataList
```

### 요청 파라미터 (일별)

| 파라미터   | 타입    | 필수 | 설명                        | 예시       |
| ---------- | ------- | ---- | --------------------------- | ---------- |
| serviceKey | String  | O    | 공공데이터 API 키           | -          |
| dataCd     | String  | O    | 자료 구분                   | ASOS       |
| dateCd     | String  | O    | 날짜 구분                   | DAY        |
| startDt    | String  | O    | 조회 기간 시작일 (YYYYMMDD) | 20241101   |
| endDt      | String  | O    | 조회 기간 종료일 (YYYYMMDD) | 20241130   |
| stnIds     | String  | O    | 지점번호                    | 108 (서울) |
| pageNo     | Integer | X    | 페이지번호                  | 1          |
| numOfRows  | Integer | X    | 한 페이지 결과 수           | 10         |
| dataType   | String  | X    | 응답형식                    | JSON       |

### 주요 관측소

| 지점번호 | 지점명 | 위치              |
| -------- | ------ | ----------------- |
| 108      | 서울   | 서울특별시 종로구 |
| 112      | 인천   | 인천광역시 중구   |
| 133      | 대전   | 대전광역시 서구   |
| 143      | 대구   | 대구광역시 동구   |
| 156      | 광주   | 광주광역시 동구   |
| 159      | 부산   | 부산광역시 동구   |

### 주요 출력 필드

| 필드명 | 설명         | 단위 |
| ------ | ------------ | ---- |
| avgTa  | 평균기온     | ℃    |
| minTa  | 최저기온     | ℃    |
| maxTa  | 최고기온     | ℃    |
| sumRn  | 일강수량     | mm   |
| avgWs  | 평균풍속     | m/s  |
| avgRhm | 평균상대습도 | %    |

### Python 예제

```python
import requests
import os
from dotenv import load_dotenv
from datetime import datetime, timedelta

load_dotenv()
API_KEY = os.getenv('PUBLICDATA_API_KEY')

url = "http://apis.data.go.kr/1360000/AsosDalyInfoService/getWthrDataList"

yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y%m%d')

params = {
    'serviceKey': API_KEY,
    'dataCd': 'ASOS',
    'dateCd': 'DAY',
    'startDt': yesterday,
    'endDt': yesterday,
    'stnIds': '108',  # 서울
    'pageNo': '1',
    'numOfRows': '10',
    'dataType': 'JSON'
}

response = requests.get(url, params=params)
data = response.json()

if data['response']['header']['resultCode'] == '00':
    items = data['response']['body']['items']['item']
    for item in items:
        print(f"날짜: {item['tm']}")
        print(f"평균기온: {item['avgTa']}°C")
        print(f"강수량: {item['sumRn']}mm")
```

### 테스트 결과

⚠️ **인증 실패** - 공공데이터포털에서 기상청 API 활용신청 승인 필요

---

## 문제 해결

### 1. 기상청 API Hub 키 문제

- **증상**: "유효한 인증키가 아닙니다" 오류
- **해결방법**:
  - 기상청 API Hub에서 키 재발급: https://apihub.kma.go.kr
  - 키 활성화 및 트래픽 제한 확인

### 2. 공공데이터포털 기상청 API 문제

- **증상**: 403 Forbidden 오류
- **해결방법**:
  - 공공데이터포털에서 각 기상청 API 활용신청
  - 승인 완료 후 사용 (승인까지 1~2시간 소요)
  - 서비스 목록:
    - 동네예보 정보조회 서비스
    - 종관기상관측 조회서비스 (ASOS)
    - AWS 관측자료 조회서비스

### 3. 격자 좌표 변환

- 위경도 → 기상청 격자 X,Y 변환 필요
- 변환 공식 또는 변환 라이브러리 사용

---

## 추가 리소스

- 기상청 API Hub: https://apihub.kma.go.kr
- 공공데이터포털 기상청 API: https://www.data.go.kr
- 기상자료개방포털: https://data.kma.go.kr
- 기상청 격자 변환: https://www.kma.go.kr/weatherinfo/forecast/digital_forecast.jsp
