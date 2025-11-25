"""
건축물대장 API - 특정 주소 테스트 스크립트

테스트 주소:
1. 대전광역시 유성구 엑스포로 325
2. 경기도 성남시 분당구 판교로 255번길 38
"""

import os
import requests
from dotenv import load_dotenv
import json

load_dotenv()
API_KEY = os.getenv('PUBLICDATA_API_KEY')

def get_jibun_from_road_address(api_key, road_address):
    """
    주소검색(도로명 -> 지번) API
    공공데이터포털의 주소검색 API 사용
    """
    url = "http://apis.data.go.kr/1611000/nsdi/emd/addr/road/list"
    
    params = {
        'serviceKey': api_key,
        'keyword': road_address,
        'returnType': 'json',
        'pageNo': '1',
        'numOfRows': '10'
    }
    
    try:
        response = requests.get(url, params=params, timeout=30)
        print(f"\n[도로명주소 -> 지번주소 변환]")
        print(f"요청 URL: {response.url}")
        print(f"응답 코드: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"응답 내용:\n{json.dumps(result, indent=2, ensure_ascii=False)}")
            return result
        else:
            print(f"오류: {response.text}")
            return None
            
    except Exception as e:
        print(f"예외 발생: {str(e)}")
        return None

def get_building_register_info(api_key, sigungu_cd, bjdong_cd, bun, ji):
    """
    건축물대장 정보 조회
    """
    url = "http://apis.data.go.kr/1613000/BldRgstHubService/getBrTitleInfo"
    
    params = {
        'serviceKey': api_key,
        'sigunguCd': sigungu_cd,
        'bjdongCd': bjdong_cd,
        'bun': bun.zfill(4),  # 4자리로 패딩
        'ji': ji.zfill(4),    # 4자리로 패딩
        'numOfRows': '10',
        'pageNo': '1',
        '_type': 'json'
    }
    
    try:
        response = requests.get(url, params=params, timeout=30)
        print(f"\n[건축물대장 정보 조회]")
        print(f"시군구코드: {sigungu_cd}, 법정동코드: {bjdong_cd}, 번: {bun}, 지: {ji}")
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
                    for idx, item in enumerate(items['item'][:3], 1):  # 최대 3건만 출력
                        print(f"\n--- 건물 {idx} ---")
                        print(f"대지위치: {item.get('platPlc', '-')}")
                        print(f"도로명주소: {item.get('newPlatPlc', '-')}")
                        print(f"건물명: {item.get('bldNm', '-')}")
                        print(f"건물구조: {item.get('strctCdNm', '-')}")
                        print(f"주용도: {item.get('mainPurpsCdNm', '-')}")
                        print(f"연면적: {item.get('totArea', '-')}㎡")
                        print(f"지상층수: {item.get('grndFlrCnt', '-')}층")
                        print(f"지하층수: {item.get('ugrndFlrCnt', '-')}층")
                        print(f"사용승인일: {item.get('useAprDay', '-')}")
                else:
                    print("⚠️ 조회된 건물이 없습니다.")
            else:
                print(f"❌ 실패 - {header.get('resultMsg', 'Unknown error')}")
            
            return result
        else:
            print(f"❌ HTTP 오류: {response.text}")
            return None
            
    except Exception as e:
        print(f"❌ 예외 발생: {str(e)}")
        return None

def test_with_known_codes():
    """
    알려진 코드로 먼저 테스트 (API 동작 확인)
    서울특별시 종로구 청운동 1번지
    """
    print("="*80)
    print("테스트 1: 알려진 주소로 API 동작 확인")
    print("="*80)
    
    # 서울 종로구 청운동
    sigungu_cd = "11110"  # 종로구
    bjdong_cd = "10100"   # 청운동
    bun = "0001"
    ji = "0000"
    
    result = get_building_register_info(API_KEY, sigungu_cd, bjdong_cd, bun, ji)
    return result is not None

def test_target_addresses():
    """
    목표 주소 테스트
    
    주의: 도로명주소 -> 지번주소 변환이 필요
    현재는 수동으로 지번 정보를 입력해야 합니다.
    """
    print("\n" + "="*80)
    print("테스트 2: 목표 주소 - 대전광역시 유성구 엑스포로 325")
    print("="*80)
    
    # 대전광역시 유성구 도룡동 (추정)
    # 실제 지번 정보는 주소검색 API나 수동 조회 필요
    print("⚠️ 도로명주소를 지번주소로 변환이 필요합니다.")
    print("대전 유성구 엑스포로 325 → 지번주소 확인 필요")
    
    # 도로명 -> 지번 변환 시도
    get_jibun_from_road_address(API_KEY, "대전광역시 유성구 엑스포로 325")
    
    print("\n" + "="*80)
    print("테스트 3: 목표 주소 - 경기도 성남시 분당구 판교로 255번길 38")
    print("="*80)
    
    print("⚠️ 도로명주소를 지번주소로 변환이 필요합니다.")
    print("성남시 분당구 판교로 255번길 38 → 지번주소 확인 필요")
    
    # 도로명 -> 지번 변환 시도
    get_jibun_from_road_address(API_KEY, "경기도 성남시 분당구 판교로 255번길 38")
    
    # 수동으로 지번 정보를 찾은 경우 테스트
    print("\n--- 수동 입력 지번 정보로 테스트 ---")
    
    # 대전 엑스포로 325 (예: 도룡동 일대)
    # 실제 코드는 확인 필요
    print("\n1) 대전 유성구 - 추정 지번으로 시도")
    # sigungu_cd = "30200"  # 대전 유성구
    # bjdong_cd = "10800"   # 도룡동 (예시)
    # get_building_register_info(API_KEY, sigungu_cd, bjdong_cd, "????", "????")
    
    print("→ 정확한 지번 정보가 필요합니다.")
    
    # 성남 분당구 판교로 255번길 38
    print("\n2) 성남 분당구 - 추정 지번으로 시도")
    # sigungu_cd = "41135"  # 성남시 분당구
    # bjdong_cd = "11000"   # 삼평동 (예시)
    # get_building_register_info(API_KEY, sigungu_cd, bjdong_cd, "????", "????")
    
    print("→ 정확한 지번 정보가 필요합니다.")

if __name__ == "__main__":
    if not API_KEY:
        print("❌ PUBLICDATA_API_KEY가 .env 파일에 설정되지 않았습니다.")
        exit(1)
    
    print("건축물대장 API 테스트 시작")
    print(f"API KEY: {API_KEY[:10]}...")
    
    # 1. 알려진 주소로 API 동작 확인
    api_works = test_with_known_codes()
    
    # 2. 목표 주소 테스트
    if api_works:
        test_target_addresses()
    
    print("\n" + "="*80)
    print("테스트 완료")
    print("="*80)
    print("\n📝 참고사항:")
    print("- 건축물대장 API는 '지번주소' 기반입니다 (sigunguCd, bjdongCd, bun, ji)")
    print("- 도로명주소를 사용하려면 별도의 주소검색 API로 지번 변환이 필요합니다.")
    print("- 네이버/카카오 주소 API 또는 행정안전부 주소 API를 사용할 수 있습니다.")
    print("- 혹은 https://www.juso.go.kr 에서 수동으로 지번을 확인할 수 있습니다.")
