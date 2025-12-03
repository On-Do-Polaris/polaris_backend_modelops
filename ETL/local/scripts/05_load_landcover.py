"""
SKALA Physical Risk AI System - 토지피복 데이터 적재
GeoTIFF 파일에서 토지피복 래스터를 raw_landcover 테이블에 로드

데이터 소스: landcover/*.tif
대상 테이블: raw_landcover
예상 데이터: 약 200개 타일

최종 수정일: 2025-12-02
"""

import sys
import subprocess
import tempfile
import os
from pathlib import Path
from tqdm import tqdm

from utils import setup_logging, get_db_connection, get_data_dir, table_exists, get_row_count


def load_tif_to_postgres(tif_path: Path, table_name: str, append: bool = False, logger=None) -> bool:
    """
    GeoTIFF 파일을 PostgreSQL raster 테이블에 로드

    Args:
        tif_path: TIF 파일 경로
        table_name: 대상 테이블 이름
        append: True면 기존 테이블에 추가
        logger: 로거 인스턴스

    Returns:
        성공 여부
    """
    try:
        db_host = os.getenv("DW_HOST", "localhost")
        db_port = os.getenv("DW_PORT", "5434")
        db_name = os.getenv("DW_NAME", "skala_datawarehouse")
        db_user = os.getenv("DW_USER", "skala_dw_user")
        db_password = os.getenv("DW_PASSWORD", "skala_dw_2025")

        # raster2pgsql 명령 구성
        cmd = ["raster2pgsql"]
        cmd.append("-a" if append else "-c")  # append or create
        cmd.extend(["-I", "-C", "-M", "-F", "-t", "100x100", "-s", "5174"])
        cmd.extend([str(tif_path), table_name])

        raster_proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        psql_cmd = ["psql", "-h", db_host, "-p", db_port, "-U", db_user, "-d", db_name, "-q"]
        psql_env = os.environ.copy()
        if db_password:
            psql_env["PGPASSWORD"] = db_password

        psql_proc = subprocess.Popen(
            psql_cmd,
            stdin=raster_proc.stdout,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=psql_env
        )

        raster_proc.stdout.close()
        stdout, stderr = psql_proc.communicate(timeout=120)

        if psql_proc.returncode != 0:
            if logger:
                logger.warning(f"⚠️  raster2pgsql 실패: {stderr.decode()[:200]}")
            return False

        return True

    except Exception as e:
        if logger:
            logger.warning(f"⚠️  오류: {e}")
        return False


def load_landcover() -> None:
    """토지피복 GeoTIFF를 raw_landcover 테이블에 로드"""
    logger = setup_logging("load_landcover")
    logger.info("=" * 60)
    logger.info("토지피복 데이터 로딩 시작")
    logger.info("=" * 60)

    try:
        conn = get_db_connection()
        logger.info("✅ 데이터베이스 연결 성공")
    except Exception as e:
        logger.error(f"❌ 데이터베이스 연결 실패: {e}")
        sys.exit(1)

    cursor = conn.cursor()

    # TIF 파일 찾기
    data_dir = get_data_dir()
    landcover_dir = data_dir / "landcover"

    if not landcover_dir.exists():
        logger.error(f"❌ landcover 디렉토리를 찾을 수 없습니다: {landcover_dir}")
        conn.close()
        sys.exit(1)

    tif_files = list(landcover_dir.glob("**/*.tif"))
    logger.info(f"📂 {len(tif_files)}개 TIF 파일 발견")

    if not tif_files:
        logger.warning("⚠️  TIF 파일이 없습니다")
        conn.close()
        return

    # 기존 테이블 삭제 및 재생성
    existing_count = get_row_count(conn, "raw_landcover")
    if existing_count > 0:
        logger.warning(f"⚠️  기존 데이터 삭제")
        cursor.execute("DROP TABLE IF EXISTS raw_landcover CASCADE")
        conn.commit()

    conn.close()

    # TIF 파일 로드
    success_count = 0
    error_count = 0
    first_file = True

    for tif_file in tqdm(tif_files, desc="TIF 로딩"):
        success = load_tif_to_postgres(
            tif_file,
            "raw_landcover",
            append=not first_file,
            logger=logger
        )

        if success:
            success_count += 1
            first_file = False
        else:
            error_count += 1

    # 결과 확인
    conn = get_db_connection()
    final_count = get_row_count(conn, "raw_landcover")
    conn.close()

    logger.info("=" * 60)
    logger.info("✅ 토지피복 데이터 로딩 완료")
    logger.info(f"   - 성공: {success_count}개 파일")
    logger.info(f"   - 실패: {error_count}개 파일")
    logger.info(f"   - 최종: {final_count:,}개 타일")
    logger.info("=" * 60)


if __name__ == "__main__":
    load_landcover()
