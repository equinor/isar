from http import HTTPStatus

import pytest
from fastapi import HTTPException
from pytest_mock import MockerFixture

from isar.models.communication.queues.events import QueueIO
from isar.models.communication.queues.queue_timeout_error import QueueTimeoutError
from isar.services.utilities.queue_utilities import QueueUtilities
from isar.services.utilities.scheduling_utilities import SchedulingUtilities
from isar.state_machine.states_enum import States
from tests.mocks.mission_definition import MockMissionDefinition


def test_timeout_send_command(
    mocker: MockerFixture, scheduling_utilities: SchedulingUtilities
):
    mocker.patch.object(QueueUtilities, "check_queue", side_effect=QueueTimeoutError)
    q: QueueIO = QueueIO(input_size=1, output_size=1)
    with pytest.raises(QueueTimeoutError):
        scheduling_utilities._send_command(True, q)
    assert q.input.empty()


def test_robot_capable_of_mission(scheduling_utilities: SchedulingUtilities):
    assert scheduling_utilities.verify_robot_capable_of_mission(
        mission=MockMissionDefinition.default_mission,
        robot_capabilities=["return_to_home", "take_image"],
    )


def test_robot_not_capable_of_mission(scheduling_utilities: SchedulingUtilities):
    with pytest.raises(HTTPException) as err:
        scheduling_utilities.verify_robot_capable_of_mission(
            mission=MockMissionDefinition.default_mission,
            robot_capabilities=["return_to_home"],
        )
    assert err.value.status_code == HTTPStatus.BAD_REQUEST


def test_state_machine_ready_to_receive_mission(
    scheduling_utilities: SchedulingUtilities,
):
    assert scheduling_utilities.verify_state_machine_ready_to_receive_mission(
        States.RobotStandingStill
    )
    assert scheduling_utilities.verify_state_machine_ready_to_receive_mission(
        States.Home
    )
    assert scheduling_utilities.verify_state_machine_ready_to_receive_mission(
        States.ReturningHome
    )
    assert scheduling_utilities.verify_state_machine_ready_to_receive_mission(
        States.AwaitNextMission
    )


def test_state_machine_not_ready_to_receive_mission(
    scheduling_utilities: SchedulingUtilities,
):
    with pytest.raises(HTTPException) as err:
        scheduling_utilities.verify_state_machine_ready_to_receive_mission(
            States.Monitor
        )
    assert err.value.status_code == HTTPStatus.CONFLICT
