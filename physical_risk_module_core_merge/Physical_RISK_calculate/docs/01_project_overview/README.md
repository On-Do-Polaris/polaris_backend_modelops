# 프로젝트 개요

이 폴더에는 SK AX 기후리스크 분석 프로젝트의 전체 개요와 시스템 아키텍처 문서가 포함되어 있습니다.

## 📚 문서 목록

### ⭐ 핵심 문서 (필독)

1. **[SYSTEM_ARCHITECTURE.md](./SYSTEM_ARCHITECTURE.md)** - 시스템 전체 아키텍처
   - H × E × V 계산 방식
   - 9개 물리적 리스크 평가 구조
   - 4개 SSP 시나리오 계산 지원 (v2.0.0)
   - 데이터 플로우 및 모듈 관계
   - 실제 사용 예시

2. **[DATA_SOURCES.md](./DATA_SOURCES.md)** - 데이터 소스 상세 가이드
   - KMA SSP 시나리오 (NetCDF)
   - 공간 데이터 (토지피복도, NDVI, DEM, SMAP)
   - 건축물대장 API
   - 재난안전데이터 API
   - 데이터 품질 관리 (93% 실제 데이터 사용)

3. **[CODE_MODULES.md](./CODE_MODULES.md)** - 코드 모듈 상세 가이드
   - risk_calculator.py (메인 오케스트레이터)
   - hazard_calculator.py (재난 강도 계산)
   - exposure_calculator.py (노출도 계산)
   - vulnerability_calculator.py (취약성 계산)
   - 데이터 로더 모듈
   - 의존성 관계

4. **[API_IMPLEMENTATION_STATUS.md](./API_IMPLEMENTATION_STATUS.md)** - API 구현 현황 (신규)
   - ✅ 완전 구현된 API (8개)
   - ⚠️ 부분 구현 (1개)
   - 🔴 미구현 (2개)
   - API 키 필요 여부
   - Fallback 정책
   - 향후 개선 계획

### 📋 기존 문서

- **ERD_Final_Guide.md** - 데이터베이스 ERD 최종 가이드
- **SK AX 기후리스크 분석 프로젝트 - 데이터 상세 정리.md** - 프로젝트 전체 데이터 상세 설명

## 🚀 빠른 시작 가이드

### 1. 시스템 이해하기

```
Risk Score = Hazard (H) × Exposure (E) × Vulnerability (V)
```

- **Hazard**: 재난의 강도 (기후 시나리오, 재난 이력 기반)
- **Exposure**: 노출도 (건물 위치, 특성)
- **Vulnerability**: 취약성 (건물의 재난 대응 능력)

### 2. 평가 대상 리스크

1. 극심한 고온 (Extreme Heat)
2. 극심한 극심한 한파 (Extreme Cold)
3. 가뭄 (Drought)
4. 하천 홍수 (River Flood)
5. 도시 홍수 (Urban Flood)
6. 해수면 상승 (Sea Level Rise)
7. 태풍 (Typhoon)
8. 산불 (Wildfire)
9. 물부족 (Water Stress)

### 3. 사용 예시

#### v2.0.0: 4개 시나리오 모두 계산

```python
from code.risk_calculator import RiskCalculator

# 전체 시나리오 계산 (SSP126, SSP245, SSP370, SSP585)
calculator = RiskCalculator(target_year=2030)
result = calculator.calculate_all_risks("대전광역시 유성구 엑스포로 325")

# 결과 확인
for scenario in ['SSP126', 'SSP245', 'SSP370', 'SSP585']:
    total = result['scenarios'][scenario]['total_score']
    level = result['scenarios'][scenario]['risk_level']
    print(f"{scenario}: {total:.1f}점 ({level})")

# 특정 시나리오만 계산
calculator = RiskCalculator(scenarios=['SSP245', 'SSP585'], target_year=2050)
result = calculator.calculate_all_risks((36.383, 127.395))
```

**결과 구조**:
```json
{
  "scenarios": {
    "SSP126": {
      "risks": { 극한고온, 극심한 한파, 가뭄... },
      "total_score": 456.78,
      "risk_level": "HIGH"
    },
    "SSP245": { ... },
    "SSP370": { ... },
    "SSP585": { ... }
  },
  "exposure": { E 데이터 },
  "vulnerability": { V 데이터 }
}
```

## 📊 데이터 소스 요약

### 기후 데이터
- **KMA SSP 시나리오** (2021-2100)
  - 파일 형식: NetCDF (.nc), gzip 압축
  - 공간 해상도: 1km 격자
  - 변수: TXx, SU25, TR25, TNn, FD0, RN, CDD, RX1DAY 등 15개

### 공간 데이터
- **토지피복도**: 환경부 중분류 (GeoTIFF)
- **NDVI**: MODIS 위성 식생지수 (HDF)
- **토양수분**: NASA SMAP L4 (HDF5)
- **DEM**: 국토지리정보원 5m 고도 (.img)
- **행정구역**: 통계청 읍면동 경계 (Shapefile)

### API 데이터
- **건축물대장**: 국토교통부 API
- **재난 이력**: 행정안전부 API
- **주소 변환**: V-World API

## 🎯 데이터 품질

**전체 시스템 실제 데이터 사용률: 93%**

| 리스크 | 실제 데이터 | 사용률 |
|--------|------------|--------|
| 극심한 고온 | KMA SSP | 100% |
| 극심한 극심한 한파 | KMA SSP | 100% |
| 가뭄 | KMA SSP + SMAP | 90% |
| 하천 홍수 | KMA SSP + 재난 API + DEM | 100% |
| 도시 홍수 | KMA SSP + 토지피복도 | 100% |
| 해수면 상승 | Haversine 거리 | 100% |
| 태풍 | 통계 | 70% |
| 산불 | NDVI + 토지피복도 + KMA | 100% |
| 수자원 | 인구 통계 | 70% |

## 🔧 시스템 요구사항

### Python 라이브러리

```bash
pip install netCDF4       # KMA SSP NetCDF 읽기
pip install h5py          # SMAP 토양수분 HDF5 읽기
pip install rasterio      # 토지피복도 GeoTIFF 읽기
pip install geopandas     # 행정구역 Shapefile 읽기
pip install requests      # API 호출
pip install python-dotenv # 환경 변수 관리
```

### API 키 설정

`.env` 파일 생성:
```
VWORLD_API_KEY=your_vworld_key
BUILDING_API_KEY=your_building_key
```

## 📁 코드 구조

```
Physical_RISK_calculate/code/
├── risk_calculator.py          # 메인 오케스트레이터 (H×E×V)
├── hazard_calculator.py        # H 계산 (재난 강도)
├── exposure_calculator.py      # E 계산 (노출도)
├── vulnerability_calculator.py # V 계산 (취약성)
│
├── climate_data_loader.py      # KMA SSP NetCDF 로더
├── spatial_data_loader.py      # 토지피복도/NDVI/토양수분 로더
├── building_data_fetcher.py    # 건축물대장 API
├── disaster_api_fetcher.py     # 재난 API
└── stream_order_simple.py      # DEM 지형 분석
```

## 🔍 관련 문서

- [데이터 모델](../02_data_models/) - DBML 스키마 정의
- [API 문서](../03_api_documentation/) - API 연동 가이드
- [리스크 분석](../04_risk_analysis/) - 재해 유형별 분석 방법론
- [데이터 관리](../05_data_management/) - 데이터 전처리 및 관리

## 📝 주요 특징

### TCFD 준수
- 모든 데이터 소스 명시
- 품질 등급 평가 (high/medium/low)
- TCFD 경고 메시지 제공

### 시나리오 기반 분석
- SSP126: 저탄소 시나리오
- SSP245: 중간 시나리오 (기본값)
- SSP370: 고탄소 시나리오
- SSP585: 최악 시나리오

### 도로명 주소 지원
- 도로명 주소: "대전광역시 유성구 엑스포로 325"
- 지번 주소: "대전광역시 유성구 원촌동 140-1"
- 자동 변환 (V-World API)

## 🐛 알려진 이슈 및 향후 개선

### 진행 중
1. ⚠️ SMAP 토양수분 좌표 변환 (현재 -9999 반환)
2. ⚠️ RN 연간 강수량 일부 파일 로드 실패

### 향후 개선
1. 태풍 Best Track API 연동
2. 수도 사용량 API 연동
3. 배치 분석 기능 (여러 주소 동시 처리)
4. PDF/DOCX 리포트 생성

---

## 📝 변경 이력

### v2.0.0 (2024-11-24)
- ✅ **4개 SSP 시나리오 동시 계산 지원** (SSP126/245/370/585)
- ✅ 시나리오별 비교 출력 기능
- ✅ API 구현 현황 문서 작성
- ✅ 도로명 주소 변환 버그 수정 (ROAD/PARCEL 자동 전환)
- ✅ disaster_api_fetcher.py 정상 작동 확인

### v1.0.0 (2024-11-22)
- 최초 버전
- 9개 물리적 리스크 평가
- H × E × V 계산 구조
- 단일 시나리오 (SSP245) 지원

---

**프로젝트**: SK AX 물리적 기후 리스크 평가 시스템
**버전**: 2.0.0
**최종 업데이트**: 2024-11-24
