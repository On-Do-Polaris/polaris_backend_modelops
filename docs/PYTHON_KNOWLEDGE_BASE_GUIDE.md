# Python Knowledge Base (파이썬 지식 베이스) 활용 가이드

## 📌 개요

이 문서는 파이썬 파일을 **Knowledge Base**(지식 베이스) 또는 **Static RAG**(정적 RAG)로 활용하는 방법에 대해 설명합니다.

## 🔍 명칭 및 개념

### 일반적으로 사용되는 명칭들

1. **Knowledge Base (지식 베이스)**
   - 구조화된 지식을 파이썬 딕셔너리/리스트로 저장
   - 가장 일반적이고 직관적인 명칭

2. **Static RAG (정적 RAG)**
   - Retrieval-Augmented Generation의 간소화 버전
   - 벡터 DB 없이 직접 참조하는 방식

3. **In-Memory Knowledge Store (인메모리 지식 저장소)**
   - 메모리에 로드되어 즉시 접근 가능한 지식 저장 방식

4. **Embedded Knowledge Repository (임베디드 지식 저장소)**
   - 코드에 내장된 지식 저장소

5. **Code-as-Data Pattern (코드-데이터 패턴)**
   - 코드와 데이터를 함께 관리하는 패턴

## 🆚 기존 RAG vs Python Knowledge Base 비교

| 구분 | 전통적 RAG | Python Knowledge Base |
|------|-----------|----------------------|
| **데이터 저장** | 벡터 DB (Pinecone, ChromaDB 등) | Python 딕셔너리/리스트 |
| **검색 방식** | 벡터 유사도 검색 | 딕셔너리 키 직접 접근 |
| **속도** | DB 쿼리 필요 (수십~수백ms) | 메모리 접근 (1ms 이하) |
| **복잡도** | 높음 (임베딩, 벡터화 필요) | 낮음 (import만 필요) |
| **적합한 경우** | 대량의 비정형 문서 검색 | 구조화된 메타데이터, 룰 기반 지식 |
| **유지보수** | DB 관리 필요 | 코드와 함께 버전 관리 |

## 📂 프로젝트 예시 분석

### 1. question_generator.py (기존 예시)

```python
# 구조화된 질문 은행을 딕셔너리로 저장
QUESTION_BANK = {
    "BAS": [
        {
            "id": "B01",
            "level": 1,
            "text": "만나서 반가워. 오늘 하루는 어땠어?",
            "insight": "대화 시작 및 초기 라포 형성"
        },
        # ... 더 많은 질문들
    ],
    "PEER": [...],
    "SCH": [...]
}

class QuestionGenerator:
    def __init__(self):
        self.question_bank = QUESTION_BANK

    def generate_question_set(self, category: str, count: int = 5) -> list:
        # 카테고리별로 질문을 직접 검색하여 반환
        if category not in self.question_bank:
            return []
        # ...
```

**특징:**
- 카테고리 기반 구조화된 지식
- 클래스를 통한 접근 제어
- 메모리 효율적 (import 시 한 번만 로드)

### 2. LLM_RAG_DATA_DICTIONARY.json을 Python Knowledge Base로 전환

현재 JSON 파일로 관리 중인 데이터 딕셔너리를 Python Knowledge Base로 전환하면 다음과 같은 이점이 있습니다:

#### 이점:
1. **타입 안정성**: Python 타입 힌팅 활용 가능
2. **코드 자동완성**: IDE에서 자동완성 지원
3. **성능**: JSON 파싱 불필요, 직접 메모리 접근
4. **버전 관리**: Git으로 코드와 함께 관리
5. **유효성 검증**: import 시 문법 오류 자동 검출

## 🛠️ 우리 프로젝트 적용 방안

### 방안 1: Climate Data Dictionary를 Python Knowledge Base로 전환

**파일 생성: `docs/climate_data_dictionary.py`**

```python
"""
Climate Data Dictionary - Knowledge Base for Report Generation
기후 데이터 딕셔너리 - 리포트 생성을 위한 지식 베이스
"""

from typing import Dict, List, Any
from dataclasses import dataclass

@dataclass
class DataField:
    """기후 데이터 필드 정보"""
    full_name: str
    definition: str
    unit: str
    data_source: str
    high_value_means: str
    impacts_on: Dict[str, str]
    used_in: List[str]
    interaction_with_other_data: Dict[str, str]
    calculation_formula: str = ""
    bin_descriptions: Dict[str, str] = None

# 극심한 고온 (Extreme Heat)
EXTREME_HEAT = {
    "WSDI": DataField(
        full_name="Warm Spell Duration Index (열파 지속 지수)",
        definition="평년(1981-2010) 대비 일최고기온이 90백분위 이상인 날이 최소 6일 연속되는 기간의 연간 일수 합계",
        unit="일/년 (days)",
        data_source="KMA 극값지수",
        high_value_means="WSDI > Q99 (상위 1%)는 극한 폭염을 의미하며, 건물 냉방 부하 증가, 에너지 소비 급증, 인프라 열화 가속을 유발합니다.",
        impacts_on={
            "financial_risk": "냉방비 급증으로 OPEX 증가. WSDI > Q99 시 손상률 3.5%, 일반 수준 대비 35배 증가",
            "operational_risk": "고온으로 인한 설비 과부하, 직원 생산성 저하",
            "reputation_risk": "기후 적응 능력 부족으로 TCFD 공시에서 물리적 리스크 대응 미흡 평가"
        },
        used_in=[
            "Impact Analysis: 폭염 강도별 에너지 비용 증가율 추정",
            "Strategy Generation: 외기 냉방제어 시스템 도입, 고효율 냉방기 교체",
            "Report Generation: TCFD 물리적 리스크 섹션에서 SSP 시나리오별 WSDI 추이 분석"
        ],
        interaction_with_other_data={
            "baseline_wsdi": "기준기간(1991-2020) WSDI 데이터로 분위수 임계값 계산"
        },
        bin_descriptions={
            "bin_0": "일반 수준 - 손상률 0.1%",
            "bin_1": "경미 폭염 - 손상률 0.5%",
            "bin_2": "중간 폭염 - 손상률 1.5%",
            "bin_3": "심각 폭염 - 손상률 2.8%",
            "bin_4": "극한 폭염 - 손상률 3.5%"
        }
    )
}

# 가뭄 (Drought)
DROUGHT = {
    "SPEI_12": DataField(
        full_name="Standardized Precipitation-Evapotranspiration Index 12개월",
        definition="강수량과 증발산량을 고려한 12개월 누적 수분 가용성 지수",
        unit="무차원 (표준화 지수)",
        data_source="KMA SPEI 데이터",
        high_value_means="SPEI-12 ≤ -2.0 (극심 가뭄)은 용수 공급 제한, 토양 수분 고갈을 의미합니다.",
        impacts_on={
            "financial_risk": "SPEI-12 ≤ -2.0 시 손상률 20%, 용수비 최대 3배 상승 가능",
            "operational_risk": "용수 공급 제한으로 제조 공정 중단 위험",
            "reputation_risk": "CDP Water 등급 하락 가능"
        },
        used_in=[
            "Impact Analysis: 가뭄 심도별 용수 비용 증가 정량화",
            "Strategy Generation: 우수 집수 탱크 설치, 용수 재이용률 70% 달성",
            "Report Generation: TCFD 물 스트레스 대응 전략 공시"
        ],
        interaction_with_other_data={
            "monthly_data": "월별 SPEI-12 값을 평탄화하여 월 기반 확률 계산"
        },
        bin_descriptions={
            "bin_0": "정상~습윤 - 손상률 0.1%",
            "bin_1": "중간 가뭄 - 손상률 2%",
            "bin_2": "심각 가뭄 - 손상률 8%",
            "bin_3": "극심 가뭄 - 손상률 20%"
        }
    )
}

# 전체 데이터 딕셔너리 통합
CLIMATE_DATA_DICTIONARY = {
    "extreme_heat": EXTREME_HEAT,
    "drought": DROUGHT,
    # ... 다른 리스크 타입들
}

class ClimateDataKnowledgeBase:
    """기후 데이터 지식 베이스 접근 클래스"""

    def __init__(self):
        self.data_dict = CLIMATE_DATA_DICTIONARY

    def get_field_info(self, risk_type: str, field_name: str) -> DataField:
        """특정 리스크의 필드 정보 조회"""
        if risk_type not in self.data_dict:
            raise ValueError(f"Unknown risk type: {risk_type}")
        if field_name not in self.data_dict[risk_type]:
            raise ValueError(f"Unknown field: {field_name} in {risk_type}")
        return self.data_dict[risk_type][field_name]

    def get_usage_for_report(self, risk_type: str, field_name: str) -> List[str]:
        """리포트 생성 시 해당 필드의 활용 방법 조회"""
        field = self.get_field_info(risk_type, field_name)
        return field.used_in

    def get_impact_description(self, risk_type: str, field_name: str,
                               impact_type: str) -> str:
        """특정 영향 타입(financial/operational/reputation)에 대한 설명 조회"""
        field = self.get_field_info(risk_type, field_name)
        return field.impacts_on.get(impact_type, "")

    def search_by_keyword(self, keyword: str) -> List[Dict[str, Any]]:
        """키워드로 관련 필드 검색"""
        results = []
        for risk_type, fields in self.data_dict.items():
            for field_name, field_data in fields.items():
                if (keyword.lower() in field_data.definition.lower() or
                    keyword.lower() in field_data.full_name.lower()):
                    results.append({
                        "risk_type": risk_type,
                        "field_name": field_name,
                        "field_data": field_data
                    })
        return results

# 싱글톤 인스턴스
climate_kb = ClimateDataKnowledgeBase()
```

### 방안 2: 리포트 생성 시 활용 예시

**파일: `agents/report_generator.py`**

```python
from docs.climate_data_dictionary import climate_kb

class ReportGenerator:
    """TCFD 리포트 생성기"""

    def generate_impact_section(self, risk_type: str, field_name: str,
                                current_value: float) -> str:
        """Impact Analysis 섹션 생성"""

        # Knowledge Base에서 필드 정보 조회
        field_info = climate_kb.get_field_info(risk_type, field_name)

        # 재무 영향 설명 조회
        financial_impact = climate_kb.get_impact_description(
            risk_type, field_name, "financial_risk"
        )

        # 리포트 텍스트 생성
        report = f"""
## {field_info.full_name}

### 정의
{field_info.definition}

### 현재 상태
- 측정값: {current_value} {field_info.unit}
- 의미: {field_info.high_value_means}

### 재무 영향
{financial_impact}

### 운영 영향
{climate_kb.get_impact_description(risk_type, field_name, "operational_risk")}

### 평판 리스크
{climate_kb.get_impact_description(risk_type, field_name, "reputation_risk")}
        """

        return report

    def generate_strategy_recommendations(self, risk_type: str,
                                         field_name: str) -> List[str]:
        """전략 권고사항 생성"""

        usage_list = climate_kb.get_usage_for_report(risk_type, field_name)

        # "Strategy Generation:" 항목만 필터링
        strategies = [
            item.replace("Strategy Generation: ", "")
            for item in usage_list
            if item.startswith("Strategy Generation:")
        ]

        return strategies
```

### 방안 3: LLM 프롬프트에 컨텍스트 주입

```python
from docs.climate_data_dictionary import climate_kb

def generate_llm_context(risk_type: str, field_name: str) -> str:
    """LLM 프롬프트에 주입할 컨텍스트 생성"""

    field_info = climate_kb.get_field_info(risk_type, field_name)

    context = f"""
당신은 기후 리스크 분석 전문가입니다. 다음 데이터를 기반으로 리포트를 작성해주세요:

**데이터 필드:** {field_info.full_name}
**정의:** {field_info.definition}
**단위:** {field_info.unit}
**높은 값의 의미:** {field_info.high_value_means}

**재무 리스크:**
{field_info.impacts_on['financial_risk']}

**운영 리스크:**
{field_info.impacts_on['operational_risk']}

**평판 리스크:**
{field_info.impacts_on['reputation_risk']}

**활용 방법:**
{chr(10).join(f"- {item}" for item in field_info.used_in)}

**다른 데이터와의 관계:**
{chr(10).join(f"- {k}: {v}" for k, v in field_info.interaction_with_other_data.items())}
"""

    return context

# 사용 예시
llm_prompt = f"""
{generate_llm_context("extreme_heat", "WSDI")}

위 정보를 바탕으로 WSDI 값이 30일인 경우의 리스크 분석 리포트를 작성해주세요.
"""
```

## 📊 추천 방안 요약

| 방안 | 장점 | 단점 | 추천 상황 |
|------|------|------|-----------|
| **JSON 파일** | 외부 시스템과 호환성 높음 | 런타임 파싱 필요, 타입 안정성 낮음 | 외부 API 연동 필요 시 |
| **Python Knowledge Base** | 빠른 접근, 타입 안정성, IDE 지원 | Python 환경에서만 사용 가능 | 내부 로직에서 빠른 참조 필요 시 |
| **하이브리드** | 두 방식의 장점 활용 | 관리 복잡도 증가 | 대규모 프로젝트 |

## 🎯 결론 및 권장사항

**우리 프로젝트에 권장하는 방식:**

1. **Python Knowledge Base 방식 채택**
   - `docs/climate_data_dictionary.py` 생성
   - 타입 힌팅과 dataclass 활용으로 안정성 확보
   - 리포트 생성 에이전트에서 직접 import하여 사용

2. **JSON 파일 유지 (백업/외부 연동용)**
   - 기존 `LLM_RAG_DATA_DICTIONARY.json` 유지
   - Python 파일과 동기화 스크립트 작성 (선택)

3. **Knowledge Base 클래스 설계**
   - 싱글톤 패턴으로 메모리 효율화
   - 검색/필터링 메서드 제공
   - LLM 프롬프트 생성 헬퍼 메서드 제공

이 방식은 **"Static RAG"** 또는 **"In-Code Knowledge Base"**로 부르며,
벡터 DB 없이도 구조화된 지식을 효율적으로 활용할 수 있는 경량 RAG 패턴입니다.
