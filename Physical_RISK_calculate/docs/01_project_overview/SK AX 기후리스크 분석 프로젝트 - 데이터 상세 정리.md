# SK AX 기후리스크 분석 프로젝트 - 데이터 상세 정리

## 1. CMIP6 SSP 시나리오 데이터

- **출처**: 기상청 기후정보포털
- **링크**: https://climate.go.kr
- **데이터 타입**: NetCDF
- **데이터 설명**: SSP1-2.6/SSP2-4.5/SSP3-7.0/SSP5-8.5 시나리오별 미래 기후전망 데이터 (일최고기온, 일최저기온, 강수량, 풍속, 해수면 고도 등)
- **사용처**:
  - 폭염 위해성 평가 (일최고기온)
  - 한파 위해성 평가 (일최저기온)
  - 가뭄 위해성 평가 (강수량, 기온)
  - 태풍 위해성 평가 (일평균 풍속)
  - 해안홍수 위해성 평가 (해수면 상승)
- **입력 인자**:
  - 시나리오: SSP1-2.6, SSP2-4.5, SSP3-7.0, SSP5-8.5
  - 시간범위: 2021~2100년
  - 공간해상도: 1km (남한상세)
  - 변수: 기온, 강수량, 풍속, 해수면고도
- **출력인자**:
  - 일최고기온(℃), 일최저기온(℃), 강수량(mm)
  - 일평균 풍속(m/s), 해수면고도(m)
  - 극한기후지수 (RX1DAY, RX5DAY, SDII 등)[^1][^2]

---

## 2. 환경부 토지피복도

- **출처**: 환경공간정보서비스
- **링크**: https://aid.mcee.go.kr (자료신청 메뉴)
- **데이터 타입**: SHP, GeoTIFF
- **데이터 설명**: 항공사진과 위성영상을 이용하여 지표면 상태를 분류한 공간데이터 (대분류 7개, 중분류 23개, 세분류 41개), 2018년까지 업데이트
- **사용처**:
  - 폭염 노출도 평가 (유출곡선지수 결정)
  - 한파 노출도 평가 (유출곡선지수 결정)
  - 산불 노출도 평가 (토지피복 유형)
  - 도시홍수 노출도 평가 (불투수면 비율)
  - 가뭄 노출도 평가 (토지이용 특성)
  - 산불 취약성 평가 (가연성 토지피복)
- **입력 인자**:
  - 지역(시도, 시군구)
  - 제작년도
- **출력인자**:
  - 토지피복 분류코드 및 명칭
  - 면적(㎡), 비율(%)
  - 공간좌표 (Geometry)[^3][^4]

---

## 3. 국토지리정보원 DEM (수치표고모델)

- **출처**: 국토정보플랫폼
- **링크**: http://map.ngii.go.kr/mn/mainPage.do
- **API 키**: `70B0548B5723A55E7C3E6BECCBB65A53D8F97DA7E7`
- **데이터 타입**: ASCII, IMG, PDF
- **데이터 설명**: 1:1,000 축척 수치표고모델, 지형의 고도 정보
- **사용처**:
  - 폭염 노출도 평가 (지형조건 분석)
  - 한파 노출도 평가 (지형조건 분석)
  - 산불 노출도 평가 (경사도, 고도)
  - 도시홍수 노출도 평가 (배수경로 분석)
  - 내륙홍수 노출도 평가 (범람 위험지역)
  - 해안홍수 노출도 평가 (해발고도)
- **입력 인자**:
  - 지역(좌표 또는 행정구역)
  - 해상도
- **출력인자**:
  - 표고값(m)
  - 경사도(°)
  - 경사향[^5][^6]

---

## 4. 국토교통부 건축물대장 API

- **출처**: 공공데이터포털
- **링크**: https://www.data.go.kr/data/15135963/openapi.do
- **API 키 (Encoding)**: `7w8yGDAgOEqoA83iJfNVoW1VVPfWSQNWBXhsogrBzgifRXJYTwWE8CMKnlP9KT5gNV5VGC3X3vGIFWyphY5o1A%3D%3D`
- **API 키 (Decoding)**: `7w8yGDAgOEqoA83iJfNVoW1VVPfWSQNWBXhsogrBzgifRXJYTwWE8CMKnlP9KT5gNV5VGC3X3vGIFWyphY5o1A==`
- **데이터 타입**: JSON/XML
- **데이터 설명**: 전국 건축물의 상세 정보 (구조, 연도, 높이, 용도, 면적, 지하층 등)
- **사용처**:
  - 폭염 취약성 평가 (건물 냉방 효율성, 건축연도)
  - 한파 취약성 평가 (건물 난방 효율성, 건축연도)
  - 산불 취약성 평가 (건물 구조, 가연성)
  - 도시홍수 취약성 평가 (지하층 유무)
  - 내륙홍수 취약성 평가 (건물 높이, 구조)
  - 해안홍수 취약성 평가 (건물 정보)
  - 태풍 노출도 평가 (건물 면적, 자산가치)
- **입력 인자**:
  - 시군구코드 (5자리)
  - 법정동코드
  - 지번
  - 페이지번호, 한 페이지 결과 수
- **출력인자**:
  - 건물구조 (철근콘크리트, 철골, 목조 등)
  - 건축연도(년)
  - 건물높이(m), 층수(지상/지하)
  - 용도 (공장, 물류센터, 사무소 등)
  - 위도/경도
  - 연면적(㎡), 대지면적(㎡)
  - 공시가격(원)

---

## 5. 국립중앙의료원 병원 API

- **출처**: 공공데이터포털
- **링크**: https://www.data.go.kr/data/15000736/openapi.do
- **API 키**: `4b2f121a7492c996d0dca08a311bb9ae1063ae49a3ef40ed955de1f617da8bce`
- **데이터 타입**: JSON/XML
- **데이터 설명**: 전국 병·의원 찾기 서비스 (병원 위치, 진료과목 등)
- **사용처**:
  - 폭염 취약성 평가 (의료접근성)
  - 한파 취약성 평가 (의료접근성)
- **입력 인자**:
  - 지역명 (시도, 시군구)
  - 병원종별
  - 페이지번호, 한 페이지 결과 수
- **출력인자**:
  - 병원명
  - 주소
  - 위도/경도
  - 진료과목
  - 병원종별 (상급종합병원, 종합병원, 병원, 의원 등)

---

## 6. ERA5 재분석 데이터

- **출처**: Copernicus Climate Data Store (ECMWF)
- **링크**: https://cds.climate.copernicus.eu
- **데이터 타입**: NetCDF, GRIB
- **데이터 설명**: 전지구 기상 재분석 데이터 (1940년~현재), 시간당 데이터 제공, FWI(Fire Weather Index) 산출 가능
- **사용처**:
  - 산불 위해성 평가 (FWI 계산, 건조일수)
- **입력 인자**:
  - 시간: 시작일, 종료일, 시간(UTC)
  - 공간: 위도/경도 범위 또는 격자
  - 변수: 기온(2m), 강수량, 풍속(10m), 상대습도, 토양수분
  - Product type: reanalysis
- **출력인자**:
  - 기온(℃ 또는 K)
  - 강수량(mm)
  - 풍속(m/s)
  - 상대습도(%)
  - FWI (Fire Weather Index)
  - 연속 건조일수(일)[^7][^8][^9][^10]

---

## 7. 산림청 산불위험예보시스템

- **출처**: 국립산불위험예보시스템 (국립산림과학원)
- **링크**: https://forestfire.nifos.go.kr
- **데이터 타입**: 웹 서비스 (지도 이미지, 표 데이터)
- **데이터 설명**: 지형조건, 산림상황, 기상정보 기반 산불위험도 5단계 예보 (낮음-보통-높음-매우높음-심각)
- **사용처**:
  - 산불 노출도 평가 (산불위험등급)
- **입력 인자**:
  - 날짜 (예보일)
  - 지역 (시군구)
- **출력인자**:
  - 산불위험등급 (1~5단계)
  - 산불발생확률
  - 날씨정보 (기온, 습도, 풍속)[^11][^12]

---

## 8. 소방청 전국소방서 좌표

- **출처**: 공공데이터포털 또는 소방청
- **링크**: (별도 확인 필요)
- **데이터 타입**: CSV, JSON
- **데이터 설명**: 전국 소방서 위치정보 및 관할구역
- **사용처**:
  - 산불 취약성 평가 (소방서 접근성, 대응시간)
- **입력 인자**:
  - 지역 (시도, 시군구)
- **출력인자**:
  - 소방서명
  - 주소
  - 위도/경도
  - 관할구역

---

## 9. 기상청 강수량 데이터 (관측 및 시나리오)

- **출처**: 기상청 기후정보포털, 기상청 AWS/ASOS API
- **링크**:
  - 기후정보포털: https://climate.go.kr
  - 기상자료개방포털: https://data.kma.go.kr
  - AWS API: https://data.go.kr/data/15084817/openapi.do
  - ASOS API: https://data.go.kr/data/15084817/openapi.do
- **API 키**: `4b2f121a7492c996d0dca08a311bb9ae1063ae49a3ef40ed955de1f617da8bce`
- **데이터 타입**: NetCDF (시나리오), JSON/XML (관측)
- **데이터 설명**:
  - 관측: AWS 10분/시간단위, ASOS 시간/일 단위 강수량
  - 시나리오: 일별 강수량 및 극한강수지수 (RX1DAY, RX5DAY, SDII 등)
- **사용처**:
  - 도시홍수 위해성 평가 (RX1DAY, SDII)
  - 내륙홍수 위해성 평가 (RX5DAY)
  - 가뭄 위해성 평가 (누적강수량, SPI 계산)
  - 물부족 위해성 평가 (강수량 추이)
- **입력 인자**:
  - 관측소코드 또는 AWS ID
  - 관측시각 (YYYYMMDDHH24MI)
  - 지역 (시나리오)
  - 페이지번호, 한 페이지 결과 수
- **출력인자**:
  - 강수량(mm)
  - 강수강도(mm/hr)
  - 극한강수지수 (RX1DAY, RX5DAY, SDII)
  - 누적강수량(mm)[^13][^14][^15][^16][^17][^18]

---

## 10. WAMIS 유역/하천 데이터

- **출처**: 국가수자원관리종합정보시스템 (WAMIS)
- **링크**: https://wamis.go.kr
- **API 링크**:
  - 유역특성: https://data.go.kr/data/15107318/openapi.do
  - 웹 서비스: https://map.wamis.go.kr
- **API 키**: `4b2f121a7492c996d0dca08a311bb9ae1063ae49a3ef40ed955de1f617da8bce` (공공데이터포털)
- **데이터 타입**: JSON/XML, SHP
- **데이터 설명**:
  - 유역특성: 유역면적, 유로연장, 유출곡선지수(CN), 하천등급
  - 홍수량: 빈도별 홍수량 산정결과
  - 용수이용: 취수량, 용수 수요량
- **사용처**:
  - 내륙홍수 위해성 평가 (하천범람 위험도, 홍수량)
  - 물부족 위해성 평가 (용수 취수량)
- **입력 인자**:
  - 하천코드
  - 대권역명, 중권역명, 소권역명
  - 산정지점명
  - 년도
  - 페이지번호
- **출력인자**:
  - 유역면적(km²)
  - 유로연장(km)
  - 유출곡선지수(CN)
  - 빈도별 홍수량(㎥/s) - 80년, 100년, 200년 빈도
  - 하천위치(Geometry)
  - 유역경계(Polygon)
  - 생활용수/공업용수/농업용수 취수량(㎥/일)[^19][^20][^21][^22][^23][^24]

---

## 11. 브이월드 (VWorld) 공간정보 API

- **출처**: 브이월드 (국토교통부)
- **링크**: https://www.vworld.kr/dev
- **API 키**:
  - `14A52498-DB87-3CF4-91D4-D31039BC603F`
  - `961911EC-A96C-3B0E-AE0D-15B8E47EDF59`
- **데이터 타입**: GeoJSON, WMS (지도이미지)
- **데이터 설명**:
  - 하천망 (LT_C_WKMSTRM): 전국 하천 벡터 데이터
  - 시군구 코드: 행정구역 경계
  - 해안선 (lt_l_toisdepcntah): 기본도 해안선 데이터
- **사용처**:
  - 내륙홍수 위해성 평가 (사업장-하천 거리 계산)
  - 해안홍수 노출도 평가 (해안선 근접도)
- **입력 인자**:
  - service: data
  - request: GetFeature
  - data: 레이어명 (LT_C_WKMSTRM 등)
  - key: API 키
  - domain: 서비스 도메인
  - geomFilter: POINT(경도 위도) 또는 BBOX
  - buffer: 검색반경(m)
  - size: 결과 개수
  - format: json, xml
- **출력인자**:
  - 하천명
  - 하천등급
  - 하천 geometry (LineString)
  - 거리(m)
  - 해안선 geometry
  - 행정구역코드, 행정구역명[^25][^26]

---

## 12. 행정안전부 재해연보

- **출처**: 공공데이터포털 (행정안전부)
- **링크**: https://data.go.kr/data/15107303/openapi.do
- **API 키**: `4b2f121a7492c996d0dca08a311bb9ae1063ae49a3ef40ed955de1f617da8bce`
- **데이터 타입**: XML
- **데이터 설명**: 지역별 자연재난 피해 통계 (태풍, 대설, 낙뢰, 홍수, 호우, 강풍, 풍랑, 해일, 대설, 한파 등)
- **사용처**:
  - 내륙홍수 노출도 평가 (과거 침수 이력)
  - 태풍 노출도 평가 (과거 태풍 피해)
- **입력 인자**:
  - year: 년도 (YYYY)
  - 지역: 시도, 시군구
  - pageNo: 페이지번호
  - numOfRows: 한 페이지 결과 수
- **출력인자**:
  - 재난유형 (태풍, 홍수 등)
  - 인명피해 (사망, 실종, 부상) (명)
  - 이재민(명)
  - 재산피해(천원)
  - 건물피해 (전파, 반파, 침수) (동)
  - 경작지피해(ha)[^27]

---

## 13. 해양수산부 해안선 데이터

- **출처**: 국립해양조사원 / 공공데이터포털
- **링크**: https://data.go.kr (해양수산부 국립해양조사원\_해안선)
- **데이터 타입**: SHP (Shapefile)
- **데이터 설명**: 우리나라 해안선(바다와 육지 경계) 공간정보, 총 길이 15,285.4km (2023년 기준), 1:25,000 축척
- **사용처**:
  - 해안홍수 노출도 평가 (해안 근접도, 해안선 거리)
- **입력 인자**:
  - 파일 다운로드 (API 형태 아님)
- **출력인자**:
  - 해안선 geometry (LineString)
  - 해안선 길이(km)
  - 해안선 유형 (자연해안, 인공해안)[^28][^29]

---

## 14. 통계청/행정안전부 인구통계

- **출처**: 통계청 KOSIS 또는 행정안전부
- **링크**:
  - KOSIS: https://kosis.kr
  - 행정안전부 주민등록 인구통계
- **API 키**:
  - KOSIS: `Y2FlOTQ5ZjcyZjIwYjYyYzU1ZDQ1MDViZmNmOGQ1NjY=`
  - 공공데이터포털: `4b2f121a7492c996d0dca08a311bb9ae1063ae49a3ef40ed955de1f617da8bce`
- **데이터 타입**: CSV, Excel, JSON/XML
- **데이터 설명**: 시군구별 인구 통계, 인구밀도, 가구수, 인구 추계
- **사용처**:
  - 도시홍수 노출도 평가 (인구밀도)
  - 가뭄 노출도 평가 (인구수)
  - 물부족 노출도 평가 (인구수)
  - 물부족 위해성 평가 (인구 추계)
- **입력 인자**:
  - 행정구역코드 (시도, 시군구)
  - 기준년도
  - 통계항목코드
- **출력인자**:
  - 총인구수(명)
  - 인구밀도(명/km²)
  - 가구수(가구)
  - 연령별/성별 인구

---

## 15. NASA SMAP 토양수분 데이터

- **출처**: NASA Soil Moisture Active Passive (SMAP)
- **링크**:
  - https://smap.jpl.nasa.gov
  - Google Earth Engine
- **데이터 타입**: HDF5, NetCDF, GeoTIFF
- **데이터 설명**:
  - SMAP L3: 전지구 일별 9km 표층 토양수분
  - SMAP L4: 전지구 3시간 9km 표층/근권 토양수분
- **사용처**:
  - 가뭄 취약성 평가 (토양수분 모니터링)
- **입력 인자**:
  - 날짜 (YYYY-MM-DD)
  - 위도/경도 범위 또는 격자
  - Product: L3 또는 L4
  - Version: 최신버전
- **출력인자**:
  - 표층 토양수분 (0-5cm, m³/m³ 또는 %)
  - 근권 토양수분 (0-100cm, m³/m³)
  - 토양온도(K)
  - 품질플래그[^30][^31][^32][^33][^34]

---

## 16. MODIS NDVI 식생지수

- **출처**: NASA MODIS (Terra/Aqua 위성)
- **링크**:
  - https://modis.gsfc.nasa.gov
  - Google Earth Engine
  - USGS Earth Explorer
- **데이터 타입**: HDF, GeoTIFF
- **데이터 설명**:
  - MOD13Q1: 250m 해상도 16일 주기 NDVI/EVI (Terra)
  - MYD13Q1: 250m 해상도 16일 주기 NDVI/EVI (Aqua)
  - MOD13A3: 1km 해상도 월단위 NDVI/EVI
- **사용처**:
  - 가뭄 취약성 평가 (식생활력도 모니터링, 가뭄영향 평가)
- **입력 인자**:
  - 날짜 (YYYY-MM-DD)
  - 위도/경도 범위 또는 타일번호
  - Product: MOD13Q1, MYD13Q1, MOD13A3
  - 해상도: 250m, 1km
- **출력인자**:
  - NDVI (정규식생지수, -1~1)
  - EVI (개선식생지수)
  - 화소품질지수 (Quality flag)
  - 관측일(Julian day)[^35][^36]

---

## 17. 환경부 상수도 보급률

- **출처**: 환경부 또는 공공데이터포털
- **링크**: (별도 확인 필요 - 환경통계포털)
- **데이터 타입**: CSV, Excel
- **데이터 설명**: 시군구별 상수도 보급률, 급수인구, 상수도 시설 현황
- **사용처**:
  - 물부족 노출도 평가 (상수도 인프라)
  - 물부족 취약성 평가 (상수도 보급률)
- **입력 인자**:
  - 시도, 시군구
  - 년도
- **출력인자**:
  - 상수도보급률(%)
  - 급수인구(명)
  - 총인구(명)
  - 상수도 시설용량(㎥/일)

---

## 18. K-water 댐 저수율 (수문 운영 정보)

- **출처**: 한국수자원공사 / 공공데이터포털
- **링크**:
  - https://data.edmgr.kr (K-water 환경데이터마트)
  - https://data.go.kr (한국수자원공사\_수문 운영 정보)
- **데이터 타입**: JSON/XML
- **데이터 설명**: K-water 관리 댐 (다목적댐 21개소, 용수댐, 홍수조절댐) 실시간 운영정보 (10분 단위)
- **사용처**:
  - 물부족 취약성 평가 (댐 저수상황 모니터링)
- **입력 인자**:
  - 댐코드 (예: 3200700 - 소양강댐)
  - 관측시각 (YYYYMMDDHHMM)
  - pageNo: 페이지번호
  - numOfRows: 한 페이지 결과 수
- **출력인자**:
  - 댐명
  - 강우량(mm) - 전일, 금일
  - 유입량(㎥/s)
  - 방류량(㎥/s)
  - 저수위(EL.m)
  - 저수량(백만㎥)
  - 저수율(%)
  - 만수위(EL.m), 총저수량(백만㎥)[^37][^38]

---

## 19. 기상청 태풍 API

- **출처**: 기상청 API 허브
- **링크**: https://apihub.kma.go.kr
- **API 키**: `4KCY7DWXSOmgmOw1lxjp2A`
- **데이터 타입**: 고정길이 텍스트, CSV, XML/JSON
- **데이터 설명**:
  - 태풍 정보 조회 (태풍 목록, 태풍정보+예측)
  - 우리나라 영향 태풍 조회 (역사적 태풍)
  - 태풍 베스트트랙 (확정된 태풍 경로)
  - TD(열대성저기압) 정보
- **사용처**:
  - 태풍 위해성 평가 (과거 태풍 이력, 강도, 경로)
- **입력 인자**:
  - YY: 년도 (YYYY)
  - typ: 태풍번호 (해당년도 순번)
  - seq: 발표번호
  - mode: 표출범위 (0~3)
  - year: 발생연도
  - grade: 태풍등급 (TD, TS, STS, TY, L)
  - tcid: 태풍호수 (예: 2201)
  - pageNo, numOfRows, dataType
  - disp: 표출형태 (0: 고정길이, 1: CSV)
  - help: 도움말 옵션 (0~2)
- **출력인자**:
  - 태풍명 (국제명, 한글명)
  - 태풍번호/호수
  - 위도/경도(°)
  - 중심기압(hPa)
  - 최대풍속(m/s)
  - 강풍반경(km) - 15m/s 이상
  - 이동방향(°), 이동속도(km/h)
  - 예측경로 정보 (6시간~120시간)
  - 태풍등급 (TD, TS, STS, TY)
  - 발생일시, 소멸일시

---

## 20. DART 전자공시 (기업 재무정보)

- **출처**: 금융감독원 전자공시시스템
- **링크**: https://dart.fss.or.kr
- **데이터 타입**: HTML, PDF, XML (OpenDart API)
- **데이터 설명**: 상장기업 재무제표 (자산총액, 유형자산, 재고자산 등)
- **사용처**:
  - 태풍 노출도 평가 (자산가치 평가)
- **입력 인자**:
  - 회사코드 (고유번호)
  - 사업보고서 년도
  - 보고서코드
- **출력인자**:
  - 자산총액(백만원, 천원)
  - 유형자산(백만원) - 토지, 건물, 기계장치
  - 재고자산(백만원)
  - 매출액(백만원)

---

## 21. 재난안전데이터 공통 API

### 21-1. 행정안전부 긴급재난문자

- **출처**: 행정안전부 재난안전데이터 공유플랫폼
- **URL**: `https://www.safetydata.go.kr/V2/api/DSSP-IF-00247`
- **Service Key**: `3W265G78NB926HJ2`
- **데이터 타입**: JSON/XML
- **데이터 설명**: 긴급재난문자 발송 이력 (태풍, 호우, 지진 등)
- **사용처**: 재난 이력 파악 (전체 리스크)
- **입력 인자**:
  - serviceKey
  - returnType: json/xml
  - pageNo, numOfRows
  - crtDt: 조회시작일자 (YYYYMMDD)
  - rgnNm: 지역명 (시도명, 시군구명)
- **출력인자**:
  - 발송일시, 발송지역, 재난유형, 메시지내용

### 21-2. 기상청 AWS 10분주기

- **URL**: `https://www.safetydata.go.kr/V2/api/DSSP-IF-00026`
- **Service Key**: `98ZFVI407K6KCP66`
- **데이터 설명**: 자동기상관측(AWS) 10분 주기 데이터
- **사용처**: 실시간 기상 모니터링 (전체 리스크)
- **입력 인자**:
  - AWS_OBSVTR_CD: AWS관측소코드 (3자리)
  - OBSRVN_HR: 관측시간 (YYYYMMDDHHMM)
- **출력인자**: 기온, 강수량, 풍속, 습도

### 21-3. 지역재해위험지구

- **URL**: `https://www.safetydata.go.kr/V2/api/DSSP-IF-10075`
- **Service Key**: `01BS26YZV6W5A9H0`
- **데이터 설명**: 재해위험지구 지정 현황
- **사용처**: 홍수/산불 위험지역 파악
- **입력 인자**: serviceKey, pageNo, numOfRows, returnType
- **출력인자**: 지구명, 소재지, 위험유형, 지정일자

### 21-4. 하천정보

- **URL**: `https://www.safetydata.go.kr/V2/api/DSSP-IF-10720`
- **Service Key**: `B7XA41C895N96P2Z`
- **데이터 설명**: 하천 제원 및 관리 정보
- **사용처**: 내륙홍수 위해성 평가
- **입력 인자**: serviceKey, pageNo, numOfRows, returnType
- **출력인자**: 하천명, 위치, 관리기관, 제원정보, 하천관리번호, 본류, 1지류~6지류, 수계코드, 하천등급코드, 하천기점값1~3, 하천기점경계내용, 하천종점명1~3, 하천종점경계내용, 홍수용량, 하천너비, 하천연장길이, 유로연장내용, 유역면적, 하천번호, 모식도코드

response = requests.get(url, params=payloads)

---

## 22. 기타 AI/분석 도구

### 22-1. OpenAI API

- **API 키**:
- **사용처**: AI 기반 리스크 분석, 텍스트 생성

### 22-2. LangSmith API

- **API 키**:
- **사용처**: LLM 애플리케이션 모니터링 및 디버깅
  <span style="display:none">[^39][^40][^41][^42][^43][^44][^45][^46][^47][^48][^49]</span>

<div align="center">⁂</div>

[^1]: https://www.climate.go.kr
[^2]: https://www.climate.go.kr/home/CCS/contents_2021/info/download.html
[^3]: https://blog.naver.com/villa2672/221609160229
[^4]: https://aid.mcee.go.kr/req/intro.do
[^5]: https://foss4g.tistory.com/1060
[^6]: https://www.data.go.kr/data/15059920/fileData.do
[^7]: https://pmc.ncbi.nlm.nih.gov/articles/PMC7341852/
[^8]: https://cds.climate.copernicus.eu/datasets/reanalysis-era5-single-levels?tab=download
[^9]: https://ewds.climate.copernicus.eu/datasets/cems-fire-historical-v1
[^10]: https://special-waddle.tistory.com/9
[^11]: https://forestfire.nifos.go.kr
[^12]: https://www.forest.go.kr/newkfsweb/html/HtmlPage.do?pg=%2Ffgis%2FUI_KFS_5002_030200.html\&mn=KFS_02_04_03_05_02\&orgId=fgis
[^13]: https://data.kma.go.kr
[^14]: https://blog.naver.com/kma_131/223984885065?fromRss=true\&trackingCode=rss
[^15]: https://www.weather.go.kr/w/observation/land/past-obs/obs-by-day.do
[^16]: https://data.kma.go.kr/data/grnd/selectAsosRltmList.do
[^17]: https://www.data.go.kr/data/15057084/openapi.do
[^18]: https://www.data.go.kr/data/15059218/openapi.do
[^19]: https://map.wamis.go.kr
[^20]: http://www.wamis.go.kr
[^21]: https://www.wamis.go.kr/wkb/wkb_anlst_lst.do
[^22]: https://www.wamis.go.kr/wsc/wsc_fldcal_lst.do
[^23]: https://www.wamis.go.kr/wsc/wsc_fldparam_lst.do
[^24]: https://www.data.go.kr/data/15130605/fileData.do?recommendDataYn=Y
[^25]: https://blog.naver.com/v-world/221283248853
[^26]: https://www.youtube.com/watch?v=ke3rx0_eD5I
[^27]: https://www.data.go.kr/data/15107316/openapi.do
[^28]: https://www.data.go.kr/data/15083948/fileData.do
[^29]: https://oceanjikim.tistory.com/13
[^30]: https://onlinelibrary.wiley.com/doi/pdfdirect/10.1029/2019MS001729
[^31]: https://developers.google.com/earth-engine/datasets/catalog/NASA_SMAP_SPL4SMGP_008?hl=ko
[^32]: https://developers.google.com/earth-engine/datasets/catalog/NASA_SMAP_SPL3SMP_E_005?hl=ko
[^33]: https://study-climate-change.tistory.com/31
[^34]: https://www.kihs.re.kr/kor_sub/bbs/file_view.do?bbs_detail_idx=1334
[^35]: https://gist.github.com/mahdin75/7bc4e25110e02aa301427f8b081fddc0
[^36]: https://foss4g.tistory.com/1583
[^37]: https://data.edmgr.kr/dataView.do?id=www-data-go-kr-data-openapi-15099110
[^38]: https://www.data.go.kr/data/15099110/openapi.do?recommendDataYn=Y
[^39]: https://www.clim-past.net/8/1649/2012/cp-8-1649-2012.pdf
[^40]: https://www.mdpi.com/2071-1050/12/1/394/pdf
[^41]: https://www.mdpi.com/2072-4292/12/9/1532/pdf
[^42]: https://www.mdpi.com/2072-4292/12/14/2242/pdf
[^43]: https://www.mdpi.com/2072-4292/13/12/2266/pdf?version=1626322340
[^44]: https://www.mdpi.com/2073-4441/12/6/1590/pdf
[^45]: https://www.mdpi.com/2073-4441/13/22/3171/pdf
[^46]: https://www.mdpi.com/2073-4433/13/2/292/pdf?version=1644563857
[^47]: https://www.data.go.kr/data/15075543/fileData.do
[^48]: https://developevolvify.tistory.com/106
[^49]: https://velog.io/@minjiki2/API-공공데이터-오픈-API-사용법
