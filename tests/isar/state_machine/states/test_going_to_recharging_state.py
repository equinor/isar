from typing import cast

from isar.models.events import AbortedMission, EmptyMessage, Events
from isar.state_machine.state import EventHandlerMapping, State
from isar.state_machine.states.going_to_recharging import GoingToRecharging
from isar.state_machine.states.going_to_recharging_with_mission import (
    GoingToRechargingWithMission,
)
from isar.state_machine.states.returning_home import ReturningHome
from isar.state_machine.states.stopping_go_to_recharge import StoppingGoToRecharge


def test_stopping_to_recharge_goes_to_going_to_recharging_when_no_remaining_tasks(
    events: Events,
) -> None:
    current_state = StoppingGoToRecharge(events)
    stopping_go_to_recharge_state: State = cast(State, current_state)
    event_handler: EventHandlerMapping | None = (
        stopping_go_to_recharge_state.get_event_handler_by_name(
            "mission_already_done_event"
        )
    )

    assert event_handler is not None

    transition = event_handler.handler(EmptyMessage())

    current_state = transition(events)
    assert type(current_state) is GoingToRecharging


def test_stopping_to_recharge_goes_to_going_to_recharging_with_aborted_mission(
    events: Events,
) -> None:
    current_state = StoppingGoToRecharge(events)
    stopping_go_to_recharge_state: State = cast(State, current_state)
    event_handler: EventHandlerMapping | None = (
        stopping_go_to_recharge_state.get_event_handler_by_name("successful_stop_event")
    )

    assert event_handler is not None

    transition = event_handler.handler(AbortedMission(name="test"))

    assert events.mqtt_queue.empty()

    current_state = transition(events)
    assert type(current_state) is GoingToRechargingWithMission


def test_return_home_goes_to_recharging_when_battery_low(events: Events) -> None:
    current_state = ReturningHome(events)
    returning_home_state: State = cast(State, current_state)
    event_handler: EventHandlerMapping | None = (
        returning_home_state.get_event_handler_by_name(
            "robot_battery_below_threshold_event"
        )
    )

    assert event_handler is not None

    transition = event_handler.handler(EmptyMessage())

    current_state = transition(events)
    assert type(current_state) is GoingToRecharging


def test_cancelling_mission_when_going_home_to_recharge(events: Events) -> None:
    current_state = GoingToRechargingWithMission(
        events, mission=AbortedMission(name="test", id="test_id")
    )
    returning_home_state: State = cast(State, current_state)
    event_handler: EventHandlerMapping | None = (
        returning_home_state.get_event_handler_by_name("stop_mission_event")
    )

    assert event_handler is not None

    transition = event_handler.handler("test_id")

    current_state = transition(events)
    assert type(current_state) is GoingToRecharging
