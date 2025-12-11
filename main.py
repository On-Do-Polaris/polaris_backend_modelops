"""
ModelOps Site Assessment API
사업장 리스크 평가 및 이전 후보지 추천 API

FastAPI 메인 앱
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from modelops.api.routes import health, site_assessment
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
    title="ModelOps Site Assessment API",
    description="""
    사업장 리스크 평가 및 이전 후보지 추천 API

    ## Features
    - **사업장 리스크 계산**: 건물 정보 기반 9개 기후 리스크 통합 평가
    - **이전 후보지 추천**: ~1000개 후보 격자를 평가하여 최적 입지 추천
    - **AAL 기반 의사결정**: 기후 리스크와 건물 취약성을 결합한 연평균 손실 계산
    - **자동 배치 처리**: Hazard, Probability 스케줄러로 전국 격자 데이터 자동 계산
    - **결과 저장**: 계산 결과 자동 DB 저장

    ## 계산 프로세스
    1. **H (Hazard)**: DB 조회 (스케줄러가 미리 계산)
    2. **E (Exposure)**: 건물 정보 기반 노출도 계산
    3. **V (Vulnerability)**: 건물 특성 기반 취약성 계산
    4. **통합 리스크**: H × E × V / 10000
    5. **AAL 계산**: base_aal × F_vuln × (1 - insurance_rate)
       - base_aal: DB 조회 (기후만 고려)
       - F_vuln: 0.9 + (V_score / 100) × 0.2

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
    ### Site Assessment (사업장 리스크 평가)
    - POST `/api/v1/site-assessment/calculate`: 사업장 리스크 계산
    - POST `/api/v1/site-assessment/recommend-locations`: 이전 후보지 추천

    ### Health Check
    - GET `/health`: 서버 상태 확인
    - GET `/health/db`: 데이터베이스 연결 확인
    """,
    version="2.0.0",
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
app.include_router(site_assessment.router)
app.include_router(health.router)


@app.on_event("startup")
async def startup_event():
    """서버 시작 시 실행"""
    global probability_scheduler, hazard_scheduler

    logger.info("=" * 60)
    logger.info("ModelOps Site Assessment API 시작")
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

    logger.info("ModelOps Site Assessment API 종료")


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "ModelOps Site Assessment API",
        "version": "2.0.0",
        "description": "사업장 리스크 평가 및 이전 후보지 추천 API",
        "docs": "/docs",
        "health": "/health",
        "features": [
            "사업장 리스크 계산 (건물 정보 기반 H × E × V)",
            "이전 후보지 추천 (~1000개 격자 평가)",
            "AAL 기반 의사결정 (base_aal × F_vuln)",
            "자동 배치 처리 (Hazard, Probability 스케줄러)"
        ],
        "calculation_process": {
            "1_hazard": "DB 조회 (스케줄러가 미리 계산)",
            "2_exposure": "건물 정보 기반 노출도 계산",
            "3_vulnerability": "건물 특성 기반 취약성 계산",
            "4_integrated_risk": "H × E × V / 10000",
            "5_aal": "base_aal × F_vuln × (1 - insurance_rate)"
        },
        "endpoints": {
            "calculate_site_risk": "POST /api/v1/site-assessment/calculate",
            "recommend_locations": "POST /api/v1/site-assessment/recommend-locations",
            "health": "GET /health",
            "health_db": "GET /health/db"
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
