import os
from typing import Optional

try:
    from pydantic_settings import BaseSettings

    class Settings(BaseSettings):
        # Database (Data Warehouse - Primary DB for climate data)
        database_host: str = "localhost"
        database_port: int = 5555
        database_name: str = "datawarehouse"
        database_user: str = "skala"
        database_password: str = "skala1234"

        # Scheduler
        probability_schedule_month: int = 1
        probability_schedule_day: int = 1
        probability_schedule_hour: int = 2
        probability_schedule_minute: int = 0

        hazard_schedule_month: int = 1
        hazard_schedule_day: int = 1
        hazard_schedule_hour: int = 4
        hazard_schedule_minute: int = 0

        # Batch Processing
        parallel_workers: int = 4
        batch_size: int = 1000

        # NOTIFY
        notify_channel: str = "aiops_trigger"

        class Config:
            env_file = ".env"
            case_sensitive = False
            extra = "ignore"  # 정의되지 않은 환경변수 무시

    settings = Settings()

except ImportError:
    # pydantic_settings가 없으면 간단한 클래스 사용
    class Settings:
        database_host: str = os.getenv("DATABASE_HOST", "localhost")
        database_port: int = int(os.getenv("DATABASE_PORT", "5555"))
        database_name: str = os.getenv("DATABASE_NAME", "datawarehouse")
        database_user: str = os.getenv("DATABASE_USER", "skala")
        database_password: str = os.getenv("DATABASE_PASSWORD", "skala1234")

        probability_schedule_month: int = 1
        probability_schedule_day: int = 1
        probability_schedule_hour: int = 2
        probability_schedule_minute: int = 0

        hazard_schedule_month: int = 1
        hazard_schedule_day: int = 1
        hazard_schedule_hour: int = 4
        hazard_schedule_minute: int = 0

        parallel_workers: int = 4
        batch_size: int = 1000

        notify_channel: str = "aiops_trigger"

    settings = Settings()
