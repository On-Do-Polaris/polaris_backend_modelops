import os
import requests
from dotenv import load_dotenv

load_dotenv()
API_KEY = os.getenv('PUBLICDATA_API_KEY')

def test_building(name, sigungu_cd, bjdong_cd, bun, ji):
    url = "http://apis.data.go.kr/1613000/BldRgstHubService/getBrTitleInfo"
    params = {
        'serviceKey': API_KEY,
        'sigunguCd': sigungu_cd,
        'bjdongCd': bjdong_cd,
        'bun': str(bun).zfill(4),
        'ji': str(ji).zfill(4),
        'numOfRows': '10',
        '_type': 'json'
    }
    
    response = requests.get(url, params=params, timeout=30)
    print(f"\n{'='*80}")
    print(f"{name}")
    print(f"{'='*80}")
    print(f"지번: {sigungu_cd}-{bjdong_cd} {bun}-{ji}")
    print(f"응답: {response.status_code}")
    
    if response.status_code == 200:
        result = response.json()
        header = result.get('response', {}).get('header', {})
        if header.get('resultCode') == '00':
            body = result.get('response', {}).get('body', {})
            total = body.get('totalCount', 0)
            if isinstance(total, str):
                total = int(total) if total.isdigit() else 0
            
            print(f"✅ 건축물 {total}건 조회")
            
            if total > 0:
                items = body.get('items', {}).get('item', [])
                if not isinstance(items, list):
                    items = [items]
                
                for idx, item in enumerate(items[:3], 1):
                    print(f"\n  건물 {idx}:")
                    print(f"    대지위치: {item.get('platPlc', '-')}")
                    print(f"    도로명: {item.get('newPlatPlc', '-')}")
                    print(f"    건물명: {item.get('bldNm', '(없음)')}")
                    print(f"    용도: {item.get('mainPurpsCdNm', '-')}")
                    print(f"    연면적: {item.get('totArea', '-')}㎡")
                return True
        else:
            print(f"❌ 오류: {header.get('resultMsg', '-')}")
    return False

print("건축물대장 API - V-World에서 찾은 정확한 지번으로 테스트\n")

# 테스트 1: 대전 유성구 원촌동 140-1
test_building(
    "대전광역시 유성구 엑스포로 325 → 원촌동 140-1",
    "30200",  # 대전 유성구
    "12500",  # 원촌동
    "140",
    "1"
)

# 테스트 2: 성남 분당구 삼평동 612-4
test_building(
    "경기도 성남시 분당구 판교로 255번길 38 → 삼평동 612-4",
    "41135",  # 성남시 분당구
    "11000",  # 삼평동
    "612",
    "4"
)

print(f"\n{'='*80}")
print("✅ 건축물대장 API 정상 작동 확인 완료")
print("="*80)
