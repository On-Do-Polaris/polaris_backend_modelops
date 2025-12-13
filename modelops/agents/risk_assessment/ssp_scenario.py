# run_integrated_risk_timeseries.py
from .integrated_risk_agent import IntegratedRiskAgent

SCENARIOS = ["SSP126", "SSP245", "SSP370", "SSP585"]
YEARS = range(2021, 2101)

def run_timeseries(latitude: float, longitude: float):
    all_results = {}  # {scenario: {year: result_dict}}

    for scenario in SCENARIOS:
        all_results[scenario] = {}

        for year in YEARS:
            agent = IntegratedRiskAgent(scenario=scenario, target_year=year, database_connection=None)

            # progress_callback은 선택. 필요하면 아래처럼 출력 가능
            def progress_callback(current, total, risk_type):
                print(f"[{scenario} {year}] {current}/{total} {risk_type}")

            result = agent.calculate_all_risks(
                latitude=latitude,
                longitude=longitude,
                progress_callback=progress_callback
            )

            all_results[scenario][year] = result

    return all_results

if __name__ == "__main__":
    # TODO: 여기에 실제 위경도 넣기
    lat, lon = 36.37, 127.36
    results = run_timeseries(lat, lon)

    # 결과 활용 예:
    # results["SSP245"][2030]["summary"]["average_integrated_risk"]
    print("done")
