from queue import Empty, Queue
from typing import Any

from isar.models.communication.queues.status_queue import StatusQueue


def trigger_event(queue: Queue, data: Any = None) -> None:
    queue.put(data if data is not None else True)


def check_shared_state(queue: StatusQueue) -> Any:
    try:
        return queue.check()
    except Empty:
        return None


def update_shared_state(queue: StatusQueue, data: Any = None) -> None:
    queue.update(data if data is not None else True)


def check_for_event(queue: Queue) -> Any:
    try:
        return queue.get(block=False)
    except Empty:
        return None
