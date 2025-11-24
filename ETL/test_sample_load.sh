#!/bin/bash
#
# SKALA Physical Risk AI - Sample Data Loading Test
# 모든 ETL 스크립트를 샘플 모드(10개)로 실행하여 전체 파이프라인을 테스트합니다
#
# 최종 수정일: 2025-11-22
# 버전: v01

set -e  # Exit on error

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Activate virtual environment
source .venv/bin/activate

# Set sample mode
export SAMPLE_LIMIT=10
export PYTHONPATH=.

echo "========================================"
echo "SKALA Physical Risk AI - Sample Data Test"
echo "========================================"
echo ""
echo "⚠️  Sample Mode: Loading 10 samples per dataset"
echo ""

# Function to run script and report status
run_etl() {
    local script_name=$1
    local description=$2

    echo ""
    echo "${YELLOW}▶ Running: ${description}${NC}"
    echo "   Script: ${script_name}"

    if .venv/bin/python3 scripts/${script_name} 2>&1 | tee logs/${script_name}.log; then
        echo "${GREEN}✅ ${description} - SUCCESS${NC}"
        return 0
    else
        echo "${RED}❌ ${description} - FAILED${NC}"
        return 1
    fi
}

# Create logs directory
mkdir -p logs

# Initialize counters
total=0
success=0
failed=0

# Run ETL scripts in order
echo ""
echo "Starting ETL pipeline..."
echo ""

# 1. Admin regions
((total++))
if run_etl "load_admin_regions.py" "행정구역 데이터"; then
    ((success++))
else
    ((failed++))
fi

# 2. Sea level
((total++))
if run_etl "load_sea_level_netcdf.py" "해수면 데이터" <<< 'y'; then
    ((success++))
else
    ((failed++))
fi

# 3. Monthly grid data
((total++))
if run_etl "load_monthly_grid_data.py" "월별 그리드 데이터" <<< 'y'; then
    ((success++))
else
    ((failed++))
fi

# 4. Yearly grid data
((total++))
if run_etl "load_yearly_grid_data.py" "연별 그리드 데이터" <<< 'y'; then
    ((success++))
else
    ((failed++))
fi

# 5. Population
((total++))
if run_etl "load_population.py" "인구 데이터"; then
    ((success++))
else
    ((failed++))
fi

# 6. Landcover (requires GDAL)
((total++))
if run_etl "load_landcover.py" "토지피복 데이터"; then
    ((success++))
else
    ((failed++))
fi

# 7. DEM (requires GDAL)
((total++))
if run_etl "load_dem.py" "고도 데이터"; then
    ((success++))
else
    ((failed++))
fi

# 8. Drought (requires GDAL)
((total++))
if run_etl "load_drought.py" "가뭄 데이터"; then
    ((success++))
else
    ((failed++))
fi

# Summary
echo ""
echo "========================================"
echo "ETL Pipeline Test Results"
echo "========================================"
echo ""
echo "Total scripts: ${total}"
echo "${GREEN}Success: ${success}${NC}"
echo "${RED}Failed: ${failed}${NC}"
echo ""

if [ $failed -eq 0 ]; then
    echo "${GREEN}✅ All ETL scripts completed successfully!${NC}"
    exit 0
else
    echo "${RED}⚠️  Some ETL scripts failed. Check logs/ directory for details.${NC}"
    exit 1
fi
