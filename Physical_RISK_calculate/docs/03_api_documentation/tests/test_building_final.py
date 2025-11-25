"""
건축물대장 API 최종 테스트 결과

테스트 요약:
- API 상태: ✅ 정상 작동
- 검증 방법: 서울 종로구 청운동 1번지로 성공 확인

요청 주소:
1. 대전광역시 유성구 엑스포로 325
2. 경기도 성남시 분당구 판교로 255번길 38

결과: 정확한 지번주소 정보 확인 필요
"""

import os
import requests
from dotenv import load_dotenv

load_dotenv()
API_KEY = os.getenv('PUBLICDATA_API_KEY')
VWORLD_KEY = os.getenv('VWORLD_API_KEY')

def vworld_geocode(keyword):
    """
    V-World Geocoder API - 주소로 좌표 검색
    """
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
        'category': 'ROAD',
        'format': 'json',
        'errorformat': 'json',
        'key': VWORLD_KEY
    }
    
    try:
        response = requests.get(url, params=params, timeout=30)
        print(f"\n[V-World Geocode: {keyword}]")
        print(f"응답 코드: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            
            if result.get('response', {}).get('status') == 'OK':
                items = result.get('response', {}).get('result', {}).get('items', [])
                total = result.get('response', {}).get('result', {}).get('total', 0)
                
                print(f"✅ 검색 결과: {total}건")
                
                for idx, item in enumerate(items[:3], 1):
                    print(f"\n  주소 {idx}:")
                    print(f"  - 제목: {item.get('title', '-')}")
                    print(f"  - 카테고리: {item.get('category', '-')}")
                    print(f"  - 주소: {item.get('address', {}).get('road', '-')}")
                    print(f"  - 지번: {item.get('address', {}).get('parcel', '-')}")
                    
                    point = item.get('point', {})
                    if point:
                        print(f"  - 좌표: {point.get('x', '-')}, {point.get('y', '-')}")
                
                return items
            else:
                error = result.get('response', {}).get('error', {})
                print(f"❌ 오류: {error.get('text', 'Unknown')}")
                return []
        else:
            print(f"❌ HTTP 오류: {response.text}")
            return []
            
    except Exception as e:
        print(f"❌ 예외: {str(e)}")
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
        print(f"시군구: {sigungu_cd}, 법정동: {bjdong_cd}, 번: {bun}, 지: {ji}")
        print(f"{'='*80}")
        
        if response.status_code == 200:
            result = response.json()
            header = result.get('response', {}).get('header', {})
            
            if header.get('resultCode') == '00':
                body = result.get('response', {}).get('body', {})
                total_count = body.get('totalCount', 0)
                
                # totalCount를 정수로 변환
                if isinstance(total_count, str):
                    total_count = int(total_count) if total_count.isdigit() else 0
                
                print(f"✅ 건축물 {total_count}건 조회")
                
                if total_count > 0:
                    items = body.get('items', {})
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
                        
                        return True
                else:
                    print("  ⚠️ 해당 지번에 등록된 건물이 없습니다.")
                    return False
            else:
                print(f"❌ API 오류: {header.get('resultMsg', '-')}")
                return False
        else:
            print(f"❌ HTTP 오류")
            return False
            
    except Exception as e:
        print(f"❌ 예외: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("="*80)
    print("건축물대장 API 최종 테스트")
    print("="*80)
    
    # 1. API 작동 확인 (알려진 주소)
    print("\n[1단계] API 작동 확인")
    success_ref = get_building_info(
        "서울 종로구 청운동 1번지 (참조 테스트)",
        "11110",  # 종로구
        "10100",  # 청운동
        "1",
        "0"
    )
    
    if success_ref:
        print("\n✅ 건축물대장 API는 정상 작동합니다!")
    else:
        print("\n❌ API 작동 실패")
        exit(1)
    
    # 2. V-World로 주소 검색
    print(f"\n\n{'='*80}")
    print("[2단계] 요청 주소 검색 (V-World)")
    print("="*80)
    
    addr1_results = vworld_geocode("대전광역시 유성구 엑스포로 325")
    addr2_results = vworld_geocode("경기도 성남시 분당구 판교로 255번길 38")
    
    # 3. 건축물대장 조회 (수동 지번)
    print(f"\n\n{'='*80}")
    print("[3단계] 건축물대장 조회 시도")
    print("="*80)
    
    # 네이버 그린팩토리 추정 지번
    get_building_info(
        "경기도 성남시 분당구 삼평동 680 (네이버 그린팩토리 추정)",
        "41135",  # 성남시 분당구
        "11000",  # 삼평동
        "680",
        "0"
    )
    
    # 대전 엑스포 과학공원 추정
    get_building_info(
        "대전광역시 유성구 도룡동 3 (엑스포 과학공원 추정)",
        "30200",  # 대전 유성구
        "10800",  # 도룡동
        "3",
        "0"
    )
    
    # 최종 결론
    print(f"\n\n{'='*80}")
    print("최종 결론")
    print("="*80)
    print("""
✅ 건축물대장 API: 정상 작동 (참조 테스트 성공)

⚠️ 요청하신 주소:
  1. 대전광역시 유성구 엑스포로 325
  2. 경기도 성남시 분당구 판교로 255번길 38

→ 정확한 지번주소 확인 후 재테스트 필요

📝 지번 확인 방법:
  - 네이버/카카오 지도에서 해당 주소 검색
  - 주소 상세정보에서 '지번' 확인
  - 또는 https://www.juso.go.kr 에서 검색

💡 건축물대장 API는 '지번주소' 기반이므로:
  - 시군구코드 (5자리)
  - 법정동코드 (5자리)
  - 번 (본번)
  - 지 (부번)
  이 4가지 정보가 모두 정확해야 조회 가능합니다.
""")
