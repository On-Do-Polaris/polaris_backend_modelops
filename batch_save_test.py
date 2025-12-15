"""9개 리스크 H 계산 후 DB 저장 테스트"""
import sys
sys.path.insert(0, '.')

from modelops.utils.hazard_data_collector import HazardDataCollector
from modelops.database.connection import DatabaseConnection
from modelops.agents.hazard_calculate.extreme_heat_hscore_agent import ExtremeHeatHScoreAgent
from modelops.agents.hazard_calculate.extreme_cold_hscore_agent import ExtremeColdHScoreAgent
from modelops.agents.hazard_calculate.drought_hscore_agent import DroughtHScoreAgent
from modelops.agents.hazard_calculate.river_flood_hscore_agent import RiverFloodHScoreAgent
from modelops.agents.hazard_calculate.urban_flood_hscore_agent import UrbanFloodHScoreAgent
from modelops.agents.hazard_calculate.wildfire_hscore_agent import WildfireHScoreAgent
from modelops.agents.hazard_calculate.water_stress_hscore_agent import WaterStressHScoreAgent
from modelops.agents.hazard_calculate.sea_level_rise_hscore_agent import SeaLevelRiseHScoreAgent
from modelops.agents.hazard_calculate.typhoon_hscore_agent import TyphoonHScoreAgent

lat, lon = 37.5665, 126.978
scenario = 'SSP245'
year = 2030

agents = {
    'extreme_heat': ExtremeHeatHScoreAgent(),
    'extreme_cold': ExtremeColdHScoreAgent(),
    'drought': DroughtHScoreAgent(),
    'river_flood': RiverFloodHScoreAgent(),
    'urban_flood': UrbanFloodHScoreAgent(),
    'wildfire': WildfireHScoreAgent(),
    'water_stress': WaterStressHScoreAgent(),
    'sea_level_rise': SeaLevelRiseHScoreAgent(),
    'typhoon': TyphoonHScoreAgent(),
}

collector = HazardDataCollector(scenario=scenario, target_year=year)
results = []

print('='*60)
print(f'  9개 리스크 H 계산 및 DB 저장 테스트')
print(f'  Location: ({lat}, {lon}), {scenario}, {year}')
print('='*60)

for risk_type, agent in agents.items():
    collected = collector.collect_data(lat, lon, risk_type)
    h_score = agent.calculate_hazard(collected)

    results.append({
        'latitude': lat,
        'longitude': lon,
        'scenario': scenario,
        'target_year': year,
        'risk_type': risk_type,
        'hazard_score_100': h_score * 100
    })
    print(f'{risk_type:20s}: H={h_score:.4f} ({h_score*100:.1f}/100)')

print()
print('DB에 저장 중...')
DatabaseConnection.save_hazard_results(results)
print('저장 완료!')
