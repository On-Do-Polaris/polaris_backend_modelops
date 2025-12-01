-- E, V, AAL 스케일링 결과 저장을 위한 테이블 생성
-- 작성일: 2025-12-01

-- 1. Exposure 결과 저장 테이블
CREATE TABLE IF NOT EXISTS exposure_results (
    latitude NUMERIC NOT NULL,
    longitude NUMERIC NOT NULL,
    risk_type VARCHAR(50) NOT NULL,
    exposure_score REAL,  -- 0.0 ~ 1.0
    proximity_factor REAL,  -- 위험 요소와의 근접도
    calculated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (latitude, longitude, risk_type)
);

CREATE INDEX IF NOT EXISTS idx_exposure_location ON exposure_results(latitude, longitude);
CREATE INDEX IF NOT EXISTS idx_exposure_risk_type ON exposure_results(risk_type);

COMMENT ON TABLE exposure_results IS 'E (Exposure/노출도) 계산 결과 저장';
COMMENT ON COLUMN exposure_results.exposure_score IS '노출도 점수 (0.0-1.0)';
COMMENT ON COLUMN exposure_results.proximity_factor IS '위험 요소 근접도 (0.0-1.0)';


-- 2. Vulnerability 결과 저장 테이블
CREATE TABLE IF NOT EXISTS vulnerability_results (
    latitude NUMERIC NOT NULL,
    longitude NUMERIC NOT NULL,
    risk_type VARCHAR(50) NOT NULL,
    vulnerability_score REAL,  -- 0.0 ~ 100.0
    vulnerability_level VARCHAR(20),  -- very_low, low, medium, high, very_high
    factors JSONB,  -- 취약성 요인 상세 정보
    calculated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (latitude, longitude, risk_type),
    CONSTRAINT chk_vulnerability_score CHECK (vulnerability_score >= 0 AND vulnerability_score <= 100),
    CONSTRAINT chk_vulnerability_level CHECK (vulnerability_level IN ('very_low', 'low', 'medium', 'high', 'very_high'))
);

CREATE INDEX IF NOT EXISTS idx_vulnerability_location ON vulnerability_results(latitude, longitude);
CREATE INDEX IF NOT EXISTS idx_vulnerability_risk_type ON vulnerability_results(risk_type);
CREATE INDEX IF NOT EXISTS idx_vulnerability_level ON vulnerability_results(vulnerability_level);
CREATE INDEX IF NOT EXISTS idx_vulnerability_factors ON vulnerability_results USING GIN (factors);

COMMENT ON TABLE vulnerability_results IS 'V (Vulnerability/취약성) 계산 결과 저장';
COMMENT ON COLUMN vulnerability_results.vulnerability_score IS '취약성 점수 (0-100)';
COMMENT ON COLUMN vulnerability_results.vulnerability_level IS '취약성 등급';
COMMENT ON COLUMN vulnerability_results.factors IS '취약성 요인 상세 (건물 연령, 구조 등)';


-- 3. AAL 스케일링 결과 저장 테이블
CREATE TABLE IF NOT EXISTS aal_scaled_results (
    latitude NUMERIC NOT NULL,
    longitude NUMERIC NOT NULL,
    risk_type VARCHAR(50) NOT NULL,
    base_aal REAL,  -- 기존 probability_results.probability
    vulnerability_scale REAL,  -- F_vuln (0.9 ~ 1.1)
    final_aal REAL,  -- base_aal × F_vuln × (1 - insurance)
    insurance_rate REAL DEFAULT 0.0,  -- 보험 보전율 (현재 0.0)
    expected_loss BIGINT,  -- 예상 손실액 (원) - NULL 가능
    calculated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (latitude, longitude, risk_type),
    CONSTRAINT chk_vulnerability_scale CHECK (vulnerability_scale >= 0.9 AND vulnerability_scale <= 1.1),
    CONSTRAINT chk_insurance_rate CHECK (insurance_rate >= 0 AND insurance_rate <= 1)
);

CREATE INDEX IF NOT EXISTS idx_aal_scaled_location ON aal_scaled_results(latitude, longitude);
CREATE INDEX IF NOT EXISTS idx_aal_scaled_risk_type ON aal_scaled_results(risk_type);

COMMENT ON TABLE aal_scaled_results IS 'AAL 스케일링 결과 저장 (V 반영)';
COMMENT ON COLUMN aal_scaled_results.base_aal IS '기본 AAL (probability_results.probability)';
COMMENT ON COLUMN aal_scaled_results.vulnerability_scale IS '취약성 스케일 계수 F_vuln (0.9-1.1)';
COMMENT ON COLUMN aal_scaled_results.final_aal IS '최종 AAL (base_aal × F_vuln × (1 - insurance))';
COMMENT ON COLUMN aal_scaled_results.insurance_rate IS '보험 보전율 (0-1, 현재 0.0 고정)';
COMMENT ON COLUMN aal_scaled_results.expected_loss IS '예상 손실액 (자산값 있을 경우 계산, 현재 NULL)';
