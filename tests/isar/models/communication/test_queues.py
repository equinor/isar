from queue import Empty

import pytest

from isar.models.communication.queues import Queues, StatusQueue


class TestQueues:
    def test_queues(self):
        queues = Queues()
        assert queues.start_mission is not None
        assert (
            queues.start_mission.input is not None
            and queues.start_mission.input.maxsize == 1
        )
        assert (
            queues.start_mission.output is not None
            and queues.start_mission.output.maxsize == 1
        )
        assert queues.stop_mission is not None
        assert (
            queues.stop_mission.input is not None
            and queues.stop_mission.input.maxsize == 1
        )
        assert (
            queues.stop_mission.output is not None
            and queues.stop_mission.output.maxsize == 1
        )


def test_staus_queue_empty():
    status_queue: StatusQueue = StatusQueue()
    with pytest.raises(Empty):
        status_queue.check()


def test_status_queue_check():
    status_queue: StatusQueue = StatusQueue()
    status_queue.update("Test")
    assert status_queue.check() == "Test"
    assert status_queue._qsize() == 1


def test_status_queue_update():
    status_queue: StatusQueue = StatusQueue()
    status_queue.update("Test")
    status_queue.update("New Test")
    assert status_queue._qsize() == 1
    assert status_queue.check() == "New Test"
