# API 문서

이 폴더에는 프로젝트에서 사용하는 다양한 외부 API 연동 가이드와 테스트 코드가 포함되어 있습니다.

## 📁 폴더 구조

```
03_api_documentation/
├── guides/          # API 연동 가이드 및 문서
├── references/      # API 참고 자료 (기술문서, 가이드북 등)
└── tests/           # API 테스트 스크립트
```

## 📚 주요 API 가이드

### 공공데이터 API

- [공공데이터포털 API](guides/01_공공데이터포털_API.md)
- [재난안전데이터공유플랫폼 API](guides/02_재난안전데이터공유플랫폼_API.md)
- [재난안전데이터플랫폼 API](guides/04_재난안전데이터플랫폼_API.md)

### 지도/공간 정보 API

- [VWorld API](guides/02_VWorld_API.md)
- [WMS](guides/WMS.md)

### 기상 정보 API

- [기상청 API](guides/03_기상청_API.md)
- [기상청 태풍베스트트랙 API](guides/03_기상청_태풍베스트트랙_API.md)

### 통계 API

- [SGIS 인구통계 API](guides/05_SGIS_인구통계_API.md)

### 기타 주제별 API

- [건축물 정보](guides/buildings.md)
- [병원 정보](guides/hospital.md)
- [소방서 정보](guides/firestation.md)
- [대피소 정보](guides/shelter.md)
- [태풍 정보](guides/typhoon.md)
- [산불 지도](guides/wildfiremap.md)
- 기타 다수...

## 🔑 API 키 관리

API 키 관리 방법은 [api_key.md](guides/api_key.md)를 참고하세요.

## 🧪 테스트

[tests/](tests/) 폴더에 각 API별 테스트 스크립트가 포함되어 있습니다.

## 📖 참고 자료

[references/](references/) 폴더에 API 기술문서 및 활용 가이드가 포함되어 있습니다.
