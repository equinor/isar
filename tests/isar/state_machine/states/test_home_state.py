from isar.models.events import EmptyMessage, Events
from isar.state_machine.state import EventHandlerMapping
from isar.state_machine.states.home import Home
from isar.state_machine.states.intervention_needed import InterventionNeeded
from isar.state_machine.states.lockdown import Lockdown
from isar.state_machine.states.recharging import Recharging
from isar.state_machine.states.returning_home import ReturningHome
from robot_interface.models.exceptions.robot_exceptions import ErrorMessage, ErrorReason
from robot_interface.models.mission.status import RobotStatus


def test_lockdown_transitions_to_home(events: Events) -> None:
    current_state = Lockdown(events)

    event_handler: EventHandlerMapping | None = current_state.get_event_handler_by_name(
        "release_from_lockdown"
    )

    assert event_handler is not None

    transition = event_handler.handler(EmptyMessage())

    assert events.api_requests.release_from_lockdown.response.check()
    current_state = transition(events)
    assert type(current_state) is Home


def test_state_machine_with_return_home_failure_successful_retries(
    events: Events,
) -> None:
    current_state = ReturningHome(events)

    event_handler_success: EventHandlerMapping | None = (
        current_state.get_event_handler_by_name("mission_succeeded_event")
    )
    event_handler_failure: EventHandlerMapping | None = (
        current_state.get_event_handler_by_name("mission_failed_event")
    )

    assert event_handler_success is not None
    assert event_handler_failure is not None

    transition = event_handler_failure.handler(
        ErrorMessage(
            error_reason=ErrorReason.RobotUnknownErrorException,
            error_description="test",
        )
    )

    assert transition is not None  # type: ignore
    assert type(current_state) is ReturningHome

    transition = event_handler_success.handler(EmptyMessage())

    current_state = transition(events)
    assert type(current_state) is Home


def test_intervention_needed_transitions_to_home_if_robot_is_home(
    events: Events,
) -> None:
    current_state = InterventionNeeded(events)

    event_handler: EventHandlerMapping | None = current_state.get_event_handler_by_name(
        "robot_status_event"
    )
    assert event_handler is not None

    transition = event_handler.handler(RobotStatus.Home)

    assert transition is not None

    current_state = transition(events)
    assert type(current_state) is Home


def test_recharging_goes_to_home_when_battery_high(events: Events) -> None:
    current_state = Recharging(events)

    event_handler: EventHandlerMapping | None = current_state.get_event_handler_by_name(
        "robot_battery_above_recharge_threshold_event"
    )

    assert event_handler is not None

    transition = event_handler.handler(EmptyMessage())

    current_state = transition(events)

    assert type(current_state) is Home
