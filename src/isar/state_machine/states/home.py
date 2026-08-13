import isar.state_machine.states.await_next_mission as AwaitNextMission
import isar.state_machine.states.lockdown as Lockdown
import isar.state_machine.states.maintenance as Maintenance
import isar.state_machine.states.monitor as Monitor
import isar.state_machine.states.offline as Offline
import isar.state_machine.states.recharging as Recharging
import isar.state_machine.states.returning_home as ReturningHome
import isar.state_machine.states.stopping as Stopping
import isar.state_machine.states.unknown_status as UnknownStatus
from isar.models.events import EmptyMessage, Events
from isar.state_machine.state import EventHandlerMapping, State, Transition
from isar.state_machine.states_enum import States
from robot_interface.models.mission.mission import Mission
from robot_interface.models.mission.status import RobotStatus


class Home(State):

    def __init__(self, events: Events):

        def _robot_status_event_handler(
            robot_status: RobotStatus,
        ) -> (
            Transition[AwaitNextMission.AwaitNextMission]
            | Transition[Offline.Offline]
            | Transition[Maintenance.Maintenance]
            | Transition[UnknownStatus.UnknownStatus]
            | None
        ):
            if robot_status == RobotStatus.Home:
                return None
            elif robot_status == RobotStatus.Available:
                return AwaitNextMission.transition()
            elif robot_status == RobotStatus.Offline:
                return Offline.transition()
            elif robot_status == RobotStatus.TeleOperation:
                return Maintenance.transition_without_replying_to_API()
            return UnknownStatus.transition()

        event_handlers: list[EventHandlerMapping] = [
            EventHandlerMapping[Mission](
                event=events.api_requests.start_mission.request,
                handler=lambda mission: Monitor.transition_and_start_mission(
                    mission, True
                ),
            ),
            EventHandlerMapping[EmptyMessage](
                event=events.api_requests.return_home.request,
                handler=lambda _: ReturningHome.transition_and_start_mission(True),
            ),
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
                event=events.api_requests.send_to_lockdown.request,
                handler=lambda _: Lockdown.transition_and_respond_to_api(),
            ),
            EventHandlerMapping[EmptyMessage](
                event=events.robot_service_events.battery_below_mission_threshold,
                handler=lambda _: Recharging.transition(),
            ),
            EventHandlerMapping[EmptyMessage](
                event=events.api_requests.set_maintenance_mode.request,
                handler=lambda _: Maintenance.transition_and_reply_to_API(),
            ),
        ]
        super().__init__(
            state_name=States.Home,
            signal_exit_event=events.signal_state_machine_exit,
            event_handler_mappings=event_handlers,
        )


def transition() -> Transition[Home]:
    def _transition(events: Events) -> Home:
        # This clears the current robot status value, so we don't read an outdated value
        events.robot_service_events.robot_status_update.clear_event()

        return Home(events)

    return _transition
