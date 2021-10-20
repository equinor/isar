from dataclasses import asdict
from http import HTTPStatus

import pytest

from isar.mission_planner.local_planner import LocalPlanner
from isar.mission_planner.mission_planner_interface import MissionPlannerError
from isar.models.communication.messages import StartMissionMessages
from isar.services.utilities.scheduling_utilities import SchedulingUtilities
from tests.api.apis.supervisor.test_supervisor_routes import mock_start_mission
from tests.test_utilities.mock_models.mock_mission_definition import (
    mock_mission_definition,
)


@pytest.mark.parametrize(
    "mission_id, mock_get_mission, mock_get_mission_side_effect,"
    "mock_start, expected_output, expected_status_code",
    [
        (
            12345,
            mock_mission_definition(),
            None,
            mock_start_mission(HTTPStatus.OK),
            StartMissionMessages.success(),
            HTTPStatus.OK,
        ),
        (
            12345,
            None,
            MissionPlannerError,
            mock_start_mission(HTTPStatus.OK),
            StartMissionMessages.mission_not_found(),
            HTTPStatus.NOT_FOUND,
        ),
    ],
)
@pytest.mark.unittest
def test_start_mission(
    client,
    access_token,
    mocker,
    mission_id,
    mock_get_mission,
    mock_get_mission_side_effect,
    mock_start,
    expected_output,
    expected_status_code,
):
    mocker.patch.object(
        LocalPlanner,
        "get_mission",
        return_value=mock_get_mission,
        side_effect=mock_get_mission_side_effect,
    )
    mocker.patch.object(
        SchedulingUtilities,
        "start_mission",
        return_value=mock_start,
    )

    response = client.get(
        "/schedule/start-mission",
        headers={"Authorization": "Bearer {}".format(access_token)},
        query_string={"mission_id": mission_id},
    )
    assert response.json == asdict(expected_output)
    assert response.status_code == expected_status_code
