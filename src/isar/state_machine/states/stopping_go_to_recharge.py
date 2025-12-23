from typing import TYPE_CHECKING, List, Optional

from isar.eventhandlers.eventhandler import EventHandlerMapping, State, Transition
from isar.models.events import Event
from isar.state_machine.states.going_to_recharging import GoingToRecharging
from isar.state_machine.states.monitor import Monitor
from isar.state_machine.states_enum import States
from robot_interface.models.exceptions.robot_exceptions import ErrorMessage

if TYPE_CHECKING:
    from isar.state_machine.state_machine import StateMachine


class StoppingGoToRecharge(State):

    @staticmethod
    def transition(mission_id: str) -> Transition["StoppingGoToRecharge"]:
        def _transition(state_machine: "StateMachine"):
            return StoppingGoToRecharge(state_machine, mission_id=mission_id)

        return _transition

    def __init__(self, state_machine: "StateMachine", mission_id: str):
        events = state_machine.events

        def _failed_stop_event_handler(
            event: Event[ErrorMessage],
        ) -> Optional[Transition[Monitor]]:
            error_message: Optional[ErrorMessage] = event.consume_event()
            if error_message is None:
                return None

            return Monitor.transition(mission_id)

        def _successful_stop_event_handler(
            event: Event[bool],
        ) -> Optional[Transition[GoingToRecharging]]:
            if not event.consume_event():
                return None

            state_machine.publish_mission_aborted(
                mission_id, "Robot battery too low to continue mission", True
            )
            state_machine.start_return_home_mission()
            return GoingToRecharging.transition()

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
            state_name=States.StoppingGoToRecharge,
            state_machine=state_machine,
            event_handler_mappings=event_handlers,
        )
