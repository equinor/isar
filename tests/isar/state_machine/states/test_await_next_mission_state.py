import time
from collections import deque
from typing import Optional, cast

from isar.eventhandlers.eventhandler import EventHandlerBase, EventHandlerMapping
from isar.modules import ApplicationContainer
from isar.robot.robot_status import RobotStatusThread
from isar.services.utilities.scheduling_utilities import SchedulingUtilities
from isar.state_machine.state_machine import StateMachine
from isar.state_machine.states_enum import States
from robot_interface.models.mission.mission import Mission
from robot_interface.models.mission.status import MissionStatus, RobotStatus
from tests.test_mocks.robot_interface import StubRobot
from tests.test_mocks.state_machine_mocks import (
    RobotServiceThreadMock,
    StateMachineThreadMock,
    UploaderThreadMock,
)
from tests.test_mocks.task import StubTask


def test_state_machine_with_successful_mission_stop(
    container: ApplicationContainer,
    robot_service_thread: RobotServiceThreadMock,
    state_machine_thread: StateMachineThreadMock,
    uploader_thread: UploaderThreadMock,
    mocker,
) -> None:
    mocker.patch.object(StubRobot, "robot_status", return_value=RobotStatus.Home)
    mocker.patch.object(
        StubRobot, "mission_status", return_value=MissionStatus.InProgress
    )

    mocker.patch.object(
        RobotStatusThread, "_is_ready_to_poll_for_status", return_value=True
    )

    # Set the return home delay to a higher value than the test needs to run
    state_machine_thread.state_machine.await_next_mission_state.timers[
        0
    ].timeout_in_seconds = 15

    mission: Mission = Mission(
        name="Dummy misson", tasks=[StubTask.take_image() for _ in range(0, 20)]
    )

    scheduling_utilities: SchedulingUtilities = container.scheduling_utilities()

    state_machine_thread.start()
    robot_service_thread.start()
    uploader_thread.start()
    time.sleep(1)
    scheduling_utilities.start_mission(mission=mission)
    time.sleep(0.5)
    scheduling_utilities.stop_mission(mission_id=mission.id)
    time.sleep(3)  # Allow enough time to stop the mission

    assert state_machine_thread.state_machine.transitions_list == deque(
        [
            States.UnknownStatus,
            States.Home,
            States.Monitor,
            States.Stopping,
            States.AwaitNextMission,
        ]
    )


def test_transition_from_resuming_to_await_next_mission(
    sync_state_machine: StateMachine,
) -> None:
    sync_state_machine.state = sync_state_machine.resuming_state.name  # type: ignore

    resuming_state: EventHandlerBase = cast(
        EventHandlerBase, sync_state_machine.resuming_state
    )
    event_handler: Optional[EventHandlerMapping] = (
        resuming_state.get_event_handler_by_name("failed_resume_event")
    )

    assert event_handler is not None

    event_handler.event.trigger_event(True)
    transition = event_handler.handler(event_handler.event)

    assert transition is sync_state_machine.mission_resuming_failed  # type: ignore

    transition()
    assert sync_state_machine.state is sync_state_machine.await_next_mission_state.name  # type: ignore


def test_unknown_status_transitions_to_await_next_mission_if_it_was_already_available(
    sync_state_machine: StateMachine, mocker
) -> None:
    sync_state_machine.shared_state.robot_status.trigger_event(RobotStatus.Available)
    # Make sure that we have not changed robot status
    sync_state_machine.events.robot_service_events.robot_status_changed.consume_event()

    mocker.patch.object(EventHandlerBase, "_run", return_value=None)
    sync_state_machine.state = sync_state_machine.unknown_status_state.name  # type: ignore

    unknown_status_state: EventHandlerBase = cast(
        EventHandlerBase, sync_state_machine.unknown_status_state
    )
    unknown_status_state.start()
    event_handler: Optional[EventHandlerMapping] = (
        unknown_status_state.get_event_handler_by_name("robot_status_event")
    )
    assert event_handler is not None

    transition = event_handler.handler(event_handler.event)

    assert transition is sync_state_machine.robot_status_available  # type: ignore
    transition()
    assert sync_state_machine.state is sync_state_machine.await_next_mission_state.name  # type: ignore


def test_transition_from_resuming_return_home_to_await_next_mission(
    sync_state_machine: StateMachine,
) -> None:
    sync_state_machine.state = sync_state_machine.resuming_return_home_state.name  # type: ignore

    resuming_return_home_state: EventHandlerBase = cast(
        EventHandlerBase, sync_state_machine.resuming_return_home_state
    )
    event_handler: Optional[EventHandlerMapping] = (
        resuming_return_home_state.get_event_handler_by_name("failed_resume_event")
    )

    assert event_handler is not None

    event_handler.event.trigger_event(True)
    transition = event_handler.handler(event_handler.event)

    assert transition is sync_state_machine.return_home_mission_resuming_failed  # type: ignore

    transition()
    assert sync_state_machine.state is sync_state_machine.await_next_mission_state.name  # type: ignore
