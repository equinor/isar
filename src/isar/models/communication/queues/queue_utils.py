from queue import Empty
from typing import Any, Optional, TypeVar

from isar.models.communication.queues.events import Event

T = TypeVar("T")


def trigger_event_without_data(event: Event[Any]) -> None:
    event.put(True)


def trigger_event(event: Event[T], data: T) -> None:
    event.put(data)


def check_shared_state(event: Event[T]) -> Optional[T]:
    try:
        return event.check()
    except Empty:
        return None


def update_shared_state(event: Event[T], data: T) -> None:
    event.update(data)


def check_for_event(event: Event[T]) -> Optional[T]:
    try:
        return event.get(block=False)
    except Empty:
        return None


def check_for_event_without_consumption(event: Event[T]) -> bool:
    return (
        event.qsize() != 0
    )  # Queue size is not reliable, but should be sufficient for this case
