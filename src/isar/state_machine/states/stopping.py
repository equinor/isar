from typing import TYPE_CHECKING, List, Union

import isar.state_machine.states.await_next_mission as AwaitNextMission
import isar.state_machine.states.monitor as Monitor
import isar.state_machine.states.returning_home as ReturningHome
from isar.apis.models.models import ControlMissionResponse
from isar.eventhandlers.eventhandler import EventHandlerMapping, State, Transition
from isar.state_machine.states_enum import States
from robot_interface.models.exceptions.robot_exceptions import ErrorMessage

if TYPE_CHECKING:
    from isar.state_machine.state_machine import StateMachine


class Stopping(State):

    def __init__(self, state_machine: "StateMachine", mission_id: str):
        events = state_machine.events

        def _failed_stop_event_handler(
            error_message: ErrorMessage,
        ) -> Transition[Monitor.Monitor]:
            stopped_mission_response: ControlMissionResponse = ControlMissionResponse(
                success=False, failure_reason="ISAR failed to stop mission"
            )
            state_machine.events.api_requests.stop_mission.response.trigger_event(
                stopped_mission_response
            )
            return Monitor.transition(mission_id)

        def _successful_stop_event_handler(
            successful_stop: bool,
        ) -> Union[
            Transition[AwaitNextMission.AwaitNextMission],
            Transition[ReturningHome.ReturningHome],
        ]:
            state_machine.events.api_requests.stop_mission.response.trigger_event(
                ControlMissionResponse(success=True)
            )

            if not state_machine.battery_level_is_above_mission_start_threshold():
                state_machine.start_return_home_mission()
                return ReturningHome.transition()
            return AwaitNextMission.transition()

        event_handlers: List[EventHandlerMapping] = [
            EventHandlerMapping(
                name="failed_stop_event",
                event=events.robot_service_events.mission_failed_to_stop,
                handler=_failed_stop_event_handler,
            ),
            EventHandlerMapping(
                name="successful_stop_event",
                event=events.robot_service_events.mission_successfully_stopped,
                handler=_successful_stop_event_handler,
            ),
        ]
        super().__init__(
            state_name=States.Stopping,
            state_machine=state_machine,
            event_handler_mappings=event_handlers,
        )


def transition(mission_id: str) -> Transition[Stopping]:
    def _transition(state_machine: "StateMachine"):
        return Stopping(state_machine, mission_id)

    return _transition
