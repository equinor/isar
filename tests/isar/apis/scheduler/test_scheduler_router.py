import re
from http import HTTPStatus
from unittest import mock
from uuid import uuid4

import pytest
from fastapi.encoders import jsonable_encoder
from fastapi.testclient import TestClient
from pytest_mock import MockerFixture

from isar.apis.models.models import ControlMissionResponse
from isar.apis.models.start_mission_definition import StopMissionDefinition
from isar.mission_planner.local_planner import LocalPlanner
from isar.mission_planner.mission_planner_interface import MissionPlannerError
from isar.models.events import EventTimeoutError
from isar.services.utilities.scheduling_utilities import SchedulingUtilities
from isar.state_machine.states_enum import States
from tests.test_double.mission_definition import DummyMissionDefinition

dummy_mission = DummyMissionDefinition.default_mission
dummy_mission_stopped = DummyMissionDefinition.stopped_mission

mock_return_unknown_status = mock.Mock(return_value=States.UnknownStatus)
mock_return_robot_standing_still = mock.Mock(return_value=States.RobotStandingStill)
mock_return_robot_standing_still_then_monitor = mock.Mock(
    side_effect=[States.RobotStandingStill, States.Monitor]
)
mock_return_monitor = mock.Mock(return_value=States.Monitor)
mock_return_paused = mock.Mock(return_value=States.Paused)
mock_void = mock.Mock()

dummy_task = dummy_mission.tasks[0]
dummy_start_mission_response = DummyMissionDefinition.dummy_start_mission_response
dummy_control_mission_response = ControlMissionResponse(
    mission_id=dummy_mission.id,
    mission_status=dummy_mission.status,
    task_id=dummy_task.id,
    task_status=dummy_task.status,
)
dummy_stopped_control_mission_response = ControlMissionResponse(
    mission_id=dummy_mission_stopped.id,
    mission_status=dummy_mission_stopped.status,
    task_id=dummy_mission_stopped.tasks[0].id,
    task_status=dummy_mission_stopped.tasks[0].status,
)
mock_return_control_mission_response = mock.Mock(
    return_value=dummy_control_mission_response
)
mock_return_stopped_control_mission_response = mock.Mock(
    return_value=dummy_stopped_control_mission_response
)
mock_queue_timeout_error = mock.Mock(side_effect=EventTimeoutError)
mock_mission_planner_error = mock.Mock(side_effect=MissionPlannerError)

dummy_stopped_with_mission_id_control_mission_response = ControlMissionResponse(
    mission_id=dummy_mission_stopped.id,
    mission_status=dummy_mission_stopped.status,
    mission_not_found=True,
    task_id=dummy_mission_stopped.tasks[0].id,
    task_status=dummy_mission_stopped.tasks[0].status,
)
mock_return_control_mission_stop_wrong_id_response = mock.Mock(
    return_value=dummy_stopped_with_mission_id_control_mission_response
)


class TestStartMissionByID:
    schedule_start_mission_path = "/schedule/start-mission"
    mock_get_mission = mock.Mock(return_value=dummy_mission)

    @mock.patch.object(
        SchedulingUtilities, "get_state", mock_return_robot_standing_still
    )
    @mock.patch.object(SchedulingUtilities, "get_mission", mock_get_mission)
    @mock.patch.object(SchedulingUtilities, "start_mission", mock_void)
    def test_start_mission_by_id(self, client: TestClient):
        response = client.post(url=f"{self.schedule_start_mission_path}/1")
        assert response.status_code == HTTPStatus.OK
        assert response.json() == jsonable_encoder(dummy_start_mission_response)

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
        assert response.status_code == HTTPStatus.CONFLICT
        assert response.json() == {
            "detail": "State machine has entered a state which cannot start a mission"
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
    dummy_start_mission_definition = (
        DummyMissionDefinition.dummy_start_mission_definition
    )
    dummy_start_mission_content = {"mission_definition": dummy_start_mission_definition}

    @mock.patch.object(
        SchedulingUtilities, "get_state", mock_return_robot_standing_still
    )
    @mock.patch.object(SchedulingUtilities, "start_mission", mock_void)
    def test_start_mission(self, client: TestClient):
        response = client.post(
            url=self.schedule_start_mission_path,
            json=jsonable_encoder(self.dummy_start_mission_content),
        )
        assert response.status_code == HTTPStatus.OK

    @mock.patch.object(
        SchedulingUtilities, "get_state", mock_return_robot_standing_still_then_monitor
    )
    @mock.patch.object(SchedulingUtilities, "start_mission", mock_void)
    def test_start_multiple_mission_at_once(self, client: TestClient):
        response1 = client.post(
            url=self.schedule_start_mission_path,
            json=jsonable_encoder(self.dummy_start_mission_content),
        )
        response2 = client.post(
            url=self.schedule_start_mission_path,
            json=jsonable_encoder(self.dummy_start_mission_content),
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
            json=jsonable_encoder(self.dummy_start_mission_content),
        )
        assert response.status_code == HTTPStatus.CONFLICT

    @mock.patch.object(
        SchedulingUtilities, "get_state", mock_return_robot_standing_still
    )
    @mock.patch.object(SchedulingUtilities, "_send_command", mock_queue_timeout_error)
    def test_start_mission_timeout(self, client: TestClient):
        response = client.post(
            url=self.schedule_start_mission_path,
            json=jsonable_encoder(self.dummy_start_mission_content),
        )
        assert response.status_code == HTTPStatus.CONFLICT
        assert response.json() == {
            "detail": "State machine has entered a state which cannot start a mission"
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
        assert re.search("take_thermal_image", response_detail)
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
        assert response.json() == jsonable_encoder(dummy_control_mission_response)

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
        assert response.status_code == HTTPStatus.CONFLICT
        assert response.json() == {
            "detail": "State machine has entered a state which cannot pause a mission"
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
        assert response.json() == jsonable_encoder(dummy_control_mission_response)

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
        SchedulingUtilities,
        "_send_command",
        mock_return_stopped_control_mission_response,
    )
    def test_stop_mission(
        self, client: TestClient, state: States, mocker: MockerFixture
    ):
        mocker.patch.object(SchedulingUtilities, "get_state", return_value=state)
        response = client.post(
            url=self.schedule_stop_mission_path,
            json=jsonable_encoder({"mission_id": StopMissionDefinition(mission_id="")}),
        )
        assert response.status_code == HTTPStatus.OK
        assert response.json() == jsonable_encoder(
            dummy_stopped_control_mission_response
        )

    @mock.patch.object(SchedulingUtilities, "get_state", mock_return_unknown_status)
    @mock.patch.object(
        SchedulingUtilities, "stop_mission", dummy_control_mission_response
    )
    def test_can_not_stop_mission_in_unknown_status(self, client: TestClient):
        response = client.post(url=self.schedule_stop_mission_path)
        assert response.status_code == HTTPStatus.CONFLICT

    @mock.patch.object(SchedulingUtilities, "get_state", mock_return_monitor)
    @mock.patch.object(SchedulingUtilities, "_send_command", mock_queue_timeout_error)
    def test_stop_mission_timeout(self, client: TestClient):
        response = client.post(
            url=self.schedule_stop_mission_path,
            json=jsonable_encoder({"mission_id": StopMissionDefinition(mission_id="")}),
        )
        assert response.status_code == HTTPStatus.CONFLICT

    @mock.patch.object(SchedulingUtilities, "get_state", mock_return_monitor)
    @mock.patch.object(
        SchedulingUtilities,
        "_send_command",
        mock_return_control_mission_stop_wrong_id_response,
    )
    def test_stop_mission_with_mission_id(self, client: TestClient):
        response = client.post(
            url=self.schedule_stop_mission_path,
            json=jsonable_encoder(
                {"mission_id": StopMissionDefinition(mission_id=str(uuid4()))}
            ),
        )
        assert response.status_code == HTTPStatus.NOT_FOUND


class TestInfoRobotSettings:
    def test_info_robot_settings(self, client: TestClient):
        response = client.get(url="/info/robot-settings")
        assert response.status_code == HTTPStatus.OK
