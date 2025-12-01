"""
SKALA Physical Risk AI System - 데이터베이스 설정
이중 데이터베이스 설정을 위한 연결 유틸리티

최종 수정일: 2025-11-21
버전: v02
"""

import os
from pathlib import Path
from typing import Literal

import psycopg2
from psycopg2.extensions import connection as Connection
from dotenv import load_dotenv

# .env 파일 로드 (프로젝트 루트에서)
env_path = Path(__file__).parent.parent.parent / ".env"
load_dotenv(dotenv_path=env_path, override=True)

DatabaseType = Literal["datawarehouse", "application", "legacy"]


def get_connection(db_type: DatabaseType = "datawarehouse") -> Connection:
    """
    Get database connection based on type

    Args:
        db_type: Type of database connection
            - "datawarehouse": FastAPI용 데이터 웨어하우스 (기후 데이터)
            - "application": Spring Boot용 애플리케이션 DB (사용자/사업장)
            - "legacy": 기존 단일 DB (마이그레이션용)

    Returns:
        psycopg2 connection object

    Raises:
        ValueError: Invalid database type
        psycopg2.Error: Connection failed
    """
    if db_type == "datawarehouse":
        return psycopg2.connect(
            host=os.getenv("DW_HOST", "localhost"),
            port=os.getenv("DW_PORT", "5433"),
            dbname=os.getenv("DW_NAME", "skala_datawarehouse"),
            user=os.getenv("DW_USER", "skala_dw_user"),
            password=os.getenv("DW_PASSWORD", "")
        )

    elif db_type == "application":
        return psycopg2.connect(
            host=os.getenv("APP_HOST", "localhost"),
            port=os.getenv("APP_PORT", "5432"),
            dbname=os.getenv("APP_NAME", "skala_application"),
            user=os.getenv("APP_USER", "skala_app_user"),
            password=os.getenv("APP_PASSWORD", "")
        )

    elif db_type == "legacy":
        # For migration from single DB to dual DB
        return psycopg2.connect(
            host=os.getenv("DB_HOST", "localhost"),
            port=os.getenv("DB_PORT", "5432"),
            dbname=os.getenv("DB_NAME", "skala_physical_risk"),
            user=os.getenv("DB_USER", "skala_dev"),
            password=os.getenv("DB_PASSWORD", "")
        )

    else:
        raise ValueError(f"Invalid database type: {db_type}. Must be 'datawarehouse', 'application', or 'legacy'")


def get_db_url(db_type: DatabaseType = "datawarehouse") -> str:
    """
    Get database connection URL for SQLAlchemy

    Args:
        db_type: Type of database

    Returns:
        PostgreSQL connection URL string
    """
    if db_type == "datawarehouse":
        host = os.getenv("DW_HOST", "localhost")
        port = os.getenv("DW_PORT", "5433")
        dbname = os.getenv("DW_NAME", "skala_datawarehouse")
        user = os.getenv("DW_USER", "skala_dw_user")
        password = os.getenv("DW_PASSWORD", "")

    elif db_type == "application":
        host = os.getenv("APP_HOST", "localhost")
        port = os.getenv("APP_PORT", "5432")
        dbname = os.getenv("APP_NAME", "skala_application")
        user = os.getenv("APP_USER", "skala_app_user")
        password = os.getenv("APP_PASSWORD", "")

    elif db_type == "legacy":
        host = os.getenv("DB_HOST", "localhost")
        port = os.getenv("DB_PORT", "5432")
        dbname = os.getenv("DB_NAME", "skala_physical_risk")
        user = os.getenv("DB_USER", "skala_dev")
        password = os.getenv("DB_PASSWORD", "")

    else:
        raise ValueError(f"Invalid database type: {db_type}")

    return f"postgresql://{user}:{password}@{host}:{port}/{dbname}"


# Backwards compatibility for existing scripts
def get_db_connection():
    """
    Legacy function for existing scripts
    Returns connection to datawarehouse by default
    """
    return get_connection("datawarehouse")


if __name__ == "__main__":
    # Test connections
    print("Testing database connections...")

    # Test datawarehouse
    try:
        conn = get_connection("datawarehouse")
        cursor = conn.cursor()
        cursor.execute("SELECT version();")
        version = cursor.fetchone()[0]
        print(f"✅ Datawarehouse: {version}")
        cursor.close()
        conn.close()
    except Exception as e:
        print(f"❌ Datawarehouse: {e}")

    # Test application
    try:
        conn = get_connection("application")
        cursor = conn.cursor()
        cursor.execute("SELECT version();")
        version = cursor.fetchone()[0]
        print(f"✅ Application: {version}")
        cursor.close()
        conn.close()
    except Exception as e:
        print(f"❌ Application: {e}")
