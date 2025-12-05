"""
SKALA Physical Risk AI System - 사이트 추가 데이터 적재
Excel 파일에서 판교DC 전력 및 판교캠퍼스 에너지 사용량 데이터를 로드

데이터 소스:
    - 판교dc 전력 사용량_*.xlsx
    - 판교캠퍼스_에너지 사용량_*.xlsx
대상 테이블:
    - site_additional_data (data_category: 'power')

최종 수정일: 2025-12-03
버전: v02
"""

import sys
import os
import json
import pandas as pd
from pathlib import Path
from tqdm import tqdm
from datetime import datetime

from utils import setup_logging, get_db_connection, get_data_dir, table_exists, get_row_count


# 고정 Site ID (환경변수 또는 기본값)
PANGYO_DC_SITE_ID = os.environ.get('PANGYO_DC_SITE_ID', '00000000-0000-0000-0000-000000000001')
PANGYO_CAMPUS_SITE_ID = os.environ.get('PANGYO_CAMPUS_SITE_ID', '00000000-0000-0000-0000-000000000002')


def load_dc_power() -> int:
    """
    판교DC 전력 사용량 데이터 로드

    Returns:
        int: 삽입된 레코드 수
    """
    logger = setup_logging("load_site_data")
    logger.info("판교DC 전력 데이터 로딩")

    conn = get_db_connection()
    cursor = conn.cursor()

    # Excel 파일 찾기
    data_dir = get_data_dir()
    xlsx_files = list(data_dir.glob("*판교dc*전력*.xlsx")) + list(data_dir.glob("*판교DC*전력*.xlsx"))

    if not xlsx_files:
        logger.warning("판교DC 전력 Excel 파일을 찾을 수 없습니다")
        conn.close()
        return 0

    xlsx_file = xlsx_files[0]
    logger.info(f"   파일: {xlsx_file.name}")

    # 기존 판교DC 전력 데이터 삭제
    cursor.execute("""
        DELETE FROM site_additional_data
        WHERE site_id = %s AND data_category = 'power'
    """, (PANGYO_DC_SITE_ID,))
    conn.commit()

    # Excel 읽기 (헤더가 6행째부터 시작)
    try:
        df = pd.read_excel(xlsx_file, skiprows=6)
    except Exception as e:
        logger.error(f"   Excel 읽기 실패: {e}")
        conn.close()
        return 0

    # 컬럼명 설정
    df.columns = ['idx', 'measurement_date', 'measurement_hour',
                  'it_avg', 'it_max', 'cooling_avg', 'cooling_max',
                  'lighting_avg', 'lighting_max', 'total_avg', 'total_max']

    # 측정일 채우기 (ffill)
    df['measurement_date'] = df['measurement_date'].ffill()

    # 시간대 파싱 (예: "01시" -> 1)
    df = df[df['measurement_hour'].astype(str).str.match(r'^\d+시$', na=False)]
    df['measurement_hour'] = df['measurement_hour'].astype(str).str.replace('시', '').astype(int)

    # 24시 제외 (체크 제약: 0-23)
    df = df[df['measurement_hour'] < 24]

    # 유효 데이터 필터
    df = df.dropna(subset=['it_avg', 'total_avg'])

    # 날짜 변환 (오류 무시)
    df['measurement_date'] = pd.to_datetime(df['measurement_date'], errors='coerce')
    df = df.dropna(subset=['measurement_date'])  # 변환 실패한 행 제거
    df['measurement_year'] = df['measurement_date'].dt.year
    df['measurement_month'] = df['measurement_date'].dt.month

    logger.info(f"   유효 행: {len(df):,}개")

    # 월별 집계하여 저장 (시간별 데이터는 너무 많아서 월별 합계로)
    monthly_df = df.groupby(['measurement_year', 'measurement_month']).agg({
        'it_avg': 'sum',
        'cooling_avg': 'sum',
        'lighting_avg': 'sum',
        'total_avg': 'sum'
    }).reset_index()

    # 전체 데이터를 JSONB로 저장
    power_data = {
        'data_type': 'dc_power',
        'site_name': '판교DC',
        'monthly_data': [],
        'total_records': len(df),
        'date_range': {
            'start': df['measurement_date'].min().strftime('%Y-%m-%d'),
            'end': df['measurement_date'].max().strftime('%Y-%m-%d')
        }
    }

    for _, row in monthly_df.iterrows():
        power_data['monthly_data'].append({
            'year': int(row['measurement_year']),
            'month': int(row['measurement_month']),
            'it_power_kwh': float(row['it_avg']),
            'cooling_power_kwh': float(row['cooling_avg']),
            'lighting_power_kwh': float(row['lighting_avg']) if pd.notna(row['lighting_avg']) else 0,
            'total_power_kwh': float(row['total_avg'])
        })

    # site_additional_data에 삽입
    try:
        cursor.execute("""
            INSERT INTO site_additional_data (
                site_id, data_category, structured_data,
                metadata, uploaded_at
            ) VALUES (%s, %s, %s, %s, NOW())
            ON CONFLICT (site_id, data_category)
            DO UPDATE SET
                structured_data = EXCLUDED.structured_data,
                metadata = EXCLUDED.metadata,
                uploaded_at = NOW()
        """, (
            PANGYO_DC_SITE_ID,
            'power',
            json.dumps(power_data, ensure_ascii=False),
            json.dumps({
                'source': '판교DC 전력 사용량 Excel',
                'file_name': xlsx_file.name,
                'loaded_at': datetime.now().isoformat()
            }, ensure_ascii=False)
        ))
        conn.commit()
        insert_count = 1
    except Exception as e:
        logger.error(f"   삽입 오류: {e}")
        insert_count = 0

    cursor.close()
    conn.close()

    logger.info(f"   site_additional_data (power - 판교DC): {len(monthly_df)}개월 데이터 저장")
    return insert_count


def load_campus_energy() -> int:
    """
    판교캠퍼스 에너지 사용량 데이터 로드

    Returns:
        int: 삽입된 레코드 수
    """
    logger = setup_logging("load_site_data")
    logger.info("판교캠퍼스 에너지 데이터 로딩")

    conn = get_db_connection()
    cursor = conn.cursor()

    # Excel 파일 찾기
    data_dir = get_data_dir()
    xlsx_files = list(data_dir.glob("*판교캠퍼스*에너지*.xlsx"))

    if not xlsx_files:
        logger.warning("판교캠퍼스 에너지 Excel 파일을 찾을 수 없습니다")
        conn.close()
        return 0

    xlsx_file = xlsx_files[0]
    logger.info(f"   파일: {xlsx_file.name}")

    # 기존 판교캠퍼스 에너지 데이터 삭제
    cursor.execute("""
        DELETE FROM site_additional_data
        WHERE site_id = %s AND data_category = 'power'
    """, (PANGYO_CAMPUS_SITE_ID,))
    conn.commit()

    # 시트 목록 확인
    xl = pd.ExcelFile(xlsx_file)
    logger.info(f"   시트: {xl.sheet_names}")

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

    # 전체 데이터를 JSONB로 저장
    energy_data = {
        'data_type': 'campus_energy',
        'site_name': '판교캠퍼스',
        'monthly_data': []
    }

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
        for month in range(1, 13):
            col_idx = month + 1  # 컬럼 2=1월, 3=2월, ...

            water_usage = safe_float(df.iloc[2, col_idx])
            water_cost = safe_float(df.iloc[6, col_idx])
            gas_usage = safe_float(df.iloc[21, col_idx])
            gas_cost = safe_float(df.iloc[27, col_idx])
            power_usage = safe_float(df.iloc[30, col_idx])
            power_cost = safe_float(df.iloc[41, col_idx])

            # 유효한 데이터만 추가
            if power_usage > 0 or water_usage > 0 or gas_usage > 0:
                energy_data['monthly_data'].append({
                    'year': year,
                    'month': month,
                    'total_power_kwh': power_usage,
                    'water_usage_m3': water_usage,
                    'gas_usage_m3': gas_usage,
                    'power_cost_krw': safe_int(power_cost),
                    'water_cost_krw': safe_int(water_cost),
                    'gas_cost_krw': safe_int(gas_cost)
                })

    # 날짜 범위 계산
    if energy_data['monthly_data']:
        years = [d['year'] for d in energy_data['monthly_data']]
        energy_data['date_range'] = {
            'start_year': min(years),
            'end_year': max(years)
        }
        energy_data['total_records'] = len(energy_data['monthly_data'])

    # site_additional_data에 삽입
    try:
        cursor.execute("""
            INSERT INTO site_additional_data (
                site_id, data_category, structured_data,
                metadata, uploaded_at
            ) VALUES (%s, %s, %s, %s, NOW())
            ON CONFLICT (site_id, data_category)
            DO UPDATE SET
                structured_data = EXCLUDED.structured_data,
                metadata = EXCLUDED.metadata,
                uploaded_at = NOW()
        """, (
            PANGYO_CAMPUS_SITE_ID,
            'power',
            json.dumps(energy_data, ensure_ascii=False),
            json.dumps({
                'source': '판교캠퍼스 에너지사용량 Excel',
                'file_name': xlsx_file.name,
                'loaded_at': datetime.now().isoformat()
            }, ensure_ascii=False)
        ))
        conn.commit()
        insert_count = 1
    except Exception as e:
        logger.error(f"   삽입 오류: {e}")
        insert_count = 0

    cursor.close()
    conn.close()

    logger.info(f"   site_additional_data (power - 판교캠퍼스): {len(energy_data['monthly_data'])}개월 데이터 저장")
    return insert_count


def load_site_data() -> None:
    """전체 사이트 데이터 로드"""
    logger = setup_logging("load_site_data")
    logger.info("=" * 60)
    logger.info("사이트 추가 데이터 로딩 시작")
    logger.info("=" * 60)

    # DB 연결 테스트
    try:
        conn = get_db_connection()
        logger.info("데이터베이스 연결 성공")
    except Exception as e:
        logger.error(f"데이터베이스 연결 실패: {e}")
        sys.exit(1)

    # 테이블 존재 확인
    if not table_exists(conn, "site_additional_data"):
        logger.error("site_additional_data 테이블이 존재하지 않습니다")
        conn.close()
        sys.exit(1)

    conn.close()

    # 판교DC 전력 로드
    dc_count = load_dc_power()

    # 판교캠퍼스 에너지 로드
    campus_count = load_campus_energy()

    # 결과 출력
    logger.info("=" * 60)
    logger.info("사이트 추가 데이터 로딩 완료")
    logger.info(f"   - 판교DC 전력 데이터: {dc_count}개 레코드")
    logger.info(f"   - 판교캠퍼스 에너지 데이터: {campus_count}개 레코드")
    logger.info("=" * 60)


if __name__ == "__main__":
    load_site_data()
