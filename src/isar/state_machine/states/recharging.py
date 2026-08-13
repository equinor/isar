import isar.state_machine.states.home as Home
import isar.state_machine.states.lockdown as Lockdown
import isar.state_machine.states.maintenance as Maintenance
import isar.state_machine.states.offline as Offline
from isar.models.events import EmptyMessage, Events
from isar.state_machine.state import EventHandlerMapping, State, Transition
from isar.state_machine.states_enum import States
from robot_interface.models.mission.status import RobotStatus


class Recharging(State):

    def __init__(self, events: Events):

        event_handlers: list[EventHandlerMapping] = [
            EventHandlerMapping[EmptyMessage](
                event=events.robot_service_events.battery_above_recharge_threshold,
                handler=lambda _: Home.transition(),
            ),
            EventHandlerMapping[RobotStatus](
                event=events.robot_service_events.robot_status_update,
                handler=lambda robot_status: (
                    Offline.transition()
                    if robot_status == RobotStatus.Offline
                    else None
                ),
            ),
            EventHandlerMapping[EmptyMessage](
                event=events.api_requests.send_to_lockdown.request,
                handler=lambda _: Lockdown.transition_and_respond_to_api(),
            ),
            EventHandlerMapping[EmptyMessage](
                event=events.api_requests.set_maintenance_mode.request,
                handler=lambda _: Maintenance.transition_and_reply_to_API(),
            ),
        ]
        super().__init__(
            state_name=States.Recharging,
            signal_exit_event=events.signal_state_machine_exit,
            event_handler_mappings=event_handlers,
        )


def transition() -> Transition[Recharging]:
    def _transition(events: Events) -> Recharging:
        return Recharging(events)

    return _transition
