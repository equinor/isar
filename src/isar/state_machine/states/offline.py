import isar.state_machine.states.home as Home
import isar.state_machine.states.intervention_needed as InterventionNeeded
import isar.state_machine.states.maintenance as Maintenance
import isar.state_machine.states.unknown_status as UnknownStatus
from isar.models.events import EmptyMessage, Events
from isar.state_machine.state import EventHandlerMapping, State, Transition
from isar.state_machine.states_enum import States
from robot_interface.models.mission.status import RobotStatus


def Offline(events: Events) -> State:

    def _robot_status_event_handler(
        robot_status: RobotStatus,
    ) -> Transition | None:
        if robot_status == RobotStatus.Offline:
            return None
        elif robot_status == RobotStatus.Home:
            return Home.transition()
        elif robot_status == RobotStatus.Available:
            return InterventionNeeded.transition(
                "Robot not home after going online. Localisation likely needed"
            )
        elif robot_status == RobotStatus.TeleOperation:
            return Maintenance.transition_without_replying_to_API()
        return UnknownStatus.transition()

    event_handlers: list[EventHandlerMapping] = [
        EventHandlerMapping[RobotStatus](
            event=events.robot_service_events.robot_status_update,
            handler=_robot_status_event_handler,
        ),
        EventHandlerMapping[EmptyMessage](
            event=events.api_requests.set_maintenance_mode.request,
            handler=lambda _: Maintenance.transition_and_reply_to_API(),
        ),
    ]
    return State(
        state_name=States.Offline,
        signal_exit_event=events.signal_state_machine_exit,
        event_handler_mappings=event_handlers,
    )


def transition() -> Transition:
    def _transition(events: Events) -> State:
        return Offline(events)

    return _transition
