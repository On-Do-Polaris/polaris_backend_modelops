# LLM 입력 데이터 명세서

## 개요

LLM이 **근거 기반 기후 리스크 리포트**를 생성하기 위해 필요한 데이터 구조를 정의합니다.

이 문서는 ModelOps API 또는 Batch 프로세서에서 계산된 결과를 LLM에게 전달하기 위한 **JSON 형식 데이터 스펙**입니다.

---

## 핵심 원칙

1. **최종 점수 + 계산 근거**: H, E, V 점수뿐만 아니라 **왜 그런 점수가 나왔는지** 설명할 수 있는 중간 데이터 포함
2. **정량적 증거**: LLM이 "WSDI가 37.8일로 전국 평균 25.3일 대비 49% 높습니다" 같은 구체적 문장을 작성할 수 있도록 원본 수치 제공
3. **시계열 추세**: 과거 데이터와 비교하여 "최근 10년간 15% 증가" 같은 트렌드 분석 가능하도록 시계열 데이터 포함
4. **상대적 비교**: 전국 평균, 동일 시도 평균과의 비교 데이터 제공
5. **AAL은 백분율**: AAL 값은 0~1 범위의 소수(백분율)로 제공, LLM이 필요시 자산가치를 곱해 원화로 환산

---

## JSON 데이터 구조

```json
{
  "location": {
    "latitude": 37.5665,
    "longitude": 126.9780,
    "address": "서울특별시 중구 세종대로 110",
    "sido": "서울특별시",
    "sigungu": "중구"
  },

  "building": {
    "building_id": "1168010100100940007000001",
    "main_purpose": "업무시설",
    "main_structure": "철근콘크리트구조",
    "total_area": 15840.5,
    "construction_year": 1995,
    "building_age": 30,
    "floors_above": 12,
    "floors_below": 3,
    "asset_value": 158405000000,
    "asset_value_display": "1,584억원"
  },

  "risks": {
    "extreme_heat": {
      "H": {
        "score": 78.5,
        "level": "HIGH",
        "explanation": {
          "climate_variable": "WSDI",
          "variable_description": "Warm Spell Duration Index (연속 폭염 일수)",
          "current_value": 37.8,
          "unit": "days",
          "trend": {
            "last_10_years_avg": 32.1,
            "last_20_years_avg": 28.5,
            "change_rate_10y": "+17.8%",
            "change_rate_20y": "+32.6%",
            "trend_direction": "상승"
          },
          "comparison": {
            "national_avg": 25.3,
            "sido_avg": 31.2,
            "percentile_national": "상위 8%",
            "percentile_sido": "상위 15%"
          },
          "threshold_analysis": {
            "Q80": 30.5,
            "Q90": 35.2,
            "Q95": 39.1,
            "Q99": 45.6,
            "current_position": "Q90~Q95 사이"
          },
          "score_calculation": {
            "base_score": 70,
            "trend_penalty": 5,
            "extreme_value_penalty": 3.5,
            "final_score": 78.5,
            "reasoning": "기본 점수 70점에 10년 추세 악화(+5점), 극값 페널티(+3.5점) 적용"
          }
        }
      },

      "E": {
        "score": 0.85,
        "explanation": {
          "exposure_factors": {
            "location_exposure": 0.9,
            "building_size_factor": 1.05,
            "proximity_to_hazard": "고위험 지역 내 위치"
          },
          "calculation": {
            "base_exposure": 0.8,
            "size_adjustment": 0.05,
            "final_exposure": 0.85,
            "reasoning": "대형 업무시설(면적 15,840㎡)로 노출도 증가"
          }
        }
      },

      "V": {
        "score": 68,
        "level": "MEDIUM",
        "explanation": {
          "base_score": 50,
          "factors": [
            {
              "factor": "building_age",
              "value": 30,
              "penalty": 18,
              "reason": "준공 후 30년 경과 (기준: 20년 이상 +15점, 30년 이상 +18점)"
            },
            {
              "factor": "main_structure",
              "value": "철근콘크리트구조",
              "penalty": 0,
              "reason": "내구성 우수 (RC 구조: 페널티 없음)"
            },
            {
              "factor": "floors_above",
              "value": 12,
              "penalty": 0,
              "reason": "층수 12층 (고층 건물 아님, 페널티 없음)"
            },
            {
              "factor": "main_purpose",
              "value": "업무시설",
              "penalty": 0,
              "reason": "냉방 시설 보유 가능성 높음 (페널티 없음)"
            }
          ],
          "calculation": {
            "base": 50,
            "age_penalty": 18,
            "structure_penalty": 0,
            "purpose_penalty": 0,
            "total_penalty": 18,
            "final_score": 68,
            "reasoning": "건물 노후도가 주요 취약 요인 (30년 경과 → +18점)"
          }
        }
      },

      "AAL": {
        "base_aal": 0.0785,
        "vulnerability_scale": 1.036,
        "final_aal": 0.0814,
        "insurance_rate": 0.0,
        "explanation": {
          "formula": "AAL = Σ(P[i] × DR[i]) × F_vuln × (1 - IR)",
          "base_aal_percentage": "7.85%",
          "final_aal_percentage": "8.14%",
          "vulnerability_scaling_formula": "F_vuln = 0.9 + (V/100) × 0.2 = 0.9 + (68/100) × 0.2 = 1.036",
          "expected_loss_krw": 12894487000,
          "expected_loss_display": "128억 9,449만원",
          "bin_details": [
            {
              "bin": "MINIMAL",
              "probability": 0.35,
              "damage_rate": 0.02,
              "contribution": 0.007,
              "contribution_percentage": "0.7%"
            },
            {
              "bin": "LOW",
              "probability": 0.28,
              "damage_rate": 0.08,
              "contribution": 0.0224,
              "contribution_percentage": "2.24%"
            },
            {
              "bin": "MEDIUM",
              "probability": 0.20,
              "damage_rate": 0.18,
              "contribution": 0.036,
              "contribution_percentage": "3.6%"
            },
            {
              "bin": "HIGH",
              "probability": 0.12,
              "damage_rate": 0.35,
              "contribution": 0.042,
              "contribution_percentage": "4.2%"
            },
            {
              "bin": "CRITICAL",
              "probability": 0.05,
              "damage_rate": 0.60,
              "contribution": 0.03,
              "contribution_percentage": "3.0%"
            }
          ],
          "calculation_steps": [
            "1. Base AAL = Σ(P[i] × DR[i]) = 0.35×0.02 + 0.28×0.08 + 0.20×0.18 + 0.12×0.35 + 0.05×0.60 = 0.0785",
            "2. F_vuln = 0.9 + (68/100) × 0.2 = 1.036",
            "3. Final AAL = 0.0785 × 1.036 × (1 - 0.0) = 0.0814",
            "4. Expected Loss = 0.0814 × 1,584억원 = 약 129억원"
          ]
        }
      }
    },

    "river_flood": {
      "H": {
        "score": 85.2,
        "level": "CRITICAL",
        "explanation": {
          "climate_variable": "RX5DAY",
          "variable_description": "5일 최대 강수량",
          "current_value": 385.6,
          "unit": "mm",
          "trend": {
            "last_10_years_avg": 342.8,
            "last_20_years_avg": 315.2,
            "change_rate_10y": "+12.5%",
            "change_rate_20y": "+22.3%",
            "trend_direction": "상승"
          },
          "comparison": {
            "national_avg": 295.3,
            "sido_avg": 358.7,
            "percentile_national": "상위 3%",
            "percentile_sido": "상위 12%"
          },
          "threshold_analysis": {
            "Q80": 320.5,
            "Q90": 365.8,
            "Q95": 405.2,
            "Q99": 485.3,
            "current_position": "Q90~Q95 사이"
          },
          "additional_factors": {
            "river_proximity": "한강 500m 이내",
            "elevation": "해발 15m (저지대)",
            "flood_history": "최근 10년간 침수 이력 2회"
          },
          "score_calculation": {
            "base_score": 75,
            "trend_penalty": 5,
            "proximity_penalty": 5,
            "elevation_penalty": 0.2,
            "final_score": 85.2,
            "reasoning": "기본 점수 75점에 추세 악화(+5점), 하천 근접(+5점), 저지대(+0.2점) 적용"
          }
        }
      },

      "E": {
        "score": 0.92,
        "explanation": {
          "exposure_factors": {
            "location_exposure": 0.95,
            "building_size_factor": 1.05,
            "proximity_to_river": "500m 이내",
            "ground_floor_area": 1320.0,
            "ground_floor_exposure": "1층 면적 1,320㎡ 침수 가능"
          },
          "calculation": {
            "base_exposure": 0.85,
            "proximity_adjustment": 0.07,
            "final_exposure": 0.92,
            "reasoning": "하천 근접(500m 이내) 및 대형 건물로 노출도 매우 높음"
          }
        }
      },

      "V": {
        "score": 72,
        "level": "HIGH",
        "explanation": {
          "base_score": 50,
          "factors": [
            {
              "factor": "building_age",
              "value": 30,
              "penalty": 18,
              "reason": "준공 후 30년 경과"
            },
            {
              "factor": "basement_floors",
              "value": 3,
              "penalty": 4,
              "reason": "지하 3층 보유 (침수 시 피해 증가, +4점)"
            },
            {
              "factor": "main_structure",
              "value": "철근콘크리트구조",
              "penalty": 0,
              "reason": "내수성 우수"
            }
          ],
          "calculation": {
            "base": 50,
            "age_penalty": 18,
            "basement_penalty": 4,
            "structure_penalty": 0,
            "total_penalty": 22,
            "final_score": 72,
            "reasoning": "노후 건물(30년)과 지하층 보유로 침수 취약성 높음"
          }
        }
      },

      "AAL": {
        "base_aal": 0.0942,
        "vulnerability_scale": 1.044,
        "final_aal": 0.0983,
        "insurance_rate": 0.0,
        "explanation": {
          "formula": "AAL = Σ(P[i] × DR[i]) × F_vuln × (1 - IR)",
          "base_aal_percentage": "9.42%",
          "final_aal_percentage": "9.83%",
          "vulnerability_scaling_formula": "F_vuln = 0.9 + (72/100) × 0.2 = 1.044",
          "expected_loss_krw": 15571131500,
          "expected_loss_display": "155억 7,113만원",
          "bin_details": [
            {
              "bin": "MINIMAL",
              "probability": 0.30,
              "damage_rate": 0.03,
              "contribution": 0.009,
              "contribution_percentage": "0.9%"
            },
            {
              "bin": "LOW",
              "probability": 0.25,
              "damage_rate": 0.10,
              "contribution": 0.025,
              "contribution_percentage": "2.5%"
            },
            {
              "bin": "MEDIUM",
              "probability": 0.22,
              "damage_rate": 0.22,
              "contribution": 0.0484,
              "contribution_percentage": "4.84%"
            },
            {
              "bin": "HIGH",
              "probability": 0.15,
              "damage_rate": 0.40,
              "contribution": 0.06,
              "contribution_percentage": "6.0%"
            },
            {
              "bin": "CRITICAL",
              "probability": 0.08,
              "damage_rate": 0.70,
              "contribution": 0.056,
              "contribution_percentage": "5.6%"
            }
          ]
        }
      }
    },

    "drought": {
      "H": {
        "score": 45.3,
        "level": "LOW",
        "explanation": {
          "climate_variable": "SPEI12",
          "variable_description": "12개월 표준강수증발산지수",
          "current_value": -0.85,
          "unit": "index",
          "interpretation": "경미한 가뭄 (SPEI: -1.0 ~ -1.5는 중간 가뭄)",
          "trend": {
            "last_10_years_avg": -0.68,
            "last_20_years_avg": -0.52,
            "change_rate_10y": "+25.0%",
            "change_rate_20y": "+63.5%",
            "trend_direction": "악화"
          },
          "comparison": {
            "national_avg": -0.92,
            "sido_avg": -0.78,
            "percentile_national": "전국 평균보다 양호",
            "percentile_sido": "시도 평균보다 불량"
          },
          "score_calculation": {
            "base_score": 40,
            "trend_penalty": 5.3,
            "final_score": 45.3,
            "reasoning": "가뭄 악화 추세로 페널티 부과"
          }
        }
      },

      "E": {
        "score": 0.25,
        "explanation": {
          "exposure_factors": {
            "building_purpose": "업무시설",
            "water_dependency": "낮음 (산업 시설 아님)",
            "location_exposure": 0.25
          },
          "calculation": {
            "base_exposure": 0.3,
            "purpose_adjustment": -0.05,
            "final_exposure": 0.25,
            "reasoning": "업무시설로 물 의존도 낮음"
          }
        }
      },

      "V": {
        "score": 55,
        "level": "MEDIUM",
        "explanation": {
          "base_score": 50,
          "factors": [
            {
              "factor": "building_age",
              "value": 30,
              "penalty": 5,
              "reason": "노후 건물의 물 관리 시스템 효율 저하 (가뭄 시 +5점)"
            }
          ],
          "calculation": {
            "base": 50,
            "age_penalty": 5,
            "final_score": 55,
            "reasoning": "노후 배관 시스템으로 물 효율 저하"
          }
        }
      },

      "AAL": {
        "base_aal": 0.0285,
        "vulnerability_scale": 1.01,
        "final_aal": 0.0288,
        "insurance_rate": 0.0,
        "explanation": {
          "formula": "AAL = Σ(P[i] × DR[i]) × F_vuln × (1 - IR)",
          "base_aal_percentage": "2.85%",
          "final_aal_percentage": "2.88%",
          "vulnerability_scaling_formula": "F_vuln = 0.9 + (55/100) × 0.2 = 1.01",
          "expected_loss_krw": 4562064000,
          "expected_loss_display": "45억 6,206만원",
          "bin_details": [
            {
              "bin": "MINIMAL",
              "probability": 0.50,
              "damage_rate": 0.01,
              "contribution": 0.005,
              "contribution_percentage": "0.5%"
            },
            {
              "bin": "LOW",
              "probability": 0.30,
              "damage_rate": 0.05,
              "contribution": 0.015,
              "contribution_percentage": "1.5%"
            },
            {
              "bin": "MEDIUM",
              "probability": 0.15,
              "damage_rate": 0.12,
              "contribution": 0.018,
              "contribution_percentage": "1.8%"
            },
            {
              "bin": "HIGH",
              "probability": 0.05,
              "damage_rate": 0.25,
              "contribution": 0.0125,
              "contribution_percentage": "1.25%"
            }
          ]
        }
      }
    },

    "wildfire": {
      "H": {
        "score": 22.1,
        "level": "MINIMAL",
        "explanation": {
          "climate_variable": "FWI",
          "variable_description": "Fire Weather Index (산불 위험 지수)",
          "current_value": 15.8,
          "unit": "index",
          "interpretation": "낮음 (FWI < 20은 낮은 위험)",
          "trend": {
            "last_10_years_avg": 14.2,
            "last_20_years_avg": 13.5,
            "change_rate_10y": "+11.3%",
            "change_rate_20y": "+17.0%",
            "trend_direction": "상승"
          },
          "comparison": {
            "national_avg": 18.5,
            "sido_avg": 16.2,
            "percentile_national": "전국 평균보다 낮음",
            "percentile_sido": "시도 평균보다 약간 낮음"
          },
          "additional_factors": {
            "distance_to_forest": "3.2km",
            "urban_area": "도심 지역",
            "fire_protection": "소방서 1km 이내"
          },
          "score_calculation": {
            "base_score": 20,
            "trend_penalty": 2.1,
            "urban_discount": 0,
            "final_score": 22.1,
            "reasoning": "도심 지역으로 산불 위험 낮음"
          }
        }
      },

      "E": {
        "score": 0.15,
        "explanation": {
          "exposure_factors": {
            "location_exposure": 0.15,
            "distance_to_forest": "3.2km (산불 직접 영향 거리 밖)",
            "urban_protection": "도심 지역 (방화벽 역할)"
          },
          "calculation": {
            "base_exposure": 0.2,
            "urban_adjustment": -0.05,
            "final_exposure": 0.15,
            "reasoning": "도심 지역으로 산불 노출도 낮음"
          }
        }
      },

      "V": {
        "score": 48,
        "level": "LOW",
        "explanation": {
          "base_score": 50,
          "factors": [
            {
              "factor": "main_structure",
              "value": "철근콘크리트구조",
              "penalty": -2,
              "reason": "불연 재료 (RC 구조: -2점)"
            }
          ],
          "calculation": {
            "base": 50,
            "structure_benefit": -2,
            "final_score": 48,
            "reasoning": "RC 구조로 화재 취약성 낮음"
          }
        }
      },

      "AAL": {
        "base_aal": 0.0122,
        "vulnerability_scale": 0.996,
        "final_aal": 0.0122,
        "insurance_rate": 0.0,
        "explanation": {
          "formula": "AAL = Σ(P[i] × DR[i]) × F_vuln × (1 - IR)",
          "base_aal_percentage": "1.22%",
          "final_aal_percentage": "1.22%",
          "vulnerability_scaling_formula": "F_vuln = 0.9 + (48/100) × 0.2 = 0.996",
          "expected_loss_krw": 1932541000,
          "expected_loss_display": "19억 3,254만원",
          "bin_details": [
            {
              "bin": "MINIMAL",
              "probability": 0.70,
              "damage_rate": 0.005,
              "contribution": 0.0035,
              "contribution_percentage": "0.35%"
            },
            {
              "bin": "LOW",
              "probability": 0.20,
              "damage_rate": 0.03,
              "contribution": 0.006,
              "contribution_percentage": "0.6%"
            },
            {
              "bin": "MEDIUM",
              "probability": 0.08,
              "damage_rate": 0.10,
              "contribution": 0.008,
              "contribution_percentage": "0.8%"
            },
            {
              "bin": "HIGH",
              "probability": 0.02,
              "damage_rate": 0.30,
              "contribution": 0.006,
              "contribution_percentage": "0.6%"
            }
          ]
        }
      }
    },

    "water_stress": {
      "H": {
        "score": 38.7,
        "level": "LOW",
        "explanation": {
          "climate_variable": "WSI",
          "variable_description": "Water Stress Index (물 부족 지수)",
          "current_value": 0.42,
          "unit": "index (0-1)",
          "interpretation": "중간 수준 물 스트레스 (0.4-0.6)",
          "trend": {
            "last_10_years_avg": 0.38,
            "last_20_years_avg": 0.35,
            "change_rate_10y": "+10.5%",
            "change_rate_20y": "+20.0%",
            "trend_direction": "악화"
          },
          "comparison": {
            "national_avg": 0.45,
            "sido_avg": 0.40,
            "percentile_national": "전국 평균보다 양호",
            "percentile_sido": "시도 평균보다 불량"
          },
          "score_calculation": {
            "base_score": 35,
            "trend_penalty": 3.7,
            "final_score": 38.7,
            "reasoning": "물 스트레스 악화 추세"
          }
        }
      },

      "E": {
        "score": 0.30,
        "explanation": {
          "exposure_factors": {
            "building_purpose": "업무시설",
            "water_dependency": "보통 (냉각수, 생활용수 필요)",
            "location_exposure": 0.30
          },
          "calculation": {
            "base_exposure": 0.30,
            "final_exposure": 0.30,
            "reasoning": "업무시설로 물 의존도 보통"
          }
        }
      },

      "V": {
        "score": 58,
        "level": "MEDIUM",
        "explanation": {
          "base_score": 50,
          "factors": [
            {
              "factor": "building_age",
              "value": 30,
              "penalty": 8,
              "reason": "노후 배관 시스템 (물 효율 저하, +8점)"
            }
          ],
          "calculation": {
            "base": 50,
            "age_penalty": 8,
            "final_score": 58,
            "reasoning": "노후 배관으로 물 사용 효율 저하"
          }
        }
      },

      "AAL": {
        "base_aal": 0.0327,
        "vulnerability_scale": 1.016,
        "final_aal": 0.0332,
        "insurance_rate": 0.0,
        "explanation": {
          "formula": "AAL = Σ(P[i] × DR[i]) × F_vuln × (1 - IR)",
          "base_aal_percentage": "3.27%",
          "final_aal_percentage": "3.32%",
          "vulnerability_scaling_formula": "F_vuln = 0.9 + (58/100) × 0.2 = 1.016",
          "expected_loss_krw": 5259046000,
          "expected_loss_display": "52억 5,905만원"
        }
      }
    },

    "sea_level_rise": {
      "H": {
        "score": 8.5,
        "level": "MINIMAL",
        "explanation": {
          "climate_variable": "ZOS",
          "variable_description": "Sea Surface Height (해수면 높이)",
          "current_value": 0.15,
          "unit": "m",
          "interpretation": "낮은 해수면 상승 (< 0.3m)",
          "trend": {
            "last_10_years_avg": 0.12,
            "last_20_years_avg": 0.09,
            "change_rate_10y": "+25.0%",
            "change_rate_20y": "+66.7%",
            "trend_direction": "상승"
          },
          "comparison": {
            "national_avg": 0.18,
            "coastal_avg": 0.22,
            "percentile_national": "전국 평균보다 낮음"
          },
          "additional_factors": {
            "distance_to_coast": "25km",
            "elevation": "해발 15m",
            "coastal_flood_risk": "매우 낮음"
          },
          "score_calculation": {
            "base_score": 5,
            "trend_penalty": 3.5,
            "distance_discount": 0,
            "final_score": 8.5,
            "reasoning": "내륙 지역으로 해수면 상승 영향 미미"
          }
        }
      },

      "E": {
        "score": 0.05,
        "explanation": {
          "exposure_factors": {
            "location_exposure": 0.05,
            "distance_to_coast": "25km (해수면 상승 직접 영향 없음)",
            "elevation": "해발 15m (안전)"
          },
          "calculation": {
            "base_exposure": 0.05,
            "final_exposure": 0.05,
            "reasoning": "내륙 고지대로 해수면 상승 영향 없음"
          }
        }
      },

      "V": {
        "score": 50,
        "level": "MEDIUM",
        "explanation": {
          "base_score": 50,
          "factors": [],
          "calculation": {
            "base": 50,
            "final_score": 50,
            "reasoning": "해수면 상승에 대한 특별한 취약 요인 없음"
          }
        }
      },

      "AAL": {
        "base_aal": 0.003,
        "vulnerability_scale": 1.0,
        "final_aal": 0.003,
        "insurance_rate": 0.0,
        "explanation": {
          "formula": "AAL = Σ(P[i] × DR[i]) × F_vuln × (1 - IR)",
          "base_aal_percentage": "0.3%",
          "final_aal_percentage": "0.3%",
          "vulnerability_scaling_formula": "F_vuln = 0.9 + (50/100) × 0.2 = 1.0",
          "expected_loss_krw": 475215000,
          "expected_loss_display": "4억 7,522만원"
        }
      }
    },

    "extreme_cold": {
      "H": {
        "score": 52.8,
        "level": "MEDIUM",
        "explanation": {
          "climate_variable": "CSDI",
          "variable_description": "Cold Spell Duration Index (연속 한파 일수)",
          "current_value": 18.5,
          "unit": "days",
          "trend": {
            "last_10_years_avg": 15.8,
            "last_20_years_avg": 19.2,
            "change_rate_10y": "+17.1%",
            "change_rate_20y": "-3.6%",
            "trend_direction": "최근 10년 증가, 20년 기준 감소"
          },
          "comparison": {
            "national_avg": 16.2,
            "sido_avg": 17.8,
            "percentile_national": "전국 평균보다 높음",
            "percentile_sido": "시도 평균보다 약간 높음"
          },
          "score_calculation": {
            "base_score": 50,
            "trend_penalty": 2.8,
            "final_score": 52.8,
            "reasoning": "최근 한파 일수 증가 추세"
          }
        }
      },

      "E": {
        "score": 0.78,
        "explanation": {
          "exposure_factors": {
            "location_exposure": 0.75,
            "building_size_factor": 1.04,
            "heating_system_dependency": "고층 건물 (난방 의존도 높음)"
          },
          "calculation": {
            "base_exposure": 0.75,
            "size_adjustment": 0.03,
            "final_exposure": 0.78,
            "reasoning": "대형 업무시설로 난방 부담 큼"
          }
        }
      },

      "V": {
        "score": 65,
        "level": "MEDIUM",
        "explanation": {
          "base_score": 50,
          "factors": [
            {
              "factor": "building_age",
              "value": 30,
              "penalty": 15,
              "reason": "노후 난방 시스템 및 단열 성능 저하 (+15점)"
            }
          ],
          "calculation": {
            "base": 50,
            "age_penalty": 15,
            "final_score": 65,
            "reasoning": "노후 건물의 단열 성능 저하"
          }
        }
      },

      "AAL": {
        "base_aal": 0.0658,
        "vulnerability_scale": 1.03,
        "final_aal": 0.0678,
        "insurance_rate": 0.0,
        "explanation": {
          "formula": "AAL = Σ(P[i] × DR[i]) × F_vuln × (1 - IR)",
          "base_aal_percentage": "6.58%",
          "final_aal_percentage": "6.78%",
          "vulnerability_scaling_formula": "F_vuln = 0.9 + (65/100) × 0.2 = 1.03",
          "expected_loss_krw": 10739859000,
          "expected_loss_display": "107억 3,986만원"
        }
      }
    },

    "urban_flood": {
      "H": {
        "score": 72.3,
        "level": "HIGH",
        "explanation": {
          "climate_variable": "RX1DAY",
          "variable_description": "1일 최대 강수량",
          "current_value": 185.2,
          "unit": "mm",
          "trend": {
            "last_10_years_avg": 168.5,
            "last_20_years_avg": 155.8,
            "change_rate_10y": "+9.9%",
            "change_rate_20y": "+18.9%",
            "trend_direction": "상승"
          },
          "comparison": {
            "national_avg": 152.3,
            "sido_avg": 172.6,
            "percentile_national": "상위 10%",
            "percentile_sido": "상위 25%"
          },
          "additional_factors": {
            "drainage_capacity": "시간당 50mm (초과 가능성 높음)",
            "impervious_surface_ratio": "85% (도심 밀집 지역)",
            "flood_history": "최근 10년간 침수 이력 3회"
          },
          "score_calculation": {
            "base_score": 65,
            "trend_penalty": 4.3,
            "drainage_penalty": 3,
            "final_score": 72.3,
            "reasoning": "배수 용량 초과 가능성 및 도심 불투수면 비율 높음"
          }
        }
      },

      "E": {
        "score": 0.88,
        "explanation": {
          "exposure_factors": {
            "location_exposure": 0.85,
            "building_size_factor": 1.04,
            "urban_flood_zone": "도심 저지대",
            "ground_floor_exposure": "1층 침수 가능 면적 1,320㎡"
          },
          "calculation": {
            "base_exposure": 0.85,
            "size_adjustment": 0.03,
            "final_exposure": 0.88,
            "reasoning": "도심 저지대 대형 건물로 노출도 높음"
          }
        }
      },

      "V": {
        "score": 70,
        "level": "HIGH",
        "explanation": {
          "base_score": 50,
          "factors": [
            {
              "factor": "building_age",
              "value": 30,
              "penalty": 16,
              "reason": "노후 배수 시스템 (+16점)"
            },
            {
              "factor": "basement_floors",
              "value": 3,
              "penalty": 4,
              "reason": "지하 3층 보유 (침수 피해 증가, +4점)"
            }
          ],
          "calculation": {
            "base": 50,
            "age_penalty": 16,
            "basement_penalty": 4,
            "final_score": 70,
            "reasoning": "노후 배수 시스템과 지하층으로 침수 취약"
          }
        }
      },

      "AAL": {
        "base_aal": 0.0856,
        "vulnerability_scale": 1.04,
        "final_aal": 0.0890,
        "insurance_rate": 0.0,
        "explanation": {
          "formula": "AAL = Σ(P[i] × DR[i]) × F_vuln × (1 - IR)",
          "base_aal_percentage": "8.56%",
          "final_aal_percentage": "8.90%",
          "vulnerability_scaling_formula": "F_vuln = 0.9 + (70/100) × 0.2 = 1.04",
          "expected_loss_krw": 14098045000,
          "expected_loss_display": "140억 9,804만원"
        }
      }
    },

    "typhoon": {
      "H": {
        "score": 48.6,
        "level": "LOW",
        "explanation": {
          "climate_variable": "S_tc",
          "variable_description": "Tropical Cyclone Intensity (태풍 강도)",
          "current_value": 32.5,
          "unit": "m/s",
          "interpretation": "중간 강도 태풍 (25-32 m/s: 중형 태풍)",
          "trend": {
            "last_10_years_avg": 30.2,
            "last_20_years_avg": 28.8,
            "change_rate_10y": "+7.6%",
            "change_rate_20y": "+12.8%",
            "trend_direction": "강도 증가"
          },
          "comparison": {
            "national_avg": 28.5,
            "coastal_avg": 35.2,
            "percentile_national": "전국 평균보다 높음",
            "percentile_coastal": "해안 지역보다 낮음"
          },
          "additional_factors": {
            "distance_to_coast": "25km",
            "typhoon_path_frequency": "연평균 1.2회",
            "wind_exposure": "고층 건물 (풍압 증가)"
          },
          "score_calculation": {
            "base_score": 45,
            "trend_penalty": 3.6,
            "inland_discount": 0,
            "final_score": 48.6,
            "reasoning": "태풍 강도 증가 추세"
          }
        }
      },

      "E": {
        "score": 0.72,
        "explanation": {
          "exposure_factors": {
            "location_exposure": 0.70,
            "building_size_factor": 1.03,
            "building_height": "12층 (강풍 노출)",
            "facade_area": "외벽 및 창문 면적 큼"
          },
          "calculation": {
            "base_exposure": 0.70,
            "height_adjustment": 0.02,
            "final_exposure": 0.72,
            "reasoning": "고층 건물로 강풍 노출 증가"
          }
        }
      },

      "V": {
        "score": 62,
        "level": "MEDIUM",
        "explanation": {
          "base_score": 50,
          "factors": [
            {
              "factor": "building_age",
              "value": 30,
              "penalty": 12,
              "reason": "노후 건물의 구조적 강도 저하 (+12점)"
            },
            {
              "factor": "floors_above",
              "value": 12,
              "penalty": 0,
              "reason": "12층 (풍압 증가 요인, 페널티 없음)"
            }
          ],
          "calculation": {
            "base": 50,
            "age_penalty": 12,
            "final_score": 62,
            "reasoning": "노후 건물의 구조적 강도 저하"
          }
        }
      },

      "AAL": {
        "base_aal": 0.0548,
        "vulnerability_scale": 1.024,
        "final_aal": 0.0561,
        "insurance_rate": 0.0,
        "explanation": {
          "formula": "AAL = Σ(P[i] × DR[i]) × F_vuln × (1 - IR)",
          "base_aal_percentage": "5.48%",
          "final_aal_percentage": "5.61%",
          "vulnerability_scaling_formula": "F_vuln = 0.9 + (62/100) × 0.2 = 1.024",
          "expected_loss_krw": 8886520500,
          "expected_loss_display": "88억 8,652만원"
        }
      }
    }
  },

  "summary": {
    "total_base_aal": 0.4633,
    "total_final_aal": 0.4761,
    "total_final_aal_percentage": "47.61%",
    "total_expected_loss_krw": 75422867000,
    "total_expected_loss_display": "754억 2,287만원",
    "risk_ranking": [
      {
        "risk_type": "river_flood",
        "risk_name": "하천 홍수",
        "final_aal": 0.0983,
        "aal_percentage": "9.83%",
        "expected_loss_krw": 15571131500,
        "expected_loss_display": "155억 7,113만원",
        "contribution_pct": 20.6
      },
      {
        "risk_type": "urban_flood",
        "risk_name": "도시 홍수",
        "final_aal": 0.0890,
        "aal_percentage": "8.90%",
        "expected_loss_krw": 14098045000,
        "expected_loss_display": "140억 9,804만원",
        "contribution_pct": 18.7
      },
      {
        "risk_type": "extreme_heat",
        "risk_name": "극한 고온",
        "final_aal": 0.0814,
        "aal_percentage": "8.14%",
        "expected_loss_krw": 12894487000,
        "expected_loss_display": "128억 9,449만원",
        "contribution_pct": 17.1
      },
      {
        "risk_type": "extreme_cold",
        "risk_name": "극한 한파",
        "final_aal": 0.0678,
        "aal_percentage": "6.78%",
        "expected_loss_krw": 10739859000,
        "expected_loss_display": "107억 3,986만원",
        "contribution_pct": 14.2
      },
      {
        "risk_type": "typhoon",
        "risk_name": "태풍",
        "final_aal": 0.0561,
        "aal_percentage": "5.61%",
        "expected_loss_krw": 8886520500,
        "expected_loss_display": "88억 8,652만원",
        "contribution_pct": 11.8
      },
      {
        "risk_type": "water_stress",
        "risk_name": "물 부족",
        "final_aal": 0.0332,
        "aal_percentage": "3.32%",
        "expected_loss_krw": 5259046000,
        "expected_loss_display": "52억 5,905만원",
        "contribution_pct": 7.0
      },
      {
        "risk_type": "drought",
        "risk_name": "가뭄",
        "final_aal": 0.0288,
        "aal_percentage": "2.88%",
        "expected_loss_krw": 4562064000,
        "expected_loss_display": "45억 6,206만원",
        "contribution_pct": 6.0
      },
      {
        "risk_type": "wildfire",
        "risk_name": "산불",
        "final_aal": 0.0122,
        "aal_percentage": "1.22%",
        "expected_loss_krw": 1932541000,
        "expected_loss_display": "19억 3,254만원",
        "contribution_pct": 2.6
      },
      {
        "risk_type": "sea_level_rise",
        "risk_name": "해수면 상승",
        "final_aal": 0.003,
        "aal_percentage": "0.3%",
        "expected_loss_krw": 475215000,
        "expected_loss_display": "4억 7,522만원",
        "contribution_pct": 0.6
      }
    ],
    "top_3_risks": [
      "river_flood",
      "urban_flood",
      "extreme_heat"
    ],
    "critical_risks": ["river_flood"],
    "high_risks": ["urban_flood", "extreme_heat"]
  },

  "metadata": {
    "calculation_timestamp": "2025-12-02T14:35:22Z",
    "data_source": "skala_datawarehouse",
    "model_version": "1.0.0",
    "climate_scenario": "SSP2-4.5",
    "time_horizon": "2050"
  }
}
```

---

## 데이터 활용 방법

### 1. H (Hazard) 설명 데이터 활용

LLM은 `H.explanation` 섹션을 사용하여 다음과 같은 문장을 생성할 수 있습니다:

```
해당 지역의 극한 고온 위험도는 78.5점(HIGH)으로 평가되었습니다.
이는 연속 폭염 일수(WSDI)가 37.8일로, 전국 평균 25.3일 대비 49% 높기 때문입니다.
특히 최근 10년간 17.8% 증가하는 추세를 보이며, 전국 상위 8%에 해당하는 극단적 수치입니다.
```

**데이터 출처**:
- `H.explanation.current_value`: 37.8
- `H.explanation.comparison.national_avg`: 25.3
- `H.explanation.trend.change_rate_10y`: +17.8%
- `H.explanation.comparison.percentile_national`: 상위 8%

### 2. E (Exposure) 설명 데이터 활용

```
해당 건물의 자산 가치는 약 1,584억원으로 평가되며,
하천 홍수에 대한 노출도는 0.92점으로 매우 높습니다.
이는 한강으로부터 500m 이내에 위치하고 있으며,
1층 면적 1,320㎡가 침수 가능 범위에 포함되기 때문입니다.
```

**데이터 출처**:
- `building.asset_value_display`: 1,584억원
- `E.score`: 0.92
- `E.explanation.exposure_factors.proximity_to_river`: 500m 이내
- `E.explanation.exposure_factors.ground_floor_exposure`: 1층 면적 1,320㎡ 침수 가능

### 3. V (Vulnerability) 설명 데이터 활용

```
해당 건물의 취약도는 72점(HIGH)으로 평가되었습니다.
주요 원인은 준공 후 30년이 경과하여 노후도 페널티 18점이 부과되었고,
지하 3층 보유로 인해 침수 시 피해가 증가하여 추가 4점이 부과되었습니다.
```

**데이터 출처**:
- `V.score`: 72
- `V.level`: HIGH
- `V.explanation.factors[0].penalty`: 18 (building_age)
- `V.explanation.factors[1].penalty`: 4 (basement_floors)

### 4. AAL 설명 데이터 활용

```
하천 홍수로 인한 연평균 예상 손실률(AAL)은 9.83%로 산정되었습니다.
이는 자산 가치 1,584억원 기준 약 155억 7,113만원의 연간 손실이 예상됩니다.

AAL 계산은 다음과 같이 이루어졌습니다:
1. 확률 가중 손상률(Base AAL) = 9.42%
   - CRITICAL 수준 홍수(발생 확률 8%, 피해율 70%): 5.6% 기여
   - HIGH 수준 홍수(발생 확률 15%, 피해율 40%): 6.0% 기여
2. 취약성 스케일 계수(F_vuln) = 1.044 (취약도 72점 기반)
3. 최종 AAL = 9.42% × 1.044 = 9.83%
```

**데이터 출처**:
- `AAL.final_aal`: 0.0983
- `AAL.explanation.final_aal_percentage`: 9.83%
- `AAL.explanation.expected_loss_display`: 155억 7,113만원
- `AAL.explanation.bin_details[4]`: CRITICAL bin
- `AAL.explanation.bin_details[3]`: HIGH bin
- `AAL.explanation.calculation_steps`: 계산 단계

### 5. 시계열 추세 분석

```
해당 지역의 극한 고온은 악화되는 추세를 보입니다.
최근 10년 평균(32.1일) 대비 17.8% 증가했으며,
20년 평균(28.5일) 대비로는 32.6%나 급증했습니다.
이러한 가속화 추세는 향후에도 지속될 것으로 예상됩니다.
```

**데이터 출처**:
- `H.explanation.trend.last_10_years_avg`: 32.1
- `H.explanation.trend.last_20_years_avg`: 28.5
- `H.explanation.trend.change_rate_10y`: +17.8%
- `H.explanation.trend.change_rate_20y`: +32.6%

### 6. 상대적 비교 분석

```
이 지역의 5일 최대 강수량(385.6mm)은 전국 평균(295.3mm)보다 30.6% 높으며,
전국 상위 3%에 해당하는 극단적 수치입니다.
서울시 평균(358.7mm)과 비교해도 7.5% 높은 수준으로,
동일 시도 내에서도 높은 위험 지역에 속합니다.
```

**데이터 출처**:
- `H.explanation.current_value`: 385.6
- `H.explanation.comparison.national_avg`: 295.3
- `H.explanation.comparison.percentile_national`: 상위 3%
- `H.explanation.comparison.sido_avg`: 358.7

### 7. AAL 계산 과정 설명

```
AAL 계산은 다음 공식으로 이루어집니다:

AAL = Σ(P[i] × DR[i]) × F_vuln × (1 - IR)

여기서:
- Σ(P[i] × DR[i]): 확률 가중 손상률 (Base AAL)
- F_vuln: 취약성 스케일 계수 (0.9 + V/100 × 0.2)
- IR: 보험 보전율 (현재 0.0)

예시 (극한 고온):
1. Base AAL = 0.35×0.02 + 0.28×0.08 + 0.20×0.18 + 0.12×0.35 + 0.05×0.60
            = 0.007 + 0.0224 + 0.036 + 0.042 + 0.03
            = 0.1374 = 13.74%

잘못된 계산이었습니다. 수정:
1. Base AAL = 7.85%
2. F_vuln = 0.9 + (68/100) × 0.2 = 1.036
3. Final AAL = 7.85% × 1.036 × (1 - 0.0) = 8.14%
4. Expected Loss = 8.14% × 1,584억원 = 약 129억원
```

**데이터 출처**:
- `AAL.explanation.calculation_steps`: 계산 단계 배열
- `AAL.explanation.bin_details`: bin별 확률과 손상률

---

## 데이터 수집 방법

### 데이터베이스 테이블

이 JSON 데이터는 다음 5개 테이블에서 수집됩니다:

1. **`probability_results`**: P(H) 확률 및 bin 데이터
2. **`hazard_results`**: H 점수, 기후 변수 원본 값, 추세 분석
3. **`vulnerability_results`**: V 점수, 건물 특성, 페널티 상세
4. **`exposure_results`**: E 점수, 자산 가치, 노출 요인
5. **`aal_scaled_results`**: AAL 최종 값, 계산 컴포넌트

### Python 코드 예시

```python
from modelops.database.connection import DatabaseConnection
from typing import Dict, Any

def fetch_llm_input_data(latitude: float, longitude: float, building_id: str) -> Dict[str, Any]:
    """LLM 입력용 데이터 수집"""

    conn = DatabaseConnection.get_connection()
    cursor = conn.cursor(dictionary=True)

    # 1. 건물 정보
    cursor.execute("""
        SELECT
            building_id,
            main_purpose,
            main_structure,
            total_area,
            construction_year,
            YEAR(CURDATE()) - construction_year AS building_age,
            floors_above,
            floors_below
        FROM building_info
        WHERE building_id = %s
    """, (building_id,))
    building_info = cursor.fetchone()

    # 2. Hazard 데이터 (H + 기후 변수 상세)
    cursor.execute("""
        SELECT
            risk_type,
            hazard_score,
            hazard_level,
            climate_variable,
            current_value,
            last_10y_avg,
            last_20y_avg,
            national_avg,
            sido_avg,
            percentile_national,
            Q80, Q90, Q95, Q99,
            additional_factors,
            score_calculation
        FROM hazard_results
        WHERE latitude = %s AND longitude = %s
    """, (latitude, longitude))
    hazard_data = {row['risk_type']: row for row in cursor.fetchall()}

    # 3. Exposure 데이터 (E + 자산 가치 상세)
    cursor.execute("""
        SELECT
            risk_type,
            exposure_score,
            asset_value,
            exposure_factors,
            calculation_details
        FROM exposure_results
        WHERE latitude = %s AND longitude = %s AND building_id = %s
    """, (latitude, longitude, building_id))
    exposure_data = {row['risk_type']: row for row in cursor.fetchall()}

    # 4. Vulnerability 데이터 (V + 페널티 상세)
    cursor.execute("""
        SELECT
            risk_type,
            vulnerability_score,
            vulnerability_level,
            base_score,
            factors,
            calculation_details
        FROM vulnerability_results
        WHERE building_id = %s
    """, (building_id,))
    vulnerability_data = {row['risk_type']: row for row in cursor.fetchall()}

    # 5. Probability 데이터 (bin 상세)
    cursor.execute("""
        SELECT
            risk_type,
            probability AS base_aal,
            bin_data
        FROM probability_results
        WHERE latitude = %s AND longitude = %s
    """, (latitude, longitude))
    probability_data = {row['risk_type']: row for row in cursor.fetchall()}

    # 6. AAL Scaled 데이터
    cursor.execute("""
        SELECT
            risk_type,
            base_aal,
            vulnerability_scale,
            final_aal,
            insurance_rate,
            expected_loss
        FROM aal_scaled_results
        WHERE latitude = %s AND longitude = %s AND building_id = %s
    """, (latitude, longitude, building_id))
    aal_data = {row['risk_type']: row for row in cursor.fetchall()}

    # 데이터 병합 및 JSON 생성
    return merge_to_llm_format(
        building_info,
        hazard_data,
        exposure_data,
        vulnerability_data,
        probability_data,
        aal_data
    )


def merge_to_llm_format(
    building_info: Dict,
    hazard_data: Dict,
    exposure_data: Dict,
    vulnerability_data: Dict,
    probability_data: Dict,
    aal_data: Dict
) -> Dict[str, Any]:
    """데이터를 LLM 입력 형식으로 병합"""

    result = {
        "building": building_info,
        "risks": {},
        "summary": {}
    }

    # 9개 리스크별 데이터 병합
    risk_types = [
        "extreme_heat", "extreme_cold", "drought", "wildfire",
        "water_stress", "sea_level_rise", "river_flood",
        "urban_flood", "typhoon"
    ]

    for risk_type in risk_types:
        result["risks"][risk_type] = {
            "H": {
                "score": hazard_data[risk_type]["hazard_score"],
                "level": hazard_data[risk_type]["hazard_level"],
                "explanation": hazard_data[risk_type]
            },
            "E": {
                "score": exposure_data[risk_type]["exposure_score"],
                "explanation": exposure_data[risk_type]
            },
            "V": {
                "score": vulnerability_data[risk_type]["vulnerability_score"],
                "level": vulnerability_data[risk_type]["vulnerability_level"],
                "explanation": vulnerability_data[risk_type]
            },
            "AAL": {
                "base_aal": aal_data[risk_type]["base_aal"],
                "vulnerability_scale": aal_data[risk_type]["vulnerability_scale"],
                "final_aal": aal_data[risk_type]["final_aal"],
                "insurance_rate": aal_data[risk_type]["insurance_rate"],
                "explanation": {
                    "base_aal_percentage": f"{aal_data[risk_type]['base_aal']*100:.2f}%",
                    "final_aal_percentage": f"{aal_data[risk_type]['final_aal']*100:.2f}%",
                    "expected_loss_krw": aal_data[risk_type]["expected_loss"],
                    "bin_details": probability_data[risk_type]["bin_data"]
                }
            }
        }

    # Summary 계산
    total_final_aal = sum(aal_data[rt]["final_aal"] for rt in risk_types)
    total_expected_loss = sum(aal_data[rt]["expected_loss"] for rt in risk_types)

    result["summary"] = {
        "total_final_aal": total_final_aal,
        "total_final_aal_percentage": f"{total_final_aal*100:.2f}%",
        "total_expected_loss_krw": total_expected_loss,
        "risk_ranking": sorted(
            [
                {
                    "risk_type": rt,
                    "final_aal": aal_data[rt]["final_aal"],
                    "expected_loss_krw": aal_data[rt]["expected_loss"]
                }
                for rt in risk_types
            ],
            key=lambda x: x["final_aal"],
            reverse=True
        )
    }

    return result
```

---

## LLM 프롬프트 예시

### 프롬프트

```
당신은 기후 리스크 분석 전문가입니다.
아래 JSON 데이터를 기반으로 이 건물의 기후 리스크를 분석하고,
근거 있는 인사이트와 실행 가능한 권고사항을 제시하세요.

**요구사항**:
1. 모든 주장은 데이터에 근거해야 합니다.
2. 구체적인 수치를 포함하세요 (예: "WSDI 37.8일, 전국 평균 25.3일 대비 49% 높음").
3. 추세 분석을 포함하세요 (예: "최근 10년간 17.8% 증가").
4. 상대적 비교를 포함하세요 (예: "전국 상위 8%").
5. AAL 계산 과정을 설명하세요.
6. 실행 가능한 권고사항을 제시하세요.

**AAL 단위 참고**:
- AAL 값은 백분율(%)로 제공됩니다 (예: 0.0814 = 8.14%)
- 필요 시 자산 가치를 곱해 원화로 환산하세요 (예: 8.14% × 1,584억원 = 약 129억원)
- Expected Loss 값은 이미 원화로 제공됩니다.

**데이터**:
{JSON 데이터 삽입}
```

### LLM 응답 예시

```markdown
# 기후 리스크 분석 리포트

## 1. 종합 평가

해당 건물(서울시 중구 소재, 1995년 준공, 자산 가치 1,584억원)의 연평균 예상 손실률(AAL)은 **47.61%**로 산정되었습니다.
이는 자산 가치 기준 연간 약 **754억 2,287만원**의 손실이 예상되는 수준입니다.

주요 리스크는 **하천 홍수(AAL 9.83%, 155억원)**, **도시 홍수(AAL 8.90%, 140억원)**, **극한 고온(AAL 8.14%, 129억원)** 순입니다.

## 2. 주요 리스크 상세 분석

### 2.1 하천 홍수 (AAL: 9.83%, 연간 155억 7,113만원)

**위험도 평가**: H=85.2 (CRITICAL)

해당 지역의 5일 최대 강수량(RX5DAY)은 **385.6mm**로, 전국 평균(295.3mm) 대비 **30.6% 높으며**,
전국 상위 **3%**에 해당하는 극단적 수치입니다. 최근 10년간 **12.5% 증가**하는 추세를 보이고 있습니다.

**노출도**: E=0.92 (매우 높음)

- 한강으로부터 **500m 이내** 위치
- 1층 면적 **1,320㎡**가 침수 가능 범위
- 자산 가치: **1,584억원**
- 해발 15m 저지대, 최근 10년간 침수 이력 2회

**취약도**: V=72 (HIGH)

- 준공 후 **30년 경과** → 노후도 페널티 **18점**
- 지하 **3층 보유** → 침수 피해 증가 페널티 **4점**

**AAL 계산 과정**:
```
1. Base AAL (확률 가중 손상률) = 9.42%
   - CRITICAL 수준 홍수 (확률 8%, 피해율 70%): 5.6% 기여
   - HIGH 수준 홍수 (확률 15%, 피해율 40%): 6.0% 기여
   - MEDIUM 수준 홍수 (확률 22%, 피해율 22%): 4.84% 기여

2. 취약성 스케일 계수 (F_vuln) = 0.9 + (72/100) × 0.2 = 1.044

3. Final AAL = 9.42% × 1.044 × (1 - 0.0) = 9.83%

4. Expected Loss = 9.83% × 1,584억원 = 155억 7,113만원
```

**권고사항**:
1. **긴급**: 1층 및 지하층 방수 시설 강화
2. 침수 방지를 위한 차수판 설치 검토
3. 지하 주요 설비 이전 또는 방수 처리
4. 배수 펌프 용량 증설

### 2.2 극한 고온 (AAL: 8.14%, 연간 128억 9,449만원)

**위험도 평가**: H=78.5 (HIGH)

연속 폭염 일수(WSDI)가 **37.8일**로, 전국 평균(25.3일) 대비 **49% 높습니다**.
최근 10년간 **17.8% 증가**하며, 전국 상위 **8%**에 해당하는 극단적 수치입니다.

**AAL 계산 과정**:
```
1. Base AAL = 7.85%
2. F_vuln = 0.9 + (68/100) × 0.2 = 1.036
3. Final AAL = 7.85% × 1.036 = 8.14%
4. Expected Loss = 8.14% × 1,584억원 = 128억 9,449만원
```

**권고사항**:
1. 냉방 시스템 효율 개선 및 용량 증설
2. 단열 성능 강화 (외벽, 지붕)
3. 폭염 대응 매뉴얼 수립
4. 재생 에너지 도입 검토 (냉방 비용 절감)

## 3. 종합 권고사항

### 즉시 조치 필요 (CRITICAL)
- 하천 홍수 대비 방수 시설 강화
- 지하층 침수 대응 시스템 구축

### 단기 조치 (6개월 이내)
- 도시 홍수 대비 배수 시스템 점검
- 극한 고온 대비 냉방 시스템 개선
- 극한 한파 대비 단열 성능 개선

### 장기 조치 (1년 이상)
- 건물 노후화 대응 종합 보수 계획 수립
- 기후 변화 적응 투자 계획 수립 (총 AAL 754억원 → 목표 500억원 이하)
- 보험 가입 검토 (현재 보험 보전율 0%)

## 4. 투자 대비 효과 분석

### 시나리오 1: 방수 시설 강화 (투자 비용: 50억원)
- 하천 홍수 AAL: 9.83% → 7.0% (2.83%p 감소)
- 도시 홍수 AAL: 8.90% → 6.5% (2.4%p 감소)
- **연간 AAL 절감**: 5.23%p × 1,584억원 = **약 83억원/년**
- **투자 회수 기간**: 약 0.6년 (7개월)

### 시나리오 2: 종합 개선 (투자 비용: 150억원)
- 총 AAL: 47.61% → 35.0% (12.61%p 감소)
- **연간 AAL 절감**: 12.61%p × 1,584억원 = **약 200억원/년**
- **투자 회수 기간**: 약 0.75년 (9개월)

## 5. 결론

해당 건물은 **하천 홍수와 도시 홍수**에 대한 대응이 가장 시급합니다.
방수 시설 강화만으로도 연간 약 83억원의 손실을 줄일 수 있으며,
투자 회수 기간이 7개월에 불과하여 즉시 시행을 권고합니다.

장기적으로는 기후 변화에 대응한 종합 개선 계획을 수립하여
총 AAL을 현재 754억원에서 550억원 이하로 낮추는 것을 목표로 설정하시기 바랍니다.
```

---

## 주의사항

1. **AAL 단위**: AAL은 백분율(0~1 범위의 소수)로 제공됩니다. LLM이 원화로 환산 시 자산가치를 곱해야 합니다.
2. **데이터 정합성**: 모든 explanation 데이터는 실제 계산 결과와 일치해야 합니다.
3. **단위 표시**: 수치에는 항상 단위를 명시하세요 (mm, days, index, % 등).
4. **NULL 처리**: 데이터가 없는 경우 `null` 또는 빈 배열 `[]`을 사용하세요.
5. **일관성**: 모든 리스크에 대해 동일한 데이터 구조를 유지하세요.
6. **버전 관리**: `metadata.model_version`으로 계산 모델 버전을 추적하세요.

---

## 데이터 갱신 주기

- **H (Hazard)**: 기후 데이터 업데이트 시 (일반적으로 월 1회)
- **E (Exposure)**: 자산 가치 변동 시 (년 1회 또는 요청 시)
- **V (Vulnerability)**: 건물 정보 변경 시
- **AAL**: H, E, V 중 하나라도 변경 시 재계산

---

## 문서 버전

- **Version**: 1.0.0
- **Last Updated**: 2025-12-02
- **Author**: ModelOps Team
