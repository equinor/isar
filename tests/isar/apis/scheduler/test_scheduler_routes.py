from http import HTTPStatus
from typing import Optional, Tuple

import pytest

from isar.apis.security.authentication import Authenticator
from isar.mission_planner.local_planner import LocalPlanner
from isar.mission_planner.mission_planner_interface import MissionPlannerError
from isar.models.communication.queues.queue_timeout_error import QueueTimeoutError
from isar.services.utilities.queue_utilities import QueueUtilities
from isar.services.utilities.scheduling_utilities import SchedulingUtilities
from isar.state_machine.states_enum import States
from tests.mocks.mission_definition import MockMissionDefinition


def mock_check_queue(was_mission_started, state_at_request):
    mock_return_1 = was_mission_started, state_at_request
    if was_mission_started or state_at_request != "idle":
        mock_return_2 = False
    else:
        mock_return_2 = True

    return [mock_return_1, mock_return_2]


class TestSchedulerRoutes:
    @pytest.mark.parametrize(
        "mission_id, mock_get_mission, expected_exception,"
        "mock_get_state, mock_start_mission_side_effect, expected_status_code",
        [
            (
                12345,
                MockMissionDefinition.default_mission,
                MissionPlannerError,
                States.Idle,
                None,
                HTTPStatus.INTERNAL_SERVER_ERROR,
            ),
            (
                1,
                MockMissionDefinition.default_mission,
                None,
                States.Idle,
                QueueTimeoutError,
                HTTPStatus.REQUEST_TIMEOUT,
            ),
            (
                1,
                MockMissionDefinition.default_mission,
                None,
                States.Monitor,
                True,
                HTTPStatus.CONFLICT,
            ),
            (
                1,
                MockMissionDefinition.default_mission,
                None,
                States.Idle,
                QueueTimeoutError,
                HTTPStatus.REQUEST_TIMEOUT,
            ),
            (
                1,
                MockMissionDefinition.default_mission,
                None,
                States.Idle,
                None,
                HTTPStatus.OK,
            ),
        ],
    )
    def test_start_mission(
        self,
        client,
        access_token,
        mocker,
        mission_id,
        mock_get_mission,
        expected_exception,
        mock_get_state,
        mock_start_mission_side_effect,
        expected_status_code,
    ):
        mocker.patch.object(
            LocalPlanner,
            "get_mission",
            return_value=mock_get_mission,
            side_effect=expected_exception,
        )

        mocker.patch.object(
            SchedulingUtilities,
            "get_state",
            return_value=mock_get_state,
        )

        mocker.patch.object(
            SchedulingUtilities,
            "start_mission",
            side_effect=mock_start_mission_side_effect,
        )

        response = client.post(
            f"schedule/start-mission?ID={mission_id}",
            headers={"Authorization": "Bearer {}".format(access_token)},
        )

        assert response.status_code == expected_status_code

    @pytest.mark.parametrize(
        "state, mock_return, expected_status_code",
        [
            (
                States.Monitor,
                QueueTimeoutError(),
                HTTPStatus.REQUEST_TIMEOUT,
            ),
            (
                States.InitiateStep,
                None,
                HTTPStatus.OK,
            ),
            (
                States.Idle,
                None,
                HTTPStatus.CONFLICT,
            ),
        ],
    )
    def test_stop_mission(
        self,
        client,
        access_token,
        mocker,
        state,
        mock_return,
        expected_status_code,
    ):
        mocker.patch.object(SchedulingUtilities, "get_state", return_value=state)
        mocker.patch.object(
            SchedulingUtilities, "stop_mission", side_effect=mock_return
        )

        response = client.post(
            "/schedule/stop-mission",
            headers={"Authorization": "Bearer {}".format(access_token)},
        )

        assert response.status_code == expected_status_code

    @pytest.mark.parametrize(
        "mock_start_mission, mock_get_state,expected_status_code,request_params",
        [
            (
                None,
                States.Idle,
                HTTPStatus.OK,
                {"x": 1, "y": 1, "z": 1, "orientation": "0,0,0,1"},
            ),
            (
                QueueTimeoutError,
                States.Idle,
                HTTPStatus.REQUEST_TIMEOUT,
                {"x": 1, "y": 1, "z": 1, "orientation": "0,0,0,1"},
            ),
            (
                None,
                States.Monitor,
                HTTPStatus.CONFLICT,
                {"x": 1, "y": 1, "z": 1, "orientation": "0,0,0,1"},
            ),
            (
                None,
                States.Idle,
                HTTPStatus.UNPROCESSABLE_ENTITY,
                {"x": None, "y": 1, "z": 1, "orientation": "0,0,0,1"},
            ),
        ],
    )
    def test_schedule_drive_to(
        self,
        client,
        access_token,
        mock_start_mission,
        mock_get_state,
        mocker,
        expected_status_code,
        request_params,
    ):
        mocker.patch.object(
            SchedulingUtilities, "get_state", return_value=mock_get_state
        )

        mocker.patch.object(
            SchedulingUtilities, "start_mission", side_effect=mock_start_mission
        )
        mocker.patch.object(Authenticator, "should_authenticate", return_value=False)

        query_string = (
            f"x-value={request_params['x']}&"
            f"y-value={request_params['y']}&"
            f"z-value={request_params['z']}&"
            f"quaternion={request_params['orientation'][0]}&"
            f"quaternion={request_params['orientation'][2]}&"
            f"quaternion={request_params['orientation'][4]}&"
            f"quaternion={request_params['orientation'][6]}"
        )

        response = client.post(
            f"/schedule/drive-to?{query_string}",
            headers={"Authorization": "Bearer {}".format(access_token)},
        )

        assert response.status_code == expected_status_code
