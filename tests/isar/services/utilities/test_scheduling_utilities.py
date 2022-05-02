from http import HTTPStatus

import pytest

from isar.models.communication.messages import StartMissionMessages
from isar.models.communication.queues.queue_timeout_error import QueueTimeoutError
from isar.services.utilities.queue_utilities import QueueUtilities
from isar.state_machine.states_enum import States
from tests.mocks.mission_definition import MockMissionDefinition


class TestSchedulingUtilities:
    @pytest.mark.parametrize(
        "mock_return, expected_ready",
        [
            ((False, States.Idle), True),
            ((True, States.Idle), False),
            (
                (False, States.Monitor),
                False,
            ),
            ((False, States.Off), False),
            (
                (False, States.Finalize),
                False,
            ),
            (
                (False, States.InitiateStep),
                False,
            ),
            (
                (True, States.Monitor),
                False,
            ),
            ((True, States.Off), False),
            (
                (True, States.Finalize),
                False,
            ),
            (
                (True, States.InitiateStep),
                False,
            ),
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
                MockMissionDefinition.default_mission,
                HTTPStatus.OK,
            ),
            (
                [QueueTimeoutError()],
                MockMissionDefinition.default_mission,
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
