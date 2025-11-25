"""
건축물대장 API - V-World에서 찾은 정확한 지번으로 테스트

V-World 검색 결과:
1. 대전광역시 유성구 엑스포로 325 → 원촌동 140-1
2. 경기도 성남시 분당구 판교로 255번길 38 → 삼평동 612-4
"""

import os
import requests
from dotenv import load_dotenv

load_dotenv()
API_KEY = os.getenv('PUBLICDATA_API_KEY')

def get_building(name, sigungu_cd, bjdong_cd, bun, ji):
    url = "http://apis.data.go.kr/1613000/BldRgstHubService/getBrTitleInfo"
    params = {
        'serviceKey': API_KEY,
        'sigunguCd': sigungu_cd,
        'bjdongCd': bjdong_cd,
        'bun': str(bun).zfill(4),
        'ji': str(ji).zfill(4),
        'numOfRows': '10',
        'pageNo': '1',
        '_type': 'json'
    }
    
    response = requests.get(url, params=params, timeout=30)
    print(f"\n{'='*80}")
    print(f"{name}")
    print(f"{'='*80}")
    print(f"지번코드: {sigungu_cd}-{bjdong_cd} {bun}-{ji}")
    print(f"응답 코드: {response.status_code}")
    
    if response.status_code == 200:
        result = response.json()
        header = result.get('response', {}).get('header', {})
        
        if header.get('resultCode') == '00':
            body = result.get('response', {}).get('body', {})
            total_count = body.get('totalCount', 0)
            
            # 문자열을 정수로 변환
            if isinstance(total_count, str):
                total_count = int(total_count) if total_count.isdigit() else 0
            
            print(f"✅ 건축물 {total_count}건 조회")
            
            if total_count > 0:
                items = body.get('items', {}).get('item', [])
                if not isinstance(items, list):
                    items = [items]
                
                for idx, item in enumerate(items[:3], 1):
                    print(f"\n  건물 {idx}:")
                    print(f"    대지위치: {item.get('platPlc', '-')}")
                    print(f"    도로명주소: {item.get('newPlatPlc', '-')}")
                    print(f"    건물명: {item.get('bldNm', '(없음)')}")
                    print(f"    건물구조: {item.get('strctCdNm', '-')}")
                    print(f"    주용도: {item.get('mainPurpsCdNm', '-')}")
                    print(f"    연면적: {item.get('totArea', '-')}㎡")
                    print(f"    층수: 지상{item.get('grndFlrCnt', '-')}/지하{item.get('ugrndFlrCnt', '-')}")
                    print(f"    사용승인일: {item.get('useAprDay', '-')}")
                
                return True
            else:
                print("  ⚠️ 해당 지번에 등록된 건물이 없습니다.")
                return False
        else:
            print(f"❌ API 오류: {header.get('resultMsg', 'Unknown')}")
            return False
    else:
        print(f"❌ HTTP 오류: {response.status_code}")
        return False

if __name__ == "__main__":
    print("건축물대장 API - V-World에서 찾은 정확한 지번으로 테스트")
    print(f"API KEY: {API_KEY[:10]}...\n")
    
    success_count = 0
    total_count = 2
    
    # 테스트 1: 대전 유성구 원촌동 140-1 (엑스포로 325)
    if get_building(
        "대전광역시 유성구 엑스포로 325 → 원촌동 140-1",
        "30200",  # 대전 유성구
        "12500",  # 원촌동
        "140",
        "1"
    ):
        success_count += 1
    
    # 테스트 2: 성남 분당구 삼평동 612-4 (판교로 255번길 38)
    if get_building(
        "경기도 성남시 분당구 판교로 255번길 38 → 삼평동 612-4",
        "41135",  # 성남시 분당구
        "11000",  # 삼평동
        "612",
        "4"
    ):
        success_count += 1
    
    print(f"\n{'='*80}")
    print(f"최종 결과: {success_count}/{total_count} 성공")
    print(f"{'='*80}")
    
    if success_count == total_count:
        print("\n✅ 요청하신 두 주소 모두 건축물대장 API로 정상 조회되었습니다!")
    elif success_count > 0:
        print(f"\n⚠️ {success_count}개 주소만 조회되었습니다.")
    else:
        print("\n⚠️ 두 주소 모두 건축물대장에 등록되어 있지 않습니다.")
        print("   (건물이 미등록이거나 지번 정보가 정확하지 않을 수 있습니다)")
