"""
SKALA Physical Risk AI System - 하천정보 API ETL

API: 재난안전데이터공유플랫폼 하천정보
URL: https://www.safetydata.go.kr/V2/api/DSSP-IF-10720
용도: 홍수 위험 평가를 위한 하천 정보

최종 수정일: 2025-12-02
"""

import os
import sys
from pathlib import Path

# 상위 경로 추가
sys.path.insert(0, str(Path(__file__).parent))

from utils import (
    setup_logging,
    get_db_connection,
    get_api_key,
    APIClient,
    batch_upsert,
    get_table_count,
    API_ENDPOINTS
)


def fetch_river_info(client: APIClient, api_key: str, logger, page_no: int = 1, num_of_rows: int = 100):
    """
    하천정보 API 호출

    Args:
        client: API 클라이언트
        api_key: API 키
        logger: 로거
        page_no: 페이지 번호
        num_of_rows: 페이지당 결과 수

    Returns:
        API 응답 데이터
    """
    url = API_ENDPOINTS['river_info']
    params = {
        'serviceKey': api_key,
        'returnType': 'json',
        'pageNo': str(page_no),
        'numOfRows': str(num_of_rows)
    }

    logger.info(f"하천정보 API 호출: 페이지 {page_no}")
    return client.get(url, params=params, timeout=30)


def parse_river_data(raw_data: dict, logger) -> list:
    """
    API 응답 파싱

    Args:
        raw_data: API 응답
        logger: 로거

    Returns:
        파싱된 데이터 리스트
    """
    parsed = []

    if not raw_data:
        logger.warning("API 응답 없음")
        return parsed

    # 헤더 확인
    header = raw_data.get('header', {})
    if header.get('resultCode') != '00':
        logger.error(f"API 오류: {header.get('resultMsg')}")
        return parsed

    # 본문 데이터 추출
    body = raw_data.get('body', [])
    if not body:
        logger.warning("API 응답 body 없음")
        return parsed

    for item in body:
        try:
            record = {
                'river_code': item.get('RVR_CD', ''),
                'river_name': item.get('RVR_NM', ''),
                'river_grade': int(item.get('RVR_GRD_CD', 0) or 0),
                'watershed_area_km2': float(item.get('DRAR', 0) or 0),
                'river_length_km': float(item.get('RVR_PRLG_LEN', 0) or 0),
                'start_point': item.get('ORG_PT', ''),
                'end_point': item.get('CNFLS_PT', ''),
                'management_org': item.get('MGMT_ORG', ''),
                'basin_name': item.get('WTRSHD_NM', ''),
                'sido_name': item.get('CTPV_NM', ''),
                'sigungu_name': item.get('SGG_NM', ''),
                'api_response': item
            }

            # river_code가 없으면 river_name + grade로 생성
            if not record['river_code']:
                record['river_code'] = f"{record['river_name']}_{record['river_grade']}"

            parsed.append(record)

        except Exception as e:
            logger.warning(f"레코드 파싱 실패: {e}")
            continue

    return parsed


def load_river_info(sample_limit: int = None):
    """
    하천정보 데이터 적재

    Args:
        sample_limit: 샘플 제한 (테스트용)
    """
    logger = setup_logging("load_river_info")
    logger.info("=" * 60)
    logger.info("하천정보 API ETL 시작")
    logger.info("=" * 60)

    # API 키 확인
    api_key = get_api_key('RIVER_API_KEY')
    if not api_key:
        logger.error("RIVER_API_KEY 환경변수 필요")
        return

    # DB 연결
    conn = get_db_connection()
    logger.info("DB 연결 완료")

    # API 클라이언트
    client = APIClient(logger)

    # 데이터 수집
    all_data = []
    page_no = 1
    num_of_rows = 100

    while True:
        raw_data = fetch_river_info(client, api_key, logger, page_no, num_of_rows)
        if not raw_data:
            break

        parsed = parse_river_data(raw_data, logger)
        if not parsed:
            break

        all_data.extend(parsed)
        logger.info(f"페이지 {page_no}: {len(parsed)}건 수집 (누적: {len(all_data)}건)")

        # 샘플 제한 확인
        if sample_limit and len(all_data) >= sample_limit:
            all_data = all_data[:sample_limit]
            logger.info(f"샘플 제한 적용: {sample_limit}건")
            break

        # 더 이상 데이터가 없으면 종료
        if len(parsed) < num_of_rows:
            break

        page_no += 1

    # DB 적재
    if all_data:
        logger.info(f"총 {len(all_data)}건 DB 적재 시작")
        success_count = batch_upsert(
            conn,
            'api_river_info',
            all_data,
            unique_columns=['river_code'],
            batch_size=100
        )
        logger.info(f"DB 적재 완료: {success_count}건")
    else:
        logger.warning("적재할 데이터 없음")

    # 결과 확인
    total_count = get_table_count(conn, 'api_river_info')
    logger.info(f"api_river_info 테이블 총 레코드: {total_count}건")

    conn.close()
    logger.info("하천정보 API ETL 완료")


if __name__ == "__main__":
    # 환경변수로 샘플 제한 설정 가능
    sample_limit = int(os.getenv('SAMPLE_LIMIT', 0)) or None
    load_river_info(sample_limit=sample_limit)
