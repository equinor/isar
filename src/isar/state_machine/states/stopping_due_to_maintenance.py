from typing import TYPE_CHECKING, List

import isar.state_machine.states.intervention_needed as InterventionNeeded
import isar.state_machine.states.maintenance as Maintenance
from isar.apis.models.models import MaintenanceResponse
from isar.eventhandlers.eventhandler import EventHandlerMapping, State, Transition
from isar.models.events import EmptyMessage
from isar.state_machine.states_enum import States
from robot_interface.models.exceptions.robot_exceptions import ErrorMessage

if TYPE_CHECKING:
    from isar.state_machine.state_machine import StateMachine


class StoppingDueToMaintenance(State):

    def __init__(self, state_machine: "StateMachine", mission_id: str):
        events = state_machine.events

        def _failed_stop_event_handler(
            error_message: ErrorMessage,
        ) -> Transition[InterventionNeeded.InterventionNeeded]:
            events.api_requests.set_maintenance_mode.response.trigger_event(
                MaintenanceResponse(
                    is_maintenance_mode=False,
                    failure_reason="Failed to stop ongoing mission",
                )
            )
            state_machine.logger.error(
                f"Failed to stop mission in StoppingDueToMaintenance. Message: {error_message.error_description}"
            )
            return InterventionNeeded.transition()

        def _successful_stop_event_handler(
            successful_stop: EmptyMessage,
        ) -> Transition[Maintenance.Maintenance]:
            state_machine.publish_mission_aborted(
                mission_id, "Mission aborted, robot being sent to maintenance", True
            )
            events.api_requests.set_maintenance_mode.response.trigger_event(
                MaintenanceResponse(is_maintenance_mode=True)
            )
            return Maintenance.transition()

        event_handlers: List[EventHandlerMapping] = [
            EventHandlerMapping[ErrorMessage](
                name="failed_stop_event",
                event=events.robot_service_events.mission_failed_to_stop,
                handler=_failed_stop_event_handler,
            ),
            EventHandlerMapping[EmptyMessage](
                name="successful_stop_event",
                event=events.robot_service_events.mission_successfully_stopped,
                handler=_successful_stop_event_handler,
            ),
        ]
        super().__init__(
            state_name=States.StoppingDueToMaintenance,
            state_machine=state_machine,
            event_handler_mappings=event_handlers,
        )


def transition(mission_id: str) -> Transition[StoppingDueToMaintenance]:
    def _transition(state_machine: "StateMachine") -> StoppingDueToMaintenance:
        return StoppingDueToMaintenance(state_machine, mission_id)

    return _transition
