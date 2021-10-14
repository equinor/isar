from dataclasses import asdict
from http import HTTPStatus
from typing import Optional, Tuple

import pytest

from isar.models.communication.messages import (
    StartMessage,
    StartMissionMessages,
    StopMissionMessages,
)
from isar.models.communication.queues.queue_timeout_error import QueueTimeoutError
from isar.services.readers.base_reader import BaseReaderError
from isar.services.readers.mission_reader import MissionReaderError
from isar.services.readers.mission_reader import LocalPlanner
from isar.services.utilities.queue_utilities import QueueUtilities
from isar.services.utilities.scheduling_utilities import SchedulingUtilities
from tests.test_utilities.mock_models.mock_mission_definition import (
    mock_mission_definition,
)
from tests.test_utilities.mock_models.mock_status import mock_status


def mock_check_queue(was_mission_started, state_at_request):
    mock_return_1 = mock_status(
        mission_in_progress=was_mission_started, current_state=state_at_request
    )
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


class TestSupervisorRoutes:
    @pytest.mark.parametrize(
        "mission_id, mock_mission_id_valid, mock_get_mission_by_id, "
        "expected_exception,"
        "mock_ready_to_start, mock_start, expected_output, expected_status_code",
        [
            (
                12345,
                False,
                mock_mission_definition(),
                None,
                mock_ready_to_start_mission(HTTPStatus.OK),
                mock_start_mission(HTTPStatus.OK),
                StartMissionMessages.invalid_mission_id(12345),
                HTTPStatus.NOT_FOUND,
            ),
            (
                None,
                False,
                mock_mission_definition(),
                None,
                mock_ready_to_start_mission(HTTPStatus.OK),
                mock_start_mission(HTTPStatus.OK),
                StartMissionMessages.bad_request(),
                HTTPStatus.BAD_REQUEST,
            ),
            (
                1,
                True,
                None,
                MissionReaderError,
                mock_ready_to_start_mission(HTTPStatus.OK),
                mock_start_mission(HTTPStatus.OK),
                StartMissionMessages.mission_not_found(),
                HTTPStatus.NOT_FOUND,
            ),
            (
                1,
                True,
                mock_mission_definition(),
                None,
                mock_ready_to_start_mission(HTTPStatus.REQUEST_TIMEOUT),
                mock_start_mission(HTTPStatus.OK),
                StartMissionMessages.queue_timeout(),
                HTTPStatus.REQUEST_TIMEOUT,
            ),
            (
                1,
                True,
                mock_mission_definition(),
                None,
                mock_ready_to_start_mission(HTTPStatus.CONFLICT),
                mock_start_mission(HTTPStatus.OK),
                StartMissionMessages.mission_in_progress(),
                HTTPStatus.CONFLICT,
            ),
            (
                1,
                True,
                mock_mission_definition(),
                None,
                mock_ready_to_start_mission(HTTPStatus.OK),
                mock_start_mission(HTTPStatus.REQUEST_TIMEOUT),
                StartMissionMessages.queue_timeout(),
                HTTPStatus.REQUEST_TIMEOUT,
            ),
            (
                1,
                True,
                mock_mission_definition(),
                None,
                mock_ready_to_start_mission(HTTPStatus.OK),
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
        mock_mission_id_valid,
        mock_get_mission_by_id,
        expected_exception,
        mock_ready_to_start,
        mock_start,
        expected_output,
        expected_status_code,
    ):
        mocker.patch.object(
            LocalPlanner,
            "mission_id_valid",
            return_value=mock_mission_id_valid,
        )
        mocker.patch.object(
            LocalPlanner,
            "get_mission",
            return_value=mock_get_mission_by_id,
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

        response = client.get(
            "/schedule/start-mission",
            headers={"Authorization": "Bearer {}".format(access_token)},
            query_string={"mission_id": mission_id},
        )
        assert response.json == asdict(expected_output)
        assert response.status_code == expected_status_code

    @pytest.mark.parametrize(
        "should_stop, mock_return, expected_output, expected_status_code",
        [
            (
                True,
                QueueTimeoutError(),
                StopMissionMessages.queue_timeout(),
                HTTPStatus.REQUEST_TIMEOUT,
            ),
            (
                True,
                [StopMissionMessages.success()],
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
        should_stop,
        mock_return,
        expected_output,
        expected_status_code,
    ):
        mocker.patch.object(QueueUtilities, "check_queue", side_effect=mock_return)

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
        mocker_return = mock_check_queue(was_mission_started, state_at_request)
        mocker.patch.object(QueueUtilities, "check_queue", side_effect=mocker_return)
        response = client.get(
            "/schedule/drive-to",
            headers={"Authorization": "Bearer {}".format(access_token)},
            query_string=request_params,
        )
        assert response.status_code == expected_status_code

    @pytest.mark.parametrize(
        "mock_ready_to_start, mock_start, expected_status_code, request_params",
        [
            (
                mock_ready_to_start_mission(HTTPStatus.REQUEST_TIMEOUT),
                mock_start_mission(HTTPStatus.OK),
                HTTPStatus.REQUEST_TIMEOUT,
                {"x_target": 1, "y_target": 1, "z_target": 1},
            ),
            (
                mock_ready_to_start_mission(HTTPStatus.CONFLICT),
                mock_start_mission(HTTPStatus.OK),
                HTTPStatus.CONFLICT,
                {"x_target": 1, "y_target": 1, "z_target": 1},
            ),
            (
                mock_ready_to_start_mission(HTTPStatus.OK),
                mock_start_mission(HTTPStatus.OK),
                HTTPStatus.OK,
                {"x_target": 1, "y_target": 1, "z_target": 1},
            ),
            (
                mock_ready_to_start_mission(HTTPStatus.OK),
                mock_start_mission(HTTPStatus.REQUEST_TIMEOUT),
                HTTPStatus.REQUEST_TIMEOUT,
                {"x_target": 1, "y_target": 1, "z_target": 1},
            ),
        ],
    )
    def test_take_image(
        self,
        client,
        access_token,
        mock_ready_to_start,
        mock_start,
        mocker,
        expected_status_code,
        request_params,
    ):
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

        response = client.get(
            "/schedule/take-image",
            headers={"Authorization": "Bearer {}".format(access_token)},
            query_string=request_params,
        )
        assert response.status_code == expected_status_code
