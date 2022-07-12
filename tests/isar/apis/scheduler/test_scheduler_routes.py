from http import HTTPStatus
import json

import pytest
from isar.apis.models.models import InputOrientation, InputPosition
from fastapi.testclient import TestClient
from fastapi.encoders import jsonable_encoder
from isar.apis.security.authentication import Authenticator
from isar.apis.models import InputPose
from isar.mission_planner.local_planner import LocalPlanner
from isar.mission_planner.mission_planner_interface import MissionPlannerError
from isar.models.communication.queues.queue_timeout_error import QueueTimeoutError
from isar.services.utilities.scheduling_utilities import SchedulingUtilities
from isar.state_machine.states_enum import States
from tests.mocks.mission_definition import MockMissionDefinition

mock_orientation: InputOrientation = InputOrientation(
    x=0, y=0, z=0, w=1, frame_name="robot"
)
mock_position: InputPosition = InputPosition(x=1, y=1, z=1, frame_name="robot")
mock_pose: InputPose = InputPose(
    orientation=mock_orientation, position=mock_position, frame_name="robot"
)


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
    def test_start_mission_by_id(
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
            f"schedule/start-mission/{mission_id}",
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
        "mock_start_mission, mock_get_state,expected_status_code,target_pose",
        [
            (
                None,
                States.Idle,
                HTTPStatus.OK,
                mock_pose,
            ),
            (
                QueueTimeoutError,
                States.Idle,
                HTTPStatus.REQUEST_TIMEOUT,
                mock_pose,
            ),
            (
                None,
                States.Monitor,
                HTTPStatus.CONFLICT,
                mock_pose,
            ),
            (
                None,
                States.Idle,
                HTTPStatus.UNPROCESSABLE_ENTITY,
                InputPosition(
                    x=1,
                    y=1,
                    z=1,
                    frame_name="robot",
                ),
            ),
        ],
    )
    def test_schedule_drive_to(
        self,
        client: TestClient,
        access_token,
        mock_start_mission,
        mock_get_state,
        mocker,
        expected_status_code,
        target_pose,
    ):
        mocker.patch.object(
            SchedulingUtilities, "get_state", return_value=mock_get_state
        )

        mocker.patch.object(
            SchedulingUtilities, "start_mission", side_effect=mock_start_mission
        )
        mocker.patch.object(Authenticator, "should_authenticate", return_value=False)

        data: str = json.dumps(jsonable_encoder(target_pose))

        response = client.post(
            url=f"/schedule/drive-to",
            headers={"Authorization": "Bearer {}".format(access_token)},
            data=data,
        )

        assert response.status_code == expected_status_code
