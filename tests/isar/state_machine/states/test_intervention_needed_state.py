from typing import Optional, cast

from isar.config.settings import settings
from isar.eventhandlers.eventhandler import EventHandlerBase, EventHandlerMapping
from isar.state_machine.state_machine import StateMachine
from robot_interface.models.exceptions.robot_exceptions import ErrorMessage, ErrorReason
from robot_interface.models.mission.mission import Mission
from robot_interface.models.mission.status import MissionStatus, RobotStatus
from robot_interface.models.mission.task import TakeImage, Task
from tests.test_mocks.pose import DummyPose


def test_going_to_recharging_goes_to_intervention_needed(
    sync_state_machine: StateMachine,
) -> None:
    sync_state_machine.state = sync_state_machine.going_to_recharging_state.name  # type: ignore
    going_to_recharging_state: EventHandlerBase = cast(
        EventHandlerBase, sync_state_machine.going_to_recharging_state
    )
    event_handler: Optional[EventHandlerMapping] = (
        going_to_recharging_state.get_event_handler_by_name("mission_status_event")
    )

    assert event_handler is not None

    event_handler.event.trigger_event(MissionStatus.Failed)
    transition = event_handler.handler(event_handler.event)

    assert transition is sync_state_machine.return_home_failed  # type: ignore
    transition()
    assert sync_state_machine.state is sync_state_machine.intervention_needed_state.name  # type: ignore


def test_going_to_lockdown_task_failed_transitions_to_intervention_needed(
    sync_state_machine: StateMachine,
) -> None:
    sync_state_machine.shared_state.robot_battery_level.trigger_event(10.0)
    sync_state_machine.state = sync_state_machine.going_to_lockdown_state.name  # type: ignore

    going_to_lockdown_state: EventHandlerBase = cast(
        EventHandlerBase, sync_state_machine.going_to_lockdown_state
    )
    event_handler: Optional[EventHandlerMapping] = (
        going_to_lockdown_state.get_event_handler_by_name("mission_status_event")
    )

    assert event_handler is not None

    event_handler.event.trigger_event(MissionStatus.Failed)
    transition = event_handler.handler(event_handler.event)

    assert transition is sync_state_machine.lockdown_mission_failed  # type: ignore
    transition()
    assert sync_state_machine.state is sync_state_machine.intervention_needed_state.name  # type: ignore


def test_going_to_lockdown_mission_failed_transitions_to_intervention_needed(
    sync_state_machine: StateMachine,
) -> None:
    task_1: Task = TakeImage(
        target=DummyPose.default_pose().position, robot_pose=DummyPose.default_pose()
    )
    sync_state_machine.shared_state.mission_id.trigger_event(
        Mission(name="Dummy misson", tasks=[task_1])
    )
    sync_state_machine.shared_state.robot_battery_level.trigger_event(10.0)
    sync_state_machine.state = sync_state_machine.going_to_lockdown_state.name  # type: ignore

    going_to_lockdown_state: EventHandlerBase = cast(
        EventHandlerBase, sync_state_machine.going_to_lockdown_state
    )
    event_handler: Optional[EventHandlerMapping] = (
        going_to_lockdown_state.get_event_handler_by_name("mission_failed_event")
    )

    assert event_handler is not None

    # The type of error reason is not important for this test
    event_handler.event.trigger_event(
        ErrorMessage(error_description="", error_reason=ErrorReason.RobotAPIException)
    )
    transition = event_handler.handler(event_handler.event)

    assert transition is sync_state_machine.lockdown_mission_failed  # type: ignore
    transition()
    assert sync_state_machine.state is sync_state_machine.intervention_needed_state.name  # type: ignore


def test_state_machine_with_return_home_failure(
    sync_state_machine: StateMachine,
) -> None:
    sync_state_machine.shared_state.robot_battery_level.trigger_event(80.0)
    sync_state_machine.state = sync_state_machine.returning_home_state.name  # type: ignore

    returning_home_state: EventHandlerBase = cast(
        EventHandlerBase, sync_state_machine.returning_home_state
    )
    event_handler: Optional[EventHandlerMapping] = (
        returning_home_state.get_event_handler_by_name("mission_status_event")
    )

    # We do not retry return home missions if the robot is not ready for another mission
    sync_state_machine.shared_state.robot_status.trigger_event(RobotStatus.Available)

    assert event_handler is not None

    for i in range(settings.RETURN_HOME_RETRY_LIMIT - 1):

        event_handler.event.trigger_event(MissionStatus.Failed)
        transition = event_handler.handler(event_handler.event)

        assert transition is None  # type: ignore
        assert (
            sync_state_machine.returning_home_state.failed_return_home_attempts == i + 1
        )

    event_handler.event.trigger_event(MissionStatus.Failed)
    transition = event_handler.handler(event_handler.event)

    assert transition is sync_state_machine.return_home_failed  # type: ignore

    transition()
    assert sync_state_machine.state is sync_state_machine.intervention_needed_state.name  # type: ignore


def test_return_home_mission_failed_transitions_to_intervention_needed(
    sync_state_machine: StateMachine,
) -> None:
    sync_state_machine.state = sync_state_machine.returning_home_state.name  # type: ignore

    returning_home_state: EventHandlerBase = cast(
        EventHandlerBase, sync_state_machine.returning_home_state
    )
    event_handler: Optional[EventHandlerMapping] = (
        returning_home_state.get_event_handler_by_name("mission_failed_event")
    )
    assert event_handler is not None

    event_handler.event.trigger_event(
        ErrorMessage(
            error_description="Test return to home mission failed",
            error_reason=ErrorReason.RobotMissionStatusException,
        )
    )
    transition = event_handler.handler(event_handler.event)

    assert transition is sync_state_machine.return_home_failed  # type: ignore
    transition()
    assert sync_state_machine.state is sync_state_machine.intervention_needed_state.name  # type: ignore


def test_intervention_needed_transitions_does_not_transition_if_status_is_not_home(
    sync_state_machine: StateMachine,
) -> None:
    sync_state_machine.state = sync_state_machine.intervention_needed_state.name  # type: ignore

    intervention_needed_state: EventHandlerBase = cast(
        EventHandlerBase, sync_state_machine.intervention_needed_state
    )
    event_handler: Optional[EventHandlerMapping] = (
        intervention_needed_state.get_event_handler_by_name("robot_status_event")
    )
    assert event_handler is not None

    statuses = [
        RobotStatus.Available,
        RobotStatus.BlockedProtectiveStop,
        RobotStatus.Busy,
        RobotStatus.Paused,
        RobotStatus.Offline,
    ]
    for status in statuses:
        sync_state_machine.shared_state.robot_status.update(status)

        event_handler.event.trigger_event(True)
        transition = event_handler.handler(event_handler.event)

        assert transition is None  # type: ignore
