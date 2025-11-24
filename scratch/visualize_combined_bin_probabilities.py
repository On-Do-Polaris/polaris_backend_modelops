'''
파일명: visualize_combined_bin_probabilities.py
최종 수정일: 2025-11-24
파일 개요: 연도별 bin 확률 결합 시각화 (bin2~bin5 결합)
'''
import json
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import numpy as np
from pathlib import Path

# 한글 폰트 설정
plt.rcParams['font.family'] = 'Malgun Gothic'
plt.rcParams['axes.unicode_minus'] = False

def load_data(json_path: str) -> dict:
    """JSON 데이터 로드"""
    with open(json_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def calculate_combined_probability(bin_probs: list) -> float:
    """
    bin1을 제외한 나머지 bin 확률 합산
    bin1: 위험 없음/일반 수준
    bin2~bin5: 위험 수준 (결합)
    """
    if len(bin_probs) >= 2:
        return sum(bin_probs[1:])  # bin2 이상 합산
    return 0.0

def main():
    # 데이터 로드
    json_path = Path(__file__).parent / 'yearly_bin_probabilities.json'
    data = load_data(json_path)

    metadata = data['metadata']
    risks = data['risks']

    # 데이터가 있는 리스크만 필터링
    valid_risks = {k: v for k, v in risks.items()
                   if v['data'].get('SSP126') and v['data'].get('SSP585')}

    print(f"유효한 리스크 수: {len(valid_risks)}")
    for risk_key in valid_risks:
        print(f"  - {valid_risks[risk_key]['name']} ({valid_risks[risk_key]['indicator']})")

    # 연도 범위
    years = list(range(2021, 2101))

    # 시각화 설정
    n_risks = len(valid_risks)
    fig, axes = plt.subplots(n_risks, 1, figsize=(14, 3 * n_risks), sharex=True)

    if n_risks == 1:
        axes = [axes]

    colors = {'SSP126': '#2166ac', 'SSP585': '#b2182b'}

    for idx, (risk_key, risk_data) in enumerate(valid_risks.items()):
        ax = axes[idx]

        risk_name = risk_data['name']
        indicator = risk_data['indicator']

        for scenario in ['SSP126', 'SSP585']:
            scenario_data = risk_data['data'].get(scenario, {})

            combined_probs = []
            valid_years = []

            for year in years:
                year_str = str(year)
                if year_str in scenario_data:
                    bin_probs = scenario_data[year_str]
                    combined = calculate_combined_probability(bin_probs)
                    combined_probs.append(combined * 100)  # 퍼센트로 변환
                    valid_years.append(year)

            if valid_years:
                ax.plot(valid_years, combined_probs,
                       color=colors[scenario],
                       linewidth=1.5,
                       label=scenario,
                       alpha=0.8)

                # 이동평균 (5년) 추가
                if len(combined_probs) >= 5:
                    ma = np.convolve(combined_probs, np.ones(5)/5, mode='valid')
                    ma_years = valid_years[2:-2]
                    ax.plot(ma_years, ma,
                           color=colors[scenario],
                           linewidth=2.5,
                           linestyle='--',
                           alpha=0.9)

        ax.set_ylabel('위험 확률 (%)', fontsize=10)
        ax.set_title(f'{risk_name} ({indicator}) - bin2~bin5 결합 확률', fontsize=12, fontweight='bold')
        ax.legend(loc='upper left', fontsize=9)
        ax.grid(True, alpha=0.3)
        ax.set_ylim(0, 100)

        # 2050, 2100 수직선
        ax.axvline(x=2050, color='gray', linestyle=':', alpha=0.5)
        ax.axvline(x=2100, color='gray', linestyle=':', alpha=0.5)

    axes[-1].set_xlabel('연도', fontsize=11)

    plt.suptitle(f'기후 리스크별 위험 발생 확률 추이 (2021-2100)\n'
                 f'위치: {metadata["location"]} | 실선: 연간값, 점선: 5년 이동평균',
                 fontsize=14, fontweight='bold', y=1.02)

    plt.tight_layout()

    # 저장
    output_path = Path(__file__).parent / 'combined_bin_probabilities.png'
    plt.savefig(output_path, dpi=150, bbox_inches='tight', facecolor='white')
    print(f"\n시각화 저장 완료: {output_path}")

    plt.show()

    # 주요 시점별 요약 출력
    print("\n" + "="*80)
    print("주요 시점별 위험 확률 요약 (bin2~bin5 결합, %)")
    print("="*80)

    key_years = [2030, 2050, 2070, 2100]

    for risk_key, risk_data in valid_risks.items():
        print(f"\n{risk_data['name']} ({risk_data['indicator']}):")
        print("-" * 60)

        for scenario in ['SSP126', 'SSP585']:
            scenario_data = risk_data['data'].get(scenario, {})
            values = []

            for year in key_years:
                year_str = str(year)
                if year_str in scenario_data:
                    combined = calculate_combined_probability(scenario_data[year_str]) * 100
                    values.append(f"{year}: {combined:.1f}%")
                else:
                    values.append(f"{year}: N/A")

            print(f"  {scenario}: {' | '.join(values)}")

if __name__ == '__main__':
    main()
