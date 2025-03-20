from queue import Empty, Queue
from typing import Optional, TypeVar

from isar.models.communication.queues.status_queue import StatusQueue

T = TypeVar("T")


def trigger_event_without_data(queue: Queue[bool]) -> None:
    queue.put(True)


def trigger_event(queue: Queue[T], data: T) -> None:
    queue.put(data)


def check_shared_state(queue: StatusQueue[T]) -> Optional[T]:
    try:
        return queue.check()
    except Empty:
        return None


def update_shared_state(queue: StatusQueue[T], data: T) -> None:
    queue.update(data)


def check_for_event(queue: Queue[T]) -> Optional[T]:
    try:
        return queue.get(block=False)
    except Empty:
        return None


def check_for_event_without_consumption(queue: Queue[T]) -> bool:
    return (
        queue.qsize() != 0
    )  # Queue size is not reliable, but should be sufficient for this case
