#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
리스크 비교 기능 테스트 스크립트

사용법:
    python test_risk_comparison.py
"""

import json
import sys
import os

# 테스트 파일이 src 폴더 외부의 tests 폴더에 있으므로,
# 상위 폴더(Physical_RISK_calculate)를 sys.path에 추가하여 src 모듈을 찾을 수 있도록 함
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.calculators.risk_calculator import RiskCalculator


def print_separator(title=""):
    """구분선 출력"""
    if title:
        print(f"\n{'='*80}")
        print(f"  {title}")
        print(f"{'='*80}")
    else:
        print(f"{'─'*80}")


def format_risk_detail(risk):
    """리스크 상세 정보 포맷팅"""
    return (
        f"  {risk['name']:12s} | "
        f"점수: {risk['score']:6.2f} | "
        f"심각도: {risk['severity']:8s} | "
        f"카테고리: {risk['category']:8s} | "
        f"H:{risk['components']['hazard']:.0f} "
        f"E:{risk['components']['exposure']:.0f} "
        f"V:{risk['components']['vulnerability']:.0f}"
    )


def test_basic_comparison():
    """기본 리스크 비교 테스트"""
    print_separator("📊 리스크 비교 기능 테스트")

    # 1. 리스크 계산기 초기화
    print("\n[Step 1] RiskCalculator 초기화...")
    calculator = RiskCalculator(target_year=2030)

    # 2. 테스트 위치 (서울시청 좌표)
    test_location = (37.5665, 126.9780)
    print(f"[Step 2] 테스트 위치: {test_location}")
    print("         (서울시청 좌표)")

    # 3. 전체 리스크 계산
    print("\n[Step 3] 전체 리스크 계산 중...")
    print_separator()
    risk_results = calculator.calculate_all_risks(test_location)

    # 4. 리스크 비교 수행
    print_separator("리스크 비교 수행")
    print("\n[Step 4] compare_risks_comprehensive() 호출...")
    comparison = calculator.compare_risks_comprehensive(
        risk_results=risk_results,
        scenario='SSP245'
    )

    # 5. TCFD 준수 리스크 출력
    print_separator("🎯 TCFD 최우선 리스크")

    print("\n📌 Primary Acute Risk (급성 리스크):")
    if comparison['tcfd']['primary_acute_risk']:
        risk = comparison['tcfd']['primary_acute_risk']
        print(format_risk_detail(risk))
    else:
        print("  N/A")

    print("\n📌 Primary Chronic Risk (만성 리스크):")
    if comparison['tcfd']['primary_chronic_risk']:
        risk = comparison['tcfd']['primary_chronic_risk']
        print(format_risk_detail(risk))
    else:
        print("  N/A")

    # 6. 전체 순위 출력
    print_separator("📈 전체 리스크 순위 (1-9위)")

    severity_emoji = {
        'CRITICAL': '🔴',
        'HIGH': '🟠',
        'MEDIUM': '🟡',
        'LOW': '🟢',
        'MINIMAL': '✅',
    }

    category_emoji = {
        'acute': '⚡',
        'chronic': '📈',
    }

    for risk in comparison['all_risks_ranked']:
        emoji = severity_emoji.get(risk['severity'], '❓')
        cat_emoji = category_emoji.get(risk['category'], '❓')
        print(
            f"  {emoji} #{risk['rank']:2d}위  {cat_emoji} {risk['name']:12s} | "
            f"{risk['score']:6.2f}점 ({risk['severity']:8s})"
        )

    # 7. 카테고리별 순위 출력
    print_separator("⚡ Acute Risks (급성 리스크)")
    for risk in comparison['acute_risks_ranked']:
        print(f"  #{risk['rank']:2d}위  {risk['name']:12s} | {risk['score']:6.2f}점")

    print_separator("📈 Chronic Risks (만성 리스크)")
    for risk in comparison['chronic_risks_ranked']:
        print(f"  #{risk['rank']:2d}위  {risk['name']:12s} | {risk['score']:6.2f}점")

    # 8. 메타데이터 출력
    print_separator("ℹ️  메타데이터")
    meta = comparison['metadata']
    print(f"\n  시나리오: {meta['scenario']} ({meta['scenario_name']})")
    print(f"  분석 연도: {meta['target_year']}")
    print(f"  분류 기준: {meta['classification_standard']}")
    print(f"  비교 방법: {meta['comparison_method']}")
    print(f"  TCFD 준수: {meta['tcfd_compliant']}")
    print(f"  분석 리스크 수: {meta['total_risks_analyzed']}개")
    print(f"  Acute: {meta['acute_risks_count']}개, Chronic: {meta['chronic_risks_count']}개")

    print_separator()

    return comparison


def test_scenario_comparison():
    """여러 시나리오 비교 테스트"""
    print_separator("🌍 시나리오별 리스크 비교")

    calculator = RiskCalculator(target_year=2030)
    test_location = (37.5665, 126.9780)

    # 전체 리스크 계산 (4개 시나리오)
    print("\n[전체 시나리오 리스크 계산 중...]")
    risk_results = calculator.calculate_all_risks(test_location)

    # 시나리오별 비교
    scenarios = ['SSP126', 'SSP245', 'SSP370', 'SSP585']
    comparisons = {}

    for scenario in scenarios:
        comparisons[scenario] = calculator.compare_risks_comprehensive(
            risk_results=risk_results,
            scenario=scenario
        )

    # 시나리오별 1위 리스크 출력
    print_separator("시나리오별 1위 리스크")
    print(f"\n{'시나리오':<10} | {'1위 리스크':<15} | {'점수':<8} | {'카테고리'}")
    print(f"{'-'*60}")

    for scenario in scenarios:
        top_risk = comparisons[scenario]['all_risks_ranked'][0]
        print(
            f"{scenario:<10} | {top_risk['name']:<15} | "
            f"{top_risk['score']:>6.2f}점 | {top_risk['category']}"
        )

    print_separator()

    return comparisons


def test_json_output():
    """JSON 출력 테스트 (프론트엔드 API 응답 예시)"""
    print_separator("📦 JSON 출력 테스트 (API 응답 형식)")

    calculator = RiskCalculator(target_year=2030)
    test_location = (37.5665, 126.9780)

    risk_results = calculator.calculate_all_risks(test_location)
    comparison = calculator.compare_risks_comprehensive(
        risk_results=risk_results,
        scenario='SSP245'
    )

    # JSON 변환
    json_output = json.dumps(comparison, ensure_ascii=False, indent=2)

    # 파일로 저장
    output_file = 'risk_comparison_output.json'
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(json_output)

    print(f"\n✅ JSON 파일 저장 완료: {output_file}")
    print(f"\n📄 JSON 샘플 (처음 30줄):")
    print_separator()

    lines = json_output.split('\n')
    for i, line in enumerate(lines[:30], 1):
        print(f"{i:3d} | {line}")

    if len(lines) > 30:
        print(f"... (총 {len(lines)}줄)")

    print_separator()

    return comparison


def main():
    """메인 테스트 실행"""
    print("\n" + "="*80)
    print("  리스크 비교 기능 종합 테스트")
    print("="*80)

    try:
        # 테스트 1: 기본 리스크 비교
        comparison1 = test_basic_comparison()

        # 테스트 2: 시나리오별 비교
        # comparisons = test_scenario_comparison()

        # 테스트 3: JSON 출력
        comparison3 = test_json_output()

        print_separator("✅ 모든 테스트 완료")
        print("\n🎉 리스크 비교 기능이 정상적으로 작동합니다!")
        print("\n📚 다음 단계:")
        print("  1. risk_comparison_output.json 파일 확인")
        print("  2. 프론트엔드 API 연동")
        print("  3. 대시보드 UI 구현")
        print("\n📖 참고 문서:")
        print("  - docs/02_methodology/risk_comparison_methodology.md")
        print("  - docs/05_frontend/risk_comparison_api_examples.md")

        print_separator()

    except Exception as e:
        print(f"\n❌ 테스트 실패: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
