"""
Data Warehouse 연결 테스트 스크립트
"""
import os
from dotenv import load_dotenv
from ETL.scripts.db_config import get_connection, get_db_url

# .env 파일 로드
load_dotenv()

print("=== Data Warehouse Connection Test ===\n")

# 환경 변수 확인
print("Environment Variables:")
print(f"  DW_HOST: {os.getenv('DW_HOST', 'NOT SET')}")
print(f"  DW_PORT: {os.getenv('DW_PORT', 'NOT SET')}")
print(f"  DW_NAME: {os.getenv('DW_NAME', 'NOT SET')}")
print(f"  DW_USER: {os.getenv('DW_USER', 'NOT SET')}")
print(f"  DW_PASSWORD: {'***' if os.getenv('DW_PASSWORD') else 'NOT SET'}")
print()

# 연결 URL 확인
print("Connection URL:")
try:
    url = get_db_url("datawarehouse")
    # 비밀번호 마스킹
    masked_url = url.replace(os.getenv('DW_PASSWORD', ''), '***')
    print(f"  {masked_url}")
    print()
except Exception as e:
    print(f"  Error: {e}\n")

# 실제 연결 테스트
print("Connection Test:")
try:
    conn = get_connection("datawarehouse")
    cursor = conn.cursor()
    cursor.execute("SELECT version();")
    version = cursor.fetchone()[0]
    print(f"  SUCCESS: Connected to PostgreSQL")
    print(f"  Version: {version[:50]}...")

    # 테이블 존재 확인
    cursor.execute("""
        SELECT table_name
        FROM information_schema.tables
        WHERE table_schema = 'public'
        ORDER BY table_name
        LIMIT 5
    """)
    tables = cursor.fetchall()
    if tables:
        print(f"\n  Sample tables:")
        for table in tables:
            print(f"    - {table[0]}")
    else:
        print(f"\n  No tables found in public schema")

    cursor.close()
    conn.close()
    print("\n[OK] Data Warehouse connection successful!")

except Exception as e:
    print(f"  FAILED: {e}")
    print("\n[ERROR] Data Warehouse connection failed!")
