from collections import deque

from pytest_mock import MockerFixture

from isar.config.settings import settings
from isar.models.events import Events
from isar.modules import ApplicationContainer
from isar.services.utilities.scheduling_utilities import SchedulingUtilities
from isar.state_machine.state import EventHandlerMapping
from isar.state_machine.states.await_next_mission import AwaitNextMission
from isar.state_machine.states.paused import Paused
from isar.state_machine.states.resuming import Resuming
from isar.state_machine.states.resuming_return_home import ResumingReturnHome
from isar.state_machine.states.return_home_paused import ReturnHomePaused
from isar.state_machine.states.unknown_status import UnknownStatus
from isar.state_machine.states_enum import States
from robot_interface.models.exceptions.robot_exceptions import ErrorMessage, ErrorReason
from robot_interface.models.mission.mission import Mission
from robot_interface.models.mission.status import MissionStatus, RobotStatus
from tests.test_mocks.robot_interface import StubRobot
from tests.test_mocks.state_machine_mocks import (
    RobotServiceThreadMock,
    StateMachineThreadMock,
    UploaderThreadMock,
)
from tests.test_mocks.task import StubTask
from tests.wait import wait_until


def test_state_machine_with_successful_mission_stop(
    container: ApplicationContainer,
    robot_service_thread: RobotServiceThreadMock,
    state_machine_thread: StateMachineThreadMock,
    uploader_thread: UploaderThreadMock,
    mocker: MockerFixture,
) -> None:
    mocker.patch.object(StubRobot, "robot_status", return_value=RobotStatus.Home)
    mocker.patch.object(
        StubRobot, "mission_status", return_value=MissionStatus.InProgress
    )

    mocker.patch.object(settings, "ROBOT_API_BATTERY_POLL_INTERVAL", 0.01)
    mocker.patch.object(settings, "ROBOT_API_STATUS_POLL_INTERVAL", 0.01)
    mocker.patch.object(settings, "FSM_SLEEP_TIME", 0.01)
    mocker.patch.object(settings, "RETURN_HOME_DELAY", 15)

    mission: Mission = Mission(
        name="Dummy misson", tasks=[StubTask.take_image() for _ in range(0, 20)]
    )

    scheduling_utilities: SchedulingUtilities = container.scheduling_utilities()

    state_machine_thread.start()
    robot_service_thread.start()
    uploader_thread.start()
    wait_until(
        lambda: States.Home in state_machine_thread.state_machine.transitions_list
    )
    scheduling_utilities.start_mission(mission=mission)
    wait_until(
        lambda: state_machine_thread.state_machine.state_event.check() == States.Monitor
    )
    scheduling_utilities.stop_mission(mission_id=mission.id)

    expected_transitions = deque(
        [
            States.UnknownStatus,
            States.Home,
            States.Monitor,
            States.Stopping,
            States.AwaitNextMission,
        ]
    )
    wait_until(
        lambda: state_machine_thread.state_machine.transitions_list
        == expected_transitions
    )


def test_transition_from_resuming_to_paused(events: Events) -> None:
    current_state = Resuming(events, "mission_id")

    event_handler: EventHandlerMapping | None = current_state.get_event_handler_by_name(
        "failed_resume_event"
    )

    assert event_handler is not None

    transition = event_handler.handler(
        ErrorMessage(
            error_reason=ErrorReason.RobotUnknownErrorException, error_description=""
        )
    )

    current_state = transition(events)
    assert type(current_state) is Paused


def test_unknown_status_transitions_to_await_next_mission_if_it_was_already_available(
    events: Events,
) -> None:
    current_state = UnknownStatus(events)

    event_handler: EventHandlerMapping | None = current_state.get_event_handler_by_name(
        "robot_status_event"
    )
    assert event_handler is not None

    transition = event_handler.handler(RobotStatus.Available)

    current_state = transition(events)
    assert type(current_state) is AwaitNextMission


def test_transition_from_resuming_return_home_to_await_next_mission(
    events: Events,
) -> None:
    current_state = ResumingReturnHome(events)

    event_handler: EventHandlerMapping | None = current_state.get_event_handler_by_name(
        "failed_resume_event"
    )

    assert event_handler is not None

    transition = event_handler.handler(
        ErrorMessage(
            error_reason=ErrorReason.RobotUnknownErrorException, error_description=""
        )
    )

    current_state = transition(events)
    assert type(current_state) is ReturnHomePaused
