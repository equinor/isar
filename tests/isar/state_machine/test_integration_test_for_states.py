import time
from collections import deque
from threading import Thread
from typing import List

from pytest_mock import MockerFixture

from isar.config.settings import settings
from isar.modules import ApplicationContainer
from isar.services.utilities.scheduling_utilities import SchedulingUtilities
from isar.state_machine.states_enum import States
from isar.storage.storage_interface import StorageInterface
from robot_interface.models.mission.mission import Mission
from robot_interface.models.mission.status import MissionStatus, RobotStatus, TaskStatus
from robot_interface.models.mission.task import TakeImage, Task
from tests.test_mocks.inspection import stub_pose
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
from tests.wait import wait_until


def test_state_machine_transitions_when_running_full_mission(
    container: ApplicationContainer,
    state_machine_thread: StateMachineThreadMock,
    robot_service_thread: RobotServiceThreadMock,
    mocker: MockerFixture,
) -> None:
    mocker.patch.object(settings, "RETURN_HOME_DELAY", 0.01)
    mocker.patch.object(settings, "FSM_SLEEP_TIME", 0.01)

    state_machine_thread.start()
    robot_service_thread.start()
    wait_until(
        lambda: States.UnknownStatus
        in state_machine_thread.state_machine.transitions_list
        and robot_service_thread.robot_service.status_thread is not None
    )
    # Setting the poll interval to a lower value to ensure that the robot status is
    # updated during the mission. This value needs to be set after the robot service
    # thread has been started.
    robot_service_thread.robot_service.robot = (
        StubRobotRobotStatusBusyIfNotHomeOrUnknownStatus(
            current_state=robot_service_thread.robot_service.shared_state.state,
            initiate_mission_delay=1,
        )
    )

    task_1: Task = TakeImage(target=stub_pose().position, robot_pose=stub_pose())
    task_2: Task = TakeImage(target=stub_pose().position, robot_pose=stub_pose())
    mission: Mission = Mission(name="Dummy mission", tasks=[task_1, task_2])

    scheduling_utilities: SchedulingUtilities = container.scheduling_utilities()
    scheduling_utilities.start_mission(mission=mission)

    expected_transitions = deque(
        [
            States.UnknownStatus,
            States.AwaitNextMission,
            States.Monitor,
            States.AwaitNextMission,
            States.ReturningHome,
            States.Home,
        ]
    )
    wait_until(
        lambda: state_machine_thread.state_machine.transitions_list
        == expected_transitions
    )


def test_state_machine_failed_dependency(
    container: ApplicationContainer,
    state_machine_thread: StateMachineThreadMock,
    robot_service_thread: RobotServiceThreadMock,
    mocker: MockerFixture,
) -> None:
    mocker.patch.object(settings, "RETURN_HOME_DELAY", 0.01)
    mocker.patch.object(settings, "RETURN_HOME_RETRY_LIMIT", 3)
    mocker.patch.object(settings, "FSM_SLEEP_TIME", 0.01)

    task_1: Task = TakeImage(target=stub_pose().position, robot_pose=stub_pose())
    task_2: Task = TakeImage(target=stub_pose().position, robot_pose=stub_pose())
    mission: Mission = Mission(name="Dummy misson", tasks=[task_1, task_2])

    mocker.patch.object(StubRobot, "task_status", return_value=TaskStatus.Failed)
    mocker.patch.object(StubRobot, "mission_status", return_value=MissionStatus.Failed)

    state_machine_thread.start()
    robot_service_thread.start()
    wait_until(
        lambda: States.UnknownStatus
        in state_machine_thread.state_machine.transitions_list
    )
    scheduling_utilities: SchedulingUtilities = container.scheduling_utilities()
    scheduling_utilities.start_mission(mission=mission)

    expected_transitions = deque(
        [
            States.UnknownStatus,
            States.AwaitNextMission,
            States.Monitor,
            States.AwaitNextMission,
            States.ReturningHome,
            States.ReturningHome,
            States.ReturningHome,
            States.ReturningHome,
            States.ReturningHome,
            States.InterventionNeeded,
        ]
    )
    wait_until(
        lambda: state_machine_thread.state_machine.transitions_list
        == expected_transitions,
        timeout=10.0,
    )


def test_state_machine_with_successful_collection(
    container: ApplicationContainer,
    state_machine_thread: StateMachineThreadMock,
    robot_service_thread: RobotServiceThreadMock,
    uploader_thread: UploaderThreadMock,
    robot_inspection_service_thread: Thread,
    mocker: MockerFixture,
) -> None:
    robot_inspection_service_thread.start()
    mocker.patch.object(StubRobot, "robot_status", return_value=RobotStatus.Home)

    storage_mock: StorageInterface = container.storage_handlers(List[StorageInterface])[
        0
    ]

    mocker.patch.object(settings, "ROBOT_API_BATTERY_POLL_INTERVAL", 0.01)
    mocker.patch.object(settings, "FSM_SLEEP_TIME", 0.01)

    mission: Mission = Mission(name="Dummy misson", tasks=[StubTask.take_image()])
    scheduling_utilities: SchedulingUtilities = container.scheduling_utilities()

    mocker.patch.object(settings, "RETURN_HOME_DELAY", 0.01)
    state_machine_thread.start()
    uploader_thread.start()

    robot_service_thread.start()
    wait_until(
        lambda: States.UnknownStatus
        in state_machine_thread.state_machine.transitions_list
    )
    scheduling_utilities.start_mission(mission=mission)

    expected_transitions = deque(
        [
            States.UnknownStatus,
            States.Home,
            States.Monitor,
            States.AwaitNextMission,
            States.ReturningHome,
            States.Home,
        ]
    )
    wait_until(
        lambda: state_machine_thread.state_machine.transitions_list
        == expected_transitions
        and len(storage_mock.stored_inspections) == 1  # type: ignore
    )


def test_state_machine_with_unsuccessful_collection(
    container: ApplicationContainer,
    mocker: MockerFixture,
    state_machine_thread: StateMachineThreadMock,
    robot_service_thread: RobotServiceThreadMock,
    uploader_thread: UploaderThreadMock,
) -> None:
    mocker.patch.object(StubRobot, "robot_status", return_value=RobotStatus.Home)

    storage_mock: StorageInterface = container.storage_handlers(List[StorageInterface])[
        0
    ]

    mocker.patch.object(StubRobot, "get_inspection", return_value=None)

    mocker.patch.object(settings, "ROBOT_API_BATTERY_POLL_INTERVAL", 0.01)
    mocker.patch.object(settings, "ROBOT_API_STATUS_POLL_INTERVAL", 0.01)
    mocker.patch.object(settings, "FSM_SLEEP_TIME", 0.01)
    mocker.patch.object(settings, "RETURN_HOME_DELAY", 0.01)
    state_machine_thread.start()
    robot_service_thread.start()
    uploader_thread.start()
    wait_until(
        lambda: States.Home in state_machine_thread.state_machine.transitions_list
    )
    mission: Mission = Mission(name="Dummy misson", tasks=[StubTask.take_image()])
    scheduling_utilities: SchedulingUtilities = container.scheduling_utilities()
    scheduling_utilities.start_mission(mission=mission)

    expected_transitions = deque(
        [
            States.UnknownStatus,
            States.Home,
            States.Monitor,
            States.AwaitNextMission,
            States.ReturningHome,
            States.Home,
        ]
    )
    wait_until(
        lambda: state_machine_thread.state_machine.transitions_list
        == expected_transitions
    )
    # Mission completion is observable, but confirming no delayed upload requires
    # a bounded quiet window.
    time.sleep(0.1)
    expected_stored_items = 0
    assert len(storage_mock.stored_inspections) == expected_stored_items  # type: ignore


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

    mocker.patch.object(settings, "FSM_SLEEP_TIME", 0.01)

    state_machine_thread.start()
    robot_service_thread.start()
    wait_until(
        lambda: States.UnknownStatus
        in state_machine_thread.state_machine.transitions_list
    )
    scheduling_utilities.return_home()
    wait_until(
        lambda: state_machine_thread.state_machine.current_state.name
        == States.ReturningHome
    )
    scheduling_utilities.start_mission(mission=mission)
    expected_transitions = deque(
        [
            States.UnknownStatus,
            States.Home,
            States.ReturningHome,
            States.StoppingReturnHome,
            States.Monitor,
        ]
    )
    wait_until(
        lambda: state_machine_thread.state_machine.transitions_list
        == expected_transitions
    )
    assert (
        not state_machine_thread.state_machine.events.api_requests.start_mission.request.has_event()
    )


def test_state_machine_failed_to_initiate_mission_and_return_home(
    container: ApplicationContainer,
    state_machine_thread: StateMachineThreadMock,
    robot_service_thread: RobotServiceThreadMock,
    mocker: MockerFixture,
) -> None:
    mocker.patch.object(settings, "ROBOT_API_BATTERY_POLL_INTERVAL", 0.01)
    mocker.patch.object(settings, "FSM_SLEEP_TIME", 0.01)
    mocker.patch.object(settings, "RETURN_HOME_DELAY", 0.01)

    robot_service_thread.robot_service.robot = StubRobotInitiateMissionRaisesException()

    task_1: Task = TakeImage(target=stub_pose().position, robot_pose=stub_pose())
    task_2: Task = TakeImage(target=stub_pose().position, robot_pose=stub_pose())
    mission: Mission = Mission(name="Dummy misson", tasks=[task_1, task_2])

    state_machine_thread.start()
    robot_service_thread.start()

    # TODO: check mqtt
    wait_until(
        lambda: States.UnknownStatus
        in state_machine_thread.state_machine.transitions_list
    )
    scheduling_utilities: SchedulingUtilities = container.scheduling_utilities()
    scheduling_utilities.start_mission(mission=mission)

    expected_transitions = deque(
        [
            States.UnknownStatus,
            States.AwaitNextMission,
            States.Monitor,
            States.AwaitNextMission,
            States.ReturningHome,
            States.ReturningHome,
            States.ReturningHome,
            States.ReturningHome,
            States.ReturningHome,
            States.InterventionNeeded,
        ]
    )
    wait_until(
        lambda: state_machine_thread.state_machine.transitions_list
        == expected_transitions,
        timeout=10.0,
    )


def test_state_machine_battery_too_low_to_start_mission(
    container: ApplicationContainer,
    state_machine_thread: StateMachineThreadMock,
    robot_service_thread: RobotServiceThreadMock,
    mocker: MockerFixture,
) -> None:
    mocker.patch.object(settings, "FSM_SLEEP_TIME", 0.01)
    mocker.patch.object(settings, "ROBOT_API_BATTERY_POLL_INTERVAL", 0.01)
    mocker.patch.object(settings, "ROBOT_API_STATUS_POLL_INTERVAL", 0.01)
    state_machine_thread.start()
    mocker.patch.object(StubRobot, "robot_status", return_value=RobotStatus.Home)
    mocker.patch.object(StubRobot, "get_battery_level", return_value=10.0)
    robot_service_thread.start()

    expected_transitions = deque(
        [
            States.UnknownStatus,
            States.Home,
            States.Recharging,
        ]
    )
    wait_until(
        lambda: state_machine_thread.state_machine.transitions_list
        == expected_transitions
    )
