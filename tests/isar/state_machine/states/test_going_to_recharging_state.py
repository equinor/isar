from typing import Optional, cast

from isar.config.settings import settings
from isar.eventhandlers.eventhandler import EventHandlerBase, EventHandlerMapping
from isar.state_machine.state_machine import StateMachine


def test_stopping_to_recharge_goes_to_going_to_recharging(
    sync_state_machine: StateMachine,
) -> None:
    sync_state_machine.shared_state.mission_id.trigger_event("mission_id")
    sync_state_machine.state = sync_state_machine.stopping_go_to_recharge_state.name  # type: ignore
    stopping_go_to_recharge_state: EventHandlerBase = cast(
        EventHandlerBase, sync_state_machine.stopping_go_to_recharge_state
    )
    event_handler: Optional[EventHandlerMapping] = (
        stopping_go_to_recharge_state.get_event_handler_by_name("successful_stop_event")
    )

    assert event_handler is not None

    event_handler.event.trigger_event(True)
    transition = event_handler.handler(event_handler.event)

    assert transition is sync_state_machine.start_recharging_mission_monitoring  # type: ignore
    assert not sync_state_machine.events.mqtt_queue.empty()

    mqtt_message = sync_state_machine.events.mqtt_queue.get(block=False)
    assert mqtt_message is not None
    mqtt_payload_topic = mqtt_message[0]
    assert mqtt_payload_topic is settings.TOPIC_ISAR_MISSION_ABORTED

    transition()
    assert sync_state_machine.state is sync_state_machine.going_to_recharging_state.name  # type: ignore


def test_return_home_goes_to_recharging_when_battery_low(
    sync_state_machine: StateMachine,
) -> None:
    sync_state_machine.state = sync_state_machine.returning_home_state.name  # type: ignore
    returning_home_state: EventHandlerBase = cast(
        EventHandlerBase, sync_state_machine.returning_home_state
    )
    event_handler: Optional[EventHandlerMapping] = (
        returning_home_state.get_event_handler_by_name("robot_battery_update_event")
    )

    assert event_handler is not None

    event_handler.event.trigger_event(10.0)
    transition = event_handler.handler(event_handler.event)

    assert transition is sync_state_machine.go_to_recharging  # type: ignore
    transition()
    assert sync_state_machine.state is sync_state_machine.going_to_recharging_state.name  # type: ignore
