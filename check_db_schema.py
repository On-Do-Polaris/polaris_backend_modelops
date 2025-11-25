"""
Data Warehouse 스키마 확인 스크립트
"""
import os
from dotenv import load_dotenv
from ETL.scripts.db_config import get_connection

# .env 파일 로드
load_dotenv()

print("=== Data Warehouse Schema Check ===\n")

try:
    conn = get_connection("datawarehouse")
    cursor = conn.cursor()

    # 모든 테이블 조회
    print("1. All Tables in Database:")
    cursor.execute("""
        SELECT table_name, pg_size_pretty(pg_total_relation_size(quote_ident(table_name)::regclass)) as size
        FROM information_schema.tables
        WHERE table_schema = 'public'
        ORDER BY table_name
    """)
    tables = cursor.fetchall()

    if tables:
        for i, (table_name, size) in enumerate(tables, 1):
            print(f"   {i:2d}. {table_name:40s} ({size})")
        print(f"\n   Total: {len(tables)} tables\n")
    else:
        print("   No tables found\n")

    # 주요 테이블들의 컬럼 정보 확인
    important_tables = [
        'probability_results',
        'hazard_results',
        'climate_data',
        'api_buildings',
        'api_coastal_infrastructure'
    ]

    print("2. Important Tables Schema:")
    for table in important_tables:
        cursor.execute("""
            SELECT column_name, data_type, character_maximum_length, is_nullable
            FROM information_schema.columns
            WHERE table_schema = 'public' AND table_name = %s
            ORDER BY ordinal_position
        """, (table,))
        columns = cursor.fetchall()

        if columns:
            print(f"\n   Table: {table}")
            print(f"   {'Column':<30s} {'Type':<20s} {'Nullable':<10s}")
            print(f"   {'-'*60}")
            for col_name, data_type, max_len, nullable in columns:
                type_str = f"{data_type}" + (f"({max_len})" if max_len else "")
                print(f"   {col_name:<30s} {type_str:<20s} {nullable:<10s}")

    # 인덱스 확인
    print("\n\n3. Indexes:")
    cursor.execute("""
        SELECT
            tablename,
            indexname,
            indexdef
        FROM pg_indexes
        WHERE schemaname = 'public'
        ORDER BY tablename, indexname
    """)
    indexes = cursor.fetchall()

    if indexes:
        current_table = None
        for tablename, indexname, indexdef in indexes:
            if current_table != tablename:
                print(f"\n   Table: {tablename}")
                current_table = tablename
            print(f"      - {indexname}")

    cursor.close()
    conn.close()

    print("\n[OK] Schema check completed!")

except Exception as e:
    print(f"[ERROR] Failed to check schema: {e}")
