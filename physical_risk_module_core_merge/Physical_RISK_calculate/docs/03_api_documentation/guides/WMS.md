# VWorld WMS/WFS 공간정보 API

## 1. 개요
- **API:** VWorld WMS(Web Map Service) / WFS(Web Feature Service)
- **제공기관:** VWorld (브이월드)
- **설명:** VWorld에서 제공하는 고품질의 공간정보를 표준 OGC 인터페이스(WMS, WFS)를 통해 접근할 수 있는 API입니다. 도로, 건물, 지적도, 용도지역지구 등 다양한 레이어의 지도 이미지나 피처(벡터) 데이터를 직접 조회하고 분석하는 데 사용됩니다.
- **참고:** 이 문서에서는 `도로망` 데이터 접근을 중심으로 설명합니다.

## 2. 요청 정보
- **WMS Base URL:** `https://api.vworld.kr/req/wms`
- **WFS Base URL:** `https://api.vworld.kr/req/wfs`
- **인증:**
  - **인증키:** 필요 (VWorld에서 발급)
  - **전달 방식:** 요청 파라미터 `key`에 포함하여 전송
  - **샘플 키:** `961911EC-A96C-3B0E-AE0D-15B8E47EDF59` (**주의:** 테스트용으로, 실제 운영 시에는 본인의 인증키를 발급받아 사용해야 합니다.)
- **데이터 포맷:**
  - **WMS:** PNG, JPEG 등 이미지 포맷
  - **WFS:** GML, JSON, JSONP 등

## 3. 주요 오퍼레이션 및 활용 예시

### 가. 도로망 지도 이미지 요청 (WMS - GetMap)
- **Method:** `GET`
- **설명:** 특정 영역의 도로망 레이어를 지도 이미지로 요청합니다. 시각화에 주로 사용됩니다.
- **주요 요청 파라미터:**
  | 이름 | 파라미터명 | 필수 | 설명 |
  |---|---|---|---|
  | 서비스 | `service` | Y | `WMS` |
  | 요청 | `request` | Y | `GetMap` |
  | 인증키 | `key` | Y | 발급받은 인증키 |
  | 레이어 | `layers` | Y | `lt_c_spbd_info` (도로중심선) |
  | 좌표계 | `crs` | Y | `EPSG:4326` 등 요청 좌표계 |
  | 영역 | `bbox` | Y | `xmin,ymin,xmax,ymax` 형식의 영역 |
  | 너비/높이 | `width`/`height` | Y | 요청할 이미지의 픽셀 크기 |
  | 이미지 포맷 | `format` | Y | `image/png` 등 |

### 나. 도로망 데이터(피처) 요청 (WFS - GetFeature)
- **Method:** `GET`
- **설명:** 특정 조건(영역, 속성 등)에 맞는 도로망 데이터를 벡터(Feature) 형태로 직접 요청합니다. 도로의 밀도, 접근성 분석 등 공간 분석에 사용됩니다.
- **주요 요청 파라미터:**
  | 이름 | 파라미터명 | 필수 | 설명 |
  |---|---|---|---|
  | 서비스 | `service` | Y | `WFS` |
  | 요청 | `request` | Y | `GetFeature` |
  | 인증키 | `key` | Y | 발급받은 인증키 |
  | 레이어 | `typename` | Y | `lt_c_spbd_info` (도로중심선) |
  | 좌표계 | `srsname` | Y | `EPSG:4326` 등 요청 좌표계 |
  | 영역 | `bbox` | N | `xmin,ymin,xmax,ymax` 형식의 영역 |
  | 출력 포맷 | `output` | N | `application/json` 등 |
  | 필터 | `filter` | N | OGC Filter를 사용하여 속성 기반 필터링 |

- **주요 응답 필드 (도로중심선 레이어):**
  - `rn`: 도로명
  - `road_bt`: 도로 폭
  - `road_lt`: 도로 길이
  - `the_geom`: 도로의 공간 정보 (Geometry)


  WMS/WFS API 2.0 레퍼런스
버전 1.0
이전화면
소개
WMS(Web Map Service)와 WFS(Web Feature Service)를 통해 고품질의 공간정보 서비스를 제공합니다.
인증된 키를 사용하여 요청 URL을 서버에 전송하면 WMS 1.3.0 / WFS 1.1.0 서비스를 활용하실 수 있습니다.
WMS 요청 URL
https://api.vworld.kr/req/wms?key=인증키&[WMS Param]
주의! https나 Flex 등 웹뷰어가 아닌 브라우저에서의 API사용은 요청URL에 도메인정보를 추가하여 서비스를 이용합니다.

예) https://api.vworld.kr/req/wms?key=인증키&domain=인증받은도메인&[WMS Param]
WFS 요청 URL
https://api.vworld.kr/req/wfs?key=인증키&[WFS Param]
주의! https나 Flex 등 웹뷰어가 아닌 브라우저에서의 API사용은 요청URL에 도메인정보를 추가하여 서비스를 이용합니다.

예) https://api.vworld.kr/req/wfs?key=인증키&domain=인증받은도메인&[WFS Param]
서비스대상(총 167종)
경계 : 광역시도, 리, 시군구, 읍면동 (4종)
관광 : 관광안내소, 전통시장현황 (2종)
교통 : 교통CCTV, 교통노드, 교통링크, 도로중심선 (4종)
국가지명 : 국가지명 (1종)
농업·농촌 : 농업진흥지역도, 영농여건불리농지도 (2종)
도시계획 : 개발행위허가제한지역, 도시계획(공간시설), 도시계획(공공문화체육시설) 등 (12종)
문화재 : 국가유산보호도, 박물관미술관, 전통사찰보존 (3종)
문화예술 : 작은도서관 (1종)
사회복지 : 기타보호시설, 노인복지시설, 아동복지시설, 아동안전지킴이집 (4종)
산업 : 주요상권, 창업보육센터 (2종)
산업단지 : 단지경계, 단지시설용지, 단지용도지역, 단지유치업종 (4종)
수자원 : 대권역, 중권역, 표준권역, 하천망 (4종)
용도지역지구 : 개발제한구역, 개발진흥지구, 경관지구, 고도지구, 관리지역 등 (17종)
용도지역지구(기타) : 가축사육제한지역, 관광지, 국민임대주택, 급경사재해예방지역 등 (17종)
일반행정 : 도로명주소건물, 도로명주소도로, 건축물정보 (3종)
임업·산촌 : 산림입지도 (1종)
자연 : 단층, 배수등급, 수문지질단위, 수질다이어그램, 심토토성, 유효토심, 자갈함량 등 (14종)
정밀도로지도 : 과속방지턱, 노면선표시, 노면표시, 높이장애물, 보도구간, 신호등, 안전표지 등 (15종)
재난방재 : 산불위험예측지도, 소방서관할구역, 재해위험지구 (3종)
체육 : 국립자연공원, 군립자연공원, 도립자연공원, 등산로, 자전거보관소 (5종)
토지 : 사업지구경계도, 연속지적도, LX맵 (3종)
학교 : 고등학교학교군, 교육행정구역, 중학교학교군, 초등학교학교군 (4종)
항공·공항 : (UA)초경량비행장치공역, 경계구역, 공중급유구역, 공중전투기동훈련장, 관제권 등 (21종)
해양·수산·어촌 : (2차) 관리연안해역, (2차) 보전연안해역, (2차) 이용연안해역, (2차) 특수연안해역 등 (13종)
환경보호 : 골프장현황도, 상수원보호, 수질측정망공단배수지점, 수질측정망농업용수지점 등 (8종)
레이어리스트 상세보기

상세보기
WMS 상세정보
요청파라미터
파라미터	선택	설명	유효값
service	O/1	요청 서비스명	WMS(기본값)
version	O/1	요청 서비스 버전	1.3.0(기본값)
request	M/1	요청 서비스 오퍼레이션	GetMap, GetCapabilities
key	M/1	발급받은 api key	
format	O/1	응답결과 포맷	image/png(기본값)
exceptions	O/1	에러 응답결과 포맷	text/xml(기본값)
layers	M/1	하나 또는 쉼표(,)로 분리된 지도레이어 목록, 최대 4개	레이어 목록 참고
styles	O/1	LAYERS와 1대1 관계의 하나 또는 쉼표(,)로 분리된 스타일 목록	레이어 목록 참고
bbox	M/1	요청 객체의 Bounding box
(xmin,ymin,xmax,ymax)	예외) EPSG:4326, EPSG:5185, EPSG:5186, EPSG:5187, EPSG:5188 경우 (ymin,xmin,ymax,xmax)
width	M/1	지도의 픽셀 너비	숫자
height	M/1	지도의 픽셀 너비	숫자
transparent	O/1	지도 배경의 투명도 여부	TRUE, FALSE(기본값)
bgcolor	O/1	배경색 정의부	0xFFFFFF(기본값)
crs	O/1	응답결과 좌표계와 bbox 파라미터의 좌표계, 지원좌표계	EPSG:4326(기본값)
domain	O/1	API KEY를 발급받을때 입력했던 URL
* HTTPS,FLEX등 웹뷰어가 아닌 브라우저에서의 API사용은 DOMAIN을 추가하여 서비스를 이용할 수 있습니다.	
GetFeatueInfo 요청파라미터
파라미터	선택	설명	유효값
service	O/1	요청 서비스명	WMS(기본값)
version	O/1	요청 서비스 버전	1.3.0(기본값)
key	M/1	발급받은 api key	
layers	M/1	하나 또는 쉼표(,)로 분리된 지도레이어 목록, 최대 4개	레이어 목록 참고
styles	O/1	LAYERS와 1대1 관계의 하나 또는 쉼표(,)로 분리된 스타일 목록	레이어 목록 참고
crs	O/1	응답결과 좌표계와 bbox 파라미터의 좌표계, 지원좌표계	EPSG:4326(기본값)
bbox	M/1	요청 객체의 Bounding box
(xmin,ymin,xmax,ymax)	예외) EPSG:4326, EPSG:5185, EPSG:5186, EPSG:5187, EPSG:5188 경우 (ymin,xmin,ymax,xmax)
width	M/1	지도의 픽셀 너비	숫자
height	M/1	지도의 픽셀 너비	숫자
request	M/1	요청 서비스 오퍼레이션	GetFeatueInfo
query_layers	M/1	하나 또는 쉼표(,)로 분리된 지도레이어 목록	레이어 목록 참고
info_format	O/1	응답결과 포맷	info_format 참조
feature_count	O/1	출력되는 피처의 최대 개수	기본값 : 1
i	M/1	지도상의 X좌표(왼쪽이 0)	
j	M/1	지도상이 Y좌표(상단이 0)	
exceptions	O/1	에러 응답결과 포맷	text/xml(기본값)
info_format
Format	Syntax
TEXT	info_format=text/plain(기본값)
GML 2	info_format=application/vnd.ogc.gml
GML 3	info_format=application/vnd.ogc.gml/3.1.1
HTML	info_format=text/html
JSON	info_format=application/json
JSONP	info_format=text/javascript
WMS 사용예제
클립보드에 복사
API결과 미리보기
https://api.vworld.kr/req/wms?
SERVICE=WMS&
REQUEST=GetMap&
VERSION=1.3.0&
LAYERS=lp_pa_cbnd_bonbun,lp_pa_cbnd_bubun&
STYLES=lp_pa_cbnd_bonbun_line,lp_pa_cbnd_bubun_line&
CRS=EPSG:900913&
BBOX=14133818.022824,4520485.8511757,14134123.770937,4520791.5992888&
WIDTH=256&
HEIGHT=256&
FORMAT=image/png&
TRANSPARENT=false&
BGCOLOR=0xFFFFFF&
EXCEPTIONS=text/xml&
KEY=[KEY]&
DOMAIN=[DOMAIN]
OGC WMS specification
https://www.ogc.org/standard/wms
WFS 상세정보
WFS 컬럼정보
WFS 컬럼정보 파일 내려받기
요청파라미터
파라미터	선택	설명	유효값
service	O/1	요청 서비스명	WFS(기본값)
version	O/1	요청 서비스 버전	1.1.0(기본값)
request	M/1	요청 서비스 오퍼레이션	GetFeature, GetCapabilities
key	M/1	발급받은 api key	
output	O/1	응답결과 포맷
* output=text/javascript는 JSONP를 반환	text/xml; subtype=gml/2.1.2(기본값),
GML2,
text/xml; subtype=gml/3.1.1,
GML3,
application/json,
text/javascript
format_options	O/1	jsonp 응답 형식의 콜백 함수 이름을 지정합니다.
ex) format_options=callback:func_callback	기본값 : parseResponse
exceptions	O/1	에러 응답결과 포맷	text/xml(기본값)
typename	M/1	하나 또는 쉼표(,)로 분리된 지도레이어 목록, 최대 4개	레이어 목록 참고
featureid	O/1	요청 FEATURE ID	
bbox	O/1	요청 객체의 Bounding box	EPSG:4326일 경우 (ymin,xmin,ymax,xmax) , 그 외 (xmin,ymin,xmax,ymax)
propertyname	O/1	하나 또는 쉼표(,)로 분리된 속성 목록	
maxfeatures	O/1	출력되는 피처의 최대 개수
* version파라미터 값이 1.0.0일때 사용가능	숫자 기본값 : 1000, 최소값 : 1, 최대값 : 1000
count	O/1	출력되는 피처의 최대 개수
* version파라미터 값이 2.0.0일때만 사용가능	숫자 기본값 : 1000, 최소값 : 1, 최대값 : 1000
startindex	O/1	출력되는 피처의 시작지점 설정
* version파라미터 값이 2.0.0일때만 사용가능	예) startindex=10이면 11번째 피처부터 출력
sortby	O/1	정렬하고 싶은 속성명을 지정한다.
사용법 : PropertyName [A|D][,PropertyName [A|D],…], A는 오름차순, D는 내림차순에 사용한다.
예 제 : sortby=Field1 D,Field A	입력값을 encodeURIComponent로 변환 후 요청
srsname	O/1	응답결과 좌표계와 bbox 파라미터의 좌표계, 지원좌표계	EPSG:900913(기본값)
domain	O/1	API KEY를 발급받을때 입력했던 URL
* HTTPS,FLEX등 웹뷰어가 아닌 브라우저에서의 API사용은 DOMAIN을 추가하여 서비스를 이용할 수 있습니다.	
filter	O/1	WFS FILTER 1.1 Specification 참고	입력값을 encodeURIComponent로 변환 후 요청
WFS 사용예제
클립보드에 복사
API결과 미리보기
https://api.vworld.kr/req/wfs?
SERVICE=WFS&
REQUEST=GetFeature&
TYPENAME=lt_c_uq111&
BBOX=13987670,3912271,14359383,4642932&
PROPERTYNAME=mnum,sido_cd,sigungu_cd,dyear,dnum,ucode,bon_bun,bu_bun,uname,sido_name,sigg_name,ag_geom&
VERSION=1.1.0&
MAXFEATURES=40&
SRSNAME=EPSG:900913&
OUTPUT=GML2&
EXCEPTIONS=text/xml&
KEY=[KEY]&
DOMAIN=[DOMAIN]&
FILTER=[WFS FILTER 1.1 참고]
OGC WFS specification
https://www.ogc.org/standard/wfs
WFS FILTER 1.1 Specification
https://www.ogc.org/standard/filter
WFS FILTER 1.1 예제
- PropertyIsEqualTo
<ogc:Filter>
     <ogc:PropertyIsEqualTo matchCase="true">
          <ogc:PropertyName>dyear</ogc:PropertyName>
          <ogc:Literal>2005</ogc:Literal>
     </ogc:PropertyIsEqualTo>
</ogc:Filter>
- PropertyIsNotEqualTo
<ogc:Filter>
     <ogc:PropertyIsNotEqualTo matchCase="true">
          <ogc:PropertyName>dyear</ogc:PropertyName>
          <ogc:Literal>2005</ogc:Literal>
     </ogc:PropertyIsNotEqualTo>
</ogc:Filter>
- PropertyIsLessThan
<ogc:Filter>
     <ogc:PropertyIsLessThan matchCase="false">
          <ogc:PropertyName>dyear</ogc:PropertyName>
          <ogc:Literal>2005</ogc:Literal>
     </ogc:PropertyIsLessThan>
</ogc:Filter>
- PropertyIsLessThanOrEqualTo
<ogc:Filter>
     <ogc:PropertyIsLessThanOrEqualTo matchCase="false">
          <ogc:PropertyName>dyear</ogc:PropertyName>
          <ogc:Literal>2005</ogc:Literal>
     </ogc:PropertyIsLessThanOrEqualTo>
</ogc:Filter>
- PropertyIsGreaterThan
<ogc:Filter>
     <ogc:PropertyIsGreaterThan matchCase="true">
          <ogc:PropertyName>dyear</ogc:PropertyName>
          <ogc:Literal>2005</ogc:Literal>
     </ogc:PropertyIsGreaterThan>
</ogc:Filter>
- PropertyIsGreaterThanOrEqualTo
<ogc:Filter>
     <ogc:PropertyIsGreaterThanOrEqualTo matchCase="false">
          <ogc:PropertyName>dyear</ogc:PropertyName>
          <ogc:Literal>2005</ogc:Literal>
     </ogc:PropertyIsGreaterThanOrEqualTo>
</ogc:Filter>
- PropertyIsLike
<ogc:Filter>
     <ogc:PropertyIsLike wildCard="*" singleChar="_" escapeChar="\">
          <ogc:PropertyName>sido_name</ogc:PropertyName>
          <ogc:Literal>서울*</ogc:Literal>
     </ogc:PropertyIsLike>
</ogc:Filter>
- PropertyIsNull
<ogc:Filter>
     <ogc:PropertyIsNull>
          <ogc:PropertyName>remark</ogc:PropertyName>
     </ogc:PropertyIsLike>
</ogc:Filter>
- PropertyIsBetween
<ogc:Filter>
     <ogc:PropertyIsBetween>
          <ogc:PropertyName>dyear</ogc:PropertyName>
          <ogc:LowerBoundary>
               <ogc:Literal>2000</ogc:Literal>
          </ogc:LowerBoundary>
          <ogc:UpperBoundary>
               <ogc:Literal>2005</ogc:Literal>
          </ogc:UpperBoundary>
     </ogc:PropertyIsBetween>
</ogc:Filter>
- Intersects
<ogc:Filter>
     <ogc:Intersects>
          <ogc:PropertyName>ag_geom</ogc:PropertyName>
          <Point srsName="EPSG:900913">
               <pos>14132768.287088 4494181.0225382</pos>
          </Point>
     </ogc:Intersects>
</ogc:Filter>
- BBOX
<ogc:Filter>
     <ogc:BBOX>
          <ogc:PropertyName>ag_geom</ogc:PropertyName>
          <Envelope srsDimension="2" srsName="EPSG:900913">
               <lowerCorner>14132768.287088 4494181.0225382</lowerCorner>
               <upperCorner>14132777.841717 4494190.5771668</upperCorner>
          </Envelope>
     </ogc:BBOX>
</ogc:Filter>
- AND
<ogc:Filter>
     <ogc:And>
          <ogc:PropertyIsEqualTo>
               <ogc:PropertyName>sigg_name</ogc:PropertyName>
               <ogc:Literal>안양시동안구</ogc:Literal>
          </ogc:PropertyIsEqualTo>
          <ogc:PropertyIsLessThan>
               <ogc:PropertyName>ucode</ogc:PropertyName>
               <ogc:Literal>UQA112</ogc:Literal>
          </ogc:PropertyIsLessThan>
     </ogc:And>
</ogc:Filter>
- Or
<ogc:Filter>
     <ogc:Or>
          <ogc:PropertyIsGreaterThan>
               <ogc:PropertyName>ucode</ogc:PropertyName>
               <ogc:Literal>UQA113</ogc:Literal>
          </ogc:PropertyIsGreaterThan>
          <ogc:PropertyIsLessThan>
               <ogc:PropertyName>sigungu_cd</ogc:PropertyName>
               <ogc:Literal>174</ogc:Literal>
          </ogc:PropertyIsLessThan>
     </ogc:Or>
</ogc:Filter>
- Not
<ogc:Filter>
     <ogc:Not>
          <ogc:PropertyIsEqualTo>
               <ogc:PropertyName>sigg_name</ogc:PropertyName>
               <ogc:Literal>종로구</ogc:Literal>
          </ogc:PropertyIsEqualTo>
     </ogc:Not>
</ogc:Filter>
- Spatial + Attribute
<ogc:Filter>
     <ogc:And>
          <ogc:PropertyIsLessThan>
               <ogc:PropertyName>sigungu_cd</ogc:PropertyName>
               <ogc:Literal>174</ogc:Literal>
          </ogc:PropertyIsLessThan>
          <ogc:Intersects>
               <ogc:PropertyName>ag_geom</ogc:PropertyName>
               <Point srsName="EPSG:900913">
                    <pos>14132768.287088 4494181.0225382</pos>
               </Point>
          </ogc:Intersects>
     </ogc:And>
</ogc:Filter>
WMS/WFS 공통정보
지원좌표계
좌표계	설명
WGS84 경위도	EPSG:4326
GRS80 경위도	EPSG:4019
Google Mercator	EPSG:3857, EPSG:900913
서부원점(GRS80)	EPSG:5180(50만), EPSG:5185
중부원점(GRS80)	EPSG:5181(50만), EPSG:5186
제주원점(GRS80, 55만)	EPSG:5182
동부원점(GRS80)	EPSG:5183(50만), EPSG:5187
동해(울릉)원점(GRS80)	EPSG:5184(50만), EPSG:5188
UTM-K(GRS80)	EPSG:5179
오류 응답결과
항목명	타입	설명
service	문자	요청 서비스 정보 Root
 	name	문자	요청 서비스명
 	version	숫자	요청 서비스 버전
 	operation	문자	요청 서비스 오퍼레이션 이름
 	time	숫자	응답결과 생성 시간
status	문자	처리 결과의 상태 표시, 유효값 : OK(성공), NOT_FOUND(결과없음), ERROR(에러)
error	문자	에러 정보 Root
 	level	숫자	에러 레벨
 	code	문자	에러 코드
 	text	문자	에러 메시지
오류메세지
코드	레벨	메세지	비고
PARAM_REQUIRED	1	필수 파라미터인 <%S1>가 없어서 요청을 처리할수 없습니다.	%S1 : 파라미터 이름
INVALID_TYPE	1	<%S1> 파라미터 타입이 유효하지 않습니다.
유효한 파라미터 타입 : <%S2>
입력한 파라미터 값 : <%S3>	%S1 : 파라미터 이름
%S2 : 유효한 파라미터 값의 유형
%S3 : 입력한 파라미터 값
INVALID_RANGE	1	<%S1> 파라미터의 값이 유효한 범위를 넘었습니다.
유효한 파라미터 타입 : <%S2>
입력한 파라미터 값 : <%S3>	%S1 : 파라미터 이름
%S2 : 유효한 파라미터 값의 범위
%S3 : 입력한 파라미터 값
INVALID_KEY	2	등록되지 않은 인증키입니다.	 
INCORRECT_KEY	2	인증키 정보가 올바르지 않습니다.
(ex. 인증키 발급 시 입력한 도메인이 다를경우)	 
UNAVAILABLE_KEY	2	임시로 인증키를 사용할 수 없는 상태입니다.	 
OVER_REQUEST_LIMIT	2	서비스 사용량이 일일 제한량을 초과하여 더 이상 서비스를 사용할 수 없습니다.	 
SYSTEM_ERROR	3	시스템 에러가 발생하였습니다.	 
UNKNOWN_ERROR	3	알 수 없는 에러가 발생하였습니다.	 
오픈API 목록 돌아가기