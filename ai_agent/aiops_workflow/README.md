# AIops Workflow

P(H) 확률 및 Hazard Score 배치 계산 워크플로우

## 📁 구조

```
aiops_workflow/
├── __init__.py
├── batch/
│   ├── __init__.py
│   ├── probability_batch.py       # P(H) 배치 계산
│   ├── probability_scheduler.py   # P(H) 스케줄러
│   ├── hazard_batch.py           # Hazard Score 배치 계산
│   └── hazard_scheduler.py       # Hazard Score 스케줄러
├── example_run.py                # 실행 예제
└── README.md                     # 이 파일
```

## 🚀 사용 방법

### 1. 수동 배치 실행

```python
from ai_agent.aiops_workflow import ProbabilityBatchProcessor

# 격자 좌표 (실제로는 DB에서 조회)
grid_coordinates = [
    {'lat': 37.5665, 'lon': 126.9780},  # 서울
    {'lat': 35.1796, 'lon': 129.0756},  # 부산
]

# P(H) 배치 실행
processor = ProbabilityBatchProcessor({
    'parallel_workers': 8
})

result = processor.process_all_grids(grid_coordinates)
print(result)
# {
#     'total_grids': 2,
#     'processed': 2,
#     'failed': 0,
#     'success_rate': 100.0,
#     'duration_hours': 0.5
# }
```

### 2. 스케줄러 자동 실행

```python
from ai_agent.aiops_workflow import ProbabilityScheduler

# 격자 좌표 조회 함수
def get_grids():
    # DB에서 조회
    return db.query("SELECT lat, lon FROM grid_coordinates")

# 스케줄러 설정 (매년 1월 1일 02:00)
scheduler = ProbabilityScheduler({
    'schedule': {
        'type': 'cron',
        'month': 1,
        'day': 1,
        'hour': 2
    },
    'batch_config': {
        'parallel_workers': 8
    }
})

scheduler.start(grid_coordinates_callback=get_grids)
```

## 📊 처리 흐름

### P(H) 배치 계산
1. 격자 좌표 수신
2. 각 격자별로 기후 데이터 조회
3. 9개 리스크 에이전트 실행
   - coastal_flood, cold_wave, drought, high_temperature
   - inland_flood, typhoon, urban_flood, water_scarcity, wildfire
4. 결과 DB 저장
5. 성공률 및 통계 반환

### Hazard Score 배치 계산
1. 격자 좌표 수신
2. 각 격자별로 기후 데이터 조회
3. 9개 리스크 에이전트 실행
4. Hazard Score 계산 (H only, E/V 제외)
5. 결과 DB 저장
6. 성공률 및 통계 반환

## ⚙️ 설정

### 배치 프로세서 설정
```python
config = {
    'parallel_workers': 8,        # 병렬 워커 수
    'db_config': {},              # DB 설정
    'storage_config': {}          # 저장소 설정
}
```

### 스케줄러 설정
```python
config = {
    'schedule': {
        'type': 'cron',           # 'cron' 또는 'interval'
        'month': 1,               # cron: 월 (1-12)
        'day': 1,                 # cron: 일 (1-31)
        'hour': 2,                # cron: 시간 (0-23)
        'minute': 0,              # cron: 분 (0-59)
        # 또는
        'hours': 24               # interval: N시간마다
    },
    'batch_config': {
        'parallel_workers': 8
    },
    'enable_scheduler': True      # 스케줄러 활성화
}
```

## 📝 예제 실행

```bash
# 수동 배치 실행
python ai_agent/aiops_workflow/example_run.py

# 스케줄러 실행 (백그라운드)
python -c "from ai_agent.aiops_workflow.example_run import example_scheduler; example_scheduler()"
```

## 🔧 TODO

- [ ] 데이터베이스 저장 로직 구현 (`_save_results`)
- [ ] 기후 데이터 조회 로직 구현 (`_fetch_climate_data`)
- [ ] 에러 재시도 로직 추가
- [ ] 메트릭 모니터링 추가 (선택적)
- [ ] 알림 기능 추가 (선택적)

## 📅 실행 스케줄

- **P(H) 배치**: 매년 1월 1일 오전 2시
- **Hazard Score 배치**: 매년 1월 1일 오전 4시

## 📈 성능

- 병렬 처리: ProcessPoolExecutor 사용
- 기본 워커 수: 4개 (설정 가능)
- 예상 처리 시간: 격자당 약 2초 (10,000개 기준 약 1.4시간)
