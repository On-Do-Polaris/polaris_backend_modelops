"""
SKALA Physical Risk AI System - 토지피복 데이터 로딩
raster2pgsql을 사용하여 토지피복 TIF 래스터를 raw_landcover 테이블에 로딩

최종 수정일: 2025-11-20
버전: v02

호출: load_data.sh
"""

import sys
import zipfile
import tempfile
import os
import subprocess
from pathlib import Path
from tqdm import tqdm

from utils import setup_logging, get_db_connection, get_data_dir, table_exists, get_row_count


def load_tif_to_postgres(tif_path, table_name, append=False, logger=None):
    """
    Load a TIF file into PostgreSQL using raster2pgsql

    Args:
        tif_path: Path to TIF file
        table_name: Target table name
        append: If True, append to existing table; else create new
        logger: Logger instance

    Returns:
        True if successful, False otherwise
    """
    try:
        # Get DB credentials from environment
        db_host = os.getenv("DW_HOST", "localhost")
        db_port = os.getenv("DW_PORT", "5433")
        db_name = os.getenv("DW_NAME", "skala_datawarehouse")
        db_user = os.getenv("DW_USER", "skala_dw_user")
        db_password = os.getenv("DW_PASSWORD", "skala_dev_2025")

        # Build raster2pgsql command
        cmd = ["raster2pgsql"]

        if append:
            cmd.append("-a")  # Append mode
        else:
            cmd.append("-c")  # Create mode (drop and recreate table)

        cmd.extend([
            "-I",  # Create spatial index
            "-C",  # Apply raster constraints
            "-M",  # Vacuum analyze
            "-F",  # Add filename column
            "-t", "100x100",  # Tile size
            "-s", "5174",  # SRID (Korean coordinate system)
            str(tif_path),
            table_name
        ])

        # Run raster2pgsql
        raster_proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        # Pipe to psql
        psql_cmd = [
            "psql",
            "-h", db_host,
            "-p", db_port,
            "-U", db_user,
            "-d", db_name,
            "-q"  # Quiet mode
        ]

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
        stdout, stderr = psql_proc.communicate()

        if psql_proc.returncode != 0:
            if logger:
                logger.warning(f"⚠️  raster2pgsql failed: {stderr.decode()}")
            return False

        return True

    except Exception as e:
        if logger:
            logger.warning(f"⚠️  Error: {e}")
        return False


def load_landcover():
    """
    Load landcover raster data from TIF files

    Source: data/landcover/ME_GROUNDCOVERAGE_50000/*.zip and *.tif
    Target: raw_landcover table
    """
    logger = setup_logging("load_landcover")
    logger.info("=" * 60)
    logger.info("Loading Landcover Raster Data")
    logger.info("=" * 60)

    # Get database connection
    try:
        conn = get_db_connection()
        logger.info("✅ Database connection established")
    except Exception as e:
        logger.error(f"❌ Failed to connect to database: {e}")
        sys.exit(1)

    # Check if table exists
    if not table_exists(conn, "raw_landcover"):
        logger.error("❌ Table 'raw_landcover' does not exist. Run create_tables.sh first.")
        conn.close()
        sys.exit(1)

    # Check if data already exists
    existing_count = get_row_count(conn, "raw_landcover")
    if existing_count > 0:
        logger.warning(f"⚠️  Table already contains {existing_count} rows")
        response = input("Do you want to clear and reload? (y/N): ")
        if response.lower() != 'y':
            logger.info("Skipping load")
            conn.close()
            return

        cursor = conn.cursor()
        cursor.execute("DROP TABLE IF EXISTS raw_landcover CASCADE")
        conn.commit()
        cursor.close()
        logger.info("✅ Table dropped, will recreate")

    conn.close()

    # Get data directory
    data_dir = get_data_dir()
    landcover_dir = data_dir / "landcover" / "ME_GROUNDCOVERAGE_50000"

    if not landcover_dir.exists():
        logger.error(f"❌ Landcover directory not found: {landcover_dir}")
        sys.exit(1)

    # Find all ZIP and TIF files
    zip_files = list(landcover_dir.glob("*.zip"))
    tif_files = list(landcover_dir.glob("*.tif"))

    total_files = len(zip_files) + len(tif_files)
    logger.info(f"📂 Found {len(zip_files)} ZIP files and {len(tif_files)} TIF files")
    logger.info(f"   Total: {total_files} files to process")
    logger.info("")
    logger.info("⚠️  This will use raster2pgsql to load raster data")
    logger.info("⚠️  Estimated time: ~{} minutes".format(total_files // 10))

    success_count = 0
    error_count = 0
    first_file = True

    # Process direct TIF files first
    for tif_file in tqdm(tif_files, desc="Loading TIF"):
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

    # Process ZIP files
    tmpdir = tempfile.mkdtemp()

    for zip_file in tqdm(zip_files, desc="Loading ZIP"):
        try:
            # Extract TIF from ZIP
            with zipfile.ZipFile(zip_file, 'r') as zf:
                tif_members = [m for m in zf.namelist() if m.endswith('.tif')]
                if not tif_members:
                    logger.warning(f"⚠️  No TIF found in {zip_file.name}")
                    error_count += 1
                    continue

                # Extract first TIF
                tif_name = tif_members[0]
                zf.extract(tif_name, tmpdir)
                extracted_tif = os.path.join(tmpdir, tif_name)

            # Load to PostgreSQL
            success = load_tif_to_postgres(
                extracted_tif,
                "raw_landcover",
                append=not first_file,
                logger=logger
            )

            if success:
                success_count += 1
                first_file = False
            else:
                error_count += 1

            # Clean up extracted file
            try:
                os.remove(extracted_tif)
            except:
                pass

        except Exception as e:
            logger.warning(f"⚠️  Error processing {zip_file.name}: {e}")
            error_count += 1
            continue

    # Clean up temp directory
    try:
        os.rmdir(tmpdir)
    except:
        pass

    logger.info("")
    logger.info("=" * 60)
    logger.info(f"✅ Landcover data loading complete!")
    logger.info(f"   Success: {success_count} files")
    logger.info(f"   Errors: {error_count} files")
    logger.info("=" * 60)


if __name__ == "__main__":
    load_landcover()
