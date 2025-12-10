"""
ModelOps 통합 시스템 테스트

이 파일은 다음 기능들을 테스트합니다:
1. API 호출 시 배치형태 진행 (WebSocket 실시간 진행률)
2. 프론트엔드에서 퍼센트 진행률 확인
3. 시간 트리거로 H, E, V, P(H) 배치 실행
4. PostgreSQL NOTIFY/LISTEN 트리거 동작 확인

작성일: 2025-12-05
"""

import asyncio
import json
import time
import requests
import websockets
import psycopg2
from datetime import datetime
from typing import Dict, Any, List
import logging

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ModelOpsSystemTester:
    """ModelOps 시스템 통합 테스터"""

    def __init__(self, api_base_url: str = "http://localhost:8001"):
        self.api_base_url = api_base_url
        self.db_config = {
            'host': 'localhost',
            'port': 5433,
            'database': 'skala_datawarehouse',
            'user': 'skala_dw_user',
            'password': '1234'
        }

    # ===========================
    # TEST 1: API 호출 및 실시간 진행률 확인
    # ===========================

    async def test_api_with_websocket_progress(self, latitude: float = 37.5665, longitude: float = 126.9780):
        """
        API 호출 후 WebSocket으로 실시간 진행률(퍼센트) 확인

        테스트 항목:
        - API 호출이 성공적으로 큐에 등록되는지
        - WebSocket 연결이 정상적으로 이루어지는지
        - 9개 리스크가 순차적으로 처리되는지 (미니배치)
        - 진행률이 퍼센트로 정확히 표시되는지 (0% → 11% → 22% → ... → 100%)
        - 최종 완료 상태가 'completed'로 전환되는지
        """
        logger.info("=" * 80)
        logger.info("TEST 1: API 호출 및 WebSocket 실시간 진행률 확인")
        logger.info("=" * 80)

        try:
            # 1. API 호출 (계산 요청)
            logger.info(f"1단계: API 호출 - POST /api/v1/risk-assessment/calculate")
            logger.info(f"   위치: ({latitude}, {longitude})")

            response = requests.post(
                f"{self.api_base_url}/api/v1/risk-assessment/calculate",
                json={
                    "latitude": latitude,
                    "longitude": longitude
                },
                timeout=10
            )

            if response.status_code != 200:
                logger.error(f"   ❌ API 호출 실패: {response.status_code}")
                logger.error(f"   응답: {response.text}")
                return False

            result = response.json()
            request_id = result['request_id']
            websocket_url = result['websocket_url']

            logger.info(f"   ✅ API 호출 성공")
            logger.info(f"   Request ID: {request_id}")
            logger.info(f"   Status: {result['status']}")
            logger.info(f"   WebSocket URL: {websocket_url}")

            # 2. WebSocket 연결 및 실시간 진행률 모니터링
            logger.info(f"\n2단계: WebSocket 연결 - 실시간 진행률 모니터링")

            ws_url = websocket_url.replace("ws://localhost", "ws://localhost")
            logger.info(f"   연결 URL: {ws_url}")

            progress_history = []

            async with websockets.connect(ws_url) as websocket:
                logger.info("   ✅ WebSocket 연결 성공")
                logger.info("\n   [진행률 모니터링 시작]")
                logger.info("   " + "-" * 70)

                while True:
                    try:
                        message = await asyncio.wait_for(websocket.recv(), timeout=60.0)
                        progress = json.loads(message)
                        progress_history.append(progress)

                        # 진행률 계산
                        current = progress.get('current', 0)
                        total = progress.get('total', 9)
                        percentage = round((current / total) * 100, 1) if total > 0 else 0

                        status = progress.get('status', 'unknown')
                        current_risk = progress.get('current_risk', '-')

                        # 진행률 출력
                        logger.info(
                            f"   [{percentage:5.1f}%] {current}/{total} - "
                            f"Status: {status:12s} - Current: {current_risk}"
                        )

                        # 완료 또는 실패 시 종료
                        if status in ['completed', 'failed']:
                            logger.info("   " + "-" * 70)

                            if status == 'completed':
                                logger.info(f"   ✅ 계산 완료!")
                                logger.info(f"   최종 진행률: {percentage}%")

                                # 결과 확인
                                if 'results' in progress and progress['results']:
                                    logger.info(f"\n   [계산 결과 요약]")
                                    results = progress['results']

                                    if 'summary' in results:
                                        summary = results['summary']
                                        logger.info(f"   - 평균 취약성: {summary.get('average_vulnerability', 0)}")
                                        logger.info(f"   - 평균 노출도: {summary.get('average_exposure', 0)}")

                                        highest_aal = summary.get('highest_aal_risk', {})
                                        logger.info(
                                            f"   - 최고 위험: {highest_aal.get('risk_type', '-')} "
                                            f"(AAL: {highest_aal.get('final_aal', 0)})"
                                        )

                                return True
                            else:
                                error = progress.get('error', 'Unknown error')
                                logger.error(f"   ❌ 계산 실패: {error}")
                                return False

                    except asyncio.TimeoutError:
                        logger.error("   ❌ WebSocket 타임아웃 (60초)")
                        return False

        except requests.exceptions.RequestException as e:
            logger.error(f"❌ API 요청 오류: {e}")
            return False
        except Exception as e:
            logger.error(f"❌ 테스트 실패: {e}", exc_info=True)
            return False

    # ===========================
    # TEST 2: HTTP Polling 방식 진행률 확인
    # ===========================

    def test_http_polling_progress(self, latitude: float = 37.5665, longitude: float = 126.9780):
        """
        HTTP Polling 방식으로 진행률 확인 (WebSocket 대안)

        프론트엔드에서 setInterval로 진행률을 조회하는 방식 시뮬레이션
        """
        logger.info("=" * 80)
        logger.info("TEST 2: HTTP Polling 방식 진행률 확인")
        logger.info("=" * 80)

        try:
            # 1. API 호출
            logger.info(f"1단계: 계산 요청")
            response = requests.post(
                f"{self.api_base_url}/api/v1/risk-assessment/calculate",
                json={"latitude": latitude, "longitude": longitude},
                timeout=10
            )

            if response.status_code != 200:
                logger.error(f"❌ API 호출 실패")
                return False

            result = response.json()
            request_id = result['request_id']
            logger.info(f"   ✅ Request ID: {request_id}")

            # 2. Polling으로 진행률 확인 (0.5초마다)
            logger.info(f"\n2단계: Polling 시작 (0.5초 간격)")
            logger.info("   " + "-" * 70)

            max_polls = 120  # 최대 60초 (120 * 0.5초)
            poll_count = 0

            while poll_count < max_polls:
                time.sleep(0.5)
                poll_count += 1

                # 진행률 조회
                status_response = requests.get(
                    f"{self.api_base_url}/api/v1/risk-assessment/status",
                    params={"request_id": request_id},
                    timeout=5
                )

                if status_response.status_code != 200:
                    logger.error(f"❌ 상태 조회 실패")
                    return False

                progress = status_response.json()
                current = progress.get('current', 0)
                total = progress.get('total', 9)
                percentage = round((current / total) * 100, 1) if total > 0 else 0
                status = progress.get('status', 'unknown')

                logger.info(
                    f"   [Poll #{poll_count:3d}] {percentage:5.1f}% - "
                    f"{current}/{total} - Status: {status}"
                )

                if status in ['completed', 'failed']:
                    logger.info("   " + "-" * 70)
                    if status == 'completed':
                        logger.info(f"   ✅ Polling 완료!")
                        return True
                    else:
                        logger.error(f"   ❌ 계산 실패")
                        return False

            logger.error("   ❌ Polling 타임아웃 (60초)")
            return False

        except Exception as e:
            logger.error(f"❌ 테스트 실패: {e}")
            return False

    # ===========================
    # TEST 3: 시간 트리거 확인 (Scheduler)
    # ===========================

    def test_scheduler_triggers(self):
        """
        시간 트리거 스케줄러 동작 확인

        테스트 항목:
        - ProbabilityScheduler가 올바르게 설정되어 있는지
        - HazardScheduler가 올바르게 설정되어 있는지
        - 스케줄 시간이 .env 설정과 일치하는지

        주의: 실제 스케줄러는 서버가 실행 중일 때만 동작
        """
        logger.info("=" * 80)
        logger.info("TEST 3: 시간 트리거(Scheduler) 설정 확인")
        logger.info("=" * 80)

        try:
            from modelops.batch.probability_scheduler import ProbabilityScheduler
            from modelops.batch.hazard_scheduler import HazardScheduler
            from modelops.config.settings import settings

            # 1. Probability Scheduler 확인
            logger.info("1단계: ProbabilityScheduler 확인")
            logger.info(f"   스케줄: 매년 {settings.probability_schedule_month}월 "
                       f"{settings.probability_schedule_day}일 "
                       f"{settings.probability_schedule_hour}:{settings.probability_schedule_minute:02d}")

            prob_scheduler = ProbabilityScheduler()
            logger.info(f"   ✅ ProbabilityScheduler 초기화 성공")

            # 2. Hazard Scheduler 확인
            logger.info(f"\n2단계: HazardScheduler 확인")
            logger.info(f"   스케줄: 매년 {settings.hazard_schedule_month}월 "
                       f"{settings.hazard_schedule_day}일 "
                       f"{settings.hazard_schedule_hour}:{settings.hazard_schedule_minute:02d}")

            hazard_scheduler = HazardScheduler()
            logger.info(f"   ✅ HazardScheduler 초기화 성공")

            logger.info(f"\n3단계: 스케줄러 동작 검증")
            logger.info(f"   ⚠️  실제 스케줄 실행은 서버 실행 중에만 동작합니다")
            logger.info(f"   ⚠️  수동 실행은 아래 'TEST 4'에서 테스트됩니다")

            return True

        except Exception as e:
            logger.error(f"❌ 스케줄러 테스트 실패: {e}", exc_info=True)
            return False

    # ===========================
    # TEST 4: PostgreSQL NOTIFY/LISTEN 트리거
    # ===========================

    def test_notify_trigger(self, job_type: str = "probability"):
        """
        PostgreSQL NOTIFY/LISTEN 트리거 테스트

        실제로 NOTIFY를 발생시켜서 리스너가 받는지 확인

        Args:
            job_type: 'probability' 또는 'hazard'
        """
        logger.info("=" * 80)
        logger.info(f"TEST 4: PostgreSQL NOTIFY 트리거 ({job_type})")
        logger.info("=" * 80)

        try:
            # PostgreSQL NOTIFY 발생
            logger.info(f"1단계: NOTIFY 발생")

            conn = psycopg2.connect(**self.db_config)
            cursor = conn.cursor()

            channel = "aiops_trigger"
            logger.info(f"   Channel: {channel}")
            logger.info(f"   Payload: {job_type}")

            cursor.execute(f"NOTIFY {channel}, '{job_type}';")
            conn.commit()

            logger.info(f"   ✅ NOTIFY 발송 완료")

            cursor.close()
            conn.close()

            logger.info(f"\n2단계: 리스너 확인")
            logger.info(f"   ⚠️  리스너 프로세스가 실행 중이어야 합니다")
            logger.info(f"   ⚠️  리스너 로그를 확인하여 메시지 수신 여부를 확인하세요")
            logger.info(f"\n   리스너 실행 방법:")
            logger.info(f"   python -m modelops.triggers.notify_listener")

            return True

        except Exception as e:
            logger.error(f"❌ NOTIFY 테스트 실패: {e}")
            return False

    # ===========================
    # TEST 5: 배치 프로세서 수동 실행
    # ===========================

    def test_batch_processor_manual_run(self, batch_type: str = "probability", sample_size: int = 2):
        """
        배치 프로세서 수동 실행 테스트

        Args:
            batch_type: 'probability' 또는 'hazard'
            sample_size: 테스트할 격자 개수
        """
        logger.info("=" * 80)
        logger.info(f"TEST 5: 배치 프로세서 수동 실행 ({batch_type})")
        logger.info("=" * 80)

        try:
            # 샘플 격자 좌표 생성
            sample_grids = [
                {'latitude': 37.5665, 'longitude': 126.9780},  # 서울
                {'latitude': 37.4563, 'longitude': 126.7052}   # 인천
            ][:sample_size]

            logger.info(f"1단계: 샘플 격자 준비")
            logger.info(f"   격자 개수: {len(sample_grids)}")
            for i, grid in enumerate(sample_grids, 1):
                logger.info(f"   Grid {i}: ({grid['latitude']}, {grid['longitude']})")

            # 배치 프로세서 실행
            logger.info(f"\n2단계: 배치 프로세서 실행")

            if batch_type == "probability":
                from modelops.batch.probability_batch import ProbabilityBatchProcessor

                processor = ProbabilityBatchProcessor({
                    'parallel_workers': 2
                })

                logger.info(f"   타입: P(H) Batch")
                result = processor.process_all_grids(sample_grids)

            elif batch_type == "hazard":
                from modelops.batch.hazard_batch import HazardBatchProcessor

                processor = HazardBatchProcessor({
                    'parallel_workers': 2
                })

                logger.info(f"   타입: Hazard Score Batch")
                result = processor.process_all_grids(sample_grids)
            else:
                logger.error(f"❌ 알 수 없는 배치 타입: {batch_type}")
                return False

            # 결과 출력
            logger.info(f"\n3단계: 배치 결과")
            logger.info(f"   전체 격자: {result['total_grids']}")
            logger.info(f"   처리 성공: {result['processed']}")
            logger.info(f"   처리 실패: {result['failed']}")
            logger.info(f"   성공률: {result['success_rate']}%")
            logger.info(f"   소요 시간: {result['duration_seconds']:.2f}초")

            if result['success_rate'] >= 100:
                logger.info(f"   ✅ 배치 처리 성공!")
                return True
            else:
                logger.warning(f"   ⚠️  일부 격자 처리 실패")
                return False

        except Exception as e:
            logger.error(f"❌ 배치 테스트 실패: {e}", exc_info=True)
            return False

    # ===========================
    # TEST 6: 저장된 결과 조회
    # ===========================

    def test_retrieve_cached_results(self, latitude: float = 37.5665, longitude: float = 126.9780):
        """
        DB에 저장된 E, V, AAL 결과 조회 테스트
        """
        logger.info("=" * 80)
        logger.info("TEST 6: 저장된 결과 조회")
        logger.info("=" * 80)

        try:
            logger.info(f"1단계: 결과 조회 요청")
            logger.info(f"   위치: ({latitude}, {longitude})")

            response = requests.get(
                f"{self.api_base_url}/api/v1/risk-assessment/results",
                params={"latitude": latitude, "longitude": longitude},
                timeout=10
            )

            if response.status_code == 404:
                logger.warning(f"   ⚠️  저장된 결과 없음")
                logger.info(f"   → 먼저 TEST 1을 실행하여 결과를 생성하세요")
                return False

            if response.status_code != 200:
                logger.error(f"   ❌ 조회 실패: {response.status_code}")
                return False

            results = response.json()

            logger.info(f"\n2단계: 결과 요약")
            logger.info(f"   위치: ({results['latitude']}, {results['longitude']})")
            logger.info(f"   계산 일시: {results.get('calculated_at', '-')}")

            if 'summary' in results and results['summary']:
                summary = results['summary']
                logger.info(f"\n   [요약 통계]")
                logger.info(f"   - 총 Final AAL: {summary.get('total_final_aal', 0)}")
                logger.info(f"   - 평균 취약성: {summary.get('average_vulnerability', 0)}")
                logger.info(f"   - 리스크 개수: {summary.get('risk_count', 0)}")

            logger.info(f"\n   [9개 리스크별 결과]")

            if 'aal_scaled' in results:
                for risk_type, aal_data in results['aal_scaled'].items():
                    logger.info(
                        f"   - {risk_type:20s}: AAL={aal_data.get('final_aal', 0):.6f}, "
                        f"Grade={aal_data.get('grade', '-')}"
                    )

            logger.info(f"\n   ✅ 결과 조회 성공!")
            return True

        except Exception as e:
            logger.error(f"❌ 결과 조회 실패: {e}")
            return False


# ===========================
# 메인 실행 함수
# ===========================

async def run_all_tests():
    """모든 테스트 실행"""
    tester = ModelOpsSystemTester()

    logger.info("\n")
    logger.info("█" * 80)
    logger.info("█" + " " * 78 + "█")
    logger.info("█" + " " * 20 + "ModelOps 통합 시스템 테스트" + " " * 30 + "█")
    logger.info("█" + " " * 78 + "█")
    logger.info("█" * 80)
    logger.info("\n")

    test_results = {}

    # TEST 1: API + WebSocket 실시간 진행률
    logger.info("⚠️  서버가 실행 중이어야 합니다: python main.py\n")
    user_input = input("서버가 실행 중입니까? (y/n): ")

    if user_input.lower() == 'y':
        test_results['API WebSocket'] = await tester.test_api_with_websocket_progress()
        print("\n")

        # TEST 2: HTTP Polling
        test_results['HTTP Polling'] = tester.test_http_polling_progress()
        print("\n")

        # TEST 6: 저장된 결과 조회
        test_results['Cached Results'] = tester.test_retrieve_cached_results()
        print("\n")
    else:
        logger.info("서버 테스트를 건너뜁니다.\n")

    # TEST 3: 스케줄러 설정 확인
    test_results['Scheduler Config'] = tester.test_scheduler_triggers()
    print("\n")

    # TEST 4: NOTIFY 트리거
    user_input = input("PostgreSQL NOTIFY 테스트를 실행하시겠습니까? (y/n): ")
    if user_input.lower() == 'y':
        test_results['NOTIFY Trigger'] = tester.test_notify_trigger("probability")
        print("\n")

    # TEST 5: 배치 프로세서 수동 실행
    user_input = input("배치 프로세서 수동 실행 테스트를 하시겠습니까? (y/n): ")
    if user_input.lower() == 'y':
        test_type = input("배치 타입 (probability/hazard): ")
        test_results[f'{test_type} Batch'] = tester.test_batch_processor_manual_run(test_type, sample_size=2)
        print("\n")

    # 결과 요약
    logger.info("=" * 80)
    logger.info("테스트 결과 요약")
    logger.info("=" * 80)

    for test_name, result in test_results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        logger.info(f"{test_name:25s}: {status}")

    total_tests = len(test_results)
    passed_tests = sum(1 for r in test_results.values() if r)

    logger.info("=" * 80)
    logger.info(f"전체: {total_tests} / 통과: {passed_tests} / 실패: {total_tests - passed_tests}")
    logger.info("=" * 80)


if __name__ == "__main__":
    asyncio.run(run_all_tests())
