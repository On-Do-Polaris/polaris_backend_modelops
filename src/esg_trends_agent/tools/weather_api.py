"""
==================================================================
[모듈명] tools/weather_api.py
기상청 단기예보 API 래퍼

[모듈 목표]
1) 기상청 API 호출
2) 지역명 → 격자 좌표 변환
3) 기상 데이터 파싱
4) 물리적 리스크 판단
==================================================================
"""
import requests
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from ..utils.config import Config
from ..utils.logging import get_logger

logger = get_logger("esg_agent.weather")

# 지역명 → 격자 좌표 매핑 테이블
LOCATION_GRID_MAP: Dict[str, Tuple[int, int]] = {
    # 서울/경기
    "서울": (60, 127),
    "성남": (63, 124),
    "수원": (60, 121),
    "고양": (57, 128),
    "용인": (64, 119),
    "인천": (55, 124),
    # 광역시
    "부산": (98, 76),
    "대구": (89, 90),
    "대전": (67, 100),
    "광주": (58, 74),
    "울산": (102, 84),
    "세종": (66, 103),
}

# 기상청 API 엔드포인트
KMA_API_URL = "http://apis.data.go.kr/1360000/VilageFcstInfoService_2.0/getVilageFcst"


def get_base_datetime() -> Tuple[str, str]:
    """기상청 API 요청용 기준 날짜/시간 계산

    기상청 단기예보는 02, 05, 08, 11, 14, 17, 20, 23시에 발표
    현재 시간 기준으로 가장 최근 발표 시간 반환

    Returns:
        Tuple[str, str]: (base_date, base_time) - YYYYMMDD, HHMM 형식
    """
    now = datetime.now()
    base_times = [2, 5, 8, 11, 14, 17, 20, 23]

    # 현재 시간보다 이전의 가장 최근 발표 시간 찾기
    current_hour = now.hour
    base_time = None

    for t in reversed(base_times):
        if current_hour >= t:
            base_time = t
            break

    # 아직 첫 발표 전이면 전날 23시 데이터 사용
    if base_time is None:
        now = now - timedelta(days=1)
        base_time = 23

    base_date = now.strftime("%Y%m%d")
    base_time_str = f"{base_time:02d}00"

    return base_date, base_time_str


def fetch_weather_for_location(location: str, max_retries: int = 5) -> Optional[Dict]:
    """특정 지역의 기상 데이터 조회

    Args:
        location: 지역명 (예: "서울", "성남", "대전")
        max_retries: 최대 재시도 횟수

    Returns:
        Dict: 기상 데이터 또는 None
    """
    import time

    if location not in LOCATION_GRID_MAP:
        logger.warning(f"지원하지 않는 지역: {location}")
        return None

    nx, ny = LOCATION_GRID_MAP[location]
    base_date, base_time = get_base_datetime()

    params = {
        "serviceKey": Config.KMA_API_KEY,
        "numOfRows": "100",
        "pageNo": "1",
        "dataType": "JSON",
        "base_date": base_date,
        "base_time": base_time,
        "nx": nx,
        "ny": ny,
    }

    for attempt in range(max_retries):
        try:
            response = requests.get(KMA_API_URL, params=params, timeout=10)

            # 429 에러 시 대기 후 재시도
            if response.status_code == 429:
                wait_time = (attempt + 1) * 30  # 30초, 60초, 90초, 120초, 150초
                logger.warning(f"429 Too Many Requests ({location}), {wait_time}초 대기 후 재시도...")
                time.sleep(wait_time)
                continue

            response.raise_for_status()
            data = response.json()

            # 응답 검증
            if "response" not in data:
                logger.error(f"잘못된 API 응답: {data}")
                return None

            header = data["response"]["header"]
            if header["resultCode"] != "00":
                logger.error(f"API 오류: {header['resultMsg']}")
                return None

            items = data["response"]["body"]["items"]["item"]
            return parse_weather_items(items, location)

        except requests.RequestException as e:
            if attempt < max_retries - 1:
                wait_time = (attempt + 1) * 3
                logger.warning(f"기상청 API 요청 실패 ({location}), {wait_time}초 후 재시도: {e}")
                time.sleep(wait_time)
            else:
                logger.error(f"기상청 API 요청 실패 ({location}): {e}")
                return None
        except (KeyError, TypeError) as e:
            logger.error(f"기상 데이터 파싱 실패 ({location}): {e}")
            return None

    logger.error(f"기상청 API 최대 재시도 횟수 초과 ({location})")
    return None


def parse_weather_items(items: List[Dict], location: str) -> Dict:
    """기상 데이터 아이템 파싱

    Args:
        items: API 응답 아이템 리스트
        location: 지역명

    Returns:
        Dict: 파싱된 기상 데이터
    """
    weather_data = {
        "location": location,
        "temperature": None,
        "humidity": None,
        "wind_speed": None,
        "precipitation_prob": None,
        "precipitation": None,
        "sky_condition": None,
        "observed_at": datetime.now().isoformat(),
    }

    # 카테고리별 첫 번째 값만 사용 (가장 가까운 예보)
    category_map = {
        "TMP": "temperature",       # 기온
        "REH": "humidity",          # 습도
        "WSD": "wind_speed",        # 풍속
        "POP": "precipitation_prob", # 강수확률
        "PCP": "precipitation",     # 강수량
        "SKY": "sky_condition",     # 하늘상태
    }

    seen_categories = set()

    for item in items:
        category = item.get("category")
        if category in category_map and category not in seen_categories:
            value = item.get("fcstValue")
            field = category_map[category]

            if category in ["TMP", "REH", "POP"]:
                try:
                    weather_data[field] = float(value)
                except (ValueError, TypeError):
                    pass
            elif category == "WSD":
                try:
                    weather_data[field] = float(value)
                except (ValueError, TypeError):
                    pass
            elif category == "PCP":
                # 강수량은 "강수없음" 또는 숫자mm 형태
                if value == "강수없음":
                    weather_data[field] = 0.0
                else:
                    try:
                        weather_data[field] = float(value.replace("mm", ""))
                    except (ValueError, TypeError):
                        weather_data[field] = 0.0
            elif category == "SKY":
                # 하늘상태: 1=맑음, 3=구름많음, 4=흐림
                sky_map = {"1": "맑음", "3": "구름많음", "4": "흐림"}
                weather_data[field] = sky_map.get(value, "알수없음")

            seen_categories.add(category)

    return weather_data


def analyze_physical_risks(weather_data: Dict) -> List[str]:
    """기상 데이터 기반 물리적 리스크 분석

    Args:
        weather_data: 기상 데이터

    Returns:
        List[str]: 해당되는 물리적 리스크 목록
    """
    risks = []

    temp = weather_data.get("temperature")
    humidity = weather_data.get("humidity")
    wind_speed = weather_data.get("wind_speed")
    precip_prob = weather_data.get("precipitation_prob")
    precip = weather_data.get("precipitation")

    # 극심한 고온: 기온 33°C 이상
    if temp is not None and temp >= 33:
        risks.append("극심한 고온")

    # 극심한 한파: 기온 -12°C 이하
    if temp is not None and temp <= -12:
        risks.append("극심한 한파")

    # 도시 홍수: 강수확률 80% 이상 + 강수량 30mm 이상
    if precip_prob is not None and precip is not None:
        if precip_prob >= 80 and precip >= 30:
            risks.append("도시 홍수")

    # 산불 위험: 고온(30°C 이상) + 저습도(30% 이하) + 강풍(10m/s 이상)
    if temp is not None and humidity is not None and wind_speed is not None:
        if temp >= 30 and humidity <= 30 and wind_speed >= 10:
            risks.append("산불")

    return risks


def fetch_weather(locations: Optional[List[str]] = None) -> Dict[str, Dict]:
    """여러 지역의 기상 데이터 조회

    Args:
        locations: 지역명 리스트 (없으면 Config에서 가져옴)

    Returns:
        Dict[str, Dict]: 지역별 기상 데이터
    """
    import time

    if locations is None:
        locations = Config.get_weather_locations()

    result = {}
    for i, location in enumerate(locations):
        # 첫 요청 전에도 5초 대기, 이후 15초 딜레이 (429 방지)
        if i == 0:
            logger.info("기상청 API 준비 시간 5초 대기...")
            time.sleep(5)
        else:
            time.sleep(15)  # 15초 딜레이

        weather_data = fetch_weather_for_location(location)
        if weather_data:
            result[location] = weather_data
            logger.info(f"기상 데이터 수집 완료: {location}")
            # 결과 출력
            print(f"\n{'='*50}")
            print(f"🌤️ [{location}] 날씨 데이터")
            print(f"{'='*50}")
            print(f"  기온: {weather_data.get('temperature')}°C")
            print(f"  습도: {weather_data.get('humidity')}%")
            print(f"  하늘: {weather_data.get('sky_condition')}")
            print(f"  풍속: {weather_data.get('wind_speed')}m/s")
            print(f"  강수확률: {weather_data.get('precipitation_prob')}%")
        else:
            logger.warning(f"기상 데이터 수집 실패: {location}")

    return result
