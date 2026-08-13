from isar.models.events import AbortedMission, EmptyMessage, Events
from isar.state_machine.state import EventHandlerMapping
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
    event_handler: EventHandlerMapping = current_state.get_event_handler_by_event(
        events.robot_service_events.stopped_mission_already_done
    )

    transition = event_handler.handler(EmptyMessage())

    current_state = transition(events)
    assert type(current_state) is GoingToRecharging


def test_stopping_to_recharge_goes_to_going_to_recharging_with_aborted_mission(
    events: Events,
) -> None:
    current_state = StoppingGoToRecharge(events)
    event_handler: EventHandlerMapping = current_state.get_event_handler_by_event(
        events.robot_service_events.mission_successfully_stopped
    )

    transition = event_handler.handler(AbortedMission(id="id", name="test"))

    assert events.mqtt_queue.empty()

    current_state = transition(events)
    assert type(current_state) is GoingToRechargingWithMission


def test_return_home_goes_to_recharging_when_battery_low(events: Events) -> None:
    current_state = ReturningHome(events)
    event_handler: EventHandlerMapping = current_state.get_event_handler_by_event(
        events.robot_service_events.battery_below_mission_threshold
    )

    transition = event_handler.handler(EmptyMessage())

    current_state = transition(events)
    assert type(current_state) is GoingToRecharging


def test_cancelling_mission_when_going_home_to_recharge(events: Events) -> None:
    current_state = GoingToRechargingWithMission(
        events, mission=AbortedMission(name="test", id="test_id")
    )
    event_handler: EventHandlerMapping = current_state.get_event_handler_by_event(
        events.api_requests.stop_mission.request
    )

    transition = event_handler.handler("test_id")

    current_state = transition(events)
    assert type(current_state) is GoingToRecharging
