from typing import List

import isar.state_machine.states.home as Home
import isar.state_machine.states.maintenance as Maintenance
import isar.state_machine.states.returning_home as ReturningHome
import isar.state_machine.states.unknown_status as UnknownStatus
from isar.models.events import EmptyMessage, Events
from isar.services.utilities.mqtt_utilities import publish_intervention_needed
from isar.state_machine.state import EventHandlerMapping, State, Transition
from isar.state_machine.states_enum import States
from robot_interface.models.mission.status import RobotStatus


class InterventionNeeded(State):

    def __init__(self, events: Events):

        def release_intervention_needed_handler(
            should_release: EmptyMessage,
        ) -> Transition[UnknownStatus.UnknownStatus]:
            events.api_requests.release_intervention_needed.response.trigger_event(
                EmptyMessage()
            )
            return UnknownStatus.transition()

        def _robot_status_event_handler(
            robot_status: RobotStatus,
        ) -> Transition[Home.Home] | None:
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
                handler=lambda _: Maintenance.transition_and_reply_to_API(),
            ),
            EventHandlerMapping[RobotStatus](
                name="robot_status_event",
                event=events.robot_service_events.robot_status_update,
                handler=_robot_status_event_handler,
            ),
        ]
        super().__init__(
            state_name=States.InterventionNeeded,
            signal_exit_event=events.signal_state_machine_exit,
            event_handler_mappings=event_handlers,
        )


def transition(reason: str) -> Transition[InterventionNeeded]:
    def _transition(events: Events) -> InterventionNeeded:
        publish_intervention_needed(events.mqtt_queue, error_message=reason)

        return InterventionNeeded(events)

    return _transition
