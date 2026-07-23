from isar.config.settings import settings
from isar.models.events import Events
from isar.state_machine.state import EventHandlerMapping
from isar.state_machine.states.going_to_lockdown import GoingToLockdown
from isar.state_machine.states.going_to_recharging import GoingToRecharging
from isar.state_machine.states.intervention_needed import InterventionNeeded
from isar.state_machine.states.returning_home import ReturningHome
from robot_interface.models.exceptions.robot_exceptions import ErrorMessage, ErrorReason
from robot_interface.models.mission.status import RobotStatus


def test_going_to_recharging_goes_to_intervention_needed(events: Events) -> None:
    current_state = GoingToRecharging(events)
    event_handler: EventHandlerMapping | None = current_state.get_event_handler_by_name(
        "mission_failed_event"
    )

    assert event_handler is not None

    transition = event_handler.handler(
        ErrorMessage(
            error_reason=ErrorReason.RobotUnknownErrorException,
            error_description="test",
        )
    )

    current_state = transition(events)
    assert type(current_state) is InterventionNeeded


def test_going_to_lockdown_task_failed_transitions_to_intervention_needed(
    events: Events,
) -> None:
    current_state = GoingToLockdown(events)

    event_handler: EventHandlerMapping | None = current_state.get_event_handler_by_name(
        "mission_failed_event"
    )

    assert event_handler is not None

    transition = event_handler.handler(
        ErrorMessage(
            error_reason=ErrorReason.RobotUnknownErrorException,
            error_description="test",
        )
    )

    current_state = transition(events)
    assert type(current_state) is InterventionNeeded


def test_going_to_lockdown_mission_failed_transitions_to_intervention_needed(
    events: Events,
) -> None:
    current_state = GoingToLockdown(events)

    event_handler: EventHandlerMapping | None = current_state.get_event_handler_by_name(
        "mission_failed_event"
    )

    assert event_handler is not None

    # The type of error reason is not important for this test
    transition = event_handler.handler(
        ErrorMessage(error_description="", error_reason=ErrorReason.RobotAPIException)
    )

    current_state = transition(events)
    assert type(current_state) is InterventionNeeded


def test_state_machine_with_return_home_failure(events: Events) -> None:
    current_state = ReturningHome(events)

    failure_event_handler: EventHandlerMapping | None

    for i in range(settings.RETURN_HOME_RETRY_LIMIT - 1):

        failure_event_handler = current_state.get_event_handler_by_name(
            "mission_failed_event"
        )

        transition = failure_event_handler.handler(
            ErrorMessage(
                error_reason=ErrorReason.RobotUnknownErrorException,
                error_description="test",
            )
        )

        assert transition is not None  # type: ignore
        current_state = transition(events)
        assert type(current_state) is ReturningHome

    failure_event_handler = current_state.get_event_handler_by_name(
        "mission_failed_event"
    )

    transition = failure_event_handler.handler(
        ErrorMessage(
            error_reason=ErrorReason.RobotUnknownErrorException,
            error_description="test",
        )
    )

    current_state = transition(events)
    assert type(current_state) is InterventionNeeded


def test_intervention_needed_transitions_does_not_transition_if_status_is_not_home(
    events: Events,
) -> None:
    current_state = InterventionNeeded(events)

    event_handler: EventHandlerMapping | None = current_state.get_event_handler_by_name(
        "robot_status_event"
    )
    assert event_handler is not None

    statuses = [
        RobotStatus.Available,
        RobotStatus.TeleOperation,
        RobotStatus.Busy,
        RobotStatus.Offline,
    ]
    for status in statuses:
        transition = event_handler.handler(status)

        assert transition is None  # type: ignore
