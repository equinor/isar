import pytest

from isar.models.events import Event, EventTimeoutError


class TestQueueUtilities:
    @pytest.mark.parametrize(
        "message, queue_timeout, expected_message",
        [
            (
                "Test",
                10,
                "Test",
            ),
            (None, 1, None),
        ],
    )
    def test_check_queue_with_queue_size_one(
        self, message, queue_timeout, expected_message
    ) -> None:
        test_event: Event = Event()
        if message is not None:
            test_event.put(message)
            message = test_event.consume_event(timeout=queue_timeout)
            assert message == expected_message
        else:
            with pytest.raises(EventTimeoutError):
                test_event.consume_event(timeout=queue_timeout)

    def test_clear_queue(self) -> None:
        test_event: Event = Event()
        test_event.put(1)
        test_event.clear_event()
        assert test_event.empty()
