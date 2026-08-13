from isar.models.events import AbortedMission, EmptyMessage, Events
from isar.state_machine.state import EventHandlerMapping
from isar.state_machine.states.going_to_recharging import GoingToRecharging
from isar.state_machine.states.home import Home
from isar.state_machine.states.monitor import Monitor
from isar.state_machine.states.recharging import Recharging
from isar.state_machine.states.recharging_with_mission import RechargingWithMission


def test_going_to_recharging_goes_to_recharge(events: Events) -> None:
    current_state = GoingToRecharging(events)
    event_handler: EventHandlerMapping = current_state.get_event_handler_by_event(
        events.robot_service_events.mission_succeeded
    )

    transition = event_handler.handler(EmptyMessage())

    current_state = transition(events)
    assert type(current_state) is Recharging


def test_home_goes_to_recharging_when_battery_low(events: Events) -> None:
    current_state = Home(events)
    event_handler: EventHandlerMapping = current_state.get_event_handler_by_event(
        events.robot_service_events.battery_below_mission_threshold
    )

    transition = event_handler.handler(EmptyMessage())

    current_state = transition(events)
    assert type(current_state) is Recharging


def test_continuing_mission_when_battery_high(events: Events) -> None:
    current_state = RechargingWithMission(
        events, mission=AbortedMission(name="test", id="test_id")
    )
    event_handler: EventHandlerMapping = current_state.get_event_handler_by_event(
        events.robot_service_events.battery_above_recharge_threshold_event
    )

    transition = event_handler.handler(EmptyMessage())

    current_state = transition(events)
    assert type(current_state) is Monitor


def test_cancelling_mission_when_recharging_with_mission(events: Events) -> None:
    current_state = RechargingWithMission(
        events, mission=AbortedMission(name="test", id="test_id")
    )
    event_handler: EventHandlerMapping = current_state.get_event_handler_by_event(
        events.api_requests.stop_mission.request
    )

    transition = event_handler.handler("test_id")

    current_state = transition(events)
    assert type(current_state) is Recharging
