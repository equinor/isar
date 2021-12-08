from http import HTTPStatus

import pytest

from isar.models.communication.messages import StartMissionMessages
from isar.models.communication.queues.queue_timeout_error import QueueTimeoutError
from isar.services.utilities.queue_utilities import QueueUtilities
from isar.state_machine.states_enum import States
from tests.mocks.status import mock_mission_definition, mock_status


class TestSchedulingUtilities:
    @pytest.mark.parametrize(
        "mock_return, expected_ready",
        [
            (mock_status(mission_in_progress=False, current_state=States.Idle), True),
            (mock_status(mission_in_progress=True, current_state=States.Idle), False),
            (
                mock_status(mission_in_progress=False, current_state=States.Monitor),
                False,
            ),
            (mock_status(mission_in_progress=False, current_state=States.Off), False),
            (
                mock_status(mission_in_progress=False, current_state=States.Cancel),
                False,
            ),
            (mock_status(mission_in_progress=False, current_state=States.Send), False),
            (
                mock_status(mission_in_progress=True, current_state=States.Monitor),
                False,
            ),
            (mock_status(mission_in_progress=True, current_state=States.Off), False),
            (mock_status(mission_in_progress=True, current_state=States.Cancel), False),
            (mock_status(mission_in_progress=True, current_state=States.Send), False),
        ],
    )
    def test_ready_to_start_mission(
        self, mocker, scheduling_utilities, mock_return, expected_ready
    ):
        mocker.patch.object(QueueUtilities, "check_queue", return_value=mock_return)
        ready, response = scheduling_utilities.ready_to_start_mission()
        assert ready == expected_ready

    @pytest.mark.parametrize(
        "mock_return, mission, expected_output",
        [
            (
                [StartMissionMessages.success()],
                mock_mission_definition(),
                HTTPStatus.OK,
            ),
            (
                [QueueTimeoutError()],
                mock_mission_definition(),
                HTTPStatus.REQUEST_TIMEOUT,
            ),
        ],
    )
    def test_start_mission(
        self, mocker, scheduling_utilities, mock_return, mission, expected_output
    ):
        mocker.patch.object(QueueUtilities, "check_queue", side_effect=mock_return)

        message, status_code = scheduling_utilities.start_mission(mission)

        assert status_code == expected_output
