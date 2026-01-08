import sys
from typing import List
from datetime import datetime
import logging
import queue
import sqlite3

class LogDB:
    def __init__(
        self,logs_file: str):
        self.log_file = logs_file
        self.db = sqlite3.connect(logs_file)
        self.cursor = self.db.cursor()
        self.create_schema()
        #self.clear_logs()
    
    def create_schema(self):
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS logs (
                time TEXT NOT NULL,
                message TEXT NOT NULL
                )""")
    
    def clear_logs(self, by_time:datetime|None = None, by_count:int|None = None):
        WHERE_CLOUSE = ""
        if by_time:
            WHERE_CLOUSE = "WHERE time < '{}'".format(by_time.isoformat())
        if by_count:
            raise Exception("Not implemented")
        self.cursor.execute(f"""
            DELETE FROM logs {WHERE_CLOUSE}
            """)
        self.db.commit()

    def add_log(self, message: str):
        self.cursor.execute("""
            INSERT INTO logs (time, message)
            VALUES (?, ?)
            """, (datetime.now().isoformat(), message))
        self.db.commit()

    def fetch_message(self, by_time:datetime|None = None, by_count:int|None = None):
        WHERE_CLOUSE = ""
        if by_time:
            WHERE_CLOUSE = "WHERE time < '{}'".format(by_time.isoformat())
        if by_count:
            raise Exception("Not implemented")
        self.cursor.execute(f"""
            SELECT message FROM logs {WHERE_CLOUSE}
            """)
        res = self.cursor.fetchall()
        res = list(map(lambda x: x[0],res))
        return res
    

class ListHandler(logging.Handler):
    """Custom logging handler that stores log messages in a list."""

    def __init__(
        self,
        logs_file: str,
        MAX_MSGS: int = 1000,
        MAX_TIME_SEC: int = 600,
    ):
        super().__init__()
        self.log_q = logs_file
        self.db = LogDB(logs_file)
        
        self.messages = []
        self.max_messages = MAX_MSGS
        self.max_tme_sec = MAX_TIME_SEC
        self.last_log_time = None

    def emit(self, record):
        """Store formatted log messages in the list."""
        current_time = datetime.now()
        # if self.last_log_time:
        #     if (current_time - self.last_log_time).total_seconds() >= self.max_tme_sec:
        #         self.clear_log()
        msg = self.format(record)
        # self.log_messages.append(msg)
        self.db.add_log(msg)
        self.last_log_time = current_time

    def clear_log(self):
        self.db.clear_logs()
        self.messages.clear()

    def get_messages(self) -> List[str]:
        msgs = self.db.fetch_message()
        self.db.clear_logs()
        self.messages.extend(msgs)
        if len(self.messages) > self.max_messages:
            self.messages = self.messages[-self.max_messages :]
        return list(self.messages)


logger = logging.getLogger()
logging_cache = ListHandler("/tmp/sim_log.db")
stream_handler = logging.StreamHandler(sys.stdout)
logger.addHandler(logging_cache)
logger.addHandler(stream_handler)
logger.setLevel(logging.INFO)
