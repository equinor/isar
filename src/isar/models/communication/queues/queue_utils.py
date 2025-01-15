import queue
from typing import Any

from isar.models.communication.queues.queue_io import QueueIO
from isar.models.communication.queues.status_queue import StatusQueue


def trigger_event(queueio: QueueIO, data: Any = None) -> None:
    queueio.input.put(data if data is not None else True)


def check_shared_state(queueio: StatusQueue) -> Any:
    try:
        return queueio.check()
    except queue.Empty:
        return None


def check_for_event(queueio: QueueIO) -> Any:
    try:
        return queueio.input.get(block=False)
    except queue.Empty:
        return None
