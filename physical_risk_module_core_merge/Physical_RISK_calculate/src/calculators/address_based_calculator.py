#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
도로명 주소 기반 리스크 계산기

여러 도로명 주소를 입력받아 자동으로:
1. 주소 → 좌표 변환 (VWorld Geocoder API)
2. 각 좌표에 대해 9개 리스크 계산
3. 결과를 JSON 파일로 저장
"""

import os
import json
import requests
from typing import List, Dict
from pathlib import Path
from dotenv import load_dotenv
from hazard_calculator import HazardCalculator

# 환경변수 로드
BASE_DIR = Path(__file__).parent.parent
load_dotenv(BASE_DIR / ".env")


class AddressBasedCalculator:
    """
    도로명 주소 기반 리스크 계산기
    """

    def __init__(self, scenario: str = 'SSP585', target_year: int = 2050):
        self.vworld_api_key = os.getenv("VWORLD_API_KEY")
        self.calculator = HazardCalculator(scenario=scenario, target_year=target_year)
        self.scenario = scenario
        self.target_year = target_year

    def address_to_coords(self, address: str) -> Dict:
        """
        도로명 주소 → 좌표 변환 (VWorld Geocoder API)

        Args:
            address: 도로명 주소 (예: "서울특별시 강남구 테헤란로 152")

        Returns:
            {
                'address': str,      # 입력 주소
                'lat': float,        # 위도
                'lon': float,        # 경도
                'sido': str,         # 시도명
                'sigungu': str,      # 시군구명
                'success': bool,     # 성공 여부
                'error': str         # 오류 메시지 (실패 시)
            }
        """
        url = "https://api.vworld.kr/req/address"
        params = {
            "service": "address",
            "request": "getCoord",
            "version": "2.0",
            "crs": "EPSG:4326",
            "address": address,
            "format": "json",
            "type": "ROAD",  # 도로명 주소
            "key": self.vworld_api_key
        }

        try:
            response = requests.get(url, params=params, timeout=10)
            data = response.json()

            if data['response']['status'] != 'OK':
                return {
                    'address': address,
                    'success': False,
                    'error': f"VWorld API 응답 실패: {data['response'].get('status')}"
                }

            results = data['response']['result']
            if not results or results['point']['x'] == '0':
                return {
                    'address': address,
                    'success': False,
                    'error': "해당 주소를 찾을 수 없음"
                }

            # 좌표 추출
            point = results['point']
            lon = float(point['x'])
            lat = float(point['y'])

            # 시도/시군구 추출 (추가 API 호출 필요)
            address_info = self._get_address_from_coords(lat, lon)

            return {
                'address': address,
                'lat': lat,
                'lon': lon,
                'sido': address_info.get('sido', ''),
                'sigungu': address_info.get('sigungu', ''),
                'success': True
            }

        except Exception as e:
            return {
                'address': address,
                'success': False,
                'error': str(e)
            }

    def _get_address_from_coords(self, lat: float, lon: float) -> Dict:
        """
        좌표 → 주소 정보 추출 (역지오코딩)

        Args:
            lat: 위도
            lon: 경도

        Returns:
            {'sido': str, 'sigungu': str}
        """
        url = "https://api.vworld.kr/req/address"
        params = {
            "service": "address",
            "request": "getAddress",
            "version": "2.0",
            "crs": "EPSG:4326",
            "point": f"{lon},{lat}",
            "format": "json",
            "type": "PARCEL",
            "key": self.vworld_api_key
        }

        try:
            response = requests.get(url, params=params, timeout=10)
            data = response.json()

            if data['response']['status'] == 'OK':
                results = data['response']['result']
                if results:
                    for item in results:
                        structure = item.get('structure', {})
                        sido = structure.get('level1', '')
                        sigungu = structure.get('level2', '')
                        if sido:
                            return {'sido': sido, 'sigungu': sigungu}

            return {'sido': '', 'sigungu': ''}

        except Exception:
            return {'sido': '', 'sigungu': ''}

    def calculate_from_addresses(self, addresses: List[str], output_dir: str = None) -> List[Dict]:
        """
        여러 도로명 주소에 대해 리스크 계산

        Args:
            addresses: 도로명 주소 리스트
            output_dir: 결과 저장 디렉토리 (None이면 저장 안함)

        Returns:
            결과 리스트
        """
        results = []

        print("\n" + "="*80)
        print(f"도로명 주소 기반 리스크 계산 ({len(addresses)}개 지점)")
        print(f"시나리오: {self.scenario}, 분석연도: {self.target_year}")
        print("="*80)

        for i, address in enumerate(addresses, 1):
            print(f"\n[{i}/{len(addresses)}] {address}")
            print("-" * 80)

            # 1. 주소 → 좌표 변환
            coords_result = self.address_to_coords(address)

            if not coords_result['success']:
                print(f"   ❌ 주소 변환 실패: {coords_result['error']}")
                results.append({
                    'address': address,
                    'success': False,
                    'error': coords_result['error']
                })
                continue

            lat = coords_result['lat']
            lon = coords_result['lon']
            print(f"   ✅ 좌표 변환 성공: ({lat:.6f}, {lon:.6f})")
            print(f"      위치: {coords_result['sido']} {coords_result['sigungu']}")

            # 2. 리스크 계산
            try:
                hazard_result = self.calculator.calculate(lat, lon)

                result = {
                    'address': address,
                    'lat': lat,
                    'lon': lon,
                    'sido': coords_result['sido'],
                    'sigungu': coords_result['sigungu'],
                    'success': True,
                    'scenario': self.scenario,
                    'target_year': self.target_year,
                    'hazards': hazard_result
                }

                results.append(result)
                print(f"   ✅ 리스크 계산 완료")

            except Exception as e:
                print(f"   ❌ 리스크 계산 실패: {e}")
                results.append({
                    'address': address,
                    'lat': lat,
                    'lon': lon,
                    'success': False,
                    'error': str(e)
                })

        # 3. 결과 저장
        if output_dir:
            self._save_results(results, output_dir)

        # 4. 요약 출력
        self._print_summary(results)

        return results

    def _save_results(self, results: List[Dict], output_dir: str):
        """
        결과를 JSON 파일로 저장

        Args:
            results: 계산 결과 리스트
            output_dir: 저장 디렉토리
        """
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        # 파일명: address_based_risk_SSP585_2050.json
        filename = f"address_based_risk_{self.scenario}_{self.target_year}.json"
        filepath = output_path / filename

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)

        print(f"\n💾 결과 저장: {filepath}")

    def _print_summary(self, results: List[Dict]):
        """
        계산 결과 요약 출력

        Args:
            results: 계산 결과 리스트
        """
        print("\n" + "="*80)
        print("계산 결과 요약")
        print("="*80)

        total = len(results)
        success = sum(1 for r in results if r['success'])
        failed = total - success

        print(f"\n총 {total}개 지점:")
        print(f"  ✅ 성공: {success}개")
        print(f"  ❌ 실패: {failed}개")

        if failed > 0:
            print(f"\n실패한 주소:")
            for r in results:
                if not r['success']:
                    print(f"  - {r['address']}: {r.get('error', '알 수 없는 오류')}")

        # 성공한 지점의 리스크 요약
        if success > 0:
            print(f"\n리스크 요약 (성공한 {success}개 지점):")
            print("-" * 80)

            for r in results:
                if r['success']:
                    hazards = r['hazards']
                    print(f"\n📍 {r['address']}")
                    print(f"   위치: {r['sido']} {r['sigungu']} ({r['lat']:.4f}, {r['lon']:.4f})")

                    # 주요 리스크만 출력
                    heat = hazards['extreme_heat']
                    cold = hazards['extreme_cold']
                    slr = hazards['sea_level_rise']

                    if 'hci' in heat:
                        print(f"   🌡️  극심한 고온: HCI {heat['hci']:.3f} ({heat['hazard_level']})")
                    if 'cci' in cold:
                        print(f"   ❄️  극심한 저온: CCI {cold['cci']:.3f} ({cold['hazard_level']})")

                    if 'slr_increase_cm' in slr:
                        if slr['coastal_exposure']:
                            print(f"   🌊 해수면 상승: {slr['slr_increase_cm']:+.1f}cm ({slr['hazard_level']})")
                        else:
                            print(f"   🌊 해수면 상승: 내륙 (해안 {slr['distance_to_coast_m']/1000:.1f}km)")


# 테스트 코드
if __name__ == "__main__":
    # 여러 도로명 주소 테스트
    test_addresses = [
        # 광역시/특별시
        "서울특별시 강남구 테헤란로 152",        # 서울 강남 (SK텔레콤)
        "부산광역시 해운대구 해운대해변로 264",   # 부산 해운대 (해안)
        "대전광역시 유성구 대학로 291",         # 대전 유성 (KAIST)
        "인천광역시 연수구 송도과학로 127",      # 인천 송도 (해안)
        "광주광역시 북구 용봉로 77",            # 광주 (전남대)

        # 도 지역
        "경기도 수원시 영통구 삼성로 129",       # 수원 (삼성전자)
        "강원특별자치도 춘천시 강원대학길 1",    # 춘천 (강원대)
        "충청남도 천안시 서북구 성환읍 대학로 91",  # 천안 (나사렛대)
        "전라북도 전주시 덕진구 백제대로 567",   # 전주 (전북대)
        "경상남도 창원시 의창구 창원대학로 20",  # 창원 (창원대)
    ]

    # 계산기 초기화
    calculator = AddressBasedCalculator(scenario='SSP585', target_year=2050)

    # 결과 저장 디렉토리
    output_dir = BASE_DIR / "data" / "address_based_results"

    # 계산 실행
    results = calculator.calculate_from_addresses(test_addresses, output_dir=str(output_dir))

    print("\n✅ 모든 계산 완료!")
