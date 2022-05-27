import pytest

from isar.models.communication.queues.queue_io import QueueIO
from isar.models.communication.queues.queue_timeout_error import QueueTimeoutError
from isar.services.utilities.queue_utilities import QueueUtilities


def test_timeout_send_command(mocker, scheduling_utilities):
    mocker.patch.object(QueueUtilities, "check_queue", side_effect=QueueTimeoutError)
    q: QueueIO = QueueIO(input_size=1, output_size=1)
    with pytest.raises(QueueTimeoutError):
        scheduling_utilities._send_command(True, q)
    assert q.input.empty()
