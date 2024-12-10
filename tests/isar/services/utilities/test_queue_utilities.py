from queue import Queue

import pytest

from isar.models.communication.queues.queue_timeout_error import QueueTimeoutError
from isar.services.utilities.queue_utilities import QueueUtilities


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
        test_queue: Queue = Queue(maxsize=1)
        if message is not None:
            test_queue.put(message)
            message = QueueUtilities.check_queue(test_queue, queue_timeout)
            assert message == expected_message
        else:
            with pytest.raises(QueueTimeoutError):
                QueueUtilities.check_queue(test_queue, queue_timeout)

    def test_clear_queue(self) -> None:
        test_queue: Queue = Queue(maxsize=2)
        test_queue.put(1)
        test_queue.put(2)
        QueueUtilities.clear_queue(test_queue)
        assert test_queue.empty()
