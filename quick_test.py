"""빠른 9개 에이전트 테스트"""
import sys
sys.path.insert(0, '.')

from modelops.utils.hazard_data_collector import HazardDataCollector
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

collector = HazardDataCollector(scenario=scenario, target_year=year)

agents = [
    ('extreme_heat', ExtremeHeatHScoreAgent(), ['wsdi', 'su25', 'tr25']),
    ('extreme_cold', ExtremeColdHScoreAgent(), ['csdi', 'tnn', 'fd0', 'id0']),
    ('drought', DroughtHScoreAgent(), ['spei12', 'cdd', 'annual_rainfall']),
    ('river_flood', RiverFloodHScoreAgent(), ['rx1day', 'twi']),
    ('urban_flood', UrbanFloodHScoreAgent(), ['rx1day']),
    ('wildfire', WildfireHScoreAgent(), ['ta', 'rhm', 'ws', 'rn']),
    ('water_stress', WaterStressHScoreAgent(), ['rainfall', 'cdd']),
    ('sea_level_rise', SeaLevelRiseHScoreAgent(), ['slr', 'distance']),
    ('typhoon', TyphoonHScoreAgent(), ['frequency', 'max_wind', 'rx1day_mm']),
]

print('='*70)
print('  9개 에이전트 DB->Agent 변수 추적 결과')
print('='*70)

for risk_type, agent, vars_to_check in agents:
    collected = collector.collect_data(lat, lon, risk_type)
    score = agent.calculate_hazard(collected)
    details = collected.get('calculation_details', {}).get(risk_type, {})

    print(f'\n[{risk_type.upper()}] H={score:.4f}')
    for var in vars_to_check:
        agent_val = details.get(var, 'NOT RECORDED')
        if agent_val == 'NOT RECORDED':
            print(f'  X {var}: NOT RECORDED')
        else:
            print(f'  O {var}: {agent_val}')

print('\n' + '='*70)
print('  완료')
print('='*70)
