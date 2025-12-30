from typing import TYPE_CHECKING, List, Optional

import isar.state_machine.states.resuming as Resuming
import isar.state_machine.states.stopping_due_to_maintenance as StoppingDueToMaintenance
import isar.state_machine.states.stopping_go_to_lockdown as StoppingGoToLockdown
import isar.state_machine.states.stopping_paused_mission as StoppingPausedMission
from isar.apis.models.models import ControlMissionResponse
from isar.config.settings import settings
from isar.eventhandlers.eventhandler import EventHandlerMapping, State, Transition
from isar.state_machine.states_enum import States

if TYPE_CHECKING:
    from isar.state_machine.state_machine import StateMachine


class Paused(State):

    def __init__(self, state_machine: "StateMachine", mission_id: str):
        events = state_machine.events
        shared_state = state_machine.shared_state

        def _stop_mission_event_handler(
            stop_mission_id: str,
        ) -> Optional[Transition[StoppingPausedMission.StoppingPausedMission]]:
            if mission_id == stop_mission_id or stop_mission_id == "":
                state_machine.events.api_requests.stop_mission.response.trigger_event(
                    ControlMissionResponse(success=True)
                )
                state_machine.events.state_machine_events.stop_mission.trigger_event(
                    True
                )
                return StoppingPausedMission.transition(mission_id)
            else:
                state_machine.events.api_requests.stop_mission.response.trigger_event(
                    ControlMissionResponse(
                        success=False, failure_reason="Mission not found"
                    )
                )
                return None

        def _robot_battery_level_updated_handler(
            battery_level: float,
        ) -> Optional[Transition[StoppingPausedMission.StoppingPausedMission]]:
            if (
                battery_level is None
                or battery_level >= settings.ROBOT_MISSION_BATTERY_START_THRESHOLD
            ):
                return None

            state_machine.publish_mission_aborted(
                mission_id, "Robot battery too low to continue mission", True
            )
            state_machine.logger.warning(
                "Cancelling current mission due to low battery"
            )
            state_machine.events.state_machine_events.stop_mission.trigger_event(True)
            return StoppingPausedMission.transition(mission_id)

        def _send_to_lockdown_event_handler(
            should_lockdown: bool,
        ) -> Transition[StoppingGoToLockdown.StoppingGoToLockdown]:
            state_machine.logger.warning(
                "Cancelling current mission due to robot going to lockdown"
            )
            state_machine.events.state_machine_events.stop_mission.trigger_event(True)
            return StoppingGoToLockdown.transition(mission_id)

        def _set_maintenance_mode_event_handler(
            should_set_maintenande_mode: bool,
        ) -> Transition[StoppingDueToMaintenance.StoppingDueToMaintenance]:
            state_machine.logger.warning(
                "Cancelling current mission due to robot going to maintenance mode"
            )
            state_machine.events.state_machine_events.stop_mission.trigger_event(True)
            return StoppingDueToMaintenance.transition(mission_id)

        def _resume_mission_event_handler(
            should_resume: bool,
        ) -> Optional[Transition[Resuming.Resuming]]:
            state_machine.events.api_requests.resume_mission.response.trigger_event(
                ControlMissionResponse(success=True)
            )
            state_machine.events.state_machine_events.resume_mission.trigger_event(True)
            return Resuming.transition(mission_id)

        event_handlers: List[EventHandlerMapping] = [
            EventHandlerMapping(
                name="stop_mission_event",
                event=events.api_requests.stop_mission.request,
                handler=_stop_mission_event_handler,
            ),
            EventHandlerMapping(
                name="resume_mission_event",
                event=events.api_requests.resume_mission.request,
                handler=_resume_mission_event_handler,
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
            state_name=States.Paused,
            state_machine=state_machine,
            event_handler_mappings=event_handlers,
        )


def transition(mission_id: str) -> Transition[Paused]:
    def _transition(state_machine: "StateMachine"):
        return Paused(state_machine, mission_id)

    return _transition
