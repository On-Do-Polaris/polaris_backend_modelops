"""
기상청 API 테스트 스크립트
- 태풍 정보 API
- 기상관측 API (AWS, ASOS)
"""

import requests
import json
from dotenv import load_dotenv
import os
from datetime import datetime, timedelta

# .env 파일 로드
load_dotenv()

# API 키 가져오기
KMA_API_KEY = os.getenv('KMA_API_KEY')

print(f"KMA API Key: {KMA_API_KEY[:10]}..." if KMA_API_KEY else "API Key not found")
print("=" * 80)

# 1. 태풍 정보 API 테스트
def test_typhoon_api():
    """기상청 태풍 정보 API 테스트"""
    print("\n[1] 태풍 정보 API 테스트")
    print("-" * 80)
    
    # 태풍 목록 조회
    url = "https://apihub.kma.go.kr/api/typ01/typhoonInfo"
    
    # 최근 연도의 태풍 조회
    current_year = datetime.now().year
    
    params = {
        'serviceKey': KMA_API_KEY,
        'tm': str(current_year),  # 년도
        'pageNo': '1',
        'numOfRows': '5',
        'dataType': 'JSON'
    }
    
    try:
        response = requests.get(url, params=params, timeout=15)
        print(f"Status Code: {response.status_code}")
        print(f"URL: {response.url}")
        
        if response.status_code == 200:
            try:
                data = response.json()
                print(f"Response: {json.dumps(data, indent=2, ensure_ascii=False)[:1000]}")
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


# 2. 기상 관측 데이터 API 테스트 (단기예보)
def test_weather_forecast():
    """기상청 단기예보 API 테스트"""
    print("\n[2] 단기예보 조회 API 테스트")
    print("-" * 80)
    
    url = "http://apis.data.go.kr/1360000/VilageFcstInfoService_2.0/getVilageFcst"
    
    # 공공데이터포털의 기상청 API 키 사용
    PUBLICDATA_KEY = os.getenv('PUBLICDATA_API_KEY')
    
    # 현재 시각 기준으로 base_date, base_time 설정
    now = datetime.now()
    base_date = now.strftime('%Y%m%d')
    base_time = '0500'  # 05시 발표 기준
    
    params = {
        'serviceKey': PUBLICDATA_KEY,
        'pageNo': '1',
        'numOfRows': '10',
        'dataType': 'JSON',
        'base_date': base_date,
        'base_time': base_time,
        'nx': '60',  # 서울 격자 X
        'ny': '127'  # 서울 격자 Y
    }
    
    try:
        response = requests.get(url, params=params, timeout=15)
        print(f"Status Code: {response.status_code}")
        print(f"URL: {response.url}")
        
        if response.status_code == 200:
            try:
                data = response.json()
                print(f"Response: {json.dumps(data, indent=2, ensure_ascii=False)[:1500]}")
                
                if 'response' in data:
                    header = data['response'].get('header', {})
                    print(f"\nResult Code: {header.get('resultCode')}")
                    print(f"Result Msg: {header.get('resultMsg')}")
                
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


# 3. 지상 관측 자료 조회 (ASOS)
def test_asos_data():
    """기상청 지상 관측 자료 조회 (ASOS)"""
    print("\n[3] 지상 관측 자료 (ASOS) 조회 테스트")
    print("-" * 80)
    
    url = "http://apis.data.go.kr/1360000/AsosDalyInfoService/getWthrDataList"
    
    PUBLICDATA_KEY = os.getenv('PUBLICDATA_API_KEY')
    
    # 어제 날짜
    yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y%m%d')
    
    params = {
        'serviceKey': PUBLICDATA_KEY,
        'pageNo': '1',
        'numOfRows': '10',
        'dataType': 'JSON',
        'dataCd': 'ASOS',
        'dateCd': 'DAY',
        'startDt': yesterday,
        'endDt': yesterday,
        'stnIds': '108'  # 서울 관측소
    }
    
    try:
        response = requests.get(url, params=params, timeout=15)
        print(f"Status Code: {response.status_code}")
        print(f"URL: {response.url}")
        
        if response.status_code == 200:
            try:
                data = response.json()
                print(f"Response: {json.dumps(data, indent=2, ensure_ascii=False)[:1500]}")
                
                if 'response' in data:
                    header = data['response'].get('header', {})
                    print(f"\nResult Code: {header.get('resultCode')}")
                    print(f"Result Msg: {header.get('resultMsg')}")
                    
                    body = data['response'].get('body', {})
                    if 'items' in body and 'item' in body['items']:
                        items = body['items']['item']
                        if items:
                            item = items[0] if isinstance(items, list) else items
                            print(f"\n관측소: {item.get('stnNm')}")
                            print(f"평균기온: {item.get('avgTa')}°C")
                            print(f"일강수량: {item.get('sumRn')}mm")
                
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


# 4. AWS 시간별 관측 자료
def test_aws_data():
    """기상청 AWS 시간별 관측 자료"""
    print("\n[4] AWS 시간별 관측 자료 테스트")
    print("-" * 80)
    
    url = "http://apis.data.go.kr/1360000/AsosHourlyInfoService/getWthrDataList"
    
    PUBLICDATA_KEY = os.getenv('PUBLICDATA_API_KEY')
    
    # 어제 날짜
    yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y%m%d')
    
    params = {
        'serviceKey': PUBLICDATA_KEY,
        'pageNo': '1',
        'numOfRows': '10',
        'dataType': 'JSON',
        'dataCd': 'ASOS',
        'dateCd': 'HR',
        'startDt': yesterday,
        'startHh': '00',
        'endDt': yesterday,
        'endHh': '23',
        'stnIds': '108'  # 서울 관측소
    }
    
    try:
        response = requests.get(url, params=params, timeout=15)
        print(f"Status Code: {response.status_code}")
        print(f"URL: {response.url}")
        
        if response.status_code == 200:
            try:
                data = response.json()
                print(f"Response: {json.dumps(data, indent=2, ensure_ascii=False)[:1500]}")
                
                if 'response' in data:
                    header = data['response'].get('header', {})
                    print(f"\nResult Code: {header.get('resultCode')}")
                    print(f"Result Msg: {header.get('resultMsg')}")
                
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
        '태풍 정보 API': test_typhoon_api(),
        '단기예보 API': test_weather_forecast(),
        'ASOS 일별 관측': test_asos_data(),
        'ASOS 시간별 관측': test_aws_data()
    }
    
    print("\n" + "=" * 80)
    print("테스트 결과 요약")
    print("=" * 80)
    for api_name, result in results.items():
        status = "✓ 성공" if result else "✗ 실패"
        print(f"{api_name}: {status}")
