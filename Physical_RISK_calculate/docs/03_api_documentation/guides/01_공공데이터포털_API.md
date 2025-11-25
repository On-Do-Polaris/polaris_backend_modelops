# 공공데이터포털 API 가이드

## 개요

공공데이터포털에서 제공하는 기후리스크 분석 관련 Open API 모음입니다.

**API 키**: `.env` 파일의 `PUBLICDATA_API_KEY` 참조

---

## 1. 건축물대장 API

### 기본 정보

- **제공기관**: 국토교통부
- **서비스명**: 건축물대장 정보 서비스
- **링크**: https://www.data.go.kr/data/15135963/openapi.do
- **응답형식**: JSON/XML

### 용도

- 폭염/한파 취약성 평가 (건물 냉난방 효율성, 건축연도)
- 산불 취약성 평가 (건물 구조, 가연성)
- 도시/내륙/해안홍수 취약성 평가 (지하층, 건물 높이, 구조)
- 태풍 노출도 평가 (건물 면적, 자산가치)

### API 엔드포인트

```
http://apis.data.go.kr/1613000/BldRgstHubService/getBrTitleInfo
```

### 요청 파라미터

| 파라미터   | 타입    | 필수 | 설명                  | 예시           |
| ---------- | ------- | ---- | --------------------- | -------------- |
| serviceKey | String  | O    | 공공데이터포털 API 키 | -              |
| sigunguCd  | String  | O    | 시군구코드 (5자리)    | 11110 (종로구) |
| bjdongCd   | String  | O    | 법정동코드            | 10100          |
| bun        | String  | O    | 번 (4자리)            | 0001           |
| ji         | String  | O    | 지 (4자리)            | 0000           |
| numOfRows  | Integer | X    | 한 페이지 결과 수     | 10             |
| pageNo     | Integer | X    | 페이지번호            | 1              |
| \_type     | String  | X    | 응답형식              | json           |

### 응답 예시 (주요 필드)

```json
{
  "response": {
    "header": {
      "resultCode": "00",
      "resultMsg": "NORMAL SERVICE"
    },
    "body": {
      "items": {
        "item": [
          {
            "platPlc": "서울특별시 종로구 청운동 1번지",
            "newPlatPlc": "서울특별시 종로구 자하문로36길 16-14 (청운동)",
            "bldNm": "청운벽산빌리지",
            "dongNm": "9동",
            "totArea": 5489.43,
            "strctCd": "21",
            "strctCdNm": "철근콘크리트구조",
            "mainPurpsCd": "02000",
            "mainPurpsCdNm": "공동주택",
            "grndFlrCnt": 3,
            "ugrndFlrCnt": 2,
            "pmsDay": "19870404",
            "useAprDay": "19881111"
          }
        ]
      },
      "totalCount": "11"
    }
  }
}
```

### 주요 출력 필드

| 필드명        | 설명                                   | 용도        |
| ------------- | -------------------------------------- | ----------- |
| strctCdNm     | 건물구조 (철근콘크리트, 철골, 목조 등) | 취약성 평가 |
| pmsDay        | 건축연도(YYYYMMDD)                     | 노후도 평가 |
| grndFlrCnt    | 지상층수                               | 건물 높이   |
| ugrndFlrCnt   | 지하층수                               | 침수 취약성 |
| mainPurpsCdNm | 용도                                   | 자산 분류   |
| totArea       | 연면적(㎡)                             | 자산가치    |

### Python 예제

```python
import requests
import os
from dotenv import load_dotenv

load_dotenv()
API_KEY = os.getenv('PUBLICDATA_API_KEY')

url = "http://apis.data.go.kr/1613000/BldRgstHubService/getBrTitleInfo"

params = {
    'serviceKey': API_KEY,
    'sigunguCd': '11110',  # 서울 종로구
    'bjdongCd': '10100',    # 청운동
    'bun': '0001',
    'ji': '0000',
    'numOfRows': '10',
    'pageNo': '1',
    '_type': 'json'
}

response = requests.get(url, params=params)
data = response.json()
print(data)
```

### 테스트 결과

✅ **성공** - 정상적으로 건축물 정보를 조회할 수 있습니다.

---

## 2. 국립중앙의료원 병원 API

### 기본 정보

- **제공기관**: 보건복지부 국립중앙의료원
- **서비스명**: 병·의원 찾기 서비스
- **링크**: https://www.data.go.kr/data/15000736/openapi.do
- **응답형식**: XML

### 용도

- 폭염 취약성 평가 (의료접근성)
- 한파 취약성 평가 (의료접근성)

### API 엔드포인트

```
http://apis.data.go.kr/B552657/HsptlAsembySearchService/getHsptlMdcncListInfoInqire
```

### 요청 파라미터

| 파라미터   | 타입    | 필수 | 설명                  | 예시       |
| ---------- | ------- | ---- | --------------------- | ---------- |
| serviceKey | String  | O    | 공공데이터포털 API 키 | -          |
| Q0         | String  | X    | 시도명                | 서울특별시 |
| Q1         | String  | X    | 시군구명              | 종로구     |
| QT         | String  | X    | 병원종별              | -          |
| pageNo     | Integer | X    | 페이지번호            | 1          |
| numOfRows  | Integer | X    | 한 페이지 결과 수     | 10         |

### 응답 예시 (주요 필드)

```xml
<item>
  <dutyAddr>서울특별시 종로구 종로 335, 원풍빌딩 6층 (창신동)</dutyAddr>
  <dutyDivNam>의원</dutyDivNam>
  <dutyName>(의)열린의료재단동대문열린의원</dutyName>
  <dutyTel1>02-924-0875</dutyTel1>
  <wgs84Lat>37.5731036083714</wgs84Lat>
  <wgs84Lon>127.018258839394</wgs84Lon>
</item>
```

### 주요 출력 필드

| 필드명     | 설명                                          | 용도      |
| ---------- | --------------------------------------------- | --------- |
| dutyName   | 병원명                                        | 식별      |
| dutyAddr   | 주소                                          | 위치 파악 |
| wgs84Lat   | 위도                                          | 거리 계산 |
| wgs84Lon   | 경도                                          | 거리 계산 |
| dutyDivNam | 병원종별 (상급종합병원, 종합병원, 병원, 의원) | 의료 수준 |

### Python 예제

```python
import requests
import os
from dotenv import load_dotenv

load_dotenv()
API_KEY = os.getenv('PUBLICDATA_API_KEY')

url = "http://apis.data.go.kr/B552657/HsptlAsembySearchService/getHsptlMdcncListInfoInqire"

params = {
    'serviceKey': API_KEY,
    'Q0': '서울특별시',
    'Q1': '종로구',
    'pageNo': '1',
    'numOfRows': '10'
}

response = requests.get(url, params=params)
print(response.text)  # XML 응답
```

### 테스트 결과

✅ **성공** - 정상적으로 병원 목록을 조회할 수 있습니다.

---

## 3. 행정안전부 재해연보 API

### 기본 정보

- **제공기관**: 행정안전부
- **서비스명**: 재해연보 API
- **링크**: https://data.go.kr/data/15107303/openapi.do
- **응답형식**: XML

### 용도

- 내륙홍수 노출도 평가 (과거 침수 이력)
- 태풍 노출도 평가 (과거 태풍 피해)

### 주요 출력 정보

- 재난유형 (태풍, 홍수, 호우 등)
- 인명피해 (사망, 실종, 부상)
- 이재민 수
- 재산피해액
- 건물피해 (전파, 반파, 침수)
- 경작지피해

### 테스트 결과

⚠️ **실패** - 엔드포인트 오류 (500 Internal Server Error)

- 다른 엔드포인트 또는 추가 파라미터 확인 필요

---

## 4. WAMIS 유역특성 API

### 기본 정보

- **제공기관**: 국토교통부 (WAMIS)
- **서비스명**: 유역특성 정보
- **링크**: https://data.go.kr/data/15107318/openapi.do
- **응답형식**: JSON/XML

### 용도

- 내륙홍수 위해성 평가 (하천범람 위험도, 홍수량)
- 물부족 위해성 평가 (용수 취수량)

### 주요 출력 정보

- 유역면적(km²)
- 유로연장(km)
- 유출곡선지수(CN)
- 빈도별 홍수량(㎥/s) - 80년, 100년, 200년 빈도
- 생활용수/공업용수/농업용수 취수량(㎥/일)

### 테스트 결과

⚠️ **실패** - 엔드포인트 오류 (500 Internal Server Error)

- 다른 엔드포인트 또는 추가 파라미터 확인 필요

---

## 참고사항

### 성공한 API

1. ✅ **건축물대장 API** - 정상 작동
2. ✅ **병원 API** - 정상 작동

### 추가 확인 필요한 API

1. ⚠️ **재해연보 API** - 엔드포인트 재확인 필요
2. ⚠️ **WAMIS API** - 엔드포인트 재확인 필요

### 문제 해결 방안

- API 문서에서 정확한 엔드포인트 URL 확인
- 필수 파라미터 누락 여부 확인
- 공공데이터포털에서 활용신청 승인 상태 확인
