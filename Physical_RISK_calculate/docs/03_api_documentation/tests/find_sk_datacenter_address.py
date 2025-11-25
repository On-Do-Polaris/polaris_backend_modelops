"""
DART API로 SK 데이터센터 주소 찾기

DART API 키 발급: https://opendart.fss.or.kr/
"""

import requests

def search_sk_companies():
    """DART - SK 관련 회사 검색"""
    # DART API는 인증키가 필요하지만, 공개 정보로 SK 데이터센터 주소를 찾아봅니다
    
    print("="*80)
    print("SK 데이터센터 공개 정보 조사")
    print("="*80)
    
    known_addresses = {
        "SK C&C 판교 데이터센터": [
            "경기도 성남시 분당구 대왕판교로 145번길 131",  # SK C&C 판교캠퍼스
            "경기도 성남시 분당구 삼평동 627",
        ],
        "SK텔레콤 판교 사옥": [
            "경기도 성남시 분당구 분당로 151",
            "경기도 성남시 분당구 삼평동 627-1",
        ],
        "SK텔레콤 대덕연구센터": [
            "대전광역시 유성구 가정로 70",
            "대전광역시 유성구 가정동 35",
        ],
        "SK브로드밴드 데이터센터": [
            "경기도 성남시 분당구 판교로 230",
            "경기도 성남시 분당구 삼평동 686",
        ]
    }
    
    print("\n알려진 SK 관련 데이터센터 주소:\n")
    for company, addresses in known_addresses.items():
        print(f"📍 {company}")
        for addr in addresses:
            print(f"   - {addr}")
        print()
    
    return known_addresses

def vworld_search_and_parse(keyword, vworld_key):
    """V-World로 주소 검색 및 지번 추출"""
    url = "https://api.vworld.kr/req/search"
    
    params = {
        'service': 'search',
        'request': 'search',
        'version': '2.0',
        'crs': 'EPSG:4326',
        'size': '5',
        'page': '1',
        'query': keyword,
        'type': 'ADDRESS',
        'format': 'json',
        'key': vworld_key
    }
    
    try:
        response = requests.get(url, params=params, timeout=30)
        if response.status_code == 200:
            result = response.json()
            if result.get('response', {}).get('status') == 'OK':
                items = result.get('response', {}).get('result', {}).get('items', [])
                
                results = []
                for item in items:
                    jibun = item.get('address', {}).get('parcel', '')
                    if jibun:
                        results.append(jibun)
                
                return results
    except:
        pass
    
    return []

def parse_jibun(jibun_address):
    """지번주소에서 시군구코드, 법정동코드, 번, 지 추출 (간단 버전)"""
    # 예: "경기도 성남시 분당구 삼평동 627"
    # 실제로는 법정동코드 매핑 테이블이 필요
    
    codes = {
        # 성남시 분당구
        "성남시 분당구 삼평동": ("41135", "11000"),
        "성남시 분당구 삼평로": ("41135", "11000"),
        
        # 대전 유성구
        "대전광역시 유성구 가정동": ("30200", "10600"),
        "대전 유성구 가정동": ("30200", "10600"),
    }
    
    for key, (sigungu, bjdong) in codes.items():
        if key in jibun_address:
            # 번-지 추출
            parts = jibun_address.split()
            if len(parts) >= 4:
                bun_ji = parts[-1]
                if '-' in bun_ji:
                    bun, ji = bun_ji.split('-')
                else:
                    bun = bun_ji
                    ji = "0"
                
                return sigungu, bjdong, bun, ji
    
    return None, None, None, None

if __name__ == "__main__":
    import os
    from dotenv import load_dotenv
    
    load_dotenv()
    PUBLICDATA_KEY = os.getenv('PUBLICDATA_API_KEY')
    VWORLD_KEY = os.getenv('VWORLD_API_KEY')
    
    # 알려진 주소 출력
    known = search_sk_companies()
    
    # 각 주소를 V-World로 검색
    print("="*80)
    print("V-World로 지번 확인")
    print("="*80 + "\n")
    
    test_addresses = [
        "경기도 성남시 분당구 대왕판교로 145번길 131",
        "경기도 성남시 분당구 삼평동 627",
        "대전광역시 유성구 가정로 70",
        "대전광역시 유성구 가정동 35",
    ]
    
    for addr in test_addresses:
        print(f"\n🔍 {addr}")
        jibun_list = vworld_search_and_parse(addr, VWORLD_KEY)
        
        if jibun_list:
            for jibun in jibun_list[:3]:
                print(f"   → {jibun}")
                
                # 지번 파싱 시도
                sigungu, bjdong, bun, ji = parse_jibun(jibun)
                if sigungu:
                    print(f"      코드: {sigungu}-{bjdong} {bun}-{ji}")
        else:
            print("   ⚠️ 검색 결과 없음")
    
    print("\n" + "="*80)
    print("💡 다음 단계:")
    print("="*80)
    print("""
1. DART API 키 발급 (https://opendart.fss.or.kr/)
2. SK 관련 회사 고유번호 검색:
   - SK텔레콤: 00126380
   - SK C&C: 00164742
   - SK브로드밴드: 00138826
   
3. 사업보고서에서 사업장 주소 추출
4. 해당 주소로 건축물대장 조회

또는 SK 홈페이지/IR자료에서 직접 확인 가능
""")
