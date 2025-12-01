#!/bin/bash
# 월별 그리드 데이터 NetCDF 파일 압축 해제 스크립트

BASE_DIR="/Users/odong-i/Desktop/SKALA/FinalProject/DB_ALL/ETL/data/KMA/extracted/KMA/downloads_kma_ssp_gridraw"

# 시나리오 목록
SCENARIOS=("SSP126" "SSP245" "SSP370" "SSP585")

# 변수 목록
VARIABLES=("TA" "RN" "WS" "RHM" "SI")

echo "=========================================="
echo "월별 그리드 데이터 NetCDF 파일 압축 해제"
echo "=========================================="

for scenario in "${SCENARIOS[@]}"; do
    for var in "${VARIABLES[@]}"; do
        monthly_dir="${BASE_DIR}/${scenario}/monthly"
        nc_file="${monthly_dir}/${scenario}_${var}_gridraw_monthly_2021-2100.nc"

        echo ""
        echo "처리 중: ${scenario}/${var}"

        if [ -f "${nc_file}" ]; then
            cd "${monthly_dir}"

            # 파일 타입 확인
            file_type=$(file "${nc_file}" | grep -o "gzip compressed data")

            if [ -n "$file_type" ]; then
                echo "  - gzip 압축 파일 감지, 압축 해제 중..."

                # 1. .nc -> .nc.gz로 rename
                mv "${nc_file}" "${nc_file}.gz"

                # 2. gunzip으로 압축 해제 (tar 파일 생성)
                gunzip "${nc_file}.gz"

                # 3. tar 파일인지 확인
                if [ -f "${nc_file}" ]; then
                    file_type=$(file "${nc_file}" | grep -o "tar archive")

                    if [ -n "$file_type" ]; then
                        echo "  - tar archive 감지, 추출 중..."

                        # 4. tar 파일 추출
                        tar -xf "${nc_file}"

                        # 5. 원본 tar 파일 삭제
                        rm "${nc_file}"

                        # 6. 추출된 NetCDF 파일 확인
                        extracted_file=$(find . -maxdepth 1 -name "AR6_${scenario}_*_${var}_*.nc" -type f)

                        if [ -n "$extracted_file" ]; then
                            echo "  ✓ 완료: ${extracted_file}"
                            file "${extracted_file}"
                        else
                            echo "  ✗ 실패: 추출된 NetCDF 파일을 찾을 수 없음"
                        fi
                    else
                        echo "  ✗ 경고: tar archive가 아님"
                    fi
                else
                    echo "  ✗ 실패: gunzip 후 파일 없음"
                fi
            else
                echo "  - 이미 압축 해제된 파일"
            fi
        else
            echo "  ✗ 파일 없음: ${nc_file}"
        fi
    done
done

echo ""
echo "=========================================="
echo "압축 해제 완료!"
echo "=========================================="
