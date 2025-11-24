'''
파일명: base_hazard_hscore_agent.py
최종 수정일: 2025-11-21
버전: v1
파일 개요: Hazard 점수(H) 계산 베이스 Agent
변경 이력:
	- 2025-11-21: v1 - H×E×V에서 H만 계산하도록 분리
		* Exposure, Vulnerability 계산 제거
		* Hazard 점수만 계산
		* 클래스명: BasePhysicalRiskScoreAgent → BaseHazardHScoreAgent
'''
from typing import Dict, Any
from abc import ABC, abstractmethod
import logging
  

logger = logging.getLogger(__name__)


class BaseHazardHScoreAgent(ABC):
	"""
	Hazard 점수(H) 계산 베이스 Agent
	기후 위험의 강도 및 발생 빈도 평가
	"""

	def __init__(self, risk_type: str):
		"""
		BaseHazardHScoreAgent 초기화

		Args:
			risk_type: 리스크 타입 (예: 'high_temperature', 'typhoon')
		"""
		self.risk_type = risk_type
		self.logger = logger
		self.logger.info(f"{risk_type} Hazard Score Agent 초기화")

	def calculate_hazard_score(
		self,
		collected_data: Dict[str, Any]
	) -> Dict[str, Any]:
		"""
		Hazard 점수(H) 계산

		Args:
			collected_data: 수집된 기후 데이터

		Returns:
			Hazard 점수 딕셔너리
				- risk_type: 리스크 타입
				- hazard_score: Hazard 점수 (0.0 ~ 1.0)
				- hazard_score_100: 100점 스케일 점수
				- hazard_level: 위험 등급
				- calculation_details: 계산 상세 내역
				- status: 계산 상태
		"""
		self.logger.info(f"{self.risk_type} Hazard Score 계산 시작")

		try:
			# Hazard 점수 계산 (추상 메서드)
			hazard_score = self.calculate_hazard(collected_data)

			# 100점 스케일 변환
			hazard_score_100 = hazard_score * 100

			# 위험 등급 산출
			hazard_level = self.get_hazard_level(hazard_score_100)

			result = {
				'risk_type': self.risk_type,
				'hazard_score': round(hazard_score, 4),
				'hazard_score_100': round(hazard_score_100, 2),
				'hazard_level': hazard_level,
				'calculation_details': {
					'formula': 'Hazard Score (H) - 기후 위험 강도 및 발생 빈도',
					'result': {
						'Hazard Score': round(hazard_score, 4),
						'Hazard Score (100-scale)': round(hazard_score_100, 2)
					}
				},
				'status': 'completed'
			}

			self.logger.info(
				f"{self.risk_type} Hazard Score 계산 완료: "
				f"{hazard_score_100:.2f}/100 (H={hazard_score:.4f})"
			)
			return result

		except Exception as e:
			self.logger.error(f"{self.risk_type} Hazard Score 계산 중 오류: {str(e)}", exc_info=True)
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

	def get_hazard_level(self, hazard_score_100: float) -> str:
		"""
		Hazard 점수에 따른 위험 등급 반환

		Args:
			hazard_score_100: Hazard 점수 (0 ~ 100)

		Returns:
			위험 등급 문자열
				- 'Very High': 80 이상
				- 'High': 60 ~ 80
				- 'Medium': 40 ~ 60
				- 'Low': 20 ~ 40
				- 'Very Low': 20 미만
		"""
		if hazard_score_100 >= 80:
			return 'Very High'
		elif hazard_score_100 >= 60:
			return 'High'
		elif hazard_score_100 >= 40:
			return 'Medium'
		elif hazard_score_100 >= 20:
			return 'Low'
		else:
			return 'Very Low'

	def get_recommendation(self, hazard_score_100: float) -> str:
		"""
		Hazard 점수에 따른 권고사항 생성

		Args:
			hazard_score_100: Hazard 점수 (0 ~ 100)

		Returns:
			권고사항 문자열
		"""
		hazard_level = self.get_hazard_level(hazard_score_100)

		recommendations = {
			'Very High': f'{self.risk_type} 위험이 매우 높습니다. 즉각적인 모니터링과 대응 준비가 필요합니다.',
			'High': f'{self.risk_type} 위험이 높습니다. 예방적 조치를 강화하세요.',
			'Medium': f'{self.risk_type} 위험을 지속적으로 모니터링하세요.',
			'Low': f'{self.risk_type} 위험은 낮으나 정기적인 확인이 필요합니다.',
			'Very Low': f'{self.risk_type} 위험은 매우 낮지만 기후 변화 추세를 주시하세요.'
		}

		return recommendations.get(hazard_level, '정기적인 위험 재평가가 필요합니다.')
