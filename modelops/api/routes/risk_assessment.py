"""
Risk Assessment API
E, V, AAL 통합 계산 API with WebSocket Real-time Progress
"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException
from ..schemas.risk_models import (
    RiskAssessmentRequest,
    RiskAssessmentResponse,
    ProgressUpdate,
    RiskResultsResponse
)
from ...agents.risk_assessment import IntegratedRiskAgent
from ...database.connection import DatabaseConnection
import asyncio
import uuid
import logging
from datetime import datetime
from typing import Dict, Any

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/risk-assessment", tags=["risk-assessment"])

# 진행상황 저장소 (임시, 실제로는 Redis 사용 권장)
progress_store: Dict[str, Dict[str, Any]] = {}


@router.post("/calculate", response_model=RiskAssessmentResponse)
async def calculate_risk_assessment(request: RiskAssessmentRequest):
    """
    E, V, AAL 통합 계산 API

    Request:
        {
            "latitude": 37.5665,
            "longitude": 126.9780
        }

    Response:
        {
            "request_id": "req-uuid-12345",
            "status": "queued",
            "websocket_url": "ws://localhost:8001/api/v1/risk-assessment/ws/req-uuid-12345"
        }
    """
    request_id = f"req-{uuid.uuid4()}"

    logger.info(f"새로운 계산 요청: {request_id} - ({request.latitude}, {request.longitude})")

    # 초기 상태 저장
    progress_store[request_id] = {
        'status': 'queued',
        'current': 0,
        'total': 9,
        'current_risk': None,
        'results': None,
        'error': None,
        'created_at': datetime.now().isoformat()
    }

    # 백그라운드에서 계산 시작
    asyncio.create_task(
        _execute_calculation(request_id, request.latitude, request.longitude)
    )

    return RiskAssessmentResponse(
        request_id=request_id,
        status="queued",
        websocket_url=f"ws://localhost:8001/api/v1/risk-assessment/ws/{request_id}",
        message="계산이 큐에 등록되었습니다. WebSocket으로 실시간 진행상황을 확인하세요."
    )


async def _execute_calculation(request_id: str, latitude: float, longitude: float):
    """백그라운드 계산 실행"""
    agent = IntegratedRiskAgent(database_connection=DatabaseConnection)

    def progress_callback(current: int, total: int, risk_type: str):
        """진행상황 업데이트 콜백"""
        progress_store[request_id] = {
            'status': 'processing',
            'current': current,
            'total': total,
            'current_risk': risk_type,
            'results': None,
            'error': None
        }
        logger.info(f"[{request_id}] Progress: {current}/{total} - {risk_type}")

    try:
        logger.info(f"[{request_id}] 계산 시작")

        # 계산 실행
        results = agent.calculate_all_risks(
            latitude=latitude,
            longitude=longitude,
            progress_callback=progress_callback
        )

        # 완료 상태 업데이트
        progress_store[request_id] = {
            'status': 'completed',
            'current': 9,
            'total': 9,
            'current_risk': None,
            'results': results,
            'error': None
        }

        logger.info(f"[{request_id}] 계산 완료")

    except Exception as e:
        # 에러 상태 업데이트
        logger.error(f"[{request_id}] 계산 실패: {e}", exc_info=True)
        progress_store[request_id] = {
            'status': 'failed',
            'current': progress_store[request_id].get('current', 0),
            'total': 9,
            'current_risk': None,
            'error': str(e),
            'results': None
        }


@router.get("/status/{request_id}")
async def get_calculation_status(request_id: str):
    """
    계산 진행 상황 조회 (HTTP Polling 방식)

    Response:
        {
            "status": "processing",
            "current": 3,
            "total": 9,
            "current_risk": "wildfire"
        }
    """
    if request_id not in progress_store:
        raise HTTPException(
            status_code=404,
            detail=f"Request ID not found: {request_id}"
        )

    return progress_store[request_id]


@router.websocket("/ws/{request_id}")
async def websocket_progress(websocket: WebSocket, request_id: str):
    """
    WebSocket으로 실시간 진행상황 전송

    클라이언트 예시 (JavaScript):
        const ws = new WebSocket('ws://localhost:8001/api/v1/risk-assessment/ws/req-12345');
        ws.onmessage = (event) => {
            const progress = JSON.parse(event.data);
            console.log(`Progress: ${progress.current}/${progress.total} - ${progress.current_risk}`);
        };

    클라이언트 예시 (Python):
        import asyncio
        import websockets
        import json

        async def watch_progress():
            async with websockets.connect(ws_url) as websocket:
                while True:
                    message = await websocket.recv()
                    progress = json.loads(message)
                    if progress['status'] == 'completed':
                        break
    """
    await websocket.accept()
    logger.info(f"WebSocket 연결: {request_id}")

    try:
        last_state = None

        while True:
            # 진행상황 확인
            if request_id in progress_store:
                current_state = progress_store[request_id]

                # 상태 변경 시에만 전송
                if current_state != last_state:
                    await websocket.send_json(current_state)
                    last_state = current_state.copy()

                    # 완료 또는 실패 시 종료
                    if current_state['status'] in ['completed', 'failed']:
                        logger.info(f"WebSocket 종료: {request_id} - {current_state['status']}")
                        await asyncio.sleep(1)  # 최종 메시지 전송 후 1초 대기
                        break
            else:
                # Request ID가 없으면 에러
                await websocket.send_json({
                    'status': 'error',
                    'error': 'Request ID not found'
                })
                break

            await asyncio.sleep(0.5)  # 0.5초마다 체크

    except WebSocketDisconnect:
        logger.info(f"WebSocket 연결 끊김: {request_id}")
    except Exception as e:
        logger.error(f"WebSocket 에러: {e}")
    finally:
        # 완료 후 일정 시간 후 삭제 (메모리 관리)
        await asyncio.sleep(300)  # 5분 후
        if request_id in progress_store:
            del progress_store[request_id]
            logger.info(f"Progress store 삭제: {request_id}")


@router.get("/results/{latitude}/{longitude}")
async def get_cached_results(latitude: float, longitude: float):
    """
    저장된 E, V, AAL 결과 조회

    Response:
        {
            "latitude": 37.5665,
            "longitude": 126.9780,
            "exposure": {risk_type: {...}},
            "vulnerability": {risk_type: {...}},
            "aal_scaled": {risk_type: {...}},
            "summary": {...},
            "calculated_at": "2025-12-01T10:30:00Z"
        }
    """
    try:
        # DB에서 조회
        with DatabaseConnection.get_connection() as conn:
            cursor = conn.cursor()

            # Exposure 조회
            cursor.execute("""
                SELECT risk_type, exposure_score, proximity_factor, calculated_at
                FROM exposure_results
                WHERE latitude = %s AND longitude = %s
            """, (latitude, longitude))
            exposure_rows = cursor.fetchall()

            # Vulnerability 조회
            cursor.execute("""
                SELECT risk_type, vulnerability_score, vulnerability_level, factors, calculated_at
                FROM vulnerability_results
                WHERE latitude = %s AND longitude = %s
            """, (latitude, longitude))
            vulnerability_rows = cursor.fetchall()

            # AAL 조회
            cursor.execute("""
                SELECT risk_type, base_aal, vulnerability_scale, final_aal,
                       insurance_rate, expected_loss, calculated_at
                FROM aal_scaled_results
                WHERE latitude = %s AND longitude = %s
            """, (latitude, longitude))
            aal_rows = cursor.fetchall()

        # 데이터가 없으면 404
        if not exposure_rows and not vulnerability_rows and not aal_rows:
            raise HTTPException(
                status_code=404,
                detail=f"No results found for location ({latitude}, {longitude})"
            )

        # 결과 변환
        exposure = {row['risk_type']: dict(row) for row in exposure_rows}
        vulnerability = {row['risk_type']: dict(row) for row in vulnerability_rows}
        aal_scaled = {row['risk_type']: dict(row) for row in aal_rows}

        # 요약 통계 계산
        if aal_scaled:
            total_final_aal = sum(aal['final_aal'] for aal in aal_scaled.values())
            avg_vulnerability = sum(v['vulnerability_score'] for v in vulnerability.values()) / len(vulnerability) if vulnerability else 0

            summary = {
                'total_final_aal': round(total_final_aal, 6),
                'average_vulnerability': round(avg_vulnerability, 2),
                'risk_count': len(aal_scaled)
            }
        else:
            summary = None

        # 가장 최근 계산 시각
        all_timestamps = []
        if exposure_rows:
            all_timestamps.append(exposure_rows[0]['calculated_at'])
        if vulnerability_rows:
            all_timestamps.append(vulnerability_rows[0]['calculated_at'])
        if aal_rows:
            all_timestamps.append(aal_rows[0]['calculated_at'])

        calculated_at = max(all_timestamps) if all_timestamps else None

        return {
            'latitude': latitude,
            'longitude': longitude,
            'exposure': exposure,
            'vulnerability': vulnerability,
            'aal_scaled': aal_scaled,
            'summary': summary,
            'calculated_at': calculated_at
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"결과 조회 실패: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve results: {str(e)}"
        )
