import pytest

from isar.models.events import Event, Events


@pytest.mark.parametrize("command", ["start_mission", "stop_mission"])
def test_api_command_queues_hold_one_message(command: str) -> None:
    events = Events()

    api_event = getattr(events.api_requests, command)

    assert (api_event.request.maxsize, api_event.response.maxsize) == (1, 1)


def test_status_queue_empty() -> None:
    status_event: Event = Event("test")

    value = status_event.check()

    assert value is None


def test_status_event_check() -> None:
    status_event: Event = Event("test")
    status_event.update("Test")

    value = status_event.check()

    assert value == "Test"
    assert status_event._qsize() == 1


def test_status_event_update() -> None:
    status_event: Event = Event("test")
    status_event.update("Test")

    status_event.update("New Test")

    assert status_event._qsize() == 1
    assert status_event.check() == "New Test"
