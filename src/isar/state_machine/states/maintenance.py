from typing import TYPE_CHECKING, List, Optional, Union

from isar.eventhandlers.eventhandler import EventHandlerMapping, State, Transition
from isar.models.events import Event
from isar.state_machine.states.home import Home
from isar.state_machine.states.intervention_needed import InterventionNeeded
from isar.state_machine.states_enum import States
from robot_interface.models.mission.status import RobotStatus

if TYPE_CHECKING:
    from isar.state_machine.state_machine import StateMachine


class Maintenance(State):

    @staticmethod
    def transition() -> Transition["Maintenance"]:
        def _transition(state_machine: "StateMachine"):
            return Maintenance(state_machine)

        return _transition

    def __init__(self, state_machine: "StateMachine"):
        events = state_machine.events

        def _release_from_maintenance_handler(
            event: Event[bool],
        ) -> Optional[Union[Transition[Home], Transition[InterventionNeeded]]]:
            should_release_from_maintenance: bool = event.consume_event()
            if should_release_from_maintenance:
                events.api_requests.release_from_maintenance_mode.response.trigger_event(
                    True
                )

                robot_status = state_machine.shared_state.robot_status.check()
                if robot_status == RobotStatus.Home:
                    return Home.transition()
                else:
                    return InterventionNeeded.transition()

            return None

        event_handlers: List[EventHandlerMapping] = [
            EventHandlerMapping(
                name="release_from_maintenance",
                event=events.api_requests.release_from_maintenance_mode.request,
                handler=_release_from_maintenance_handler,
            ),
        ]

        super().__init__(
            state_name=States.Maintenance,
            state_machine=state_machine,
            event_handler_mappings=event_handlers,
        )
