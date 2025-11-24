# 미래 용수이용량 추정 로직

## 개요

본 문서는 WAMIS 과거 용수이용량 데이터와 WRI Aqueduct 4.0 BWS(Baseline Water Stress) 데이터를 활용하여 SSP 시나리오별 미래 용수이용량을 추정하는 로직을 정의합니다.

## 1. 데이터 소스

### 1.1 WAMIS 용수이용량 (과거)
- **출처**: 국가수자원관리종합정보시스템 (WAMIS)
- **기간**: 1991-2023 (연도별)
- **단위**: 백만 m³/year
- **용도**: 생활용수, 공업용수, 농업용수

### 1.2 Aqueduct 4.0 BWS (미래)
- **출처**: World Resources Institute (WRI) Aqueduct 4.0
- **모델**: GCAM (Global Change Analysis Model) + PCR-GLOBWB 수문모델
- **앵커 연도**: 2019 (baseline), 2030, 2050, 2080
- **시나리오**: optimistic (opt), business-as-usual (bau), pessimistic (pes)

## 2. SSP 시나리오 매핑

| SSP 시나리오 | Aqueduct 시나리오 | RCP 경로 | 산출 방법 |
|--------------|-------------------|----------|-----------|
| SSP1-2.6 | optimistic (opt) | RCP2.6 | 직접 사용 |
| SSP2-4.5 | - | RCP4.5 | (opt + bau) / 2 보간 |
| SSP3-7.0 | business-as-usual (bau) | RCP7.0 | 직접 사용 |
| SSP5-8.5 | pessimistic (pes) | RCP8.5 | 직접 사용 |

### SSP2-4.5 보간 근거
- S&P Global Climanomics methodology 적용
- SSP2-4.5는 SSP1-2.6과 SSP3-7.0의 중간 경로로 물리적으로 합리적

## 3. BWS 정의

```
BWS = Withdrawal / Available Water
```

- **Withdrawal**: 총 용수 취수량 (생활+공업+농업)
- **Available Water**: 가용 수자원량

## 4. 핵심 가정

BWS 비율(ratio)이 미래 용수이용량 변화율과 동일하다고 가정:

```
BWS_ratio(year) = BWS(year) / BWS_baseline

Withdrawal_future(year) = Withdrawal_baseline × BWS_ratio(year)
```

**근거**:
- BWS = Withdrawal / Available_Water
- BWS_ratio = [Withdrawal_future / AW_future] / [Withdrawal_baseline / AW_baseline]
- 기후변화로 AW 변화 시, 수요도 비례하여 조정된다고 가정
- GCAM 모델의 수요-공급 균형 시뮬레이션 결과 반영

## 5. 1년 단위 BWS 선형 보간

### 5.1 앵커 포인트
```
Year:  2019 -------- 2030 -------- 2050 -------- 2080
BWS:   baseline     anchor_1      anchor_2      anchor_3
```

### 5.2 구간별 연간 변화율

```python
# 구간 1: 2019-2030 (11년)
rate_2019_2030 = (BWS_2030 - BWS_2019) / (2030 - 2019)

# 구간 2: 2030-2050 (20년)
rate_2030_2050 = (BWS_2050 - BWS_2030) / (2050 - 2030)

# 구간 3: 2050-2080 (30년)
rate_2050_2080 = (BWS_2080 - BWS_2050) / (2080 - 2050)
```

### 5.3 임의 연도 BWS 계산

```python
def interpolate_bws(year, bws_2019, bws_2030, bws_2050, bws_2080):
    """
    1년 단위 BWS 선형 보간

    Args:
        year: 목표 연도
        bws_2019: baseline BWS (2019)
        bws_2030: 2030년 BWS
        bws_2050: 2050년 BWS
        bws_2080: 2080년 BWS

    Returns:
        보간된 BWS 값
    """
    if year <= 2019:
        return bws_2019
    elif year <= 2030:
        rate = (bws_2030 - bws_2019) / 11
        return bws_2019 + (year - 2019) * rate
    elif year <= 2050:
        rate = (bws_2050 - bws_2030) / 20
        return bws_2030 + (year - 2030) * rate
    elif year <= 2080:
        rate = (bws_2080 - bws_2050) / 30
        return bws_2050 + (year - 2050) * rate
    else:
        # 2080 이후는 2080 값 유지 (외삽 제한)
        return bws_2080
```

## 6. SSP2-4.5 보간

```python
def calculate_ssp245_bws(bws_opt, bws_bau):
    """
    SSP2-4.5 BWS 보간 (단순 평균)

    Args:
        bws_opt: SSP1-2.6 (optimistic) BWS
        bws_bau: SSP3-7.0 (business-as-usual) BWS

    Returns:
        SSP2-4.5 BWS
    """
    return (bws_opt + bws_bau) / 2
```

## 7. 미래 용수이용량 계산

```python
def calculate_future_withdrawal(
    withdrawal_baseline: float,
    bws_baseline: float,
    bws_future: float
) -> float:
    """
    미래 용수이용량 계산

    Args:
        withdrawal_baseline: 기준 연도 용수이용량 (m³/year)
        bws_baseline: 기준 연도 BWS
        bws_future: 목표 연도 BWS

    Returns:
        미래 용수이용량 (m³/year)
    """
    bws_ratio = bws_future / bws_baseline
    return withdrawal_baseline * bws_ratio
```

## 8. 전체 계산 흐름

```python
def get_future_withdrawals(
    withdrawal_baseline: float,
    aqueduct_data: dict,
    years: list,
    scenarios: list = ['SSP1-2.6', 'SSP2-4.5', 'SSP3-7.0', 'SSP5-8.5']
) -> dict:
    """
    시나리오별/연도별 미래 용수이용량 계산

    Args:
        withdrawal_baseline: WAMIS 기준 연도 용수이용량
        aqueduct_data: Aqueduct BWS 데이터
            {
                'baseline': float,  # BWS 2019
                'opt': {'2030': float, '2050': float, '2080': float},
                'bau': {'2030': float, '2050': float, '2080': float},
                'pes': {'2030': float, '2050': float, '2080': float}
            }
        years: 계산할 연도 리스트 [2020, 2021, ..., 2050]
        scenarios: SSP 시나리오 리스트

    Returns:
        {
            'SSP1-2.6': {2020: withdrawal, 2021: withdrawal, ...},
            'SSP2-4.5': {...},
            'SSP3-7.0': {...},
            'SSP5-8.5': {...}
        }
    """
    bws_baseline = aqueduct_data['baseline']

    # 시나리오별 앵커 BWS 추출
    scenario_anchors = {
        'SSP1-2.6': aqueduct_data['opt'],
        'SSP3-7.0': aqueduct_data['bau'],
        'SSP5-8.5': aqueduct_data['pes']
    }

    results = {}

    for scenario in scenarios:
        results[scenario] = {}

        for year in years:
            if scenario == 'SSP2-4.5':
                # SSP2-4.5: opt와 bau 보간
                bws_opt = interpolate_bws(
                    year, bws_baseline,
                    aqueduct_data['opt']['2030'],
                    aqueduct_data['opt']['2050'],
                    aqueduct_data['opt']['2080']
                )
                bws_bau = interpolate_bws(
                    year, bws_baseline,
                    aqueduct_data['bau']['2030'],
                    aqueduct_data['bau']['2050'],
                    aqueduct_data['bau']['2080']
                )
                bws_future = calculate_ssp245_bws(bws_opt, bws_bau)
            else:
                # 직접 매핑 시나리오
                anchors = scenario_anchors[scenario]
                bws_future = interpolate_bws(
                    year, bws_baseline,
                    anchors['2030'],
                    anchors['2050'],
                    anchors['2080']
                )

            # 미래 용수이용량 계산
            withdrawal_future = calculate_future_withdrawal(
                withdrawal_baseline, bws_baseline, bws_future
            )

            results[scenario][year] = {
                'bws': bws_future,
                'bws_ratio': bws_future / bws_baseline,
                'withdrawal': withdrawal_future
            }

    return results
```

## 9. 시간 범위 정의

### 9.1 중기 (Mid-term)
- **연도**: 2026, 2027, 2028, 2029, 2030
- **단위**: 1년
- **총 기간**: 5년

### 9.2 장기 (Long-term)
- **연도**: 2020, 2021, 2022, ..., 2050
- **단위**: 1년
- **총 기간**: 31년

### 9.3 단기 (Short-term) - 추후 구현
- **기간**: 2026-1, 2026-2, 2026-3, 2026-4
- **단위**: 분기
- **총 기간**: 1년 (4분기)

## 10. 출력 형식

### 10.1 중기 결과
```json
{
  "time_horizon": "mid_term",
  "years": [2026, 2027, 2028, 2029, 2030],
  "baseline": {
    "year": 2022,
    "withdrawal": 1000.0,
    "unit": "백만m³/year"
  },
  "scenarios": {
    "SSP1-2.6": {
      "2026": {"bws_ratio": 1.05, "withdrawal": 1050.0},
      "2027": {"bws_ratio": 1.06, "withdrawal": 1060.0},
      "2028": {"bws_ratio": 1.07, "withdrawal": 1070.0},
      "2029": {"bws_ratio": 1.08, "withdrawal": 1080.0},
      "2030": {"bws_ratio": 1.09, "withdrawal": 1090.0}
    },
    "SSP2-4.5": {...},
    "SSP3-7.0": {...},
    "SSP5-8.5": {...}
  }
}
```

### 10.2 장기 결과
```json
{
  "time_horizon": "long_term",
  "years": [2020, 2021, 2022, ..., 2050],
  "baseline": {
    "year": 2022,
    "withdrawal": 1000.0,
    "unit": "백만m³/year"
  },
  "scenarios": {
    "SSP1-2.6": {
      "2020": {"bws_ratio": 1.00, "withdrawal": 1000.0},
      "2021": {"bws_ratio": 1.01, "withdrawal": 1010.0},
      ...
      "2050": {"bws_ratio": 1.22, "withdrawal": 1220.0}
    },
    "SSP2-4.5": {...},
    "SSP3-7.0": {...},
    "SSP5-8.5": {...}
  }
}
```

## 11. 참고문헌

1. **Aqueduct 4.0**: Kuzma, S., et al. (2023). "Aqueduct 4.0: Updated decision-relevant global water risk indicators." World Resources Institute Technical Note.

2. **GCAM Model**: Calvin, K., et al. (2019). "GCAM v5.1: representing the linkages between energy, water, land, climate, and economic systems." Geoscientific Model Development.

3. **PCR-GLOBWB**: Sutanudjaja, E.H., et al. (2018). "PCR-GLOBWB 2: a 5 arcmin global hydrological and water resources model." Geoscientific Model Development.

4. **SSP Scenarios**: Riahi, K., et al. (2017). "The Shared Socioeconomic Pathways and their energy, land use, and greenhouse gas emissions implications." Global Environmental Change.

5. **Water Sector Assumptions**: Graham, N.T., et al. (2020). "Water Sector Assumptions for the Shared Socioeconomic Pathways." Global Environmental Change.

6. **S&P Climanomics**: S&P Global (2022). "Climanomics Physical Risk Methodology."

## 12. 한계 및 주의사항

1. **선형 보간 한계**: 실제 변화는 비선형일 수 있으나, 앵커 포인트 간 선형 보간 적용
2. **지역 불확실성**: Aqueduct는 국가 단위 데이터로, 지역별 변동성 미반영
3. **수요 탄력성**: 가격/정책 변화에 따른 수요 탄력성 미반영
4. **기후 피드백**: 기후변화로 인한 급격한 수자원 변화 가능성 존재
5. **2080 이후 외삽**: 2080년 이후는 2080 값으로 고정 (외삽 제한)
