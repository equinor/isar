import isar.state_machine.states.await_next_mission as AwaitNextMission
import isar.state_machine.states.home as Home
import isar.state_machine.states.maintenance as Maintenance
import isar.state_machine.states.offline as Offline
import isar.state_machine.states.stopping_unknown_mission as StoppingUnknownMission
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
def UnknownStatus(events: Events) -> StateDef:

    def _robot_status_event_handler(
        robot_status: RobotStatus,
    ) -> Transition | None:
        if robot_status == RobotStatus.Home:
            return Home.transition(events)
        elif robot_status == RobotStatus.Available:
            return AwaitNextMission.transition(events)
        elif robot_status == RobotStatus.Offline:
            return Offline.transition(events)
        elif robot_status == RobotStatus.TeleOperation:
            return Maintenance.transition_without_replying_to_API(events)
        elif robot_status == RobotStatus.Busy:
            return StoppingUnknownMission.transition(events)
        return None

    event_handlers: list[EventHandlerMapping] = [
        EventHandlerMapping[EmptyMessage](
            event=events.api_requests.stop_mission.request,
            handler=lambda _: StoppingUnknownMission.transition_and_respond_to_API(
                events
            ),
        ),
        EventHandlerMapping[RobotStatus](
            event=events.robot_async_events.robot_status_update,
            handler=_robot_status_event_handler,
        ),
        EventHandlerMapping[EmptyMessage](
            event=events.api_requests.set_maintenance_mode.request,
            handler=lambda _: Maintenance.transition_and_reply_to_API(events),
        ),
    ]
    return StateDef(
        name=States.UnknownStatus,
        handlers=event_handlers,
    )


@transition_definition
def transition(events: Events) -> Transition:
    return Transition(UnknownStatus(events))
