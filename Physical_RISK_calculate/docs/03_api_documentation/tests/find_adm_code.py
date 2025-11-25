"""
SGIS 행정구역코드 찾기 도구
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
    url = "https://sgisapi.kostat.go.kr/OpenAPI3/auth/authentication.json"
    params = {
        'consumer_key': SGIS_SERVICE_ID,
        'consumer_secret': SGIS_SECURITY_KEY
    }
    response = requests.get(url, params=params, timeout=10)
    if response.status_code == 200:
        data = response.json()
        if data.get('errCd') == 0:
            return data['result']['accessToken']
    return None

# 2. 대전광역시 시군구 조회
def find_daejeon_districts(access_token):
    url = "https://sgisapi.kostat.go.kr/OpenAPI3/stats/searchpopulation.json"
    params = {
        'accessToken': access_token,
        'year': '2023',
        'adm_cd': '30',  # 대전광역시
        'low_search': '1',  # 1단계 하위 (시군구)
        'gender': '0'
    }
    response = requests.get(url, params=params, timeout=10)
    if response.status_code == 200:
        data = response.json()
        if data.get('errCd') == 0:
            results = data.get('result', [])
            print("대전광역시 시군구:")
            for item in results:
                print(f"  [{item.get('adm_cd')}] {item.get('adm_nm')}: {item.get('population')}명")
            return results
    return []

# 3. 유성구 읍면동 조회
def find_yuseong_dongs(access_token, yuseong_code):
    url = "https://sgisapi.kostat.go.kr/OpenAPI3/stats/searchpopulation.json"
    params = {
        'accessToken': access_token,
        'year': '2023',
        'adm_cd': yuseong_code,  # 유성구 코드
        'low_search': '1',  # 1단계 하위 (읍면동)
        'gender': '0'
    }
    response = requests.get(url, params=params, timeout=10)
    if response.status_code == 200:
        data = response.json()
        if data.get('errCd') == 0:
            results = data.get('result', [])
            print(f"\n유성구 ({yuseong_code}) 읍면동:")
            for item in results:
                adm_nm = item.get('adm_nm', '')
                if '원촌' in adm_nm:
                    print(f"  ★ [{item.get('adm_cd')}] {adm_nm}: {item.get('population')}명")
                else:
                    print(f"  [{item.get('adm_cd')}] {adm_nm}: {item.get('population')}명")
            return results
    return []

# 4. 서울 종로구 읍면동 조회
def find_jongno_dongs(access_token):
    url = "https://sgisapi.kostat.go.kr/OpenAPI3/stats/searchpopulation.json"
    params = {
        'accessToken': access_token,
        'year': '2023',
        'adm_cd': '11110',  # 서울 종로구
        'low_search': '1',  # 1단계 하위 (읍면동)
        'gender': '0'
    }
    response = requests.get(url, params=params, timeout=10)
    if response.status_code == 200:
        data = response.json()
        if data.get('errCd') == 0:
            results = data.get('result', [])
            print(f"\n서울 종로구 읍면동:")
            for item in results:
                adm_nm = item.get('adm_nm', '')
                if '서린' in adm_nm:
                    print(f"  ★ [{item.get('adm_cd')}] {adm_nm}: {item.get('population')}명")
                else:
                    print(f"  [{item.get('adm_cd')}] {adm_nm}: {item.get('population')}명")
            return results
    return []

if __name__ == "__main__":
    print("=" * 80)
    print("SGIS 행정구역코드 찾기")
    print("=" * 80)
    
    access_token = get_access_token()
    if access_token:
        print(f"✓ 액세스 토큰 발급 성공\n")
        
        # 대전광역시 시군구
        daejeon_districts = find_daejeon_districts(access_token)
        
        # 유성구 코드 찾기
        yuseong_code = None
        for district in daejeon_districts:
            if '유성' in district.get('adm_nm', ''):
                yuseong_code = district.get('adm_cd')
                break
        
        if yuseong_code:
            find_yuseong_dongs(access_token, yuseong_code)
        
        # 서울 종로구 읍면동
        find_jongno_dongs(access_token)
    else:
        print("✗ 인증 실패")
