"""
SKALA Physical Risk AI System - 사이트 데이터 적재
Excel 파일에서 판교DC 전력 및 판교캠퍼스 에너지 사용량 데이터를 로드

데이터 소스:
    - 판교dc 전력 사용량_*.xlsx
    - 판교캠퍼스_에너지 사용량_*.xlsx
대상 테이블:
    - site_dc_power_usage
    - site_campus_energy_usage

최종 수정일: 2025-12-02
"""

import sys
import pandas as pd
from pathlib import Path
from tqdm import tqdm
from datetime import datetime

from utils import setup_logging, get_db_connection, get_data_dir, table_exists, get_row_count


# 고정 Site ID (UUID)
PANGYO_DC_SITE_ID = '00000000-0000-0000-0000-000000000001'
PANGYO_CAMPUS_SITE_ID = '00000000-0000-0000-0000-000000000002'


def load_dc_power() -> int:
    """판교DC 전력 사용량 데이터 로드"""
    logger = setup_logging("load_site_data")
    logger.info("\n📊 판교DC 전력 데이터 로딩")

    conn = get_db_connection()
    cursor = conn.cursor()

    # Excel 파일 찾기
    data_dir = get_data_dir()
    xlsx_files = list(data_dir.glob("*판교dc*전력*.xlsx")) + list(data_dir.glob("*판교DC*전력*.xlsx"))

    if not xlsx_files:
        logger.warning("⚠️  판교DC 전력 Excel 파일을 찾을 수 없습니다")
        conn.close()
        return 0

    xlsx_file = xlsx_files[0]
    logger.info(f"   파일: {xlsx_file.name}")

    # 기존 데이터 삭제
    cursor.execute("TRUNCATE TABLE site_dc_power_usage")
    conn.commit()

    # Excel 읽기 (헤더가 6행째부터 시작)
    try:
        df = pd.read_excel(xlsx_file, skiprows=6)
    except Exception as e:
        logger.error(f"   ❌ Excel 읽기 실패: {e}")
        conn.close()
        return 0

    # 컬럼명 설정
    df.columns = ['idx', 'measurement_date', 'measurement_hour',
                  'it_avg', 'it_max', 'cooling_avg', 'cooling_max',
                  'lighting_avg', 'lighting_max', 'total_avg', 'total_max']

    # 측정일 채우기 (ffill)
    df['measurement_date'] = df['measurement_date'].ffill()

    # 시간대 파싱 (예: "01시" -> 1)
    df['hour_str'] = df['measurement_hour']
    df = df[df['measurement_hour'].astype(str).str.match(r'^\d+시$', na=False)]
    df['measurement_hour'] = df['measurement_hour'].astype(str).str.replace('시', '').astype(int)

    # 24시 제외 (체크 제약: 0-23)
    df = df[df['measurement_hour'] < 24]

    # 유효 데이터 필터
    df = df.dropna(subset=['it_avg', 'total_avg'])

    # 날짜 변환
    df['measurement_date'] = pd.to_datetime(df['measurement_date'])
    df['measurement_year'] = df['measurement_date'].dt.year
    df['measurement_month'] = df['measurement_date'].dt.month

    logger.info(f"   유효 행: {len(df):,}개")

    # 데이터 삽입
    insert_count = 0

    for _, row in tqdm(df.iterrows(), total=len(df), desc="   DC 전력"):
        try:
            cursor.execute("""
                INSERT INTO site_dc_power_usage (
                    site_id, it_power_kwh, cooling_power_kwh, lighting_power_kwh,
                    total_power_kwh, measurement_year, measurement_month,
                    measurement_date, measurement_hour, data_source
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                PANGYO_DC_SITE_ID,
                float(row['it_avg']),
                float(row['cooling_avg']),
                float(row['lighting_avg']) if pd.notna(row['lighting_avg']) else 0,
                float(row['total_avg']),
                int(row['measurement_year']),
                int(row['measurement_month']),
                row['measurement_date'].date(),
                int(row['measurement_hour']),
                '판교DC 전력 사용량 Excel'
            ))
            insert_count += 1

            if insert_count % 1000 == 0:
                conn.commit()

        except Exception as e:
            if insert_count < 5:
                logger.warning(f"   ⚠️  삽입 오류: {e}")

    conn.commit()
    cursor.close()
    conn.close()

    logger.info(f"   ✅ site_dc_power_usage: {insert_count:,}개")
    return insert_count


def load_campus_energy() -> int:
    """판교캠퍼스 에너지 사용량 데이터 로드"""
    logger = setup_logging("load_site_data")
    logger.info("\n📊 판교캠퍼스 에너지 데이터 로딩")

    conn = get_db_connection()
    cursor = conn.cursor()

    # Excel 파일 찾기
    data_dir = get_data_dir()
    xlsx_files = list(data_dir.glob("*판교캠퍼스*에너지*.xlsx"))

    if not xlsx_files:
        logger.warning("⚠️  판교캠퍼스 에너지 Excel 파일을 찾을 수 없습니다")
        conn.close()
        return 0

    xlsx_file = xlsx_files[0]
    logger.info(f"   파일: {xlsx_file.name}")

    # 기존 데이터 삭제
    cursor.execute("TRUNCATE TABLE site_campus_energy_usage")
    conn.commit()

    # 시트 목록 확인
    xl = pd.ExcelFile(xlsx_file)
    logger.info(f"   시트: {xl.sheet_names}")

    insert_count = 0

    def safe_float(val, default=0):
        try:
            if pd.isna(val):
                return default
            return float(val)
        except:
            return default

    def safe_int(val, default=None):
        try:
            if pd.isna(val) or val == 0:
                return default
            return int(float(val))
        except:
            return default

    # 연도별 시트 처리
    for sheet_name in xl.sheet_names:
        if '에너지' not in sheet_name:
            continue

        # 연도 추출
        year = None
        for y in range(2020, 2030):
            if str(y) in sheet_name:
                year = y
                break

        if not year:
            continue

        df = pd.read_excel(xlsx_file, sheet_name=sheet_name, header=None)

        # 데이터 추출 (행 인덱스는 Excel 구조에 따라 조정)
        # Row 2: 수도 사용량(ton)
        # Row 6: 수도 요금
        # Row 21: 가스 사용량(㎥)
        # Row 27: 가스 요금 합계
        # Row 30: 전기 사용량(kWh)
        # Row 41: 전기 요금 합계

        for month in range(1, 13):
            col_idx = month + 1  # 컬럼 2=1월, 3=2월, ...

            water_usage = safe_float(df.iloc[2, col_idx])
            water_cost = safe_float(df.iloc[6, col_idx])
            gas_usage = safe_float(df.iloc[21, col_idx])
            gas_cost = safe_float(df.iloc[27, col_idx])
            power_usage = safe_float(df.iloc[30, col_idx])
            power_cost = safe_float(df.iloc[41, col_idx])

            # 유효한 데이터만 삽입
            if power_usage > 0 or water_usage > 0 or gas_usage > 0:
                try:
                    cursor.execute("""
                        INSERT INTO site_campus_energy_usage (
                            site_id, total_power_kwh, water_usage_m3, gas_usage_m3,
                            power_cost_krw, water_cost_krw, gas_cost_krw,
                            measurement_year, measurement_month, data_source
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """, (
                        PANGYO_CAMPUS_SITE_ID,
                        power_usage,
                        water_usage,
                        gas_usage,
                        safe_int(power_cost),
                        safe_int(water_cost),
                        safe_int(gas_cost),
                        year,
                        month,
                        '판교캠퍼스 에너지사용량 Excel'
                    ))
                    insert_count += 1
                except Exception as e:
                    if insert_count < 5:
                        logger.warning(f"   ⚠️  삽입 오류: {e}")

    conn.commit()
    cursor.close()
    conn.close()

    logger.info(f"   ✅ site_campus_energy_usage: {insert_count}개")
    return insert_count


def load_site_data() -> None:
    """전체 사이트 데이터 로드"""
    logger = setup_logging("load_site_data")
    logger.info("=" * 60)
    logger.info("사이트 데이터 로딩 시작")
    logger.info("=" * 60)

    # DB 연결 테스트
    try:
        conn = get_db_connection()
        logger.info("✅ 데이터베이스 연결 성공")
        conn.close()
    except Exception as e:
        logger.error(f"❌ 데이터베이스 연결 실패: {e}")
        sys.exit(1)

    # 판교DC 전력 로드
    dc_count = load_dc_power()

    # 판교캠퍼스 에너지 로드
    campus_count = load_campus_energy()

    # 결과 출력
    logger.info("\n" + "=" * 60)
    logger.info("✅ 사이트 데이터 로딩 완료")
    logger.info(f"   - site_dc_power_usage: {dc_count:,}개")
    logger.info(f"   - site_campus_energy_usage: {campus_count}개")
    logger.info("=" * 60)


if __name__ == "__main__":
    load_site_data()
