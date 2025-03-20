import re
from http import HTTPStatus
from unittest import mock

import pytest
from fastapi.encoders import jsonable_encoder
from fastapi.testclient import TestClient
from pytest_mock import MockerFixture

from isar.apis.models.models import ControlMissionResponse
from isar.mission_planner.local_planner import LocalPlanner
from isar.mission_planner.mission_planner_interface import MissionPlannerError
from isar.models.communication.queues.queue_timeout_error import QueueTimeoutError
from isar.services.utilities.scheduling_utilities import SchedulingUtilities
from isar.state_machine.states_enum import States
from tests.mocks.mission_definition import MockMissionDefinition

mock_mission = MockMissionDefinition.default_mission

mock_return_unknown_status = mock.Mock(return_value=States.UnknownStatus)
mock_return_robot_standing_still = mock.Mock(return_value=States.RobotStandingStill)
mock_return_robot_standing_still_then_monitor = mock.Mock(
    side_effect=[States.RobotStandingStill, States.Monitor]
)
mock_return_monitor = mock.Mock(return_value=States.Monitor)
mock_return_paused = mock.Mock(return_value=States.Paused)
mock_void = mock.Mock()

mock_task = mock_mission.tasks[0]
mock_start_mission_response = MockMissionDefinition.mock_start_mission_response
mock_control_mission_response = ControlMissionResponse(
    mission_id=mock_mission.id,
    mission_status=mock_mission.status,
    task_id=mock_task.id,
    task_status=mock_task.status,
)
mock_return_control_mission_response = mock.Mock(
    return_value=mock_control_mission_response
)
mock_queue_timeout_error = mock.Mock(side_effect=QueueTimeoutError)
mock_mission_planner_error = mock.Mock(side_effect=MissionPlannerError)


class TestStartMissionByID:
    schedule_start_mission_path = "/schedule/start-mission"
    mock_get_mission = mock.Mock(return_value=mock_mission)

    @mock.patch.object(
        SchedulingUtilities, "get_state", mock_return_robot_standing_still
    )
    @mock.patch.object(SchedulingUtilities, "get_mission", mock_get_mission)
    @mock.patch.object(SchedulingUtilities, "start_mission", mock_void)
    def test_start_mission_by_id(self, client: TestClient):
        response = client.post(url=f"{self.schedule_start_mission_path}/1")
        assert response.status_code == HTTPStatus.OK
        assert response.json() == jsonable_encoder(mock_start_mission_response)

    @mock.patch.object(SchedulingUtilities, "get_state", mock_return_monitor)
    @mock.patch.object(SchedulingUtilities, "get_mission", mock_get_mission)
    @mock.patch.object(SchedulingUtilities, "start_mission", mock_void)
    def test_state_machine_in_conflicting_state(self, client: TestClient):
        response = client.post(url=f"{self.schedule_start_mission_path}/1")
        assert response.status_code == HTTPStatus.CONFLICT

    @mock.patch.object(
        SchedulingUtilities, "get_state", mock_return_robot_standing_still
    )
    @mock.patch.object(SchedulingUtilities, "start_mission", mock_void)
    def test_mission_not_found(self, client: TestClient):
        response = client.post(url=f"{self.schedule_start_mission_path}/9999")
        assert response.status_code == HTTPStatus.NOT_FOUND
        assert response.json() == {"detail": "Mission with id '9999' not found"}

    @mock.patch.object(
        SchedulingUtilities, "get_state", mock_return_robot_standing_still
    )
    @mock.patch.object(SchedulingUtilities, "get_mission", mock_get_mission)
    @mock.patch.object(SchedulingUtilities, "_send_command", mock_queue_timeout_error)
    def test_start_mission_timeout(self, client: TestClient):
        response = client.post(url=f"{self.schedule_start_mission_path}/1")
        assert response.status_code == HTTPStatus.INTERNAL_SERVER_ERROR
        assert response.json() == {
            "detail": "Internal Server Error - Failed to start mission in ISAR"
        }

    @mock.patch.object(
        SchedulingUtilities, "get_state", mock_return_robot_standing_still
    )
    @mock.patch.object(SchedulingUtilities, "get_mission", mock_get_mission)
    @mock.patch("isar.config.settings.robot_settings.CAPABILITIES", [])
    @mock.patch.object(SchedulingUtilities, "start_mission", mock_void)
    def test_robot_not_capable(self, client: TestClient):
        response = client.post(url=f"{self.schedule_start_mission_path}/1")
        assert response.status_code == HTTPStatus.BAD_REQUEST
        response_detail = response.json()["detail"]
        assert re.match(
            "Bad Request - Robot is not capable of performing mission.", response_detail
        )
        assert re.search("take_image", response_detail)

    @mock.patch.object(
        SchedulingUtilities, "get_state", mock_return_robot_standing_still
    )
    @mock.patch.object(SchedulingUtilities, "start_mission", mock_void)
    @mock.patch.object(LocalPlanner, "get_mission", mock_mission_planner_error)
    def test_mission_planner_error(self, client: TestClient):
        response = client.post(url=f"{self.schedule_start_mission_path}/1")
        assert response.status_code == HTTPStatus.INTERNAL_SERVER_ERROR
        assert response.json() == {"detail": "Could not plan mission"}


class TestStartMission:
    schedule_start_mission_path = "/schedule/start-mission"
    mock_start_mission_definition = MockMissionDefinition.mock_start_mission_definition
    mock_start_mission_content = {"mission_definition": mock_start_mission_definition}

    @mock.patch.object(
        SchedulingUtilities, "get_state", mock_return_robot_standing_still
    )
    @mock.patch.object(SchedulingUtilities, "start_mission", mock_void)
    def test_start_mission(self, client: TestClient):
        response = client.post(
            url=self.schedule_start_mission_path,
            json=jsonable_encoder(self.mock_start_mission_content),
        )
        assert response.status_code == HTTPStatus.OK

    @mock.patch.object(
        SchedulingUtilities, "get_state", mock_return_robot_standing_still_then_monitor
    )
    @mock.patch.object(SchedulingUtilities, "start_mission", mock_void)
    def test_start_multiple_mission_at_once(self, client: TestClient):
        response1 = client.post(
            url=self.schedule_start_mission_path,
            json=jsonable_encoder(self.mock_start_mission_content),
        )
        response2 = client.post(
            url=self.schedule_start_mission_path,
            json=jsonable_encoder(self.mock_start_mission_content),
        )
        assert response1.status_code == HTTPStatus.OK
        assert response2.status_code == HTTPStatus.CONFLICT

    def test_incomplete_request(self, client: TestClient):
        response = client.post(url=self.schedule_start_mission_path, json={})
        assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY

    @mock.patch.object(SchedulingUtilities, "get_state", mock_return_monitor)
    def test_state_machine_in_conflicting_state(self, client: TestClient):
        response = client.post(
            url=self.schedule_start_mission_path,
            json=jsonable_encoder(self.mock_start_mission_content),
        )
        assert response.status_code == HTTPStatus.CONFLICT

    @mock.patch.object(
        SchedulingUtilities, "get_state", mock_return_robot_standing_still
    )
    @mock.patch.object(SchedulingUtilities, "_send_command", mock_queue_timeout_error)
    def test_start_mission_timeout(self, client: TestClient):
        response = client.post(
            url=self.schedule_start_mission_path,
            json=jsonable_encoder(self.mock_start_mission_content),
        )
        assert response.status_code == HTTPStatus.INTERNAL_SERVER_ERROR
        assert response.json() == {
            "detail": "Internal Server Error - Failed to start mission in ISAR"
        }

    @mock.patch.object(
        SchedulingUtilities, "get_state", mock_return_robot_standing_still
    )
    @mock.patch("isar.config.settings.robot_settings.CAPABILITIES", [])
    @mock.patch.object(SchedulingUtilities, "start_mission", mock_void)
    def test_robot_not_capable(self, client: TestClient):
        response = client.post(url=f"{self.schedule_start_mission_path}/1")
        assert response.status_code == HTTPStatus.BAD_REQUEST
        response_detail = response.json()["detail"]
        assert re.match(
            "Bad Request - Robot is not capable of performing mission.", response_detail
        )
        assert re.search("return_to_home", response_detail)
        assert re.search("take_image", response_detail)


class TestPauseMission:
    schedule_pause_mission_path = "/schedule/pause-mission"

    @mock.patch.object(SchedulingUtilities, "get_state", mock_return_monitor)
    @mock.patch.object(
        SchedulingUtilities, "_send_command", mock_return_control_mission_response
    )
    def test_pause_mission(self, client: TestClient):
        response = client.post(url=self.schedule_pause_mission_path)
        assert response.status_code == HTTPStatus.OK
        assert response.json() == jsonable_encoder(mock_control_mission_response)

    @mock.patch.object(
        SchedulingUtilities, "get_state", mock_return_robot_standing_still
    )
    def test_state_machine_in_conflicting_state(self, client: TestClient):
        response = client.post(url=self.schedule_pause_mission_path)
        assert response.status_code == HTTPStatus.CONFLICT

    @mock.patch.object(SchedulingUtilities, "get_state", mock_return_monitor)
    @mock.patch.object(SchedulingUtilities, "_send_command", mock_queue_timeout_error)
    def test_pause_mission_timeout(self, client: TestClient):
        response = client.post(url=self.schedule_pause_mission_path)
        assert response.status_code == HTTPStatus.INTERNAL_SERVER_ERROR
        assert response.json() == {
            "detail": "Internal Server Error - Failed to pause mission"
        }


class TestResumeMission:
    schedule_resume_mission_path = "/schedule/resume-mission"

    @mock.patch.object(SchedulingUtilities, "get_state", mock_return_paused)
    @mock.patch.object(
        SchedulingUtilities, "_send_command", mock_return_control_mission_response
    )
    def test_resume_mission(self, client: TestClient):
        response = client.post(url=self.schedule_resume_mission_path)
        assert response.status_code == HTTPStatus.OK
        assert response.json() == jsonable_encoder(mock_control_mission_response)

    @mock.patch.object(
        SchedulingUtilities, "get_state", mock_return_robot_standing_still
    )
    def test_state_machine_in_conflicting_state(self, client: TestClient):
        response = client.post(url=self.schedule_resume_mission_path)
        assert response.status_code == HTTPStatus.CONFLICT

    @mock.patch.object(SchedulingUtilities, "get_state", mock_return_paused)
    @mock.patch.object(SchedulingUtilities, "_send_command", mock_queue_timeout_error)
    def test_resume_mission_timeout(self, client: TestClient):
        response = client.post(url=self.schedule_resume_mission_path)
        assert response.status_code == HTTPStatus.INTERNAL_SERVER_ERROR
        assert response.json() == {
            "detail": "Internal Server Error - Failed to resume mission"
        }


class TestStopMission:
    schedule_stop_mission_path = "/schedule/stop-mission"
    valid_states = [
        States.AwaitNextMission,
        States.RobotStandingStill,
        States.ReturningHome,
        States.Monitor,
        States.Paused,
    ]

    @pytest.mark.parametrize("state", valid_states)
    @mock.patch.object(
        SchedulingUtilities, "_send_command", mock_return_control_mission_response
    )
    def test_stop_mission(
        self, client: TestClient, state: States, mocker: MockerFixture
    ):
        mocker.patch.object(SchedulingUtilities, "get_state", return_value=state)
        response = client.post(url=self.schedule_stop_mission_path)
        assert response.status_code == HTTPStatus.OK
        assert response.json() == jsonable_encoder(mock_control_mission_response)

    @mock.patch.object(SchedulingUtilities, "get_state", mock_return_unknown_status)
    @mock.patch.object(
        SchedulingUtilities, "stop_mission", mock_control_mission_response
    )
    def test_can_not_stop_mission_in_unknown_status(self, client: TestClient):
        response = client.post(url=self.schedule_stop_mission_path)
        assert response.status_code == HTTPStatus.CONFLICT

    @mock.patch.object(SchedulingUtilities, "get_state", mock_return_monitor)
    @mock.patch.object(SchedulingUtilities, "_send_command", mock_queue_timeout_error)
    def test_stop_mission_timeout(self, client: TestClient):
        response = client.post(url=self.schedule_stop_mission_path)
        assert response.status_code == HTTPStatus.INTERNAL_SERVER_ERROR


class TestInfoRobotSettings:
    def test_info_robot_settings(self, client: TestClient):
        response = client.get(url="/info/robot-settings")
        assert response.status_code == HTTPStatus.OK
