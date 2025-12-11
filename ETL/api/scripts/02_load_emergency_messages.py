"""
SKALA Physical Risk AI System - 긴급재난문자 API ETL

API: 재난안전데이터공유플랫폼 긴급재난문자
URL: https://www.safetydata.go.kr/V2/api/DSSP-IF-00247
용도: 재난 이력 추적 (침수/홍수/태풍 발생 횟수)

최종 수정일: 2025-12-10
버전: v02 - 스키마 변경 (alert_date, disaster_type, severity, region)
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
    get_table_count,
    API_ENDPOINTS
)


# 허용되는 재난 유형 (10종)
VALID_DISASTER_TYPES = [
    '호우', '태풍', '지진', '대설', '한파',
    '폭염', '강풍', '황사', '산불', '해일'
]

# 제외할 키워드 (실종신고 관련)
EXCLUDE_KEYWORDS = ['실종', '찾습니다', '배회중', '경찰청']

# severity 매핑
SEVERITY_MAP = {
    '주의보': '주의보',
    '경보': '경보',
    '긴급': '경보',
    '위급': '경보',
    '안전안내': '주의보',
    '해제': '주의보'
}


def fetch_emergency_messages(api_key: str, logger,
                             region: str = None, start_date: str = None,
                             page_no: int = 1, num_of_rows: int = 100):
    """
    긴급재난문자 API 호출 (SSL verify=False 필요)
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


def normalize_disaster_type(dst_se_nm: str) -> str:
    """
    재난유형을 10종으로 정규화
    """
    if not dst_se_nm:
        return None

    dst_se_nm = dst_se_nm.strip()

    # 직접 매핑
    for valid_type in VALID_DISASTER_TYPES:
        if valid_type in dst_se_nm:
            return valid_type

    # 유사어 매핑
    type_aliases = {
        '침수': '호우',
        '홍수': '호우',
        '집중호우': '호우',
        '우박': '호우',
        '낙뢰': '호우',
        '폭풍': '태풍',
        '눈': '대설',
        '폭설': '대설',
        '추위': '한파',
        '더위': '폭염',
        '고온': '폭염',
        '미세먼지': '황사',
        '쓰나미': '해일',
        '풍랑': '강풍',
        '산사태': '호우',
        '화재': '산불'
    }

    for alias, valid_type in type_aliases.items():
        if alias in dst_se_nm:
            return valid_type

    return None


def normalize_severity(emrg_step_nm: str) -> str:
    """
    강도를 주의보/경보로 정규화
    """
    if not emrg_step_nm:
        return '주의보'  # 기본값

    emrg_step_nm = emrg_step_nm.strip()

    # 매핑 적용
    for key, value in SEVERITY_MAP.items():
        if key in emrg_step_nm:
            return value

    # 기본값
    return '주의보'


def parse_emergency_data(raw_data: dict, logger) -> list:
    """
    API 응답 파싱 (새 스키마: alert_date, disaster_type, severity, region)
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
            msg_content = item.get('MSG_CN', '')

            # 실종 관련 키워드 포함 시 제외
            if any(kw in msg_content for kw in EXCLUDE_KEYWORDS):
                continue

            # 날짜 파싱
            crt_dt_str = item.get('CRT_DT', '')
            alert_date = None

            for fmt in ['%Y/%m/%d %H:%M:%S', '%Y-%m-%d %H:%M:%S', '%Y%m%d%H%M%S', '%Y-%m-%d']:
                try:
                    if crt_dt_str:
                        dt = datetime.strptime(crt_dt_str, fmt)
                        alert_date = dt.date()  # DATE만 추출
                        break
                except:
                    continue

            if not alert_date:
                continue

            # 재난유형 정규화 (10종 제한)
            dst_se_nm = item.get('DST_SE_NM', '')
            disaster_type = normalize_disaster_type(dst_se_nm)

            if not disaster_type:
                continue  # 10종에 해당하지 않으면 스킵

            # 강도 정규화 (주의보/경보)
            emrg_step_nm = item.get('EMRG_STEP_NM', '')
            severity = normalize_severity(emrg_step_nm)

            # 지역명
            region = item.get('RCPTN_RGN_NM', '') or item.get('RGN_NM', '')
            if not region:
                continue

            # 지역명 길이 제한 (200자)
            if len(region) > 200:
                region = region[:200]

            record = {
                'alert_date': alert_date,
                'disaster_type': disaster_type,
                'severity': severity,
                'region': region
            }

            parsed.append(record)

        except Exception as e:
            logger.warning(f"레코드 파싱 실패: {e}")
            continue

    return parsed


def batch_insert_emergency_messages(conn, data: list, logger):
    """
    긴급재난문자 데이터 배치 INSERT
    (중복 허용 - 동일 날짜/유형/지역의 다른 메시지일 수 있음)
    """
    if not data:
        return 0

    cursor = conn.cursor()
    inserted = 0

    insert_sql = """
        INSERT INTO api_emergency_messages (alert_date, disaster_type, severity, region)
        VALUES (%s, %s, %s, %s)
    """

    try:
        for record in data:
            cursor.execute(insert_sql, (
                record['alert_date'],
                record['disaster_type'],
                record['severity'],
                record['region']
            ))
            inserted += 1

        conn.commit()
        logger.info(f"배치 INSERT 완료: {inserted}건")

    except Exception as e:
        conn.rollback()
        logger.error(f"배치 INSERT 오류: {e}")
    finally:
        cursor.close()

    return inserted


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
    type_stats = {t: 0 for t in VALID_DISASTER_TYPES}

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

            # 재난유형별 통계 업데이트
            for record in parsed:
                if record['disaster_type'] in type_stats:
                    type_stats[record['disaster_type']] += 1

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
        success_count = batch_insert_emergency_messages(conn, all_data, logger)
        logger.info(f"DB 적재 완료: {success_count}건")

        # 재난 유형별 통계 출력
        logger.info("=" * 40)
        logger.info("재난 유형별 통계:")
        for dtype, count in type_stats.items():
            if count > 0:
                logger.info(f"  {dtype}: {count}건")
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
