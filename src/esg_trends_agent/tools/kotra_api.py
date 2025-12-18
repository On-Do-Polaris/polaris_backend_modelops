"""
==================================================================
[모듈명] tools/kotra_api.py
KOTRA ESG 동향뉴스 API 래퍼

[모듈 목표]
1) KOTRA ESG 동향뉴스 API 호출
2) 글로벌 ESG 뉴스 데이터 파싱
==================================================================
"""
import requests
from datetime import datetime, date
from typing import Dict, List, Optional
from ..utils.config import Config
from ..utils.logging import get_logger

logger = get_logger("esg_agent.kotra")

# 대한무역투자진흥공사 ESG 동향뉴스 API 엔드포인트
KOTRA_API_URL = "https://apis.data.go.kr/B410001/trend-news/getTrend-news"


def fetch_kotra_esg_news(
    num_of_rows: int = 10,
    pub_date: Optional[str] = None,
    max_retries: int = 3
) -> List[Dict]:
    """KOTRA ESG 동향뉴스 조회

    Args:
        num_of_rows: 조회할 뉴스 개수
        pub_date: 발행일 필터 (YYYY-MM-DD 형식, 없으면 전체)
        max_retries: 최대 재시도 횟수

    Returns:
        List[Dict]: ESG 뉴스 리스트
    """
    import time

    if not Config.KOTRA_API_KEY:
        logger.warning("KOTRA_API_KEY가 설정되지 않음, 검색 API로 대체")
        return []

    params = {
        "serviceKey": Config.KOTRA_API_KEY,
        "type": "json",
        "numOfRows": num_of_rows,
        "pageNo": 1,
    }

    if pub_date:
        params["pubDate"] = pub_date

    for attempt in range(max_retries):
        try:
            response = requests.get(KOTRA_API_URL, params=params, timeout=15)

            # 429/500/502/503 에러 시 대기 후 재시도
            if response.status_code in [429, 500, 502, 503]:
                wait_time = (attempt + 1) * 5  # 5초, 10초, 15초
                logger.warning(f"KOTRA API {response.status_code} 에러, {wait_time}초 대기 후 재시도...")
                time.sleep(wait_time)
                continue

            response.raise_for_status()
            data = response.json()

            # 응답이 리스트인 경우 (새로운 API 구조)
            if isinstance(data, list):
                return parse_kotra_items(data)

            # 기존 구조 호환
            if "response" in data:
                header = data["response"]["header"]
                if header.get("resultCode") != "00":
                    logger.error(f"KOTRA API 오류: {header.get('resultMsg', 'Unknown error')}")
                    return []
                items = data["response"]["body"]["itemList"]["item"]
                if not isinstance(items, list):
                    items = [items]
                return parse_kotra_items(items)

            logger.error(f"알 수 없는 KOTRA API 응답 구조: {type(data)}")
            return []

        except requests.RequestException as e:
            if attempt < max_retries - 1:
                wait_time = (attempt + 1) * 5
                logger.warning(f"KOTRA API 요청 실패, {wait_time}초 후 재시도: {e}")
                time.sleep(wait_time)
            else:
                logger.error(f"KOTRA API 요청 실패 (최대 재시도 초과): {e}")
                return []
        except (KeyError, TypeError) as e:
            logger.error(f"KOTRA 데이터 파싱 실패: {e}")
            return []

    logger.error("KOTRA API 최대 재시도 횟수 초과")
    return []


def parse_kotra_items(items: List[Dict]) -> List[Dict]:
    """KOTRA 뉴스 아이템 파싱

    Args:
        items: API 응답 아이템 리스트

    Returns:
        List[Dict]: 파싱된 뉴스 리스트
    """
    news_list = []

    for item in items:
        try:
            # 새로운 API 필드명 사용
            news = {
                "title": item.get("nttSj", ""),           # 뉴스 제목
                "summary": item.get("smmarCn", ""),       # 요약 내용
                "published_at": item.get("othbcDt", ""),  # 발행일 (YYYY-MM-DD)
                "country": item.get("nat", ""),           # 국가
                "region": item.get("regn", ""),           # 지역
                "trade_office": item.get("kbc", ""),      # 무역관
                "source": "KOTRA",
                "url": "",  # API에서 URL 미제공
            }

            # 지역 분류
            region_map = {
                "북미": "미국",
                "유럽": "EU",
                "아시아": "아시아",
                "중남미": "기타",
                "중동": "기타",
                "아프리카": "기타",
                "대양주": "기타",
            }
            news["region_category"] = region_map.get(news["region"], "기타")

            news_list.append(news)
        except Exception as e:
            logger.warning(f"뉴스 아이템 파싱 실패: {e}")
            continue

    logger.info(f"KOTRA ESG 뉴스 {len(news_list)}건 수집 완료")

    # 결과 출력
    if news_list:
        print(f"\n{'='*50}")
        print(f"🌍 KOTRA 글로벌 ESG 뉴스 ({len(news_list)}건)")
        print(f"{'='*50}")
        for i, news in enumerate(news_list[:5], 1):
            print(f"\n[{i}] {news.get('title', '')[:50]}...")
            print(f"    지역: {news.get('region', '')} / {news.get('country', '')}")
            print(f"    날짜: {news.get('published_at', '')}")

    return news_list


def fetch_recent_esg_news(days: int = 7, limit: int = 10) -> List[Dict]:
    """최근 ESG 뉴스 조회

    Args:
        days: 조회할 기간 (일)
        limit: 최대 뉴스 개수

    Returns:
        List[Dict]: ESG 뉴스 리스트
    """
    # KOTRA API는 날짜 필터링이 제한적이므로 더 많이 가져와서 필터링
    news_list = fetch_kotra_esg_news(num_of_rows=limit * 2)

    if not news_list:
        return []

    # 최근 날짜 기준 필터링
    today = date.today()
    filtered = []

    for news in news_list:
        try:
            pub_date_str = news.get("published_at", "")
            if pub_date_str:
                pub_date = datetime.strptime(pub_date_str, "%Y-%m-%d").date()
                diff = (today - pub_date).days
                if diff <= days:
                    filtered.append(news)
        except ValueError:
            # 날짜 파싱 실패 시 포함
            filtered.append(news)

    return filtered[:limit]
