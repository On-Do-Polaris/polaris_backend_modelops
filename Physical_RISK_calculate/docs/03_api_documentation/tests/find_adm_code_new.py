"""
SGIS 행정구역 코드 찾기 (행정구역 API 사용)
"""

import os
import requests
from dotenv import load_dotenv

# .env 파일 로드
env_path = os.path.join(os.path.dirname(__file__), '..', '..', '..', '.env')
load_dotenv(env_path)

SGIS_SERVICE_ID = os.getenv('SGIS_SERVICE_ID')
SGIS_SECURITY_KEY = os.getenv('SGIS_SECURITY_KEY')

# 1. 인증 토큰 발급
def get_access_token():
    """SGIS 액세스 토큰 발급"""
    url = "https://sgisapi.kostat.go.kr/OpenAPI3/auth/authentication.json"
    params = {
        'consumer_key': SGIS_SERVICE_ID,
        'consumer_secret': SGIS_SECURITY_KEY
    }
    
    response = requests.get(url, params=params)
    data = response.json()
    
    if data.get('errCd') == 0:
        return data['result']['accessToken']
    else:
        print(f"토큰 발급 실패: {data}")
        return None

# 2. 행정구역 코드 조회 (SGIS 행정구역 API)
def search_area_code(access_token, cd=''):
    """행정구역 코드 조회 (cd: 상위 행정구역 코드)"""
    url = "https://sgisapi.kostat.go.kr/OpenAPI3/addr/stage.json"
    
    params = {
        'accessToken': access_token
    }
    
    if cd:
        params['cd'] = cd
    
    response = requests.get(url, params=params)
    data = response.json()
    
    if response.status_code == 200 and data.get('errCd') == 0:
        results = data.get('result', [])
        return results
    else:
        print(f"✗ 조회 실패: {data}")
        return []

def main():
    print("=" * 100)
    print("SGIS 행정구역 코드 조회")
    print("=" * 100)
    
    # 토큰 발급
    access_token = get_access_token()
    if not access_token:
        return
    
    # 1. 시도 목록 조회 (전국)
    print("\n[1] 시도 목록 조회 (전국)")
    print("-" * 100)
    sido_list = search_area_code(access_token)
    print(f"✓ 조회 성공 ({len(sido_list)}건)")
    for item in sido_list:
        print(f"  코드: {item.get('cd'):<15} | 이름: {item.get('addr_name')}")
    
    # 2. 서울특별시 시군구 목록 조회
    seoul = next((item for item in sido_list if '서울' in item.get('addr_name', '')), None)
    if seoul:
        seoul_cd = seoul['cd']
        print(f"\n[2] 서울특별시 시군구 목록 조회 (코드: {seoul_cd})")
        print("-" * 100)
        seoul_gu = search_area_code(access_token, cd=seoul_cd)
        print(f"✓ 조회 성공 ({len(seoul_gu)}건)")
        for item in seoul_gu:
            if '종로구' in item.get('addr_name', '') or '강남구' in item.get('addr_name', ''):
                print(f"  코드: {item.get('cd'):<15} | 이름: {item.get('addr_name')} ★")
            else:
                print(f"  코드: {item.get('cd'):<15} | 이름: {item.get('addr_name')}")
        
        # 3. 서울 종로구 읍면동 목록 조회
        jongro = next((item for item in seoul_gu if '종로구' in item.get('addr_name', '')), None)
        if jongro:
            jongro_cd = jongro['cd']
            print(f"\n[3] 서울 종로구 읍면동 목록 조회 (코드: {jongro_cd})")
            print("-" * 100)
            jongro_dong = search_area_code(access_token, cd=jongro_cd)
            print(f"✓ 조회 성공 ({len(jongro_dong)}건)")
            for item in jongro_dong:
                if '종로' in item.get('addr_name', '') or '서린' in item.get('addr_name', ''):
                    print(f"  코드: {item.get('cd'):<15} | 이름: {item.get('addr_name')} ★")
                else:
                    print(f"  코드: {item.get('cd'):<15} | 이름: {item.get('addr_name')}")
        
        # 4. 서울 강남구 읍면동 목록 조회
        gangnam = next((item for item in seoul_gu if '강남구' in item.get('addr_name', '')), None)
        if gangnam:
            gangnam_cd = gangnam['cd']
            print(f"\n[4] 서울 강남구 읍면동 목록 조회 (코드: {gangnam_cd})")
            print("-" * 100)
            gangnam_dong = search_area_code(access_token, cd=gangnam_cd)
            print(f"✓ 조회 성공 ({len(gangnam_dong)}건)")
            for item in gangnam_dong:
                if '삼성' in item.get('addr_name', ''):
                    print(f"  코드: {item.get('cd'):<15} | 이름: {item.get('addr_name')} ★")
                else:
                    print(f"  코드: {item.get('cd'):<15} | 이름: {item.get('addr_name')}")
    
    # 5. 대전광역시 시군구 목록 조회
    daejeon = next((item for item in sido_list if '대전' in item.get('addr_name', '')), None)
    if daejeon:
        daejeon_cd = daejeon['cd']
        print(f"\n[5] 대전광역시 시군구 목록 조회 (코드: {daejeon_cd})")
        print("-" * 100)
        daejeon_gu = search_area_code(access_token, cd=daejeon_cd)
        print(f"✓ 조회 성공 ({len(daejeon_gu)}건)")
        for item in daejeon_gu:
            if '유성구' in item.get('addr_name', ''):
                print(f"  코드: {item.get('cd'):<15} | 이름: {item.get('addr_name')} ★")
            else:
                print(f"  코드: {item.get('cd'):<15} | 이름: {item.get('addr_name')}")
        
        # 6. 대전 유성구 읍면동 목록 조회
        yuseong = next((item for item in daejeon_gu if '유성구' in item.get('addr_name', '')), None)
        if yuseong:
            yuseong_cd = yuseong['cd']
            print(f"\n[6] 대전 유성구 읍면동 목록 조회 (코드: {yuseong_cd})")
            print("-" * 100)
            yuseong_dong = search_area_code(access_token, cd=yuseong_cd)
            print(f"✓ 조회 성공 ({len(yuseong_dong)}건)")
            for item in yuseong_dong:
                if '원촌' in item.get('addr_name', ''):
                    print(f"  코드: {item.get('cd'):<15} | 이름: {item.get('addr_name')} ★")
                else:
                    print(f"  코드: {item.get('cd'):<15} | 이름: {item.get('addr_name')}")

if __name__ == "__main__":
    main()
