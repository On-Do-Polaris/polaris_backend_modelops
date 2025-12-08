# Open API 문서 및 테스트 가이드

## 📋 개요

SK AX 기후리스크 분석 프로젝트에서 사용하는 Open API들에 대한 상세 문서 및 테스트 결과입니다.

---

## 📂 문서 구조

```
api_docs/
├── README.md                          # 이 파일
├── 01_공공데이터포털_API.md            # 건축물대장, 병원, 재해연보, WAMIS
├── 02_VWorld_API.md                   # 하천망, 행정구역, 해안선, Geocoding
├── 03_기상청_API.md                    # 태풍, 단기예보, ASOS 관측
├── 04_재난안전데이터플랫폼_API.md       # 긴급재난문자, AWS10분, 재해위험지구, 하천
├── 05_SGIS_인구통계_API.md            # 읍면동 단위 인구통계 (통계청)
├── test_publicdata_api.py            # 공공데이터포털 API 테스트 스크립트
├── test_all_publicdata_api.py        # 공공데이터포털 승인 API 전체 테스트
├── test_vworld_api.py                # V-World API 테스트 스크립트
├── test_kma_api.py                   # 기상청 API 테스트 스크립트
├── test_safety_api.py                # 재난안전데이터 플랫폼 API 테스트 스크립트
└── test_sgis_api.py                  # SGIS 인구통계 API 테스트 스크립트
```

---

## 🔑 API 키 관리

모든 API 키는 프로젝트 루트의 `.env` 파일에 저장되어 있습니다.

```env
# 공공데이터포털
PUBLICDATA_API_KEY=4b3982d6a266a28f83a1a2c80d64fc4df8c29317b6d6f439dc3d8cb28c3c1ce1

# V-World
VWORLD_API_KEY=9D8FAEF2-A9C2-36F1-A016-712A69BA0791

# KOSIS
KOSIS_API_KEY=OGMzMGYxMTM3MmNiZDg5MjdmNTExMjExNGNjMDhkOGU

# 기상청 API
KMA_API_KEY=YnZ6Ktn-SbK2eirZ_rmyCA

# 재난안전데이터 플랫폼
EMERGENCYMESSAGE_API_KEY=3W265G78NB926HJ2
AWS10_API_KEY=98ZFVI407K6KCP66
DISASTERAREA_API_KEY=01BS26YZV6W5A9H0
RIVER_API_KEY=B7XA41C895N96P2Z

# SGIS (통계청 통계지리정보서비스)
SGIS_SERVICE_ID=4bcd973fb05e4701b46e
SGIS_SECURITY_KEY=cc02b9af51ee4ddfbfeb
```

---

## ✅ API 테스트 결과

### 1. 공공데이터포털 API

| API명              | 상태    | 비고                  |
| ------------------ | ------- | --------------------- |
| 건축물대장 API     | ✅ 성공 | 건축물 정보 조회 정상 |
| 병원 API           | ✅ 성공 | 병원 목록 조회 정상   |
| 재해연보 API       | ⚠️ 실패 | 엔드포인트 오류 (500) |
| WAMIS 유역특성 API | ⚠️ 실패 | 엔드포인트 오류 (500) |

**테스트 실행:**

```bash
python Physical_RISK_calculate/docs/api_docs/test_publicdata_api.py
```

---

### 2. V-World API

| API명         | 상태           | 비고                |
| ------------- | -------------- | ------------------- |
| 하천망 데이터 | ⚠️ 인증 오류   | API 키 확인 필요    |
| 행정구역 경계 | ⚠️ 인증 오류   | API 키 확인 필요    |
| Geocoding     | ⚠️ 데이터 없음 | 주소 형식 확인 필요 |
| WMS 지도      | ⚠️ 인증 오류   | API 키 확인 필요    |

**문제**: 현재 `.env`의 `VWORLD_API_KEY`로 인증 오류 발생  
**해결방안**: V-World 개발자센터에서 API 키 재발급 및 도메인 등록

**테스트 실행:**

```bash
python Physical_RISK_calculate/docs/api_docs/test_vworld_api.py
```

---

### 3. 기상청 API

| API명            | 상태    | 비고                     |
| ---------------- | ------- | ------------------------ |
| 태풍 정보 API    | ⚠️ 실패 | 유효한 인증키 아님 (401) |
| 단기예보 API     | ⚠️ 실패 | 활용신청 승인 필요 (403) |
| ASOS 일별 관측   | ⚠️ 실패 | 활용신청 승인 필요 (403) |
| ASOS 시간별 관측 | ⚠️ 실패 | 활용신청 승인 필요 (403) |

**문제**:

- 기상청 API Hub 키 유효하지 않음
- 공공데이터포털 기상청 API 활용신청 미승인

**해결방안**:

1. 기상청 API Hub에서 키 재발급: https://apihub.kma.go.kr
2. 공공데이터포털에서 기상청 API 활용신청 및 승인 대기

**테스트 실행:**

```bash
python Physical_RISK_calculate/docs/api_docs/test_kma_api.py
```

---

### 4. 재난안전데이터 플랫폼 API

| API명                | 상태    | 데이터 건수 | 비고                  |
| -------------------- | ------- | ----------- | --------------------- |
| 긴급재난문자 API     | ✅ 성공 | 190건       | 최근 30일 데이터      |
| AWS 10분주기 API     | ✅ 성공 | 0건         | 관측소/시각 조정 필요 |
| 지역재해위험지구 API | ✅ 성공 | 2,243건     | 전국 재해위험지구     |
| 하천정보 API         | ✅ 성공 | 3,893건     | 전국 하천 정보        |

**테스트 실행:**

```bash
python Physical_RISK_calculate/docs/api_docs/test_safety_api.py
```

✅ **가장 안정적으로 작동하는 API 그룹**

---

### 5. SGIS 인구통계 API

| API명            | 상태    | 데이터 건수 | 비고               |
| ---------------- | ------- | ----------- | ------------------ |
| OAuth 인증       | ✅ 성공 | -           | 액세스 토큰 발급   |
| 읍면동 인구통계  | ✅ 성공 | 19건        | 서울 노원구 읍면동 |
| 특정 읍면동 조회 | ✅ 성공 | 1건         | 월계1동: 22,158명  |
| 성별 인구통계    | ✅ 성공 | 3건         | 전체/남자/여자     |

**특징**:

- ✅ **읍면동 단위 상세 인구 데이터** 제공
- ✅ 행정안전부 API와 달리 시·도 단위가 아닌 **읍면동 단위** 제공
- ✅ 성별, 연령대별 통계 제공
- ✅ 2015년 ~ 2023년 연도별 데이터

**테스트 실행:**

```bash
python Physical_RISK_calculate/docs/api_docs/test_sgis_api.py
```

✅ **읍면동 단위 인구 데이터가 필요한 경우 필수 API**

---

## 🚀 사용 방법

### 1. 환경 설정

```bash
# 필요한 패키지 설치
pip install requests python-dotenv

# .env 파일이 프로젝트 루트에 있는지 확인
```

### 2. 개별 API 테스트

각 테스트 스크립트를 실행하여 API 연결 확인:

```bash
cd /path/to/project/root

python Physical_RISK_calculate/docs/api_docs/test_publicdata_api.py
python Physical_RISK_calculate/docs/api_docs/test_vworld_api.py
python Physical_RISK_calculate/docs/api_docs/test_kma_api.py
python Physical_RISK_calculate/docs/api_docs/test_safety_api.py
```

### 3. API 문서 참조

각 API별 상세 문서를 참조하여 파라미터 및 응답 형식 확인:

- `01_공공데이터포털_API.md`
- `02_VWorld_API.md`
- `03_기상청_API.md`
- `04_재난안전데이터플랫폼_API.md`

---

## ⚠️ 문제 및 해결 방안

### 공통 문제

#### 1. API 키 인증 오류

**증상**: "인증키 정보가 올바르지 않습니다" 또는 403/401 오류  
**해결방안**:

- 각 플랫폼에서 API 키 유효성 확인
- 활용신청 승인 상태 확인
- 키 재발급 또는 신규 발급

#### 2. 활용신청 미승인

**증상**: 403 Forbidden 오류  
**해결방안**:

- 공공데이터포털에서 활용신청
- 승인까지 1~2시간 소요
- 승인 후 테스트

#### 3. 엔드포인트 오류

**증상**: 500 Internal Server Error  
**해결방안**:

- API 문서에서 정확한 엔드포인트 URL 확인
- 필수 파라미터 누락 여부 확인
- 다른 엔드포인트 시도

---

## 📊 API별 활용도

### 즉시 사용 가능 (✅)

1. **건축물대장 API** - 건물 정보
2. **병원 API** - 의료시설 정보
3. **재난안전데이터 플랫폼 APIs** (전체 4개)
   - 긴급재난문자
   - 지역재해위험지구
   - 하천정보

### 추가 확인 필요 (⚠️)

1. **V-World APIs** - API 키 재발급
2. **기상청 APIs** - API 키 재발급 및 활용신청
3. **재해연보 API** - 엔드포인트 확인
4. **WAMIS API** - 엔드포인트 확인

---

## 📝 기후리스크 분석별 API 매핑

### 극심한 고온 리스크

- 건축물대장 API (건물 구조, 연도)
- 병원 API (의료접근성)
- ASOS API (기온 데이터) - 활용신청 필요

### 홍수 리스크

- 하천정보 API (하천 제원)
- 지역재해위험지구 API (홍수 위험지구)
- 건축물대장 API (지하층 정보)

### 태풍 리스크

- 태풍 정보 API - API 키 재발급 필요
- 긴급재난문자 API (과거 태풍 피해)
- 건축물대장 API (자산가치)

### 산불 리스크

- 지역재해위험지구 API (산불 위험지구)
- 소방서 정보 (별도 확인 필요)

---

## 🔄 업데이트 이력

- **2024-11-22**: 초기 문서 작성 및 전체 API 테스트 완료
  - 공공데이터포털 API: 2개 성공, 2개 확인 필요
  - V-World API: API 키 문제 확인
  - 기상청 API: 활용신청 필요
  - 재난안전데이터 플랫폼 API: 전체 성공 ✅

---

## 📞 문의 및 지원

각 API 플랫폼별 문의처:

- **공공데이터포털**: https://www.data.go.kr/tcs/main.do
- **V-World**: https://www.vworld.kr/dev
- **기상청 API Hub**: https://apihub.kma.go.kr
- **재난안전데이터**: https://www.safetydata.go.kr

---

## 📌 다음 단계

1. ✅ **완료**: 모든 API 테스트 및 문서화
2. 🔄 **진행중**: API 키 문제 해결
   - V-World API 키 재발급
   - 기상청 API 활용신청
3. ⏳ **예정**: 실제 분석 코드에 API 통합
