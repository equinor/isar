from typing import TYPE_CHECKING, List

import isar.state_machine.states.resuming as Resuming
import isar.state_machine.states.stopping_due_to_maintenance as StoppingDueToMaintenance
import isar.state_machine.states.stopping_go_to_lockdown as StoppingGoToLockdown
import isar.state_machine.states.stopping_go_to_recharge as StoppingGoToRecharge
import isar.state_machine.states.stopping_paused_mission as StoppingPausedMission
from isar.apis.models.models import ControlMissionResponse
from isar.eventhandlers.state import EventHandlerMapping, State, Transition
from isar.models.events import EmptyMessage
from isar.state_machine.states_enum import States

if TYPE_CHECKING:
    from isar.state_machine.state_machine import StateMachine


class Paused(State):

    def __init__(self, state_machine: "StateMachine", mission_id: str):
        events = state_machine.events

        def _stop_mission_event_handler(
            stop_mission_id: str,
        ) -> Transition[StoppingPausedMission.StoppingPausedMission] | None:
            if mission_id == stop_mission_id or stop_mission_id == "":
                return StoppingPausedMission.transition_and_trigger_stop(
                    mission_id, True
                )
            else:
                state_machine.events.api_requests.stop_mission.response.trigger_event(
                    ControlMissionResponse(
                        success=False, failure_reason="Mission not found"
                    )
                )
                return None

        event_handlers: List[EventHandlerMapping] = [
            EventHandlerMapping[str](
                name="stop_mission_event",
                event=events.api_requests.stop_mission.request,
                handler=_stop_mission_event_handler,
            ),
            EventHandlerMapping[EmptyMessage](
                name="resume_mission_event",
                event=events.api_requests.resume_mission.request,
                handler=lambda _: Resuming.transition_resume_mission_and_respond_to_API(
                    mission_id
                ),
            ),
            EventHandlerMapping[EmptyMessage](
                name="robot_battery_below_threshold_event",
                event=events.robot_service_events.battery_below_mission_threshold,
                handler=lambda _: StoppingGoToRecharge.transition_and_stop_mission(),
            ),
            EventHandlerMapping[EmptyMessage](
                name="send_to_lockdown_event",
                event=events.api_requests.send_to_lockdown.request,
                handler=lambda _: StoppingGoToLockdown.transition_and_stop_mission(
                    mission_id
                ),
            ),
            EventHandlerMapping[EmptyMessage](
                name="set_maintenance_mode",
                event=events.api_requests.set_maintenance_mode.request,
                handler=lambda _: StoppingDueToMaintenance.transition_and_stop_mission(
                    mission_id
                ),
            ),
        ]
        super().__init__(
            state_name=States.Paused,
            state_machine=state_machine,
            event_handler_mappings=event_handlers,
        )


def transition(mission_id: str) -> Transition[Paused]:
    def _transition(state_machine: "StateMachine") -> Paused:
        return Paused(state_machine, mission_id)

    return _transition
