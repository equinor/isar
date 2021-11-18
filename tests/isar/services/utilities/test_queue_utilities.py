from queue import Queue

import pytest

from isar.models.communication.messages import StartMissionMessages
from isar.models.communication.queues.queue_timeout_error import QueueTimeoutError
from isar.services.utilities.queue_utilities import QueueUtilities


class TestQueueUtilities:
    @pytest.mark.parametrize(
        "message, queue_timeout, expected_message, expected_timeout",
        [
            (
                StartMissionMessages.success(),
                10,
                StartMissionMessages.success(),
                False,
            ),
            (None, 1, None, True),
        ],
    )
    def test_check_queue_with_queue_size_one(
        self, message, queue_timeout, expected_message, expected_timeout
    ):
        test_queue = Queue(maxsize=1)
        if message is not None:
            test_queue.put(message)
            message = QueueUtilities.check_queue(test_queue, queue_timeout)
            assert message == expected_message
        else:
            with pytest.raises(QueueTimeoutError):
                QueueUtilities.check_queue(test_queue, queue_timeout)
