from typing import Optional, cast

from isar.config.settings import settings
from isar.eventhandlers.eventhandler import EventHandlerMapping, State
from isar.state_machine.state_machine import StateMachine
from isar.state_machine.states.await_next_mission import AwaitNextMission
from isar.state_machine.states.going_to_lockdown import GoingToLockdown
from isar.state_machine.states.going_to_recharging import GoingToRecharging
from isar.state_machine.states.intervention_needed import InterventionNeeded
from isar.state_machine.states.return_home_paused import ReturnHomePaused
from isar.state_machine.states.returning_home import ReturningHome
from isar.state_machine.states.stopping_go_to_lockdown import StoppingGoToLockdown
from robot_interface.models.exceptions.robot_exceptions import ErrorMessage, ErrorReason


def test_transition_from_return_home_paused_to_going_to_lockdown(
    sync_state_machine: StateMachine,
) -> None:
    sync_state_machine.current_state = ReturnHomePaused(sync_state_machine)

    return_home_paused_state: State = cast(State, sync_state_machine.current_state)
    event_handler: Optional[EventHandlerMapping] = (
        return_home_paused_state.get_event_handler_by_name("send_to_lockdown_event")
    )

    transition = event_handler.handler(True)

    sync_state_machine.current_state = transition(sync_state_machine)

    assert sync_state_machine.events.api_requests.send_to_lockdown.response.has_event()
    assert type(sync_state_machine.current_state) is GoingToLockdown

    going_to_lockdown_state: State = cast(State, sync_state_machine.current_state)
    lockdown_event_handler: Optional[EventHandlerMapping] = (
        going_to_lockdown_state.get_event_handler_by_name("mission_failed_to_resume")
    )
    assert lockdown_event_handler is not None

    transition = lockdown_event_handler.handler(
        ErrorMessage(
            error_description="Test going to lockdown resume return to home mission failed",
            error_reason=ErrorReason.RobotCommunicationException,
        )
    )

    sync_state_machine.current_state = transition(sync_state_machine)
    assert type(sync_state_machine.current_state) is InterventionNeeded


def test_stopping_lockdown_transitions_to_going_to_lockdown(
    sync_state_machine: StateMachine,
) -> None:
    sync_state_machine.shared_state.robot_battery_level.trigger_event(10.0)
    sync_state_machine.current_state = StoppingGoToLockdown(
        sync_state_machine, "mission_id"
    )

    stopping_go_to_lockdown_state: State = cast(State, sync_state_machine.current_state)
    event_handler: Optional[EventHandlerMapping] = (
        stopping_go_to_lockdown_state.get_event_handler_by_name("successful_stop_event")
    )

    assert event_handler is not None

    transition = event_handler.handler(True)

    assert (
        sync_state_machine.events.api_requests.send_to_lockdown.response.check().lockdown_started
    )

    assert not sync_state_machine.events.mqtt_queue.empty()
    mqtt_message = sync_state_machine.events.mqtt_queue.get(block=False)
    assert mqtt_message is not None
    mqtt_payload_topic = mqtt_message[0]
    assert mqtt_payload_topic is settings.TOPIC_ISAR_MISSION_ABORTED

    sync_state_machine.current_state = transition(sync_state_machine)
    assert type(sync_state_machine.current_state) is GoingToLockdown


def test_return_home_transitions_to_going_to_lockdown(
    sync_state_machine: StateMachine,
) -> None:
    sync_state_machine.shared_state.robot_battery_level.trigger_event(10.0)
    sync_state_machine.current_state = ReturningHome(sync_state_machine)

    returning_home_state: State = cast(State, sync_state_machine.current_state)
    event_handler: Optional[EventHandlerMapping] = (
        returning_home_state.get_event_handler_by_name("send_to_lockdown_event")
    )

    assert event_handler is not None

    transition = event_handler.handler(True)

    sync_state_machine.current_state = transition(sync_state_machine)
    assert type(sync_state_machine.current_state) is GoingToLockdown


def test_recharging_transitions_to_going_to_lockdown(
    sync_state_machine: StateMachine,
) -> None:
    sync_state_machine.shared_state.robot_battery_level.trigger_event(10.0)
    sync_state_machine.current_state = GoingToRecharging(sync_state_machine)

    going_to_recharging_state: State = cast(State, sync_state_machine.current_state)
    event_handler: Optional[EventHandlerMapping] = (
        going_to_recharging_state.get_event_handler_by_name("send_to_lockdown_event")
    )

    assert event_handler is not None

    transition = event_handler.handler(True)

    sync_state_machine.current_state = transition(sync_state_machine)
    assert type(sync_state_machine.current_state) is GoingToLockdown


def test_await_next_mission_transitions_to_going_to_lockdown(
    sync_state_machine: StateMachine,
) -> None:
    sync_state_machine.shared_state.robot_battery_level.trigger_event(10.0)
    sync_state_machine.current_state = AwaitNextMission(sync_state_machine)

    await_next_mission_state: State = cast(State, sync_state_machine.current_state)
    event_handler: Optional[EventHandlerMapping] = (
        await_next_mission_state.get_event_handler_by_name("send_to_lockdown_event")
    )

    assert event_handler is not None

    transition = event_handler.handler(True)

    assert sync_state_machine.events.api_requests.send_to_lockdown.response.check()
    sync_state_machine.current_state = transition(sync_state_machine)
    assert type(sync_state_machine.current_state) is GoingToLockdown
