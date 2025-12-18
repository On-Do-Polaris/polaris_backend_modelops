#!/bin/bash

echo "ESG Trends Agent Cron 등록"

cd "$(dirname "$0")/.." || exit 1
PROJECT_DIR="$(pwd)"

echo "프로젝트 경로: $PROJECT_DIR"

# .env 파일 확인
if [ ! -f .env ]; then
    echo "경고: .env 파일이 없습니다"
    echo ".env 파일을 생성하고 API 키를 설정하세요"
fi

# logs 디렉터리 생성
mkdir -p logs

# Cron 작업 등록
echo ""
echo "Cron 작업 등록 중..."

# cron 작업 내용 (월~금 오전 9시 실행)
CRON_JOB="0 9 * * 1-5 cd $PROJECT_DIR && ./run.sh >> $PROJECT_DIR/logs/cron.log 2>&1"

# 기존 cron 목록 가져오기
crontab -l 2>/dev/null > /tmp/current_cron

# 이미 등록된 작업인지 확인
if grep -q "esg-trends-agent" /tmp/current_cron 2>/dev/null || grep -q "$PROJECT_DIR.*run.sh" /tmp/current_cron 2>/dev/null; then
    echo "기존 ESG Trends Agent Cron 작업을 제거합니다..."
    grep -v "esg-trends-agent" /tmp/current_cron | grep -v "$PROJECT_DIR.*run.sh" > /tmp/new_cron
    mv /tmp/new_cron /tmp/current_cron
fi

# 새 cron 작업 추가
echo "$CRON_JOB" >> /tmp/current_cron

# cron 등록
crontab /tmp/current_cron

# 임시 파일 삭제
rm -f /tmp/current_cron

echo ""
echo "========================================="
echo "Cron 작업이 등록되었습니다"
echo "========================================="
echo ""
echo "실행 시간: 월~금 오전 9시"
echo "실행 명령: $PROJECT_DIR/run.sh"
echo "로그 위치: $PROJECT_DIR/logs/cron.log"

echo ""
echo "현재 등록된 Cron 작업:"
crontab -l | grep -v "^#" | grep -v "^$"

echo ""
echo "========================================="
echo "Cron 설정 완료"
echo "========================================="
echo ""
echo "확인: crontab -l"
echo "편집: crontab -e"
echo "제거: crontab -r (모든 cron 삭제) 또는 crontab -e (특정 라인 삭제)"
