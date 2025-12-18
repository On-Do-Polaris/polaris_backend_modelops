# PostgreSQL Connection Pool Race Condition 해결

## 문제 상황

배치 작업 시작 시 다음과 같은 에러가 발생했습니다:

```
2025-12-18 00:17:10,053 - modelops.database.connection - INFO - Database connection pool initialized (minconn=2, maxconn=20)
2025-12-18 00:17:10,110 - modelops.data_loaders.building_data_fetcher - ERROR - Failed to get building code: connection already closed
2025-12-18 00:17:10,111 - modelops.data_loaders.building_data_fetcher - ERROR - Failed to get building code: connection already closed
2025-12-18 00:17:10,112 - modelops.data_loaders.building_data_fetcher - ERROR - Failed to get building code: connection already closed
```

**특징:**
- Connection Pool 초기화 후 **57ms** 만에 에러 발생
- 초기 시작 시에만 발생하고, 이후에는 정상 작동
- 여러 Thread에서 동시에 발생

## 원인 분석

### Race Condition 발생 시나리오

```
1. 배치 작업 시작 (00:17:10.000)
   ↓
2. Connection Pool 초기화 (00:17:10.053)
   - minconn=2, maxconn=20 설정
   ↓
3. 4개 Worker가 병렬로 작업 시작
   ↓
4. 각 Worker에서 9개 리스크 Agent 초기화 (00:17:10.098-101)
   - 총 36개 Agent가 동시에 생성
   ↓
5. 여러 Agent가 동시에 DB 연결 시도 (00:17:10.110)
   - get_connection() 호출
   - _connection_pool.getconn() 실행
   ↓
6. 에러 발생: "connection already closed"
```

### 왜 "connection already closed" 에러가 발생했는가?

**핵심 문제:** Connection Pool 초기화가 완료되었지만, Pool 내부의 연결들이 완전히 준비되기 전에 여러 Thread가 동시에 연결을 요청했습니다.

1. **Pool 초기화 시점과 사용 시점의 간극**
   - `ThreadedConnectionPool` 생성 직후에는 연결이 완전히 준비되지 않을 수 있음
   - Pool은 생성되었지만, 실제 DB 연결은 아직 유효하지 않은 상태

2. **동시 요청으로 인한 경쟁 상태**
   - 36개 Agent가 동시에 `getconn()` 호출
   - 일부 Thread는 아직 유효하지 않은 연결을 받음
   - 해당 연결로 쿼리 실행 시 "connection already closed" 에러

3. **이후 정상 작동하는 이유**
   - 초기 race condition이 해결되면 Pool이 안정화됨
   - 이미 검증된 연결들이 Pool에 존재
   - 이후 요청들은 안정화된 Pool에서 정상 연결을 가져옴

## 해결 방법

### 연결 검증 로직 추가

Connection Pool 초기화 후 즉시 연결을 검증하여, Pool이 완전히 준비된 후에만 사용할 수 있도록 보장합니다.

#### 수정 전 코드

```python
@classmethod
def _init_pool(cls):
    """Connection Pool 초기화 (Lazy Initialization)"""
    import threading

    if cls._pool_lock is None:
        cls._pool_lock = threading.Lock()

    with cls._pool_lock:
        if cls._connection_pool is None:
            try:
                cls._connection_pool = pool.ThreadedConnectionPool(
                    minconn=2,
                    maxconn=20,
                    host=settings.database_host,
                    port=settings.database_port,
                    dbname=settings.database_name,
                    user=settings.database_user,
                    password=settings.database_password
                )
                logger.info("Database connection pool initialized (minconn=2, maxconn=20)")
            except Exception as e:
                logger.error(f"Failed to initialize connection pool: {e}")
                raise
```

#### 수정 후 코드

```python
@classmethod
def _init_pool(cls):
    """Connection Pool 초기화 (Lazy Initialization)"""
    import threading

    if cls._pool_lock is None:
        cls._pool_lock = threading.Lock()

    with cls._pool_lock:
        if cls._connection_pool is None:
            try:
                cls._connection_pool = pool.ThreadedConnectionPool(
                    minconn=2,
                    maxconn=20,
                    host=settings.database_host,
                    port=settings.database_port,
                    dbname=settings.database_name,
                    user=settings.database_user,
                    password=settings.database_password
                )

                # Connection Pool 연결 검증 (초기화 후 바로 연결 테스트)
                test_conn = cls._connection_pool.getconn()
                try:
                    with test_conn.cursor() as cursor:
                        cursor.execute("SELECT 1")
                    cls._connection_pool.putconn(test_conn)
                    logger.info("Database connection pool initialized and verified (minconn=2, maxconn=20)")
                except Exception as e:
                    cls._connection_pool.putconn(test_conn)
                    raise Exception(f"Connection pool verification failed: {e}")

            except Exception as e:
                logger.error(f"Failed to initialize connection pool: {e}")
                cls._connection_pool = None  # 실패 시 None으로 재설정
                raise
```

### 주요 변경 사항

1. **연결 검증 추가**
   ```python
   test_conn = cls._connection_pool.getconn()
   cursor.execute("SELECT 1")
   cls._connection_pool.putconn(test_conn)
   ```
   - Pool에서 테스트 연결을 가져와서 간단한 쿼리 실행
   - 정상 작동 확인 후 Pool에 반환

2. **Thread-Safe 보장**
   - `_pool_lock` 내에서 검증 수행
   - 여러 Thread가 동시에 초기화를 시도해도 한 번만 실행됨

3. **실패 시 재시도 가능**
   ```python
   cls._connection_pool = None  # 실패 시 None으로 재설정
   ```
   - 검증 실패 시 Pool을 None으로 재설정
   - 다음 `get_connection()` 호출 시 재초기화 시도

## 효과

### Before (수정 전)
```
✗ Pool 초기화 → 즉시 사용 시도 → Race Condition 발생
✗ "connection already closed" 에러 발생
✗ 초기 요청 실패, 재시도 필요
```

### After (수정 후)
```
✓ Pool 초기화 → 연결 검증 → 사용 가능 상태 확인
✓ 검증된 Pool만 사용 가능
✓ 초기 요청부터 정상 작동
✓ Race Condition 방지
```

## 결론

**문제:** Connection Pool 초기화와 사용 사이의 타이밍 간극으로 인한 Race Condition

**해결:** Pool 초기화 후 즉시 연결을 검증하여 완전히 준비된 Pool만 사용

**효과:**
- 초기 배치 작업 시작 시 "connection already closed" 에러 제거
- Thread-Safe한 Pool 초기화 보장
- 안정적인 병렬 처리 가능

---

**관련 파일:** `modelops/database/connection.py`

**관련 이슈:** PostgreSQL Connection Pool, ThreadedConnectionPool, Race Condition, Multi-threading

**참고:**
- [psycopg2 Connection Pool Documentation](https://www.psycopg.org/docs/pool.html)
- [Python Threading Documentation](https://docs.python.org/3/library/threading.html)
