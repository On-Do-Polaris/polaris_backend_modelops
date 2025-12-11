"""
Site Assessment API Schemas
사업장 리스크 계산 및 이전 후보지 추천 Request/Response 모델
"""

from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime


class BuildingInfo(BaseModel):
    """건물 정보"""
    building_type: str = Field(..., description="건물 유형 (예: office, factory, warehouse)")
    structure: str = Field(default="철근콘크리트", description="구조 (철근콘크리트, 목조 등)")
    building_age: int = Field(..., description="건물 연식 (년)")
    total_area_m2: float = Field(..., description="연면적 (m²)")
    ground_floors: int = Field(..., description="지상 층수")
    basement_floors: int = Field(default=0, description="지하 층수")
    has_piloti: bool = Field(default=False, description="필로티 구조 여부")
    elevation_m: Optional[float] = Field(None, description="해발고도 (m)")


class AssetInfo(BaseModel):
    """자산 정보"""
    total_value: Optional[float] = Field(None, description="총 자산가치 (원)")
    insurance_coverage_rate: float = Field(default=0.0, description="보험 보전율 (0-1)")


class SiteRiskRequest(BaseModel):
    """사업장 리스크 계산 요청"""
    latitude: float = Field(..., ge=33.0, le=39.0, description="위도")
    longitude: float = Field(..., ge=124.5, le=132.0, description="경도")
    site_id: Optional[str] = Field(None, description="사업장 ID")
    building_info: BuildingInfo = Field(..., description="건물 정보")
    asset_info: Optional[AssetInfo] = Field(None, description="자산 정보")


class SiteRiskResponse(BaseModel):
    """사업장 리스크 계산 응답"""
    site_id: Optional[str] = Field(None, description="사업장 ID")
    latitude: float = Field(..., description="위도")
    longitude: float = Field(..., description="경도")
    hazard: Dict[str, Any] = Field(..., description="9개 리스크별 H 점수")
    exposure: Dict[str, Any] = Field(..., description="9개 리스크별 E 점수")
    vulnerability: Dict[str, Any] = Field(..., description="9개 리스크별 V 점수")
    integrated_risk: Dict[str, Any] = Field(..., description="9개 리스크별 통합 점수 (H × E × V / 10000)")
    aal_scaled: Dict[str, Any] = Field(..., description="9개 리스크별 AAL")
    summary: Dict[str, Any] = Field(..., description="요약 통계")
    calculated_at: datetime = Field(..., description="계산 시각")


class CandidateGrid(BaseModel):
    """후보 격자 좌표"""
    latitude: float = Field(..., ge=33.0, le=39.0, description="위도")
    longitude: float = Field(..., ge=124.5, le=132.0, description="경도")


class SearchCriteria(BaseModel):
    """검색 조건"""
    max_candidates: int = Field(default=3, description="추천 후보지 개수")
    ssp_scenario: str = Field(default="ssp2", description="SSP 시나리오")
    target_year: int = Field(default=2040, description="목표 연도")


class SiteRelocationRequest(BaseModel):
    """사업장 이전 후보지 추천 요청"""
    candidate_grids: List[CandidateGrid] = Field(..., description="후보 격자 리스트 (~1000개)")
    building_info: BuildingInfo = Field(..., description="건물 정보")
    asset_info: Optional[AssetInfo] = Field(None, description="자산 정보")
    search_criteria: Optional[SearchCriteria] = Field(default_factory=SearchCriteria, description="검색 조건")


class RiskDetail(BaseModel):
    """리스크 상세 정보"""
    h_score: float = Field(..., description="Hazard 점수 (0-100)")
    e_score: float = Field(..., description="Exposure 점수 (0-100)")
    v_score: float = Field(..., description="Vulnerability 점수 (0-100)")
    integrated_risk_score: float = Field(..., description="통합 리스크 점수 (H × E × V / 10000)")
    base_aal: float = Field(..., description="기후 기반 AAL (climate-only)")
    f_vuln: float = Field(..., description="취약성 스케일링 계수 (0.9 + V/100 × 0.2)")
    final_aal: float = Field(..., description="최종 AAL (base_aal × f_vuln × (1 - insurance_rate))")


class LocationCandidate(BaseModel):
    """후보지 정보"""
    rank: int = Field(..., description="순위 (1, 2, 3)")
    latitude: float = Field(..., description="위도")
    longitude: float = Field(..., description="경도")
    total_aal: float = Field(..., description="총 AAL (9개 리스크 합계)")
    average_integrated_risk: float = Field(..., description="평균 통합 리스크 점수")
    risk_details: Dict[str, RiskDetail] = Field(..., description="리스크별 상세 정보 (9개)")


class SiteRelocationResponse(BaseModel):
    """사업장 이전 후보지 추천 응답"""
    candidates: List[LocationCandidate] = Field(..., description="추천 후보지 리스트 (최대 3개)")
    total_grids_evaluated: int = Field(..., description="평가된 격자 총 개수")
    search_criteria: SearchCriteria = Field(..., description="검색 조건")
    calculated_at: datetime = Field(..., description="계산 시각")
