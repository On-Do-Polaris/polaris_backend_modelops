# 통계청/행정안전부 인구통계 API

## API 개요

- **출처**: 통계청 KOSIS (Korean Statistical Information Service) / 행정안전부
- **링크**:
  - KOSIS: https://kosis.kr
  - KOSIS OpenAPI: https://kosis.kr/openapi/index/index.jsp
  - 행정안전부 주민등록 인구통계: https://jumin.mois.go.kr
- **API 키**:
  - KOSIS: `Y2FlOTQ5ZjcyZjIwYjYyYzU1ZDQ1MDViZmNmOGQ1NjY=`
  - 공공데이터포털: `4b2f121a7492c996d0dca08a311bb9ae1063ae49a3ef40ed955de1f617da8bce`
- **데이터 타입**: JSON, XML, CSV, Excel
- **데이터 설명**: 시군구별 인구 통계, 인구밀도, 가구수, 인구 추계, 연령별/성별 인구

## 사용 목적

본 프로젝트에서 인구통계 API는 다음 기후 리스크 평가에 사용됩니다:

- **도시홍수 노출도 평가**: 인구밀도 분석
- **가뭄 노출도 평가**: 인구수 분석
- **물부족 노출도 평가**: 인구수, 인구 추계
- **물부족 위해성 평가**: 미래 인구 추계

## API 엔드포인트

### 1. KOSIS StatAPI (통계표 조회)

```
GET https://kosis.kr/openapi/Param/statisticsParameterData.do
```

### 2. 행정안전부 주민등록 인구통계 API

```
GET http://apis.data.go.kr/1741000/StanReginCd/getStanReginCdList
```

## 요청 파라미터

### KOSIS StatAPI 파라미터

| 파라미터 | 타입 | 필수 | 설명 | 예시 |
|---------|------|------|------|------|
| `method` | String | O | 메소드명 (고정값) | `getList` |
| `apiKey` | String | O | KOSIS API 키 | `Y2FlOTQ5...` |
| `itmId` | String | O | 항목 ID | `T2+` (총인구) |
| `objL1` | String | O | 대상 분류 레벨 1 | `ALL` |
| `objL2` | String | X | 대상 분류 레벨 2 | `11` (서울) |
| `objL3` | String | X | 대상 분류 레벨 3 | `11110` (종로구) |
| `prdSe` | String | O | 기간 구분 | `Y` (연간) |
| `startPrdDe` | String | O | 시작 기간 | `2020` |
| `endPrdDe` | String | O | 종료 기간 | `2023` |
| `orgId` | String | O | 통계청 기관 ID | `101` |
| `tblId` | String | O | 통계표 ID | `DT_1B04005N` |
| `format` | String | X | 응답 형식 (json/xml) | `json` |
| `jsonVD` | String | X | JSON value dimension | `Y` |
| `prdSel` | String | X | 기간 선택 방식 | `Y` |
| `loadingLevel` | String | X | 로딩 레벨 | `3` |

### 주요 통계표 ID (tblId)

| 통계표 ID | 설명 | 사용처 |
|----------|------|--------|
| `DT_1B04005N` | 시군구별 인구수 | 전체 리스크 |
| `DT_1B04006` | 시도별 인구밀도 | 도시홍수, 가뭄 |
| `DT_1YL20631` | 장래인구추계 (시도) | 물부족 위해성 |
| `DT_1B81A21` | 시군구별 가구수 | 노출도 평가 |

### 항목 ID (itmId)

| 항목 ID | 설명 |
|--------|------|
| `T2` | 총인구 |
| `T3` | 남자 인구 |
| `T4` | 여자 인구 |
| `T10` | 가구수 |
| `T20` | 인구밀도 (명/km²) |

## 응답 데이터

### KOSIS StatAPI 응답 (JSON)

```json
[
  {
    "TBL_ID": "DT_1B04005N",
    "TBL_NM": "시군구별 인구수",
    "C1": "2023",
    "C1_NM": "2023년",
    "C1_OBJ_NM": "시점",
    "DT": "20231231",
    "PRD_DE": "2023",
    "PRD_SE": "Y",
    "ITM_ID": "T2",
    "ITM_NM": "총인구수",
    "UNIT_NM": "명",
    "C2": "11",
    "C2_NM": "서울특별시",
    "C2_OBJ_NM": "행정구역(시도)",
    "C3": "11110",
    "C3_NM": "종로구",
    "C3_OBJ_NM": "행정구역(시군구)",
    "DT_VALUE": "145289"
  }
]
```

### 행정안전부 주민등록 인구 응답

```json
{
  "StanReginCd": [
    {
      "region_cd": "11110",
      "sido_cd": "11",
      "sgg_cd": "110",
      "umd_cd": "",
      "ri_cd": "",
      "locatadd_nm": "종로구",
      "locallow_nm": "서울특별시",
      "adpt_de": "20231231"
    }
  ]
}
```

## Python 사용 예시

### 1. KOSIS API - 시군구별 인구 조회

```python
import requests
from typing import Optional, List, Dict

def get_population_kosis(
    api_key: str,
    sido_code: str,
    sigungu_code: str,
    year: str,
    stat_code: str = "DT_1B04005N"
) -> Optional[Dict]:
    """
    KOSIS API를 통해 시군구별 인구 데이터를 조회합니다.

    Args:
        api_key: KOSIS API 키
        sido_code: 시도 코드 (2자리, 예: '11' = 서울)
        sigungu_code: 시군구 코드 (5자리, 예: '11110' = 종로구)
        year: 조회 년도 (YYYY)
        stat_code: 통계표 ID

    Returns:
        Dict: 인구 데이터
    """
    url = "https://kosis.kr/openapi/Param/statisticsParameterData.do"

    params = {
        "method": "getList",
        "apiKey": api_key,
        "itmId": "T2+",  # 총인구
        "objL1": "ALL",
        "objL2": sido_code,
        "objL3": sigungu_code,
        "format": "json",
        "jsonVD": "Y",
        "prdSe": "Y",
        "startPrdDe": year,
        "endPrdDe": year,
        "orgId": "101",
        "tblId": stat_code
    }

    try:
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()

        data = response.json()

        if data and len(data) > 0:
            result = data[0]
            return {
                '시도': result.get('C2_NM', ''),
                '시군구': result.get('C3_NM', ''),
                '년도': result.get('PRD_DE', ''),
                '총인구': int(result.get('DT_VALUE', 0)),
                '단위': result.get('UNIT_NM', '명')
            }
        else:
            print("No data found")
            return None

    except requests.exceptions.RequestException as e:
        print(f"Request failed: {e}")
        return None
    except Exception as e:
        print(f"Error: {e}")
        return None

# 사용 예시
api_key = "Y2FlOTQ5ZjcyZjIwYjYyYzU1ZDQ1MDViZmNmOGQ1NjY="

# 서울 종로구 2023년 인구 조회
population = get_population_kosis(
    api_key,
    sido_code="11",
    sigungu_code="11110",
    year="2023"
)

if population:
    print(f"지역: {population['시도']} {population['시군구']}")
    print(f"총인구: {population['총인구']:,}명")
```

### 2. 인구밀도 조회

```python
def get_population_density(
    api_key: str,
    sido_code: str,
    year: str
) -> Optional[Dict]:
    """
    시도별 인구밀도를 조회합니다.

    Args:
        api_key: KOSIS API 키
        sido_code: 시도 코드
        year: 조회 년도

    Returns:
        Dict: 인구밀도 데이터
    """
    url = "https://kosis.kr/openapi/Param/statisticsParameterData.do"

    params = {
        "method": "getList",
        "apiKey": api_key,
        "itmId": "T20+",  # 인구밀도
        "objL1": "ALL",
        "objL2": sido_code,
        "format": "json",
        "jsonVD": "Y",
        "prdSe": "Y",
        "startPrdDe": year,
        "endPrdDe": year,
        "orgId": "101",
        "tblId": "DT_1B04006"
    }

    try:
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()

        data = response.json()

        if data and len(data) > 0:
            result = data[0]
            return {
                '시도': result.get('C2_NM', ''),
                '년도': result.get('PRD_DE', ''),
                '인구밀도': float(result.get('DT_VALUE', 0)),
                '단위': '명/km²'
            }
        else:
            return None

    except Exception as e:
        print(f"Error: {e}")
        return None

# 사용 예시
density = get_population_density(api_key, sido_code="11", year="2023")
if density:
    print(f"{density['시도']} 인구밀도: {density['인구밀도']:.2f} 명/km²")
```

### 3. 장래인구추계 조회 (물부족 위해성)

```python
def get_population_projection(
    api_key: str,
    sido_code: str,
    start_year: str,
    end_year: str
) -> List[Dict]:
    """
    장래인구추계 데이터를 조회합니다.

    Args:
        api_key: KOSIS API 키
        sido_code: 시도 코드
        start_year: 시작 년도
        end_year: 종료 년도

    Returns:
        List[Dict]: 연도별 인구 추계 데이터
    """
    url = "https://kosis.kr/openapi/Param/statisticsParameterData.do"

    params = {
        "method": "getList",
        "apiKey": api_key,
        "itmId": "T2+",  # 총인구
        "objL1": "ALL",
        "objL2": sido_code,
        "format": "json",
        "jsonVD": "Y",
        "prdSe": "Y",
        "startPrdDe": start_year,
        "endPrdDe": end_year,
        "orgId": "101",
        "tblId": "DT_1YL20631"  # 장래인구추계
    }

    try:
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()

        data = response.json()

        projections = []
        for item in data:
            projections.append({
                '시도': item.get('C2_NM', ''),
                '년도': item.get('PRD_DE', ''),
                '추계인구': int(item.get('DT_VALUE', 0))
            })

        return projections

    except Exception as e:
        print(f"Error: {e}")
        return []

# 사용 예시 (2020~2050년 서울시 인구 추계)
projections = get_population_projection(
    api_key,
    sido_code="11",
    start_year="2020",
    end_year="2050"
)

for proj in projections:
    print(f"{proj['년도']}년: {proj['추계인구']:,}명")
```

### 4. 시군구별 인구 통계 일괄 조회

```python
def get_all_sigungu_population(
    api_key: str,
    sido_code: str,
    year: str
) -> List[Dict]:
    """
    특정 시도의 모든 시군구 인구를 조회합니다.

    Args:
        api_key: KOSIS API 키
        sido_code: 시도 코드
        year: 조회 년도

    Returns:
        List[Dict]: 시군구별 인구 데이터
    """
    url = "https://kosis.kr/openapi/Param/statisticsParameterData.do"

    params = {
        "method": "getList",
        "apiKey": api_key,
        "itmId": "T2+",
        "objL1": "ALL",
        "objL2": sido_code,
        "objL3": "",  # 빈 값으로 하면 모든 시군구 조회
        "format": "json",
        "jsonVD": "Y",
        "prdSe": "Y",
        "startPrdDe": year,
        "endPrdDe": year,
        "orgId": "101",
        "tblId": "DT_1B04005N"
    }

    try:
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()

        data = response.json()

        populations = []
        for item in data:
            populations.append({
                '시도': item.get('C2_NM', ''),
                '시군구': item.get('C3_NM', ''),
                '시군구코드': item.get('C3', ''),
                '년도': item.get('PRD_DE', ''),
                '총인구': int(item.get('DT_VALUE', 0))
            })

        # 인구순 정렬
        populations.sort(key=lambda x: x['총인구'], reverse=True)

        return populations

    except Exception as e:
        print(f"Error: {e}")
        return []

# 사용 예시 (서울시 전체 구 인구 조회)
seoul_populations = get_all_sigungu_population(api_key, sido_code="11", year="2023")

print(f"서울시 구별 인구 (2023년)")
print("-" * 50)
for pop in seoul_populations:
    print(f"{pop['시군구']:10s}: {pop['총인구']:>10,}명")
```

### 5. 인구 증감률 계산

```python
def calculate_population_growth_rate(
    api_key: str,
    sido_code: str,
    sigungu_code: str,
    start_year: str,
    end_year: str
) -> Optional[Dict]:
    """
    인구 증감률을 계산합니다.

    Args:
        api_key: KOSIS API 키
        sido_code: 시도 코드
        sigungu_code: 시군구 코드
        start_year: 시작 년도
        end_year: 종료 년도

    Returns:
        Dict: 인구 증감률 정보
    """
    start_pop = get_population_kosis(api_key, sido_code, sigungu_code, start_year)
    end_pop = get_population_kosis(api_key, sido_code, sigungu_code, end_year)

    if not start_pop or not end_pop:
        return None

    start_value = start_pop['총인구']
    end_value = end_pop['총인구']

    growth_rate = ((end_value - start_value) / start_value) * 100
    annual_growth_rate = growth_rate / (int(end_year) - int(start_year))

    return {
        '지역': f"{start_pop['시도']} {start_pop['시군구']}",
        '시작년도': start_year,
        '종료년도': end_year,
        '시작인구': start_value,
        '종료인구': end_value,
        '총증감률_%': round(growth_rate, 2),
        '연평균증감률_%': round(annual_growth_rate, 2)
    }

# 사용 예시
growth = calculate_population_growth_rate(
    api_key,
    sido_code="11",
    sigungu_code="11110",
    start_year="2010",
    end_year="2023"
)

if growth:
    print(f"지역: {growth['지역']}")
    print(f"기간: {growth['시작년도']} ~ {growth['종료년도']}")
    print(f"인구 변화: {growth['시작인구']:,}명 → {growth['종료인구']:,}명")
    print(f"총 증감률: {growth['총증감률_%']}%")
    print(f"연평균 증감률: {growth['연평균증감률_%']}%")
```

## 프로젝트 내 사용 위치

본 API는 다음 리스크 계산 모듈에서 사용됩니다:

1. **도시홍수 리스크** ([urban_flood_risk.py](../code/urban_flood_risk.py))
   - 인구밀도 조회 (노출도 평가)

2. **가뭄 리스크** ([drought_risk.py](../code/drought_risk.py))
   - 인구수 조회 (노출도 평가)

3. **물부족 리스크** ([water_stress_risk.py](../code/water_stress_risk.py))
   - 현재 인구수 조회 (노출도 평가)
   - 장래 인구 추계 조회 (위해성 평가)

## 주의사항

1. **API 키 관리**: API 키는 [api_key.md](api_key.md)에 별도로 관리됩니다.
2. **API 키 인코딩**: KOSIS API 키는 Base64 인코딩된 값입니다.
3. **요청 제한**: KOSIS API는 일일 요청 횟수 제한이 있을 수 있습니다.
4. **데이터 갱신**: 인구통계는 연 1회 갱신되며, 전년도 말 기준 데이터가 제공됩니다.
5. **통계표 ID**: 통계표 ID(tblId)는 KOSIS 웹사이트에서 확인 가능합니다.
6. **행정구역 코드**: 시도 코드는 2자리, 시군구 코드는 5자리입니다.

## 시도 코드 목록

| 코드 | 시도명 |
|------|--------|
| `11` | 서울특별시 |
| `26` | 부산광역시 |
| `27` | 대구광역시 |
| `28` | 인천광역시 |
| `29` | 광주광역시 |
| `30` | 대전광역시 |
| `31` | 울산광역시 |
| `36` | 세종특별자치시 |
| `41` | 경기도 |
| `42` | 강원도 |
| `43` | 충청북도 |
| `44` | 충청남도 |
| `45` | 전라북도 |
| `46` | 전라남도 |
| `47` | 경상북도 |
| `48` | 경상남도 |
| `50` | 제주특별자치도 |

## 참고 문서

- KOSIS 포털: https://kosis.kr
- KOSIS OpenAPI 가이드: https://kosis.kr/openapi/index/index.jsp
- 행정안전부 주민등록 인구통계: https://jumin.mois.go.kr
- 통계청 장래인구추계: https://kostat.go.kr
