"""
SKALA Physical Risk AI System - Load Grid Station Mappings

데이터 소스: grid_to_nearest_stations.json
대상 테이블: grid_station_mappings (Datawarehouse)
예상 데이터: 97,377개 격자 × 3개 관측소 ≈ 292,131개 매핑

Last Modified: 2025-01-24
"""

import sys
import json
from pathlib import Path
from tqdm import tqdm
from utils import setup_logging, get_db_connection, get_data_dir, table_exists


def load_grid_station_mappings() -> None:
    """격자-관측소 매핑 데이터를 JSON 파일에서 로드하여 grid_station_mappings 테이블에 저장"""
    logger = setup_logging("load_grid_station_mappings")
    logger.info("=" * 60)
    logger.info("격자-관측소 매핑 데이터 로딩 시작")
    logger.info("=" * 60)

    # 데이터베이스 연결
    try:
        conn = get_db_connection()
        logger.info("✅ Datawarehouse 연결 성공")
    except Exception as e:
        logger.error(f"❌ 데이터베이스 연결 실패: {e}")
        sys.exit(1)

    # 테이블 존재 여부 확인
    if not table_exists(conn, "grid_station_mappings"):
        logger.error("❌ grid_station_mappings 테이블이 존재하지 않습니다")
        logger.error("   먼저 10_create_reference_data_tables.sql을 실행하세요")
        conn.close()
        sys.exit(1)

    cursor = conn.cursor()

    # JSON 파일 찾기
    data_dir = get_data_dir()
    json_file = data_dir / "grid_to_nearest_stations.json"

    if not json_file.exists():
        logger.error(f"❌ JSON 파일을 찾을 수 없습니다: {json_file}")
        conn.close()
        sys.exit(1)

    logger.info(f"📂 데이터 파일: {json_file}")

    try:
        # JSON 파일 읽기
        with open(json_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        grid_mapping = data.get("grid_mapping", {})
        grid_info = data.get("grid_info", {})

        logger.info(f"📊 격자 정보:")
        logger.info(f"   - 위도 범위: {grid_info.get('lat_min')}°N ~ {grid_info.get('lat_max')}°N")
        logger.info(f"   - 경도 범위: {grid_info.get('lon_min')}°E ~ {grid_info.get('lon_max')}°E")
        logger.info(f"   - 해상도: {grid_info.get('resolution')}°")
        logger.info(f"   - 육지 격자: {grid_info.get('n_land_grids'):,}개")
        logger.info(f"   - 총 격자: {len(grid_mapping):,}개")

        # 기존 데이터 확인
        cursor.execute("SELECT COUNT(*) FROM grid_station_mappings")
        existing_count = cursor.fetchone()[0]

        if existing_count > 0:
            logger.warning(f"⚠️  기존 데이터 {existing_count:,}개 발견")
            response = input("기존 데이터를 삭제하고 새로 로드하시겠습니까? (y/N): ")
            if response.lower() != "y":
                logger.info("작업을 취소했습니다")
                conn.close()
                return

            logger.info("🗑️  기존 데이터 삭제 중...")
            cursor.execute("DELETE FROM grid_station_mappings")
            conn.commit()
            logger.info("✅ 기존 데이터 삭제 완료")

        # 데이터 삽입 SQL
        insert_sql = """
            INSERT INTO grid_station_mappings (
                grid_lat, grid_lon, basin_code, basin_name,
                station_rank, obscd, obsnm,
                station_lat, station_lon, distance_km,
                geom
            ) VALUES (
                %s, %s, %s, %s,
                %s, %s, %s,
                %s, %s, %s,
                ST_SetSRID(ST_MakePoint(%s, %s), 4326)
            )
        """

        # 데이터 삽입
        logger.info("💾 데이터 삽입 중...")
        insert_count = 0
        error_count = 0

        # 진행률 표시를 위한 전체 매핑 수 계산
        total_mappings = sum(len(grid_data.get("nearest_stations", [])) for grid_data in grid_mapping.values())
        logger.info(f"📊 총 {total_mappings:,}개 매핑 발견")

        with tqdm(total=total_mappings, desc="매핑 로딩") as pbar:
            for grid_key, grid_data in grid_mapping.items():
                grid_lat = grid_data.get("lat")
                grid_lon = grid_data.get("lon")
                basin_code = grid_data.get("basin_code")
                basin_name = grid_data.get("basin_name")

                nearest_stations = grid_data.get("nearest_stations", [])

                # 각 관측소에 대해 순위를 매겨 저장
                for rank, station in enumerate(nearest_stations, start=1):
                    try:
                        cursor.execute(insert_sql, (
                            grid_lat,
                            grid_lon,
                            basin_code,
                            basin_name,
                            rank,
                            station.get("obscd"),
                            station.get("obsnm"),
                            station.get("lat"),
                            station.get("lon"),
                            station.get("distance_km"),
                            grid_lon,  # geom - longitude
                            grid_lat,  # geom - latitude
                        ))
                        insert_count += 1
                        pbar.update(1)

                    except Exception as e:
                        error_count += 1
                        logger.error(f"❌ 데이터 삽입 실패 (grid={grid_key}, rank={rank}): {e}")
                        if error_count > 100:
                            logger.error("❌ 오류가 너무 많아 작업을 중단합니다")
                            conn.rollback()
                            conn.close()
                            sys.exit(1)
                        pbar.update(1)

                # 주기적으로 커밋 (10,000개마다)
                if insert_count % 10000 == 0:
                    conn.commit()

        # 최종 커밋
        conn.commit()
        logger.info("✅ 데이터 삽입 완료")

        # 최종 통계
        cursor.execute("SELECT COUNT(*) FROM grid_station_mappings")
        final_count = cursor.fetchone()[0]

        cursor.execute("""
            SELECT station_rank, COUNT(*)
            FROM grid_station_mappings
            GROUP BY station_rank
            ORDER BY station_rank
        """)
        rank_stats = cursor.fetchall()

        cursor.execute("""
            SELECT basin_name, COUNT(DISTINCT CONCAT(grid_lat::TEXT, ',', grid_lon::TEXT))
            FROM grid_station_mappings
            GROUP BY basin_name
            ORDER BY COUNT(*) DESC
        """)
        basin_stats = cursor.fetchall()

        logger.info("=" * 60)
        logger.info("✅ 격자-관측소 매핑 데이터 로딩 완료")
        logger.info("=" * 60)
        logger.info(f"📊 통계:")
        logger.info(f"   - 총 매핑: {final_count:,}개")
        logger.info(f"   - 삽입 성공: {insert_count:,}개")
        logger.info(f"   - 삽입 실패: {error_count:,}개")
        logger.info("")
        logger.info("🎯 순위별 매핑 수:")
        for rank, count in rank_stats:
            logger.info(f"   - Rank {rank}: {count:,}개")
        logger.info("")
        logger.info("📍 유역별 격자 수:")
        for basin_name, count in basin_stats[:10]:  # 상위 10개만 표시
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
    load_grid_station_mappings()
