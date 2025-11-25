"""
기상청 태풍 베스트트랙 API 테스트 스크립트
"""

import os
import requests
from dotenv import load_dotenv
import json

# .env 파일 로드
env_path = os.path.join(os.path.dirname(__file__), '..', '..', '..', '.env')
load_dotenv(env_path)

# API 키 가져오기
KMA_API_KEY = os.getenv('KMA_API_KEY')

print("기상청 API Key:")
print(f"  KMA_API_KEY: {KMA_API_KEY}")

print("\n" + "=" * 80)
print("기상청 태풍 베스트트랙 API 테스트")
print("=" * 80)


def test_typhoon_besttrack():
    """태풍 베스트트랙 조회"""
    print("\n[1] 태풍 베스트트랙 조회")
    print("-" * 80)
    
    # 최근 태풍 데이터 조회 (2022년 태풍)
    test_cases = [
        {'year': '2022', 'grade': 'TY', 'tcid': '2201', 'name': '2022년 1호 태풍'},
        {'year': '2022', 'grade': 'TY', 'tcid': '2211', 'name': '2022년 11호 태풍 (힌남노)'},
        {'year': '2021', 'grade': 'TY', 'tcid': '2114', 'name': '2021년 14호 태풍 (찬투)'},
    ]
    
    success_count = 0
    total_count = len(test_cases)
    
    for test_case in test_cases:
        year = test_case['year']
        grade = test_case['grade']
        tcid = test_case['tcid']
        name = test_case['name']
        
        print(f"\n  {name} 조회 중...")
        print(f"  (년도: {year}, 등급: {grade}, 호수: {tcid})")
        
        url = "https://apihub.kma.go.kr/api/typ01/url/typ_besttrack.php"
        params = {
            'year': year,
            'grade': grade,
            'tcid': tcid,
            'help': '1',  # 변수명 + 설명 표시
            'authKey': KMA_API_KEY
        }
        
        try:
            response = requests.get(url, params=params, timeout=30)  # 타임아웃 30초로 증가
            print(f"  Status Code: {response.status_code}")
            
            if response.status_code == 200:
                # 응답 데이터 파싱
                content = response.text
                lines = content.strip().split('\n')
                
                # # 으로 시작하지 않는 데이터 라인만 추출
                data_lines = [line for line in lines if line and not line.startswith('#')]
                
                # 데이터 확인
                if len(data_lines) > 0:
                    print(f"  ✓ 성공 - 태풍 베스트트랙 데이터 조회")
                    print(f"  총 {len(data_lines)}개 시간대 데이터")
                    
                    # 첫 번째 데이터 라인 파싱
                    first_data = data_lines[0].split()
                    if len(first_data) >= 10:
                        print(f"\n  첫 번째 관측 데이터:")
                        print(f"    태풍등급: {first_data[0]}")
                        print(f"    태풍호수: {first_data[1]}")
                        print(f"    일시: {first_data[2]}-{first_data[3].zfill(2)}-{first_data[4].zfill(2)} {first_data[5].zfill(2)}:00")
                        print(f"    위치: 경도 {first_data[6]}°E, 위도 {first_data[7]}°N")
                        print(f"    중심최대풍속: {first_data[8]} m/s")
                        print(f"    중심기압: {first_data[9]} hPa")
                        if len(first_data) >= 12:
                            print(f"    강풍반경(15m/s): 장반경 {first_data[10]}km, 단반경 {first_data[11]}km")
                        if len(first_data) >= 15:
                            print(f"    폭풍반경(25m/s): 장반경 {first_data[13]}km, 단반경 {first_data[14]}km")
                        if len(first_data) > 16:
                            print(f"    태풍이름: {first_data[16]}")
                    
                    success_count += 1
                else:
                    print(f"  ✗ 실패 - 데이터가 없거나 형식이 잘못됨")
                    print(f"  응답: {content[:200]}...")
                    
            else:
                print(f"  ✗ 실패 - HTTP {response.status_code}")
                print(f"  응답: {response.text[:200]}...")
                
        except Exception as e:
            print(f"  ✗ 에러 발생: {str(e)}")
    
    print("\n" + "=" * 80)
    print("테스트 결과 요약")
    print("=" * 80)
    print(f"태풍 베스트트랙: {'✓ 성공' if success_count > 0 else '✗ 실패'}")
    print(f"\n성공: {success_count}/{total_count}, 실패: {total_count - success_count}/{total_count}")
    
    return success_count > 0


# 메인 실행
if __name__ == "__main__":
    test_typhoon_besttrack()
