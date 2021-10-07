from http import HTTPStatus

import pytest

from isar.models.communication.messages import StartMissionMessages
from isar.services.utilities.scheduling_utilities import SchedulingUtilities
from tests.test_utilities.mock_models.mock_mission_definition import (
    mock_mission_definition,
)


class TestSchedulingUtilities:
    @pytest.mark.parametrize(
        "mock_return, mission, expected_output",
        [
            (
                [StartMissionMessages.success()],
                mock_mission_definition(),
                HTTPStatus.OK,
            ),
            (
                [StartMissionMessages.ack_timeout()],
                mock_mission_definition(),
                HTTPStatus.CONFLICT,
            ),
            (
                [StartMissionMessages.failed_to_create_mission()],
                mock_mission_definition(),
                HTTPStatus.CONFLICT,
            ),
        ],
    )
    def test_start_mission(
        self, mocker, scheduling_utilities, mock_return, mission, expected_output
    ):
        mocker.patch.object(
            SchedulingUtilities, "wait_on_start_ack", side_effect=mock_return
        )

        message, status_code = scheduling_utilities.start_mission(mission)

        assert status_code == expected_output
