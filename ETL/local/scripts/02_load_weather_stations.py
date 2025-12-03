"""
SKALA Physical Risk AI System - 기상관측소 데이터 적재
JSON 파일에서 기상관측소 정보를 weather_stations 테이블에 로드

데이터 소스: stations_with_coordinates.json
대상 테이블: weather_stations
예상 데이터: 약 1,000개 관측소

최종 수정일: 2025-12-02
"""

import sys
import json
from pathlib import Path
from tqdm import tqdm

from utils import setup_logging, get_db_connection, get_data_dir, table_exists, get_row_count


def load_weather_stations() -> None:
    """기상관측소 JSON을 weather_stations 테이블에 로드"""
    logger = setup_logging("load_weather_stations")
    logger.info("=" * 60)
    logger.info("기상관측소 데이터 로딩 시작")
    logger.info("=" * 60)

    # 데이터베이스 연결
    try:
        conn = get_db_connection()
        logger.info("✅ 데이터베이스 연결 성공")
    except Exception as e:
        logger.error(f"❌ 데이터베이스 연결 실패: {e}")
        sys.exit(1)

    if not table_exists(conn, "weather_stations"):
        logger.error("❌ weather_stations 테이블이 존재하지 않습니다")
        conn.close()
        sys.exit(1)

    cursor = conn.cursor()

    # JSON 파일 찾기
    data_dir = get_data_dir()
    json_files = list(data_dir.glob("*stations*.json"))

    if not json_files:
        logger.error(f"❌ stations JSON 파일을 찾을 수 없습니다")
        conn.close()
        sys.exit(1)

    json_file = json_files[0]
    logger.info(f"📂 데이터 파일: {json_file.name}")

    # 기존 데이터 삭제
    existing_count = get_row_count(conn, "weather_stations")
    if existing_count > 0:
        logger.warning(f"⚠️  기존 데이터 {existing_count:,}개 삭제")
        cursor.execute("TRUNCATE TABLE weather_stations CASCADE")
        conn.commit()

    # JSON 로드
    try:
        with open(json_file, 'r', encoding='utf-8') as f:
            stations = json.load(f)
    except Exception as e:
        logger.error(f"❌ JSON 파일 읽기 실패: {e}")
        conn.close()
        sys.exit(1)

    # 데이터가 리스트인 경우와 딕셔너리인 경우 처리
    if isinstance(stations, dict):
        stations = list(stations.values())

    logger.info(f"📊 {len(stations):,}개 관측소 발견")

    # 데이터 삽입
    insert_count = 0
    error_count = 0

    for station in tqdm(stations, desc="관측소 로딩"):
        try:
            # 필드명은 JSON 구조에 따라 조정 필요
            station_id = station.get('stnId', station.get('station_id', station.get('id')))
            station_name = station.get('stnNm', station.get('station_name', station.get('name')))
            lat = station.get('lat', station.get('latitude'))
            lon = station.get('lon', station.get('longitude'))

            if not all([station_id, lat, lon]):
                continue

            cursor.execute("""
                INSERT INTO weather_stations (
                    station_id, station_name, latitude, longitude, geom
                ) VALUES (
                    %s, %s, %s, %s,
                    ST_SetSRID(ST_MakePoint(%s, %s), 4326)
                )
                ON CONFLICT (station_id) DO NOTHING
            """, (
                str(station_id), station_name,
                float(lat), float(lon),
                float(lon), float(lat)
            ))
            insert_count += 1

        except Exception as e:
            error_count += 1
            if error_count <= 5:
                logger.warning(f"⚠️  관측소 처리 오류: {e}")

    conn.commit()

    # 결과 출력
    final_count = get_row_count(conn, "weather_stations")

    logger.info("=" * 60)
    logger.info("✅ 기상관측소 데이터 로딩 완료")
    logger.info(f"   - 삽입: {insert_count:,}개")
    logger.info(f"   - 오류: {error_count:,}개")
    logger.info(f"   - 최종: {final_count:,}개")
    logger.info("=" * 60)

    cursor.close()
    conn.close()


if __name__ == "__main__":
    load_weather_stations()
