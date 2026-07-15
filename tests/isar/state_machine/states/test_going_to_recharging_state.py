from typing import cast

from isar.eventhandlers.state import EventHandlerMapping, State
from isar.models.events import AbortedMission, EmptyMessage
from isar.state_machine.state_machine import StateMachine
from isar.state_machine.states.going_to_recharging import GoingToRecharging
from isar.state_machine.states.going_to_recharging_with_mission import (
    GoingToRechargingWithMission,
)
from isar.state_machine.states.returning_home import ReturningHome
from isar.state_machine.states.stopping_go_to_recharge import StoppingGoToRecharge


def test_stopping_to_recharge_goes_to_going_to_recharging_when_no_remaining_tasks(
    sync_state_machine: StateMachine,
) -> None:
    sync_state_machine.current_state = StoppingGoToRecharge(sync_state_machine)
    stopping_go_to_recharge_state: State = cast(State, sync_state_machine.current_state)
    event_handler: EventHandlerMapping | None = (
        stopping_go_to_recharge_state.get_event_handler_by_name(
            "mission_already_done_event"
        )
    )

    assert event_handler is not None

    transition = event_handler.handler(EmptyMessage())

    sync_state_machine.current_state = transition(sync_state_machine)
    assert type(sync_state_machine.current_state) is GoingToRecharging


def test_stopping_to_recharge_goes_to_going_to_recharging_with_aborted_mission(
    sync_state_machine: StateMachine,
) -> None:
    sync_state_machine.current_state = StoppingGoToRecharge(sync_state_machine)
    stopping_go_to_recharge_state: State = cast(State, sync_state_machine.current_state)
    event_handler: EventHandlerMapping | None = (
        stopping_go_to_recharge_state.get_event_handler_by_name("successful_stop_event")
    )

    assert event_handler is not None

    transition = event_handler.handler(AbortedMission(name="test"))

    assert sync_state_machine.events.mqtt_queue.empty()

    sync_state_machine.current_state = transition(sync_state_machine)
    assert type(sync_state_machine.current_state) is GoingToRechargingWithMission


def test_return_home_goes_to_recharging_when_battery_low(
    sync_state_machine: StateMachine,
) -> None:
    sync_state_machine.current_state = ReturningHome(sync_state_machine)
    returning_home_state: State = cast(State, sync_state_machine.current_state)
    event_handler: EventHandlerMapping | None = (
        returning_home_state.get_event_handler_by_name(
            "robot_battery_below_threshold_event"
        )
    )

    assert event_handler is not None

    transition = event_handler.handler(EmptyMessage())

    sync_state_machine.current_state = transition(sync_state_machine)
    assert type(sync_state_machine.current_state) is GoingToRecharging


def test_cancelling_mission_when_going_home_to_recharge(
    sync_state_machine: StateMachine,
) -> None:
    sync_state_machine.current_state = GoingToRechargingWithMission(
        sync_state_machine, mission=AbortedMission(name="test", id="test_id")
    )
    returning_home_state: State = cast(State, sync_state_machine.current_state)
    event_handler: EventHandlerMapping | None = (
        returning_home_state.get_event_handler_by_name("stop_mission_event")
    )

    assert event_handler is not None

    transition = event_handler.handler("test_id")

    sync_state_machine.current_state = transition(sync_state_machine)
    assert type(sync_state_machine.current_state) is GoingToRecharging
