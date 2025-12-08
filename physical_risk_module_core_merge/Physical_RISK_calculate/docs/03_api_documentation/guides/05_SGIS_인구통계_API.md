# SGIS (통계지리정보서비스) 인구통계 API 가이드

## 개요

**SGIS (Statistical Geographic Information Service)**는 통계청에서 제공하는 통계지리정보서비스로, **읍면동 단위의 상세한 인구통계 데이터**를 제공합니다.

- **제공기관**: 통계청
- **데이터 출처**: 인구주택총조사
- **API 유형**: REST API (JSON)
- **인증 방식**: OAuth 2.0 (Access Token)

## 주요 특징

✅ **읍면동 단위 인구 데이터** 제공  
✅ **성별 인구통계** 제공 (전체/남자/여자)  
✅ **연도별 데이터** 제공 (2015년 ~ 2023년)  
✅ **행정구역 계층 조회** 가능 (시도 → 시군구 → 읍면동)

## API 엔드포인트

### 1. 인증 (OAuth Token 발급)

**요청 URL**

```
https://sgisapi.kostat.go.kr/OpenAPI3/auth/authentication.json
```

**요청 파라미터**

| 파라미터          | 타입   | 필수 | 설명          | 예시                   |
| ----------------- | ------ | ---- | ------------- | ---------------------- |
| `consumer_key`    | String | ✓    | 서비스 ID     | `4bcd973fb05e4701b46e` |
| `consumer_secret` | String | ✓    | 서비스 Secret | `cc02b9af51ee4ddfbfeb` |

**응답 예시**

```json
{
  "id": "API_0101",
  "result": {
    "accessToken": "9c67c1ac-4bab-45a6-8xxx",
    "accessTimeout": "1763826686298"
  },
  "errMsg": "Success",
  "errCd": 0
}
```

### 2. 인구통계 조회

**요청 URL**

```
https://sgisapi.kostat.go.kr/OpenAPI3/stats/searchpopulation.json
```

**요청 파라미터**

| 파라미터      | 타입   | 필수 | 설명                                                                                       | 예시                      |
| ------------- | ------ | ---- | ------------------------------------------------------------------------------------------ | ------------------------- |
| `accessToken` | String | ✓    | OAuth 인증 토큰                                                                            | `9c67c1ac-4bab-45a6-8xxx` |
| `year`        | String | ✓    | 기준연도                                                                                   | `2023`                    |
| `adm_cd`      | String | 선택 | 행정구역코드<br>- 미입력: 전국 시도<br>- 2자리: 시도<br>- 5자리: 시군구<br>- 8자리: 읍면동 | `11110` (종로구)          |
| `low_search`  | String | 선택 | 하위 통계 정보<br>- 0: 해당 행정구역만<br>- 1: 1단계 하위<br>- 2: 2단계 하위               | `1`                       |
| `gender`      | String | 선택 | 성별<br>- 0: 전체 (기본값)<br>- 1: 남자<br>- 2: 여자                                       | `0`                       |
| `age_type`    | String | 선택 | 연령타입 코드                                                                              | -                         |
| `edu_level`   | String | 선택 | 교육정도 (2010년까지만)                                                                    | -                         |
| `mrg_state`   | String | 선택 | 혼인상태 (2010년까지만)                                                                    | -                         |

**응답 예시**

```json
{
  "id": "API_0302",
  "result": [
    {
      "adm_cd": "11110510",
      "adm_nm": "월계1동",
      "population": "22158"
    },
    {
      "adm_cd": "11110520",
      "adm_nm": "월계2동",
      "population": "25090"
    }
  ],
  "errMsg": "Success",
  "errCd": 0
}
```

## 사용 예제

### Python

```python
import requests

# 1. OAuth 토큰 발급
auth_url = "https://sgisapi.kostat.go.kr/OpenAPI3/auth/authentication.json"
auth_params = {
    'consumer_key': 'YOUR_SERVICE_ID',
    'consumer_secret': 'YOUR_SECURITY_KEY'
}
auth_response = requests.get(auth_url, params=auth_params)
access_token = auth_response.json()['result']['accessToken']

# 2. 인구통계 조회 (서울 강남구 읍면동별)
stats_url = "https://sgisapi.kostat.go.kr/OpenAPI3/stats/searchpopulation.json"
stats_params = {
    'accessToken': access_token,
    'year': '2023',
    'adm_cd': '11230',  # 서울 강남구
    'low_search': '1',  # 1단계 하위 (읍면동)
    'gender': '0'  # 전체
}
stats_response = requests.get(stats_url, params=stats_params)
data = stats_response.json()

# 결과 출력
for item in data['result']:
    print(f"{item['adm_nm']}: {item['population']}명")
```

## 테스트 결과

### ✅ 성공한 테스트 (3/3)

#### 1. 읍면동별 인구통계 조회

- **지역**: 서울특별시 강남구 (행정구역코드: 11230)
- **조회 결과**: 22개 읍면동
- **데이터 예시**:
  - 신사동: 14,143명
  - 삼성1동: 11,344명
  - 삼성2동: 28,760명
  - 대치1동: 22,447명
  - 역삼1동: 33,619명
  - 역삼2동: 34,689명

#### 2. 특정 읍면동 상세 조회

- **지역**: 서울 강남구 삼성1동 (행정구역코드: 11230580)
- **인구수**: 11,344명

#### 3. 성별 인구통계 조회

- **지역**: 서울 종로구 종로1·2·3·4가동 (행정구역코드: 11010610)
- **전체**: 6,901명
- **남자**: 3,810명
- **여자**: 3,091명

## 행정구역코드 체계

| 자릿수 | 구분   | 예시       | 설명                      |
| ------ | ------ | ---------- | ------------------------- |
| 2자리  | 시도   | `11`       | 서울특별시                |
| 5자리  | 시군구 | `11230`    | 서울특별시 강남구         |
| 8자리  | 읍면동 | `11230580` | 서울특별시 강남구 삼성1동 |

### 주요 시도 코드 (2024년 기준)

| 코드 | 시도명         |
| ---- | -------------- |
| `11` | 서울특별시     |
| `21` | 부산광역시     |
| `22` | 대구광역시     |
| `23` | 인천광역시     |
| `24` | 광주광역시     |
| `25` | 대전광역시     |
| `26` | 울산광역시     |
| `29` | 세종특별자치시 |
| `31` | 경기도         |
| `32` | 강원특별자치도 |
| `33` | 충청북도       |
| `34` | 충청남도       |
| `35` | 전북특별자치도 |
| `36` | 전라남도       |
| `37` | 경상북도       |
| `38` | 경상남도       |
| `39` | 제주특별자치도 |

### 시군구 코드 예시 (서울)

| 코드    | 시군구명 |
| ------- | -------- |
| `11010` | 종로구   |
| `11230` | 강남구   |
| `11110` | 노원구   |

### 읍면동 코드 예시

| 코드       | 읍면동명                    |
| ---------- | --------------------------- |
| `11230580` | 서울 강남구 삼성1동         |
| `11010610` | 서울 종로구 종로1·2·3·4가동 |
| `25040590` | 대전 유성구 노은1동         |

**⚠️ 중요:**

- SGIS API는 `SGIS 행정구역 API (OpenAPI3/addr/stage.json)`를 통해 최신 코드 조회 필요
- 다른 공공데이터 API와 코드 체계가 다를 수 있음 (예: 대전광역시 코드가 `30`이 아닌 `25`)
- 행정구역 통폐합으로 코드가 변경될 수 있으므로 API를 통한 확인 권장

## 활용 사례

### 1. 기후리스크 분석

- 읍면동 단위 인구밀도 분석
- 취약계층(고령자, 영유아) 비율 산정
- 재난 대응 우선순위 설정

### 2. 리스크 스코어링

```python
# V_exposure (노출도) 계산
# 인구밀도가 높을수록 노출도 증가
population_density = total_population / area
V_exposure = min(population_density / 10000, 1.0)
```

### 3. 시나리오별 영향 분석

- SSP126/245/370/585 시나리오별 인구 영향 평가
- 읍면동별 기후리스크 우선순위 분석

## 주의사항

1. **Access Token 만료**

   - 토큰은 일정 시간 후 만료됨 (`accessTimeout` 참고)
   - 만료 시 재발급 필요

2. **행정구역 변경**

   - 행정구역 통폐합으로 일부 코드가 변경될 수 있음
   - 최신 행정구역코드 확인 필요

3. **데이터 제공 범위**

   - 2015년 이후: 교육정도, 혼인상태 정보 미제공
   - 일부 통계는 2010년까지만 제공

4. **API 사용량 제한**
   - 일일 호출 횟수 제한 있음
   - 대량 조회 시 주의 필요

## 관련 링크

- **SGIS 공식 사이트**: https://sgis.kostat.go.kr
- **API 문서**: https://sgis.kostat.go.kr/developer/html/newOpenApi/api/dataApi/addressBoundary.html
- **통계청**: https://kostat.go.kr

## 환경변수 설정

```bash
# .env 파일
SGIS_SERVICE_ID=your_service_id_here
SGIS_SECURITY_KEY=your_security_key_here
```

## 에러 코드

| 코드   | 메시지                          | 설명                   |
| ------ | ------------------------------- | ---------------------- |
| `0`    | Success                         | 정상 처리              |
| `-100` | 인증키가 유효하지 않습니다      | Service ID/Secret 오류 |
| `-101` | 액세스 토큰이 유효하지 않습니다 | 토큰 만료 또는 오류    |
| `-200` | 검색결과가 존재하지 않습니다    | 잘못된 행정구역코드    |

---

**작성일**: 2025-11-22  
**테스트 환경**: Python 3.x, requests 라이브러리  
**API 버전**: OpenAPI 3.0
