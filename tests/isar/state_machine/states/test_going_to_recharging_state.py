from typing import Optional, cast

from isar.config.settings import settings
from isar.eventhandlers.eventhandler import EventHandlerMapping, State
from isar.state_machine.state_machine import StateMachine
from isar.state_machine.states.going_to_recharging import GoingToRecharging
from isar.state_machine.states.returning_home import ReturningHome
from isar.state_machine.states.stopping_go_to_recharge import StoppingGoToRecharge


def test_stopping_to_recharge_goes_to_going_to_recharging(
    sync_state_machine: StateMachine,
) -> None:
    sync_state_machine.current_state = StoppingGoToRecharge(
        sync_state_machine, "mission_id"
    )
    stopping_go_to_recharge_state: State = cast(State, sync_state_machine.current_state)
    event_handler: Optional[EventHandlerMapping] = (
        stopping_go_to_recharge_state.get_event_handler_by_name("successful_stop_event")
    )

    assert event_handler is not None

    transition = event_handler.handler(True)

    assert not sync_state_machine.events.mqtt_queue.empty()

    mqtt_message = sync_state_machine.events.mqtt_queue.get(block=False)
    assert mqtt_message is not None
    mqtt_payload_topic = mqtt_message[0]
    assert mqtt_payload_topic is settings.TOPIC_ISAR_MISSION_ABORTED

    sync_state_machine.current_state = transition(sync_state_machine)
    assert type(sync_state_machine.current_state) is GoingToRecharging


def test_return_home_goes_to_recharging_when_battery_low(
    sync_state_machine: StateMachine,
) -> None:
    sync_state_machine.current_state = ReturningHome(sync_state_machine)
    returning_home_state: State = cast(State, sync_state_machine.current_state)
    event_handler: Optional[EventHandlerMapping] = (
        returning_home_state.get_event_handler_by_name("robot_battery_update_event")
    )

    assert event_handler is not None

    transition = event_handler.handler(10.0)

    sync_state_machine.current_state = transition(sync_state_machine)
    assert type(sync_state_machine.current_state) is GoingToRecharging
