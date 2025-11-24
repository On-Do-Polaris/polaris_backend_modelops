"""
대덕 데이터센터(대전광역시 유성구) 관련 WAMIS 데이터 수집
- 용수이용량: 대전광역시 + 금강권역
- 유량관측소: 금강권역 내 대전 근처 관측소
"""
import requests
import json
from pathlib import Path

OUTPUT_DIR = Path(__file__).parent

def fetch_water_usage():
    """대전광역시 금강권역 용수이용량 데이터 수집"""
    url = "http://www.wamis.go.kr:8080/wamis/openapi/wks/wks_wiawtaa_lst"
    params = {
        "admcd": "30",  # 대전광역시
        "basin": "3",   # 금강
        "output": "json"
    }

    response = requests.get(url, params=params)
    data = response.json()

    output_file = OUTPUT_DIR / "daejeon_water_usage.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"용수이용량 데이터 저장: {output_file}")
    print(f"  - 레코드 수: {data.get('count', 0)}")

    return data

def fetch_flow_stations():
    """금강권역 유량 관측소 목록 수집"""
    url = "http://www.wamis.go.kr:8080/wamis/openapi/wkw/flw_dubobsif"
    params = {
        "basin": "3",  # 금강
        "output": "json"
    }

    response = requests.get(url, params=params)
    data = response.json()

    output_file = OUTPUT_DIR / "geum_river_stations.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"유량 관측소 목록 저장: {output_file}")
    print(f"  - 관측소 수: {data.get('count', 0)}")

    # 대전 근처 관측소 필터링 (갑천, 유성, 대전 관련)
    keywords = ['대전', '유성', '갑천', '관저', '도안', '둔산', '노은']
    daejeon_stations = []

    for station in data.get('list', []):
        name = station.get('obsnm', '')
        for kw in keywords:
            if kw in name:
                daejeon_stations.append(station)
                break

    if daejeon_stations:
        print(f"\n대전 근처 관측소:")
        for st in daejeon_stations:
            print(f"  - {st['obscd']}: {st['obsnm']} ({st['minyear']}-{st['maxyear']})")
    else:
        # 대전과 가까운 관측소 찾기 (서구, 중구, 유성구 근처)
        # 갑천 합류점 근처 관측소
        print("\n대전 키워드 관측소 없음. 금강 본류 관측소 중 대전 근처:")
        for station in data.get('list', []):
            name = station.get('obsnm', '')
            # 금강 본류 대전권 관측소 (공주, 부여 이전)
            if '공주' in name or '부강' in name or '세종' in name or '청원' in name:
                print(f"  - {station['obscd']}: {name} ({station['minyear']}-{station['maxyear']})")

    return data, daejeon_stations

def fetch_daily_flow(obscd: str, year: int):
    """특정 관측소의 일유량 데이터 수집"""
    url = "http://www.wamis.go.kr:8080/wamis/openapi/wkw/flw_dtdata"
    params = {
        "obscd": obscd,
        "year": str(year),
        "output": "json"
    }

    response = requests.get(url, params=params)
    data = response.json()

    return data

def fetch_multi_year_flow(obscd: str, start_year: int, end_year: int):
    """다년간 일유량 데이터 수집"""
    all_data = []

    for year in range(start_year, end_year + 1):
        print(f"  {year}년 데이터 수집 중...")
        data = fetch_daily_flow(obscd, year)

        if data.get('list'):
            for record in data['list']:
                record['year'] = year
            all_data.extend(data['list'])

    return all_data

def main():
    print("=" * 60)
    print("대덕 데이터센터 WAMIS 데이터 수집")
    print("위치: 대전광역시 유성구 엑스포로 325 (34124)")
    print("=" * 60)

    # 1. 용수이용량 데이터
    print("\n[1] 용수이용량 데이터 수집")
    water_usage = fetch_water_usage()

    # 2. 유량 관측소 목록
    print("\n[2] 금강권역 유량 관측소 목록 수집")
    stations_data, daejeon_stations = fetch_flow_stations()

    # 3. 대표 관측소 일유량 데이터 (최근 5년)
    # 대전 근처 가장 적합한 관측소 선택 (부강 또는 공주)
    # 부강(3008690)이 대전과 가장 가까움
    print("\n[3] 대표 관측소 일유량 데이터 수집")

    # 금강권역에서 대전에 가까운 관측소 찾기
    target_obs = None
    for station in stations_data.get('list', []):
        if '부강' in station.get('obsnm', ''):
            target_obs = station
            break

    if not target_obs:
        # 부강 없으면 공주
        for station in stations_data.get('list', []):
            if '공주' in station.get('obsnm', ''):
                target_obs = station
                break

    if target_obs:
        obscd = target_obs['obscd']
        print(f"선택된 관측소: {target_obs['obsnm']} ({obscd})")

        # 최근 5년 데이터
        flow_data = fetch_multi_year_flow(obscd, 2019, 2024)

        output_file = OUTPUT_DIR / f"daily_flow_{obscd}_2019_2024.json"
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump({
                "station": target_obs,
                "data": flow_data
            }, f, ensure_ascii=False, indent=2)

        print(f"일유량 데이터 저장: {output_file}")
        print(f"  - 레코드 수: {len(flow_data)}")

    # 4. 갑천(대전시내) 관측소 데이터도 수집
    print("\n[4] 갑천(대전시내) 관측소 일유량 데이터 수집")
    gapcheon_stations = [st for st in stations_data.get('list', []) if '대전' in st.get('obsnm', '')]

    # 가장 오래된 데이터가 있는 갑천 관측소 선택 (노은교 - 1986년부터)
    gapcheon_target = None
    for st in gapcheon_stations:
        if '노은교' in st.get('obsnm', ''):
            gapcheon_target = st
            break

    if not gapcheon_target and gapcheon_stations:
        gapcheon_target = gapcheon_stations[0]

    if gapcheon_target:
        obscd = gapcheon_target['obscd']
        print(f"선택된 갑천 관측소: {gapcheon_target['obsnm']} ({obscd})")

        # 최근 10년 데이터 (baseline 구축용)
        flow_data = fetch_multi_year_flow(obscd, 2014, 2024)

        output_file = OUTPUT_DIR / f"daily_flow_gapcheon_{obscd}_2014_2024.json"
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump({
                "station": gapcheon_target,
                "data": flow_data
            }, f, ensure_ascii=False, indent=2)

        print(f"갑천 일유량 데이터 저장: {output_file}")
        print(f"  - 레코드 수: {len(flow_data)}")

    print("\n" + "=" * 60)
    print("데이터 수집 완료!")
    print("=" * 60)

if __name__ == "__main__":
    main()
