"""
건축물대장 API - 실제 지번으로 테스트

웹에서 수동 확인한 지번 정보:
1. 대전광역시 유성구 엑스포로 325 → 대전광역시 유성구 도룡동 3-3
2. 경기도 성남시 분당구 판교로 255번길 38 → 경기도 성남시 분당구 삼평동 680
"""

import os
import requests
from dotenv import load_dotenv
import json

load_dotenv()
API_KEY = os.getenv('PUBLICDATA_API_KEY')

def get_building_register_info(api_key, address_name, sigungu_cd, bjdong_cd, bun, ji):
    """
    건축물대장 정보 조회
    """
    url = "http://apis.data.go.kr/1613000/BldRgstHubService/getBrTitleInfo"
    
    # 번/지를 4자리로 패딩
    bun_padded = str(bun).zfill(4)
    ji_padded = str(ji).zfill(4)
    
    params = {
        'serviceKey': api_key,
        'sigunguCd': sigungu_cd,
        'bjdongCd': bjdong_cd,
        'bun': bun_padded,
        'ji': ji_padded,
        'numOfRows': '10',
        'pageNo': '1',
        '_type': 'json'
    }
    
    try:
        response = requests.get(url, params=params, timeout=30)
        print(f"\n{'='*80}")
        print(f"[{address_name}]")
        print(f"{'='*80}")
        print(f"시군구코드: {sigungu_cd}, 법정동코드: {bjdong_cd}, 번: {bun_padded}, 지: {ji_padded}")
        print(f"응답 코드: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            
            # 성공 여부 확인
            header = result.get('response', {}).get('header', {})
            if header.get('resultCode') == '00':
                items = result.get('response', {}).get('body', {}).get('items', {})
                total_count = result.get('response', {}).get('body', {}).get('totalCount', 0)
                
                print(f"✅ 성공 - 총 {total_count}건 조회")
                
                if items and 'item' in items:
                    item_list = items['item']
                    if not isinstance(item_list, list):
                        item_list = [item_list]
                    
                    for idx, item in enumerate(item_list[:5], 1):  # 최대 5건 출력
                        print(f"\n--- 건물 {idx} ---")
                        print(f"대지위치(지번): {item.get('platPlc', '-')}")
                        print(f"도로명주소: {item.get('newPlatPlc', '-')}")
                        print(f"건물명: {item.get('bldNm', '-')}")
                        print(f"동명칭: {item.get('dongNm', '-')}")
                        print(f"건물구조: {item.get('strctCdNm', '-')}")
                        print(f"주용도: {item.get('mainPurpsCdNm', '-')}")
                        print(f"연면적: {item.get('totArea', '-')}㎡")
                        print(f"지상층수: {item.get('grndFlrCnt', '-')}층")
                        print(f"지하층수: {item.get('ugrndFlrCnt', '-')}층")
                        print(f"허가일: {item.get('pmsDay', '-')}")
                        print(f"사용승인일: {item.get('useAprDay', '-')}")
                else:
                    print("⚠️ 조회된 건물이 없습니다.")
                
                return True
            else:
                print(f"❌ 실패 - {header.get('resultMsg', 'Unknown error')}")
                return False
        else:
            print(f"❌ HTTP 오류: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ 예외 발생: {str(e)}")
        return False

if __name__ == "__main__":
    if not API_KEY:
        print("❌ PUBLICDATA_API_KEY가 .env 파일에 설정되지 않았습니다.")
        exit(1)
    
    print("건축물대장 API - 실제 주소 테스트")
    print(f"API KEY: {API_KEY[:10]}...\n")
    
    success_count = 0
    total_count = 0
    
    # 테스트 1: 대전광역시 유성구 도룡동 3-3 (엑스포로 325)
    total_count += 1
    if get_building_register_info(
        api_key=API_KEY,
        address_name="대전광역시 유성구 엑스포로 325 (도룡동 3-3)",
        sigungu_cd="30200",  # 대전 유성구
        bjdong_cd="10800",   # 도룡동
        bun="3",
        ji="3"
    ):
        success_count += 1
    
    # 테스트 2: 경기도 성남시 분당구 삼평동 680 (판교로 255번길 38)
    total_count += 1
    if get_building_register_info(
        api_key=API_KEY,
        address_name="경기도 성남시 분당구 판교로 255번길 38 (삼평동 680)",
        sigungu_cd="41135",  # 성남시 분당구
        bjdong_cd="11000",   # 삼평동
        bun="680",
        ji="0"
    ):
        success_count += 1
    
    # 최종 결과
    print(f"\n{'='*80}")
    print(f"최종 결과: {success_count}/{total_count} 성공")
    print(f"{'='*80}")
    
    if success_count == total_count:
        print("✅ 모든 주소에서 건축물대장 API가 정상 작동합니다!")
    else:
        print("⚠️ 일부 주소에서 조회 실패 - 지번 정보 확인이 필요합니다.")
    
    print("\n📌 참고:")
    print("- 지번 정보는 https://www.juso.go.kr 에서 확인 가능합니다.")
    print("- 시군구코드/법정동코드는 행정표준코드관리시스템에서 확인 가능합니다.")
