from isar.models.events import Event, Events


class TestEvents:
    def test_events(self) -> None:
        events: Events = Events()
        assert events.api_requests.start_mission is not None
        assert (
            events.api_requests.start_mission.request is not None
            and events.api_requests.start_mission.request.maxsize == 1
        )
        assert (
            events.api_requests.start_mission.response is not None
            and events.api_requests.start_mission.response.maxsize == 1
        )
        assert events.api_requests.stop_mission is not None
        assert (
            events.api_requests.stop_mission.request is not None
            and events.api_requests.stop_mission.request.maxsize == 1
        )
        assert (
            events.api_requests.stop_mission.response is not None
            and events.api_requests.stop_mission.response.maxsize == 1
        )


def test_staus_queue_empty() -> None:
    status_event: Event = Event()
    assert status_event.check() is None


def test_status_event_check() -> None:
    status_event: Event = Event()
    status_event.update("Test")
    assert status_event.check() == "Test"
    assert status_event._qsize() == 1


def test_status_event_update() -> None:
    status_event: Event = Event()
    status_event.update("Test")
    status_event.update("New Test")
    assert status_event._qsize() == 1
    assert status_event.check() == "New Test"
