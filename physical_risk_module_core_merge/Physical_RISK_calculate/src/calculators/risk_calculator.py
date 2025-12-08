#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Risk Calculator
최종 리스크 점수 계산: Risk = H × E × V
"""

from typing import Dict, Union, Tuple
import json
from datetime import datetime
from .exposure_calculator import ExposureCalculator
from .hazard_calculator import HazardCalculator
from .vulnerability_calculator import VulnerabilityCalculator


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

    # TCFD 물리적 리스크 분류 (TCFD Final Report 2017 기준)
    TCFD_ACUTE_RISKS = ['typhoon', 'river_flood', 'urban_flood', 'wildfire']
    TCFD_CHRONIC_RISKS = ['extreme_heat', 'extreme_cold', 'drought', 'water_stress', 'sea_level_rise']

    RISK_DISPLAY_NAMES = {
        'extreme_heat': '극심한 고온',
        'extreme_cold': '극심한 한파',
        'drought': '가뭄',
        'river_flood': '하천 홍수',
        'urban_flood': '도시 홍수',
        'sea_level_rise': '해수면 상승',
        'typhoon': '태풍',
        'wildfire': '산불',
        'water_stress': '물부족',
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
                'river_flood', 'urban_flood', 'sea_level_rise',
                'typhoon', 'wildfire', 'water_stress'
            ]

            for risk_type in risk_types:
                risks[risk_type] = self._calculate_single_risk(
                    risk_type, H[risk_type], E, V[risk_type]
                )

            # TCFD 준수: 통합 점수 없이 개별 리스크만 평가
            # 근거: TCFD Final Report (2017) - 리스크별 독립 평가 권장
            # "Organizations should describe the specific climate-related risks
            #  without aggregating into a single risk score"
            results[scenario] = {
                'risks': risks,
                'hazard': H,
            }

            # 시나리오별 결과 출력
            self._print_scenario_results(scenario, risks)

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

    def compare_risks_comprehensive(
        self,
        risk_results: Dict,
        scenario: str = 'SSP245'
    ) -> Dict:
        """
        TCFD 준수 + 프론트엔드 최적화 리스크 비교

        전체 리스크를 점수순으로 정렬하여 제공하며,
        TCFD 기준에 따른 Acute/Chronic 분류도 함께 제공합니다.

        Args:
            risk_results: calculate_all_risks() 의 반환값
            scenario: 비교할 시나리오 (기본값: SSP245)

        Returns:
            {
                # TCFD 준수: 최우선 급성/만성 리스크
                'tcfd': {
                    'primary_acute_risk': {
                        'type': 'typhoon',
                        'name': '태풍',
                        'score': 85.3,
                        'severity': 'CRITICAL',
                        'category': 'acute',
                        'components': {
                            'hazard': 90.0,
                            'exposure': 80.0,
                            'vulnerability': 95.0
                        }
                    },
                    'primary_chronic_risk': {
                        'type': 'extreme_heat',
                        'name': '극심한 고온',
                        'score': 72.1,
                        'severity': 'HIGH',
                        'category': 'chronic',
                        'components': {...}
                    }
                },

                # 프론트엔드용: 전체 리스크 순위 (9개 전체)
                'all_risks_ranked': [
                    {
                        'rank': 1,
                        'type': 'typhoon',
                        'name': '태풍',
                        'score': 85.3,
                        'severity': 'CRITICAL',
                        'category': 'acute',
                        'components': {...}
                    },
                    # ... 9개 전체
                ],

                # 카테고리별 순위 (선택)
                'acute_risks_ranked': [...],
                'chronic_risks_ranked': [...],

                # 메타데이터
                'metadata': {
                    'scenario': 'SSP245',
                    'scenario_name': '중간 시나리오 (현재 추세)',
                    'target_year': 2030,
                    'classification_standard': 'TCFD Final Report 2017',
                    'comparison_method': 'Direct H×E×V score comparison within same normalization',
                    'tcfd_compliant': True
                }
            }

        근거:
            - TCFD Final Report (2017): Physical risks를 Acute와 Chronic으로 분류
            - IPCC AR6 WGII Chapter 16: 리스크 평가 프레임워크
            - 동일한 정규화 체계(0-100) 내에서 직접 비교 가능
        """

        # 입력 검증
        if scenario not in self.SCENARIOS:
            raise ValueError(f"Invalid scenario: {scenario}. Must be one of {self.SCENARIOS}")

        if 'scenarios' not in risk_results:
            raise ValueError("Invalid risk_results format. Expected output from calculate_all_risks()")

        if scenario not in risk_results['scenarios']:
            raise ValueError(f"Scenario {scenario} not found in risk_results")

        # 해당 시나리오의 리스크 데이터 추출
        scenario_data = risk_results['scenarios'][scenario]
        risks = scenario_data['risks']

        # 전체 리스크 리스트 생성 (점수순 정렬)
        all_risks = []
        for risk_type, risk_data in risks.items():
            # TCFD 카테고리 분류
            if risk_type in self.TCFD_ACUTE_RISKS:
                category = 'acute'
            elif risk_type in self.TCFD_CHRONIC_RISKS:
                category = 'chronic'
            else:
                category = 'unknown'  # 예외 처리

            all_risks.append({
                'type': risk_type,
                'name': self.RISK_DISPLAY_NAMES.get(risk_type, risk_type),
                'score': risk_data['score'],
                'severity': risk_data['severity'],
                'category': category,
                'components': risk_data['components']
            })

        # 점수순 정렬 (내림차순)
        all_risks_sorted = sorted(all_risks, key=lambda x: x['score'], reverse=True)

        # 순위 추가
        for idx, risk in enumerate(all_risks_sorted, start=1):
            risk['rank'] = idx

        # TCFD 분류: 급성/만성 리스크 분리
        acute_risks = [r for r in all_risks_sorted if r['category'] == 'acute']
        chronic_risks = [r for r in all_risks_sorted if r['category'] == 'chronic']

        # TCFD 최우선 리스크 선정
        primary_acute = acute_risks[0] if acute_risks else None
        primary_chronic = chronic_risks[0] if chronic_risks else None

        # 결과 구성
        result = {
            'tcfd': {
                'primary_acute_risk': primary_acute,
                'primary_chronic_risk': primary_chronic
            },
            'all_risks_ranked': all_risks_sorted,
            'acute_risks_ranked': acute_risks,
            'chronic_risks_ranked': chronic_risks,
            'metadata': {
                'scenario': scenario,
                'scenario_name': self.SCENARIO_NAMES[scenario],
                'target_year': self.target_year,
                'classification_standard': 'TCFD Final Report 2017',
                'comparison_method': 'Direct H×E×V score comparison within same normalization',
                'tcfd_compliant': True,
                'total_risks_analyzed': len(all_risks_sorted),
                'acute_risks_count': len(acute_risks),
                'chronic_risks_count': len(chronic_risks)
            }
        }

        return result

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
            # 극심한 고온 일수 기반
            days = hazard['heatwave_days_per_year']
            return min(100, days * 3)  # 25일 → 75점

        elif risk_type == 'extreme_cold':
            days = hazard['coldwave_days_per_year']
            return min(100, days * 5)  # 10일 → 50점

        elif risk_type == 'drought':
            freq = hazard['drought_frequency']
            return min(100, freq * 500)  # 0.1 → 50점

        elif risk_type == 'river_flood':
            # 침수 이력 + 강수량
            history = hazard.get('historical_flood_count', 0)
            rainfall = hazard.get('extreme_rainfall_1day_mm', 0)
            return min(100, history * 10 + rainfall / 5)

        elif risk_type == 'urban_flood':
            history = hazard.get('historical_flood_count', 0)
            rainfall = hazard.get('extreme_rainfall_1hr_mm', 0)
            return min(100, history * 10 + rainfall)

        elif risk_type == 'sea_level_rise':
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
        if risk_type == 'river_flood':
            # 하천 홍수: 하천 거리 기반
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

        elif risk_type == 'urban_flood':
            # 도시 홍수: 불투수면 비율 기반 (TCFD 정합성 개선)
            urban_exp = exposure.get('urban_flood_exposure', {})
            impervious_ratio = urban_exp.get('impervious_surface_ratio', 0.6)  # 기본값: 주거 지역

            # 불투수면 비율 → 점수 변환 (>80% → 90점)
            if impervious_ratio >= 0.80:
                return 90  # 매우 높음 (상업/공업)
            elif impervious_ratio >= 0.70:
                return 75  # 높음 (복합)
            elif impervious_ratio >= 0.60:
                return 60  # 중간 (주거)
            elif impervious_ratio >= 0.50:
                return 40  # 낮음
            else:
                return 20  # 매우 낮음 (농촌/녹지)

        elif risk_type == 'sea_level_rise':
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

        elif risk_type == 'wildfire':
            # 산불 노출도 (산림 인접도)
            # Critical (< 100m): 100점
            # Warning (100m ~ 500m): 70점
            # Caution (500m ~ 2000m): 40점
            # Safe (> 2000m): 10점
            wildfire_exp = exposure.get('wildfire_exposure', {})
            dist = wildfire_exp.get('distance_to_forest_m', 2000)
            
            if dist < 100:
                return 100
            elif dist < 500:
                return 70
            elif dist < 2000:
                return 40
            else:
                return 10

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

    def _print_scenario_results(self, scenario: str, risks: Dict):
        """시나리오별 결과 출력 (TCFD 준수: 개별 리스크만)"""
        print(f"\n📊 {scenario} 결과")
        print(f"{'─'*80}")

        risk_names = {
            'extreme_heat': '극심한 고온',
            'extreme_cold': '극심한 한파',
            'drought': '가뭄',
            'river_flood': '하천 홍수',
            'urban_flood': '도시 홍수',
            'sea_level_rise': '해수면 상승',
            'typhoon': '태풍',
            'wildfire': '산불',
            'water_stress': '물부족',
        }

        severity_emoji = {
            'MINIMAL': '✅',
            'LOW': '🟢',
            'MEDIUM': '🟡',
            'HIGH': '🟠',
            'CRITICAL': '🔴',
        }

        # 리스크별 점수 출력 (점수 높은 순으로 정렬)
        sorted_risks = sorted(risks.items(), key=lambda x: x[1]['score'], reverse=True)

        for risk_type, risk_data in sorted_risks:
            emoji = severity_emoji[risk_data['severity']]
            name = risk_names[risk_type]
            score = risk_data['score']
            severity = risk_data['severity']

            comp = risk_data['components']
            print(f"{emoji} {name:12s}: {score:6.2f} ({severity:8s}) "
                  f"[H={comp['hazard']:.0f} × E={comp['exposure']:.0f} × V={comp['vulnerability']:.0f}]")

        print(f"\n💡 TCFD 준수: 통합 점수 없이 개별 리스크로 평가됩니다.")

    def _print_scenario_comparison(self, results: Dict):
        """시나리오별 리스크 비교 출력 (TCFD 준수)"""
        print(f"\n{'='*80}")
        print("📊 시나리오별 리스크 비교 (개별 평가)")
        print(f"{'='*80}")

        risk_names = {
            'extreme_heat': '극심한 고온',
            'extreme_cold': '극심한 한파',
            'drought': '가뭄',
            'river_flood': '하천 홍수',
            'urban_flood': '도시 홍수',
            'sea_level_rise': '해수면 상승',
            'typhoon': '태풍',
            'wildfire': '산불',
            'water_stress': '물부족',
        }

        # 리스크별 시나리오 비교
        print(f"\n📈 리스크별 시나리오 비교 (SSP126 → SSP585):")
        print(f"{'─'*80}")

        risk_types = [
            'extreme_heat', 'extreme_cold', 'drought',
            'river_flood', 'urban_flood', 'sea_level_rise',
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

        print(f"\n{'='*80}")
        print("💡 각 리스크는 독립적으로 평가되며 통합 점수는 산출하지 않습니다.")
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
