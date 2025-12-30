from typing import TYPE_CHECKING, List, Optional, Union

import isar.state_machine.states.await_next_mission as AwaitNextMission
import isar.state_machine.states.blocked_protective_stop as BlockedProtectiveStop
import isar.state_machine.states.home as Home
import isar.state_machine.states.maintenance as Maintenance
import isar.state_machine.states.offline as Offline
import isar.state_machine.states.stopping as Stopping
from isar.apis.models.models import MaintenanceResponse
from isar.eventhandlers.eventhandler import EventHandlerMapping, State, Transition
from isar.state_machine.states_enum import States
from isar.state_machine.utils.common_event_handlers import stop_mission_event_handler
from robot_interface.models.mission.status import RobotStatus

if TYPE_CHECKING:
    from isar.state_machine.state_machine import StateMachine


class UnknownStatus(State):

    def __init__(self, state_machine: "StateMachine"):
        # Ensures that we will check the status immediately instead of waiting for it to change
        events = state_machine.events
        shared_state = state_machine.shared_state
        events.robot_service_events.robot_status_changed.trigger_event(True)

        def _set_maintenance_mode_event_handler(
            should_set_maintenande_mode: bool,
        ) -> Transition[Maintenance.Maintenance]:
            events.api_requests.set_maintenance_mode.response.trigger_event(
                MaintenanceResponse(is_maintenance_mode=True)
            )
            return Maintenance.transition()

        def _robot_status_event_handler(
            has_changed: bool,
        ) -> Optional[
            Union[
                Transition[Home.Home],
                Transition[AwaitNextMission.AwaitNextMission],
                Transition[Offline.Offline],
                Transition[BlockedProtectiveStop.BlockedProtectiveStop],
                Transition[Stopping.Stopping],
            ]
        ]:
            robot_status: Optional[RobotStatus] = shared_state.robot_status.check()

            if robot_status == RobotStatus.Home:
                self.logger.info(
                    "Got robot status home while in unknown status state. Leaving unknown status state."
                )
                return Home.transition()
            elif robot_status == RobotStatus.Available:
                self.logger.info(
                    "Got robot status available while in unknown status state. Leaving unknown status state."
                )
                return AwaitNextMission.transition()
            elif robot_status == RobotStatus.Offline:
                self.logger.info(
                    "Got robot status offline while in unknown status state. Leaving unknown status state."
                )
                return Offline.transition()
            elif robot_status == RobotStatus.BlockedProtectiveStop:
                self.logger.info(
                    "Got robot status blocked protective stop while in unknown status state. Leaving unknown status state."
                )
                return BlockedProtectiveStop.transition()
            elif robot_status == RobotStatus.Busy:
                state_machine.events.state_machine_events.stop_mission.trigger_event(
                    True
                )
                self.logger.info(
                    "Got robot status busy while in unknown status state. Leaving unknown status state."
                )
                return Stopping.transition("")
            return None

        event_handlers: List[EventHandlerMapping] = [
            EventHandlerMapping(
                name="stop_mission_event",
                event=events.api_requests.stop_mission.request,
                handler=lambda event: stop_mission_event_handler(
                    state_machine, event, None
                ),
            ),
            EventHandlerMapping(
                name="robot_status_event",
                event=events.robot_service_events.robot_status_changed,
                handler=_robot_status_event_handler,
            ),
            EventHandlerMapping(
                name="set_maintenance_mode",
                event=events.api_requests.set_maintenance_mode.request,
                handler=_set_maintenance_mode_event_handler,
            ),
        ]
        super().__init__(
            state_name=States.UnknownStatus,
            state_machine=state_machine,
            event_handler_mappings=event_handlers,
        )


def transition() -> Transition[UnknownStatus]:
    def _transition(state_machine: "StateMachine"):
        return UnknownStatus(state_machine)

    return _transition
