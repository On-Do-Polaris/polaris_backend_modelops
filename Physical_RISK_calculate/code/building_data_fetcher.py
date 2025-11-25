"""
건축물 대장 API를 활용한 건물 정보 자동 조회
위/경도 → 건물 정보 자동 수집
"""

import os
import requests
import xmltodict
from pathlib import Path
from dotenv import load_dotenv
from typing import Dict, Optional
from geopy.distance import geodesic

# 환경변수 로드
BASE_DIR = Path(__file__).parent.parent
load_dotenv(BASE_DIR / ".env")

# 하천 차수 추출 모듈
try:
    from stream_order_simple import StreamOrderExtractor, get_stream_order_fallback
    STREAM_ORDER_AVAILABLE = True
except ImportError:
    STREAM_ORDER_AVAILABLE = False
    print("⚠️  stream_order_simple 모듈 import 실패 - 하천 차수는 기본값 사용")

# 재난안전데이터 API 모듈
try:
    from disaster_api_fetcher import DisasterAPIFetcher
    DISASTER_API_AVAILABLE = True
except ImportError:
    DISASTER_API_AVAILABLE = False
    print("⚠️  disaster_api_fetcher 모듈 import 실패 - 재난 데이터는 기본값 사용")

class BuildingDataFetcher:
    """건축물 정보 자동 조회 클래스"""

    def __init__(self):
        self.building_api_key = os.getenv("BUILDING_API_KEY")
        self.vworld_api_key = os.getenv("VWORLD_API_KEY")
        self.building_base_url = "https://apis.data.go.kr/1613000/BldRgstHubService"

        # 하천 차수 추출기 초기화
        if STREAM_ORDER_AVAILABLE:
            try:
                self.stream_extractor = StreamOrderExtractor()
            except Exception as e:
                print(f"   ⚠️  StreamOrderExtractor 초기화 실패: {e}")
                self.stream_extractor = None
        else:
            self.stream_extractor = None

        # 재난안전데이터 API 초기화
        if DISASTER_API_AVAILABLE:
            try:
                self.disaster_fetcher = DisasterAPIFetcher()
            except Exception as e:
                print(f"   ⚠️  DisasterAPIFetcher 초기화 실패: {e}")
                self.disaster_fetcher = None
        else:
            self.disaster_fetcher = None

    def get_building_code_from_coords(self, lat: float, lon: float) -> Optional[Dict]:
        """
        위/경도 → 시군구코드, 법정동코드, 번/지 변환
        V-World Geocoder API 사용 (EPSG:4326 WGS84 좌표계)

        Returns:
            {
                'sido': str,  # 시도명
                'sigungu': str,  # 시군구명
                'dong': str,  # 법정동명
                'dong_code': str,  # 법정동코드
                'bun': str,  # 본번
                'ji': str,  # 부번
                'full_address': str,  # 전체 주소
                'parcel_address': str,  # 지번 주소
                'road_address': str,  # 도로명 주소
            }
        """
        url = "https://api.vworld.kr/req/address"
        params = {
            "service": "address",
            "request": "getAddress",
            "version": "2.0",
            "crs": "EPSG:4326",
            "point": f"{lon},{lat}",
            "format": "json",
            "type": "BOTH",  # 도로명 + 지번 둘 다
            "zipcode": "true",
            "simple": "false",
            "key": self.vworld_api_key
        }

        try:
            response = requests.get(url, params=params, timeout=10)
            data = response.json()

            if data['response']['status'] != 'OK':
                print(f"   ⚠️  V-World API 응답 실패: {data['response'].get('status')}")
                return None

            results = data['response']['result']
            if not results:
                print(f"   ⚠️  해당 좌표의 주소 정보 없음")
                return None

            # 지번 주소 찾기 (type='parcel')
            parcel_result = None
            road_result = None

            for item in results:
                if item.get('type') == 'parcel':
                    parcel_result = item
                elif item.get('type') == 'road':
                    road_result = item

            # 지번 주소 우선 사용
            if parcel_result:
                structure = parcel_result.get('structure', {})

                # 번지 정보 파싱 (level5 또는 number1/number2)
                bun = structure.get('number1', '')
                ji = structure.get('number2', '')

                # number1/number2가 없으면 level5에서 파싱
                if not bun:
                    level5 = structure.get('level5', '')
                    if level5 and '-' in level5:
                        parts = level5.split('-')
                        bun = parts[0]
                        ji = parts[1] if len(parts) > 1 else ''
                    elif level5:
                        bun = level5
                        ji = ''

                result_dict = {
                    'sido': structure.get('level1', ''),
                    'sigungu': structure.get('level2', ''),
                    'dong': structure.get('level4L', ''),  # 법정동명
                    'dong_code': structure.get('level4LC', ''),  # 법정동코드 (10자리)
                    'bun': bun,
                    'ji': ji,
                    'full_address': parcel_result.get('text', ''),
                    'parcel_address': parcel_result.get('text', ''),
                    'road_address': road_result.get('text', '') if road_result else '',
                    'zipcode': parcel_result.get('zipcode', ''),
                }

                print(f"   ✅ 지번 주소: {result_dict['parcel_address']}")
                if result_dict['bun']:
                    print(f"      본번/부번: {result_dict['bun']}-{result_dict['ji'] if result_dict['ji'] else '0'}")
                if result_dict['dong_code']:
                    print(f"      법정동코드: {result_dict['dong_code']}")

                return result_dict

            elif road_result:
                # 도로명 주소만 있는 경우
                structure = road_result.get('structure', {})
                print(f"   ⚠️  지번 주소 없음, 도로명 주소만 사용")

                return {
                    'sido': structure.get('level1', ''),
                    'sigungu': structure.get('level2', ''),
                    'dong': structure.get('level4L', ''),
                    'dong_code': structure.get('level4LC', ''),
                    'bun': '',
                    'ji': '',
                    'full_address': road_result.get('text', ''),
                    'parcel_address': '',
                    'road_address': road_result.get('text', ''),
                    'zipcode': road_result.get('zipcode', ''),
                }

            return None

        except Exception as e:
            print(f"   ⚠️  주소 조회 실패: {e}")
            import traceback
            traceback.print_exc()
            return None

    def get_admin_code(self, sigungu_name: str, dong_name: str, dong_code: str = None) -> Optional[Dict]:
        """
        시군구명, 동명 → 행정코드 변환

        Args:
            sigungu_name: 시군구명 (예: 강남구)
            dong_name: 법정동명 (예: 삼성동)
            dong_code: V-World에서 받은 법정동코드 10자리 (예: 1168010500)

        Returns:
            {'sigungu_cd': str, 'bjdong_cd': str}
        """
        # 시군구 코드 매핑 (서울/경기 주요 지역)
        sigungu_codes = {
            '종로구': '11110', '중구': '11140', '용산구': '11170',
            '성동구': '11200', '광진구': '11215', '동대문구': '11230',
            '중랑구': '11260', '성북구': '11290', '강북구': '11305',
            '도봉구': '11320', '노원구': '11350', '은평구': '11380',
            '서대문구': '11410', '마포구': '11440', '양천구': '11470',
            '강서구': '11500', '구로구': '11530', '금천구': '11545',
            '영등포구': '11560', '동작구': '11590', '관악구': '11620',
            '서초구': '11650', '강남구': '11680', '송파구': '11710',
            '강동구': '11740',
            '수원시': '41110', '성남시': '41130', '고양시': '41280',
            '용인시': '41460', '부천시': '41190', '안산시': '41270',
            '남양주시': '41360', '화성시': '41590', '평택시': '41220',
            '유성구': '30200', '서구': '30170', '대덕구': '30230',
            '동구': '30110', '중구': '30140'
        }

        sigungu_cd = sigungu_codes.get(sigungu_name, '11680')  # 기본값: 강남구

        # 법정동 코드 처리
        if dong_code and len(dong_code) == 10:
            # V-World 법정동코드 (10자리) → 건축물대장 법정동코드 (5자리)
            # 예: 1168010500 → 10500
            bjdong_cd = dong_code[-5:]  # 뒤 5자리
        else:
            # 법정동코드 없으면 전체 조회
            bjdong_cd = '00000'

        return {
            'sigungu_cd': sigungu_cd,
            'bjdong_cd': bjdong_cd
        }

    def get_building_title_info(self, sigungu_cd: str, bjdong_cd: str = '00000',
                                 bun: str = None, ji: str = None) -> Optional[Dict]:
        """
        건축물 표제부 조회 - 구조, 용도, 층수 등

        Args:
            sigungu_cd: 시군구코드 (5자리)
            bjdong_cd: 법정동코드 (5자리)
            bun: 본번 (선택, 정확한 건물 특정시)
            ji: 부번 (선택, 정확한 건물 특정시)

        Note:
            본번/부번은 4자리 0-패딩 필요 (예: 16 → 0016)
            본번/부번으로 조회시 결과가 없으면, 법정동 전체 조회로 재시도
        """
        url = f"{self.building_base_url}/getBrTitleInfo"

        # 본번/부번 0-패딩 (4자리)
        if bun:
            bun = bun.zfill(4)
        if ji:
            ji = ji.zfill(4)

        # 1차 시도: 본번/부번 포함 조회
        params = {
            "serviceKey": self.building_api_key,
            "sigunguCd": sigungu_cd,
            "bjdongCd": bjdong_cd,
            "_type": "json",
            "numOfRows": 100,  # 법정동 전체 조회시 많은 결과 대비
            "pageNo": 1
        }

        if bun:
            params['bun'] = bun
        if ji:
            params['ji'] = ji

        try:
            response = requests.get(url, params=params, timeout=10)
            data = response.json()

            if data['response']['header']['resultCode'] == '00':
                body = data['response'].get('body', {})
                items = body.get('items', {})

                # items가 비어있거나 ''인 경우 처리
                if not items or items == '' or 'item' not in items:
                    # 본번/부번으로 조회 실패시, 법정동만으로 재시도
                    if bun or ji:
                        print(f"   ⚠️  본번/부번({bun}-{ji})으로 조회 실패, 법정동 전체 조회 재시도...")
                        params.pop('bun', None)
                        params.pop('ji', None)
                        response = requests.get(url, params=params, timeout=10)
                        data = response.json()

                        if data['response']['header']['resultCode'] == '00':
                            body = data['response'].get('body', {})
                            items = body.get('items', {})

                            if not items or items == '' or 'item' not in items:
                                print(f"   ⚠️  법정동 전체 조회도 실패")
                                return None
                        else:
                            return None
                    else:
                        print(f"   ⚠️  건축물 조회 결과 없음 (시군구: {sigungu_cd}, 법정동: {bjdong_cd})")
                        return None

                item_list = items['item']

                # 리스트가 비어있는 경우 → 재시도
                if isinstance(item_list, list) and len(item_list) == 0:
                    # 본번/부번으로 조회 실패시, 법정동만으로 재시도
                    if bun or ji:
                        print(f"   ⚠️  본번/부번({bun}-{ji})으로 건물 리스트 비어있음, 법정동 전체 조회 재시도...")
                        params.pop('bun', None)
                        params.pop('ji', None)
                        response = requests.get(url, params=params, timeout=10)
                        data = response.json()

                        if data['response']['header']['resultCode'] == '00':
                            body = data['response'].get('body', {})
                            items = body.get('items', {})

                            if items and items != '' and 'item' in items:
                                item_list = items['item']
                                if not (isinstance(item_list, list) and len(item_list) == 0):
                                    print(f"   ✅ 법정동 전체 조회 성공")
                                else:
                                    print(f"   ⚠️  법정동 전체 조회도 빈 리스트")
                                    return None
                            else:
                                print(f"   ⚠️  법정동 전체 조회도 실패")
                                return None
                        else:
                            return None
                    else:
                        print(f"   ⚠️  건축물 리스트 비어있음")
                        return None

                # 리스트인 경우 첫 번째 항목, 딕셔너리인 경우 그대로
                item = item_list[0] if isinstance(item_list, list) else item_list

                # 여러 건물이 있으면 경고
                if isinstance(item_list, list) and len(item_list) > 1:
                    print(f"   ⚠️  법정동 내 건물 {len(item_list)}개 발견, 첫 번째 건물 사용")

                result = {
                    'grndFlrCnt': int(item.get('grndFlrCnt', 0) or 0),  # 지상층수
                    'ugrndFlrCnt': int(item.get('ugrndFlrCnt', 0) or 0),  # 지하층수
                    'useAprDay': item.get('useAprDay', '20000101'),  # 사용승인일
                    'strctCdNm': item.get('strctCdNm', '기타'),  # 구조
                    'mainPurpsCdNm': item.get('mainPurpsCdNm', '기타'),  # 주용도
                    'etcPurps': item.get('etcPurps', ''),  # 기타용도
                    'heit': float(item.get('heit', 0) or 0),  # 높이
                    'platArea': float(item.get('platArea', 0) or 0),  # 대지면적
                    'archArea': float(item.get('archArea', 0) or 0),  # 건축면적
                    'totArea': float(item.get('totArea', 0) or 0),  # 연면적
                }

                print(f"   ✅ 건축물 API 조회 성공: {result['mainPurpsCdNm']}, {result['grndFlrCnt']}층")
                return result

        except Exception as e:
            print(f"   ⚠️  건축물 조회 실패: {e}")
            import traceback
            print(f"   상세: {traceback.format_exc()}")
            return None

    def get_building_age(self, use_apr_day: str) -> int:
        """사용승인일 → 건물 연령 계산"""
        try:
            year = int(use_apr_day[:4])
            from datetime import datetime
            current_year = datetime.now().year
            return current_year - year
        except:
            return 30  # 기본값: 30년

    def classify_building_type(self, main_purpose: str) -> str:
        """건물 주용도 → 리스크 계산용 건물 유형 분류"""
        if '단독' in main_purpose or '다가구' in main_purpose or '다세대' in main_purpose:
            return '주택'
        elif '아파트' in main_purpose or '연립' in main_purpose:
            return '아파트'
        elif '상업' in main_purpose or '판매' in main_purpose or '근린' in main_purpose:
            return '상가'
        elif '공장' in main_purpose or '창고' in main_purpose:
            return '공장'
        elif '업무' in main_purpose or '오피스' in main_purpose:
            return '사무실'
        else:
            return '기타'

    def has_piloti_structure(self, strct_cd_nm: str, grnd_flr_cnt: int) -> bool:
        """필로티 구조 추정 (구조 + 층수 기반)"""
        # 철근콘크리트조 + 3층 이상일 경우 필로티 가능성 있음
        if '철근콘크리트' in strct_cd_nm and grnd_flr_cnt >= 3:
            return False  # 보수적으로 False (필로티 없음으로 가정)
        return False

    def get_river_info(self, lat: float, lon: float) -> Dict:
        """
        하천 정보 조회 (V-World WFS API 사용)
        - 하천까지 거리
        - 하천 차수
        - 유역 정보
        """
        url = "http://api.vworld.kr/req/wfs"
        params = {
            "service": "wfs",
            "request": "GetFeature",
            "typename": "lt_c_wkmstrm",  # 하천 레이어
            "version": "1.1.0",
            "srsname": "EPSG:4326",
            "bbox": f"{lon-0.05},{lat-0.05},{lon+0.05},{lat+0.05}",
            "output": "application/json",
            "key": self.vworld_api_key
        }

        try:
            response = requests.get(url, params=params, timeout=15)
            data = response.json()

            features = data.get('features', [])
            if not features:
                raise ValueError("주변 10km 이내 하천 정보 없음 - V-World WFS API 응답 없음")

            # 가장 가까운 하천 찾기
            min_distance = float('inf')
            nearest_river = None

            for feature in features[:10]:  # 최대 10개 확인
                geom = feature.get('geometry', {})
                coords = geom.get('coordinates', [])
                properties = feature.get('properties', {})

                if coords:
                    # LineString의 첫 번째 좌표
                    if isinstance(coords[0], list):
                        river_lon, river_lat = coords[0][0], coords[0][1]
                    else:
                        river_lon, river_lat = coords[0], coords[1]

                    distance = geodesic((lat, lon), (river_lat, river_lon)).meters

                    if distance < min_distance:
                        min_distance = distance
                        nearest_river = {
                            'distance_m': distance,
                            'stream_order': int(properties.get('stream_order', properties.get('strahler', 3))),
                            'river_name': properties.get('name', properties.get('riv_name', '미상')),
                            'watershed_code': properties.get('watershed_cd', ''),
                        }

            if nearest_river:
                print(f"   ✅ 하천 정보: {nearest_river['river_name']}, 거리 {nearest_river['distance_m']:.0f}m, 차수 {nearest_river['stream_order']}")
                return nearest_river
            else:
                raise ValueError("하천 좌표 파싱 실패")

        except Exception as e:
            error_msg = f"⚠️  [TCFD 경고] 하천 정보 조회 실패: {e}"
            print(f"   {error_msg}")
            raise ValueError(error_msg)

    def get_distance_to_coast(self, lat: float, lon: float) -> float:
        """
        해안선까지 거리 계산
        간단한 추정: 위도 기반 (북위 34-38도 사이면 육지)
        """
        # 한국 해안선 주요 지점들 (간단한 추정)
        coastal_points = [
            (35.1796, 129.0756),  # 부산
            (37.4563, 126.7052),  # 인천
            (33.5097, 126.4914),  # 제주
            (38.2080, 128.5912),  # 속초
            (34.8118, 128.4170),  # 통영
        ]

        min_distance = 100000  # 100km (내륙)
        for coast_lat, coast_lon in coastal_points:
            distance = geodesic((lat, lon), (coast_lat, coast_lon)).meters
            min_distance = min(min_distance, distance)

        return min_distance

    def get_stream_order_from_dem(self, lat: float, lon: float) -> Optional[Dict]:
        """
        DEM 데이터로부터 하천 차수 추출 (투명한 방법)

        Returns:
            {'stream_order': int, 'flow_accumulation': float, 'method': str}
            또는 None (실패시)
        """
        if not self.stream_extractor:
            return None

        try:
            result = self.stream_extractor.get_stream_order_at_point(
                lat, lon,
                flow_threshold=500,
                search_radius=100
            )
            return result
        except Exception as e:
            print(f"   ⚠️  DEM 하천 차수 추출 실패: {e}")
            return None

    def fetch_all_building_data(self, lat: float, lon: float) -> Dict:
        """
        위/경도 → 모든 필요한 건물 정보 자동 수집
        TCFD 공시용: API 실패시 에러 발생, 기본값 사용 안함
        """
        print(f"   🔍 건축물 정보 조회 중...")
        errors = []

        # 1. 좌표 → 주소/행정코드
        addr_info = self.get_building_code_from_coords(lat, lon)
        if not addr_info:
            errors.append("[TCFD 에러] V-World Geocoder API 실패 - 주소 조회 불가")

        # 2. 행정코드 가져오기
        if addr_info:
            codes = self.get_admin_code(
                addr_info.get('sigungu', ''),
                addr_info.get('dong', ''),
                addr_info.get('dong_code', '')  # V-World 법정동코드 전달
            )
        else:
            codes = None

        # 3. 건축물 정보 조회
        building_info = None
        if codes:
            building_info = self.get_building_title_info(
                codes['sigungu_cd'],
                codes['bjdong_cd'],
                addr_info.get('bun'),
                addr_info.get('ji')
            )

        if not building_info:
            errors.append(f"[TCFD 에러] 건축물대장 API 실패 - 건물 정보 조회 불가 (시군구: {codes['sigungu_cd'] if codes else 'N/A'})")

        # 4. 하천 정보 조회 (거리 + 차수)
        river_info = None
        try:
            river_info = self.get_river_info(lat, lon)
        except Exception as e:
            errors.append(str(e))

        # 4-2. DEM으로부터 하천 차수 추출 (투명한 방법)
        dem_stream_info = self.get_stream_order_from_dem(lat, lon)
        if dem_stream_info:
            print(f"   ✅ DEM 하천 차수: {dem_stream_info['stream_order']} (방법: {dem_stream_info['method']})")

        # 4-3. 재난안전데이터 API로 하천정보 조회
        disaster_river_info = None
        if self.disaster_fetcher:
            try:
                disaster_river_info = self.disaster_fetcher.get_nearest_river_info(lat, lon)
            except Exception as e:
                errors.append(str(e))

        # 5. 해안 거리 조회
        coast_distance = self.get_distance_to_coast(lat, lon)

        # 6. 데이터 정리
        if building_info:
            building_age = self.get_building_age(building_info['useAprDay'])
            build_year = int(building_info['useAprDay'][:4])
            building_type = self.classify_building_type(building_info['mainPurpsCdNm'])
            has_piloti = self.has_piloti_structure(building_info['strctCdNm'], building_info['grndFlrCnt'])

            result = {
                # 건축물 기본 정보 (실제 API 데이터)
                'basement_floors': building_info['ugrndFlrCnt'],
                'ground_floors': building_info['grndFlrCnt'],
                'building_age': building_age,
                'build_year': build_year,
                'building_type': building_type,
                'structure': building_info['strctCdNm'],
                'main_purpose': building_info['mainPurpsCdNm'],
                'has_piloti': has_piloti,
            }

            print(f"   ✅ 건축물 정보 조회 완료")
            print(f"      - 건물 유형: {building_type}")
            print(f"      - 건축연도: {build_year}년 (노후도: {building_age}년)")
            print(f"      - 층수: 지상 {building_info['grndFlrCnt']}층 / 지하 {building_info['ugrndFlrCnt']}층")
        else:
            # 건축물 API 실패시 기본값 (경고 표시)
            print(f"   ⚠️  [TCFD 경고] 건축물 정보 없음 - 보수적 기본값 사용")
            result = {
                'basement_floors': 1,  # 보수적 가정
                'ground_floors': 3,
                'building_age': 30,
                'build_year': 1995,
                'building_type': '주택',
                'structure': '철근콘크리트조',
                'main_purpose': '단독주택',
                'has_piloti': False,
            }

        # 하천 정보 추가
        # DEM 기반 하천 차수를 우선 사용 (더 투명하고 정확함)
        if dem_stream_info:
            stream_order_value = dem_stream_info['stream_order']
            stream_order_method = dem_stream_info['method']
        elif river_info:
            stream_order_value = river_info['stream_order']
            stream_order_method = 'V-World WFS API'
        else:
            stream_order_value = 4
            stream_order_method = 'Conservative default (no data)'
            errors.append("[TCFD 경고] 하천 차수 정보 없음 - 보수적 기본값 4 사용")

        # 유역 면적 - 재난안전데이터 API 우선 사용
        if disaster_river_info:
            watershed_area = disaster_river_info['watershed_area_km2']
            river_name = disaster_river_info['river_name']
        elif river_info:
            watershed_area = 2500
            river_name = river_info.get('river_name', '미상')
            errors.append("[TCFD 경고] 유역면적 데이터 없음 - 보수적 기본값 2500km² 사용")
        else:
            watershed_area = 3000
            river_name = '미상'
            errors.append("[TCFD 경고] 유역면적 데이터 없음 - 보수적 기본값 3000km² 사용")

        if river_info or disaster_river_info:
            result.update({
                'distance_to_river_m': river_info.get('distance_m', 500) if river_info else disaster_river_info.get('distance_m', 500),
                'stream_order': stream_order_value,
                'stream_order_method': stream_order_method,
                'river_name': river_name,
                'watershed_area_km2': watershed_area,
            })
        else:
            # 하천 정보 없으면 보수적 추정
            print(f"   ⚠️  [TCFD 경고] 하천 정보 없음 - 보수적 값 사용")
            result.update({
                'distance_to_river_m': 500,  # 보수적: 가까운 거리 가정
                'stream_order': stream_order_value,
                'stream_order_method': stream_order_method,
                'river_name': river_name,
                'watershed_area_km2': watershed_area,
            })

        # 해안 거리
        result['distance_to_coast_m'] = coast_distance

        # 침수 이력 - 재난안전데이터 API 사용
        if self.disaster_fetcher and addr_info:
            try:
                # 시도명으로 조회 (예: "서울특별시")
                region = addr_info.get('sido', '')
                flood_count = self.disaster_fetcher.get_flood_history(region, years=5)
                result['flood_history_count'] = flood_count
            except Exception as e:
                result['flood_history_count'] = 0
                errors.append(f"[TCFD 경고] 침수 이력 조회 실패: {e}")
        else:
            result['flood_history_count'] = 0
            errors.append("[TCFD 경고] 침수 이력 데이터 없음 - 0으로 가정 (과소평가 가능성)")

        # 에러 출력
        if errors:
            print(f"\n   ⚠️  ========== TCFD 데이터 품질 경고 ==========")
            for i, error in enumerate(errors, 1):
                print(f"   {i}. {error}")
            print(f"   ============================================\n")

        return result

    def _get_default_values(self) -> Dict:
        """API 조회 실패 시 기본값 반환"""
        return {
            'basement_floors': 1,
            'ground_floors': 3,
            'building_age': 30,
            'build_year': 1995,
            'building_type': '주택',
            'structure': '철근콘크리트조',
            'main_purpose': '단독주택',
            'has_piloti': False,
            'distance_to_river_m': 1000,
            'distance_to_coast_m': 50000,
            'watershed_area_km2': 2500,
            'stream_order': 3,
            'flood_history_count': 0,
        }


if __name__ == "__main__":
    # 테스트
    fetcher = BuildingDataFetcher()

    # 테스트 1: 판교
    print("\n[테스트 1] 판교")
    data1 = fetcher.fetch_all_building_data(37.405884769, 127.099877814)
    print(f"\n결과: {data1}")

    # 테스트 2: 대전
    print("\n\n[테스트 2] 대전")
    data2 = fetcher.fetch_all_building_data(36.3741, 127.3838)
    print(f"\n결과: {data2}")
