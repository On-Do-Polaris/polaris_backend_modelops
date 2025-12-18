#!/bin/bash

echo "ESG Trends Agent 시스템 설정"

cd "$(dirname "$0")/.." || exit 1
PROJECT_DIR="$(pwd)"

echo "프로젝트 경로: $PROJECT_DIR"

# .env 파일 확인
if [ ! -f .env ]; then
    echo ".env 파일이 없습니다"
    echo ".env 파일을 생성하고 API 키를 설정하세요"
    exit 1
fi

# 1. 기존 컨테이너 정리
echo ""
echo "[1/4] 기존 컨테이너 정리..."
docker rm -f esg-trends-agent 2>/dev/null

# 2. Docker 이미지 빌드
echo ""
echo "[2/4] Docker 이미지 빌드 중..."
docker build -t esg-trends-agent:latest .

if [ $? -ne 0 ]; then
    echo "이미지 빌드 실패"
    exit 1
fi

echo ""
echo "빌드된 이미지:"
docker images | grep esg-trends-agent

# 3. 테스트 실행
echo ""
echo "[3/4] 테스트 실행 중..."
./docker/run.sh

if [ $? -ne 0 ]; then
    echo "테스트 실행 실패"
    exit 1
fi

# 4. Cron 등록
echo ""
echo "[4/4] Cron 작업 등록 중..."

# cron 작업 내용 (매일 오전 9시 실행)
CRON_JOB="0 9 * * * cd $PROJECT_DIR && ./docker/run.sh >> $PROJECT_DIR/logs/cron.log 2>&1"

# 기존 cron 목록 가져오기
crontab -l 2>/dev/null > /tmp/current_cron

# 이미 등록된 작업인지 확인
if grep -q "esg-trends-agent" /tmp/current_cron 2>/dev/null || grep -q "$PROJECT_DIR/docker/run.sh" /tmp/current_cron 2>/dev/null; then
    echo "기존 Cron 작업을 제거합니다..."
    grep -v "esg-trends-agent" /tmp/current_cron | grep -v "$PROJECT_DIR/docker/run.sh" > /tmp/new_cron
    mv /tmp/new_cron /tmp/current_cron
fi

# 새 cron 작업 추가
echo "$CRON_JOB" >> /tmp/current_cron

# cron 등록
crontab /tmp/current_cron

# 임시 파일 삭제
rm -f /tmp/current_cron

echo ""
echo "Cron 작업이 등록되었습니다:"
echo "  - 실행 시간: 매일 오전 9시"
echo "  - 로그 위치: $PROJECT_DIR/logs/cron.log"

echo ""
echo "현재 등록된 Cron 작업:"
crontab -l | grep -v "^#" | grep -v "^$"

echo ""
echo "========================================="
echo "ESG Trends Agent 시스템 설정 완료"
echo "========================================="
echo ""
echo "수동 실행: ./docker/run.sh"
echo "Cron 확인: crontab -l"
echo "Cron 제거: crontab -e (해당 라인 삭제)"
