#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
백엔드 파이프라인 메인 오케스트레이터
위/경도 또는 주소 입력 → 최종 리포트 출력
"""

from typing import Dict, Optional, Union
from datetime import datetime
import json
from pathlib import Path


class RiskAssessmentPipeline:
    """
    물리적 리스크 평가 파이프라인

    플로우:
    1. 데이터 수집
    2. 취약성 분석
    3. [병렬] 물리적 리스크 점수 + AAL 계산
    4. 기초 보고서 분석
    5. 영향 분석
    6. 대응 전략 생성 (LLM/RAG)
    7. 리포트 생성
    8. 검증 → (실패 시 재생성)
    9. 최종 리포트 산출
    """

    def __init__(self, config: Optional[Dict] = None):
        """
        Args:
            config: 파이프라인 설정
        """
        self.config = config or self._default_config()

        # 각 모듈 초기화는 lazy loading
        self._data_collector = None
        self._vulnerability_analyzer = None
        self._risk_calculator = None
        self._aal_calculator = None
        self._impact_analyzer = None
        self._strategy_generator = None
        self._report_generator = None
        self._validator = None

    def run(self, location: Union[str, tuple], asset_value: float = None) -> Dict:
        """
        파이프라인 전체 실행

        Args:
            location: 주소(str) 또는 (lat, lon) 튜플
            asset_value: 자산 가치 (원), AAL 계산용

        Returns:
            최종 리포트 (JSON)
        """
        print("="*80)
        print("🚀 물리적 리스크 평가 파이프라인 시작")
        print("="*80)

        # 1. 데이터 수집
        print("\n[Step 1/9] 데이터 수집")
        data = self._step1_data_collection(location)

        # 2. 취약성 분석
        print("\n[Step 2/9] 취약성 분석")
        vulnerability = self._step2_vulnerability_analysis(data)

        # 3. [병렬] 물리적 리스크 점수 + AAL 계산
        print("\n[Step 3/9] 물리적 리스크 총합 점수 산출 & 연평균 재무 손실률 분석 (병렬)")
        risk_scores = self._step3a_calculate_risk_scores(data, vulnerability)
        aal_result = self._step3b_calculate_aal(data, vulnerability, asset_value)

        # 4. 기초 보고서 분석
        print("\n[Step 4/9] 기초 보고서 분석 (SK AX SR 보고서)")
        base_report = self._step4_base_report_analysis(risk_scores, aal_result)

        # 5. 영향 분석
        print("\n[Step 5/9] 영향 분석 (9대 물리적 리스크별)")
        impact_analysis = self._step5_impact_analysis(risk_scores, data, vulnerability)

        # 6. 대응 전략 생성 (LLM/RAG)
        print("\n[Step 6/9] 대응 전략 생성 (LLM/RAG)")
        strategies = self._step6_strategy_generation(
            risk_scores,
            impact_analysis,
            data
        )

        # 7. 리포트 생성
        print("\n[Step 7/9] 리포트 생성")
        report = self._step7_report_generation(
            data=data,
            vulnerability=vulnerability,
            risk_scores=risk_scores,
            aal_result=aal_result,
            impact_analysis=impact_analysis,
            strategies=strategies,
        )

        # 8. 검증 (정확성, 일관성 확인)
        print("\n[Step 8/9] 검증 (정확성, 일관성 확인)")
        max_retries = 3
        for attempt in range(max_retries):
            validation_result = self._step8_validation(report)

            if validation_result['valid']:
                print(f"   ✅ 검증 통과")
                break
            else:
                print(f"   ⚠️  검증 실패 (시도 {attempt + 1}/{max_retries})")
                print(f"   이슈: {validation_result['issues']}")

                if attempt < max_retries - 1:
                    print(f"   🔄 리포트 재생성 중...")
                    # 문제가 있는 부분만 재생성
                    report = self._regenerate_report(report, validation_result)
                else:
                    print(f"   ⚠️  최대 재시도 횟수 초과, 경고와 함께 리포트 반환")
                    report['validation_warnings'] = validation_result['issues']

        # 9. 최종 리포트 산출
        print("\n[Step 9/9] 최종 리포트 산출")
        final_report = self._finalize_report(report)

        print("\n" + "="*80)
        print("✅ 파이프라인 완료")
        print("="*80)

        return final_report

    # ========================================================================
    # Step 1: 데이터 수집
    # ========================================================================

    def _step1_data_collection(self, location: Union[str, tuple]) -> Dict:
        """
        위/경도 또는 주소 → 모든 필요 데이터 수집

        Returns:
            {
                'location': {lat, lon, address, ...},
                'building': {floors, structure, age, ...},
                'hazard': {climate, disaster_history, ...},
                'infrastructure': {fire_station, water_supply, ...}
            }
        """
        from pipeline.data_collector import DataCollector

        if self._data_collector is None:
            self._data_collector = DataCollector()

        return self._data_collector.collect(location)

    # ========================================================================
    # Step 2: 취약성 분석
    # ========================================================================

    def _step2_vulnerability_analysis(self, data: Dict) -> Dict:
        """
        건물 연식, 내진 설계, 소방시설 등 → 취약성 지표

        Returns:
            {
                'structural': {score, factors},
                'age_deterioration': {score, factors},
                'fire_safety': {score, factors},
                'seismic': {score, factors},
                ...
            }
        """
        from pipeline.vulnerability_analyzer import VulnerabilityAnalyzer

        if self._vulnerability_analyzer is None:
            self._vulnerability_analyzer = VulnerabilityAnalyzer()

        return self._vulnerability_analyzer.analyze(data)

    # ========================================================================
    # Step 3: 물리적 리스크 점수 + AAL (병렬)
    # ========================================================================

    def _step3a_calculate_risk_scores(self, data: Dict, vulnerability: Dict) -> Dict:
        """
        9개 물리적 리스크 총합 점수 산출

        Returns:
            {
                'extreme_heat': {score, severity, factors},
                'extreme_cold': {score, severity, factors},
                'drought': {score, severity, factors},
                'inland_flood': {score, severity, factors},
                'urban_flood': {score, severity, factors},
                'coastal_flood': {score, severity, factors},
                'typhoon': {score, severity, factors},
                'wildfire': {score, severity, factors},
                'water_stress': {score, severity, factors},
                'total_score': 456.7,
                'risk_level': 'HIGH'
            }
        """
        from pipeline.risk_calculator import RiskCalculator

        if self._risk_calculator is None:
            self._risk_calculator = RiskCalculator()

        return self._risk_calculator.calculate_all_risks(data, vulnerability)

    def _step3b_calculate_aal(
        self,
        data: Dict,
        vulnerability: Dict,
        asset_value: Optional[float]
    ) -> Dict:
        """
        연평균 재무 손실률 분석 (AAL)

        Returns:
            {
                'aal_krw': 125000000,  # 연평균 손실액 (원)
                'aal_ratio': 0.025,  # 자산 대비 비율 (2.5%)
                'by_risk': {
                    'inland_flood': 50000000,
                    'typhoon': 30000000,
                    ...
                },
                'loss_curve': {...},
                'return_periods': {
                    '100yr': 500000000,
                    '500yr': 2000000000,
                }
            }
        """
        from pipeline.aal_calculator import AALCalculator

        if self._aal_calculator is None:
            self._aal_calculator = AALCalculator()

        # asset_value 기본값: 건물 특성 기반 추정
        if asset_value is None:
            asset_value = self._estimate_asset_value(data)

        return self._aal_calculator.calculate(data, vulnerability, asset_value)

    # ========================================================================
    # Step 4: 기초 보고서 분석
    # ========================================================================

    def _step4_base_report_analysis(self, risk_scores: Dict, aal_result: Dict) -> Dict:
        """
        SK AX SR 보고서 형식 분석

        Returns:
            {
                'executive_summary': str,
                'risk_matrix': {...},
                'financial_impact': {...},
                'compliance': {...}
            }
        """
        from pipeline.base_report_analyzer import BaseReportAnalyzer

        analyzer = BaseReportAnalyzer()
        return analyzer.analyze(risk_scores, aal_result)

    # ========================================================================
    # Step 5: 영향 분석
    # ========================================================================

    def _step5_impact_analysis(
        self,
        risk_scores: Dict,
        data: Dict,
        vulnerability: Dict
    ) -> Dict:
        """
        9대 물리적 리스크별 영향 분석

        Returns:
            {
                'extreme_heat': {
                    'operational_impact': {...},
                    'financial_impact': {...},
                    'timeline': {...}
                },
                ...
            }
        """
        from pipeline.impact_analyzer import ImpactAnalyzer

        if self._impact_analyzer is None:
            self._impact_analyzer = ImpactAnalyzer()

        return self._impact_analyzer.analyze(risk_scores, data, vulnerability)

    # ========================================================================
    # Step 6: 대응 전략 생성 (LLM/RAG)
    # ========================================================================

    def _step6_strategy_generation(
        self,
        risk_scores: Dict,
        impact_analysis: Dict,
        data: Dict
    ) -> Dict:
        """
        LLM(RAG)을 활용한 대응 전략 생성

        Returns:
            {
                'immediate_actions': [...],
                'short_term_strategies': [...],
                'long_term_strategies': [...],
                'investment_priorities': [...],
                'rag_sources': [...]
            }
        """
        from pipeline.strategy_generator import StrategyGenerator

        if self._strategy_generator is None:
            self._strategy_generator = StrategyGenerator()

        return self._strategy_generator.generate(risk_scores, impact_analysis, data)

    # ========================================================================
    # Step 7: 리포트 생성
    # ========================================================================

    def _step7_report_generation(self, **components) -> Dict:
        """
        모든 컴포넌트를 종합하여 최종 리포트 생성
        """
        from pipeline.report_generator import ReportGenerator

        if self._report_generator is None:
            self._report_generator = ReportGenerator()

        return self._report_generator.generate(**components)

    # ========================================================================
    # Step 8: 검증
    # ========================================================================

    def _step8_validation(self, report: Dict) -> Dict:
        """
        정확성, 일관성 확인

        Returns:
            {
                'valid': bool,
                'issues': [list of issues],
                'warnings': [list of warnings]
            }
        """
        from pipeline.report_validator import ReportValidator

        if self._validator is None:
            self._validator = ReportValidator()

        return self._validator.validate(report)

    def _regenerate_report(self, report: Dict, validation_result: Dict) -> Dict:
        """검증 실패 시 리포트 재생성"""
        # TODO: 문제가 있는 섹션만 재생성
        return report

    # ========================================================================
    # Step 9: 최종화
    # ========================================================================

    def _finalize_report(self, report: Dict) -> Dict:
        """최종 리포트 메타데이터 추가 및 포맷팅"""
        final = {
            'metadata': {
                'generated_at': datetime.now().isoformat(),
                'pipeline_version': '1.0.0',
                'tcfd_compliant': True,
            },
            'report': report
        }

        # JSON 저장
        if self.config.get('save_output', True):
            self._save_report(final)

        return final

    # ========================================================================
    # Helper Methods
    # ========================================================================

    def _default_config(self) -> Dict:
        """기본 설정"""
        return {
            'save_output': True,
            'output_dir': './outputs',
            'max_validation_retries': 3,
            'enable_llm': True,
        }

    def _estimate_asset_value(self, data: Dict) -> float:
        """건물 특성 기반 자산 가치 추정"""
        # TODO: 건물 크기, 용도, 위치 등 기반 추정
        return 5000000000  # 기본값 50억 원

    def _save_report(self, report: Dict):
        """리포트를 JSON 파일로 저장"""
        output_dir = Path(self.config['output_dir'])
        output_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"risk_report_{timestamp}.json"
        filepath = output_dir / filename

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)

        print(f"\n📄 리포트 저장: {filepath}")


# ============================================================================
# CLI Interface
# ============================================================================

def main():
    """커맨드라인 인터페이스"""
    import argparse

    parser = argparse.ArgumentParser(description='물리적 리스크 평가 파이프라인')
    parser.add_argument('--address', type=str, help='주소 (예: 서울특별시 강남구 삼성동 16-1)')
    parser.add_argument('--lat', type=float, help='위도')
    parser.add_argument('--lon', type=float, help='경도')
    parser.add_argument('--asset-value', type=float, help='자산 가치 (원)')

    args = parser.parse_args()

    # 입력 검증
    if args.address:
        location = args.address
    elif args.lat and args.lon:
        location = (args.lat, args.lon)
    else:
        print("❌ 주소(--address) 또는 위경도(--lat, --lon)를 입력하세요.")
        return

    # 파이프라인 실행
    pipeline = RiskAssessmentPipeline()
    result = pipeline.run(location, asset_value=args.asset_value)

    print("\n" + "="*80)
    print("📊 결과 요약:")
    print("="*80)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
