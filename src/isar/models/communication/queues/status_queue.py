from collections import deque
from queue import Empty, Queue
from typing import TypeVar

T = TypeVar("T")


class StatusQueue(Queue[T]):
    def __init__(self) -> None:
        super().__init__()

    def check(self) -> T:
        if not self._qsize():
            raise Empty
        with self.mutex:
            queueList = list(self.queue)
            return queueList.pop()

    def update(self, item: T):
        with self.mutex:
            self.queue: deque[T] = deque()
            self.queue.append(item)
