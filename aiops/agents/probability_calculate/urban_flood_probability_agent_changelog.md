# Urban Flood Probability Agent 변경 이력

## 파일 정보
- **파일명**: `urban_flood_probability_agent.py`
- **최종 수정일**: 2025-11-22
- **버전**: v2

---

## v2 변경사항 (2025-11-22)

### 주요 변경: RAIN80 호우빈도 기반 + 취약도 계수 방식

기존 drain_capacity 기반 초과강우 방식에서 **RAIN80(호우일수)를 직접 강도지표로 사용**하는 방식으로 변경.
DEM(경사도)과 토지피복도(도시화율)를 활용하여 **vulnerability_factor(취약도 계수)**를 계산.

### 핵심 로직

```
X_pflood = RAIN80 × vulnerability_factor
```

- **RAIN80**: 연간 80mm 이상 호우일수 (일)
- **vulnerability_factor**: 배수능력 프록시 기반 취약도 계수 (0.64~1.44)

### 추가된 메서드

#### `_calculate_vulnerability_factor(self, collected_data: Dict[str, Any]) -> float`

DEM과 토지피복도를 이용한 취약도 계수 계산

**입력 데이터:**
```python
collected_data = {
    'terrain_data': {
        'urban_ratio': 0.7,  # 도시화율 (0~1), 토지피복도 기반
        'slope': 0.02        # 경사도 (0~1, 비율), DEM 기반
    }
}
```

**로직:**

1. **도시화율 기반 base_vulnerability 결정:**

| urban_ratio | base_vulnerability | 설명 |
|-------------|-------------------|------|
| >= 0.7 | 0.8 | 고도 도시화: 배수시설 양호 → 낮은 취약도 |
| 0.3 ~ 0.7 | 1.0 | 중간 도시화 |
| < 0.3 | 1.2 | 저도시화: 자연 배수 의존 → 높은 취약도 |

2. **경사도 기반 slope_factor 결정:**

| slope | slope_factor | 설명 |
|-------|--------------|------|
| < 0.01 (1%) | 1.2 | 평지: 배수 느림 → 취약 |
| 0.01 ~ 0.03 | 1.0 | 기본 |
| > 0.03 (3%) | 0.8 | 경사지: 배수 빠름 → 덜 취약 |

3. **최종 취약도 계수:**
```
vulnerability_factor = base_vulnerability × slope_factor
```

**예시:**
- 도시화율 0.8, 경사도 0.02 → 0.8 × 1.0 = **0.8** (양호한 배수)
- 도시화율 0.5, 경사도 0.005 → 1.0 × 1.2 = **1.2** (취약)
- 도시화율 0.2, 경사도 0.05 → 1.2 × 0.8 = **0.96**

---

### Bin 구간 변경

**변경 전 (v1):** 침수심 기반 (m)
```python
bins = [(0, 0), (0, 0.3), (0.3, 1.0), (1.0, inf)]
dr_intensity = [0.00, 0.05, 0.25, 0.50]
```

**변경 후 (v2):** 보정된 호우일수 기반 (일)
```python
bins = [(0, 1), (1, 3), (3, 5), (5, inf)]
dr_intensity = [0.00, 0.05, 0.15, 0.35]
```

| Bin | 범위 | 의미 | DR_intensity |
|-----|------|------|--------------|
| bin1 | < 1일 | 호우 거의 없음 | 0% |
| bin2 | 1 ~ 3일 | 낮은 빈도 | 5% |
| bin3 | 3 ~ 5일 | 중간 빈도 | 15% |
| bin4 | >= 5일 | 높은 빈도 | 35% |

---

## 강도지표 계산 흐름

```
[입력]
├── KMA RAIN80 데이터 (연도별 호우일수)
├── DEM → slope (경사도)
└── 토지피복도 → urban_ratio (도시화율)

[취약도 계수 계산]
├── urban_ratio → base_vulnerability (0.8/1.0/1.2)
├── slope → slope_factor (0.8/1.0/1.2)
└── vulnerability_factor = base × slope (0.64~1.44)

[강도지표 계산]
└── X_pflood = RAIN80 × vulnerability_factor

[bin 분류]
├── bin1: < 1일 (호우 거의 없음)
├── bin2: 1 ~ 3일 (낮은 빈도)
├── bin3: 3 ~ 5일 (중간 빈도)
└── bin4: >= 5일 (높은 빈도)

[출력]
└── 연도별 bin 확률 P[i], 기본 손상률 DR[i]
```

---

## 기본값 (데이터 누락 시)

| 파라미터 | 기본값 | 비고 |
|----------|--------|------|
| urban_ratio | 0.5 | 중간 도시화 가정 |
| slope | 0.02 (2%) | 완만한 경사 가정 |

---

## 테스트 결과 (대전 유성구 데이터센터)

**입력 조건:**
- RAIN80: 0.4 ~ 4.8일 (80년 데이터)
- urban_ratio: 0.75 (고도 도시화)
- slope: 0.02 (2% 경사)
- vulnerability_factor: 0.8

**결과:**
| Bin | 확률 P | 손상률 DR |
|-----|--------|-----------|
| bin1 (< 1일) | 15.0% | 0% |
| bin2 (1~3일) | 80.0% | 5% |
| bin3 (3~5일) | 5.0% | 15% |
| bin4 (≥5일) | 0.0% | 35% |

→ 대부분 연도가 bin2에 분포, 극심한 홍수 위험(bin4)은 0%

---

## v1 (2025-11-21)
- 초기 버전
- AAL에서 확률 계산으로 분리
- 강도지표: `X_pflood(t,j) = k_depth × max(0, R_peak - drain_capacity)`
- bin: 침수심 기준 `[0), [0~0.3m), [0.3~1.0m), [≥1.0m)`
- DR_intensity: `[0.00, 0.05, 0.25, 0.50]`
- **drain_capacity 하드코딩 (60 mm/h)**
