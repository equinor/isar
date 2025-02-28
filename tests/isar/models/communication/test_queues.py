from queue import Empty

import pytest

from isar.models.communication.queues.events import Events, StatusQueue


class TestQueues:
    def test_queues(self) -> None:
        queues: Events = Events()
        assert queues.api_requests.start_mission is not None
        assert (
            queues.api_requests.start_mission.input is not None
            and queues.api_requests.start_mission.input.maxsize == 1
        )
        assert (
            queues.api_requests.start_mission.output is not None
            and queues.api_requests.start_mission.output.maxsize == 1
        )
        assert queues.api_requests.stop_mission is not None
        assert (
            queues.api_requests.stop_mission.input is not None
            and queues.api_requests.stop_mission.input.maxsize == 1
        )
        assert (
            queues.api_requests.stop_mission.output is not None
            and queues.api_requests.stop_mission.output.maxsize == 1
        )


def test_staus_queue_empty() -> None:
    status_queue: StatusQueue = StatusQueue()
    with pytest.raises(Empty):
        status_queue.check()


def test_status_queue_check() -> None:
    status_queue: StatusQueue = StatusQueue()
    status_queue.update("Test")
    assert status_queue.check() == "Test"
    assert status_queue._qsize() == 1


def test_status_queue_update() -> None:
    status_queue: StatusQueue = StatusQueue()
    status_queue.update("Test")
    status_queue.update("New Test")
    assert status_queue._qsize() == 1
    assert status_queue.check() == "New Test"
