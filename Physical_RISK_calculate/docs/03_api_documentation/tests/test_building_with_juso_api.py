"""
도로명주소 API로 정확한 지번 찾기

국토교통부 도로명주소 API 사용
"""

import os
import requests
from dotenv import load_dotenv
import json

load_dotenv()
API_KEY = os.getenv('PUBLICDATA_API_KEY')

def search_juso(api_key, keyword):
    """
    도로명주소 API - 주소 검색
    """
    url = "http://www.juso.go.kr/addrlink/addrLinkApi.do"
    
    params = {
        'confmKey': api_key,
        'currentPage': '1',
        'countPerPage': '10',
        'keyword': keyword,
        'resultType': 'json'
    }
    
    try:
        response = requests.get(url, params=params, timeout=30)
        print(f"\n{'='*80}")
        print(f"[주소 검색: {keyword}]")
        print(f"{'='*80}")
        print(f"응답 코드: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            
            # 결과 확인
            common = result.get('results', {}).get('common', {})
            total_count = int(common.get('totalCount', 0))
            
            print(f"검색 결과: {total_count}건")
            
            if total_count > 0:
                juso_list = result.get('results', {}).get('juso', [])
                
                for idx, juso in enumerate(juso_list[:5], 1):
                    print(f"\n--- 주소 {idx} ---")
                    print(f"도로명주소: {juso.get('roadAddr', '-')}")
                    print(f"지번주소: {juso.get('jibunAddr', '-')}")
                    print(f"상세건물명: {juso.get('bdNm', '-')}")
                    print(f"시군구코드: {juso.get('sigunguCd', '-')}")
                    print(f"법정동코드: {juso.get('bcode', '-')}")
                    print(f"법정동명: {juso.get('bdongNm', '-')}")
                    print(f"건물본번: {juso.get('buldMnnm', '-')}")
                    print(f"건물부번: {juso.get('buldSlno', '-')}")
                    print(f"지번본번: {juso.get('lnbrMnnm', '-')}")
                    print(f"지번부번: {juso.get('lnbrSlno', '-')}")
                    
                return juso_list
            else:
                print("검색 결과가 없습니다.")
                return []
        else:
            print(f"❌ HTTP 오류: {response.text}")
            return []
            
    except Exception as e:
        print(f"❌ 예외 발생: {str(e)}")
        return []

def get_building_info(api_key, sigungu_cd, bjdong_cd, bun, ji):
    """
    건축물대장 정보 조회
    """
    url = "http://apis.data.go.kr/1613000/BldRgstHubService/getBrTitleInfo"
    
    params = {
        'serviceKey': api_key,
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
        print(f"\n[건축물대장 조회]")
        print(f"시군구코드: {sigungu_cd}, 법정동코드: {bjdong_cd}, 번: {bun}, 지: {ji}")
        print(f"응답 코드: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            header = result.get('response', {}).get('header', {})
            
            if header.get('resultCode') == '00':
                items = result.get('response', {}).get('body', {}).get('items', {})
                total_count = result.get('response', {}).get('body', {}).get('totalCount', 0)
                
                print(f"✅ 건축물 {total_count}건 조회")
                
                if items and 'item' in items:
                    item_list = items['item']
                    if not isinstance(item_list, list):
                        item_list = [item_list]
                    
                    for idx, item in enumerate(item_list[:3], 1):
                        print(f"\n  건물 {idx}:")
                        print(f"  - 건물명: {item.get('bldNm', '-')}")
                        print(f"  - 구조: {item.get('strctCdNm', '-')}")
                        print(f"  - 용도: {item.get('mainPurpsCdNm', '-')}")
                        print(f"  - 연면적: {item.get('totArea', '-')}㎡")
                        print(f"  - 층수: 지상{item.get('grndFlrCnt', '-')}/지하{item.get('ugrndFlrCnt', '-')}")
                
                return total_count > 0
            else:
                print(f"❌ API 오류: {header.get('resultMsg', 'Unknown')}")
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
    
    print("도로명주소 → 지번주소 → 건축물대장 조회 테스트")
    print(f"API KEY: {API_KEY[:10]}...\n")
    
    # 테스트 1: 대전광역시 유성구 엑스포로 325
    print("\n" + "="*80)
    print("테스트 1: 대전광역시 유성구 엑스포로 325")
    print("="*80)
    
    juso_list_1 = search_juso(API_KEY, "대전광역시 유성구 엑스포로 325")
    
    if juso_list_1:
        juso = juso_list_1[0]
        sigungu_cd = juso.get('sigunguCd', '')
        # bcode는 10자리 (시군구코드 5자리 + 법정동코드 5자리)
        bcode = juso.get('bcode', '')
        bjdong_cd = bcode[5:] if len(bcode) >= 10 else ''
        bun = juso.get('lnbrMnnm', '0')
        ji = juso.get('lnbrSlno', '0')
        
        print(f"\n추출된 코드:")
        print(f"시군구코드: {sigungu_cd}")
        print(f"법정동코드: {bjdong_cd} (bcode: {bcode})")
        print(f"번: {bun}, 지: {ji}")
        
        if sigungu_cd and bjdong_cd:
            get_building_info(API_KEY, sigungu_cd, bjdong_cd, bun, ji)
    
    # 테스트 2: 경기도 성남시 분당구 판교로 255번길 38
    print("\n" + "="*80)
    print("테스트 2: 경기도 성남시 분당구 판교로 255번길 38")
    print("="*80)
    
    juso_list_2 = search_juso(API_KEY, "경기도 성남시 분당구 판교로 255번길 38")
    
    if juso_list_2:
        juso = juso_list_2[0]
        sigungu_cd = juso.get('sigunguCd', '')
        bcode = juso.get('bcode', '')
        bjdong_cd = bcode[5:] if len(bcode) >= 10 else ''
        bun = juso.get('lnbrMnnm', '0')
        ji = juso.get('lnbrSlno', '0')
        
        print(f"\n추출된 코드:")
        print(f"시군구코드: {sigungu_cd}")
        print(f"법정동코드: {bjdong_cd} (bcode: {bcode})")
        print(f"번: {bun}, 지: {ji}")
        
        if sigungu_cd and bjdong_cd:
            get_building_info(API_KEY, sigungu_cd, bjdong_cd, bun, ji)
    
    print("\n" + "="*80)
    print("테스트 완료")
    print("="*80)
