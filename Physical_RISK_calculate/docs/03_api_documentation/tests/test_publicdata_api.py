"""
공공데이터포털 API 테스트 스크립트
- 건축물대장 API
- 병원 API  
- 재해연보 API
- WAMIS 유역특성 API
"""

import requests
import json
from dotenv import load_dotenv
import os

# .env 파일 로드
load_dotenv()

# API 키 가져오기
API_KEY = os.getenv('PUBLICDATA_API_KEY')

print(f"API Key: {API_KEY[:10]}..." if API_KEY else "API Key not found")
print("=" * 80)

# 1. 건축물대장 API 테스트
def test_building_api():
    """건축물대장 API 테스트"""
    print("\n[1] 건축물대장 API 테스트")
    print("-" * 80)
    
    url = "http://apis.data.go.kr/1613000/BldRgstHubService/getBrTitleInfo"
    
    params = {
        'serviceKey': API_KEY,
        'sigunguCd': '11110',  # 서울 종로구
        'bjdongCd': '10100',    # 청운동
        'bun': '0001',
        'ji': '0000',
        'numOfRows': '10',
        'pageNo': '1',
        '_type': 'json'
    }
    
    try:
        response = requests.get(url, params=params, timeout=10)
        print(f"Status Code: {response.status_code}")
        print(f"URL: {response.url}")
        
        if response.status_code == 200:
            try:
                data = response.json()
                print(f"Response: {json.dumps(data, indent=2, ensure_ascii=False)}")
                return True
            except json.JSONDecodeError:
                print(f"Response Text: {response.text[:500]}")
                return False
        else:
            print(f"Error: {response.text[:500]}")
            return False
    except Exception as e:
        print(f"Exception: {str(e)}")
        return False


# 2. 병원 API 테스트
def test_hospital_api():
    """국립중앙의료원 병원 API 테스트"""
    print("\n[2] 병원 API 테스트")
    print("-" * 80)
    
    url = "http://apis.data.go.kr/B552657/HsptlAsembySearchService/getHsptlMdcncListInfoInqire"
    
    params = {
        'serviceKey': API_KEY,
        'Q0': '서울특별시',      # 시도명
        'Q1': '종로구',          # 시군구명
        'QT': '',                # 병원종별
        'pageNo': '1',
        'numOfRows': '10'
    }
    
    try:
        response = requests.get(url, params=params, timeout=10)
        print(f"Status Code: {response.status_code}")
        print(f"URL: {response.url}")
        
        if response.status_code == 200:
            try:
                # XML 응답
                print(f"Response (XML): {response.text[:1000]}")
                return True
            except Exception as e:
                print(f"Parse Error: {str(e)}")
                print(f"Response Text: {response.text[:500]}")
                return False
        else:
            print(f"Error: {response.text[:500]}")
            return False
    except Exception as e:
        print(f"Exception: {str(e)}")
        return False


# 3. 재해연보 API 테스트
def test_disaster_api():
    """행정안전부 재해연보 API 테스트"""
    print("\n[3] 재해연보 API 테스트")
    print("-" * 80)
    
    url = "http://apis.data.go.kr/1741000/DisasterMsg4/getDisasterMsg1List"
    
    params = {
        'serviceKey': API_KEY,
        'pageNo': '1',
        'numOfRows': '10',
        'type': 'json'
    }
    
    try:
        response = requests.get(url, params=params, timeout=10)
        print(f"Status Code: {response.status_code}")
        print(f"URL: {response.url}")
        
        if response.status_code == 200:
            try:
                data = response.json()
                print(f"Response: {json.dumps(data, indent=2, ensure_ascii=False)}")
                return True
            except json.JSONDecodeError:
                print(f"Response Text: {response.text[:500]}")
                return False
        else:
            print(f"Error: {response.text[:500]}")
            return False
    except Exception as e:
        print(f"Exception: {str(e)}")
        return False


# 4. WAMIS 유역특성 API 테스트
def test_wamis_api():
    """WAMIS 유역특성 API 테스트"""
    print("\n[4] WAMIS 유역특성 API 테스트")
    print("-" * 80)
    
    url = "http://apis.data.go.kr/B552747/WamisBasinCharacteristics/getBasinCharacteristics"
    
    params = {
        'serviceKey': API_KEY,
        'pageNo': '1',
        'numOfRows': '10',
        'type': 'json'
    }
    
    try:
        response = requests.get(url, params=params, timeout=10)
        print(f"Status Code: {response.status_code}")
        print(f"URL: {response.url}")
        
        if response.status_code == 200:
            try:
                data = response.json()
                print(f"Response: {json.dumps(data, indent=2, ensure_ascii=False)}")
                return True
            except json.JSONDecodeError:
                print(f"Response Text: {response.text[:500]}")
                return False
        else:
            print(f"Error: {response.text[:500]}")
            return False
    except Exception as e:
        print(f"Exception: {str(e)}")
        return False


if __name__ == "__main__":
    results = {
        '건축물대장 API': test_building_api(),
        '병원 API': test_hospital_api(),
        '재해연보 API': test_disaster_api(),
        'WAMIS API': test_wamis_api()
    }
    
    print("\n" + "=" * 80)
    print("테스트 결과 요약")
    print("=" * 80)
    for api_name, result in results.items():
        status = "✓ 성공" if result else "✗ 실패"
        print(f"{api_name}: {status}")
