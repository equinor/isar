from typing import TYPE_CHECKING, List

import isar.state_machine.states.await_next_mission as AwaitNextMission
import isar.state_machine.states.lockdown as Lockdown
import isar.state_machine.states.maintenance as Maintenance
import isar.state_machine.states.monitor as Monitor
import isar.state_machine.states.offline as Offline
import isar.state_machine.states.recharging as Recharging
import isar.state_machine.states.returning_home as ReturningHome
import isar.state_machine.states.stopping as Stopping
import isar.state_machine.states.unknown_status as UnknownStatus
from isar.config.settings import settings
from isar.eventhandlers.eventhandler import EventHandlerMapping, State, Transition
from isar.models.events import EmptyMessage
from isar.state_machine.states_enum import States
from robot_interface.models.mission.mission import Mission
from robot_interface.models.mission.status import RobotStatus

if TYPE_CHECKING:
    from isar.state_machine.state_machine import StateMachine


class Home(State):

    def __init__(self, state_machine: "StateMachine"):
        events = state_machine.events
        shared_state = state_machine.shared_state

        # This clears the current robot status value, so we don't read an outdated value
        events.robot_service_events.robot_status_changed.clear_event()

        def _send_to_lockdown_event_handler(
            should_send_robot_home: EmptyMessage,
        ) -> Transition[Lockdown.Lockdown]:
            return Lockdown.transition_and_respond_to_api()

        def _set_maintenance_mode_event_handler(
            should_set_maintenance_mode: EmptyMessage,
        ) -> Transition[Maintenance.Maintenance] | None:
            return Maintenance.transition_and_reply_to_API()

        def _robot_status_event_handler(
            has_changed: EmptyMessage,
        ) -> (
            Transition[AwaitNextMission.AwaitNextMission]
            | Transition[Offline.Offline]
            | Transition[Maintenance.Maintenance]
            | Transition[UnknownStatus.UnknownStatus]
            | None
        ):
            robot_status: RobotStatus | None = shared_state.robot_status.check()
            if robot_status == RobotStatus.Home:
                return None
            elif robot_status == RobotStatus.Available:
                self.logger.info(
                    "Got robot status available while in home state. Leaving home state."
                )
                return AwaitNextMission.transition()
            elif robot_status == RobotStatus.Offline:
                self.logger.info(
                    "Got robot status offline while in home state. Leaving home state."
                )
                return Offline.transition()
            elif robot_status == RobotStatus.TeleOperation:
                self.logger.info(
                    "Got robot status teleoperation while in home state. Going to maintenance."
                )
                return Maintenance.transition_without_replying_to_API()
            self.logger.info(
                f"Got unexpected status {robot_status} while in home state. Leaving home state."
            )
            return UnknownStatus.transition()

        def _robot_battery_level_updated_handler(
            battery_level: float,
        ) -> Transition[Recharging.Recharging] | None:
            if battery_level >= settings.ROBOT_MISSION_BATTERY_START_THRESHOLD:
                return None

            return Recharging.transition()

        def _stop_mission_event_handler(
            mission_id: str,
        ) -> Transition[Stopping.Stopping]:
            return Stopping.transition_and_trigger_stop(mission_id, True)

        def _start_mission_event_handler(
            mission: Mission,
        ) -> Transition[Monitor.Monitor]:
            return Monitor.transition_and_start_mission(mission, True)

        event_handlers: List[EventHandlerMapping] = [
            EventHandlerMapping[Mission](
                name="start_mission_event",
                event=events.api_requests.start_mission.request,
                handler=_start_mission_event_handler,
            ),
            EventHandlerMapping[EmptyMessage](
                name="return_home_event",
                event=events.api_requests.return_home.request,
                handler=lambda event: ReturningHome.transition_and_start_mission(True),
            ),
            EventHandlerMapping[str](
                name="stop_mission_event",
                event=events.api_requests.stop_mission.request,
                handler=_stop_mission_event_handler,
            ),
            EventHandlerMapping[EmptyMessage](
                name="robot_status_event",
                event=events.robot_service_events.robot_status_changed,
                handler=_robot_status_event_handler,
            ),
            EventHandlerMapping[EmptyMessage](
                name="send_to_lockdown_event",
                event=events.api_requests.send_to_lockdown.request,
                handler=_send_to_lockdown_event_handler,
            ),
            EventHandlerMapping[float](
                name="robot_battery_update_event",
                event=shared_state.robot_battery_level,
                handler=_robot_battery_level_updated_handler,
                should_not_consume=True,
            ),
            EventHandlerMapping[EmptyMessage](
                name="set_maintenance_mode",
                event=events.api_requests.set_maintenance_mode.request,
                handler=_set_maintenance_mode_event_handler,
            ),
        ]
        super().__init__(
            state_name=States.Home,
            state_machine=state_machine,
            event_handler_mappings=event_handlers,
        )


def transition() -> Transition["Home"]:
    def _transition(state_machine: "StateMachine") -> Home:
        return Home(state_machine)

    return _transition
