"""
데이터베이스 테이블 생성 스크립트
E, V, AAL 결과 저장 테이블 생성
"""

import psycopg2
import os
from pathlib import Path

# .env 파일 로드
from dotenv import load_dotenv
load_dotenv()

def create_tables():
    """테이블 생성"""
    # 데이터베이스 연결
    conn = psycopg2.connect(
        host=os.getenv('DW_HOST', 'localhost'),
        port=os.getenv('DW_PORT', '5433'),
        dbname=os.getenv('DW_NAME', 'skala_datawarehouse'),
        user=os.getenv('DW_USER', 'skala_dw_user'),
        password=os.getenv('DW_PASSWORD', '1234')
    )

    try:
        cursor = conn.cursor()

        # SQL 파일 읽기
        sql_file = Path(__file__).parent / 'modelops' / 'database' / 'schema_extensions.sql'
        with open(sql_file, 'r', encoding='utf-8') as f:
            sql = f.read()

        print("테이블 생성 중...")
        cursor.execute(sql)
        conn.commit()

        print("✓ 테이블 생성 완료!")

        # 생성된 테이블 확인
        cursor.execute("""
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public'
            AND table_name IN ('exposure_results', 'vulnerability_results', 'aal_scaled_results')
            ORDER BY table_name
        """)

        tables = cursor.fetchall()
        print("\n생성된 테이블:")
        for table in tables:
            print(f"  - {table[0]}")

    except Exception as e:
        print(f"✗ 에러 발생: {e}")
        conn.rollback()
        raise
    finally:
        cursor.close()
        conn.close()


if __name__ == '__main__':
    create_tables()
