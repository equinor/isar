import isar.state_machine.states.await_next_mission as AwaitNextMission
import isar.state_machine.states.home as Home
import isar.state_machine.states.maintenance as Maintenance
import isar.state_machine.states.offline as Offline
import isar.state_machine.states.stopping as Stopping
import isar.state_machine.states.stopping_unknown_mission as StoppingUnknownMission
from isar.models.events import EmptyMessage, Events
from isar.state_machine.state import EventHandlerMapping, State, Transition
from isar.state_machine.states_enum import States
from robot_interface.models.mission.status import RobotStatus


def UnknownStatus(events: Events) -> State:

    def _robot_status_event_handler(
        robot_status: RobotStatus,
    ) -> Transition | None:
        if robot_status == RobotStatus.Home:
            return Home.transition()
        elif robot_status == RobotStatus.Available:
            return AwaitNextMission.transition()
        elif robot_status == RobotStatus.Offline:
            return Offline.transition()
        elif robot_status == RobotStatus.TeleOperation:
            return Maintenance.transition_without_replying_to_API()
        elif robot_status == RobotStatus.Busy:
            return StoppingUnknownMission.transition()
        return None

    event_handlers: list[EventHandlerMapping] = [
        EventHandlerMapping[str](
            event=events.api_requests.stop_mission.request,
            handler=lambda mission_id: Stopping.transition_and_trigger_stop_and_respond_to_API(
                mission_id
            ),
        ),
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
        state_name=States.UnknownStatus,
        signal_exit_event=events.signal_state_machine_exit,
        event_handler_mappings=event_handlers,
    )


def transition() -> Transition:
    def _transition(events: Events) -> State:
        return UnknownStatus(events)

    return _transition
