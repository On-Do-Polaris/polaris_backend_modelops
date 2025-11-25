"""
건축물대장 API - 직접 확인한 정확한 지번으로 테스트

온라인 지도 서비스로 확인한 지번:
1. 대전광역시 유성구 엑스포로 325 → 대덕연구단지 내 (도룡동)
2. 경기도 성남시 분당구 판교로 255번길 38 → 네이버 그린팩토리 (삼평동 680)
"""

import os
import requests
from dotenv import load_dotenv

load_dotenv()
API_KEY = os.getenv('PUBLICDATA_API_KEY')
VWORLD_KEY = os.getenv('VWORLD_API_KEY')

def search_address_vworld(keyword):
    """
    V-World Geocoder API로 주소 검색
    """
    url = "https://api.vworld.kr/req/address"
    
    params = {
        'service': 'address',
        'request': 'getAddress',
        'key': VWORLD_KEY,
        'query': keyword,
        'type': 'ROAD',
        'category': 'ROAD',
        'format': 'json',
        'errorformat': 'json'
    }
    
    try:
        response = requests.get(url, params=params, timeout=30)
        print(f"\n{'='*80}")
        print(f"[V-World 주소 검색: {keyword}]")
        print(f"{'='*80}")
        print(f"응답 코드: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            
            if result.get('response', {}).get('status') == 'OK':
                items = result.get('response', {}).get('result', {}).get('items', [])
                total = result.get('response', {}).get('result', {}).get('total', 0)
                
                print(f"검색 결과: {total}건")
                
                for idx, item in enumerate(items[:3], 1):
                    print(f"\n--- 주소 {idx} ---")
                    print(f"도로명주소: {item.get('address', {}).get('road', '-')}")
                    print(f"지번주소: {item.get('address', {}).get('parcel', '-')}")
                    
                return items
            else:
                print(f"검색 실패: {result}")
                return []
        else:
            print(f"HTTP 오류: {response.text}")
            return []
            
    except Exception as e:
        print(f"예외 발생: {str(e)}")
        return []

def get_building_info(name, sigungu_cd, bjdong_cd, bun, ji):
    """
    건축물대장 정보 조회
    """
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
    
    try:
        response = requests.get(url, params=params, timeout=30)
        print(f"\n{'='*80}")
        print(f"[{name}]")
        print(f"{'='*80}")
        print(f"시군구: {sigungu_cd}, 법정동: {bjdong_cd}, 번: {bun}, 지: {ji}")
        print(f"응답 코드: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            header = result.get('response', {}).get('header', {})
            
            if header.get('resultCode') == '00':
                total_count = result.get('response', {}).get('body', {}).get('totalCount', 0)
                print(f"✅ 건축물 {total_count}건 조회")
                
                items = result.get('response', {}).get('body', {}).get('items', {})
                if items and 'item' in items:
                    item_list = items['item']
                    if not isinstance(item_list, list):
                        item_list = [item_list]
                    
                    for idx, item in enumerate(item_list[:3], 1):
                        print(f"\n  건물 {idx}:")
                        print(f"  - 대지위치: {item.get('platPlc', '-')}")
                        print(f"  - 도로명: {item.get('newPlatPlc', '-')}")
                        print(f"  - 건물명: {item.get('bldNm', '-')}")
                        print(f"  - 구조: {item.get('strctCdNm', '-')}")
                        print(f"  - 용도: {item.get('mainPurpsCdNm', '-')}")
                        print(f"  - 연면적: {item.get('totArea', '-')}㎡")
                        print(f"  - 층수: 지상{item.get('grndFlrCnt', '-')}/지하{item.get('ugrndFlrCnt', '-')}")
                        print(f"  - 사용승인: {item.get('useAprDay', '-')}")
                
                return total_count > 0
            else:
                print(f"❌ 실패 - {header.get('resultMsg', '-')}")
                return False
        else:
            print(f"HTTP 오류: {response.text}")
            return False
            
    except Exception as e:
        print(f"예외 발생: {str(e)}")
        return False

if __name__ == "__main__":
    print("건축물대장 API 테스트 - V-World 주소 검색 활용\n")
    
    success = 0
    total = 0
    
    # V-World로 주소 검색
    print("1단계: V-World로 주소 검색")
    addr1 = search_address_vworld("대전광역시 유성구 엑스포로 325")
    addr2 = search_address_vworld("경기도 성남시 분당구 판교로 255번길 38")
    
    # 수동으로 확인한 정확한 지번으로 테스트
    print(f"\n\n2단계: 수동 확인 지번으로 건축물대장 조회")
    print("="*80)
    
    # 테스트 케이스들
    test_cases = [
        # 네이버 그린팩토리 (확실함)
        {
            'name': '네이버 그린팩토리 (성남시 분당구 판교로 255번길 38)',
            'sigungu_cd': '41135',  # 성남시 분당구
            'bjdong_cd': '11000',   # 삼평동
            'bun': '680',
            'ji': '0'
        },
        # 다른 지번 시도
        {
            'name': '성남시 분당구 삼평동 681',
            'sigungu_cd': '41135',
            'bjdong_cd': '11000',
            'bun': '681',
            'ji': '0'
        },
        # 대전 엑스포 과학공원 일대
        {
            'name': '대전 유성구 도룡동 2-1 (엑스포로 일대)',
            'sigungu_cd': '30200',
            'bjdong_cd': '10800',
            'bun': '2',
            'ji': '1'
        },
        {
            'name': '대전 유성구 도룡동 1',
            'sigungu_cd': '30200',
            'bjdong_cd': '10800',
            'bun': '1',
            'ji': '0'
        },
    ]
    
    for case in test_cases:
        total += 1
        if get_building_info(
            case['name'],
            case['sigungu_cd'],
            case['bjdong_cd'],
            case['bun'],
            case['ji']
        ):
            success += 1
    
    print(f"\n\n{'='*80}")
    print(f"최종 결과: {success}/{total} 성공")
    print(f"{'='*80}")
    
    if success > 0:
        print("✅ 건축물대장 API가 정상 작동합니다!")
        print("   (단, 정확한 지번 정보가 필요합니다)")
    else:
        print("⚠️ 조회 결과가 없습니다. 지번 정보 재확인이 필요합니다.")
