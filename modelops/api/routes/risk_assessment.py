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
            "longitude": 126.9780,
            "site_id": "SITE-2025-001",  (optional)
            "building_info": {...},  (optional)
            "asset_info": {...}  (optional)
        }

    Response:
        {
            "request_id": "req-uuid-12345",
            "status": "queued",
            "websocket_url": "ws://localhost:8001/api/v1/risk-assessment/ws/req-uuid-12345",
            "site_id": "SITE-2025-001"
        }
    """
    request_id = f"req-{uuid.uuid4()}"

    logger.info(f"새로운 계산 요청: {request_id} - ({request.latitude}, {request.longitude})")
    if request.site_id:
        logger.info(f"  site_id: {request.site_id}")
    if request.building_info:
        logger.info(f"  커스텀 건물 정보 제공됨")
    if request.asset_info:
        logger.info(f"  커스텀 자산 정보 제공됨")

    # 초기 상태 저장
    progress_store[request_id] = {
        'status': 'queued',
        'current': 0,
        'total': 9,
        'current_risk': None,
        'results': None,
        'error': None,
        'created_at': datetime.now().isoformat(),
        'site_id': request.site_id
    }

    # 백그라운드에서 계산 시작
    asyncio.create_task(
        _execute_calculation(
            request_id,
            request.latitude,
            request.longitude,
            request.site_id,
            request.building_info,
            request.asset_info
        )
    )

    return RiskAssessmentResponse(
        request_id=request_id,
        status="queued",
        websocket_url=f"ws://localhost:8001/api/v1/risk-assessment/ws/{request_id}",
        message="계산이 큐에 등록되었습니다. WebSocket으로 실시간 진행상황을 확인하세요.",
        site_id=request.site_id
    )


async def _execute_calculation(
    request_id: str,
    latitude: float,
    longitude: float,
    site_id: Optional[str] = None,
    building_info: Optional[Dict] = None,
    asset_info: Optional[Dict] = None
):
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
            'error': None,
            'site_id': site_id
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

        # site_id를 결과에 추가
        if site_id:
            results['site_id'] = site_id

        # 완료 상태 업데이트
        progress_store[request_id] = {
            'status': 'completed',
            'current': 9,
            'total': 9,
            'current_risk': None,
            'results': results,
            'error': None,
            'site_id': site_id
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


@router.get("/status")
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


@router.get("/results")
async def get_cached_results(latitude: float, longitude: float):
    """
    저장된 H, E, V, AAL 결과 조회 및 통합 리스크 계산

    Response:
        {
            "latitude": 37.5665,
            "longitude": 126.9780,
            "hazard": {risk_type: {"hazard_score": 0.4, "hazard_score_100": 40, ...}},
            "exposure": {risk_type: {"exposure_score": 80, ...}},
            "vulnerability": {risk_type: {"vulnerability_score": 50, ...}},
            "integrated_risk": {risk_type: {"h_score": 40, "e_score": 80, "v_score": 50, "integrated_risk_score": 16.0, ...}},
            "aal_scaled": {risk_type: {"base_aal": 0.01, "final_aal": 0.011, ...}},
            "summary": {
                "average_hazard": 35.5,
                "average_exposure": 45.0,
                "average_vulnerability": 50.0,
                "average_integrated_risk": 12.5,
                "highest_integrated_risk": {"risk_type": "river_flood", "integrated_risk_score": 25.0, "risk_level": "Low"},
                "total_final_aal": 0.09,
                "risk_count": 9
            },
            "calculated_at": "2025-12-01T10:30:00Z"
        }
    """
    try:
        # DB에서 조회
        with DatabaseConnection.get_connection() as conn:
            cursor = conn.cursor()

            # Hazard 조회 (추가)
            cursor.execute("""
                SELECT risk_type, hazard_score, hazard_score_100, hazard_level, calculated_at
                FROM hazard_results
                WHERE latitude = %s AND longitude = %s
            """, (latitude, longitude))
            hazard_rows = cursor.fetchall()

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
        if not hazard_rows and not exposure_rows and not vulnerability_rows and not aal_rows:
            raise HTTPException(
                status_code=404,
                detail=f"No results found for location ({latitude}, {longitude})"
            )

        # 결과 변환
        hazard = {row['risk_type']: dict(row) for row in hazard_rows}
        exposure = {row['risk_type']: dict(row) for row in exposure_rows}
        vulnerability = {row['risk_type']: dict(row) for row in vulnerability_rows}
        aal_scaled = {row['risk_type']: dict(row) for row in aal_rows}

        # Integrated Risk 계산 (H × E × V / 10000)
        integrated_risk = {}
        for risk_type in hazard.keys():
            h_score = hazard[risk_type].get('hazard_score_100', 0.0)
            e_score = exposure.get(risk_type, {}).get('exposure_score', 0.0)
            v_score = vulnerability.get(risk_type, {}).get('vulnerability_score', 0.0)

            # H × E × V 계산
            risk_score = (h_score * e_score * v_score) / 10000.0

            # 위험도 등급 분류
            if risk_score >= 80:
                risk_level = 'Very High'
            elif risk_score >= 60:
                risk_level = 'High'
            elif risk_score >= 40:
                risk_level = 'Medium'
            elif risk_score >= 20:
                risk_level = 'Low'
            else:
                risk_level = 'Very Low'

            integrated_risk[risk_type] = {
                'h_score': round(h_score, 2),
                'e_score': round(e_score, 2),
                'v_score': round(v_score, 2),
                'integrated_risk_score': round(risk_score, 2),
                'risk_level': risk_level,
                'formula': f'{h_score:.2f} × {e_score:.2f} × {v_score:.2f} / 10000 = {risk_score:.2f}'
            }

        # 요약 통계 계산
        if hazard and vulnerability and integrated_risk:
            avg_hazard = sum(h['hazard_score_100'] for h in hazard.values()) / len(hazard) if hazard else 0
            avg_exposure = sum(e['exposure_score'] for e in exposure.values()) / len(exposure) if exposure else 0
            avg_vulnerability = sum(v['vulnerability_score'] for v in vulnerability.values()) / len(vulnerability) if vulnerability else 0
            avg_integrated_risk = sum(ir['integrated_risk_score'] for ir in integrated_risk.values()) / len(integrated_risk) if integrated_risk else 0

            # 최고 통합 리스크
            if integrated_risk:
                highest_risk = max(integrated_risk.items(), key=lambda x: x[1]['integrated_risk_score'])
                highest_integrated_risk = {
                    'risk_type': highest_risk[0],
                    'integrated_risk_score': highest_risk[1]['integrated_risk_score'],
                    'risk_level': highest_risk[1]['risk_level']
                }
            else:
                highest_integrated_risk = None

            summary = {
                'average_hazard': round(avg_hazard, 2),
                'average_exposure': round(avg_exposure, 2),
                'average_vulnerability': round(avg_vulnerability, 2),
                'average_integrated_risk': round(avg_integrated_risk, 2),
                'highest_integrated_risk': highest_integrated_risk,
                'total_final_aal': round(sum(aal['final_aal'] for aal in aal_scaled.values()), 6) if aal_scaled else 0,
                'risk_count': len(hazard)
            }
        else:
            summary = None

        # 가장 최근 계산 시각
        all_timestamps = []
        if hazard_rows:
            all_timestamps.append(hazard_rows[0]['calculated_at'])
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
            'hazard': hazard,
            'exposure': exposure,
            'vulnerability': vulnerability,
            'integrated_risk': integrated_risk,
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
