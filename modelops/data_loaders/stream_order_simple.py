"""
DEM 데이터에서 scipy/numpy를 사용하여 하천 차수(Stream Order) 추출
TCFD 공시용: 투명한 데이터 기반 하천 차수 계산
WhiteboxTools 대신 순수 Python 구현
"""

import rasterio
import numpy as np
from pathlib import Path
from typing import Optional, Dict
from scipy import ndimage
from pyproj import Transformer


class StreamOrderExtractor:
    """DEM으로부터 하천 차수 추출 클래스 (순수 Python)"""

    def __init__(self, dem_dir: Optional[Path] = None):
        """
        Args:
            dem_dir: DEM 파일이 있는 디렉토리 (기본값: data/DEM/)
        """
        if dem_dir is None:
            base_dir = Path(__file__).parent.parent.parent  # src/data → src → Physical_RISK_calculate
            # shared_data/DEM 대신 data/DEM 사용
            dem_dir = base_dir / "data" / "DEM"

        self.dem_dir = Path(dem_dir)
        print(f"   📁 DEM 디렉토리: {self.dem_dir}")

    def find_dem_file(self, lat: float, lon: float) -> Optional[Path]:
        """
        위/경도에 해당하는 DEM 파일 찾기
        """
        # .tif, .img, .txt 파일 모두 지원
        dem_files = []
        dem_files.extend(list(self.dem_dir.glob("*.tif")))
        dem_files.extend(list(self.dem_dir.glob("*.img")))
        dem_files.extend(list(self.dem_dir.glob("*.txt")))

        if not dem_files:
            raise FileNotFoundError(f"DEM 파일이 없음: {self.dem_dir}")

        # 각 DEM 파일의 범위 확인
        for dem_file in dem_files:
            try:
                with rasterio.open(dem_file) as src:
                    transformer = Transformer.from_crs(
                        src.crs, "EPSG:4326", always_xy=True
                    )

                    bounds = src.bounds
                    min_lon, min_lat = transformer.transform(bounds.left, bounds.bottom)
                    max_lon, max_lat = transformer.transform(bounds.right, bounds.top)

                    # 픽셀 좌표로 변환하여 실제로 범위 내인지 확인
                    transformer_inv = Transformer.from_crs(
                        "EPSG:4326", src.crs, always_xy=True
                    )
                    x, y = transformer_inv.transform(lon, lat)
                    row, col = src.index(x, y)

                    # 픽셀이 DEM 범위 내에 있는지 확인
                    if 0 <= row < src.height and 0 <= col < src.width:
                        print(f"   ✅ DEM 파일 발견: {dem_file.name}")
                        return dem_file

            except Exception as e:
                continue

        # 모든 DEM이 범위 밖이면 None 반환
        raise ValueError(f"좌표 ({lat}, {lon})가 모든 DEM 파일 범위 밖")

    def calculate_flow_accumulation(self, dem: np.ndarray) -> np.ndarray:
        """
        D8 알고리즘으로 Flow Accumulation 계산
        간단한 구현: 고도 기반 하류 방향 계산
        """
        rows, cols = dem.shape
        flow_acc = np.ones_like(dem, dtype=np.float32)

        # 고도순으로 정렬 (높은 곳에서 낮은 곳으로)
        sorted_indices = np.argsort(dem.ravel())[::-1]

        # D8 방향 (8방향)
        dirs = [
            (-1, -1), (-1, 0), (-1, 1),
            (0, -1),           (0, 1),
            (1, -1),  (1, 0),  (1, 1)
        ]

        for idx in sorted_indices:
            r, c = divmod(idx, cols)

            if np.isnan(dem[r, c]):
                continue

            # 현재 셀보다 낮은 인접 셀 중 가장 낮은 셀로 흐름
            min_elevation = dem[r, c]
            min_r, min_c = r, c

            for dr, dc in dirs:
                nr, nc = r + dr, c + dc

                if 0 <= nr < rows and 0 <= nc < cols:
                    if not np.isnan(dem[nr, nc]) and dem[nr, nc] < min_elevation:
                        min_elevation = dem[nr, nc]
                        min_r, min_c = nr, nc

            # 흐름 누적
            if (min_r, min_c) != (r, c):
                flow_acc[min_r, min_c] += flow_acc[r, c]

        return flow_acc

    def estimate_stream_order_from_flow_acc(
        self,
        flow_acc: np.ndarray,
        threshold: int = 1000
    ) -> int:
        """
        Flow Accumulation 값에서 하천 차수 추정

        경험적 규칙:
        - Flow Acc < 1000: 1차 하천 (소하천)
        - 1000-5000: 2차 하천
        - 5000-10000: 3차 하천
        - 10000-50000: 4차 하천
        - > 50000: 5차 이상 하천 (큰 강)
        """
        if flow_acc < 1000:
            return 1
        elif flow_acc < 5000:
            return 2
        elif flow_acc < 10000:
            return 3
        elif flow_acc < 50000:
            return 4
        elif flow_acc < 100000:
            return 5
        else:
            return 6

    def get_stream_order_at_point(
        self,
        lat: float,
        lon: float,
        flow_threshold: int = 1000,
        search_radius: int = 100
    ) -> Optional[Dict]:
        """
        특정 좌표에서의 하천 차수 추출

        Args:
            lat: 위도
            lon: 경도
            flow_threshold: 하천으로 간주할 최소 flow accumulation
            search_radius: 주변 하천 검색 반경 (픽셀)
        """
        try:
            # 1. DEM 파일 찾기
            dem_file = self.find_dem_file(lat, lon)
            if dem_file is None:
                raise ValueError(f"좌표에 해당하는 DEM 파일 없음: ({lat}, {lon})")

            # 2. DEM 읽기
            with rasterio.open(dem_file) as src:
                # WGS84 → DEM CRS 변환
                transformer = Transformer.from_crs(
                    "EPSG:4326", src.crs, always_xy=True
                )
                x, y = transformer.transform(lon, lat)

                # 픽셀 좌표
                row, col = src.index(x, y)

                # 전체 DEM 읽기
                dem = src.read(1).astype(np.float32)
                dem_height, dem_width = dem.shape

                # 좌표가 범위 밖이면 에러
                if not (0 <= row < dem_height and 0 <= col < dem_width):
                    raise ValueError(
                        f"좌표가 DEM 범위 밖: 픽셀({row}, {col}), DEM 크기({dem_height}, {dem_width})"
                    )

                elevation = dem[row, col]

                print(f"   📍 좌표: ({lat}, {lon}) → 픽셀: ({row}, {col}), 고도: {elevation:.1f}m")

            # 3. Flow Accumulation 계산
            print(f"   🔧 Flow Accumulation 계산 중...")
            flow_acc = self.calculate_flow_accumulation(dem)

            # 4. 해당 위치의 Flow Accumulation
            point_flow_acc = flow_acc[row, col]

            # 5. 하천 차수 추정
            if point_flow_acc < flow_threshold:
                # 주변에서 가장 높은 flow accumulation 찾기
                print(f"   ⚠️  해당 위치 Flow Acc({point_flow_acc:.0f}) < 임계값({flow_threshold})")
                print(f"   🔍 주변 {search_radius}픽셀 내 하천 검색...")

                r_min = max(0, row - search_radius)
                r_max = min(dem.shape[0], row + search_radius)
                c_min = max(0, col - search_radius)
                c_max = min(dem.shape[1], col + search_radius)

                search_area = flow_acc[r_min:r_max, c_min:c_max]
                max_flow = np.max(search_area)

                if max_flow >= flow_threshold:
                    point_flow_acc = max_flow
                    print(f"      → 주변 최대 Flow Acc: {max_flow:.0f}")
                else:
                    point_flow_acc = max_flow
                    print(f"      → 주변에도 큰 하천 없음, 최대값 {max_flow:.0f} 사용")

            stream_order = self.estimate_stream_order_from_flow_acc(
                point_flow_acc, flow_threshold
            )

            # 6. 결과 반환
            result = {
                'stream_order': int(stream_order),
                'flow_accumulation': float(point_flow_acc),
                'elevation': float(elevation) if not np.isnan(elevation) else 0.0,
                'method': 'D8 Flow Accumulation + Empirical Stream Order',
                'dem_file': dem_file.name,
                'flow_threshold': flow_threshold
            }

            print(f"   ✅ 하천 차수 추정 완료: {result['stream_order']}차 하천 (Flow Acc: {point_flow_acc:.0f})")

            return result

        except Exception as e:
            print(f"   ❌ 하천 차수 추출 실패: {e}")
            raise ValueError(f"[TCFD 경고] 하천 차수 추출 실패: {e}")


# rasterio와 scipy가 없는 경우를 위한 임시 함수
def get_stream_order_fallback(lat: float, lon: float) -> Dict:
    """
    의존성이 없을 때 사용하는 fallback
    재난안전데이터 API나 다른 방법으로 대체 필요
    """
    print(f"   ⚠️  하천 차수 계산 불가 (의존성 없음), 기본값 3 사용")
    return {
        'stream_order': 3,
        'flow_accumulation': 0.0,
        'elevation': 0.0,
        'method': 'Fallback (default value)',
        'dem_file': 'N/A',
        'flow_threshold': 0
    }


if __name__ == "__main__":
    # 테스트
    print("\n" + "="*60)
    print("하천 차수 추출 테스트 (Scipy/Numpy)")
    print("="*60 + "\n")

    try:
        extractor = StreamOrderExtractor()

        # 테스트 좌표
        test_coords = [
            (37.5172, 127.0473, "서울 강남구 개포동"),
            (37.5665, 126.9780, "서울 시청"),
        ]

        for lat, lon, name in test_coords:
            print(f"\n[테스트] {name} ({lat}, {lon})")
            try:
                result = extractor.get_stream_order_at_point(
                    lat, lon,
                    flow_threshold=500,
                    search_radius=50
                )
                print(f"\n결과:")
                print(f"  - 하천 차수: {result['stream_order']}")
                print(f"  - 유량 누적: {result['flow_accumulation']:.0f}")
                print(f"  - 고도: {result['elevation']:.1f}m")
                print(f"  - 방법: {result['method']}")
                print(f"  - DEM 파일: {result['dem_file']}")
            except Exception as e:
                print(f"실패: {e}")

    except ImportError as e:
        print(f"의존성 부족: {e}")
        print("Fallback 테스트:")
        result = get_stream_order_fallback(37.5172, 127.0473)
        print(f"결과: {result}")
