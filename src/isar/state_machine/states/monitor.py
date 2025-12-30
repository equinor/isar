from typing import TYPE_CHECKING, List, Optional

import isar.state_machine.states.await_next_mission as AwaitNextMission
import isar.state_machine.states.pausing as Pausing
import isar.state_machine.states.stopping_due_to_maintenance as StoppingDueToMaintenance
import isar.state_machine.states.stopping_go_to_lockdown as StoppingGoToLockdown
import isar.state_machine.states.stopping_go_to_recharge as StoppingGoToRecharge
from isar.apis.models.models import ControlMissionResponse
from isar.config.settings import settings
from isar.eventhandlers.eventhandler import EventHandlerMapping, State, Transition
from isar.state_machine.states_enum import States
from isar.state_machine.utils.common_event_handlers import (
    mission_started_event_handler,
    stop_mission_event_handler,
)
from robot_interface.models.exceptions.robot_exceptions import ErrorMessage
from robot_interface.models.mission.status import MissionStatus

if TYPE_CHECKING:
    from isar.state_machine.state_machine import StateMachine


class Monitor(State):

    def __init__(self, state_machine: "StateMachine", mission_id: str):
        events = state_machine.events
        shared_state = state_machine.shared_state

        def _pause_mission_event_handler(
            should_pause: bool,
        ) -> Transition[Pausing.Pausing]:
            state_machine.events.api_requests.pause_mission.response.trigger_event(
                ControlMissionResponse(success=True)
            )
            state_machine.events.state_machine_events.pause_mission.trigger_event(True)
            return Pausing.transition(mission_id)

        def _robot_battery_level_updated_handler(
            battery_level: float,
        ) -> Optional[Transition[StoppingGoToRecharge.StoppingGoToRecharge]]:
            if (
                battery_level is None
                or battery_level >= settings.ROBOT_MISSION_BATTERY_START_THRESHOLD
            ):
                return None

            state_machine.logger.warning(
                "Cancelling current mission due to low battery"
            )
            state_machine.events.state_machine_events.stop_mission.trigger_event(True)
            return StoppingGoToRecharge.transition(mission_id)

        def _send_to_lockdown_event_handler(
            should_lockdown: bool,
        ) -> Transition[StoppingGoToLockdown.StoppingGoToLockdown]:
            state_machine.logger.warning(
                "Cancelling current mission due to robot going to lockdown"
            )
            state_machine.events.state_machine_events.stop_mission.trigger_event(True)
            return StoppingGoToLockdown.transition(mission_id)

        def _mission_status_event_handler(
            mission_status: MissionStatus,
        ) -> Optional[Transition[AwaitNextMission.AwaitNextMission]]:
            if mission_status not in [
                MissionStatus.InProgress,
                MissionStatus.NotStarted,
                MissionStatus.Paused,
            ]:
                state_machine.logger.info(
                    f"Mission completed with status {mission_status}"
                )
                return AwaitNextMission.transition()
            return None

        def _set_maintenance_mode_event_handler(
            should_set_maintenande_mode: bool,
        ) -> Transition[StoppingDueToMaintenance.StoppingDueToMaintenance]:
            state_machine.logger.warning(
                "Cancelling current mission due to robot going to maintenance mode"
            )
            state_machine.events.state_machine_events.stop_mission.trigger_event(True)
            return StoppingDueToMaintenance.transition(mission_id)

        def _mission_failed_event_handler(
            mission_failed: ErrorMessage,
        ) -> Transition[AwaitNextMission.AwaitNextMission]:
            state_machine.logger.warning(
                f"Failed to initiate mission because: "
                f"{mission_failed.error_description}"
            )
            return AwaitNextMission.transition()

        event_handlers: List[EventHandlerMapping] = [
            EventHandlerMapping(
                name="stop_mission_event",
                event=events.api_requests.stop_mission.request,
                handler=lambda event: stop_mission_event_handler(
                    state_machine, event, mission_id
                ),
            ),
            EventHandlerMapping(
                name="pause_mission_event",
                event=events.api_requests.pause_mission.request,
                handler=_pause_mission_event_handler,
            ),
            EventHandlerMapping(
                name="mission_started_event",
                event=events.robot_service_events.mission_started,
                handler=lambda event: mission_started_event_handler(
                    state_machine, event
                ),
            ),
            EventHandlerMapping(
                name="mission_failed_event",
                event=events.robot_service_events.mission_failed,
                handler=_mission_failed_event_handler,
            ),
            EventHandlerMapping(
                name="mission_status_event",
                event=events.robot_service_events.mission_status_updated,
                handler=_mission_status_event_handler,
            ),
            EventHandlerMapping(
                name="robot_battery_update_event",
                event=shared_state.robot_battery_level,
                handler=_robot_battery_level_updated_handler,
                should_not_consume=True,
            ),
            EventHandlerMapping(
                name="send_to_lockdown_event",
                event=events.api_requests.send_to_lockdown.request,
                handler=_send_to_lockdown_event_handler,
            ),
            EventHandlerMapping(
                name="set_maintenance_mode",
                event=events.api_requests.set_maintenance_mode.request,
                handler=_set_maintenance_mode_event_handler,
            ),
        ]
        super().__init__(
            state_name=States.Monitor,
            state_machine=state_machine,
            event_handler_mappings=event_handlers,
        )


def transition(mission_id: str) -> Transition[Monitor]:
    def _transition(state_machine: "StateMachine"):
        return Monitor(state_machine, mission_id=mission_id)

    return _transition
