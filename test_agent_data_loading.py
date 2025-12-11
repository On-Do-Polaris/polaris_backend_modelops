import pprint
from modelops.agents.probability_calculate.drought_probability_agent import DroughtProbabilityAgent

def test_drought_agent():
    """
    DroughtProbabilityAgent가 데이터를 올바르게 처리하는지 테스트합니다.
    """
    print("--- DroughtProbabilityAgent 테스트 시작 ---")

    # 1. 샘플 데이터 준비
    # calculate_intensity_indicator가 요구하는 'collected_data' 구조에 맞춰 생성합니다.
    # Drought 에이전트는 'climate_data' -> 'spei12' 경로의 월별 데이터를 사용합니다.
    sample_collected_data = {
        "climate_data": {
            # 20년간의 월별 SPEI12 샘플 데이터 (총 240개 월)
            # -1 미만: 정상, -1 ~ -1.5: 중간 가뭄, -1.5 ~ -2: 심각 가뭄, -2 이하: 극심 가뭄
            "spei12": [
                0.5, 0.2, -0.1, -0.5, -0.8, -1.1, -1.3, -1.6, -1.8, -2.1, -2.5, -1.2,
                # ... (중간 생략) ...
                *([-0.5] * 100), # 정상 상태 100개월
                *([-1.2] * 80),  # 중간 가뭄 80개월
                *([-1.7] * 40),  # 심각 가뭄 40개월
                *([-2.2] * 8),   # 극심 가뭄 8개월
            ]
        }
    }
    total_months = len(sample_collected_data["climate_data"]["spei12"])
    print(f"총 {total_months}개월 분량의 샘플 데이터를 생성했습니다.")


    # 2. 에이전트 초기화
    drought_agent = DroughtProbabilityAgent()
    print("DroughtProbabilityAgent를 초기화했습니다.")

    # 3. 확률 계산 실행
    print("calculate_probability 함수를 호출하여 계산을 실행합니다...")
    result = drought_agent.calculate_probability(sample_collected_data)
    print("계산 완료.")

    # 4. 결과 출력
    print("\n--- 최종 계산 결과 ---")
    pprint.pprint(result)

    print("\n테스트 완료. 위 결과를 통해 데이터가 의도대로 처리되었는지 확인하세요.")
    # 예: calculation_details.bins[].sample_count 합계가 총 샘플 수(240)와 일치하는지,
    #     bin 별 확률(probability)이 샘플 수 비율과 유사한지 등을 검토할 수 있습니다.

if __name__ == "__main__":
    test_drought_agent()
