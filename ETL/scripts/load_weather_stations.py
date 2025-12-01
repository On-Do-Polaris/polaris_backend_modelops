"""
SKALA Physical Risk AI System - Load Weather Stations

데이터 소스: stations_with_coordinates.json
대상 테이블: weather_stations (Datawarehouse)
예상 데이터: 1,086개 기상 관측소

Last Modified: 2025-01-24
"""

import sys
import json
from pathlib import Path
from tqdm import tqdm
from utils import setup_logging, get_db_connection, get_data_dir, table_exists


def load_weather_stations() -> None:
    """기상 관측소 데이터를 JSON 파일에서 로드하여 weather_stations 테이블에 저장"""
    logger = setup_logging("load_weather_stations")
    logger.info("=" * 60)
    logger.info("기상 관측소 데이터 로딩 시작")
    logger.info("=" * 60)

    # 데이터베이스 연결
    try:
        conn = get_db_connection()
        logger.info("✅ Datawarehouse 연결 성공")
    except Exception as e:
        logger.error(f"❌ 데이터베이스 연결 실패: {e}")
        sys.exit(1)

    # 테이블 존재 여부 확인
    if not table_exists(conn, "weather_stations"):
        logger.error("❌ weather_stations 테이블이 존재하지 않습니다")
        logger.error("   먼저 10_create_reference_data_tables.sql을 실행하세요")
        conn.close()
        sys.exit(1)

    cursor = conn.cursor()

    # JSON 파일 찾기
    data_dir = get_data_dir()
    json_file = data_dir / "stations_with_coordinates.json"

    if not json_file.exists():
        logger.error(f"❌ JSON 파일을 찾을 수 없습니다: {json_file}")
        conn.close()
        sys.exit(1)

    logger.info(f"📂 데이터 파일: {json_file}")

    try:
        # JSON 파일 읽기
        with open(json_file, "r", encoding="utf-8") as f:
            stations = json.load(f)

        logger.info(f"📊 총 {len(stations):,}개 관측소 발견")

        # 기존 데이터 확인
        cursor.execute("SELECT COUNT(*) FROM weather_stations")
        existing_count = cursor.fetchone()[0]

        if existing_count > 0:
            logger.warning(f"⚠️  기존 데이터 {existing_count:,}개 발견")
            response = input("기존 데이터를 삭제하고 새로 로드하시겠습니까? (y/N): ")
            if response.lower() != "y":
                logger.info("작업을 취소했습니다")
                conn.close()
                return

            logger.info("🗑️  기존 데이터 삭제 중...")
            cursor.execute("DELETE FROM weather_stations")
            conn.commit()
            logger.info("✅ 기존 데이터 삭제 완료")

        # 데이터 삽입 SQL
        insert_sql = """
            INSERT INTO weather_stations (
                obscd, obsnm, bbsnnm, sbsncd, mngorg,
                minyear, maxyear, basin_code, basin_name,
                latitude, longitude, geom
            ) VALUES (
                %s, %s, %s, %s, %s,
                %s, %s, %s, %s,
                %s, %s, ST_SetSRID(ST_MakePoint(%s, %s), 4326)
            )
        """

        # 데이터 삽입
        logger.info("💾 데이터 삽입 중...")
        insert_count = 0
        error_count = 0

        skipped_count = 0
        for station in tqdm(stations, desc="관측소 로딩"):
            try:
                # 좌표가 없는 관측소는 건너뛰기
                lat = station.get("lat")
                lon = station.get("lon")
                if lat is None or lon is None:
                    skipped_count += 1
                    continue

                cursor.execute(insert_sql, (
                    station.get("obscd"),
                    station.get("obsnm"),
                    station.get("bbsnnm"),
                    station.get("sbsncd"),
                    station.get("mngorg"),
                    station.get("minyear"),
                    station.get("maxyear"),
                    station.get("basin_code"),
                    station.get("basin_name"),
                    lat,
                    lon,
                    lon,  # geom - longitude
                    station.get("lat"),  # geom - latitude
                ))
                insert_count += 1

            except Exception as e:
                error_count += 1
                logger.error(f"❌ 데이터 삽입 실패 (obscd={station.get('obscd')}): {e}")
                if error_count > 10:
                    logger.error("❌ 오류가 너무 많아 작업을 중단합니다")
                    conn.rollback()
                    conn.close()
                    sys.exit(1)

        # 커밋
        conn.commit()
        logger.info("✅ 데이터 삽입 완료")

        # 최종 통계
        cursor.execute("SELECT COUNT(*) FROM weather_stations")
        final_count = cursor.fetchone()[0]

        cursor.execute("""
            SELECT basin_name, COUNT(*)
            FROM weather_stations
            GROUP BY basin_name
            ORDER BY COUNT(*) DESC
        """)
        basin_stats = cursor.fetchall()

        logger.info("=" * 60)
        logger.info("✅ 기상 관측소 데이터 로딩 완료")
        logger.info("=" * 60)
        logger.info(f"📊 통계:")
        logger.info(f"   - 총 관측소: {final_count:,}개")
        logger.info(f"   - 삽입 성공: {insert_count:,}개")
        logger.info(f"   - 삽입 실패: {error_count:,}개")
        logger.info(f"   - 좌표 없어 건너뜀: {skipped_count:,}개")
        logger.info("")
        logger.info("📍 유역별 관측소 분포:")
        for basin_name, count in basin_stats:
            logger.info(f"   - {basin_name}: {count:,}개")
        logger.info("=" * 60)

    except Exception as e:
        logger.error(f"❌ 처리 중 오류 발생: {e}")
        conn.rollback()
        raise
    finally:
        cursor.close()
        conn.close()


if __name__ == "__main__":
    load_weather_stations()
