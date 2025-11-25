# API 테스트 스크립트

이 폴더에는 각 API의 동작을 검증하기 위한 테스트 스크립트가 포함되어 있습니다.

## 🧪 테스트 스크립트 목록

### 건축물 API 테스트

- `test_building_correct_jibun.py` - 지번 주소 정합성 테스트
- `test_building_final.py` - 최종 건축물 API 테스트
- `test_building_real_addresses.py` - 실제 주소 테스트
- `test_building_vworld.py` - VWorld 건축물 정보 테스트
- `test_building_with_addresses.py` - 주소 포함 테스트
- `test_building_with_juso_api.py` - 주소 API 연동 테스트
- `test_exact_jibun.py` - 정확한 지번 테스트

### 기상 API 테스트

- `test_kma_api.py` - 기상청 API 테스트
- `test_kma_typhoon_api.py` - 기상청 태풍 API 테스트

### 공공데이터 API 테스트

- `test_publicdata_api.py` - 공공데이터포털 API 테스트
- `test_all_publicdata_api.py` - 전체 공공데이터 API 테스트

### 재난안전 API 테스트

- `test_safety_api.py` - 재난안전 API 테스트
- `test_safetydata_api.py` - 재난안전데이터 API 테스트

### 통계 API 테스트

- `test_sgis_api.py` - SGIS 인구통계 API 테스트

### 기타 테스트

- `test_vworld_api.py` - VWorld API 테스트
- `test_sk_datacenter.py` - SK 데이터센터 테스트

## 🛠️ 유틸리티 스크립트

### 행정구역 코드 검색

- `find_adm_code.py` - 행정구역 코드 찾기
- `find_adm_code_new.py` - 행정구역 코드 찾기 (신규)
- `find_sk_datacenter_address.py` - SK 데이터센터 주소 찾기

## 📝 사용 방법

각 테스트 스크립트는 독립적으로 실행 가능하며, API 키가 필요한 경우 환경 변수 또는 설정 파일에서 읽어옵니다.

```bash
python test_building_final.py
```
