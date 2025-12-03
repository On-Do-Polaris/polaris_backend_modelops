"""
SKALA Physical Risk AI System - DEM 데이터 적재
ZIP 파일에서 ASCII DEM을 추출하여 raw_dem 테이블에 로드

데이터 소스: DEM/*.zip (ASCII XYZ 포맷)
대상 테이블: raw_dem (Point geometry)
예상 데이터: 약 500,000개 포인트

최종 수정일: 2025-12-02
"""

import sys
import zipfile
import re
from pathlib import Path
from tqdm import tqdm

from utils import setup_logging, get_db_connection, get_data_dir, table_exists, get_row_count


def extract_zip_with_korean(zip_path: Path, extract_dir: Path) -> list:
    """
    한글 파일명이 포함된 ZIP 파일 압축 해제

    Args:
        zip_path: ZIP 파일 경로
        extract_dir: 압축 해제 디렉토리

    Returns:
        추출된 파일 경로 리스트
    """
    extracted_files = []

    try:
        with zipfile.ZipFile(zip_path, 'r') as zf:
            for info in zf.infolist():
                try:
                    # CP437 → EUC-KR 변환 (한글 인코딩 문제 해결)
                    decoded_name = info.filename.encode('cp437').decode('euc-kr')
                except:
                    decoded_name = info.filename

                info.filename = decoded_name
                extracted_path = extract_dir / decoded_name
                zf.extract(info, extract_dir)
                extracted_files.append(extracted_path)

    except Exception as e:
        raise Exception(f"ZIP 압축 해제 실패: {e}")

    return extracted_files


def load_dem() -> None:
    """DEM ASCII 데이터를 raw_dem 테이블에 로드 (Point geometry)"""
    logger = setup_logging("load_dem")
    logger.info("=" * 60)
    logger.info("DEM 데이터 로딩 시작")
    logger.info("=" * 60)

    try:
        conn = get_db_connection()
        logger.info("✅ 데이터베이스 연결 성공")
    except Exception as e:
        logger.error(f"❌ 데이터베이스 연결 실패: {e}")
        sys.exit(1)

    cursor = conn.cursor()

    # ZIP 파일 찾기
    data_dir = get_data_dir()
    dem_dir = data_dir / "DEM"

    if not dem_dir.exists():
        logger.error(f"❌ DEM 디렉토리를 찾을 수 없습니다: {dem_dir}")
        conn.close()
        sys.exit(1)

    zip_files = list(dem_dir.glob("*.zip"))
    logger.info(f"📂 {len(zip_files)}개 ZIP 파일 발견")

    if not zip_files:
        logger.warning("⚠️  ZIP 파일이 없습니다")
        conn.close()
        return

    # 테이블 재생성 (Point geometry 기반)
    logger.info("📊 테이블 재생성 (Point geometry)")
    cursor.execute("DROP TABLE IF EXISTS raw_dem CASCADE;")
    cursor.execute("""
        CREATE TABLE raw_dem (
            rid SERIAL PRIMARY KEY,
            x DOUBLE PRECISION NOT NULL,
            y DOUBLE PRECISION NOT NULL,
            elevation DOUBLE PRECISION NOT NULL,
            region VARCHAR(100),
            geom GEOMETRY(Point, 5174)
        );
    """)
    conn.commit()

    # 임시 디렉토리
    import tempfile
    tmp_dir = Path(tempfile.mkdtemp())

    insert_count = 0
    error_count = 0
    batch_data = []
    batch_size = 10000

    for zip_file in tqdm(zip_files, desc="ZIP 처리"):
        # 지역명 추출
        match = re.search(r'_(.+?)_ascii', zip_file.name)
        region_name = match.group(1) if match else "Unknown"

        try:
            # ZIP 압축 해제
            extracted_files = extract_zip_with_korean(zip_file, tmp_dir)
            txt_files = [f for f in extracted_files if str(f).endswith('.txt')]

            for txt_file in txt_files:
                try:
                    with open(txt_file, 'r', encoding='utf-8') as f:
                        for line in f:
                            parts = line.strip().split()
                            if len(parts) >= 3:
                                try:
                                    x, y, z = float(parts[0]), float(parts[1]), float(parts[2])
                                    batch_data.append((x, y, z, region_name, x, y))

                                    if len(batch_data) >= batch_size:
                                        cursor.executemany("""
                                            INSERT INTO raw_dem (x, y, elevation, region, geom)
                                            VALUES (%s, %s, %s, %s, ST_SetSRID(ST_MakePoint(%s, %s), 5174))
                                        """, batch_data)
                                        insert_count += len(batch_data)
                                        batch_data = []
                                        conn.commit()
                                except ValueError:
                                    continue

                    # 파일 삭제
                    txt_file.unlink()

                except Exception as e:
                    error_count += 1
                    if error_count <= 5:
                        logger.warning(f"⚠️  파일 처리 오류: {e}")

        except Exception as e:
            error_count += 1
            logger.warning(f"⚠️  ZIP 처리 오류 ({zip_file.name}): {e}")

    # 남은 배치 처리
    if batch_data:
        cursor.executemany("""
            INSERT INTO raw_dem (x, y, elevation, region, geom)
            VALUES (%s, %s, %s, %s, ST_SetSRID(ST_MakePoint(%s, %s), 5174))
        """, batch_data)
        insert_count += len(batch_data)
        conn.commit()

    # 인덱스 생성
    logger.info("📊 인덱스 생성")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_raw_dem_geom ON raw_dem USING GIST (geom);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_raw_dem_region ON raw_dem (region);")
    conn.commit()

    # 임시 디렉토리 정리
    try:
        import shutil
        shutil.rmtree(tmp_dir)
    except:
        pass

    # 결과 확인
    final_count = get_row_count(conn, "raw_dem")

    logger.info("=" * 60)
    logger.info("✅ DEM 데이터 로딩 완료")
    logger.info(f"   - 삽입: {insert_count:,}개 포인트")
    logger.info(f"   - 오류: {error_count:,}개")
    logger.info(f"   - 최종: {final_count:,}개")
    logger.info("=" * 60)

    cursor.close()
    conn.close()


if __name__ == "__main__":
    load_dem()
