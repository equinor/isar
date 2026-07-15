from typing import List

import isar.state_machine.states.home as Home
import isar.state_machine.states.intervention_needed as InterventionNeeded
import isar.state_machine.states.maintenance as Maintenance
import isar.state_machine.states.unknown_status as UnknownStatus
from isar.models.events import EmptyMessage, Events
from isar.state_machine.state import EventHandlerMapping, State, Transition
from isar.state_machine.states_enum import States
from robot_interface.models.mission.status import RobotStatus


class Offline(State):

    def __init__(self, events: Events):

        def _robot_status_event_handler(
            robot_status: RobotStatus,
        ) -> (
            Transition[Home.Home]
            | Transition[InterventionNeeded.InterventionNeeded]
            | Transition[Maintenance.Maintenance]
            | Transition[UnknownStatus.UnknownStatus]
            | None
        ):
            if robot_status == RobotStatus.Offline:
                return None
            elif robot_status == RobotStatus.Home:
                self.logger.info(
                    "Got robot status home while in offline state. Leaving offline state."
                )
                return Home.transition()
            elif robot_status == RobotStatus.Available:
                self.logger.info(
                    "Got robot status available while in offline state. Leaving offline state."
                )
                return InterventionNeeded.transition(
                    "Robot not home after going online. Localisation likely needed"
                )
            elif robot_status == RobotStatus.TeleOperation:
                self.logger.info(
                    "Got robot status teleoperation while in offline state. Leaving offline state."
                )
                return Maintenance.transition_without_replying_to_API()
            self.logger.info(
                f"Got unexpected status {robot_status} while in offline state. Leaving offline state."
            )
            return UnknownStatus.transition()

        event_handlers: List[EventHandlerMapping] = [
            EventHandlerMapping[RobotStatus](
                name="robot_status_event",
                event=events.robot_service_events.robot_status_update,
                handler=_robot_status_event_handler,
            ),
            EventHandlerMapping[EmptyMessage](
                name="set_maintenance_mode",
                event=events.api_requests.set_maintenance_mode.request,
                handler=lambda _: Maintenance.transition_and_reply_to_API(),
            ),
        ]
        super().__init__(
            state_name=States.Offline,
            signal_exit_event=events.signal_state_machine_exit,
            event_handler_mappings=event_handlers,
        )


def transition() -> Transition[Offline]:
    def _transition(events: Events) -> Offline:
        return Offline(events)

    return _transition
