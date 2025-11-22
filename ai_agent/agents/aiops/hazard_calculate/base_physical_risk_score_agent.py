'''
파일명: base_physical_risk_score_agent.py
최종 수정일: 2025-11-13
버전: v02
파일 개요: 물리적 리스크 종합 점수 산출 베이스 Agent (H×E×V 기반)
변경 이력:
	- 2025-11-11: v01 - H×E×V 방식에서 AAL×자산가치 방식으로 변경
	- 2025-11-13: v02 - AAL×자산가치 방식에서 H×E×V 방식으로 복원
'''
from typing import Dict, Any
from abc import ABC, abstractmethod
import logging


logger = logging.getLogger(__name__)


class BasePhysicalRiskScoreAgent(ABC):
	"""
	물리적 리스크 종합 점수 산출 베이스 Agent
	H (Hazard) × E (Exposure) × V (Vulnerability) 기반 리스크 점수 계산
	"""

	def __init__(self, risk_type: str):
		"""
		BasePhysicalRiskScoreAgent 초기화

		Args:
			risk_type: 리스크 타입 (예: 'high_temperature', 'typhoon')
		"""
		self.risk_type = risk_type
		self.logger = logger
		self.logger.info(f"{risk_type} Physical Risk Score Agent 초기화")

	def calculate_physical_risk_score(
		self,
		collected_data: Dict[str, Any],
		vulnerability_analysis: Dict[str, Any],
		asset_info: Dict[str, Any]
	) -> Dict[str, Any]:
		"""
		물리적 리스크 종합 점수 계산 (H × E × V)

		Args:
			collected_data: 수집된 기후 데이터
			vulnerability_analysis: 취약성 분석 결과
			asset_info: 사업장 자산 정보

		Returns:
			물리적 리스크 종합 점수 딕셔너리
				- risk_type: 리스크 타입
				- hazard_score: Hazard 점수 (0.0 ~ 1.0)
				- exposure_score: Exposure 점수 (0.0 ~ 1.0)
				- vulnerability_score: Vulnerability 점수 (0.0 ~ 1.0)
				- physical_risk_score: 물리적 리스크 점수 (0.0 ~ 1.0)
				- physical_risk_score_100: 100점 스케일 점수
				- risk_level: 위험 등급
				- calculation_details: 계산 상세 내역
				- status: 계산 상태
		"""
		self.logger.info(f"{self.risk_type} Physical Risk Score 계산 시작 (H×E×V)")

		try:
			# 1. Hazard 점수 계산
			hazard_score = self.calculate_hazard(collected_data)

			# 2. Exposure 점수 계산
			exposure_score = self.calculate_exposure(asset_info)

			# 3. Vulnerability 점수 계산
			vulnerability_score = self.calculate_vulnerability(vulnerability_analysis, asset_info)

			# 4. 물리적 리스크 점수 = H × E × V
			physical_risk_score = hazard_score * exposure_score * vulnerability_score

			# 5. 100점 스케일 변환
			physical_risk_score_100 = physical_risk_score * 100

			# 6. 위험 등급 산출
			risk_level = self.get_risk_level(physical_risk_score_100)

			result = {
				'risk_type': self.risk_type,
				'hazard_score': round(hazard_score, 4),
				'exposure_score': round(exposure_score, 4),
				'vulnerability_score': round(vulnerability_score, 4),
				'physical_risk_score': round(physical_risk_score, 4),
				'physical_risk_score_100': round(physical_risk_score_100, 2),
				'risk_level': risk_level,
				'calculation_details': {
					'formula': 'Physical Risk Score = H × E × V',
					'components': {
						'Hazard (H)': round(hazard_score, 4),
						'Exposure (E)': round(exposure_score, 4),
						'Vulnerability (V)': round(vulnerability_score, 4)
					},
					'result': {
						'Risk Score': round(physical_risk_score, 4),
						'Risk Score (100-scale)': round(physical_risk_score_100, 2)
					}
				},
				'status': 'completed'
			}

			self.logger.info(
				f"{self.risk_type} Physical Risk Score 계산 완료: "
				f"{physical_risk_score_100:.2f}/100 (H={hazard_score:.2f}, E={exposure_score:.2f}, V={vulnerability_score:.2f})"
			)
			return result

		except Exception as e:
			self.logger.error(f"{self.risk_type} Physical Risk Score 계산 중 오류: {str(e)}", exc_info=True)
			return {
				'risk_type': self.risk_type,
				'status': 'failed',
				'error': str(e)
			}

	@abstractmethod
	def calculate_hazard(self, collected_data: Dict[str, Any]) -> float:
		"""
		Hazard 점수 계산
		기후 위험의 강도 및 발생 빈도 평가

		Args:
			collected_data: 수집된 기후 데이터

		Returns:
			Hazard 점수 (0.0 ~ 1.0)
		"""
		pass

	@abstractmethod
	def calculate_exposure(self, asset_info: Dict[str, Any]) -> float:
		"""
		Exposure 점수 계산
		자산 및 인프라의 노출 정도 평가

		Args:
			asset_info: 사업장 자산 정보

		Returns:
			Exposure 점수 (0.0 ~ 1.0)
		"""
		pass

	@abstractmethod
	def calculate_vulnerability(
		self,
		vulnerability_analysis: Dict[str, Any],
		asset_info: Dict[str, Any]
	) -> float:
		"""
		Vulnerability 점수 계산
		자산 및 시설의 취약성 평가

		Args:
			vulnerability_analysis: 취약성 분석 결과
			asset_info: 사업장 자산 정보

		Returns:
			Vulnerability 점수 (0.0 ~ 1.0)
		"""
		pass

	def get_risk_level(self, physical_risk_score_100: float) -> str:
		"""
		물리적 리스크 점수에 따른 위험 등급 반환

		Args:
			physical_risk_score_100: 물리적 리스크 종합 점수 (0 ~ 100)

		Returns:
			위험 등급 문자열
				- 'Very High': 80 이상
				- 'High': 60 ~ 80
				- 'Medium': 40 ~ 60
				- 'Low': 20 ~ 40
				- 'Very Low': 20 미만
		"""
		if physical_risk_score_100 >= 80:
			return 'Very High'
		elif physical_risk_score_100 >= 60:
			return 'High'
		elif physical_risk_score_100 >= 40:
			return 'Medium'
		elif physical_risk_score_100 >= 20:
			return 'Low'
		else:
			return 'Very Low'

	def get_recommendation(self, physical_risk_score_100: float) -> str:
		"""
		물리적 리스크 점수에 따른 권고사항 생성

		Args:
			physical_risk_score_100: 물리적 리스크 종합 점수 (0 ~ 100)

		Returns:
			권고사항 문자열
		"""
		risk_level = self.get_risk_level(physical_risk_score_100)

		recommendations = {
			'Very High': f'{self.risk_type} 리스크에 대한 즉각적인 대응 조치가 필요합니다. 비상 대응 계획을 수립하고 정기적 모니터링을 실시하세요.',
			'High': f'{self.risk_type} 리스크가 높습니다. 예방적 조치를 강화하고 대응 체계를 점검하세요.',
			'Medium': f'{self.risk_type} 리스크를 지속적으로 모니터링하고 필요시 대응 방안을 마련하세요.',
			'Low': f'{self.risk_type} 리스크는 낮으나 정기적인 모니터링이 필요합니다.',
			'Very Low': f'{self.risk_type} 리스크는 매우 낮지만 기후 변화 추세를 주시하세요.'
		}

		return recommendations.get(risk_level, '정기적인 리스크 재평가가 필요합니다.')
