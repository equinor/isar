import json
from http import HTTPStatus
from typing import Optional, Tuple

import pytest

from isar.apis.security.authentication import Authenticator
from isar.mission_planner.local_planner import LocalPlanner
from isar.mission_planner.mission_planner_interface import MissionPlannerError
from isar.models.communication.messages import (
    StartMessage,
    StartMissionMessages,
    StopMissionMessages,
)
from isar.models.communication.messages.stop_message import StopMessage
from isar.models.communication.queues.queue_timeout_error import QueueTimeoutError
from isar.services.utilities.queue_utilities import QueueUtilities
from isar.services.utilities.scheduling_utilities import SchedulingUtilities
from tests.mocks.mission_definition import MockMissionDefinition


def mock_check_queue(was_mission_started, state_at_request):
    mock_return_1 = was_mission_started, state_at_request
    if was_mission_started or state_at_request != "idle":
        mock_return_2 = StartMissionMessages.mission_in_progress()
    else:
        mock_return_2 = StartMissionMessages.success()

    return [mock_return_1, mock_return_2]


def mock_ready_to_start_mission(
    status_code: int,
) -> Tuple[bool, Optional[Tuple[StartMessage, int]]]:
    if status_code == HTTPStatus.OK:
        return True, None
    elif status_code == HTTPStatus.REQUEST_TIMEOUT:
        return (
            False,
            (StartMissionMessages.queue_timeout(), HTTPStatus.REQUEST_TIMEOUT),
        )
    elif status_code == HTTPStatus.CONFLICT:
        return (
            False,
            (StartMissionMessages.mission_in_progress(), HTTPStatus.CONFLICT),
        )
    return True, None


def mock_start_mission(status_code: int) -> Tuple[StartMessage, int]:
    if status_code == HTTPStatus.OK:
        return StartMissionMessages.success(), HTTPStatus.OK
    elif status_code == HTTPStatus.REQUEST_TIMEOUT:
        return (
            StartMissionMessages.queue_timeout(),
            HTTPStatus.REQUEST_TIMEOUT,
        )
    return StartMissionMessages.success(), HTTPStatus.OK


class TestSchedulerRoutes:
    @pytest.mark.parametrize(
        "mission_id, mock_get_mission, expected_exception,"
        "mock_ready_to_start, mock_start, expected_status_code",
        [
            (
                12345,
                MockMissionDefinition.default_mission,
                MissionPlannerError,
                mock_ready_to_start_mission(HTTPStatus.OK),
                mock_start_mission(HTTPStatus.OK),
                HTTPStatus.INTERNAL_SERVER_ERROR,
            ),
            (
                1,
                MockMissionDefinition.default_mission,
                None,
                mock_ready_to_start_mission(HTTPStatus.REQUEST_TIMEOUT),
                mock_start_mission(HTTPStatus.OK),
                HTTPStatus.REQUEST_TIMEOUT,
            ),
            (
                1,
                MockMissionDefinition.default_mission,
                None,
                mock_ready_to_start_mission(HTTPStatus.CONFLICT),
                mock_start_mission(HTTPStatus.OK),
                HTTPStatus.CONFLICT,
            ),
            (
                1,
                MockMissionDefinition.default_mission,
                None,
                mock_ready_to_start_mission(HTTPStatus.OK),
                mock_start_mission(HTTPStatus.REQUEST_TIMEOUT),
                HTTPStatus.REQUEST_TIMEOUT,
            ),
            (
                1,
                MockMissionDefinition.default_mission,
                None,
                mock_ready_to_start_mission(HTTPStatus.OK),
                mock_start_mission(HTTPStatus.OK),
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
        mock_ready_to_start,
        mock_start,
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
            "ready_to_start_mission",
            return_value=mock_ready_to_start,
        )
        mocker.patch.object(
            SchedulingUtilities,
            "start_mission",
            return_value=mock_start,
        )

        response = client.post(
            f"schedule/start-mission?ID={mission_id}",
            headers={"Authorization": "Bearer {}".format(access_token)},
        )

        assert response.status_code == expected_status_code

    @pytest.mark.parametrize(
        "mock_return, expected_status_code",
        [
            (
                QueueTimeoutError(),
                HTTPStatus.REQUEST_TIMEOUT,
            ),
            (
                [StopMissionMessages.success()],
                HTTPStatus.OK,
            ),
        ],
    )
    def test_stop_mission(
        self,
        client,
        access_token,
        mocker,
        mock_return,
        expected_status_code,
    ):
        mocker.patch.object(QueueUtilities, "check_queue", side_effect=mock_return)

        response = client.post(
            "/schedule/stop-mission",
            headers={"Authorization": "Bearer {}".format(access_token)},
        )

        assert response.status_code == expected_status_code

    @pytest.mark.parametrize(
        "was_mission_started, state_at_request,expected_status_code,request_params",
        [
            (
                False,
                "idle",
                HTTPStatus.OK,
                {"x": 1, "y": 1, "z": 1, "orientation": "0,0,0,1"},
            ),
            (
                True,
                "idle",
                HTTPStatus.CONFLICT,
                {"x": 1, "y": 1, "z": 1, "orientation": "0,0,0,1"},
            ),
            (
                False,
                "get_mission",
                HTTPStatus.CONFLICT,
                {"x": 1, "y": 1, "z": 1, "orientation": "0,0,0,1"},
            ),
            (
                False,
                "idle",
                HTTPStatus.UNPROCESSABLE_ENTITY,
                {"x": None, "y": 1, "z": 1, "orientation": "0,0,0,1"},
            ),
        ],
    )
    def test_schedule_drive_to(
        self,
        client,
        access_token,
        was_mission_started,
        state_at_request,
        mocker,
        expected_status_code,
        request_params,
    ):
        mocker_return = mock_check_queue(was_mission_started, state_at_request)
        mocker.patch.object(QueueUtilities, "check_queue", side_effect=mocker_return)

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
