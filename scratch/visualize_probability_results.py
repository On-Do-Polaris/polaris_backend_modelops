"""
리스크별 발생확률 시각화
대덕 데이터센터 (대전광역시 유성구) 기준
"""
import json
import matplotlib
matplotlib.use('Agg')  # GUI 없이 실행
import matplotlib.pyplot as plt
import numpy as np
from pathlib import Path

# 한글 폰트 설정
plt.rcParams['font.family'] = 'Malgun Gothic'
plt.rcParams['axes.unicode_minus'] = False

# 결과 로드
results_path = Path(__file__).parent / "probability_test_results.json"
with open(results_path, 'r', encoding='utf-8') as f:
    results = json.load(f)

# 색상 팔레트
colors = {
    'heat': '#FF6B6B',
    'cold': '#4ECDC4',
    'drought': '#FFE66D',
    'inland_flood': '#4A90D9',
    'urban_flood': '#7B68EE',
    'wildfire': '#FF8C00',
    'water_scarcity': '#87CEEB',
    'typhoon': '#9370DB'
}

# 그래프 생성 (2x4 = 8개 리스크)
fig, axes = plt.subplots(2, 4, figsize=(18, 10))
fig.suptitle('대덕 데이터센터 리스크별 발생확률', fontsize=14, fontweight='bold')

risk_keys = ['heat', 'cold', 'drought', 'inland_flood', 'urban_flood', 'wildfire', 'water_scarcity', 'typhoon']
titles = ['폭염 (WSDI)', '한파 (CSDI)', '가뭄 (SPEI12)', '하천홍수 (RX1DAY)', '도시홍수 (RAIN80)', '산불 (FWI)', '물부족 (WSI)', '태풍 (S_tc)']

for idx, (key, title) in enumerate(zip(risk_keys, titles)):
    ax = axes[idx // 4, idx % 4]
    data = results[key]

    bins_info = data['calculation_details']['bins']
    probs = [b['probability'] * 100 for b in bins_info]
    labels = [f"bin{b['bin']}\n{b['range'].split(' ~ ')[0][:6]}" for b in bins_info]

    # 막대 그래프
    bars = ax.bar(range(len(probs)), probs, color=colors[key], edgecolor='black', alpha=0.8)

    # 값 표시
    for bar, prob in zip(bars, probs):
        if prob > 0:
            ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 1,
                   f'{prob:.1f}%', ha='center', va='bottom', fontsize=9)

    ax.set_xticks(range(len(labels)))
    ax.set_xticklabels(labels, fontsize=8)
    ax.set_ylabel('발생확률 (%)')
    ax.set_title(f'{title}\n({data["risk_type"]})', fontsize=11)
    ax.set_ylim(0, 110)

    # 시간 단위 표시
    time_unit = data['calculation_details'].get('time_unit', 'yearly')
    if time_unit == 'monthly':
        total = data['calculation_details']['total_months']
        ax.text(0.98, 0.98, f'{total}개월', transform=ax.transAxes,
               ha='right', va='top', fontsize=8, color='gray')
    else:
        total = data['calculation_details']['total_years']
        ax.text(0.98, 0.98, f'{total}년', transform=ax.transAxes,
               ha='right', va='top', fontsize=8, color='gray')

plt.tight_layout()
output_path = Path(__file__).parent / 'probability_visualization.png'
plt.savefig(output_path, dpi=150, bbox_inches='tight')
plt.close()

print(f"시각화 완료: {output_path}")


# 요약 테이블 출력
print("\n" + "="*70)
print("리스크별 발생확률 요약")
print("="*70)
print(f"{'리스크':<12} {'시간단위':<8} {'주요 bin':<20} {'확률':<10}")
print("-"*70)

for key, title in zip(risk_keys, titles):
    data = results[key]
    time_unit = data['calculation_details'].get('time_unit', 'yearly')
    bins_info = data['calculation_details']['bins']

    # 가장 높은 확률의 bin 찾기
    max_bin = max(bins_info, key=lambda x: x['probability'])

    print(f"{data['risk_type']:<12} {time_unit:<8} bin{max_bin['bin']} ({max_bin['range'][:15]}...) {max_bin['probability']*100:>6.1f}%")

print("="*70)
