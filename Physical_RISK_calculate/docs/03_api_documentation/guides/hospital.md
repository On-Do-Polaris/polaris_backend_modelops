# 국립중앙의료원 전국 병·의원 찾기 서비스 API 요약

## 📋 개요

- **제공기관**: 국립중앙의료원
- **API 유형**: REST
- **데이터포맷**: XML
- **Base URL**: `https://apis.data.go.kr/B552657/HsptlAsembySearchService`
- **인증**: 공공데이터포털 API Key 필요
- **트래픽**: 개발 1,000건/일, 운영 활용사례 등록시 증가 가능
- **활용기간**: 2025-11-13 ~ 2027-11-13

---

## 🔑 API 인증키

```
일반 인증키: 4b2f121a7492c996d0dca08a311bb9ae1063ae49a3ef40ed955de1f617da8bce
```

⚠️ **주의**: API 환경에 따라 Encoding/Decoding된 인증키를 사용해야 할 수 있음

---

## 🏥 API 엔드포인트

### 병·의원 목록 조회 `/getHsptlMdcncListInfoInqire`

병·의원 정보를 시도/시군구/진료요일/기관별/진료과목별로 조회

**요청 URL**

```
http://apis.data.go.kr/B552657/HsptlAsembySearchService/getHsptlMdcncListInfoInqire
```

---

## 📝 요청 파라미터

| 파라미터     | 변수명       | 필수 | 설명                    | 예시             |
| ------------ | ------------ | ---- | ----------------------- | ---------------- |
| 서비스키     | `serviceKey` | ✅   | 공공데이터 인증키       | `YOUR_API_KEY`   |
| 주소(시도)   | `Q0`         | ❌   | 시도명                  | `서울특별시`     |
| 주소(시군구) | `Q1`         | ❌   | 시군구명                | `강남구`         |
| 기관구분     | `QZ`         | ❌   | B:병원, C:의원          | `B`              |
| 진료과목     | `QD`         | ❌   | D001~D029 (코드표 참조) | `D001`           |
| 진료요일     | `QT`         | ❌   | 1~7(월~일), 8(공휴일)   | `1`              |
| 기관명       | `QN`         | ❌   | 병원/의원명             | `서울대학교병원` |
| 순서         | `ORD`        | ❌   | 정렬순서                | -                |
| 페이지번호   | `pageNo`     | ❌   | 페이지 번호             | `1`              |
| 목록건수     | `numOfRows`  | ❌   | 페이지당 행 수          | `10`             |

---

## 🔍 코드 참조

### 기관구분 코드 (QZ)

| 코드 | 명칭 |
| ---- | ---- |
| B    | 병원 |
| C    | 의원 |

### 진료과목 코드 (QD)

CODE_MST의 'D000' 참조 (D001~D029)

- 상세 코드는 별도 코드표 확인 필요

### 진료요일 코드 (QT)

| 코드 | 요일   |
| ---- | ------ |
| 1    | 월요일 |
| 2    | 화요일 |
| 3    | 수요일 |
| 4    | 목요일 |
| 5    | 금요일 |
| 6    | 토요일 |
| 7    | 일요일 |
| 8    | 공휴일 |

---

## 💡 Vulnerability 산출 활용

### 병원 접근성 평가

- **목적**: 폭염/한파 시 응급의료 접근성 평가
- **활용 파라미터**:
  - `Q0`, `Q1`: 사업장 위치 기준 시도/시군구
  - `QD`: 응급의학과 코드
- **산출 방법**: 사업장 좌표에서 가장 가까운 병원까지의 거리

---

## 🔍 사용 예시

### Python 예시

```python
import requests
import xml.etree.ElementTree as ET

API_KEY = "4b2f121a7492c996d0dca08a311bb9ae1063ae49a3ef40ed955de1f617da8bce"
BASE_URL = "http://apis.data.go.kr/B552657/HsptlAsembySearchService"

def get_hospitals(sido, sigungu, institution_type="B", page_no=1, num_of_rows=10):
    """병원 목록 조회"""
    endpoint = f"{BASE_URL}/getHsptlMdcncListInfoInqire"

    params = {
        "serviceKey": API_KEY,
        "Q0": sido,          # 시도
        "Q1": sigungu,       # 시군구
        "QZ": institution_type,  # B:병원, C:의원
        "pageNo": page_no,
        "numOfRows": num_of_rows
    }

    response = requests.get(endpoint, params=params)

    # XML 파싱
    root = ET.fromstring(response.content)

    hospitals = []
    for item in root.findall('.//item'):
        hospital = {
            'name': item.find('dutyName').text if item.find('dutyName') is not None else None,
            'addr': item.find('dutyAddr').text if item.find('dutyAddr') is not None else None,
            'tel': item.find('dutyTel1').text if item.find('dutyTel1') is not None else None,
        }
        hospitals.append(hospital)

    return hospitals

# 예시: 서울 강남구 병원 조회
hospitals = get_hospitals("서울특별시", "강남구", "B")

for hospital in hospitals:
    print(f"병원명: {hospital['name']}")
    print(f"주소: {hospital['addr']}")
    print(f"전화: {hospital['tel']}")
    print("---")
```

### 응급의료기관만 조회

```python
def get_emergency_hospitals(sido, sigungu):
    """응급의학과가 있는 병원 조회"""
    params = {
        "serviceKey": API_KEY,
        "Q0": sido,
        "Q1": sigungu,
        "QD": "D026",  # 응급의학과 코드 (실제 코드는 확인 필요)
        "numOfRows": 100
    }

    endpoint = f"{BASE_URL}/getHsptlMdcncListInfoInqire"
    response = requests.get(endpoint, params=params)

    return response.content
```

---

## ⚠️ 주의사항

1. **응답 포맷**:

   - XML 형식으로만 제공
   - JSON 변환 필요시 별도 파싱 작업 필요

2. **좌표 정보**:

   - API 응답에 위경도가 포함되어 있는지 확인 필요
   - 없을 경우 주소 기반 Geocoding 필요

3. **API 호출 제한**:

   - 개발계정: 일 1,000건
   - 대량 조회 시 페이징 처리 필수

4. **진료과목 코드**:

   - 별도 코드표(CODE_MST) 확인 필요
   - 참고문서에서 상세 코드 확인

5. **인증키 처리**:
   - URL Encoding/Decoding 이슈 발생 가능
   - 403 에러 발생시 인증키 인코딩 방식 변경 시도

---

## 📚 참고 링크

- [공공데이터포털](https://www.data.go.kr/data/15000736/openapi.do)
- [API 활용가이드](참고문서: NIA-IFT-OpenAPI활용가이드-01.국립중앙의료원-병의원찾기서비스.hwp)

---

## 🔄 XML 응답 예시 구조

```xml
<response>
  <header>
    <resultCode>00</resultCode>
    <resultMsg>NORMAL SERVICE</resultMsg>
  </header>
  <body>
    <items>
      <item>
        <dutyName>병원명</dutyName>
        <dutyAddr>주소</dutyAddr>
        <dutyTel1>전화번호</dutyTel1>
        <wgs84Lon>경도</wgs84Lon>
        <wgs84Lat>위도</wgs84Lat>
      </item>
    </items>
    <numOfRows>10</numOfRows>
    <pageNo>1</pageNo>
    <totalCount>100</totalCount>
  </body>
</response>
```

**주의**: 실제 응답 필드명은 공식 문서 확인 필요
