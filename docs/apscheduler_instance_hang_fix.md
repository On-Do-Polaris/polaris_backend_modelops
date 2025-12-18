# APScheduler 배치 작업 Instance Hang 문제 해결

## 문제 상황

배치 작업 실행 시 다음과 같은 경고가 발생하며 작업이 skip됨:

```
2025-12-18 09:13:54 - WARNING - Execution of job "P(H) Batch (Custom Trigger)" skipped:
maximum number of running instances reached (1)
```

**특이사항:**
- 실제로 배치 계산이 실행 중이지 않음
- `ps aux` 확인 결과 배치 프로세스가 없음
- 하지만 APScheduler는 여전히 인스턴스가 실행 중이라고 판단
- 새로운 배치 작업을 실행할 수 없음

## 원인 분석

### APScheduler의 Instance 관리 메커니즘

APScheduler는 각 Job 함수의 실행 인스턴스 수를 내부적으로 추적합니다:

```python
# Job 실행 전
job._instances += 1
if job._instances > job.max_instances:
    # "maximum number of running instances reached" 경고
    job._instances -= 1
    return

# Job 실행 완료 후 (finally 블록)
try:
    job.func(*args, **kwargs)
except:
    # 에러 로깅
finally:
    job._instances -= 1  # 반드시 실행되어야 함
```

**핵심:** `job._instances` 카운트는 **Job 함수가 return될 때만** 감소합니다.

### 실제 발생한 문제

#### 1. ProcessPoolExecutor가 Hang 상태에 빠짐

**배치 코드 구조:**
```python
# probability_timeseries_batch.py
def run_probability_batch(...):
    with ProcessPoolExecutor(max_workers=4) as executor:
        futures = {
            executor.submit(_process_task_worker, task): task
            for task in tasks
        }

        for future in as_completed(futures):
            result = future.result()  # ❌ Timeout 없음!
            # 결과 처리...
```

**문제 시나리오:**

```
1. 배치 시작 (00:17:10.053)
   ↓
2. ProcessPoolExecutor 생성, 4개 worker 프로세스 시작
   ↓
3. Worker에서 DB 연결 시도
   ↓
4. DB 연결 실패: "connection already closed" (00:17:10.110)
   - Connection Pool Race Condition 발생
   - Worker 프로세스들이 무효한 연결을 받음
   ↓
5. Worker가 DB 재연결을 시도하며 무한 대기
   ↓
6. future.result()가 무한 대기 (Timeout 없음)
   ↓
7. ProcessPoolExecutor의 with 블록이 종료되지 않음
   ↓
8. run_probability_batch() 함수가 return되지 않음
   ↓
9. probability_batch_job() 함수도 return되지 않음
   ↓
10. APScheduler는 _instances 카운트를 감소시키지 못함
    ↓
11. 영구적으로 "maximum instances reached" 상태 유지
```

#### 2. 증거 확인

배치 시작 로그는 있지만 종료 로그가 없음:

```python
# main.py
def probability_batch_job():
    logger.info("P(H) BATCH JOB STARTED")  # ✓ 로그 있음

    try:
        run_probability_batch(...)
        logger.info("P(H) BATCH JOB COMPLETED SUCCESSFULLY")  # ❌ 로그 없음
    except Exception as e:
        logger.error(f"P(H) BATCH JOB FAILED: {e}")  # ❌ 로그 없음
```

**결론:** 함수가 try 블록 내에서 멈춰서 완료 로그도, 에러 로그도 출력되지 않음

#### 3. 프로세스 상태 확인

```bash
# 컨테이너 내부에서 확인
ps aux | grep -E "(probability|hazard)"
# → 배치 프로세스 없음

ps -eLf | grep python | wc -l
# → 24개 Python 쓰레드 (main + API workers)

# 00:57-00:58에 생성된 worker 프로세스들 발견
# 이들은 site_assessment API의 ThreadPoolExecutor 워커들
```

## 해결 방법

### 1. Timeout 추가 (적용한 해결책)

#### 개별 Task Timeout

각 태스크(격자점 하나의 계산)가 5분 안에 완료되지 않으면 실패 처리:

```python
# probability_timeseries_batch.py (Line 271)
# hazard_timeseries_batch.py (Line 297)

for future in as_completed(futures):
    task = futures[future]
    try:
        result = future.result(timeout=300)  # ✓ 5분 timeout 추가

        if result['status'] == 'success':
            # 결과 처리...
        else:
            failed_count += 1

    except TimeoutError:
        # Timeout 발생 시 해당 태스크만 실패 처리
        failed_count += 1
        logger.error(f"Task timeout after 300s: {task}")
        # 다음 태스크 계속 진행
```

**효과:**
- Worker가 멈춰도 5분 후 해당 태스크만 실패 처리
- ProcessPoolExecutor가 무한 대기하지 않음
- `run_probability_batch()` 함수가 항상 return됨
- APScheduler 인스턴스 카운트가 정상적으로 감소
- 다음 배치 스케줄 가능

#### 적용 전후 비교

**Before:**
```
✗ Worker 멈춤 → future.result() 무한 대기
✗ 함수 return 안 됨 → 인스턴스 release 안 됨
✗ 다음 배치 skip: "maximum instances reached"
```

**After:**
```
✓ Worker 멈춤 → 5분 후 TimeoutError
✓ 해당 태스크 실패 처리, 다음 태스크 계속
✓ 함수 항상 return → 인스턴스 정상 release
✓ 다음 배치 정상 실행 가능
```

## 추가 방어 방안 (프로덕션 환경)

### 2. 전체 Batch Timeout

전체 배치 실행 시간 제한:

```python
# as_completed에 전체 timeout 추가
for future in as_completed(futures, timeout=7200):  # 2시간
    try:
        result = future.result(timeout=300)  # 개별 5분
```

### 3. Circuit Breaker 패턴

연속 실패 시 빠른 실패 처리:

```python
class ConnectionCircuitBreaker:
    def __init__(self, failure_threshold=5, timeout=60):
        self.failures = 0
        self.threshold = failure_threshold
        self.last_failure_time = None
        self.timeout = timeout

    def execute(self, func):
        # Circuit이 열린 상태인지 확인
        if self.failures >= self.threshold:
            if (datetime.now() - self.last_failure_time).seconds < self.timeout:
                raise CircuitOpenError("Too many failures, circuit open")
            else:
                # Timeout 지나면 재시도 허용
                self.failures = 0

        try:
            result = func()
            self.failures = 0  # 성공 시 리셋
            return result
        except Exception as e:
            self.failures += 1
            self.last_failure_time = datetime.now()

            if self.failures >= self.threshold:
                # Circuit 열림 - 전체 배치 중단
                raise CircuitOpenError(
                    f"Circuit opened after {self.failures} failures"
                ) from e
            raise

# 사용
breaker = ConnectionCircuitBreaker(failure_threshold=5)

for task in tasks:
    try:
        result = breaker.execute(lambda: process_task(task))
    except CircuitOpenError:
        logger.error("Circuit opened, stopping batch")
        break  # 배치 중단하고 return
```

**효과:**
- DB 연결이 5번 연속 실패하면 즉시 배치 종료
- 무의미한 재시도로 시간 낭비 방지
- 함수가 빠르게 return되어 인스턴스 release

### 4. Graceful Degradation (청크 단위 처리)

전체를 한 번에 처리하지 않고 청크 단위로:

```python
def run_probability_batch_chunked(
    grid_points: List[Tuple[float, float]] = None,
    chunk_size: int = 1000,
    **kwargs
):
    """청크 단위로 배치 처리"""

    if grid_points is None:
        grid_points = get_all_grid_points()

    # 격자점을 chunk_size 단위로 분할
    chunks = [
        grid_points[i:i+chunk_size]
        for i in range(0, len(grid_points), chunk_size)
    ]

    total_success = 0
    total_failed = 0

    for i, chunk in enumerate(chunks):
        logger.info(f"Processing chunk {i+1}/{len(chunks)}")

        try:
            # 청크당 timeout 설정
            with timeout_context(600):  # 10분
                run_probability_batch(
                    grid_points=chunk,
                    **kwargs
                )
            total_success += len(chunk)

        except TimeoutError:
            logger.error(f"Chunk {i} timeout, skipping")
            total_failed += len(chunk)
            continue  # 한 청크 실패해도 다음 청크 계속

        except Exception as e:
            logger.error(f"Chunk {i} failed: {e}")

            # 초반 3개 청크 실패 시 전체 중단
            if i < 3:
                raise

            total_failed += len(chunk)
            continue

    # 통계 로깅
    logger.info(f"Batch completed: {total_success} success, {total_failed} failed")

    # 항상 return 보장
    return {
        'success': total_success,
        'failed': total_failed
    }
```

**효과:**
- 한 청크가 실패해도 다른 청크는 처리됨
- 전체 배치 실패 위험 감소
- Progress tracking 용이

### 5. Dead Letter Queue (DLQ)

실패한 작업을 별도 저장하여 나중에 재처리:

```python
def save_to_dead_letter_queue(task: Dict, error: str):
    """실패한 태스크를 DLQ에 저장"""
    db = DatabaseConnection()
    db.execute("""
        INSERT INTO batch_dead_letter_queue
        (task_type, task_data, error_message, created_at)
        VALUES (%s, %s, %s, NOW())
    """, ('probability', json.dumps(task), error))

# 배치 처리 중
for future in as_completed(futures):
    try:
        result = future.result(timeout=300)

        if result['status'] == 'failed':
            # DLQ에 저장
            save_to_dead_letter_queue(
                task=result['task'],
                error=result.get('error', 'Unknown error')
            )

    except TimeoutError:
        # Timeout도 DLQ에 저장
        save_to_dead_letter_queue(
            task=task,
            error='Task timeout after 300s'
        )
```

나중에 DLQ를 조회하여 실패한 태스크만 재처리:

```python
def reprocess_dead_letter_queue():
    """DLQ의 실패한 태스크들을 재처리"""
    db = DatabaseConnection()
    failed_tasks = db.fetch_all(
        "SELECT * FROM batch_dead_letter_queue WHERE reprocessed = FALSE"
    )

    for record in failed_tasks:
        task = json.loads(record['task_data'])
        try:
            result = process_task(task)
            # 성공 시 DLQ에서 제거
            db.execute(
                "UPDATE batch_dead_letter_queue SET reprocessed = TRUE WHERE id = %s",
                (record['id'],)
            )
        except Exception as e:
            logger.error(f"Reprocess failed: {e}")
```

### 6. Health Check + 강제 종료

배치 상태를 외부에서 모니터링하여 강제 종료:

```python
import redis
import os
import signal

# 배치 시작 시 상태 등록
def start_batch_monitoring(job_id: str, max_duration: int = 7200):
    """배치 시작을 Redis에 등록"""
    r = redis.Redis()
    r.hset(f'batch:{job_id}', mapping={
        'status': 'running',
        'pid': os.getpid(),
        'start_time': datetime.now().isoformat(),
        'max_duration': max_duration
    })

# 별도 모니터링 프로세스
def batch_monitor():
    """주기적으로 배치 상태 확인"""
    r = redis.Redis()

    while True:
        for key in r.scan_iter('batch:*'):
            info = r.hgetall(key)

            if info['status'] == 'running':
                start_time = datetime.fromisoformat(info['start_time'])
                running_time = (datetime.now() - start_time).seconds
                max_duration = int(info['max_duration'])

                if running_time > max_duration:
                    # 최대 실행 시간 초과 - 강제 종료
                    pid = int(info['pid'])
                    logger.warning(f"Killing hung batch process: PID {pid}")
                    os.kill(pid, signal.SIGTERM)

                    # 상태 업데이트
                    r.hset(key, 'status', 'killed')
                    r.hset(key, 'killed_at', datetime.now().isoformat())

        time.sleep(60)  # 1분마다 체크
```

### 7. APScheduler Job 설정 강화

```python
# main.py
from apscheduler.executors.pool import ThreadPoolExecutor as APSThreadPoolExecutor

scheduler = BackgroundScheduler(
    executors={
        'default': APSThreadPoolExecutor(max_workers=2)
    },
    job_defaults={
        'coalesce': False,  # 밀린 작업 건너뛰기
        'max_instances': 1,  # 동시 실행 인스턴스 수
        'misfire_grace_time': 3600  # 1시간 이내 실행 실패 허용
    }
)

# Job 등록
scheduler.add_job(
    probability_batch_job,
    trigger=CronTrigger(month=1, day=1, hour=2, minute=0),
    id='probability_batch',
    name='P(H) Timeseries Batch',
    replace_existing=True,
    max_instances=1,
    misfire_grace_time=3600,  # 예정 시각 지나도 1시간 내 실행
    coalesce=True  # 밀린 작업 하나로 통합
)
```

## 실무 Best Practices

### 1. 계층별 Timeout 설정

```
┌─────────────────────────────────────────┐
│ APScheduler Job Level (3시간)           │
│  ┌───────────────────────────────────┐  │
│  │ Batch Function Level (2시간)      │  │
│  │  ┌─────────────────────────────┐  │  │
│  │  │ Chunk Level (10분)          │  │  │
│  │  │  ┌───────────────────────┐  │  │  │
│  │  │  │ Task Level (5분)      │  │  │  │
│  │  │  └───────────────────────┘  │  │  │
│  │  └─────────────────────────────┘  │  │
│  └───────────────────────────────────┘  │
└─────────────────────────────────────────┘
```

### 2. 실패 처리 전략

```python
실패 유형별 처리:

1. Timeout (5분)
   → 해당 태스크만 실패 처리
   → DLQ에 저장
   → 다음 태스크 계속

2. DB Connection Error (Circuit Breaker)
   → 5번 연속 실패 시 Circuit Open
   → 배치 중단하고 return
   → 인스턴스 release

3. 데이터 오류 (개별 처리)
   → 로그 기록
   → 다음 태스크 계속

4. 심각한 에러 (시스템 레벨)
   → 배치 전체 중단
   → Exception raise
   → 알림 발송
```

### 3. 모니터링 지표

```python
배치 실행 시 수집할 메트릭:

- start_time: 시작 시각
- end_time: 종료 시각
- duration: 실행 시간
- total_tasks: 전체 태스크 수
- completed_tasks: 완료된 태스크 수
- failed_tasks: 실패한 태스크 수
- timeout_tasks: Timeout된 태스크 수
- success_rate: 성공률
- avg_task_duration: 평균 태스크 처리 시간
- peak_memory: 최대 메모리 사용량
- db_connection_errors: DB 연결 에러 수
```

### 4. 프로덕션 체크리스트

- [ ] Task 레벨 timeout 설정 (5분)
- [ ] Batch 레벨 timeout 설정 (2시간)
- [ ] Circuit Breaker 구현
- [ ] Dead Letter Queue 구현
- [ ] Health Check 모니터링
- [ ] 실패 알림 설정 (Slack, Email)
- [ ] 메트릭 수집 및 대시보드
- [ ] 청크 단위 처리
- [ ] 재시도 메커니즘
- [ ] 로그 레벨 최적화

## 결론

**근본 원인:**
- ProcessPoolExecutor의 `future.result()`에 timeout이 없어서 Worker가 멈출 때 무한 대기
- 함수가 return되지 않아 APScheduler 인스턴스 카운트가 release되지 않음

**핵심 해결책:**
- `future.result(timeout=300)` 추가로 개별 태스크 timeout 설정
- Timeout 발생 시 해당 태스크만 실패 처리하고 배치 계속 진행
- 함수가 항상 return되도록 보장

**추가 방어:**
- Circuit Breaker로 연속 실패 시 빠른 종료
- 청크 단위 처리로 부분 실패 격리
- Dead Letter Queue로 실패한 작업 재처리
- Health Check로 외부 모니터링

**효과:**
- ✅ 배치 작업이 멈춰도 최대 5분 후 다음 작업 진행
- ✅ APScheduler 인스턴스가 항상 정상 release
- ✅ "maximum instances reached" 에러 해결
- ✅ 안정적인 배치 스케줄링 가능

---

**관련 파일:**
- [modelops/batch/probability_timeseries_batch.py:271](modelops/batch/probability_timeseries_batch.py#L271)
- [modelops/batch/hazard_timeseries_batch.py:297](modelops/batch/hazard_timeseries_batch.py#L297)
- [main.py:28-72](main.py#L28-L72)

**참고 자료:**
- [APScheduler Documentation](https://apscheduler.readthedocs.io/)
- [Python concurrent.futures](https://docs.python.org/3/library/concurrent.futures.html)
- [Circuit Breaker Pattern](https://martinfowler.com/bliki/CircuitBreaker.html)
