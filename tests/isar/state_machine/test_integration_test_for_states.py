import time
from collections import deque
from typing import List

import pytest
from fastapi import HTTPException
from pytest_mock import MockerFixture

from isar.config.settings import settings
from isar.modules import ApplicationContainer
from isar.robot.robot_status import RobotStatusThread
from isar.services.utilities.scheduling_utilities import SchedulingUtilities
from isar.state_machine.states_enum import States
from isar.storage.storage_interface import StorageInterface
from robot_interface.models.mission.mission import Mission
from robot_interface.models.mission.status import MissionStatus, RobotStatus
from robot_interface.models.mission.task import TakeImage, Task
from tests.test_mocks.pose import DummyPose
from tests.test_mocks.robot_interface import (
    StubRobot,
    StubRobotInitiateMissionRaisesException,
    StubRobotRobotStatusBusyIfNotHomeOrUnknownStatus,
)
from tests.test_mocks.state_machine_mocks import (
    RobotServiceThreadMock,
    StateMachineThreadMock,
    UploaderThreadMock,
)
from tests.test_mocks.task import StubTask


def test_state_machine_transitions_when_running_full_mission(
    container: ApplicationContainer,
    state_machine_thread: StateMachineThreadMock,
    robot_service_thread: RobotServiceThreadMock,
    mocker,
) -> None:
    mocker.patch.object(settings, "RETURN_HOME_DELAY", 0.01)

    state_machine_thread.start()
    robot_service_thread.start()
    time.sleep(1)
    # Setting the poll interval to a lower value to ensure that the robot status is
    # updated during the mission. This value needs to be set after the robot service
    # thread has been started.
    robot_service_thread.robot_service.robot = (
        StubRobotRobotStatusBusyIfNotHomeOrUnknownStatus(
            current_state=robot_service_thread.robot_service.shared_state.state,
            initiate_mission_delay=1,
        )
    )
    robot_service_thread.robot_service.robot_status_thread.robot_status_poll_interval = (
        0.5
    )

    task_1: Task = TakeImage(
        target=DummyPose.default_pose().position, robot_pose=DummyPose.default_pose()
    )
    task_2: Task = TakeImage(
        target=DummyPose.default_pose().position, robot_pose=DummyPose.default_pose()
    )
    mission: Mission = Mission(name="Dummy mission", tasks=[task_1, task_2])

    scheduling_utilities: SchedulingUtilities = container.scheduling_utilities()
    scheduling_utilities.start_mission(mission=mission)
    time.sleep(3)  # Allow enough time to run mission and return home

    assert state_machine_thread.state_machine.transitions_list == deque(
        [
            States.UnknownStatus,
            States.AwaitNextMission,
            States.Monitor,
            States.AwaitNextMission,
            States.ReturningHome,
            States.Home,
        ]
    )


def test_state_machine_failed_dependency(
    container: ApplicationContainer,
    state_machine_thread: StateMachineThreadMock,
    robot_service_thread: RobotServiceThreadMock,
    mocker,
) -> None:
    mocker.patch.object(settings, "RETURN_HOME_DELAY", 0.01)

    task_1: Task = TakeImage(
        target=DummyPose.default_pose().position, robot_pose=DummyPose.default_pose()
    )
    task_2: Task = TakeImage(
        target=DummyPose.default_pose().position, robot_pose=DummyPose.default_pose()
    )
    mission: Mission = Mission(name="Dummy misson", tasks=[task_1, task_2])

    mocker.patch.object(StubRobot, "mission_status", return_value=MissionStatus.Failed)

    state_machine_thread.start()
    robot_service_thread.start()
    time.sleep(1)
    scheduling_utilities: SchedulingUtilities = container.scheduling_utilities()
    scheduling_utilities.start_mission(mission=mission)
    time.sleep(3)  # Allow the state machine to transition through the mission

    assert state_machine_thread.state_machine.transitions_list == deque(
        [
            States.UnknownStatus,
            States.AwaitNextMission,
            States.Monitor,
            States.AwaitNextMission,
            States.ReturningHome,
            States.InterventionNeeded,
        ]
    )


def test_state_machine_with_successful_collection(
    container: ApplicationContainer,
    state_machine_thread: StateMachineThreadMock,
    robot_service_thread: RobotServiceThreadMock,
    uploader_thread: UploaderThreadMock,
    mocker,
) -> None:
    mocker.patch.object(StubRobot, "robot_status", return_value=RobotStatus.Home)

    storage_mock: StorageInterface = container.storage_handlers(List[StorageInterface])[
        0
    ]

    mocker.patch.object(
        RobotStatusThread, "_is_ready_to_poll_for_status", return_value=True
    )

    mission: Mission = Mission(name="Dummy misson", tasks=[StubTask.take_image()])
    scheduling_utilities: SchedulingUtilities = container.scheduling_utilities()

    mocker.patch.object(settings, "RETURN_HOME_DELAY", 0.01)
    state_machine_thread.start()
    uploader_thread.start()

    robot_service_thread.start()
    time.sleep(1)
    scheduling_utilities.start_mission(mission=mission)
    time.sleep(3)  # Allow enough time to run mission and return home

    expected_stored_items = 1
    assert len(storage_mock.stored_inspections) == expected_stored_items  # type: ignore
    assert state_machine_thread.state_machine.transitions_list == deque(
        [
            States.UnknownStatus,
            States.Home,
            States.Monitor,
            States.AwaitNextMission,
            States.ReturningHome,
            States.Home,
        ]
    )


def test_state_machine_with_unsuccessful_collection(
    container: ApplicationContainer,
    mocker,
    state_machine_thread: StateMachineThreadMock,
    robot_service_thread: RobotServiceThreadMock,
    uploader_thread: UploaderThreadMock,
) -> None:
    mocker.patch.object(StubRobot, "robot_status", return_value=RobotStatus.Home)

    storage_mock: StorageInterface = container.storage_handlers(List[StorageInterface])[
        0
    ]

    mocker.patch.object(StubRobot, "get_inspection", return_value=None)

    mocker.patch.object(
        RobotStatusThread, "_is_ready_to_poll_for_status", return_value=True
    )

    mocker.patch.object(settings, "RETURN_HOME_DELAY", 0.01)
    state_machine_thread.start()
    robot_service_thread.start()
    uploader_thread.start()
    time.sleep(1)
    mission: Mission = Mission(name="Dummy misson", tasks=[StubTask.take_image()])
    scheduling_utilities: SchedulingUtilities = container.scheduling_utilities()
    scheduling_utilities.start_mission(mission=mission)
    time.sleep(3)  # Allow enough time to run mission and return home

    expected_stored_items = 0
    assert len(storage_mock.stored_inspections) == expected_stored_items  # type: ignore

    assert state_machine_thread.state_machine.transitions_list == deque(
        [
            States.UnknownStatus,
            States.Home,
            States.Monitor,
            States.AwaitNextMission,
            States.ReturningHome,
            States.Home,
        ]
    )


def test_state_machine_with_mission_start_during_return_home_without_queueing_stop_response(
    container: ApplicationContainer,
    mocker: MockerFixture,
    state_machine_thread: StateMachineThreadMock,
    robot_service_thread: RobotServiceThreadMock,
) -> None:
    mocker.patch.object(StubRobot, "robot_status", return_value=RobotStatus.Home)
    mission: Mission = Mission(name="Dummy misson", tasks=[StubTask.take_image()])
    scheduling_utilities: SchedulingUtilities = container.scheduling_utilities()
    mocker.patch.object(
        StubRobot, "mission_status", return_value=MissionStatus.InProgress
    )

    settings.FSM_SLEEP_TIME = 0

    state_machine_thread.start()
    robot_service_thread.start()
    time.sleep(1)
    scheduling_utilities.return_home()
    time.sleep(1)
    scheduling_utilities.start_mission(mission=mission)
    time.sleep(1)
    assert state_machine_thread.state_machine.transitions_list == deque(
        [
            States.UnknownStatus,
            States.Home,
            States.ReturningHome,
            States.StoppingReturnHome,
            States.Monitor,
        ]
    )
    assert (
        not state_machine_thread.state_machine.events.api_requests.start_mission.request.has_event()
    )


def test_state_machine_failed_to_initiate_mission_and_return_home(
    container: ApplicationContainer,
    state_machine_thread: StateMachineThreadMock,
    robot_service_thread: RobotServiceThreadMock,
    mocker,
) -> None:
    mocker.patch.object(settings, "RETURN_HOME_DELAY", 0.01)

    robot_service_thread.robot_service.robot = StubRobotInitiateMissionRaisesException()

    task_1: Task = TakeImage(
        target=DummyPose.default_pose().position, robot_pose=DummyPose.default_pose()
    )
    task_2: Task = TakeImage(
        target=DummyPose.default_pose().position, robot_pose=DummyPose.default_pose()
    )
    mission: Mission = Mission(name="Dummy misson", tasks=[task_1, task_2])

    state_machine_thread.start()
    robot_service_thread.start()

    # TODO: check mqtt
    time.sleep(1)
    scheduling_utilities: SchedulingUtilities = container.scheduling_utilities()
    scheduling_utilities.start_mission(mission=mission)
    time.sleep(3)  # Allow the state machine to transition through the mission

    assert state_machine_thread.state_machine.transitions_list == deque(
        [
            States.UnknownStatus,
            States.AwaitNextMission,
            States.Monitor,
            States.AwaitNextMission,
            States.ReturningHome,
            States.InterventionNeeded,
        ]
    )


def test_state_machine_battery_too_low_to_start_mission(
    container: ApplicationContainer,
    state_machine_thread: StateMachineThreadMock,
    robot_service_thread: RobotServiceThreadMock,
    mocker,
) -> None:
    mocker.patch.object(settings, "RETURN_HOME_DELAY", 0.01)
    state_machine_thread.start()
    mocker.patch.object(StubRobot, "robot_status", return_value=RobotStatus.Home)
    mocker.patch.object(StubRobot, "get_battery_level", return_value=10.0)
    robot_service_thread.start()
    time.sleep(1)
    task_1: Task = TakeImage(
        target=DummyPose.default_pose().position, robot_pose=DummyPose.default_pose()
    )
    task_2: Task = TakeImage(
        target=DummyPose.default_pose().position, robot_pose=DummyPose.default_pose()
    )
    mission: Mission = Mission(name="Dummy misson", tasks=[task_1, task_2])

    scheduling_utilities: SchedulingUtilities = container.scheduling_utilities()

    with pytest.raises(HTTPException) as exception_details:
        scheduling_utilities.start_mission(mission=mission)
        assert exception_details.value.status_code == 408

    assert state_machine_thread.state_machine.transitions_list == deque(
        [
            States.UnknownStatus,
            States.Home,
            States.Recharging,
        ]
    )
