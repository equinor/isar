from typing import TYPE_CHECKING, List

import isar.state_machine.states.lockdown as Lockdown
import isar.state_machine.states.maintenance as Maintenance
import isar.state_machine.states.monitor as Monitor
import isar.state_machine.states.offline as Offline
import isar.state_machine.states.recharging as Recharging
from isar.apis.models.models import ControlMissionResponse
from isar.config.settings import settings
from isar.eventhandlers.eventhandler import EventHandlerMapping, State, Transition
from isar.models.events import AbortedMission, EmptyMessage
from isar.state_machine.states_enum import States
from robot_interface.models.mission.status import RobotStatus

if TYPE_CHECKING:
    from isar.state_machine.state_machine import StateMachine


class RechargingWithMission(State):

    def __init__(self, state_machine: "StateMachine", mission: AbortedMission):
        shared_state = state_machine.shared_state
        events = state_machine.events

        def robot_battery_level_updated_handler(
            battery_level: float,
        ) -> Transition[Monitor.Monitor] | None:
            if battery_level < settings.ROBOT_BATTERY_RECHARGE_THRESHOLD:
                return None

            state_machine.logger.info(
                f"Continuing mission after finishing recharging: {mission.name}"
            )
            return Monitor.transition_and_start_mission(
                mission, should_respond_to_API_request=False
            )

        def robot_offline_handler(
            robot_status: RobotStatus,
        ) -> Transition[Offline.Offline] | None:
            if robot_status == RobotStatus.Offline:
                self.logger.info(
                    "Got robot status offline while in recharging state. Leaving recharging state."
                )
                return Offline.transition()
            return None

        def _send_to_lockdown_event_handler(
            should_lockdown: EmptyMessage,
        ) -> Transition[Lockdown.Lockdown]:
            return Lockdown.transition_and_respond_to_api()

        def _set_maintenance_mode_event_handler(
            should_set_maintenance_mode: EmptyMessage,
        ) -> Transition[Maintenance.Maintenance]:
            return Maintenance.transition_and_reply_to_API()

        def _stop_mission_event_handler(
            stop_mission_id: str,
        ) -> Transition[Recharging.Recharging] | None:
            if mission.id == stop_mission_id or stop_mission_id == "":
                state_machine.events.api_requests.stop_mission.response.trigger_event(
                    ControlMissionResponse(success=True)
                )
                return Recharging.transition()
            else:
                state_machine.events.api_requests.stop_mission.response.trigger_event(
                    ControlMissionResponse(
                        success=False, failure_reason="Mission not found"
                    )
                )
                return None

        event_handlers: List[EventHandlerMapping] = [
            EventHandlerMapping[float](
                name="robot_battery_update_event",
                event=shared_state.robot_battery_level,
                handler=robot_battery_level_updated_handler,
                should_not_consume=True,
            ),
            EventHandlerMapping[RobotStatus](
                name="robot_offline_event",
                event=events.robot_service_events.robot_status_update,
                handler=robot_offline_handler,
            ),
            EventHandlerMapping[EmptyMessage](
                name="send_to_lockdown_event",
                event=events.api_requests.send_to_lockdown.request,
                handler=_send_to_lockdown_event_handler,
            ),
            EventHandlerMapping[EmptyMessage](
                name="set_maintenance_mode",
                event=events.api_requests.set_maintenance_mode.request,
                handler=_set_maintenance_mode_event_handler,
            ),
            EventHandlerMapping[str](
                name="stop_mission_event",
                event=events.api_requests.stop_mission.request,
                handler=_stop_mission_event_handler,
            ),
        ]
        super().__init__(
            state_name=States.RechargingWithMission,
            state_machine=state_machine,
            event_handler_mappings=event_handlers,
        )


def transition(mission: AbortedMission) -> Transition[RechargingWithMission]:
    def _transition(state_machine: "StateMachine") -> RechargingWithMission:
        return RechargingWithMission(state_machine, mission=mission)

    return _transition
