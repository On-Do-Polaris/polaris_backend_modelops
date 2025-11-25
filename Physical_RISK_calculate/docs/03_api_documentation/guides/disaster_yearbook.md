# 행정안전부 재해연보 API

## API 개요

- **출처**: 행정안전부 (공공데이터포털)
- **링크**: https://data.go.kr/data/15107303/openapi.do
- **API 키**: `4b2f121a7492c996d0dca08a311bb9ae1063ae49a3ef40ed955de1f617da8bce`
- **데이터 타입**: XML
- **데이터 설명**: 지역별 자연재난 피해 통계 (태풍, 대설, 낙뢰, 홍수, 호우, 강풍, 풍랑, 해일, 한파 등)

## 사용 목적

본 프로젝트에서 재해연보 API는 다음 기후 리스크 평가에 사용됩니다:

- **내륙홍수 노출도 평가**: 과거 침수 이력 분석
- **태풍 노출도 평가**: 과거 태풍 피해 이력 분석
- **전체 리스크**: 지역별 자연재난 취약성 평가

## API 엔드포인트

```
GET https://api.odcloud.kr/api/disasterYearbook/v1/list
```

또는

```
GET http://apis.data.go.kr/1741000/DisasterYearbookService/getDisasterYearbook
```

## 요청 파라미터

| 파라미터 | 타입 | 필수 | 설명 | 예시 |
|---------|------|------|------|------|
| `serviceKey` | String | O | 공공데이터포털 인증키 (Decoding) | `4b2f121a...` |
| `year` | String | X | 재난 발생 년도 (YYYY) | `2023` |
| `sidoNm` | String | X | 시도명 | `서울특별시` |
| `sigunguNm` | String | X | 시군구명 | `강남구` |
| `disasterType` | String | X | 재난 유형 | `태풍`, `호우`, `홍수` |
| `pageNo` | Integer | X | 페이지 번호 (기본값: 1) | `1` |
| `numOfRows` | Integer | X | 한 페이지 결과 수 (기본값: 10, 최대: 1000) | `100` |

## 재난 유형 코드

| 유형 | 설명 | 관련 리스크 |
|------|------|------------|
| `태풍` | 태풍 피해 | 태풍 리스크 |
| `호우` | 호우 피해 | 내륙홍수, 도시홍수 |
| `홍수` | 홍수 피해 | 내륙홍수 |
| `강풍` | 강풍 피해 | 태풍 리스크 |
| `풍랑` | 풍랑 피해 | 해안홍수 |
| `해일` | 해일 피해 | 해안홍수 |
| `대설` | 대설 피해 | 기타 |
| `한파` | 한파 피해 | 극한추위 |
| `낙뢰` | 낙뢰 피해 | 기타 |

## 응답 데이터

### XML 응답 형식

```xml
<?xml version="1.0" encoding="UTF-8"?>
<response>
    <header>
        <resultCode>00</resultCode>
        <resultMsg>NORMAL_SERVICE</resultMsg>
    </header>
    <body>
        <items>
            <item>
                <year>2023</year>                     <!-- 발생년도 -->
                <sidoNm>서울특별시</sidoNm>             <!-- 시도명 -->
                <sigunguNm>강남구</sigunguNm>           <!-- 시군구명 -->
                <disasterType>호우</disasterType>       <!-- 재난유형 -->
                <occurDt>2023-07-15</occurDt>          <!-- 발생일자 -->
                <humanDmg>                             <!-- 인명피해 -->
                    <death>0</death>                   <!-- 사망 (명) -->
                    <missing>0</missing>               <!-- 실종 (명) -->
                    <injury>2</injury>                 <!-- 부상 (명) -->
                </humanDmg>
                <victim>120</victim>                    <!-- 이재민 (명) -->
                <propertyDmg>1250000</propertyDmg>      <!-- 재산피해 (천원) -->
                <buildingDmg>                          <!-- 건물피해 -->
                    <total>45</total>                  <!-- 전파 (동) -->
                    <half>12</half>                    <!-- 반파 (동) -->
                    <flood>230</flood>                 <!-- 침수 (동) -->
                </buildingDmg>
                <farmDmg>15.3</farmDmg>                <!-- 경작지피해 (ha) -->
            </item>
        </items>
        <numOfRows>10</numOfRows>
        <pageNo>1</pageNo>
        <totalCount>125</totalCount>
    </body>
</response>
```

### JSON 응답 형식 (변환 후)

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
          "year": "2023",
          "sidoNm": "서울특별시",
          "sigunguNm": "강남구",
          "disasterType": "호우",
          "occurDt": "2023-07-15",
          "humanDmg": {
            "death": 0,
            "missing": 0,
            "injury": 2
          },
          "victim": 120,
          "propertyDmg": 1250000,
          "buildingDmg": {
            "total": 45,
            "half": 12,
            "flood": 230
          },
          "farmDmg": 15.3
        }
      ],
      "numOfRows": 10,
      "pageNo": 1,
      "totalCount": 125
    }
  }
}
```

## Python 사용 예시

### 1. 재해연보 데이터 조회

```python
import requests
import xmltodict
from typing import Optional, List, Dict

def get_disaster_yearbook(
    api_key: str,
    year: Optional[str] = None,
    sido: Optional[str] = None,
    sigungu: Optional[str] = None,
    disaster_type: Optional[str] = None,
    num_of_rows: int = 100
) -> List[Dict]:
    """
    행정안전부 재해연보 데이터를 조회합니다.

    Args:
        api_key: 공공데이터포털 API 키
        year: 재난 발생 년도 (YYYY)
        sido: 시도명 (예: '서울특별시')
        sigungu: 시군구명 (예: '강남구')
        disaster_type: 재난 유형 (예: '태풍', '호우', '홍수')
        num_of_rows: 한 페이지 결과 수

    Returns:
        List[Dict]: 재해 정보 리스트
    """
    url = "http://apis.data.go.kr/1741000/DisasterYearbookService/getDisasterYearbook"

    params = {
        "serviceKey": api_key,
        "pageNo": 1,
        "numOfRows": num_of_rows
    }

    # 선택적 파라미터 추가
    if year:
        params["year"] = year
    if sido:
        params["sidoNm"] = sido
    if sigungu:
        params["sigunguNm"] = sigungu
    if disaster_type:
        params["disasterType"] = disaster_type

    try:
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()

        # XML을 딕셔너리로 변환
        data_dict = xmltodict.parse(response.content)

        # 응답 상태 확인
        header = data_dict['response']['header']
        if header['resultCode'] != '00':
            print(f"API Error: {header['resultMsg']}")
            return []

        # items 추출
        body = data_dict['response']['body']
        items = body.get('items', {}).get('item', [])

        # 단일 결과인 경우 리스트로 변환
        if isinstance(items, dict):
            items = [items]

        return items

    except requests.exceptions.RequestException as e:
        print(f"Request failed: {e}")
        return []
    except Exception as e:
        print(f"Error: {e}")
        return []

# 사용 예시
api_key = "4b2f121a7492c996d0dca08a311bb9ae1063ae49a3ef40ed955de1f617da8bce"

# 2023년 서울 지역 호우 피해 조회
disasters = get_disaster_yearbook(
    api_key,
    year="2023",
    sido="서울특별시",
    disaster_type="호우"
)

for disaster in disasters:
    print(f"발생일: {disaster.get('occurDt', 'N/A')}")
    print(f"지역: {disaster.get('sidoNm', '')} {disaster.get('sigunguNm', '')}")
    print(f"재산피해: {disaster.get('propertyDmg', 0)} 천원")
    print(f"건물침수: {disaster.get('buildingDmg', {}).get('flood', 0)} 동")
    print("---")
```

### 2. 과거 홍수 이력 분석 (내륙홍수 리스크)

```python
def analyze_flood_history(
    api_key: str,
    sido: str,
    sigungu: str,
    start_year: int = 2010,
    end_year: int = 2023
) -> Dict:
    """
    특정 지역의 과거 홍수/호우 피해 이력을 분석합니다.

    Args:
        api_key: API 키
        sido: 시도명
        sigungu: 시군구명
        start_year: 시작 년도
        end_year: 종료 년도

    Returns:
        Dict: 홍수 이력 통계
    """
    flood_types = ["호우", "홍수"]
    total_incidents = 0
    total_property_damage = 0
    total_building_flood = 0
    total_victims = 0

    for year in range(start_year, end_year + 1):
        for disaster_type in flood_types:
            disasters = get_disaster_yearbook(
                api_key,
                year=str(year),
                sido=sido,
                sigungu=sigungu,
                disaster_type=disaster_type
            )

            for disaster in disasters:
                total_incidents += 1
                total_property_damage += int(disaster.get('propertyDmg', 0))
                total_victims += int(disaster.get('victim', 0))

                building_dmg = disaster.get('buildingDmg', {})
                if isinstance(building_dmg, dict):
                    total_building_flood += int(building_dmg.get('flood', 0))

    return {
        '지역': f"{sido} {sigungu}",
        '분석기간': f"{start_year}~{end_year}",
        '총발생횟수': total_incidents,
        '총재산피해_천원': total_property_damage,
        '총건물침수_동': total_building_flood,
        '총이재민_명': total_victims,
        '연평균발생': round(total_incidents / (end_year - start_year + 1), 2)
    }

# 사용 예시
flood_stats = analyze_flood_history(
    api_key,
    sido="서울특별시",
    sigungu="강남구",
    start_year=2015,
    end_year=2023
)

print(f"지역: {flood_stats['지역']}")
print(f"분석기간: {flood_stats['분석기간']}")
print(f"총 발생 횟수: {flood_stats['총발생횟수']}회")
print(f"연평균 발생: {flood_stats['연평균발생']}회")
print(f"총 재산피해: {flood_stats['총재산피해_천원']:,}천원")
print(f"총 건물침수: {flood_stats['총건물침수_동']}동")
```

### 3. 태풍 피해 이력 분석 (태풍 리스크)

```python
def analyze_typhoon_history(
    api_key: str,
    sido: str,
    start_year: int = 2010,
    end_year: int = 2023
) -> Dict:
    """
    특정 지역의 과거 태풍 피해 이력을 분석합니다.

    Args:
        api_key: API 키
        sido: 시도명
        start_year: 시작 년도
        end_year: 종료 년도

    Returns:
        Dict: 태풍 피해 통계
    """
    typhoon_types = ["태풍", "강풍"]
    total_incidents = 0
    total_property_damage = 0
    total_human_casualties = 0

    for year in range(start_year, end_year + 1):
        for disaster_type in typhoon_types:
            disasters = get_disaster_yearbook(
                api_key,
                year=str(year),
                sido=sido,
                disaster_type=disaster_type
            )

            for disaster in disasters:
                total_incidents += 1
                total_property_damage += int(disaster.get('propertyDmg', 0))

                human_dmg = disaster.get('humanDmg', {})
                if isinstance(human_dmg, dict):
                    total_human_casualties += int(human_dmg.get('death', 0))
                    total_human_casualties += int(human_dmg.get('missing', 0))
                    total_human_casualties += int(human_dmg.get('injury', 0))

    return {
        '지역': sido,
        '분석기간': f"{start_year}~{end_year}",
        '총태풍발생횟수': total_incidents,
        '총재산피해_천원': total_property_damage,
        '총인명피해_명': total_human_casualties,
        '연평균발생': round(total_incidents / (end_year - start_year + 1), 2)
    }

# 사용 예시
typhoon_stats = analyze_typhoon_history(
    api_key,
    sido="부산광역시",
    start_year=2015,
    end_year=2023
)

print(f"지역: {typhoon_stats['지역']}")
print(f"총 태풍 발생: {typhoon_stats['총태풍발생횟수']}회")
print(f"연평균 발생: {typhoon_stats['연평균발생']}회")
print(f"총 재산피해: {typhoon_stats['총재산피해_천원']:,}천원")
```

### 4. 노출도 점수 계산

```python
def calculate_disaster_exposure_score(
    api_key: str,
    sido: str,
    sigungu: str,
    disaster_type: str,
    years: int = 10
) -> float:
    """
    과거 재해 이력 기반 노출도 점수를 계산합니다.

    Args:
        api_key: API 키
        sido: 시도명
        sigungu: 시군구명
        disaster_type: 재난 유형
        years: 분석 기간 (년)

    Returns:
        float: 노출도 점수 (0~100)
    """
    from datetime import datetime

    end_year = datetime.now().year
    start_year = end_year - years

    disasters = []
    for year in range(start_year, end_year + 1):
        year_disasters = get_disaster_yearbook(
            api_key,
            year=str(year),
            sido=sido,
            sigungu=sigungu,
            disaster_type=disaster_type
        )
        disasters.extend(year_disasters)

    if not disasters:
        return 0.0

    # 발생 빈도 점수 (0~40점)
    frequency = len(disasters)
    frequency_score = min(frequency * 5, 40)

    # 재산피해 점수 (0~30점)
    total_property_dmg = sum(int(d.get('propertyDmg', 0)) for d in disasters)
    avg_property_dmg = total_property_dmg / len(disasters) if disasters else 0
    property_score = min(avg_property_dmg / 1000000, 30)  # 10억원 = 30점

    # 건물피해 점수 (0~30점)
    total_building_flood = 0
    for d in disasters:
        building_dmg = d.get('buildingDmg', {})
        if isinstance(building_dmg, dict):
            total_building_flood += int(building_dmg.get('flood', 0))

    avg_building_flood = total_building_flood / len(disasters) if disasters else 0
    building_score = min(avg_building_flood / 10, 30)  # 100동 = 30점

    total_score = frequency_score + property_score + building_score

    return round(min(total_score, 100), 2)

# 사용 예시
exposure_score = calculate_disaster_exposure_score(
    api_key,
    sido="서울특별시",
    sigungu="강남구",
    disaster_type="호우",
    years=10
)

print(f"노출도 점수: {exposure_score}/100")
```

## 프로젝트 내 사용 위치

본 API는 다음 리스크 계산 모듈에서 사용됩니다:

1. **내륙홍수 리스크** ([inland_flood_risk.py](../code/inland_flood_risk.py))
   - 과거 침수 이력 분석
   - 홍수 노출도 평가

2. **태풍 리스크** ([typhoon_risk.py](../code/typhoon_risk.py))
   - 과거 태풍 피해 이력 분석
   - 태풍 노출도 평가

3. **전체 리스크**
   - 지역별 자연재난 취약성 분석

## 주의사항

1. **API 키 관리**: API 키는 [api_key.md](api_key.md)에 별도로 관리됩니다.
2. **XML 파싱**: 응답 데이터가 XML 형식이므로 `xmltodict` 라이브러리 설치 필요 (`pip install xmltodict`).
3. **데이터 갱신**: 재해연보 데이터는 연 1회 갱신되며, 최신 데이터는 전년도까지 제공됩니다.
4. **결측값 처리**: 피해가 없는 경우 빈 값 또는 `0`으로 반환되므로 예외 처리가 필요합니다.
5. **지역명 정확도**: 시도명, 시군구명은 정확한 행정구역명을 사용해야 합니다 (예: '서울특별시', '부산광역시').

## 시도명 목록

- 서울특별시
- 부산광역시
- 대구광역시
- 인천광역시
- 광주광역시
- 대전광역시
- 울산광역시
- 세종특별자치시
- 경기도
- 강원도
- 충청북도
- 충청남도
- 전라북도
- 전라남도
- 경상북도
- 경상남도
- 제주특별자치도

## 참고 문서

- 공공데이터포털 재해연보 API: https://data.go.kr/data/15107303/openapi.do
- 행정안전부 재난안전데이터: https://www.safetydata.go.kr
- 재해연보 통계: https://www.mois.go.kr
