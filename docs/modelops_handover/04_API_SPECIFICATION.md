# ModelOps 이관 문서 - 04. API 명세

**문서 버전**: 1.0
**작성일**: 2025-12-01

---

## 1. API 개요

### 1.1 Base URL
```
Production: https://api.modelops.skax.com/v1
Development: http://localhost:8001/v1
```

### 1.2 인증
```http
Authorization: Bearer {API_KEY}
```

### 1.3 Rate Limiting
- **분당 최대 요청**: 100회
- **동시 요청**: 10개
- **응답 헤더**:
  - `X-RateLimit-Limit`: 100
  - `X-RateLimit-Remaining`: 95
  - `X-RateLimit-Reset`: 1638360000

---

## 2. Vulnerability 계산 API

### 2.1 요청

**Endpoint**: `POST /api/v1/calculate/vulnerability`

**Request Body**:
```json
{
  "site_id": "uuid-12345",
  "building_info": {
    "building_age": 25,
    "structure": "철근콘크리트",
    "main_purpose": "업무시설",
    "floors_below": 2,
    "floors_above": 10,
    "has_piloti": false,
    "has_seismic_design": true,
    "fire_access": true
  },
  "location": {
    "latitude": 37.5665,
    "longitude": 126.9780,
    "elevation": 38.5
  },
  "infrastructure": {
    "water_supply_available": true
  }
}
```

### 2.2 응답 (200 OK)

**동기 처리 완료**:
```json
{
  "request_id": "vuln-req-12345",
  "status": "completed",
  "site_id": "uuid-12345",
  "building_hash": "sha256-abcd1234...",
  "results": {
    "extreme_heat": {
      "score": 65.0,
      "level": "high",
      "factors": {
        "building_age": 25,
        "insulation_quality": "fair",
        "cooling_capacity": "standard",
        "heat_resistance": "medium"
      }
    },
    "extreme_cold": {
      "score": 55.0,
      "level": "medium",
      "factors": {...}
    },
    "wildfire": {...},
    "drought": {...},
    "water_stress": {...},
    "sea_level_rise": {...},
    "river_flood": {...},
    "urban_flood": {...},
    "typhoon": {...}
  },
  "computed_at": "2025-12-01T10:30:00Z",
  "expires_at": "2025-12-02T10:30:00Z"
}
```

### 2.3 응답 (202 Accepted - 비동기)

```json
{
  "request_id": "vuln-req-12345",
  "status": "processing",
  "estimated_time_seconds": 5,
  "status_url": "/api/v1/status/vuln-req-12345"
}
```

### 2.4 에러 응답

**400 Bad Request**:
```json
{
  "error": {
    "code": "INVALID_INPUT",
    "message": "building_age must be between 0 and 100",
    "details": {
      "field": "building_age",
      "value": 150,
      "constraint": "0 <= age <= 100"
    }
  }
}
```

**500 Internal Server Error**:
```json
{
  "error": {
    "code": "CALCULATION_FAILED",
    "message": "Failed to calculate vulnerability scores",
    "request_id": "vuln-req-12345"
  }
}
```

---

## 3. Exposure 계산 API

### 3.1 요청

**Endpoint**: `POST /api/v1/calculate/exposure`

**Request Body**:
```json
{
  "site_id": "uuid-12345",
  "asset_info": {
    "total_asset_value": 50000000000,
    "floor_area": 5000.0
  },
  "location": {
    "latitude": 37.5665,
    "longitude": 126.9780
  }
}
```

### 3.2 응답 (200 OK)

```json
{
  "request_id": "exp-req-67890",
  "status": "completed",
  "site_id": "uuid-12345",
  "results": {
    "extreme_heat": {"score": 0.65, "proximity_factor": 0.8},
    "extreme_cold": {"score": 0.60, "proximity_factor": 0.75},
    "wildfire": {...},
    "drought": {...},
    "water_stress": {...},
    "sea_level_rise": {...},
    "river_flood": {...},
    "urban_flood": {...},
    "typhoon": {...}
  },
  "computed_at": "2025-12-01T10:30:00Z"
}
```

---

## 4. AAL 계산 API

### 4.1 요청

**Endpoint**: `POST /api/v1/calculate/aal`

**Request Body**:
```json
{
  "site_id": "uuid-12345",
  "hazard_scores": {
    "extreme_heat": {
      "ssp1_2.6": 0.45,
      "ssp2_4.5": 0.55,
      "ssp3_7.0": 0.65,
      "ssp5_8.5": 0.75
    }
    // ... 나머지 8개 리스크
  },
  "vulnerability_scores": {
    "extreme_heat": 65.0,
    "extreme_cold": 55.0
    // ... 나머지 7개 리스크
  },
  "asset_info": {
    "total_asset_value": 50000000000,
    "insurance_coverage_rate": 0.7
  },
  "climate_data": {
    "grid_id": 12345,
    "scenario_id": 2,
    "start_year": 2025,
    "end_year": 2050,
    "variables": {
      "wsdi": [3.2, 4.1, 5.3, ...],
      "csdi": [2.1, 1.8, ...]
      // ... 나머지 변수
    }
  }
}
```

### 4.2 응답 (200 OK)

```json
{
  "request_id": "aal-req-11111",
  "status": "completed",
  "site_id": "uuid-12345",
  "results": {
    "extreme_heat": {
      "ssp1_2.6": {
        "base_aal": 0.0010,
        "vulnerability_scale": 1.05,
        "final_aal_percentage": 0.32,
        "expected_loss": 160000000,
        "risk_level": "moderate"
      },
      "ssp2_4.5": {
        "base_aal": 0.0012,
        "final_aal_percentage": 0.38,
        "expected_loss": 190000000,
        "risk_level": "moderate"
      },
      "ssp3_7.0": {...},
      "ssp5_8.5": {...}
    },
    "extreme_cold": {...},
    // ... 나머지 8개 리스크
  },
  "total_expected_loss": {
    "ssp1_2.6": 850000000,
    "ssp2_4.5": 1200000000,
    "ssp3_7.0": 1650000000,
    "ssp5_8.5": 2100000000
  },
  "computed_at": "2025-12-01T10:35:00Z",
  "expires_at": "2025-12-02T10:35:00Z"
}
```

---

## 5. Hazard Score 조회 API (배치 결과)

### 5.1 요청

**Endpoint**: `GET /api/v1/hazard-scores`

**Query Parameters**:
```
latitude=37.5665
longitude=126.9780
scenario_id=2
start_year=2025
end_year=2050
```

### 5.2 응답 (200 OK)

```json
{
  "grid_id": 12345,
  "scenario_id": 2,
  "scenario_name": "SSP2-4.5",
  "location": {
    "latitude": 37.5665,
    "longitude": 126.9780
  },
  "hazard_scores": {
    "extreme_heat": {
      "short_term": 0.45,
      "mid_term": 0.52,
      "long_term": 0.58
    },
    "extreme_cold": {...},
    // ... 나머지 8개 리스크
  },
  "computed_at": "2025-11-30T00:00:00Z"
}
```

### 5.3 에러 응답

**404 Not Found**:
```json
{
  "error": {
    "code": "RESOURCE_NOT_FOUND",
    "message": "No hazard data found for the given location and scenario",
    "details": {
      "latitude": 37.5665,
      "longitude": 126.9780,
      "scenario_id": 2
    }
  }
}
```

---

## 6. 작업 상태 조회 API

### 6.1 요청

**Endpoint**: `GET /api/v1/status/{request_id}`

**Path Parameters**:
- `request_id`: 요청 ID (예: `vuln-req-12345`)

### 6.2 응답 (200 OK)

**처리 중**:
```json
{
  "request_id": "vuln-req-12345",
  "status": "processing",
  "progress": 60,
  "started_at": "2025-12-01T10:30:00Z",
  "estimated_completion": "2025-12-01T10:30:05Z"
}
```

**완료**:
```json
{
  "request_id": "vuln-req-12345",
  "status": "completed",
  "progress": 100,
  "started_at": "2025-12-01T10:30:00Z",
  "completed_at": "2025-12-01T10:30:05Z",
  "result_url": "/api/v1/results/vuln-req-12345"
}
```

**실패**:
```json
{
  "request_id": "vuln-req-12345",
  "status": "failed",
  "progress": 40,
  "started_at": "2025-12-01T10:30:00Z",
  "failed_at": "2025-12-01T10:30:03Z",
  "error": {
    "code": "CALCULATION_FAILED",
    "message": "Invalid climate data"
  }
}
```

---

## 7. 배치 작업 트리거 API (관리자용)

### 7.1 Hazard Batch 실행

**Endpoint**: `POST /api/v1/admin/batch/hazard`

**Request Body**:
```json
{
  "scenario_ids": [1, 2, 3, 4],
  "year_range": [2025, 2050],
  "grid_ids": [12345, 12346, 12347]
}
```

**Response** (202 Accepted):
```json
{
  "batch_id": "batch-hazard-20251201",
  "status": "queued",
  "estimated_duration_minutes": 120,
  "status_url": "/api/v1/admin/batch/status/batch-hazard-20251201"
}
```

---

## 8. 에러 코드 정의

| 코드 | HTTP 상태 | 설명 |
|------|----------|------|
| `INVALID_INPUT` | 400 | 입력 데이터 검증 실패 |
| `MISSING_REQUIRED_FIELD` | 400 | 필수 필드 누락 |
| `UNAUTHORIZED` | 401 | API 키 인증 실패 |
| `RATE_LIMIT_EXCEEDED` | 429 | 요청 제한 초과 |
| `RESOURCE_NOT_FOUND` | 404 | 데이터 없음 |
| `CALCULATION_FAILED` | 500 | 계산 오류 |
| `DATABASE_ERROR` | 500 | 데이터베이스 오류 |
| `REQUEST_TIMEOUT` | 504 | 요청 시간 초과 |

---

## 9. 응답 시간 SLA

| API | 목표 응답 시간 (95th percentile) |
|-----|-------------------------------|
| Vulnerability 계산 | < 2초 |
| Exposure 계산 | < 1초 |
| AAL 계산 | < 3초 |
| Hazard Score 조회 | < 100ms |
| 상태 조회 | < 50ms |

---

## 10. 예시 cURL 요청

### Vulnerability 계산
```bash
curl -X POST https://api.modelops.skax.com/v1/calculate/vulnerability \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "site_id": "uuid-12345",
    "building_info": {
      "building_age": 25,
      "structure": "철근콘크리트",
      "main_purpose": "업무시설",
      "floors_below": 2,
      "floors_above": 10,
      "has_piloti": false,
      "has_seismic_design": true,
      "fire_access": true
    },
    "location": {
      "latitude": 37.5665,
      "longitude": 126.9780,
      "elevation": 38.5
    }
  }'
```

### Hazard Score 조회
```bash
curl -X GET "https://api.modelops.skax.com/v1/hazard-scores?latitude=37.5665&longitude=126.9780&scenario_id=2" \
  -H "Authorization: Bearer YOUR_API_KEY"
```

---

## 다음 문서

👉 [05. 코드 참조](./05_CODE_REFERENCE.md)
