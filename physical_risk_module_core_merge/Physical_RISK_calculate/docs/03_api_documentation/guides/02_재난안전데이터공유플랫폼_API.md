# 재난안전데이터공유플랫폼 API

## 개요

재난안전데이터공유플랫폼(www.safetydata.go.kr)은 행정안전부에서 운영하는 재난안전 관련 공공데이터 제공 플랫폼입니다. 기상, 재난, 재해 관련 다양한 데이터를 제공하여 재난 예방 및 대응에 활용할 수 있습니다.

**제공 기관**: 행정안전부  
**API 유형**: REST API  
**데이터 포맷**: JSON, XML  
**인증 방식**: Service Key (API 키)

## API 목록

본 프로젝트에서 활용하는 재난안전데이터공유플랫폼 API는 다음과 같습니다:

1. **하천정보** - 전국 하천 기본 정보 제공
2. **지역재해위험지구** - 재해위험지구 지정 현황
3. **행정안전부\_긴급재난문자** - 실시간 재난문자 발송 이력
4. **기상청\_AWS10분주기** - 방재기상관측 데이터 (10분 주기)

---

## 1. 하천정보 API

### 1.1 API 정보

- **API 명**: 하천정보
- **엔드포인트**: `/V2/api/DSSP-IF-10720`
- **Base URL**: `https://www.safetydata.go.kr`
- **갱신주기**: 1일
- **최종 갱신일**: 2024-04-05

### 1.2 주요 용도

- 가뭄, 풍수해(태풍, 호우, 대설) 대비 하천 정보 파악
- 하천 범람 위험도 분석
- 유역면적 및 홍수용량 기반 리스크 평가

### 1.3 요청 파라미터

| 파라미터   | 타입   | 필수 | 설명                     |
| ---------- | ------ | ---- | ------------------------ |
| serviceKey | STRING | Y    | 서비스 키                |
| numOfRows  | NUMBER | N    | 페이지당 개수 (기본: 10) |
| pageNo     | NUMBER | N    | 페이지 번호 (기본: 1)    |
| returnType | STRING | N    | 응답 타입 (json/xml)     |

### 1.4 응답 데이터 (주요 항목)

| 항목명(국문) | 항목명(영문) | 타입   | 설명              |
| ------------ | ------------ | ------ | ----------------- |
| 하천관리번호 | RVR_MNG_NO   | STRING | 하천관리번호      |
| 하천명       | RVR_NM       | STRING | 하천명            |
| 본류         | MAST         | STRING | 본류              |
| 1지류        | TRBTRY_1     | STRING | 1지류             |
| 수계코드     | WASY_CD      | STRING | 수계코드          |
| 하천등급코드 | RVR_GRD_CD   | STRING | 하천등급코드      |
| 홍수용량     | FLOD_CPC     | NUMBER | 홍수용량          |
| 하천너비     | RVR_BRDTH    | NUMBER | 하천너비          |
| 하천연장길이 | RVR_PRLG_LEN | NUMBER | 하천연장길이 (km) |
| 유역면적     | DRAR         | NUMBER | 유역면적 (km²)    |

### 1.5 샘플 코드

```python
import requests
import os
from dotenv import load_dotenv

load_dotenv()

url = "https://www.safetydata.go.kr/V2/api/DSSP-IF-10720"
params = {
    'serviceKey': os.getenv('RIVER_API_KEY'),
    'returnType': 'json',
    'pageNo': '1',
    'numOfRows': '5'
}

response = requests.get(url, params=params, verify=False)
data = response.json()

for river in data['body']:
    print(f"{river['RVR_NM']}: 연장 {river['RVR_PRLG_LEN']}km, 유역면적 {river['DRAR']}km²")
```

### 1.6 테스트 결과

- **상태**: ✅ 성공
- **응답 코드**: 200
- **조회 건수**: 5건
- **샘플 데이터**:
  - 영덕오십천: 연장 44km, 유역면적 350km²
  - 무릉천: 연장 4km, 유역면적 34km²
  - 천기천: 연장 13km, 유역면적 56km²

---

## 2. 지역재해위험지구 API

### 2.1 API 정보

- **API 명**: 지역재해위험지구
- **엔드포인트**: `/V2/api/DSSP-IF-10075`
- **Base URL**: `https://www.safetydata.go.kr`
- **갱신주기**: 1일
- **최종 갱신일**: 2024-04-05

### 2.2 주요 용도

- 재해위험지구 지정 현황 파악
- 산사태, 침수, 지진 등 재해 취약 지역 식별
- 지역별 재난 리스크 평가 및 우선순위 설정

### 2.3 요청 파라미터

| 파라미터   | 타입   | 필수 | 설명                     |
| ---------- | ------ | ---- | ------------------------ |
| serviceKey | STRING | Y    | 서비스 키                |
| numOfRows  | NUMBER | N    | 페이지당 개수 (기본: 10) |
| pageNo     | NUMBER | N    | 페이지 번호 (기본: 1)    |
| returnType | STRING | N    | 응답 타입 (json/xml)     |

### 2.4 응답 데이터 (주요 항목)

| 항목명(국문)         | 항목명(영문)           | 타입   | 설명                  |
| -------------------- | ---------------------- | ------ | --------------------- |
| 재해위험지구관리번호 | DST_RSK_DSTRCT_MNG_NO  | STRING | 재해위험지구관리번호  |
| 재해위험지구명       | DST_RSK_DSTRCT_NM      | STRING | 재해위험지구명        |
| 재해위험지구등급코드 | DST_RSK_DSTRCT_GRD_CD  | STRING | 1-상, 2-중, 3-하      |
| 재해위험지구유형코드 | DST_RSK_DSTRCT_TYPE_CD | STRING | 001-침수, 002-붕괴 등 |
| 지정일자             | DSGN_YMD               | STRING | 지정일자 (YYYYMMDD)   |
| 지정사유             | DSGN_RSN               | STRING | 지정사유              |
| 해제일자             | RMV_YMD                | STRING | 해제일자              |
| 거주세대수           | HAB_NOHO               | NUMBER | 거주세대수            |
| 거주인원수           | HAB_NOPE               | NUMBER | 거주인원수            |
| 피해이력지수         | DAM_HSTRY_IDX          | NUMBER | 피해이력지수          |

### 2.5 샘플 코드

```python
import requests
import os
from dotenv import load_dotenv

load_dotenv()

url = "https://www.safetydata.go.kr/V2/api/DSSP-IF-10075"
params = {
    'serviceKey': os.getenv('DISASTERAREA_API_KEY'),
    'returnType': 'json',
    'pageNo': '1',
    'numOfRows': '5'
}

response = requests.get(url, params=params, verify=False)
data = response.json()

for area in data['body']:
    print(f"{area['DST_RSK_DSTRCT_NM']} (등급: {area['DST_RSK_DSTRCT_GRD_CD']})")
    print(f"  지정일자: {area['DSGN_YMD']}")
    print(f"  지정사유: {area['DSGN_RSN'][:50]}...")
```

### 2.6 테스트 결과

- **상태**: ✅ 성공
- **응답 코드**: 200
- **조회 건수**: 5건
- **샘플 데이터**:
  - 성남1지구: 등급 1, 유형 002 (붕괴), 지정일 20080418
  - 성남2지구: 등급 1, 유형 002 (붕괴), 지정일 20090305
  - 무안지구: 등급 1, 유형 001 (침수), 지정일 20090731

---

## 3. 긴급재난문자 API

### 3.1 API 정보

- **API 명**: 행정안전부\_긴급재난문자
- **엔드포인트**: `/V2/api/DSSP-IF-00247`
- **Base URL**: `https://www.safetydata.go.kr`
- **갱신주기**: 1분 (실시간)
- **최종 갱신일**: 2025-11-22

### 3.2 주요 용도

- 실시간 재난 상황 모니터링
- 지역별 재난 발생 현황 파악
- 긴급 대응 시스템 연동

### 3.3 요청 파라미터

| 파라미터   | 타입   | 필수 | 설명                      |
| ---------- | ------ | ---- | ------------------------- |
| serviceKey | STRING | Y    | 서비스 키                 |
| numOfRows  | NUMBER | N    | 페이지당 개수 (기본: 10)  |
| pageNo     | NUMBER | N    | 페이지 번호 (기본: 1)     |
| returnType | STRING | N    | 응답 타입 (json/xml)      |
| crtDt      | STRING | N    | 조회시작일자 (YYYYMMDD)   |
| rgnNm      | STRING | N    | 지역명 (시도명, 시군구명) |

### 3.4 응답 데이터

| 항목명(국문) | 항목명(영문) | 타입   | 설명                         |
| ------------ | ------------ | ------ | ---------------------------- |
| 일련번호     | SN           | NUMBER | 일련번호                     |
| 생성일시     | CRT_DT       | STRING | 생성일시                     |
| 메시지내용   | MSG_CN       | STRING | 메시지내용                   |
| 수신지역명   | RCPTN_RGN_NM | STRING | 수신지역명                   |
| 긴급단계명   | EMRG_STEP_NM | STRING | 위급재난, 긴급재난, 안전안내 |
| 재해구분명   | DST_SE_NM    | STRING | 재해구분명                   |
| 등록일자     | REG_YMD      | STRING | 등록일자                     |

### 3.5 샘플 코드

```python
import requests
import os
from dotenv import load_dotenv
from datetime import datetime, timedelta

load_dotenv()

# 최근 30일 데이터 조회
start_date = (datetime.now() - timedelta(days=30)).strftime('%Y%m%d')

url = "https://www.safetydata.go.kr/V2/api/DSSP-IF-00247"
params = {
    'serviceKey': os.getenv('EMERGENCYMESSAGE_API_KEY'),
    'returnType': 'json',
    'pageNo': '1',
    'numOfRows': '10',
    'crtDt': start_date
}

response = requests.get(url, params=params, verify=False)
data = response.json()

for msg in data['body']:
    print(f"[{msg['EMRG_STEP_NM']}] {msg['DST_SE_NM']}")
    print(f"  지역: {msg['RCPTN_RGN_NM']}")
    print(f"  메시지: {msg['MSG_CN'][:100]}...")
```

### 3.6 테스트 결과

- **상태**: ✅ 성공
- **응답 코드**: 200
- **조회 건수**: 10건
- **조회 기간**: 2025-10-23 ~ 현재
- **샘플 데이터**:
  - [안전안내] 정전 사태 (강원특별자치도 인제군)
  - [안전안내] 폭풍해일주의보 (전라남도 무안군)
  - [안전안내] 교통사고 정체 (경기도 고양시)

---

## 4. 기상청 AWS10분주기 API

### 4.1 API 정보

- **API 명**: 기상청\_AWS10분주기
- **엔드포인트**: `/V2/api/DSSP-IF-00026`
- **Base URL**: `https://www.safetydata.go.kr`
- **갱신주기**: 10분
- **최종 갱신일**: 2025-11-22

### 4.2 주요 용도

- 방재기상관측 데이터 수집 (10분 주기)
- 국지적 기상 현상 파악
- 태풍, 호우, 대설, 극심한 고온 등 기상재해 모니터링

### 4.3 요청 파라미터

| 파라미터      | 타입   | 필수 | 설명                     |
| ------------- | ------ | ---- | ------------------------ |
| serviceKey    | STRING | Y    | 서비스 키                |
| numOfRows     | NUMBER | N    | 페이지당 개수 (기본: 10) |
| pageNo        | NUMBER | N    | 페이지 번호 (기본: 1)    |
| returnType    | STRING | N    | 응답 타입 (json/xml)     |
| AWS_OBSVTR_CD | STRING | N    | AWS관측소코드            |
| OBSRVN_HR     | STRING | N    | 관측시간                 |

### 4.4 응답 데이터 (주요 항목)

| 항목명(국문)  | 항목명(영문)  | 타입   | 설명          |
| ------------- | ------------- | ------ | ------------- |
| AWS관측소코드 | AWS_OBSVTR_CD | STRING | AWS관측소코드 |
| 관측시간      | OBSRVN_HR     | STRING | 관측시간      |
| 기온          | AIRTP         | NUMBER | 기온 (℃)      |
| 풍향          | WIDIR         | NUMBER | 풍향 (°)      |
| 풍속          | WISP          | NUMBER | 풍속 (m/s)    |
| 강수량        | RNFLL_F       | NUMBER | 강수량 (mm)   |
| 기압          | ATMPR         | NUMBER | 기압 (hPa)    |
| 상대습도      | RLTHDY        | NUMBER | 상대습도 (%)  |
| 적설          | SNTS          | NUMBER | 적설 (cm)     |
| 지면온도      | GRNDTMPRTR    | NUMBER | 지면온도 (℃)  |

### 4.5 샘플 코드

```python
import requests
import os
from dotenv import load_dotenv

load_dotenv()

url = "https://www.safetydata.go.kr/V2/api/DSSP-IF-00026"
params = {
    'serviceKey': os.getenv('AWS10_API_KEY'),
    'returnType': 'json',
    'pageNo': '1',
    'numOfRows': '5'
}

response = requests.get(url, params=params, verify=False)
data = response.json()

for obs in data['body']:
    print(f"관측소 {obs['AWS_OBSVTR_CD']}: {obs['OBSRVN_HR']}")
    print(f"  기온: {obs['AIRTP']}℃, 풍속: {obs['WISP']}m/s")
    print(f"  강수량: {obs['RNFLL_F']}mm, 습도: {obs['RLTHDY']}%")
```

### 4.6 테스트 결과

- **상태**: ✅ 성공
- **응답 코드**: 200
- **조회 건수**: 5건
- **샘플 데이터**:
  - 관측소 90: 기온 9.7℃, 풍속 1.5m/s, 강수량 0mm, 습도 48.8%
  - 관측소 92: 기온 10.4℃, 풍속 4.2m/s, 강수량 0mm, 습도 51%
  - 관측소 93: 기온 2.5℃, 풍속 0.4m/s, 강수량 0mm, 습도 86.1%

---

## 활용 사례

### 1. 기후리스크 분석

- **하천정보**: 홍수 위험도 평가 (유역면적, 홍수용량)
- **재해위험지구**: 취약 지역 식별 및 우선순위 설정
- **AWS10분주기**: 실시간 기상 모니터링 (강수량, 풍속)

### 2. Physical Risk 계산

```python
# V_hazard (위해도) 계산 예시
# 하천 범람 위험도 = f(강수량, 유역면적, 홍수용량)

rainfall = aws_data['RNFLL_F']  # 강수량 (mm)
drainage_area = river_data['DRAR']  # 유역면적 (km²)
flood_capacity = river_data['FLOD_CPC']  # 홍수용량

# 위험도 계산 로직
V_hazard = (rainfall * drainage_area) / flood_capacity
```

### 3. 재난 대응 시스템

- **긴급재난문자**: 실시간 재난 알림 수신 및 자동 대응
- **재해위험지구**: 사전 대피 계획 수립
- **AWS10분주기**: 기상 임계값 도달 시 알림

---

## 환경변수 설정

```bash
# .env 파일
RIVER_API_KEY=your_river_api_key_here
DISASTERAREA_API_KEY=your_disaster_area_api_key_here
EMERGENCYMESSAGE_API_KEY=your_emergency_message_api_key_here
AWS10_API_KEY=your_aws10_api_key_here
```

## 주의사항

1. **SSL 인증서 검증**

   - `verify=False` 사용 시 보안 경고 발생
   - 프로덕션 환경에서는 인증서 검증 권장

2. **API 호출 제한**

   - 일일 호출 횟수 제한 있음
   - 과도한 호출 시 서비스 제한 가능

3. **데이터 갱신 주기**

   - 하천정보/재해위험지구: 1일
   - 긴급재난문자: 1분
   - AWS10분주기: 10분

4. **응답 데이터 구조**
   - `body` 필드에 배열 형태로 데이터 제공
   - 빈 결과 시 빈 배열 반환

---

## 관련 링크

- **재난안전데이터공유플랫폼**: https://www.safetydata.go.kr
- **API 문서**: https://www.safetydata.go.kr/disaster-data/view-document?dataid={API_ID}
- **행정안전부**: https://www.mois.go.kr

---

**최종 테스트 일시**: 2025-11-22  
**테스트 결과**: 4/4 성공 (100%)
