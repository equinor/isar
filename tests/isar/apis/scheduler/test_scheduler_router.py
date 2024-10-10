import json
import re
from http import HTTPStatus
from typing import List
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
from robot_interface.models.mission.task import TaskTypes
from tests.mocks.mission_definition import MockMissionDefinition

mock_mission = MockMissionDefinition.default_mission

mock_return_off = mock.Mock(return_value=States.Off)
mock_return_idle = mock.Mock(return_value=States.Idle)
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

    @mock.patch.object(SchedulingUtilities, "get_state", mock_return_idle)
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

    @mock.patch.object(SchedulingUtilities, "get_state", mock_return_idle)
    @mock.patch.object(SchedulingUtilities, "start_mission", mock_void)
    def test_mission_not_found(self, client: TestClient):
        response = client.post(url=f"{self.schedule_start_mission_path}/9999")
        assert response.status_code == HTTPStatus.NOT_FOUND
        assert response.json() == {"detail": "Mission with id '9999' not found"}

    @mock.patch.object(SchedulingUtilities, "get_state", mock_return_idle)
    @mock.patch.object(SchedulingUtilities, "get_mission", mock_get_mission)
    @mock.patch.object(SchedulingUtilities, "_send_command", mock_queue_timeout_error)
    def test_start_mission_timeout(self, client: TestClient):
        response = client.post(url=f"{self.schedule_start_mission_path}/1")
        assert response.status_code == HTTPStatus.INTERNAL_SERVER_ERROR
        assert response.json() == {
            "detail": "Internal Server Error - Failed to start mission in ISAR"
        }

    @mock.patch.object(SchedulingUtilities, "get_state", mock_return_idle)
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
        assert re.search("return_to_home", response_detail)
        assert re.search("take_image", response_detail)

    @mock.patch.object(SchedulingUtilities, "get_state", mock_return_idle)
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
    mock_start_mission_with_task_ids_content = {
        "mission_definition": MockMissionDefinition.mock_start_mission_definition_task_ids
    }
    mock_start_mission_duplicate_task_ids_content = {
        "mission_definition": MockMissionDefinition.mock_start_mission_definition_with_duplicate_task_ids
    }

    @mock.patch.object(SchedulingUtilities, "get_state", mock_return_idle)
    @mock.patch.object(SchedulingUtilities, "start_mission", mock_void)
    def test_start_mission(self, client: TestClient):
        response = client.post(
            url=self.schedule_start_mission_path,
            json=jsonable_encoder(self.mock_start_mission_content),
        )
        assert response.status_code == HTTPStatus.OK

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

    @mock.patch.object(SchedulingUtilities, "get_state", mock_return_idle)
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

    @mock.patch.object(SchedulingUtilities, "get_state", mock_return_idle)
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

    @mock.patch.object(SchedulingUtilities, "get_state", mock_return_idle)
    @mock.patch.object(SchedulingUtilities, "start_mission", mock_void)
    def test_mission_with_input_task_ids(self, client: TestClient):
        expected_ids: List[str] = []
        for task in self.mock_start_mission_with_task_ids_content[
            "mission_definition"
        ].tasks:
            if task.id:
                expected_ids.append(task.id)

        response = client.post(
            url=self.schedule_start_mission_path,
            json=jsonable_encoder(self.mock_start_mission_with_task_ids_content),
        )
        assert response.status_code == HTTPStatus.OK
        start_mission_response: dict = response.json()
        for task in start_mission_response["tasks"]:
            assert task["id"] in expected_ids

    @mock.patch.object(SchedulingUtilities, "get_state", mock_return_idle)
    @mock.patch.object(SchedulingUtilities, "start_mission", mock_void)
    def test_mission_with_input_inspection_task_ids(self, client: TestClient):
        expected_inspection_ids: List[str] = []
        for task in self.mock_start_mission_with_task_ids_content[
            "mission_definition"
        ].tasks:
            expected_inspection_ids.append(task.inspection.id)

        response = client.post(
            url=self.schedule_start_mission_path,
            json=jsonable_encoder(self.mock_start_mission_with_task_ids_content),
        )
        assert response.status_code == HTTPStatus.OK
        start_mission_response: dict = response.json()
        for task in start_mission_response["tasks"]:
            if (
                task["type"] == TaskTypes.ReturnToHome == False
                and task["type"] == TaskTypes.Localize == False
                and task["type"] == TaskTypes.DockingProcedure == False
                and task["type"] == TaskTypes.MoveArm == False
            ):
                assert task["id"] in expected_inspection_ids

    @mock.patch.object(SchedulingUtilities, "get_state", mock_return_idle)
    @mock.patch.object(SchedulingUtilities, "start_mission", mock_void)
    def test_mission_with_duplicate_task_ids(self, client: TestClient):
        response = client.post(
            url=self.schedule_start_mission_path,
            json=jsonable_encoder(self.mock_start_mission_duplicate_task_ids_content),
        )
        assert response.status_code == HTTPStatus.BAD_REQUEST


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

    @mock.patch.object(SchedulingUtilities, "get_state", mock_return_idle)
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

    @mock.patch.object(SchedulingUtilities, "get_state", mock_return_idle)
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
        States.Initiate,
        States.Initialize,
        States.Monitor,
        States.Paused,
        States.Stop,
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

    @mock.patch.object(SchedulingUtilities, "get_state", mock_return_idle)
    @mock.patch.object(
        SchedulingUtilities, "stop_mission", mock_control_mission_response
    )
    def test_can_not_stop_mission_in_idle(self, client: TestClient):
        response = client.post(url=self.schedule_stop_mission_path)
        assert response.status_code == HTTPStatus.CONFLICT

    @mock.patch.object(SchedulingUtilities, "get_state", mock_return_off)
    @mock.patch.object(
        SchedulingUtilities, "stop_mission", mock_control_mission_response
    )
    def test_can_not_stop_mission_in_off(self, client: TestClient):
        response = client.post(url=self.schedule_stop_mission_path)
        assert response.status_code == HTTPStatus.CONFLICT

    @mock.patch.object(SchedulingUtilities, "get_state", mock_return_monitor)
    @mock.patch.object(SchedulingUtilities, "_send_command", mock_queue_timeout_error)
    def test_stop_mission_timeout(self, client: TestClient):
        response = client.post(url=self.schedule_stop_mission_path)
        assert response.status_code == HTTPStatus.INTERNAL_SERVER_ERROR


class TestDriveTo:
    schedule_drive_to_path = "/schedule/drive-to"
    mock_target_pose = MockMissionDefinition.mock_input_pose
    mock_data: str = json.dumps(jsonable_encoder(mock_target_pose))

    @mock.patch.object(SchedulingUtilities, "get_state", mock_return_idle)
    @mock.patch.object(SchedulingUtilities, "_send_command", mock_void)
    def test_drive_to(self, client: TestClient):
        response = client.post(url=self.schedule_drive_to_path, data=self.mock_data)
        assert response.status_code == HTTPStatus.OK

    @mock.patch.object(SchedulingUtilities, "get_state", mock_return_idle)
    @mock.patch.object(SchedulingUtilities, "_send_command", mock_queue_timeout_error)
    def test_drive_to_timeout(self, client: TestClient):
        response = client.post(url=self.schedule_drive_to_path, data=self.mock_data)
        assert response.status_code == HTTPStatus.INTERNAL_SERVER_ERROR
        assert response.json() == {
            "detail": "Internal Server Error - Failed to start mission in ISAR"
        }

    @mock.patch.object(SchedulingUtilities, "get_state", mock_return_monitor)
    @mock.patch.object(SchedulingUtilities, "_send_command", mock_void)
    def test_state_machine_in_conflicting_state(self, client: TestClient):
        response = client.post(url=self.schedule_drive_to_path, data=self.mock_data)
        assert response.status_code == HTTPStatus.CONFLICT


class TestInfoRobotSettings:
    def test_info_robot_settings(self, client: TestClient):
        response = client.get(url="/info/robot-settings")
        assert response.status_code == HTTPStatus.OK
