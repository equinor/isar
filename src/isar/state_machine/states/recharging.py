import isar.state_machine.states.home as Home
import isar.state_machine.states.lockdown as Lockdown
import isar.state_machine.states.maintenance as Maintenance
import isar.state_machine.states.offline as Offline
from isar.models.events import EmptyMessage, Events
from isar.state_machine.state import (
    EventHandlerMapping,
    StateDef,
    Transition,
    state_definition,
    transition_definition,
)
from isar.state_machine.states_enum import States
from robot_interface.models.mission.status import RobotStatus


@state_definition
def Recharging(events: Events) -> StateDef:

    event_handlers: list[EventHandlerMapping] = [
        EventHandlerMapping[EmptyMessage](
            event=events.robot_async_events.battery_above_recharge_threshold,
            handler=lambda _: Home.transition(events),
        ),
        EventHandlerMapping[RobotStatus](
            event=events.robot_async_events.robot_status_update,
            handler=lambda robot_status: (
                Offline.transition(events)
                if robot_status == RobotStatus.Offline
                else None
            ),
        ),
        EventHandlerMapping[EmptyMessage](
            event=events.api_requests.send_to_lockdown.request,
            handler=lambda _: Lockdown.transition_and_respond_to_api(events),
        ),
        EventHandlerMapping[EmptyMessage](
            event=events.api_requests.set_maintenance_mode.request,
            handler=lambda _: Maintenance.transition_and_reply_to_API(events),
        ),
    ]
    return StateDef(
        name=States.Recharging,
        handlers=event_handlers,
    )


@transition_definition
def transition(events: Events) -> Transition:
    return Transition(Recharging(events))
