"""
SKALA Physical Risk AI System - 긴급재난문자 API ETL

API: 재난안전데이터공유플랫폼 긴급재난문자
URL: https://www.safetydata.go.kr/V2/api/DSSP-IF-00247
용도: 재난 이력 추적 (침수/홍수/태풍 발생 횟수)

최종 수정일: 2025-12-02
"""

import os
import sys
import requests
import urllib3
from pathlib import Path
from datetime import datetime, timedelta

# SSL 경고 비활성화 (재난안전데이터 API 인증서 이슈)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# 상위 경로 추가
sys.path.insert(0, str(Path(__file__).parent))

from utils import (
    setup_logging,
    get_db_connection,
    get_api_key,
    batch_upsert,
    get_table_count,
    API_ENDPOINTS
)


# 재난 유형별 키워드
DISASTER_KEYWORDS = {
    'flood': ['침수', '홍수', '범람', '하천범람', '도로침수', '지하침수', '배수불량'],
    'typhoon': ['태풍', '강풍', '폭풍', '해일'],
    'heat': ['폭염', '고온', '열사병', '온열질환', '더위'],
    'cold': ['한파', '저온', '동파', '동상', '추위'],
    'fire': ['산불', '화재', '실화', '산림화재']
}


def classify_disaster_type(message_content: str) -> dict:
    """
    메시지 내용에서 재난 유형 분류

    Args:
        message_content: 재난문자 내용

    Returns:
        재난 유형별 bool 딕셔너리
    """
    result = {
        'is_flood_related': False,
        'is_typhoon_related': False,
        'is_heat_related': False,
        'is_cold_related': False,
        'is_fire_related': False
    }

    if not message_content:
        return result

    for dtype, keywords in DISASTER_KEYWORDS.items():
        for keyword in keywords:
            if keyword in message_content:
                result[f'is_{dtype}_related'] = True
                break

    return result


def fetch_emergency_messages(api_key: str, logger,
                             region: str = None, start_date: str = None,
                             page_no: int = 1, num_of_rows: int = 100):
    """
    긴급재난문자 API 호출 (SSL verify=False 필요)

    Args:
        api_key: API 키
        logger: 로거
        region: 지역명 (예: "서울특별시")
        start_date: 조회 시작일 (YYYYMMDD)
        page_no: 페이지 번호
        num_of_rows: 페이지당 결과 수

    Returns:
        API 응답 데이터
    """
    url = API_ENDPOINTS['emergency_messages']
    params = {
        'serviceKey': api_key,
        'returnType': 'json',
        'pageNo': str(page_no),
        'numOfRows': str(num_of_rows)
    }

    if region:
        params['rgnNm'] = region
    if start_date:
        params['crtDt'] = start_date

    logger.info(f"긴급재난문자 API 호출: 페이지 {page_no}, 지역={region or '전체'}")

    try:
        response = requests.get(url, params=params, verify=False, timeout=30)
        if response.status_code == 200:
            return response.json()
        else:
            logger.warning(f"API 응답 실패: {response.status_code}")
            return None
    except Exception as e:
        logger.error(f"API 요청 오류: {e}")
        return None


def parse_emergency_data(raw_data: dict, logger) -> list:
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

    # 본문 데이터 추출 (body는 리스트 형태)
    body = raw_data.get('body', [])
    if not body:
        logger.warning("API 응답 body 없음")
        return parsed

    # body가 리스트인지 확인
    if isinstance(body, list):
        items = body
    else:
        items = [body]

    for item in items:
        try:
            # 재난 유형 분류
            msg_content = item.get('MSG_CN', '')
            disaster_types = classify_disaster_type(msg_content)

            # 날짜 파싱
            crt_dt_str = item.get('CRT_DT', '')
            mdf_dt_str = item.get('MDF_DT', '')

            try:
                crt_dt = datetime.strptime(crt_dt_str, '%Y%m%d%H%M%S') if crt_dt_str else None
            except:
                crt_dt = None

            try:
                mdf_dt = datetime.strptime(mdf_dt_str, '%Y%m%d%H%M%S') if mdf_dt_str else None
            except:
                mdf_dt = None

            record = {
                'msg_sn': str(item.get('SN', '')),
                'msg_cn': msg_content,
                'msg_se_cd': item.get('MSG_SE_CD', ''),
                'msg_se_nm': item.get('MSG_SE_NM', ''),
                'rcptn_rgn_nm': item.get('RCPTN_RGN_NM', '') or item.get('RGN_NM', ''),  # RCPTN_RGN_NM 우선
                'rgn_cd': item.get('RGN_CD', ''),
                'crt_dt': crt_dt,
                'mdf_dt': mdf_dt,
                'emrg_step_nm': item.get('EMRG_STEP_NM', ''),
                'dst_se_nm': item.get('DST_SE_NM', ''),
                'api_response': item,
                **disaster_types
            }

            if record['msg_sn']:
                parsed.append(record)

        except Exception as e:
            logger.warning(f"레코드 파싱 실패: {e}")
            continue

    return parsed


def load_emergency_messages(sample_limit: int = None, years: int = 5):
    """
    긴급재난문자 데이터 적재

    Args:
        sample_limit: 샘플 제한 (테스트용)
        years: 조회 기간 (년)
    """
    logger = setup_logging("load_emergency_messages")
    logger.info("=" * 60)
    logger.info("긴급재난문자 API ETL 시작")
    logger.info("=" * 60)

    # API 키 확인
    api_key = get_api_key('EMERGENCYMESSAGE_API_KEY')
    if not api_key:
        logger.error("EMERGENCYMESSAGE_API_KEY 환경변수 필요")
        return

    # DB 연결
    conn = get_db_connection()
    logger.info("DB 연결 완료")

    # 조회 시작일 (N년 전)
    start_date = (datetime.now() - timedelta(days=365 * years)).strftime('%Y%m%d')
    logger.info(f"조회 기간: {start_date} ~ 현재")

    # 주요 지역별 수집
    regions = [
        '서울특별시', '부산광역시', '대구광역시', '인천광역시',
        '광주광역시', '대전광역시', '울산광역시', '세종특별자치시',
        '경기도', '강원특별자치도', '충청북도', '충청남도',
        '전북특별자치도', '전라남도', '경상북도', '경상남도', '제주특별자치도'
    ]

    all_data = []

    for region in regions:
        page_no = 1
        num_of_rows = 100
        region_count = 0

        while True:
            raw_data = fetch_emergency_messages(
                api_key, logger,
                region=region, start_date=start_date,
                page_no=page_no, num_of_rows=num_of_rows
            )

            if not raw_data:
                break

            parsed = parse_emergency_data(raw_data, logger)
            if not parsed:
                break

            all_data.extend(parsed)
            region_count += len(parsed)
            logger.info(f"  {region} 페이지 {page_no}: {len(parsed)}건")

            # 샘플 제한 확인
            if sample_limit and len(all_data) >= sample_limit:
                all_data = all_data[:sample_limit]
                logger.info(f"샘플 제한 적용: {sample_limit}건")
                break

            if len(parsed) < num_of_rows:
                break

            page_no += 1

        logger.info(f"{region}: 총 {region_count}건 수집")

        if sample_limit and len(all_data) >= sample_limit:
            break

    # DB 적재
    if all_data:
        logger.info(f"총 {len(all_data)}건 DB 적재 시작")
        success_count = batch_upsert(
            conn,
            'api_emergency_messages',
            all_data,
            unique_columns=['msg_sn'],
            batch_size=100
        )
        logger.info(f"DB 적재 완료: {success_count}건")

        # 재난 유형별 통계
        flood_count = sum(1 for d in all_data if d.get('is_flood_related'))
        typhoon_count = sum(1 for d in all_data if d.get('is_typhoon_related'))
        heat_count = sum(1 for d in all_data if d.get('is_heat_related'))
        logger.info(f"재난 유형별: 침수/홍수 {flood_count}건, 태풍 {typhoon_count}건, 폭염 {heat_count}건")
    else:
        logger.warning("적재할 데이터 없음")

    # 결과 확인
    total_count = get_table_count(conn, 'api_emergency_messages')
    logger.info(f"api_emergency_messages 테이블 총 레코드: {total_count}건")

    conn.close()
    logger.info("긴급재난문자 API ETL 완료")


if __name__ == "__main__":
    sample_limit = int(os.getenv('SAMPLE_LIMIT', 0)) or None
    load_emergency_messages(sample_limit=sample_limit)
