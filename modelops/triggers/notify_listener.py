import select
import psycopg2
import logging
from typing import Callable, Dict, Any
from ..config.settings import settings
from ..database.connection import DatabaseConnection

logger = logging.getLogger(__name__)


class NotifyListener:
    """PostgreSQL LISTEN/NOTIFY를 사용한 외부 트리거 리스너"""

    def __init__(self):
        self.conn = None
        self.handlers: Dict[str, Callable] = {}

    def register_handler(self, job_type: str, handler: Callable) -> None:
        """작업 타입별 핸들러 등록

        Args:
            job_type: 'probability' 또는 'hazard'
            handler: 실행할 핸들러 함수
        """
        self.handlers[job_type] = handler
        logger.info(f"Handler registered for job type: {job_type}")

    def start_listening(self) -> None:
        """NOTIFY 리스닝 시작"""
        connection_string = DatabaseConnection.get_connection_string()
        self.conn = psycopg2.connect(connection_string)
        self.conn.set_isolation_level(psycopg2.extensions.ISOLATION_LEVEL_AUTOCOMMIT)

        cursor = self.conn.cursor()
        cursor.execute(f"LISTEN {settings.notify_channel};")
        logger.info(f"Listening on channel: {settings.notify_channel}")

        print(f"🎧 Listening for PostgreSQL NOTIFY on channel '{settings.notify_channel}'...")

        while True:
            if select.select([self.conn], [], [], 5) == ([], [], []):
                continue
            else:
                self.conn.poll()
                while self.conn.notifies:
                    notify = self.conn.notifies.pop(0)
                    self._handle_notify(notify.payload)

    def _handle_notify(self, payload: str) -> None:
        """NOTIFY 메시지 처리

        Payload 형식: 'probability' 또는 'hazard'
        """
        logger.info(f"Received NOTIFY: {payload}")

        if payload in self.handlers:
            try:
                logger.info(f"Executing handler for: {payload}")
                self.handlers[payload]()
                logger.info(f"Handler completed for: {payload}")
            except Exception as e:
                logger.error(f"Error executing handler for {payload}: {e}")
        else:
            logger.warning(f"No handler registered for job type: {payload}")

    def stop_listening(self) -> None:
        """리스닝 중지"""
        if self.conn:
            self.conn.close()
            logger.info("Stopped listening")
