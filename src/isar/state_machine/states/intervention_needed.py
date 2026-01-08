from typing import TYPE_CHECKING, List, Optional

import isar.state_machine.states.home as Home
import isar.state_machine.states.maintenance as Maintenance
import isar.state_machine.states.returning_home as ReturningHome
import isar.state_machine.states.unknown_status as UnknownStatus
from isar.apis.models.models import MaintenanceResponse
from isar.eventhandlers.eventhandler import EventHandlerMapping, State, Transition
from isar.models.events import EmptyMessage
from isar.state_machine.states_enum import States
from robot_interface.models.mission.status import RobotStatus

if TYPE_CHECKING:
    from isar.state_machine.state_machine import StateMachine


class InterventionNeeded(State):

    def __init__(self, state_machine: "StateMachine"):
        events = state_machine.events
        shared_state = state_machine.shared_state

        def _set_maintenance_mode_event_handler(
            should_set_maintenance_mode: EmptyMessage,
        ) -> Transition[Maintenance.Maintenance]:
            events.api_requests.set_maintenance_mode.response.trigger_event(
                MaintenanceResponse(is_maintenance_mode=True)
            )
            return Maintenance.transition()

        def release_intervention_needed_handler(
            should_release: EmptyMessage,
        ) -> Transition[UnknownStatus.UnknownStatus]:
            state_machine.events.api_requests.release_intervention_needed.response.trigger_event(
                EmptyMessage()
            )
            return UnknownStatus.transition()

        def _robot_status_event_handler(
            has_changed: EmptyMessage,
        ) -> Optional[Transition[Home.Home]]:
            robot_status: Optional[RobotStatus] = shared_state.robot_status.check()
            if robot_status == RobotStatus.Home:
                self.logger.info(
                    "Got robot status home while in intervention needed state. Leaving intervention needed state."
                )
                return Home.transition()
            return None

        event_handlers: List[EventHandlerMapping] = [
            EventHandlerMapping[EmptyMessage](
                name="return_home_event",
                event=events.api_requests.return_home.request,
                handler=lambda event: ReturningHome.transition_and_start_mission(True),
            ),
            EventHandlerMapping[EmptyMessage](
                name="release_intervention_needed_event",
                event=events.api_requests.release_intervention_needed.request,
                handler=release_intervention_needed_handler,
            ),
            EventHandlerMapping[EmptyMessage](
                name="set_maintenance_mode",
                event=events.api_requests.set_maintenance_mode.request,
                handler=_set_maintenance_mode_event_handler,
            ),
            EventHandlerMapping[EmptyMessage](
                name="robot_status_event",
                event=events.robot_service_events.robot_status_changed,
                handler=_robot_status_event_handler,
            ),
        ]
        super().__init__(
            state_name=States.InterventionNeeded,
            state_machine=state_machine,
            event_handler_mappings=event_handlers,
        )


def transition() -> Transition[InterventionNeeded]:
    def _transition(state_machine: "StateMachine"):
        return InterventionNeeded(state_machine)

    return _transition
