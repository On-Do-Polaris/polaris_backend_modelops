"""
재난안전데이터 공유플랫폼 API 테스트 스크립트
- 긴급재난문자
- AWS 10분주기
- 지역재해위험지구
- 하천정보
"""

import requests
import json
from dotenv import load_dotenv
import os
from datetime import datetime, timedelta

# .env 파일 로드
load_dotenv()

# API 키 가져오기
EMERGENCYMESSAGE_API_KEY = os.getenv('EMERGENCYMESSAGE_API_KEY')
AWS10_API_KEY = os.getenv('AWS10_API_KEY')
DISASTERAREA_API_KEY = os.getenv('DISASTERAREA_API_KEY')
RIVER_API_KEY = os.getenv('RIVER_API_KEY')

print("재난안전데이터 플랫폼 API Keys:")
print(f"  긴급재난문자: {EMERGENCYMESSAGE_API_KEY}")
print(f"  AWS10분주기: {AWS10_API_KEY}")
print(f"  지역재해위험지구: {DISASTERAREA_API_KEY}")
print(f"  하천정보: {RIVER_API_KEY}")
print("=" * 80)

BASE_URL = "https://www.safetydata.go.kr/V2/api"

# 1. 긴급재난문자 API 테스트
def test_emergency_message():
    """긴급재난문자 발송 이력 조회"""
    print("\n[1] 긴급재난문자 API 테스트")
    print("-" * 80)
    
    url = f"{BASE_URL}/DSSP-IF-00247"
    
    # 최근 30일
    end_date = datetime.now()
    start_date = end_date - timedelta(days=30)
    
    params = {
        'serviceKey': EMERGENCYMESSAGE_API_KEY,
        'returnType': 'json',
        'pageNo': '1',
        'numOfRows': '10',
        'crtDt': start_date.strftime('%Y%m%d')
    }
    
    try:
        response = requests.get(url, params=params, timeout=15)
        print(f"Status Code: {response.status_code}")
        print(f"URL: {response.url}")
        
        if response.status_code == 200:
            try:
                data = response.json()
                print(f"Response: {json.dumps(data, indent=2, ensure_ascii=False)[:1500]}")
                return True
            except json.JSONDecodeError:
                print(f"Response Text: {response.text[:1000]}")
                return False
        else:
            print(f"Error: {response.text[:500]}")
            return False
    except Exception as e:
        print(f"Exception: {str(e)}")
        return False


# 2. AWS 10분주기 기상 데이터
def test_aws_10min():
    """AWS 10분주기 기상관측 데이터"""
    print("\n[2] AWS 10분주기 API 테스트")
    print("-" * 80)
    
    url = f"{BASE_URL}/DSSP-IF-00026"
    
    # 현재 시각
    now = datetime.now()
    obs_time = now.strftime('%Y%m%d%H%M')
    
    params = {
        'serviceKey': AWS10_API_KEY,
        'returnType': 'json',
        'pageNo': '1',
        'numOfRows': '10',
        'AWS_OBSVTR_CD': '001',  # AWS 관측소 코드
        'OBSRVN_HR': obs_time
    }
    
    try:
        response = requests.get(url, params=params, timeout=15)
        print(f"Status Code: {response.status_code}")
        print(f"URL: {response.url}")
        
        if response.status_code == 200:
            try:
                data = response.json()
                print(f"Response: {json.dumps(data, indent=2, ensure_ascii=False)[:1500]}")
                return True
            except json.JSONDecodeError:
                print(f"Response Text: {response.text[:1000]}")
                return False
        else:
            print(f"Error: {response.text[:500]}")
            return False
    except Exception as e:
        print(f"Exception: {str(e)}")
        return False


# 3. 지역재해위험지구 조회
def test_disaster_area():
    """지역재해위험지구 정보 조회"""
    print("\n[3] 지역재해위험지구 API 테스트")
    print("-" * 80)
    
    url = f"{BASE_URL}/DSSP-IF-10075"
    
    params = {
        'serviceKey': DISASTERAREA_API_KEY,
        'returnType': 'json',
        'pageNo': '1',
        'numOfRows': '10'
    }
    
    try:
        response = requests.get(url, params=params, timeout=15)
        print(f"Status Code: {response.status_code}")
        print(f"URL: {response.url}")
        
        if response.status_code == 200:
            try:
                data = response.json()
                print(f"Response: {json.dumps(data, indent=2, ensure_ascii=False)[:1500]}")
                return True
            except json.JSONDecodeError:
                print(f"Response Text: {response.text[:1000]}")
                return False
        else:
            print(f"Error: {response.text[:500]}")
            return False
    except Exception as e:
        print(f"Exception: {str(e)}")
        return False


# 4. 하천정보 조회
def test_river_info():
    """하천 제원 및 관리 정보 조회"""
    print("\n[4] 하천정보 API 테스트")
    print("-" * 80)
    
    url = f"{BASE_URL}/DSSP-IF-10720"
    
    params = {
        'serviceKey': RIVER_API_KEY,
        'returnType': 'json',
        'pageNo': '1',
        'numOfRows': '10'
    }
    
    try:
        response = requests.get(url, params=params, timeout=15)
        print(f"Status Code: {response.status_code}")
        print(f"URL: {response.url}")
        
        if response.status_code == 200:
            try:
                data = response.json()
                print(f"Response: {json.dumps(data, indent=2, ensure_ascii=False)[:1500]}")
                return True
            except json.JSONDecodeError:
                print(f"Response Text: {response.text[:1000]}")
                return False
        else:
            print(f"Error: {response.text[:500]}")
            return False
    except Exception as e:
        print(f"Exception: {str(e)}")
        return False


if __name__ == "__main__":
    results = {
        '긴급재난문자 API': test_emergency_message(),
        'AWS 10분주기 API': test_aws_10min(),
        '지역재해위험지구 API': test_disaster_area(),
        '하천정보 API': test_river_info()
    }
    
    print("\n" + "=" * 80)
    print("테스트 결과 요약")
    print("=" * 80)
    for api_name, result in results.items():
        status = "✓ 성공" if result else "✗ 실패"
        print(f"{api_name}: {status}")
