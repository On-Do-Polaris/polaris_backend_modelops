# 정적 스니펫 기반 리포트 자동 생성 방식 (Template-based Report Generation)

## 1. 개요
본 시스템은 SKAX ESG 기후 리스크 평가에서 산출된 **HEV 및 AAL 결과값을 기반으로 자동 리포트를 생성**하기 위한 구조이다.  
현재 버전의 리포트 생성은 **사전에 정의된 9개 리스크와 각 리스크별 설명 스니펫**을 조합하여 문단을 구성하고,  
LLM이 해당 스니펫과 계산 결과를 바탕으로 자연어 형태의 리포트를 작성하는 방식으로 작동한다.

본 방식은 **RAG(Retrieval-Augmented Generation)**와 혼동될 수 있으나,  
실제 구조는 **검색 기반의 Retrieval 과정 없이 정적 매핑을 기반으로 콘텐츠를 조합하는 방식**이다.

---

## 2. 방식 정의
### 📌 현재 방식의 핵심 요소
- **고정된 리스크 개수**: 9개의 물리적 기후 리스크로 사전에 정의됨
- **정적 지식 구조**: 리스크별 설명(정의, 사용 지표, 산출식, 데이터소스, 근거 등)이 미리 정리된 형태로 존재
- **조건 기반 선택(lookup)**: 입력된 리스크 코드와 섹션 유형(section type)에 따라 대응되는 텍스트를 선택
- **LLM 자연어 변환**: 선택된 스니펫과 사업장별 수치를 결합하여 문장화

---

## 3. 처리 흐름

사업장 입력값 (HEV, AAL, 시나리오 등)
↓
리스크 코드 및 섹션 선택
↓
정적 스니펫 테이블에서 해당 텍스트 선택 (lookup)
↓
LLM에 입력 (스니펫 + 수치 + 작성 스타일)
↓
리포트 문단 자동 생성

---

## 4. 스니펫 구조 예시

```python
RISK_SNIPPETS = {
    "EXTREME_HEAT": {
        "overview": "극심한 고온(Extreme Heat) 리스크는 ...",
        "indicator": "본 리포트에서는 WSDI(Warm Spell Duration Index)를 지표로 사용하며...",
        "data_source": "데이터는 KMA SSP 1km NetCDF 기반 WSDI를 활용하였다...",
        "methodology": "AAL은 P(H)*Damage Ratio*Asset Value 공식을 통해 산출한다...",
        "academic_basis": "해당 기준은 IPCC AR6 및 환경부 기후적응 가이드에 준한다..."
    },
    ...
}