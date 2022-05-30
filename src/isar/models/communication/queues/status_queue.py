from collections import deque
from queue import Empty, Queue
from typing import Any


class StatusQueue(Queue):
    def __init__(self) -> None:
        super().__init__()

    def check(self) -> Any:
        if not self._qsize():
            raise Empty
        with self.mutex:
            l = list(self.queue)
            return l.pop()

    def update(self, item: Any):
        with self.mutex:
            self.queue = deque()
            self.queue.append(item)
