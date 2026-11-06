import json

import pytest

from isar.models.events import AbortedMission, EmptyMessage, Events, MissionCompleted
from isar.state_machine.state import EventHandlerMapping, State
from isar.state_machine.states.going_to_recharging_with_mission import (
    GoingToRechargingWithMission,
)
from isar.state_machine.states.returning_home import ReturningHome
from isar.state_machine.states.stopping_go_to_recharge import StoppingGoToRecharge
from isar.state_machine.states_enum import States
from robot_interface.models.mission.status import MissionStatus


def test_stopping_to_recharge_goes_to_going_to_recharging_when_no_remaining_tasks(
    events: Events,
) -> None:
    current_state = State(StoppingGoToRecharge(events, mission_id="id"))
    event_handler: EventHandlerMapping = current_state.get_event_handler_by_event(
        events.action_requests.stop_mission.success
    )

    transition = event_handler.handler(MissionCompleted(MissionStatus.Successful))

    message = json.loads(events.mqtt_queue.get().payload)
    assert message["mission_id"] == "id"
    assert message["status"] == MissionStatus.Successful.value

    current_state = State(transition(events))
    assert current_state.name is States.GoingToRecharging


@pytest.mark.parametrize(
    "status",
    [MissionStatus.Successful, MissionStatus.Failed],
)
def test_stopping_to_recharge_reports_completed_mission_outcome(
    events: Events, status: MissionStatus
) -> None:
    current_state = State(StoppingGoToRecharge(events, mission_id="id"))
    handler = current_state.get_event_handler_by_event(
        events.action_requests.stop_mission.success
    )

    transition = handler.handler(MissionCompleted(status))

    message = json.loads(events.mqtt_queue.get().payload)
    assert message["mission_id"] == "id"
    assert message["status"] == status.value
    assert State(transition(events)).name is States.GoingToRecharging
    assert events.action_requests.return_home.request.has_event()


def test_stopping_to_recharge_goes_to_going_to_recharging_with_aborted_mission(
    events: Events,
) -> None:
    current_state = State(StoppingGoToRecharge(events, "id"))
    event_handler: EventHandlerMapping = current_state.get_event_handler_by_event(
        events.action_requests.stop_mission.success
    )

    transition = event_handler.handler(AbortedMission(id="id", name="test"))

    assert events.mqtt_queue.empty()

    current_state = State(transition(events))
    assert current_state.name is States.GoingToRechargingWithMission


def test_return_home_goes_to_recharging_when_battery_low(events: Events) -> None:
    current_state = State(ReturningHome(events))
    event_handler: EventHandlerMapping = current_state.get_event_handler_by_event(
        events.robot_async_events.battery_below_mission_threshold
    )

    transition = event_handler.handler(EmptyMessage())

    current_state = State(transition(events))
    assert current_state.name is States.GoingToRecharging


def test_cancelling_mission_when_going_home_to_recharge(events: Events) -> None:
    current_state = State(
        GoingToRechargingWithMission(
            events, mission=AbortedMission(name="test", id="test_id")
        )
    )
    event_handler: EventHandlerMapping = current_state.get_event_handler_by_event(
        events.api_requests.stop_mission.request
    )

    transition = event_handler.handler("test_id")

    current_state = State(transition(events))
    assert current_state.name is States.GoingToRecharging
