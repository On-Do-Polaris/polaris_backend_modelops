"""
SKALA Physical Risk AI System - 건축물대장 API ETL

API: 국토교통부 건축물대장정보 서비스
URL: https://apis.data.go.kr/1613000/BldRgstHubService
용도: 건물 구조, 연식, 층수 정보

최종 수정일: 2025-12-03
버전: v01
"""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from utils import (
    setup_logging,
    get_db_connection,
    get_api_key,
    APIClient,
    batch_upsert,
    get_table_count
)


def fetch_building_info(client: APIClient, api_key: str, logger, sigungu_cd: str, bjdong_cd: str):
    """건축물 표제부 조회"""
    url = "https://apis.data.go.kr/1613000/BldRgstHubService/getBrTitleInfo"
    params = {
        'serviceKey': api_key,
        'sigunguCd': sigungu_cd,
        'bjdongCd': bjdong_cd,
        'numOfRows': '100',
        'pageNo': '1',
        '_type': 'json'
    }

    logger.info(f"건축물대장 API 호출: {sigungu_cd}-{bjdong_cd}")
    return client.get(url, params=params, timeout=30)


def parse_building_data(raw_data: dict, logger) -> list:
    """API 응답 파싱"""
    parsed = []

    if not raw_data:
        return parsed

    response = raw_data.get('response', {})
    body = response.get('body', {})
    items = body.get('items', {}).get('item', [])

    if isinstance(items, dict):
        items = [items]

    for item in items:
        try:
            # 테이블 스키마에 맞게 컬럼 매핑
            use_apr_day = item.get('useAprDay', '')
            pmsday = item.get('pmsDay', '')

            record = {
                'mgm_bld_pk': str(item.get('mgmBldrgstPk', '')),
                'platgb_cd': item.get('platGbCd', ''),
                'sigungu_cd': item.get('sigunguCd', ''),
                'bjdong_cd': item.get('bjdongCd', ''),
                'bun': item.get('bun', ''),
                'ji': item.get('ji', ''),
                'na_ugrnd_cd': item.get('naUgrndCd', ''),
                'na_bjdong_nm': item.get('naBjdongNm', ''),
                'na_road_nm': item.get('naRoadNm', ''),
                'dong_nm': item.get('dongNm', ''),
                'ho_nm': item.get('hoNm', ''),
                'main_atch_gb_cd': item.get('mainAtchGbCd', ''),
                'strct_cd': item.get('strctCd', ''),
                'strct_nm': item.get('strctCdNm', ''),
                'etc_purps': item.get('etcPurps', ''),
                'main_purp_cd': item.get('mainPurpsCd', ''),
                'main_purp_cd_nm': item.get('mainPurpsCdNm', ''),
                'use_apr_day': use_apr_day[:10] if use_apr_day and len(use_apr_day) >= 8 else None,
                'pmsday': pmsday[:10] if pmsday and len(pmsday) >= 8 else None,
                'plat_area': float(item.get('platArea', 0) or 0),
                'arch_area': float(item.get('archArea', 0) or 0),
                'bc_rat': float(item.get('bcRat', 0) or 0),
                'tot_area': float(item.get('totArea', 0) or 0),
                'vlr_rat': float(item.get('vlRat', 0) or 0),  # 스키마: vlr_rat (용적률)
                'grnd_flr_cnt': int(item.get('grndFlrCnt', 0) or 0),
                'ugrnd_flr_cnt': int(item.get('ugrndFlrCnt', 0) or 0),
                'heit': float(item.get('heit', 0) or 0),
                # hh_cnt, fmlr_cnt, rnum 컬럼은 스키마에 없음 (제거됨)
                'api_response': item
            }

            if record['mgm_bld_pk']:
                parsed.append(record)

        except Exception as e:
            logger.warning(f"레코드 파싱 실패: {e}")
            continue

    return parsed


def load_building_data(sample_limit: int = None):
    """건축물대장 데이터 적재"""
    logger = setup_logging("load_buildings")
    logger.info("=" * 60)
    logger.info("건축물대장 API ETL 시작")
    logger.info("=" * 60)

    api_key = get_api_key('PUBLICDATA_API_KEY')
    if not api_key:
        logger.error("PUBLICDATA_API_KEY 환경변수 필요")
        return

    conn = get_db_connection()
    logger.info("DB 연결 완료")

    client = APIClient(logger)

    # 주요 시군구 코드 (서울 종로구, 강남구, 부산 해운대구 등)
    test_areas = [
        ('11110', '10100'),  # 서울 종로구 청운동
        ('11680', '10100'),  # 서울 강남구 역삼동
        ('26350', '10100'),  # 부산 해운대구 우동
    ]

    all_data = []
    for sigungu_cd, bjdong_cd in test_areas:
        raw_data = fetch_building_info(client, api_key, logger, sigungu_cd, bjdong_cd)
        if raw_data:
            parsed = parse_building_data(raw_data, logger)
            all_data.extend(parsed)
            logger.info(f"  {sigungu_cd}: {len(parsed)}건")

        if sample_limit and len(all_data) >= sample_limit:
            all_data = all_data[:sample_limit]
            break

    if all_data:
        success = batch_upsert(conn, 'api_buildings', all_data,
                               unique_columns=['mgm_bld_pk'], batch_size=100)
        logger.info(f"api_buildings: {success}건 적재")

    total = get_table_count(conn, 'api_buildings')
    logger.info(f"api_buildings 총 레코드: {total}건")

    conn.close()
    logger.info("건축물대장 API ETL 완료")


if __name__ == "__main__":
    sample_limit = int(os.getenv('SAMPLE_LIMIT', 0)) or None
    load_building_data(sample_limit=sample_limit)
