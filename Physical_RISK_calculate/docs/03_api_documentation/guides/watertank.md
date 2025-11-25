# 전국저수지 및 댐 표준데이터 요약

## 1. 데이터 개요

- **내용**: 지방자치단체에서 관리하는 저수지 및 댐 정보 제공
- **관련 법령**: 「댐건설ㆍ관리 및 주변지역지원 등에 관한 법률」, 「농어촌정비법」
- **소관기관**: 환경부, 농림축산식품부
- **제공기관**: 지방자치단체
- **갱신주기**: 연간
- **수정일**: 2025-07-08
- **분류체계**: 공공질서 및 안전 - 안전관리
- **키워드**: 저수지, 댐, 저수지및댐

---

## 2. 데이터 활용

- **Open API 제공**
- **요청 주소**:  
  `http://api.data.go.kr/openapi/tn_pubr_public_reservoirs_dams_api`
- **트래픽 제한**:
  - 개발계정: 1,000
  - 운영계정: 활용사례 등록 시 트래픽 증가 가능

---

## 3. 요청 파라미터 (Request Parameter)

| 항목명            | 설명              |
| ----------------- | ----------------- |
| pageNo            | 페이지 번호       |
| numOfRows         | 한 페이지 결과 수 |
| type              | XML/JSON 여부     |
| FCLT_NM           | 시설명            |
| CTPV_NM           | 시도명            |
| SGG_NM            | 시군구명          |
| LCTN_ROAD_NM_ADDR | 소재지 도로명주소 |
| LCTN_LOTNO_ADDR   | 소재지 지번주소   |
| TPNDG             | 총저수량          |
| VLD_PNDG          | 유효저수량        |
| RCFV_AREA         | 수혜면적          |
| DRAR              | 유역면적          |
| CMCN_YR           | 준공연도          |
| MNG_INST_NM       | 관리기관명        |
| MNG_INST_TELNO    | 관리기관 전화번호 |
| DATA_CRTR_YMD     | 데이터 기준일자   |
| instt_code        | 제공기관 코드     |
| instt_nm          | 제공기관 기관명   |

---

## 4. 출력 결과 (Response Element)

- 요청 파라미터와 동일한 항목명으로 결과 제공

---

## 5. 에러코드 안내

| 에러코드 | 메시지                                           | 설명                         |
| -------- | ------------------------------------------------ | ---------------------------- |
| 00       | NORMAL_CODE                                      | 정상                         |
| 01       | APPLICATION_ERROR                                | 어플리케이션 에러            |
| 02       | DB_ERROR                                         | 데이터베이스 에러            |
| 03       | NODATA_ERROR                                     | 데이터없음 에러              |
| 04       | HTTP_ERROR                                       | HTTP 에러                    |
| 05       | SERVICETIMEOUT_ERROR                             | 서비스 연결실패 에러         |
| 10       | INVALID_REQUEST_PARAMETER_ERROR                  | 잘못된 요청 파라메터 에러    |
| 11       | NO_MANDATORY_REQUEST_PARAMETERS_ERROR            | 필수요청 파라메터 없음       |
| 12       | NO_OPENAPI_SERVICE_ERROR                         | 오픈API서비스 없음/폐기됨    |
| 20       | SERVICE_ACCESS_DENIED_ERROR                      | 서비스 접근거부              |
| 21       | TEMPORARILY_DISABLE_THE_SERVICEKEY_ERROR         | 일시적 서비스키 사용불가     |
| 22       | LIMITED_NUMBER_OF_SERVICE_REQUESTS_EXCEEDS_ERROR | 서비스 요청제한횟수 초과에러 |
| 30       | SERVICE_KEY_IS_NOT_REGISTERED_ERROR              | 등록되지 않은 서비스키       |
| 31       | DEADLINE_HAS_EXPIRED_ERROR                       | 기한만료된 서비스키          |
| 32       | UNREGISTERED_IP_ERROR                            | 등록되지 않은 IP             |
| 33       | UNSIGNED_CALL_ERROR                              | 서명되지 않은 호출           |
| 99       | UNKNOWN_ERROR                                    | 기타에러                     |

---

## 6. 기타

- 샘플코드: Java, Javascript, C#, PHP, Curl, Objective-C, Python, Nodejs, R 등 다양한 언어 제공
- 데이터 목록 및 활용사례는 공공데이터 포털에서 확인 가능
