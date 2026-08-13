from isar.models.events import AbortedMission, EmptyMessage, Events
from isar.state_machine.state import EventHandlerMapping
from isar.state_machine.states.going_to_recharging import GoingToRecharging
from isar.state_machine.states.home import Home
from isar.state_machine.states.recharging_with_mission import RechargingWithMission
from isar.state_machine.states_enum import States


def test_going_to_recharging_goes_to_recharge(events: Events) -> None:
    current_state = GoingToRecharging(events)
    event_handler: EventHandlerMapping = current_state.get_event_handler_by_event(
        events.robot_service_events.mission_succeeded
    )

    transition = event_handler.handler(EmptyMessage())

    current_state = transition(events)
    assert current_state.name is States.Recharging


def test_home_goes_to_recharging_when_battery_low(events: Events) -> None:
    current_state = Home(events)
    event_handler: EventHandlerMapping = current_state.get_event_handler_by_event(
        events.robot_service_events.battery_below_mission_threshold
    )

    transition = event_handler.handler(EmptyMessage())

    current_state = transition(events)
    assert current_state.name is States.Recharging


def test_continuing_mission_when_battery_high(events: Events) -> None:
    current_state = RechargingWithMission(
        events, mission=AbortedMission(name="test", id="test_id")
    )
    event_handler: EventHandlerMapping = current_state.get_event_handler_by_event(
        events.robot_service_events.battery_above_recharge_threshold
    )

    transition = event_handler.handler(EmptyMessage())

    current_state = transition(events)
    assert current_state.name is States.Monitor


def test_cancelling_mission_when_recharging_with_mission(events: Events) -> None:
    current_state = RechargingWithMission(
        events, mission=AbortedMission(name="test", id="test_id")
    )
    event_handler: EventHandlerMapping = current_state.get_event_handler_by_event(
        events.api_requests.stop_mission.request
    )

    transition = event_handler.handler("test_id")

    current_state = transition(events)
    assert current_state.name is States.Recharging
