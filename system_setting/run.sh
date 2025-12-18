#!/bin/bash

echo "ESG Trends Agent Docker 실행"

# 스크립트 디렉터리로 이동
cd "$(dirname "$0")/.." || exit 1

echo "프로젝트 경로: $(pwd)"

# .env 파일 확인
if [ ! -f .env ]; then
    echo ".env 파일이 없습니다"
    echo ".env 파일을 생성하고 API 키를 설정하세요"
    exit 1
fi

# logs 디렉터리 생성
mkdir -p logs

# 기존 컨테이너 정리
docker rm -f esg-trends-agent 2>/dev/null

# Docker 컨테이너 실행
echo ""
echo "Agent 실행 중..."
docker run --rm \
    --name esg-trends-agent \
    --env-file .env \
    -v "$(pwd)/logs:/app/logs" \
    esg-trends-agent:latest

if [ $? -eq 0 ]; then
    echo ""
    echo "ESG Trends Agent 실행 완료"
else
    echo ""
    echo "ESG Trends Agent 실행 실패"
    exit 1
fi
