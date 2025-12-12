"""
AAL 계산 테스트 스크립트 (9개 위험)
2026년 더미 데이터로 각 위험별 AAL 계산
"""
import numpy as np
import logging
from typing import Dict, Any

# Probability Agents
from modelops.agents.probability_calculate.extreme_heat_probability_agent import ExtremeHeatProbabilityAgent
from modelops.agents.probability_calculate.extreme_cold_probability_agent import ExtremeColdProbabilityAgent
from modelops.agents.probability_calculate.wildfire_probability_agent import WildfireProbabilityAgent
from modelops.agents.probability_calculate.drought_probability_agent import DroughtProbabilityAgent
from modelops.agents.probability_calculate.water_stress_probability_agent import WaterStressProbabilityAgent
from modelops.agents.probability_calculate.sea_level_rise_probability_agent import SeaLevelRiseProbabilityAgent
from modelops.agents.probability_calculate.river_flood_probability_agent import RiverFloodProbabilityAgent
from modelops.agents.probability_calculate.urban_flood_probability_agent import UrbanFloodProbabilityAgent
from modelops.agents.probability_calculate.typhoon_probability_agent import TyphoonProbabilityAgent

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def generate_dummy_climate_data(risk_type: str) -> Dict[str, Any]:
    """
    위험 타입별 더미 기후 데이터 생성

    Args:
        risk_type: 위험 타입

    Returns:
        더미 기후 데이터 딕셔너리
    """
    # 2000-2026년 데이터 생성 (27년)
    years = list(range(2000, 2027))

    if risk_type == 'extreme_heat':
        # WSDI (Warm Spell Duration Index): 0~30일 범위
        wsdi = np.random.uniform(0, 30, size=len(years))
        # 최근으로 갈수록 증가 트렌드
        wsdi = wsdi + np.linspace(0, 10, len(years))
        return {
            'climate_data': {
                'wsdi': wsdi.tolist()
            },
            'baseline_wsdi': np.random.uniform(0, 20, size=30).tolist()  # 기준기간 데이터
        }

    elif risk_type == 'extreme_cold':
        # CSDI (Cold Spell Duration Index): 0~20일 범위
        csdi = np.random.uniform(0, 20, size=len(years))
        # 최근으로 갈수록 감소 트렌드
        csdi = csdi - np.linspace(0, 5, len(years))
        csdi = np.maximum(csdi, 0)  # 음수 방지
        return {
            'climate_data': {
                'csdi': csdi.tolist()
            },
            'baseline_csdi': np.random.uniform(0, 15, size=30).tolist()
        }

    elif risk_type == 'wildfire':
        # 월별 기상 데이터 생성 (TA, RHM, WS, RN)
        # 27년 × 12개월 = 324개월
        num_months = len(years) * 12
        ta = np.random.uniform(10, 35, size=num_months)  # 기온 10-35°C
        rhm = np.random.uniform(30, 90, size=num_months)  # 습도 30-90%
        ws = np.random.uniform(0, 10, size=num_months)  # 풍속 0-10 m/s
        rn = np.random.uniform(0, 50, size=num_months)  # 강수량 0-50mm

        return {
            'climate_data': {
                'ta': ta.tolist(),
                'rhm': rhm.tolist(),
                'ws': ws.tolist(),
                'rn': rn.tolist()
            }
        }

    elif risk_type == 'drought':
        # SPEI12 (Standardized Precipitation-Evapotranspiration Index): -3 ~ 3 범위
        # 27년 × 12개월 = 324개월
        num_months = len(years) * 12
        spei12 = np.random.uniform(-3, 3, size=num_months)
        # 가끔 심한 가뭄 발생
        drought_indices = np.random.choice(num_months, size=10, replace=False)
        spei12[drought_indices] = np.random.uniform(-2.5, -1.5, size=10)

        return {
            'climate_data': {
                'spei12': spei12.tolist()
            }
        }

    elif risk_type == 'water_stress':
        # 간단한 water_data 생성
        # withdrawal과 간단한 flow 데이터
        water_data = []
        flow_data = []

        for year in years:
            # 용수이용량 (m³/year): 1억~5억 범위
            withdrawal = np.random.uniform(1e8, 5e8)
            water_data.append({
                'year': year,
                'withdrawal': withdrawal
            })

            # 유량 데이터 (일유량, m³/s): 10~50 범위
            daily_flows = np.random.uniform(10, 50, size=365)
            flow_data.append({
                'year': year,
                'daily_flows': daily_flows.tolist()
            })

        return {
            'water_data': water_data,
            'flow_data': flow_data,
            'baseline_years': list(range(2000, 2020))
        }

    elif risk_type == 'sea_level_rise':
        # ZOS 데이터: 연도별 월별 해수면 높이 (meters)
        # ground_level 5m로 가정
        ground_level = 5.0

        zos_data = []
        for year in years:
            # 각 연도의 12개월 데이터
            # 해수면 높이: 4.5~5.5m (침수 발생할 수 있도록)
            monthly_zos = np.random.uniform(4.5, 5.5, size=12)
            # 최근으로 갈수록 증가
            if year >= 2020:
                monthly_zos = monthly_zos + (year - 2020) * 0.05
            zos_data.append({
                'year': year,
                'zos_values': monthly_zos.tolist()
            })

        # DEM 데이터 (최저 고도)
        dem_data = [{'x': 0, 'y': 0, 'z': ground_level}]

        return {
            'ocean_data': {
                'zos_data': zos_data,
                'dem_data': dem_data
            }
        }

    elif risk_type == 'river_flood':
        # RX1DAY: 연간 최대 일강수량 (mm)
        rx1day = np.random.uniform(50, 300, size=len(years))
        # 최근으로 갈수록 증가 트렌드
        rx1day = rx1day + np.linspace(0, 50, len(years))

        return {
            'climate_data': {
                'rx1day': rx1day.tolist(),
                'baseline_rx1day': np.random.uniform(50, 250, size=30).tolist()
            }
        }

    elif risk_type == 'urban_flood':
        # RAIN80: 연간 80mm 이상 호우일수
        rain80 = np.random.randint(0, 10, size=len(years))
        # 최근으로 갈수록 증가 트렌드
        rain80 = rain80 + (np.linspace(0, 3, len(years))).astype(int)

        return {
            'climate_data': {
                'rain80': rain80.tolist()
            }
        }

    elif risk_type == 'typhoon':
        # 태풍 Best Track 더미 데이터 (간단한 버전)
        # 연도별 S_tc (누적 노출 지수) 직접 생성
        s_tc = np.random.uniform(0, 20, size=len(years))
        # 일부 연도는 태풍 영향 없음
        s_tc = np.where(
            np.random.random(size=len(years)) > 0.7,
            s_tc,
            0
        )

        # typhoon agent는 특별한 처리가 필요하므로
        # 간단히 annual_S_tc를 직접 전달
        return {
            'annual_S_tc': s_tc.tolist()
        }

    else:
        return {}


def test_aal_calculation():
    """9개 위험에 대한 AAL 계산 테스트"""

    # 9개 위험 타입과 에이전트 매핑
    risk_agents = {
        'extreme_heat': ExtremeHeatProbabilityAgent(),
        'extreme_cold': ExtremeColdProbabilityAgent(),
        'wildfire': WildfireProbabilityAgent(),
        'drought': DroughtProbabilityAgent(),
        'water_stress': WaterStressProbabilityAgent(),
        'sea_level_rise': SeaLevelRiseProbabilityAgent(),
        'river_flood': RiverFloodProbabilityAgent(),
        'urban_flood': UrbanFloodProbabilityAgent(),
        'typhoon': TyphoonProbabilityAgent()
    }

    results = {}

    print("=" * 80)
    print(f"{'AAL 계산 테스트 (2026년 더미 데이터)':^80}")
    print("=" * 80)
    print()

    for i, (risk_type, agent) in enumerate(risk_agents.items(), 1):
        print(f"\n[{i}/9] {risk_type.upper().replace('_', ' ')} 계산 중...")
        print("-" * 80)

        try:
            # 더미 데이터 생성
            dummy_data = generate_dummy_climate_data(risk_type)

            # AAL 계산
            result = agent.calculate_probability(dummy_data)

            # 결과 저장
            results[risk_type] = result

            # 결과 출력
            if result.get('status') == 'completed':
                print(f"[OK] 계산 완료")
                print(f"  AAL: {result['aal']:.6f} ({result['aal']*100:.4f}%)")
                print(f"  Bin 확률: {result['bin_probabilities']}")
                print(f"  Bin 손상률: {result['bin_base_damage_rates']}")

                # 계산 상세 정보
                details = result.get('calculation_details', {})
                print(f"  계산 방식: {details.get('method', 'N/A')}")
                print(f"  시간 단위: {details.get('time_unit', 'N/A')}")

                if details.get('time_unit') == 'monthly':
                    print(f"  전체 월 수: {details.get('total_months', 'N/A')}")
                else:
                    print(f"  전체 연도 수: {details.get('total_years', 'N/A')}")

            else:
                print(f"[FAIL] 계산 실패")
                print(f"  오류: {result.get('error', 'Unknown error')}")

        except Exception as e:
            print(f"[ERROR] 예외 발생: {str(e)}")
            results[risk_type] = {
                'status': 'failed',
                'error': str(e)
            }

    # 요약 출력
    print("\n" + "=" * 80)
    print(f"{'계산 완료 요약':^80}")
    print("=" * 80)
    print()
    print(f"{'위험 타입':<20} {'AAL (%)':<15} {'상태':<10}")
    print("-" * 80)

    for risk_type, result in results.items():
        if result.get('status') == 'completed':
            aal_percent = result['aal'] * 100
            status = "[OK]"
            print(f"{risk_type:<20} {aal_percent:>14.4f}% {status:<10}")
        else:
            print(f"{risk_type:<20} {'N/A':>15} {'[FAIL]':<10}")

    print("\n" + "=" * 80)

    # 성공/실패 통계
    success_count = sum(1 for r in results.values() if r.get('status') == 'completed')
    print(f"\n총 {len(results)}개 위험 중 {success_count}개 성공, {len(results) - success_count}개 실패")
    print()

    return results


if __name__ == '__main__':
    results = test_aal_calculation()
