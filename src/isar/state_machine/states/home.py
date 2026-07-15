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
from isar.eventhandlers.state import EventHandlerMapping, State, Transition
from isar.models.events import EmptyMessage
from isar.state_machine.states_enum import States
from robot_interface.models.mission.mission import Mission
from robot_interface.models.mission.status import RobotStatus

if TYPE_CHECKING:
    from isar.state_machine.state_machine import StateMachine


class Home(State):

    def __init__(self, state_machine: "StateMachine"):
        events = state_machine.events

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

        event_handlers: List[EventHandlerMapping] = [
            EventHandlerMapping[Mission](
                name="start_mission_event",
                event=events.api_requests.start_mission.request,
                handler=lambda mission: Monitor.transition_and_start_mission(
                    mission, True
                ),
            ),
            EventHandlerMapping[EmptyMessage](
                name="return_home_event",
                event=events.api_requests.return_home.request,
                handler=lambda event: ReturningHome.transition_and_start_mission(True),
            ),
            EventHandlerMapping[str](
                name="stop_mission_event",
                event=events.api_requests.stop_mission.request,
                handler=lambda mission_id: Stopping.transition_and_trigger_stop(
                    mission_id, True
                ),
            ),
            EventHandlerMapping[RobotStatus](
                name="robot_status_event",
                event=events.robot_service_events.robot_status_update,
                handler=_robot_status_event_handler,
            ),
            EventHandlerMapping[EmptyMessage](
                name="send_to_lockdown_event",
                event=events.api_requests.send_to_lockdown.request,
                handler=lambda _: Lockdown.transition_and_respond_to_api(),
            ),
            EventHandlerMapping[EmptyMessage](
                name="robot_battery_below_threshold_event",
                event=events.robot_service_events.battery_below_mission_threshold,
                handler=lambda _: Recharging.transition(),
            ),
            EventHandlerMapping[EmptyMessage](
                name="set_maintenance_mode",
                event=events.api_requests.set_maintenance_mode.request,
                handler=lambda _: Maintenance.transition_and_reply_to_API(),
            ),
        ]
        super().__init__(
            state_name=States.Home,
            state_machine=state_machine,
            event_handler_mappings=event_handlers,
        )


def transition() -> Transition["Home"]:
    def _transition(state_machine: "StateMachine") -> Home:
        # This clears the current robot status value, so we don't read an outdated value
        state_machine.events.robot_service_events.robot_status_update.clear_event()

        return Home(state_machine)

    return _transition
