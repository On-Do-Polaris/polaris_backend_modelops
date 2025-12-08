# DART 전자공시 (OpenDart) API

## API 개요

- **출처**: 금융감독원 전자공시시스템 (DART - Data Analysis, Retrieval and Transfer System)
- **링크**:
  - DART 포털: https://dart.fss.or.kr
  - OpenDart API: https://opendart.fss.or.kr
- **API 키**: (별도 발급 필요 - https://opendart.fss.or.kr 가입 후 신청)
- **데이터 타입**: JSON, XML
- **데이터 설명**: 상장기업 재무제표 (자산총액, 유형자산, 재고자산 등), 사업보고서, 분기/반기보고서

## 사용 목적

본 프로젝트에서 DART API는 다음 용도로 사용됩니다:

- **보고서 작성**: 기업 재무정보, 자산가치 평가
- **태풍 노출도 평가 (선택적)**: 자산총액 기반 노출도 평가

## API 엔드포인트

### 1. 공시정보 검색 API

```
GET https://opendart.fss.or.kr/api/list.json
```

### 2. 사업보고서 주요정보 API

```
GET https://opendart.fss.or.kr/api/company.json
```

### 3. 단일회사 전체 재무제표 API

```
GET https://opendart.fss.or.kr/api/fnlttSinglAcnt.json
```

### 4. 단일회사 주요계정 API

```
GET https://opendart.fss.or.kr/api/fnlttSinglAcntAll.json
```

### 5. 고유번호 API

```
GET https://opendart.fss.or.kr/api/corpCode.xml
```

## 요청 파라미터

### 공시정보 검색 API 파라미터

| 파라미터 | 타입 | 필수 | 설명 | 예시 |
|---------|------|------|------|------|
| `crtfc_key` | String | O | API 인증키 | `xxxxxxxx...` |
| `corp_code` | String | X | 고유번호 (8자리) | `00126380` |
| `bgn_de` | String | X | 검색 시작일 (YYYYMMDD) | `20230101` |
| `end_de` | String | X | 검색 종료일 (YYYYMMDD) | `20231231` |
| `pblntf_ty` | String | X | 공시유형 | `A` (정기공시) |
| `page_no` | Integer | X | 페이지 번호 (기본값: 1) | `1` |
| `page_count` | Integer | X | 페이지당 건수 (기본값: 10, 최대: 100) | `100` |

### 단일회사 전체 재무제표 API 파라미터

| 파라미터 | 타입 | 필수 | 설명 | 예시 |
|---------|------|------|------|------|
| `crtfc_key` | String | O | API 인증키 | `xxxxxxxx...` |
| `corp_code` | String | O | 고유번호 (8자리) | `00126380` |
| `bsns_year` | String | O | 사업연도 (YYYY) | `2023` |
| `reprt_code` | String | O | 보고서 코드 | `11011` (사업보고서) |
| `fs_div` | String | O | 개별/연결 구분 | `CFS` (연결재무제표) |

### 보고서 코드

| 코드 | 보고서 종류 |
|------|------------|
| `11011` | 사업보고서 |
| `11012` | 반기보고서 |
| `11013` | 1분기보고서 |
| `11014` | 3분기보고서 |

### 재무제표 구분 코드

| 코드 | 구분 |
|------|------|
| `OFS` | 재무제표 (개별) |
| `CFS` | 연결재무제표 |

## 응답 데이터

### 재무제표 응답 (JSON)

```json
{
  "status": "000",
  "message": "정상",
  "list": [
    {
      "rcept_no": "20230316000001",
      "reprt_code": "11011",
      "bsns_year": "2023",
      "corp_code": "00126380",
      "stock_code": "005930",
      "account_nm": "자산총계",
      "account_id": "ifrs-full_Assets",
      "fs_div": "CFS",
      "fs_nm": "연결재무상태표",
      "sj_div": "BS",
      "sj_nm": "재무상태표",
      "thstrm_nm": "제54기",
      "thstrm_dt": "2023.12.31",
      "thstrm_amount": "448478456000000",
      "thstrm_add_amount": "",
      "frmtrm_nm": "제53기",
      "frmtrm_dt": "2022.12.31",
      "frmtrm_amount": "426971537000000",
      "frmtrm_add_amount": "",
      "bfefrmtrm_nm": "제52기",
      "bfefrmtrm_dt": "2021.12.31",
      "bfefrmtrm_amount": "399036953000000",
      "ord": "1",
      "currency": "KRW"
    },
    {
      "account_nm": "유형자산",
      "account_id": "ifrs-full_PropertyPlantAndEquipment",
      "thstrm_amount": "135853465000000",
      ...
    },
    {
      "account_nm": "재고자산",
      "account_id": "ifrs-full_Inventories",
      "thstrm_amount": "52670805000000",
      ...
    }
  ]
}
```

### 회사 정보 응답

```json
{
  "status": "000",
  "message": "정상",
  "corp_code": "00126380",
  "corp_name": "삼성전자",
  "corp_name_eng": "SAMSUNG ELECTRONICS CO., LTD.",
  "stock_name": "삼성전자",
  "stock_code": "005930",
  "ceo_nm": "한종희, 경계현",
  "corp_cls": "Y",
  "jurir_no": "1301110006246",
  "bizr_no": "1248100998",
  "adres": "경기도 수원시 영통구 삼성로 129 (매탄동)",
  "hm_url": "http://www.samsung.com/sec",
  "ir_url": "http://www.samsung.com/sec/ir",
  "phn_no": "031-200-1114",
  "fax_no": "031-200-7538",
  "induty_code": "264",
  "est_dt": "19690113",
  "acc_mt": "12"
}
```

## Python 사용 예시

### 1. 고유번호 조회

```python
import requests
import zipfile
import io
import xml.etree.ElementTree as ET
from typing import Optional, Dict

def get_corp_code(api_key: str, corp_name: str) -> Optional[str]:
    """
    회사명으로 DART 고유번호를 조회합니다.

    Args:
        api_key: OpenDart API 키
        corp_name: 회사명 (예: '삼성전자')

    Returns:
        str: 고유번호 (8자리) 또는 None
    """
    url = "https://opendart.fss.or.kr/api/corpCode.xml"

    params = {
        "crtfc_key": api_key
    }

    try:
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()

        # ZIP 압축 해제
        zip_file = zipfile.ZipFile(io.BytesIO(response.content))
        xml_data = zip_file.read('CORPCODE.xml')

        # XML 파싱
        root = ET.fromstring(xml_data)

        # 회사명으로 검색
        for corp in root.findall('list'):
            name = corp.find('corp_name').text
            if corp_name in name:
                corp_code = corp.find('corp_code').text
                stock_code = corp.find('stock_code').text
                print(f"찾은 회사: {name}")
                print(f"고유번호: {corp_code}")
                print(f"종목코드: {stock_code}")
                return corp_code

        print(f"'{corp_name}' 회사를 찾을 수 없습니다.")
        return None

    except Exception as e:
        print(f"Error: {e}")
        return None

# 사용 예시
api_key = "YOUR_DART_API_KEY"
corp_code = get_corp_code(api_key, "삼성전자")
```

### 2. 재무제표 조회

```python
from typing import List

def get_financial_statement(
    api_key: str,
    corp_code: str,
    bsns_year: str,
    reprt_code: str = "11011",
    fs_div: str = "CFS"
) -> List[Dict]:
    """
    기업의 재무제표를 조회합니다.

    Args:
        api_key: OpenDart API 키
        corp_code: 고유번호 (8자리)
        bsns_year: 사업연도 (YYYY)
        reprt_code: 보고서 코드 (11011=사업보고서)
        fs_div: 재무제표 구분 (CFS=연결, OFS=개별)

    Returns:
        List[Dict]: 재무제표 항목 리스트
    """
    url = "https://opendart.fss.or.kr/api/fnlttSinglAcnt.json"

    params = {
        "crtfc_key": api_key,
        "corp_code": corp_code,
        "bsns_year": bsns_year,
        "reprt_code": reprt_code,
        "fs_div": fs_div
    }

    try:
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()

        data = response.json()

        if data['status'] == '000':
            return data['list']
        else:
            print(f"API Error: {data['message']}")
            return []

    except Exception as e:
        print(f"Error: {e}")
        return []

# 사용 예시
financial_data = get_financial_statement(
    api_key,
    corp_code="00126380",  # 삼성전자
    bsns_year="2023"
)

for item in financial_data[:5]:  # 처음 5개 항목만 출력
    print(f"{item['account_nm']}: {item['thstrm_amount']} {item['currency']}")
```

### 3. 주요 재무지표 추출

```python
def extract_key_financials(
    api_key: str,
    corp_code: str,
    bsns_year: str
) -> Dict:
    """
    주요 재무지표를 추출합니다.

    Args:
        api_key: OpenDart API 키
        corp_code: 고유번호
        bsns_year: 사업연도

    Returns:
        Dict: 주요 재무지표
    """
    financial_data = get_financial_statement(api_key, corp_code, bsns_year)

    if not financial_data:
        return {}

    key_accounts = {
        '자산총계': 'ifrs-full_Assets',
        '유형자산': 'ifrs-full_PropertyPlantAndEquipment',
        '재고자산': 'ifrs-full_Inventories',
        '매출액': 'ifrs-full_Revenue',
        '영업이익': 'ifrs-full_ProfitLossFromOperatingActivities',
        '당기순이익': 'ifrs-full_ProfitLoss'
    }

    result = {
        '사업연도': bsns_year,
        '회사코드': corp_code
    }

    for item in financial_data:
        account_id = item.get('account_id', '')
        account_nm = item.get('account_nm', '')

        for key, value in key_accounts.items():
            if value in account_id or key in account_nm:
                amount = item.get('thstrm_amount', '0')
                try:
                    result[key] = int(amount) if amount else 0
                except:
                    result[key] = 0

    return result

# 사용 예시
key_financials = extract_key_financials(
    api_key,
    corp_code="00126380",
    bsns_year="2023"
)

print(f"=== {key_financials['사업연도']}년 주요 재무지표 ===")
for key, value in key_financials.items():
    if key not in ['사업연도', '회사코드']:
        print(f"{key}: {value:,}원")
```

### 4. 자산가치 평가 (태풍 리스크용)

```python
def calculate_asset_value(
    api_key: str,
    corp_code: str,
    bsns_year: str
) -> Dict:
    """
    기업의 자산가치를 평가합니다 (태풍 노출도 평가용).

    Args:
        api_key: OpenDart API 키
        corp_code: 고유번호
        bsns_year: 사업연도

    Returns:
        Dict: 자산가치 정보
    """
    financials = extract_key_financials(api_key, corp_code, bsns_year)

    if not financials:
        return {}

    total_assets = financials.get('자산총계', 0)
    tangible_assets = financials.get('유형자산', 0)
    inventory = financials.get('재고자산', 0)

    # 물리적 리스크 노출 자산 (유형자산 + 재고자산)
    physical_risk_assets = tangible_assets + inventory

    # 자산 집중도 (물리적 리스크 자산 / 총자산)
    asset_concentration = (physical_risk_assets / total_assets * 100) if total_assets > 0 else 0

    return {
        '총자산_백만원': round(total_assets / 1_000_000),
        '유형자산_백만원': round(tangible_assets / 1_000_000),
        '재고자산_백만원': round(inventory / 1_000_000),
        '물리적리스크자산_백만원': round(physical_risk_assets / 1_000_000),
        '자산집중도_%': round(asset_concentration, 2)
    }

# 사용 예시
asset_value = calculate_asset_value(
    api_key,
    corp_code="00126380",
    bsns_year="2023"
)

print("=== 자산가치 평가 ===")
print(f"총자산: {asset_value['총자산_백만원']:,} 백만원")
print(f"유형자산: {asset_value['유형자산_백만원']:,} 백만원")
print(f"재고자산: {asset_value['재고자산_백만원']:,} 백만원")
print(f"물리적 리스크 노출 자산: {asset_value['물리적리스크자산_백만원']:,} 백만원")
print(f"자산 집중도: {asset_value['자산집중도_%']}%")
```

### 5. 연도별 재무 추이 분석

```python
def analyze_financial_trend(
    api_key: str,
    corp_code: str,
    start_year: int,
    end_year: int
) -> List[Dict]:
    """
    연도별 재무 추이를 분석합니다.

    Args:
        api_key: OpenDart API 키
        corp_code: 고유번호
        start_year: 시작 년도
        end_year: 종료 년도

    Returns:
        List[Dict]: 연도별 재무 데이터
    """
    trend_data = []

    for year in range(start_year, end_year + 1):
        financials = extract_key_financials(api_key, corp_code, str(year))

        if financials:
            trend_data.append(financials)

    return trend_data

# 사용 예시
trend = analyze_financial_trend(
    api_key,
    corp_code="00126380",
    start_year=2020,
    end_year=2023
)

print("=== 연도별 재무 추이 ===")
for data in trend:
    print(f"{data['사업연도']}년: 자산총계 {data.get('자산총계', 0):,}원")
```

### 6. 회사 기본정보 조회

```python
def get_company_info(api_key: str, corp_code: str) -> Dict:
    """
    회사 기본정보를 조회합니다.

    Args:
        api_key: OpenDart API 키
        corp_code: 고유번호

    Returns:
        Dict: 회사 기본정보
    """
    url = "https://opendart.fss.or.kr/api/company.json"

    params = {
        "crtfc_key": api_key,
        "corp_code": corp_code
    }

    try:
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()

        data = response.json()

        if data['status'] == '000':
            return data
        else:
            print(f"API Error: {data['message']}")
            return {}

    except Exception as e:
        print(f"Error: {e}")
        return {}

# 사용 예시
company_info = get_company_info(api_key, corp_code="00126380")

if company_info:
    print(f"회사명: {company_info['corp_name']}")
    print(f"종목코드: {company_info['stock_code']}")
    print(f"대표자: {company_info['ceo_nm']}")
    print(f"주소: {company_info['adres']}")
    print(f"설립일: {company_info['est_dt']}")
```

## 프로젝트 내 사용 위치

본 API는 다음 용도로 사용됩니다:

1. **보고서 작성**
   - 기업 재무정보 조회
   - 자산가치 평가
   - 재무 건전성 분석

2. **태풍 리스크 (선택적)** ([typhoon_risk.py](../code/typhoon_risk.py))
   - 자산총액 기반 노출도 평가
   - 건축물대장 API 공시가격의 대안

## 주의사항

1. **API 키 발급**: OpenDart 웹사이트(https://opendart.fss.or.kr)에서 회원가입 후 API 키 발급 필요
2. **API 키 관리**: API 키는 [api_key.md](api_key.md)에 별도로 관리됩니다.
3. **요청 제한**: 분당 1,000건, 일 10,000건 제한
4. **데이터 갱신**: 공시 제출 후 수 시간~1일 소요
5. **고유번호**: 8자리 고유번호는 corpCode.xml 다운로드 후 검색 필요
6. **금액 단위**: 재무제표 금액은 원(KRW) 단위이며, 대부분 백만원/천원 단위로 표시됨
7. **연결/개별**: 재무제표는 연결(CFS)과 개별(OFS) 구분하여 조회 필요

## 주요 재무제표 계정 ID

| 계정명 | IFRS Account ID |
|--------|----------------|
| 자산총계 | `ifrs-full_Assets` |
| 유형자산 | `ifrs-full_PropertyPlantAndEquipment` |
| 재고자산 | `ifrs-full_Inventories` |
| 매출액 | `ifrs-full_Revenue` |
| 영업이익 | `ifrs-full_ProfitLossFromOperatingActivities` |
| 당기순이익 | `ifrs-full_ProfitLoss` |
| 자본총계 | `ifrs-full_Equity` |
| 부채총계 | `ifrs-full_Liabilities` |

## 상장회사 검색 팁

주요 상장회사 종목코드:
- 삼성전자: 005930
- SK하이닉스: 000660
- 현대자동차: 005380
- LG화학: 051910
- POSCO: 005490

## 참고 문서

- OpenDart 포털: https://opendart.fss.or.kr
- OpenDart API 가이드: https://opendart.fss.or.kr/guide/main.do
- DART 전자공시: https://dart.fss.or.kr
- 금융감독원: https://www.fss.or.kr
