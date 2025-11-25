"""
공공데이터포털 승인 API 전체 테스트 스크립트
총 9개 API 테스트
"""

import requests
import json
from dotenv import load_dotenv
import os
from datetime import datetime, timedelta

# .env 파일 로드
load_dotenv()

# API 키 가져오기
API_KEY = os.getenv('PUBLICDATA_API_KEY')

print(f"API Key: {API_KEY[:10]}..." if API_KEY else "API Key not found")
print("=" * 80)
print("공공데이터포털 승인 API 테스트 (총 9개)")
print("=" * 80)

# 1. 건축물대장 API (이미 테스트 완료)
def test_building_registry():
    """국토교통부_건축HUB_건축물대장정보 서비스"""
    print("\n[1] 건축물대장정보 서비스")
    print("-" * 80)
    
    url = "http://apis.data.go.kr/1613000/BldRgstHubService/getBrTitleInfo"
    
    params = {
        'serviceKey': API_KEY,
        'sigunguCd': '11110',  # 서울 종로구
        'bjdongCd': '10100',
        'bun': '0001',
        'ji': '0000',
        'numOfRows': '3',
        'pageNo': '1',
        '_type': 'json'
    }
    
    try:
        response = requests.get(url, params=params, timeout=10)
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            if 'response' in data and data['response']['header']['resultCode'] == '00':
                total = data['response']['body'].get('totalCount', 0)
                print(f"✓ 성공 - 조회된 건축물 수: {total}건")
                return True
            else:
                print(f"✗ 실패 - {data}")
                return False
        else:
            print(f"✗ 실패 - Status {response.status_code}")
            return False
    except Exception as e:
        print(f"✗ 예외 - {str(e)}")
        return False


# 2. 건물에너지정보 API (신규)
def test_building_energy():
    """국토교통부_건축HUB_건물에너지정보 서비스"""
    print("\n[2] 건물에너지정보 서비스")
    print("-" * 80)
    
    url = "http://apis.data.go.kr/1613000/BldEngyInfoService/getEnergyInfo"
    
    params = {
        'serviceKey': API_KEY,
        'sigunguCd': '11110',
        'bjdongCd': '10100',
        'bun': '0001',
        'ji': '0000',
        'numOfRows': '3',
        'pageNo': '1'
    }
    
    try:
        response = requests.get(url, params=params, timeout=10)
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            if 'response' in data and data['response']['header']['resultCode'] == '00':
                total = data['response']['body'].get('totalCount', 0)
                print(f"✓ 성공 - 조회된 에너지정보 수: {total}건")
                return True
            else:
                print(f"✗ 실패 - {data}")
                return False
        else:
            print(f"✗ 실패 - Status {response.status_code}")
            return False
    except Exception as e:
        print(f"✗ 예외 - {str(e)}")
        return False


# 3. 병원 API (이미 테스트 완료)
def test_hospital():
    """국립중앙의료원_전국 병·의원 찾기 서비스"""
    print("\n[3] 전국 병·의원 찾기 서비스")
    print("-" * 80)
    
    url = "http://apis.data.go.kr/B552657/HsptlAsembySearchService/getHsptlMdcncListInfoInqire"
    
    params = {
        'serviceKey': API_KEY,
        'Q0': '서울특별시',
        'Q1': '종로구',
        'pageNo': '1',
        'numOfRows': '3'
    }
    
    try:
        response = requests.get(url, params=params, timeout=10)
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            if '<resultCode>00</resultCode>' in response.text:
                print(f"✓ 성공 - 병원 목록 조회 성공 (XML)")
                return True
            else:
                print(f"✗ 실패 - {response.text[:200]}")
                return False
        else:
            print(f"✗ 실패 - Status {response.status_code}")
            return False
    except Exception as e:
        print(f"✗ 예외 - {str(e)}")
        return False


# 4. 자연재난 피해 API (신규)
def test_natural_disaster():
    """행정안전부_통계연보_연도별 자연재난 피해"""
    print("\n[4] 통계연보_연도별 자연재난 피해")
    print("-" * 80)
    
    # API 명세서에 따른 정확한 엔드포인트
    url = "http://apis.data.go.kr/1741000/NaturalDisasterDamageByYear/getNaturalDisasterDamageByYear"
    
    params = {
        'serviceKey': API_KEY,
        'pageNo': '1',
        'numOfRows': '10'
    }
    
    try:
        response = requests.get(url, params=params, timeout=10)
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            # XML 응답을 처리
            text = response.text
            if '<totalCount>' in text:
                # totalCount 추출
                import re
                count_match = re.search(r'<totalCount>(\d+)</totalCount>', text)
                if count_match:
                    total_count = count_match.group(1)
                    print(f"✓ 성공 - 자연재난 피해 데이터 {total_count}건 조회")
                    # 샘플 데이터 출력 (처음 500자)
                    print(f"응답 샘플:\n{text[:500]}")
                    return True
            print(f"✗ 실패 - 응답 형식 오류: {text[:200]}")
            return False
        else:
            print(f"✗ 실패 - Status {response.status_code}: {response.text[:200]}")
            return False
    except Exception as e:
        print(f"✗ 예외 - {str(e)}")
        return False


# 5. 주민등록인구 API (신규)
def test_population():
    """행정안전부_통계연보_지역별 주민등록인구"""
    print("\n[5] 통계연보_지역별 주민등록인구")
    print("-" * 80)
    
    # API 명세서에 따른 정확한 엔드포인트
    url = "http://apis.data.go.kr/1741000/RegistrationPopulationByRegion/getRegistrationPopulationByRegion"
    
    params = {
        'serviceKey': API_KEY,
        'pageNo': '1',
        'numOfRows': '50'  # 더 많은 데이터를 조회하여 읍면동 정보 확인
    }
    
    try:
        response = requests.get(url, params=params, timeout=10)
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            # XML 응답을 처리
            text = response.text
            if '<totalCount>' in text:
                # totalCount 추출
                import re
                count_match = re.search(r'<totalCount>(\d+)</totalCount>', text)
                if count_match:
                    total_count = count_match.group(1)
                    print(f"✓ 성공 - 주민등록인구 데이터 {total_count}건 조회")
                    
                    # regi 필드 패턴 추출하여 지역 정보 확인
                    regi_pattern = re.findall(r'<regi>(.*?)</regi>', text)
                    if regi_pattern:
                        print(f"\n지역 정보 샘플 (처음 20개):")
                        for i, regi in enumerate(regi_pattern[:20], 1):
                            print(f"  {i}. {regi}")
                    
                    # 전체 응답 샘플
                    print(f"\n응답 샘플:\n{text[:800]}")
                    return True
            print(f"✗ 실패 - 응답 형식 오류: {text[:200]}")
            return False
        else:
            print(f"✗ 실패 - Status {response.status_code}: {response.text[:200]}")
            return False
    except Exception as e:
        print(f"✗ 예외 - {str(e)}")
        return False


# 6. 산불위험예보정보 API (신규)
def test_forest_fire():
    """산림청 국립산림과학원_산불위험예보정보"""
    print("\n[6] 산불위험예보정보")
    print("-" * 80)
    
    # API 명세서에 따른 정확한 엔드포인트
    url = "http://apis.data.go.kr/1400377/forestPoint/forestPointListEmdSearch"
    
    params = {
        'serviceKey': API_KEY,
        'pageNo': '1',
        'numOfRows': '10',
        '_type': 'json',  # xml 또는 json
        'localAreas': '11110101',  # 서울 종로구 청운동 (샘플)
        'excludeForecast': '0'  # 0: 예보정보 포함, 1: 제외
    }
    
    try:
        response = requests.get(url, params=params, timeout=10)
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            try:
                data = response.json()
                print(f"✓ 성공 - 응답: {json.dumps(data, indent=2, ensure_ascii=False)[:500]}")
                return True
            except:
                print(f"✗ 실패 - {response.text[:200]}")
                return False
        else:
            print(f"✗ 실패 - Status {response.status_code}: {response.text[:200]}")
            return False
    except Exception as e:
        print(f"✗ 예외 - {str(e)}")
        return False


# 7. 지하수 이용현황 API (신규)
def test_groundwater():
    """한국수자원공사_지하수 세부용도별 이용 현황"""
    print("\n[7] 지하수 세부용도별 이용 현황")
    print("-" * 80)
    
    url = "http://apis.data.go.kr/B552747/GroundWaterUsage/getGroundWaterUsageList"
    
    params = {
        'serviceKey': API_KEY,
        'pageNo': '1',
        'numOfRows': '10',
        'type': 'json'
    }
    
    try:
        response = requests.get(url, params=params, timeout=10)
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            try:
                data = response.json()
                print(f"✓ 성공 - 응답: {json.dumps(data, indent=2, ensure_ascii=False)[:500]}")
                return True
            except:
                print(f"✗ 실패 - {response.text[:200]}")
                return False
        else:
            print(f"✗ 실패 - Status {response.status_code}: {response.text[:200]}")
            return False
    except Exception as e:
        print(f"✗ 예외 - {str(e)}")
        return False


# 8. 유역별 강수량 API (신규)
def test_watershed_rainfall():
    """기상청_유역별 강수량 자료"""
    print("\n[8] 유역별 강수량 자료")
    print("-" * 80)
    
    url = "http://apis.data.go.kr/1360000/WthrWrnInfoService/getPwnCd"
    
    params = {
        'serviceKey': API_KEY,
        'pageNo': '1',
        'numOfRows': '10',
        'dataType': 'JSON'
    }
    
    try:
        response = requests.get(url, params=params, timeout=10)
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            try:
                data = response.json()
                print(f"✓ 성공 - 응답: {json.dumps(data, indent=2, ensure_ascii=False)[:500]}")
                return True
            except:
                print(f"✗ 실패 - {response.text[:200]}")
                return False
        else:
            print(f"✗ 실패 - Status {response.status_code}: {response.text[:200]}")
            return False
    except Exception as e:
        print(f"✗ 예외 - {str(e)}")
        return False


# 9. 에너지사용 및 온실가스배출량 API (신규)
def test_energy_ghg():
    """한국에너지공단_에너지사용 및 온실가스배출량 통계-마이크로데이터"""
    print("\n[9] 에너지사용 및 온실가스배출량 통계")
    print("-" * 80)
    
    url = "http://apis.data.go.kr/B553530/GHG_LIST_040/GHG_LIST_04_03_20220831_VIEW01"
    
    params = {
        'serviceKey': API_KEY,
        'pageNo': '1',
        'numOfRows': '10',
        'apiType': 'JSON',
        'q1': '2023',  # 연도
        'q2': '5인~9인',  # 종사자규모명
        'q3': '서울특별시',  # 지역명
        'q4': '33409',  # 표준산업분류코드
        'q5': '전력',  # 에너지원구분명
        'q6': '전력'  # 에너지원명
    }
    
    try:
        response = requests.get(url, params=params, timeout=10)
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            try:
                data = response.json()
                print(f"✓ 성공 - 응답: {json.dumps(data, indent=2, ensure_ascii=False)[:500]}")
                return True
            except:
                print(f"✗ 실패 - {response.text[:200]}")
                return False
        else:
            print(f"✗ 실패 - Status {response.status_code}: {response.text[:200]}")
            return False
    except Exception as e:
        print(f"✗ 예외 - {str(e)}")
        return False


if __name__ == "__main__":
    results = {
        '1. 건축물대장정보': test_building_registry(),
        '2. 건물에너지정보': test_building_energy(),
        '3. 병·의원 찾기': test_hospital(),
        '4. 자연재난 피해': test_natural_disaster(),
        '5. 주민등록인구': test_population(),
        '6. 산불위험예보': test_forest_fire(),
        '7. 지하수 이용현황': test_groundwater(),
        '8. 유역별 강수량': test_watershed_rainfall(),
        '9. 에너지·온실가스': test_energy_ghg()
    }
    
    print("\n" + "=" * 80)
    print("전체 테스트 결과 요약 (총 9개)")
    print("=" * 80)
    
    success_count = 0
    for api_name, result in results.items():
        status = "✓ 성공" if result else "✗ 실패"
        if result:
            success_count += 1
        print(f"{api_name}: {status}")
    
    print(f"\n성공: {success_count}/9, 실패: {9-success_count}/9")
