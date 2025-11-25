"""
SGIS (통계지리정보서비스) 인구통계 API 테스트 스크립트
- 인증 (OAuth 토큰 발급)
- 인구통계 조회 (읍면동 단위)
"""

import os
import requests
import json
from dotenv import load_dotenv

# .env 파일 로드
env_path = os.path.join(os.path.dirname(__file__), '..', '..', '..', '.env')
load_dotenv(env_path)

# API Keys
SGIS_SERVICE_ID = os.getenv('SGIS_SERVICE_ID')
SGIS_SECURITY_KEY = os.getenv('SGIS_SECURITY_KEY')

print("SGIS API Keys:")
print(f"  Service ID: {SGIS_SERVICE_ID}")
print(f"  Security Key: {SGIS_SECURITY_KEY[:10]}...")
print()


# 1. 인증 토큰 발급
def get_access_token():
    """SGIS OAuth 인증 토큰 발급"""
    print("[1] SGIS 인증 토큰 발급")
    print("-" * 80)
    
    url = "https://sgisapi.kostat.go.kr/OpenAPI3/auth/authentication.json"
    
    params = {
        'consumer_key': SGIS_SERVICE_ID,
        'consumer_secret': SGIS_SECURITY_KEY
    }
    
    try:
        response = requests.get(url, params=params, timeout=10)
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            
            if data.get('errCd') == 0:
                access_token = data['result']['accessToken']
                access_timeout = data['result']['accessTimeout']
                print(f"✓ 성공 - 액세스 토큰 발급")
                print(f"  Token: {access_token[:20]}...")
                print(f"  Timeout: {access_timeout}")
                return access_token
            else:
                print(f"✗ 실패 - {data.get('errMsg')}")
                return None
        else:
            print(f"✗ 실패 - Status {response.status_code}")
            return None
            
    except Exception as e:
        print(f"✗ 예외 - {str(e)}")
        return None


# 2. 인구통계 조회
def test_population_stats(access_token):
    """인구통계 조회 (읍면동 단위)"""
    print("\n[2] 인구통계 조회 (읍면동 단위)")
    print("-" * 80)
    
    url = "https://sgisapi.kostat.go.kr/OpenAPI3/stats/searchpopulation.json"
    
    # 테스트 케이스 1: 서울특별시 강남구 하위 읍면동 정보
    params = {
        'accessToken': access_token,
        'year': '2023',
        'adm_cd': '11230',  # 서울특별시 강남구
        'low_search': '1',  # 1단계 하위 (읍면동)
        'gender': '0'  # 전체
    }
    
    try:
        response = requests.get(url, params=params, timeout=10)
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            
            if data.get('errCd') == 0:
                results = data.get('result', [])
                print(f"✓ 성공 - 인구통계 {len(results)}건 조회")
                print(f"\n서울특별시 강남구 읍면동별 인구 (2023년):")
                
                for i, item in enumerate(results[:10], 1):
                    adm_cd = item.get('adm_cd', '')
                    adm_nm = item.get('adm_nm', '')
                    population = item.get('population', '0')
                    print(f"  {i}. [{adm_cd}] {adm_nm}: {population:>10}명")
                
                if len(results) > 10:
                    print(f"  ... 외 {len(results) - 10}건")
                
                return True
            else:
                print(f"✗ 실패 - {data.get('errMsg')}")
                return False
        else:
            print(f"✗ 실패 - Status {response.status_code}")
            return False
            
    except Exception as e:
        print(f"✗ 예외 - {str(e)}")
        return False


# 3. 특정 읍면동 상세 조회
def test_specific_dong(access_token):
    """특정 읍면동 인구통계 상세 조회 (서울 강남구 삼성1동)"""
    print("\n[3] 특정 읍면동 상세 조회 (서울 강남구 삼성1동)")
    print("-" * 80)
    
    url = "https://sgisapi.kostat.go.kr/OpenAPI3/stats/searchpopulation.json"
    
    # 서울특별시 강남구 삼성1동
    params = {
        'accessToken': access_token,
        'year': '2023',
        'adm_cd': '11230580',  # 서울 강남구 삼성1동
        'low_search': '0',  # 해당 행정구역만
        'gender': '0'  # 전체
    }
    
    try:
        response = requests.get(url, params=params, timeout=10)
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            
            if data.get('errCd') == 0:
                results = data.get('result', [])
                if results:
                    item = results[0]
                    print(f"✓ 성공 - 상세 정보 조회")
                    print(f"  행정구역코드: {item.get('adm_cd')}")
                    print(f"  행정구역명: {item.get('adm_nm')}")
                    print(f"  인구수: {item.get('population')}명")
                    return True
                else:
                    print(f"✗ 실패 - 데이터 없음")
                    return False
            else:
                print(f"✗ 실패 - {data.get('errMsg')}")
                return False
        else:
            print(f"✗ 실패 - Status {response.status_code}")
            return False
            
    except Exception as e:
        print(f"✗ 예외 - {str(e)}")
        return False


# 4. 성별 인구통계 조회
def test_gender_stats(access_token):
    """성별 인구통계 조회 (서울 종로구 종로1·2·3·4가동)"""
    print("\n[4] 성별 인구통계 조회 (서울 종로구 종로1·2·3·4가동)")
    print("-" * 80)
    
    url = "https://sgisapi.kostat.go.kr/OpenAPI3/stats/searchpopulation.json"
    
    genders = {
        '0': '전체',
        '1': '남자',
        '2': '여자'
    }
    
    results_summary = {}
    
    for gender_code, gender_name in genders.items():
        params = {
            'accessToken': access_token,
            'year': '2023',
            'adm_cd': '11010610',  # 서울 종로구 종로1·2·3·4가동
            'low_search': '0',  # 해당 동만
            'gender': gender_code
        }
        
        try:
            response = requests.get(url, params=params, timeout=10)
            if response.status_code == 200:
                data = response.json()
                if data.get('errCd') == 0:
                    results = data.get('result', [])
                    if results:
                        population = results[0].get('population', '0')
                        results_summary[gender_name] = population
        except:
            pass
    
    if results_summary:
        print(f"✓ 성공 - 성별 인구통계 조회")
        for gender, pop in results_summary.items():
            print(f"  {gender}: {pop:>10}명")
        return True
    else:
        print(f"✗ 실패")
        return False


# 메인 실행
if __name__ == "__main__":
    print("=" * 80)
    print("SGIS 인구통계 API 테스트")
    print("=" * 80)
    print()
    
    # 1. 인증 토큰 발급
    access_token = get_access_token()
    
    if not access_token:
        print("\n인증 실패로 테스트를 중단합니다.")
        exit(1)
    
    # 2. 인구통계 조회 테스트
    results = {
        '읍면동 인구통계': test_population_stats(access_token),
        '특정 읍면동 조회': test_specific_dong(access_token),
        '성별 인구통계': test_gender_stats(access_token)
    }
    
    # 결과 요약
    print("\n" + "=" * 80)
    print("테스트 결과 요약")
    print("=" * 80)
    for test_name, result in results.items():
        status = "✓ 성공" if result else "✗ 실패"
        print(f"{test_name}: {status}")
    
    success_count = sum(1 for r in results.values() if r)
    total_count = len(results)
    print(f"\n성공: {success_count}/{total_count}, 실패: {total_count - success_count}/{total_count}")
