"""
ModelOps Risk Assessment API
E, V, AAL 계산 API with Real-time Progress

FastAPI 메인 앱
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from modelops.api.routes import risk_assessment, health, site_assessment
from modelops.batch.probability_scheduler import ProbabilityScheduler
from modelops.batch.hazard_scheduler import HazardScheduler
import logging

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

# 스케줄러 인스턴스
probability_scheduler = None
hazard_scheduler = None

# FastAPI 앱 생성
app = FastAPI(
    title="ModelOps Risk Assessment API",
    description="""
    H (Hazard), E (Exposure), V (Vulnerability), AAL (Average Annual Loss) 통합 계산 API

    ## Features
    - **H × E × V 통합 리스크 계산**: 9개 기후 리스크 통합 점수 산출
    - **사업장 리스크 계산**: 건물 정보 기반 사업장별 리스크 평가
    - **이전 후보지 추천**: ~1000개 후보 격자를 평가하여 최적 입지 추천
    - **실시간 계산**: WebSocket을 통한 실시간 진행상황 제공
    - **Mini-batch 처리**: 9개 리스크 순차 계산
    - **자동 데이터 수집**: DB에서 필요한 데이터 자동 조회
    - **결과 저장**: 계산 결과 자동 DB 저장

    ## 9개 Physical Risks
    1. extreme_heat (극한 고온)
    2. extreme_cold (극한 한파)
    3. wildfire (산불)
    4. drought (가뭄)
    5. water_stress (물 부족)
    6. sea_level_rise (해수면 상승)
    7. river_flood (하천 홍수)
    8. urban_flood (도시 홍수)
    9. typhoon (태풍)

    ## API Endpoints
    ### Risk Assessment (일반 리스크 계산)
    - POST `/api/v1/risk-assessment/calculate`: 계산 시작
    - GET `/api/v1/risk-assessment/status?request_id=...`: 진행상황 조회
    - WebSocket `/api/v1/risk-assessment/ws/{request_id}`: 실시간 진행상황
    - GET `/api/v1/risk-assessment/results?latitude=...&longitude=...`: 저장된 결과 조회

    ### Site Assessment (사업장 리스크 평가)
    - POST `/api/v1/site-assessment/calculate`: 사업장 리스크 계산
    - POST `/api/v1/site-assessment/recommend-locations`: 이전 후보지 추천

    ### Health Check
    - GET `/health`: 서버 상태 확인
    - GET `/health/db`: 데이터베이스 연결 확인
    """,
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 프로덕션에서는 특정 도메인만 허용
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 라우터 등록
app.include_router(risk_assessment.router)
app.include_router(site_assessment.router)
app.include_router(health.router)


@app.on_event("startup")
async def startup_event():
    """서버 시작 시 실행"""
    global probability_scheduler, hazard_scheduler

    logger.info("=" * 60)
    logger.info("ModelOps Risk Assessment API 시작")
    logger.info("=" * 60)
    logger.info("API 문서: http://localhost:8001/docs")
    logger.info("Health Check: http://localhost:8001/health")
    logger.info("=" * 60)

    # 스케줄러 시작
    try:
        probability_scheduler = ProbabilityScheduler()
        probability_scheduler.start()
        logger.info("✓ Probability 배치 스케줄러 시작")

        hazard_scheduler = HazardScheduler()
        hazard_scheduler.start()
        logger.info("✓ Hazard 배치 스케줄러 시작")
    except Exception as e:
        logger.error(f"✗ 스케줄러 시작 실패: {e}")
        logger.warning("스케줄러 없이 API 서버를 계속 실행합니다")


@app.on_event("shutdown")
async def shutdown_event():
    """서버 종료 시 실행"""
    global probability_scheduler, hazard_scheduler

    # 스케줄러 종료
    if probability_scheduler:
        probability_scheduler.stop()
        logger.info("Probability 배치 스케줄러 종료")

    if hazard_scheduler:
        hazard_scheduler.stop()
        logger.info("Hazard 배치 스케줄러 종료")

    logger.info("ModelOps Risk Assessment API 종료")


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "ModelOps Risk Assessment API",
        "version": "1.0.0",
        "description": "H × E × V 통합 리스크 계산 API with Real-time Progress",
        "docs": "/docs",
        "health": "/health",
        "features": [
            "H (Hazard) 점수 계산",
            "E (Exposure) 점수 계산",
            "V (Vulnerability) 점수 계산",
            "H × E × V 통합 리스크 점수 계산",
            "AAL (Average Annual Loss) 스케일링"
        ],
        "endpoints": {
            "risk_assessment": {
                "calculate": "POST /api/v1/risk-assessment/calculate",
                "status": "GET /api/v1/risk-assessment/status?request_id=...",
                "websocket": "WS /api/v1/risk-assessment/ws/{request_id}",
                "results": "GET /api/v1/risk-assessment/results?latitude=...&longitude=..."
            },
            "site_assessment": {
                "calculate_site_risk": "POST /api/v1/site-assessment/calculate",
                "recommend_locations": "POST /api/v1/site-assessment/recommend-locations"
            }
        }
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8001,
        log_level="info"
    )
