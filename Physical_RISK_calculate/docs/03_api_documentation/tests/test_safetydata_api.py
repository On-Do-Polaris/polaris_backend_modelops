"""
재난안전데이터공유플랫폼 API 테스트 스크립트
- 하천정보
- 지역재해위험지구
- 행정안전부_긴급재난문자
- 기상청_AWS10분주기
"""

import os
import requests
from dotenv import load_dotenv
import json
from datetime import datetime

# .env 파일 로드
env_path = os.path.join(os.path.dirname(__file__), '..', '..', '..', '.env')
load_dotenv(env_path)

# API 키 가져오기
RIVER_API_KEY = os.getenv('RIVER_API_KEY')
DISASTERAREA_API_KEY = os.getenv('DISASTERAREA_API_KEY')
EMERGENCYMESSAGE_API_KEY = os.getenv('EMERGENCYMESSAGE_API_KEY')
AWS10_API_KEY = os.getenv('AWS10_API_KEY')

print("재난안전데이터공유플랫폼 API Keys:")
print(f"  하천정보: {RIVER_API_KEY}")
print(f"  지역재해위험지구: {DISASTERAREA_API_KEY}")
print(f"  긴급재난문자: {EMERGENCYMESSAGE_API_KEY}")
print(f"  AWS10분주기: {AWS10_API_KEY}")

print("\n" + "=" * 80)
print("재난안전데이터공유플랫폼 API 테스트")
print("=" * 80)


# 1. 하천정보 API
def test_river_info():
    """하천정보 조회"""
    print("\n[1] 하천정보 조회")
    print("-" * 80)
    
    url = "https://www.safetydata.go.kr/V2/api/DSSP-IF-10720"
    params = {
        'serviceKey': RIVER_API_KEY,
        'returnType': 'json',
        'pageNo': '1',
        'numOfRows': '5'
    }
    
    try:
        response = requests.get(url, params=params, timeout=10, verify=False)
        print(f"Status Code: {response.status_code}")
        
        data = response.json()
        
        # 응답 구조 확인
        if 'body' in data:
            body = data['body']
            if isinstance(body, list) and len(body) > 0:
                print(f"✓ 성공 - 하천정보 {len(body)}건 조회")
                print("\n하천정보 데이터 예시:")
                for i, river in enumerate(body[:3], 1):
                    print(f"\n  {i}. {river.get('RVR_NM', 'N/A')}")
                    print(f"     하천관리번호: {river.get('RVR_MNG_NO', 'N/A')}")
                    print(f"     하천등급코드: {river.get('RVR_GRD_CD', 'N/A')}")
                    print(f"     하천연장길이: {river.get('RVR_PRLG_LEN', 'N/A')}")
                    print(f"     유역면적: {river.get('DRAR', 'N/A')}")
                return True
            else:
                print(f"✗ 실패 - 데이터 없음")
                print(f"응답: {json.dumps(data, indent=2, ensure_ascii=False)}")
                return False
        else:
            print(f"✗ 실패 - 예상치 못한 응답 구조")
            print(f"응답: {json.dumps(data, indent=2, ensure_ascii=False)}")
            return False
            
    except Exception as e:
        print(f"✗ 에러 발생: {str(e)}")
        return False


# 2. 지역재해위험지구 API
def test_disaster_area():
    """지역재해위험지구 조회"""
    print("\n[2] 지역재해위험지구 조회")
    print("-" * 80)
    
    url = "https://www.safetydata.go.kr/V2/api/DSSP-IF-10075"
    params = {
        'serviceKey': DISASTERAREA_API_KEY,
        'returnType': 'json',
        'pageNo': '1',
        'numOfRows': '5'
    }
    
    try:
        response = requests.get(url, params=params, timeout=10, verify=False)
        print(f"Status Code: {response.status_code}")
        
        data = response.json()
        
        if 'body' in data:
            body = data['body']
            if isinstance(body, list) and len(body) > 0:
                print(f"✓ 성공 - 지역재해위험지구 {len(body)}건 조회")
                print("\n지역재해위험지구 데이터 예시:")
                for i, area in enumerate(body[:3], 1):
                    print(f"\n  {i}. {area.get('DST_RSK_DSTRCT_NM', 'N/A')}")
                    print(f"     관리번호: {area.get('DST_RSK_DSTRCT_MNG_NO', 'N/A')}")
                    print(f"     등급코드: {area.get('DST_RSK_DSTRCT_GRD_CD', 'N/A')}")
                    print(f"     유형코드: {area.get('DST_RSK_DSTRCT_TYPE_CD', 'N/A')}")
                    print(f"     지정일자: {area.get('DSGN_YMD', 'N/A')}")
                    print(f"     지정사유: {area.get('DSGN_RSN', 'N/A')[:50]}...")
                return True
            else:
                print(f"✗ 실패 - 데이터 없음")
                print(f"응답: {json.dumps(data, indent=2, ensure_ascii=False)}")
                return False
        else:
            print(f"✗ 실패 - 예상치 못한 응답 구조")
            print(f"응답: {json.dumps(data, indent=2, ensure_ascii=False)}")
            return False
            
    except Exception as e:
        print(f"✗ 에러 발생: {str(e)}")
        return False


# 3. 긴급재난문자 API
def test_emergency_message():
    """긴급재난문자 조회 (최근 30일)"""
    print("\n[3] 긴급재난문자 조회")
    print("-" * 80)
    
    url = "https://www.safetydata.go.kr/V2/api/DSSP-IF-00247"
    
    # 최근 30일 데이터 조회
    from datetime import datetime, timedelta
    start_date = (datetime.now() - timedelta(days=30)).strftime('%Y%m%d')
    
    params = {
        'serviceKey': EMERGENCYMESSAGE_API_KEY,
        'returnType': 'json',
        'pageNo': '1',
        'numOfRows': '10',
        'crtDt': start_date  # 조회시작일자
    }
    
    try:
        response = requests.get(url, params=params, timeout=10, verify=False)
        print(f"Status Code: {response.status_code}")
        print(f"조회기간: {start_date} ~ 현재")
        
        data = response.json()
        
        if 'body' in data:
            body = data['body']
            if isinstance(body, list) and len(body) > 0:
                print(f"✓ 성공 - 긴급재난문자 {len(body)}건 조회")
                print("\n긴급재난문자 데이터 예시:")
                for i, msg in enumerate(body[:3], 1):
                    print(f"\n  {i}. [{msg.get('EMRG_STEP_NM', 'N/A')}] {msg.get('DST_SE_NM', 'N/A')}")
                    print(f"     생성일시: {msg.get('CRT_DT', 'N/A')}")
                    print(f"     수신지역: {msg.get('RCPTN_RGN_NM', 'N/A')}")
                    print(f"     메시지: {msg.get('MSG_CN', 'N/A')[:100]}...")
                return True
            else:
                print(f"✗ 실패 - 데이터 없음 (최근 30일간 긴급재난문자가 없을 수 있음)")
                print(f"응답: {json.dumps(data, indent=2, ensure_ascii=False)}")
                return False
        else:
            print(f"✗ 실패 - 예상치 못한 응답 구조")
            print(f"응답: {json.dumps(data, indent=2, ensure_ascii=False)}")
            return False
            
    except Exception as e:
        print(f"✗ 에러 발생: {str(e)}")
        return False


# 4. 기상청 AWS10분주기 API
def test_aws10():
    """기상청 AWS10분주기 관측 데이터 조회"""
    print("\n[4] 기상청 AWS10분주기 관측 데이터 조회")
    print("-" * 80)
    
    # 특정 관측소 코드로 조회
    # 410: 대전(대덕), 410: 기상청(보라매), 364: 분당구(판교)
    test_stations = [
        ('410', '대전 대덕'),
        ('410', '기상청 보라매'),
        ('364', '분당구 판교')
    ]
    
    all_results = []
    
    for station_code, station_name in test_stations:
        print(f"\n  {station_name} (코드: {station_code}) 조회 중...")
        
        url = "https://www.safetydata.go.kr/V2/api/DSSP-IF-00026"
        params = {
            'serviceKey': AWS10_API_KEY,
            'returnType': 'json',
            'pageNo': '1',
            'numOfRows': '5',
            'AWS_OBSVTR_CD': station_code
            }
        
        try:
            response = requests.get(url, params=params, timeout=10, verify=False)
            
            if response.status_code == 200:
                data = response.json()
                
                if 'body' in data:
                    body = data['body']
                    if isinstance(body, list) and len(body) > 0:
                        all_results.extend(body)
                        print(f"  ✓ {station_name}: {len(body)}건 조회 성공")
                    else:
                        print(f"  ✗ {station_name}: 데이터 없음")
                else:
                    print(f"  ✗ {station_name}: 예상치 못한 응답 구조")
            else:
                print(f"  ✗ {station_name}: HTTP {response.status_code}")
                
        except Exception as e:
            print(f"  ✗ {station_name}: 에러 - {str(e)}")
    
    # 결과 출력
    print(f"\nStatus Code: 200")
    if all_results:
        print(f"✓ 성공 - AWS 관측 데이터 총 {len(all_results)}건 조회")
        print("\nAWS 관측 데이터 예시:")
        for i, obs in enumerate(all_results[:5], 1):
            print(f"\n  {i}. AWS관측소코드: {obs.get('AWS_OBSVTR_CD', 'N/A')}")
            print(f"     관측시간: {obs.get('OBSRVN_HR', 'N/A')}")
            print(f"     기온: {obs.get('AIRTP', 'N/A')}℃")
            print(f"     풍속: {obs.get('WISP', 'N/A')}m/s")
            print(f"     강수량: {obs.get('RNFLL_F', 'N/A')}mm")
            print(f"     상대습도: {obs.get('RLTHDY', 'N/A')}%")
        return True
    else:
        print(f"✗ 실패 - 모든 관측소에서 데이터 없음")
        return False


# 메인 실행
if __name__ == "__main__":
    results = {
        '하천정보': test_river_info(),
        '지역재해위험지구': test_disaster_area(),
        '긴급재난문자': test_emergency_message(),
        'AWS10분주기': test_aws10()
    }
    
    print("\n" + "=" * 80)
    print("테스트 결과 요약")
    print("=" * 80)
    
    for name, result in results.items():
        status = "✓ 성공" if result else "✗ 실패"
        print(f"{name}: {status}")
    
    success_count = sum(results.values())
    total_count = len(results)
    print(f"\n성공: {success_count}/{total_count}, 실패: {total_count - success_count}/{total_count}")
