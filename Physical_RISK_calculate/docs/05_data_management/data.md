# 리스크 평가 필요 데이터 총정리

이 문서는 9대 물리적 리스크를 평가하는 데 필요한 모든 데이터의 출처와 종류를 정리합니다.

---

### 1. 🔥 폭염 (Extreme Heat)
- **위해성 (Hazard)**: CMIP6 SSP 시나리오 (일최고기온)
- **노출도 (Exposure)**: 환경부 토지피복도, 국토지리정보원 DEM
- **취약성 (Vulnerability)**: 국립중앙의료원 병원 API, 국토교통부 건축물대장 API

---

### 2. 🧊 한파 (Extreme Cold)
- **위해성 (Hazard)**: CMIP6 SSP 시나리오 (일최저기온)
- **노출도 (Exposure)**: 환경부 토지피복도, 국토지리정보원 DEM
- **취약성 (Vulnerability)**: 국립중앙의료원 병원 API, 국토교통부 건축물대장 API

---

### 3. 🔥 산불 (Wildfire)
- **위해성 (Hazard)**: ERA5 데이터 (FWI 계산용), 건조일수
- **노출도 (Exposure)**: 환경부 토지피복도, 국토지리정보원 DEM, 산림청 산불위험지도
- **취약성 (Vulnerability)**: 소방청 전국소방서 좌표, 환경부 토지피복도, 국토교통부 건축물대장 API

---

### 4. 🌧 도시 홍수 (Pluvial Flooding)
- **위해성 (Hazard)**: 기상청 강수량 데이터 (RX1DAY, SDII 등)
- **노출도 (Exposure)**: 환경부 토지피복도, 국토지리정보원 DEM, 행정안전부 인구밀도 데이터
- **취약성 (Vulnerability)**: 국토교통부 건축물대장 API (지하층)

---

### 5. 🌊 내륙 홍수 (Fluvial Flooding)
- **위해성 (Hazard)**: 기상청 강수량 데이터 (RX5DAY 등), WAMIS 유역/하천 데이터
- **노출도 (Exposure)**: 국토지리정보원 DEM, 행정안전부 재해연보 (침수 이력)
- **취약성 (Vulnerability)**: 국토교통부 건축물대장 API (건물 정보)

---

### 6. 🌊 해안 홍수 (Coastal Flood)
- **위해성 (Hazard)**: 기상청 SSP 시나리오 (해수면 상승)
- **노출도 (Exposure)**: 국토지리정보원 DEM, 해양수산부/OSM 해안선 벡터, 건축물대장 API
- **취약성 (Vulnerability)**: 국토교통부 건축물대장 API (건물 정보)

---

### 7. 💧 가뭄 (Drought)
- **위해성 (Hazard)**: 기상청 SSP 및 관측 데이터 (강수량, 기온)
- **노출도 (Exposure)**: 환경부 토지피복도, 통계청/행안부 인구통계
- **취약성 (Vulnerability)**: NASA SMAP 토양수분, MODIS NDVI

---

### 8. 🚱 물 부족 (Water Stress)
- **위해성 (Hazard)**: WAMIS 용수 취수량, 기상청 강수량, 통계청 인구 추계
- **노출도 (Exposure)**: 행정안전부 인구 데이터, 환경부 상수도 보급률
- **취약성 (Vulnerability)**: K-water 댐 저수율, 기상청 강수량, 환경부 상수도 보급률

---

### 9. 🌀 태풍 (Tropical Cyclone)
- **위해성 (Hazard)**: 기상청 SSP 시나리오 (일평균 풍속)
- **노출도 (Exposure)**: DART 전자공시 (자산가액) 또는 건축물대장 API (건물 면적)
- **취약성 (Vulnerability)**: 별도 데이터 없음 (계산식에 포함)
