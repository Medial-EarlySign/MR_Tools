import collections
import sys
from typing import List
from datetime import datetime
import logging
import multiprocessing
import queue


def clear_queue_to_size(q: multiprocessing.Queue, max_len: int):
    """Remove all items from a queue.Queue()"""
    while q.qsize() >= max_len:
        try:
            q.get_nowait()  # Remove item
        except queue.Empty:
            break  # Queue is empty


class ListHandler(logging.Handler):
    """Custom logging handler that stores log messages in a list."""

    def __init__(
        self,
        queue: multiprocessing.Queue,
        MAX_MSGS: int = 1000,
        MAX_TIME_SEC: int = 600,
    ):
        super().__init__()
        self.log_q = queue
        self.messages = []
        self.max_messages = MAX_MSGS
        self.max_tme_sec = MAX_TIME_SEC
        self.last_log_time = None

    def emit(self, record):
        """Store formatted log messages in the list."""
        current_time = datetime.now()
        if self.last_log_time:
            if (current_time - self.last_log_time).total_seconds() >= self.max_tme_sec:
                self.clear_log()
        if self.log_q.qsize() > self.max_messages:
            clear_queue_to_size(self.log_q, self.max_messages)
        msg = self.format(record)
        # self.log_messages.append(msg)
        self.log_q.put(msg)
        self.last_log_time = current_time

    def clear_log(self):
        clear_queue_to_size(self.log_q, 1)
        self.messages.clear()

    def get_messages(self) -> List[str]:
        while self.log_q.qsize() >= 1:
            try:
                self.messages.append(self.log_q.get())
            except queue.Empty:
                break  # Queue is empty
        if len(self.messages) > self.max_messages:
            self.messages = self.messages[-self.max_messages :]
        return list(self.messages)


que_log = multiprocessing.Manager().Queue()
logger = logging.getLogger()
logging_cache = ListHandler(que_log)
stream_handler = logging.StreamHandler(sys.stdout)
logger.addHandler(logging_cache)
logger.addHandler(stream_handler)
logger.setLevel(logging.INFO)
