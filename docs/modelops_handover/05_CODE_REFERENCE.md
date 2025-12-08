# ModelOps 이관 문서 - 05. 기존 코드 참조

**문서 버전**: 1.0
**작성일**: 2025-12-01

---

## 1. 파일 구조

### 1.1 이관 대상 파일 (22개)

```
ai_agent/
├── agents/
│   ├── data_processing/
│   │   └── vulnerability_analysis_agent.py  ⭐ (1개)
│   └── risk_analysis/
│       ├── physical_risk_score/  ⭐ (9개)
│       │   ├── base_physical_risk_score_agent.py
│       │   ├── extreme_heat_score_agent.py
│       │   ├── extreme_cold_score_agent.py
│       │   ├── wildfire_score_agent.py
│       │   ├── drought_score_agent.py
│       │   ├── water_stress_score_agent.py
│       │   ├── sea_level_rise_score_agent.py
│       │   ├── river_flood_score_agent.py
│       │   ├── urban_flood_score_agent.py
│       │   └── typhoon_score_agent.py
│       └── aal_analysis/  ⭐ (9개)
│           ├── base_aal_analysis_agent.py
│           ├── extreme_heat_aal_agent.py
│           ├── extreme_cold_aal_agent.py
│           ├── wildfire_aal_agent.py
│           ├── drought_aal_agent.py
│           ├── water_stress_aal_agent.py
│           ├── sea_level_rise_aal_agent.py
│           ├── river_flood_aal_agent.py
│           ├── urban_flood_aal_agent.py
│           └── typhoon_aal_agent.py
└── services/
    ├── aal_calculator.py  ⭐ (1개)
    └── exposure_calculator.py  (참조용, 1개)
```

---

## 2. Vulnerability Analysis Agent

### 2.1 파일 경로
`ai_agent/agents/data_processing/vulnerability_analysis_agent.py`

### 2.2 핵심 클래스
```python
class VulnerabilityAnalysisAgent:
    """
    취약성(Vulnerability) 분석 Agent

    건물 정보를 기반으로 9개 물리적 리스크에 대한 취약성을 정량화
    """
```

### 2.3 핵심 메서드

**`calculate_vulnerability(exposure: Dict) -> Dict`**
- **입력**: exposure (building, infrastructure, flood_exposure 등 포함)
- **출력**: 9개 리스크별 vulnerability 점수 딕셔너리

**리스크별 계산 메서드**:
```python
def _calculate_heat_vulnerability(self, exposure: Dict) -> Dict
def _calculate_cold_vulnerability(self, exposure: Dict) -> Dict
def _calculate_drought_vulnerability(self, exposure: Dict) -> Dict
def _calculate_inland_flood_vulnerability(self, exposure: Dict) -> Dict
def _calculate_urban_flood_vulnerability(self, exposure: Dict) -> Dict
def _calculate_coastal_flood_vulnerability(self, exposure: Dict) -> Dict
def _calculate_typhoon_vulnerability(self, exposure: Dict) -> Dict
def _calculate_wildfire_vulnerability(self, exposure: Dict) -> Dict
def _calculate_water_stress_vulnerability(self, exposure: Dict) -> Dict
```

### 2.4 코드 예시 (Extreme Heat)

```python
def _calculate_heat_vulnerability(self, exposure: Dict) -> Dict:
    """극한 고온 취약성"""
    building = exposure['building']
    age = building['building_age']
    structure = building['structure']

    score = 50  # 기본값

    # 건물 연식 (오래될수록 취약)
    if age > 30:
        score += 20
    elif age > 20:
        score += 10

    # 구조 (단열 성능)
    if '목조' in structure or '벽돌' in structure:
        score += 15  # 단열 취약
    elif '철근콘크리트' in structure:
        score -= 10  # 단열 양호

    # 용도 (냉방 필요성)
    if building['main_purpose'] in ['업무시설', '상업시설']:
        score += 10  # 냉방 부하 높음

    # 0-100 범위로 정규화
    score = max(0, min(100, score))

    return {
        'score': score,
        'level': self._score_to_level(score),
        'factors': {
            'building_age': age,
            'insulation_quality': 'poor' if age > 30 else 'fair',
            'cooling_capacity': 'standard',
            'heat_resistance': 'medium',
        }
    }
```

### 2.5 점수 → 등급 변환

```python
def _score_to_level(self, score: float) -> str:
    """점수를 리스크 등급으로 변환"""
    if score >= 80:
        return 'very_high'
    elif score >= 60:
        return 'high'
    elif score >= 40:
        return 'medium'
    elif score >= 20:
        return 'low'
    else:
        return 'very_low'
```

---

## 3. AAL Calculator Service

### 3.1 파일 경로
`ai_agent/services/aal_calculator.py`

### 3.2 핵심 클래스
```python
class AALCalculatorService:
    """
    AAL 기본값 계산 서비스

    입력: collected_data (기후 데이터)
    출력: base_aal (기본 연평균 손실률, 취약성 미반영)

    공식: base_aal = Σ_i [P_r[i] × DR_intensity_r[i]]
    """
```

### 3.3 리스크별 설정

```python
def _init_risk_configs(self):
    """리스크별 bin 경계 및 기본 손상률 정의"""
    self.risk_configs = {
        'extreme_heat': {
            'data_key': 'wsdi',  # WSDI (Warm Spell Duration Index)
            'bins': [0, 3, 8, 20, float('inf')],
            'base_damage_rates': [0.001, 0.003, 0.010, 0.020]  # 0.1%, 0.3%, 1.0%, 2.0%
        },
        'extreme_cold': {
            'data_key': 'csdi',
            'bins': [0, 3, 7, 15, float('inf')],
            'base_damage_rates': [0.0005, 0.0020, 0.0060, 0.0150]
        },
        'wildfire': {
            'data_key': 'fwi',
            'bins': [11.2, 21.3, 38, 50, float('inf')],
            'base_damage_rates': [0.01, 0.03, 0.10, 0.25]
        },
        # ... 나머지 리스크
    }
```

### 3.4 Base AAL 계산 로직

```python
def calculate_base_aal(self, collected_data: Dict, risk_type: str) -> float:
    """기본 AAL 계산: Σ[P_r[i] × DR_intensity_r[i]]"""

    # 1. 리스크 설정 조회
    config = self.risk_configs[risk_type]
    data_key = config['data_key']
    bins = config['bins']
    base_damage_rates = config['base_damage_rates']

    # 2. 기후 데이터 추출
    climate_data = collected_data.get('climate_data', {})
    risk_data = climate_data.get(data_key, [])
    risk_data = np.array(risk_data)

    # 3. bin별 확률 계산
    bin_counts = np.zeros(len(base_damage_rates))
    total_count = len(risk_data)

    for i in range(len(base_damage_rates)):
        if i == 0:
            mask = risk_data < bins[1]
        elif i == len(base_damage_rates) - 1:
            mask = risk_data >= bins[i]
        else:
            mask = (risk_data >= bins[i]) & (risk_data < bins[i+1])

        bin_counts[i] = np.sum(mask)

    # 4. 확률 계산: P_r[i]
    probabilities = bin_counts / total_count if total_count > 0 else np.zeros_like(bin_counts)

    # 5. base_aal 계산: Σ[P_r[i] × DR_intensity_r[i]]
    base_aal = np.sum(probabilities * np.array(base_damage_rates))

    return float(base_aal)
```

---

## 4. AAL Analysis Agent (Base)

### 4.1 파일 경로
`ai_agent/agents/risk_analysis/aal_analysis/base_aal_analysis_agent.py`

### 4.2 핵심 클래스
```python
class BaseAALAnalysisAgent:
    """
    AAL 분석 Base Agent

    base_aal + vulnerability_score → final_aal
    """

    def __init__(self, risk_type: str, config):
        self.risk_type = risk_type
        self.s_min = 0.9  # 취약성 스케일 최소값
        self.s_max = 1.1  # 취약성 스케일 최대값
        self.insurance_rate = config.get('insurance_coverage_rate', 0.7)
```

### 4.3 핵심 메서드

```python
def analyze_aal(self, base_aal: float, vulnerability_score: float) -> Dict:
    """
    AAL 분석: base_aal에 취약성 스케일링 적용

    Args:
        base_aal: 기본 AAL (AALCalculatorService에서 계산)
        vulnerability_score: 취약성 점수 (0-100)

    Returns:
        AAL 분석 결과 딕셔너리
    """
    # 1. 취약성 스케일 계수
    f_vuln = self._calculate_vulnerability_scale(vulnerability_score)

    # 2. 최종 AAL
    final_aal = base_aal * f_vuln * (1 - self.insurance_rate)
    final_aal_percentage = final_aal * 100.0

    return {
        'risk_type': self.risk_type,
        'vulnerability_score': round(vulnerability_score, 4),
        'vulnerability_scale': round(f_vuln, 4),
        'base_aal': round(base_aal, 6),
        'final_aal_percentage': round(final_aal_percentage, 4),
        'risk_level': self._get_risk_level(final_aal_percentage)
    }

def _calculate_vulnerability_scale(self, v_score: float) -> float:
    """
    F_vuln = s_min + (s_max - s_min) × (V/100)

    V=0   → F_vuln = 0.9 (10% 감소)
    V=50  → F_vuln = 1.0 (변화 없음)
    V=100 → F_vuln = 1.1 (10% 증가)
    """
    return self.s_min + (self.s_max - self.s_min) * (v_score / 100.0)
```

---

## 5. Physical Risk Score Agent (Base)

### 5.1 파일 경로
`ai_agent/agents/risk_analysis/physical_risk_score/base_physical_risk_score_agent.py`

### 5.2 핵심 메서드

```python
def calculate_physical_risk_score(self, collected_data, vulnerability_analysis, asset_info):
    """
    물리적 리스크 점수 계산: (H + E + V) / 3

    Args:
        collected_data: 기후 데이터
        vulnerability_analysis: 취약성 분석 결과
        asset_info: 자산 정보

    Returns:
        물리적 리스크 점수 (0-100 스케일)
    """
    # 1. Hazard 점수 (0-1)
    hazard_score = self.calculate_hazard(collected_data)

    # 2. Exposure 점수 (0-1)
    exposure_score = self.calculate_exposure(asset_info)

    # 3. Vulnerability 점수 (0-1로 변환)
    vulnerability_score = vulnerability_analysis[self.risk_type]['score'] / 100.0

    # 4. 물리적 리스크 점수 (0-1)
    physical_risk_score = (hazard_score + exposure_score + vulnerability_score) / 3

    # 5. 100점 스케일로 변환
    physical_risk_score_100 = physical_risk_score * 100

    return {
        'risk_type': self.risk_type,
        'hazard_score': hazard_score,
        'exposure_score': exposure_score,
        'vulnerability_score': vulnerability_score,
        'physical_risk_score_100': physical_risk_score_100,
        'risk_level': self.get_risk_level(physical_risk_score_100)
    }
```

---

## 6. 워크플로우 통합 지점

### 6.1 Node 2: Vulnerability Analysis

**파일**: `ai_agent/workflow/nodes.py`

```python
def vulnerability_analysis_node(state, config):
    """취약성 분석 노드"""
    agent = VulnerabilityAnalysisAgent()

    # Exposure 데이터 준비
    exposure = {
        'building': state['building_info'],
        'infrastructure': state['infrastructure'],
        'flood_exposure': {...}
    }

    # 취약성 계산
    vulnerability = agent.calculate_vulnerability(exposure)

    return {
        'vulnerability_analysis': vulnerability,
        'vulnerability_analysis_status': 'completed'
    }
```

### 6.2 Node 3: AAL Analysis

```python
def aal_analysis_node(state, config):
    """AAL 분석 노드 (9개 Agent 병렬 실행)"""
    from ai_agent.services.aal_calculator import AALCalculatorService

    # Base AAL 계산
    aal_calculator = AALCalculatorService()
    collected_data = state['collected_data']

    aal_results = {}

    for risk_type in RISK_TYPES:
        # 1. base_aal 계산
        base_aal = aal_calculator.calculate_base_aal(collected_data, risk_type)

        # 2. vulnerability_score 조회
        v_score = state['vulnerability_analysis'][risk_type]['score']

        # 3. AAL Agent 실행
        agent = AAL_AGENTS[risk_type](config)
        aal_result = agent.analyze_aal(base_aal, v_score)

        aal_results[risk_type] = aal_result

    return {
        'aal_analysis': aal_results,
        'aal_analysis_status': 'completed'
    }
```

---

## 7. 주요 의존성

### 7.1 Python 패키지

```python
# requirements.txt
numpy>=1.24.0
pandas>=2.0.0
scipy>=1.10.0
```

### 7.2 Import 문

```python
# Vulnerability Analysis
from typing import Dict, Any
import logging

# AAL Calculator
import numpy as np
from typing import Dict, Any

# AAL Analysis Agent
from typing import Dict, Any, List
```

---

## 8. 설정 파일

### 8.1 리스크 타입 상수

```python
# ai_agent/config/constants.py
RISK_TYPES = [
    'extreme_heat',
    'extreme_cold',
    'wildfire',
    'drought',
    'water_stress',
    'sea_level_rise',
    'river_flood',
    'urban_flood',
    'typhoon'
]

SSP_SCENARIOS = {
    1: 'SSP1-2.6',
    2: 'SSP2-4.5',
    3: 'SSP3-7.0',
    4: 'SSP5-8.5'
}
```

---

## 다음 문서

👉 [06. 마이그레이션 가이드](./06_MIGRATION_GUIDE.md)
