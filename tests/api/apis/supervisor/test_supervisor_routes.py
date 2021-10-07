from dataclasses import asdict
from http import HTTPStatus
from typing import Optional, Tuple

import pytest

from isar.mission_planner.local_planner import LocalPlanner, MissionPlannerError
from isar.models.communication.messages import (
    StartMessage,
    StartMissionMessages,
    StopMissionMessages,
)
from isar.services.utilities.scheduling_utilities import SchedulingUtilities
from tests.test_utilities.mock_models.mock_mission_definition import (
    mock_mission_definition,
)


def mock_wait_on_ack(was_mission_started, state_at_request):
    if was_mission_started or state_at_request != "idle":
        return StartMissionMessages.mission_in_progress()
    else:
        return StartMissionMessages.success()


def mock_start_mission(status_code: int) -> Tuple[StartMessage, int]:
    if status_code == HTTPStatus.OK:
        return StartMissionMessages.success(), HTTPStatus.OK
    elif status_code == HTTPStatus.REQUEST_TIMEOUT:
        return (
            StartMissionMessages.ack_timeout(),
            HTTPStatus.REQUEST_TIMEOUT,
        )
    return StartMissionMessages.success(), HTTPStatus.OK


class TestSupervisorRoutes:
    @pytest.mark.parametrize(
        "mission_id, mock_get_mission_by_id, "
        "expected_exception,"
        "mock_start, expected_output, expected_status_code",
        [
            (
                12345,
                mock_mission_definition(),
                MissionPlannerError,
                mock_start_mission(HTTPStatus.OK),
                StartMissionMessages.mission_not_found(),
                HTTPStatus.NOT_FOUND,
            ),
            (
                None,
                mock_mission_definition(),
                None,
                mock_start_mission(HTTPStatus.OK),
                StartMissionMessages.bad_request(),
                HTTPStatus.BAD_REQUEST,
            ),
            (
                1,
                None,
                MissionPlannerError,
                mock_start_mission(HTTPStatus.OK),
                StartMissionMessages.mission_not_found(),
                HTTPStatus.NOT_FOUND,
            ),
            (
                1,
                mock_mission_definition(),
                None,
                mock_start_mission(HTTPStatus.OK),
                StartMissionMessages.success(),
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
        mock_get_mission_by_id,
        expected_exception,
        mock_start,
        expected_output,
        expected_status_code,
    ):
        mocker.patch.object(
            LocalPlanner,
            "get_mission",
            return_value=mock_get_mission_by_id,
            side_effect=expected_exception,
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

    @pytest.mark.parametrize(
        "mock_return, expected_output, expected_status_code",
        [
            (
                StopMissionMessages.ack_timeout(),
                StopMissionMessages.ack_timeout(),
                HTTPStatus.CONFLICT,
            ),
            (
                StopMissionMessages.success(),
                StopMissionMessages.success(),
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
        expected_output,
        expected_status_code,
    ):
        mocker.patch.object(
            SchedulingUtilities, "wait_on_stop_ack", return_value=mock_return
        )

        response = client.get(
            "/schedule/stop_mission",
            headers={"Authorization": "Bearer {}".format(access_token)},
        )

        assert response.json == asdict(expected_output)
        assert response.status_code == expected_status_code

    def test_list_predefined_missions(
        self,
        client,
        access_token,
    ):
        response = client.get(
            "/missions/list-predefined-missions",
            headers={"Authorization": "Bearer {}".format(access_token)},
        )
        assert response.status_code == HTTPStatus.OK
        response_dict = response.json
        assert type(response_dict) == dict
        assert "id" in response_dict["missions"][0]

    @pytest.mark.parametrize(
        "was_mission_started, state_at_request, expected_status_code,request_params",
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
            (False, "idle", HTTPStatus.BAD_REQUEST, None),
            (
                False,
                "idle",
                HTTPStatus.BAD_REQUEST,
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
        mocker_return = mock_wait_on_ack(was_mission_started, state_at_request)
        mocker.patch.object(
            SchedulingUtilities, "wait_on_start_ack", return_value=mocker_return
        )
        response = client.get(
            "/schedule/drive-to",
            headers={"Authorization": "Bearer {}".format(access_token)},
            query_string=request_params,
        )
        assert response.status_code == expected_status_code

    @pytest.mark.parametrize(
        "was_mission_started, state_at_request, expected_status_code,request_params",
        [
            (
                False,
                "idle",
                HTTPStatus.OK,
                {"x_target": 1, "y_target": 1, "z_target": 1},
            ),
            (
                False,
                "send",
                HTTPStatus.CONFLICT,
                {"x_target": 1, "y_target": 1, "z_target": 1},
            ),
            (
                False,
                "idle",
                HTTPStatus.BAD_REQUEST,
                None,
            ),
            (
                False,
                "idle",
                HTTPStatus.BAD_REQUEST,
                {"x_target": "hei", "y_target": 1, "z_target": 1},
            ),
            (
                False,
                "idle",
                HTTPStatus.OK,
                {"x_target": "1", "y_target": "1", "z_target": "1"},
            ),
        ],
    )
    def test_take_image(
        self,
        client,
        access_token,
        was_mission_started,
        state_at_request,
        mocker,
        expected_status_code,
        request_params,
    ):
        mocker_return = mock_wait_on_ack(was_mission_started, state_at_request)
        mocker.patch.object(
            SchedulingUtilities, "wait_on_start_ack", return_value=mocker_return
        )

        response = client.get(
            "/schedule/take-image",
            headers={"Authorization": "Bearer {}".format(access_token)},
            query_string=request_params,
        )
        assert response.status_code == expected_status_code
