"""
SKALA Physical Risk AI System - SSP sgg261 데이터 로딩
KMA SSP 시나리오 데이터를 261개 시군구 지역에 로딩

최종 수정일: 2025-11-20
버전: v01

호출: load_data.sh
"""

import sys
import os
import gzip
import tarfile
import csv
from pathlib import Path
from datetime import datetime
from tqdm import tqdm

from utils import setup_logging, get_db_connection, get_data_dir, table_exists, get_row_count


# Variable mapping: filename → table name
VARIABLE_MAPPING = {
    # Daily variables
    "TAMAX": "tamax_data",
    "TAMIN": "tamin_data",
    # Monthly variables (if tables exist)
    "TA": None,  # Will check if table exists
    "RN": None,
    "WS": None,
    "RHM": None,
    "SI": None,
}

# SSP scenario mapping to column names
SSP_COLUMN_MAPPING = {
    "SSP126": "ssp1",
    "SSP245": "ssp2",
    "SSP370": "ssp3",
    "SSP585": "ssp5",
}


def load_sgg261_csv(csv_path, table_name, ssp_column, conn, logger):
    """
    Load sgg261 CSV file into database table

    Args:
        csv_path: Path to gzipped tar archive containing CSV file
        table_name: Target table name
        ssp_column: SSP scenario column name (ssp1, ssp2, ssp3, ssp5)
        conn: Database connection
        logger: Logger instance
    """
    # 샘플 모드 확인
    sample_limit = int(os.environ.get("SAMPLE_LIMIT", 0))
    if sample_limit > 0:
        logger.info(f"      ⚠️  샘플 모드: {sample_limit}개만 로딩합니다")

    cursor = conn.cursor()

    # Open gzipped tar archive and extract CSV
    with gzip.open(csv_path, 'rb') as gz_file:
        with tarfile.open(fileobj=gz_file, mode='r') as tar:
            # Find CSV file in tar archive (usually *.txt)
            csv_member = None
            for member in tar.getmembers():
                if member.name.endswith('.txt'):
                    csv_member = member
                    break

            if not csv_member:
                logger.error(f"      ❌ No CSV file found in {csv_path.name}")
                cursor.close()
                return

            # Extract and read CSV
            csv_file = tar.extractfile(csv_member)
            text_stream = (line.decode('utf-8') for line in csv_file)
            reader = csv.reader(text_stream)

            # Read header rows
            header1 = next(reader)  # 년-월-일, 1101000000, 1102000000, ...
            header2 = next(reader)  # 년-월-일, 서울특별시, 서울특별시, ...
            header3 = next(reader)  # 년-월-일, 종로구, 중구, ...

            # Extract admin codes and names (skip first column which is date)
            admin_codes = header1[1:]
            sido_names = header2[1:]  # 시도명
            sigungu_names = header3[1:]  # 시군구명

            logger.info(f"      Found {len(admin_codes)} sigungu regions")

            # Create admin_code → admin_id mapping
            # If admin_code doesn't exist in location_admin, create it
            admin_id_map = {}
            for idx_code, admin_code in enumerate(admin_codes):
                cursor.execute(
                    "SELECT admin_id FROM location_admin WHERE admin_code = %s",
                    (admin_code,)
                )
                result = cursor.fetchone()

                if result:
                    admin_id_map[admin_code] = result[0]
                else:
                    # Admin code doesn't exist, create it with dummy geometry
                    admin_name = sigungu_names[idx_code]
                    sido_code = admin_code[:2] if len(admin_code) >= 2 else None
                    sigungu_code = admin_code[:5] if len(admin_code) >= 5 else None

                    # Insert new admin region with dummy polygon geometry
                    # Create a small square polygon around point (0,0)
                    cursor.execute("""
                        INSERT INTO location_admin (admin_code, admin_name, level, sido_code, sigungu_code, geom, centroid)
                        VALUES (%s, %s, %s, %s, %s,
                                ST_Multi(ST_GeomFromText('POLYGON((0 0, 1 0, 1 1, 0 1, 0 0))', 5174)),
                                ST_SetSRID(ST_MakePoint(0.5, 0.5), 5174))
                        RETURNING admin_id
                    """, (admin_code, admin_name, 2, sido_code, sigungu_code))

                    new_admin_id = cursor.fetchone()[0]
                    admin_id_map[admin_code] = new_admin_id
                    conn.commit()

            logger.info(f"      Mapped {len(admin_id_map)} regions to admin_id")

            # Prepare insert/update SQL
            # Use ON CONFLICT to update if exists
            insert_sql = f"""
            INSERT INTO {table_name} (time, admin_id, {ssp_column})
            VALUES (%s, %s, %s)
            ON CONFLICT (time, admin_id)
            DO UPDATE SET {ssp_column} = EXCLUDED.{ssp_column}
            """

            batch = []
            batch_size = 10000
            row_count = 0
            total_inserted = 0

            # Read data rows
            for row in tqdm(reader, desc=f"      Loading", leave=False):
                # 샘플 모드: limit 도달 시 종료
                if sample_limit > 0 and total_inserted >= sample_limit:
                    logger.info(f"      ✅ 샘플 모드: {sample_limit}개 로딩 완료")
                    break

                date_str = row[0]  # 2021-01-01
                values = row[1:]

                # Parse date
                try:
                    obs_date = datetime.strptime(date_str, "%Y-%m-%d").date()
                except:
                    continue

                # Insert values for each admin region
                for admin_code, value_str in zip(admin_codes, values):
                    # 샘플 모드: limit 도달 시 종료
                    if sample_limit > 0 and total_inserted >= sample_limit:
                        break

                    if admin_code not in admin_id_map:
                        continue

                    try:
                        value = float(value_str)
                    except:
                        continue

                    admin_id = admin_id_map[admin_code]
                    batch.append((obs_date, admin_id, value))
                    total_inserted += 1

                    if len(batch) >= batch_size:
                        cursor.executemany(insert_sql, batch)
                        conn.commit()
                        row_count += len(batch)
                        batch = []

            # Insert remaining
            if batch:
                cursor.executemany(insert_sql, batch)
                conn.commit()
                row_count += len(batch)

    cursor.close()
    logger.info(f"      ✅ Inserted/updated {row_count:,} rows")


def load_sgg261_data():
    """
    Load SSP sgg261 data (시군구 261개 지역)

    Source: data/KMA/extracted/KMA/downloads_kma_ssp_sgg261/*/*/*.asc (gzipped CSV)
    Target: tamax_data, tamin_data, etc.
    """
    logger = setup_logging("load_sgg261_data")
    logger.info("=" * 60)
    logger.info("Loading SSP sgg261 Data (261 sigungu regions)")
    logger.info("=" * 60)

    # Get database connection
    try:
        conn = get_db_connection()
        logger.info("✅ Database connection established")
    except Exception as e:
        logger.error(f"❌ Failed to connect to database: {e}")
        sys.exit(1)

    # Get data directory
    data_dir = get_data_dir()
    sgg261_dir = data_dir / "KMA" / "extracted" / "KMA" / "downloads_kma_ssp_sgg261"

    if not sgg261_dir.exists():
        logger.error(f"❌ sgg261 directory not found: {sgg261_dir}")
        conn.close()
        sys.exit(1)

    # Process each variable
    for var_short, table_name in VARIABLE_MAPPING.items():
        if table_name is None:
            continue

        # Check if table exists (rollback first in case of previous error)
        try:
            conn.rollback()  # Ensure clean transaction state
            if not table_exists(conn, table_name):
                logger.warning(f"⚠️  Table '{table_name}' does not exist, skipping {var_short}")
                continue
        except Exception as e:
            logger.error(f"❌ Error checking table existence: {e}")
            conn.rollback()
            continue

        logger.info("")
        logger.info(f"📊 Loading {var_short} data into {table_name}...")

        # Find all sgg261 files for this variable
        sgg261_files = list(sgg261_dir.glob(f"**/*/SSP*_{var_short}_sgg261_*.asc"))

        if not sgg261_files:
            logger.warning(f"   ⚠️  No sgg261 files found for {var_short}")
            continue

        logger.info(f"   Found {len(sgg261_files)} files")

        # Process each SSP scenario file
        for sgg_file in sgg261_files:
            # Extract SSP scenario from filename
            ssp_name = sgg_file.parent.parent.name  # e.g., SSP585
            ssp_column = SSP_COLUMN_MAPPING.get(ssp_name)

            if not ssp_column:
                logger.warning(f"   ⚠️  Unknown scenario: {ssp_name}, skipping")
                continue

            logger.info(f"   Loading {ssp_name} from {sgg_file.name}...")

            try:
                load_sgg261_csv(sgg_file, table_name, ssp_column, conn, logger)
            except Exception as e:
                logger.error(f"      ❌ Error: {e}")
                # Rollback transaction on error to continue processing other files
                conn.rollback()
                continue

    conn.close()

    logger.info("")
    logger.info("=" * 60)
    logger.info("✅ SSP sgg261 data loading complete!")
    logger.info("=" * 60)


if __name__ == "__main__":
    load_sgg261_data()
