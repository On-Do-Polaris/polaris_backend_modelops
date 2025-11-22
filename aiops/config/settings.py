from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    # Database
    database_host: str = "localhost"
    database_port: int = 5432
    database_name: str = "climate_risk_db"
    database_user: str = "postgres"
    database_password: str = ""

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


settings = Settings()
