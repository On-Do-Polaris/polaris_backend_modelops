#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Risk Calculator
최종 리스크 점수 계산: Risk = H × E × V
"""

from typing import Dict, Union, Tuple
import json
from datetime import datetime
from exposure_calculator import ExposureCalculator
from hazard_calculator import HazardCalculator
from vulnerability_calculator import VulnerabilityCalculator


class RiskCalculator:
    """
    물리적 리스크 계산기

    입력: 위/경도 또는 주소
    출력: 9개 물리적 리스크 점수 (4개 시나리오별)

    계산 공식: Risk = H × E × V
    - H (Hazard): 위험 강도
    - E (Exposure): 노출도
    - V (Vulnerability): 취약성

    시나리오:
    - SSP126: 저탄소 시나리오
    - SSP245: 중간 시나리오 (기본값)
    - SSP370: 고탄소 시나리오
    - SSP585: 최악 시나리오
    """

    SCENARIOS = ['SSP126', 'SSP245', 'SSP370', 'SSP585']
    SCENARIO_NAMES = {
        'SSP126': '저탄소 시나리오 (2°C 목표)',
        'SSP245': '중간 시나리오 (현재 추세)',
        'SSP370': '고탄소 시나리오',
        'SSP585': '최악 시나리오 (4-5°C 상승)'
    }

    def __init__(self, scenarios: list = None, target_year: int = 2030):
        """
        Args:
            scenarios: 계산할 시나리오 리스트 (기본값: 전체 4개)
            target_year: 분석 연도 (2021-2100)
        """
        self.scenarios = scenarios if scenarios else self.SCENARIOS
        self.target_year = target_year
        self.exposure_calc = ExposureCalculator()
        self.vuln_calc = VulnerabilityCalculator()

        # 시나리오별 Hazard Calculator 초기화
        self.hazard_calcs = {
            scenario: HazardCalculator(scenario=scenario, target_year=target_year)
            for scenario in self.scenarios
        }

    def calculate_all_risks(
        self,
        location: Union[str, Tuple[float, float]]
    ) -> Dict:
        """
        위/경도 또는 주소 → 9개 물리적 리스크 점수 (시나리오별)

        Args:
            location: 주소(str) 또는 (lat, lon) 튜플

        Returns:
            {
                'scenarios': {
                    'SSP126': {리스크 점수, H, E, V},
                    'SSP245': {리스크 점수, H, E, V},
                    'SSP370': {리스크 점수, H, E, V},
                    'SSP585': {리스크 점수, H, E, V}
                },
                'metadata': 메타정보
            }
        """
        print("="*80)
        print("🎯 물리적 리스크 평가 시작")
        print(f"📅 분석 연도: {self.target_year}")
        print(f"📊 시나리오: {', '.join(self.scenarios)}")
        print("="*80)

        # 주소 → 좌표 변환
        if isinstance(location, str):
            lat, lon = self.exposure_calc._address_to_coords(location)
            print(f"\n📍 주소: {location}")
            print(f"   좌표: ({lat}, {lon})")
        else:
            lat, lon = location
            print(f"\n📍 좌표: ({lat}, {lon})")

        # Step 1: Exposure (E) - 모든 시나리오 공통
        print(f"\n{'─'*80}")
        print("Step 1/3: Exposure (E) 계산 (시나리오 공통)")
        print(f"{'─'*80}")
        E = self.exposure_calc.calculate((lat, lon))

        # Step 2: Vulnerability (V) - 모든 시나리오 공통
        print(f"\n{'─'*80}")
        print("Step 2/3: Vulnerability (V) 계산 (시나리오 공통)")
        print(f"{'─'*80}")
        V = self.vuln_calc.calculate(E)

        # Step 3 & 4: 시나리오별 Hazard (H) 계산 및 Risk = H × E × V
        results = {}
        for scenario in self.scenarios:
            print(f"\n{'='*80}")
            print(f"📊 {scenario} 시나리오: {self.SCENARIO_NAMES[scenario]}")
            print(f"{'='*80}")

            print(f"\n{'─'*80}")
            print(f"Step 3/3: Hazard (H) 계산 - {scenario}")
            print(f"{'─'*80}")
            H = self.hazard_calcs[scenario].calculate(lat, lon)

            print(f"\n{'─'*80}")
            print(f"최종 계산: Risk = H × E × V - {scenario}")
            print(f"{'─'*80}")

            risks = {}
            risk_types = [
                'extreme_heat', 'extreme_cold', 'drought',
                'inland_flood', 'urban_flood', 'coastal_flood',
                'typhoon', 'wildfire', 'water_stress'
            ]

            for risk_type in risk_types:
                risks[risk_type] = self._calculate_single_risk(
                    risk_type, H[risk_type], E, V[risk_type]
                )

            # 종합 점수 계산
            total_score = sum(r['score'] for r in risks.values())
            risk_level = self._calculate_risk_level(total_score)

            results[scenario] = {
                'risks': risks,
                'total_score': total_score,
                'risk_level': risk_level,
                'hazard': H,
            }

            # 시나리오별 결과 출력
            self._print_scenario_results(scenario, risks, total_score, risk_level)

        # 시나리오 비교 출력
        self._print_scenario_comparison(results)

        final_result = {
            'scenarios': results,
            'exposure': E,
            'vulnerability': V,
            'metadata': {
                'location': {'latitude': lat, 'longitude': lon},
                'target_year': self.target_year,
                'scenarios': self.scenarios,
                'calculated_at': datetime.now().isoformat(),
                'version': '2.0.0',
                'tcfd_compliant': True,
            }
        }

        return final_result

    def _calculate_single_risk(
        self,
        risk_type: str,
        hazard: Dict,
        exposure: Dict,
        vulnerability: Dict
    ) -> Dict:
        """
        단일 리스크 계산

        Risk Score = (H_score × E_score × V_score) / 10000

        각 요소를 0-100 점수로 정규화하여 계산
        """
        # Hazard Score 추출
        H_score = self._extract_hazard_score(risk_type, hazard)

        # Exposure Score 추출
        E_score = self._extract_exposure_score(risk_type, exposure)

        # Vulnerability Score
        V_score = vulnerability['score']

        # Risk = H × E × V (정규화: /10000)
        # 각각 0-100이므로 곱하면 0-1,000,000
        # /10000 → 0-100 범위
        risk_score = (H_score * E_score * V_score) / 10000

        # 심각도 평가
        severity = self._score_to_severity(risk_score)

        return {
            'score': round(risk_score, 2),
            'severity': severity,
            'components': {
                'hazard': H_score,
                'exposure': E_score,
                'vulnerability': V_score,
            },
            'level': vulnerability['level'],  # V의 레벨 포함
        }

    def _extract_hazard_score(self, risk_type: str, hazard: Dict) -> float:
        """
        Hazard 데이터 → 점수 변환 (0-100)
        """
        # 각 리스크별 Hazard를 0-100 점수로 변환
        if risk_type == 'extreme_heat':
            # 폭염 일수 기반
            days = hazard['heatwave_days_per_year']
            return min(100, days * 3)  # 25일 → 75점

        elif risk_type == 'extreme_cold':
            days = hazard['coldwave_days_per_year']
            return min(100, days * 5)  # 10일 → 50점

        elif risk_type == 'drought':
            freq = hazard['drought_frequency']
            return min(100, freq * 500)  # 0.1 → 50점

        elif risk_type == 'inland_flood':
            # 침수 이력 + 강수량
            history = hazard['historical_flood_count']
            rainfall = hazard['extreme_rainfall_100yr_mm']
            return min(100, history * 10 + rainfall / 5)

        elif risk_type == 'urban_flood':
            history = hazard['historical_flood_count']
            rainfall = hazard['extreme_rainfall_1hr_mm']
            return min(100, history * 10 + rainfall)

        elif risk_type == 'coastal_flood':
            if not hazard['coastal_exposure']:
                return 0
            surge = hazard['storm_surge_height_m']
            return min(100, surge * 30)  # 2.5m → 75점

        elif risk_type == 'typhoon':
            freq = hazard['annual_typhoon_frequency']
            wind = hazard['max_wind_speed_kmh']
            return min(100, freq * 15 + wind / 5)

        elif risk_type == 'wildfire':
            index = hazard['wildfire_risk_index']
            return index  # 이미 0-100

        elif risk_type == 'water_stress':
            ratio = hazard['supply_ratio']
            return max(0, (1 - ratio) * 100)  # 0.9 → 10점

        return 50  # 기본값

    def _extract_exposure_score(self, risk_type: str, exposure: Dict) -> float:
        """
        Exposure 데이터 → 점수 변환 (0-100)
        """
        if risk_type in ['inland_flood', 'urban_flood']:
            flood_exp = exposure['flood_exposure']
            dist = flood_exp['distance_to_river_m']

            # 하천 거리 기반 (가까울수록 높음)
            if dist < 100:
                return 90
            elif dist < 500:
                return 70
            elif dist < 1000:
                return 50
            else:
                return 30

        elif risk_type == 'coastal_flood':
            typhoon_exp = exposure['typhoon_exposure']
            if not typhoon_exp['coastal_exposure']:
                return 0
            dist = typhoon_exp['distance_to_coast_m']
            return max(0, 100 - dist / 100)

        elif risk_type == 'typhoon':
            typhoon_exp = exposure['typhoon_exposure']
            if typhoon_exp['coastal_exposure']:
                return 80
            else:
                return 40

        elif risk_type in ['extreme_heat', 'extreme_cold']:
            # 도시 열섬 효과
            heat_exp = exposure['heat_exposure']
            uhi = heat_exp['urban_heat_island']
            if uhi == 'high':
                return 70
            elif uhi == 'medium':
                return 50
            else:
                return 30

        return 50  # 기본값

    def _score_to_severity(self, score: float) -> str:
        """점수 → 심각도 변환"""
        if score >= 70:
            return 'CRITICAL'
        elif score >= 50:
            return 'HIGH'
        elif score >= 30:
            return 'MEDIUM'
        elif score >= 10:
            return 'LOW'
        else:
            return 'MINIMAL'

    def _calculate_risk_level(self, total_score: float) -> str:
        """종합 점수 → 위험 수준"""
        if total_score >= 500:
            return 'VERY_HIGH'
        elif total_score >= 350:
            return 'HIGH'
        elif total_score >= 200:
            return 'MEDIUM'
        elif total_score >= 100:
            return 'LOW'
        else:
            return 'VERY_LOW'

    def _print_scenario_results(self, scenario: str, risks: Dict, total_score: float, risk_level: str):
        """시나리오별 결과 출력"""
        print(f"\n📊 {scenario} 결과")
        print(f"{'─'*80}")

        risk_names = {
            'extreme_heat': '극한 고온',
            'extreme_cold': '극한 한파',
            'drought': '가뭄',
            'inland_flood': '내륙 홍수',
            'urban_flood': '도시 홍수',
            'coastal_flood': '해안 홍수',
            'typhoon': '태풍',
            'wildfire': '산불',
            'water_stress': '수자원 스트레스',
        }

        severity_emoji = {
            'MINIMAL': '✅',
            'LOW': '🟢',
            'MEDIUM': '🟡',
            'HIGH': '🟠',
            'CRITICAL': '🔴',
        }

        # 리스크별 점수 출력
        for risk_type, risk_data in risks.items():
            emoji = severity_emoji[risk_data['severity']]
            name = risk_names[risk_type]
            score = risk_data['score']
            severity = risk_data['severity']

            comp = risk_data['components']
            print(f"{emoji} {name:12s}: {score:6.2f} ({severity:8s}) "
                  f"[H={comp['hazard']:.0f} × E={comp['exposure']:.0f} × V={comp['vulnerability']:.0f}]")

        # 종합 점수
        print(f"\n🎯 종합 리스크 점수: {total_score:.2f} / 900")
        print(f"📈 위험 수준: {risk_level}")

    def _print_scenario_comparison(self, results: Dict):
        """시나리오 비교 출력"""
        print(f"\n{'='*80}")
        print("📊 시나리오별 종합 비교")
        print(f"{'='*80}")

        risk_names = {
            'extreme_heat': '극한 고온',
            'extreme_cold': '극한 한파',
            'drought': '가뭄',
            'inland_flood': '내륙 홍수',
            'urban_flood': '도시 홍수',
            'coastal_flood': '해안 홍수',
            'typhoon': '태풍',
            'wildfire': '산불',
            'water_stress': '수자원 스트레스',
        }

        # 1. 종합 점수 비교
        print(f"\n🎯 종합 리스크 점수 비교:")
        for scenario in self.scenarios:
            total = results[scenario]['total_score']
            level = results[scenario]['risk_level']
            print(f"  {scenario}: {total:6.2f} ({level})")

        # 2. 리스크별 시나리오 비교
        print(f"\n📈 리스크별 시나리오 비교 (SSP126 → SSP585):")
        print(f"{'─'*80}")

        risk_types = [
            'extreme_heat', 'extreme_cold', 'drought',
            'inland_flood', 'urban_flood', 'coastal_flood',
            'typhoon', 'wildfire', 'water_stress'
        ]

        for risk_type in risk_types:
            name = risk_names[risk_type]
            scores = [results[s]['risks'][risk_type]['score'] for s in self.scenarios]

            # 증감 표시
            if scores[-1] > scores[0] * 1.2:  # 20% 이상 증가
                trend = "📈 증가"
            elif scores[-1] < scores[0] * 0.8:  # 20% 이상 감소
                trend = "📉 감소"
            else:
                trend = "➡️  안정"

            score_str = " → ".join([f"{s:5.1f}" for s in scores])
            print(f"{name:12s}: {score_str}  {trend}")

        print(f"{'='*80}")

    def save_report(self, result: Dict, filename: str = None):
        """리스크 평가 결과를 JSON으로 저장"""
        if filename is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"risk_assessment_{timestamp}.json"

        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)

        print(f"\n💾 결과 저장: {filename}")


# ============================================================================
# CLI Interface
# ============================================================================

def main():
    """커맨드라인 인터페이스"""
    import argparse

    parser = argparse.ArgumentParser(description='물리적 리스크 평가')
    parser.add_argument('--address', type=str, help='주소')
    parser.add_argument('--lat', type=float, help='위도')
    parser.add_argument('--lon', type=float, help='경도')
    parser.add_argument('--output', type=str, help='출력 파일명')

    args = parser.parse_args()

    if args.address:
        location = args.address
    elif args.lat and args.lon:
        location = (args.lat, args.lon)
    else:
        # 대화형 모드
        print("물리적 리스크 평가 시스템")
        print("="*80)
        choice = input("입력 방식을 선택하세요 (1: 주소, 2: 좌표): ")

        if choice == '1':
            location = input("주소를 입력하세요: ")
        else:
            lat = float(input("위도: "))
            lon = float(input("경도: "))
            location = (lat, lon)

    # 계산 실행
    calculator = RiskCalculator()
    result = calculator.calculate_all_risks(location)

    # 결과 저장
    if args.output:
        calculator.save_report(result, args.output)


if __name__ == "__main__":
    main()
