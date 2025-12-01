"""
SKALA Physical Risk AI System - DEM 데이터 로딩
raster2pgsql을 사용하여 DEM ASCII 그리드 파일을 raw_dem 테이블에 로딩

최종 수정일: 2025-11-20
버전: v01

호출: load_data.sh
"""

import sys
import zipfile
import tempfile
import os
import subprocess
import re
from pathlib import Path
from tqdm import tqdm

from utils import setup_logging, get_db_connection, get_data_dir, table_exists, get_row_count


def extract_region_name(filename):
    """
    Extract region name from DEM ZIP filename

    Examples:
        (B080)공개DEM_서울특별시_ascii.zip -> 서울특별시
        (B080)공개DEM_경기도_ascii.zip -> 경기도
    """
    # Pattern: extract Korean text between _ and _ascii
    match = re.search(r'_(.+?)_ascii', filename)
    if match:
        return match.group(1)
    return "Unknown"


def load_ascii_grid_to_postgres(ascii_path, table_name, region_name, append=False, logger=None):
    """
    Load an ASCII grid file into PostgreSQL using GDAL + raster2pgsql

    Args:
        ascii_path: Path to ASCII grid file
        table_name: Target table name
        region_name: Region name for metadata
        append: If True, append to existing table
        logger: Logger instance

    Returns:
        True if successful, False otherwise
    """
    try:
        # Get DB credentials
        db_host = os.getenv("DW_HOST", "localhost")
        db_port = os.getenv("DW_PORT", "5433")
        db_name = os.getenv("DW_NAME", "skala_datawarehouse")
        db_user = os.getenv("DW_USER", "skala_dw_user")
        db_password = os.getenv("DW_PASSWORD", "skala_dev_2025")

        # First, convert ASCII grid to GeoTIFF using gdal_translate
        tmpdir = tempfile.mkdtemp()
        tif_path = os.path.join(tmpdir, "temp.tif")

        gdal_cmd = [
            "gdal_translate",
            "-of", "GTiff",
            "-a_srs", "EPSG:5174",  # Korean coordinate system
            str(ascii_path),
            tif_path
        ]

        gdal_proc = subprocess.run(
            gdal_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=60
        )

        if gdal_proc.returncode != 0:
            if logger:
                logger.warning(f"⚠️  gdal_translate failed: {gdal_proc.stderr.decode()}")
            try:
                os.remove(tif_path)
                os.rmdir(tmpdir)
            except:
                pass
            return False

        # Now load the GeoTIFF using raster2pgsql
        cmd = ["raster2pgsql"]

        if append:
            cmd.append("-a")  # Append
        else:
            cmd.append("-c")  # Create

        cmd.extend([
            "-I",  # Create index
            "-C",  # Apply constraints
            "-M",  # Vacuum
            "-F",  # Add filename
            "-t", "100x100",  # Tile size
            "-s", "5174",  # SRID
            tif_path,
            table_name
        ])

        raster_proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        psql_cmd = [
            "psql",
            "-h", db_host,
            "-p", db_port,
            "-U", db_user,
            "-d", db_name,
            "-q"
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

        # Clean up
        try:
            os.remove(tif_path)
            os.rmdir(tmpdir)
        except:
            pass

        if psql_proc.returncode != 0:
            if logger:
                logger.warning(f"⚠️  raster2pgsql failed: {stderr.decode()}")
            return False

        return True

    except Exception as e:
        if logger:
            logger.warning(f"⚠️  Error: {e}")
        return False


def load_dem():
    """
    Load DEM ASCII grid data

    Source: data/DEM/*.zip and direct files
    Target: raw_dem table
    """
    logger = setup_logging("load_dem")
    logger.info("=" * 60)
    logger.info("Loading DEM ASCII Grid Data")
    logger.info("=" * 60)

    # Get database connection
    try:
        conn = get_db_connection()
        logger.info("✅ Database connection established")
    except Exception as e:
        logger.error(f"❌ Failed to connect to database: {e}")
        sys.exit(1)

    # Check if table exists
    if not table_exists(conn, "raw_dem"):
        logger.error("❌ Table 'raw_dem' does not exist. Run create_tables.sh first.")
        conn.close()
        sys.exit(1)

    # Check if data already exists
    existing_count = get_row_count(conn, "raw_dem")
    if existing_count > 0:
        logger.warning(f"⚠️  Table already contains {existing_count} rows")
        response = input("Do you want to clear and reload? (y/N): ")
        if response.lower() != 'y':
            logger.info("Skipping load")
            conn.close()
            return

        cursor = conn.cursor()
        cursor.execute("DROP TABLE IF EXISTS raw_dem CASCADE")
        conn.commit()
        cursor.close()
        logger.info("✅ Table dropped, will recreate")

    conn.close()

    # Get data directory
    data_dir = get_data_dir()
    dem_dir = data_dir / "DEM"

    if not dem_dir.exists():
        logger.error(f"❌ DEM directory not found: {dem_dir}")
        sys.exit(1)

    # Find all ZIP files
    zip_files = list(dem_dir.glob("*.zip"))
    tif_files = list(dem_dir.glob("*.tif"))
    txt_files = list(dem_dir.glob("*.txt"))

    logger.info(f"📂 Found {len(zip_files)} ZIP files")
    logger.info(f"   Plus {len(tif_files)} TIF and {len(txt_files)} TXT files")
    logger.info("")
    logger.info("⚠️  This will use gdal_translate + raster2pgsql")
    logger.info(f"⚠️  Estimated time: ~{len(zip_files)} minutes")

    success_count = 0
    error_count = 0
    first_file = True

    # Process ZIP files
    tmpdir = tempfile.mkdtemp()

    for zip_file in tqdm(zip_files, desc="Processing ZIPs"):
        region_name = extract_region_name(zip_file.name)

        try:
            # Extract ASCII files from ZIP
            with zipfile.ZipFile(zip_file, 'r') as zf:
                txt_members = [m for m in zf.namelist() if m.endswith('.txt')]

                if not txt_members:
                    logger.warning(f"⚠️  No TXT files in {zip_file.name}")
                    error_count += 1
                    continue

                # Process each ASCII file
                for txt_member in txt_members:
                    zf.extract(txt_member, tmpdir)
                    extracted_txt = os.path.join(tmpdir, txt_member)

                    success = load_ascii_grid_to_postgres(
                        extracted_txt,
                        "raw_dem",
                        region_name,
                        append=not first_file,
                        logger=logger
                    )

                    if success:
                        success_count += 1
                        first_file = False
                    else:
                        error_count += 1

                    # Clean up
                    try:
                        os.remove(extracted_txt)
                    except:
                        pass

        except Exception as e:
            logger.warning(f"⚠️  Error processing {zip_file.name}: {e}")
            error_count += 1
            continue

    # Process direct TIF files
    for tif_file in tqdm(tif_files, desc="Processing TIFs"):
        from scripts.load_landcover import load_tif_to_postgres

        success = load_tif_to_postgres(
            tif_file,
            "raw_dem",
            append=not first_file,
            logger=logger
        )

        if success:
            success_count += 1
            first_file = False
        else:
            error_count += 1

    # Process direct TXT files (ASCII grids)
    for txt_file in tqdm(txt_files, desc="Processing TXTs"):
        success = load_ascii_grid_to_postgres(
            txt_file,
            "raw_dem",
            "Direct",
            append=not first_file,
            logger=logger
        )

        if success:
            success_count += 1
            first_file = False
        else:
            error_count += 1

    # Clean up
    try:
        os.rmdir(tmpdir)
    except:
        pass

    logger.info("")
    logger.info("=" * 60)
    logger.info(f"✅ DEM data loading complete!")
    logger.info(f"   Success: {success_count} files")
    logger.info(f"   Errors: {error_count} files")
    logger.info("=" * 60)


if __name__ == "__main__":
    load_dem()
