"""
SK 데이터센터 건축물대장 조회

알려진 주소:
1. 판교 데이터센터: 경기도 성남시 분당구 판교로 
2. 대덕 데이터센터: 대전광역시 유성구 (대덕연구개발특구)
"""

import os
import requests
from dotenv import load_dotenv

load_dotenv()
API_KEY = os.getenv('PUBLICDATA_API_KEY')
VWORLD_KEY = os.getenv('VWORLD_API_KEY')

def search_address_vworld(keyword):
    """V-World로 주소 검색"""
    url = "https://api.vworld.kr/req/search"
    
    params = {
        'service': 'search',
        'request': 'search',
        'version': '2.0',
        'crs': 'EPSG:4326',
        'size': '10',
        'page': '1',
        'query': keyword,
        'type': 'ADDRESS',
        'format': 'json',
        'errorformat': 'json',
        'key': VWORLD_KEY
    }
    
    try:
        response = requests.get(url, params=params, timeout=30)
        print(f"\n{'='*80}")
        print(f"[V-World 검색: {keyword}]")
        print(f"{'='*80}")
        
        if response.status_code == 200:
            result = response.json()
            if result.get('response', {}).get('status') == 'OK':
                items = result.get('response', {}).get('result', {}).get('items', [])
                total = result.get('response', {}).get('result', {}).get('total', 0)
                
                print(f"✅ 검색 결과: {total}건\n")
                
                addresses = []
                for idx, item in enumerate(items[:5], 1):
                    road_addr = item.get('address', {}).get('road', '-')
                    jibun_addr = item.get('address', {}).get('parcel', '-')
                    
                    print(f"{idx}. 도로명: {road_addr}")
                    print(f"   지번: {jibun_addr}\n")
                    
                    addresses.append({
                        'road': road_addr,
                        'jibun': jibun_addr
                    })
                
                return addresses
            else:
                print(f"검색 실패")
                return []
    except Exception as e:
        print(f"오류: {str(e)}")
        return []

def get_building_info(name, sigungu_cd, bjdong_cd, bun, ji):
    """건축물대장 조회"""
    url = "http://apis.data.go.kr/1613000/BldRgstHubService/getBrTitleInfo"
    
    params = {
        'serviceKey': API_KEY,
        'sigunguCd': sigungu_cd,
        'bjdongCd': bjdong_cd,
        'bun': str(bun).zfill(4),
        'ji': str(ji).zfill(4),
        'numOfRows': '10',
        '_type': 'json'
    }
    
    try:
        response = requests.get(url, params=params, timeout=30)
        print(f"\n{'='*80}")
        print(f"[{name}]")
        print(f"{'='*80}")
        print(f"지번 코드: {sigungu_cd}-{bjdong_cd} {bun}-{ji}")
        
        if response.status_code == 200:
            result = response.json()
            header = result.get('response', {}).get('header', {})
            
            if header.get('resultCode') == '00':
                body = result.get('response', {}).get('body', {})
                total = body.get('totalCount', 0)
                if isinstance(total, str):
                    total = int(total) if total.isdigit() else 0
                
                print(f"✅ 건축물 {total}건 조회\n")
                
                if total > 0:
                    items = body.get('items', {}).get('item', [])
                    if not isinstance(items, list):
                        items = [items]
                    
                    for idx, item in enumerate(items[:5], 1):
                        print(f"건물 {idx}:")
                        print(f"  대지위치: {item.get('platPlc', '-')}")
                        print(f"  도로명: {item.get('newPlatPlc', '-')}")
                        print(f"  건물명: {item.get('bldNm', '-')}")
                        print(f"  용도: {item.get('mainPurpsCdNm', '-')}")
                        print(f"  구조: {item.get('strctCdNm', '-')}")
                        print(f"  연면적: {item.get('totArea', '-')}㎡")
                        print(f"  층수: 지상{item.get('grndFlrCnt', '-')}/지하{item.get('ugrndFlrCnt', '-')}")
                        print(f"  사용승인: {item.get('useAprDay', '-')}\n")
                    
                    return True
                else:
                    print("⚠️ 건축물 정보 없음\n")
                    return False
            else:
                print(f"❌ API 오류: {header.get('resultMsg', '-')}\n")
                return False
    except Exception as e:
        print(f"❌ 예외: {str(e)}\n")
        return False

if __name__ == "__main__":
    print("="*80)
    print("SK 데이터센터 주소 검색 및 건축물대장 조회")
    print("="*80)
    
    # 알려진 SK 데이터센터 관련 키워드로 검색
    search_keywords = [
        "SK 판교 데이터센터",
        "성남시 분당구 삼평동 SK",
        "대전 유성구 SK 데이터센터",
        "대전 유성구 가정동 SK"
    ]
    
    print("\n[1단계] V-World로 SK 데이터센터 주소 검색")
    
    all_addresses = {}
    for keyword in search_keywords:
        addresses = search_address_vworld(keyword)
        if addresses:
            all_addresses[keyword] = addresses
    
    # 수동으로 알려진 주소 시도
    print(f"\n\n{'='*80}")
    print("[2단계] 알려진 주소로 건축물대장 조회 시도")
    print("="*80)
    
    test_cases = [
        # 판교 일대 (SK C&C, SK텔레콤 등이 있는 지역)
        {
            'name': '성남시 분당구 삼평동 680 (네이버 그린팩토리 인근)',
            'sigungu_cd': '41135',
            'bjdong_cd': '11000',
            'bun': '680',
            'ji': '0'
        },
        {
            'name': '성남시 분당구 삼평동 686',
            'sigungu_cd': '41135',
            'bjdong_cd': '11000',
            'bun': '686',
            'ji': '0'
        },
        {
            'name': '성남시 분당구 삼평동 681',
            'sigungu_cd': '41135',
            'bjdong_cd': '11000',
            'bun': '681',
            'ji': '0'
        },
        # 대전 유성구 (대덕연구단지)
        {
            'name': '대전 유성구 가정동 35',
            'sigungu_cd': '30200',
            'bjdong_cd': '10600',
            'bun': '35',
            'ji': '0'
        },
        {
            'name': '대전 유성구 가정동 36',
            'sigungu_cd': '30200',
            'bjdong_cd': '10600',
            'bun': '36',
            'ji': '0'
        },
    ]
    
    success_count = 0
    for case in test_cases:
        if get_building_info(
            case['name'],
            case['sigungu_cd'],
            case['bjdong_cd'],
            case['bun'],
            case['ji']
        ):
            success_count += 1
    
    print("="*80)
    print(f"결과: {success_count}/{len(test_cases)} 건 조회 성공")
    print("="*80)
    
    if success_count == 0:
        print("\n💡 참고:")
        print("- DART API로 정확한 사업장 주소를 확인하는 것이 좋습니다")
        print("- 또는 SK 홈페이지/지도 서비스에서 정확한 주소 확인 필요")
