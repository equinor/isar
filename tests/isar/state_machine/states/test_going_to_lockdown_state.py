from isar.models.events import EmptyMessage, Events
from isar.state_machine.state import EventHandlerMapping, State
from isar.state_machine.states.await_next_mission import AwaitNextMission
from isar.state_machine.states.going_to_recharging import GoingToRecharging
from isar.state_machine.states.lockdown_with_mission import LockdownWithMission
from isar.state_machine.states.return_home_paused import ReturnHomePaused
from isar.state_machine.states.returning_home import ReturningHome
from isar.state_machine.states.stopping_go_to_lockdown import StoppingGoToLockdown
from isar.state_machine.states_enum import States
from robot_interface.models.exceptions.robot_exceptions import ErrorMessage, ErrorReason
from robot_interface.models.mission.mission import Mission
from tests.test_mocks.task import StubTask


def test_transition_from_return_home_paused_to_going_to_lockdown(
    events: Events,
) -> None:
    current_state: State = ReturnHomePaused(events)

    event_handler: EventHandlerMapping = current_state.get_event_handler_by_event(
        events.api_requests.send_to_lockdown.request
    )

    transition = event_handler.handler(EmptyMessage())

    current_state = transition(events)

    assert events.api_requests.send_to_lockdown.response.has_event()
    assert current_state.name is States.GoingToLockdown

    lockdown_event_handler: EventHandlerMapping = (
        current_state.get_event_handler_by_event(
            events.robot_service_events.mission_failed_to_resume
        )
    )

    transition = lockdown_event_handler.handler(
        ErrorMessage(
            error_description="Test going to lockdown resume return to home mission failed",
            error_reason=ErrorReason.RobotCommunicationException,
        )
    )

    current_state = transition(events)
    assert current_state.name is States.InterventionNeeded


def test_stopping_lockdown_transitions_to_going_to_lockdown(events: Events) -> None:
    current_state = StoppingGoToLockdown(events, "mission_id")

    event_handler: EventHandlerMapping = current_state.get_event_handler_by_event(
        events.robot_service_events.mission_successfully_stopped
    )

    aborted_mission: Mission = Mission(
        id="id",
        name="Dummy misson",
        tasks=[StubTask.take_image() for _ in range(20)],
    )

    transition = event_handler.handler(aborted_mission)

    current_state = transition(events)
    assert current_state.name is States.GoingToLockdownWithMission

    assert events.api_requests.send_to_lockdown.response.check().lockdown_started

    assert events.mqtt_queue.empty()


def test_continuing_mission_after_lockdown(events: Events) -> None:
    aborted_mission: Mission = Mission(
        id="id",
        name="Dummy misson",
        tasks=[StubTask.take_image() for _ in range(20)],
    )

    current_state = LockdownWithMission(events, aborted_mission)

    event_handler: EventHandlerMapping = current_state.get_event_handler_by_event(
        events.api_requests.release_from_lockdown.request
    )

    transition = event_handler.handler(EmptyMessage())

    current_state = transition(events)
    assert current_state.name is States.Monitor

    assert events.api_requests.release_from_lockdown.response.has_event()

    assert not events.mqtt_queue.empty()


def test_return_home_transitions_to_going_to_lockdown(events: Events) -> None:
    current_state = ReturningHome(events)

    event_handler: EventHandlerMapping = current_state.get_event_handler_by_event(
        events.api_requests.send_to_lockdown.request
    )

    transition = event_handler.handler(EmptyMessage())

    current_state = transition(events)
    assert current_state.name is States.GoingToLockdown


def test_recharging_transitions_to_going_to_lockdown(events: Events) -> None:
    current_state = GoingToRecharging(events)

    event_handler: EventHandlerMapping = current_state.get_event_handler_by_event(
        events.api_requests.send_to_lockdown.request
    )

    transition = event_handler.handler(EmptyMessage())

    current_state = transition(events)
    assert current_state.name is States.GoingToLockdown


def test_await_next_mission_transitions_to_going_to_lockdown(events: Events) -> None:
    current_state = AwaitNextMission(events)

    event_handler: EventHandlerMapping = current_state.get_event_handler_by_event(
        events.api_requests.send_to_lockdown.request
    )

    transition = event_handler.handler(EmptyMessage())

    current_state = transition(events)
    assert current_state.name is States.GoingToLockdown

    assert events.api_requests.send_to_lockdown.response.check()
