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

    event_handler: EventHandlerMapping = current_state.get_event_handler_by_event(
        events.api_requests.release_from_lockdown.request
    )

    transition = event_handler.handler(EmptyMessage())

    assert events.api_requests.release_from_lockdown.response.check()
    current_state = transition(events)
    assert type(current_state) is Home


def test_state_machine_with_return_home_failure_successful_retries(
    events: Events,
) -> None:
    current_state = ReturningHome(events)

    event_handler_success: EventHandlerMapping = (
        current_state.get_event_handler_by_event(
            events.robot_service_events.mission_succeeded
        )
    )
    event_handler_failure: EventHandlerMapping = (
        current_state.get_event_handler_by_event(
            events.robot_service_events.mission_failed
        )
    )

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

    event_handler: EventHandlerMapping = current_state.get_event_handler_by_event(
        events.robot_service_events.robot_status_update
    )

    transition = event_handler.handler(RobotStatus.Home)

    assert transition is not None

    current_state = transition(events)
    assert type(current_state) is Home


def test_recharging_goes_to_home_when_battery_high(events: Events) -> None:
    current_state = Recharging(events)

    event_handler: EventHandlerMapping = current_state.get_event_handler_by_event(
        events.robot_service_events.battery_above_recharge_threshold
    )

    transition = event_handler.handler(EmptyMessage())

    current_state = transition(events)

    assert type(current_state) is Home
