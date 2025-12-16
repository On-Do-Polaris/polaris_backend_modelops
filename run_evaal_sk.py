"""SK 사업장 E, V, AAL 계산 스크립트"""
from modelops.batch.evaal_ondemand_api import calculate_evaal_ondemand

# SK 사업장 7개 고유 좌표
SK_COORDS = [
    (37.3825, 127.1220),   # SK u-타워
    (37.405879, 127.099877), # 판교 캠퍼스/데이터센터/애커튼테크
    (37.3820, 127.1250),   # 수내 오피스
    (37.570708, 126.983577), # 서린 사옥
    (36.3728, 127.3590),   # 대덕 데이터 센터
    (37.4858, 126.9302),   # 보라매 데이터 센터
    (37.5712, 126.9837),   # 애커튼 파트너스
]

TARGET_YEARS = [2030, 2050]

print('E, V, AAL 계산 시작')
for target_year in TARGET_YEARS:
    print(f'\n=== {target_year} ===')
    for lat, lon in SK_COORDS:
        print(f'  처리 중: ({lat}, {lon})')
        try:
            result = calculate_evaal_ondemand(
                latitude=lat,
                longitude=lon,
                scenario='SSP245',
                target_year=target_year,
                save_to_db=True
            )
            summary = result.get('summary', {})
            print(f'    완료: E={summary.get("total_exposure_score", 0):.1f}, V={summary.get("total_vulnerability_score", 0):.1f}, AAL={summary.get("total_final_aal", 0):.4f}')
        except Exception as e:
            print(f'    오류: {e}')
print('\n완료!')
