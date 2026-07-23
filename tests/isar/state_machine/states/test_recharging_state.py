from typing import cast

from isar.models.events import AbortedMission, EmptyMessage, Events
from isar.state_machine.state import EventHandlerMapping, State
from isar.state_machine.states.going_to_recharging import GoingToRecharging
from isar.state_machine.states.home import Home
from isar.state_machine.states.monitor import Monitor
from isar.state_machine.states.recharging import Recharging
from isar.state_machine.states.recharging_with_mission import RechargingWithMission


def test_going_to_recharging_goes_to_recharge(events: Events) -> None:
    current_state = GoingToRecharging(events)
    going_to_recharging_state: State = cast(State, current_state)
    event_handler: EventHandlerMapping | None = (
        going_to_recharging_state.get_event_handler_by_name("mission_succeeded_event")
    )

    assert event_handler is not None

    transition = event_handler.handler(EmptyMessage())

    current_state = transition(events)
    assert type(current_state) is Recharging


def test_home_goes_to_recharging_when_battery_low(events: Events) -> None:
    current_state = Home(events)
    home_state: State = cast(State, current_state)
    event_handler: EventHandlerMapping | None = home_state.get_event_handler_by_name(
        "robot_battery_below_threshold_event"
    )

    assert event_handler is not None

    transition = event_handler.handler(EmptyMessage())

    current_state = transition(events)
    assert type(current_state) is Recharging


def test_continuing_mission_when_battery_high(events: Events) -> None:
    current_state = RechargingWithMission(
        events, mission=AbortedMission(name="test", id="test_id")
    )
    returning_home_state: State = cast(State, current_state)
    event_handler: EventHandlerMapping | None = (
        returning_home_state.get_event_handler_by_name(
            "robot_battery_above_recharging_threshold_event"
        )
    )

    assert event_handler is not None

    transition = event_handler.handler(EmptyMessage())

    current_state = transition(events)
    assert type(current_state) is Monitor


def test_cancelling_mission_when_recharging_with_mission(events: Events) -> None:
    current_state = RechargingWithMission(
        events, mission=AbortedMission(name="test", id="test_id")
    )
    returning_home_state: State = cast(State, current_state)
    event_handler: EventHandlerMapping | None = (
        returning_home_state.get_event_handler_by_name("stop_mission_event")
    )

    assert event_handler is not None

    transition = event_handler.handler("test_id")

    current_state = transition(events)
    assert type(current_state) is Recharging
