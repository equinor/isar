from typing import TYPE_CHECKING, List, Optional, Union

from isar.apis.models.models import MaintenanceResponse
from isar.eventhandlers.eventhandler import EventHandlerMapping, State, Transition
from isar.models.events import Event
from isar.state_machine.states.maintenance import Maintenance
from isar.state_machine.states.monitor import Monitor
from isar.state_machine.states.returning_home import ReturningHome
from isar.state_machine.states_enum import States
from robot_interface.models.exceptions.robot_exceptions import ErrorMessage

if TYPE_CHECKING:
    from isar.state_machine.state_machine import StateMachine


class StoppingDueToMaintenance(State):

    @staticmethod
    def transition(mission_id: str) -> Transition["StoppingDueToMaintenance"]:
        def _transition(state_machine: "StateMachine"):
            return StoppingDueToMaintenance(state_machine, mission_id)

        return _transition

    def __init__(self, state_machine: "StateMachine", mission_id: str):
        events = state_machine.events

        def _failed_stop_event_handler(
            event: Event[ErrorMessage],
        ) -> Optional[Union[Transition[ReturningHome], Transition[Monitor]]]:
            error_message: Optional[ErrorMessage] = event.consume_event()
            if error_message is not None:
                events.api_requests.set_maintenance_mode.response.trigger_event(
                    MaintenanceResponse(
                        is_maintenance_mode=False,
                        failure_reason="Failed to stop ongoing mission",
                    )
                )
                state_machine.logger.error(
                    f"Failed to stop mission in StoppingDueToMaintenance. Message: {error_message.error_description}"
                )
                # TODO: see https://github.com/equinor/isar/issues/1047
                if mission_id == "":
                    return ReturningHome.transition()
                return Monitor.transition(mission_id)
            return None

        def _successful_stop_event_handler(
            event: Event[bool],
        ) -> Optional[Transition[Maintenance]]:
            if event.consume_event():
                state_machine.publish_mission_aborted(
                    mission_id, "Mission aborted, robot being sent to maintenance", True
                )
                events.api_requests.set_maintenance_mode.response.trigger_event(
                    MaintenanceResponse(is_maintenance_mode=True)
                )
                return Maintenance.transition()
            return None

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
            state_name=States.StoppingDueToMaintenance,
            state_machine=state_machine,
            event_handler_mappings=event_handlers,
        )
