"""
V-World (브이월드) API 테스트 스크립트
- 하천망 데이터
- 행정구역 정보
- 해안선 데이터
"""

import requests
import json
from dotenv import load_dotenv
import os

# .env 파일 로드
load_dotenv()

# API 키 가져오기
API_KEY = os.getenv('VWORLD_API_KEY')

print(f"API Key: {API_KEY[:10]}..." if API_KEY else "API Key not found")
print("=" * 80)

# 1. 하천망 데이터 테스트
def test_river_data():
    """VWorld 하천망 데이터 조회 테스트"""
    print("\n[1] 하천망 데이터 조회 테스트")
    print("-" * 80)
    
    url = "https://api.vworld.kr/req/data"
    
    # 한강 주변 검색 (서울 중심)
    params = {
        'service': 'data',
        'request': 'GetFeature',
        'data': 'LT_C_WKMSTRM',  # 하천망 레이어
        'key': API_KEY,
        'domain': 'http://localhost',
        'geomFilter': 'POINT(126.9780 37.5665)',  # 서울시청 좌표
        'buffer': '5000',  # 5km 반경
        'size': '5',
        'format': 'json',
        'geometry': 'true',
        'attribute': 'true'
    }
    
    try:
        response = requests.get(url, params=params, timeout=15)
        print(f"Status Code: {response.status_code}")
        print(f"URL: {response.url}")
        
        if response.status_code == 200:
            try:
                data = response.json()
                print(f"Response: {json.dumps(data, indent=2, ensure_ascii=False)}")
                
                if 'response' in data and 'result' in data['response']:
                    result = data['response']['result']
                    if 'featureCollection' in result:
                        features = result['featureCollection'].get('features', [])
                        print(f"\n검색된 하천 수: {len(features)}")
                        for i, feature in enumerate(features[:3], 1):
                            props = feature.get('properties', {})
                            print(f"  {i}. 하천명: {props.get('flw_nm', 'N/A')}, 등급: {props.get('flw_grd_nm', 'N/A')}")
                
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


# 2. 행정구역 경계 테스트
def test_admin_boundary():
    """VWorld 행정구역 경계 조회 테스트"""
    print("\n[2] 행정구역 경계 조회 테스트")
    print("-" * 80)
    
    url = "https://api.vworld.kr/req/data"
    
    params = {
        'service': 'data',
        'request': 'GetFeature',
        'data': 'LT_C_ADSIGG_INFO',  # 시군구 레이어
        'key': API_KEY,
        'domain': 'http://localhost',
        'attrFilter': 'sig_kor_nm:like:종로구',  # 종로구 검색
        'size': '5',
        'format': 'json',
        'geometry': 'false',
        'attribute': 'true'
    }
    
    try:
        response = requests.get(url, params=params, timeout=15)
        print(f"Status Code: {response.status_code}")
        print(f"URL: {response.url}")
        
        if response.status_code == 200:
            try:
                data = response.json()
                print(f"Response: {json.dumps(data, indent=2, ensure_ascii=False)}")
                
                if 'response' in data and 'result' in data['response']:
                    result = data['response']['result']
                    if 'featureCollection' in result:
                        features = result['featureCollection'].get('features', [])
                        print(f"\n검색된 행정구역 수: {len(features)}")
                        for i, feature in enumerate(features, 1):
                            props = feature.get('properties', {})
                            print(f"  {i}. 시군구: {props.get('sig_kor_nm', 'N/A')}, 코드: {props.get('sig_cd', 'N/A')}")
                
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


# 3. 주소 검색 (Geocoding) 테스트
def test_geocoding():
    """VWorld Geocoding API 테스트"""
    print("\n[3] Geocoding (주소검색) 테스트")
    print("-" * 80)
    
    url = "https://api.vworld.kr/req/address"
    
    params = {
        'service': 'address',
        'request': 'getcoord',
        'key': API_KEY,
        'address': '서울특별시 종로구 세종대로 110',
        'format': 'json',
        'type': 'road',  # 도로명주소
        'simple': 'false'
    }
    
    try:
        response = requests.get(url, params=params, timeout=10)
        print(f"Status Code: {response.status_code}")
        print(f"URL: {response.url}")
        
        if response.status_code == 200:
            try:
                data = response.json()
                print(f"Response: {json.dumps(data, indent=2, ensure_ascii=False)}")
                
                if 'response' in data and 'result' in data['response']:
                    result = data['response']['result']
                    if 'point' in result:
                        point = result['point']
                        print(f"\n좌표: X={point.get('x')}, Y={point.get('y')}")
                
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


# 4. WMS 지도 이미지 테스트 (정적 이미지)
def test_wms_map():
    """VWorld WMS 지도 이미지 테스트"""
    print("\n[4] WMS 지도 이미지 테스트")
    print("-" * 80)
    
    url = "https://api.vworld.kr/req/wms"
    
    params = {
        'service': 'WMS',
        'request': 'GetMap',
        'version': '1.3.0',
        'layers': 'lt_c_wkmstrm',  # 하천망 레이어
        'styles': 'lt_c_wkmstrm',
        'crs': 'EPSG:4326',
        'bbox': '126.9,37.5,127.0,37.6',  # 서울 일부 영역
        'width': '512',
        'height': '512',
        'format': 'image/png',
        'transparent': 'true',
        'bgcolor': '0xFFFFFF',
        'exceptions': 'text/xml',
        'key': API_KEY,
        'domain': 'http://localhost'
    }
    
    try:
        response = requests.get(url, params=params, timeout=15)
        print(f"Status Code: {response.status_code}")
        print(f"URL: {response.url}")
        print(f"Content-Type: {response.headers.get('Content-Type')}")
        
        if response.status_code == 200:
            if 'image' in response.headers.get('Content-Type', ''):
                print(f"✓ 이미지 응답 수신 (크기: {len(response.content)} bytes)")
                return True
            else:
                print(f"Response: {response.text[:500]}")
                return False
        else:
            print(f"Error: {response.text[:500]}")
            return False
    except Exception as e:
        print(f"Exception: {str(e)}")
        return False


if __name__ == "__main__":
    results = {
        '하천망 데이터': test_river_data(),
        '행정구역 경계': test_admin_boundary(),
        'Geocoding': test_geocoding(),
        'WMS 지도': test_wms_map()
    }
    
    print("\n" + "=" * 80)
    print("테스트 결과 요약")
    print("=" * 80)
    for api_name, result in results.items():
        status = "✓ 성공" if result else "✗ 실패"
        print(f"{api_name}: {status}")
